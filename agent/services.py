"""Running the agent: loading your record, the daily cap, and calling the AI model."""

from __future__ import annotations

import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .engine import tailor as engine
from .engine.extract import clean_extracted, extract_entry
from .engine.llm import AnthropicLLM, LLMError
from .engine.profile import month_to_iso, parse_profile, role_keys, skill_names
from .models import AgentRun, CareerEntry, CareerProfile

# How long a run may sit unfinished before it stops counting as "in progress".
STALE_AFTER = timedelta(minutes=10)


class AgentUnavailable(Exception):
    """A problem the person can fix, shown to them as a plain message."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def get_llm():
    if settings.AGENT_PROVIDER == "mock":
        from .engine.mock import MockLLM

        return MockLLM()
    return AnthropicLLM(settings.ANTHROPIC_API_KEY, settings.AGENT_MODEL)


def is_configured() -> bool:
    return settings.AGENT_PROVIDER == "mock" or bool(settings.ANTHROPIC_API_KEY)


def today_start():
    now = timezone.localtime()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def usage_today(user) -> dict:
    runs = AgentRun.objects.filter(owner=user, created_at__gte=today_start())
    totals = runs.aggregate(i=Sum("input_tokens"), o=Sum("output_tokens"))
    return {
        "runs_today": runs.count(),
        "daily_run_limit": settings.AGENT_DAILY_RUN_LIMIT,
        "tokens_today": (totals["i"] or 0) + (totals["o"] or 0),
        "daily_token_limit": settings.AGENT_DAILY_TOKEN_LIMIT,
    }


def load_profile(user) -> dict:
    record = CareerProfile.objects.filter(owner=user).first()
    if not record or not record.yaml.strip():
        raise AgentUnavailable("Add your profile first, on the Profile tab.")
    try:
        return parse_profile(record.yaml)
    except ValueError as exc:
        raise AgentUnavailable(str(exc)) from exc


def load_evidence(user) -> list[dict]:
    entries = [e.as_evidence() for e in CareerEntry.objects.filter(owner=user)]
    if not entries:
        raise AgentUnavailable("Your career log is empty. Import your profile bullets or log some work first.")
    return entries


def _reserve_run(user, kind: str, **fields) -> AgentRun:
    """Check the daily cap and record the run before any money is spent.

    The user's row is locked so two requests at once can't both squeeze under the cap.
    """
    if not is_configured():
        raise AgentUnavailable("The resume agent is not set up yet: ANTHROPIC_API_KEY is missing on the server.", 503)
    User = get_user_model()
    with transaction.atomic():
        User.objects.select_for_update().get(pk=user.pk)
        used = usage_today(user)
        if used["runs_today"] >= settings.AGENT_DAILY_RUN_LIMIT:
            limit = settings.AGENT_DAILY_RUN_LIMIT
            raise AgentUnavailable(
                f"You've reached today's limit of {limit} agent runs. It resets at midnight UTC.", 429
            )
        if used["tokens_today"] >= settings.AGENT_DAILY_TOKEN_LIMIT:
            raise AgentUnavailable("You've reached today's AI usage limit. It resets at midnight UTC.", 429)
        busy = AgentRun.objects.filter(
            owner=user, ok=False, error="running", created_at__gte=timezone.now() - STALE_AFTER
        ).exists()
        if busy:
            raise AgentUnavailable("Another agent run is still going. Wait for it to finish.", 409)
        return AgentRun.objects.create(owner=user, kind=kind, ok=False, error="running", **fields)


def _finish(run: AgentRun, llm, result: dict | None = None, error: str = "") -> AgentRun:
    run.input_tokens = getattr(llm, "input_tokens", 0)
    run.output_tokens = getattr(llm, "output_tokens", 0)
    run.ok = not error
    run.error = error
    if result is not None:
        run.result = result
    run.save()
    return run


def _call(run: AgentRun, fn):
    try:
        llm = get_llm()
    except LLMError as exc:
        _finish(run, None, error=str(exc))
        raise AgentUnavailable(str(exc), 503) from exc
    try:
        result = fn(llm)
    except LLMError as exc:
        _finish(run, llm, error=str(exc))
        raise AgentUnavailable(str(exc), 502) from exc
    except Exception:
        _finish(run, llm, error="Something went wrong while running the agent.")
        raise
    return _finish(run, llm, result=result)


def run_job(user, kind: str, job_text: str, job_title: str = "", application=None) -> AgentRun:
    """A fit check or a tailored resume for one job posting."""
    profile = load_profile(user)
    evidence = load_evidence(user)
    run = _reserve_run(
        user, kind, job_text=job_text, job_title=job_title, application=application, profile_snapshot=profile
    )
    work = engine.tailor if kind == AgentRun.Kind.TAILOR else engine.evaluate
    return _call(run, lambda llm: work(llm, profile, evidence, job_text))


def detect_tools(text: str, names: list[str]) -> list[str]:
    found = []
    for name in names:
        if re.search(r"(?<![\w.])" + re.escape(name) + r"(?![\w])", text, re.IGNORECASE) and name not in found:
            found.append(name)
    return found


def simple_facts(text: str, profile: dict) -> dict:
    """Facts pulled out without the AI: tools named in your skills list, and any numbers."""
    return {
        "summary": text.strip()[:200],
        "tools": detect_tools(text, skill_names(profile)),
        "skills": [],
        "accomplishments": [text.strip()],
        "metrics": re.findall(r"\d[\d,]*\+?", text),
    }


def log_entry(user, *, role: str, entry_date, raw_text: str, use_ai: bool) -> tuple[CareerEntry, list[str]]:
    """Save one work log. With use_ai, the model pulls out tools, results and follow-up questions."""
    profile = load_profile(user)
    if role not in role_keys(profile):
        raise AgentUnavailable(f"'{role}' is not a role in your profile.")
    questions: list[str] = []
    if use_ai:
        role_info = next(r for r in profile["roles"] if r["key"] == role)
        label = f"{role_info['title']} at {role_info['company']}"
        run = _reserve_run(user, AgentRun.Kind.EXTRACT, job_title=label)
        run = _call(run, lambda llm: extract_entry(llm, raw_text, label))
        facts = run.result
        questions = facts.get("open_questions", [])
    else:
        facts = simple_facts(raw_text, profile)
    facts = clean_extracted(facts, raw_text)
    entry = CareerEntry.objects.create(
        owner=user,
        role=role,
        entry_date=entry_date,
        raw_text=raw_text,
        source=CareerEntry.Source.LOG,
        **{k: facts[k] for k in ("summary", "tools", "skills", "accomplishments", "metrics")},
    )
    return entry, questions


@transaction.atomic
def import_profile_bullets(user) -> int:
    """Turn the bullets under each role in your profile into starting evidence. Replaces an earlier import."""
    profile = load_profile(user)
    CareerEntry.objects.filter(owner=user, source=CareerEntry.Source.RESUME).delete()
    rows = []
    for role in profile.get("roles", []):
        for bullet in role.get("bullets") or []:
            facts = simple_facts(str(bullet), profile)
            rows.append(
                CareerEntry(
                    owner=user,
                    role=role["key"],
                    entry_date=month_to_iso(role["start"]),
                    raw_text=str(bullet),
                    source=CareerEntry.Source.RESUME,
                    summary=str(bullet),
                    tools=facts["tools"],
                    accomplishments=[str(bullet)],
                    metrics=facts["metrics"],
                )
            )
    CareerEntry.objects.bulk_create(rows)
    return len(rows)


ENTRY_FIELDS = ("summary", "tools", "skills", "accomplishments", "metrics")


@transaction.atomic
def import_entries(user, items: list[dict], replace: bool = False) -> int:
    """Load entries saved elsewhere (for example the Claude version of the agent). Ids are renumbered."""
    from datetime import date

    rows = []
    for n, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise AgentUnavailable(f"Entry {n} is not an object.")
        raw = str(item.get("raw_text") or "").strip()
        role = str(item.get("role") or "").strip()
        if not raw or not role:
            raise AgentUnavailable(f"Entry {n} needs raw_text and role.")
        try:
            when = date.fromisoformat(str(item.get("entry_date"))[:10])
        except ValueError as exc:
            raise AgentUnavailable(f"Entry {n} has no valid entry_date (YYYY-MM-DD).") from exc
        source = item.get("source") if item.get("source") in CareerEntry.Source.values else CareerEntry.Source.LOG
        lists = {k: [str(v) for v in (item.get(k) or []) if str(v).strip()] for k in ENTRY_FIELDS[1:]}
        rows.append(
            CareerEntry(
                owner=user,
                role=role[:80],
                entry_date=when,
                raw_text=raw,
                source=source,
                summary=str(item.get("summary") or raw[:200]),
                **lists,
            )  # fmt: skip
        )
    if replace:
        CareerEntry.objects.filter(owner=user).delete()
    CareerEntry.objects.bulk_create(rows)
    return len(rows)
