# UI Testing Checklist

## Pre-Testing Setup

- [ ] Python 3.9+ installed
- [ ] Virtual environment created (`.venv/`)
- [ ] Backend dependencies installed (`requirements.txt`)
- [ ] UI dependencies installed (`requirements-ui.txt`)
- [ ] Configuration files exist (`.env.example`, `mapping.example.yaml`)

## Installation Testing

### Setup Script
- [ ] `./scripts/setup-ui.sh` runs without errors
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Success message displayed

### Manual Installation
- [ ] `pip install -r requirements.txt` succeeds
- [ ] `pip install -r requirements-ui.txt` succeeds
- [ ] `streamlit --version` shows 1.28+

## Application Startup

### Backend
- [ ] `python -m src.web.server` starts
- [ ] Shows "Running on http://127.0.0.1:8080"
- [ ] No error messages in console
- [ ] `curl http://localhost:8080/health` returns JSON

### Frontend
- [ ] `streamlit run streamlit_app.py` starts
- [ ] Browser opens automatically
- [ ] Shows "GlueUp Circle Bridge" title
- [ ] Three tabs visible: Setup, Dashboard, Sync
- [ ] Sidebar shows instructions

### Start Script
- [ ] `./scripts/start.sh` starts both services
- [ ] Backend starts first
- [ ] Frontend starts after backend ready
- [ ] Browser opens automatically
- [ ] Both services running without errors

## UI Testing - Setup Tab

### GlueUp Credentials Section
- [ ] "GlueUp Credentials" expander visible
- [ ] Base URL field shows default value
- [ ] Email field is empty/populated
- [ ] Password field is type=password (hidden)
- [ ] Public Key textarea visible
- [ ] Private Key textarea visible
- [ ] Organization ID field visible
- [ ] "Test GlueUp Connection" button visible
- [ ] Button click shows response message

### Circle Credentials Section
- [ ] "Circle Credentials" expander visible
- [ ] Base URL field shows default value
- [ ] API Token field is type=password (hidden)
- [ ] "Test Circle Connection" button visible
- [ ] Button click checks backend health

### Plan Mapping Section
- [ ] "Plan-to-Space Mapping" header visible
- [ ] YAML editor textarea visible
- [ ] If mapping.yaml exists, loads content
- [ ] If not, shows default structure
- [ ] Can edit YAML in textarea

### Save Configuration
- [ ] "Save Configuration" button visible
- [ ] Button is styled as primary (blue)
- [ ] Clicking button shows processing
- [ ] Success message appears after save
- [ ] Shows restart instructions
- [ ] .env file created/updated
- [ ] mapping.yaml file created/updated

## UI Testing - Dashboard Tab

### Health Status
- [ ] "Sync Dashboard" header visible
- [ ] Backend health check runs automatically
- [ ] Shows status metric
- [ ] Shows "Backend" metric
- [ ] Shows "Last Check" if available
- [ ] Success message if backend healthy
- [ ] Error message if backend not running

### Configuration Status
- [ ] "Configuration Status" header visible
- [ ] Environment Variables section shows
- [ ] Shows checkmark if .env exists
- [ ] Shows variable count
- [ ] Mapping Configuration section shows
- [ ] Shows checkmark if mapping.yaml exists
- [ ] Shows plan count

### Recent Activity
- [ ] "Recent Activity" header visible
- [ ] Info message shows placeholder text

## UI Testing - Sync Tab

### Layout
- [ ] "Manual Sync" header visible
- [ ] Two columns: Member Sync, Event Sync
- [ ] Both columns have equal width
- [ ] Backend Status section at bottom

### Member Sync (Left Column)
- [ ] "Member Sync" subheader visible
- [ ] Dry run checkbox visible
- [ ] Checkbox is checked by default
- [ ] Info message explains what sync does
- [ ] "Sync Members" button visible
- [ ] Button is styled as primary (blue)
- [ ] Button has play icon (▶️)

### Event Sync (Right Column)
- [ ] "Event Sync" subheader visible
- [ ] Dry run checkbox visible
- [ ] Checkbox is checked by default
- [ ] Info message explains what sync does
- [ ] "Sync Events" button visible
- [ ] Button is styled as primary (blue)
- [ ] Button has play icon (▶️)

