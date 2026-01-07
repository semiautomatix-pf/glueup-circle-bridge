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
- **Glue Up**: confirm base URL and authentication method (API key header or Bearer token). Your account manager can enable API access if not already enabled.
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
| `GLUEUP_BASE_URL` | Glue Up API base URL, e.g. `https://api.glueup.com` or your tenant base |
| `GLUEUP_AUTH_HEADER` | Header name for auth, e.g. `Authorization` or `X-API-Key` |
| `GLUEUP_AUTH_VALUE` | Full value to send, e.g. `Bearer <token>` or the API key |
| `CIRCLE_BASE_URL` | Circle Admin API base, defaults to `https://app.circle.so/api/headless/admin/v1` |
| `CIRCLE_API_TOKEN` | Your Circle Admin API token |
| `SERVER_PORT` | Optional; default `8080` |

### `src/config/endpoints.yaml`

You can overwrite any of these paths to match your tenant/version.

```yaml
glueup:
  users_list: "/api/v2/users"
  memberships_list: "/api/v2/memberships"
  # optional if you want event mirroring later
  events_list: "/api/v2/events"

circle:
  # v2 Admin API typically mounted under /api/headless/admin/v1
  list_members: "/community_members"
  invite_member: "/community_members/invite"
  update_member: "/community_members/{member_id}"
  add_member_to_space: "/spaces/{space_id}/members"
  remove_member_from_space: "/spaces/{space_id}/members/{member_id}"
  list_spaces: "/spaces"
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
- Add HMAC verification for Glue Up webhooks (if Glue Up exposes it on your tenant).
- Mirror events from Glue Up into Circle (create/update/delete).

---

## Support

This project is intentionally small, config-driven, and auditable. If you need a hardened runtime (PostgreSQL, queuing, observability), this codebase is a clean starting point.
