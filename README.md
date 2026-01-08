# GlueUp ⇆ Circle Bridge

A lightweight service that keeps your Glue Up (AMS) members in sync with your Circle community.

**What it does (out-of-the-box):**
- Pulls members and membership status from Glue Up Open API v2 (Users & Memberships collections).
- Creates or invites matching members in Circle via the Admin API v2.
- Adds/removes members to/from Spaces based on your membership plan mapping.
- Optional: mirrors tags, and deactivates access when memberships lapse.
- Exposes a tiny HTTP server for health checks, manual sync, and (optionally) webhook ingestion.

> This repository ships with safe defaults and a config-driven approach because Glue Up tenants can differ and Circle endpoints evolve. You only need to paste the exact endpoint paths from your Glue Up and Circle docs into `src/config/endpoints.yaml` (examples included).

---

## Quick start

### 1) Prerequisites
- Python 3.10+
- A Glue Up account with Open API v2 access enabled.
- A Circle community API token (Admin API v2).

### 2) Grab API details
- **Glue Up**: obtain your API credentials (public key, private key, email, and password). Your account manager can enable API access if not already enabled. The bridge uses HMAC-SHA256 signature authentication with automatic session token management.
- **Circle**: in your community go to **Developers → Tokens** and create an Admin API token. Keep it secret.

### 3) Configure
Copy the env and YAML templates and fill them in:

```bash
cp .env.example .env
cp src/config/endpoints.example.yaml src/config/endpoints.yaml
cp src/config/mapping.example.yaml src/config/mapping.yaml
```

Then edit:
- `.env` — paste tokens/keys and base URLs.
- `src/config/endpoints.yaml` — confirm endpoint paths (you can copy/paste from the Circle Admin API and Glue Up Apiary docs).
- `src/config/mapping.yaml` — map Glue Up membership plans → Circle space IDs.

### 4) Install & run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src.web.server
```

By default the server listens on `http://0.0.0.0:8080` with these routes:
- `GET /health` – readiness probe
- `POST /sync/members` – on-demand member sync (`{"dry_run": true}` supported)
- `POST /webhooks/glueup` – optional webhook receiver (configure it in Glue Up if webhooks are available to you)

### 5) One-off manual sync

```bash
curl -X POST http://localhost:8080/sync/members -H "Content-Type: application/json" -d '{"dry_run": true}'
```

Flip `dry_run` to `false` when you’re happy with the proposed changes.

---

## Configuration

### `.env`

| Variable | Description |
|---|---|
| `GLUEUP_BASE_URL` | Glue Up API base URL including version, e.g. `https://api.glueup.com/v2` |
| `GLUEUP_PUBLIC_KEY` | Your Glue Up API public key |
| `GLUEUP_PRIVATE_KEY` | Your Glue Up API private key |
| `GLUEUP_EMAIL` | Your Glue Up account email |
| `GLUEUP_PASSPHRASE` | Your Glue Up account password (plaintext - the code will MD5 hash it) |
| `GLUEUP_ORGANIZATION_ID` | Your Glue Up organization ID (find in dashboard URL or API responses) |
| `CIRCLE_BASE_URL` | Circle Admin API base, defaults to `https://app.circle.so/api/admin/v2` |
| `CIRCLE_API_TOKEN` | Your Circle Admin API token |
| `SERVER_PORT` | Optional; default `8080` |

> **Note**: Glue Up authentication is handled automatically by the bridge. It generates HMAC-SHA256 signatures for each request and manages session tokens internally, refreshing them as needed.

### `src/config/endpoints.yaml`

You can overwrite any of these paths to match your tenant/version.

```yaml
glueup:
  # POST - Returns active membership members
  members_directory: "/membershipDirectory/members"
  # POST - Returns membership types
  membership_types: "/public/membership/publishedMembershipTypeList"
  # GET - Returns memberships for authenticated user
  memberships_list: "/membership/activeApplicationList"
  # POST - Returns events list
  events_list: "/event/list"

circle:
  list_members: "/community_members"
  invite_member: "/community_members"
  update_member: "/community_members/{member_id}"
  add_member_to_space: "/space_members"
  remove_member_from_space: "/space_members"
  list_spaces: "/spaces"
  list_space_members: "/space_members"
```

> Exact names can vary across API versions. Open the Circle Admin API page and copy the operation paths. Same for Glue Up via the Apiary doc. This app simply stitches whatever you put here.

### `src/config/mapping.yaml`

Minimal example mapping Glue Up plan *slugs* (or names) to Circle **space IDs**.

```yaml
plans_to_spaces:
  professional: ["12345"]
  student: ["67890", "11223"]

default_spaces: []    # spaces every member should join
tags:
  active: ["Active"]
  lapsed: ["Lapsed"]
```

---

## Deploy

### Production (gunicorn)

For production deployments, use gunicorn:

```bash
gunicorn -c gunicorn.conf.py src.web.server:application
```

### Docker

```bash
docker build -t glueup-circle-bridge:latest .
docker run -p 8080:8080 --env-file .env -v $(pwd)/src/config:/app/src/config:ro glueup-circle-bridge:latest
```

### Cron for periodic sync

Add a crontab entry (every 6 hours):

```
0 */6 * * * curl -s -X POST http://localhost:8080/sync/members -H 'Content-Type: application/json' -d '{"dry_run": false}' >/var/log/glueup-circle-sync.log 2>&1
```

---

## Safety & logging

- All write calls are gated behind `dry_run` until you flip the switch.
- Idempotency: we compute a member “desired state” and skip calls if the member already matches it.
- Rate-limits: the HTTP client retries with backoff on 429/5xx.
- Minimal local cache on disk (`.cache/known_members.json`) for email→ID lookups to speed up runs.

---

## What to customise next

- Extend `GlueUpClient` to pull the exact fields you want (custom fields, company name, expiry date).
- In `CircleClient`, wire up tags and groups if you use them heavily.
- Add webhook signature verification for incoming Glue Up webhook payloads.
- Mirror events from Glue Up into Circle (create/update/delete).

---

## Support

This project is intentionally small, config-driven, and auditable. If you need a hardened runtime (PostgreSQL, queuing, observability), this codebase is a clean starting point.
