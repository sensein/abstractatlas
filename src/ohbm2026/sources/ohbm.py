"""OHBM 2026 adapter — the Oxford-Abstracts incumbent behind ``AbstractSource``.

Read-only re-expression of the shape ``assets.normalize_abstract`` already
produces (the Stage 1 corpus record) as the canonical
:class:`~ohbm2026.sources.base.AbstractRecord`. It writes nothing and changes
no on-disk artifact (FR-008) — it exists so the existing OHBM corpus can flow
through the same interface as any new source, and so the ``responses[]`` custom
questions become named ``sections`` (the generalization of the fixed six
embed components) rather than being matched by literal ``question_name``
downstream.

Author *details* are not part of the Stage 1 abstract record (they live in the
separate ``authors.json`` normalized dataset); the abstract dict carries only
``{author_order, id}`` stubs, which are preserved verbatim in
``extra["author_refs"]`` so nothing is lost. A future join can hydrate full
:class:`AbstractAuthor`s.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ohbm2026 import artifacts
from ohbm2026.sources.base import (
    AbstractRecord,
    BaseAbstractSource,
    SourceDescriptor,
    SourceNormalizationError,
    SourceProvenance,
    digest_raw,
)

_SOURCE = "ohbm2026"
_VENUE = "OHBM 2026"


class OhbmSource(BaseAbstractSource):
    """Adapter over the OHBM Stage 1 normalized corpus.

    Parameters
    ----------
    corpus_path:
        Default corpus JSON to read when :meth:`fetch_raw` is given no
        explicit records. Defaults to
        :data:`artifacts.PRIMARY_ABSTRACTS_PATH`.
    fetched_at:
        Optional ISO timestamp stamped into provenance (injected, never
        read from the clock inline).
    """

    def __init__(self, corpus_path: Path | None = None, *, fetched_at: str | None = None) -> None:
        self._corpus_path = Path(corpus_path) if corpus_path else artifacts.PRIMARY_ABSTRACTS_PATH
        self._fetched_at = fetched_at

    @property
    def descriptor(self) -> SourceDescriptor:
        return SourceDescriptor(
            name=_SOURCE,
            kind="conference",
            title="OHBM 2026",
            homepage="https://www.humanbrainmapping.org",
            notes="Oxford Abstracts GraphQL corpus (Stage 1 normalized record).",
        )

    def fetch_raw(self, query: Any) -> Iterable[Mapping[str, Any]]:
        """Yield Stage 1 abstract records.

        ``query`` may be: a list/tuple of record mappings (in-memory,
        used by tests); a mapping with an ``"abstracts"`` list (a corpus
        envelope); or a path / ``None`` (read the corpus JSON, expecting a
        top-level ``"abstracts"`` list). A malformed shape raises rather
        than yielding nothing silently.
        """
        if isinstance(query, (list, tuple)):
            records: Iterable[Any] = query
        elif isinstance(query, Mapping) and "abstracts" in query:
            records = query["abstracts"]
        else:
            records = self._read_corpus(query)
        for item in records:
            if not isinstance(item, Mapping):
                raise SourceNormalizationError(f"OHBM record was not a mapping: {type(item)!r}")
            yield item

    def normalize(self, raw: Mapping[str, Any]) -> AbstractRecord:
        native_id = raw.get("id")
        if native_id is None or str(native_id).strip() == "":
            raise SourceNormalizationError("OHBM record missing required 'id'")
        title = raw.get("title")
        if not isinstance(title, str) or not title.strip():
            raise SourceNormalizationError(f"OHBM record {native_id!r} missing required non-empty 'title'")

        sections = {
            item["question_name"]: item["value"]
            for item in raw.get("responses", [])
            if isinstance(item, Mapping)
            and isinstance(item.get("question_name"), str)
            and isinstance(item.get("value"), str)
            and item["value"].strip()
        }
        figure_urls = tuple(
            item["source_url"]
            for item in raw.get("figure_urls", [])
            if isinstance(item, Mapping) and isinstance(item.get("source_url"), str) and item["source_url"]
        )
        poster_id = raw.get("poster_id")
        extra = {
            "accepted_for": raw.get("accepted_for"),
            "program_sessions": raw.get("program_sessions"),
            "external_urls": raw.get("external_urls"),
            "author_refs": raw.get("authors"),
        }
        extra = {k: v for k, v in extra.items() if v not in (None, [], "")}

        return AbstractRecord(
            source=_SOURCE,
            native_id=str(native_id),
            title=title,
            display_id=str(poster_id) if poster_id not in (None, "") else None,
            abstract=None,
            sections=sections,
            venue=_VENUE,
            figure_urls=figure_urls,
            extra=extra,
            provenance=SourceProvenance(
                source=_SOURCE,
                descriptor=self.descriptor,
                fetched_at=self._fetched_at,
                raw_digest=digest_raw(raw),
            ),
        )

    # -- helpers -----------------------------------------------------------

    def _read_corpus(self, query: Any) -> Iterable[Mapping[str, Any]]:
        path = Path(query) if isinstance(query, (str, Path)) else self._corpus_path
        if not path.exists():
            raise SourceNormalizationError(f"OHBM corpus not found at {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SourceNormalizationError(f"OHBM corpus at {path} is not valid JSON: {exc}") from exc
        abstracts = payload.get("abstracts") if isinstance(payload, Mapping) else None
        if not isinstance(abstracts, list):
            raise SourceNormalizationError(f"OHBM corpus at {path} has no top-level 'abstracts' list")
        return abstracts
