# REQ-004: Campaign CRUD API - Execution Guide

## Prerequisites

### System Requirements
- Python 3.12+
- PostgreSQL 15+
- pip or Poetry for dependency management

### Environment Setup

1. **Create virtual environment:**
   bash
   cd runs/kit/REQ-004
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate  # Windows
   

2. **Install dependencies:**
   bash
   pip install -r requirements.txt
   

3. **Set environment variables:**
   bash
   export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/voicesurvey_test"
   export APP_ENV="dev"
   export LOG_LEVEL="DEBUG"
   export OIDC_ISSUER_URL="https://auth.example.com"
   export OIDC_CLIENT_ID="test-client"
   export JWT_AUDIENCE="voicesurvey-api"
   

   Or create a `.env` file in the `runs/kit/REQ-004` directory.

4. **Database setup:**
   bash
   # Ensure PostgreSQL is running
   # Create test database
   createdb voicesurvey_test
   
   # Apply migrations from REQ-001
   psql -d voicesurvey_test -f ../REQ-001/src/storage/sql/V0001.up.sql
   

## Running Tests

### Full Test Suite
bash
cd runs/kit/REQ-004
pytest test/ -v --tb=short

### With Coverage
bash
pytest test/ -v --cov=src/app --cov-report=term-missing --cov-report=xml:reports/coverage.xml

### Specific Test Files
bash
# CRUD tests
pytest test/test_campaign_crud.py -v

# Service tests
pytest test/test_campaign_service.py -v

## Code Quality Checks

### Linting
bash
ruff check src/app tests
ruff format src/app tests --check

### Type Checking
bash
mypy src/app --ignore-missing-imports

### Security Scan
bash
bandit -r src/app -ll

## Running the Application

### Development Server
bash
cd runs/kit/REQ-004
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

### API Documentation
Once running, access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Testing with curl

### Create Campaign
bash
curl -X POST http://localhost:8000/api/campaigns \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Campaign",
    "description": "Test description",
    "language": "en",
    "intro_script": "Hello, this is a test survey...",
    "question_1": {"text": "Question 1?", "type": "free_text"},
    "question_2": {"text": "Question 2?", "type": "scale"},
    "question_3": {"text": "Question 3?", "type": "numeric"},
    "max_attempts": 3,
    "retry_interval_minutes": 60
  }'

### List Campaigns
bash
curl -X GET "http://localhost:8000/api/campaigns?page=1&page_size=20" \
  -H "Authorization: Bearer <token>"

### Get Campaign
bash
curl -X GET http://localhost:8000/api/campaigns/<campaign_id> \
  -H "Authorization: Bearer <token>"

## Troubleshooting

### Import Errors
If you encounter import errors, ensure PYTHONPATH is set:
bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

### Database Connection Issues
1. Verify PostgreSQL is running
2. Check DATABASE_URL format
3. Ensure database exists and migrations are applied

### Test Failures
1. Ensure test database is clean
2. Check that migrations from REQ-001 are applied
3. Verify environment variables are set

## CI/CD Integration

### GitHub Actions
The LTC.json file defines test cases compatible with the Harper eval runner.

### Jenkins
groovy
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
                sh 'cd runs/kit/REQ-004 && pytest test/ -v --junitxml=reports/junit.xml'
            }
        }
    }
}

## Artifacts

- **Test Reports:** `runs/kit/REQ-004/reports/junit.xml`
- **Coverage Report:** `runs/kit/REQ-004/reports/coverage.xml`
- **API Collection:** `runs/kit/REQ-004/test/api/campaigns.json`