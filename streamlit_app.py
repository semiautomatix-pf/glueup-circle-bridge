"""GlueUp Circle Bridge - Streamlit UI

Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import requests
import yaml
import os
from pathlib import Path

# Flask backend URL - use SERVER_PORT from .env or default to 8080
SERVER_PORT = os.getenv("SERVER_PORT", "8080")
BACKEND_URL = os.getenv("BACKEND_URL", f"http://localhost:{SERVER_PORT}")

# Config file paths
ENV_FILE = Path(".env")
MAPPING_FILE = Path("src/config/mapping.yaml")

st.set_page_config(
    page_title="GlueUp Circle Bridge",
    page_icon="🔄",
    layout="wide"
)

st.title("🔄 GlueUp Circle Bridge")

# Tabs for different sections
tab_setup, tab_dashboard, tab_sync = st.tabs([
    "⚙️ Setup",
    "📊 Dashboard",
    "🔄 Sync"
])

# ============================================================================
# TAB 1: SETUP
# ============================================================================
with tab_setup:
    st.header("Configuration")

    # Load existing .env values if they exist
    env_values = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_values[key] = value

    with st.expander("GlueUp Credentials", expanded=True):
        glueup_base_url = st.text_input(
            "Base URL",
            value=env_values.get("GLUEUP_BASE_URL", "https://api.glueup.com"),
            key="glueup_url"
        )
        glueup_email = st.text_input(
            "Email",
            value=env_values.get("GLUEUP_EMAIL", ""),
            key="glueup_email"
        )
        glueup_password = st.text_input(
            "Password",
            type="password",
            value=env_values.get("GLUEUP_PASSPHRASE", ""),
            key="glueup_password"
        )
        glueup_public_key = st.text_area(
            "Public Key",
            value=env_values.get("GLUEUP_PUBLIC_KEY", ""),
            height=100,
            key="glueup_public"
        )
        glueup_private_key = st.text_area(
            "Private Key",
            value=env_values.get("GLUEUP_PRIVATE_KEY", ""),
            height=100,
            key="glueup_private"
        )
        glueup_org_id = st.text_input(
            "Organization ID",
            value=env_values.get("GLUEUP_ORGANIZATION_ID", ""),
            key="glueup_org"
        )

        if st.button("Test GlueUp Connection"):
            with st.spinner("Testing connection..."):
                try:
                    # Check if values are filled
                    if all([glueup_email, glueup_password, glueup_public_key,
                           glueup_private_key, glueup_org_id]):
                        st.success("✅ Credentials entered (save and restart backend to test)")
                    else:
                        st.error("❌ Please fill in all fields")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    with st.expander("Circle Credentials", expanded=True):
        circle_base_url = st.text_input(
            "Base URL",
            value=env_values.get("CIRCLE_BASE_URL", "https://app.circle.so/api/v1"),
            key="circle_url"
        )
        circle_token = st.text_input(
            "API Token",
            type="password",
            value=env_values.get("CIRCLE_API_TOKEN", ""),
            key="circle_token"
        )

        if st.button("Test Circle Connection"):
            with st.spinner("Testing connection..."):
                try:
                    response = requests.get(
                        f"{BACKEND_URL}/health",
                        timeout=10
                    )
                    if response.status_code == 200:
                        st.success("✅ Backend is running (save config and restart to test Circle)")
                    else:
                        st.error(f"❌ Backend error: {response.text}")
                except Exception as e:
                    st.error(f"❌ Backend not running or error: {e}")

    st.divider()

    # Plan mapping section
    st.subheader("Plan-to-Space Mapping")

    # Load current mapping if exists
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE) as f:
            current_mapping = yaml.safe_load(f)
    else:
        current_mapping = {"plans_to_spaces": {}, "default_spaces": []}

    # Simple text-based mapping editor
    st.write("Edit your plan-to-space mappings below:")
    mapping_text = st.text_area(
        "Mappings (YAML format)",
        value=yaml.dump(current_mapping, default_flow_style=False),
        height=200
    )

    st.divider()

    # Save configuration
    if st.button("💾 Save Configuration", type="primary"):
        try:
            # Save .env file
            env_content = f"""GLUEUP_BASE_URL={glueup_base_url}
