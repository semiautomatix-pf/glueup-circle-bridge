# GlueUp Circle Bridge - UI Quick Start

## Super Quick Setup (1 minute)

```bash
# 1. Install everything
./scripts/setup-ui.sh

# 2. Start both backend and UI
./scripts/start.sh
```

Browser opens automatically to http://localhost:8501

## Manual Setup (If scripts don't work)

### One-time Setup
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-ui.txt
```

### Every Time You Use It

**Option A: Single command (Mac/Linux)**
```bash
python -m src.web.server & streamlit run streamlit_app.py
```

**Option B: Two terminals (Recommended)**

Terminal 1:
```bash
python -m src.web.server
```

Terminal 2:
```bash
streamlit run streamlit_app.py
```

## Using the UI

### 1. First Time Setup (⚙️ Setup Tab)

**GlueUp Credentials:**
- Base URL: `https://api.glueup.com`
- Email: Your GlueUp email
- Password: Your GlueUp password
- Public Key: Your API public key
- Private Key: Your API private key
- Organization ID: Your org ID

**Circle Credentials:**
- Base URL: `https://app.circle.so/api/v1`
- API Token: Your Circle admin token

**Plan Mapping:**
```yaml
plans_to_spaces:
  premium-member: [12345, 67890]
  basic-member: [12345]
default_spaces: []
```

**Save Configuration** → Restart backend (Terminal 1)

### 2. Dashboard (📊)
- Check backend health
- View configuration status

### 3. Sync (🔄)

**Member Sync:**
1. ✅ Enable "Dry run" checkbox
2. Click "▶️ Sync Members"
3. Review what would happen
4. ❌ Disable "Dry run"
5. Click "▶️ Sync Members" again

**Event Sync:**
1. ✅ Enable "Dry run" checkbox
2. Click "▶️ Sync Events"
3. Review what would happen
4. ❌ Disable "Dry run"
5. Click "▶️ Sync Events" again

## Common Issues

### "Backend not running"
**Fix:** Check Terminal 1 shows Flask running on port 8080

### Config changes not applying
**Fix:** After clicking "Save Configuration" in UI:
1. Go to Terminal 1
2. Press Ctrl+C to stop backend
3. Run `python -m src.web.server` again

### Port 8080 already in use
**Fix:**
```bash
# Find what's using it
lsof -i :8080

# Kill it
kill <PID>
```

### Streamlit won't start
**Fix:** Make sure you installed UI dependencies:
```bash
pip install -r requirements-ui.txt
```

## Stopping Everything

1. Close browser (optional)
2. Press Ctrl+C in both terminals

## Pro Tips

✅ **Always dry-run first** - See what will happen before making changes

🔄 **Restart backend after config changes** - Required for new settings to take effect

📊 **Check Dashboard regularly** - Monitor sync status and health

💾 **Backup before production sync** - Export your Circle data first time

## Getting Space IDs

Need to know your Circle space IDs for mapping?

```bash
curl http://localhost:8080/spaces | jq
```

Or check Circle admin panel → Spaces → Click a space → Look at URL for space ID

## What Each Sync Does

### Member Sync
- Fetches members from GlueUp
- Maps membership plans to Circle spaces
- Invites new members to Circle
- Adds/removes members from spaces
- Handles individual and corporate members

### Event Sync
- Fetches published events from GlueUp
- Creates new events in Circle
- Updates changed events
- Skips unchanged events

## File Locations

- **Config:** `.env` and `src/config/*.yaml`
- **Cache:** `.cache/known_members.json`
- **Logs:** Console output in Terminal 1

## Need More Help?

- Full documentation: [RUNNING.md](docs/RUNNING.md)
- Backend details: [README.md](README.md)
- Implementation guide: `docs/IMPLEMENTATION_GUIDE.md`
