"""Accuracy checks on everything the AI writes.

The AI is told to follow your depth notes, but instructions alone are not a guarantee.
These checks run in code after the AI answers. Anything that fails is removed and listed
in the report, so a resume can only say less than your record, never more.

What gets checked, for every bullet and every sentence of the summary:
  1. Tools and technologies named must appear in the evidence it cites.
  2. Numbers (counts, percentages, dollar amounts, years) must appear in the evidence.
  3. Leadership words such as "led", "owned", "managed", or "responsible for" must appear in the evidence.
     So must words that make a claim bigger, such as "entire", "millions", or "zero downtime".
  4. Inflating words such as "expert" must appear in the evidence, and seniority words
     such as "senior" must appear in one of your job titles.
  5. Years of experience may not exceed limits.max_years_experience.
  6. Nothing on the limits.no_experience list may appear.
  7. Nothing on the limits.never_claim list may appear.
  8. Topics on limits.never_lead may not be paired with a leadership word.
  9. Terms in limits.context_rules may only appear next to the words that keep them honest
     (for example, AWS only in the context of migrating to Azure).
"""

from __future__ import annotations

import re
from datetime import date

from .profile import month_to_iso, skill_names

LEADERSHIP_WORDS = {
    "led",
    "lead",
    "leads",
    "leading",
    "owned",
    "owning",
    "ownership",
    "headed",
    "heading",
    "spearheaded",
    "spearheading",
    "directed",
    "directing",
    "championed",
    "architected",
    "oversaw",
    "oversee",
    "oversees",
    "overseeing",
    "managed",
    "manage",
    "manages",
    "managing",
    "supervised",
    "supervising",
    "mentored",
    "mentoring",
    "drove",
    "orchestrated",
    "pioneered",
    "founded",
    "chaired",
    "commanded",
    "ran",
    "running",
    "sole",
    "solely",
    "single-handedly",
    "independently",
    "singlehandedly",
}

# Multi-word ways of claiming ownership. Checked the same way as the words above.
LEADERSHIP_PHRASES = [
    "took charge",
    "in charge of",
    "responsible for",
    "accountable for",
    "point person",
    "on my own",
    "by myself",
    "took the lead",
    "took ownership",
    "go-to person",
]

# Words that make a claim bigger: scope, scale, and outcomes. They must appear in the evidence.
SCALE_WORDS = {
    "entire",
    "entirely",
    "whole",
    "end-to-end",
    "millions",
    "million",
    "billions",
    "billion",
    "thousands",
    "hundreds",
    "dozens",
    "tens",
    "half",
    "halved",
    "doubled",
    "tripled",
    "zero",
    "percent",
    "fortune",
    "enterprise-wide",
    "company-wide",
    "organization-wide",
    "globally",
    "global",
}

# Seniority words are only allowed when one of your job titles uses them.
TITLE_WORDS = {"senior", "principal", "staff", "chief", "head"}

INFLATION_WORDS = {
    "expert",
    "experts",
    "extensive",
    "extensively",
    "seasoned",
    "veteran",
    "mastery",
    "deep",
    "deeply",
    "world-class",
    "guru",
    "authority",
    "decade",
    "decades",
}

NUMBER_WORDS = {
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "hundred": 100,
    "thousand": 1000,
}

# Common technologies the AI might add even though they are not in your profile.
# Your profile skills, project stacks, and limits.no_experience are added to this list.
COMMON_TECH = [
    "Azure",
    "AWS",
    "GCP",
    "Google Cloud",
    "Docker",
    "Kubernetes",
    "Helm",
    "Terraform",
    "Ansible",
    "Pulumi",
    "Bicep",
    "ARM templates",
    "CloudFormation",
    "Jenkins",
    "GitHub Actions",
    "GitLab",
    "Azure DevOps",
    "Kafka",
    "RabbitMQ",
    "Event Hubs",
    "Spark",
    "Databricks",
    "Snowflake",
    "Power BI",
    "Fabric",
    "Tableau",
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "Go",
    "Golang",
    "Rust",
    "C#",
    "C++",
    "PHP",
    "Ruby",
    "Scala",
    "Kotlin",
    "PowerShell",
    "Bash",
    "React",
    "Angular",
    "Vue",
    "Vue.js",
    "Svelte",
    "Next.js",
    "Node.js",
    "ASP.NET",
    "Spring Boot",
    "Django",
    "Flask",
    "FastAPI",
    "PostgreSQL",
    "MySQL",
    "SQL Server",
    "Oracle",
    "MongoDB",
    "Cosmos DB",
    "DynamoDB",
    "Redis",
    "Elasticsearch",
    "GraphQL",
    "Prometheus",
    "Grafana",
    "Datadog",
    "Splunk",
    "New Relic",
    "OpenTelemetry",
    "Azure Monitor",
    "Okta",
    "Intune",
    "M365",
    "SharePoint",
    "ServiceNow",
    "Salesforce",
    "SAP",
    "Linux",
    "Windows Server",
    "VMware",
    "LangChain",
    "OpenAI",
    "TensorFlow",
    "PyTorch",
    "Airflow",
    "Lambda",
    "EC2",
    "S3",
    "SQS",
]

