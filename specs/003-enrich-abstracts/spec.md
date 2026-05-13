# Feature Specification: Stage 2 — Enrich Abstracts (Figures, Claims, References)

**Feature Branch**: `003-enrich-abstracts`
**Created**: 2026-05-13
**Status**: Draft
**Input**: User description: "let's move on to stage 2 (enrichment for figures, claims, and references), these will only be done on non-withdrawn and abstracts and should also support future changes in movement of abstracts between non-withdrawn and withrdrawn. the final enriched abstracts should contain figure interpretation, claims, and references. they should be optimized for minimizing storage and random seeks. this is now secondary data, and should carry provenance info on models used to enrich it, the components should be cached so that rerunning would redo if models have changed."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Operator runs Stage 2 against the current accepted corpus and produces an enriched corpus (Priority: P1) — MVP

After Stage 1 has produced `data/primary/abstracts.json` (and the
matching figure assets + author roster), a project maintainer wants
to derive the enriched corpus that downstream consumers (UI, search,
clustering) read. They invoke a single, focused entry point for
Stage 2. The stage reads only the **accepted** corpus, runs the
three enrichment components — **figure interpretation**, **claims
extraction**, **reference resolution** — and writes one enriched
corpus artifact along with a machine-readable provenance record
that names every model used.

**Why this priority**: this is the MVP. Without enriched output,
none of Stage 3+ (embeddings, clustering, UI) can move forward. A
successful run validates: the accepted-only filter works, the
three components run, the per-component caches populate, the
output format is queryable, and provenance captures every model
choice.

**Independent Test**: Against a small synthetic accepted corpus
(N=5 abstracts, each with one figure URL and a short reference
list), run Stage 2 with fixed model identifiers. Verify the
enriched corpus contains every accepted abstract with all three
enrichment fields populated, and that the provenance record names
all three model identifiers.

**Acceptance Scenarios**:

1. **Given** an accepted corpus and the three enrichment models
   configured, **When** the operator runs Stage 2, **Then** every
   accepted abstract appears in the enriched corpus exactly once,
   each with `figure_interpretation`, `claims`, and `references`
   populated (figures may be empty for abstracts without methods/
   results figures; claims may be empty if extraction returns no
   claims; references may be empty for abstracts without a
   references section).
2. **Given** the same state, **When** the run completes, **Then**
   the provenance record names the model identifier for each
   component, the cache hit/miss counts per component, and the
   number of input abstracts processed.
3. **Given** a withdrawn abstract, **When** Stage 2 runs, **Then**
   that abstract is NOT present in the enriched corpus
   (accepted-only filter, FR-002).

---

### User Story 2 — Re-run with unchanged models reuses all caches; is fast and idempotent (Priority: P1)

The operator re-runs Stage 2 with no input changes and no model
changes. The stage observes that every per-component cache key is
already populated, re-uses cached enrichments without re-calling
any vision / claims / reference-resolution upstream, and produces
a byte-identical enriched corpus.

**Why this priority**: caching is the load-bearing feature that
makes Stage 2 practical at corpus scale. Without it, every re-run
re-invokes paid LLM APIs over thousands of abstracts. P1 because
the cost and correctness of every later run depend on it.

**Independent Test**: Run Stage 2 twice in succession. The second
run's provenance record MUST show 100% cache hits per component
and zero LLM/API calls. Primary outputs (the enriched corpus
file) MUST be byte-identical between runs aside from
provenance-only fields (timestamp, run_id).

**Acceptance Scenarios**:

1. **Given** Stage 2 has completed once, **When** the operator
   re-runs with the same input corpus and the same model
   identifiers, **Then** every per-component cache lookup hits and
   the run completes without issuing any LLM / API calls for
   enrichment.
2. **Given** that second run, **When** the operator diffs the
   enriched corpus from the two runs, **Then** the diff is empty
   (modulo provenance run-id and timestamp).

---

### User Story 3 — Changing one component's model invalidates only that component's cache (Priority: P1)

