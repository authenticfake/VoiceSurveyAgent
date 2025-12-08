# REQ-003: RBAC Authorization Middleware — Execution Guide

## Overview

This KIT implements Role-Based Access Control (RBAC) authorization middleware for the Voice Survey Agent application. It provides:

- Role extraction from JWT claims or database records
- Route decorators for enforcing minimum required roles
- Permission-based access control
- Access denied logging with user ID, endpoint, and timestamp

## Prerequisites

### System Requirements
- Python 3.12+
- PostgreSQL 15+ (for integration tests)
- pip or Poetry for dependency management

### Dependencies
The following packages are required (see `requirements.txt`):
- fastapi>=0.111.0
- pydantic>=2.7.0
- pytest>=8.0.0
- pytest-asyncio>=0.23.0
- httpx>=0.27.0
- ruff>=0.4.0
- mypy>=1.10.0
- bandit>=1.7.0

## Environment Setup

### 1. Set Environment Variables

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/voicesurvey_test"
export OIDC_ISSUER="https://test-idp.example.com"
export OIDC_CLIENT_ID="test-client-id"
export OIDC_CLIENT_SECRET="test-client-secret"
export JWT_SECRET_KEY="test-secret-key-for-jwt-signing"
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
```

### 2. Install Dependencies

```bash
cd runs/kit/REQ-003
pip install -r requirements.txt
```

## Running Tests

### All Tests
```bash
cd runs/kit/REQ-003
pytest test/ -v --tb=short
```

### Specific Test Files
```bash
# RBAC unit tests
pytest test/test_rbac.py -v

# Integration tests
pytest test/test_rbac_integration.py -v
```

### With Coverage
```bash
pytest test/ -v --cov=src --cov-report=term-missing --cov-report=xml:reports/coverage.xml
```

## Quality Checks

### Linting
```bash
cd runs/kit/REQ-003
ruff check src test
```

### Type Checking
```bash
cd runs/kit/REQ-003
mypy src --ignore-missing-imports
```

### Security Scan
```bash
cd runs/kit/REQ-003
bandit -r src -ll
```

## Usage Examples

### Using Role Decorators

```python
from fastapi import APIRouter, Depends
from app.auth.rbac import require_role, AdminUser, CampaignManagerUser
from app.auth.schemas import UserRole

router = APIRouter()

# Require admin role
@router.get("/api/admin/config")
async def get_config(user: AdminUser):
    return {"config": "admin_data"}

# Require campaign_manager role (or higher)
@router.post("/api/campaigns")
async def create_campaign(user: CampaignManagerUser):
    return {"id": "new-campaign"}

# Using require_role directly
@router.put("/api/campaigns/{id}")
async def update_campaign(
    id: str,
    user = Depends(require_role(UserRole.CAMPAIGN_MANAGER))
):
    return {"updated": id}
```

### Using Permission Decorators

```python
from app.auth.rbac import require_permission, Permission

@router.delete("/api/exclusions/{id}")
async def delete_exclusion(
    id: str,
    user = Depends(require_permission(Permission.ADMIN_EXCLUSION_MANAGE))
):
    return {"deleted": id}
```

## Role Hierarchy

| Role | Level | Permissions |
|------|-------|-------------|
| admin | 3 | All permissions |
| campaign_manager | 2 | Campaign CRUD, Contact management, Stats |
| viewer | 1 | Read-only access |

## Troubleshooting

### Import Errors
Ensure PYTHONPATH includes all required KIT source directories:
```bash
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
```

### Test Database Connection
For integration tests requiring database:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/voicesurvey_test"
```

### Missing Dependencies
If tests fail due to missing packages:
```bash
pip install -r runs/kit/REQ-003/requirements.txt
```

## CI/CD Integration

### GitHub Actions
The LTC.json file defines the test contract for CI:
- Install dependencies
- Run linting
- Run type checking
- Run tests
- Run security scan

### Jenkins Pipeline
```groovy
stage('RBAC Tests') {
    steps {
        sh 'cd runs/kit/REQ-003 && pip install -r requirements.txt'
        sh 'cd runs/kit/REQ-003 && pytest test/ -v --junitxml=reports/junit.xml'
    }
}
```

## Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Source | `runs/kit/REQ-003/src/app/auth/rbac.py` | RBAC implementation |
| Tests | `runs/kit/REQ-003/test/` | Test files |
| JUnit Report | `runs/kit/REQ-003/reports/junit.xml` | Test results |
| Coverage | `runs/kit/REQ-003/reports/coverage.xml` | Coverage report |