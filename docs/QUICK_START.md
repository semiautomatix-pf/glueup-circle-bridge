# Quick Start Guide - New Features

This guide helps you quickly get started with the newly implemented features: corporate member syncing, event syncing, and enhanced deduplication.

## Prerequisites

1. Service is running: `python -m src.web.server`
2. Configuration files updated (`.env`, `endpoints.yaml`, `mapping.yaml`)
3. GlueUp and Circle API credentials configured

---

## Corporate Member Syncing

### Step 1: Configure Corporate Plans

Edit `src/config/mapping.yaml` and add your corporate plan names:

```yaml
plans_to_spaces:
  # Check GlueUp for exact plan names (case-sensitive!)
  "corporate gold": ["YOUR_SPACE_ID"]
  "corporate silver": ["YOUR_SPACE_ID"]
  "corporate platinum": ["YOUR_SPACE_ID"]
```

### Step 2: Test with Dry Run

```bash
curl -X POST http://localhost:8080/sync/members \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

### Step 3: Check Member Types

Look for this in the response:

```json
{
  "member_types": {
    "individual": 150,
    "corporate_admin": 5,
    "corporate_contact": 20
  }
}
```

### Step 4: Execute Sync

```bash
curl -X POST http://localhost:8080/sync/members \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

### Step 5: Verify in Circle

- Check that corporate contacts appear in Circle
- Verify they're added to correct spaces
- Check names and emails are correct

---

## Event Syncing

### Step 1: Configure Event Space

Edit `src/config/mapping.yaml`:

```yaml
events:
  default_space_id: "2411092"  # Replace with your Circle space ID
  sync_settings:
    create_new: true
    update_existing: true
    delete_removed: false  # Keep this false for safety
    published_only: true
```

### Step 2: Test Event Sync with Dry Run

The user ID is automatically derived from your Circle API token, so you don't need to look it up!

```bash
curl -X POST http://localhost:8080/sync/events \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'
```

**Optional:** If you want to use a specific user ID instead:
```bash
# First find a user ID
curl -H "Authorization: Bearer YOUR_CIRCLE_API_TOKEN" \
  https://app.circle.so/api/admin/v2/community_members \
  | jq '.records[] | {id, email, first_name, last_name}'

# Then specify it explicitly
curl -X POST http://localhost:8080/sync/events \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true, "user_id": YOUR_USER_ID}'
```

### Step 3: Check What Would Be Created

Look for this in the response:

```json
{
  "created": 8,
  "updated": 0,
  "skipped": 0,
  "errors": 0,
  "details": [
    {
      "action": "create_event",
      "glueup_id": "12345",
      "title": "Annual Conference 2026",
      "slug": "annual-conference-2026-12345",
      "dry_run": true
    }
  ]
}
```

### Step 4: Execute Event Sync

```bash
curl -X POST http://localhost:8080/sync/events \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

### Step 5: Verify Events in Circle

- Check events appear in the configured space
- Verify dates are correct
- Check event details (title, description, location)

### Step 6: Check Event Status

```bash
curl http://localhost:8080/events/status | jq
```

---

## Testing Deduplication

### Test 1: In-Batch Deduplication

**Scenario:** Person exists in both individual and corporate membership with same email

**Expected:** Only one Circle member created

```bash
# Run sync
curl -X POST http://localhost:8080/sync/members -d '{"dry_run": false}' | jq

# Check duplicates_skipped count
# Should be > 0 if duplicates were found
```

### Test 2: Webhook Deduplication

```bash
# Send webhook twice
curl -X POST http://localhost:8080/webhooks/glueup \
  -H "Content-Type: application/json" \
  -d '{"id": "test-webhook-123", "type": "member.updated"}'

# First call: processes webhook
# Second call: returns {"skipped": "duplicate"}
```

### Test 3: Cache Validation

```bash
# Check cache health
curl -X POST http://localhost:8080/admin/cache/validate \
  -H "Content-Type: application/json" \
  -d '{"repair": false}' | jq

# If issues found, repair them
curl -X POST http://localhost:8080/admin/cache/validate \
  -H "Content-Type: application/json" \
  -d '{"repair": true}' | jq
```

---

## Monitoring Commands

### Check Cache Statistics

```bash
curl http://localhost:8080/admin/cache/stats | jq
```

Expected output:
```json
{
  "members_count": 175,
  "member_spaces_count": 175,
  "events_count": 56,
  "webhooks_count": 234
}
```

### Get Event Sync Status

```bash
curl http://localhost:8080/events/status | jq
```

### Check Member Sync Status

```bash
# Dry run to see current state without changes
curl -X POST http://localhost:8080/sync/members \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}' | jq
```

### List All Circle Spaces

```bash
curl http://localhost:8080/spaces | jq
```

---

## Common Workflows

### Daily Member Sync (via cron)

Add to crontab:
```cron
# Every 6 hours
0 */6 * * * curl -s -X POST http://localhost:8080/sync/members \
  -H 'Content-Type: application/json' \
  -d '{"dry_run": false}' >> /var/log/member-sync.log 2>&1
