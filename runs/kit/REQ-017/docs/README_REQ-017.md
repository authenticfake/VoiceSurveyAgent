# REQ-017: Campaign Dashboard Stats API

## Summary

This module implements the campaign dashboard statistics API for the VoiceSurveyAgent system. It provides aggregate metrics including contact state distributions, call outcome counts, completion rates, and time series data for campaign monitoring.

## Features

- **Contact State Metrics**: Total, pending, in_progress, completed, refused, not_reached, excluded counts
- **Call Outcome Metrics**: Total attempts, completed, refused, no_answer, busy, failed counts
- **Completion Rates**: Completion rate, refusal rate, not_reached rate, answer rate
- **Duration Statistics**: Average, min, max, and total call duration
- **Time Series Data**: Hourly (last 24h) and daily (last 30d) call activity
- **Caching**: 60-second TTL Redis caching for performance
- **RBAC**: Role-based access control (admin, campaign_manager, viewer)

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Redis 7+

### Installation

```bash
cd runs/kit/REQ-017
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/voicesurvey
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret-key
```

### Running

```bash
uvicorn app.main:app --reload
```

### API Usage

```bash
# Get campaign stats
curl -X GET "http://localhost:8000/api/campaigns/{campaign_id}/stats" \
  -H "Authorization: Bearer {token}"

# Get stats without time series
curl -X GET "http://localhost:8000/api/campaigns/{campaign_id}/stats?include_time_series=false" \
  -H "Authorization: Bearer {token}"

# Invalidate cache (admin only)
curl -X POST "http://localhost:8000/api/campaigns/{campaign_id}/stats/invalidate" \
  -H "Authorization: Bearer {token}"
```

## Testing

```bash
# Run all tests
pytest -v test/

# Run with coverage
pytest --cov=app --cov-report=html test/
```

## Acceptance Criteria

- [x] GET /api/campaigns/{id}/stats returns aggregate metrics
- [x] Metrics include total, completed, refused, not_reached counts
- [x] Time-series data for calls per hour/day
- [x] Stats cached with 60-second TTL
- [x] Response time under 500ms for campaigns with 10k contacts (via caching)

## Module Structure

```
runs/kit/REQ-017/
├── src/
│   └── app/
│       ├── dashboard/
│       │   ├── __init__.py
│       │   ├── models.py      # SQLAlchemy models
│       │   ├── schemas.py     # Pydantic schemas
│       │   ├── repository.py  # Database queries
│       │   ├── service.py     # Business logic
│       │   └── router.py      # API endpoints
│       ├── shared/
│       │   ├── __init__.py
│       │   ├── auth.py        # Authentication
│       │   ├── cache.py       # Redis caching
│       │   ├── config.py      # Configuration
│       │   └── database.py    # Database setup
│       ├── __init__.py
│       └── main.py            # FastAPI app
├── test/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_dashboard_api.py
│   ├── test_dashboard_repository.py
│   ├── test_dashboard_service.py
│   └── test_schemas.py
├── docs/
│   ├── KIT_REQ-017.md
│   └── README_REQ-017.md
├── ci/
│   ├── LTC.json
│   └── HOWTO.md
└── requirements.txt