import json, os
from typing import Dict, List, Optional

class StateCache:
    """
    A tiny JSON-file cache for member lookups and current space assignments.
    In production you might replace this with a database.
    """
    def __init__(self, path: str = ".cache/known_members.json"):
        self.path = path
        self._data = {"email_to_member_id": {}, "member_spaces": {}}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    self._data = json.load(f)
            except Exception:
                pass

    def lookup_member_id(self, email: str) -> Optional[str]:
        return self._data["email_to_member_id"].get(email)

    def set_member_id(self, email: str, member_id: str) -> None:
        self._data["email_to_member_id"][email] = member_id

    def member_spaces(self, member_id: str) -> List[str]:
        return self._data["member_spaces"].get(member_id, [])

    def set_member_spaces(self, member_id: str, spaces: List[str]) -> None:
        self._data["member_spaces"][member_id] = spaces

    def save(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2, sort_keys=True)
