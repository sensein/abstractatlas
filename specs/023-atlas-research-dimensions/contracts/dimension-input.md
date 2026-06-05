# Contract — Dimension Input & Build Wiring

## Distiller CLI (`scripts/distill_dimensions.py`)

Reduces the full operator file to the slim build input.

```
distill_dimensions.py --in  data/inputs/neuroscape-dimensions/abstracts.detail.json \
                      --out data/inputs/neuroscape-dimensions/dimensions.slim.json
```

- Reads the full `abstracts.detail.json`; per abstract keeps only the Oxford
  submission id + the four dimension label lists; drops every other field.
- Writes the slim file (data-model §2c) deterministically (`sort_keys=True`).
- Raises `DimensionInputError` if the source isn't the expected shape (no
  `abstracts` map / no join key / no dimension fields on any record).
- Both files are gitignored under `data/inputs/neuroscape-dimensions/`.

## Build CLI surface (`scripts/build_ui_data.py`)

New optional argument — points at the **slim** file:

```
--dimensions PATH    Slim dimensions file (dimensions.slim.json), keyed by
                     Oxford submission id, carrying only the four dimension
                     label lists. When present, each exported abstract is
                     left-joined with its focus / research_modality /
                     theory_scope / epistemic_basis lists. When absent, those
                     four facets are empty (opt-in per build).
```

Default: `None`. Recommended path (gitignored):
`data/inputs/neuroscape-dimensions/dimensions.slim.json`.

Threaded into `build_ui_data_package(..., dimensions_path=args.dimensions)`.

## `ohbm2026.ui_data.dimensions` (NEW module)

```python
DIMENSION_KEYS: tuple[str, ...]          # the 4 canonical keys
DIMENSION_LABELS: Mapping[str, str]      # key -> human label

class DimensionInputError(Stage6BuildError): ...

def distill_dimensions(full_path: Path, slim_path: Path) -> dict[str, Any]:
    """Read the full abstracts.detail.json, write the slim file (data-model
    §2c), return a small summary {abstracts_in, abstracts_out_with_values}.
    Raises DimensionInputError on layout mismatch. Deterministic output."""

def load_research_dimensions(path: Path) -> dict[int, dict[str, list[str]]]:
    """Read the SLIM file. {submission_id: {dim_key: [labels]}}. Raises
    DimensionInputError on missing/unreadable/malformed/layout-mismatch input."""

def compute_dimension_coverage(
    dimensions: Mapping[int, Mapping[str, list[str]]],
    exported_submission_ids: Iterable[int],
    *, source_file: str, source_sha256: str,
) -> dict[str, Any]:
    """The §3 provenance block. matched/no_value per dimension + unmatched_in_file."""
```

### Behavioural requirements

| Condition | Required behaviour |
|-----------|--------------------|
| `--dimensions` omitted | 4 facets empty; no provenance block; build succeeds (logged once) |
| path passed, file absent/unreadable | raise `DimensionInputError` naming the path |
| not valid JSON / wrong top-level shape | raise `DimensionInputError` (layout discovered, not assumed) |
| no record has any of the 4 fields | raise `DimensionInputError` ("not a dimension file") |
| a dimension value not a list-of-str | raise `DimensionInputError` naming the id + dimension |
| file entry id not in export | counted into `unmatched_in_file`, logged, **not** added (FR-012) |
| exported abstract not in file | its 4 dimensions are `[]` (no error) |
| empty list for a dimension | treated as no-value (`[]`) |
| duplicate/whitespace labels | de-duplicated, stripped (peer-facet parity) |

## Builder wiring (`builder.py`)

1. If `dimensions_path`: `dims = load_research_dimensions(path)`; compute
   `source_sha256` (streamed) + `source_file` (basename).
2. Pass `research_dimensions=dims` into `build_abstracts(...)`.
3. After abstracts built, `coverage = compute_dimension_coverage(dims,
   exported_submission_ids=abstract_ids, source_file=..., source_sha256=...)`.
4. Pass `dimension_coverage=coverage` into `build_manifest(...)` → embedded in
   the manifest's `research_dimensions` block (omitted when no file).

## Provenance (FR-010 / CA-008)

Manifest gains `research_dimensions` (§3 of data-model). Stores **basename +
sha256** only — never an absolute or `~` path. Serialized under the existing
`json.dumps(manifest, sort_keys=True)` path so rebuilds stay byte-identical.

## Tests (write first — all fail before implementation)

`tests/test_ui_data_dimensions.py`:
- distill happy-path → slim file contains only id + 4 lists, no other fields;
  deterministic (two runs byte-identical); raises on full-file layout mismatch;
- load happy-path (slim file) → correct `{id: {dim: [labels]}}`;
- missing-file / bad-JSON / wrong-shape / no-dimension-fields / non-list-value
  → `DimensionInputError`;
- coverage: `matched + no_value == corpus_count` per dimension (D1);
- `unmatched_in_file` counts file-only ids and adds zero abstracts (D3);
- de-dup + strip of labels (D2 parity).

`tests/test_ui_data_abstracts.py` (extend): with a dimension map, exported
records' `facets` carry the 4 keys with the right labels; abstracts absent from
the file get `[]`; omitting the map ⇒ all 4 empty (D4).
