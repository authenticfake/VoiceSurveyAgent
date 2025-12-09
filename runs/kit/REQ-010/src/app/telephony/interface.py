"""
Telephony provider interface definition.

REQ-009: Telephony provider adapter interface
REQ-010: Telephony webhook handler (parse_webhook_event method)
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.telephony.events import CallEvent

class CallInitiationRequest:
    """Request to initiate an outbound call."""

    def __init__(
        self,
        to_number: str,
        from_number: str,
        callback_url: str,
        call_id: str,
        campaign_id: UUID,
        contact_id: UUID,
        language: str = "en",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize call initiation request.

        Args:
            to_number: Destination phone number (E.164 format).
            from_number: Caller ID phone number.
            callback_url: URL for webhook callbacks.
            call_id: Internal call identifier.
            campaign_id: Campaign UUID.
            contact_id: Contact UUID.
            language: Call language (en/it).
            metadata: Additional metadata to pass to provider.
        """
        self.to_number = to_number
        self.from_number = from_number
        self.callback_url = callback_url
        self.call_id = call_id
        self.campaign_id = campaign_id
        self.contact_id = contact_id
        self.language = language
        self.metadata = metadata or {}

class CallInitiationResponse:
    """Response from call initiation."""

    def __init__(
        self,
        provider_call_id: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initialize call initiation response.

        Args:
            provider_call_id: Provider's unique call identifier.
            status: Initial call status from provider.
            metadata: Additional response metadata.
        """
        self.provider_call_id = provider_call_id
        self.status = status
        self.metadata = metadata or {}

class TelephonyProviderError(Exception):
    """Base exception for telephony provider errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        provider_response: dict[str, Any] | None = None,
    ) -> None:
        """Initialize telephony provider error.

        Args:
            message: Error message.
            error_code: Provider-specific error code.
            provider_response: Raw provider response.
        """
        super().__init__(message)
        self.error_code = error_code
        self.provider_response = provider_response or {}

class TelephonyProvider(ABC):
    """Abstract interface for telephony providers.

    Defines the contract that all telephony provider adapters must implement.
    This enables dependency injection and testing with mock providers.
    """

    @abstractmethod
    async def initiate_call(
        self,
        request: CallInitiationRequest,
    ) -> CallInitiationResponse:
        """Initiate an outbound call.

        Args:
            request: Call initiation request with all required parameters.

        Returns:
            Response containing provider call ID and status.

        Raises:
            TelephonyProviderError: If call initiation fails.
        """
        ...

    @abstractmethod
    def parse_webhook_event(
        self,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> CallEvent:
        """Parse a webhook payload into a domain CallEvent.

        Args:
            payload: Raw webhook payload from provider.
            headers: HTTP headers from webhook request (for signature validation).

        Returns:
            Parsed CallEvent domain object.

        Raises:
            ValueError: If payload cannot be parsed.
            TelephonyProviderError: If signature validation fails.
        """
        ...

    @abstractmethod
    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        url: str | None = None,
    ) -> bool:
        """Validate webhook signature if provider supports it.

        Args:
            payload: Raw request body bytes.
            signature: Signature header value.
            url: Request URL (some providers include in signature).

        Returns:
            True if signature is valid, False otherwise.
        """
        ...