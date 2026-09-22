import uuid

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.ai_analysis import AIAnalysis
from app.services.llm_provider import LLMProvider, LLMStructuredOutputError, generate_structured


def run_llm_call(
    db: Session,
    provider: LLMProvider,
    prompt_name: str,
    prompt_version: int,
    prompt: str,
    schema: type[BaseModel],
    source_video_id: uuid.UUID | None = None,
    max_retries: int = 1,
) -> BaseModel:
    """Run a structured LLM call and record it (cost, tokens, success) in
    AIAnalysis regardless of outcome, then raise on failure.

    Every call is logged, successful or not — that's T08's "cost of each
    call is recorded" accept check; a failed call still cost tokens.
    """
    call = generate_structured(provider, prompt, schema, max_retries=max_retries)

    db.add(
        AIAnalysis(
            source_video_id=source_video_id,
            provider=provider.name,
            model=provider.model,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            attempts=call.attempts,
            input_tokens=call.usage.input_tokens,
            output_tokens=call.usage.output_tokens,
            cost_usd=call.usage.cost_usd,
            success=call.success,
            error_message=call.error,
            raw_response=call.raw_text[:5000] if call.raw_text else None,
        )
    )
    db.commit()

    if not call.success:
        raise LLMStructuredOutputError(call.error)

    return call.result
