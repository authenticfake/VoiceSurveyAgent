"""
Pytest configuration and fixtures for REQ-016 tests.

REQ-016: Email worker service
"""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment variables between tests."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)