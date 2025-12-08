# REQ-004: Campaign CRUD API

## Quick Start

### Installation
```bash
cd runs/kit/REQ-004
pip install -r requirements.txt
```

### Run Tests
```bash
pytest test/ -v
```

### Start API Server
```bash
uvicorn app.main:app --reload
```

## What This Module Does

REQ-004 provides the core Campaign management APIs for the voice survey system:

- **Create** campaigns with 3 questions and retry policies
- **List** campaigns with filtering and pagination  
- **Update** campaign configuration (when in draft/paused state)
- **Manage** campaign lifecycle through status transitions
- **Delete** campaigns (soft delete to cancelled status)

## Key Features

✅ **State Machine Validation** - Enforces valid campaign status transitions
✅ **Role-Based Access** - Different permissions for admin, manager, viewer roles
✅ **Input Validation** - Comprehensive validation of all campaign fields
✅ **Pagination** - Efficient handling of large campaign lists
✅ **Audit Trail** - Tracks who created/modified campaigns

## API Examples

### Create Campaign
```python
POST /api/campaigns
{
  "name": "Customer Satisfaction Q4",
  "language": "en",
  "intro_script": "Hello, this is a brief survey...",
  "question_1_text": "How satisfied are you?",
  "question_1_type": "scale",
  "question_2_text": "What can we improve?", 
  "question_2_type": "free_text",
  "question_3_text": "Would you recommend us?",
  "question_3_type": "scale",
  "max_attempts": 3,
  "retry_interval_minutes": 120
}
```

### Update Status
```python
POST /api/campaigns/{id}/status
{
  "status": "running"
}
```

## Integration Points

- **REQ-001**: Uses Campaign database model
- **REQ-002**: Requires JWT authentication
- **REQ-003**: Enforces RBAC permissions
- **REQ-005**: Will add validation service
- **REQ-006**: Will enable contact uploads

## Testing

The module includes comprehensive tests:
- Unit tests for service logic
- Repository tests with in-memory database
- API integration tests
- Schema validation tests

Run all tests:
```bash
pytest test/ -v --cov=app.campaigns
```

## Support

For issues or questions about this module:
1. Check the [KIT Documentation](./KIT_REQ-004.md)
2. Review test cases for usage examples
3. Contact the survey-platform-team
```

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-004**: Campaign CRUD API

### Rationale
REQ-004 was selected as it's marked as "in_progress" in the plan and depends on REQ-003 (RBAC authorization) which is also in progress. The RAG context shows that REQ-001 (database schema) and REQ-002 (OIDC authentication) are already implemented, providing the foundation needed for this REQ.

### In/Out of Scope

**In Scope:**
- Complete Campaign CRUD REST API implementation
- Service layer with business logic and state machine
- Repository layer for database operations  
- Pydantic schemas for validation
- Comprehensive test coverage
- API documentation

**Out of Scope:**
- Campaign activation logic (REQ-005)
- Contact upload functionality (REQ-006)
- Actual telephony integration
- Frontend UI components

### How to Run Tests

```bash
# From project root
cd runs/kit/REQ-004

# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest test/ -v

# Run specific test files
pytest test/test_campaign_service.py -v
pytest test/test_campaign_repository.py -v
pytest test/test_campaign_crud.py -v

# With coverage
pytest test/ --cov=app.campaigns --cov-report=term-missing
```

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ (or SQLite for testing)
- Dependencies from REQ-001, REQ-002, REQ-003
- Set PYTHONPATH to include src directories from dependent REQs

### Dependencies and Mocks
- **Mocked**: Database sessions in API tests, authentication in unit tests
- **Real**: SQLAlchemy models, Pydantic validation, business logic
- **Test DB**: Uses in-memory SQLite for repository tests

### Product Owner Notes
The implementation follows the state machine design from the SPEC, ensuring campaigns can only transition between valid states. The API enforces role-based permissions where:
- Viewers can only read campaigns
- Campaign managers can create and modify campaigns
- Only admins can delete campaigns

The soft delete approach (setting status to cancelled) preserves audit trail and historical data as required for compliance.

### RAG Citations
- Used Campaign model structure from `runs/kit/REQ-001/src/app/shared/models/campaign.py`
- Referenced enum definitions from `runs/kit/REQ-001/src/app/shared/models/enums.py`
- Followed authentication patterns from `runs/kit/REQ-002/src/app/auth/`
- Aligned with database schema from `runs/kit/REQ-001/src/storage/sql/V0001.up.sql`