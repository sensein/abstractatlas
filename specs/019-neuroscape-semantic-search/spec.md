# Feature Specification: NeuroScape Semantic Search

**Feature Branch**: `019-neuroscape-semantic-search`
**Created**: 2026-05-26
**Status**: Draft
**Input**: User description: "let's do semantic search"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find neuroscience articles by meaning, not keyword (Priority: P1)

A researcher visiting `/neuroscape/` wants to discover articles related to a
concept (e.g. "default mode network rumination") even when the article titles
don't use those exact words. Today the subsite ships **only typo-tolerant
lexical search over the ~461k article titles**, so a query like *"resting
state introspection"* returns nothing if no title contains both substrings —
even though dozens of titles about default-mode-network rumination, mind-
wandering, and self-referential thought are semantically relevant.

The OHBM 2026 subsite (`/ohbm2026/`) already has this behaviour: a `✨ Semantic`
toggle expands the result list with cards surfaced by meaning-similarity, each
flagged with a `✨` badge so the user can distinguish "matched my words" from
"matched my intent". The same affordance is the most-requested gap on
`/neuroscape/`.

**Why this priority**: This is the single largest discoverability gap on the
new NeuroScape subsite. Spec 015 / FR-018 explicitly committed to title-only
lexical search as the v1 release-blocker, with the matching semantic phase
deferred to a sibling stage. With Stage 15 shipped, this is that sibling
stage.

