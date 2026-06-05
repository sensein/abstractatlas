# Phase 0 — Research: Atlas Research-Classification Dimensions

All "NEEDS CLARIFICATION" items from Technical Context are resolved below.
Each entry: **Decision / Rationale / Alternatives considered**, grounded in the
actual code paths read during planning (file:line references).

## R1 — Integration point: where do the four dimensions enter the data?

**Decision**: Merge inside the **Stage 6 UI-data builder**
(`scripts/build_ui_data.py` → `ohbm2026.ui_data.builder.build_ui_data_package`
→ `ui_data/abstracts.iter_abstracts`), injecting the four dimensions into each
exported record's existing `facets` dict. The four keys then flow unchanged
through the parquet emitter, the manifest facet catalog, and the site's
generic facet loader.

**Rationale**:
- `iter_abstracts` (`src/ohbm2026/ui_data/abstracts.py:445`) already yields each
  record with `abstract_id` (the Oxford submission id — the dimension file's
  key) AND a `facets` dict (`abstracts.py:597`). The four dimensions are
  list-of-string categorical axes — structurally identical to existing facet
  lists like `keywords` / `brain_regions`. They belong in `facets`.
- Iterating only the accepted/deduped/exported corpus makes the left-join
  one-directional for free (Clarification 1): a dimension-file entry whose
  submission id is never yielded is simply never looked up → never added.
- The site loader (`site/src/lib/shards.ts:93`) types `facets` as
  `Record<string, string | string[]>` and the parquet decoder
  (`loader.ts:516`) hydrates the struct generically — adding sub-fields needs
  zero loader changes.

**Alternatives considered**:
- *Fold into the Stage 2 enriched corpus* (`abstracts_enriched.sqlite`):
  rejected — these dimensions were computed by a separate external analysis,
  not the Stage 2 figures/claims/references pipeline; threading them through
  Stage 2 would conflate two provenance chains and force a corpus re-enrich for
  a UI-only display change.
- *Merge in `build-atlas-package`* (the parquet that feeds atlas-root /
  neuroscape): rejected — `build-atlas-package` consumes `ohbm2026.parquet` for
  vectors/overlay only, not facets; the four dimensions are scoped to
  `/ohbm2026/` (spec Assumptions), so atlas-root/neuroscape must stay
  untouched.
- *Separate top-level record field instead of `facets`*: rejected — would
  bypass the manifest facet catalog + the site's generic facet machinery,
  forcing bespoke loader/sidebar code for no benefit.

## R2 — Join key

**Decision**: Join by **Oxford submission id**. The dimension file is a JSON
object keyed by submission-id strings (`"1196698"`), and each record also
carries `id` with the same value. The canonical corpus record's `id`
(`abstracts.py:579`, surfaced as `abstract_id` on the yielded record) is that
same submission id. Coerce both to `int` for the lookup.

**Rationale**: `abstract_id` is already the internal join key the rest of the
build uses for rollup/analysis joins (`abstracts.py:576-579`). The export
drops it from the wire (only `poster_id` ships), but it is available at
build/merge time — exactly where the join happens.

**Alternatives considered**: title/text matching (rejected — fragile,
collision-prone, and unnecessary when a stable id exists).

## R3 — Surfacing: facets + detail (confirmed via Clarification 2)

**Decision**: Surface as **both** filterable facets (sidebar) and per-abstract
computed-insights (DetailPanel chips). No scatter color-overlay.

**Rationale + mechanics** (from the site exploration):
- **Facets**: the sidebar (`FacetSidebar.svelte:72`) renders generically from
  `FACET_KEYS_ORDERED`; `valuesFor()` (`facets.ts:100`) already falls back to
  `record.facets[key]` for any key. So the *only* site facet change is adding
  the four keys to three constants in `facets.ts` (`FACETS_FROM_BLOCK`,
  `FACET_KEYS_ORDERED`, `FACET_LABELS`). Facet *options* are auto-discovered.
- **Detail chips**: existing categorical facets are deliberately NOT shown in
  the DetailPanel today (`DetailPanel.svelte:464` comment). The four dimensions
  are an *additive* exception — add four labelled chip blocks (template: the
  Methods chip block, `DetailPanel.svelte:725`) in the computed-insights zone
  (`data-zone="computed"`, around line 489), each guarded to omit when the
  list is empty (FR-007).

**Alternatives considered**: detail-only (rejected — Clarification 2 chose
both); scatter color-overlay (rejected — out of scope, larger change to the
UMAP color pipeline).

