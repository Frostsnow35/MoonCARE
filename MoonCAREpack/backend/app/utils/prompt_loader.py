from pathlib import Path
from typing import Any


PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


class _SafePromptContext(dict):
    """String formatter context that leaves unknown prompt fields blank."""

    def __missing__(self, key: str) -> str:
        return ""


def load_prompt(filename: str) -> str:
    """Load an Agent prompt template from backend/app/prompts."""
    prompt_path = PROMPT_DIR / filename
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def render_prompt(filename: str, **context: Any) -> str:
    """Load and format a prompt template with named context values."""
    template = load_prompt(filename)
    safe_context = _SafePromptContext({key: "" if value is None else value for key, value in context.items()})
    return template.format_map(safe_context)
