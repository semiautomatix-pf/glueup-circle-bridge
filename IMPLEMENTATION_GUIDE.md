# Implementation Guide: Production-Ready GlueUp-Circle Bridge

This document outlines all changes required to make the GlueUp-Circle bridge production-viable and correct.

## Critical Issues (Must Fix)

### 1. Glue Up Authentication (CRITICAL)
**Issue**: Glue Up API requires TWO headers (`a` and `token`), but client only sends one.  
**Files**: `src/clients/glueup.py:6-8`, `src/config/config.py:18-19`  
**Fix**:

#### Update `src/config/config.py`:
```python
@dataclass
class BridgeConfig:
    glueup_base_url: str
    glueup_header_a: str      # NEW: First required header
    glueup_token: str         # NEW: Second required header
    circle_base_url: str
    circle_api_token: str
    endpoints: Dict[str, Dict[str, str]]
    mapping: Dict

def load_config() -> BridgeConfig:
    glueup_base_url = os.getenv("GLUEUP_BASE_URL", "").strip()
    glueup_header_a = os.getenv("GLUEUP_HEADER_A", "").strip()     # NEW
    glueup_token = os.getenv("GLUEUP_TOKEN", "").strip()           # NEW
    circle_base_url = os.getenv("CIRCLE_BASE_URL", "https://app.circle.so/api/admin/v2").strip()
    circle_api_token = os.getenv("CIRCLE_API_TOKEN", "").strip()
    
    # ... yaml loading ...
    
    return BridgeConfig(
        glueup_base_url=glueup_base_url,
        glueup_header_a=glueup_header_a,     # NEW
        glueup_token=glueup_token,           # NEW
        circle_base_url=circle_base_url,
        circle_api_token=circle_api_token,
        endpoints=endpoints,
        mapping=mapping,
    )
```

#### Update `src/clients/glueup.py`:
```python
class GlueUpClient:
    def __init__(self, base_url: str, header_a: str, token: str, endpoints: Dict[str, str]):
        # Both headers required per API docs
        headers = {
            "a": header_a,
            "token": token,
            "Content-Type": "application/json"
        }
        self.http = HttpClient(base_url, headers=headers)
        self.endpoints = endpoints
```

#### Update `src/main.py`:
```python
def main():
    cfg = load_config()
    glueup = GlueUpClient(
        cfg.glueup_base_url,
        cfg.glueup_header_a,    # NEW
        cfg.glueup_token,       # NEW
        cfg.endpoints["glueup"]
    )
```

#### Environment variables:
```bash
GLUEUP_HEADER_A=your_a_value
GLUEUP_TOKEN=your_token_value
# Remove: GLUEUP_AUTH_HEADER, GLUEUP_AUTH_VALUE
```

---

### 2. Circle API Endpoint Corrections (CRITICAL)
**Issue**: Endpoint paths in `endpoints.yaml` don't match Admin API V2.  
**Files**: `src/config/endpoints.yaml:6-11`, `src/clients/circle.py:27-33`

#### Update `src/config/endpoints.yaml`:
```yaml
circle:
  list_members: "/community_members"
  invite_member: "/community_members"           # Changed from /community_members/invite
  update_member: "/community_members/{member_id}"
  add_member_to_space: "/space_members"         # Changed from /spaces/{space_id}/members
  remove_member_from_space: "/space_members"    # Changed from /spaces/{space_id}/members/{member_id}
  list_spaces: "/spaces"
  list_space_members: "/space_members"          # NEW
```

