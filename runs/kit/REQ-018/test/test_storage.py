"""
Unit tests for storage providers.

REQ-018: Campaign CSV export
"""

from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from app.dashboard.storage import InMemoryStorageProvider
from app.shared.exceptions import StorageError


class TestInMemoryStorageProvider:
    """Tests for InMemoryStorageProvider."""

    @pytest_asyncio.fixture
    async def storage(self) -> InMemoryStorageProvider:
        """Create in-memory storage provider."""
        return InMemoryStorageProvider()

    @pytest.mark.asyncio
    async def test_upload_file(self, storage: InMemoryStorageProvider):
        """Test uploading a file."""
        content = b"test,data\n1,2"
        key = await storage.upload_file(
            key="test/file.csv",
            content=content,
            content_type="text/csv",
        )

        assert key == "test/file.csv"
        assert storage.get_content(key) == content

    @pytest.mark.asyncio
    async def test_generate_presigned_url(self, storage: InMemoryStorageProvider):
        """Test generating presigned URL."""
        content = b"test content"
        key = await storage.upload_file(key="test/file.csv", content=content)

        url, expires_at = await storage.generate_presigned_url(
            key=key,
            expiration_seconds=3600,
        )

        assert url is not None
        assert "test/file.csv" in url
        assert expires_at > datetime.utcnow()
        assert expires_at < datetime.utcnow() + timedelta(seconds=3601)

    @pytest.mark.asyncio
    async def test_generate_presigned_url_file_not_found(
        self,
        storage: InMemoryStorageProvider,
    ):
        """Test generating presigned URL for non-existent file."""
        with pytest.raises(StorageError) as exc_info:
            await storage.generate_presigned_url(
                key="nonexistent/file.csv",
                expiration_seconds=3600,
            )
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_delete_file(self, storage: InMemoryStorageProvider):
        """Test deleting a file."""
        content = b"test content"
        key = await storage.upload_file(key="test/file.csv", content=content)

        result = await storage.delete_file(key)

        assert result is True
        assert storage.get_content(key) is None

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, storage: InMemoryStorageProvider):
        """Test deleting non-existent file."""
        result = await storage.delete_file("nonexistent/file.csv")
        assert result is False

    @pytest.mark.asyncio
    async def test_file_exists(self, storage: InMemoryStorageProvider):
        """Test checking file existence."""
        content = b"test content"
        key = await storage.upload_file(key="test/file.csv", content=content)

        assert await storage.file_exists(key) is True
        assert await storage.file_exists("nonexistent/file.csv") is False