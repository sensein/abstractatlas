# Contract: Ingestor interface + registry

Module: `src/abstractatlas/ingest/{base,registry,schema}.py`. Additive —
wraps existing normalization, changes no downstream stage.

## `Ingestor` (ABC)

```python
class SourceType(str, Enum):
    conference = "conference"
    literature_index = "literature_index"

class Ingestor(ABC):
    name: str            # unique, registered (e.g. "ohbm-2026")
    source_type: SourceType

    @abstractmethod
    def pull(self, **opts) -> RawRecords: ...
        # acquire raw records from the origin; resumable/checkpointed as the
        # existing stages already are (Constitution III). No behavior change.

    @abstractmethod
    def normalize(self, raw: RawRecords) -> Iterable[IngestedDocument]: ...
        # source-specific mapping to the standardized schema; WRAPS existing
        # logic (assets.normalize_abstract for OHBM; NeuroScape record map).

    def ingest(self, **opts) -> IngestResult:
        # pull → normalize → validate(schema) → write; attaches SourceProvenance.
        # Validation failure raises a precise, source-attributed typed error
        # (no silent skip / partial success — Constitution VI, FR-008).
```

## Registry (runtime discovery — Constitution VII / FR-010)

```python
@register  # or entry-point based
class ConferenceOHBMIngestor(Ingestor): ...

registry.names()      # -> ["neuroscape-pubmed", "ohbm-2026"] (discovered, not hardcoded)
registry.get("xyz")   # -> raises IngestorNotFound("unknown ingestor 'xyz'; known: [...]")
```

- No downstream stage may hardcode a source list; they consume
  `IngestedDocument` generically.
- Adding a new ingestor = implement the ABC + register → runnable via CLI,
  zero downstream edits (SC-006).

## First two instances (ports — SC-003/SC-004)

| Ingestor | name | source_type | wraps | output |
|----------|------|-------------|-------|--------|
| Conference (OHBM) | `ohbm-2026` | conference | `fetch/stage.py` + `assets.normalize_abstract` | byte-identical `data/primary/abstracts.json` |
| Literature (NeuroScape) | `neuroscape-pubmed` | literature_index | NeuroScape record normalization (atlas_package inputs) | unchanged |

## Required tests (failing-first — CA-002)

1. `registry.names()` includes both ported ingestors; `get(unknown)` raises with the known list.
2. Each ingestor's `normalize` output validates against the LinkML schema.
3. A deliberately malformed record → precise source-attributed validation error; not written downstream.
4. Port fidelity: `ConferenceOHBMIngestor` reproduces the prior normalized OHBM corpus byte-for-byte on a fixture.
5. Registry registration is idempotent + discovered at runtime (no hardcoded list).

## Typed errors

Extend the existing `OhbmStageError`→(renamed) exception hierarchy with an
`IngestError` subtree: `IngestorNotFound`, `IngestSchemaValidationError`
(carries source + offending field), consistent with the fail-loud posture.