#### Update `src/clients/circle.py`:
```python
from typing import Dict, List, Optional

class CircleClient:
    def __init__(self, base_url: str, api_token: str, endpoints: Dict[str, str]):
        headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
        self.http = HttpClient(base_url, headers=headers)
        self.endpoints = endpoints

    def list_members(self, page: int = 1, per_page: int = 100) -> List[Dict]:
        """List all community members with pagination."""
        params = {"page": page, "per_page": per_page}
        data = self.http.request("GET", self.endpoints["list_members"], params=params)
        return data.get("records", [])

    def invite_member(self, email: str, name: Optional[str] = None, space_ids: Optional[List[int]] = None) -> Dict:
        """Invite/create a new community member. Admin API uses POST /community_members."""
        body = {"email": email}
        if name:
            # Split name into first/last if provided
            parts = name.split(" ", 1)
            body["first_name"] = parts[0]
            if len(parts) > 1:
                body["last_name"] = parts[1]
        # Note: space_ids might need to be added separately via add_member_to_space
        # Check Admin API docs for whether space_ids is supported on member creation
        return self.http.request("POST", self.endpoints["invite_member"], json_body=body)

    def update_member(self, member_id: str, payload: Dict) -> Dict:
        """Update an existing member."""
        path = self.endpoints["update_member"].replace("{member_id}", str(member_id))
        return self.http.request("PUT", path, json_body=payload)

    def add_member_to_space(self, email: str, space_id: int) -> Dict:
        """Add member to space. Admin API V2 uses email + space_id in body."""
        body = {"email": email, "space_id": space_id}
        return self.http.request("POST", self.endpoints["add_member_to_space"], json_body=body)

    def remove_member_from_space(self, email: str, space_id: int) -> Dict:
        """Remove member from space. Admin API V2 uses email + space_id as query params."""
        params = {"email": email, "space_id": space_id}
        return self.http.request("DELETE", self.endpoints["remove_member_from_space"], params=params)

    def list_spaces(self, page: int = 1, per_page: int = 100) -> List[Dict]:
        """List all spaces with pagination."""
        params = {"page": page, "per_page": per_page}
        data = self.http.request("GET", self.endpoints["list_spaces"], params=params)
        return data.get("records", [])

    def list_space_members(self, space_id: int, page: int = 1, per_page: int = 100) -> List[Dict]:
        """List members of a specific space with pagination."""
        params = {"space_id": space_id, "page": page, "per_page": per_page}
        data = self.http.request("GET", self.endpoints["list_space_members"], params=params)
        return data.get("records", [])

    def get_all_members(self) -> List[Dict]:
        """Fetch ALL members across all pages."""
        all_members = []
        page = 1
        while True:
            response = self.http.request("GET", self.endpoints["list_members"], params={"page": page, "per_page": 100})
            members = response.get("records", [])
            all_members.extend(members)
            if not response.get("has_next_page", False):
                break
            page += 1
        return all_members

    def get_all_spaces(self) -> List[Dict]:
        """Fetch ALL spaces across all pages."""
        all_spaces = []
        page = 1
        while True:
            response = self.http.request("GET", self.endpoints["list_spaces"], params={"page": page, "per_page": 100})
            spaces = response.get("records", [])
            all_spaces.extend(spaces)
            if not response.get("has_next_page", False):
                break
            page += 1
        return all_spaces
```

---

### 3. Pagination Implementation (CRITICAL)
**Issue**: No pagination handling; orgs with >100 members/spaces will have incomplete syncs.  
**Files**: `src/clients/glueup.py:11-29`, `src/clients/circle.py:10-14`

#### Update `src/clients/glueup.py`:
```python
def get_all_users(self) -> List[Dict]:
    """Fetch ALL users across all pages."""
    all_users = []
    page = 1
    while True:
        params = {"page": page, "per_page": 100}
        data = self.http.request("GET", self.endpoints["users_list"], params=params)
        users = data.get("data", [])
        all_users.extend(users)
        # Check if there's a next page (adjust based on actual Glue Up pagination response)
        if not data.get("next_page") and len(users) < 100:
            break
        page += 1
    return all_users

def get_all_memberships(self) -> List[Dict]:
    """Fetch ALL memberships across all pages."""
    all_memberships = []
    page = 1
    while True:
        params = {"page": page, "per_page": 100}
        data = self.http.request("GET", self.endpoints["memberships_list"], params=params)
        memberships = data.get("data", [])
        all_memberships.extend(memberships)
        if not data.get("next_page") and len(memberships) < 100:
            break
        page += 1
    return all_memberships
```

**Note**: Update sync logic in `src/core/sync.py` to use `get_all_users()` and `get_all_memberships()` instead of the single-page methods.

---

### 4. Reconciliation Against Live Circle Data (CRITICAL)
**Issue**: Sync decisions based on stale cache, not current Circle membership.  
**Files**: `src/core/sync.py:60-83`, `src/core/state.py:9-30`

