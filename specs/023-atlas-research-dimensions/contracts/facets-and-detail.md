# Contract — Facets & DetailPanel UI

Scope: `/ohbm2026/` only. Atlas-root and neuroscape are untouched (they do not
consume `ohbm2026.parquet` facets).

## Data carrier

The four dimensions ship as four list-of-string sub-fields of each abstract's
`facets` STRUCT in `ohbm2026.parquet` (see data-model §4). The site loader is
generic — `AbstractRecord.facets: Record<string, string | string[]>`
(`shards.ts:93`) and `loader.ts:516` hydrate them with no change.

## Parquet emitter (`formats/parquet_single.py`)

`_facets_to_arrow` `keys` tuple (line 82) MUST include the four keys, else the
columns are silently dropped:

```python
keys = (..., "brain_networks", "accepted_for",
        "focus", "research_modality", "theory_scope", "epistemic_basis")
```

**Test**: `tests/test_ui_data_parquet_single.py` — round-trip an abstract with
non-empty dimensions; assert the decoded `facets` STRUCT carries all four with
values; assert an empty dimension round-trips as `[]`.

## Manifest catalog (`manifest.py`)

`FACET_KEYS` + `FACET_LABELS` gain the four keys (labels from
`DIMENSION_LABELS`). `_facet_options` auto-discovers options.

**Test**: `tests/test_ui_data_manifest.py` — the four facets appear in
`manifest["facets"]` with non-empty `options` matching the fixture's labels.

## Site facets (`site/src/lib/facets.ts`)

Add the four keys to `FACETS_FROM_BLOCK`, `FACET_KEYS_ORDERED` (insert after
`brain_networks`, before `keywords`), and `FACET_LABELS`. `valuesFor()`
unchanged.

**Behaviour**: each is a multi-valued OR-membership facet (value present in the
record's list); option counts narrow with the active query exactly like every
other block facet (FR-008, FR-009).

**Test**: `site/src/tests/unit/facets.test.ts` — fixtures gain the 4 keys;
assert `valuesFor` returns the labels; assert facet-count maps include the 4
facets with correct per-option counts; assert OR-membership for a multi-label
record.

## Site sidebar (`FacetSidebar.svelte`)

No component change — renders generically from `FACET_KEYS_ORDERED`. The four
facets appear automatically once `facets.ts` is updated. (Optional: leave them
out of `collapsedByDefault` to start open, or include to start collapsed —
implementer's choice; default to collapsed to match peer block facets.)

## Site DetailPanel (`DetailPanel.svelte`)

Add four labelled chip blocks in the computed-insights zone
(`data-zone="computed"`, near line 489), template = the Methods chip block
(line 725):

- one block per dimension, `data-testid="extra-{key}"`, `<h2>{label}</h2>`,
  `<ul class="chips">` of the values;
- coerce `string -> [string]`, array passthrough;
- render nothing when the list is empty (FR-007 — no empty/`N/A` chip);
- visually consistent with existing chip groups (reuse `.chips` / `.extra`).

**Tests**:
- unit (component or facets-adjacent): empty dimension ⇒ block omitted.
- e2e (`site/src/tests/e2e/detail-extra-fields.spec.ts`): open an abstract
  known to have all four dimensions → all four blocks render with values; open
  one missing `theory_scope` → that block absent, others present.

## Schema doc (`specs/008-ui-rewrite/contracts/ui_data.linkml.yaml`)

`AbstractRecord.facets` slot is `range: Any` (line 280) — no structural change.
Update its description: "the 11 keyword/method/etc. lists" → "the 15
keyword/method/dimension lists" so the doc stays truthful.

## Non-regression (FR-014 / SC-006)

Existing facets, search, scatter, claims, figures behaviour unchanged. The
`tests/test_ohbm2026_parquet_rename.py`-style byte-stability check (SC-005) and
the existing Stage 6 invariant suite (`builder.py:302`) must still pass.
