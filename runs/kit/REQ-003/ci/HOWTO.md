# REQ-003: RBAC Authorization Middleware - Execution Guide

## Overview

This KIT implements Role-Based Access Control (RBAC) middleware for the Voice Survey Agent application. It provides role extraction, permission checking, and route decorators for enforcing minimum required roles on API endpoints.

## Prerequisites

### System Requirements
- Python 3.12+
- pip or poetry for dependency management

### Dependencies
The implementation depends on:
- REQ-001: Database schema (User model with role field)
- REQ-002: OIDC authentication (CurrentUser context)

## Environment Setup

### 1. Set PYTHONPATH

```bash
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src:$PYTHONPATH"
```

### 2. Environment Variables

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/voicesurvey"
export OIDC_ISSUER="https://your-idp.example.com"
export OIDC_CLIENT_ID="your-client-id"
export OIDC_CLIENT_SECRET="your-client-secret"
export JWT_SECRET_KEY="your-jwt-secret-key"
export LOG_LEVEL="INFO"
```

### 3. Install Dependencies

```bash
pip install -r runs/kit/REQ-003/requirements.txt
```

## Running Tests

### All Tests
```bash
pytest runs/kit/REQ-003/test -v
```

### With Coverage
```bash
pytest runs/kit/REQ-003/test -v --cov=runs/kit/REQ-003/src --cov-report=term-missing
```

### Specific Test Classes
```bash
# Test role hierarchy
pytest runs/kit/REQ-003/test/test_rbac.py::TestRoleLevel -v

# Test permission checks
pytest runs/kit/REQ-003/test/test_rbac.py::TestHasMinimumRole -v

# Test integration
pytest runs/kit/REQ-003/test/test_rbac.py::TestRBACIntegration -v
```

## Code Quality Checks

### Linting
```bash
ruff check runs/kit/REQ-003/src runs/kit/REQ-003/test
```

### Type Checking
```bash
mypy runs/kit/REQ-003/src --ignore-missing-imports
```

### Security Scan
```bash
bandit -r runs/kit/REQ-003/src -ll
```

## Usage Examples

### Using Role Dependencies

```python
from fastapi import APIRouter, Depends
from app.auth.rbac import require_admin, require_campaign_manager, AdminUser, CampaignManagerUser

router = APIRouter()

# Admin-only endpoint
@router.get("/admin/config")
async def get_config(user: AdminUser):
    return {"config": "..."}

# Campaign manager endpoint
@router.put("/campaigns/{id}")
async def update_campaign(id: str, user: CampaignManagerUser):
    return {"updated": id}
```

### Using Role Decorator

```python
from app.auth.rbac import rbac_decorator
from app.auth.schemas import UserRole

@router.delete("/campaigns/{id}")
@rbac_decorator(UserRole.ADMIN)
async def delete_campaign(id: str, current_user: CurrentUser):
    return {"deleted": id}
```

### Checking Permissions Programmatically

```python
from app.auth.rbac import has_minimum_role, can_modify_campaigns, is_admin
from app.auth.schemas import UserRole

# Check if user has minimum role
if has_minimum_role(user.role, UserRole.CAMPAIGN_MANAGER):
    # Allow action

# Check campaign modification permission
if can_modify_campaigns(user.role):
    # Allow campaign modification

# Check admin status
if is_admin(user.role):
    # Allow admin action
```

## Troubleshooting

### Import Errors

If you encounter import errors, ensure PYTHONPATH includes all required KIT paths:

```bash
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
```

### Test Failures

1. **Missing dependencies**: Run `pip install -r runs/kit/REQ-003/requirements.txt`
2. **Database connection**: Ensure DATABASE_URL is set correctly
3. **OIDC configuration**: Verify OIDC environment variables

### Access Denied Logging

Access denied events are logged with the following structure:
```json
{
  "event": "access_denied",
  "user_id": "uuid",
  "endpoint": "/api/path",
  "user_role": "viewer",
  "required_role": "admin",
  "timestamp": "2024-01-15T10:30:00"
}
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run RBAC Tests
  env:
    PYTHONPATH: runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src
  run: |
    pip install -r runs/kit/REQ-003/requirements.txt
    pytest runs/kit/REQ-003/test -v --junitxml=reports/junit.xml
```

### Jenkins

```groovy
stage('RBAC Tests') {
    environment {
        PYTHONPATH = "runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
    }
    steps {
        sh 'pip install -r runs/kit/REQ-003/requirements.txt'
        sh 'pytest runs/kit/REQ-003/test -v --junitxml=reports/junit.xml'
    }
}
```

## Architecture Notes

### Role Hierarchy

```
ADMIN (30) > CAMPAIGN_MANAGER (20) > VIEWER (10)
```

### Permission Matrix

| Endpoint Type | VIEWER | CAMPAIGN_MANAGER | ADMIN |
|--------------|--------|------------------|-------|
| Read campaigns | ✓ | ✓ | ✓ |
| Modify campaigns | ✗ | ✓ | ✓ |
| Admin config | ✗ | ✗ | ✓ |
| Export data | ✗ | ✓ | ✓ |