### Backend Status
- [ ] "Backend Status" subheader visible
- [ ] "Check Backend Health" button visible
- [ ] Button has magnifying glass icon (🔍)

## Functional Testing - Member Sync

### Dry Run Mode
- [ ] Enable dry run checkbox
- [ ] Click "Sync Members"
- [ ] Spinner appears during sync
- [ ] Success message on completion
- [ ] JSON output displayed
- [ ] Summary statistics shown (invited, updated, errors)
- [ ] dry_run=true in request

### Production Mode
- [ ] Disable dry run checkbox
- [ ] Click "Sync Members"
- [ ] Spinner appears during sync
- [ ] Success message on completion
- [ ] JSON output displayed
- [ ] Summary statistics shown
- [ ] dry_run=false in request

### Error Handling
- [ ] Stop backend, click sync
- [ ] Error message shows "Backend not running"
- [ ] Instructions to start backend shown

## Functional Testing - Event Sync

### Dry Run Mode
- [ ] Enable dry run checkbox
- [ ] Click "Sync Events"
- [ ] Spinner appears during sync
- [ ] Success message on completion
- [ ] JSON output displayed
- [ ] Summary statistics shown (created, updated, skipped)
- [ ] dry_run=true in request

### Production Mode
- [ ] Disable dry run checkbox
- [ ] Click "Sync Events"
- [ ] Spinner appears during sync
- [ ] Success message on completion
- [ ] JSON output displayed
- [ ] Summary statistics shown
- [ ] dry_run=false in request

### Error Handling
- [ ] Stop backend, click sync
- [ ] Error message shows "Backend not running"
- [ ] Instructions to start backend shown

## Functional Testing - Backend Health

### Health Check
- [ ] Click "Check Backend Health"
- [ ] Success message if backend running
- [ ] JSON output displayed
- [ ] Shows status, ok, timestamp
- [ ] Error message if backend not running
- [ ] Error message if backend unreachable

## Sidebar Testing

### Content
- [ ] "Quick Start" header visible
- [ ] "Running the Application" section shows
- [ ] Command examples displayed
- [ ] "Setup Steps" section shows
- [ ] "Syncing" section shows
- [ ] "Tips" section shows
- [ ] Pro tip at bottom

### Formatting
- [ ] Markdown renders correctly
- [ ] Code blocks formatted properly
- [ ] Lists display correctly
- [ ] Links work (if any)

## Configuration Persistence

### Save and Load
- [ ] Enter GlueUp credentials in Setup
- [ ] Enter Circle credentials in Setup
- [ ] Click "Save Configuration"
- [ ] Restart Streamlit (Ctrl+C, restart)
- [ ] Reload page
- [ ] Credentials still visible in fields
- [ ] Passwords remain hidden but are there

### File Creation
- [ ] After save, .env file exists
- [ ] .env contains correct keys
- [ ] .env has correct format (KEY=VALUE)
- [ ] mapping.yaml exists
- [ ] mapping.yaml has valid YAML syntax

## Error Handling

### Backend Not Running
- [ ] Stop Flask backend
- [ ] Dashboard shows error
- [ ] Sync buttons show error
- [ ] Error messages are clear
- [ ] Instructions provided

### Invalid Configuration
- [ ] Enter invalid YAML in mapping editor
- [ ] Click "Save Configuration"
- [ ] Error message appears
- [ ] Explains what went wrong

### Network Timeout
- [ ] Set very short timeout (if possible)
- [ ] Trigger sync
- [ ] Timeout message appears
- [ ] Suggests checking logs

## Integration Testing

### End-to-End Member Sync
- [ ] Start both services
- [ ] Configure credentials in Setup
- [ ] Save configuration
- [ ] Restart backend
- [ ] Go to Sync tab
- [ ] Enable dry run
- [ ] Click "Sync Members"
- [ ] Review output
- [ ] Disable dry run
- [ ] Click "Sync Members"
- [ ] Verify in Circle dashboard