#### Update `src/core/sync.py`:
```python
def reconcile_spaces(circle_client: CircleClient, email: str, target_space_ids: List[str], dry_run: bool) -> None:
    """
    Reconcile member's space membership against target list.
    Uses LIVE Circle data as source of truth, not cache.
    """
    # Fetch current spaces from Circle API
    all_spaces = circle_client.get_all_spaces()
    space_id_map = {str(s["id"]): s for s in all_spaces}
    
    # Get member's CURRENT space memberships from Circle
    current_spaces = set()
    for space_id in space_id_map.keys():
        members = circle_client.list_space_members(int(space_id))
        if any(m.get("community_member", {}).get("email") == email for m in members):
            current_spaces.add(space_id)
    
    target_spaces = set(target_space_ids)
    
    # Add to missing spaces
    to_add = target_spaces - current_spaces
    for space_id in to_add:
        space_name = space_id_map.get(space_id, {}).get("name", space_id)
        if dry_run:
            print(f"[DRY RUN] Would add {email} to space {space_name} ({space_id})")
        else:
            try:
                circle_client.add_member_to_space(email, int(space_id))
                print(f"Added {email} to space {space_name} ({space_id})")
            except Exception as e:
                print(f"Failed to add {email} to space {space_id}: {e}")
    
    # Remove from unwanted spaces
    to_remove = current_spaces - target_spaces
    for space_id in to_remove:
        space_name = space_id_map.get(space_id, {}).get("name", space_id)
        if dry_run:
            print(f"[DRY RUN] Would remove {email} from space {space_name} ({space_id})")
        else:
            try:
                circle_client.remove_member_from_space(email, int(space_id))
                print(f"Removed {email} from space {space_name} ({space_id})")
            except Exception as e:
                print(f"Failed to remove {email} from space {space_id}: {e}")
```

**Alternative (performance optimization)**: Fetch all space memberships once and build an email->spaces map instead of checking each space individually.

---

### 5. Cache Update After Invite (CRITICAL)
**Issue**: New members never added to cache; sync continues indefinitely.  
**File**: `src/core/sync.py:45-58`

#### Update `src/core/sync.py`:
```python
def sync_members(glueup: GlueUpClient, circle: CircleClient, mapping: Dict, state: SyncState, dry_run: bool = False) -> None:
    users = glueup.get_all_users()  # Use paginated version
    memberships = glueup.get_all_memberships()  # Use paginated version
    user_to_memberships = {m["user_id"]: m for m in memberships}

    for user in users:
        email = user.get("email")
        user_id = user.get("id")
        if not email:
            continue

        membership = user_to_memberships.get(user_id)
        if not membership:
            continue

        # Check if member exists in Circle
        if email not in state.member_spaces:
            # Invite new member
            if dry_run:
                print(f"[DRY RUN] Would invite {email}")
                # Don't continue - we need to reconcile spaces even in dry run
            else:
                try:
                    circle.invite_member(email, name=user.get("name"))
                    print(f"Invited {email}")
                    # Add to cache immediately after successful invite
                    state.member_spaces[email] = []
                    state.save()
                except Exception as e:
                    print(f"Failed to invite {email}: {e}")
                    continue  # Skip space reconciliation if invite failed

        # Map membership to spaces
        plan_slug = membership.get("plan_slug") or membership.get("plan_name", "").lower()
        target_space_ids = mapping.get("plans", {}).get(plan_slug, [])

        # Reconcile spaces (for both new and existing members)
        reconcile_spaces(circle, email, target_space_ids, dry_run)
        
        # Update cache with current target spaces
        if not dry_run:
            state.member_spaces[email] = target_space_ids
            state.save()
```

---

### 6. Webhook Security (CRITICAL)
**Issue**: No authentication; anyone can trigger full syncs.  
**File**: `src/web/server.py:45-52`

#### Update `src/web/server.py`:
```python
import hmac
import hashlib
import os

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

@app.route("/webhook/glueup", methods=["POST"])
def glueup_webhook():
    """Webhook endpoint for Glue Up events. Validates signature before processing."""
    
    # Validate webhook signature
    signature = request.headers.get("X-GlueUp-Signature", "")
    if not signature or not WEBHOOK_SECRET:
        return jsonify({"error": "Missing or invalid signature"}), 401
    
    body = request.get_data()
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        return jsonify({"error": "Invalid signature"}), 401
    
    # Process webhook
    payload = request.get_json()
    event_type = payload.get("event")
    
    # Only trigger sync for relevant events
    if event_type in ["member.created", "member.updated", "membership.changed"]:
        sync_members(glueup_client, circle_client, config.mapping, state, dry_run=False)
        return jsonify({"status": "synced"}), 200
    
    return jsonify({"status": "ignored"}), 200
```

