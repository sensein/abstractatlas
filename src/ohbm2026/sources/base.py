"""Source-neutral canonical record + the ``AbstractSource`` interface.

Design (``specs/027-multi-source-foundation/data-model.md`` and
``contracts/abstract-source.md``):

The pipeline today has no shared notion of "a record" — OHBM ingest
returns an untyped ``dict`` keyed on ``poster_id`` (Oxford
``program_code``) while the NeuroScape loader returns a different
dataclass keyed on ``pubmed_id``. The two never share a contract. This
module defines the missing seam so a third family (a preprint feed,
another conference, an arbitrary corpus) plugs in behind ONE interface
instead of becoming a new silo.

Every record carries a stable, global identity ``record_uid =
"<source>:<native_id>"`` plus machine-readable :class:`SourceProvenance`
— the two things a downstream knowledge graph (issue #66) needs and the
current per-corpus id namespaces cannot provide.

Principle VI: validation failures raise the typed
:class:`SourceNormalizationError`; nothing is silently coerced or
dropped. Principle VII: sources discover their fields from the payload
and surface mismatches as errors (see :mod:`ohbm2026.sources.biorxiv`).
"""

from __future__ import annotations

import abc
import hashlib
import json
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Iterable, Iterator, Mapping, Protocol, runtime_checkable

from ohbm2026.exceptions import OhbmStageError

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SourceError(OhbmStageError):
    """Any failure originating in the multi-source ingest layer.

    Roots under :class:`~ohbm2026.exceptions.OhbmStageError` so callers
    can catch "any pipeline-stage failure" uniformly, mirroring the
    Stage 1/2/3 subtrees.
    """


class SourceNormalizationError(SourceError):
    """A raw source payload could not be normalized into an
    :class:`AbstractRecord` — a required field was missing/empty, an
    identifier was malformed, or a descriptor was invalid.

    Raised loudly rather than skipping the record (Principle VI/VII).
    """


# ---------------------------------------------------------------------------
# Identity + digest helpers
# ---------------------------------------------------------------------------

_UID_DELIMITER = ":"

# The vocabulary of source kinds. Deliberately small and open to
# extension via a new spec; NOT a hardcoded per-source allow-list —
# every concrete source declares which kind it is.
VALID_SOURCE_KINDS = frozenset({"conference", "preprint", "journal", "corpus", "talk", "other"})


def build_record_uid(source: str, native_id: str) -> str:
    """Compose the stable global id ``"<source>:<native_id>"``.

    ``source`` must not contain the reserved delimiter so the uid can be
    split back into its two parts unambiguously.
    """
    if not isinstance(source, str) or not source.strip():
        raise SourceNormalizationError("record uid requires a non-empty source")
    if not isinstance(native_id, str) or not native_id.strip():
        raise SourceNormalizationError("record uid requires a non-empty native_id")
    if _UID_DELIMITER in source:
        raise SourceNormalizationError(
            f"source name {source!r} may not contain the reserved {_UID_DELIMITER!r} delimiter"
        )
    return f"{source}{_UID_DELIMITER}{native_id}"


def split_record_uid(record_uid: str) -> tuple[str, str]:
    """Inverse of :func:`build_record_uid` — ``(source, native_id)``."""
    source, _, native_id = record_uid.partition(_UID_DELIMITER)
    if not source or not native_id:
        raise SourceNormalizationError(f"malformed record uid {record_uid!r}")
    return source, native_id


