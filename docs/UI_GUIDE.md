# GlueUp Circle Bridge - UI User Guide

## Overview

The Streamlit web UI provides a visual interface for managing the GlueUp Circle Bridge without needing to use the command line or edit configuration files manually.

## Starting the Application

### Quick Start
```bash
./scripts/start.sh
```

Browser automatically opens to: http://localhost:8501

### Manual Start (Two Terminals)
```bash
# Terminal 1 - Backend
python -m src.web.server

# Terminal 2 - Frontend
streamlit run streamlit_app.py
```

## UI Layout

The interface has three main tabs:

```
┌─────────────────────────────────────────────────────┐
│  🔄 GlueUp Circle Bridge                            │
├─────────────────────────────────────────────────────┤
│  ⚙️ Setup  │  📊 Dashboard  │  🔄 Sync             │
└─────────────────────────────────────────────────────┘
```

Plus a **sidebar** with quick reference information.

---

## Tab 1: ⚙️ Setup

**Purpose:** Configure credentials and plan mappings

### GlueUp Credentials Section

**Fields:**
- **Base URL:** Usually `https://api.glueup.com`
- **Email:** Your GlueUp login email
- **Password:** Your GlueUp password (will be MD5 hashed by backend)
- **Public Key:** Your GlueUp API public key
- **Private Key:** Your GlueUp API private key
- **Organization ID:** Your GlueUp organization ID

**Test Connection Button:**
- Click to verify credentials are filled in
- Actual API test happens when backend restarts

**Where to find these values:**
1. GlueUp Dashboard → Settings → API Access
2. Contact your GlueUp account manager if API access not enabled
3. Organization ID is in your dashboard URL or API responses

### Circle Credentials Section

**Fields:**
- **Base URL:** Usually `https://app.circle.so/api/v1`
- **API Token:** Your Circle Admin API token

**Test Connection Button:**
- Click to verify backend is running
- Shows connection status to backend

**Where to find these values:**
1. Circle Dashboard → Developers → Tokens
2. Create a new Admin API token
3. Keep it secret and secure

### Plan-to-Space Mapping Section

**Purpose:** Maps GlueUp membership plans to Circle spaces

**Format (YAML):**
```yaml
plans_to_spaces:
  premium-member: [12345, 67890]  # Premium gets 2 spaces
  basic-member: [12345]            # Basic gets 1 space
  "corporate gold": [45678]        # Corporate plan

default_spaces: [2411092]          # All members get this space
```

**How to get space IDs:**

Option 1 - Via Backend API:
```bash
curl http://localhost:8080/spaces | jq
```

Option 2 - Via Circle Dashboard:
1. Go to Spaces
2. Click a space
3. Look at URL: `/spaces/12345` ← that's the ID

**How to get plan slugs:**
- GlueUp Dashboard → Membership → Plans
- Use exact plan name (case-sensitive!)
- If plan name has spaces, use quotes: `"premium member"`

### Save Configuration Button

**What it does:**
1. Writes credentials to `.env` file
2. Writes mappings to `src/config/mapping.yaml`
3. Shows success message

**Important:**
⚠️ After saving, you MUST restart the Flask backend for changes to take effect!

**How to restart backend:**
1. Go to Terminal 1 (where backend is running)
2. Press Ctrl+C to stop
3. Run `python -m src.web.server` again
4. Wait for "Running on http://127.0.0.1:8080"

---

## Tab 2: 📊 Dashboard

**Purpose:** Monitor system health and configuration status

### Health Status

**Shows:**
- Backend status (healthy/unhealthy)
- Last health check timestamp
- Connection status

**Green = Good:**
- ✅ Backend is healthy and running

**Red = Problem:**
- ❌ Backend not running
- ❌ Backend returned error

**Fix:** Check Terminal 1, restart backend if needed

### Configuration Status

**Two sections:**

1. **Environment Variables**
   - Shows if `.env` file exists
   - Shows count of variables
   - Green checkmark = configured

2. **Mapping Configuration**
   - Shows if `mapping.yaml` exists
   - Shows count of plan mappings
   - Green checkmark = configured

**If missing:**
- Go to Setup tab
- Fill in credentials/mappings
- Click Save Configuration

### Recent Activity

**Placeholder for future:**
- Will show sync history
- Will show recent operations
- Currently shows "Logs will appear here"

---

## Tab 3: 🔄 Sync

**Purpose:** Trigger member and event synchronization

