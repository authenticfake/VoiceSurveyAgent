# REQ-002: OIDC Authentication Integration - Execution Guide

## Overview

This KIT implements OIDC authentication integration for the VoiceSurveyAgent application, including:
- OIDC authorization code flow with configurable IdP endpoints
- JWT token validation middleware for API requests
- User record creation/update on first login with OIDC subject mapping
- Session tokens with configurable expiration and refresh capability
- Login endpoint returning user profile with role information

## Prerequisites

### Required Software
- Python 3.12+
- pip or Poetry for dependency management
- PostgreSQL 15+ (for production) or SQLite (for testing)

### Environment Variables

Create a `.env` file or set the following environment variables:

```bash
# Application
APP_ENV=dev
DEBUG=true
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://afranco:Andrea.1@localhost:5432/voicesurveyagent

# OIDC Configuration
OIDC_ISSUER_URL=http://localhost:8080
OIDC_CLIENT_ID=voice-survey-agent
OIDC_CLIENT_SECRET=wQGovP2T32xHHGVwEzRO7M2WLcSBuBPl
OIDC_REDIRECT_URI=http://localhost:8000/api/auth/callback
OIDC_SCOPES=openid profile email

# JWT Configuration
JWT_SECRET_KEY=your-secure-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000
```

## Installation

### Local Development

```bash
# Navigate to the KIT directory
cd runs/kit/REQ-002

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set PYTHONPATH for imports
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
```

### Alternative: Using Poetry

```bash
cd runs/kit/REQ-002
poetry install
poetry shell
```

## Running Tests

### Full Test Suite

```bash
# From project root
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test -v --tb=short

# With coverage
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test -v \
  --cov=runs/kit/REQ-002/src \
  --cov-report=term-missing \
  --cov-report=html:runs/kit/REQ-002/reports/htmlcov
```

### Individual Test Files

```bash
# JWT tests
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test/test_jwt.py -v

# Repository tests
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test/test_repository.py -v

# Service tests
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test/test_service.py -v

# Middleware tests
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test/test_middleware.py -v

# Router/API tests
PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test/test_router.py -v
```

## Code Quality Checks

### Linting

```bash
# Check for issues
ruff check runs/kit/REQ-002/src runs/kit/REQ-002/test

# Auto-fix issues
ruff check runs/kit/REQ-002/src runs/kit/REQ-002/test --fix

# Format code
ruff format runs/kit/REQ-002/src runs/kit/REQ-002/test
```

### Type Checking

```bash
mypy runs/kit/REQ-002/src --ignore-missing-imports
```

### Security Scanning

```bash
bandit -r runs/kit/REQ-002/src -ll
```

## Running the Application

### Development Server

```bash
cd runs/kit/REQ-002
PYTHONPATH=src uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production

```bash
cd runs/kit/REQ-002
PYTHONPATH=src uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Authentication Endpoints

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| GET | `/api/auth/login` | Initiate OIDC login flow | No |
| GET | `/api/auth/callback` | Handle OIDC callback | No |
| POST | `/api/auth/refresh` | Refresh access token | No (uses refresh token) |
| GET | `/api/auth/me` | Get current user profile | Yes |
| GET | `/health` | Health check | No |

### Example API Calls

```bash
# Initiate login
curl http://localhost:8000/api/auth/login

# Refresh tokens
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your-refresh-token"}'

# Get current user (requires valid access token)
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer your-access-token"

# Health check
curl http://localhost:8000/health
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure `PYTHONPATH` includes the `src` directory
   ```bash
   export PYTHONPATH=$PYTHONPATH:$(pwd)/runs/kit/REQ-002/src
   ```

2. **Database connection errors**: Verify `DATABASE_URL` is correct and the database is running

3. **OIDC errors**: Check that `OIDC_ISSUER_URL`, `OIDC_CLIENT_ID`, and `OIDC_CLIENT_SECRET` are correctly configured

4. **Token validation errors**: Ensure `JWT_SECRET_KEY` is consistent across restarts

### Debug Mode

Enable debug logging:
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

## CI/CD Integration

### GitHub Actions

The LTC.json file defines the test cases for CI:

```yaml
- name: Run REQ-002 Tests
  run: |
    pip install -r runs/kit/REQ-002/requirements.txt
    PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test -v \
      --cov=runs/kit/REQ-002/src \
      --junitxml=runs/kit/REQ-002/reports/junit.xml
```

### Jenkins Pipeline

```groovy
stage('REQ-002 Tests') {
    steps {
        sh '''
            pip install -r runs/kit/REQ-002/requirements.txt
            PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test -v
        '''
    }
}
```

## Artifacts

| Path | Description |
|------|-------------|
| `runs/kit/REQ-002/src/` | Source code |
| `runs/kit/REQ-002/test/` | Test files |
| `runs/kit/REQ-002/reports/junit.xml` | JUnit test results |
| `runs/kit/REQ-002/reports/coverage.xml` | Coverage report |
| `runs/kit/REQ-002/ci/LTC.json` | Test contract |