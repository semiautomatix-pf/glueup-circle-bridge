from typing import Any, Dict, List, Optional
from .http import HttpClient

class CircleClient:
    def __init__(self, base_url: str, api_token: str, endpoints: Dict[str, str]):
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        self.http = HttpClient(base_url, headers=headers)
        self.endpoints = endpoints

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
