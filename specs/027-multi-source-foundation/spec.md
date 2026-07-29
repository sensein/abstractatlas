# Feature Specification: Multi-Source Ingest Foundation (Arc A)

**Feature Branch**: `claude/abstract-atlas-architecture-review-rp9ob9`
**Created**: 2026-07-28
**Status**: Draft (design doc + landed proof-of-concept)
**Input**: Architect's review request — "consider where there is technical debt and
decisions as we want to update this to include other types of abstracts from
other conferences and datasets", framed by issue
[#66](https://github.com/sensein/abstractatlas/issues/66) ("Next steps towards
personalized and global knowledge graphs").

> This document is both a design doc/ADR and the spec for the first landed
> slice. A working proof-of-concept ships alongside it:
> `src/ohbm2026/sources/{base,biorxiv}.py` + `tests/test_sources_{base,biorxiv}.py`.
> It is **additive and inert** — it does not yet replace the OHBM `fetch/` +
> `assets.py` ingest or the NeuroScape loader. Its job is to prove the
> abstraction against a second source *family* before the incumbents migrate
> behind it.

## Context: why now

The repo already carries two datasets — OHBM 2026 (Oxford Abstracts GraphQL)
and NeuroScape (a ~600K-article PubMed corpus). They are **two disjoint ingest
silos with no shared contract**: different identifiers (`poster_id` /
Oxford `program_code` vs `pubmed_id`), different record shapes (an untyped
`dict` vs the `ArticleHeader` dataclass), different error hierarchies, and no
common entry point. They converge only at the parquet stage.

Adding "other conferences and datasets" therefore means writing an Nth silo,
not plugging into an interface. Issue #66 makes the direction explicit:
multi-source ingestion (bioRxiv / psyArxiv / medRxiv named directly), a shift
from "search mode" to "search over knowledge mode" (claims → an evidence/
knowledge graph), and a federated posture where this atlas is one node among
lab/personal graphs. All of that needs a stable, source-neutral record with
global identity and provenance — the thing the current per-corpus namespaces
cannot provide.

Two prior specs deliberately deferred generalization (`009` FR-109: "MUST NOT
introduce a `conference_id` field … deferred until a second conference
exists"; `015/research.md` rejected the generalized `conference_id`-column
layout). That YAGNI call was reasonable then. #66 is the signal it has come
due.

### Related architectural finding (out of scope here, but the reason Arc A comes first)

The current cross-dataset design projects every corpus into NeuroScape's fixed
64-dim UMAP space via `umap.transform` (`atlas_package/ohbm_projector.py`).
Issue #66 reports the general version of this (a MiniLM→NeuroScape-64d
projector) **failed** ("the learned projector was not good"), and a
natively-aligned embedder is proposed to replace it. That is **Arc B** — a
separate spec. Arc A (this doc) is a precondition: you cannot cleanly swap the
embedding/projection seam until "a record" and "a source" are first-class.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add a new source family behind one interface (Priority: P1)

A developer wants to ingest bioRxiv/medRxiv preprints into the atlas. Today
this means authoring a third bespoke loader. With Arc A they implement one
`AbstractSource` (descriptor + `fetch_raw` + `normalize`) and get a stream of
canonical `AbstractRecord`s with global identity and provenance.

**Why this priority**: it is the direct answer to the user's request and the
unblocker for every #66 downstream (KG, cross-source search, federation).

**Independent Test**: implement `BiorxivSource`, normalize a real-shaped
bioRxiv detail record offline (injected fetcher), and assert the canonical
record fields + `record_uid` + provenance. **Landed** in
`tests/test_sources_biorxiv.py` (12 cases, all green).

**Acceptance Scenarios**:

1. **Given** a bioRxiv details payload, **When** `normalize` runs, **Then** it
   yields an `AbstractRecord` with `source="biorxiv"`,
   `native_id=<doi>`, `record_uid="biorxiv:<doi>"`, parsed authors, `year`
   from the date, the abstract as a `sections["abstract"]` entry, and
   source-specific fields (category, version, license, published DOI) in
   `extra`.
