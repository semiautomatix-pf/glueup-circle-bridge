# GlueUp ⇆ Circle Bridge

A lightweight service that keeps your Glue Up (AMS) members and events in sync with your Circle community.

**What it does (out-of-the-box):**

**Member Syncing:**
- Syncs **individual members** from Glue Up membership directory
- Syncs **corporate memberships** including admin contacts and member contacts
- Creates or invites matching members in Circle via the Admin API v2
- Adds/removes members to/from Spaces based on membership plan mapping
- Multi-layer deduplication (in-batch, cache-based, webhook-based)
- Optional: mirrors tags, and deactivates access when memberships lapse

**Event Syncing:**
- Syncs published events from Glue Up to Circle
- Creates new events automatically with rich details:
  - Event title, subtitle, and full description (HTML)
  - Start/end dates with timezone support
  - Venue details (name, address, city, country, GPS coordinates)
  - Auto-detected location type (in-person, virtual, or TBD)
  - Cover images from event templates
- Updates events when GlueUp data changes (via checksum comparison)
- Maintains event mappings in cache
- Supports dry-run mode for safe testing
- Only syncs future events (past events automatically excluded)

**Infrastructure:**
- Exposes HTTP server for health checks, manual sync, and webhook ingestion
- Webhook deduplication to prevent duplicate processing
- State cache with member, event, and webhook tracking
- Admin endpoints for cache validation and statistics

> This repository ships with safe defaults and a config-driven approach because Glue Up tenants can differ and Circle endpoints evolve. You only need to paste the exact endpoint paths from your Glue Up and Circle docs into `src/config/endpoints.yaml` (examples included).

---

## Quick start

### 1) Prerequisites
- Python 3.10+
- A Glue Up account with Open API v2 access enabled.
- A Circle community API token (Admin API v2).

### 2) Grab API details
- **Glue Up**: obtain your API credentials (public key, private key, email, and password). Your account manager can enable API access if not already enabled. The bridge uses HMAC-SHA256 signature authentication with automatic session token management.
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

**Core Endpoints:**
- `GET /health` – readiness probe
- `GET /spaces` – list all Circle spaces with IDs (for mapping configuration)

**Member Sync:**
- `POST /sync/members` – on-demand member sync (`{"dry_run": true}` supported)
  - Syncs individual members, corporate admin contacts, and corporate member contacts
  - Returns detailed report with member types, duplicates, cache hits/misses

**Event Sync:**
- `POST /sync/events` – on-demand event sync (`{"dry_run": true}` supported)
  - Syncs published events from GlueUp to Circle
  - Creates new events and updates changed events
  - `user_id` is automatically derived from Circle API token (or can be explicitly provided)
  - Returns report with created, updated, deleted, skipped counts
- `GET /events/status` – event sync statistics and mappings

**Webhooks:**
- `POST /webhooks/glueup` – webhook receiver with deduplication
  - Automatically prevents duplicate processing
  - Triggers member sync for webhook payloads

**Admin & Cache Management:**
- `GET /admin/cache/stats` – cache statistics (members, events, webhooks)
- `POST /admin/cache/validate` – validate cache against Circle API (`{"repair": true}` to fix discrepancies)

### 5) Manual sync

**Member Sync:**
```bash
# Dry run first to see what would happen
curl -X POST http://localhost:8080/sync/members -H "Content-Type: application/json" -d '{"dry_run": true}'

# Execute actual sync
curl -X POST http://localhost:8080/sync/members -H "Content-Type: application/json" -d '{"dry_run": false}'
```

**Event Sync:**

```bash
# Dry run first (user_id automatically derived from token)
curl -X POST http://localhost:8080/sync/events -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# Execute actual sync
curl -X POST http://localhost:8080/sync/events -H "Content-Type: application/json" \
  -d '{"dry_run": false}'

# Check event sync status
curl http://localhost:8080/events/status

# Optional: Specify a different user_id explicitly
curl -X POST http://localhost:8080/sync/events -H "Content-Type: application/json" \
  -d '{"dry_run": false, "user_id": 123}'
```

**Cache Management:**
```bash
# Get cache statistics
curl http://localhost:8080/admin/cache/stats

# Validate cache against Circle API
curl -X POST http://localhost:8080/admin/cache/validate -H "Content-Type: application/json" \
  -d '{"repair": false}'

# Validate and repair cache
curl -X POST http://localhost:8080/admin/cache/validate -H "Content-Type: application/json" \
  -d '{"repair": true}'
```

