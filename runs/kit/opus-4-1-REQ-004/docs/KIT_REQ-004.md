# KIT Documentation - REQ-004: Campaign CRUD API

## Overview
REQ-004 implements the Campaign CRUD (Create, Read, Update, Delete) API endpoints for the voice survey agent system. This module provides REST APIs for managing survey campaigns with proper authentication, authorization, and state machine validation.

## Architecture

### Module Structure
```
app/campaigns/
├── __init__.py       # Module exports
├── router.py         # FastAPI route handlers
├── service.py        # Business logic layer
├── repository.py     # Database access layer
└── schemas.py        # Pydantic models for validation
```

### Design Patterns
- **Repository Pattern**: Separates data access logic from business logic
- **Service Layer**: Encapsulates business rules and orchestration
- **Dependency Injection**: Uses FastAPI's dependency system for loose coupling
- **State Machine**: Enforces valid campaign status transitions

## API Endpoints

### POST /api/campaigns
Creates a new campaign in draft status.
- **Authorization**: campaign_manager, admin
- **Returns**: Created campaign with ID

### GET /api/campaigns
Lists campaigns with pagination and filtering.
- **Authorization**: all authenticated users
- **Query params**: status, page, page_size
- **Returns**: Paginated campaign list

### GET /api/campaigns/{id}
Retrieves campaign details by ID.
- **Authorization**: all authenticated users
- **Returns**: Campaign details

### PUT /api/campaigns/{id}
Updates campaign fields (only in draft/paused status).
- **Authorization**: campaign_manager, admin
- **Returns**: Updated campaign

### POST /api/campaigns/{id}/status
Transitions campaign to new status.
- **Authorization**: campaign_manager, admin
- **Valid transitions**:
  - draft → scheduled, running, cancelled
  - scheduled → running, paused, cancelled
  - running → paused, completed, cancelled
  - paused → running, cancelled

### DELETE /api/campaigns/{id}
Soft deletes campaign (sets status to cancelled).
- **Authorization**: admin only
- **Restriction**: Cannot delete running campaigns

## State Machine

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> scheduled
    draft --> running
    draft --> cancelled
    scheduled --> running
    scheduled --> paused
    scheduled --> cancelled
    running --> paused
    running --> completed
    running --> cancelled
    paused --> running
    paused --> cancelled
    completed --> [*]
    cancelled --> [*]
```

## Database Schema

The module uses the Campaign model from REQ-001:
- **id**: UUID primary key
- **name**: Campaign name
- **status**: Enum (draft, scheduled, running, paused, completed, cancelled)
- **language**: Enum (en, it)
- **questions**: 3 required questions with types
- **retry_policy**: Max attempts, interval, time windows
- **email_templates**: References for completion/refusal/not-reached emails
- **timestamps**: created_at, updated_at

## Dependencies

### Internal Dependencies
- REQ-001: Database models and migrations
- REQ-002: OIDC authentication
- REQ-003: RBAC authorization middleware

### External Libraries
- FastAPI: Web framework
- Pydantic: Data validation
- SQLAlchemy: ORM
- pytest: Testing framework

## Testing Strategy

### Unit Tests
- **Service Layer**: Business logic validation, state transitions
- **Repository Layer**: Database operations with in-memory SQLite
- **Schema Validation**: Input/output validation

### Integration Tests
- **API Endpoints**: Full request/response cycle
- **Authentication**: JWT token validation
- **Authorization**: Role-based access control

### Test Coverage
- Target: 80% minimum
- Current focus: Happy paths and error cases
- Mocking: Database sessions, authentication

## Error Handling

### Custom Exceptions
- **NotFoundError**: Resource not found (404)
- **ValidationError**: Invalid input or state (400)
- **StateTransitionError**: Invalid status transition (400)
- **AuthorizationError**: Insufficient permissions (403)

### Error Responses
All errors return structured JSON:
```json
{
  "detail": "Error message",
  "status_code": 400
}
```

## Security Considerations

### Authentication
- JWT tokens required for all endpoints
- Token validation via middleware
- Session expiration handling

### Authorization
- Role-based access control (RBAC)
- Roles: admin, campaign_manager, viewer
- Endpoint-level permission checks

### Data Validation
- Input sanitization via Pydantic
- SQL injection prevention via ORM
- XSS prevention in text fields

## Performance Optimizations

### Database
- Indexed columns: name, status, created_by_user_id
- Pagination for list endpoints
- Selective field loading

### Caching
- Prepared for Redis integration (future)
- 60-second TTL for stats (REQ-017)

## Configuration

### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/voicesurvey
OIDC_ISSUER=https://your-idp.com
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-secret
LOG_LEVEL=INFO
```

### Deployment
- Container-ready with Dockerfile
- Kubernetes manifests for EKS
- Health check endpoints

## Future Enhancements

### Planned Features
- Bulk campaign operations
- Campaign templates
- Advanced filtering and search
- Audit trail for all changes
- Webhook notifications for status changes

### Technical Debt
- Add comprehensive logging
- Implement rate limiting
- Add metrics collection
- Enhance error messages with field-level details