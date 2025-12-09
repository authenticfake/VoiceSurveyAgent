"""
Pytest configuration and fixtures.

REQ-010: Telephony webhook handler
"""

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

@pytest.fixture(autouse=True)
def setup_test_env() -> None:
    """Set up test environment variables."""
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
    os.environ.setdefault("TWILIO_ACCOUNT_SID", "test_sid")
    os.environ.setdefault("TWILIO_AUTH_TOKEN", "test_token")
    os.environ.setdefault("LOG_LEVEL", "DEBUG")