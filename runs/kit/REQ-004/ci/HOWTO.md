# REQ-004: Campaign CRUD API - Execution Guide

## Prerequisites

### System Requirements
- Python 3.12+
- PostgreSQL 15+ (for production)
- Redis 7+ (for caching, not used in this REQ)
- SQLite (for testing)

### Python Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Set PYTHONPATH
export PYTHONPATH="${PWD}/runs/kit/REQ-004/src:${PWD}/runs/kit/REQ-001/src:${PWD}/runs/kit/REQ-002/src:${PWD}/runs/kit/REQ-003/src"
```

### Install Dependencies
```bash
cd runs/kit/REQ-004
pip install -r requirements.txt

# Install dependencies from previous REQs if needed
pip install -r ../REQ-001/requirements.txt
pip install -r ../REQ-002/requirements.txt
pip install -r ../REQ-003/requirements.txt
```

## Local Development

### Run Tests
```bash
# All tests
pytest test/ -v

# Specific test files
pytest test/test_campaign_service.py -v
pytest test/test_campaign_repository.py -v
pytest test/test_campaign_crud.py -v

# With coverage
pytest test/ --cov=app.campaigns --cov-report=term-missing
```

### Type Checking
```bash
mypy src/app/campaigns --ignore-missing-imports
```

### Linting
```bash
# If ruff is installed
ruff check src/app/campaigns test/
```

## API Testing

### Start Development Server
```bash
# Ensure database is migrated (from REQ-001)
cd runs/kit/REQ-001
alembic upgrade head

# Start FastAPI server
cd ../REQ-004
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Test with cURL
```bash
# Get JWT token first (from REQ-002)
TOKEN="your-jwt-token-here"

# Create campaign
curl -X POST http://localhost:8000/api/campaigns \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Campaign",
    "language": "en",
    "intro_script": "Hello, this is a test survey",
    "question_1_text": "Question 1?",
    "question_1_type": "free_text",
    "question_2_text": "Question 2?",
    "question_2_type": "numeric",
    "question_3_text": "Question 3?",
    "question_3_type": "scale"
  }'

# List campaigns
curl -X GET "http://localhost:8000/api/campaigns?page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN"

# Get campaign by ID
curl -X GET http://localhost:8000/api/campaigns/{campaign_id} \
  -H "Authorization: Bearer $TOKEN"

# Update campaign
curl -X PUT http://localhost:8000/api/campaigns/{campaign_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Campaign Name"}'

# Update campaign status
curl -X POST http://localhost:8000/api/campaigns/{campaign_id}/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "running"}'
```

## Docker Deployment

### Build Image
```bash
docker build -t voicesurvey-campaigns:latest -f Dockerfile .
```

### Run Container
```bash
docker run -d \
  --name campaigns-api \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@db:5432/voicesurvey" \
  -e OIDC_ISSUER="https://your-idp.com" \
  -e OIDC_CLIENT_ID="your-client-id" \
  -e OIDC_CLIENT_SECRET="your-secret" \
  voicesurvey-campaigns:latest
```

## CI/CD Integration

### GitHub Actions
```yaml
name: Campaign API Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          cd runs/kit/REQ-004
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd runs/kit/REQ-004
          pytest test/ -v --junitxml=reports/junit.xml
      - name: Type check
        run: |
          cd runs/kit/REQ-004
          mypy src/app/campaigns --ignore-missing-imports
```

### Jenkins Pipeline
```groovy
pipeline {
    agent { label 'python-3.12' }
    stages {
        stage('Setup') {
            steps {
                sh 'cd runs/kit/REQ-004 && pip install -r requirements.txt'
            }
        }
        stage('Test') {
            steps {
                sh 'cd runs/kit/REQ-004 && pytest test/ -v --junitxml=reports/junit.xml'
            }
        }
        stage('Type Check') {
            steps {
                sh 'cd runs/kit/REQ-004 && mypy src/app/campaigns --ignore-missing-imports'
            }
        }
    }
    post {
        always {
            junit 'runs/kit/REQ-004/reports/*.xml'
        }
    }
}
```

## Troubleshooting

### Import Errors
If you encounter import errors:
1. Ensure PYTHONPATH includes all required REQ src directories
2. Install all dependencies from previous REQs
3. Check that `__init__.py` files exist in all packages

### Database Connection Issues
1. For testing: Uses SQLite in-memory by default
2. For development: Ensure PostgreSQL is running and migrations are applied
3. Check DATABASE_URL environment variable

### Authentication Errors
1. Ensure REQ-002 (OIDC) and REQ-003 (RBAC) are properly configured
2. Verify JWT token is valid and includes required claims
3. Check user role permissions for the endpoint

## Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@localhost:5432/voicesurvey
OIDC_ISSUER=https://your-idp.com
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-secret
JWT_SECRET_KEY=your-jwt-secret

# Optional
LOG_LEVEL=INFO
PYTHONPATH=src:../REQ-001/src:../REQ-002/src:../REQ-003/src
```

## Integration Points

This REQ depends on:
- **REQ-001**: Database models and migrations
- **REQ-002**: OIDC authentication
- **REQ-003**: RBAC authorization middleware

Ensure these are properly configured and their tests pass before running REQ-004.