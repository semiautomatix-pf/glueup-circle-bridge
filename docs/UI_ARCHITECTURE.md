# UI Architecture

## Overview

The GlueUp Circle Bridge now includes a Streamlit-based web UI that provides a user-friendly interface for configuration and sync operations.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Browser                              │
│                  http://localhost:8501                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ HTTP
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   Streamlit Frontend                         │
│                   (streamlit_app.py)                         │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Setup Tab    │  │ Dashboard    │  │  Sync Tab    │     │
│  │ - Credentials│  │ - Health     │  │ - Members    │     │
│  │ - Mappings   │  │ - Stats      │  │ - Events     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  Reads/Writes:                                              │
│  - .env file                                                │
│  - src/config/mapping.yaml                                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ HTTP REST API
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   Flask Backend                              │
│                (src/web/server.py)                           │
│                http://localhost:8080                         │
│                                                              │
│  API Endpoints:                                             │
│  - GET  /health                                             │
│  - GET  /spaces                                             │
│  - POST /sync/members                                       │
│  - POST /sync/events                                        │
│  - GET  /events/status                                      │
│  - GET  /admin/cache/stats                                  │
│  - POST /admin/cache/validate                               │
│  - POST /webhooks/glueup                                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ HTTP APIs
                        ▼
        ┌───────────────────────────────┐
        │                               │
        ▼                               ▼
┌───────────────┐              ┌────────────────┐
│  GlueUp API   │              │   Circle API   │
│  (v2)         │              │   (Admin v2)   │
└───────────────┘              └────────────────┘
```

## Component Responsibilities

### Streamlit Frontend (`streamlit_app.py`)

**Purpose:** User interface for configuration and operations

**Features:**
- Visual configuration editor
- Real-time health monitoring
- Sync trigger buttons with dry-run support
- Result visualization

**Technologies:**
- Streamlit (Python UI framework)
- PyYAML (config file handling)
- Requests (HTTP client for backend)

**No writes to:**
- Database
- Cache files
- Log files

**Reads/writes:**
- `.env` (credentials)
- `src/config/mapping.yaml` (plan mappings)

### Flask Backend (`src/web/server.py`)

**Purpose:** Business logic and API orchestration

**Features:**
- Member sync engine
- Event sync engine
- Cache management
- Webhook handling

**Technologies:**
- Flask (Python web framework)
- Custom API clients (GlueUp, Circle)
- JSON file-based state cache

**Reads/writes:**
- `.cache/known_members.json` (state cache)
- Log files

## Data Flow

### Configuration Flow

```
User fills Setup form
        ↓
Streamlit writes to .env + mapping.yaml
        ↓
User restarts Flask backend
        ↓
Flask loads new config on startup
        ↓
Config available for sync operations
```

### Member Sync Flow

```
User clicks "Sync Members"
        ↓
Streamlit POSTs to /sync/members
        ↓
Flask fetches from GlueUp API
        ↓
Flask computes desired state
        ↓
Flask updates Circle API
        ↓
Flask updates cache
        ↓
Flask returns report
        ↓
Streamlit displays results
```

### Event Sync Flow

```
User clicks "Sync Events"
        ↓
Streamlit POSTs to /sync/events
        ↓
Flask fetches events from GlueUp
        ↓
Flask compares with Circle (checksums)
        ↓
Flask creates/updates events in Circle
        ↓
Flask updates event cache
        ↓
Flask returns report
        ↓
Streamlit displays results
```

## Port Allocation

| Service | Port | Protocol | Access |
|---------|------|----------|--------|
| Streamlit UI | 8501 | HTTP | Browser |
| Flask Backend | 8080 | HTTP | Internal |
| GlueUp API | 443 | HTTPS | External |
| Circle API | 443 | HTTPS | External |

## File Structure

```
glueup-circle-bridge/
├── streamlit_app.py          # Streamlit UI (NEW)
├── start.sh                  # Convenience startup script (NEW)
├── setup-ui.sh               # One-time setup script (NEW)
├── requirements-ui.txt       # UI dependencies (NEW)
├── RUNNING.md                # User guide (NEW)
├── UI-QUICKSTART.md          # Quick reference (NEW)
├── .env                      # Credentials (read/write by UI)
├── src/
│   ├── web/
│   │   └── server.py         # Flask backend (MODIFIED)
│   ├── config/
│   │   ├── mapping.yaml      # Plan mappings (read/write by UI)
│   │   ├── endpoints.yaml    # API endpoints
│   │   └── config.py         # Config loader
│   ├── clients/              # API clients
│   └── core/                 # Sync logic
└── .cache/
    └── known_members.json    # State cache
