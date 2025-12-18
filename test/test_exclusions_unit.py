"""
Unit tests for exclusion list management.

REQ-007: Exclusion list management
"""

import pytest

from app.contacts.exclusions.schemas import (
    ExclusionCreateRequest,
    ExclusionImportError,
    ExclusionImportResponse,
)
from app.contacts.exclusions.service import normalize_phone_number


class TestNormalizePhoneNumber:
    """Tests for phone number normalization."""

    def test_valid_e164_format(self) -> None:
        """Test valid E.164 format passes through."""
        assert normalize_phone_number("+14155551234") == "+14155551234"
        assert normalize_phone_number("+393331234567") == "+393331234567"
        assert normalize_phone_number("+442071234567") == "+442071234567"

    def test_e164_with_whitespace(self) -> None:
        """Test E.164 with whitespace is normalized."""
        assert normalize_phone_number("  +14155551234  ") == "+14155551234"
        assert normalize_phone_number("+1 415 555 1234") == "+14155551234"

    def test_e164_with_formatting(self) -> None:
        """Test E.164 with formatting characters is normalized."""
        assert normalize_phone_number("+1-415-555-1234") == "+14155551234"
        assert normalize_phone_number("+1 (415) 555-1234") == "+14155551234"
        assert normalize_phone_number("+1.415.555.1234") == "+14155551234"

    def test_double_zero_prefix(self) -> None:
        """Test 00 prefix is converted to +."""
        assert normalize_phone_number("0014155551234") == "+14155551234"
        assert normalize_phone_number("00393331234567") == "+393331234567"

    def test_invalid_format_returns_none(self) -> None:
        """Test invalid formats return None."""
        assert normalize_phone_number("") is None
        assert normalize_phone_number("   ") is None
        assert normalize_phone_number("1234567") is None  # No country code
        assert normalize_phone_number("abc123") is None
        assert normalize_phone_number("+1234") is None  # Too short

    def test_too_long_number(self) -> None:
        """Test numbers that are too long return None."""
        assert normalize_phone_number("+12345678901234567890") is None


class TestExclusionCreateRequest:
    """Tests for ExclusionCreateRequest schema."""

    def test_valid_phone_number(self) -> None:
        """Test valid phone number is accepted."""
        request = ExclusionCreateRequest(phone_number="+14155551234")
        assert request.phone_number == "+14155551234"

    def test_phone_with_whitespace_trimmed(self) -> None:
        """Test phone number whitespace is trimmed."""
        request = ExclusionCreateRequest(phone_number="  +14155551234  ")
        assert request.phone_number == "+14155551234"

    def test_optional_reason(self) -> None:
        """Test reason is optional."""
        request = ExclusionCreateRequest(phone_number="+14155551234")
        assert request.reason is None

        request_with_reason = ExclusionCreateRequest(
            phone_number="+14155551234",
            reason="Customer requested removal",
        )
        assert request_with_reason.reason == "Customer requested removal"

    def test_empty_phone_rejected(self) -> None:
        """Test empty phone number is rejected."""
        with pytest.raises(ValueError):
            ExclusionCreateRequest(phone_number="")

    def test_invalid_phone_rejected(self) -> None:
        """Test invalid phone number is rejected."""
        with pytest.raises(ValueError):
            ExclusionCreateRequest(phone_number="abc123")


class TestExclusionImportResponse:
    """Tests for ExclusionImportResponse schema."""

    def test_response_creation(self) -> None:
        """Test response can be created with all fields."""
        response = ExclusionImportResponse(
            accepted_count=10,
            rejected_count=2,
            duplicate_count=1,
            errors=[
                ExclusionImportError(
                    line_number=5,
                    phone_number="invalid",
                    error="Invalid format",
                )
            ],
        )
        assert response.accepted_count == 10
        assert response.rejected_count == 2
        assert response.duplicate_count == 1
        assert len(response.errors) == 1
        assert response.errors[0].line_number == 5

    def test_empty_errors_list(self) -> None:
        """Test response with no errors."""
        response = ExclusionImportResponse(
            accepted_count=10,
            rejected_count=0,
            duplicate_count=0,
            errors=[],
        )
        assert response.errors == []