#### Environment variables:
```bash
WEBHOOK_SECRET=your_secret_key_here
```

**Note**: Confirm actual Glue Up webhook signature header name and algorithm from their docs.

---

### 7. Production WSGI Server (CRITICAL)
**Issue**: Running Flask dev server in production (insecure, unstable).  
**File**: `src/web/server.py:54-56`

#### Update `src/web/server.py`:
```python
# Remove this block:
# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=8080)

# Add WSGI callable for production servers
application = app  # For gunicorn/uwsgi
```

#### Add `requirements.txt`:
```
flask==3.0.0
requests==2.31.0
pyyaml==6.0
gunicorn==21.2.0
```

#### Add `gunicorn.conf.py`:
```python
bind = "0.0.0.0:8080"
workers = 4
worker_class = "sync"
timeout = 120
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

#### Update deployment command:
```bash
# Production:
gunicorn -c gunicorn.conf.py src.web.server:application

# Development:
FLASK_APP=src/web/server.py FLASK_ENV=development flask run
```

---

## High-Priority Issues (Should Fix)

### 8. Multiple Membership Handling
**Issue**: Only selects first active membership arbitrarily.  
**File**: `src/core/sync.py:38-41`

#### Update `src/core/sync.py`:
```python
def get_primary_membership(memberships: List[Dict], user_id: str) -> Optional[Dict]:
    """
    Select primary membership from multiple active memberships.
    Priority: active > highest tier > most recent.
    """
    user_memberships = [m for m in memberships if m.get("user_id") == user_id]
    
    if not user_memberships:
        return None
    
    # Filter to active only
    active = [m for m in user_memberships if m.get("status") == "active"]
    if not active:
        return None
    
    # If multiple active, pick highest tier (customize tier logic)
    # Example: assume higher plan_id = higher tier
    # Adjust based on your actual membership structure
    active.sort(key=lambda m: (m.get("plan_id", 0), m.get("created_at", "")), reverse=True)
    
    return active[0]

# In sync_members:
membership = get_primary_membership(memberships, user_id)
```

---

### 9. Manual Sync Dry-Run Default
**Issue**: Manual `/sync/members` defaults to dry-run=True, confusing for users.  
**File**: `src/web/server.py:38-43`

#### Update `src/web/server.py`:
```python
@app.route("/sync/members", methods=["POST"])
def sync_members_endpoint():
    """Manual sync endpoint. Defaults to live sync (dry_run=False)."""
    dry_run = request.args.get("dry_run", "false").lower() == "true"
    sync_members(glueup_client, circle_client, config.mapping, state, dry_run=dry_run)
    return jsonify({"status": "completed", "dry_run": dry_run}), 200
```

Usage:
```bash
# Live sync (default):
curl -X POST http://localhost:8080/sync/members

# Dry run (explicit):
curl -X POST http://localhost:8080/sync/members?dry_run=true
```

---

### 10. Error Handling for Cache Corruption
**Issue**: Cache load errors silently reset state.  
**File**: `src/core/state.py:16-18`

#### Update `src/core/state.py`:
```python
import shutil
from datetime import datetime

def load(self) -> None:
    """Load state from cache file with backup on corruption."""
    if not os.path.exists(self.cache_path):
        return
    
    try:
        with open(self.cache_path, "r") as f:
            data = json.load(f)
            self.member_spaces = data.get("member_spaces", {})
            print(f"Loaded cache with {len(self.member_spaces)} members")
    except (json.JSONDecodeError, IOError) as e:
        # Backup corrupted cache
        backup_path = f"{self.cache_path}.corrupt.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy(self.cache_path, backup_path)
        print(f"WARNING: Cache corrupted, backed up to {backup_path}")
        print(f"Error: {e}")
        print("Starting with empty cache - this will re-invite all members!")
        self.member_spaces = {}
