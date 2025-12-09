"""Pytest configuration and fixtures for auth tests."""
import os
import pytest
from unittest import mock

@pytest.fixture(autouse=True)
def mock_env():
    """Mock environment variables for tests."""
    env = {
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
        "OIDC_ISSUER_URL": "https://idp.example.com",
        "OIDC_CLIENT_ID": "test-client",
        "OIDC_CLIENT_SECRET": "test-secret",
        "OIDC_JWKS_URI": "https://idp.example.com/.well-known/jwks.json",
    }
    with mock.patch.dict(os.environ, env):
        yield