"""Building a tailored resume and fit report, then checking every claim against your record."""

from __future__ import annotations

import re

from . import guard
from .llm import complete_json
from .profile import allowed_vocab, tokens
from .prompts import EVALUATE_SYSTEM, TAILOR_SYSTEM, build_user
from .text import clean_text

EVIDENCE_CAP = 150
STOPWORDS = {"and", "or", "of", "the", "for", "with", "as", "in", "to", "a", "an", "&"}


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z0-9+#.]{2,}", text.lower()))


def select_evidence(entries: list[dict], job_text: str, cap: int = EVIDENCE_CAP) -> list[dict]:
    """Keep the log small enough for the model by ranking entries by overlap with the posting."""
    if len(entries) <= cap:
        return entries
    job_words = _words(job_text)

    def score(entry: dict) -> int:
        text = " ".join([entry.get("summary") or "", entry["raw_text"], " ".join(entry["tools"])])
        return len(_words(text) & job_words)

    keep = {e["id"] for e in sorted(entries, key=score, reverse=True)[:cap]}
    return [e for e in entries if e["id"] in keep]


def _evidence_payload(entries: list[dict]) -> list[dict]:
    return [
        {
            "id": e["id"],
            "date": e["entry_date"],
            "role": e["role"],
            "summary": e["summary"],
            "accomplishments": e["accomplishments"],
            "metrics": e["metrics"],
            "tools": e["tools"],
            "skills": e["skills"],
            "raw_text": e["raw_text"][:800],
        }
        for e in entries
    ]


def _profile_payload(profile: dict) -> dict:
    return {
        "summary_base": profile.get("summary_base", ""),
        "roles": [
            {k: r.get(k) for k in ("key", "company", "title", "start", "end")} | {"optional": bool(r.get("optional"))}
            for r in profile.get("roles", [])
        ],
        "skills": profile.get("skills", []),
        "certifications": profile.get("certifications", []),
        "projects": [{k: p.get(k, "") for k in ("name", "stack", "description")} for p in profile.get("projects", [])],
        "education": profile.get("education", []),
    }


def _payload(profile: dict, evidence: list[dict], job_text: str) -> dict:
    return {
        "job_posting": job_text,
        "profile": _profile_payload(profile),
        "depth_notes": profile.get("depth_notes", []),
        "limits": profile.get("limits", {}),
        "evidence": _evidence_payload(evidence),
    }


def _clean_list(values) -> list[str]:
    return [clean_text(str(v)) for v in (values or []) if str(v).strip()]


def tailor(llm, profile: dict, entries: list[dict], job_text: str) -> dict:
    evidence = select_evidence(entries, job_text)
    user = build_user("Write the tailored resume for this job.", _payload(profile, evidence, job_text))
    raw = complete_json(llm, TAILOR_SYSTEM, user, 8000)
    return validate(raw, profile, evidence)


def coerce_sources(value) -> list[int]:
    """Accept evidence ids however the model writes them: 7, "7", "#7", 7.0, or "7, 8"."""
    if value is None:
        return []
    items = value if isinstance(value, (list, tuple)) else [value]
    ids: list[int] = []
    for item in items:
        if isinstance(item, bool):
            continue
        if isinstance(item, int):
            ids.append(item)
        elif isinstance(item, float) and item.is_integer():
            ids.append(int(item))
        elif isinstance(item, str):
            ids += [int(n) for n in re.findall(r"\d+", item)]
    return list(dict.fromkeys(ids))


def resolve_role_key(value, profile: dict) -> str | None:
    """Match the role by key, or by company name if the model used that instead."""
    text = str(value or "").strip().lower()
    for role in profile.get("roles", []):
        if text in {str(role["key"]).lower(), str(role["company"]).lower()}:
            return role["key"]
    return None


def _check_summary(text: str, profile: dict, evidence: list[dict], removed: list[str]) -> str:
    record = guard.record_text(profile, evidence)
    record_numbers = guard.numbers_in(record)
    for e in evidence:
        record_numbers |= guard.entry_numbers(e)
    kept = []
    for sentence in guard.sentences(text):
        problems = guard.check_text(sentence, record, record_numbers, record, profile)
        if problems:
            removed.append(f"Summary sentence removed ({'; '.join(problems)}): {sentence}")
        else:
            kept.append(sentence)
    if kept:
        return " ".join(kept)
    removed.append("No AI-written summary sentence passed the checks, so your profile summary was used instead.")
    return clean_text(str(profile.get("summary_base", "")))