```

## Security Considerations

### Credentials Storage
- Stored in `.env` file (plaintext)
- Not committed to git (in `.gitignore`)
- Only accessible on local filesystem

### Network Security
- Frontend communicates with backend via localhost
- Backend communicates with APIs via HTTPS
- No external access to ports 8080/8501 by default

### Best Practices
1. Never commit `.env` to version control
2. Use environment-specific tokens (dev/prod)
3. Rotate API tokens regularly
4. Restrict filesystem permissions on `.env`
5. Use HTTPS proxy for production (nginx/caddy)

## Deployment Options

### Development (Local)

```bash
# Two terminals
Terminal 1: python -m src.web.server
Terminal 2: streamlit run streamlit_app.py
```

### Production Option 1: Systemd Services

See [RUNNING.md](../RUNNING.md) for systemd service examples.

### Production Option 2: Docker

```bash
# Backend container
docker run -d -p 8080:8080 --env-file .env backend:latest

# Frontend container
docker run -d -p 8501:8501 \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/src/config:/app/src/config \
  frontend:latest
```

### Production Option 3: Reverse Proxy

```nginx
# nginx config
server {
    listen 80;
    server_name bridge.example.com;

    location / {
        proxy_pass http://localhost:8501;  # Streamlit
    }

    location /api {
        proxy_pass http://localhost:8080;  # Flask
    }
}
```

## Monitoring

### Health Checks

**Backend:**
```bash
curl http://localhost:8080/health
```

**Frontend:**
```bash
curl http://localhost:8501/_stcore/health
```

### Metrics to Monitor

- Sync success/failure rate
- API response times
- Cache hit/miss ratio
- Duplicate detection rate
- Webhook processing rate

### Log Locations

- **Backend logs:** Console output (Terminal 1)
- **Frontend logs:** Console output (Terminal 2)
- **Cache file:** `.cache/known_members.json`

## Troubleshooting

### UI can't reach backend

**Symptom:** "Backend not running" error in UI

**Solutions:**
1. Check Flask is running: `curl http://localhost:8080/health`
2. Check port 8080 not in use: `lsof -i :8080`
3. Check firewall rules

### Config changes not applying

**Symptom:** Changes saved but sync still uses old config

**Solution:** Restart Flask backend (config loaded on startup)

### Port conflicts

**Symptom:** "Address already in use" error

**Solutions:**
```bash
# Find process using port
lsof -i :8080  # or :8501

# Kill process
kill -9 <PID>

# Or change port
export SERVER_PORT=8081
streamlit run streamlit_app.py --server.port 8502
```

## Future Enhancements

Potential UI improvements:

1. **Authentication:** Add basic auth for UI access
2. **Scheduling:** Built-in cron-like scheduler for automatic syncs
3. **Log viewer:** Real-time log streaming in UI
4. **Metrics dashboard:** Charts for sync history and trends
5. **Member browser:** View/search synced members
6. **Event calendar:** Visual event sync status
7. **Diff viewer:** Show before/after state for syncs
8. **Rollback:** Undo last sync operation
9. **Bulk operations:** Multi-member/event operations
10. **API key management:** Generate/revoke webhook keys

## Performance Considerations

### Streamlit

- Runs in single-threaded mode
- Suitable for single user
- For multi-user, consider:
  - Streamlit Cloud (hosted)
  - Custom authentication
  - Gunicorn worker pool

### Flask Backend

- Already production-ready with gunicorn
- Handles concurrent requests
- State cache is thread-safe (file locking)

### Scaling

Current implementation handles:
- 1,000s of members
- 100s of events
- 10s of syncs per day

For larger scale:
- Migrate cache to PostgreSQL
- Add Redis for session state
- Use Celery for async tasks
- Add Prometheus metrics
