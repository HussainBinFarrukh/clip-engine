import pytest
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai_analysis import AIAnalysis
from app.services.ai_analysis import run_llm_call
from app.services.llm_provider import (
    GeminiProvider,
    LLMError,
    LLMProvider,
    LLMStructuredOutputError,
    LLMUsage,
    generate_structured,
    get_llm_provider,
)
from app.services.prompts import load_prompt
from tests.conftest import skip_if_transient_llm_outage


class DemoSchema(BaseModel):
    summary: str
    confidence: float


class _ScriptedProvider(LLMProvider):
    """Returns a fixed sequence of raw responses, one per call — lets tests
    exercise retry/failure paths deterministically, without a real API."""

    name = "scripted"
    model = "scripted-v1"

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []

    def generate(self, prompt: str) -> tuple[str, LLMUsage]:
        self.calls.append(prompt)
        text = self._responses.pop(0)
        return text, LLMUsage(input_tokens=10, output_tokens=5, cost_usd=0.001)


def test_generate_structured_succeeds_on_first_valid_response() -> None:
    provider = _ScriptedProvider(['{"summary": "ok", "confidence": 0.9}'])

    call = generate_structured(provider, "prompt", DemoSchema)

    assert call.success
    assert call.attempts == 1
    assert call.result.summary == "ok"
    assert call.usage.input_tokens == 10


def test_generate_structured_retries_then_succeeds() -> None:
    provider = _ScriptedProvider(
        ["not json at all", '{"summary": "ok", "confidence": 0.5}']
    )

    call = generate_structured(provider, "prompt", DemoSchema, max_retries=1)

    assert call.success
    assert call.attempts == 2
    assert len(provider.calls) == 2
    # The retry prompt should include the correction instruction.
    assert "invalid" in provider.calls[1].lower()
    # Usage accumulates across both attempts.
    assert call.usage.input_tokens == 20


def test_generate_structured_fails_cleanly_after_max_retries() -> None:
    provider = _ScriptedProvider(["nope", "still nope"])

    call = generate_structured(provider, "prompt", DemoSchema, max_retries=1)

    assert not call.success
    assert call.result is None
    assert call.attempts == 2
    assert "invalid JSON" in call.error


def test_generate_structured_rejects_json_missing_required_fields() -> None:
    provider = _ScriptedProvider(['{"summary": "ok"}'])  # missing "confidence"

    call = generate_structured(provider, "prompt", DemoSchema, max_retries=0)

    assert not call.success
    assert call.attempts == 1


def test_run_llm_call_logs_ai_analysis_row_on_success(db_session: Session) -> None:
    provider = _ScriptedProvider(['{"summary": "ok", "confidence": 0.8}'])

    result = run_llm_call(
        db_session, provider, "structured_demo", 1, "prompt", DemoSchema
    )

    assert result.summary == "ok"
    rows = db_session.query(AIAnalysis).all()
    assert len(rows) == 1
    assert rows[0].success is True
    assert rows[0].provider == "scripted"
    assert rows[0].cost_usd == 0.001
    assert rows[0].attempts == 1


def test_run_llm_call_logs_failure_and_raises(db_session: Session) -> None:
    provider = _ScriptedProvider(["bad", "still bad"])

    with pytest.raises(LLMStructuredOutputError):
        run_llm_call(
            db_session, provider, "structured_demo", 1, "prompt", DemoSchema, max_retries=1
        )

    rows = db_session.query(AIAnalysis).all()
    assert len(rows) == 1
    assert rows[0].success is False
    assert rows[0].error_message is not None
    # A failed call still cost tokens — that's still recorded.
    assert rows[0].input_tokens == 20


def test_get_llm_provider_swaps_via_environment_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_llm_provider.cache_clear()
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key-for-this-test")
    monkeypatch.setattr(settings, "gemini_model", "gemini-3.6-flash")

    provider = get_llm_provider()
    assert isinstance(provider, GeminiProvider)
    assert provider.model == "gemini-3.6-flash"

    get_llm_provider.cache_clear()
    monkeypatch.setattr(settings, "llm_provider", "some_unsupported_provider")
    with pytest.raises(LLMError):
        get_llm_provider()

    get_llm_provider.cache_clear()


@pytest.mark.skipif(not settings.gemini_api_key, reason="no GEMINI_API_KEY configured")
def test_real_gemini_call_produces_valid_structured_output(db_session: Session) -> None:
    provider = get_llm_provider()
    prompt_template = load_prompt("structured_demo", 1)
    prompt = prompt_template.format(
        input_text="Clip Engine helps creators turn long videos into short clips."
    )

    try:
        result = run_llm_call(db_session, provider, "structured_demo", 1, prompt, DemoSchema)
    except LLMError as exc:
        skip_if_transient_llm_outage(exc)  # skips, or re-raises exc if not transient

    assert isinstance(result.summary, str) and len(result.summary) > 0
    assert 0.0 <= result.confidence <= 1.0

    rows = db_session.query(AIAnalysis).all()
    assert len(rows) == 1
    assert rows[0].success is True
    assert rows[0].provider == "gemini"
    assert rows[0].input_tokens > 0
    assert rows[0].cost_usd >= 0
