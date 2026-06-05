# Feature Specification: Atlas Research-Classification Dimensions

**Feature Branch**: `023-atlas-research-dimensions`
**Created**: 2026-06-05
**Status**: Draft
**Input**: User description: "Extract from this file: /Users/satra/Downloads/abstracts.detail.json the information that mario generated, and update the ohbm atlas file with these additional details and make them available in the ui. I ran the dimension analysis from neuroscape now also on the OHBM 2026 abstracts and added information on four dimensions to abstracts.detail.json. The dimensions I added are focus (appliedness): fundamental, translational, clinical etc.; research_modality (methodological approach): computational, experiment, observation etc.; theory_scope: overarching framework, micro-theory etc.; epistemic_basis (theory engagement): theory-driven, data-driven. These can be additional computed insights items in the atlas."

## Overview

A separate "NeuroScape dimension analysis" was run over the OHBM 2026 abstracts, classifying each abstract along **four research-classification dimensions** that do not exist in the current canonical corpus or atlas. The analysis output lives in an operator-supplied file (`abstracts.detail.json`), keyed by Oxford submission id, and adds these per-abstract multi-label fields:

- **focus** — degree of appliedness (observed labels: *Fundamental, Translational, Clinical, Method Development, Technological Exploitation, Economic, Legal*).
- **research_modality** — methodological approach (observed labels: *Computational, Experimental, Observational, Meta-analytic, Theoretical*).
- **theory_scope** — scope of the theoretical framing (observed labels: *Overarching Framework, Domain Framework, Disease-specific Framework, Micro Theory*).
- **epistemic_basis** — theory engagement (observed labels: *Hypothesis-driven, Data-driven*).

This feature ingests those four dimensions, joins them onto the canonical OHBM 2026 abstracts by submission id, carries them through the atlas data package, and surfaces them in the atlas UI as new per-abstract **computed insights** and **filterable facets** — peers of the existing categorical dimensions (study type, species, recording technology, brain regions, topic, etc.).

A repo **distiller** tool first reduces the bulky operator-supplied `abstracts.detail.json` (which carries many other analysis fields) to a **slim dimensions file** containing only the Oxford submission id and the four dimension label lists per abstract. The data-package build consumes that slim file (see Clarifications).

## Clarifications

### Session 2026-06-05

- Q: Join direction — should abstracts present in the dimension file but absent from the export be pulled in? → A: No. The merge is a left-join onto the exported/displayed corpus only; the export set is authoritative. Dimension-file entries with no matching exported abstract are counted/logged but never added to the corpus, and never create new abstract records.
- Q: How broadly are the four dimensions surfaced in the UI? → A: Both — as per-abstract computed insights (DetailPanel) and as filterable facets (sidebar), matching peer categorical dimensions. No scatter color-overlay (out of scope).
- Q: Should the build consume the full detail file or a slim derived version? → A: A slim derived file containing only the Oxford submission id + the four dimension label lists per abstract (all other fields dropped). A new repo **distiller** tool reads the full `abstracts.detail.json` and writes the slim file; the data-package build consumes the slim file.
- Q: Is the slim dimensions file committed or gitignored? → A: Gitignored under `data/inputs/neuroscape-dimensions/`, regenerated deterministically by the distiller (Constitution II — no committed data; the distiller is the reproducible source-of-record).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See a poster's research-classification at a glance (Priority: P1)

A conference attendee or organizer opens a single abstract's detail view in the atlas. Alongside the existing computed insights (topic, study type, species, claims, figures), they now see the four research-classification dimensions for that abstract, each rendered as a labelled set of category chips. An abstract classified as *Translational + Clinical* focus, *Computational + Observational* modality, *Domain Framework* theory scope, and *Hypothesis-driven* epistemic basis shows all four dimensions with those values. Abstracts that the dimension analysis left unclassified for a given dimension simply omit that dimension (no empty/placeholder chip).

**Why this priority**: This is the literal request — "additional computed insights items in the atlas." It delivers the core value (the four new dimensions become visible per abstract) and is independently shippable even if filtering is not yet wired.

**Independent Test**: Open the detail view for an abstract known to be classified on all four dimensions; confirm all four labelled dimensions render with the correct category values, and confirm an abstract with no value for `theory_scope` omits that dimension cleanly.

**Acceptance Scenarios**:

