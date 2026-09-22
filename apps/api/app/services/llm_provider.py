import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache

import requests
from pydantic import BaseModel, ValidationError

from app.core.config import settings


class LLMError(RuntimeError):
    pass


class LLMStructuredOutputError(LLMError):
    """Raised when the model's output still doesn't validate against the
    schema after all retries."""


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int
    output_tokens: int
    cost_usd: float


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def generate(self, prompt: str) -> tuple[str, LLMUsage]:
        """One call: return the raw text response and its usage/cost."""
        ...


# USD per 1M tokens. Placeholder rates for T08's infrastructure — verify
# against current Google AI pricing before trusting this for real budget
# tracking (same "needs current verification" caveat this project already
# applies to platform quotas — see docs/PLATFORMS.md).
_GEMINI_DEFAULT_PRICING = {"input": 0.10, "output": 0.40}
# Generous: this environment's outbound network is slow/variable (observed
# 20-50s+ for a trivial prompt), not just the model's own latency.
_REQUEST_TIMEOUT_SECONDS = 120
_GEMINI_PRICING_PER_MILLION_TOKENS: dict[str, dict[str, float]] = {
    "gemini-3.6-flash": {"input": 0.10, "output": 0.40},
}


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self.model = model

    def generate(self, prompt: str) -> tuple[str, LLMUsage]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        response = requests.post(
            url,
            params={"key": self._api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                # Structured-output calls don't need extended reasoning;
                # disabling it cuts both latency and token cost (confirmed:
                # a trivial prompt burned 52 "thought" tokens with the
                # default budget, and 0 with thinkingBudget 0).
                "generationConfig": {"thinkingConfig": {"thinkingBudget": 0}},
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()

        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"unexpected Gemini response shape: {payload}") from exc

        usage = payload.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)
        pricing = _GEMINI_PRICING_PER_MILLION_TOKENS.get(self.model, _GEMINI_DEFAULT_PRICING)
        cost_usd = (
            input_tokens * pricing["input"] + output_tokens * pricing["output"]
        ) / 1_000_000

        return text, LLMUsage(
            input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost_usd
        )


@lru_cache
def get_llm_provider() -> LLMProvider:
    """Selects the adapter via the LLM_PROVIDER env var (T08 accept:
    "swapping the adapter via an environment variable works"). Only
    "gemini" is implemented; add a branch here for the next provider."""
    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            raise LLMError("GEMINI_API_KEY is not set")
        return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
    raise LLMError(f"unknown LLM_PROVIDER '{settings.llm_provider}'")


@dataclass(frozen=True)
class StructuredCallResult:
    success: bool
    result: BaseModel | None
    usage: LLMUsage
    attempts: int
    raw_text: str
    error: str | None


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Some models wrap JSON in a markdown fence despite instructions.
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    return json.loads(cleaned)


def generate_structured(
    provider: LLMProvider,
    prompt: str,
    schema: type[BaseModel],
    max_retries: int = 1,
) -> StructuredCallResult:
    """Call the provider, parse+validate JSON against `schema`.

    On invalid JSON (parse error or schema-validation error), retries with
    an error-correction message appended, up to `max_retries` times. Never
    raises — the caller (which may want to log a failed attempt before
    deciding to raise) inspects `.success`.
    """
    total_input = 0
    total_output = 0
    total_cost = 0.0
    current_prompt = prompt
    last_error: str | None = None
    last_text = ""

    for attempt in range(1, max_retries + 2):  # first try + max_retries retries
        text, usage = provider.generate(current_prompt)
        last_text = text
        total_input += usage.input_tokens
        total_output += usage.output_tokens
        total_cost += usage.cost_usd
        total_usage = LLMUsage(total_input, total_output, total_cost)

        try:
            data = _extract_json(text)
            result = schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = str(exc)
            current_prompt = (
                f"{prompt}\n\nYour previous response was invalid: {last_error}. "
                "Return ONLY a valid JSON object matching the required fields."
            )
            continue

        return StructuredCallResult(
            success=True,
            result=result,
            usage=total_usage,
            attempts=attempt,
            raw_text=last_text,
            error=None,
        )

    return StructuredCallResult(
        success=False,
        result=None,
        usage=LLMUsage(total_input, total_output, total_cost),
        attempts=max_retries + 1,
        raw_text=last_text,
        error=f"invalid JSON after {max_retries + 1} attempt(s): {last_error}",
    )
