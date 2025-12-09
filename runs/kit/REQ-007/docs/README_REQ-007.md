# REQ-007: Exclusion List Management

## Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ with database from REQ-001
- Dependencies from REQ-002, REQ-003, REQ-006

### Installation

```bash
cd runs/kit/REQ-007
pip install -r requirements.txt
```

### Running Tests

```bash
# Unit tests (no database required)
pytest test/test_exclusions_unit.py -v

# Integration tests (requires database)
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey_test
pytest test/test_exclusions_integration.py -v

# All tests with coverage
pytest test/ --cov=src/app/contacts/exclusions --cov-report=term-missing
```

### API Usage Examples

#### Import CSV
```bash
curl -X POST "http://localhost:8000/api/exclusions/import" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@exclusions.csv"
```

#### Add Single Exclusion
```bash
curl -X POST "http://localhost:8000/api/exclusions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+14155551234", "reason": "Customer request"}'
```

#### List Exclusions
```bash
curl "http://localhost:8000/api/exclusions?page=1&page_size=50" \
  -H "Authorization: Bearer $TOKEN"
```

#### Delete Exclusion (Admin Only)
```bash
curl -X DELETE "http://localhost:8000/api/exclusions/{id}" \
  -H "Authorization: Bearer $TOKEN"
```

## Module Integration

To integrate with the main application:

```python
from fastapi import FastAPI
from app.contacts.exclusions import router as exclusions_router

app = FastAPI()
app.include_router(exclusions_router)
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | Required |
| LOG_LEVEL | Logging level | INFO |