from pathlib import Path

_PROMPTS_ROOT = Path(__file__).resolve().parents[1] / "prompts"


def load_prompt(name: str, version: int) -> str:
    """Load a versioned prompt template from app/prompts/{name}/v{version}.txt.

    Prompts are files, not inline strings, so a prompt change is a diffable,
    reviewable change with its own version number (AIAnalysis rows record
    which prompt_name/prompt_version produced them).
    """
    path = _PROMPTS_ROOT / name / f"v{version}.txt"
    if not path.exists():
        raise FileNotFoundError(f"no prompt file at {path}")
    return path.read_text(encoding="utf-8")
