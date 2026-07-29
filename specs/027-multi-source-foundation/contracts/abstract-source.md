# Contract: `AbstractSource`

The interface every ingest source satisfies. Defined in
`src/ohbm2026/sources/base.py` as a `@runtime_checkable` `Protocol`, with
`BaseAbstractSource` (ABC) supplying the composed `records()` for convenience.

## Interface

```python
@runtime_checkable
class AbstractSource(Protocol):
    @property
    def descriptor(self) -> SourceDescriptor: ...
    def fetch_raw(self, query: Any) -> Iterable[Mapping[str, Any]]: ...
    def normalize(self, raw: Mapping[str, Any]) -> AbstractRecord: ...
    def records(self, query: Any) -> Iterator[AbstractRecord]: ...
```

## Responsibilities (deliberately separated)

| Member | Purity | Responsibility |
| --- | --- | --- |
| `descriptor` | pure | Static source identity for provenance + discovery. |
| `fetch_raw(query)` | I/O | Yield raw source payloads for a query. The source owns its OWN enumeration/pagination internally (an id list for a conference; date-interval + cursor for a preprint feed). This is the ONLY member that touches a network/disk. |
| `normalize(raw)` | pure | Map ONE raw payload → one `AbstractRecord`. Unit-testable with no I/O. |
| `records(query)` | — | `normalize` ∘ `fetch_raw`. Provided by `BaseAbstractSource`. |

## Guarantees a conforming source MUST provide

- **G1 (loud normalization)**: a raw payload that cannot be normalized —
  missing/empty required field, malformed id — raises
  `SourceNormalizationError`. It MUST NOT return `None` or skip silently
  (Principle VI).
- **G2 (discovered structure)**: field presence and pagination bounds are read
  from the payload (e.g. bioRxiv `collection`, `messages[0].total`), never
  matched against a hardcoded list; a shape mismatch raises (Principle VII).
- **G3 (offline-testable)**: any network access is injectable so `normalize`
  and `records` run in the suite with no live calls (Principle I).
- **G4 (identity + provenance)**: every returned record has a non-empty
  `record_uid` and a `SourceProvenance` with a deterministic `raw_digest`
  (CA-008).
- **G5 (no core leakage)**: source-specific fields go in `record.extra`, not
  new top-level record fields. The core stays source-neutral.

## Conformance tests

`tests/test_sources_base.py` (the interface + record) and
`tests/test_sources_biorxiv.py` (a concrete source). A new source SHOULD add a
`tests/test_sources_<name>.py` asserting: descriptor kind; core-field mapping;
`record_uid`; author parsing; loud failure on a missing required field;
`records()` over an injected fetcher; `isinstance(src, AbstractSource)`.

## Reference implementation

`BiorxivSource` (`src/ohbm2026/sources/biorxiv.py`): a DOI-keyed preprint feed
paginated by date interval, proving the interface holds for a source family
structurally unlike Oxford Abstracts GraphQL.

## Migration path (follow-up, FR-008)

The OHBM ingest and NeuroScape loader become `AbstractSource`s via thin
adapters — `assets.normalize_abstract`'s dict and `ArticleHeader` each map into
`AbstractRecord` — WITHOUT changing their on-disk artifacts. At that point the
embed/analyze middle can read `AbstractRecord.sections` instead of
literal-matching Oxford `question_name`s, and the corpus dimension (FR-009) can
enter `artifacts.py` paths + `build_dependency_basis`.