1. **Given** an abstract with non-empty values for all four dimensions, **When** a user opens its detail view, **Then** the four dimensions appear in the computed-insights region, each labelled and showing its category values.
2. **Given** an abstract with no value for one dimension (e.g. empty `theory_scope`), **When** a user opens its detail view, **Then** the other three dimensions render and the empty one is omitted (no blank or "N/A" chip).
3. **Given** the four new dimensions, **When** they render, **Then** they are visually consistent with the existing computed-insights/categorical dimensions (same chip styling, labelling, and ordering conventions).

---

### User Story 2 - Filter the corpus by a research dimension (Priority: P2)

A user browsing the atlas wants to narrow the corpus to, e.g., all *Clinical*-focus, *Data-driven* abstracts. The four new dimensions appear as facets in the facet sidebar alongside the existing facets, each showing the available category options with live counts. Selecting one or more options filters the visible abstract set (and the scatter/list) using the same multi-select semantics as existing multi-valued facets, and facet counts narrow consistently with the rest of the active query.

**Why this priority**: The four dimensions are low-cardinality categorical axes — the same shape as every existing facet — so exposing them for filtering is the natural extension that turns "visible" into "explorable." It builds on Story 1's data plumbing but is independently testable.

**Independent Test**: Open the facet sidebar, confirm the four new facets appear with option counts that sum consistently with the corpus; select an option and confirm the abstract set and counts update like any existing facet.

**Acceptance Scenarios**:

1. **Given** the facet sidebar, **When** a user views it, **Then** the four new dimensions appear as facets with their category options and per-option counts.
2. **Given** a multi-valued abstract (e.g. focus = *Translational + Clinical*), **When** a user filters on `focus = Clinical`, **Then** that abstract is included (membership = "value present in the abstract's list").
3. **Given** an active filter on another facet, **When** a user views the new facets' counts, **Then** the counts reflect the rest of the active query (consistent with existing facet count behaviour).

---

### User Story 3 - Reproducible, provenance-tracked ingestion of the dimension file (Priority: P3)

An operator re-runs the data-package build after the dimension analysis is updated (or initially supplied). The operator-supplied dimension file is treated as a discoverable input: the build joins it onto the canonical corpus by submission id, reports how many abstracts matched / were missing values per dimension, records the input's provenance (source file identity, join coverage, code revision) in the build's machine-readable provenance, and fails loudly with a precise error if the file is absent when the feature is enabled or if the join key cannot be resolved — never silently emitting a corpus with the dimensions missing.

**Why this priority**: The constitution requires resumable, auditable, provenance-tracked, fail-loud pipelines. This makes the ingestion trustworthy and repeatable rather than a one-off manual merge, but the visible UI value (Stories 1–2) can be demonstrated first.

**Independent Test**: Run the build with the dimension file present and confirm provenance records the join coverage; run it with the file declared but absent and confirm a precise error rather than a silent omission.

**Acceptance Scenarios**:

1. **Given** the dimension file present and the feature enabled, **When** the data package is built, **Then** the build reports per-dimension match/coverage counts and records the input in provenance.
2. **Given** the dimension file declared/enabled but missing or unreadable, **When** the build runs, **Then** it fails with a precise, typed error naming the missing input rather than producing a corpus without the dimensions.
3. **Given** an entry in the dimension file whose submission id has no match in the canonical corpus, **When** the build runs, **Then** the mismatch is surfaced (counted/logged) rather than silently dropped without record.

---

### Edge Cases

