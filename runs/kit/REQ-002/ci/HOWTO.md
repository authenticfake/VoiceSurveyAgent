# REQ-002: OIDC Authentication Integration - Execution Guide

## Prerequisites

### System Requirements
- Python 3.12+
- PostgreSQL 15+ (for user storage)
- Redis 7+ (optional, for production state storage)

### Environment Setup

1. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate  # Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r runs/kit/REQ-002/requirements.txt
   ```

3. **Configure environment variables:**
   Create a `.env` file or export variables:
   ```bash
   export DATABASE_URL="postgresql://user:password@localhost:5432/voicesurvey"
   export REDIS_URL="redis://localhost:6379/0"
   export OIDC_ISSUER="https://your-idp.example.com"
   export OIDC_AUTHORIZATION_ENDPOINT="https://your-idp.example.com/authorize"
   export OIDC_TOKEN_ENDPOINT="https://your-idp.example.com/token"
   export OIDC_USERINFO_ENDPOINT="https://your-idp.example.com/userinfo"
   export OIDC_JWKS_URI="https://your-idp.example.com/.well-known/jwks.json"
   export OIDC_CLIENT_ID="your-client-id"
   export OIDC_CLIENT_SECRET="your-client-secret"
   export OIDC_REDIRECT_URI="http://localhost:8000/api/auth/callback"
   ```

### PYTHONPATH Configuration

Set PYTHONPATH to include the source directory:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/runs/kit/REQ-002/src:$(pwd)/runs/kit/REQ-001/src"
```

## Running Tests

### Unit Tests
```bash
pytest runs/kit/REQ-002/test/ -v --tb=short
```

### With Coverage
```bash
pytest runs/kit/REQ-002/test/ \
  --cov=runs/kit/REQ-002/src/app/auth \
  --cov-report=term-missing \
  --cov-report=xml:runs/kit/REQ-002/reports/coverage.xml
```

### Generate JUnit Report
```bash
pytest runs/kit/REQ-002/test/ \
  --junitxml=runs/kit/REQ-002/reports/junit.xml
```

## Running the Application

### Development Server
```bash
cd runs/kit/REQ-002/src
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation
Once running, access:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Authentication Flow

### 1. Initiate Login
```bash
curl http://localhost:8000/api/auth/login
```
Response contains `authorization_url` - redirect user to this URL.

### 2. Handle Callback
After user authenticates with IdP, they're redirected to callback:
```bash
curl "http://localhost:8000/api/auth/callback?code=AUTH_CODE&state=STATE"
```

### 3. Use Access Token
Include token in subsequent requests:
```bash
curl -H "Authorization: Bearer ACCESS_TOKEN" http://localhost:8000/api/auth/me
```

### 4. Refresh Token
```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "REFRESH_TOKEN"}'
```

## Troubleshooting

### Common Issues

1. **Import errors:**
   - Ensure PYTHONPATH includes both REQ-001 and REQ-002 src directories
   - Verify all dependencies are installed

2. **Database connection errors:**
   - Verify PostgreSQL is running
   - Check DATABASE_URL format: `postgresql://user:pass@host:port/dbname`

3. **OIDC errors:**
   - Verify all OIDC endpoints are accessible
   - Check client_id and client_secret are correct
   - Ensure redirect_uri matches IdP configuration

4. **Token validation failures:**
   - Check JWKS endpoint is accessible
   - Verify token hasn't expired
   - Ensure audience matches client_id

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
```

## Enterprise Runner Configuration

### Jenkins Pipeline
```groovy
pipeline {
    agent { label 'python-3.12' }
    environment {
        PYTHONPATH = "${WORKSPACE}/runs/kit/REQ-002/src:${WORKSPACE}/runs/kit/REQ-001/src"
    }
    stages {
        stage('Install') {
            steps {
                sh 'pip install -r runs/kit/REQ-002/requirements.txt'
            }
        }
        stage('Test') {
            steps {
                sh '''
                    pytest runs/kit/REQ-002/test/ \
                      --junitxml=runs/kit/REQ-002/reports/junit.xml \
                      --cov=runs/kit/REQ-002/src/app/auth \
                      --cov-report=xml:runs/kit/REQ-002/reports/coverage.xml
                '''
            }
            post {
                always {
                    junit 'runs/kit/REQ-002/reports/junit.xml'
                    publishCoverage adapters: [coberturaAdapter('runs/kit/REQ-002/reports/coverage.xml')]
                }
            }
        }
    }
}
```

### GitHub Actions
```yaml
name: REQ-002 Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r runs/kit/REQ-002/requirements.txt
      - name: Run tests
        env:
          PYTHONPATH: ${{ github.workspace }}/runs/kit/REQ-002/src:${{ github.workspace }}/runs/kit/REQ-001/src
          DATABASE_URL: postgresql://test:test@localhost:5432/test
        run: pytest runs/kit/REQ-002/test/ -v
```

## Artifacts Location

| Artifact | Path |
|----------|------|
| Source code | `runs/kit/REQ-002/src/app/auth/` |
| Tests | `runs/kit/REQ-002/test/` |
| JUnit report | `runs/kit/REQ-002/reports/junit.xml` |
| Coverage report | `runs/kit/REQ-002/reports/coverage.xml` |
| LTC config | `runs/kit/REQ-002/ci/LTC.json` |