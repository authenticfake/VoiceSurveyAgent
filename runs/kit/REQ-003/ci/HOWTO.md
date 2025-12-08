# HOWTO: REQ-003 RBAC Authorization Middleware

## Prerequisites

- Python 3.12+
- pip
- pytest

## Environment Setup

### 1. Create Virtual Environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
```

### 2. Install Dependencies

```bash
pip install -r runs/kit/REQ-003/requirements.txt
```

### 3. Set PYTHONPATH

The RBAC module depends on code from REQ-001 and REQ-002. Set PYTHONPATH to include all source directories:

```bash
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
```

Or on Windows:
```cmd
set PYTHONPATH=runs/kit/REQ-003/src;runs/kit/REQ-002/src;runs/kit/REQ-001/src
```

### 4. Environment Variables

Configure RBAC behavior via environment variables:

```bash
export RBAC_LOG_DENIALS=true
export RBAC_ADMIN_PATHS=/api/admin
export RBAC_MANAGER_PATHS=/api/campaigns
export RBAC_LOG_REQUEST_DETAILS=true
```

## Running Tests

### Run All Tests

```bash
pytest runs/kit/REQ-003/test/ -v
```

### Run Specific Test Files

```bash
# Role tests
pytest runs/kit/REQ-003/test/test_rbac_roles.py -v

# Permission tests
pytest runs/kit/REQ-003/test/test_rbac_permissions.py -v

# Logging tests
pytest runs/kit/REQ-003/test/test_rbac_logging.py -v

# Config tests
pytest runs/kit/REQ-003/test/test_rbac_config.py -v

# Integration tests
pytest runs/kit/REQ-003/test/test_rbac_integration.py -v
```

### Run with Coverage

```bash
pytest runs/kit/REQ-003/test/ -v \
  --cov=runs/kit/REQ-003/src \
  --cov-report=html:runs/kit/REQ-003/reports/htmlcov \
  --cov-report=xml:runs/kit/REQ-003/reports/coverage.xml
```

### Generate JUnit Report

```bash
pytest runs/kit/REQ-003/test/ -v \
  --junitxml=runs/kit/REQ-003/reports/junit.xml
```

## Linting and Type Checking

### Lint with Ruff

```bash
pip install ruff
ruff check runs/kit/REQ-003/src
```

### Type Check with MyPy

```bash
pip install mypy
mypy runs/kit/REQ-003/src
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'app'`:

1. Ensure PYTHONPATH is set correctly
2. Verify all dependency KITs (REQ-001, REQ-002) are present
3. Check that `__init__.py` files exist in all package directories

### Test Failures

If tests fail with authentication errors:

1. The integration tests use a mock auth middleware
2. Ensure the test fixtures are properly creating mock users
3. Check that the `x-test-role` header is being set correctly

### Logging Issues

If access denial logs are not appearing:

1. Check `RBAC_LOG_DENIALS` environment variable is `true`
2. Verify logging is configured at WARNING level or lower
3. Check that the logger `voicesurveyagent.rbac.access` is not filtered

## CI/CD Integration

### Jenkins Pipeline

```groovy
stage('Test REQ-003') {
    steps {
        sh '''
            export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
            pip install -r runs/kit/REQ-003/requirements.txt
            pytest runs/kit/REQ-003/test/ -v --junitxml=reports/junit.xml
        '''
    }
    post {
        always {
            junit 'reports/junit.xml'
        }
    }
}
```

### GitHub Actions

```yaml
- name: Test REQ-003
  env:
    PYTHONPATH: runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src
  run: |
    pip install -r runs/kit/REQ-003/requirements.txt
    pytest runs/kit/REQ-003/test/ -v --junitxml=reports/junit.xml
```

## Artifacts

After running tests, find reports at:

- JUnit XML: `runs/kit/REQ-003/reports/junit.xml`
- Coverage XML: `runs/kit/REQ-003/reports/coverage.xml`
- Coverage HTML: `runs/kit/REQ-003/reports/htmlcov/index.html`
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-003**: RBAC authorization middleware

### Rationale
REQ-003 depends on REQ-002 (OIDC authentication) which is marked as `in_progress`. The RBAC module extends the authentication system by adding role-based access control on top of the JWT validation middleware.

### In Scope
- Role enum with three tiers: `admin`, `campaign_manager`, `viewer`
- Role hierarchy with privilege levels
- Permission definitions per role
- FastAPI dependency decorators: `require_role`, `require_any_role`, `require_permission`
- Access denial logging with structured JSON format
- Configuration via environment variables
- Unit tests for all components
- Integration tests with FastAPI test client

### Out of Scope
- Database persistence of access denial logs (handled by external logging infrastructure)
- Dynamic permission management via API (permissions are code-defined)
- Multi-tenant role isolation (single-tenant per SPEC)

### How to Run Tests

```bash
# Set PYTHONPATH to include all required source directories
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"

# Install dependencies
pip install -r runs/kit/REQ-003/requirements.txt

# Run all tests
pytest runs/kit/REQ-003/test/ -v

# Run with coverage
pytest runs/kit/REQ-003/test/ -v --cov=runs/kit/REQ-003/src --cov-report=term-missing
```

### Prerequisites
- Python 3.12+
- pytest, pytest-asyncio, httpx
- FastAPI, Pydantic
- REQ-001 and REQ-002 source code available in PYTHONPATH

### Dependencies and Mocks
- **REQ-001**: Uses User model definition (role field)
- **REQ-002**: Uses JWT validation middleware and request.state.user pattern
- **Mocks**: Tests use MockUser class and mock FastAPI Request objects to simulate authenticated requests without requiring actual OIDC flow

### Product Owner Notes
- Role hierarchy follows SPEC: admin > campaign_manager > viewer
- Permissions are granular (e.g., `campaigns:create`, `config:update`) for future flexibility
- Access denial logging includes correlation ID for distributed tracing integration
- Configuration is environment-driven per TECH_CONSTRAINTS

### RAG Citations
- REQ-001 schema: Used User model with role field as enum
- REQ-002 auth: Followed pattern of setting request.state.user and request.state.jwt_claims
- PLAN.md: Confirmed RBAC module path as `app.auth.rbac` extending `app.auth`
- SPEC.md: Referenced RBAC roles (admin, campaign_manager, viewer) and endpoint restrictions

```json
{
  "index": [
    {
      "req": "REQ-003",
      "src": [
        "runs/kit/REQ-003/src/app/auth/rbac/__init__.py",
        "runs/kit/REQ-003/src/app/auth/rbac/roles.py",
        "runs/kit/REQ-003/src/app/auth/rbac/permissions.py",
        "runs/kit/REQ-003/src/app/auth/rbac/logging.py",
        "runs/kit/REQ-003/src/app/auth/rbac/config.py"
      ],
      "tests": [
        "runs/kit/REQ-003/test/test_rbac_roles.py",
        "runs/kit/REQ-003/test/test_rbac_permissions.py",
        "runs/kit/REQ-003/test/test_rbac_logging.py",
        "runs/kit/REQ-003/test/test_rbac_config.py",
        "runs/kit/REQ-003/test/test_rbac_integration.py"
      ]
    }
  ]
}