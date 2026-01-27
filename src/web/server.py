import os, json, logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from ..config.config import load_config
from ..clients.glueup import GlueUpClient
from ..clients.glueup_auth import GlueUpAuth
from ..clients.circle import CircleClient
from ..core.state import StateCache
from ..core.sync import sync_members
from ..core.event_sync import sync_events

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("bridge")

cfg = load_config()

app = Flask(__name__)

glueup_auth = GlueUpAuth(
    base_url=cfg.glueup_base_url,
    public_key=cfg.glueup_public_key,
    private_key=cfg.glueup_private_key,
    email=cfg.glueup_email,
    passphrase=cfg.glueup_passphrase,
)

glue = GlueUpClient(
    base_url=cfg.glueup_base_url,
    auth=glueup_auth,
    endpoints=cfg.endpoints["glueup"],
)

circle = CircleClient(
    base_url=cfg.circle_base_url,
    api_token=cfg.circle_api_token,
    endpoints=cfg.endpoints["circle"],
)

state = StateCache()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/spaces")
def list_spaces():
    """List all Circle spaces with their IDs for mapping configuration."""
    spaces = circle.get_all_spaces()
    return jsonify([{"id": s.get("id"), "name": s.get("name")} for s in spaces])

@app.post("/sync/members")
def sync_members_route():
    body = request.get_json(silent=True) or {}
    dry_run = bool(body.get("dry_run", True))
    report = sync_members(glue, circle, cfg.mapping, state, cfg.glueup_organization_id, dry_run=dry_run)
    return jsonify(report)

@app.post("/webhooks/glueup")
def glueup_webhook():
    # Accept a user/membership payload and trigger a targeted sync with deduplication
    payload = request.get_json(silent=True) or {}
    log.info("Webhook payload received: %s", json.dumps(payload)[:500])

    # Generate webhook ID for deduplication
    webhook_id = payload.get("id") or payload.get("event_id") or hash(json.dumps(payload, sort_keys=True))

    # Check if already processed
    if state.has_processed_webhook(webhook_id):
        log.info("Webhook %s already processed, skipping", webhook_id)
        return jsonify({"received": True, "skipped": "duplicate", "webhook_id": str(webhook_id)})

    # Mark as processed
    webhook_timestamp = payload.get("timestamp") or payload.get("created_at")
    state.mark_webhook_processed(webhook_id, timestamp=webhook_timestamp)
    state.save()

    # Trigger sync
    report = sync_members(glue, circle, cfg.mapping, state, cfg.glueup_organization_id, dry_run=False)
    return jsonify({"received": True, "processed": True, "webhook_id": str(webhook_id), "sync_report": report})


@app.get("/admin/cache/stats")
def cache_stats():
    """Get cache statistics."""
    return jsonify(state.get_stats())


@app.post("/admin/cache/validate")
def validate_cache():
    """Validate cache against Circle API and optionally repair discrepancies."""
    from ..core.sync import validate_cache_against_circle

    body = request.get_json(silent=True) or {}
    repair = bool(body.get("repair", False))

    validation_report = validate_cache_against_circle(circle, state, repair=repair)
    return jsonify(validation_report)


@app.post("/sync/events")
def sync_events_route():
    """Trigger event sync from GlueUp to Circle.

    Body parameters:
        dry_run (bool): If true, only report what would be done (default: true)
        user_id (int, optional): Circle user ID for event ownership.
                                 If not provided, automatically derived from API token.
    """
    body = request.get_json(silent=True) or {}
    dry_run = bool(body.get("dry_run", True))
    user_id = body.get("user_id")

    # If user_id not provided, derive it from the Circle API token
    if not user_id:
        try:
            user_id = circle.get_current_user_id()
            log.info("Using auto-derived user ID: %d", user_id)
        except Exception as e:
            log.error("Failed to derive user ID: %s", e)
            return jsonify({
                "error": "user_id not provided and could not be derived from API token",
                "details": str(e),
                "hint": "Either provide user_id in request body or ensure Circle API token has access to community members"
            }), 400
    else:
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return jsonify({"error": "user_id must be an integer"}), 400

    report = sync_events(glue, circle, cfg.mapping, state, user_id, dry_run=dry_run)
    return jsonify(report)


@app.get("/events/status")
def events_status():
    """Get event sync statistics from cache."""
    stats = state.get_stats()
    all_events = state.get_all_event_mappings()

    # Calculate last sync time
    last_sync = None
    if all_events:
        last_sync = max(m.get("last_sync", 0) for m in all_events.values())

    return jsonify({
        "total_events_synced": stats["events_count"],
        "last_sync_timestamp": last_sync,
        "event_mappings": all_events,
    })


# WSGI application entry point for production servers (e.g., gunicorn)
application = app

if __name__ == "__main__":
    port = int(os.getenv("SERVER_PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
