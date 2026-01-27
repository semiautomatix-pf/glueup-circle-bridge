"""Event synchronization between GlueUp and Circle.

This module handles syncing events from GlueUp to Circle, including:
- Creating new events
- Updating changed events (via checksum comparison)
- Tracking event mappings in state cache
- Transforming GlueUp event structure to Circle format
"""

import hashlib
import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..clients.circle import CircleClient
from ..clients.glueup import GlueUpClient
from .state import StateCache

log = logging.getLogger("bridge")


def slugify(text: str) -> str:
    """Create URL-safe slug from text.

    Args:
        text: Text to slugify

    Returns:
        URL-safe slug
    """
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and special chars with hyphens
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    # Remove leading/trailing hyphens
    text = text.strip("-")
    # Limit length
    return text[:100]


def compute_event_checksum(event_data: Dict[str, Any]) -> str:
    """Compute MD5 checksum for event data to detect changes.

    Args:
        event_data: GlueUp event data dict

    Returns:
        MD5 hex digest
    """
    venue_info = event_data.get("venueInfo", {})

    # Use key fields that indicate the event has changed
    key_fields = {
        "title": event_data.get("title"),
        "subTitle": event_data.get("subTitle"),
        "about": event_data.get("about"),
        "summary": event_data.get("summary"),
        "startDateTime": event_data.get("startDateTime"),
        "endDateTime": event_data.get("endDateTime"),
        "venue_name": venue_info.get("name"),
        "venue_address": venue_info.get("address"),
        "venue_city": venue_info.get("city"),
        "venue_country": venue_info.get("country"),
        "venue_timezone": venue_info.get("timezone"),
        # Include template images in checksum
        "template_images": event_data.get("template", {}).get("images", {}),
    }
    canonical = json.dumps(key_fields, sort_keys=True, default=str)
    return hashlib.md5(canonical.encode()).hexdigest()


def format_datetime(timestamp_ms: Optional[int]) -> Optional[str]:
    """Convert GlueUp millisecond timestamp to ISO 8601 datetime string.

    Args:
        timestamp_ms: Timestamp in milliseconds since epoch

    Returns:
        ISO 8601 formatted datetime string or None
    """
    if not timestamp_ms:
        return None
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000.0)
        return dt.isoformat()
    except (ValueError, OSError):
        return None