# Other ways the same tool is commonly written in a log.
ALIASES = {
    "kubernetes": ["k8s", "aks", "kubectl"],
    "azure kubernetes service": ["aks"],
    "azure active directory": ["aad", "entra"],
    "entra id": ["azure ad", "azure active directory", "aad"],
    "javascript": ["js"],
    "postgresql": ["postgres"],
    "m365": ["microsoft 365", "office 365", "o365"],
    "azure": ["aks", "entra"],
}

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#'./-]*")
NUMBER_RE = re.compile(r"(?<![\w.\-/])\$?(\d[\d,]*(?:\.\d+)?)(?=x\b|[^\w\-.]|\.(?!\d)|$)")
YEARS_RE = re.compile(
    r"(?:over|more than|nearly|almost|about|around|approximately|roughly|close to)?\s*"
    r"(\d+(?:\.\d+)?|" + "|".join(NUMBER_WORDS) + r")\s*\+?\s*(?:or more\s+)?(?:years?|yrs?)\b",
    re.IGNORECASE,
)


# ----- small text helpers -----------------------------------------------------


def words(text: str) -> set[str]:
    """Lowercase words, keeping hyphenated words whole so 'co-managed' is not 'managed'."""
    return {t.rstrip(".,;:/-'") for t in TOKEN_RE.findall(str(text).lower())}


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", str(text).strip()) if s.strip()]


IRREGULAR_VERBS = {
    "led",
    "built",
    "drove",
    "oversaw",
    "ran",
    "made",
    "wrote",
    "set",
    "took",
    "won",
    "began",
    "grew",
    "kept",
    "met",
    "sent",
    "spent",
    "brought",
    "taught",
    "held",
    "did",
    "found",
    "gave",
    "cut",
    "shipped",
    "lead",
    "own",
    "manage",
    "oversee",
    "head",
    "direct",
    "drive",
}


def _starts_with_verb(clause: str) -> bool:
    first = (TOKEN_RE.findall(clause.lower()) or [""])[0]
    # A part starting with an -ing word ("leading its rollout") describes the part before it, so it is joined to it.
    return first in IRREGULAR_VERBS or first.endswith("ed")


def clauses(text: str) -> list[str]:
    """Split text into the parts that each have their own action, so in
    'Contributed to IAM and oversaw AD migrations' the word 'oversaw' belongs to AD, not IAM.
    A part with no action of its own (like 'and IAM') is joined to the part before it,
    and a lone leadership word (like 'Led and') is joined to the part after it."""
    result: list[str] = []
    for sentence in sentences(text):
        parts = [p.strip() for p in re.split(r"[,;:]|\band\b|\bwhile\b|\bthen\b|\bincluding\b", sentence) if p.strip()]
        merged: list[str] = []
        carry = ""
        for part in parts:
            part = (carry + " " + part).strip() if carry else part
            carry = ""
            part_words = TOKEN_RE.findall(part.lower())
            if len(part_words) <= 2 and set(part_words) <= LEADERSHIP_WORDS | {"and", "co"}:
                carry = part
                continue
            if merged and not _starts_with_verb(part):
                merged[-1] = merged[-1] + " " + part
            else:
                merged.append(part)
        if carry:
            merged.append(carry)
        result += merged
    return result


def _term_pattern(term: str) -> str:
    return r"(?<![\w.+#\-])" + re.escape(term) + r"(?:s|es)?(?![\w+#])"


def has_term(text: str, term: str, case_sensitive: bool = False) -> bool:
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.search(_term_pattern(term), text, flags) is not None


