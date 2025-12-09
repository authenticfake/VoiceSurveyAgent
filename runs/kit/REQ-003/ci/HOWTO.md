# REQ-003: RBAC Authorization Middleware - Execution Guide

## Overview

This document provides instructions for running and testing the RBAC authorization middleware implementation for the VoiceSurveyAgent project.

## Prerequisites

### Required Software
- Python 3.12+
- pip or Poetry for dependency management
- PostgreSQL 15+ (for integration tests, optional)

### Environment Variables

Set the following environment variables before running:

```bash
export DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test"
export JWT_SECRET_KEY="test-secret-key-for-testing-purposes-only"
export JWT_ALGORITHM="HS256"
export JWT_ACCESS_TOKEN_EXPIRE_MINUTES="30"
export JWT_REFRESH_TOKEN_EXPIRE_DAYS="7"
export OIDC_CLIENT_ID="test-client"
export OIDC_CLIENT_SECRET="test-secret"
export OIDC_ISSUER_URL="https://test-idp.example.com"
export OIDC_REDIRECT_URI="http://localhost:8000/api/auth/callback"
```

### Python Path Configuration

The RBAC module depends on code from REQ-001 and REQ-002. Set PYTHONPATH:

```bash
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
```

## Installation

### Using pip

```bash
# Install dependencies
pip install -r runs/kit/REQ-003/requirements.txt
```

### Using Poetry (if available)

```bash
cd runs/kit/REQ-003
poetry install
```

## Running Tests

### All Tests

```bash
# From project root
PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src" \
pytest runs/kit/REQ-003/test -v
```

### With Coverage

```bash
PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src" \
pytest runs/kit/REQ-003/test \
  --cov=runs/kit/REQ-003/src \
  --cov-report=term-missing \
  --cov-report=xml:runs/kit/REQ-003/reports/coverage.xml \
  --junitxml=runs/kit/REQ-003/reports/junit.xml
```

### Specific Test Classes

```bash
# Test Role enum
pytest runs/kit/REQ-003/test/test_rbac.py::TestRoleEnum -v

# Test RBAC checker integration
pytest runs/kit/REQ-003/test/test_rbac.py::TestRBACCheckerIntegration -v

# Test permissions configuration
pytest runs/kit/REQ-003/test/test_rbac.py::TestRolePermissions -v
```

## Linting and Type Checking

### Ruff Linting

```bash
ruff check runs/kit/REQ-003/src runs/kit/REQ-003/test
```

### MyPy Type Checking

```bash
PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src" \
mypy runs/kit/REQ-003/src --ignore-missing-imports
```

## Usage Examples

### Using RBAC Decorators in Routes

```python
from fastapi import APIRouter, Depends
from app.auth.rbac import require_admin, require_campaign_manager, require_viewer
from app.auth.middleware import CurrentUser

router = APIRouter()

# Admin-only endpoint
@router.get("/admin/config")
async def get_admin_config(
    user: CurrentUser = Depends(require_admin),
):
    return {"config": "admin-only-data"}

# Campaign manager or admin
@router.post("/campaigns")
async def create_campaign(
    user: CurrentUser = Depends(require_campaign_manager),
):
    return {"message": "Campaign created"}

# Any authenticated user
@router.get("/campaigns")
async def list_campaigns(
    user: CurrentUser = Depends(require_viewer),
):
    return {"campaigns": []}
```

### Custom Role Requirements

```python
from app.auth.rbac import require_role, Role

@router.delete("/campaigns/{id}")
async def delete_campaign(
    id: str,
    user: CurrentUser = Depends(require_role(Role.CAMPAIGN_MANAGER)),
):
    return {"deleted": id}
```

### Checking Permissions Programmatically

```python
from app.auth.rbac import RolePermissions, check_role_permission, Role

# Check if user can create campaigns
if RolePermissions.can_perform(user.role, RolePermissions.CAMPAIGN_CREATE):
    # Allow operation
    pass

# Check role hierarchy
if check_role_permission(user.role, Role.CAMPAIGN_MANAGER):
    # User has campaign_manager or higher role
    pass
```

## Artifacts

After running tests with coverage, the following artifacts are generated:

| Artifact | Path | Description |
|----------|------|-------------|
| JUnit XML | `runs/kit/REQ-003/reports/junit.xml` | Test results in JUnit format |
| Coverage XML | `runs/kit/REQ-003/reports/coverage.xml` | Coverage report in Cobertura format |

## Troubleshooting

### Import Errors

If you encounter import errors like `ModuleNotFoundError: No module named 'app'`:

1. Ensure PYTHONPATH includes all required kit directories
2. Verify the directory structure matches expected paths
3. Check that `__init__.py` files exist in all package directories

### Database Connection Issues

For tests that require database access:

1. Ensure PostgreSQL is running
2. Verify DATABASE_URL is correctly set
3. Tests use mocks by default; real DB is only needed for integration tests

### JWT Validation Failures

If JWT validation fails in tests:

1. Ensure JWT_SECRET_KEY matches between token creation and validation
2. Check that token expiration times are set correctly
3. Verify JWT_ALGORITHM is consistent

## CI/CD Integration

### GitHub Actions

The LTC.json file defines test cases compatible with GitHub Actions:

```yaml
- name: Run RBAC Tests
  env:
    PYTHONPATH: "runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
  run: |
    pip install -r runs/kit/REQ-003/requirements.txt
    pytest runs/kit/REQ-003/test -v --junitxml=reports/junit.xml
```

### Jenkins

```groovy
stage('RBAC Tests') {
    steps {
        sh '''
            export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
            pip install -r runs/kit/REQ-003/requirements.txt
            pytest runs/kit/REQ-003/test -v --junitxml=reports/junit.xml
        '''
    }
    post {
        always {
            junit 'reports/junit.xml'
        }
    }
}