def validate(raw: dict, profile: dict, evidence: list[dict]) -> dict:
    """Remove anything the model wrote that your record does not back up."""
    by_id = {e["id"]: e for e in evidence}
    record = guard.record_text(profile, evidence)
    vocab = allowed_vocab(profile, evidence)
    project_names = {p["name"] for p in profile.get("projects", [])}
    removed: list[str] = []

    experience: dict[str, list[dict]] = {}
    for role in raw.get("experience") or []:
        key = resolve_role_key(role.get("role_key"), profile)
        if not key:
            removed.append(f"Role '{role.get('role_key')}' is not in your profile, so its bullets were removed.")
            continue
        for bullet in role.get("bullets") or []:
            if isinstance(bullet, str):
                bullet = {"text": bullet}
            text = clean_text(str(bullet.get("text", "")))
            if not text:
                continue
            sources = coerce_sources(bullet.get("sources"))
            if not sources:
                removed.append(f"Bullet with no evidence listed: {text}")
                continue
            unknown = [s for s in sources if s not in by_id]
            if unknown:
                removed.append(f"Bullet cites log entries that do not exist ({', '.join(map(str, unknown))}): {text}")
                continue
            other_role = [s for s in sources if by_id[s]["role"] != key]
            if other_role:
                removed.append(
                    f"Bullet cites log entries from a different job ({', '.join(map(str, other_role))}): {text}"
                )
                continue
            proof = "\n".join(guard.entry_text(by_id[s]) for s in sources)
            proof_numbers = set().union(*(guard.entry_numbers(by_id[s]) for s in sources))
            problems = guard.check_text(text, proof, proof_numbers, record, profile, role_key=key)
            if problems:
                removed.append(f"Bullet removed ({'; '.join(problems)}): {text}")
                continue
            experience.setdefault(key, []).append({"text": text, "sources": sources})

    skills = []
    seen_items: set[str] = set()
    for group in raw.get("skills") or []:
        items = []
        for item in group.get("items") or []:
            item = clean_text(str(item))
            if not item or item.lower() in seen_items:
                continue
            banned = guard.check_skill(item, profile)
            item_tokens = tokens(item) - STOPWORDS
            if banned:
                removed.append(banned)
            elif item_tokens and item_tokens <= vocab:
                items.append(item)
                seen_items.add(item.lower())
            else:
                removed.append(f"Skill not found in your record: {item}")
        if items:
            skills.append({"category": clean_text(str(group.get("category", "Skills"))), "items": items})

    summary = _check_summary(clean_text(str(raw.get("summary", ""))), profile, evidence, removed)

    return {
        "summary": summary,
        "skills": skills,
        "experience": [{"role_key": k, "bullets": v} for k, v in experience.items()],
        "projects": [n for n in (raw.get("projects") or []) if n in project_names],
        "fit_score": raw.get("fit_score"),
        "fit_explanation": clean_text(str(raw.get("fit_explanation", ""))),
        "keywords_matched": _clean_list(raw.get("keywords_matched")),
        "keywords_missing": _clean_list(raw.get("keywords_missing")),
        "gaps": _clean_list(raw.get("gaps")),
        "interview_prep": _clean_list(raw.get("interview_prep")),
        "removed": removed,
        "evidence_count": len(evidence),
    }


def evaluate(llm, profile: dict, entries: list[dict], job_text: str) -> dict:
    evidence = select_evidence(entries, job_text)
    user = build_user("Evaluate this job for the candidate.", _payload(profile, evidence, job_text))
    raw = complete_json(llm, EVALUATE_SYSTEM, user, 3000)
    return {
        "fit_score": raw.get("fit_score"),
        "worth_applying": clean_text(str(raw.get("worth_applying", ""))),
        "fit_explanation": clean_text(str(raw.get("fit_explanation", ""))),
        "strengths": _clean_list(raw.get("strengths")),
        "gaps": _clean_list(raw.get("gaps")),
        "keywords_missing": _clean_list(raw.get("keywords_missing")),
        "hard_blockers": _clean_list(raw.get("hard_blockers")),
    }