---

## Configuration

### `.env`

| Variable | Description |
|---|---|
| `GLUEUP_BASE_URL` | Glue Up API base URL including version, e.g. `https://api.glueup.com/v2` |
| `GLUEUP_PUBLIC_KEY` | Your Glue Up API public key |
| `GLUEUP_PRIVATE_KEY` | Your Glue Up API private key |
| `GLUEUP_EMAIL` | Your Glue Up account email |
| `GLUEUP_PASSPHRASE` | Your Glue Up account password (plaintext - the code will MD5 hash it) |
| `GLUEUP_ORGANIZATION_ID` | Your Glue Up organization ID (find in dashboard URL or API responses) |
| `CIRCLE_BASE_URL` | Circle Admin API base, defaults to `https://app.circle.so/api/admin/v2` |
| `CIRCLE_API_TOKEN` | Your Circle Admin API token |
| `SERVER_PORT` | Optional; default `8080` |

> **Note**: Glue Up authentication is handled automatically by the bridge. It generates HMAC-SHA256 signatures for each request and manages session tokens internally, refreshing them as needed.

### `src/config/endpoints.yaml`

You can overwrite any of these paths to match your tenant/version.

```yaml
glueup:
  # POST - Returns active individual members
  members_directory: "/membershipDirectory/members"
  # POST - Returns corporate memberships with contacts
  corporate_memberships_directory: "/membershipDirectory/corporateMemberships"
  # POST - Returns membership types
  membership_types: "/public/membership/publishedMembershipTypeList"
  # GET - Returns memberships for authenticated user
  memberships_list: "/membership/activeApplicationList"
  # POST - Returns events list
  events_list: "/event/list"

circle:
  # Member endpoints
  list_members: "/community_members"
  invite_member: "/community_members"
  update_member: "/community_members/{member_id}"
  add_member_to_space: "/space_members"
  remove_member_from_space: "/space_members"
  list_spaces: "/spaces"
  list_space_members: "/space_members"
  # Event endpoints
  list_events: "/events"
  create_event: "/events"
  update_event: "/events/{id}"
  delete_event: "/events/{id}"
  get_event: "/events/{id}"
```

> Exact names can vary across API versions. Open the Circle Admin API page and copy the operation paths. Same for Glue Up via the Apiary doc. This app simply stitches whatever you put here.

### `src/config/mapping.yaml`

Maps Glue Up plan *slugs* (or names) to Circle **space IDs**, and configures event sync settings.

```yaml
plans_to_spaces:
  professional: ["12345"]
  student: ["67890", "11223"]
  # Corporate membership plans (check GlueUp for exact names - case sensitive)
  "corporate gold": ["45678"]
  "corporate silver": ["45678"]

default_spaces: ["2411092"]    # spaces every member should join (e.g., Announcements)

tags:
  active: ["Active"]
  lapsed: ["Lapsed"]

# Event sync configuration
events:
  default_space_id: "2411092"  # Space where all events will be created

  sync_settings:
    create_new: true          # Create new events in Circle
    update_existing: true     # Update Circle events when GlueUp event changes
    delete_removed: false     # Delete Circle events removed from GlueUp (recommended: false)
    published_only: true      # Only sync published events
    future_only: true         # Only sync future/upcoming events (past events ignored)
    sync_attendees: false     # Sync event attendees (not yet implemented)

  field_overrides:
    host: "GlueUp Events"
    location_type: "tbd"      # "in_person", "virtual", or "tbd"
    rsvp_disabled: false
    send_email_confirmation: true
    send_email_reminder: true
```

---

## Testing & verification

### Member Sync Testing

**1. Configure corporate plan mappings:**
- Check GlueUp for exact corporate plan names (case-sensitive)
- Update `src/config/mapping.yaml` with corporate plan slugs
- Map them to appropriate Circle space IDs

**2. Run dry-run first:**
```bash
curl -X POST http://localhost:8080/sync/members -H "Content-Type: application/json" -d '{"dry_run": true}' | jq
```

**3. Verify report includes all member types:**
- Check `member_types` in report for individual, corporate_admin, corporate_contact counts
- Review `duplicates_skipped` for deduplication effectiveness
- Check `cache_hits` vs `cache_misses` for cache performance

**4. Execute actual sync:**
```bash
curl -X POST http://localhost:8080/sync/members -H "Content-Type: application/json" -d '{"dry_run": false}' | jq
```

