"""Stage 3 component-text assembler.

Pure functions that read an enriched-abstract record and return the
canonical string for one named component (`title`, `introduction`,
`methods`, `results`, `conclusion`, `claims`, `inference_claims`).
No I/O; the orchestrator handles SQLite reads and feeds dicts in.

The component recipes are documented in
`specs/005-embeddings-matrix/data-model.md` §1.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from ohbm2026.enrich.text import html_to_markdown

__all__ = [
    "DEFAULT_COMPONENTS",
    "PARTIAL_COMPONENTS",
    "ALL_COMPONENTS",
    "assemble_component",
    "assemble_all_components",
    "abstract_has_component",
]


DEFAULT_COMPONENTS: tuple[str, ...] = (
    "title",
    "introduction",
    "methods",
    "results",
    "conclusion",
    "claims",
)
PARTIAL_COMPONENTS: tuple[str, ...] = ("inference_claims",)
ALL_COMPONENTS: tuple[str, ...] = DEFAULT_COMPONENTS + PARTIAL_COMPONENTS

_PROSE_COMPONENTS = {"introduction", "methods", "results", "conclusion"}
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_whitespace(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", (value or "")).strip()


def _render_section_value(value: str) -> str:
    if not value or not value.strip():
        return ""
    # The enrichment helper already handles HTML→markdown for Oxford
    # Abstracts payloads; reuse it for consistency across stages (and
    # for any source whose section bodies carry markup).
    return _normalize_whitespace(html_to_markdown(value))


def _section_text(record: dict, component: str) -> str:
    """Return the prose text for a section component.

    Resolves against two record shapes, in this order (Arc A'.2 —
    specs/027-multi-source-foundation):

    1. ``record["sections"]`` — the canonical `AbstractRecord` open
       section mapping, which any source can populate with its own
       section vocabulary.
    2. ``record["responses"]`` — the Oxford Abstracts shape, matched on
       ``question_name``.

    Both matches are case-insensitive. When ``sections`` contains the key
    it wins outright (even if empty), so a source can explicitly assert
    "this section exists and is blank"; when the key is absent entirely,
    resolution falls through to ``responses`` so the legacy OHBM path is
    untouched.
    """
    target = component.strip().lower()

    sections = record.get("sections")
    if isinstance(sections, Mapping):
        for name, value in sections.items():
            if isinstance(name, str) and name.strip().lower() == target:
                return _render_section_value(value if isinstance(value, str) else "")

    for response in record.get("responses") or []:
        name = (response.get("question_name") or "").strip().lower()
        if name == target:
            return _render_section_value(response.get("value") or "")
    return ""


def _claims_text(record: dict, *, filter_implicit: bool = False) -> str:
    claims: Iterable[dict] = record.get("claims") or []
    chunks: list[str] = []
    for claim in claims:
        if filter_implicit and claim.get("claim_type") != "IMPLICIT":
            continue
        text = (claim.get("claim") or "").strip()
        if text:
            chunks.append(text)
    return "\n\n".join(chunks)


def assemble_component(record: dict, component: str) -> str:
    """Assemble the canonical text for one component of one abstract.

    Returns an empty string when the abstract lacks content for the
    requested component (e.g., the introduction section is missing
    or the IMPLICIT-only claims list is empty). The orchestrator
    treats an empty result as "this abstract is absent from this
    component's bundle".

    Raises `ValueError` if the component name is not recognized.
    """
    if component == "title":
        return _normalize_whitespace(record.get("title") or "")
    if component in _PROSE_COMPONENTS:
        return _section_text(record, component)
    if component == "claims":
        return _claims_text(record)
    if component == "inference_claims":
        return _claims_text(record, filter_implicit=True)
    raise ValueError(f"unknown component {component!r}")


def assemble_all_components(
    record: dict, components: Iterable[str]
) -> dict[str, str]:
    """Convenience wrapper: assemble every requested component for one
    record in one pass. Useful when the orchestrator wants to
    materialize the text matrix up front."""
    return {comp: assemble_component(record, comp) for comp in components}


def abstract_has_component(record: dict, component: str) -> bool:
    """True iff `assemble_component(record, component)` would return a
    non-empty string. Cheap probe used by the coverage gate."""
    return bool(assemble_component(record, component))
