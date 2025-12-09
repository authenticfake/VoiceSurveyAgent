"""
Unit tests for LLM gateway factory.

REQ-011: LLM gateway integration
"""

import os
import pytest
from unittest.mock import patch

from app.dialogue.llm.factory import (
    create_llm_gateway,
    create_llm_gateway_from_config,
    DEFAULT_MODELS,
)
from app.dialogue.llm.models import LLMProvider, LLMProviderError
from app.dialogue.llm.openai_adapter import OpenAIAdapter
from app.dialogue.llm.anthropic_adapter import AnthropicAdapter

class TestCreateLLMGateway:
    """Tests for create_llm_gateway factory function."""

    def test_create_openai_gateway(self) -> None:
        """Test creating OpenAI gateway."""
        gateway = create_llm_gateway(
            provider=LLMProvider.OPENAI,
            api_key="test-key",
        )
        assert isinstance(gateway, OpenAIAdapter)
        assert gateway.provider == LLMProvider.OPENAI

    def test_create_anthropic_gateway(self) -> None:
        """Test creating Anthropic gateway."""
        gateway = create_llm_gateway(
            provider=LLMProvider.ANTHROPIC,
            api_key="test-key",
        )
        assert isinstance(gateway, AnthropicAdapter)
        assert gateway.provider == LLMProvider.ANTHROPIC

    def test_create_gateway_with_string_provider(self) -> None:
        """Test creating gateway with string provider name."""
        gateway = create_llm_gateway(
            provider="openai",
            api_key="test-key",
        )
        assert isinstance(gateway, OpenAIAdapter)

    def test_create_gateway_with_custom_model(self) -> None:
        """Test creating gateway with custom model."""
        gateway = create_llm_gateway(
            provider=LLMProvider.OPENAI,
            api_key="test-key",
            model="gpt-4",
        )
        assert gateway.default_model == "gpt-4"

    def test_create_gateway_with_custom_timeout(self) -> None:
        """Test creating gateway with custom timeout."""
        gateway = create_llm_gateway(
            provider=LLMProvider.OPENAI,
            api_key="test-key",
            timeout_seconds=60.0,
        )
        assert gateway._timeout_seconds == 60.0

    def test_create_gateway_uses_default_model(self) -> None:
        """Test that default model is used when not specified."""
        gateway = create_llm_gateway(
            provider=LLMProvider.OPENAI,
            api_key="test-key",
        )
        assert gateway.default_model == DEFAULT_MODELS[LLMProvider.OPENAI]

    def test_create_gateway_from_env_var(self) -> None:
        """Test creating gateway with API key from environment."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-test-key"}):
            gateway = create_llm_gateway(provider=LLMProvider.OPENAI)
            assert gateway._api_key == "env-test-key"

    def test_create_gateway_missing_api_key(self) -> None:
        """Test error when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure env var is not set
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(LLMProviderError) as exc_info:
                create_llm_gateway(provider=LLMProvider.OPENAI)
            assert "API key required" in str(exc_info.value)

    def test_create_gateway_unsupported_provider(self) -> None:
        """Test error for unsupported provider."""
        with pytest.raises(LLMProviderError) as exc_info:
            create_llm_gateway(provider="unsupported", api_key="test")
        assert "Unsupported LLM provider" in str(exc_info.value)

class TestCreateLLMGatewayFromConfig:
    """Tests for create_llm_gateway_from_config function."""

    def test_create_from_config(self) -> None:
        """Test creating gateway from config values."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            gateway = create_llm_gateway_from_config(
                provider_name="openai",
                model_name="gpt-4.1-mini",
                timeout_seconds=45.0,
            )
            assert isinstance(gateway, OpenAIAdapter)
            assert gateway.default_model == "gpt-4.1-mini"
            assert gateway._timeout_seconds == 45.0

    def test_create_anthropic_from_config(self) -> None:
        """Test creating Anthropic gateway from config."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            gateway = create_llm_gateway_from_config(
                provider_name="anthropic",
                model_name="claude-3-5-sonnet-20241022",
            )
            assert isinstance(gateway, AnthropicAdapter)