**5. Verify in Circle:**
- Check that corporate contacts appear with correct names and emails
- Verify they're added to correct spaces based on plan mapping
- Check cache stats: `curl http://localhost:8080/admin/cache/stats | jq`

### Event Sync Testing

**1. Configure event settings:**
- Set `default_space_id` in `src/config/mapping.yaml` to a valid Circle space ID
- Review `sync_settings` to match your needs
- Adjust `field_overrides` as needed

**2. Look up Circle user ID:**
```bash
# Find an admin user to use as event creator
curl -H "Authorization: Bearer YOUR_CIRCLE_TOKEN" \
  https://app.circle.so/api/admin/v2/community_members | jq '.records[] | {id, email, first_name, last_name}' | head -20
```

**3. Run event sync dry-run:**
```bash
curl -X POST http://localhost:8080/sync/events -H "Content-Type: application/json" \
  -d '{"dry_run": true, "user_id": YOUR_USER_ID}' | jq
```

**4. Verify report:**
- Check `created` count for new events
- Review `details` array for event titles and slugs
- Ensure no errors reported

**5. Execute actual sync:**
```bash
curl -X POST http://localhost:8080/sync/events -H "Content-Type: application/json" \
  -d '{"dry_run": false, "user_id": YOUR_USER_ID}' | jq
```

**6. Verify events in Circle:**
- Check that events appear in the configured space
- Verify dates are correct (GlueUp milliseconds → ISO 8601 conversion)
- Verify event details (title, description, location)

**7. Test update detection:**
- Modify an event in GlueUp (change title or date)
- Re-run event sync
- Verify `updated` count increases and event not duplicated
- Check that unchanged events show as `skipped`

### Deduplication Testing

**1. Test in-batch deduplication:**
- Create a member with same email in both individual and corporate membership in GlueUp
- Run member sync
- Verify only ONE Circle member created
- Check `duplicates_skipped` count in report

**2. Test webhook deduplication:**
- Send a webhook payload to `/webhooks/glueup`
- Send same payload again immediately
- Verify second request returns `{"skipped": "duplicate"}`

**3. Test cache validation:**
```bash
# Check for cache issues
curl -X POST http://localhost:8080/admin/cache/validate -H "Content-Type: application/json" \
  -d '{"repair": false}' | jq

# Repair if needed
curl -X POST http://localhost:8080/admin/cache/validate -H "Content-Type: application/json" \
  -d '{"repair": true}' | jq
```

### Monitoring

**Key metrics to watch:**

```bash
# Cache statistics
curl http://localhost:8080/admin/cache/stats | jq

# Event sync status
curl http://localhost:8080/events/status | jq

# Member sync report (dry-run for monitoring)
curl -X POST http://localhost:8080/sync/members -d '{"dry_run": true}' | jq '.member_types, .duplicates_skipped, .cache_hits, .cache_misses'
```

**Log monitoring:**
```bash
# Watch logs during sync
tail -f /var/log/glueup-circle-bridge.log

# Or with Docker
docker logs -f glueup-circle-bridge

# Check for errors
grep ERROR /var/log/glueup-circle-bridge.log

# Check member type distribution
grep "member_types" /var/log/glueup-circle-bridge.log
```

---

## Deploy

### Production (gunicorn)

For production deployments, use gunicorn:

```bash
gunicorn -c gunicorn.conf.py src.web.server:application
```

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

**Dry Run Mode:**
- All write calls are gated behind `dry_run` until you flip the switch
- Both member and event sync support dry-run mode for safe testing

**Deduplication:**
- **In-batch**: Prevents same email from being processed multiple times in single sync
- **Cache-based**: Uses local cache for fast email→ID lookups
- **Membership index**: Cross-checks cache against Circle API to catch stale data
- **Webhook**: Prevents duplicate webhook processing using webhook ID tracking
- **Event checksum**: Skips event updates when content hasn't changed

**Idempotency:**
- Members: compute desired state and skip if already matching
- Events: checksum comparison prevents unnecessary updates

**Resilience:**
- Rate-limits: HTTP client retries with exponential backoff on 429/5xx
- Cache recovery: automatic cache validation and repair endpoints
- Error handling: detailed error reporting without stopping full sync

**State Cache:**
- Local disk cache at `.cache/known_members.json`
- Tracks: members, events, webhooks (last 1000)
- Backward compatible with existing cache files
- Auto-cleanup of webhook records to prevent unbounded growth