## R4 — Manifest is informational; `facets.ts` is the source of truth

**Decision**: Update **both** the Python manifest facet catalog AND the site
`facets.ts` constants.

**Rationale**: The manifest's `facets[]` array (`manifest.py:217`) is emitted
and carries key/label/options, but the site does NOT drive the sidebar from it
— the sidebar is hardcoded to `FACET_KEYS_ORDERED` (`facets.ts`). So the Python
manifest change alone will NOT surface the facets in the UI; `facets.ts` must
also gain the four keys. We keep the manifest catalog correct anyway (CA-007
discovery + future-proofing + provenance), and the parquet `_facets_to_arrow`
fixed key tuple (`parquet_single.py:82`) must gain the four keys or the columns
are silently dropped.

**Alternatives considered**: make the sidebar fully manifest-driven (rejected —
larger refactor, out of scope; noted as possible future cleanup).

## R5 — Provenance carrier (FR-010 / CA-008)

**Decision**: Record dimension provenance in the **manifest** (the data
package's machine-readable provenance surface; embedded in the `manifest`
table of `ohbm2026.parquet`). Add a `research_dimensions` block:
`{source_file: <basename>, source_sha256: <hex>, dimensions: {focus: {matched,
no_value}, ...}, unmatched_in_file: <int>}`. Store the file *basename* +
sha256, never an absolute/home path (CA-008).

**Rationale**: Stage 6 has no separate `data/provenance/*.json` file — the
manifest's `build_info` is the provenance contract, validated byte-identical
across shards (Invariant 6, `builder.py:406`). Extending the manifest keeps
provenance co-located with the artifact.

**Alternatives considered**: a standalone `data/provenance/dimensions__*.json`
(rejected — diverges from the Stage 6 manifest-as-provenance pattern; the
manifest already travels with the parquet to every consumer).

## R6 — Failure modes (FR-011 / CA-006 / CA-007)

**Decision**: New typed `DimensionInputError(Stage6BuildError)`. Raise precisely
when: `--dimensions` is passed but the path doesn't exist / isn't readable;
the JSON isn't the expected `{id: {…}}` object; the file is missing all four
expected dimension fields on every record (layout mismatch — discovered, not
assumed); or a record's dimension value isn't a list of strings. When
`--dimensions` is **omitted**, the four facets are simply empty (no error) —
the feature is opt-in per build, matching how `--enriched`/`--references` are
optional. Unmatched-in-file submission ids are counted + logged (not an
error), per Clarification 1 / FR-012.

**Rationale**: Constitution VI/VII — fail loud on contract violations, discover
the layout at runtime, never silently emit a corpus that *looks* enriched but
isn't. The "absent file ⇒ empty facets" path is the deliberate, documented
opt-in default, not a silent fallback (it's logged and the empty facets are
visibly absent in the UI).

**Alternatives considered**: hard-require `--dimensions` always (rejected —
would break every existing build invocation and dev rebuild that doesn't have
the file).

## R7 — Determinism (Invariant 6)

**Decision**: The join is a pure dict lookup over a sorted iteration; no
randomness, no timestamps in the merged values. Coverage counts are derived
deterministically from the (unchanged file, unchanged corpus). Same inputs →
byte-identical `ohbm2026.parquet` (the existing `DETERMINISTIC_MTIME` +
`sort_keys` machinery already guarantees this for the manifest provenance
block, which uses `json.dumps(..., sort_keys=True)` at `parquet_single.py:289`).
**Verification**: SC-005 — rebuild twice, assert identical bytes.

## R8 — Slim derived input via a distiller (Clarification 3 + 4)

**Decision**: The build does NOT read the ~120 MB `abstracts.detail.json`
directly. A small repo distiller (`scripts/distill_dimensions.py` +
`dimensions.distill_dimensions`) reduces it to a slim
`dimensions.slim.json` (`{submission_id: {4 dimension lists}}`, all other
fields dropped). The build's `--dimensions` flag points at the slim file. Both
files are gitignored under `data/inputs/neuroscape-dimensions/`.

**Rationale**: keeps the build input compact and purpose-built; the distiller
is the reproducible source-of-record (Constitution III) so the slim file is
regenerable rather than a hand-made artifact; Constitution II keeps both the
raw and derived files out of git (the distiller's determinism is what makes
not-committing safe — Clarification 4 chose gitignored over a committed seed).

**Alternatives considered**: read the four fields from the full file in place
(rejected — Clarification 3 chose a slim file); commit the slim file as a seed
(rejected — Clarification 4 chose gitignored, consistent with Constitution II).
