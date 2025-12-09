# REQ-002: OIDC Authentication Integration - Execution Guide

## Overview

This KIT implements OIDC authentication integration for the Voice Survey Agent platform, including:
- OIDC authorization code flow with configurable IdP endpoints
- JWT token validation middleware
- User record creation/update on first login
- Session tokens with configurable expiration and refresh capability

## Prerequisites

### System Requirements
- Python 3.12+
- PostgreSQL 14+ (for user storage)
- Access to an OIDC-compliant Identity Provider (e.g., Keycloak, Auth0, Okta)

### Environment Variables

bash
# Database
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey"

# OIDC Configuration
export OIDC_ISSUER_URL="https://your-idp.example.com"
export OIDC_AUTHORIZATION_ENDPOINT="https://your-idp.example.com/authorize"
export OIDC_TOKEN_ENDPOINT="https://your-idp.example.com/token"
export OIDC_USERINFO_ENDPOINT="https://your-idp.example.com/userinfo"
export OIDC_JWKS_URI="https://your-idp.example.com/.well-known/jwks.json"
export OIDC_CLIENT_ID="your-client-id"
export OIDC_CLIENT_SECRET="your-client-secret"
export OIDC_REDIRECT_URI="http://localhost:8000/api/auth/callback"

# Token Settings (optional)
export ACCESS_TOKEN_EXPIRE_MINUTES="30"
export REFRESH_TOKEN_EXPIRE_DAYS="7"
export JWT_ALGORITHM="RS256"
export OIDC_SCOPES="openid profile email"

## Local Development Setup

### 1. Install Dependencies

bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r runs/kit/REQ-002/requirements.txt

### 2. Set PYTHONPATH

bash
# Include both REQ-001 (database models) and REQ-002 source
export PYTHONPATH="runs/kit/REQ-002/src:runs/kit/REQ-001/src:$PYTHONPATH"

### 3. Run Database Migrations

Ensure REQ-001 migrations have been applied:

bash
cd runs/kit/REQ-001
./scripts/db_upgrade.sh

### 4. Run Tests

bash
# Run all tests
pytest runs/kit/REQ-002/test -v

# Run with coverage
pytest runs/kit/REQ-002/test -v --cov=runs/kit/REQ-002/src --cov-report=html

# Run specific test file
pytest runs/kit/REQ-002/test/test_auth_middleware.py -v

## Running the Application

### Integration with FastAPI App

python
from fastapi import FastAPI
from app.auth.config import AuthConfig
from app.auth.middleware import JWTAuthMiddleware
from app.auth.router import router as auth_router

app = FastAPI()

# Load auth config
auth_config = AuthConfig.from_env()

# Add authentication middleware
app.add_middleware(JWTAuthMiddleware, config=auth_config)

# Include auth routes
app.include_router(auth_router)

### Testing Authentication Flow

1. **Initiate Login:**
   bash
   curl -v http://localhost:8000/api/auth/login
   # Follow redirect to IdP
   

2. **After IdP Authentication:**
   The callback endpoint receives the authorization code and returns tokens:
   json
   {
     "access_token": "eyJ...",
     "token_type": "Bearer",
     "expires_in": 1800,
     "refresh_token": "...",
     "user": {
       "id": "...",
       "email": "user@example.com",
       "name": "User Name",
       "role": "viewer"
     }
   }
   

3. **Access Protected Endpoints:**
   bash
   curl -H "Authorization: Bearer <access_token>" \
        http://localhost:8000/api/protected
   

4. **Refresh Token:**
   bash
   curl -X POST http://localhost:8000/api/auth/refresh \
        -H "Content-Type: application/json" \
        -d '{"refresh_token": "<refresh_token>"}'
   

## CI/CD Integration

### GitHub Actions

The LTC.json file defines the test contract. Run in CI:

yaml
- name: Run REQ-002 Tests
  run: |
    pip install -r runs/kit/REQ-002/requirements.txt
    PYTHONPATH=runs/kit/REQ-002/src:runs/kit/REQ-001/src \
    pytest runs/kit/REQ-002/test -v --junitxml=reports/junit-req002.xml

### Jenkins Pipeline

groovy
stage('REQ-002 Tests') {
    steps {
        sh '''
            pip install -r runs/kit/REQ-002/requirements.txt
            export PYTHONPATH=runs/kit/REQ-002/src:runs/kit/REQ-001/src
            pytest runs/kit/REQ-002/test -v --junitxml=reports/junit-req002.xml
        '''
    }
    post {
        always {
            junit 'reports/junit-req002.xml'
        }
    }
}

## Troubleshooting

### Common Issues

1. **Import Errors:**
   - Ensure PYTHONPATH includes both REQ-001 and REQ-002 src directories
   - Verify all dependencies are installed

2. **OIDC Configuration Errors:**
   - Verify all OIDC environment variables are set
   - Check IdP endpoints are accessible
   - Ensure client credentials are correct

3. **Token Validation Failures:**
   - Verify JWKS URI is accessible
   - Check token algorithm matches IdP configuration
   - Ensure issuer and audience claims match configuration

4. **Database Connection Errors:**
   - Verify DATABASE_URL is correct
   - Ensure PostgreSQL is running
   - Check REQ-001 migrations have been applied

### Debug Mode

Enable SQL logging for debugging:
bash
export SQL_ECHO=true

## Architecture Notes

### Module Structure

runs/kit/REQ-002/src/app/auth/
├── __init__.py          # Module exports
├── config.py            # Configuration from environment
├── models.py            # Pydantic models for auth DTOs
├── exceptions.py        # Custom auth exceptions
├── jwks.py              # JWKS client for key management
├── oidc_client.py       # OIDC authorization code flow
├── jwt_validator.py     # JWT token validation
├── service.py           # Auth service (user management)
├── middleware.py        # FastAPI JWT middleware
├── dependencies.py      # FastAPI dependencies
└── router.py            # API routes

### Key Design Decisions

1. **Composition over Inheritance:** All dependencies are injected
2. **Interface-based Design:** Services depend on abstractions
3. **Async-first:** All I/O operations are async
4. **Testability:** Mock-friendly design with dependency injection