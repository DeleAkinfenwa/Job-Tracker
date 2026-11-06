"""Loading the profile: the fixed facts (contact info, titles, dates, certifications)."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import yaml

CURRENT_WORDS = {"present", "current", "now"}


def parse_profile(text: str) -> dict:
    """Read profile YAML and check each role has what the resume needs. Raises ValueError with a plain message."""
    try:
        profile = yaml.safe_load(text or "") or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"The profile is not valid YAML: {exc}") from exc
    if not isinstance(profile, dict):
        raise ValueError("The profile must be a YAML mapping with keys like contact, roles and skills.")
    roles = profile.get("roles") or []
    if not isinstance(roles, list):
        raise ValueError("roles must be a list.")
    for role in roles:
        if not isinstance(role, dict):
            raise ValueError("Each role must be a mapping with key, company, title, start and end.")
        missing = [k for k in ("key", "company", "title", "start", "end") if not role.get(k)]
        if missing:
            raise ValueError(f"A role in the profile is missing: {', '.join(missing)}")
    return profile


def load_profile(path: Path) -> dict:
    return parse_profile(path.read_text(encoding="utf-8"))


def role_keys(profile: dict) -> list[str]:
    return [r["key"] for r in profile.get("roles", [])]


def role_by_key(profile: dict, key: str) -> dict | None:
    return next((r for r in profile.get("roles", []) if r["key"] == key), None)


def current_role_key(profile: dict) -> str | None:
    for role in profile.get("roles", []):
        if str(role.get("end", "")).strip().lower() in CURRENT_WORDS:
            return role["key"]
    return None


def month_to_iso(text: str) -> str:
    """Turn 'Nov 2022' or 'November 2022' into '2022-11-01'."""
    for fmt in ("%b %Y", "%B %Y", "%Y-%m", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(text).strip(), fmt).date().replace(day=1).isoformat()
        except ValueError:
            continue
    return date.today().isoformat()


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9+#.]*", str(text).lower()))


def skill_names(profile: dict) -> list[str]:
    """Every individual skill name in the profile, split out of grouped entries."""
    names: list[str] = []
    for group in profile.get("skills", []):
        for item in group.get("items", []):
            for part in re.split(r"[,()/]", str(item)):
                part = part.strip()
                if part:
                    names.append(part)
    return names


def allowed_vocab(profile: dict, evidence: list[dict]) -> set[str]:
    """Words a skill may be built from: profile skills, project stacks, and logged tools."""
    vocab: set[str] = set()
    for name in skill_names(profile):
        vocab |= tokens(name)
    for project in profile.get("projects", []):
        vocab |= tokens(project.get("stack", ""))
    for entry in evidence:
        raw = str(entry.get("raw_text", "")).lower()
        for item in entry.get("tools", []) + entry.get("skills", []):
            # Only trust what the AI pulled out of a log if it is really in your words.
            if re.search(r"(?<![\w.+#-])" + re.escape(str(item).lower()) + r"(?![\w+#])", raw):
                vocab |= tokens(item)
    return vocab