def term_in_evidence(term: str, evidence: str) -> bool:
    candidates = [term] + ALIASES.get(term.lower(), [])
    if len(term) > 3 and term.lower().endswith("s"):
        candidates.append(term[:-1])
    return any(has_term(evidence, c) for c in candidates)


def _normalize_number(raw: str) -> str:
    value = raw.replace(",", "").replace("$", "")
    if "." in value:
        value = value.rstrip("0").rstrip(".")
    return value


SHORTHAND_RE = re.compile(r"(?<![\w.\-/])\$?(\d+(?:\.\d+)?)\s?([kKmMbB])\b")
SHORTHAND = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}


def _shorthand_numbers(text: str) -> set[str]:
    return {
        _normalize_number(repr(round(float(m.group(1)) * SHORTHAND[m.group(2).lower()], 6)))
        for m in SHORTHAND_RE.finditer(text)
    }


def numbers_in(text: str, skip_spans: list[tuple[int, int]] | None = None) -> set[str]:
    found = set()
    for match in NUMBER_RE.finditer(text):
        if skip_spans and any(a <= match.start() < b for a, b in skip_spans):
            continue
        found.add(_normalize_number(match.group(1)))
    for word in words(text):
        if word in NUMBER_WORDS:
            found.add(str(NUMBER_WORDS[word]))
    return found | _shorthand_numbers(text)


def _number_word_spans(text: str, skip_spans: list[tuple[int, int]]) -> set[str]:
    found = set()
    for match in re.finditer(r"\b(" + "|".join(NUMBER_WORDS) + r")\b", text, re.IGNORECASE):
        if not any(a <= match.start() < b for a, b in skip_spans):
            found.add(str(NUMBER_WORDS[match.group(1).lower()]))
    return found


def claimed_numbers(text: str, skip_spans: list[tuple[int, int]]) -> set[str]:
    found = set()
    for match in NUMBER_RE.finditer(text):
        if not any(a <= match.start() < b for a, b in skip_spans):
            found.add(_normalize_number(match.group(1)))
    return found | _number_word_spans(text, skip_spans) | _shorthand_numbers(text)


# ----- limits from profile.yaml -----------------------------------------------


def _months_between(start: str, end: str) -> int:
    s = date.fromisoformat(month_to_iso(start))
    e = (
        date.today()
        if str(end).strip().lower() in {"present", "current", "now"}
        else date.fromisoformat(month_to_iso(end))
    )
    return max(0, (e.year - s.year) * 12 + e.month - s.month + 1)


def max_years(profile: dict) -> float:
    limits = profile.get("limits") or {}
    if limits.get("max_years_experience") is not None:
        return float(limits["max_years_experience"])
    months = sum(_months_between(r["start"], r["end"]) for r in profile.get("roles", []) if not r.get("optional"))
    return round(months / 12, 1)


def _phrases(items) -> list[dict]:
    """never_claim entries may be plain text or {phrase, role}."""
    out = []
    for item in items or []:
        if isinstance(item, dict):
            out.append({"phrase": str(item.get("phrase", "")), "role": item.get("role")})
        else:
            out.append({"phrase": str(item), "role": None})
    return [p for p in out if p["phrase"].strip()]


def tech_terms(profile: dict) -> list[str]:
    terms = list(COMMON_TECH) + skill_names(profile)
    for project in profile.get("projects", []):
        terms += [t.strip() for t in str(project.get("stack", "")).split(",")]
    terms += [str(t) for t in (profile.get("limits") or {}).get("no_experience", [])]
    seen, result = set(), []
    for t in terms:
        if t and len(t) > 1 and t.lower() not in seen:
            seen.add(t.lower())
            result.append(t)
    return sorted(result, key=len, reverse=True)


# ----- the record: what counts as proof ---------------------------------------


def entry_text(entry: dict) -> str:
    """Only your own words count as proof, never the AI's summary of them."""
    return str(entry.get("raw_text", ""))


def entry_numbers(entry: dict) -> set[str]:
    nums = numbers_in(entry_text(entry))
    year = str(entry.get("entry_date", ""))[:4]
    if year.isdigit():
        nums.add(year)
    return nums


