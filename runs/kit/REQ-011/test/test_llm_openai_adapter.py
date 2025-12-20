"""
Unit tests for OpenAI adapter (sync-only).

REQ-011: LLM gateway integration
"""

from __future__ import annotations

import pytest

from app.dialogue.llm.openai_adapter import OpenAIAdapter
from app.dialogue.llm.models import (
    ChatMessage,
    ChatRequest,
    ControlSignal,
    LLMAuthenticationError,
    LLMProvider,
    LLMRateLimitError,
    LLMTimeoutError,
    MessageRole,
    SurveyContext,
)


class FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, headers: dict | None = None) -> None:
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = headers or {}
        self.content = b"1"
        self.text = "x"

    def json(self) -> dict:
        return self._json_data


class FakeTransport:
    def __init__(self, responses: list[FakeResponse] | None = None, raise_exc: Exception | None = None) -> None:
        self._responses = responses or []
        self._raise_exc = raise_exc
        self.calls: list[dict] = []

    def post(self, url: str, *, json: dict, headers: dict, timeout: float) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._responses.pop(0)


@pytest.fixture
def sample_request() -> ChatRequest:
    return ChatRequest(
        messages=[ChatMessage(role=MessageRole.USER, content="Hello")],
        correlation_id="test-correlation-123",
    )


@pytest.fixture
def sample_openai_response() -> dict:
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4.1-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you?\nSIGNAL: CONSENT_ACCEPTED",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


def test_properties() -> None:
    adapter = OpenAIAdapter(api_key="k", default_model="gpt-4.1-mini")
    assert adapter.provider == LLMProvider.OPENAI
    assert adapter.default_model == "gpt-4.1-mini"


def test_successful_completion(sample_request: ChatRequest, sample_openai_response: dict) -> None:
    transport = FakeTransport(responses=[FakeResponse(200, sample_openai_response)])
    adapter = OpenAIAdapter(
        api_key="test-api-key",
        default_model="gpt-4.1-mini",
        timeout_seconds=10.0,
        max_retries=2,
        transport=transport,
        sleep_func=lambda _: None,
    )

    response = adapter.chat_completion_sync(sample_request)

    assert response.content == "Hello! How can I help you?"
    assert response.model == "gpt-4.1-mini"
    assert response.provider == LLMProvider.OPENAI
    assert response.correlation_id == "test-correlation-123"
    assert ControlSignal.CONSENT_ACCEPTED in response.control_signals
    assert response.usage["total_tokens"] == 30

    assert transport.calls[0]["timeout"] == 10.0  # timeout forwarded


def test_completion_with_survey_context_adds_system_prompt(sample_openai_response: dict) -> None:
    context = SurveyContext(
        campaign_name="Test Survey",
        intro_script="Hello, this is a test survey.",
        question_1_text="Q1",
        question_1_type="scale",
        question_2_text="Q2",
        question_2_type="free_text",
        question_3_text="Q3",
        question_3_type="numeric",
    )
    request = ChatRequest(
        messages=[ChatMessage(role=MessageRole.USER, content="Yes")],
        survey_context=context,
        correlation_id="test-123",
    )

    transport = FakeTransport(responses=[FakeResponse(200, sample_openai_response)])
    adapter = OpenAIAdapter(api_key="k", transport=transport, sleep_func=lambda _: None)

    adapter.chat_completion_sync(request)

    payload = transport.calls[0]["json"]
    msgs = payload["messages"]
    assert msgs[0]["role"] == "system"
    assert "Test Survey" in msgs[0]["content"]


def test_timeout_error(sample_request: ChatRequest, caplog: pytest.LogCaptureFixture) -> None:
    transport = FakeTransport(raise_exc=TimeoutError("timeout"))
    adapter = OpenAIAdapter(api_key="k", transport=transport, timeout_seconds=0.1)

    with pytest.raises(LLMTimeoutError) as exc_info:
        adapter.chat_completion_sync(sample_request)

    assert exc_info.value.correlation_id == "test-correlation-123"
    assert exc_info.value.provider == LLMProvider.OPENAI
    assert any(getattr(r, "correlation_id", None) == "test-correlation-123" for r in caplog.records)


def test_authentication_error_no_retry() -> None:
    transport = FakeTransport(responses=[FakeResponse(401)])
    adapter = OpenAIAdapter(api_key="k", max_retries=3, transport=transport, sleep_func=lambda _: None)

    with pytest.raises(LLMAuthenticationError):
        adapter.chat_completion_sync(ChatRequest(messages=[ChatMessage(role=MessageRole.USER, content="x")], correlation_id="c"))

    assert len(transport.calls) == 1


def test_rate_limit_retry_then_success(sample_openai_response: dict) -> None:
    transport = FakeTransport(
        responses=[
            FakeResponse(429, headers={"Retry-After": "0"}),
            FakeResponse(200, sample_openai_response),
        ]
    )
    adapter = OpenAIAdapter(api_key="k", max_retries=2, transport=transport, sleep_func=lambda _: None)

    resp = adapter.chat_completion_sync(ChatRequest(messages=[ChatMessage(role=MessageRole.USER, content="x")], correlation_id="c"))

    assert resp.provider == LLMProvider.OPENAI
    assert len(transport.calls) == 2


def test_rate_limit_final_raises() -> None:
    transport = FakeTransport(
        responses=[
            FakeResponse(429, headers={"Retry-After": "0"}),
            FakeResponse(429, headers={"Retry-After": "0"}),
        ]
    )
    adapter = OpenAIAdapter(api_key="k", max_retries=2, transport=transport, sleep_func=lambda _: None)

    with pytest.raises(LLMRateLimitError):
        adapter.chat_completion_sync(ChatRequest(messages=[ChatMessage(role=MessageRole.USER, content="x")], correlation_id="c"))

    assert len(transport.calls) == 2
