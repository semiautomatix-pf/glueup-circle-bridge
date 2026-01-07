from typing import Dict, List, Optional
from .http import HttpClient
import os

class GlueUpClient:
    def __init__(self, base_url: str, header_a: str, token: str, endpoints: Dict[str, str]):
        # Glue Up API requires both 'a' and 'token' headers
        headers = {"a": header_a, "token": token, "Content-Type": "application/json"}
        self.http = HttpClient(base_url, headers=headers)
        self.endpoints = endpoints

    def list_users(self, updated_since: Optional[str] = None) -> List[Dict]:
        params = {}
        if updated_since:
            params["updated_since"] = updated_since
        data = self.http.request("GET", self.endpoints["users_list"], params=params)
        # normalise: expect data may be in {records:[...]} or {data:[...]}
        items = data.get("records") or data.get("data") or data.get("users") or []
        return items

    def list_memberships(self, user_id: Optional[str] = None) -> List[Dict]:
        params = {}
        if user_id:
            params["user_id"] = user_id
        data = self.http.request("GET", self.endpoints["memberships_list"], params=params)
        items = data.get("records") or data.get("data") or data.get("memberships") or []
        return items

    def list_events(self) -> List[Dict]:
        data = self.http.request("GET", self.endpoints.get("events_list", "/events"))
        return data.get("records") or data.get("data") or data.get("events") or []

    def get_all_users(self) -> List[Dict]:
        """Paginate through all users and return the complete list."""
        all_users = []
        page = 1

        while True:
            params = {"page": page, "per_page": 100}
            data = self.http.request("GET", self.endpoints["users_list"], params=params)
            users = data.get("records") or data.get("data") or data.get("users") or []
            all_users.extend(users)

            if len(users) < 100 or "next_page" not in data:
                break
            page += 1

        return all_users

    def get_all_memberships(self) -> List[Dict]:
        """Paginate through all memberships and return the complete list."""
        all_memberships = []
        page = 1

        while True:
            params = {"page": page, "per_page": 100}
            data = self.http.request("GET", self.endpoints["memberships_list"], params=params)
            memberships = data.get("records") or data.get("data") or data.get("memberships") or []
            all_memberships.extend(memberships)

            if len(memberships) < 100 or "next_page" not in data:
                break
            page += 1

        return all_memberships
