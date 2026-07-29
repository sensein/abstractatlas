"""NeuroScape adapter — the PubMed-corpus incumbent behind ``AbstractSource``.

Read-only re-expression of the per-article identity fields the NeuroScape
loader exposes (``ArticleHeader``: ``pubmed_id`` / ``title`` / ``year`` /
``cluster_id``) as the canonical
:class:`~ohbm2026.sources.base.AbstractRecord`. Writes nothing and changes no
on-disk artifact (FR-008).

NeuroScape deliberately does NOT store bodies locally (abstract text, authors,
journal, DOI are fetched at view time via NCBI EFetch — 2026-05-23
clarification), so the record's ``abstract`` is ``None`` and ``sections`` is
empty. That is faithful to the source, not a missing mapping.

The adapter duck-types its input — a ``Mapping`` OR any object exposing the
four attributes — so the light, stdlib-only ``sources`` layer never imports the
heavy loader (h5py / numpy).
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from ohbm2026.sources.base import (
    AbstractRecord,
    BaseAbstractSource,
    SourceDescriptor,
    SourceNormalizationError,
    SourceProvenance,
    digest_raw,
)

_SOURCE = "neuroscape"
_VENUE = "NeuroScape (PubMed)"
_PUBMED_URL = "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"


def _field(raw: Any, key: str) -> Any:
    """Read ``key`` from a Mapping or an attribute-bearing object."""
    if isinstance(raw, Mapping):
        return raw.get(key)
    return getattr(raw, key, None)


class NeuroScapeSource(BaseAbstractSource):
    """Adapter over NeuroScape per-article headers.

    Parameters
    ----------
    fetched_at:
        Optional ISO timestamp stamped into provenance (injected).
    """

    def __init__(self, *, fetched_at: str | None = None) -> None:
        self._fetched_at = fetched_at

    @property
    def descriptor(self) -> SourceDescriptor:
        return SourceDescriptor(
            name=_SOURCE,
            kind="corpus",
            title="NeuroScape",
            homepage="https://pubmed.ncbi.nlm.nih.gov",
            notes="NeuroScape PubMed corpus; bodies fetched at view time via NCBI EFetch.",
        )

    def fetch_raw(self, query: Any) -> Iterable[Any]:
        """Yield raw article headers.

        ``query`` is a list/iterable of ``ArticleHeader``-like objects or
        mappings (the loader owns discovery/HDF5 iteration; this adapter
        stays dependency-light and operates on already-loaded headers).
        """
        if query is None:
            raise SourceNormalizationError(
                "NeuroScapeSource.fetch_raw requires an iterable of article headers "
                "(the loader owns corpus discovery; this adapter maps already-loaded headers)"
            )
        return list(query)

    def normalize(self, raw: Any) -> AbstractRecord:
        pubmed_id = _field(raw, "pubmed_id")
        if pubmed_id is None or str(pubmed_id).strip() == "":
            raise SourceNormalizationError("NeuroScape record missing required 'pubmed_id'")
        title = _field(raw, "title")
        if not isinstance(title, str) or not title.strip():
            raise SourceNormalizationError(
                f"NeuroScape record {pubmed_id!r} missing required non-empty 'title'"
            )
        year = _field(raw, "year")
        cluster_id = _field(raw, "cluster_id")

        canonical = {"pubmed_id": pubmed_id, "title": title, "year": year, "cluster_id": cluster_id}
        extra = {k: v for k, v in {"cluster_id": cluster_id}.items() if v is not None}

        return AbstractRecord(
            source=_SOURCE,
            native_id=str(pubmed_id),
            title=title,
            display_id=str(pubmed_id),
            abstract=None,
            venue=_VENUE,
            year=int(year) if isinstance(year, (int, str)) and str(year).lstrip("-").isdigit() else None,
            url=_PUBMED_URL.format(pmid=pubmed_id),
            extra=extra,
            provenance=SourceProvenance(
                source=_SOURCE,
                descriptor=self.descriptor,
                fetched_at=self._fetched_at,
                raw_digest=digest_raw(canonical),
            ),
        )
