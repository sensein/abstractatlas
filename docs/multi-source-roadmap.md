# Multi-Source Atlas: Current State and Roadmap

**Written**: 2026-07-28 · **Context**: architecture review of the abstract atlas
as it extends beyond OHBM 2026 · **Strategic frame**:
[issue #66](https://github.com/sensein/abstractatlas/issues/66) ("Next steps
towards personalized and global knowledge graphs"), which asks for "a
scientific and engineering roadmap … that we can assign and iterate on
relatively quickly and scalably."

This document is the companion to `specs/027-multi-source-foundation/`. That
spec covers one slice (the ingest seam); this one covers where the whole system
stands and what order the remaining work should happen in.

---

## 1. Current state

### What works well

The Track A pipeline (fetch → enrich → embed → analyze → UI data → three static
builds) is disciplined engineering: content-addressed state keys, append-only
evidence, machine-readable provenance at every stage, typed per-stage exception
subtrees, a constitution that is actually followed, and a genuinely elegant
data-transport trick (row-group-per-table parquet so a browser range-fetches one
inner table instead of a 97 MB file). The ML core — embeddings, UMAP, Leiden/
HDBSCAN, c-TF-IDF topics, claim/reference extraction — is largely corpus-neutral
and ports to new corpora cheaply.

### What blocks multi-source growth

| Layer | State |
| --- | --- |
| Ingest | Two disjoint silos (Oxford GraphQL, NeuroScape release) with no shared contract. Now partly addressed — see below. |
| Identity | No global key. `poster_id` (an Oxford `program_code`) leaks from ingest to URL routes; NeuroScape added a *second* namespace (`pubmed_id`) instead of generalizing. |
| Paths / state keys | Single-corpus by construction (`data/primary/abstracts.json`); several stages actively *enforce* one-corpus-per-tree. |
| Cross-corpus map | NeuroScape is hardcoded as the base map; every corpus must be projectable into its fixed 64-dim UMAP space. **Issue #66 reports this projector failed.** |
| Section schema | A fixed six-component contract matched literally against Oxford `question_name`s; a differently-sectioned corpus yields **silently empty** embedding bundles. |
| Frontend | ~186 `SITE_MODE ===` conditionals across 18 files; a ~2,500-line `+page.svelte` carrying all three sites. Adding a 4th site touches 15–25 files. |
| Hosting | Three enumeration tuples that `raise` on an unexpected parquet; a new corpus file is rejected until all are edited in lockstep. |

### What just landed (PR #73, in review)

`src/ohbm2026/sources/` — a typed source-neutral `AbstractRecord` with global
identity `record_uid = "<source>:<native_id>"`, an open `sections` mapping, and
per-record provenance; an `AbstractSource` interface; and three conforming
sources (`biorxiv` preprint, `ohbm2026` conference, `neuroscape` corpus).

**Important caveat: this seam is inert.** Nothing in the production pipeline
calls it yet. It is a proof that one contract can express three source families,
not a live ingest path. Making it live is Arc A′ below, and it is the single
highest-value next step.

### Three findings that should shape the plan

**F1 — Enrichment economics break at corpus scale.** The claims/figures/
references pipeline is agentic and per-abstract. It is affordable for OHBM
(~3×10³ abstracts) and is why it has never been run over NeuroScape
(~6×10⁵ articles), which stores only four identity fields per record and no
bodies at all. But #66's central goal — "move from search mode to search over
knowledge mode" — requires claims to exist *at corpus scale*. Today's cost model
cannot get there, and bioRxiv alone adds thousands of records a month. This is
the main scientific-ambition-vs-engineering-reality gap.

**F2 — None of the repo's guarantees are enforced remotely.** All eight CI
workflows are UI/deploy/e2e/Lighthouse. **No workflow runs the 426-test Python
suite or the constitution lint** — those live in a local pre-commit hook that
each clone must opt into (`git config core.hooksPath .githooks`). For a
single-maintainer repo that was fine. #66 describes an explicitly multi-person,
multi-repo, agent-assisted effort, where "the byte-identity guarantee" and
"provenance on every artifact" are exactly the invariants a new contributor
breaks first. Cheapest high-leverage fix in this document.

**F3 — The N-deployment frontend model runs out at about three.** One SvelteKit
project built three times via `SITE_MODE` works today because tree-shaking keeps
each bundle clean. At 6–10 sources it becomes 6–10 builds plus a combinatorial
mode matrix, and the atlas-root build already reaches directly into a sibling's
parquet internals (with a drift-detection subsystem existing solely to police
that coupling).

---

## 2. Decisions to make

These are forks in the road, not tasks. Each needs an owner's call; the
recommendation is mine.

### D1 — Does NeuroScape-64d remain *the* canonical map?

- **Options**: (a) keep it and fix the projector; (b) make the map space
  pluggable, with NeuroScape-64d as the default instance; (c) periodically
  re-fit a joint map over all corpora.
- **Recommendation: (b).** (a) locks a general atlas into a neuroscience-tuned
  space, which is wrong for an ML or clinical corpus; (c) breaks the
  byte-identity/immutability guarantees and is expensive. (b) preserves every
  existing NeuroScape result while making the embedder/projector a seam — which
  it must become anyway, since #66 reports the learned projector failed and
  @MSenden is building a natively-aligned embedder to replace the Voyage
  dependency.
- **Consequence**: a corpus declares which map space it lives in; cross-corpus
  neighbour queries are valid only within a shared space, and the UI must say so
  rather than implying false adjacency.

### D2 — What is the enrichment cost model at scale? (see F1)

- **Recommendation: a tiered enrichment ladder, with the tier recorded per
  record.**
  - **T0 — universal**: metadata + embeddings. Cheap, runs over everything.
  - **T1 — bulk**: claim/entity spans from a small local model over a filtered
    subset (recent, on-topic, or high-citation).
  - **T2 — deep**: today's agentic, ECO-annotated, tool-verified pipeline for
    high-value targets (conference corpora, user-requested records).
- **Why it matters beyond cost**: #66 also asks for "some formalism of evidence
  strength and reproducibility". The enrichment tier *is* a first, honest
  evidence-depth signal, and surfacing it prevents the UI from presenting a
  cheaply-extracted claim and a tool-verified one as equally solid.

### D3 — Static artifacts, or a service?

- The architecture's quiet superpower is zero infrastructure: static
  content-addressed artifacts on gh-pages, queried in-browser by range fetch.
  #66's asks (downloadable subgraphs, lab/personal graphs, agent/skill access)
  create pressure toward a queryable backend.
- **Recommendation: stay static as long as possible.** Ship knowledge-graph
  tables in the same range-fetchable parquet layout and publish the URL +
  schema as a documented data contract, so external consumers (structsense,
  MCP servers, NeuroWiki, MeetGraph, lokf) fetch the same bytes the UI does.
  "Download part of the graph into a local system" is *better* served by
  immutable content-addressed files than by an API. Introduce a service only
  when write-back or per-user personalization genuinely demands it — and when it
  comes, let it wrap the artifacts rather than replace them.

### D4 — When to collapse the frontend to one build? (see F3)

- **Recommendation**: at the 4th source, not before — but stop adding new
  `SITE_MODE` conditionals now. Target: one build, a runtime source registry
  (`{id, basePath, dataUrl, schema, facets, idField, permalink}`), per-source
  lazy data loading, unchanged URL layout.

### D5 — Does the package keep the name `ohbm2026`?

- A package named `ohbm2026` (and `ohbmcli`) for a multi-source atlas will
  confuse every new contributor #66 hopes to attract.
- **Recommendation**: rename to a neutral package (e.g. `abstractatlas`) with a
  compatibility shim — mechanical, low-risk, but do it **once**, bundled with
  the Arc A′ path changes so there is a single migration rather than two.

---

## 3. Roadmap

Ordered by dependency, not by appeal. Each arc is independently shippable and
maps to a Spec Kit spec.

### Arc 0 — Enforce the invariants in CI *(days; do first, blocks nothing)*
Run the Python suite + `constitution-check.sh --full` on every PR. Optionally
gate the byte-identity check for `/ohbm2026/` output. **Why first**: it is cheap,
it is a precondition for safely accepting outside contributions (#66's whole
premise), and every later arc is a large refactor whose safety net this is.

### Arc A — Source seam *(landed, in review: PR #73)*
Merge it. Note it is inert until A′.

### Arc A′ — Make the seam live *(the real unlock)*
1. Add the `source` dimension to `artifacts.py` paths and
   `build_dependency_basis`; relax one-corpus-per-tree guards to one-per-source.
2. Point the embed component-resolver at `AbstractRecord.sections`, and make a
   requested-but-absent section a **loud error** instead of a silent empty
   bundle.
3. Route OHBM and NeuroScape ingest through their adapters; assert existing
   artifacts stay byte-identical.
4. Bundle the D5 rename here if approved.
**Exit criterion**: two corpora coexist in one data tree, and adding a third
requires no edits to existing ingest modules.

### Arc B — Pluggable map space + embedder *(unblocks the #66 projector failure)*
Introduce a `MapSpace` (fit vectors, transform out-of-sample, cluster identity)
with NeuroScape-64d as the default instance; land @MSenden's aligned embedder
behind it; remove the hardcoded `expected_dim = 64` and the
NeuroScape-as-base assumption from the orchestrator. Also fix the shared INT8
quantization scale, which today makes adding a corpus perturb existing corpora's
bytes — in tension with the no-regenerate guarantee. **Coordinate with
@MSenden**; this arc is partly upstream of this repo.

### Arc C — Tiered enrichment + evidence depth *(implements D2)*
Ladder T0/T1/T2, tier recorded per record and surfaced in the UI. Unblocks
claims at corpus scale, which is the precondition for "search over knowledge".

### Arc D — Knowledge graph keyed by `record_uid` *(the #66 core)*
Converge the ECO-annotated claims, the Stage-23 research dimensions, and
structsense extraction onto one graph schema whose node identity is
`record_uid` (BioCypher is a reasonable reference, per @adelavega). Ship as
range-fetchable static tables per D3. This is where "abstraction of claims into
a knowledge model" and "connections between problem spaces" become queryable
rather than aspirational.

### Arc E — Frontend source registry *(per D4, at source #4)*
Collapse the ~186 mode conditionals; decompose `+page.svelte`; one build.

### Arc F — Federation and external access *(the #66 endgame)*
A documented, versioned export contract: downloadable subgraph slices,
a stable schema, and an MCP/skill surface so agents and lab tools
(NeuroWiki, MeetGraph, lokf) consume the atlas as data. Depends on Arc D.

### Sequencing risks

- **Do not add a third corpus through the current `atlas_package` path.** Its
  two-corpus enumerations (`OhbmInputRecord`, `ohbm_overlay`,
  `sibling_state_keys`, three hosting tuples that `raise` on an unexpected
  parquet) would harden. A′ and B first.
- **Do not start with Arc D or E.** Both are downstream of the record contract
  (A′) and, for D, of enrichment economics (C). A KG built on today's
  per-corpus id namespaces would need rebuilding.
- **The US4 cross-conference semantic ranker is half-landed** — the browser-side
  merge is contracted but the Python side never writes OHBM vectors
  (`orchestrator.py` hardcodes `n_ohbm_vectors: 0`). Finish or explicitly park
  it; a half-wired feature is a trap for the next contributor.

---

## 4. If only three things happen

1. **Arc 0** — CI runs the tests and the constitution lint. Days of work;
   protects everything else.
2. **Arc A′** — make the source seam live and give artifacts a `source`
   dimension. This is what actually makes "another conference or dataset" a
   configuration rather than a fork.
3. **Decide D1 and D2** — whether NeuroScape stays the mandatory map, and what
   enrichment costs at corpus scale. Both are cheap to decide now and expensive
   to reverse after Arc D exists.
