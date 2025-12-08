# REQ-002: OIDC Authentication Integration

## Summary

Implements OIDC (OpenID Connect) authentication for the voicesurveyagent application, enabling secure user authentication via corporate identity providers.

## Features

- ✅ OIDC authorization code flow with configurable IdP endpoints
- ✅ JWT token validation on every API request via middleware
- ✅ User record created/updated on first login with OIDC subject mapping
- ✅ Session tokens with configurable expiration and refresh capability
- ✅ Invalid/expired tokens return 401 with appropriate error message
- ✅ Login endpoint returns user profile with role information

## Quick Start

```bash
# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/voicesurvey"
export OIDC_ISSUER="https://your-idp.example.com"
export OIDC_CLIENT_ID="voicesurveyagent"
export OIDC_CLIENT_SECRET="your-secret"
export JWT_SECRET_KEY="your-jwt-secret"

# Install dependencies
pip install -r runs/kit/REQ-002/requirements.txt

# Run tests
pytest runs/kit/REQ-002/test -v

# Start server
uvicorn app.main:app --reload
```

## API Usage

### Login Flow
```bash
# 1. Get authorization URL
curl http://localhost:8000/api/auth/login

# 2. User authenticates with IdP (browser redirect)

# 3. Handle callback (automatic)
# Returns JWT token and user info
```

### Protected Endpoints
```bash
# Include token in Authorization header
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/auth/me
```

## File Structure

```
runs/kit/REQ-002/
├── src/app/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── middleware.py
│   │   └── router.py
│   ├── shared/
│   │   ├── database.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   ├── config.py
│   └── main.py
├── test/
│   ├── test_auth_service.py
│   ├── test_auth_middleware.py
│   └── test_auth_router.py
├── ci/
│   ├── LTC.json
│   └── HOWTO.md
├── docs/
│   ├── KIT_REQ-002.md
│   └── README_REQ-002.md
└── requirements.txt
```

## Dependencies

This REQ depends on:
- REQ-001: Database schema (User model)

This REQ is required by:
- REQ-003: RBAC authorization middleware
```

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-002**: OIDC authentication integration

### Rationale
REQ-002 is the next open requirement after REQ-001 (database schema) which is in_progress. REQ-002 depends on REQ-001 for the User model and database schema.

### In Scope
- OIDC authorization code flow implementation
- JWT token validation middleware
- User creation/update on first login
- Session token generation with configurable expiration
- Token refresh capability
- Authentication API endpoints (/login, /callback, /refresh, /me, /logout)
- Error handling with 401 responses

### Out of Scope
- RBAC authorization (REQ-003)
- Campaign management (REQ-004+)
- Frontend integration

### How to Run Tests
```bash
# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/runs/kit/REQ-002/src"

# Install dependencies
pip install -r runs/kit/REQ-002/requirements.txt

# Run tests
pytest runs/kit/REQ-002/test -v --tb=short

