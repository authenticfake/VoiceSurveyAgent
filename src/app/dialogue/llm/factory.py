"""
Factory for creating LLM gateway instances.

REQ-011: LLM gateway integration
"""

import os
from typing import Any

from app.dialogue.llm.gateway import LLMGateway
from app.dialogue.llm.models import LLMProvider, LLMProviderError
from app.dialogue.llm.openai_adapter import OpenAIAdapter
from app.dialogue.llm.anthropic_adapter import AnthropicAdapter
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Default models per provider
DEFAULT_MODELS = {
    LLMProvider.OPENAI: "gpt-4.1-mini",
    LLMProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
}

# Environment variable names for API keys
API_KEY_ENV_VARS = {
    LLMProvider.OPENAI: "OPENAI_API_KEY",
    LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
}

def create_llm_gateway(
    provider: LLMProvider | str,
    api_key: str | None = None,
    model: str | None = None,
    timeout_seconds: float = 30.0,
    max_retries: int = 3,
    **kwargs: Any,
) -> LLMGateway:
    """Create an LLM gateway instance for the specified provider.

    Args:
        provider: LLM provider (openai, anthropic) or LLMProvider enum.
        api_key: API key for the provider. If not provided, reads from environment.
        model: Model to use. If not provided, uses provider default.
        timeout_seconds: Request timeout in seconds.
        max_retries: Maximum number of retries for failed requests.
        **kwargs: Additional provider-specific arguments.

    Returns:
        LLMGateway instance.

    Raises:
        LLMProviderError: If provider is not supported or API key is missing.
    """
    # Convert string to enum if needed
    if isinstance(provider, str):
        try:
            provider = LLMProvider(provider.lower())
        except ValueError:
            raise LLMProviderError(
                f"Unsupported LLM provider: {provider}. "
                f"Supported providers: {[p.value for p in LLMProvider]}"
            )

    # Get API key from environment if not provided
    if api_key is None:
        env_var = API_KEY_ENV_VARS.get(provider)
        if env_var:
            api_key = os.environ.get(env_var)

    if not api_key:
        raise LLMProviderError(
            f"API key required for {provider.value}. "
            f"Set {API_KEY_ENV_VARS.get(provider)} environment variable or pass api_key parameter."
        )

    # Get default model if not provided
    if model is None:
        model = DEFAULT_MODELS.get(provider, "")

    logger.info(
        f"Creating LLM gateway",
        extra={
            "provider": provider.value,
            "model": model,
            "timeout_seconds": timeout_seconds,
        },
    )

    if provider == LLMProvider.OPENAI:
        return OpenAIAdapter(
            api_key=api_key,
            default_model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            base_url=kwargs.get("base_url"),
        )
    elif provider == LLMProvider.ANTHROPIC:
        return AnthropicAdapter(
            api_key=api_key,
            default_model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            base_url=kwargs.get("base_url"),
        )
    else:
        raise LLMProviderError(f"Unsupported LLM provider: {provider.value}")

def create_llm_gateway_from_config(
    provider_name: str,
    model_name: str,
    timeout_seconds: float = 30.0,
) -> LLMGateway:
    """Create LLM gateway from configuration values.

    This is a convenience function for creating gateways from
    ProviderConfig entity values.

    Args:
        provider_name: Provider name from config (e.g., "openai").
        model_name: Model name from config (e.g., "gpt-4.1-mini").
        timeout_seconds: Request timeout.

    Returns:
        LLMGateway instance.
    """
    return create_llm_gateway(
        provider=provider_name,
        model=model_name,
        timeout_seconds=timeout_seconds,
    )