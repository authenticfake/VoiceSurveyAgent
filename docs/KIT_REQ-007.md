# KIT Documentation — REQ-007: Exclusion List Management

## Overview

REQ-007 implements exclusion list management for the VoiceSurveyAgent platform. This feature allows campaign managers to maintain a list of phone numbers that should never be called, ensuring compliance with do-not-call regulations and customer preferences.

## Acceptance Criteria Status

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| POST /api/exclusions/import accepts CSV of phone numbers | ✅ | `router.py:import_exclusions()` |
| Contacts matching exclusion list marked as excluded state | ✅ | `service.py:mark_contacts_excluded()` |
| Excluded contacts never returned by scheduler queries | ✅ | Contacts with `state=excluded` or `do_not_call=True` |
| Manual exclusion addition via API supported | ✅ | `router.py:create_exclusion()` |
| Exclusion removal requires admin role | ✅ | `router.py:delete_exclusion()` with `require_admin` |

## Architecture

### Module Structure

```
runs/kit/REQ-007/src/app/contacts/exclusions/
├── __init__.py          # Module exports
├── models.py            # SQLAlchemy model for ExclusionListEntry
├── repository.py        # Database operations
├── schemas.py           # Pydantic request/response schemas
├── service.py           # Business logic
└── router.py            # FastAPI endpoints
```

### Dependencies

- **REQ-001**: Database schema (exclusion_list_entries table)
- **REQ-002**: Authentication (CurrentUser)
- **REQ-003**: RBAC (role-based access control)
- **REQ-006**: Contact models and state management

### Key Components

1. **ExclusionListEntry Model**: SQLAlchemy model matching the database schema
2. **ExclusionRepository**: Data access layer with bulk operations
3. **ExclusionService**: Business logic including CSV import and contact sync
4. **API Router**: RESTful endpoints with proper RBAC

## API Endpoints

### POST /api/exclusions/import
Import phone numbers from CSV file.

**Request**: Multipart form with CSV file
**Response**: `ExclusionImportResponse` with counts and errors
**Role**: campaign_manager or admin

### POST /api/exclusions
Add single phone number to exclusion list.

**Request**: `ExclusionCreateRequest`
**Response**: `ExclusionEntryResponse`
**Role**: campaign_manager or admin

### GET /api/exclusions
List all exclusion entries with pagination.

**Query Params**: `page`, `page_size`
**Response**: `ExclusionListResponse`
**Role**: campaign_manager or admin

### GET /api/exclusions/{id}
Get single exclusion entry.

**Response**: `ExclusionEntryResponse`
**Role**: campaign_manager or admin

### DELETE /api/exclusions/{id}
Remove exclusion entry.

**Response**: 204 No Content
**Role**: admin only

### POST /api/exclusions/sync-contacts
Mark contacts as excluded based on exclusion list.

**Query Params**: `campaign_id` (optional)
**Response**: `{"excluded_count": int}`
**Role**: admin only

## CSV Import Format

The CSV file must have a `phone_number` or `phone` column. Optional `reason` column.

```csv
phone_number,reason
+14155551234,Customer request
+14155555678,DNC list
```

## Phone Number Normalization

Phone numbers are normalized to E.164 format:
- Removes whitespace, dashes, dots, parentheses
- Converts `00` prefix to `+`
- Validates length (7-15 digits after country code)

## Testing

### Unit Tests
```bash
pytest runs/kit/REQ-007/test/test_exclusions_unit.py -v
```

### Integration Tests
```bash
# Requires PostgreSQL database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/test \
pytest runs/kit/REQ-007/test/test_exclusions_integration.py -v
```

## Security Considerations

1. **RBAC Enforcement**: All endpoints require authentication
2. **Admin-Only Deletion**: Only admins can remove exclusions
3. **Input Validation**: Phone numbers validated before storage
4. **Audit Logging**: All operations logged with user context