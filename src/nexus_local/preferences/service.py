"""Preference profile: validated keys, versioned values, prompt directives.
Preferences change prompting only — they never trigger training."""
from __future__ import annotations

from sqlalchemy import select

from ..db import audit, get_session
from ..models import Preference

SCHEMA: dict[str, set[str]] = {
    "explanation_level": {"beginner", "intermediate", "advanced"},
    "language": {"english", "hinglish", "hindi"},
    "verbosity": {"concise", "balanced", "detailed"},
    "ordering": {"code_first", "explanation_first"},
    "tone": {"academic", "casual", "professional"},
    "strict_citations": {"on", "off"},
    "clarifying_questions": {"often", "when_necessary"},
    "tables": {"use", "avoid"},
    "examples": {"prefer_examples", "prefer_theory"},
    "preferred_language": {"python", "go", "typescript", "javascript", "rust", "java", "cpp"},
}

DIRECTIVES = {
    ("explanation_level", "beginner"): "Explain assuming no prior background; define jargon.",
    ("explanation_level", "advanced"): "Assume strong background; skip basics.",
    ("verbosity", "concise"): "Keep the answer short and direct.",
    ("verbosity", "detailed"): "Give a thorough, complete answer.",
    ("ordering", "code_first"): "Show working code before explanation.",
    ("ordering", "explanation_first"): "Explain the approach before any code.",
    ("tone", "academic"): "Use a formal, precise tone.",
    ("tone", "casual"): "Use a relaxed, conversational tone.",
    ("tone", "professional"): "Use a clear, professional tone.",
    ("tables", "avoid"): "Do not use tables.",
    ("examples", "prefer_examples"): "Illustrate points with concrete examples.",
    ("language", "hinglish"): "Respond in Hinglish (Hindi-English mix, Latin script).",
    ("language", "hindi"): "Respond in Hindi.",
}


def set_preference(key: str, value: str) -> Preference:
    if key not in SCHEMA:
        raise ValueError(f"Unknown preference key: {key}")
    if value not in SCHEMA[key]:
        raise ValueError(f"Invalid value '{value}' for {key}; allowed: {sorted(SCHEMA[key])}")
    with get_session() as s:
        p = s.scalar(select(Preference).where(Preference.key == key))
        if p:
            p.value = value
            p.version += 1
        else:
            p = Preference(key=key, value=value)
            s.add(p)
            s.flush()
        audit(s, "set", "preference", p.id, f"{key}={value}")
        s.commit()
        return p


def get_profile() -> dict[str, str]:
    with get_session() as s:
        return {p.key: p.value for p in s.execute(select(Preference)).scalars()}


def build_style_directives() -> str:
    return "\n".join(f"- {DIRECTIVES[(k, v)]}"
                     for k, v in get_profile().items() if (k, v) in DIRECTIVES)


def applied_preference_summary() -> list[str]:
    """Which preferences influenced this answer — shown in 'Why this answer?'."""
    return [f"{k}={v}" for k, v in get_profile().items() if (k, v) in DIRECTIVES]
