"""
Storage backend implementations.

REQ-022: Data retention jobs

Provides storage backends for:
- AWS S3 object storage
- Local filesystem (for development/testing)
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError

from infra.retention.interfaces import StorageBackend

logger = logging.getLogger(__name__)


class S3StorageBackend:
    """AWS S3 storage backend for recordings."""
    
    def __init__(
        self,
        bucket_name: str,
        region: str = "eu-central-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """
        Initialize S3 storage backend.
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region
            aws_access_key_id: Optional AWS access key (uses env/IAM if not provided)
            aws_secret_access_key: Optional AWS secret key
        """
        self._bucket_name = bucket_name
        self._region = region
        
        session_kwargs = {"region_name": region}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key
        
        self._client = boto3.client("s3", **session_kwargs)
    
    async def delete_object(self, key: str) -> bool:
        """Delete an object from S3."""
        try:
            self._client.delete_object(Bucket=self._bucket_name, Key=key)
            logger.debug(f"Deleted S3 object: {key}")
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                logger.warning(f"S3 object not found: {key}")
                return False
            logger.error(f"Failed to delete S3 object {key}: {e}")
            raise
    
    async def list_objects(
        self,
        prefix: str,
        older_than: Optional[datetime] = None,
    ) -> List[str]:
        """List objects with optional age filter."""
        keys = []
        paginator = self._client.get_paginator("list_objects_v2")
        
        for page in paginator.paginate(Bucket=self._bucket_name, Prefix=prefix):
            for obj in page.get("Contents", []):
                if older_than is None or obj["LastModified"].replace(tzinfo=None) < older_than:
                    keys.append(obj["Key"])
        
        return keys
    
    async def object_exists(self, key: str) -> bool:
        """Check if an object exists in S3."""
        try:
            self._client.head_object(Bucket=self._bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return False
            raise


class LocalStorageBackend:
    """Local filesystem storage backend for development/testing."""
    
    def __init__(self, base_path: str = "/tmp/recordings"):
        """
        Initialize local storage backend.
        
        Args:
            base_path: Base directory for recordings
        """
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)
    
    async def delete_object(self, key: str) -> bool:
        """Delete a file from local storage."""
        file_path = self._base_path / key
        
        if not file_path.exists():
            logger.warning(f"Local file not found: {key}")
            return False
        
        try:
            file_path.unlink()
            logger.debug(f"Deleted local file: {key}")
            return True
        except OSError as e:
            logger.error(f"Failed to delete local file {key}: {e}")
            raise
    
    async def list_objects(
        self,
        prefix: str,
        older_than: Optional[datetime] = None,
    ) -> List[str]:
        """List files with optional age filter."""
        search_path = self._base_path / prefix
        
        if not search_path.exists():
            return []
        
        keys = []
        for file_path in search_path.rglob("*"):
            if file_path.is_file():
                if older_than is None:
                    keys.append(str(file_path.relative_to(self._base_path)))
                else:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < older_than:
                        keys.append(str(file_path.relative_to(self._base_path)))
        
        return keys
    
    async def object_exists(self, key: str) -> bool:
        """Check if a file exists."""
        return (self._base_path / key).exists()