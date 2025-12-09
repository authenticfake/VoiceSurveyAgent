"""
Pytest configuration and fixtures for REQ-007 tests.
"""

import os
import sys

import pytest

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Also add parent kit directories for shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "REQ-001", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "REQ-002", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "REQ-003", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "REQ-004", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "REQ-005", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "REQ-006", "src"))


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio backend for async tests."""
    return "asyncio"