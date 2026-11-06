"""A fake model for tests and offline demos. It needs no API key.

It deliberately returns a few bad outputs (an em dash, an unsupported bullet, an
overstated bullet, an inflated summary sentence, and a skill that is not in the record)
so the tests prove the safety checks work.
"""

from __future__ import annotations

import json
import re

from .profile import tokens

KNOWN_TOOLS = [
    "Azure",
    "AWS",
    "Docker",
    "Kubernetes",
    "Terraform",
    "Python",
    "JavaScript",
    "React",
    "Node.js",
    "PostgreSQL",
    "SQL",
    "MongoDB",
    "Redis",
    "Git",
    "Azure DevOps",
    "Azure Monitor",
    "Postman",
    "PowerShell",
    "Kafka",
    "Bicep",
    "Java",
]


def _payload(user: str) -> dict:
    marker = "INPUT_JSON:"
    idx = user.find(marker)
    return json.loads(user[idx + len(marker) :]) if idx != -1 else {}


def _found(tool: str, text: str) -> bool:
    return re.search(r"(?<![\w.])" + re.escape(tool) + r"(?![\w])", text, re.IGNORECASE) is not None


class MockLLM:
    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        payload = _payload(user)
        if "TASK:EXTRACT" in system:
            return json.dumps(self._extract(payload))
        if "TASK:TAILOR" in system:
            return json.dumps(self._tailor(payload))
        if "TASK:EVALUATE" in system:
            return json.dumps(self._evaluate(payload))
        return "{}"

    def _extract(self, p: dict) -> dict:
        log = p.get("log", "").strip()
        first = re.split(r"(?<=[.!?])\s", log)[0] if log else ""
        return {
            "summary": first,
            "tools": [t for t in KNOWN_TOOLS if _found(t, log)],
            "skills": [],
            "accomplishments": [first] if first else [],
            "metrics": re.findall(r"\d[\d,]*\+?", log),
            "open_questions": ["What was the measurable result?"],
        }

    def _missing(self, p: dict) -> list[str]:
        profile = p.get("profile", {})
        vocab: set[str] = set()
        for group in profile.get("skills", []):
            for item in group.get("items", []):
                vocab |= tokens(item)
        for entry in p.get("evidence", []):
            for tool in entry.get("tools", []):
                vocab |= tokens(tool)
        job = p.get("job_posting", "")
        return [t for t in KNOWN_TOOLS if _found(t, job) and not tokens(t) <= vocab]

    def _tailor(self, p: dict) -> dict:
        evidence = p.get("evidence", [])
        experience = []
        for role in p.get("profile", {}).get("roles", []):
            items = [e for e in evidence if e["role"] == role["key"]][:6]
            if items:
                experience.append(
                    {
                        "role_key": role["key"],
                        "bullets": [{"text": e["summary"], "sources": [e["id"]]} for e in items],
                    }
                )
        if experience:
            first = experience[0]["bullets"][0]
            experience[0]["bullets"].append({"text": "Unsupported claim that should be dropped.", "sources": [999999]})
            experience[0]["bullets"].append(
                {"text": "Led a team of 12 engineers to deliver the work.", "sources": first["sources"]}
            )
            # Written as a string id to prove valid bullets are not lost to formatting.
            first["sources"] = [str(s) for s in first["sources"]]
        skills = [
            {"category": g["category"], "items": list(g["items"])} for g in p.get("profile", {}).get("skills", [])
        ]
        if skills:
            skills[0]["items"].append("Kafka")
        missing = self._missing(p)
        return {
            "summary": (
                "Software engineer \u2014 cloud and full-stack work, written only from the record. "
                "Brings 10 years of experience."
            ),
            "skills": skills,
            "experience": experience,
            "projects": [proj["name"] for proj in p.get("profile", {}).get("projects", [])],
            "fit_score": 6,
            "fit_explanation": "Mock assessment for testing.",
            "keywords_matched": [],
            "keywords_missing": missing,
            "gaps": missing,
            "interview_prep": ["Be ready to explain the most recent log entry."],
        }

    def _evaluate(self, p: dict) -> dict:
        missing = self._missing(p)
        return {
            "fit_score": 6,
            "worth_applying": "maybe",
            "fit_explanation": "Mock assessment for testing.",
            "strengths": ["Cloud migration experience"],
            "gaps": missing,
            "keywords_missing": missing,
            "hard_blockers": [],
        }
