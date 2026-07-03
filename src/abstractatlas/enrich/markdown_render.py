"""Manuscript / section / claim markdown builders for the Stage 2 pipeline.

Lifted verbatim from the legacy `src/ohbm2026/enrichment.py` as part of
the Stage 5 package reorganization (specs/007-package-reorg/).

Mid-tier module: imports `enrich.text.html_to_markdown` (leaf) for HTML→
Markdown conversion. Consumed by `enrich/claims.py` and `enrich/stage.py`
when assembling the per-abstract Markdown blob handed to the claim
extractor.
"""

from __future__ import annotations

import json
from typing import Any

from ohbm2026.enrich.text import html_to_markdown

SECTION_ORDER: list[tuple[str, str]] = [
    ("introduction", "Introduction"),
    ("methods", "Methods"),
    ("results", "Results"),
    ("discussion", "Discussion"),
    ("conclusion", "Conclusion"),
    ("references", "References"),
    ("acknowledgement", "Acknowledgement"),
]
CLAIM_SECTION_ORDER: list[tuple[str, str]] = [
    ("introduction", "Introduction"),
    ("methods", "Methods"),
    ("results", "Results"),
    ("discussion", "Discussion"),
    ("conclusion", "Conclusion"),
]
SECTION_MARKDOWN_KEYS = {section_key: f"{section_key}_markdown" for section_key, _ in SECTION_ORDER}
CONTENT_QUESTION_NAMES: set[str] = {
    "Primary Parent Category & Sub-Category",
    "Secondary Parent Category & Sub-Category",
    "Keywords",
    "Which processing packages did you use for your study?",
    "For human MRI, what field strength scanner do you use?",
    'Please indicate below if your study was a "resting state" or "task-activation” study.',
    "Please indicate which methods were used in your research:",
    "Healthy subjects only or patients (note that patient studies may also involve healthy subjects).",
    "If other, please specify:",
    "If Other, please list the terms below. Multiple terms must be separated by semi-colons ( ; ).",
    "If yes:",
    "If other, please explain:",
}
NORMALIZED_CONTENT_QUESTION_NAMES = {normalize.lower() for normalize in CONTENT_QUESTION_NAMES}


def normalize_question_name(question_name: str | None) -> str:
    return (question_name or "").strip().lower()


def question_to_section(question_name: str | None) -> str | None:
    normalized = normalize_question_name(question_name)
    if normalized == "title":
        return "title"
    if normalized.startswith("introduction"):
        return "introduction"
    if normalized.startswith("methods") and "figure" not in normalized:
        return "methods"
    if normalized.startswith("results") and "figure" not in normalized:
        return "results"
    if normalized.startswith("discussion"):
        return "discussion"
    if normalized.startswith("conclusion"):
        return "conclusion"
    if normalized.startswith("references"):
        return "references"
    if normalized.startswith("acknowledgement") or normalized.startswith("acknowledgment"):
        return "acknowledgement"
    return None


def parse_list_value(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return [raw_value.strip()] if raw_value.strip() else []
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    if isinstance(parsed, str) and parsed.strip():
        return [parsed.strip()]
    return []


def build_sections_markdown(abstract: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, str]]]:
    sections: dict[str, list[str]] = {key: [] for key, _ in SECTION_ORDER}
    unmapped: list[dict[str, str]] = []
    for response_index, response in enumerate(abstract.get("responses", [])):
        value = response.get("value")
        if not isinstance(value, str) or not value.strip():
            continue
        section_key = question_to_section(response.get("question_name"))
        markdown = html_to_markdown(value)
        if not markdown:
            continue
        if section_key is None:
            unmapped.append(
                {
                    "question_name": response.get("question_name") or "",
                    "markdown": markdown,
                    "response_index": response_index,
                }
            )
        elif section_key != "title":
            sections[section_key].append(markdown)

    return {key: "\n\n".join(values).strip() for key, values in sections.items() if values}, unmapped


def is_content_question(question_name: str | None) -> bool:
    if not question_name:
        return False
    normalized = normalize_question_name(question_name)
    if normalized in NORMALIZED_CONTENT_QUESTION_NAMES:
        return True
    return False


def content_question_sort_key(item: dict[str, str]) -> tuple[int, str]:
    response_index = item.get("response_index")
    if isinstance(response_index, int):
        return (response_index, str(item.get("question_name") or ""))
    return (10_000, str(item.get("question_name") or ""))


