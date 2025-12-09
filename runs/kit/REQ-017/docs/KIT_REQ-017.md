# KIT Documentation — REQ-017: Campaign Dashboard Stats API

## Overview

REQ-017 implements the campaign dashboard statistics API, providing aggregate metrics for campaign monitoring and reporting. The API returns contact state distributions, call outcome counts, completion rates, call duration statistics, and time series data.

## Architecture

### Components

1. **DashboardService** (`app/dashboard/service.py`)
   - Orchestrates stats computation and caching
   - Calculates completion and conversion rates
   - Manages cache invalidation

2. **DashboardRepository** (`app/dashboard/repository.py`)
   - Executes optimized SQL queries for aggregations
   - Handles time series data generation
   - Provides contact and call outcome counts

3. **Router** (`app/dashboard/router.py`)
   - Exposes REST API endpoints
   - Handles authentication and authorization
   - Validates request parameters

4. **Cache** (`app/shared/cache.py`)
   - Redis-based caching with 60-second TTL
   - JSON serialization for complex objects
   - Graceful degradation on cache failures

### Data Flow

```
Request → Router → Auth Middleware → Service → Cache Check
                                         ↓
                                    Cache Miss
                                         ↓
                                    Repository → Database
                                         ↓
                                    Compute Stats
                                         ↓
                                    Store in Cache
                                         ↓
                                    Return Response
```

## API Endpoints

### GET /api/campaigns/{campaign_id}/stats

Returns aggregate statistics for a campaign.

**Parameters:**
- `campaign_id` (path): UUID of the campaign
- `include_time_series` (query, default=true): Include hourly/daily time series
- `time_series_hours` (query, default=24): Hours of hourly data (1-168)
- `time_series_days` (query, default=30): Days of daily data (1-90)

**Response:**
```json
{
  "campaign_id": "uuid",
  "campaign_name": "string",
  "campaign_status": "running",
  "contacts": {
    "total": 100,
    "pending": 20,
    "in_progress": 5,
    "completed": 50,
    "refused": 10,
    "not_reached": 10,
    "excluded": 5
  },
  "call_outcomes": {
    "total_attempts": 150,
    "completed": 50,
    "refused": 10,
    "no_answer": 60,
    "busy": 20,
    "failed": 10
  },
  "rates": {
    "completion_rate": 50.0,
    "refusal_rate": 10.0,
    "not_reached_rate": 10.0,
    "answer_rate": 40.0
  },
  "duration_stats": {
    "average_duration_seconds": 120.5,
    "min_duration_seconds": 30.0,
    "max_duration_seconds": 300.0,
    "total_duration_seconds": 6025.0
  },
  "time_series_hourly": [...],
  "time_series_daily": [...],
  "generated_at": "2024-01-15T10:30:00Z",
  "cached": false
}
```

**Authorization:** Requires `admin`, `campaign_manager`, or `viewer` role.

### POST /api/campaigns/{campaign_id}/stats/invalidate

Invalidates cached statistics for a campaign.

**Authorization:** Requires `admin` role only.

## Performance

### Caching Strategy

- Stats are cached in Redis with 60-second TTL
- Cache key format: `campaign_stats:{campaign_id}`
- Cache miss triggers fresh computation
- Graceful degradation if Redis unavailable

### Query Optimization

- Indexed columns used for filtering (campaign_id, state, outcome)
- Aggregate queries use GROUP BY for efficient counting
- Time series uses PostgreSQL `date_trunc` for bucketing
- Response time target: <500ms for 10k contacts

## Dependencies

### From Previous REQs

- **REQ-001**: Database schema (Campaign, Contact, CallAttempt models)
- **REQ-002**: OIDC authentication
- **REQ-003**: RBAC authorization
- **REQ-014**: Survey response persistence

### External Dependencies

- PostgreSQL with asyncpg driver
- Redis for caching
- python-jose for JWT validation

## Testing

### Unit Tests

- `test_dashboard_service.py`: Service logic and caching
- `test_dashboard_repository.py`: Database queries
- `test_schemas.py`: Pydantic model validation

### Integration Tests

- `test_dashboard_api.py`: Full API endpoint testing

### Running Tests

```bash
cd runs/kit/REQ-017
pip install -r requirements.txt
pytest -v test/
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql://... | PostgreSQL connection URL |
| REDIS_URL | redis://localhost:6379/0 | Redis connection URL |
| STATS_CACHE_TTL_SECONDS | 60 | Cache TTL in seconds |
| JWT_SECRET_KEY | dev-secret-key | JWT validation secret |
| LOG_LEVEL | INFO | Logging level |