### Two Columns

```
┌──────────────────────┬──────────────────────┐
│   Member Sync        │    Event Sync        │
└──────────────────────┴──────────────────────┘
```

### Member Sync (Left Column)

**What it does:**
- Fetches members from GlueUp
- Maps membership plans to Circle spaces
- Invites new members to Circle
- Adds/removes members from spaces

**Controls:**
- ☑️ **Dry run checkbox** (default: ON)
  - ON = Test mode, no changes made
  - OFF = Production mode, changes applied
- **▶️ Sync Members button**

**Workflow:**
1. ✅ Enable "Dry run" checkbox
2. Click "▶️ Sync Members"
3. Wait for spinner to finish
4. Review JSON output
5. Check summary statistics
6. If looks good: ❌ Disable "Dry run"
7. Click "▶️ Sync Members" again
8. Verify changes in Circle

**Output shows:**
```json
{
  "invited": 5,           // New members invited
  "updated": 12,          // Existing members updated
  "errors": 0,            // Errors encountered
  "member_types": {       // Breakdown by type
    "individual": 8,
    "corporate_admin": 4,
    "corporate_contact": 5
  },
  "duplicates_skipped": 2,  // Deduplication
  "cache_hits": 10,         // Cache performance
  "cache_misses": 7
}
```

**Tips:**
- Always dry-run first!
- Check for errors before production run
- Review duplicates_skipped to verify deduplication
- Monitor cache_hits for performance

### Event Sync (Right Column)

**What it does:**
- Fetches published events from GlueUp
- Creates new events in Circle
- Updates changed events
- Skips unchanged events

**Controls:**
- ☑️ **Dry run checkbox** (default: ON)
  - ON = Test mode, no changes made
  - OFF = Production mode, changes applied
- **▶️ Sync Events button**

**Workflow:**
1. ✅ Enable "Dry run" checkbox
2. Click "▶️ Sync Events"
3. Wait for spinner to finish
4. Review JSON output
5. Check summary statistics
6. If looks good: ❌ Disable "Dry run"
7. Click "▶️ Sync Events" again
8. Verify events in Circle

**Output shows:**
```json
{
  "created": 3,          // New events created
  "updated": 2,          // Events updated
  "deleted": 0,          // Events deleted
  "skipped": 15,         // Unchanged events
  "errors": 0,           // Errors encountered
  "details": [           // Per-event details
    {
      "title": "Annual Conference",
      "action": "created",
      "glueup_id": "abc123",
      "circle_id": 789
    }
  ]
}
```

**Tips:**
- Always dry-run first!
- Check for errors before production run
- Review skipped count (should be high on subsequent runs)
- Verify event details (title, date, location)

### Backend Status Section (Bottom)

**Purpose:** Quick health check

**Button:** 🔍 Check Backend Health

**Click to:**
- Verify backend is reachable
- See health check response
- Confirm API is working

**Response:**
```json
{
  "status": "healthy",
  "ok": true,
  "timestamp": "2024-01-27T14:30:00Z"
}
```

---

## Sidebar

**Contains:**
- Quick start instructions
- Running commands
- Setup steps
- Sync workflow
- Pro tips

**Always visible** on left side of screen for quick reference.

---

## Common Tasks

### First Time Setup

1. Start app: `./scripts/start.sh`
2. Go to **Setup** tab
3. Fill in GlueUp credentials
4. Fill in Circle token
5. Edit plan mappings
6. Click **Save Configuration**
7. Restart backend (Terminal 1: Ctrl+C, then restart)
8. Go to **Dashboard** tab
9. Verify green checkmarks

### Daily Sync Workflow

1. Go to **Sync** tab
2. ✅ Enable dry-run checkbox
3. Click **Sync Members** or **Sync Events**
4. Review results
5. If no errors: ❌ Disable dry-run
6. Click sync button again
7. Verify in Circle dashboard

### Checking Status

1. Go to **Dashboard** tab
2. Look for green checkmarks
3. Click **Check Backend Health** in Sync tab
4. Review recent activity (coming soon)

### Changing Configuration

1. Go to **Setup** tab
2. Update credentials or mappings
3. Click **Save Configuration**
4. **Important:** Restart backend!
5. Go to **Dashboard** to verify

### Troubleshooting Connection Issues

1. Go to **Dashboard** tab
2. If red ❌ appears:
   - Check Terminal 1 for errors
   - Verify backend is running on port 8080
   - Try: `curl http://localhost:8080/health`