2. **Given** a payload missing `doi` or `title`, **When** `normalize` runs,
   **Then** it raises `SourceNormalizationError` (never a silent skip).
3. **Given** an injected multi-record page, **When** `records(query)` runs,
   **Then** it yields one canonical record per collection item and satisfies
   the `AbstractSource` Protocol structurally.

### User Story 2 - One stable identity + provenance per record (Priority: P1)

Every record, regardless of source, carries `record_uid = "<source>:<native_id>"`
and machine-readable `SourceProvenance` (source descriptor + fetched-at +
sha256 raw digest). This is the join key a knowledge graph and a
cross-source search index need.

**Why this priority**: identity is the deepest debt (`poster_id` leaks from
ingest to URL routes today); without it, cross-source linking has nowhere to
land. The deferred `CrossConferenceLinkRow` type already assumed a
format-agnostic `id_a`/`id_b` — this supplies it.

**Independent Test**: `build_record_uid` round-trips via `split_record_uid`;
colon-in-source and empty parts are rejected; `digest_raw` is order-stable.
**Landed** in `tests/test_sources_base.py`.

**Acceptance Scenarios**:

1. **Given** `(source, native_id)`, **When** `build_record_uid` runs, **Then**
   it returns `"<source>:<native_id>"` and rejects a source containing `:`.
2. **Given** two dict orderings of the same raw record, **When** `digest_raw`
   runs on each, **Then** the digests are equal.

### User Story 3 - Open section model (no forced-empty schema) (Priority: P2)

A source whose sections are named differently from OHBM's fixed six
(`title/introduction/methods/results/conclusion/claims`) is expressed via an
open `sections: Mapping[str, str]`, not silently coerced to empty component
bundles (the current silent-degradation trap in `embed/stage.py:360-376`).

**Why this priority**: unblocks non-OHBM-shaped abstracts without touching the
embed/analyze middle yet; the migration of the embed component-resolver to
read `AbstractRecord.sections` is a follow-up.

**Independent Test**: `AbstractRecord(sections={...})` exposes a read-only
mapping; bioRxiv maps its single abstract blob to `sections["abstract"]`.
**Landed**.

### Edge Cases

- **Colliding native ids across sources** (a poster_id that equals a pmid):
  disambiguated by the `source` prefix in `record_uid`. No global id collision.
- **Missing/empty required field**: raises `SourceNormalizationError`; the
  batch orchestrator (future) decides quarantine-vs-abort, but the record is
  never silently dropped.
- **Pagination end**: discovered from the source payload's own
  `count`/`total`/`cursor` (bioRxiv), not a hardcoded page size (Principle VII).
- **Unknown source `kind`**: `SourceDescriptor.__post_init__` rejects it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define one source-neutral canonical record
  (`AbstractRecord`) with fields: `source`, `native_id`, `title`,
  `display_id`, `abstract`, `sections`, `authors`, `figure_urls`, `venue`,
  `year`, `url`, `extra`, `provenance`. *(Landed.)*
- **FR-002**: Each record MUST expose a derived global identity
  `record_uid = "<source>:<native_id>"`. *(Landed.)*
- **FR-003**: The system MUST define an `AbstractSource` interface with
  `descriptor`, `fetch_raw(query)`, `normalize(raw) -> AbstractRecord`, and a
  composed `records(query)`. `normalize` MUST be a pure function unit-testable
  without I/O. *(Landed as a `Protocol` + `BaseAbstractSource`.)*
- **FR-004**: The system MUST ship one concrete non-OHBM source
  (`BiorxivSource`) proving the interface against a different source family
  (DOI-keyed preprint feed). *(Landed.)*
- **FR-005**: Normalization failures MUST raise a typed
  `SourceNormalizationError` rooted under `OhbmStageError`; records MUST NOT be
  silently skipped. *(Landed.)*
- **FR-006**: Every record MUST carry machine-readable provenance
  (source descriptor + fetched-at + deterministic raw digest). *(Landed.)*