def digest_raw(raw: Mapping[str, Any]) -> str:
    """Deterministic sha256 of a raw source record, for provenance.

    Canonicalized (sorted keys, compact separators) so the digest is
    stable across dict ordering — the same guarantee the rest of the
    repo's state-keys rely on (``artifacts._stable_hash``).
    """
    encoded = json.dumps(raw, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_only(mapping: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(mapping) if mapping else {})


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AbstractAuthor:
    """One author, source-neutral. ``name`` is always present; the
    parsed ``family``/``given`` and identifiers are best-effort."""

    name: str
    family: str | None = None
    given: str | None = None
    orcid: str | None = None
    affiliation: str | None = None
    order: int | None = None


@dataclass(frozen=True)
class SourceDescriptor:
    """Static identity of a source, for provenance + discovery.

    ``kind`` must be one of :data:`VALID_SOURCE_KINDS`; an unknown kind
    is a loud error rather than a silently-accepted free string.
    """

    name: str
    kind: str
    title: str
    homepage: str | None = None
    api_base: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in VALID_SOURCE_KINDS:
            raise SourceNormalizationError(
                f"unknown source kind {self.kind!r}; expected one of {sorted(VALID_SOURCE_KINDS)}"
            )
        if _UID_DELIMITER in self.name:
            raise SourceNormalizationError(
                f"source name {self.name!r} may not contain {_UID_DELIMITER!r}"
            )


@dataclass(frozen=True)
class SourceProvenance:
    """Machine-readable provenance for one normalized record (CA-008)."""

    source: str
    descriptor: SourceDescriptor
    fetched_at: str | None
    raw_digest: str
    query: str | None = None


# ---------------------------------------------------------------------------
# Canonical record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AbstractRecord:
    """The one canonical, source-neutral abstract/work record.

    Replaces the two divergent shapes in the codebase today (OHBM's
    ``dict`` keyed on ``poster_id`` and NeuroScape's ``ArticleHeader``
    keyed on ``pubmed_id``). Identity is ``(source, native_id)``;
    ``display_id`` is the human-facing id for that source (``poster_id``
    for OHBM, DOI for a preprint, PMID for PubMed).

    ``sections`` is the generalization of the fixed six-component OHBM
    schema (``title/introduction/methods/results/conclusion/claims``):
    an open mapping of section-name → text, so a source with different
    section names is expressed, not forced empty. ``extra`` carries
    source-specific fields that the generic pipeline treats as opaque.
    """

    source: str
    native_id: str
    title: str
    display_id: str | None = None
    abstract: str | None = None
    sections: Mapping[str, str] = field(default_factory=dict)
    authors: tuple[AbstractAuthor, ...] = ()
    figure_urls: tuple[str, ...] = ()
    venue: str | None = None
    year: int | None = None
    url: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)
    provenance: SourceProvenance | None = None

    def __post_init__(self) -> None:
        for name in ("source", "native_id", "title"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise SourceNormalizationError(f"AbstractRecord.{name} must be a non-empty string")
        # Validate the uid can be composed (rejects colon-in-source etc.)
        build_record_uid(self.source, self.native_id)
        # Freeze the two open mappings so the record is genuinely immutable.
        object.__setattr__(self, "sections", _read_only(self.sections))
        object.__setattr__(self, "extra", _read_only(self.extra))

    @property
    def record_uid(self) -> str:
        """Stable global identity: ``"<source>:<native_id>"``."""
        return build_record_uid(self.source, self.native_id)


# ---------------------------------------------------------------------------
# Source interface
# ---------------------------------------------------------------------------


@runtime_checkable
class AbstractSource(Protocol):
    """Structural interface every source satisfies.

    Three responsibilities, deliberately separated so the pure mapping
    (:meth:`normalize`) is unit-testable offline while the I/O
    (:meth:`fetch_raw`) is the only part that touches a network/disk:

      * :attr:`descriptor` — static identity/provenance.
      * :meth:`fetch_raw` — yield raw source payloads for a query
        (the source owns its own enumeration/pagination internally).
      * :meth:`normalize` — pure ``raw -> AbstractRecord``.
      * :meth:`records` — the composed ``fetch_raw`` ∘ ``normalize``.
    """

    @property
    def descriptor(self) -> SourceDescriptor: ...

    def fetch_raw(self, query: Any) -> Iterable[Mapping[str, Any]]: ...

    def normalize(self, raw: Mapping[str, Any]) -> AbstractRecord: ...

    def records(self, query: Any) -> Iterator[AbstractRecord]: ...


class BaseAbstractSource(abc.ABC):
    """Convenience base providing the composed :meth:`records`.

    Concrete sources implement :attr:`descriptor`, :meth:`fetch_raw`,
    and :meth:`normalize`; they inherit :meth:`records` for free.
    Instances are structural :class:`AbstractSource` values.
    """

    @property
    @abc.abstractmethod
    def descriptor(self) -> SourceDescriptor: ...

    @abc.abstractmethod
    def fetch_raw(self, query: Any) -> Iterable[Mapping[str, Any]]: ...

    @abc.abstractmethod
    def normalize(self, raw: Mapping[str, Any]) -> AbstractRecord: ...

    def records(self, query: Any) -> Iterator[AbstractRecord]:
        for raw in self.fetch_raw(query):
            yield self.normalize(raw)