```

---

## Medium-Priority Issues (Recommended)

### 11. Tag Support
**Issue**: Mapping defines tags but sync ignores them.  
**File**: `src/config/mapping.yaml`, `src/core/sync.py`

If tags should drive space removal (e.g., "lapsed" members lose access):

#### Update `src/core/sync.py`:
```python
def should_have_access(membership: Dict, user: Dict, mapping: Dict) -> bool:
    """Determine if member should retain access based on membership and tags."""
    status = membership.get("status")
    if status != "active":
        return False
    
    # Check tags if configured
    user_tags = user.get("tags", [])
    blocked_tags = mapping.get("blocked_tags", ["lapsed"])
    
    if any(tag in blocked_tags for tag in user_tags):
        return False
    
    return True

# In sync_members:
if not should_have_access(membership, user, mapping):
    # Remove from all spaces
    reconcile_spaces(circle, email, [], dry_run)
    continue
```

---

### 12. Logging
**Issue**: Only print statements; no structured logging for production.

#### Add `src/core/logger.py`:
```python
import logging
import sys

def setup_logger(name: str = "glueup-circle-bridge") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger
```

Replace all `print()` calls with `logger.info()`, `logger.error()`, etc.

---

## Testing Requirements

### 13. Add Tests
**File**: Create `tests/test_sync.py`, `tests/test_clients.py`

```python
# tests/test_clients.py
import pytest
from unittest.mock import Mock, patch
from src.clients.circle import CircleClient

def test_circle_add_member_to_space():
    """Test that add_member_to_space uses correct API format."""
    mock_http = Mock()
    client = CircleClient("https://api.circle.so", "token", {
        "add_member_to_space": "/space_members"
    })
    client.http = mock_http
    
    client.add_member_to_space("user@example.com", 123)
    
    mock_http.request.assert_called_once_with(
        "POST",
        "/space_members",
        json_body={"email": "user@example.com", "space_id": 123}
    )

# Add tests for pagination, auth, reconciliation, etc.
```

---

## Deployment Checklist

### Environment Variables
```bash
# Glue Up
GLUEUP_BASE_URL=https://api.glueup.com
GLUEUP_HEADER_A=your_a_header
GLUEUP_TOKEN=your_token

# Circle
CIRCLE_BASE_URL=https://app.circle.so/api/admin/v2
CIRCLE_API_TOKEN=your_bearer_token

# Security
WEBHOOK_SECRET=your_webhook_secret

# Cache
CACHE_PATH=/var/lib/bridge/cache.json
```

### Docker Deployment (Recommended)
Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY src/config/*.yaml ./src/config/

EXPOSE 8080

CMD ["gunicorn", "-c", "gunicorn.conf.py", "src.web.server:application"]
```

### Health Check Endpoint
Add to `src/web/server.py`:
```python
@app.route("/health", methods=["GET"])
def health_check():
    """Health check for load balancers."""
    return jsonify({"status": "healthy"}), 200
```

---

## Priority Order

1. **Fix Glue Up auth** (blocks all Glue Up API calls)
2. **Fix Circle endpoints** (blocks all Circle operations)
3. **Add pagination** (prevents incomplete syncs)
4. **Fix reconciliation logic** (prevents incorrect space assignments)
5. **Fix cache update** (prevents infinite re-invites)
6. **Add webhook security** (prevents abuse)
7. **Deploy with gunicorn** (production stability)
8. **Add tests** (prevent regressions)
9. **Improve logging** (production observability)
10. **Handle edge cases** (tags, multiple memberships)

---

## Validation Steps

After implementing changes:

1. **Auth test**: Verify both Glue Up headers sent correctly
2. **Pagination test**: Verify all members/spaces fetched (not just first page)
3. **Reconciliation test**: Manually check Circle space memberships match expected state
4. **Cache test**: Verify new invites update cache correctly
5. **Webhook test**: Verify signature validation blocks unauthorized requests
6. **Load test**: Run sync with 500+ members to verify performance

---

## Open Questions for Stakeholders

1. **Multiple memberships**: If a user has multiple active memberships (e.g., Gold + Silver), which plan's spaces should apply?
2. **Tag behavior**: Should "lapsed" or "inactive" tags remove users from all spaces, or just prevent new space adds?
3. **Glue Up webhook format**: What is the exact signature header name and HMAC algorithm used?
4. **Circle API limits**: Are there rate limits we need to handle (e.g., max requests per minute)?
5. **Monitoring**: What metrics should be exposed (sync duration, error rate, member count)?

---

## References

- Circle Admin API V2: `docs/circle-admin-swagger.yaml`
- Glue Up API: `docs/glueupapi.apib`
- Current implementation: `src/` directory