### End-to-End Event Sync
- [ ] Start both services
- [ ] Configure credentials in Setup
- [ ] Save configuration
- [ ] Restart backend
- [ ] Go to Sync tab
- [ ] Enable dry run
- [ ] Click "Sync Events"
- [ ] Review output
- [ ] Disable dry run
- [ ] Click "Sync Events"
- [ ] Verify in Circle dashboard

## Performance Testing

### Responsiveness
- [ ] UI loads quickly (<2 seconds)
- [ ] Tab switching is instant
- [ ] Button clicks respond immediately
- [ ] Spinners show during operations
- [ ] Large JSON output doesn't freeze UI

### Memory Usage
- [ ] Check Python memory usage (backend)
- [ ] Check browser memory usage
- [ ] No memory leaks after multiple syncs
- [ ] Application runs stable over time

## Cross-Platform Testing

### Linux
- [ ] Setup script works
- [ ] Start script works
- [ ] Both services start
- [ ] UI accessible in browser

### macOS
- [ ] Setup script works
- [ ] Start script works
- [ ] Both services start
- [ ] UI accessible in browser

### Windows
- [ ] pip install works
- [ ] Backend starts with `python -m src.web.server`
- [ ] Frontend starts with `streamlit run streamlit_app.py`
- [ ] UI accessible in browser

## Browser Testing

### Chrome/Chromium
- [ ] UI renders correctly
- [ ] All features work
- [ ] No console errors

### Firefox
- [ ] UI renders correctly
- [ ] All features work
- [ ] No console errors

### Safari (macOS)
- [ ] UI renders correctly
- [ ] All features work
- [ ] No console errors

## Documentation Testing

### README.md
- [ ] Web UI section exists
- [ ] Link to RUNNING.md works
- [ ] Instructions are clear

### RUNNING.md
- [ ] Installation instructions work
- [ ] Startup instructions work
- [ ] Troubleshooting section helpful
- [ ] Examples are correct

### UI-QUICKSTART.md
- [ ] Commands work
- [ ] Quick reference is accurate
- [ ] Pro tips are useful

### docs/UI_GUIDE.md
- [ ] Complete walkthrough
- [ ] All sections covered
- [ ] Examples work

## Security Testing

### Credential Handling
- [ ] Passwords shown as *** in UI
- [ ] .env file not committed to git
- [ ] .env in .gitignore
- [ ] Tokens not logged in console

### Network Security
- [ ] Backend on localhost only
- [ ] Frontend on localhost only
- [ ] No external access by default

## Cleanup Testing

### Stopping Services
- [ ] Ctrl+C stops Streamlit cleanly
- [ ] Ctrl+C stops Flask cleanly
- [ ] start.sh cleanup works
- [ ] No zombie processes left

### File Cleanup
- [ ] Temporary files removed
- [ ] Cache files preserved
- [ ] Config files preserved

## Regression Testing

### Backend Compatibility
- [ ] /health endpoint works
- [ ] /spaces endpoint works
- [ ] /sync/members endpoint works
- [ ] /sync/events endpoint works
- [ ] /admin/cache/stats endpoint works

### No Breaking Changes
- [ ] Backend still works via curl
- [ ] Docker build still works
- [ ] Existing workflows unchanged

## Final Checks

### User Experience
- [ ] UI is intuitive
- [ ] Error messages are helpful
- [ ] Success messages are clear
- [ ] Loading states are visible
- [ ] Layout is clean and organized

### Documentation Quality
- [ ] All files created
- [ ] Documentation is complete
- [ ] Examples work
- [ ] Links are correct
- [ ] No typos in critical sections

### Production Readiness
- [ ] Dry run mode works
- [ ] Production mode works
- [ ] Error handling is robust
- [ ] Logging is adequate
- [ ] Configuration is flexible

## Test Results

**Date tested:** _________________

**Tested by:** _________________

**Python version:** _________________

**OS:** _________________

**Overall result:** ☐ PASS  ☐ FAIL

**Notes:**
_______________________________________________
_______________________________________________
_______________________________________________

## Issues Found

| # | Issue | Severity | Status | Notes |
|---|-------|----------|--------|-------|
| 1 |       |          |        |       |
| 2 |       |          |        |       |
| 3 |       |          |        |       |

## Recommendations

_______________________________________________
_______________________________________________
_______________________________________________
