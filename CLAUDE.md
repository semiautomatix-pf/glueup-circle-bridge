# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GlueUp Circle Bridge is a Python service that synchronizes members from Glue Up (Association Management System) to Circle communities. It maps Glue Up membership plans to Circle spaces and manages member access accordingly.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m src.web.server

# Docker build and run
docker build -t glueup-circle-bridge:latest .
docker run -p 8080:8080 --env-file .env -v $(pwd)/src/config:/app/src/config:ro glueup-circle-bridge:latest
```

## API Endpoints

- `GET /health` - Health check
- `POST /sync/members` - Trigger sync (body: `{"dry_run": true/false}`)
- `POST /webhooks/glueup` - Webhook receiver

## Architecture

```
src/
├── clients/           # API clients
│   ├── http.py       # Generic HTTP client with tenacity retry logic
│   ├── glueup.py     # Glue Up API v2 client
│   └── circle.py     # Circle Admin API v2 client
├── config/
│   ├── config.py     # BridgeConfig dataclass, loads from env + YAML
│   ├── endpoints.yaml    # API endpoint paths
│   └── mapping.yaml      # Plan-to-space mappings
├── core/
│   ├── sync.py       # Main sync algorithm (decide_spaces, derive_status)
│   └── state.py      # JSON cache at .cache/known_members.json
└── web/
    └── server.py     # Flask app, initializes clients on startup
```

## Key Concepts

**Sync Flow**: Fetch Glue Up users → get memberships per user → determine primary membership → map plan slug to Circle spaces → compute diff (add/remove spaces) → apply changes or invite new members

**State Cache**: `state.py` maintains `email_to_member_id` and `member_spaces` mappings to minimize API calls and track current state

**Configuration**: Environment variables (`.env`) for credentials, YAML files for endpoint paths and plan-to-space mappings

## Configuration Files

- `.env` - API credentials (GLUEUP_BASE_URL, GLUEUP_AUTH_*, CIRCLE_BASE_URL, CIRCLE_API_TOKEN)
- `src/config/endpoints.yaml` - API endpoint paths for both services
- `src/config/mapping.yaml` - `plans_to_spaces` mapping and `default_spaces` list

## Known Issues

From IMPLEMENTATION_GUIDE.md:

1. **Glue Up Auth**: Current implementation uses single header; should support TWO headers (`a` and `token`)
2. **Circle Endpoints**: Some endpoint paths may not match Admin API V2 spec - verify against `docs/circle-admin-swagger.yaml`

## Notes

- No test suite exists
- `dry_run=true` is the safe default for sync operations
- HTTP client uses tenacity with 5 retries and exponential backoff (1-20s)
- API docs available in `docs/` directory (Glue Up .apib, Circle swagger files)