def calculate_duration(start_ms: Optional[int], end_ms: Optional[int]) -> Optional[int]:
    """Calculate duration in seconds between start and end timestamps.

    Args:
        start_ms: Start timestamp in milliseconds
        end_ms: End timestamp in milliseconds

    Returns:
        Duration in seconds or None
    """
    if not start_ms or not end_ms:
        return None
    try:
        return max(0, (end_ms - start_ms) // 1000)
    except (TypeError, ValueError):
        return None


def build_location_string(venue_info: Optional[Dict]) -> str:
    """Format venue information as a location string.

    Args:
        venue_info: Venue dict with name, address, city, country

    Returns:
        Formatted location string
    """
    if not venue_info:
        return ""

    parts = []

    # Helper to safely extract string value
    def safe_str(value) -> Optional[str]:
        if not value:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            # Try common keys for nested objects
            return value.get("name") or value.get("value") or value.get("code")
        return str(value)

    # Add venue name
    name = safe_str(venue_info.get("name"))
    if name:
        parts.append(name)

    # Add address
    address = safe_str(venue_info.get("address"))
    if address:
        parts.append(address)

    # Add city
    city = safe_str(venue_info.get("city"))
    if city:
        parts.append(city)

    # Add country
    country = venue_info.get("country")
    if country:
        country_str = safe_str(country)
        if country_str:
            parts.append(country_str)

    return ", ".join(parts)


def detect_location_type(venue_info: Optional[Dict]) -> str:
    """Detect if event is in-person, virtual, or TBD based on venue info.

    Args:
        venue_info: Venue dict from GlueUp

    Returns:
        "in_person", "virtual", or "tbd"
    """
    if not venue_info:
        return "tbd"

    venue_name = (venue_info.get("name") or "").lower()

    # Check for virtual indicators
    virtual_keywords = ["online", "virtual", "webinar", "zoom", "teams", "meet"]
    if any(keyword in venue_name for keyword in virtual_keywords):
        return "virtual"

    # If has physical address components, likely in-person
    has_address = bool(venue_info.get("address") or venue_info.get("city"))
    if has_address:
        return "in_person"

    return "tbd"


def extract_cover_image_url(glueup_event: Dict[str, Any]) -> Optional[str]:
    """Extract cover image URL from GlueUp event template.

    Args:
        glueup_event: Event data from GlueUp API

    Returns:
        Image URL or None
    """
    template = glueup_event.get("template", {})
    images = template.get("images", {})

    # Try banner first, then header image
    banner = images.get("banner", {})
    if banner and banner.get("uri"):
        # GlueUp uses placeholder ::size:: in URIs - replace with actual size
        uri = banner["uri"].replace("::size::", "1200x630")
        # Make absolute URL if relative
        if uri.startswith("/"):
            # Note: Would need base URL - for now return None for relative paths
            return None
        return uri

    header = images.get("headerImage", {})
    if header and header.get("uri"):
        uri = header["uri"].replace("::size::", "1200x630")
        if uri.startswith("/"):
            return None
        return uri

    return None


def transform_glueup_event_to_circle(
    glueup_event: Dict[str, Any],
    space_id: str,
    user_id: int,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Transform GlueUp event structure to Circle API format.

    Args:
        glueup_event: Event data from GlueUp API
        space_id: Circle space ID for the event
        user_id: Circle user ID (event creator)
        config: Event configuration dict

    Returns:
        Event data formatted for Circle API
    """
    # Extract basic info
    title = glueup_event.get("title", "Untitled Event")
    subtitle = glueup_event.get("subTitle", "")

    # GlueUp uses 'about' for HTML description, 'summary' for shorter text
    description = (
        glueup_event.get("about") or
        glueup_event.get("summary") or
        glueup_event.get("description") or
        ""
    )

    # Add subtitle to description if present
    if subtitle:
        description = f"<p><strong>{subtitle}</strong></p>\n{description}"

    start_ms = glueup_event.get("startDateTime")
    end_ms = glueup_event.get("endDateTime")
    venue = glueup_event.get("venueInfo", {})

    # Format dates
    start_at = format_datetime(start_ms)
    end_at = format_datetime(end_ms)

    # Generate slug from title and GlueUp ID for uniqueness
    glueup_id = glueup_event.get("id", "")
    slug = slugify(f"{title}-{glueup_id}")

    # Build location string
    location = build_location_string(venue)

    # Detect location type (in_person, virtual, tbd)
    location_type = detect_location_type(venue)

    # Get timezone from venue
    timezone = venue.get("timezone") if venue else None

    # Get field overrides from config
    overrides = config.get("field_overrides", {})

    # Allow config to override location_type if explicitly set
    if overrides.get("location_type"):
        location_type = overrides["location_type"]

    host = overrides.get("host", "GlueUp Events")
    rsvp_disabled = overrides.get("rsvp_disabled", False)
    send_email_confirmation = overrides.get("send_email_confirmation", True)
    send_email_reminder = overrides.get("send_email_reminder", True)

    # Extract cover image
    cover_image_url = extract_cover_image_url(glueup_event)

    # Helper to safely extract string value from any field
    def safe_extract_str(value) -> Optional[str]:
        if not value:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return value.get("name") or value.get("value") or value.get("code")
        return str(value)

    # Build venue/location details
    venue_details = {}
    if venue:
        venue_name = safe_extract_str(venue.get("name"))
        if venue_name:
            venue_details["venue_name"] = venue_name

        venue_address = safe_extract_str(venue.get("address"))
        if venue_address:
            venue_details["venue_address"] = venue_address

        venue_city = safe_extract_str(venue.get("city"))
        if venue_city:
            venue_details["venue_city"] = venue_city

        # Get country name
        country = venue.get("country")
        if country:
            country_str = safe_extract_str(country)
            if country_str:
                venue_details["venue_country"] = country_str

        # Get map coordinates
        map_data = venue.get("map", {})
        if isinstance(map_data, dict):
            lat = map_data.get("latitude")
            lon = map_data.get("longitude")
            if lat is not None and lon is not None:
                try:
                    venue_details["venue_latitude"] = float(lat)
                    venue_details["venue_longitude"] = float(lon)
                except (ValueError, TypeError):
                    pass

    # Build Circle event payload
    event_data = {
        "name": title,
        "slug": slug,
        "body": description,
        "starts_at": start_at,
        "ends_at": end_at,
        "location": location,
        "location_type": location_type,
        "host": host,
        "rsvp_disabled": rsvp_disabled,
        "send_email_confirmation": send_email_confirmation,
        "send_email_reminder": send_email_reminder,
        "user_id": user_id,
        "space_id": space_id,
    }

    # Add optional fields if present
    if cover_image_url:
        event_data["cover_image_url"] = cover_image_url

    if timezone:
        event_data["timezone"] = timezone

    # Add venue details as metadata or custom fields
    # Note: Circle might not support all these fields directly
    # You may need to include them in the body/description instead
    if venue_details:
        # Some APIs support metadata - adjust based on Circle's actual API
        event_data.update(venue_details)

    return event_data


def sync_events(
    glue: GlueUpClient,
    circle: CircleClient,
    config: Dict[str, Any],
    state: StateCache,
    user_id: int,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Sync events from GlueUp to Circle.

    Args:
        glue: GlueUp API client
        circle: Circle API client
        config: Event configuration dict
        state: State cache for tracking mappings
        user_id: Circle user ID for event ownership
        dry_run: If True, only report what would be done

    Returns:
        Sync report dict with created, updated, deleted, skipped, errors counts
    """
    report = {
        "created": 0,
        "updated": 0,
        "deleted": 0,
        "skipped": 0,
        "errors": 0,
        "details": [],
    }

    # Get event config
    event_config = config.get("events", {})
    sync_settings = event_config.get("sync_settings", {})
    default_space_id = event_config.get("default_space_id")

    if not default_space_id:
        log.error("No default_space_id configured for events")
        return {"error": "No default_space_id configured", "details": []}

    create_new = sync_settings.get("create_new", True)
    update_existing = sync_settings.get("update_existing", True)
    delete_removed = sync_settings.get("delete_removed", False)
    published_only = sync_settings.get("published_only", True)
    future_only = sync_settings.get("future_only", True)

    # Fetch GlueUp events
    log.info(
        "Fetching events from GlueUp (published_only=%s, future_only=%s)...",
        published_only,
        future_only
    )
    try:
        glueup_events = glue.get_all_events(published_only=published_only, future_only=future_only)
        log.info("Fetched %d events from GlueUp", len(glueup_events))
    except Exception as e:
        log.exception("Failed to fetch GlueUp events: %s", e)
        return {"error": str(e), "details": []}

    # Track which GlueUp events we've seen
    seen_glueup_ids = set()

    # Process each GlueUp event
    for glueup_event in glueup_events:
        glueup_id = str(glueup_event.get("id", ""))
        if not glueup_id:
            log.warning("Event missing ID, skipping: %s", glueup_event.get("title"))
            report["skipped"] += 1
            continue

        seen_glueup_ids.add(glueup_id)

        # Check if event already exists in cache
        mapping = state.get_event_mapping(glueup_id)

        # Compute checksum for change detection
        checksum = compute_event_checksum(glueup_event)

        # Transform event data
        try:
            event_data = transform_glueup_event_to_circle(
                glueup_event, default_space_id, user_id, event_config
            )
        except Exception as e:
            log.exception("Failed to transform event %s: %s", glueup_id, e)
            report["errors"] += 1
            continue

        if not mapping:
            # New event - create if enabled
            if create_new:
                if dry_run:
                    report["created"] += 1
                    detail = {
                        "action": "create_event",
                        "glueup_id": glueup_id,
                        "title": event_data["name"],
                        "slug": event_data["slug"],
                        "starts_at": event_data.get("starts_at"),
                        "ends_at": event_data.get("ends_at"),
                        "location": event_data.get("location"),
                        "location_type": event_data.get("location_type"),
                        "timezone": event_data.get("timezone"),
                        "has_cover_image": bool(event_data.get("cover_image_url")),
                        "dry_run": True,
                    }
                    report["details"].append(detail)
                else:
                    try:
                        result = circle.create_event(event_data, default_space_id)
                        circle_event_id = result.get("id")
                        slug = result.get("slug", event_data["slug"])

                        # Store mapping
                        state.set_event_mapping(
                            glueup_id, circle_event_id, slug, time.time(), checksum
                        )
                        state.save()

                        report["created"] += 1
                        detail = {
                            "action": "create_event",
                            "glueup_id": glueup_id,
                            "circle_event_id": circle_event_id,
                            "title": event_data["name"],
                            "slug": slug,
                            "starts_at": event_data.get("starts_at"),
                            "location": event_data.get("location"),
                            "location_type": event_data.get("location_type"),
                            "result": "success",
                        }
                        report["details"].append(detail)
                        log.info(
                            "Created event: %s (ID: %s) at %s - %s",
                            event_data["name"],
                            circle_event_id,
                            event_data.get("location", "TBD"),
                            event_data.get("location_type", "tbd")
                        )
                    except Exception as e:
                        log.exception("Failed to create event %s: %s", glueup_id, e)
                        report["errors"] += 1
                        report["details"].append({
                            "action": "create_event",
                            "glueup_id": glueup_id,
                            "title": event_data["name"],
                            "error": str(e),
                        })
            else:
                report["skipped"] += 1
        else:
            # Existing event - check if changed
            if mapping["checksum"] == checksum:
                # Unchanged - skip
                report["skipped"] += 1
                log.debug("Event %s unchanged, skipping", glueup_id)
            else:
                # Changed - update if enabled
                if update_existing:
                    if dry_run:
                        report["updated"] += 1
                        report["details"].append({
                            "action": "update_event",
                            "glueup_id": glueup_id,
                            "circle_event_id": mapping["circle_event_id"],
                            "title": event_data["name"],
                            "dry_run": True,
                        })
                    else:
                        try:
                            circle.update_event(mapping["circle_event_id"], event_data)

                            # Update mapping with new checksum
                            state.set_event_mapping(
                                glueup_id,
                                mapping["circle_event_id"],
                                mapping["slug"],
                                time.time(),
                                checksum,
                            )
                            state.save()

                            report["updated"] += 1
                            report["details"].append({
                                "action": "update_event",
                                "glueup_id": glueup_id,
                                "circle_event_id": mapping["circle_event_id"],
                                "title": event_data["name"],
                                "result": "success",
                            })
                            log.info("Updated event: %s (Circle ID %s)", event_data["name"], mapping["circle_event_id"])
                        except Exception as e:
                            log.exception("Failed to update event %s: %s", glueup_id, e)
                            report["errors"] += 1
                            report["details"].append({
                                "action": "update_event",
                                "glueup_id": glueup_id,
                                "circle_event_id": mapping["circle_event_id"],
                                "title": event_data["name"],
                                "error": str(e),
                            })
                else:
                    report["skipped"] += 1

    # Handle deleted events (removed from GlueUp)
    if delete_removed:
        all_mappings = state.get_all_event_mappings()
        for glueup_id, mapping in all_mappings.items():
            if glueup_id not in seen_glueup_ids:
                # Event removed from GlueUp - delete from Circle
                if dry_run:
                    report["deleted"] += 1
                    report["details"].append({
                        "action": "delete_event",
                        "glueup_id": glueup_id,
                        "circle_event_id": mapping["circle_event_id"],
                        "dry_run": True,
                    })
                else:
                    try:
                        circle.delete_event(mapping["circle_event_id"], default_space_id)
                        state.remove_event_mapping(glueup_id)
                        state.save()

                        report["deleted"] += 1
                        report["details"].append({
                            "action": "delete_event",
                            "glueup_id": glueup_id,
                            "circle_event_id": mapping["circle_event_id"],
                            "result": "success",
                        })
                        log.info("Deleted event: GlueUp ID %s, Circle ID %s", glueup_id, mapping["circle_event_id"])
                    except Exception as e:
                        log.exception("Failed to delete event %s: %s", glueup_id, e)
                        report["errors"] += 1

    log.info(
        "Event sync complete: %d created, %d updated, %d deleted, %d skipped, %d errors",
        report["created"],
        report["updated"],
        report["deleted"],
        report["skipped"],
        report["errors"],
    )

    return report
