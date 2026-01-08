import os, json, logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from ..config.config import load_config
from ..clients.glueup import GlueUpClient
from ..clients.glueup_auth import GlueUpAuth
from ..clients.circle import CircleClient
from ..core.state import StateCache
from ..core.sync import sync_members

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
    # Minimal placeholder: accept a user/membership payload and trigger a targeted sync later
    payload = request.get_json(silent=True) or {}
    log.info("Webhook payload received: %s", json.dumps(payload)[:500])
    # For simplicity we just run a quick sync. In production you'd parse the IDs and update just that member.
    report = sync_members(glue, circle, cfg.mapping, state, cfg.glueup_organization_id, dry_run=False)
    return jsonify({"received": True, "sync_report": report})

# WSGI application entry point for production servers (e.g., gunicorn)
application = app

if __name__ == "__main__":
    port = int(os.getenv("SERVER_PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
