"""Writing the resume (Word and Markdown) and the fit report."""

from __future__ import annotations

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from .profile import role_by_key

MARGIN_IN = 0.7
PAGE_WIDTH_IN = 8.5


def _contact_line(profile: dict) -> str:
    c = profile.get("contact", {})
    parts = [c.get(k) for k in ("location", "phone", "website", "email", "linkedin")]
    return "  |  ".join(p for p in parts if p)


def _roles_in_order(doc: dict, profile: dict) -> list[tuple[dict, list[str]]]:
    """Profile order. Required roles always appear; optional roles only when the model used them."""
    chosen = {r["role_key"]: [b["text"] for b in r["bullets"]] for r in doc["experience"]}
    result = []
    for role in profile.get("roles", []):
        bullets = chosen.get(role["key"])
        if bullets:
            result.append((role, bullets))
        elif not role.get("optional"):
            result.append((role, list(role.get("bullets", []))[:3]))
    return result


def _projects(doc: dict, profile: dict) -> list[dict]:
    by_name = {p["name"]: p for p in profile.get("projects", [])}
    return [by_name[n] for n in doc["projects"] if n in by_name]


def to_markdown(doc: dict, profile: dict) -> str:
    c = profile.get("contact", {})
    lines = [f"# {c.get('name', '')}", "", _contact_line(profile), "", "## Summary", "", doc["summary"], ""]
    if doc["skills"]:
        lines += ["## Skills", ""]
        lines += [f"**{g['category']}:** {', '.join(g['items'])}  " for g in doc["skills"]]
        lines.append("")
    if profile.get("certifications"):
        lines += ["## Certifications", ""] + [f"- {cert}" for cert in profile["certifications"]] + [""]
    lines += ["## Experience", ""]
    for role, bullets in _roles_in_order(doc, profile):
        lines += [f"### {role['title']}, {role['company']}", f"*{role['start']} - {role['end']}*", ""]
        lines += [f"- {b}" for b in bullets] + [""]
    projects = _projects(doc, profile)
    if projects:
        lines += ["## Projects", ""]
        for p in projects:
            lines += [f"**{p['name']}** | {p.get('stack', '')} | {p.get('link', '')}", "", p.get("description", ""), ""]
    if profile.get("education"):
        lines += ["## Education", ""]
        for e in profile["education"]:
            lines.append(f"**{e['credential']}, {e['school']}**  {e.get('dates', '')}  ")
            if e.get("note"):
                lines.append(e["note"])
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def _bottom_border(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    for attr, value in (("w:val", "single"), ("w:sz", "6"), ("w:space", "1"), ("w:color", "444444")):
        bottom.set(qn(attr), value)
    borders.append(bottom)
    p_pr.append(borders)


def to_docx(doc: dict, profile: dict, path) -> None:
    """An ATS-friendly Word file: single column, no tables, real text everywhere. path may be a file object."""
    d = Document()
    section = d.sections[0]
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Inches(MARGIN_IN))
    normal = d.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(2)
    right_edge = Inches(PAGE_WIDTH_IN - 2 * MARGIN_IN)

    def heading(text: str) -> None:
        p = d.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(12)
        _bottom_border(p)

    def left_right(left: str, right: str, bold_left: bool = True) -> None:
        p = d.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.tab_stops.add_tab_stop(right_edge, WD_TAB_ALIGNMENT.RIGHT)
        p.add_run(left).bold = bold_left
        if right:
            r = p.add_run("\t" + right)
            r.italic = True

    contact = profile.get("contact", {})
    name = d.add_paragraph()
    name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = name.add_run(contact.get("name", ""))
    run.bold = True
    run.font.size = Pt(18)
    line = d.add_paragraph()
    line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = line.add_run(_contact_line(profile))
    r.font.size = Pt(9.5)
    r.font.color.rgb = RGBColor(0x44, 0x44, 0x44)

    heading("Summary")
    d.add_paragraph(doc["summary"])

    if doc["skills"]:
        heading("Skills")
        for group in doc["skills"]:
            p = d.add_paragraph()
            p.add_run(f"{group['category']}: ").bold = True
            p.add_run(", ".join(group["items"]))

    if profile.get("certifications"):
        heading("Certifications")
        for cert in profile["certifications"]:
            d.add_paragraph(cert)

    heading("Experience")
    for role, bullets in _roles_in_order(doc, profile):
        left_right(f"{role['title']}, {role['company']}", f"{role['start']} - {role['end']}")
        for b in bullets:
            d.add_paragraph(b, style="List Bullet")

    projects = _projects(doc, profile)
    if projects:
        heading("Projects")
        for p in projects:
            para = d.add_paragraph()
            para.paragraph_format.space_before = Pt(6)
            para.add_run(p["name"]).bold = True
            extra = " | ".join(x for x in (p.get("stack"), p.get("link")) if x)
            if extra:
                para.add_run(f" | {extra}")
            d.add_paragraph(p.get("description", ""))

    if profile.get("education"):
        heading("Education")
        for e in profile["education"]:
            left_right(f"{e['credential']}, {e['school']}", e.get("dates", ""))
            if e.get("note"):
                d.add_paragraph(e["note"])

    d.save(path)


def report_markdown(doc: dict, profile: dict, job_name: str) -> str:
    lines = [
        f"# Fit report: {job_name}",
        "",
        f"**Fit score:** {doc.get('fit_score')} out of 10",
        "",
        doc["fit_explanation"],
        "",
    ]

    def section(title: str, items: list[str], empty: str = "None") -> None:
        lines.extend([f"## {title}", ""])
        lines.extend([f"- {i}" for i in items] if items else [empty])
        lines.append("")

    section("Keywords matched", doc["keywords_matched"])
    section("Keywords missing", doc["keywords_missing"])
    section("Gaps (left off the resume on purpose)", doc["gaps"])
    section("Be ready to explain in an interview", doc["interview_prep"])
    section("Removed by the accuracy check", doc["removed"], "Nothing was removed.")

    lines += ["## Where each bullet came from", ""]
    for role in doc["experience"]:
        info = role_by_key(profile, role["role_key"]) or {}
        lines.append(f"**{info.get('company', role['role_key'])}**")
        lines += [f"- {b['text']}  (log entries: {', '.join(map(str, b['sources']))})" for b in role["bullets"]]
        lines.append("")
    lines.append(f"Evidence entries reviewed: {doc['evidence_count']}")
    return "\n".join(lines).strip() + "\n"


def evaluation_markdown(result: dict, job_name: str) -> str:
    lines = [
        f"# Evaluation: {job_name}",
        "",
        f"**Fit score:** {result.get('fit_score')} out of 10",
        f"**Worth applying:** {result.get('worth_applying')}",
        "",
        result["fit_explanation"],
        "",
    ]
    for title, key in (
        ("Strengths", "strengths"),
        ("Gaps", "gaps"),
        ("Keywords missing", "keywords_missing"),
        ("Possible blockers", "hard_blockers"),
    ):
        lines += [f"## {title}", ""] + ([f"- {i}" for i in result[key]] or ["None"]) + [""]
    return "\n".join(lines).strip() + "\n"
