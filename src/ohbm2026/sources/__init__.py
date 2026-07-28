"""Multi-source ingest foundation (Arc A of the architecture review).

This package introduces the *source-neutral* abstraction the pipeline
lacks today: a typed canonical :class:`~ohbm2026.sources.base.AbstractRecord`
and an :class:`~ohbm2026.sources.base.AbstractSource` Protocol that any
conference, preprint feed, or corpus can satisfy. See
``specs/027-multi-source-foundation/`` for the design.

It is deliberately additive and stdlib-only: it does not yet replace the
existing OHBM ``fetch/`` + ``assets.py`` ingest or the NeuroScape loader.
It exists to prove the abstraction against a concrete second-family source
(bioRxiv) before the incumbents are migrated behind it.
"""

from __future__ import annotations

from ohbm2026.sources.base import (
    AbstractAuthor,
    AbstractRecord,
    AbstractSource,
    BaseAbstractSource,
    SourceDescriptor,
    SourceError,
    SourceNormalizationError,
    SourceProvenance,
    build_record_uid,
    digest_raw,
)

__all__ = [
    "AbstractAuthor",
    "AbstractRecord",
    "AbstractSource",
    "BaseAbstractSource",
    "SourceDescriptor",
    "SourceError",
    "SourceNormalizationError",
    "SourceProvenance",
    "build_record_uid",
    "digest_raw",
]