The operator changes the figure-interpretation model identifier
(e.g., `gpt-4.1-mini` → `gpt-4o`) but keeps the claims and
reference-resolution models unchanged. Stage 2 re-fetches figure
interpretations from the new model, **reuses cached claims and
references**, and writes a new enriched corpus + new provenance.

**Why this priority**: prevents wasteful re-enrichment of
component A just because component B's model changed. P1 because
the whole point of component-level caches is independent
invalidation; if cache invalidation is too coarse, runs become
expensive and operators avoid them.

**Independent Test**: Complete a Stage 2 run. Change only the
figure model identifier in configuration. Re-run. Provenance MUST
show 100% cache miss for figures, 100% cache hits for claims and
references, and the enriched corpus's `figure_interpretation`
fields match the new model's output.

**Acceptance Scenarios**:

1. **Given** a baseline enriched corpus, **When** only the figure
   model identifier changes, **Then** the figure-interpretation
   cache is invalidated for every abstract while claims and
   references caches are reused intact.
2. **Given** that change, **When** the operator inspects the new
   provenance record, **Then** the figure-component section names
   the new model and shows the cache-miss count equal to the
   abstract count; the claims and references sections show 100%
   cache hits.

---

### User Story 4 — Abstracts moving between accepted and withdrawn are handled gracefully across runs (Priority: P2)

Between two Stage 2 runs, three things happen upstream:

- Abstract A is in the accepted corpus on run 1; it's withdrawn
  before run 2.
- Abstract B was withdrawn on run 1; it's restored to accepted
  before run 2 (rare, but possible).
- Abstract C is in the accepted corpus on both runs.

