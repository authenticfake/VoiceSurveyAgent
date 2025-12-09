"""
Secrets Manager tests for REQ-019: Admin configuration API
"""

import pytest

from app.admin.secrets import MockSecretsManager


@pytest.mark.asyncio
class TestMockSecretsManager:
    """Tests for MockSecretsManager."""

    async def test_put_and_get_secret(self):
        """Test storing and retrieving a secret."""
        manager = MockSecretsManager()

        await manager.put_secret("test-secret", {"key": "value"})
        result = await manager.get_secret("test-secret")

        assert result == {"key": "value"}

    async def test_get_nonexistent_secret(self):
        """Test retrieving a nonexistent secret returns empty dict."""
        manager = MockSecretsManager()

        result = await manager.get_secret("nonexistent")

        assert result == {}

    async def test_update_existing_secret(self):
        """Test updating an existing secret."""
        manager = MockSecretsManager()

        await manager.put_secret("test-secret", {"key1": "value1"})
        await manager.put_secret("test-secret", {"key1": "updated", "key2": "value2"})

        result = await manager.get_secret("test-secret")

        assert result == {"key1": "updated", "key2": "value2"}

    async def test_delete_secret(self):
        """Test deleting a secret."""
        manager = MockSecretsManager()

        await manager.put_secret("test-secret", {"key": "value"})
        await manager.delete_secret("test-secret")

        result = await manager.get_secret("test-secret")

        assert result == {}

    async def test_delete_nonexistent_secret(self):
        """Test deleting a nonexistent secret doesn't raise."""
        manager = MockSecretsManager()

        # Should not raise
        await manager.delete_secret("nonexistent")