**Independent Test**: Open `/neuroscape/`, type a 3-5 word concept phrase that
does NOT appear verbatim in any article title (e.g. *"sleep memory
consolidation hippocampus"*), enable the `✨ Semantic` toggle, and observe at
least one semantically related article surface in the result list with a `✨`
badge. Toggle off → the result list reverts to the lexical-only set.

**Acceptance Scenarios**:

1. **Given** the user is on `/neuroscape/` and types a multi-word concept
   phrase that has zero substring matches in any title, **When** they enable
   `✨ Semantic`, **Then** the result list shows semantically related articles
   each marked with a `✨` badge, ranked by semantic similarity.

2. **Given** a query string that has BOTH lexical matches AND semantically
   related non-lexical matches, **When** semantic search is enabled, **Then**
   the result list shows lexical hits first (unbadged) followed by semantic-
   only hits (badged), in a single ranked list.

3. **Given** the user toggles `✨ Semantic` off, **When** the result list
   re-renders, **Then** all `✨`-badged rows disappear and only the lexical
   set remains, preserving scroll position.

4. **Given** the user clicks a `✨`-badged article row, **When** the detail
   panel opens, **Then** it loads the full abstract from PubMed (via the
   existing E-utilities path established in Stage 15) — there is no new
   metadata required to make a semantic-only hit clickable.

---

### User Story 2 - Visual feedback while the semantic index loads (Priority: P2)

The semantic index for the full 461k-article corpus is a non-trivial download
the first time a user enables `✨ Semantic`. The OHBM 2026 corpus's semantic
sidecar is ~1 MB (3,240 abstracts); NeuroScape's is ~140× that. A first-time
toggle must give the user a clear "loading semantic search…" affordance so
the toggle does not appear broken or frozen.

**Why this priority**: Without it, the feature feels broken on first use —
the user enables the toggle, nothing visibly changes for several seconds, and
they conclude semantic search "doesn't work" or "didn't load". Strong loading
feedback is the difference between a usable feature and one users disable.

**Independent Test**: Clear browser storage, navigate to `/neuroscape/`,
enable `✨ Semantic` for the first time, observe a visible loading state on
the toggle (or near it) while the semantic vectors download and the worker
initialises, and confirm the toggle reaches a stable "ready" state before
the user is allowed to expect semantic hits in the result list.

**Acceptance Scenarios**:

1. **Given** the user enables `✨ Semantic` for the first time in this
   session, **When** the semantic vectors are still downloading, **Then** the
   toggle shows a loading indicator and the result list does not silently
   appear stale.

2. **Given** the semantic vectors fail to download (network error,
   429-rate-limit on the host, etc.), **When** the failure is detected,
   **Then** the toggle returns to its off state and a visible message
   explains the failure with a `Retry` affordance — the user is never left
   with a toggle stuck in a "loading forever" state.

3. **Given** the user has previously loaded the semantic vectors in this
   browser, **When** they re-enable `✨ Semantic` in a later session, **Then**
   the toggle reaches the ready state in under 2 seconds without re-
   downloading (a cache hit on the asset).

---

### User Story 3 - Search-bar continuity with the rest of the site (Priority: P3)

The OHBM 2026 `<SearchBar>` already supports a rich syntax (operators like
`au:`, `kw:`, `id:`, semantic toggle, `-foo` exclude clauses). The
`/neuroscape/` subsite currently has a slimmer, cluster-and-year-scoped
search input only. As semantic ranks land, the search experience between the
two subsites becomes inconsistent.

**Why this priority**: Stage 15 already committed to slim-by-design for the
NeuroScape search (the corpus is 100× larger and the field set is
"title-only"), and the operator syntax wouldn't add value where the only
indexed field is `title`. So this story is about **shared UX patterns** (`✨`
toggle visual, badge styling, ranking-tie-break behaviour) rather than full
search-bar parity. Worth doing because it removes the "this subsite feels
different" friction visitors report when they cross-navigate via atlas-root
links.

**Independent Test**: Cross-navigate `/ohbm2026/` → `/neuroscape/`, observe
that the `✨ Semantic` toggle has the same visual position, the same
loading-state pattern, and the same `✨` badge styling on semantic-only
result rows. Then cross-navigate back to `/ohbm2026/` and confirm nothing in
that experience changed.

**Acceptance Scenarios**:

1. **Given** a user familiar with the OHBM 2026 search toggle, **When** they
   land on `/neuroscape/`, **Then** the `✨ Semantic` toggle is visually and
   behaviourally consistent: same position relative to the input, same
   loading affordance, same disabled-while-loading semantics.

2. **Given** the user has both subsites open in tabs, **When** they enable
   semantic search on one, **Then** enabling it on the other does not require
   re-learning the toggle — the affordance is recognisably the same control.

---

### Edge Cases

- **Empty query + semantic enabled**: a user who toggles `✨ Semantic` on
  with an empty input sees no semantic-only hits (since there is no query to
  rank against). The toggle should remain visibly "on" and ready; semantic
  hits appear as soon as the user types.
- **Single-character or very short query**: queries shorter than a small
  threshold (e.g. <3 chars) MUST NOT spend a worker round-trip on semantic
  ranking. The toggle stays on but semantic ranking pauses until the query
  has enough signal.
- **Filtered scope**: when a cluster or year facet is active, the semantic
  result list MUST respect the facet — semantic-only hits OUTSIDE the active
  facet scope are filtered out, not displayed greyed-out.
- **Already-in-cart row surfaced semantically**: an article the user already
  added to their cart via lexical search and that ALSO scores high
  semantically MUST NOT appear twice. Its row shows the existing in-cart
  state and no `✨` badge (the lexical match takes precedence over the
  semantic-only badge).
- **Browser without WebAssembly / SIMD**: the semantic worker MUST detect the
  absence of the runtime features it needs (e.g. SIMD for the cosine
  similarity inner loop) and surface a clear "semantic search isn't
  available on this browser" state rather than silently falling back to a
  slow path that locks the UI thread.
- **Stale on-disk cache after a re-build**: when a `build-atlas-package`
  rebuild changes the semantic index state-key, an old browser cache MUST
  detect the mismatch (via the index's manifest sidecar) and re-fetch
  rather than serve a stale index whose row order no longer matches the
  current articles table.
- **First-load on a metered connection**: the semantic index download MUST
  be entirely user-initiated (only triggered when the user enables `✨
  Semantic`) so visitors who never use the feature never pay the bytes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `/neuroscape/` subsite MUST add a `✨ Semantic` toggle to
  its search affordance, visually consistent with the OHBM 2026 toggle.

- **FR-002**: When semantic search is enabled and the query is non-empty,
  the result list MUST be a MERGE of (a) the existing lexical typo-tolerant
  matches over titles AND (b) semantic top-K matches from the NeuroScape
  article corpus, with each semantic-only row visibly badged.

- **FR-003**: Semantic-only result rows MUST carry the same `✨` badge
  styling and tooltip text as the OHBM 2026 site — the visual contract is
  shared between the two subsites so users learn it once.

- **FR-004**: The semantic index MUST be loaded lazily — bytes are
  downloaded only after the user enables `✨ Semantic`. Visitors who do not
  enable semantic search MUST NOT incur any of the index's network cost.

- **FR-005**: A successful first-time semantic toggle MUST surface a
  loading state (visual indicator on or near the toggle) for the duration
  of the index fetch + worker boot. The toggle MUST reach a stable "ready"
  state before the user is expected to see semantic hits in the result
  list.

- **FR-006**: A failed semantic index load (network failure, server error,
  byte-count mismatch with the manifest, etc.) MUST return the toggle to
  its off state with a visible explanatory message + a `Retry` affordance.
  The toggle MUST NOT silently stay in a "loading forever" state.

- **FR-007**: The semantic index MUST be byte-identical for the same
  underlying NeuroScape article set + semantic-model parameters across
  rebuilds (the same byte-identity contract that the rest of Stage 15 already
  honours via pinned timestamps).

- **FR-008**: The detail panel for a semantically-surfaced article MUST be
  identical to the detail panel for a lexically-surfaced article (same
  PubMed E-utilities fetch path, same per-article permalink, same cart-add
  affordance). Semantic-only rows are full first-class citizens once
  surfaced.

- **FR-009**: When a cluster or year facet is active on `/neuroscape/`, the
  semantic result list MUST respect that facet — semantic-only hits outside
  the active scope are filtered from the result list, NOT shown greyed-out.

- **FR-010**: Queries with fewer than a minimum-character threshold MUST
  NOT spend a worker round-trip. The threshold MUST match the OHBM 2026
  site's existing minimum so users do not see different "semantic kicks in
  after N chars" behaviour between the two subsites.

- **FR-011**: The semantic index sidecar MUST ship with machine-readable
  provenance (article-set state-key, model identifier, vector dimension,
  quantisation strategy, build code-revision, build wall-clock timestamps)
  so the browser can detect a stale-cache vs. current-index mismatch and a
  human can audit which articles + model produced the embeddings.

- **FR-012**: The `ohbmcli build-atlas-package` command MUST be the single
  entry point that produces the semantic index. The index MUST be produced
  in the same run that produces `neuroscape.parquet` (so the two are
  always co-versioned) and MUST live next to it on the deploy host.

- **FR-013**: A configuration flag on `ohbmcli build-atlas-package` MUST
  allow operators to skip the semantic-index step for fast iterations on
  the rest of the build (the index pre-compute is the longest single step
  on a fresh run). When skipped, the produced bundle MUST be missing only
  the semantic sidecar — `neuroscape.parquet` itself MUST be unchanged.

- **FR-014**: The browser MUST detect a `neuroscape.parquet` ↔ semantic-
  sidecar state-key drift (the parquet says state-key X, the cached
  sidecar says state-key Y) and surface a precise reload affordance — the
  same visible-error pattern Stage 15 established for the cross-parquet
  drift detector.

- **FR-015**: The semantic similarity computation MUST run off the main
  thread (in a Web Worker). The result list MUST remain scroll-responsive
  while a semantic ranking is in flight.

- **FR-016**: The `/ohbm2026/` semantic search behaviour, the OHBM
  parquet, and the atlas-root build MUST be byte-identical before and
  after this change. This feature MUST add a sibling artefact to the
  NeuroScape side without modifying any OHBM 2026 surface.

### Key Entities

- **NeuroScape semantic index**: a per-article vector keyed by `pubmed_id`,
  produced once per `neuroscape.parquet` rebuild, carrying enough numerical
  precision for relative-rank cosine similarity but quantised aggressively
  enough that the full corpus stays a manageable download. Co-versioned
  with the articles table via a shared state-key.

- **Semantic-index manifest**: a small companion JSON document that
  declares the state-key, model identifier, vector dimension, quantisation
  strategy, vector count, byte-count, and build provenance. The browser
  fetches this first to decide whether its cached index is still fresh.

- **Query embedder**: the in-browser pathway from the user's typed string
  to a vector in the same space as the corpus index. Runs entirely client-
  side so no per-query network call is made. The embedder model MUST match
  the corpus embedder model (else cosine similarity is meaningless).

### Constitution Alignment *(mandatory)*

- **CA-001**: All Python execution for the semantic-index build step
  (orchestrator, embedding compute, sidecar emit, tests) MUST use
  `.venv/bin/python` or `uv` targeting that interpreter.

- **CA-002**: Each behaviour-changing user story MUST land with its tests
  added or updated BEFORE implementation:
  - US1 tests: semantic-only hit appears in the merged result list with a
    `✨` badge for a query with no lexical matches; toggle-off reverts.
  - US2 tests: loading indicator visible during first toggle; failure
    path returns toggle to off + shows Retry.
  - US3 tests: the toggle's visual position + badge styling match the
    OHBM 2026 reference.
  - Index byte-identity test: two consecutive `build-atlas-package` runs
    with pinned timestamps produce sha256-identical semantic sidecars
    (mirrors the existing parquet byte-identity test).

- **CA-003**: When this feature lands, the spec 015 plan + the `CLAUDE.md`
  reading-order block MUST be updated to record the semantic-search add,
  and the deferred-item inventory's "NeuroScape semantic search" entry
  MUST be flipped from Still-Relevant to Addressed.

- **CA-004**: No new external service credentials are required by this
  feature — embedding compute runs locally during the
  `ohbm2026.build-atlas-package` Python step. If a future iteration ever
  swaps to a hosted embedding API, that swap MUST name the env-var
  boundary in its spec, not this one.

- **CA-005**: The semantic index sidecar produced by the Python build
  MUST land under a gitignored path (`data/outputs/atlas-package/` is
  already gitignored). No part of the index — bytes, manifest, or per-
  build provenance — may be tracked in the repository.

- **CA-006**: Every failure mode in the spec (sidecar fetch failure,
  byte-count mismatch, state-key drift, missing browser feature) MUST
  surface a visible, actionable error to the user — never a silent
  fallback to lexical-only ranking with no explanation. The browser MUST
  log enough context to the dev console for support diagnosis.

- **CA-007**: The build step MUST NOT hardcode the NeuroScape article
  count, the v1.0.1 shard layout, or the per-shard pubmed-id range. The
  article set, vector dimension, and per-article ordering MUST be
  discovered at runtime from the same NeuroScape v1.0.1 loader that
  Stage 15 already uses.

- **CA-008**: The deployed semantic sidecar MUST ship with its provenance
  file (FR-011) alongside the bytes — same path root, no absolute paths,
  no user-home paths. The provenance MUST name the build code-revision,
  the model identifier, the wall-clock build timestamps, the article-set
  state-key, and the resulting vector-bytes sha256 so the browser can
  cross-check a cached copy against a fresh manifest.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user typing a 3-5 word conceptual query that has ZERO
  lexical title matches MUST receive at least one `✨`-badged semantic
  hit in the result list within 3 seconds of the last keystroke (after
  the semantic index is loaded).

- **SC-002**: First-time semantic-toggle activation MUST reach a stable
  "ready" state — semantic hits visible for the current query — within
  10 seconds on a typical home broadband connection (≥10 Mbps). Slower
  connections see a proportional wait but never a frozen UI.

- **SC-003**: Subsequent semantic-toggle activations in a returning
  session (same browser, same site state-key, valid cache) MUST reach
  the "ready" state in under 2 seconds. The browser MUST NOT re-download
  the index when its cached copy matches the current sidecar manifest.

- **SC-004**: A second `build-atlas-package` run with unchanged
  NeuroScape inputs + pinned timestamps MUST produce a byte-identical
  semantic sidecar (sha256 match) to the first run. This mirrors the
  existing Stage 15 byte-identity contract.

- **SC-005**: Adding the semantic-index build step to a fresh
  `build-atlas-package` run MUST add less than 15 minutes to the
  end-to-end wall-clock time on the operator's reference machine. The
  index pre-compute step MUST be cacheable on its own (same key
  approach as the UMAP-fit cache) so an iteration that does not change
  the article set is essentially free on re-run.

- **SC-006**: On a representative sample of 20 evaluation queries
  curated by the project (concept queries that have known semantically-
  relevant articles but no exact-string title overlap), at least 80% of
  the queries MUST surface at least one of the curated relevant
  articles in the top-10 semantic hits. Below this rate the spec is not
  shipping a usable semantic experience and the underlying embedding
  recipe needs revisiting.

- **SC-007**: The OHBM 2026 site (`/ohbm2026/`) build output MUST be
  byte-identical before and after this change ships (gh-pages bundle
  sha-tracked in CI). This feature is a strictly additive sibling on
  the NeuroScape side.

- **SC-008**: The `✨ Semantic` toggle MUST be visually identical
  (position, label, loading-spinner pattern, badge styling) between
  the two subsites — verified by a side-by-side screenshot diff in
  the e2e suite that already gates each deploy.

## Assumptions

- **Corpus scope**: The semantic index covers the FULL NeuroScape v1.0.1
  article set that `/neuroscape/` already serves (~461k articles,
  1999–2023). No year-range or cluster-subset filtering is applied at
  index-build time — the runtime facets handle scope filtering on the
  user's side.

- **Semantic field**: Embeddings cover article TITLES ONLY. This matches
  the explicit user stipulation that for NeuroScape "we only need to
  store the pubmed_id and fetch abstract details on the fly" (recorded
  in the spec 015 clarification round). Indexing body text would require
  shipping body text, which contradicts that directive.

- **Embedding model**: The corpus embedder + browser query embedder pair
  is the same MiniLM family the OHBM 2026 site already uses. This keeps
  the two subsites' semantic affordance behaviourally consistent (same
  similarity metric, same query-to-vector transform) and reuses the
  existing Web Worker + INT8-quantisation pattern without inventing a
  second one. The exact model identifier is a planning-phase choice and
  may differ in a minor variant (e.g. a slightly larger MiniLM trained
  on a biomedical corpus) — but the FAMILY is fixed.

