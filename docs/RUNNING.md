# Running GlueUp Circle Bridge

## Prerequisites

1. Python 3.9+ installed
2. Dependencies installed: `pip install -r requirements.txt`
3. Streamlit installed: `pip install streamlit`

## Starting the Application

### Option 1: Two Terminal Windows (Recommended)

**Terminal 1 - Backend:**
```bash
cd /path/to/glueup-circle-bridge
python -m src.web.server
```
Wait until you see: `Running on http://127.0.0.1:8080`

**Terminal 2 - Frontend:**
```bash
cd /path/to/glueup-circle-bridge
streamlit run streamlit_app.py
```

Browser will auto-open to: `http://localhost:8501`

### Option 2: Single Command (Background Backend)

**Mac/Linux:**
```bash
python -m src.web.server & streamlit run streamlit_app.py
```

**Windows:**
```powershell
Start-Process python -ArgumentList "-m", "src.web.server" -NoNewWindow
streamlit run streamlit_app.py
```

## First-Time Setup

1. Open the Streamlit UI (should auto-open in browser at http://localhost:8501)
2. Go to **⚙️ Setup** tab
3. Fill in credentials:
   - **GlueUp Section:**
     - Base URL (usually: `https://api.glueup.com`)
     - Email
     - Password (Passphrase)
     - Public Key
     - Private Key
     - Organization ID
   - **Circle Section:**
     - Base URL (usually: `https://app.circle.so/api/v1`)
     - API Token
4. Edit plan-to-space mappings in YAML editor:
   ```yaml
   plans_to_spaces:
     premium-member: [12345, 67890]  # Maps plan slug to space IDs
     basic-member: [12345]
   default_spaces: []
   ```
5. Click **💾 Save Configuration**
6. **Restart backend:**
   - Stop Terminal 1 (Ctrl+C)
   - Run `python -m src.web.server` again

## Using the Application

### Dashboard Tab (📊)
- View backend health status
- Check configuration files exist
- See system overview

### Setup Tab (⚙️)
- Edit credentials
- Modify plan-to-space mappings
- Save configuration changes
- Test connections

### Sync Tab (🔄)
- **Member Sync:** Sync members from GlueUp to Circle based on membership plans
- **Event Sync:** Sync events from GlueUp to Circle
- **Dry Run Mode:** Enable to test without making actual changes (recommended first time)

## Syncing Workflow

### First Sync (Testing)
1. Go to **🔄 Sync** tab
2. ✅ Enable **"Dry run (test only)"** checkbox
3. Click **▶️ Sync Members** or **▶️ Sync Events**
4. Review the output to see what would happen
5. Check for errors or unexpected changes

### Production Sync
1. Go to **🔄 Sync** tab
2. ❌ Disable **"Dry run (test only)"** checkbox
3. Click **▶️ Sync Members** or **▶️ Sync Events**
4. Monitor the results
5. Check Circle to verify changes

## Troubleshooting

### "Backend not running" error
**Solution:**
- Check Terminal 1 shows Flask running on port 8080
- Visit http://localhost:8080/health in browser to verify
- Look for error messages in Terminal 1

### Changes not applying
**Solution:**
- After saving config in Setup tab, you MUST restart Flask backend
- Stop Terminal 1 (Ctrl+C)
- Run `python -m src.web.server` again

### Port already in use
**Flask (port 8080):**
```bash
# Find what's using port 8080
lsof -i :8080  # Mac/Linux
netstat -ano | findstr :8080  # Windows

# Kill the process or change port
export FLASK_RUN_PORT=8081
python -m src.web.server
```

**Streamlit (port 8501):**
- Streamlit will automatically try 8502, 8503, etc.
- Or specify a port: `streamlit run streamlit_app.py --server.port 8502`

### Sync timeout
**Symptoms:** Sync runs for 5 minutes then times out

**Solutions:**
- Check backend logs (Terminal 1) for errors
- Verify GlueUp/Circle credentials are correct
- Test with smaller data set first
- Check network connectivity

### YAML syntax errors
**Symptoms:** "Failed to save" error when saving mapping

**Solution:**
- Check YAML syntax is correct (indentation matters!)
- Example correct format:
  ```yaml
  plans_to_spaces:
    plan-slug-one: [12345, 67890]
    plan-slug-two: [12345]
  default_spaces: []
  ```

## Stopping the Application

1. Close browser window (optional)
2. In Terminal 2 (Streamlit): Press **Ctrl+C**
3. In Terminal 1 (Flask): Press **Ctrl+C**

## Advanced: Running as a Service

For production use, consider running both services as systemd services (Linux) or Windows services.

### Example systemd service (Linux)

**Backend service:** `/etc/systemd/system/glueup-bridge-backend.service`
```ini
[Unit]
Description=GlueUp Circle Bridge Backend
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/glueup-circle-bridge
ExecStart=/usr/bin/python3 -m src.web.server
Restart=always

[Install]
WantedBy=multi-user.target
```

**Frontend service:** `/etc/systemd/system/glueup-bridge-frontend.service`
```ini
[Unit]
Description=GlueUp Circle Bridge Frontend
After=network.target glueup-bridge-backend.service

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/glueup-circle-bridge
ExecStart=/usr/bin/streamlit run streamlit_app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable glueup-bridge-backend glueup-bridge-frontend
sudo systemctl start glueup-bridge-backend glueup-bridge-frontend
```

## Getting Help

- Check backend logs in Terminal 1
- Verify configuration files in Setup tab
- Test backend health: http://localhost:8080/health
- Review error messages in Streamlit UI
- Check GitHub issues: https://github.com/anthropics/claude-code/issues

## Security Notes

- ⚠️ **Never commit `.env` file to git** - it contains sensitive credentials
- 🔒 Keep API tokens secure
- 🚫 Don't expose ports 8080/8501 to public internet without authentication
- ✅ Use environment variables or secure secret management for production
