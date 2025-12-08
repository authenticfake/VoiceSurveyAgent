# REQ-004: Campaign CRUD API - Execution Guide

## Prerequisites

### Required Tools
- Python 3.12+
- pip or Poetry for dependency management
- PostgreSQL 15+ (for production) or SQLite (for testing)

### Environment Variables
```bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/voicesurvey"
export OIDC_ISSUER="https://your-idp.com/"
export OIDC_CLIENT_ID="your-client-id"
export OIDC_CLIENT_SECRET="your-client-secret"
export JWT_SECRET_KEY="your-jwt-secret"
export LOG_LEVEL="INFO"
```

## Local Development Setup

### 1. Install Dependencies
```bash
# From project root
pip install -r runs/kit/REQ-004/requirements.txt

# Or with Poetry
poetry install
```

### 2. Set PYTHONPATH
```bash
# Include all dependent REQ modules
export PYTHONPATH=runs/kit/REQ-001/src:runs/kit/REQ-002/src:runs/kit/REQ-003/src:runs/kit/REQ-004/src
```

### 3. Run Database Migrations
```bash
# Ensure REQ-001 migrations are applied first
cd runs/kit/REQ-001
alembic upgrade head
```

### 4. Run Tests
```bash
# Run all tests with coverage
pytest runs/kit/REQ-004/test -v --cov=app.campaigns --cov-report=term-missing

# Run specific test file
pytest runs/kit/REQ-004/test/test_campaign_service.py -v

# Run with SQLite in-memory (default for tests)
DATABASE_URL="sqlite+aiosqlite:///:memory:" pytest runs/kit/REQ-004/test -v
```

### 5. Run Linting and Type Checks
```bash
# Linting
ruff check runs/kit/REQ-004/src runs/kit/REQ-004/test

# Type checking
mypy runs/kit/REQ-004/src --ignore-missing-imports

# Security scan
bandit -r runs/kit/REQ-004/src -ll
```

## Running the API Server

### Development Server
```bash
# Start FastAPI with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing API Endpoints
```bash
# Create a campaign (requires valid JWT)
curl -X POST http://localhost:8000/api/campaigns \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "name": "Test Campaign",
    "intro_script": "Hello, this is a test survey...",
    "question_1_text": "How satisfied are you?",
    "question_1_type": "scale",
    "question_2_text": "What can we improve?",
    "question_2_type": "free_text",
    "question_3_text": "How many times have you used our service?",
    "question_3_type": "numeric"
  }'

# List campaigns
curl http://localhost:8000/api/campaigns \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Get campaign by ID
curl http://localhost:8000/api/campaigns/{campaign_id} \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Container Execution

### Build Docker Image
```bash
docker build -t voicesurvey-api:latest -f Dockerfile .
```

### Run with Docker Compose
```bash
docker-compose up -d
```

## CI/CD Integration

### GitHub Actions
The LTC.json file defines all test cases. Run them in sequence:
1. `install_deps` - Install Python dependencies
2. `lint` - Run ruff linter
3. `types` - Run mypy type checker
4. `tests` - Run pytest with coverage
5. `security` - Run bandit security scanner

### Jenkins Pipeline
```groovy
pipeline {
    agent { label 'python-3.12' }
    stages {
        stage('Install') {
            steps {
                sh 'pip install -r runs/kit/REQ-004/requirements.txt'
            }
        }
        stage('Test') {
            steps {
                sh '''
                    export PYTHONPATH=runs/kit/REQ-001/src:runs/kit/REQ-002/src:runs/kit/REQ-003/src:runs/kit/REQ-004/src
                    pytest runs/kit/REQ-004/test -v --junitxml=test-results.xml --cov=app.campaigns --cov-report=xml
                '''
            }
            post {
                always {
                    junit 'test-results.xml'
                    publishCoverage adapters: [coberturaAdapter('coverage.xml')]
                }
            }
        }
    }
}
```

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError: No module named 'app'`:
1. Ensure PYTHONPATH includes all REQ source directories
2. Verify the directory structure matches expected paths
3. Check that `__init__.py` files exist in all packages

### Database Connection Issues
1. Verify DATABASE_URL is correctly formatted
2. For async drivers, use `postgresql+asyncpg://` or `sqlite+aiosqlite://`
3. Ensure database server is running and accessible

### Authentication Errors
1. Verify OIDC configuration matches your IdP
2. Check JWT token is valid and not expired
3. Ensure user has required role (campaign_manager or admin)

## Artifacts Location
- Test reports: `runs/kit/REQ-004/reports/junit.xml`
- Coverage report: `runs/kit/REQ-004/reports/coverage.xml`
- API documentation: `runs/kit/REQ-004/test/api/campaigns.json`