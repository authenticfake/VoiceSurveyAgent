# REQ-006: Contact CSV Upload and Parsing

## Overview

This module provides CSV upload functionality for campaign contacts in the voicesurveyagent system. Campaign managers can upload contact lists with phone numbers, emails, and metadata, which are validated and stored for outbound calling campaigns.

## Features

- **CSV File Upload**: Multipart file upload with configurable delimiter and encoding
- **Phone Validation**: E.164 format validation with automatic formatting cleanup
- **Email Validation**: RFC-compliant email format checking
- **Flexible Headers**: Support for header aliases (e.g., "phone" → "phone_number")
- **Error Reporting**: Detailed per-row error messages with line numbers
- **Duplicate Detection**: Prevents duplicates within file and across campaign
- **Bulk Processing**: Efficient bulk insert for valid contacts
- **Pagination**: Paginated contact listing with state filtering

## Quick Start

### Upload Contacts

```python
import httpx

async with httpx.AsyncClient() as client:
    with open("contacts.csv", "rb") as f:
        response = await client.post(
            "http://localhost:8080/api/campaigns/{campaign_id}/contacts/upload",
            files={"file": ("contacts.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {token}"},
        )
    print(response.json())
```

### CSV Format

```csv
phone_number,email,external_contact_id,language,has_prior_consent,do_not_call
+14155551234,test@example.com,EXT001,en,true,false
+14155551235,test2@example.com,EXT002,it,false,false
```

## API Reference

See [KIT_REQ-006.md](./KIT_REQ-006.md) for detailed API documentation.

## Testing

```bash
# Run all tests
pytest runs/kit/REQ-006/test/ -v

# Run with coverage
pytest runs/kit/REQ-006/test/ -v --cov=app.contacts --cov-report=term-missing
```

## Module Structure

```
app/contacts/
├── __init__.py      # Module exports
├── models.py        # Contact SQLAlchemy model
├── schemas.py       # Pydantic request/response schemas
├── repository.py    # Database operations
├── service.py       # Business logic
├── router.py        # FastAPI endpoints
└── csv_parser.py    # CSV parsing and validation