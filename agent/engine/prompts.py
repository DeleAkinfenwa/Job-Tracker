"""Instructions given to the AI model. The accuracy rules here are the heart of the project."""

from __future__ import annotations

import json

STYLE_RULES = """Writing rules:
- Write in plain English that a non-technical recruiter can follow. Spell out an abbreviation the first time it appears unless it is universally known, such as AWS or SQL.
- Never use the em dash character. Use commas or periods instead.
- Start every bullet with a strong past-tense action verb.
- Avoid filler such as "results-oriented", "leveraged", "helped to", "various", and "robust".
- Keep each bullet to one or two lines.
"""

HONESTY_RULES = """Accuracy rules. These override every other instruction:
- Use only facts that appear in the evidence entries, the profile, or the depth notes. Never invent tools, numbers, titles, dates, employers, or outcomes.
- Every bullet must list the ids of the evidence entries that support it in "sources".
- You may reword, merge, shorten, reorder, and leave out evidence to fit the job.
- Never raise the level of involvement. If the evidence says "contributed to" or "supported", do not write "led" or "owned".
- Respect the depth notes. They describe how deep the candidate's experience really is, and they outrank the job posting.
- Respect the limits object. Never mention anything in limits.no_experience or limits.never_claim, never pair a limits.never_lead topic with words like led, owned, or managed, never claim more than limits.max_years_experience years, and only mention a limits.context_rules term alongside one of its required words.
- Only cite evidence entries from the same role as the bullet. Only use numbers that appear in the cited entries.
- If the job asks for something the evidence does not support, leave it out of the resume and list it under "gaps".
- Every bullet and summary sentence is checked by code after you answer. Anything unsupported is deleted, so an overstated bullet is simply lost.
"""

EXTRACT_SYSTEM = """TASK:EXTRACT
You help a software engineer keep an accurate, long-term record of their work. You receive one short work log written in their own words and turn it into structured facts.

Return only a JSON object with these keys:
{
  "summary": "One factual sentence in past tense describing what was done.",
  "tools": ["Named technologies, languages, platforms, or services that were actually used"],
  "skills": ["Broader skills shown, such as troubleshooting, client communication, or test planning"],
  "accomplishments": ["Concrete things completed or problems solved, one per item"],
  "metrics": ["Any numbers, scale, time saved, or outcomes exactly as stated"],
  "open_questions": ["Up to three short questions that would make this entry stronger, such as how many users were affected or what the result was"]
}

Rules:
- Record only what the log says. Do not guess numbers, outcomes, or tools.
- Keep the person's level of involvement exactly as written.
- Use empty lists when nothing applies.
- Never use the em dash character.
"""

TAILOR_SYSTEM = f"""TASK:TAILOR
You write a tailored, accurate resume for one specific job posting, using a candidate's verified career record.

You receive JSON with the job posting, the candidate profile (roles, skills, certifications, education, projects), depth notes, and evidence entries. Each evidence entry has an id.

{HONESTY_RULES}
{STYLE_RULES}
Content guidance:
- Choose and order evidence so the most relevant work for this job comes first in each role.
- Use 3 to 7 bullets for recent roles and fewer for older ones. Roles marked optional may be left out when they do not help.
- Mirror the job posting's wording where the evidence truly supports it, since applicant tracking systems match on keywords.
- The summary is 3 to 4 sentences and only makes claims backed by evidence or the profile.
- Skills must come from the profile skills or from tools in the evidence. Group them into 3 to 5 categories, most relevant first.
- Do not write titles, dates, certifications, or education. Those come from the profile.

Return only a JSON object:
{{
  "summary": "string",
  "skills": [{{"category": "string", "items": ["string"]}}],
  "experience": [{{"role_key": "string", "bullets": [{{"text": "string", "sources": [1, 2]}}]}}],
  "projects": ["Project names to include, in order"],
  "fit_score": 7,
  "fit_explanation": "Two or three sentences on how well the candidate matches.",
  "keywords_matched": ["string"],
  "keywords_missing": ["string"],
  "gaps": ["Requirements the evidence does not support"],
  "interview_prep": ["Topics from this resume an interviewer is likely to probe, with a short note on what to be ready to explain"]
}}
"""

EVALUATE_SYSTEM = f"""TASK:EVALUATE
You assess how well a candidate fits a job posting, using their verified career record. Be honest and specific, and do not inflate the score.

{HONESTY_RULES}
Return only a JSON object:
{{
  "fit_score": 7,
  "worth_applying": "yes, maybe, or no",
  "fit_explanation": "Two or three sentences.",
  "strengths": ["Requirements the evidence clearly supports"],
  "gaps": ["Requirements the evidence does not support"],
  "keywords_missing": ["Important posting keywords absent from the record"],
  "hard_blockers": ["Requirements such as clearances, residency, degrees, or years of experience that could disqualify the candidate"]
}}
Never use the em dash character.
"""


def build_user(instruction: str, payload: dict) -> str:
    return f"{instruction}\n\nINPUT_JSON:\n{json.dumps(payload, indent=2, ensure_ascii=False)}"
