"""GlueUp API client with dynamic authentication.

This module provides the GlueUpClient class for interacting with the GlueUp API.
It uses GlueUpAuth for dynamic header generation per request.
"""

import logging
from typing import Any, Dict, List, Optional

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .glueup_auth import GlueUpAuth

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30


class GlueUpClientError(Exception):
    """Raised when a GlueUp API request fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GlueUpClient:
    """Client for interacting with the GlueUp API.

    Uses GlueUpAuth for dynamic authentication headers on each request,
    ensuring fresh signatures and valid tokens.

    Attributes:
        base_url: The base URL for the GlueUp API.
        auth: The GlueUpAuth instance for header generation.
        endpoints: A dictionary mapping endpoint names to paths.
    """

    def __init__(self, base_url: str, auth: GlueUpAuth, endpoints: Dict[str, str]):
        """Initialize the GlueUp client.

        Args:
            base_url: The base URL for the GlueUp API.
            auth: A GlueUpAuth instance for dynamic authentication.
            endpoints: A dictionary mapping endpoint names to API paths.
        """
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.endpoints = endpoints
        self._session = requests.Session()

    def _build_url(self, path: str) -> str:
        """Build a full URL from a path.

        Args:
            path: The API path (e.g., "/users").

        Returns:
            The full URL.
        """
        if not path.startswith("/"):
            path = "/" + path
        return self.base_url + path

    @retry(
        reraise=True,
        retry=retry_if_exception_type((GlueUpClientError, requests.RequestException)),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(5),
    )
    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated request to the GlueUp API.

        Gets fresh headers from the auth module for each request attempt,
        ensuring the signature and token are valid.

        Args:
            method: The HTTP method (GET, POST, etc.).
            path: The API path.
            params: Optional query parameters.
            json_body: Optional JSON body for the request.

        Returns:
            The JSON response as a dictionary.

        Raises:
            GlueUpClientError: If the request fails with a 4xx/5xx status.
            requests.RequestException: If a network error occurs.
        """
        url = self._build_url(path)
        headers = self.auth.get_headers(method)

        logger.debug("Making %s request to %s", method, url)

        response = self._session.request(
            method,
            url,
            params=params,
            json=json_body,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )

        if response.status_code >= 400:
            logger.error(
                "Request failed: %s %s returned %d: %s",
                method,
                url,
                response.status_code,
                response.text,
            )
            raise GlueUpClientError(
                f"HTTP {response.status_code}: {response.text}",
                status_code=response.status_code,
            )

        if not response.content:
            return {}

        try:
            return response.json()
        except ValueError:
            logger.warning("Response is not valid JSON, returning raw text")
            return {"raw": response.text}

    def list_users(self, updated_since: Optional[str] = None) -> List[Dict]:
        """List users from the GlueUp API.

        Args:
            updated_since: Optional ISO timestamp to filter users updated after this time.

        Returns:
            A list of user dictionaries.
        """
        params = {}
        if updated_since:
            params["updated_since"] = updated_since

        data = self._request("GET", self.endpoints["users_list"], params=params)
        # Normalize: expect data may be in {records:[...]} or {data:[...]}
        items = data.get("records") or data.get("data") or data.get("users") or []
        return items

    def list_memberships(self, user_id: Optional[str] = None) -> List[Dict]:
        """List memberships from the GlueUp API.

        Args:
            user_id: Optional user ID to filter memberships.

        Returns:
            A list of membership dictionaries.
        """
        params = {}
        if user_id:
            params["user_id"] = user_id

        data = self._request("GET", self.endpoints["memberships_list"], params=params)
        items = data.get("records") or data.get("data") or data.get("memberships") or []
        return items

    def list_events(self) -> List[Dict]:
        """List events from the GlueUp API.

        Returns:
            A list of event dictionaries.
        """
        data = self._request("GET", self.endpoints.get("events_list", "/events"))
        return data.get("records") or data.get("data") or data.get("events") or []

    def get_all_users(self) -> List[Dict]:
        """Paginate through all users and return the complete list.

        Returns:
            A list of all user dictionaries.
        """
        all_users = []
        page = 1

        while True:
            params = {"page": page, "per_page": 100}
            data = self._request("GET", self.endpoints["users_list"], params=params)
            users = data.get("records") or data.get("data") or data.get("users") or []
            all_users.extend(users)

            if len(users) < 100 or "next_page" not in data:
                break
            page += 1

        return all_users

    def get_all_memberships(self) -> List[Dict]:
        """Paginate through all memberships and return the complete list.

        Returns:
            A list of all membership dictionaries.
        """
        all_memberships = []
        page = 1

        while True:
            params = {"page": page, "per_page": 100}
            data = self._request("GET", self.endpoints["memberships_list"], params=params)
            memberships = data.get("records") or data.get("data") or data.get("memberships") or []
            all_memberships.extend(memberships)

            if len(memberships) < 100 or "next_page" not in data:
                break
            page += 1

        return all_memberships