---

## Features & roadmap

**✅ Implemented:**
- Individual member syncing
- Corporate member syncing (admin contacts + member contacts)
- Event syncing (create/update with checksum-based change detection)
- Multi-layer deduplication (in-batch, cache, webhook, event)
- State cache with member, event, and webhook tracking
- Cache validation and repair utilities
- Webhook deduplication
- Admin endpoints for monitoring and cache management

**🔮 Future enhancements:**
- Event attendee/RSVP syncing from GlueUp to Circle
- Custom field mapping for members (company name, member ID, etc.)
- Tag and group synchronization
- Webhook signature verification for GlueUp payloads
- Scheduled automatic syncs (currently requires cron or external scheduler)
- PostgreSQL backend option (instead of JSON cache)
- Observability: Prometheus metrics, structured logging
- Bi-directional sync: Circle → GlueUp updates

---

## Troubleshooting

### Corporate members not syncing

**Problem:** Corporate admin/member contacts not appearing in Circle

**Solutions:**
1. Verify GlueUp organization ID is set: `GLUEUP_ORGANIZATION_ID` in `.env`
2. Check endpoint is configured: `corporate_memberships_directory` in `endpoints.yaml`
3. Verify corporate plan names in `mapping.yaml` match GlueUp exactly (case-sensitive)
4. Check logs for "Fetched X corporate memberships" message
5. Run with dry-run and check `member_types` in report

### Events not creating

**Problem:** Event sync reports errors or events don't appear

**Solutions:**
1. Verify `default_space_id` in `mapping.yaml` is a valid Circle space ID
2. Check `user_id` parameter is correct Circle user ID (not email)
3. Ensure user has permission to create events in that space
4. Check GlueUp events are published: `publishToEventWebsite: true`
5. Review error details in sync report

### Duplicate members

**Problem:** Same person appears multiple times in Circle

**Solutions:**
1. Check if person exists in multiple GlueUp membership types with different emails
2. Run cache validation: `POST /admin/cache/validate` with `repair: true`
3. Review `duplicates_skipped` count in sync report
4. Check for webhook replay - verify webhook deduplication is working

### Cache out of sync

**Problem:** Members in Circle but not in cache, or vice versa

**Solutions:**
```bash
# Validate and repair cache
curl -X POST http://localhost:8080/admin/cache/validate \
  -H "Content-Type: application/json" -d '{"repair": true}' | jq
```

If cache is corrupted:
```bash
# Backup and reset cache
cp .cache/known_members.json .cache/backup.json
rm .cache/known_members.json
# Restart service - will rebuild cache from Circle API
```

### Authentication failures

**Problem:** GlueUp API returns 401/403 errors

**Solutions:**
1. Verify credentials in `.env` are correct
2. Check `GLUEUP_PASSPHRASE` is plaintext (will be MD5 hashed automatically)
3. Ensure GlueUp API access is enabled for your account
4. Check `requestOrganizationId` header matches your organization

### Rate limiting

**Problem:** HTTP 429 errors from APIs

**Solutions:**
- Client already implements exponential backoff (1-20s, 5 retries)
- If still hitting limits, reduce sync frequency
- Consider implementing longer delays between syncs

### Webhook not processing

**Problem:** Webhooks received but not triggering sync

**Solutions:**
1. Check webhook payload has `id` or `event_id` field for deduplication
2. Verify webhook isn't being filtered as duplicate (check `webhook_events` in cache)
3. Review webhook handler logs for errors
4. Test webhook manually with curl

---

## Support

This project is intentionally small, config-driven, and auditable. If you need a hardened runtime (PostgreSQL, queuing, observability), this codebase is a clean starting point.

### Getting help

- Check logs first: look for ERROR level messages
- Review documentation:
  - `/docs/QUICK_START.md` - Quick reference guide
  - `/docs/IMPLEMENTATION_SUMMARY.md` - Complete technical documentation
  - `/docs/EVENT_FIELD_MAPPING.md` - Detailed event field mapping reference
- Validate configuration: ensure all required fields are set in `.env` and YAML files
- Test with dry-run: always use `dry_run: true` first to see what would happen

### Contributing

This is a focused bridge implementation. For feature requests or bug reports, please:
1. Check existing issues first
2. Provide minimal reproduction steps
3. Include relevant log excerpts
4. Specify your GlueUp and Circle API versions
