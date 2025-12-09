# KIT Documentation: REQ-006 - Contact CSV Upload and Parsing

## Summary

REQ-006 implements the contact CSV upload and parsing functionality for the voicesurveyagent system. This enables campaign managers to upload contact lists via CSV files, with comprehensive validation, error reporting, and duplicate detection.

## Acceptance Criteria Status

| Criterion | Status | Notes |
|-----------|--------|-------|
| POST /api/campaigns/{id}/contacts/upload accepts multipart CSV | ✅ Implemented | Full multipart file upload support |
| Phone numbers validated against E.164 format | ✅ Implemented | Regex validation with formatting cleanup |
| Invalid rows collected with line number and error reason | ✅ Implemented | Detailed error reporting per row |
| Valid rows create Contact records in pending state | ✅ Implemented | Bulk insert with state=pending |
| At least 95% of valid rows accepted when file has mixed validity | ✅ Implemented | Tested with 95/100 valid rows |

## Architecture

### Module Structure

```
app/contacts/
├── __init__.py          # Module exports
├── models.py            # SQLAlchemy Contact model
├── schemas.py           # Pydantic schemas for API
├── repository.py        # Database operations
├── service.py           # Business logic
├── router.py            # FastAPI endpoints
└── csv_parser.py        # CSV parsing and validation
```

### Key Components

1. **CSVParser**: Handles CSV file parsing with:
   - Header normalization and alias mapping
   - E.164 phone number validation
   - Email format validation
   - Boolean and language parsing
   - Row-by-row error collection

2. **ContactService**: Business logic layer providing:
   - CSV upload processing
   - Duplicate detection (file and campaign level)
   - Paginated contact retrieval
   - Campaign status validation

3. **ContactRepository**: Database operations including:
   - Bulk contact creation
   - Paginated queries with filters
   - Phone number uniqueness checks

## API Endpoints

### POST /api/campaigns/{id}/contacts/upload

Upload a CSV file of contacts for a campaign.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: CSV file
- Query params: `delimiter` (default: `,`), `encoding` (default: `utf-8`)

**Response:**
```json
{
  "accepted_count": 95,
  "rejected_count": 5,
  "total_rows": 100,
  "acceptance_rate": 0.95,
  "errors": [
    {
      "line_number": 15,
      "field": "phone_number",
      "error": "Invalid phone number format",
      "value": "invalid_phone"
    }
  ]
}
```

### GET /api/campaigns/{id}/contacts

List contacts for a campaign with pagination.

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 50, max: 100)
- `state`: Filter by contact state

**Response:**
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 50,
  "pages": 2
}
```

### GET /api/campaigns/{id}/contacts/{contact_id}

Get details of a specific contact.

## CSV Format

### Supported Headers

| Standard Name | Aliases |
|--------------|---------|
| phone_number | phone, telephone, tel, mobile |
| external_contact_id | contact_id, ext_id, id |
| email | mail, e-mail, email_address |
| language | lang, locale, preferred_language |
| has_prior_consent | consent, prior_consent |
| do_not_call | dnc, do_not_contact |

### Validation Rules

1. **Phone Number** (required):
   - Must be E.164 format: `+` followed by 1-15 digits
   - Common formatting characters are stripped
   - Country code prefix added if missing

2. **Email** (optional):
   - RFC 5322 simplified validation
   - Normalized to lowercase

3. **Language** (optional):
   - Values: `en`, `it`, `auto` (default)
   - Case-insensitive

4. **Boolean Fields** (optional):
   - True: `true`, `1`, `yes`, `y`, `t`
   - False: anything else (default)

## Error Handling

### File-Level Errors (line_number=0)
- Empty file
- Missing required headers
- Encoding errors

### Row-Level Errors
- Invalid phone number format
- Invalid email format
- Duplicate phone in file
- Duplicate phone in campaign

## Security

- Requires `campaign_manager` or `admin` role for upload
- Campaign must be in `draft` status
- All endpoints require authentication

## Performance Considerations

- Bulk insert for valid contacts
- In-memory duplicate detection within file
- Database check for existing contacts
- Streaming CSV parsing (memory efficient)

## Dependencies

- REQ-001: Database schema
- REQ-002: Authentication
- REQ-003: RBAC
- REQ-004: Campaign CRUD
- REQ-005: Campaign validation (contact count)