from pathlib import Path

from app.search.registry import REGISTRY

# Base prompt is authored in base_prompt.md alongside this module so
# system instructions stay versioned as documentation, not inline code.
_BASE_PROMPT_PATH = Path(__file__).with_name("base_prompt.md")
try:
    _BASE_PROMPT = _BASE_PROMPT_PATH.read_text(encoding="utf-8")
except FileNotFoundError:
    _BASE_PROMPT = (
        "You are an image search assistant. Convert user natural language queries into filters.\n"
        "Available live filters:"
    )


def build_system_prompt() -> str:
    """Assemble deploy-time immutable filter descriptions for the agent.

    Uses the base prompt file and each live filter's DESCRIPTION (authored in
    its sibling markdown file). Falls back to SPEC_FORMAT / SPEC_EXAMPLE if a
    description is missing.
    """
    lines = [_BASE_PROMPT.strip()]
    for kind, cls in REGISTRY.items():
        if not cls.is_live:
            continue
        desc = getattr(cls, "DESCRIPTION", "")
        if desc and desc.strip():
            lines.append(desc.strip())
        else:
            lines.append(f"- {kind.value}: {cls.SPEC_FORMAT} Example: {cls.SPEC_EXAMPLE}")
    return "\n\n".join(lines)


SYSTEM_PROMPT = build_system_prompt()
