"""
AWS Secrets Manager integration for secure credential storage.

REQ-019: Admin configuration API
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

from app.shared.config import get_settings
from app.shared.exceptions import SecretsManagerError

logger = logging.getLogger(__name__)


class SecretsManagerInterface(ABC):
    """Abstract interface for secrets management."""

    @abstractmethod
    async def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """Retrieve a secret by name."""
        pass

    @abstractmethod
    async def put_secret(self, secret_name: str, secret_value: Dict[str, Any]) -> None:
        """Store or update a secret."""
        pass

    @abstractmethod
    async def delete_secret(self, secret_name: str) -> None:
        """Delete a secret."""
        pass


class AWSSecretsManager(SecretsManagerInterface):
    """AWS Secrets Manager implementation."""

    def __init__(self, region: Optional[str] = None, prefix: Optional[str] = None):
        settings = get_settings()
        self.region = region or settings.aws_region
        self.prefix = prefix or settings.aws_secrets_manager_prefix
        self._client = None

    @property
    def client(self):
        """Lazy initialization of boto3 client."""
        if self._client is None:
            self._client = boto3.client("secretsmanager", region_name=self.region)
        return self._client

    def _get_full_secret_name(self, secret_name: str) -> str:
        """Get full secret name with prefix."""
        return f"{self.prefix}/{secret_name}"

    async def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """Retrieve a secret from AWS Secrets Manager."""
        full_name = self._get_full_secret_name(secret_name)
        try:
            response = self.client.get_secret_value(SecretId=full_name)
            secret_string = response.get("SecretString")
            if secret_string:
                return json.loads(secret_string)
            raise SecretsManagerError(
                message=f"Secret {secret_name} has no string value",
                details={"secret_name": secret_name},
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "ResourceNotFoundException":
                logger.warning(f"Secret not found: {full_name}")
                return {}
            logger.error(f"Failed to get secret {full_name}: {e}")
            raise SecretsManagerError(
                message=f"Failed to retrieve secret: {secret_name}",
                details={"secret_name": secret_name, "error": str(e)},
            )

    async def put_secret(self, secret_name: str, secret_value: Dict[str, Any]) -> None:
        """Store or update a secret in AWS Secrets Manager."""
        full_name = self._get_full_secret_name(secret_name)
        secret_string = json.dumps(secret_value)

        try:
            # Try to update existing secret
            self.client.put_secret_value(SecretId=full_name, SecretString=secret_string)
            logger.info(f"Updated secret: {full_name}")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "ResourceNotFoundException":
                # Create new secret
                try:
                    self.client.create_secret(Name=full_name, SecretString=secret_string)
                    logger.info(f"Created secret: {full_name}")
                except ClientError as create_error:
                    logger.error(f"Failed to create secret {full_name}: {create_error}")
                    raise SecretsManagerError(
                        message=f"Failed to create secret: {secret_name}",
                        details={"secret_name": secret_name, "error": str(create_error)},
                    )
            else:
                logger.error(f"Failed to update secret {full_name}: {e}")
                raise SecretsManagerError(
                    message=f"Failed to update secret: {secret_name}",
                    details={"secret_name": secret_name, "error": str(e)},
                )

    async def delete_secret(self, secret_name: str) -> None:
        """Delete a secret from AWS Secrets Manager."""
        full_name = self._get_full_secret_name(secret_name)
        try:
            self.client.delete_secret(SecretId=full_name, ForceDeleteWithoutRecovery=True)
            logger.info(f"Deleted secret: {full_name}")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code != "ResourceNotFoundException":
                logger.error(f"Failed to delete secret {full_name}: {e}")
                raise SecretsManagerError(
                    message=f"Failed to delete secret: {secret_name}",
                    details={"secret_name": secret_name, "error": str(e)},
                )


class MockSecretsManager(SecretsManagerInterface):
    """Mock secrets manager for testing."""

    def __init__(self):
        self._secrets: Dict[str, Dict[str, Any]] = {}

    async def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """Retrieve a secret from in-memory store."""
        return self._secrets.get(secret_name, {})

    async def put_secret(self, secret_name: str, secret_value: Dict[str, Any]) -> None:
        """Store a secret in in-memory store."""
        self._secrets[secret_name] = secret_value

    async def delete_secret(self, secret_name: str) -> None:
        """Delete a secret from in-memory store."""
        self._secrets.pop(secret_name, None)


def get_secrets_manager() -> SecretsManagerInterface:
    """Factory function to get secrets manager instance."""
    settings = get_settings()
    if settings.app_env == "test":
        return MockSecretsManager()
    return AWSSecretsManager()