import json
import os
import time
from typing import Dict, List, Optional

class StateCache:
    """
    A tiny JSON-file cache for member lookups, current space assignments, events, and webhook tracking.
    In production you might replace this with a database.
    """
    MAX_WEBHOOK_RECORDS = 1000  # Keep last 1000 webhook records

    def __init__(self, path: str = ".cache/known_members.json"):
        self.path = path
        self._data = {
            "email_to_member_id": {},
            "member_spaces": {},
            "events": {},  # glueup_id -> {circle_event_id, slug, last_sync, checksum}
            "webhook_events": {},  # webhook_id -> {processed_at, timestamp}
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    loaded = json.load(f)
                    # Merge loaded data with defaults (for backward compatibility)
                    self._data.update(loaded)
                    # Ensure all keys exist
                    if "events" not in self._data:
                        self._data["events"] = {}
                    if "webhook_events" not in self._data:
                        self._data["webhook_events"] = {}
            except Exception:
                pass

    # Member methods
    def lookup_member_id(self, email: str) -> Optional[str]:
        return self._data["email_to_member_id"].get(email)

    def set_member_id(self, email: str, member_id: str) -> None:
        self._data["email_to_member_id"][email] = member_id

    def member_spaces(self, member_id: str) -> List[str]:
        return self._data["member_spaces"].get(member_id, [])

    def set_member_spaces(self, member_id: str, spaces: List[str]) -> None:
        self._data["member_spaces"][member_id] = spaces

    # Event methods
    def get_event_mapping(self, glueup_event_id: str) -> Optional[Dict]:
        """Get Circle event mapping for a GlueUp event ID.

        Returns:
            Dict with circle_event_id, slug, last_sync, checksum or None
        """
        return self._data["events"].get(str(glueup_event_id))

    def set_event_mapping(
        self,
        glueup_id: str,
        circle_id: str,
        slug: str,
        timestamp: float,
        checksum: str,
    ) -> None:
        """Store event mapping between GlueUp and Circle.

        Args:
            glueup_id: GlueUp event ID
            circle_id: Circle event ID
            slug: Event slug in Circle
            timestamp: Unix timestamp of last sync
            checksum: MD5 checksum of event data
        """
        self._data["events"][str(glueup_id)] = {
            "circle_event_id": circle_id,
            "slug": slug,
            "last_sync": timestamp,
            "checksum": checksum,
        }

    def remove_event_mapping(self, glueup_event_id: str) -> None:
        """Remove event mapping."""
        self._data["events"].pop(str(glueup_event_id), None)

    def get_all_event_mappings(self) -> Dict[str, Dict]:
        """Get all event mappings.

        Returns:
            Dict mapping glueup_id to event mapping dict
        """
        return self._data["events"]

    # Webhook deduplication methods
    def has_processed_webhook(self, webhook_id: str) -> bool:
        """Check if a webhook has already been processed.

        Args:
            webhook_id: Unique webhook identifier

        Returns:
            True if webhook was already processed
        """
        return str(webhook_id) in self._data["webhook_events"]

    def mark_webhook_processed(self, webhook_id: str, timestamp: Optional[float] = None) -> None:
        """Mark a webhook as processed.

        Args:
            webhook_id: Unique webhook identifier
            timestamp: Optional webhook timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = time.time()

        self._data["webhook_events"][str(webhook_id)] = {
            "processed_at": time.time(),
            "timestamp": timestamp,
        }

        # Auto-cleanup: keep only last MAX_WEBHOOK_RECORDS
        if len(self._data["webhook_events"]) > self.MAX_WEBHOOK_RECORDS:
            # Sort by processed_at and keep newest
            sorted_webhooks = sorted(
                self._data["webhook_events"].items(),
                key=lambda x: x[1]["processed_at"],
                reverse=True,
            )
            self._data["webhook_events"] = dict(sorted_webhooks[:self.MAX_WEBHOOK_RECORDS])

    # Cache statistics
    def get_stats(self) -> Dict:
        """Get cache statistics.

        Returns:
            Dict with counts of members, events, webhooks
        """
        return {
            "members_count": len(self._data["email_to_member_id"]),
            "member_spaces_count": len(self._data["member_spaces"]),
            "events_count": len(self._data["events"]),
            "webhooks_count": len(self._data["webhook_events"]),
        }

    def save(self) -> None:
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2, sort_keys=True)
