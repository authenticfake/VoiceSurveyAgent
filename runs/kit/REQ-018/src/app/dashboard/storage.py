"""
Storage interface for CSV exports.

REQ-018: Campaign CSV export
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional
from uuid import UUID

import aioboto3
from botocore.exceptions import ClientError

from app.shared.config import get_settings
from app.shared.exceptions import StorageError

logger = logging.getLogger(__name__)
settings = get_settings()


class StorageProvider(ABC):
    """Abstract storage provider interface."""

    @abstractmethod
    async def upload_file(
        self,
        key: str,
        content: bytes,
        content_type: str = "text/csv",
    ) -> str:
        """Upload file to storage and return the key."""
        pass

    @abstractmethod
    async def generate_presigned_url(
        self,
        key: str,
        expiration_seconds: int,
    ) -> tuple[str, datetime]:
        """Generate presigned URL for download. Returns (url, expires_at)."""
        pass

    @abstractmethod
    async def delete_file(self, key: str) -> bool:
        """Delete file from storage. Returns True if successful."""
        pass

    @abstractmethod
    async def file_exists(self, key: str) -> bool:
        """Check if file exists in storage."""
        pass


class S3StorageProvider(StorageProvider):
    """AWS S3 storage provider implementation."""

    def __init__(
        self,
        bucket_name: str,
        region: str,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ):
        self.bucket_name = bucket_name
        self.region = region
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key

    def _get_session(self) -> aioboto3.Session:
        """Get aioboto3 session."""
        return aioboto3.Session(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region,
        )

    async def upload_file(
        self,
        key: str,
        content: bytes,
        content_type: str = "text/csv",
    ) -> str:
        """Upload file to S3."""
        session = self._get_session()
        try:
            async with session.client("s3") as s3:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=content,
                    ContentType=content_type,
                )
                logger.info(
                    "File uploaded to S3",
                    extra={"bucket": self.bucket_name, "key": key},
                )
                return key
        except ClientError as e:
            logger.error(
                "Failed to upload file to S3",
                extra={"bucket": self.bucket_name, "key": key, "error": str(e)},
            )
            raise StorageError(
                message=f"Failed to upload file: {str(e)}",
                operation="upload",
                details={"bucket": self.bucket_name, "key": key},
            )

    async def generate_presigned_url(
        self,
        key: str,
        expiration_seconds: int,
    ) -> tuple[str, datetime]:
        """Generate presigned URL for S3 object."""
        session = self._get_session()
        try:
            async with session.client("s3") as s3:
                url = await s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": key},
                    ExpiresIn=expiration_seconds,
                )
                expires_at = datetime.utcnow() + timedelta(seconds=expiration_seconds)
                logger.info(
                    "Generated presigned URL",
                    extra={"bucket": self.bucket_name, "key": key},
                )
                return url, expires_at
        except ClientError as e:
            logger.error(
                "Failed to generate presigned URL",
                extra={"bucket": self.bucket_name, "key": key, "error": str(e)},
            )
            raise StorageError(
                message=f"Failed to generate download URL: {str(e)}",
                operation="presign",
                details={"bucket": self.bucket_name, "key": key},
            )

    async def delete_file(self, key: str) -> bool:
        """Delete file from S3."""
        session = self._get_session()
        try:
            async with session.client("s3") as s3:
                await s3.delete_object(Bucket=self.bucket_name, Key=key)
                logger.info(
                    "File deleted from S3",
                    extra={"bucket": self.bucket_name, "key": key},
                )
                return True
        except ClientError as e:
            logger.error(
                "Failed to delete file from S3",
                extra={"bucket": self.bucket_name, "key": key, "error": str(e)},
            )
            return False

    async def file_exists(self, key: str) -> bool:
        """Check if file exists in S3."""
        session = self._get_session()
        try:
            async with session.client("s3") as s3:
                await s3.head_object(Bucket=self.bucket_name, Key=key)
                return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return False
            logger.error(
                "Failed to check file existence",
                extra={"bucket": self.bucket_name, "key": key, "error": str(e)},
            )
            return False


class InMemoryStorageProvider(StorageProvider):
    """In-memory storage provider for testing."""

    def __init__(self):
        self._storage: dict[str, bytes] = {}
        self._urls: dict[str, tuple[str, datetime]] = {}

    async def upload_file(
        self,
        key: str,
        content: bytes,
        content_type: str = "text/csv",
    ) -> str:
        """Store file in memory."""
        self._storage[key] = content
        logger.info("File stored in memory", extra={"key": key})
        return key

    async def generate_presigned_url(
        self,
        key: str,
        expiration_seconds: int,
    ) -> tuple[str, datetime]:
        """Generate mock presigned URL."""
        if key not in self._storage:
            raise StorageError(
                message="File not found",
                operation="presign",
                details={"key": key},
            )
        url = f"http://localhost/mock-storage/{key}"
        expires_at = datetime.utcnow() + timedelta(seconds=expiration_seconds)
        self._urls[key] = (url, expires_at)
        return url, expires_at

    async def delete_file(self, key: str) -> bool:
        """Delete file from memory."""
        if key in self._storage:
            del self._storage[key]
            if key in self._urls:
                del self._urls[key]
            return True
        return False

    async def file_exists(self, key: str) -> bool:
        """Check if file exists in memory."""
        return key in self._storage

    def get_content(self, key: str) -> Optional[bytes]:
        """Get file content (for testing)."""
        return self._storage.get(key)


def get_storage_provider() -> StorageProvider:
    """Get configured storage provider."""
    return S3StorageProvider(
        bucket_name=settings.s3_bucket_name,
        region=settings.aws_region,
        access_key_id=settings.aws_access_key_id,
        secret_access_key=settings.aws_secret_access_key,
    )