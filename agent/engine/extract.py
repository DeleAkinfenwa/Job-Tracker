"""Turning a plain-language work log into structured facts."""

from __future__ import annotations

from .llm import complete_json
from .prompts import EXTRACT_SYSTEM, build_user
from .text import clean_text

LIST_KEYS = ("tools", "skills", "accomplishments", "metrics", "open_questions")


def extract_entry(llm, raw_text: str, role_label: str) -> dict:
    payload = {"role": role_label, "log": raw_text}
    out = complete_json(llm, EXTRACT_SYSTEM, build_user("Extract the facts from this work log.", payload), 1500)
    return clean_extracted(out, raw_text)


def clean_extracted(out: dict, raw_text: str) -> dict:
    """Tidy extracted facts, whether they came from the AI here or were supplied in a file."""
    result = {"summary": clean_text(str(out.get("summary", ""))) or raw_text.strip()[:200]}
    for key in LIST_KEYS:
        values = out.get(key) or []
        result[key] = [clean_text(str(v)) for v in values if str(v).strip()]
    return result