Stage 2 handles each correctly: A is **dropped** from the run 2
enriched corpus; B is **re-included** with its enrichment
populated (from cache if its content hash hasn't changed); C is
**unchanged**.

**Why this priority**: this is the explicit "movement between
non-withdrawn and withdrawn" requirement. P2 because the more
common single-corpus-state case (US1) is the MVP; this story
prevents corruption when state changes between runs.

**Independent Test**: Synthesize the three-abstract scenario with
deterministic content hashes. Verify run 2's enriched corpus
contains B and C but not A; verify B's enrichment used cache
hits (because content unchanged); verify provenance records the
delta vs the previous run.

**Acceptance Scenarios**:

1. **Given** abstract A was enriched in run 1 and is withdrawn
   before run 2, **When** Stage 2 runs, **Then** A is absent from
   the run 2 enriched corpus; A's per-component cache entries
   remain on disk (not purged) so that a future re-acceptance is
   cheap.
2. **Given** abstract B was withdrawn at run 1 and is accepted
   at run 2 (and its content hash matches what was cached during
   an even earlier acceptance), **When** Stage 2 runs, **Then** B
   appears in the enriched corpus and its enrichment comes from
   cache (zero LLM calls for B).
3. **Given** abstract C is accepted in both runs, **When** Stage 2
   runs the second time, **Then** C's enrichment is byte-identical
   to the first run (subject to US2's idempotency guarantees).

---

### Edge Cases

- An accepted abstract has zero figures → `figure_interpretation`
  field is an empty list (not null, not missing), and no figure
  cache lookups happen for it.
- The figure assets directory is missing or empty → figure
  enrichment fails loudly; the run exits non-zero without writing
  a partial enriched corpus.
- A figure asset file is present but unreadable (corrupted PNG) →
  per-figure failure recorded; the abstract is still enriched with
  whatever figures DID resolve; provenance records the figure
  failure count; if failure rate exceeds a threshold (default
  matching Stage 1's `--figure-failure-threshold` style), the run
  exits non-zero.
- A reference can't be resolved by any backend (DOI lookup fails,
  OpenAlex search returns no hits, Semantic Scholar fallback also
  empty) → the reference appears in the output with its raw text
  plus a `resolution_status: "unresolved"` marker; the run does
  NOT fail because of unresolvable references.
- The claims extractor returns an LLM response that doesn't parse
  as the expected schema → per-abstract failure recorded;
  abstract is included with `claims: []` and a flag noting the
  parse failure; provenance records the failure; if rate exceeds
  a threshold, the run exits non-zero.
- The accepted corpus is empty (zero abstracts) → fail loudly with
  a precise error; do NOT write an empty enriched corpus that
  would clobber a previous good one (mirrors Stage 1's
  semantically-empty-corpus rule).
- An operator deletes one component's cache directory while
  another is intact → the missing component re-runs end-to-end;
  others reuse intact entries. No cross-component dependency in
  cache invalidation.
- An operator changes a model's *version* (same identifier, new
  weights) and the model provider doesn't surface the change → we
  can't detect this without operator intent; an explicit
  `--invalidate <component>` flag lets the operator force a
  refresh of that component's cache.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Stage 2 MUST be invocable as a standalone, focused
  entry point — running it MUST NOT trigger any Stage 1 or Stage 3
  behavior as a side effect.
- **FR-002**: Stage 2 MUST read the accepted corpus only
  (`data/primary/abstracts.json`). It MUST NOT read or enrich the
  withdrawn corpus (`data/primary/abstracts_withdrawn.json`).
- **FR-003**: Stage 2 MUST produce a single canonical enriched
  corpus artifact at `data/primary/abstracts_enriched.<ext>` (path
  pinned by the storage-format Assumption below). The enriched
  corpus MUST contain every accepted abstract exactly once and MUST
  NOT contain any abstract that is not currently accepted.
- **FR-004**: Each enriched abstract record MUST carry the
  unchanged Stage 1 fields PLUS three new fields:
  - `figure_interpretation`: a list of per-figure interpretation
    objects (figure URL, model output, model identifier, cache
    key). Empty list if the abstract has zero methods/results
    figures.
  - `claims`: a list of extracted claim records (one per claim,
    with claim text, model identifier, cache key). Empty list if
    extraction returns no claims.
  - `references`: a list of resolved reference records (raw
    reference text, resolution status, resolved identifier(s)
    such as DOI/PMID/OpenAlex ID, source-of-resolution flag).
- **FR-005**: Stage 2 MUST cache each of the three enrichment
  components independently. Cache keys MUST encode the
  component's input content hash AND the model identifier (or
  resolution-strategy identifier for references). When the
  component's model changes, only that component's cache becomes
  stale; the other two are reused intact. Cache entries live
  under `data/cache/<component>/`.
- **FR-006**: A Stage 2 re-run with no input change and no model
  change MUST produce a byte-identical enriched corpus (modulo
  provenance run-id and timestamp). The run MUST issue zero
  LLM/API calls for enrichment components in this case.
- **FR-007**: Stage 2 MUST emit machine-readable provenance
  alongside the enriched corpus, capturing: run timestamp, code
  revision, command line, env vars consulted (names only),
  per-component model identifier, per-component cache hit/miss
  counts, per-component failure counts, abstract counts (input vs
  enriched), and a delta-vs-previous-run summary (added /
  removed / unchanged abstract counts) if a previous enriched
  corpus is present. Path: `data/inputs/abstracts_enrich_provenance__<state-key>.json`.
- **FR-008**: Stage 2 MUST handle the three movement cases across
  runs (US4) idempotently: a previously-enriched abstract that is
  no longer accepted is dropped from the enriched corpus; an
  abstract that becomes (re-)accepted is included with its
  enrichment (from cache when content hash matches); an abstract
  that stays accepted is byte-identical. Cache entries for
  no-longer-accepted abstracts MUST NOT be purged — they survive
  for cheap re-enrichment if the abstract is restored.
- **FR-009**: The enriched corpus format MUST be optimized for
  (a) compact on-disk size and (b) constant-time random lookup of
  any abstract by ID. The corpus MUST be a single file (not a
  per-abstract file tree). A sidecar index is acceptable.