def record_text(profile: dict, evidence: list[dict]) -> str:
    """Everything in your record except the depth notes and limits, which describe what you have NOT done."""
    parts = [str(profile.get("summary_base", ""))]
    for role in profile.get("roles", []):
        parts += [role.get("title", ""), role.get("company", ""), str(role.get("start", "")), str(role.get("end", ""))]
        parts += [str(b) for b in role.get("bullets", [])]
    for group in profile.get("skills", []):
        parts += [str(i) for i in group.get("items", [])]
    parts += [str(c) for c in profile.get("certifications", [])]
    for p in profile.get("projects", []):
        parts += [str(p.get(k, "")) for k in ("name", "stack", "description")]
    for e in profile.get("education", []):
        parts += [str(e.get(k, "")) for k in ("credential", "school", "dates", "note")]
    parts += [entry_text(e) for e in evidence]
    return "\n".join(parts)


# ----- the checks -------------------------------------------------------------


def check_text(
    text: str, proof: str, proof_numbers: set[str], record: str, profile: dict, role_key: str | None = None
) -> list[str]:
    """Return the reasons this text is not supported. An empty list means it passed."""
    limits = profile.get("limits") or {}
    problems: list[str] = []
    lower = text.lower()
    text_words = words(text)
    proof_words = words(proof)

    for term in limits.get("no_experience", []) or []:
        if has_term(text, str(term)):
            problems.append(f"mentions {term}, which your profile lists as no experience")

    for item in _phrases(limits.get("never_claim")):
        if item["role"] and item["role"] != role_key:
            continue
        if has_term(text, item["phrase"]):
            problems.append(f"claims '{item['phrase']}', which your profile says never to claim")

    for topic in limits.get("never_lead", []) or []:
        for clause in clauses(text):
            hits = sorted(words(clause) & LEADERSHIP_WORDS) + [p for p in LEADERSHIP_PHRASES if p in clause.lower()]
            if has_term(clause, str(topic)) and hits:
                lead = hits[0]
                problems.append(f"says '{lead}' about {topic}, which your profile says was a team effort")

    for word in sorted(text_words & LEADERSHIP_WORDS):
        if word not in proof_words:
            problems.append(f"says '{word}' but the evidence does not")
    for phrase in LEADERSHIP_PHRASES:
        if phrase in lower and phrase not in proof.lower():
            problems.append(f"says '{phrase}' but the evidence does not")

    for word in sorted(text_words & SCALE_WORDS):
        if word not in proof_words and not (word == "end-to-end" and "end to end" in proof.lower()):
            problems.append(f"says '{word}', which makes the claim bigger than the evidence")

    for word in sorted(text_words & INFLATION_WORDS):
        if word not in proof_words:
            problems.append(f"says '{word}', which nothing in your record supports")

    title_words = words(" ".join(str(r.get("title", "")) for r in profile.get("roles", [])))
    for word in sorted(text_words & TITLE_WORDS):
        # A bullet may repeat the word when its own evidence uses it ("presented to senior leadership").
        # The summary has no single source, so there it must match a job title.
        in_own_evidence = role_key is not None and word in proof_words
        if word not in title_words and not in_own_evidence:
            problems.append(f"says '{word}', which nothing in your record supports")

    years_spans = []
    limit = max_years(profile)
    for match in YEARS_RE.finditer(text):
        years_spans.append(match.span())
        raw = match.group(1).lower()
        value = float(NUMBER_WORDS[raw]) if raw in NUMBER_WORDS else float(raw)
        if value > limit:
            problems.append(f"claims {match.group(0).strip()}, more than your {limit:g} years")

    for number in sorted(claimed_numbers(text, years_spans)):
        if number not in proof_numbers:
            problems.append(f"uses the number {number}, which is not in the evidence")

    for term in tech_terms(profile):
        if has_term(text, term, case_sensitive=True) and not term_in_evidence(term, proof):
            problems.append(f"mentions {term}, which is not in the evidence")

    for rule in limits.get("context_rules", []) or []:
        term = str(rule.get("term", ""))
        needed = [str(w).lower() for w in rule.get("require_any", [])]
        for sentence in sentences(text):
            if term and has_term(sentence, term) and not any(w in sentence.lower() for w in needed):
                problems.append(
                    f"mentions {term} without the context your profile requires "
                    f"({rule.get('reason', 'see depth notes')})"
                )
                break

    return list(dict.fromkeys(problems))


def check_skill(item: str, profile: dict) -> str | None:
    for term in (profile.get("limits") or {}).get("no_experience", []) or []:
        if has_term(item, str(term)):
            return f"Skill removed because your profile lists no experience with {term}: {item}"
    return None