3. If port conflict:
   - Find process: `lsof -i :8080`
   - Kill it: `kill <PID>`
   - Restart backend

---

## Error Messages

### "Backend not running"

**Cause:** Flask backend not reachable

**Fix:**
1. Check Terminal 1
2. If not running: `python -m src.web.server`
3. If running: check for errors in logs
4. Verify port 8080 not in use

### "Failed to save: ..."

**Cause:** Permission error or invalid YAML

**Fix:**
1. Check file permissions on `.env` and `mapping.yaml`
2. Verify YAML syntax (indentation matters!)
3. Check disk space

### "Sync failed: ..."

**Cause:** API error or configuration issue

**Fix:**
1. Check credentials are correct
2. Verify API tokens are not expired
3. Check plan mappings are correct
4. Review error details in JSON output
5. Check backend logs (Terminal 1)

### "Sync timed out"

**Cause:** Large dataset or slow API

**Fix:**
1. Check network connectivity
2. Verify APIs are responding
3. Try with smaller dataset
4. Check backend logs for details

---

## Keyboard Shortcuts

**Streamlit shortcuts:**
- `R` - Rerun app
- `C` - Clear cache
- `Ctrl+C` (in terminal) - Stop app

**Browser shortcuts:**
- `Ctrl+F` - Find in page
- `Ctrl+R` - Refresh page
- `F12` - Open developer tools

---

## Tips & Best Practices

### ✅ Do's

- **Always dry-run first** before production sync
- **Backup configuration** before making changes
- **Test connection** after updating credentials
- **Monitor Dashboard** for system health
- **Review output** before disabling dry-run
- **Restart backend** after config changes

### ❌ Don'ts

- **Don't skip dry-run** on first sync
- **Don't disable dry-run** without reviewing results
- **Don't forget to restart backend** after saving config
- **Don't commit .env** to version control
- **Don't run production sync** without testing first
- **Don't expose ports** to public internet without auth

### 🎯 Pro Tips

1. **Use dry-run liberally** - It's free and safe
2. **Check logs** in Terminal 1 for detailed info
3. **Bookmark this guide** for quick reference
4. **Export Circle data** before first production sync
5. **Monitor duplicates_skipped** to verify deduplication
6. **Watch cache_hits** for performance insights

---

## Getting Help

### If Something Goes Wrong

1. **Check this guide** first
2. **Review error message** in UI
3. **Check backend logs** (Terminal 1)
4. **Try dry-run** to diagnose
5. **Restart backend** if config changed
6. **Check file permissions** on config files

### Documentation Resources

- **Quick reference:** UI-QUICKSTART.md
- **Installation guide:** RUNNING.md
- **Technical details:** README.md
- **Architecture:** docs/UI_ARCHITECTURE.md
- **Implementation:** UI-IMPLEMENTATION-SUMMARY.md

### Support Channels

- Check GitHub issues
- Review backend logs
- Test with dry-run mode
- Verify configuration files

---

## Stopping the Application

1. Close browser tab (optional)
2. Press `Ctrl+C` in Terminal 2 (Streamlit)
3. Press `Ctrl+C` in Terminal 1 (Flask)

Or if using `start.sh`:
- Press `Ctrl+C` once
- Script will stop both services

---

## Advanced Features

### Command Line Access

Backend still supports direct API calls:

```bash
# List spaces
curl http://localhost:8080/spaces | jq

# Sync members
curl -X POST http://localhost:8080/sync/members \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# Get cache stats
curl http://localhost:8080/admin/cache/stats | jq
```

### Cache Management

```bash
# Get statistics
curl http://localhost:8080/admin/cache/stats | jq

# Validate cache
curl -X POST http://localhost:8080/admin/cache/validate \
  -H "Content-Type: application/json" \
  -d '{"repair": false}' | jq

# Repair cache
curl -X POST http://localhost:8080/admin/cache/validate \
  -H "Content-Type: application/json" \
  -d '{"repair": true}' | jq
```

### Event Status

```bash
curl http://localhost:8080/events/status | jq
```

---

## Conclusion

The Streamlit UI provides a simple, visual interface for managing the GlueUp Circle Bridge. Always use dry-run mode first, verify results, then run production syncs. Monitor the Dashboard for health status and check logs for detailed information.

For more help, see [RUNNING.md](../RUNNING.md) or [UI-QUICKSTART.md](../UI-QUICKSTART.md).