GLUEUP_EMAIL={glueup_email}
GLUEUP_PASSPHRASE={glueup_password}
GLUEUP_PUBLIC_KEY={glueup_public_key}
GLUEUP_PRIVATE_KEY={glueup_private_key}
GLUEUP_ORGANIZATION_ID={glueup_org_id}
CIRCLE_BASE_URL={circle_base_url}
CIRCLE_API_TOKEN={circle_token}
"""
            with open(ENV_FILE, 'w') as f:
                f.write(env_content)

            # Save mapping.yaml
            mapping_data = yaml.safe_load(mapping_text)
            with open(MAPPING_FILE, 'w') as f:
                yaml.dump(mapping_data, f)

            st.success("✅ Configuration saved! Restart Flask backend to apply changes.")
            st.info("Restart command: `python -m src.web.server`")
        except Exception as e:
            st.error(f"❌ Failed to save: {e}")

# ============================================================================
# TAB 2: DASHBOARD
# ============================================================================
with tab_dashboard:
    st.header("Sync Dashboard")

    # Fetch stats from backend
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Status", health.get("status", "unknown"))
            with col2:
                st.metric("Backend", "✅ Running")
            with col3:
                if "timestamp" in health:
                    st.metric("Last Check", health["timestamp"])

            st.success("✅ Backend is healthy and running")
        else:
            st.warning("⚠️ Backend returned error")
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend not running. Start with: `python -m src.web.server`")
    except Exception as e:
        st.error(f"❌ Error connecting to backend: {e}")

    st.divider()

    # Show configuration status
    st.subheader("Configuration Status")

    col_env, col_mapping = st.columns(2)

    with col_env:
        st.write("**Environment Variables:**")
        if ENV_FILE.exists():
            st.success("✅ .env file exists")
            with open(ENV_FILE) as f:
                lines = [line.split('=')[0] for line in f if '=' in line]
                st.text(f"Found {len(lines)} variables")
        else:
            st.warning("⚠️ .env file not found")

    with col_mapping:
        st.write("**Mapping Configuration:**")
        if MAPPING_FILE.exists():
            st.success("✅ mapping.yaml exists")
            with open(MAPPING_FILE) as f:
                mapping_data = yaml.safe_load(f)
                plans_count = len(mapping_data.get("plans_to_spaces", {}))
                st.text(f"Found {plans_count} plan mappings")
        else:
            st.warning("⚠️ mapping.yaml not found")

    st.divider()

    # Activity log placeholder
    st.subheader("Recent Activity")
    st.info("Logs will appear here after running syncs")

# ============================================================================
# TAB 3: MANUAL SYNC
# ============================================================================
with tab_sync:
    st.header("Manual Sync")

    col_members, col_events = st.columns(2)

    with col_members:
        st.subheader("Member Sync")
        dry_run_members = st.checkbox("Dry run (test only)", value=True, key="dry_members")

        st.info("ℹ️ Syncs members from GlueUp to Circle based on membership plans")

        if st.button("▶️ Sync Members", type="primary"):
            with st.spinner("Syncing members..."):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/sync/members",
                        json={"dry_run": dry_run_members},
                        timeout=300  # 5 minute timeout
                    )

                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ Member sync complete!")

                        # Show results
                        st.json(result)

                        # Summary
                        if "report" in result:
                            report = result["report"]
                            st.write("**Summary:**")
                            st.write(f"- Invited: {report.get('invited', 0)}")
                            st.write(f"- Updated: {report.get('updated', 0)}")
                            st.write(f"- Errors: {report.get('errors', 0)}")
                    else:
                        st.error(f"❌ Sync failed: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Backend not running. Start with: `python -m src.web.server`")
                except requests.exceptions.Timeout:
                    st.error("❌ Sync timed out. Check backend logs.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    with col_events:
        st.subheader("Event Sync")
        dry_run_events = st.checkbox("Dry run (test only)", value=True, key="dry_events")

        st.info("ℹ️ Syncs events from GlueUp to Circle")

        if st.button("▶️ Sync Events", type="primary"):
            with st.spinner("Syncing events..."):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/sync/events",
                        json={"dry_run": dry_run_events},
                        timeout=300
                    )

                    if response.status_code == 200:
                        result = response.json()
                        st.success("✅ Event sync complete!")

                        # Show results
                        st.json(result)

                        # Summary
                        if "report" in result:
                            report = result["report"]
                            st.write("**Summary:**")
                            st.write(f"- Created: {report.get('created', 0)}")
                            st.write(f"- Updated: {report.get('updated', 0)}")
                            st.write(f"- Skipped: {report.get('skipped', 0)}")
                    else:
                        st.error(f"❌ Sync failed: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("❌ Backend not running. Start with: `python -m src.web.server`")
                except requests.exceptions.Timeout:
                    st.error("❌ Sync timed out. Check backend logs.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    st.divider()

    # Status check
    st.subheader("Backend Status")
    if st.button("🔍 Check Backend Health"):
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=5)
            if response.status_code == 200:
                st.success("✅ Backend is running")
                st.json(response.json())
            else:
                st.error("❌ Backend returned error")
        except requests.exceptions.ConnectionError:
            st.error("❌ Backend not reachable at http://localhost:8080")
            st.info("Start backend with: `python -m src.web.server`")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# ============================================================================
# SIDEBAR: Instructions
# ============================================================================
with st.sidebar:
    st.header("🚀 Quick Start")

    st.markdown("""
    ### Running the Application

    **Quick start:**
    ```bash
    ./scripts/start.sh
    ```

    **Or manually:**
    ```bash
    # Terminal 1
    python -m src.web.server

    # Terminal 2
    streamlit run streamlit_app.py
    ```

    ---

    ### Setup Steps
    1. Go to **Setup** tab
    2. Enter GlueUp credentials
    3. Enter Circle API token
    4. Edit plan mappings
    5. Click **Save Configuration**
    6. Restart Flask backend

    ---

    ### Syncing
    1. Go to **Sync** tab
    2. Enable/disable dry run
    3. Click sync buttons
    4. Check results in output

    ---

    ### Tips
    - ✅ Always use **dry run** first
    - 🔄 Restart backend after config changes
    - 📊 Check Dashboard for status

    ---

    ### Documentation
    - [Quick Reference](docs/UI-QUICKSTART.md)
    - [Full Guide](docs/RUNNING.md)
    """)

    st.divider()

    st.info("💡 Tip: Use dry run mode to test before making real changes")

    st.divider()

    st.caption("GlueUp Circle Bridge v1.0")
