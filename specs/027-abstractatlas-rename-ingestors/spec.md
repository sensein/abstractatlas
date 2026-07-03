# Feature Specification: Abstract Atlas Rename + Pluggable LinkML Ingestors

**Feature Branch**: `027-abstractatlas-rename-ingestors`  
**Created**: 2026-07-02  
**Status**: Draft  
**Input**: User description: "move organization and naming from the overall component being ohbm2026 to abstractatlas (already the new name of the repo). ohbm2026 was an instance of information being added. we would like to allow for different kinds of ingestors of information including extending the pubmed space, other indices like arxiv/biorxiv/medrxiv, as well as other conferences. this should include renaming the cli and re-organizing ingest pipelines into more standardized linkml schemas."

## Overview

The project began as a pipeline for a single event's abstracts ("OHBM 2026") and grew a second information source (the NeuroScape PubMed backdrop). The component is still named after that first instance (`ohbm2026` package, `ohbmcli` command), even though the product is now "Abstract Atlas" (the repository, the site, the domain). This feature renames the component to **abstractatlas** and re-frames the codebase around a general idea: **an atlas assembled from many *ingested sources*, where "OHBM 2026" is just one ingested source among many** (other conferences; literature indices such as PubMed extensions, arXiv, bioRxiv, medRxiv).

To make that framing real, ingestion becomes a **pluggable architecture**: each information source is an *ingestor* that pulls records from its origin and normalizes them into a **standardized, LinkML-defined ingest schema**. The two existing sources — the OHBM conference (via Oxford Abstracts) and the PubMed/NeuroScape corpus — are ported to become the first two ingestor instances, proving the abstraction without adding any new source in this change.

**Scope decisions (confirmed):**
- **Build:** the foundation only — rename, the pluggable ingestor architecture + standardized LinkML ingest schema, and porting the two existing sources. New source ingestors (arXiv, bioRxiv, medRxiv, additional conferences) are explicitly deferred to follow-on specs that this architecture enables.
- **Rename reach:** code, CLI, package, and docs. Existing on-disk data artifact paths and published data-package names (e.g. `ohbm2026.parquet`) are **preserved** for continuity — no data regeneration, no re-publish, the live site's data stays byte-identical.
- **CLI name:** `ohbmcli` → **`aacli`**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator runs the pipeline under the new name with no behavior change (Priority: P1) 🎯 MVP

An operator who runs the canonical pipeline invokes the renamed command
(`aacli <subcommand>`) and imports the renamed package (`abstractatlas`)
in scripts. Every existing subcommand and workflow behaves identically and
writes the same artifacts to the same paths as before the rename.

**Why this priority**: The rename is the core ask and the riskiest part
(broad blast radius). Landing it with zero behavioral/data change is the
shippable MVP and the foundation everything else builds on.

**Independent Test**: Run the existing pipeline subcommands via `aacli`
against a fixture corpus and confirm the produced artifacts are identical
(same paths, same content) to a pre-rename run; confirm `import abstractatlas`
works and the old `ohbm2026` import path is gone (or a clearly-deprecated
alias).

**Acceptance Scenarios**:

1. **Given** a checkout on the renamed component, **When** the operator runs `aacli <subcommand>` for each existing subcommand, **Then** each behaves identically to the former `ohbmcli <subcommand>` and writes the same artifacts to the same locations.
2. **Given** existing on-disk artifacts and caches created before the rename, **When** the pipeline runs after the rename, **Then** those artifacts/caches are still discovered and reused (no forced recompute from a name change).
3. **Given** the published data package and the live site, **When** the rename lands, **Then** the site's data is byte-identical and no data re-publish is required.
4. **Given** documentation (README, agent/context docs), **When** the rename lands, **Then** all operator-facing docs reference `abstractatlas` / `aacli` and contain no stale `ohbm2026` / `ohbmcli` instructions.

---

### User Story 2 - Maintainer adds a new information source without touching downstream stages (Priority: P2)

A maintainer wants to onboard a new source (e.g. a literature index or
another conference). They implement a single, well-defined **ingestor**
contract — "how to pull records from this source and normalize them" — and
register it. Downstream stages (enrichment, embeddings, analysis, export,
UI packaging) consume the standardized ingest output and require no changes
to accept the new source.

**Why this priority**: This is the durable value — turning a
single-instance pipeline into a multi-source atlas. It is validated in this
change by porting the two existing sources onto the ingestor contract; new
sources are follow-on work.

**Independent Test**: Confirm the two existing sources (OHBM conference,
PubMed/NeuroScape) are each expressed as a named ingestor behind the common
contract and produce their former outputs, and that a documented "add an
ingestor" path exists that touches only ingestor code (no edits to
downstream stages) — demonstrated by the two ports changing zero downstream
stage logic.

**Acceptance Scenarios**:

