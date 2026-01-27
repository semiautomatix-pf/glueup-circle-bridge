import logging
from typing import Any, Dict, List, Optional
from .http import HttpClient

logger = logging.getLogger(__name__)

class CircleClient:
    def __init__(self, base_url: str, api_token: str, endpoints: Dict[str, str]):
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        self.http = HttpClient(base_url, headers=headers)
        self.endpoints = endpoints
        self._cached_user_id: Optional[int] = None

    def list_members(self, page: int = 1, per_page: int = 100) -> List[Dict]:
        params = {"page": page, "per_page": per_page}
        data = self.http.request("GET", self.endpoints["list_members"], params=params)
        # Admin API returns paginated {records:[...]} commonly
        return data.get("records") or data.get("members") or data.get("data") or []

    def invite_member(self, email: str, name: Optional[str] = None, spaces: Optional[List[str]] = None, tags: Optional[List[str]] = None) -> Dict:
        body = {"email": email}
        if name:
            # Split name into first_name and last_name for Circle API
            parts = name.strip().split(maxsplit=1)
            body["first_name"] = parts[0]
            body["last_name"] = parts[1] if len(parts) > 1 else ""
        if spaces:
            body["space_ids"] = spaces
        if tags:
            body["tags"] = tags
        return self.http.request("POST", self.endpoints["invite_member"], json_body=body)

    def update_member(self, member_id: str, payload: Dict) -> Dict:
        path = self.endpoints["update_member"].replace("{member_id}", member_id)
        return self.http.request("PUT", path, json_body=payload)

    def add_member_to_space(self, email: str, space_id: str) -> Dict:
        body = {"email": email, "space_id": space_id}
        return self.http.request("POST", self.endpoints["add_member_to_space"], json_body=body)

    def remove_member_from_space(self, email: str, space_id: str) -> Dict:
        params = {"email": email, "space_id": space_id}
        return self.http.request("DELETE", self.endpoints["remove_member_from_space"], params=params)

    def list_spaces(self, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
        params = {"page": page, "per_page": per_page}
        return self.http.request("GET", self.endpoints.get("list_spaces", "/spaces"), params=params)

    def list_space_members(self, space_id: str, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
        params = {"space_id": space_id, "page": page, "per_page": per_page}
        return self.http.request("GET", self.endpoints["list_space_members"], params=params)

    def get_all_members(self, per_page: int = 100) -> List[Dict]:
        """Fetch all members by paginating through results using has_next_page."""
        all_members = []
        page = 1
        while True:
            params = {"page": page, "per_page": per_page}
            data = self.http.request("GET", self.endpoints["list_members"], params=params)
            records = data.get("records") or data.get("members") or data.get("data") or []
            all_members.extend(records)
            if not data.get("has_next_page", False):
                break
            page += 1
        return all_members

    def get_all_spaces(self, per_page: int = 100) -> List[Dict]:
        """Fetch all spaces by paginating through results using has_next_page."""
        all_spaces = []
        page = 1
        while True:
            params = {"page": page, "per_page": per_page}
            data = self.http.request("GET", self.endpoints.get("list_spaces", "/spaces"), params=params)
            records = data.get("records") or data.get("data") or data.get("spaces") or []
            all_spaces.extend(records)
            if not data.get("has_next_page", False):
                break
            page += 1
        return all_spaces

    # Event methods
    def list_events(self, space_id: Optional[str] = None, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
        """List events from Circle.

        Args:
            space_id: Optional space ID to filter events
            page: Page number (default 1)
            per_page: Results per page (default 100)

        Returns:
            Response dict with records and pagination info
        """
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if space_id:
            params["space_id"] = space_id
        return self.http.request("GET", self.endpoints["list_events"], params=params)

    def get_all_events(self, space_id: Optional[str] = None, per_page: int = 100) -> List[Dict]:
        """Fetch all events by paginating through results.

        Args:
            space_id: Optional space ID to filter events
            per_page: Results per page (default 100)

        Returns:
            List of all event dicts
        """
        all_events = []
        page = 1
        while True:
            data = self.list_events(space_id=space_id, page=page, per_page=per_page)
            records = data.get("records") or data.get("events") or data.get("data") or []
            all_events.extend(records)
            if not data.get("has_next_page", False):
                break
            page += 1
        return all_events

    def create_event(self, event_data: Dict[str, Any], space_id: str) -> Dict:
        """Create an event in Circle.

        Args:
            event_data: Event data dict
            space_id: Space ID where event should be created

        Returns:
            Created event dict
        """
        body = {**event_data, "space_id": space_id}
        return self.http.request("POST", self.endpoints["create_event"], json_body=body)

    def update_event(self, event_id: str, event_data: Dict[str, Any]) -> Dict:
        """Update an event in Circle.

        Args:
            event_id: Circle event ID
            event_data: Event data dict to update

        Returns:
            Updated event dict
        """
        path = self.endpoints["update_event"].replace("{id}", str(event_id))
        return self.http.request("PUT", path, json_body=event_data)

    def delete_event(self, event_id: str, space_id: str) -> Dict:
        """Delete an event from Circle.

        Args:
            event_id: Circle event ID
            space_id: Space ID containing the event

        Returns:
            Response dict
        """
        path = self.endpoints["delete_event"].replace("{id}", str(event_id))
        params = {"space_id": space_id}
        return self.http.request("DELETE", path, params=params)

    def get_event_by_slug(self, slug: str, space_id: Optional[str] = None) -> Optional[Dict]:
        """Find an event by its slug.

        Args:
            slug: Event slug to search for
            space_id: Optional space ID to narrow search

        Returns:
            Event dict if found, None otherwise
        """
        events = self.get_all_events(space_id=space_id)
        for event in events:
            if event.get("slug") == slug:
                return event
        return None

    def get_current_user_id(self) -> int:
        """Get the user ID associated with the current API token.

        Fetches the first admin/member from the community and caches the ID.
        This is typically the account that owns the API token.

        Returns:
            User ID as integer

        Raises:
            ValueError: If no users found or ID cannot be determined
        """
        # Return cached value if available
        if self._cached_user_id is not None:
            return self._cached_user_id

        logger.info("Fetching user ID for current API token...")

        try:
            # Fetch community members (token owner should be first or in first page)
            members = self.list_members(page=1, per_page=10)

            if not members:
                raise ValueError("No community members found - cannot determine user ID")

            # Use the first member (typically the admin/token owner)
            first_member = members[0]
            user_id = first_member.get("id")

            if not user_id:
                raise ValueError("Member record missing 'id' field")

            self._cached_user_id = int(user_id)
            logger.info("Resolved user ID: %d (email: %s)", self._cached_user_id, first_member.get("email"))

            return self._cached_user_id

        except Exception as e:
            logger.error("Failed to get current user ID: %s", e)
            raise ValueError(f"Cannot determine user ID from API token: {e}") from e