- **FR-010**: Stage 2 MUST surface every failure loudly with a
  typed cause: missing/invalid input corpus, missing API key for
  the configured backend, exhausted retries on an LLM call,
  schema-shape change in an LLM response, threshold-exceeded
  failure rate per component. Silent fallbacks, bare excepts, and
  "log and continue" handlers that hide systematic failures are
  PROHIBITED (Principle VI). Per-record failures within a
  component are tolerated up to a configurable threshold; beyond
  the threshold the run exits non-zero.
- **FR-011**: Stage 2 MUST write all artifacts under existing
  gitignored data roots: enriched corpus under `data/primary/`;
  provenance under `data/inputs/`; per-component caches under
  `data/cache/<component>/`. The stage MUST refuse to write
  outside the gitignored boundary even if explicitly directed
  to.
- **FR-012**: Stage 2 MUST follow the per-stage pattern (six
  contracts) documented in `docs/per-stage-pattern.md`. The
  orchestrator MUST be the canonical reference instance for the
  pattern *at the multi-component scale*; Stage 1 covered the
  single-fetch case.
- **FR-013**: Stage 2 entry points MUST run only through the
  repository-local `.venv/bin/python` (or `uv` targeting it). All
  invocation examples in docs MUST show that form.
- **FR-014**: The CLI surface MUST expose Stage 2 as a single
  subcommand `ohbmcli enrich-abstracts` (plus a thin
  `scripts/run_enrich_abstracts.py` wrapper). Legacy subcommands
  (`enrich`, `analyze-figures`, `extract-claims`,
  `reference-metadata`) are REPLACED by the new entry; no
  backward-compat alias is required, parallel to FR-014 / FR-024
  of the Stage 1 spec. Component-level focused refresh is
  available via `--invalidate <component>` flags rather than
  separate subcommands.
- **FR-015**: Stage 2 MUST NOT alter Stage 1 outputs, Stage 1
  contracts, or any pre-Stage-2 artifact. The accepted corpus,
  authors roster, figure assets, GraphQL schema artifact, and
  fetch provenance all remain read-only inputs to Stage 2.
- **FR-016**: README, `CLAUDE.md`, and `docs/reproducibility-vision.md`
  MUST be updated in the same change to document the Stage 2
  invocation, replace any references to the now-removed legacy
  subcommands, and cross-link the per-stage pattern doc.
- **FR-017**: Stage 2 MUST support an OPTIONAL Parquet export of the
  enriched corpus alongside the canonical SQLite+zlib output. The
  export is enabled by `--export-parquet PATH` (default off; no
  export). When enabled, the Parquet file is written AFTER the
  SQLite atomic commit succeeds — the SQLite output remains the
  canonical, never-skipped artifact. The Parquet writer MUST
  lazy-import `pyarrow` so the optional dependency is only required
  when the flag is set; module-level import paths remain stdlib-
  only. The Parquet file is written under the same gitignored
  boundary rules as every other artifact (FR-011) and carries the
  same per-row shape as the SQLite payload (one row per abstract,
  full JSON-as-string in a payload column; `id` as a typed column).
  Rationale: the empirical benchmark (research.md §1) confirmed
  Parquet zstd is the most compact format and the de-facto
  analytics standard; keeping a conversion route open is essential
  for embedding-related work in future stages and for any
  downstream tool (DuckDB, pandas, polars, browser-side analytic
  engines) that prefers columnar input.

### Key Entities

- **Enriched Abstract Record**: one record per currently-accepted
  abstract. Contains every Stage 1 corpus field unchanged plus
  `figure_interpretation`, `claims`, `references` as defined in
  FR-004. Identified by `id` (same as the Stage 1 `id`).
- **Component Cache Entry**: keyed by `(component, content_hash,
  model_id)`. Stores the component's resolved output plus
  metadata (model identifier, model version if available, fetched-
  at timestamp). Lives under `data/cache/<component>/`.
- **Stage 2 Provenance Record**: machine-readable sidecar capturing
  the run's choices and outcomes. See FR-007 for the field list.
  Lives at `data/inputs/abstracts_enrich_provenance__<state-key>.json`.