1. **Given** the ingestor architecture, **When** the available ingestors are listed, **Then** the OHBM conference ingestor and the PubMed/NeuroScape ingestor both appear as named, discoverable instances.
2. **Given** a new source to onboard, **When** a maintainer implements the ingestor contract and registers it, **Then** it becomes runnable through the CLI and feeds downstream stages with no downstream code changes.
3. **Given** the ported OHBM ingestor, **When** it runs, **Then** it reproduces the former OHBM ingestion output exactly (same normalized corpus).

---

### User Story 3 - Ingested records conform to a standardized schema across sources (Priority: P3)

Records emitted by any ingestor validate against a **standardized LinkML
ingest schema** with a common core (identity, title, authors, abstract
text, source provenance) plus source-type-specific extensions (a
conference contributes session/program/poster fields; a literature index
contributes DOI/venue/index identifiers). This gives every downstream stage
a uniform, documented contract regardless of source.

**Why this priority**: Standardization is what makes US2 safe and durable,
but it can land immediately after the architecture and the ports. It is the
contract layer, not new user-facing behavior.

**Independent Test**: Run each ingestor and validate its emitted records
against the published LinkML ingest schema; confirm a record missing a
required core field or violating the schema is rejected with a precise
error rather than silently passed downstream.

**Acceptance Scenarios**:

1. **Given** the standardized ingest schema, **When** an ingestor emits records, **Then** those records validate against the schema (core fields present, source-extension fields well-formed).
2. **Given** a malformed ingested record, **When** it is validated, **Then** validation fails loudly with a precise, source-attributed error and the record is not passed to downstream stages.
3. **Given** the ported OHBM output, **When** validated against the schema, **Then** it conforms — proving the schema captures the existing shape without reshaping the preserved published data.

---

### Edge Cases

