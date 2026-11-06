"""Small text helpers shared across the project."""

from __future__ import annotations

import re

EM_DASH = "\u2014"
EN_DASH = "\u2013"


def clean_text(text: str) -> str:
    """Remove em dashes (and spaced en dashes) in favor of commas, per your writing preference."""
    text = text.replace(f" {EM_DASH} ", ", ").replace(EM_DASH, ", ").replace(f" {EN_DASH} ", ", ")
    text = re.sub(r"\s+,", ",", text).replace(",,", ",")
    return re.sub(r"\s{2,}", " ", text).strip()