def filter_content_questions_markdown(items: list[dict[str, str]]) -> list[dict[str, str]]:
    filtered = [
        item
        for item in items
        if is_content_question(item.get("question_name")) and item.get("markdown")
    ]
    ordered = sorted(filtered, key=content_question_sort_key)
    return [
        {
            "question_name": str(item.get("question_name") or ""),
            "markdown": str(item.get("markdown") or "").strip(),
        }
        for item in ordered
    ]


def figure_analysis_sort_key(entry: dict[str, Any]) -> tuple[int, str, str]:
    question_name = str(entry.get("question_name") or entry.get("source_question_name") or "").strip()
    normalized = normalize_question_name(question_name)
    if "methods" in normalized and "figure" in normalized:
        group = 0
    elif "results" in normalized and "figure" in normalized:
        group = 1
    else:
        group = 2
    return (
        group,
        question_name,
        str(entry.get("local_path") or ""),
    )


def sort_figure_analysis_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(list(entries), key=figure_analysis_sort_key)


def render_abstract_markdown(title: str, sections_markdown: dict[str, str]) -> str:
    parts = [f"# {title}"] if title else []
    for section_key, heading in SECTION_ORDER:
        section_value = sections_markdown.get(section_key)
        if section_value:
            parts.append(f"## {heading}\n\n{section_value}")
    return "\n\n".join(parts).strip()


def render_claim_section_markdown(title: str, sections_markdown: dict[str, str]) -> str:
    parts = [f"# {title}"] if title else []
    for section_key, heading in CLAIM_SECTION_ORDER:
        section_value = sections_markdown.get(section_key)
        if section_value:
            parts.append(f"## {heading}\n\n{section_value}")
    return "\n\n".join(parts).strip()


def render_additional_content_questions_markdown(items: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for item in items:
        question_name = str(item.get("question_name") or "").strip()
        markdown = str(item.get("markdown") or "").strip()
        if not markdown:
            continue
        if question_name:
            parts.append(f"### {question_name}\n\n{markdown}")
        else:
            parts.append(markdown)
    return "\n\n".join(parts).strip()


def render_figure_analyses_markdown(figure_analyses: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for index, entry in enumerate(sort_figure_analysis_entries(figure_analyses), start=1):
        analysis = entry.get("analysis") if isinstance(entry, dict) else {}
        if not isinstance(analysis, dict):
            analysis = {}
        subsection_parts: list[str] = []
        label = str(entry.get("question_name") or "").strip() if isinstance(entry, dict) else ""
        heading = label or f"Figure {index}"
        caption_guess = str(analysis.get("caption_guess") or "").strip()
        rich_markdown = str(analysis.get("rich_markdown") or "").strip()
        ocr_text = str(analysis.get("ocr_text") or "").strip()
        notes = str(analysis.get("notes") or "").strip()
        if caption_guess:
            subsection_parts.append(f"**Caption guess:** {caption_guess}")
        if rich_markdown:
            subsection_parts.append(rich_markdown)
        if ocr_text:
            subsection_parts.append(f"**OCR text:** {ocr_text}")
        if notes:
            subsection_parts.append(f"**Notes:** {notes}")
        if subsection_parts:
            parts.append(f"### {heading}\n\n" + "\n\n".join(subsection_parts))
    return "\n\n".join(parts).strip()


def build_claim_manuscript_markdown(
    title: str,
    sections_markdown: dict[str, str],
    additional_content_questions: list[dict[str, str]],
    figure_analyses: list[dict[str, Any]] | None = None,
) -> str:
    parts: list[str] = []
    abstract_markdown = render_claim_section_markdown(title, sections_markdown)
    if abstract_markdown:
        parts.append(abstract_markdown)
    elif title:
        parts.append(f"# {title}")
    figure_markdown = render_figure_analyses_markdown(list(figure_analyses or []))
    if figure_markdown:
        parts.append(f"## Figure Analyses\n\n{figure_markdown}")
    additional_content_markdown = render_additional_content_questions_markdown(additional_content_questions)
    if additional_content_markdown:
        parts.append(f"## Additional Content\n\n{additional_content_markdown}")
    manuscript = "\n\n".join(part for part in parts if part).strip()
    return manuscript or (title.strip() if title else "Untitled abstract")
