# Research: Multi-Source Ingest Foundation

Consolidated findings from the architecture review (four subsystem deep-reads)
and the issue #66 discussion that motivated it.

## R1 — There is no source abstraction today

Grep for `Protocol|ABC|abstractmethod|Source` across `src/ohbm2026` returns
only unrelated hits. The two real sources share nothing:

| Aspect | OHBM (Oxford GraphQL) | NeuroScape (PubMed release) |
| --- | --- | --- |
| Entry | `fetch/stage.py` + `assets.py` | `atlas_package/neuroscape_loader.py` |
| Record | untyped `dict` (`assets.normalize_abstract:311-337`) | `ArticleHeader` dataclass (`:89-112`) |
| Primary id | `id` (Oxford submission_id) | `pubmed_id` |
| Display id | `poster_id` (= `program_code`) | `pubmed_id` |
| Errors | `GraphQLAPIError` | `NeuroScapeInputError` |
| Transport | Hasura GraphQL, `x-api-key` | on-disk CSV + HDF5 |

**Decision**: introduce ONE interface + ONE record, additive first. Do not
refactor the incumbents in the same slice (keeps their artifacts byte-stable).

## R2 — Identity is the deepest debt

`poster_id` (an Oxford `program_code`) is the universal key from ingest to URL
routes; NeuroScape answered this by adding a *second* namespace rather than
generalizing. Two forward-looking hooks already exist but are **cosmetic**:

- `ui_data/builder.py:123` — `conference_id="ohbm2026"` stamped into
  `build_info` only; does not participate in paths or state-keys.
- `ui_data/types.py:290` — `CrossConferenceLinkRow` with format-agnostic
  `id_a`/`id_b`, never populated.

**Decision**: identity = `record_uid = "<source>:<native_id>"`. This is the
structural version of those two hooks and the node id a KG (#66) will use.
The colon delimiter is reserved (source names may not contain it) so the uid
splits back unambiguously.

## R3 — The fixed six-component section schema

`embed/components.py:29-68` matches `title/introduction/methods/results/
conclusion/claims` literally against Oxford `responses[].question_name`, and
these six are *exempt from the coverage gate* (`embed/stage.py:360-376`) — a
corpus with different section names yields **silently empty** bundles.

**Decision**: `AbstractRecord.sections` is an open `Mapping[str,str]`. bioRxiv
maps its single blob to `sections["abstract"]`. Migrating the embed
component-resolver to read `record.sections` (and to fail loudly on a
requested-but-absent section) is FR-008/FR-009 follow-up.

## R4 — bioRxiv chosen as the proof source (why not another conference)

Picking a *different family* stresses the abstraction harder than a second
GraphQL conference would:

- id is a **DOI** (string), not an int submission id.
- enumeration is **date-interval pagination with a cursor**, not an id list.
- content is a **single abstract blob**, not named sections.
- authors are a **semicolon-delimited string**, not structured rows.

bioRxiv/medRxiv/psyArxiv are named directly in #66, and this environment
exposes bioRxiv + PubMed MCP tools, so it is both strategically relevant and
locally testable. The public details API
(`api.biorxiv.org/details/<server>/<interval>/<cursor>`) needs no credentials.

## R5 — Network injection for offline tests (Principle I + III)

The source takes an injectable `fetch_page(server, interval, cursor)`. The
default is a stdlib `urllib` GET (honours the environment proxy); tests pass a
fake returning fixture pages. `fetched_at` is injected, never read from the
clock inline, so a build can make normalized output deterministic (matches the
repo's resumability discipline).

## R6 — Relation to issue #66 (what this does and does NOT do)

Does:
- Supplies the source-neutral record + interface + global identity + provenance
  that multi-source ingestion and a knowledge graph both require.
- Demonstrates a preprint family (bioRxiv), one of the named #66 targets.

Does NOT (separate arcs / specs):
- **Arc B — embedding/projection seam.** #66 reports the MiniLM→NeuroScape-64d
  projector failed; MSenden proposes a natively-aligned embedder. Making the
  embedder/projector pluggable is its own spec; Arc A is its precondition.
- **KG / claims-as-knowledge-model.** The convergence of ECO-annotated claims
  + Stage-23 research dimensions + structsense extraction onto a graph schema
  (BioCypher referenced in-thread) is downstream of this record.
- **Frontend per-site config registry.** The ~186 `SITE_MODE ===` conditionals
  and the 2,500-line `+page.svelte` are a separate UI arc.
- **Federation** (downloadable subgraphs, lab/personal graphs — NeuroWiki,
  MeetGraph, lokf): a program-level concern this record is a building block for.

## R7 — Sequencing risk

Do **not** add a third conference through the current `atlas_package` path
(`OhbmInputRecord`, `ohbm_overlay`, `sibling_state_keys={"ohbm2026","neuroscape"}`,
the three hosting enumeration tuples that `raise` on an unexpected parquet).
Doing so hardens the two-corpus enumeration further. Arc A + the OHBM/NeuroScape
adapters (FR-008) first; then the corpus dimension in paths/state-keys (FR-009);
then revisit the projection seam (Arc B).
