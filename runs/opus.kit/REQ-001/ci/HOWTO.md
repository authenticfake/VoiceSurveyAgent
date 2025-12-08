# REQ-001: OIDC Auth and RBAC - Execution Guide

## Overview

This REQ implements OIDC-based authentication and role-based access control (RBAC) for the Voice Survey Agent backend APIs.

## Prerequisites

### System Requirements
- Python 3.12+
- pip (latest version recommended)

### Environment Variables

```bash
# Required for production
export OIDC_ISSUER="https://your-idp.example.com/"
export OIDC_CLIENT_ID="your-client-id"
export OIDC_CLIENT_SECRET="your-client-secret"
export OIDC_REDIRECT_URI="http://localhost:8000/api/auth/callback"

# Optional
export CORS_ORIGINS="http://localhost:3000,http://localhost:8000"
export SKIP_OIDC_DISCOVERY="false"  # Set to "true" for testing without IdP
```

## Local Development Setup

### 1. Create Virtual Environment

```bash
cd runs/kit/REQ-001
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set PYTHONPATH

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### 4. Run Tests

```bash
# All tests
pytest test -v

# With coverage
pytest test -v --cov=app --cov-report=html

# Specific test file
pytest test/auth/test_domain.py -v
```

### 5. Run Application

```bash
# Development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Test Execution

### Unit Tests
```bash
pytest test/auth/test_domain.py -v
pytest test/auth/test_repository.py -v
pytest test/auth/test_service.py -v
```

### Integration Tests
```bash
pytest test/api/test_auth_routes.py -v
```

### Full Test Suite with Coverage
```bash
pytest test -v --cov=app --cov-report=xml:reports/coverage.xml --junitxml=reports/junit.xml
```

## CI/CD Integration

### GitHub Actions

The LTC.json file defines the test cases for CI execution:

```yaml
- name: Run REQ-001 Tests
  env:
    PYTHONPATH: runs/kit/REQ-001/src
    SKIP_OIDC_DISCOVERY: "true"
  run: |
    pip install -r runs/kit/REQ-001/requirements.txt
    pytest runs/kit/REQ-001/test -v --cov=app
```

### Jenkins Pipeline

```groovy
stage('REQ-001 Tests') {
    environment {
        PYTHONPATH = "runs/kit/REQ-001/src"
        SKIP_OIDC_DISCOVERY = "true"
    }
    steps {
        sh 'pip install -r runs/kit/REQ-001/requirements.txt'
        sh 'pytest runs/kit/REQ-001/test -v --junitxml=reports/junit.xml'
    }
    post {
        always {
            junit 'reports/junit.xml'
        }
    }
}
```

## API Endpoints

### Authentication Endpoints

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/api/auth/login` | Initiate OIDC login | No |
| POST | `/api/auth/callback` | Handle OAuth callback | No |
| GET | `/api/auth/callback` | Handle OAuth callback (GET) | No |
| GET | `/api/auth/me` | Get current user | Yes |
| POST | `/api/auth/logout` | Logout user | Yes |

### Protected Endpoints (RBAC Demo)

| Method | Path | Required Role |
|--------|------|---------------|
| GET | `/api/protected/viewer-resource` | viewer, campaign_manager, admin |
| GET | `/api/protected/writer-resource` | campaign_manager, admin |
| GET | `/api/protected/admin-resource` | admin |
| GET | `/api/protected/my-permissions` | Any authenticated |

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure PYTHONPATH includes `runs/kit/REQ-001/src`
   - Verify virtual environment is activated

2. **OIDC Discovery Fails**
   - Set `SKIP_OIDC_DISCOVERY=true` for local testing
   - Verify OIDC_ISSUER URL is accessible

3. **Token Validation Errors**
   - Check OIDC_CLIENT_ID matches your IdP configuration
   - Verify token hasn't expired

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload --log-level debug
```

## Reports Location

After test execution:
- JUnit XML: `runs/kit/REQ-001/reports/junit.xml`
- Coverage XML: `runs/kit/REQ-001/reports/coverage.xml`
- Coverage HTML: `runs/kit/REQ-001/htmlcov/index.html`

## Integration with Other REQs

This REQ provides reusable auth dependencies for other REQs:

```python
from app.auth.dependencies import (
    get_current_user,
    require_role,
    RequireAdmin,
    RequireWriter,
    RequireReader,
)
from app.auth.domain import User, UserRole
```

Other REQs should import these dependencies to enforce authentication and authorization on their endpoints.