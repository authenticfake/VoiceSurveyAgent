# KIT Documentation: REQ-002 - OIDC Authentication Integration

## Overview

This KIT implements OIDC authentication integration for the VoiceSurveyAgent application, providing secure user authentication via corporate Identity Providers.

## Components

### Core Modules

1. **app/config.py** - Application configuration with OIDC settings
2. **app/auth/oidc.py** - OIDC client for IdP communication
3. **app/auth/jwt.py** - JWT token creation and validation
4. **app/auth/models.py** - User SQLAlchemy model
5. **app/auth/schemas.py** - Pydantic schemas for API
6. **app/auth/repository.py** - User data access layer
7. **app/auth/service.py** - Authentication business logic
8. **app/auth/middleware.py** - FastAPI authentication middleware
9. **app/auth/router.py** - Authentication API endpoints

### Shared Modules

1. **app/shared/database.py** - Async database session management
2. **app/shared/exceptions.py** - Custom exception classes
3. **app/shared/logging.py** - Structured JSON logging

## Architecture

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Auth Router   │────▶│   Auth Service  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                        ┌───────────────────────────────┼───────────────────────────────┐
                        │                               │                               │
                        ▼                               ▼                               ▼
                ┌───────────────┐              ┌───────────────┐              ┌───────────────┐
                │  OIDC Client  │              │  JWT Handler  │              │ User Repository│
                └───────────────┘              └───────────────┘              └───────────────┘
                        │                                                             │
                        ▼                                                             ▼
                ┌───────────────┐                                             ┌───────────────┐
                │   IdP (OIDC)  │                                             │   PostgreSQL  │
                └───────────────┘                                             └───────────────┘

## Authentication Flow

1. **Login Initiation**
   - Client calls `GET /api/auth/login`
   - Server generates state parameter and authorization URL
   - Client redirects user to IdP

2. **OIDC Callback**
   - IdP redirects to `GET /api/auth/callback` with code and state
   - Server validates state and exchanges code for tokens
   - Server fetches user info from IdP
   - Server creates/updates user record
   - Server issues session tokens (access + refresh)

3. **Token Validation**
   - Every protected request includes Bearer token
   - Middleware validates token signature and expiry
   - Middleware loads user from database
   - Request proceeds with authenticated user context

4. **Token Refresh**
   - Client calls `POST /api/auth/refresh` with refresh token
   - Server validates refresh token
   - Server issues new access and refresh tokens

## Security Considerations

- State parameter prevents CSRF attacks
- JWT tokens signed with HS256 algorithm
- Refresh tokens enable session extension without re-authentication
- Token expiry configurable via environment variables
- Secrets stored in environment, not code

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| OIDC_ISSUER_URL | IdP issuer URL | - |
| OIDC_CLIENT_ID | OAuth2 client ID | - |
| OIDC_CLIENT_SECRET | OAuth2 client secret | - |
| OIDC_REDIRECT_URI | Callback URL | http://localhost:8000/api/auth/callback |
| JWT_SECRET_KEY | Token signing key | - |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | Access token TTL | 60 |
| JWT_REFRESH_TOKEN_EXPIRE_DAYS | Refresh token TTL | 7 |

## Dependencies

- **REQ-001**: Database schema (User table)

## Test Coverage

- JWT token creation and validation
- User repository CRUD operations
- Authentication endpoints
- Middleware token validation
- Error handling for invalid/expired tokens