- **Abstract missing from the dimension file** (the analysis covered 3329/3333 for `focus`, 2890/3333 for `theory_scope`, etc.): the abstract renders with no value for that dimension; the dimension is omitted from its detail view and the abstract is excluded from that facet's option counts (it has no value), not bucketed as "Unknown" unless explicitly chosen.
- **Unexpected / new category label** not in the observed vocabulary: the label is carried through and displayed as-is (the dimension vocabulary is discovered from the data, not hardcoded), rather than dropped or erroring.
- **Submission-id join collision or unresolved key**: surfaced as a build error/warning with counts, never silently merged onto the wrong abstract.
- **Withdrawn abstracts present in the dimension file but not in the published corpus**: excluded; only abstracts in the canonical published set receive the dimensions.
- **Duplicate or differently-cased labels within one abstract's list** (e.g. `["Clinical","clinical"]`): de-duplicated consistently with how peer multi-valued dimensions are handled.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST extract the four research-classification dimensions (`focus`, `research_modality`, `theory_scope`, `epistemic_basis`) for the abstracts covered, sourcing them from the slim dimensions file (FR-016).
- **FR-016**: A repo **distiller** tool MUST read the full operator-supplied `abstracts.detail.json` and emit a **slim dimensions file** containing, per abstract, only the Oxford submission id and the four dimension label lists — dropping every other field. The distiller MUST be deterministic (same input ⇒ same slim output) and fail loudly if the source lacks the expected dimension fields or join key.
- **FR-017**: The data-package build MUST consume the **slim dimensions file** (not the full detail file) as its dimension input.
- **FR-002**: The system MUST attach the extracted dimensions to the OHBM 2026 abstracts via a **left-join onto the exported/displayed corpus** using the Oxford submission id as the join key, mapping to the atlas's user-facing abstract identifier (poster id). The exported corpus is authoritative: the merge only enriches abstracts that are already in the export and MUST NOT add, create, or pull in any abstract that is not in the export.
- **FR-003**: Each dimension MUST be represented as a multi-valued (zero-or-more category labels) per-abstract attribute, preserving the labels as provided by the analysis.
- **FR-004**: The category vocabulary for each dimension MUST be discovered from the data at build time (not hardcoded), so new or revised labels flow through without code changes.
- **FR-005**: The four dimensions MUST be carried through the atlas data package so they are available to the UI for the published OHBM 2026 corpus.
- **FR-006**: The UI MUST display the four dimensions in each abstract's computed-insights region, each labelled with a human-readable dimension name and rendered consistently with existing categorical insights.
- **FR-007**: A dimension with no value for a given abstract MUST be omitted from that abstract's detail view (no empty/placeholder rendering).
- **FR-008**: The four dimensions MUST be exposed as filterable facets in the facet sidebar, with per-option counts and multi-select membership semantics matching existing multi-valued facets.
- **FR-009**: Facet option counts for the new dimensions MUST narrow consistently with the rest of the active query, matching existing facet count behaviour.
- **FR-010**: The build MUST report per-dimension join coverage (matched abstracts, abstracts with no value) and record the **slim dimensions file** input in machine-readable provenance.
- **FR-011**: The dimension input is opt-in per build. When the `--dimensions` flag is **omitted**, the four facets are simply empty and the build succeeds (logged, not a silent fallback). When the flag is **passed** but the slim dimensions file is missing, unreadable, or malformed, or the join key cannot be resolved, the build MUST fail loudly with a precise, typed error — never silently emitting a corpus with the dimensions absent.
- **FR-012**: Submission ids present in the slim dimensions file that do not match an exported abstract MUST be surfaced (counted/logged) and then discarded — never silently dropped without record, and never added to the corpus.
- **FR-013**: Human-readable display labels for the four dimension names and (where helpful) their categories MUST be defined so the UI presents them in plain language consistent with the existing dimensions.
- **FR-014**: The feature MUST NOT regress the existing `/ohbm2026/` atlas surfaces (existing facets, insights, search, scatter) — the four dimensions are additive.
- **FR-015**: Both the large raw `abstracts.detail.json` and the derived slim dimensions file MUST live under a gitignored input location (`data/inputs/neuroscape-dimensions/`); neither is committed.

### Key Entities *(include if feature involves data)*

- **Full dimension file (`abstracts.detail.json`)**: operator-supplied output of the NeuroScape dimension analysis (~120 MB), keyed by Oxford submission id. Per record it carries the four new dimension fields (each a list of category labels) plus many other analysis fields the atlas already has or does not need. Only the four dimensions are in scope; it is the distiller's input, not the build's.
- **Slim dimensions file**: the distiller's output — a compact file keyed by Oxford submission id carrying only the four dimension label lists per abstract. This is the data-package build's dimension input. Gitignored under `data/inputs/neuroscape-dimensions/`.
- **Distiller**: a repo tool that deterministically reduces the full dimension file to the slim dimensions file.
- **Research-classification dimension**: a named categorical axis (`focus`, `research_modality`, `theory_scope`, `epistemic_basis`) with a discovered vocabulary of category labels; multi-valued per abstract; a peer of the existing atlas dimensions (study type, species, recording technology, brain regions, topic).
- **Abstract record (atlas)**: the per-abstract entity carried in the atlas data package and rendered in the UI, identified by poster id. Gains four new optional multi-valued dimension attributes.
- **Facet**: a UI/data construct exposing a categorical dimension for filtering with option→count maps. Four new facets are added.
- **Build provenance**: machine-readable record co-located with the data-package output, extended to record the dimension-file input identity and per-dimension join coverage.

### Constitution Alignment *(mandatory)*

