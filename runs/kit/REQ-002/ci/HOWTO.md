# REQ-002: OIDC Authentication Integration - Execution Guide

## Prerequisites

- Python 3.12+
- pip or poetry for dependency management
- PostgreSQL 15+ (for production) or SQLite (for testing)

## Environment Setup

### 1. Create Virtual Environment

bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows

### 2. Install Dependencies

bash
pip install -r runs/kit/REQ-002/requirements.txt

### 3. Configure Environment Variables

Create a `.env` file or export the following variables:

bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/voicesurvey"
export OIDC_ISSUER_URL="https://your-idp.com"
export OIDC_CLIENT_ID="your-client-id"
export OIDC_CLIENT_SECRET="your-client-secret"
export OIDC_REDIRECT_URI="http://localhost:8000/api/auth/callback"
export JWT_SECRET_KEY="your-secure-secret-key"
export DEBUG="false"

## Running Tests

### Local Execution

bash
# Set PYTHONPATH to include source directory
export PYTHONPATH=runs/kit/REQ-002/src

# Run all tests with coverage
pytest runs/kit/REQ-002/test -v --cov=app --cov-report=term-missing

# Run specific test file
pytest runs/kit/REQ-002/test/test_jwt.py -v

# Run with JUnit XML output for CI
pytest runs/kit/REQ-002/test -v --junitxml=reports/junit.xml --cov=app --cov-report=xml:reports/coverage.xml

### Code Quality Checks

bash
# Linting
ruff check runs/kit/REQ-002/src runs/kit/REQ-002/test

# Auto-fix linting issues
ruff check --fix runs/kit/REQ-002/src runs/kit/REQ-002/test

# Type checking
PYTHONPATH=runs/kit/REQ-002/src mypy runs/kit/REQ-002/src --ignore-missing-imports

## Running the Application

bash
# Development server
PYTHONPATH=runs/kit/REQ-002/src uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production server
PYTHONPATH=runs/kit/REQ-002/src uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/auth/login` | GET | Initiate OIDC login flow |
| `/api/auth/callback` | GET | Handle OIDC callback |
| `/api/auth/refresh` | POST | Refresh access token |
| `/api/auth/me` | GET | Get current user profile |
| `/api/auth/logout` | POST | Logout current user |

## Troubleshooting

### Import Errors

If you encounter import errors, ensure PYTHONPATH is set correctly:

bash
export PYTHONPATH=runs/kit/REQ-002/src:$PYTHONPATH

### Database Connection Issues

For testing, the system uses SQLite in-memory database. For production:

1. Ensure PostgreSQL is running
2. Verify DATABASE_URL is correct
3. Run migrations from REQ-001 first

### OIDC Configuration

1. Verify OIDC_ISSUER_URL is accessible
2. Ensure client ID and secret are correct
3. Check redirect URI matches IdP configuration

## CI/CD Integration

### GitHub Actions

The LTC.json file defines the test contract. Use it with:

yaml
- name: Run Tests
  run: |
    pip install -r runs/kit/REQ-002/requirements.txt
    PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test -v --cov=app

### Jenkins

groovy
stage('Test REQ-002') {
    steps {
        sh 'pip install -r runs/kit/REQ-002/requirements.txt'
        sh 'PYTHONPATH=runs/kit/REQ-002/src pytest runs/kit/REQ-002/test -v --junitxml=reports/junit.xml'
    }
    post {
        always {
            junit 'reports/junit.xml'
        }
    }
}

## Artifacts

| Path | Description |
|------|-------------|
| `runs/kit/REQ-002/src/app/` | Application source code |
| `runs/kit/REQ-002/test/` | Test files |
| `reports/junit.xml` | JUnit test results |
| `reports/coverage.xml` | Coverage report |