# REQ-020: Call Detail View API

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL (for integration tests)
- Dependencies from REQ-001, REQ-002, REQ-003, REQ-014

### Installation

```bash
cd runs/kit/REQ-020
pip install -r requirements.txt
```

### Running Tests

```bash
# All tests
pytest -v test/

# Unit tests only
pytest -v test/test_call_detail_service.py test/test_call_models.py

# Integration tests only
pytest -v test/test_call_detail_router.py
```

### Running the API

```bash
# Development server
uvicorn app.main:app --reload --port 8000
```

## Module Overview

This module implements `GET /api/calls/{call_id}` for retrieving detailed call information.

### Features

- ✅ Call detail retrieval by call_id
- ✅ RBAC enforcement (campaign_manager/admin only)
- ✅ Transcript snippet inclusion
- ✅ Recording URL from metadata
- ✅ Proper error handling (404, 403, 401)

### Files

| File | Purpose |
|------|---------|
| `src/app/calls/models.py` | Pydantic response models |
| `src/app/calls/service.py` | Business logic |
| `src/app/calls/repository.py` | Data access layer |
| `src/app/calls/router.py` | FastAPI endpoints |
| `src/app/calls/exceptions.py` | Domain exceptions |

## API Reference

### GET /api/calls/{call_id}

Retrieve details for a specific call attempt.

**Authorization:** Requires `campaign_manager` or `admin` role.

**Response:** `CallDetailResponse` with call outcome, timestamps, transcript, and recording URL.

See `test/api/calls.json` for Postman collection.