- **CA-001**: All Python execution for this feature MUST use the repository-local `.venv/bin/python` interpreter or `uv` targeting that interpreter, including the data-package build and any ingestion/merge step.
- **CA-002**: Behaviour-changing stories MUST add or update tests before implementation: the ingestion/join (coverage counts, missing-file error, unmatched-id reporting), the data-package emission of the four fields, and the UI rendering + faceting (detail display, omit-on-empty, facet counts/membership). Site tests run via `vitest run`.
- **CA-003**: Changes to canonical inputs/outputs/review surfaces MUST update docs in the same change — at minimum `CLAUDE.md` (artifact-layout / default-pipeline notes), the relevant data-package contract/schema, and any facet/insight documentation; README if a new build flag or input is introduced.
- **CA-004**: This feature introduces no new credentials or secrets; the dimension file is a local operator-supplied input. No checked-in tokens.
- **CA-005**: The dimension file and all derived/build artifacts MUST land in gitignored paths (e.g. `data/inputs/`, the data-package output roots); no generated data or the large raw file is tracked in the repository.
- **CA-006**: Error paths MUST be explicit and typed — missing/unreadable/malformed dimension file, unresolved join key, and schema mismatches surface as precise errors (re-raised with context), never bare excepts, silent fallbacks, or skipped verification gates.
- **CA-007**: The dimension-file layout (its fields and the join-key field) and the canonical corpus's identifier mapping MUST be discovered at runtime from the data/metadata; a mismatch (missing expected dimension fields, missing join key) MUST surface as an error rather than being matched against a hardcoded assumption.
- **CA-008**: The data-package output produced by this feature MUST ship machine-readable provenance co-located with it, naming the dimension-file input, per-dimension join coverage, config, code revision, command line, and seed where applicable, free of absolute or user-home paths.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every published OHBM 2026 abstract that has a value for a given dimension in the source file, that abstract's detail view shows that dimension with the correct category values — 100% fidelity to the source for matched abstracts.
- **SC-002**: A user can open any abstract's detail view and see all four research-classification dimensions (or correctly see a dimension omitted when it has no value) without errors or placeholder noise.
- **SC-003**: A user can filter the corpus by any of the four new dimensions and the visible abstract set and option counts update consistently with existing facets.
- **SC-004**: The build reports per-dimension join coverage matching the source distribution (e.g. ~3329/3333 abstracts classified on `focus`, ~2890/3333 on `theory_scope`) and records it in provenance.
- **SC-005**: Re-running the build with an unchanged dimension file and corpus produces an unchanged result for the four dimensions (deterministic, auditable ingestion).
- **SC-006**: The existing `/ohbm2026/` atlas surfaces show no regression — all prior facets, insights, search, and scatter behaviour are unchanged.
- **SC-007**: A build with `--dimensions` **passed** at a missing/unreadable/malformed path fails with a precise error naming the input, never silently producing a corpus without the dimensions. (A build with the flag **omitted** succeeds with empty dimension facets — the documented opt-in default.)

## Assumptions

- **Surfacing scope** (confirmed — see Clarifications): The four dimensions are surfaced both as per-abstract computed-insights **and** as filterable facets in the sidebar. Adding a dedicated scatter color-overlay / "color by dimension" mode is **out of scope** for this feature (the scatter remains cluster-colored).
- **Scope of conferences**: Only the OHBM 2026 corpus (`/ohbm2026/` surfaces and the OHBM abstract atlas data) receives these dimensions; the NeuroScape PubMed corpus and atlas-root cross-conference surfaces are out of scope.
- **Join key**: The dimension file's record key / `id` field is the Oxford submission id, which the canonical corpus already carries and maps to poster id; the join is by submission id, not by title or text matching.
- **Source of the four fields only**: Only `focus`, `research_modality`, `theory_scope`, and `epistemic_basis` are ingested from the dimension file; its other fields (figure analyses, claims, references, topics, species, etc.) are already produced by the canonical pipeline and are not re-sourced from this file.
- **Multi-valued, OR-membership facets**: Each dimension is multi-valued; facet membership uses "value present in the abstract's list" (OR within a dimension), matching existing multi-valued facets such as keywords/brain regions.
- **Vocabulary discovered, not curated**: The displayed category set per dimension is whatever appears in the data; no curated/closed enum is imposed (FR-004), though a human-readable display label is supplied for the four dimension *names*.
- **Input landing**: The operator places the full `abstracts.detail.json` under `data/inputs/neuroscape-dimensions/` and runs the distiller (FR-016) to produce the slim dimensions file in the same gitignored directory; the build consumes the slim file. Neither file is committed.
- **Empty = absent**: An empty list for a dimension is treated as "no value" (omit from detail, exclude from that facet's counts), consistent with the source where 4–443 abstracts lack a value per dimension.