- **FR-007**: Network access MUST be injectable so the test suite runs offline
  under `.venv/bin/python`. *(Landed via `fetch_page` injection.)*
- **FR-008** *(follow-up, not in this slice)*: The OHBM `assets.normalize_abstract`
  output and the NeuroScape `ArticleHeader` MUST be expressible as
  `AbstractRecord`s via adapter sources, so the two incumbents migrate behind
  the interface without changing their on-disk artifacts.
- **FR-009** *(follow-up)*: `artifacts.py` path builders and
  `build_dependency_basis` MUST gain a `source`/`conference` dimension so two
  corpora can coexist in the data tree, replacing the current
  one-corpus-per-tree guards (`analyze/stage.py:158-162`,
  `ui_data/state_key.py:85-90`) with one-per-source guards.

### Key Entities

- **AbstractRecord**: the canonical work/abstract; identity `(source, native_id)`.
- **AbstractAuthor**: source-neutral author (name + best-effort family/given/orcid/affiliation/order).
- **SourceDescriptor**: static source identity (name, kind, title, homepage, api_base); `kind ∈ {conference, preprint, journal, corpus, talk, other}`.
- **SourceProvenance**: per-record provenance (source, descriptor, fetched_at, raw sha256, query).
- **AbstractSource**: the ingest interface; `BaseAbstractSource` supplies `records()`.

### Constitution Alignment *(mandatory)*

- **CA-001**: All execution uses `.venv/bin/python` (venv created for this
  slice; tests run `PYTHONPATH=src .venv/bin/python -m unittest`).
- **CA-002**: Tests were written first and confirmed failing before
  implementation (Principle IV) — see the two test modules' docstrings.
- **CA-003**: This doc + `CLAUDE.md`/`README` module map are the docs to update
  when the incumbents migrate (FR-008); this slice is additive and changes no
  canonical default, so no runbook change is required yet.
- **CA-004**: No credentials. The bioRxiv API is public and unauthenticated;
  the default fetcher issues an anonymous GET through the environment proxy.
- **CA-005**: No new dataset/cache/export is written. The prototype is code +
  tests only; no `data/` writes.
- **CA-006**: Every error path raises the typed `SourceNormalizationError`;
  no bare `except`, no silent fallback.
- **CA-007**: bioRxiv field presence and pagination bounds are discovered from
  each payload (`collection`, `messages[0].total`), not matched against a
  hardcoded field list; mismatches raise.
- **CA-008**: Each record ships `SourceProvenance` with a deterministic raw
  digest; the digest helper canonicalizes key order (matching
  `artifacts._stable_hash`). No absolute/user-home paths are stored.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new source family is added by implementing exactly one class
  (`descriptor` + `fetch_raw` + `normalize`) with zero edits to existing
  ingest modules. *(Met: `BiorxivSource` is ~180 lines, touches nothing else.)*
- **SC-002**: 100% of the source layer's tests run offline under
  `.venv/bin/python` with no optional heavy dependencies. *(Met: 23 tests,
  stdlib only, 0.003s.)*
- **SC-003**: Two source families (OHBM-shaped and preprint-shaped) are
  representable by the same record with neither leaking source-specific fields
  into the core (they live in `extra`). *(Met for bioRxiv; OHBM adapter is
  FR-008.)*
- **SC-004**: Every emitted record has a non-empty `record_uid` and
  `provenance.raw_digest`. *(Met, asserted in tests.)*

## Assumptions

- The bioRxiv details API shape (`collection` + `messages[cursor/count/total]`,
  semicolon author strings, `YYYY-MM-DD` dates) is current; it is discovered
  per-payload so a drift surfaces as a loud error, not a silent skip.
- Migrating the OHBM and NeuroScape incumbents behind the interface (FR-008)
  and adding the corpus dimension to paths/state-keys (FR-009) are the next
  spec's work; this slice intentionally stops at "prove the seam".
- The knowledge-graph schema for claims/evidence (#66) sits downstream of this
  record and is a separate arc; `AbstractRecord.record_uid` is the intended
  node identity it will reference.