- **Storage Index** (if the storage format is line-delimited):
  byte-offset map `{abstract_id: offset_in_corpus_file}` sidecar
  enabling O(1) random reads. Lives alongside the enriched corpus.

### Constitution Alignment *(mandatory)*

- **CA-001**: Every Python invocation introduced by this feature
  runs through `.venv/bin/python` or `uv` targeting it; no system
  Python.
- **CA-002**: Tests for each user story land before implementation.
  US1 → end-to-end run against synthetic fixture; US2 → byte-
  identical re-run; US3 → per-component cache invalidation; US4 →
  three-case movement scenario. Tests-first.
- **CA-003**: README, `CLAUDE.md`, `docs/reproducibility-vision.md`
  update in the same change as the code; cross-link the per-stage
  pattern doc; remove legacy subcommand references (FR-014, FR-016).
- **CA-004**: API keys named only as env vars in spec + code
  (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENALEX_API`, etc.).
  Values NEVER recorded in provenance; only names appear in
  `env_vars_consulted`.
- **CA-005**: Enriched corpus, caches, and provenance all live
  under existing gitignored roots. No new artifact root introduced
  (FR-011).
- **CA-006**: All failure modes enumerated in FR-010 surface
  loudly with typed causes. Per-component cache misses are NOT
  silent fallbacks — they're cache misses, with explicit hit/miss
  counts in provenance. Bare excepts and "log and continue" around
  systematic failures are PROHIBITED.
- **CA-007**: External-state discovery (Principle VII):
  - LLM response schemas are checked at parse time; mismatch
    raises a typed error rather than producing a "best effort"
    record.
  - The set of supported figure-interpretation backends, claims
    backends, and reference-resolution backends is discovered at
    runtime from the configured environment (which API keys are
    present, which optional dependencies are installed) — not
    hardcoded as a baked-in support matrix.
- **CA-008**: The enriched corpus is **secondary data**, derived
  from the Stage 1 primary corpus. It IS organizer-facing
  (downstream of every UI / poster proposal / sequencing
  artifact), so its provenance record (FR-007) MUST satisfy
  Principle VIII: no absolute paths, no user-home paths, machine-
  readable, complete enough to reproduce the run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fresh contributor can run Stage 2 end-to-end
  against a fresh Stage 1 corpus by following only the updated
  README's Stage 2 section, with no other documentation lookups
  required.
- **SC-002**: A second Stage 2 run with no input or model change
  produces a byte-identical enriched corpus (modulo provenance
  run-id and timestamp) AND issues zero LLM/API calls for
  enrichment components — verified by an automated test that
  counts requests through a mocked transport.
- **SC-003**: Changing one component's model identifier causes
  exactly that component's cache to be invalidated; the other two
  components show 100% cache hits on the next run — verified by
  an automated test.
- **SC-004**: 100% of accepted-corpus abstracts are present in the
  enriched corpus exactly once; 0% of withdrawn abstracts are
  present — verified by an automated test against a fixture
  containing both.
- **SC-005**: Three-case movement test (US4) passes with all three
  assertions: dropped, restored-from-cache, unchanged.
- **SC-006**: Random lookup of any single abstract by ID from the
  enriched corpus completes in under 10 milliseconds on a typical
  developer laptop, with the storage format honoring the "minimize
  random seeks" requirement (FR-009).
- **SC-007**: The on-disk enriched corpus file is smaller than
  the equivalent verbose JSON representation by at least 30% (the
  exact ratio depends on the storage format chosen during
  planning).
- **SC-008**: The full project test suite remains green after the
  feature lands (excluding the pre-existing unrelated failure in
  `test_plot_poster_layout_floorplan`), and the
  `constitution-check.sh --full` lint stays at exit 0.
- **SC-009**: A run interrupted mid-enrichment is resumable: the
  next invocation re-uses every per-record cache entry already
  written and only re-enriches abstracts whose cache entries
  weren't yet populated — verified by an automated test that
  simulates an interruption.

## Assumptions

These are informed defaults applied when the brief did not specify.
Any of them can be overridden in `/speckit-clarify` or
`/speckit-plan`.

- **Storage format**: line-delimited JSON (JSONL) with an optional
  byte-offset index sidecar (`*.idx.json`) keyed by abstract ID,
  optionally gzip-compressed. JSONL is stdlib-friendly, streams
  cheaply, compresses well, and an offset sidecar gives O(1)
  random lookup. SQLite is an alternative considered in planning;
  the spec's only firm constraint (FR-009) is "single file +
  O(1) random by ID + compact".
- **Default models** (mirrors current pipeline defaults; operator
  can override via CLI flags or env):
  - Figure interpretation: OpenAI `gpt-4.1-mini`.
  - Claims extraction: OpenAI `gpt-4o-2024-08-06` via `cllm`.
  - Reference resolution: lexical splitting → DOI/PMID → OpenAlex
    title search → Semantic Scholar fallback (the existing
    multi-stage strategy).
- **Cache key semantics**: `sha256(component_input)` joined with
  `model_id` (or `strategy_id` for references). Both content and
  model are part of the cache key — changing either invalidates.
  Model VERSION drift (same identifier, different weights) is NOT
  auto-detected; operators force a refresh via
  `--invalidate <component>` when they know it has changed.
- **Per-record provenance is corpus-level, not per-abstract**: the
  Stage 2 Provenance Record names the models once at the corpus
  level. Per-abstract enrichment records include just the cache
  key (which embeds the model identifier) — avoids inflating
  every record with redundant model strings while remaining
  fully auditable.
- **Failure threshold defaults**: per-component failure rate above
  5% exits non-zero (matches Stage 1's figure-failure-threshold
  default). The threshold is configurable per component via CLI.
- **Withdrawn-corpus enrichment is OUT of scope for v1**: Stage 2
  only runs against `data/primary/abstracts.json`. If a future
  decision wants withdrawn abstracts enriched (e.g., for organizer
  audit purposes), it's a separate spec round; the cache layout
  is already keyed by `(content_hash, model_id)`, so the
  withdrawn-corpus run would naturally reuse cached components.
- **Pre-existing oversized enrichment.py refactor**: at ~62 KB,
  `src/ohbm2026/enrichment.py` is a cleanup candidate. The spec
  DOES NOT mandate that refactor — only that Stage 2's
  orchestrator + per-component contracts are clean. The plan
  phase can decide whether to split `enrichment.py` now or in a
  follow-on round.
- **Reference resolution backends**: the existing multi-stage
  resolution strategy (DOI → PMID → OpenAlex title → Semantic
  Scholar) is retained. The "model" for the references component
  is the **strategy version** plus any LLM-assisted
  reference-splitting model identifier.
- **Cache-versioning**: when the cache schema itself changes
  (e.g., adding a new field to cache entries), the cache files
  carry a `cache_version` field. Loading a cache entry with an
  unrecognized `cache_version` treats it as a cache miss and
  re-runs the component; no silent migration.

## Future Work (explicitly OUT of scope for this spec)

- **Stages 3..N cleanups**: embeddings (`embed-*`), clustering
  (`semantic-analysis`, `cluster-benchmark`), projections
  (`umap-plot`, `compare-projections`, `optimize-projections`),
  UI build (`export-ui`, `build-ui`), poster layout / sequencing.
  Each gets its own `/speckit-specify` round.
- **Astro UI rewrite**.
- **Withdrawn-corpus enrichment**: only the accepted corpus is
  enriched in v1.
- **Splitting `enrichment.py`** into smaller modules: candidate
  follow-up, not mandated by this spec.
- **Replacing JSONL with SQLite or Parquet** for the enriched
  corpus: planning-phase decision; this spec only constrains
  shape (single file, O(1) random, compact).
- **Cross-stage state-key namespacing convention**: each stage
  derives its own state-key from its inputs. A future
  meta-stage may unify these into a single project-state graph;
  out of scope here.
