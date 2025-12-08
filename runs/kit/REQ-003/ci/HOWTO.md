# HOWTO — REQ-003: RBAC Authorization Middleware

## Prerequisites

- Python 3.12+
- pip or poetry
- REQ-001 and REQ-002 implementations available

## Environment Setup

### Option 1: Using PYTHONPATH (Recommended for Development)

```bash
# Set PYTHONPATH to include all required KIT sources
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src:$PYTHONPATH"

# Verify imports work
python -c "from app.auth.rbac import RBACChecker; print('OK')"
```

### Option 2: Editable Install

```bash
# If using a unified pyproject.toml
pip install -e .
```

## Running Tests

### Local Execution

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx fastapi pydantic

# Run all tests
pytest runs/kit/REQ-003/test/test_rbac.py -v

# Run with coverage
pytest runs/kit/REQ-003/test/test_rbac.py \
  --cov=runs/kit/REQ-003/src \
  --cov-report=term-missing \
  --cov-fail-under=80

# Run specific test class
pytest runs/kit/REQ-003/test/test_rbac.py::TestRBACChecker -v
```

### Using LTC Cases

```bash
# Install dependencies (case: install_deps)
pip install pytest pytest-asyncio pytest-cov httpx fastapi pydantic

# Run tests (case: tests)
pytest runs/kit/REQ-003/test/test_rbac.py -v --tb=short

# Run with coverage reports (case: tests_with_coverage)
pytest runs/kit/REQ-003/test/test_rbac.py \
  --cov=runs/kit/REQ-003/src \
  --cov-report=xml:runs/kit/REQ-003/reports/coverage.xml \
  --junitxml=runs/kit/REQ-003/reports/junit.xml
```

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run REQ-003 Tests
  env:
    PYTHONPATH: runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src
  run: |
    pip install pytest pytest-asyncio pytest-cov httpx fastapi pydantic
    pytest runs/kit/REQ-003/test/test_rbac.py \
      --cov=runs/kit/REQ-003/src \
      --cov-report=xml \
      --junitxml=test-results.xml
```

### Jenkins

```groovy
stage('REQ-003 Tests') {
    environment {
        PYTHONPATH = "runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
    }
    steps {
        sh 'pip install pytest pytest-asyncio pytest-cov httpx fastapi pydantic'
        sh 'pytest runs/kit/REQ-003/test/test_rbac.py --junitxml=test-results.xml'
    }
    post {
        always {
            junit 'test-results.xml'
        }
    }
}
```

## Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| JUnit XML | `runs/kit/REQ-003/reports/junit.xml` | Test results |
| Coverage XML | `runs/kit/REQ-003/reports/coverage.xml` | Coverage report |

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'app'`

**Solution**: Ensure PYTHONPATH includes all required KIT source directories:
```bash
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"
```

### Missing Dependencies

**Problem**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**: Install test dependencies:
```bash
pip install pytest pytest-asyncio pytest-cov httpx fastapi pydantic
```

### Test Failures

**Problem**: Tests fail with authentication errors

**Solution**: Ensure REQ-002 auth middleware is properly mocked in tests. The test suite uses `MockUser` objects that don't require actual OIDC configuration.
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-003**: RBAC authorization middleware

### Rationale
REQ-003 depends on REQ-002 (OIDC authentication) which provides the user context. This implementation builds on the auth module structure established in REQ-002.

### In Scope
- Role-permission mapping (admin, campaign_manager, viewer)
- Permission checking functions
- FastAPI dependency-based route protection
- Decorator-based RBAC for service methods
- Access denial logging with user ID, endpoint, and timestamp
- Comprehensive test coverage

### Out of Scope
- Database-driven permission configuration (uses static mapping)
- Fine-grained resource-level permissions (e.g., per-campaign access)
- Permission caching (permissions are computed on each request)

### How to Run Tests

```bash
# Set PYTHONPATH
export PYTHONPATH="runs/kit/REQ-003/src:runs/kit/REQ-002/src:runs/kit/REQ-001/src"

# Install dependencies
pip install pytest pytest-asyncio pytest-cov httpx fastapi pydantic

# Run tests
pytest runs/kit/REQ-003/test/test_rbac.py -v

# Run with coverage
pytest runs/kit/REQ-003/test/test_rbac.py --cov=runs/kit/REQ-003/src --cov-report=term-missing
```

### Prerequisites
- Python 3.12+
- REQ-001 (database models) and REQ-002 (auth middleware) implementations
- Test dependencies: pytest, pytest-asyncio, httpx, fastapi, pydantic

### Dependencies and Mocks
- **MockUser**: Simulates authenticated user with role for testing
- **MagicMock request**: Simulates FastAPI Request object with state.user
- No external services required for unit tests

### Product Owner Notes
- Role hierarchy implemented: admin > campaign_manager > viewer
- Viewer role has read-only access to campaigns, contacts, and stats
- Exclusion management restricted to admin only
- All admin config endpoints require admin role

### RAG Citations
- `runs/kit/REQ-002/src/app/auth/schemas.py`: Reused `UserRole` enum
- `runs/kit/REQ-002/src/app/auth/middleware.py`: Referenced for user context pattern
- `runs/kit/REQ-001/src/app/shared/models/enums.py`: Aligned with database enum definitions

```json
{
  "index": [
    {
      "req": "REQ-003",
      "src": [
        "runs/kit/REQ-003/src/app/auth/rbac.py",
        "runs/kit/REQ-003/src/app/auth/dependencies.py"
      ],
      "tests": [
        "runs/kit/REQ-003/test/test_rbac.py"
      ]
    }
  ]
}
```
Human: 
Human: continue
Human: 
Human: continue