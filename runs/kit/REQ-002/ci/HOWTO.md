# REQ-002: OIDC Authentication Integration - Execution Guide

## Prerequisites

### Required Tools
- Python 3.12+
- PostgreSQL 15+ (for integration tests)
- pip or poetry for dependency management

### Environment Variables
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/voicesurvey"
export OIDC_ISSUER="https://your-idp.example.com"
export OIDC_CLIENT_ID="voicesurveyagent"
export OIDC_CLIENT_SECRET="your-client-secret"
export OIDC_REDIRECT_URI="http://localhost:8000/api/auth/callback"
export JWT_SECRET_KEY="your-secure-secret-key"
export JWT_ALGORITHM="HS256"
export JWT_EXPIRATION_MINUTES="60"
```

## Local Development

### Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r runs/kit/REQ-002/requirements.txt

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/runs/kit/REQ-002/src"
```

### Running Tests
```bash
# Run all tests
pytest runs/kit/REQ-002/test -v

# Run with coverage
pytest runs/kit/REQ-002/test --cov=runs/kit/REQ-002/src/app --cov-report=term-missing

# Run specific test file
pytest runs/kit/REQ-002/test/test_auth_service.py -v
```

### Running the Application
```bash
# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Container Execution

### Docker Build
```bash
docker build -t voicesurvey-auth -f Dockerfile .
```

### Docker Run
```bash
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e OIDC_ISSUER="https://your-idp.example.com" \
  -e OIDC_CLIENT_ID="voicesurveyagent" \
  -e OIDC_CLIENT_SECRET="secret" \
  -e JWT_SECRET_KEY="your-secret" \
  voicesurvey-auth
```

## CI/CD Integration

### GitHub Actions
The LTC.json file defines test cases that can be executed in CI:
1. `install_deps` - Install Python dependencies
2. `tests` - Run pytest test suite
3. `coverage` - Generate coverage report

### Jenkins Pipeline
```groovy
pipeline {
    agent { label 'python-3.12' }
    stages {
        stage('Install') {
            steps {
                sh 'pip install -r runs/kit/REQ-002/requirements.txt'
            }
        }
        stage('Test') {
            steps {
                sh 'pytest runs/kit/REQ-002/test --junitxml=test-results.xml'
            }
        }
    }
}
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure PYTHONPATH includes the src directory
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/runs/kit/REQ-002/src"
   ```

2. **Database connection errors**: Verify DATABASE_URL is set correctly
   ```bash
   echo $DATABASE_URL
   ```

3. **OIDC configuration errors**: Check that OIDC_ISSUER is accessible
   ```bash
   curl -s "${OIDC_ISSUER}/.well-known/openid-configuration" | jq .
   ```

4. **JWT validation errors**: Ensure JWT_SECRET_KEY matches between token generation and validation

## Artifacts

- Test results: `runs/kit/REQ-002/reports/junit.xml`
- Coverage report: `runs/kit/REQ-002/reports/coverage.xml`
- Logs: Standard output (structured JSON format)