```

### Daily Event Sync (via cron)

Add to crontab:
```cron
# Every 12 hours (user_id automatically derived from token)
0 */12 * * * curl -s -X POST http://localhost:8080/sync/events \
  -H 'Content-Type: application/json' \
  -d '{"dry_run": false}' >> /var/log/event-sync.log 2>&1
```

### Weekly Cache Validation

Add to crontab:
```cron
# Every Sunday at 2am
0 2 * * 0 curl -s -X POST http://localhost:8080/admin/cache/validate \
  -H 'Content-Type: application/json' \
  -d '{"repair": true}' >> /var/log/cache-validation.log 2>&1
```

---

## Troubleshooting Quick Fixes

### Corporate members not appearing?

```bash
# 1. Check if corporate endpoint is working
grep "corporate_memberships_directory" src/config/endpoints.yaml

# 2. Check if organization ID is set
grep "GLUEUP_ORGANIZATION_ID" .env

# 3. Check logs for corporate membership count
# Should see: "Fetched X corporate memberships"
```

### Events not creating?

```bash
# 1. Check space ID is valid
curl http://localhost:8080/spaces | jq '.[] | select(.id == "YOUR_SPACE_ID")'

# 2. Check user ID auto-detection works
curl -X POST http://localhost:8080/sync/events \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}' | jq
# If there's an error about user_id, the Circle token may not have access to community members

# 3. Check events are published in GlueUp
# Look for: "publishToEventWebsite": true
```

### Cache issues?

```bash
# Quick fix: Validate and repair
curl -X POST http://localhost:8080/admin/cache/validate \
  -H "Content-Type: application/json" \
  -d '{"repair": true}' | jq

# Nuclear option: Reset cache
cp .cache/known_members.json .cache/backup-$(date +%Y%m%d).json
rm .cache/known_members.json
# Restart service to rebuild cache
```

---

## Complete Test Run

Here's a complete sequence to test all features:

```bash
# 1. Check service health
curl http://localhost:8080/health

# 2. Get cache stats (baseline)
curl http://localhost:8080/admin/cache/stats | jq

# 3. List available spaces
curl http://localhost:8080/spaces | jq

# 4. Test member sync (dry run)
curl -X POST http://localhost:8080/sync/members \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}' | jq

# 5. Execute member sync
curl -X POST http://localhost:8080/sync/members \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}' | jq

# 6. Test event sync (dry run) - user_id automatically derived
curl -X POST http://localhost:8080/sync/events \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}' | jq

# 7. Execute event sync
curl -X POST http://localhost:8080/sync/events \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}' | jq

# 8. Check event status
curl http://localhost:8080/events/status | jq

# 9. Test webhook deduplication
curl -X POST http://localhost:8080/webhooks/glueup \
  -H "Content-Type: application/json" \
  -d '{"id": "test-123"}' | jq

# Send same webhook again - should be skipped
curl -X POST http://localhost:8080/webhooks/glueup \
  -H "Content-Type: application/json" \
  -d '{"id": "test-123"}' | jq

# 10. Validate cache
curl -X POST http://localhost:8080/admin/cache/validate \
  -H "Content-Type: application/json" \
  -d '{"repair": false}' | jq

# 11. Get final cache stats
curl http://localhost:8080/admin/cache/stats | jq
```

---

## Success Indicators

After running the test sequence, you should see:

✅ **Member Sync:**
- `member_types` shows individual, corporate_admin, corporate_contact
- `duplicates_skipped` count if any duplicates found
- `cache_hits` high, `cache_misses` low (after first sync)
- All member types appear in Circle

✅ **Event Sync:**
- `created` count shows new events
- `updated` count shows changed events on subsequent syncs
- `skipped` count shows unchanged events
- Events visible in Circle with correct dates and details

✅ **Deduplication:**
- Second webhook call returns `{"skipped": "duplicate"}`
- No duplicate members created for same email
- Cache validation shows mostly valid entries
- Webhook count in cache stats

✅ **Cache Health:**
- `members_count` matches Circle member count
- `events_count` matches synced event count
- `webhooks_count` increases with each webhook
- Cache validation reports minimal issues

---

## Next Steps

Once basic functionality is confirmed:

1. **Set up scheduled syncs** - Use cron or similar scheduler
2. **Monitor logs** - Watch for errors or warnings
3. **Tune configuration** - Adjust sync frequencies based on load
4. **Test edge cases** - Try various membership and event scenarios
5. **Document your mappings** - Keep track of plan → space mappings
6. **Set up alerts** - Get notified of sync failures
7. **Backup cache** - Regularly backup `.cache/known_members.json`

---

## Getting Help

If you encounter issues:

1. Check logs: `docker logs glueup-circle-bridge` or application logs
2. Review this guide and ensure all steps followed correctly
3. Check the main README.md for detailed configuration
4. Review IMPLEMENTATION_SUMMARY.md for technical details
5. Validate configuration files (`.env`, `endpoints.yaml`, `mapping.yaml`)
6. Test with dry-run first before executing actual changes

---

**Remember:** Always use `dry_run: true` first when testing new configurations!