- **Quantisation**: INT8 quantisation is the planning-phase default,
  consistent with the OHBM 2026 site. If the planning phase finds that
  INT8 yields a sidecar above ~80 MB (the largest cost we are willing
  to put behind a user-initiated toggle), the plan may select a more
  aggressive scheme (PCA pre-quantisation, product quantisation, or a
  smaller-dim model). This trade-off is OUT OF SCOPE for this spec —
  the SCOPE is "ship semantic search", not "ship MiniLM-INT8
  specifically".

- **Distribution**: The semantic sidecar ships alongside
  `neuroscape.parquet` on the same gh-pages-served path that the
  parquet uses today. No new hosting infrastructure is needed.

- **Cache strategy**: The browser uses the same Cache API + state-key
  validation pattern that Stage 15 already uses for the parquet
  bundle. The state-key check is the source of truth for "is my cache
  still fresh?", not a wall-clock TTL.

- **Browser support**: WebAssembly + SIMD is assumed available on
  contemporary desktop and mobile browsers (the same baseline the
  OHBM 2026 semantic worker already requires). Older browsers see the
  "feature unavailable" path from FR-006.

- **Cross-conference search**: A user typing on `/ohbm2026/` does NOT
  see NeuroScape articles in their results, and vice-versa. Each
  subsite's search remains scoped to its own corpus. Cross-conference
  semantic search across both corpuses is a separate, future scope and
  intentionally NOT in this spec.

- **Permalink behaviour unchanged**: Clicking a semantic-only result
  row opens the same `/neuroscape/abstract/<pubmed_id>/` permalink that
  a lexical-only row opens. The semantic ranking is a discovery aid
  layered on the existing detail-panel path; nothing about
  per-article detail loads or permalinks changes.

- **Stage-15 byte-identity invariants survive**: Adding this feature
  must NOT change `atlas.parquet` or `ohbm2026.parquet` bytes. Only
  `neuroscape.parquet` may grow (if the planning phase elects to embed
  the sidecar inside it) and a new sidecar file may appear. The
  existing CI byte-identity gate is the enforcement mechanism.
