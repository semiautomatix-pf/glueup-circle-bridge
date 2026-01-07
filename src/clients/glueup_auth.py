"""GlueUp authentication module for dynamic header generation.

This module handles the authentication requirements for the GlueUp API:
- Dynamic 'a' header generation using HMAC-SHA256
- Session token management with automatic refresh
"""

import hashlib
import hmac
import logging
import threading
import time
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)


class GlueUpAuthError(Exception):
    """Raised when GlueUp authentication fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class GlueUpAuth:
    """Handles GlueUp API authentication and header generation.

    The GlueUp API requires two headers for authenticated requests:
    - 'a': A dynamically generated HMAC-SHA256 signature header
    - 'token': A session token obtained from the /v2/user/session endpoint

    Attributes:
        base_url: The base URL for the GlueUp API.
        public_key: The public API key for signing requests.
        private_key: The private API key used as HMAC secret.
        email: The user email for session authentication.
        passphrase: The user passphrase for session authentication.
        version: The API version string (default "1.0").
    """

    SESSION_ENDPOINT = "/v2/user/session"
    DEFAULT_TIMEOUT = 30
    TOKEN_EXPIRY_BUFFER_MS = 60 * 1000  # Refresh 60 seconds before expiry

    def __init__(
        self,
        base_url: str,
        public_key: str,
        private_key: str,
        email: str,
        passphrase: str,
        version: str = "1.0",
    ):
        """Initialize the GlueUp authentication handler.

        Args:
            base_url: The base URL for the GlueUp API.
            public_key: The public API key for signing requests.
            private_key: The private API key used as HMAC secret.
            email: The user email for session authentication.
            passphrase: The user passphrase for session authentication.
            version: The API version string (default "1.0").
        """
        self.base_url = base_url.rstrip("/")
        self.public_key = public_key
        self.private_key = private_key
        self.email = email
        self.passphrase = passphrase
        self.version = version

        self._token: Optional[str] = None
        self._token_expiry: Optional[int] = None
        self._token_lock = threading.Lock()

    def generate_a_header(self, method: str) -> str:
        """Generate the 'a' header for a GlueUp API request.

        The header format is: v=1.0;k=<publicKey>;ts=<timestampMillis>;d=<hex_hmac_sha256>

        The HMAC-SHA256 digest is computed from:
            baseString = {METHOD}{publicKey}{version}{timestamp}

        Args:
            method: The HTTP method (GET, POST, etc.) in uppercase.

        Returns:
            The formatted 'a' header string.
        """
        timestamp_millis = int(time.time() * 1000)
        base_string = f"{method.upper()}{self.public_key}{self.version}{timestamp_millis}"

        digest = hmac.new(
            self.private_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        header = f"v={self.version};k={self.public_key};ts={timestamp_millis};d={digest}"
        logger.debug("Generated 'a' header for method %s", method)
        return header

    def _is_token_valid(self, current_time_millis: int) -> bool:
        """Check if the current token is valid with expiry buffer.

        Args:
            current_time_millis: The current time in milliseconds.

        Returns:
            True if token exists and won't expire within the buffer period.
        """
        if not self._token or not self._token_expiry:
            return False
        return current_time_millis < (self._token_expiry - self.TOKEN_EXPIRY_BUFFER_MS)

    def get_token(self) -> str:
        """Get a valid session token, authenticating if necessary.

        Returns a cached token if it exists and has not expired (with buffer).
        Otherwise, calls _authenticate() to obtain a new token.

        This method is thread-safe using double-check locking to prevent
        race conditions when multiple threads attempt to refresh simultaneously.

        Returns:
            A valid session token string.

        Raises:
            GlueUpAuthError: If authentication fails.
        """
        current_time_millis = int(time.time() * 1000)

        # Fast path: check without lock
        if self._is_token_valid(current_time_millis):
            logger.debug("Using cached token (expires in %d ms)", self._token_expiry - current_time_millis)
            return self._token

        # Slow path: acquire lock for refresh
        with self._token_lock:
            # Double-check after acquiring lock (another thread may have refreshed)
            if self._is_token_valid(current_time_millis):
                logger.debug("Token refreshed by another thread, using cached token")
                return self._token

            logger.info("Token expired or not present, authenticating...")
            return self._authenticate()

    def _authenticate(self) -> str:
        """Authenticate with GlueUp to obtain a new session token.

        Calls the /v2/user/session endpoint with email and MD5-hashed passphrase
        to obtain a new session token.

        Returns:
            The new session token string.

        Raises:
            GlueUpAuthError: If authentication fails.
        """
        url = f"{self.base_url}{self.SESSION_ENDPOINT}"
        a_header = self.generate_a_header("POST")

        headers = {
            "a": a_header,
            "Content-Type": "application/json",
        }

        # Hash the passphrase with MD5 as required by GlueUp API
        passphrase_hash = hashlib.md5(self.passphrase.encode("utf-8")).hexdigest()

        payload = {
            "email": {"value": self.email},
            "passphrase": {"value": passphrase_hash},
        }

        logger.debug("Authenticating with GlueUp at %s", url)

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.DEFAULT_TIMEOUT,
            )
        except requests.RequestException as e:
            logger.error("Authentication request failed: %s", e)
            raise GlueUpAuthError(f"Authentication request failed: {e}") from e

        if response.status_code >= 400:
            logger.error(
                "Authentication failed with status %d: %s",
                response.status_code,
                response.text,
            )
            raise GlueUpAuthError(
                f"Authentication failed: {response.text}",
                status_code=response.status_code,
            )

        try:
            data = response.json()
        except ValueError as e:
            logger.error("Failed to parse authentication response: %s", e)
            raise GlueUpAuthError("Invalid JSON response from authentication endpoint") from e

        # Extract token from response: {"value": {"token": "...", "expiry": ...}}
        value = data.get("value", {})
        token = value.get("token")
        expiry = value.get("expiry")

        if not token:
            logger.error("No token in authentication response: %s", data)
            raise GlueUpAuthError("No token returned in authentication response")

        self._token = token
        self._token_expiry = expiry

        logger.info("Successfully authenticated, token expires at %s", expiry)
        return self._token

    def get_headers(self, method: str) -> Dict[str, str]:
        """Get all headers required for a GlueUp API request.

        Generates the dynamic 'a' header and includes the session token.

        Args:
            method: The HTTP method (GET, POST, etc.) for the request.

        Returns:
            A dictionary containing all required headers:
            - 'a': The dynamically generated signature header
            - 'token': The session token
            - 'Content-Type': application/json

        Raises:
            GlueUpAuthError: If authentication fails when obtaining the token.
        """
        return {
            "a": self.generate_a_header(method),
            "token": self.get_token(),
            "Content-Type": "application/json",
        }
