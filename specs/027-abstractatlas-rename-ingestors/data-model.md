# Phase 1 Data Model: Abstract Atlas Rename + Pluggable LinkML Ingestors

No change to persisted data (FR-004). The "model" here is (a) the ingest
schema entities and (b) the code-level contract objects. The full schema
lives in `contracts/ingest-schema.linkml.yaml`; this is the conceptual view.

## Ingest schema entities (LinkML)

### IngestedDocument (core)
The normalized record every ingestor emits. Downstream stages consume this.

| Slot | Type | Req | Notes |
|------|------|-----|-------|
| `doc_id` | string | ✓ | stable within-source identity |
| `source` | SourceProvenance | ✓ | which ingestor/source produced it |
| `title` | string | ✓ | |
| `authors` | Author[] | ✓ | ordered; may be empty for some sources |
| `abstract_text` | string | ✓ | abstract / summary body (markdown-ish) |
| `year` | integer | ○ | publication/presentation year when known |

### SourceProvenance
| Slot | Type | Req | Notes |
|------|------|-----|-------|
| `ingestor` | string | ✓ | registered ingestor name (e.g. `ohbm-2026`, `neuroscape-pubmed`) |
| `source_type` | SourceType enum | ✓ | `conference` \| `literature_index` |
| `origin` | string | ✓ | origin identifier (e.g. `oxford-abstracts`, `pubmed`); no absolute/home paths |
| `retrieved_at` | date | ○ | when pulled |

### ConferenceDocument (extends IngestedDocument)
| Slot | Type | Notes |
|------|------|-------|
| `poster_id` | string | preserved OHBM `program_code` mapping |
| `program_sessions` | ProgramSession[] | flattened session/program membership |

### LiteratureDocument (extends IngestedDocument)
| Slot | Type | Notes |
|------|------|-------|
| `doi` | string | when available |
| `venue` | string | journal / server |
| `index_id` | string | e.g. PubMed id, arXiv id (future) |

Validation rules (enforced at ingest, FR-008):
- Core required slots present; `source.source_type` matches the concrete
  class (a `ConferenceDocument` MUST have `source_type == conference`).
- A conference record MUST NOT carry literature-only slots and vice versa
  (prevents source masquerade — edge case).
- Malformed → precise, source-attributed error; record not passed downstream.

## Code-level contract objects

### Ingestor (ABC / Protocol) — `abstractatlas/ingest/base.py`
| Member | Signature | Notes |
|--------|-----------|-------|
| `name` | `str` | unique registered name |
| `source_type` | `SourceType` | conference \| literature_index |
| `pull(...)` | `-> RawRecords` | acquire raw records from the origin (resumable/checkpointed as today) |
| `normalize(raw)` | `-> Iterable[IngestedDocument]` | source-specific normalization (wraps existing logic) |
| `ingest(...)` | `-> IngestResult` | pull → normalize → validate(schema) → write; carries provenance |

### IngestorRegistry — `abstractatlas/ingest/registry.py`
| Member | Signature | Notes |
|--------|-----------|-------|
| `register(ingestor)` | | idempotent registration (decorator/entry-point) |
| `get(name)` | `-> Ingestor` | precise error listing known names if absent (VII) |
| `names()` | `-> list[str]` | runtime-discovered catalog for the CLI |

### First two instances (ports)
- `ConferenceOHBMIngestor` (`name="ohbm-2026"`, `conference`) — wraps
  `fetch/stage.py` + `assets.normalize_abstract`; output byte-identical to
  today's `data/primary/abstracts.json`.
- `LiteratureNeuroscapeIngestor` (`name="neuroscape-pubmed"`,
  `literature_index`) — wraps the NeuroScape record normalization consumed
  by `atlas_package`; output unchanged.

## Rename mapping (identity, not data)

| Old | New | Notes |
|-----|-----|-------|
| package `ohbm2026` | `abstractatlas` | `git mv` + import rewrite |
| CLI `ohbmcli` | `aacli` | canonical; `ohbmcli` = deprecated shim |
| entry points `ohbm-*` | `aa-*` (if used) / dropped | per rename-map |
| `import ohbm2026` | `import abstractatlas` | `ohbm2026` = deprecation shim |
| data paths, state-keys, `ohbm2026.parquet` | **UNCHANGED** | FR-004 — source data identity preserved |

No published data bytes change; only code/CLI/doc identity changes.