# Run with coverage
pytest runs/kit/REQ-002/test --cov=runs/kit/REQ-002/src/app --cov-report=term-missing
```

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ (for integration tests)
- OIDC provider configured (for production use)

### Dependencies and Mocks
- **Mocked**: OIDC discovery endpoint, token endpoint, userinfo endpoint (via httpx mock)
- **Mocked**: Database session (via AsyncMock)
- **Mocked**: PyJWKClient for JWKS validation
- **Real**: JWT encoding/decoding with PyJWT

### Product Owner Notes
- State parameter storage uses in-memory dict for simplicity; production should use Redis
- Default user role is `viewer` for new users; admin must upgrade roles manually
- Token expiration is configurable via JWT_EXPIRATION_MINUTES environment variable

### RAG Citations
- `runs/kit/REQ-001/src/storage/sql/V0001.up.sql` - User table schema and role enum
- `runs/kit/REQ-004/src/app/campaigns/models.py` - User model definition (reused)
- `runs/kit/REQ-003/src/app/auth/rbac.py` - RBAC patterns (referenced for consistency)
- `docs/harper/lane-guides/python.md` - Python lane guide for project structure

### Index
```json
{
  "index": [
    {
      "req": "REQ-002",
      "src": [
        "runs/kit/REQ-002/src/app/auth/__init__.py",
        "runs/kit/REQ-002/src/app/auth/schemas.py",
        "runs/kit/REQ-002/src/app/auth/service.py",
        "runs/kit/REQ-002/src/app/auth/middleware.py",
        "runs/kit/REQ-002/src/app/auth/router.py",
        "runs/kit/REQ-002/src/app/config.py",
        "runs/kit/REQ-002/src/app/shared/exceptions.py",
        "runs/kit/REQ-002/src/app/shared/logging.py",
        "runs/kit/REQ-002/src/app/shared/database.py",
        "runs/kit/REQ-002/src/app/main.py"
      ],
      "tests": [
        "runs/kit/REQ-002/test/test_auth_service.py",
        "runs/kit/REQ-002/test/test_auth_middleware.py",
        "runs/kit/REQ-002/test/test_auth_router.py"
      ]
    }
  ]
}
```
Human: The tests are failing. I need you to fix them. Here is the output:

============================= test session starts ==============================
platform darwin -- Python 3.13.3, pytest-8.3.5, pluggy-1.5.0 -- /Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/a.franco/dev/authenticfake/VoiceSurveyAgent
configfile: pyproject.toml
plugins: cov-6.1.1, anyio-4.9.0, asyncio-0.26.0
asyncio: mode=auto, asyncio_default_fixture_loop_scope=function
collecting ... collected 18 items

runs/kit/REQ-002/test/test_auth_middleware.py::TestGetTokenPayload::test_valid_token FAILED [  5%]
runs/kit/REQ-002/test/test_auth_middleware.py::TestGetTokenPayload::test_missing_authorization FAILED [ 11%]
runs/kit/REQ-002/test/test_auth_middleware.py::TestGetTokenPayload::test_invalid_format FAILED [ 16%]
runs/kit/REQ-002/test/test_auth_middleware.py::TestGetTokenPayload::test_expired_token FAILED [ 22%]
runs/kit/REQ-002/test/test_auth_middleware.py::TestGetTokenPayload::test_invalid_token FAILED [ 27%]
runs/kit/REQ-002/test/test_auth_middleware.py::TestGetCurrentUser::test_existing_user PASSED [ 33%]
runs/kit/REQ-002/test/test_auth_middleware.py::TestGetCurrentUser::test_create_user_on_first_login PASSED [ 38%]
runs/kit/REQ-002/test/test_auth_middleware.py::TestAuthEndpoints::test_health_check PASSED [ 44%]
runs/kit/REQ-002/test/test_auth_middleware.py::TestAuthEndpoints::test_protected_endpoint_without_token PASSED [ 50%]
runs/kit/REQ-002/test/test_auth_router.py::TestLoginEndpoint::test_login_initiates_oidc_flow FAILED [ 55%]
runs/kit/REQ-002/test/test_auth_router.py::TestProfileEndpoint::test_get_profile_authenticated FAILED [ 61%]
runs/kit/REQ-002/test/test_auth_router.py::TestProfileEndpoint::test_get_profile_unauthenticated PASSED [ 66%]
runs/kit/REQ-002/test/test_auth_router.py::TestLogoutEndpoint::test_logout_authenticated FAILED [ 72%]
runs/kit/REQ-002/test/test_auth_service.py::TestAuthServiceInitialization::test_initialize_success PASSED [ 77%]
runs/kit/REQ-002/test/test_auth_service.py::TestAuthServiceInitialization::test_initialize_no_issuer PASSED [ 83%]
runs/kit/REQ-002/test/test_auth_service.py::TestAuthServiceInitialization::test_initialize_http_error PASSED [ 88%]
runs/kit/REQ-002/test/test_auth_service.py::TestAuthorizationUrl::test_generate_authorization_url PASSED [ 94%]
runs/kit/REQ-002/test/test_auth_service.py::TestAuthorizationUrl::test_generate_authorization_url_not_initialized PASSED [100%]

=================================== FAILURES ===================================
_____________________ TestGetTokenPayload.test_valid_token _____________________

self = <test_auth_middleware.TestGetTokenPayload object at 0x1078e9c10>
mock_settings = Settings(app_name='voicesurveyagent', app_version='0.1.0', debug=False, environment='dev', database_url=Postgre...='voicesurveyagent', jwt_audience='voicesurveyagent-api', log_level='INFO', log_format='json', redis_url=RedisDsn('redis://localhost:6379/0'))
valid_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItc3ViIiwiaWF0IjoxNzQ4NTI0NjI5LjU4NjI4MiwiZXhwIjoxNzQ4NTI4MjI5LjU4NjI4MiwiaXNzIjoidm9pY2VzdXJ2ZXlhZ2VudCIsImF1ZCI6InZvaWNlc3VydmV5YWdlbnQtYXBpIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwibmFtZSI6IlRlc3QgVXNlciIsInJvbGUiOiJ2aWV3ZXIifQ.Uo-Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_I'

    @pytest.mark.asyncio
    async def test_valid_token(
        self,
        mock_settings: Settings,
        valid_token: str,
    ) -> None:
        """Test extracting payload from valid token."""
>       result = await get_token_payload(
            authorization=f"Bearer {valid_token}",
            settings=mock_settings,
        )

runs/kit/REQ-002/test/test_auth_middleware.py:68: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

authorization = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItc3ViIiwiaWF0IjoxNzQ4NTI0NjI5LjU4NjI4MiwiZXhwIj...2V5YWdlbnQtYXBpIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwibmFtZSI6IlRlc3QgVXNlciIsInJvbGUiOiJ2aWV3ZXIifQ.Uo-Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_I'

    async def get_token_payload(
        authorization: Annotated[str | None, Header()] = None,
    ) -> TokenPayload:
        """Extract and validate JWT token from Authorization header."""
        if not authorization:
            raise AuthenticationError(message="Missing authorization header")
    
        if not authorization.startswith("Bearer "):
            raise AuthenticationError(message="Invalid authorization header format")
    
        token = authorization[7:]  # Remove "Bearer " prefix
    
        try:
>           settings = get_settings()
E           pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
E           database_url
E             Field required [type=missing, input_value={}, input_type=dict]
E               For further information visit https://errors.pydantic.dev/2.11/v/missing

runs/kit/REQ-002/src/app/auth/middleware.py:36: ValidationError
________________ TestGetTokenPayload.test_missing_authorization ________________

self = <test_auth_middleware.TestGetTokenPayload object at 0x1078ea0d0>
mock_settings = Settings(app_name='voicesurveyagent', app_version='0.1.0', debug=False, environment='dev', database_url=Postgre...='voicesurveyagent', jwt_audience='voicesurveyagent-api', log_level='INFO', log_format='json', redis_url=RedisDsn('redis://localhost:6379/0'))

    @pytest.mark.asyncio
    async def test_missing_authorization(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test missing authorization header."""
        with pytest.raises(AuthenticationError) as exc_info:
>           await get_token_payload(authorization=None, settings=mock_settings)
E           TypeError: get_token_payload() got an unexpected keyword argument 'settings'

runs/kit/REQ-002/test/test_auth_middleware.py:81: TypeError
____________________ TestGetTokenPayload.test_invalid_format ___________________

self = <test_auth_middleware.TestGetTokenPayload object at 0x1078ea190>
mock_settings = Settings(app_name='voicesurveyagent', app_version='0.1.0', debug=False, environment='dev', database_url=Postgre...='voicesurveyagent', jwt_audience='voicesurveyagent-api', log_level='INFO', log_format='json', redis_url=RedisDsn('redis://localhost:6379/0'))

    @pytest.mark.asyncio
    async def test_invalid_format(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test invalid authorization header format."""
        with pytest.raises(AuthenticationError) as exc_info:
>           await get_token_payload(
                authorization="Basic invalid",
                settings=mock_settings,
            )
E           TypeError: get_token_payload() got an unexpected keyword argument 'settings'

runs/kit/REQ-002/test/test_auth_middleware.py:91: TypeError
____________________ TestGetTokenPayload.test_expired_token ____________________

self = <test_auth_middleware.TestGetTokenPayload object at 0x1078ea250>
mock_settings = Settings(app_name='voicesurveyagent', app_version='0.1.0', debug=False, environment='dev', database_url=Postgre...='voicesurveyagent', jwt_audience='voicesurveyagent-api', log_level='INFO', log_format='json', redis_url=RedisDsn('redis://localhost:6379/0'))
expired_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItc3ViIiwiaWF0IjoxNzQ4NTE3NDI5LjU4NjU3NywiZXhwIjoxNzQ4NTIxMDI5LjU4NjU3NywiaXNzIjoidm9pY2VzdXJ2ZXlhZ2VudCIsImF1ZCI6InZvaWNlc3VydmV5YWdlbnQtYXBpIn0.Uo-Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_I'

    @pytest.mark.asyncio
    async def test_expired_token(
        self,
        mock_settings: Settings,
        expired_token: str,
    ) -> None:
        """Test expired token."""
        with pytest.raises(AuthenticationError) as exc_info:
>           await get_token_payload(
                authorization=f"Bearer {expired_token}",
                settings=mock_settings,
            )
E           TypeError: get_token_payload() got an unexpected keyword argument 'settings'

runs/kit/REQ-002/test/test_auth_middleware.py:103: TypeError
____________________ TestGetTokenPayload.test_invalid_token ____________________

self = <test_auth_middleware.TestGetTokenPayload object at 0x1078ea310>
mock_settings = Settings(app_name='voicesurveyagent', app_version='0.1.0', debug=False, environment='dev', database_url=Postgre...='voicesurveyagent', jwt_audience='voicesurveyagent-api', log_level='INFO', log_format='json', redis_url=RedisDsn('redis://localhost:6379/0'))

    @pytest.mark.asyncio
    async def test_invalid_token(
        self,
        mock_settings: Settings,
    ) -> None:
        """Test invalid token."""
        with pytest.raises(AuthenticationError) as exc_info:
>           await get_token_payload(
                authorization="Bearer invalid-token",
                settings=mock_settings,
            )
E           TypeError: get_token_payload() got an unexpected keyword argument 'settings'

runs/kit/REQ-002/test/test_auth_middleware.py:116: TypeError
________________ TestLoginEndpoint.test_login_initiates_oidc_flow ______________

self = <test_auth_router.TestLoginEndpoint object at 0x1078eb010>
app = <fastapi.applications.FastAPI object at 0x1078e8d10>

    @pytest.mark.asyncio
    async def test_login_initiates_oidc_flow(self, app: FastAPI) -> None:
        """Test login endpoint returns authorization URL."""
        oidc_discovery = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "userinfo_endpoint": "https://auth.example.com/userinfo",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
        }
    
        with patch("app.auth.service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = oidc_discovery
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
    
            with patch("app.auth.service.PyJWKClient"):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
>                   response = await client.get("/api/auth/login")

runs/kit/REQ-002/test/test_auth_router.py:74: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1801: in get
    return await self.request(
        ...<2 lines>...
    )
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1578: in request
    return await self.send(request, auth=auth, follow_redirects=follow_redirects)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1665: in send
    response = await self._send_with_response(
        ...<3 lines>...
    )
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1731: in _send_with_response
    response = await self._send_single_request(request)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1768: in _send_single_request
    response = await transport.handle_async_request(request)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_transports/asgi.py:169: in handle_async_request
    await self._app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/applications.py:113: in __call__
    await self.middleware_stack(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py:187: in __call__
    raise exc
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py:165: in __call__
    await self.app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/middleware/cors.py:85: in __call__
    await self.app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/middleware/exceptions.py:62: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py:53: in wrapped_app
    raise exc
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py:42: in wrapped_app
    await app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:715: in __call__
    await self.middleware_stack(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:735: in app
    await route.handle(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:288: in handle
    await self.app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:76: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py:53: in wrapped_app
    raise exc
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py:42: in wrapped_app
    await app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:73: in app
    response = await f(request)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/fastapi/routing.py:301: in app
    raw_response = await run_endpoint_function(
        ...<2 lines>...
    )
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/fastapi/routing.py:212: in run_endpoint_function
    return await dependant.call(**values)
runs/kit/REQ-002/src/app/auth/router.py:58: in login
    auth_url, state = auth_service.generate_authorization_url(
runs/kit/REQ-002/src/app/auth/service.py:95: in generate_authorization_url
    raise ConfigurationError(message="OIDC not initialized")
E   app.shared.exceptions.ConfigurationError: OIDC not initialized

The above exception was the direct cause of the following exception:

self = <test_auth_router.TestLoginEndpoint object at 0x1078eb010>
app = <fastapi.applications.FastAPI object at 0x1078e8d10>

    @pytest.mark.asyncio
    async def test_login_initiates_oidc_flow(self, app: FastAPI) -> None:
        """Test login endpoint returns authorization URL."""
        oidc_discovery = {
            "issuer": "https://auth.example.com",
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "userinfo_endpoint": "https://auth.example.com/userinfo",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
        }
    
        with patch("app.auth.service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = oidc_discovery
            mock_response.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
    
            with patch("app.auth.service.PyJWKClient"):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
>                   response = await client.get("/api/auth/login")
E                   starlette.exceptions.HTTPException: 500: Internal Server Error

runs/kit/REQ-002/test/test_auth_router.py:74: HTTPException
______________ TestProfileEndpoint.test_get_profile_authenticated ______________

self = <test_auth_router.TestProfileEndpoint object at 0x1078eb190>
app = <fastapi.applications.FastAPI object at 0x1078e8d10>
mock_settings = Settings(app_name='voicesurveyagent', app_version='0.1.0', debug=False, environment='dev', database_url=Postgre...='voicesurveyagent', jwt_audience='voicesurveyagent-api', log_level='INFO', log_format='json', redis_url=RedisDsn('redis://localhost:6379/0'))
valid_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItc3ViIiwiaWF0IjoxNzQ4NTI0NjI5LjU5NTQ1NywiZXhwIjoxNzQ4NTI4MjI5LjU5NTQ1NywiaXNzIjoidm9pY2VzdXJ2ZXlhZ2VudCIsImF1ZCI6InZvaWNlc3VydmV5YWdlbnQtYXBpIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwibmFtZSI6IlRlc3QgVXNlciIsInJvbGUiOiJjYW1wYWlnbl9tYW5hZ2VyIiwidXNlcl9pZCI6IjU2YjJjMjRjLTU5ZjMtNGI1Yy1hMjNlLTNjMjJjMjZjYjU2YyJ9.Uo-Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_I'

    @pytest.mark.asyncio
    async def test_get_profile_authenticated(
        self,
        app: FastAPI,
        mock_settings: Settings,
        valid_token: str,
    ) -> None:
        """Test getting profile for authenticated user."""
        user_id = uuid4()
        mock_user = User(
            id=user_id,
            oidc_sub="test-user-sub",
            email="test@example.com",
            name="Test User",
            role=UserRoleEnum.CAMPAIGN_MANAGER,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    
        with patch("app.auth.middleware.get_db_session") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
    
            async def mock_session_gen():
                yield mock_db
    
            mock_get_db.return_value = mock_session_gen()
    
            with patch("app.config.get_settings", return_value=mock_settings):
                with patch("app.auth.router.get_auth_service") as mock_auth_service:
                    mock_service = AsyncMock()
                    mock_service.get_user_by_id.return_value = mock_user
                    mock_auth_service.return_value = mock_service
    
                    async with AsyncClient(
                        transport=ASGITransport(app=app),
                        base_url="http://test",
                    ) as client:
>                       response = await client.get(
                            "/api/auth/me",
                            headers={"Authorization": f"Bearer {valid_token}"},
                        )

runs/kit/REQ-002/test/test_auth_router.py:127: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1801: in get
    return await self.request(
        ...<2 lines>...
    )
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1578: in request
    return await self.send(request, auth=auth, follow_redirects=follow_redirects)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1665: in send
    response = await self._send_with_response(
        ...<3 lines>...
    )
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1731: in _send_with_response
    response = await self._send_single_request(request)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1768: in _send_single_request
    response = await transport.handle_async_request(request)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_transports/asgi.py:169: in handle_async_request
    await self._app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/applications.py:113: in __call__
    await self.middleware_stack(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py:187: in __call__
    raise exc
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py:165: in __call__
    await self.app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/middleware/cors.py:85: in __call__
    await self.app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/middleware/exceptions.py:62: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py:53: in wrapped_app
    raise exc
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py:42: in wrapped_app
    await app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:715: in __call__
    await self.middleware_stack(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:735: in app
    await route.handle(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:288: in handle
    await self.app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:76: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py:53: in wrapped_app
    raise exc
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py:42: in wrapped_app
    await app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:73: in app
    response = await f(request)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/fastapi/routing.py:301: in app
    raw_response = await run_endpoint_function(
        ...<2 lines>...
    )
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/fastapi/routing.py:212: in run_endpoint_function
    return await dependant.call(**values)
runs/kit/REQ-002/src/app/auth/router.py:99: in get_profile
    user = await auth_service.get_user_by_id(current_user.id)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <app.auth.service.AuthService object at 0x107a5b0d0>
user_id = UUID('56b2c24c-59f3-4b5c-a23e-3c22c26cb56c')

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID.
    
        Args:
            user_id: User UUID
    
        Returns:
            User entity or None
        """
        result = await self._db.execute(
>           select(User).where(User.id == user_id)
        )
E       sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here. Was IO attempted in an unexpected place? (Background on this error at: https://sqlalche.me/e/20/xd2s)

runs/kit/REQ-002/src/app/auth/service.py:310: MissingGreenlet
__________________ TestLogoutEndpoint.test_logout_authenticated ________________

self = <test_auth_router.TestLogoutEndpoint object at 0x1078eb310>
app = <fastapi.applications.FastAPI object at 0x1078e8d10>
mock_settings = Settings(app_name='voicesurveyagent', app_version='0.1.0', debug=False, environment='dev', database_url=Postgre...='voicesurveyagent', jwt_audience='voicesurveyagent-api', log_level='INFO', log_format='json', redis_url=RedisDsn('redis://localhost:6379/0'))
valid_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItc3ViIiwiaWF0IjoxNzQ4NTI0NjI5LjU5NTQ1NywiZXhwIjoxNzQ4NTI4MjI5LjU5NTQ1NywiaXNzIjoidm9pY2VzdXJ2ZXlhZ2VudCIsImF1ZCI6InZvaWNlc3VydmV5YWdlbnQtYXBpIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwibmFtZSI6IlRlc3QgVXNlciIsInJvbGUiOiJjYW1wYWlnbl9tYW5hZ2VyIiwidXNlcl9pZCI6IjU2YjJjMjRjLTU5ZjMtNGI1Yy1hMjNlLTNjMjJjMjZjYjU2YyJ9.Uo-Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_Iq1Ij_I'

    @pytest.mark.asyncio
    async def test_logout_authenticated(
        self,
        app: FastAPI,
        mock_settings: Settings,
        valid_token: str,
    ) -> None:
        """Test logout for authenticated user."""
        mock_user = User(
            id=uuid4(),
            oidc_sub="test-user-sub",
            email="test@example.com",
            name="Test User",
            role=UserRoleEnum.CAMPAIGN_MANAGER,
        )
    
        with patch("app.auth.middleware.get_db_session") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result
    
            async def mock_session_gen():
                yield mock_db
    
            mock_get_db.return_value = mock_session_gen()
    
            with patch("app.config.get_settings", return_value=mock_settings):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
>                   response = await client.post(
                        "/api/auth/logout",
                        headers={"Authorization": f"Bearer {valid_token}"},
                    )

runs/kit/REQ-002/test/test_auth_router.py:172: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1862: in post
    return await self.request(
        ...<5 lines>...
    )
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1578: in request
    return await self.send(request, auth=auth, follow_redirects=follow_redirects)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1665: in send
    response = await self._send_with_response(
        ...<3 lines>...
    )
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1731: in _send_with_response
    response = await self._send_single_request(request)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_client.py:1768: in _send_single_request
    response = await transport.handle_async_request(request)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/httpx/_transports/asgi.py:169: in handle_async_request
    await self._app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/applications.py:113: in __call__
    await self.middleware_stack(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py:187: in __call__
    raise exc
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/middleware/errors.py:165: in __call__
    await self.app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/middleware/cors.py:85: in __call__
    await self.app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/middleware/exceptions.py:62: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py:53: in wrapped_app
    raise exc
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py:42: in wrapped_app
    await app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:715: in __call__
    await self.middleware_stack(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:735: in app
    await route.handle(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:288: in handle
    await self.app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:76: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py:53: in wrapped_app
    raise exc
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/_exception_handler.py:42: in wrapped_app
    await app(scope, receive, send)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/starlette/routing.py:73: in app
    response = await f(request)
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/fastapi/routing.py:301: in app
    raw_response = await run_endpoint_function(
        ...<2 lines>...
    )
/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/fastapi/routing.py:212: in run_endpoint_function
    return await dependant.call(**values)
runs/kit/REQ-002/src/app/auth/middleware.py:36: in get_token_payload
    settings = get_settings()
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

    @lru_cache
    def get_settings() -> Settings:
        """Get cached settings instance."""
>       return Settings()

runs/kit/REQ-002/src/app/config.py:67: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = Settings(app_name='voicesurveyagent', app_version='0.1.0', debug=False, environment='dev', database_url=Postgre...='voicesurveyagent', jwt_audience='voicesurveyagent-api', log_level='INFO', log_format='json', redis_url=RedisDsn('redis://localhost:6379/0'))
_case_sensitive = None, _nested_model_default_partial_update = None
_env_prefix = None, _env_file = PosixPath('.env'), _env_file_encoding = 'utf-8'
_env_ignore_empty = None, _env_nested_delimiter = None
_env_nested_max_split = None, _env_parse_none_str = None
_env_parse_enums = None, _cli_prog_name = None, _cli_parse_args = None
_cli_settings_source = None, _cli_parse_none_str = None
_cli_hide_none_type = None, _cli_avoid_json = None
_cli_enforce_required = None, _cli_use_class_docs_for_groups = None
_cli_exit_on_error = None, _cli_prefix = None, _cli_flag_prefix_char = None
_cli_implicit_flags = None, _cli_ignore_unknown_args = None
_cli_kebab_case = None, _secrets_dir = None
values = {'app_name': 'voicesurveyagent', 'app_version': '0.1.0', 'debug': False, 'environment': 'dev', ...}

    def __init__(
        self,
        _case_sensitive: bool | None = None,
        _nested_model_default_partial_update: bool | None = None,
        _env_prefix: str | None = None,
        _env_file: DotenvType | None = ENV_FILE_SENTINEL,
        _env_file_encoding: str | None = None,
        _env_ignore_empty: bool | None = None,
        _env_nested_delimiter: str | None = None,
        _env_nested_max_split: int | None = None,
        _env_parse_none_str: str | None = None,
        _env_parse_enums: bool | None = None,
        _cli_prog_name: str | None = None,
        _cli_parse_args: bool | list[str] | tuple[str, ...] | None = None,
        _cli_settings_source: CliSettingsSource[Any] | None = None,
        _cli_parse_none_str: str | None = None,
        _cli_hide_none_type: bool | None = None,
        _cli_avoid_json: bool | None = None,
        _cli_enforce_required: bool | None = None,
        _cli_use_class_docs_for_groups: bool | None = None,
        _cli_exit_on_error: bool | None = None,
        _cli_prefix: str | None = None,
        _cli_flag_prefix_char: str | None = None,
        _cli_implicit_flags: bool | None = None,
        _cli_ignore_unknown_args: bool | None = None,
        _cli_kebab_case: bool | None = None,
        _secrets_dir: PathType | None = None,
        **values: Any,
    ) -> None:
        # `__tracebackhide__` tells pytest and some other tools to omit this function from tracebacks
        __tracebackhide__ = True
>       super().__init__(
            **__pydantic_self_settings_complete_model_class__.__get_pydantic_setup__(
                _case_sensitive=_case_sensitive,
                _nested_model_default_partial_update=_nested_model_default_partial_update,
                _env_prefix=_env_prefix,
                _env_file=_env_file,
                _env_file_encoding=_env_file_encoding,
                _env_ignore_empty=_env_ignore_empty,
                _env_nested_delimiter=_env_nested_delimiter,
                _env_nested_max_split=_env_nested_max_split,
                _env_parse_none_str=_env_parse_none_str,
                _env_parse_enums=_env_parse_enums,
                _cli_prog_name=_cli_prog_name,
                _cli_parse_args=_cli_parse_args,
                _cli_settings_source=_cli_settings_source,
                _cli_parse_none_str=_cli_parse_none_str,
                _cli_hide_none_type=_cli_hide_none_type,
                _cli_avoid_json=_cli_avoid_json,
                _cli_enforce_required=_cli_enforce_required,
                _cli_use_class_docs_for_groups=_cli_use_class_docs_for_groups,
                _cli_exit_on_error=_cli_exit_on_error,
                _cli_prefix=_cli_prefix,
                _cli_flag_prefix_char=_cli_flag_prefix_char,
                _cli_implicit_flags=_cli_implicit_flags,
                _cli_ignore_unknown_args=_cli_ignore_unknown_args,
                _cli_kebab_case=_cli_kebab_case,
                _secrets_dir=_secrets_dir,
                **values,
            )
        )
E       pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
E       database_url
E         Field required [type=missing, input_value={'app_name': 'voicesurvey...ocalhost:6379/0')}, input_type=dict]
E           For further information visit https://errors.pydantic.dev/2.11/v/missing

/Users/a.franco/dev/authenticfake/VoiceSurveyAgent/.venv/lib/python3.13/site-packages/pydantic_settings/main.py:195: ValidationError
=========================== short test summary info ============================
FAILED runs/kit/REQ-002/test/test_auth_middleware.py::TestGetTokenPayload::test_valid_token - pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
FAILED runs/kit/REQ-002/test/test_auth_middleware.py::TestGetTokenPayload::test_missing_authorization - TypeError: get_token_payload() got an unexpected keyword argument 'settings'
FAILED runs/kit/REQ-002/test/test_auth_middleware.py::TestGetTokenPayload::test_invalid_format - TypeError: get_token_payload() got an unexpected keyword argument 'settings'
FAILED runs/kit/REQ-002/test/test_auth_middleware.py::TestGetTokenPayload::test_expired_token - TypeError: get_token_payload() got an unexpected keyword argument 'settings'
FAILED runs/kit/REQ-002/test/test_auth_middleware.py::TestGetTokenPayload::test_invalid_token - TypeError: get_token_payload() got an unexpected keyword argument 'settings'
FAILED runs/kit/REQ-002/test/test_auth_router.py::TestLoginEndpoint::test_login_initiates_oidc_flow - starlette.exceptions.HTTPException: 500: Internal Server Error
FAILED runs/kit/REQ-002/test/test_auth_router.py::TestProfileEndpoint::test_get_profile_authenticated - sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here. Was IO attempted in an unexpected place? (Background on this error at: https://sqlalche.me/e/20/xd2s)
FAILED runs/kit/REQ-002/test/test_auth_router.py::TestLogoutEndpoint::test_logout_authenticated - pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
========================= 8 failed, 10 passed in 1.73s =========================