# Phase 1 — Data Model: Atlas Research-Classification Dimensions

## 1. Dimension constants (single source of truth)

Defined once in `src/ohbm2026/ui_data/dimensions.py` and mirrored in
`site/src/lib/facets.ts`. The Python tuple drives the merge, the parquet key
tuple, and the manifest catalog; the site mirror drives the sidebar + detail.

```python
DIMENSION_KEYS = ("focus", "research_modality", "theory_scope", "epistemic_basis")

DIMENSION_LABELS = {
    "focus": "Focus",
    "research_modality": "Research modality",
    "theory_scope": "Theory scope",
    "epistemic_basis": "Epistemic basis",
}
```

Observed category vocabularies (discovered from data — NOT enforced as an enum,
FR-004; listed here for reference/tests only):

| Dimension | Observed labels (count in 3333-abstract source) |
|-----------|--------------------------------------------------|
| `focus` | Translational (2570), Clinical (1368), Method Development (1247), Fundamental (927), Technological Exploitation (66), Economic (4), Legal (3) |
| `research_modality` | Computational (2097), Experimental (1499), Observational (1432), Meta-analytic (77), Theoretical (15) |
| `theory_scope` | Micro Theory (1532), Domain Framework (1208), Disease-specific Framework (1150), Overarching Framework (17) |
| `epistemic_basis` | Hypothesis-driven (2571), Data-driven (1538) |

## 2. Input files — full detail → slim dimensions (distiller)

### 2a. Full detail file — `abstracts.detail.json` (distiller input only)

Operator-supplied (NeuroScape dimension analysis), ~120 MB. Top-level shape:

```jsonc
{
  "abstracts": {
    "1196698": {
      "id": 1196698,
      "focus": ["Translational", "Clinical"],
      "research_modality": ["Observational", "Computational"],
      "theory_scope": ["Domain Framework"],
      "epistemic_basis": ["Data-driven"]
      // ...many other fields (figure_analyses, claims, ...) — IGNORED
    },
    // ... ~3333 entries keyed by Oxford submission-id string
  }
}
```

This file is **not** read by the data-package build — only by the distiller.

### 2b. Distiller — full → slim (`distill_dimensions(full_path, slim_path)`)

Reads the full file, keeps only the Oxford submission id + the four dimension
label lists per abstract, drops everything else, and writes the slim file
deterministically (`sort_keys=True`, stable ordering). Fails loudly
(`DimensionInputError`) if the source lacks the expected dimension fields or the
`abstracts` map / join key. The distiller is the reproducible source-of-record;
the slim file is regenerable from the full file at any time.

### 2c. Slim dimensions file (build input)

Compact JSON keyed by Oxford submission-id string, four label lists only:

```jsonc
{
  "schema_version": "dimensions.slim.v1",
  "dimensions": {
    "1196698": {
      "focus": ["Translational", "Clinical"],
      "research_modality": ["Observational", "Computational"],
      "theory_scope": ["Domain Framework"],
      "epistemic_basis": ["Data-driven"]
    }
    // ... only abstracts with ≥1 non-empty dimension need an entry
  }
}
```

- **Key**: Oxford submission-id string. Coerced to `int` for the join.
- **Per dimension**: a JSON array of category-label strings (may be empty `[]`).
- **Coverage** (from source): `focus` 3329/3333, `research_modality` 3326/3333,
  `theory_scope` 2890/3333, `epistemic_basis` 3325/3333.
- Gitignored under `data/inputs/neuroscape-dimensions/dimensions.slim.json`.

### Load + validate (`load_research_dimensions(slim_path) -> dict[int, dict[str, list[str]]]`)

Reads the **slim** file. Returns `{submission_id: {dim_key: [labels...]}}`,
dimension keys restricted to `DIMENSION_KEYS`, each value a de-duplicated list of
non-empty strings.

Raises `DimensionInputError` (subclass of `Stage6BuildError`) when:
- path passed but missing / unreadable / not valid JSON;
- top level isn't an object with an `abstracts` object (or a bare `{id: {...}}`
  object) — layout discovered, not assumed (CA-007);
