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
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated request to the GlueUp API.

        Gets fresh headers from the auth module for each request attempt,
        ensuring the signature and token are valid.

        Args:
            method: The HTTP method (GET, POST, etc.).
            path: The API path.
            params: Optional query parameters.
            json_body: Optional JSON body for the request.
            extra_headers: Optional additional headers (e.g., requestOrganizationId).

        Returns:
            The JSON response as a dictionary.

        Raises:
            GlueUpClientError: If the request fails with a 4xx/5xx status.
            requests.RequestException: If a network error occurs.
        """
        url = self._build_url(path)
        headers = self.auth.get_headers(method)
        if extra_headers:
            headers.update(extra_headers)

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

    def list_members(self, organization_id: str, limit: int = 100, offset: int = 0) -> List[Dict]:
        """List members from the membership directory.

        Uses POST /membershipDirectory/members endpoint.

        Args:
            organization_id: The organization ID for the requestOrganizationId header.
            limit: Maximum number of records to return (default 100).
            offset: Number of records to skip (default 0).

        Returns:
            A list of member dictionaries with membership and individualMember data.
        """
        json_body = {
            "projection": [],
            "filter": [],
            "order": {"familyName": "asc"},
            "offset": offset,
            "limit": limit,
        }

        data = self._request(
            "POST",
            self.endpoints["members_directory"],
            json_body=json_body,
            extra_headers={"requestOrganizationId": organization_id},
        )
        return data.get("value") or []

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

    def list_events(
        self,
        limit: int = 100,
        offset: int = 0,
        published_only: bool = True,
        future_only: bool = True,
    ) -> List[Dict]:
        """List events from the GlueUp API.

        Uses POST /event/list endpoint.

        Args:
            limit: Maximum number of records to return (default 100).
            offset: Number of records to skip (default 0).
            published_only: If True, only return published events (default True).
            future_only: If True, only return future/upcoming events (default True).

        Returns:
            A list of event dictionaries.
        """
        import time

        # Request specific fields from GlueUp API
        json_body: Dict[str, Any] = {
            "projection": [
                "id",
                "title",
                "subTitle",
                "summary",
                "about",
                "description",
                "language.code",
                "defaultLanguage.code",
                "startDateTime",
                "endDateTime",
                "venueInfo.id",
                "venueInfo.name",
                "venueInfo.address",
                "venueInfo.city",
                "venueInfo.timezone",
                "venueInfo.country.name",
                "venueInfo.country.code",
                "venueInfo.map.latitude",
                "venueInfo.map.longitude",
                "template.images.banner.uri",
                "template.images.headerImage.uri",
                "published",
                "openToPublic",
                "imageUrl",
                "coverImageUrl",
            ],
            "filter": [],
            "order": {"startDateTime": "asc"},
            "offset": offset,
            "limit": limit,
        }

        # Filter for published events if requested
        if published_only:
            json_body["filter"].append({
                "projection": "published",
                "operator": "eq",
                "values": [True]
            })

        # Filter for future events only (endDateTime > now)
        if future_only:
            current_time_ms = int(time.time() * 1000)
            json_body["filter"].append({
                "projection": "endDateTime",
                "operator": "gt",
                "values": [current_time_ms]
            })

        data = self._request("POST", self.endpoints.get("events_list", "/event/list"), json_body=json_body)
        return data.get("value") or data.get("records") or data.get("events") or []

    def get_all_events(self, published_only: bool = True, future_only: bool = True) -> List[Dict]:
        """Paginate through all events and return the complete list.

        Args:
            published_only: If True, only return published events (default True).
            future_only: If True, only return future/upcoming events (default True).

        Returns:
            A list of all event dictionaries.
        """
        all_events = []
        offset = 0
        limit = 100

        while True:
            events = self.list_events(
                limit=limit,
                offset=offset,
                published_only=published_only,
                future_only=future_only
            )
            all_events.extend(events)

            if len(events) < limit:
                break
            offset += limit

        logger.info(
            "Fetched %d events from GlueUp (published_only=%s, future_only=%s)",
            len(all_events),
            published_only,
            future_only
        )
        return all_events

    def get_all_members(self, organization_id: str) -> List[Dict]:
        """Paginate through all members and return the complete list.

        Uses POST /membershipDirectory/members with offset pagination.

        Args:
            organization_id: The organization ID for the requestOrganizationId header.

        Returns:
            A list of all member dictionaries.
        """
        all_members = []
        offset = 0
        limit = 100

        while True:
            members = self.list_members(organization_id, limit=limit, offset=offset)
            all_members.extend(members)

            if len(members) < limit:
                break
            offset += limit

        return all_members

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

    def list_corporate_memberships(
        self, organization_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict]:
        """List corporate memberships from the membership directory.

        Uses POST /membershipDirectory/corporateMemberships endpoint.

        Args:
            organization_id: The organization ID for the requestOrganizationId header.
            limit: Maximum number of records to return (default 100).
            offset: Number of records to skip (default 0).

        Returns:
            A list of corporate membership dictionaries with membership, adminContact, and memberContacts data.
        """
        json_body = {
            "projection": [],
            "filter": [],
            "order": {"name": "asc"},
            "offset": offset,
            "limit": limit,
        }

        data = self._request(
            "POST",
            self.endpoints["corporate_memberships_directory"],
            json_body=json_body,
            extra_headers={"requestOrganizationId": organization_id},
        )
        return data.get("value") or []

    def get_all_corporate_memberships(self, organization_id: str) -> List[Dict]:
        """Paginate through all corporate memberships and return the complete list.

        Uses POST /membershipDirectory/corporateMemberships with offset pagination.

        Args:
            organization_id: The organization ID for the requestOrganizationId header.

        Returns:
            A list of all corporate membership dictionaries.
        """
        all_corporate = []
        offset = 0
        limit = 100

        while True:
            corporate = self.list_corporate_memberships(organization_id, limit=limit, offset=offset)
            all_corporate.extend(corporate)

            if len(corporate) < limit:
                break
            offset += limit

        return all_corporate

    def get_all_members_unified(self, organization_id: str) -> Dict[str, List[Dict]]:
        """Fetch both individual and corporate members.

        Args:
            organization_id: The organization ID for API requests.

        Returns:
            A dictionary with 'individual' and 'corporate' keys containing member lists.
        """
        logger.info("Fetching individual members...")
        individual = self.get_all_members(organization_id)
        logger.info("Fetched %d individual members", len(individual))

        logger.info("Fetching corporate memberships...")
        corporate = self.get_all_corporate_memberships(organization_id)
        logger.info("Fetched %d corporate memberships", len(corporate))

        return {"individual": individual, "corporate": corporate}