- **Naming divergence for preserved data**: the package is `abstractatlas` but the published parquet keeps the name `ohbm2026.parquet` (that source's data name). The system must tolerate — and clearly document — this intentional divergence rather than "fix" the data name (which would force a re-publish).
- **Legacy imports / command**: existing scripts, cron jobs, or muscle-memory using `ohbmcli` / `import ohbm2026` fail loudly with the standard not-found error (hard cutover — the old names are removed), never a confusing partial success.
- **State-keyed caches/checkpoints**: caches and checkpoints keyed by names that embed `ohbm2026` must remain readable so the rename does not silently invalidate expensive prior work.
- **Source-type asymmetry**: a conference record has no DOI/journal; a literature record has no poster/session. The schema must make each set optional-by-source without letting a conference record masquerade as literature or vice versa.
- **Two sources, one atlas**: an ingestor's records carry which source they came from, so downstream can attribute, filter, and de-duplicate across sources.
- **Provenance continuity**: provenance records that referenced the old component name must remain interpretable; new provenance uses the new name.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Python package MUST be renamed `ohbm2026` → `abstractatlas`, and all internal imports, references, and docs updated to the new name.
- **FR-002**: The canonical CLI MUST be renamed `ohbmcli` → `aacli`; every existing subcommand MUST remain available with identical behavior and options.
- **FR-003**: Legacy entry points (`ohbmcli`, `import ohbm2026`) MUST be removed outright (hard cutover — no deprecation shims); using them MUST fail loudly with the standard not-found error (`command not found` / `ModuleNotFoundError: No module named 'ohbm2026'`), never partially work in a confusing way.
- **FR-004**: Existing on-disk data artifact paths, artifact/state-key naming, cache/checkpoint keys, and published data-package names (including `ohbm2026.parquet`) MUST be preserved so no data is regenerated and the live site requires no re-publish (byte-identical data).
- **FR-005**: Ingestion MUST be organized as a pluggable architecture: a common **ingestor contract** (pull records from a source → normalize) with a runtime-discoverable registry of named ingestors.
- **FR-006**: The two existing sources — the OHBM conference (Oxford Abstracts) and the PubMed/NeuroScape corpus — MUST be ported to become the first two ingestor instances behind the common contract, each reproducing its former normalized output exactly.
- **FR-007**: A standardized **LinkML ingest schema** MUST define the normalized record contract: a common core plus source-type-specific extensions; the schema is the single source of truth downstream stages rely on.
- **FR-008**: Each ingestor MUST validate its emitted records against the LinkML ingest schema; validation failures MUST surface as precise, source-attributed errors and MUST NOT pass malformed records downstream.
- **FR-009**: Downstream stages (enrichment, embeddings, analysis, export/UI packaging, atlas-package build) MUST require no behavioral changes to consume the standardized ingest output; their produced artifacts MUST remain byte-identical for the existing sources.
- **FR-010**: The ingestor registry MUST be discovered at runtime (from registration/metadata), not matched against a hardcoded source list; onboarding a new ingestor MUST NOT require editing downstream stages.
- **FR-011**: Each ingested record MUST carry machine-readable source provenance (which ingestor/source produced it) so downstream can attribute and filter by source.
- **FR-012**: Documentation that defines canonical commands, package layout, and workflows (README, agent/context docs, and naming references in project governance docs) MUST be updated in the same change to the new names.

### Key Entities *(include if feature involves data)*

- **Ingestor**: a named, registered unit that knows how to pull records from one source origin and normalize them into the standardized ingest schema. Attributes: name, source type (conference | literature-index), origin configuration, output = validated ingested records.
- **Ingested record (standardized)**: the normalized document emitted by any ingestor. Core: stable identity, title, authors, abstract/summary text, source provenance. Extensions by source type — conference: program/session/poster identifiers; literature index: DOI/venue/index identifiers/year.
- **Ingestor registry**: the runtime-discoverable catalog mapping ingestor names to their implementations; the CLI and orchestration read from it.
- **Ingest schema (LinkML)**: the machine-readable contract (core + per-source-type extensions) all ingestors validate against and all downstream stages consume.

### Constitution Alignment *(mandatory)*

- **CA-001**: All Python execution MUST use the repository-local `.venv/bin/python` or `uv` targeting it — unchanged by the rename.
- **CA-002**: Verification is identified first: the existing test suite (renamed) MUST pass under the new package/CLI names; new tests cover the ingestor registry/contract, LinkML schema validation (accept valid, reject malformed), and the two ports reproducing prior outputs — added/failing before implementation.
- **CA-003**: Docs that define canonical defaults, commands, inputs, outputs, and review surfaces (README, CLAUDE.md, governance naming references) MUST be updated in the same change (FR-012).
- **CA-004**: No new credentials; existing source credentials (e.g. Oxford Abstracts, OpenAI, data host) are referenced by env-var name only and are unchanged by the rename.
- **CA-005**: No new dataset/cache/export is introduced; existing artifact roots stay gitignored and preserved; the LinkML schema is source, not data.
- **CA-006**: Error paths are explicit and loud: schema-validation failures, unknown-ingestor requests, and legacy-name usage MUST raise precise, typed errors — no silent skips or partial successes; no verification-gate bypass to force the rename green.
- **CA-007**: The ingestor registry and any source enumerations MUST be discovered at runtime from registration/metadata, never a hardcoded allow-list; an unknown or mismatched source surfaces a precise error naming what was searched/found.
- **CA-008**: Provenance for organizer-facing/downstream artifacts is preserved and extended: each ingested record + each produced artifact ships machine-readable provenance (source/ingestor, inputs, config, revision) with no absolute/user-home paths; existing provenance remains interpretable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every existing subcommand dispatches under `aacli` with unchanged names/args, the full test suite passes (SC-002), AND at least one representative fixture subcommand produces artifacts identical (same path + content) to a pre-rename run. (Subcommands requiring live external services are covered by dispatch + suite, not by re-running them against those services.)
- **SC-002**: The full existing test suite passes under the renamed package/CLI with zero skips introduced by the rename.
- **SC-003**: The live site's data is byte-identical after the rename with no data re-publish (published data-package names preserved).
- **SC-004**: Both existing sources are expressed as named ingestors behind the common contract; porting them changed **zero** lines of downstream stage logic (measured by the diff touching only ingestor + rename code).
- **SC-005**: 100% of records emitted by each ingestor validate against the LinkML ingest schema; a deliberately malformed record is rejected with a precise, source-attributed error (0 malformed records reach downstream).
- **SC-006**: A maintainer can onboard a new source by implementing only the ingestor contract + registering it, with no edits to downstream stages — demonstrated by a documented "add an ingestor" guide and the two ports as worked examples.
- **SC-007**: Using a legacy name (`ohbmcli` / `import ohbm2026`) fails loudly and immediately with the standard not-found error — never a silent or partial success. (Hard cutover: the old names are gone.)

## Assumptions

- "Foundation only": this change renames + establishes the ingestor architecture + LinkML ingest schema + ports the two existing sources. It does **not** add arXiv/bioRxiv/medRxiv or new-conference ingestors — those are follow-on specs enabled by this foundation.
- Data continuity is paramount: on-disk artifact layout and published data-package names are preserved verbatim (including the historical `ohbm2026.parquet` name), so the rename is a code/CLI/package/docs change with no data regeneration or site re-publish.
- The standardized LinkML ingest schema is designed to **capture the existing normalized shape** (so the ported OHBM output validates and downstream stays byte-identical), while being general enough to admit literature-index sources — it does not reshape already-published data.
- Hard cutover: NO deprecation shims. `ohbmcli` and `import ohbm2026` are removed and fail loudly; the sole interface is `aacli` / `abstractatlas`. (The local venv must be reinstalled so a previously pip-installed `ohbm2026` dist is replaced by `abstractatlas`.)
- Governance docs (constitution) contain naming references (`ohbmcli`, `src/ohbm2026/`, `data/abstracts.json`); updating those references is in scope for doc-sync, coordinated with the project's constitution-amendment process where required.
- Downstream stages already treat the corpus generically enough that a standardized ingest contract can be introduced without changing their outputs for the existing sources.
