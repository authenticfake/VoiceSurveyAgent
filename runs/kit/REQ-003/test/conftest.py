"""
Pytest configuration and fixtures for REQ-003 tests.
"""

import pytest
from uuid import uuid4

from app.auth.schemas import UserRole


@pytest.fixture
def mock_user_id():
    """Generate a mock user ID."""
    return uuid4()


@pytest.fixture
def mock_oidc_sub():
    """Generate a mock OIDC subject."""
    return f"oidc-sub-{uuid4().hex[:8]}"