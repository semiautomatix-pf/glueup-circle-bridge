# Event Field Mapping: GlueUp → Circle

This document details how event data is mapped from GlueUp to Circle.

## Core Event Fields

| GlueUp Field | Circle Field | Notes |
|--------------|--------------|-------|
| `id` | `slug` (derived) | Used as part of slug: `{title-slug}-{id}` |
| `title` | `name` | Event title |
| `subTitle` | `body` (prepended) | Subtitle prepended to description as bold text |
| `about` | `body` | Primary description (HTML format) |
| `summary` | `body` (fallback) | Used if `about` is empty |
| `startDateTime` | `starts_at` | Converted from milliseconds to ISO 8601 |
| `endDateTime` | `ends_at` | Converted from milliseconds to ISO 8601 |

## Venue/Location Fields

| GlueUp Field | Circle Field | Notes |
|--------------|--------------|-------|
| `venueInfo.name` | `location` | Combined into location string |
| `venueInfo.address` | `location` | Combined into location string |
| `venueInfo.city` | `location` | Combined into location string |
| `venueInfo.country.name` | `location` | Combined into location string |
| `venueInfo.timezone` | `timezone` | Event timezone (e.g., "Australia/Brisbane") |
| `venueInfo.map.latitude` | `venue_latitude` | GPS coordinates |
| `venueInfo.map.longitude` | `venue_longitude` | GPS coordinates |
| `venueInfo` (detected) | `location_type` | Auto-detected: "in_person", "virtual", or "tbd" |

### Location Type Auto-Detection

The system automatically detects the location type:

- **"virtual"** - If venue name contains: online, virtual, webinar, zoom, teams, meet
- **"in_person"** - If venue has address or city information
- **"tbd"** - If venue information is missing or incomplete

You can override auto-detection by setting `field_overrides.location_type` in `mapping.yaml`.

## Image Fields

| GlueUp Field | Circle Field | Notes |
|--------------|--------------|-------|
| `template.images.banner.uri` | `cover_image_url` | Primary cover image (1200x630 size) |
| `template.images.headerImage.uri` | `cover_image_url` (fallback) | Used if banner not available |
| `imageUrl` | `cover_image_url` (fallback) | Direct image URL if available |

**Note:** GlueUp uses placeholder `::size::` in URIs which is replaced with `1200x630` for optimal display. Relative URLs (starting with `/`) are currently not supported and will be skipped.

## Configuration Fields

These fields come from `mapping.yaml` configuration:

| Config Field | Circle Field | Default | Notes |
|--------------|--------------|---------|-------|
| `field_overrides.host` | `host` | "GlueUp Events" | Event host name |
| `field_overrides.rsvp_disabled` | `rsvp_disabled` | false | Disable RSVPs |
| `field_overrides.send_email_confirmation` | `send_email_confirmation` | true | RSVP confirmation email |
| `field_overrides.send_email_reminder` | `send_email_reminder` | true | Pre-event reminder email |
| `field_overrides.location_type` | `location_type` | (auto-detect) | Force location type if set |

## Metadata Fields

Additional venue details that may be included (depending on Circle API support):

| GlueUp Field | Circle Field | Notes |
|--------------|--------------|-------|
| `venueInfo.name` | `venue_name` | Venue name as separate field |
| `venueInfo.address` | `venue_address` | Street address |
| `venueInfo.city` | `venue_city` | City name |
| `venueInfo.country.name` | `venue_country` | Country name |

## Filters Applied

Events are filtered during sync based on configuration:

| Filter | Field | Default | Purpose |
|--------|-------|---------|---------|
| `published_only` | `published` | true | Only published events |
| `future_only` | `endDateTime` | true | Only events ending after current time |

## Checksum Fields

These fields are used to detect changes (MD5 checksum):

- `title`
- `subTitle`
- `about`
- `summary`
- `startDateTime`
- `endDateTime`
- `venueInfo.name`
- `venueInfo.address`
- `venueInfo.city`
- `venueInfo.country`
- `venueInfo.timezone`
- `template.images` (banner and header)

If any of these fields change in GlueUp, the event will be updated in Circle (if `update_existing: true`).

## Example Transformation

### GlueUp Event Data:
```json
{
  "id": 160084,
  "title": "How to Grow Revenue Without Losing Your Why",
  "subTitle": "A Power Session",
  "about": "<p>In this 45-minute power session...</p>",
  "startDateTime": 1764644400000,
  "endDateTime": 1764647100000,
  "venueInfo": {
    "name": "Conference Center",
    "address": "123 Main St",
    "city": "Brisbane",
    "timezone": "Australia/Brisbane",
    "country": {
      "name": "Australia",
      "code": "AU"
    },
    "map": {
      "latitude": -27.508271,
      "longitude": 152.995605
    }
  },
  "template": {
    "images": {
      "banner": {
        "uri": "/resources/public/images/fixed-width/::size::/banner.png"
      }
    }
  }
}
```

### Circle Event Data:
```json
{
  "name": "How to Grow Revenue Without Losing Your Why",
  "slug": "how-to-grow-revenue-without-losing-your-why-160084",
  "body": "<p><strong>A Power Session</strong></p>\n<p>In this 45-minute power session...</p>",
  "starts_at": "2025-12-01T09:00:00",
  "ends_at": "2025-12-01T09:45:00",
  "location": "Conference Center, 123 Main St, Brisbane, Australia",
  "location_type": "in_person",
  "timezone": "Australia/Brisbane",
  "host": "GlueUp Events",
  "rsvp_disabled": false,
  "send_email_confirmation": true,
  "send_email_reminder": true,
  "user_id": 12345,
  "space_id": "2411092",
  "venue_name": "Conference Center",
  "venue_address": "123 Main St",
  "venue_city": "Brisbane",
  "venue_country": "Australia",
  "venue_latitude": -27.508271,
  "venue_longitude": 152.995605
}
```

## Fields Not Currently Synced

These GlueUp fields are available but not currently mapped:

- `language.code` - Event language
- `defaultLanguage.code` - Default language
- `openToPublic` - Whether event is public (used for filtering only)
- `template.fontFamily` - Font styling
- `template.colors` - Color scheme
- Custom fields - Any organization-specific custom fields

If you need any of these fields synced, they can be added to the transformation logic.

## Testing Event Data

To see what data is being synced in dry-run mode:

```bash
curl -X POST http://localhost:8082/sync/events \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}' | jq '.details[]'
```

This will show:
- Event title
- Slug
- Start/end times
- Location string
- Location type (auto-detected)
- Timezone
- Whether cover image is present

## Customization

To customize field mapping, edit:
- `src/core/event_sync.py` - `transform_glueup_event_to_circle()` function
- `src/config/mapping.yaml` - `events.field_overrides` section

To request more fields from GlueUp API:
- `src/clients/glueup.py` - `list_events()` function - add to `projection` array
