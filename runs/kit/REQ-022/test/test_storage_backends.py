"""
Tests for storage backends.

REQ-022: Data retention jobs
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from infra.retention.storage import LocalStorageBackend


class TestLocalStorageBackend:
    """Tests for LocalStorageBackend."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def storage(self, temp_dir):
        """Create storage backend with temp directory."""
        return LocalStorageBackend(base_path=temp_dir)
    
    @pytest.mark.asyncio
    async def test_delete_existing_object(self, storage, temp_dir):
        """Test deleting an existing file."""
        # Create test file
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        result = await storage.delete_object("test.txt")
        
        assert result is True
        assert not test_file.exists()
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_object(self, storage):
        """Test deleting a non-existent file."""
        result = await storage.delete_object("nonexistent.txt")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_object_exists_true(self, storage, temp_dir):
        """Test checking existence of existing file."""
        test_file = Path(temp_dir) / "exists.txt"
        test_file.write_text("content")
        
        result = await storage.object_exists("exists.txt")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_object_exists_false(self, storage):
        """Test checking existence of non-existent file."""
        result = await storage.object_exists("missing.txt")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_objects(self, storage, temp_dir):
        """Test listing objects."""
        # Create test files
        subdir = Path(temp_dir) / "recordings"
        subdir.mkdir()
        (subdir / "file1.wav").write_text("content1")
        (subdir / "file2.wav").write_text("content2")
        
        result = await storage.list_objects("recordings")
        
        assert len(result) == 2
        assert "recordings/file1.wav" in result or "recordings\\file1.wav" in result
    
    @pytest.mark.asyncio
    async def test_list_objects_empty_prefix(self, storage):
        """Test listing with non-existent prefix."""
        result = await storage.list_objects("nonexistent")
        
        assert len(result) == 0