# Web UI Documentation

## Quick Links

### Getting Started
- **[UI Quick Start](UI-QUICKSTART.md)** - 1-page quick reference (START HERE!)
- **[Running Guide](RUNNING.md)** - Complete installation and usage guide
- **[UI User Guide](UI_GUIDE.md)** - Detailed walkthrough of all features

### Reference
- **[UI Architecture](UI_ARCHITECTURE.md)** - Technical architecture and design
- **[Implementation Summary](UI-IMPLEMENTATION-SUMMARY.md)** - What was built and why
- **[Testing Checklist](UI-TESTING-CHECKLIST.md)** - Comprehensive test cases

## Quick Start

```bash
# One-time setup
./scripts/setup-ui.sh

# Start application
./scripts/start.sh
```

Browser opens to http://localhost:8501

## File Organization

```
glueup-circle-bridge/
├── streamlit_app.py           # Main UI application
├── requirements-ui.txt        # UI dependencies
├── scripts/
│   ├── setup-ui.sh           # Setup automation
│   └── start.sh              # Start both services
└── docs/
    ├── UI_README.md          # This file
    ├── UI-QUICKSTART.md      # Quick reference
    ├── RUNNING.md            # Full user guide
    ├── UI_GUIDE.md           # Feature walkthrough
    ├── UI_ARCHITECTURE.md    # Technical details
    ├── UI-IMPLEMENTATION-SUMMARY.md
    └── UI-TESTING-CHECKLIST.md
```

## Documentation Hierarchy

1. **New users** → Start with [UI-QUICKSTART.md](UI-QUICKSTART.md)
2. **Need details** → Read [RUNNING.md](RUNNING.md)
3. **Using features** → Refer to [UI_GUIDE.md](UI_GUIDE.md)
4. **Technical info** → See [UI_ARCHITECTURE.md](UI_ARCHITECTURE.md)
5. **Testing** → Use [UI-TESTING-CHECKLIST.md](UI-TESTING-CHECKLIST.md)

## Common Tasks

### First Time Setup
See [UI-QUICKSTART.md § Super Quick Setup](UI-QUICKSTART.md#super-quick-setup-1-minute)

### Daily Usage
See [UI_GUIDE.md § Common Tasks](UI_GUIDE.md#common-tasks)

### Troubleshooting
See [RUNNING.md § Troubleshooting](RUNNING.md#troubleshooting)

### Architecture Questions
See [UI_ARCHITECTURE.md](UI_ARCHITECTURE.md)

## Support

- Check [UI-QUICKSTART.md](UI-QUICKSTART.md) for quick fixes
- Read [RUNNING.md](RUNNING.md) for complete guide
- Review [UI_GUIDE.md](UI_GUIDE.md) for feature help
- See main [README.md](../README.md) for backend details
