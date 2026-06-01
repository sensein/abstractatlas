# Search Unification Plan — ohbm2026 / atlas-root / neuroscape

**Status:** implemented (PR #60). Phases 1–4 + the facet-count fix are landed and verified on production data; see the per-phase checklist in §3.

**Why:** Three site surfaces (`SITE_MODE` = `ohbm2026`, `atlas-root`, `neuroscape`) run search with diverging engines and, on the two large NeuroScape surfaces, semantic search that is neither exhaustive nor cleanly decoupled from the rendered scatter. atlas-root recently returned **zero** semantic results (fixed in PR #59) precisely because the ranker's lookup maps were derived from the displayed LOD scatter. This plan makes search behave consistently, reach the whole corpus, and never depend on what the UMAP happens to be showing.

## Guiding principles (non-negotiable)

1. **Consistent search** semantics across `ohbm2026`, `atlas-root`, `neuroscape` — same query grammar, same ranking contract, same result-assembly shape.
2. **Exhaustive reachability** — despite NeuroScape/atlas-root scale (~461k articles), the algorithm must provide a path to search the *entire* corpus, not a sample or a single routed cluster.
3. **UMAP-independent search** — what is rendered in the scatter must never gate search results on atlas-root or neuroscape. The scatter is display-only. It may *filter* results only when the user explicitly acts (facet selection, lasso) — exactly like ohbm2026.

---

## 1. Current state (analysis of prior steps)

### 1.1 Per-surface search flow

**ohbm2026 (~3.2k abstracts).**
- Index: `buildInvertedIndex` over the **full text** (title + sections + authors + topics + methods), `filter.ts`.
- Lexical: `lexicalSearch()` → `searchInvertedIndex()`; operators AND/OR/`"phrase"`/`-negation` with Damerau-Levenshtein typo tolerance.
- Semantic: worker brute-forces cosine over the **entire** INT8 corpus matrix (loaded once at init). Exhaustive.
- Result: `ResultList`, sorted by exactness then semantic score. Search set = `filteredIds` (search ∩ facets ∩ lasso ∩ author chips).

**atlas-root (~461k NeuroScape backdrop + ~3.2k OHBM overlay).**
- Scatter (`atlasBackdrop`): decimated LOD tier (carries umap coords) — **display only**.
- Search corpus (`listCorpus`): **full 461k** identity table, deliberately decoupled from the scatter (`+page.svelte:562-573`).
- Lexical: `searchTitleIndex()` over `titleSearchIndex` (full 461k, **title-only**) + a locally-built overlay index. Same operators as ohbm.
- Semantic: cluster-routed ranker when the vectors sidecar is configured, else KNN-only fallback.
- Result: `AtlasRootBrowsePanel` (merged backdrop + overlay; lexical first, semantic-only rows appended).

**neuroscape (full 461k).**
- `atlasBackdrop === listCorpus` (full corpus; no split).
- Lexical: `searchTitleIndex()` over the full title index. Same operators.
- Semantic: cluster-routed ranker (primary) + KNN fallback. Result: `NeuroscapeBrowsePanel`.

### 1.2 Divergences

| | ohbm2026 | atlas-root | neuroscape |
|---|---|---|---|
| Lexical index | full-text inverted index | title-only (full 461k) | title-only (full 461k) |
| Lexical engine/operators | shared parser; AND/OR/phrase/neg/typo | same | same |
| Semantic method | brute-force over full INT8 matrix | cluster-routed ranker / KNN fallback | cluster-routed ranker / KNN fallback |
| Semantic exhaustive? | **yes** | **no** (≤1–4 of 175 clusters) | **no** (≤1–4 of 175 clusters) |
| Result component | `ResultList` | `AtlasRootBrowsePanel` | `NeuroscapeBrowsePanel` |

The lexical contract is already consistent. The split is in **semantic**: ohbm is exhaustive brute-force; the NeuroScape surfaces are cluster-bounded. The title-only vs full-text difference on NeuroScape is a **data** constraint (the corpus ships titles only), not a code one.

### 1.3 UMAP → search coupling points

Search results are **not** gated by the rendered LOD scatter — the result list runs over `listCorpus`/`filteredBackdrop` (full corpus). Facet (`+page.svelte:696-708`) and lasso (`737-747`, point-in-polygon over **full** coords) filters apply to both scatter and search — these are legitimate, explicit user filters (the ohbm model).

The real violations are in the **semantic** layer:

- **R1 — ranker maps built from the scatter.** `pubmedToCluster` and `knnIndex` are built from `atlasBackdrop` (`+page.svelte:1338-1350`). On atlas-root that is the LOD sample, so most full-corpus ids the ranker brute-forces were absent → every candidate dropped → 0 results (PR #59 patched the symptom by falling back to the routed cluster for seeds; the *source* coupling remains).
- **R2 — KNN-fallback seeds gated by `filteredBackdrop`.** `neuroscapeKnnHits` intersects seeds with the facet-filtered backdrop (`+page.svelte:816,819`). When no explicit facet/lasso is active this is the full corpus (fine); the concern is only that the gate is expressed against the display structure rather than the corpus + an explicit filter set.
- **R3 — `knn=0` everywhere.** The k=20 graph (`neighbors_neuroscape`, 461k rows, present and correct in `neuroscape.parquet`) is folded onto articles only in a **late background wave** (`+page.svelte:1474-1485`), *after* `initRanker` has already snapshotted `atlasBackdrop` into `knnIndex`. The ranker is never re-initialised, so KNN-expansion never runs on either surface. Semantic is currently "routed-cluster only".

### 1.4 Exhaustiveness bounds

- Lexical: exhaustive on all three (full-corpus index).
- Semantic ohbm: exhaustive (full brute-force).
- Semantic NeuroScape: bounded by cluster routing (1 cluster) + per-query cap (`clusterCap=4`, FR-024) → ~4/175 clusters reachable; `SEMANTIC_TOP_N=250`, `SEMANTIC_MAX_DISTANCE=0.8`. The "Expand search depth" affordance lifts the cap but is still cluster-bounded. A relevant article in a non-routed, non-expanded cluster is unreachable. Full vector set = **172 MB** (why routing exists).

---

## 2. Proposed unified design

### 2.1 Principle 1 — consistency

- Keep the shared `parseQuery` grammar + operators across all three (already true).
- Unify result assembly into one contract: lexical hits ranked by exactness, then semantic-only hits appended by ascending distance, with the `✨ d=` badge — already near-identical between the panels; factor the shared ranking/merge into one helper so the three panels can't drift.
- Document that NeuroScape semantic + lexical are **title-scoped** because the corpus ships titles only; this becomes full-text automatically if/when abstract text is added to `neuroscape.parquet`. No code fork.

### 2.2 Principle 3 — UMAP-independent search

- Build the ranker's `pubmedToCluster` and `knnIndex` from the **full corpus** (`listCorpus` + `neighbors_neuroscape`), never from `atlasBackdrop`. This removes R1 at the source (and makes PR #59's seed fallback a belt-and-suspenders rather than the load-bearing fix).
- Re-initialise (or incrementally update) the ranker config when the full corpus + neighbours finish loading, so `knnIndex` is populated — fixes R3.
- Express the KNN-fallback seed gate (R2) as `corpus minus explicit-filter`, not as "membership in the displayed backdrop". With no active facet/lasso, the gate is the entire corpus.
- Invariant to lock with a test: for a fixed query and fixed facet/lasso state, **results are identical regardless of LOD tier / what the scatter renders**.

### 2.3 Principle 2 — exhaustive, relevance-bounded semantic (chosen approach)

**Progressive cluster sweep, bounded by semantic distance, accelerated by the k=20 graph** (per the design decision):

1. Embed the query; rank all ~175 cluster centroids by similarity.
2. Load the nearest cluster; brute-force → seeds.
3. **KNN-expand via `neighbors_neuroscape`** from the seeds. The graph already carries neighbour ids + distances, so this reaches the closest cross-cluster matches **without fetching those clusters' full vectors** — cheap recall where it matters most.
4. **Sweep outward** to the next-nearest centroids, merging hits, **only while** results stay within the distance threshold (`SEMANTIC_MAX_DISTANCE`). **Stop** when the best new hits from the next cluster exceed the threshold (and/or the centroid distance itself crosses it) — no fetching far/irrelevant clusters.
5. Cost therefore scales with the *relevance neighbourhood* of the query, not with corpus size. A tight query touches ~1 cluster + its KNN neighbours; a broad query sweeps more, stopping at the relevance horizon.

This gives a genuine path to exhaustive recall **within the relevant region** while bounding bandwidth. A hard "search everything" fallback (full 172 MB brute-force) can be layered later if a use case ever needs recall beyond the threshold, but is not required by this design.

This also tightens consistency with ohbm: ohbm brute-forces its (small) full matrix; NeuroScape brute-forces the relevant clusters + KNN-expands — the same "find nearest by cosine, gate by distance" contract, scaled by routing.

### 2.4 Prerequisite fix (unblocks 2.2/2.3)

Wire `neighbors_neuroscape` into the ranker's `knnIndex` from the full corpus at (or after) the neighbours wave, and re-init the ranker config. Without this the sweep has no graph to accelerate with and `knn=0` persists.

---

## 3. Implementation phases

1. ✅ **Decouple ranker maps from the scatter** (P3/R1): `pubmedToCluster`/`knnIndex` built from `listCorpus`, refreshed in place via `updateRankerMaps` as the corpus/neighbours stream in. Verified: atlas-root `p2c` 327 → 461,316.
2. ✅ **Wire the KNN graph** (R3): `knnIndex` populated from `neighbors_neuroscape`; ranker maps upgraded after the neighbours wave (no worker/LRU reset). Verified: neuroscape `knn` 0 → 461,316.
3. ✅ **Relevance-bounded progressive sweep** (P2): `rankClusters` + nearest-first sweep with the distance-threshold stop + KNN-expand; FR-024 cap bounds bandwidth. Verified: neuroscape 1 → 4 clusters, ~54 → 2243 candidates. Unit tests: neighbouring-cluster reach, threshold stop.
4. ✅ **Unify result assembly** (P1): shared `assembleResults` helper (`src/lib/search/assemble.ts`); atlas-root passes N `CorpusSource`s (OHBM + NeuroScape today), neuroscape passes one. 6 unit tests.
5. ✅ **Facet counts narrow with search** (P1/P3): `neuroSearchMatch`/`ohbmSearchMatch` narrow the facet-count base sources. Verified: neuroscape 461,316/175 → 251/56 clusters.
6. ✅ **Verified on production data** (preview builds, the probe harness): root + neuroscape render broad, threshold-bounded semantic sets; results invariant to LOD tier; no page errors. svelte-check clean; 238 unit tests pass.

**Deferred (follow-ups, not blocking):** atlas-root has no KNN neighbour graph resident (`knn=0` there), so its semantic relies on the routed-cluster sweep without cross-cluster KNN-expansion — fetching a neighbour slice for root would turn that on. OHBM-side semantic (an `ohbm_vectors` table) is still pending the build step.

## 4. Risks / open questions

- Per-query bandwidth under broad queries (many clusters within threshold). Mitigation: cap clusters/query with a visible "expand" affordance; reuse warm clusters (existing LRU).
- The 172 MB hard-exhaustive fallback is intentionally out of scope unless needed.
- Re-init vs incremental update of the ranker config when corpus/neighbours arrive — pick the simpler correct option (full re-init on the neighbours wave).