- no record carries **any** of the four expected dimension fields (the file is
  not a dimension file — fail loud rather than emit all-empty facets);
- a present dimension value is not a list of strings.

Empty list ⇒ "no value" (dropped to `[]`, omitted from detail + excluded from
that facet's option counts — FR-007, Edge Cases).

## 3. Coverage report (provenance input)

`compute_dimension_coverage(dimensions, exported_submission_ids) -> dict`:

```jsonc
{
  "source_file": "dimensions.slim.json",       // slim-file basename only — no abs/home path (CA-008)
  "source_sha256": "<64-hex>",
  "dimensions": {
    "focus":             {"matched": 3329, "no_value": 4},
    "research_modality": {"matched": 3326, "no_value": 7},
    "theory_scope":      {"matched": 2890, "no_value": 443},
    "epistemic_basis":   {"matched": 3325, "no_value": 8}
  },
  "unmatched_in_file": 0   // file entries whose submission id is not in the export (FR-012)
}
```

`matched` = exported abstracts that received ≥1 label for that dimension;
`no_value` = exported abstracts with no label for it. `matched + no_value` =
`corpus_count` for every dimension (invariant for the regression test).

## 4. Per-record facets (extended)

`AbstractRow.facets` (TypedDict `FacetValues` in `ui_data/types.py`) gains four
list fields, taking the count from 11 to 15:

```python
class FacetValues(TypedDict, total=False):
    keywords: list[str]
    methods: list[str]
    study_type: list[str]
    population: list[str]
    field_strength: list[str]
    processing_packages: list[str]
    species: list[str]
    recording_technology: list[str]
    brain_regions: list[str]
    brain_networks: list[str]
    accepted_for: list[str]
    focus: list[str]               # NEW
    research_modality: list[str]   # NEW
    theory_scope: list[str]        # NEW
    epistemic_basis: list[str]     # NEW
```

Populated in `iter_abstracts` from `research_dimensions.get(abstract_id, {})`;
each missing dimension defaults to `[]`. Serialized into the parquet abstracts
STRUCT by widening the fixed key tuple in `_facets_to_arrow`
(`parquet_single.py:82`).

## 5. Manifest facet catalog (extended)

`manifest.py` `FACET_KEYS` + `FACET_LABELS` gain the four keys; `_facet_options`
then auto-discovers their option sets from the per-record `facets` lists
(alphabetical, like the other block facets). The manifest also gains the
`research_dimensions` provenance block from §3, embedded via
`build_manifest(... dimension_coverage=...)`.

## 6. Site mirror (`facets.ts`)

```ts
const FACETS_FROM_BLOCK = [ /* …existing 10… */,
  'focus', 'research_modality', 'theory_scope', 'epistemic_basis' ] as const;
// FacetKey union auto-includes them via (typeof FACETS_FROM_BLOCK)[number]
// FACET_KEYS_ORDERED: insert the 4 after 'brain_networks', before 'keywords'
// FACET_LABELS: add the 4 labels from DIMENSION_LABELS
```

`valuesFor()` needs no change (generic `record.facets[key]` fallback).

## 7. DetailPanel computed-insights blocks

Four labelled chip blocks (`data-testid="extra-{key}"`, `data-zone="computed"`)
rendered in the computed-insights zone, each:
- reads `abstract.facets[key]` (coerce string→[string], array passthrough);
- renders nothing when the list is empty (FR-007);
- styled with the existing `.chips` / `.extra` classes.

## 8. Invariants (additive to Stage 6 §8)

- **D1**: for every dimension, `matched + no_value == manifest.corpus_count`.
- **D2**: every label present on an exported abstract's dimension comes
  verbatim from the source file for that submission id (no synthesis).
- **D3**: `unmatched_in_file` counts file entries with no exported match; those
  entries add zero abstracts (left-join — Clarification 1).
- **D4**: omitting `--dimensions` ⇒ all four facet lists empty on every record,
  `research_dimensions` provenance block absent/empty, build still succeeds.
- **D5**: same file + same corpus ⇒ byte-identical `ohbm2026.parquet` (SC-005).
