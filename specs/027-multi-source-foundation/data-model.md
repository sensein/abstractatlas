# Data Model: Multi-Source Ingest Foundation

All types live in `src/ohbm2026/sources/base.py`. Frozen dataclasses; the two
open mappings (`sections`, `extra`) are wrapped in `MappingProxyType` so a
record is genuinely immutable.

## AbstractRecord

The single canonical, source-neutral record. Replaces OHBM's untyped `dict`
(keyed on `poster_id`) and NeuroScape's `ArticleHeader` (keyed on `pubmed_id`).

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `source` | `str` | ✅ | Short source name, e.g. `"biorxiv"`, `"ohbm2026"`. No `:`. |
| `native_id` | `str` | ✅ | The source's own id — DOI, submission id, PMID. Always coerced to `str`. |
| `title` | `str` | ✅ | Non-empty. |
| `display_id` | `str \| None` | | Human-facing id (`poster_id` for OHBM, DOI for a preprint). |
| `abstract` | `str \| None` | | Full abstract text when the source has one blob. |
| `sections` | `Mapping[str,str]` | | Open section-name → text. Generalizes the fixed six OHBM components. Read-only. |
| `authors` | `tuple[AbstractAuthor, …]` | | Ordered. |
| `figure_urls` | `tuple[str, …]` | | Source figure/asset URLs (empty for text-only sources). |
| `venue` | `str \| None` | | e.g. `"bioRxiv"`, `"OHBM 2026"`. |
| `year` | `int \| None` | | Publication/submission year. |
| `url` | `str \| None` | | Canonical link (e.g. `https://doi.org/<doi>`). |
| `extra` | `Mapping[str,Any]` | | Source-specific opaque fields (category, version, license…). Kept OUT of the core so the generic pipeline stays source-neutral. Read-only. |
| `provenance` | `SourceProvenance \| None` | | Per-record provenance. |

**Derived**: `record_uid` (property) = `"<source>:<native_id>"`.

**Validation** (`__post_init__`, raises `SourceNormalizationError`):
`source`, `native_id`, `title` must be non-empty strings; `record_uid` must be
composable (rejects colon-in-source).

## AbstractAuthor

| Field | Type | Notes |
| --- | --- | --- |
| `name` | `str` | Always present (raw display name). |
| `family` | `str \| None` | Best-effort parse. |
| `given` | `str \| None` | Best-effort parse. |
| `orcid` | `str \| None` | |
| `affiliation` | `str \| None` | |
| `order` | `int \| None` | 0-based author order. |

## SourceDescriptor

| Field | Type | Notes |
| --- | --- | --- |
| `name` | `str` | Source short name (no `:`). |
| `kind` | `str` | One of `{conference, preprint, journal, corpus, talk, other}` — validated. |
| `title` | `str` | Display name. |
| `homepage` | `str \| None` | |
| `api_base` | `str \| None` | |
| `notes` | `str \| None` | |

`VALID_SOURCE_KINDS` is a small, spec-extensible vocabulary — **not** a
per-source allow-list. Each concrete source declares its own kind.

## SourceProvenance (CA-008)

| Field | Type | Notes |
| --- | --- | --- |
| `source` | `str` | |
| `descriptor` | `SourceDescriptor` | Static source identity. |
| `fetched_at` | `str \| None` | ISO timestamp, injected (never `now()` inline). |
| `raw_digest` | `str` | sha256 of the canonicalized raw record (order-stable, matches `artifacts._stable_hash` style). |
| `query` | `str \| None` | Optional query descriptor. |

## Identity helpers

- `build_record_uid(source, native_id) -> str` — `"<source>:<native_id>"`;
  rejects empty parts and a colon in `source`.
- `split_record_uid(uid) -> (source, native_id)` — inverse.
- `digest_raw(raw) -> str` — deterministic sha256 for provenance.

## Mapping examples

### bioRxiv details record → AbstractRecord

| bioRxiv field | AbstractRecord |
| --- | --- |
| `doi` | `native_id`, `display_id`; `url = https://doi.org/<doi>` |
| `title` | `title` |
| `abstract` | `abstract`, `sections["abstract"]` |
| `authors` (`"Last, First; …"`) | `authors[]` (parsed family/given, order) |
| `date` (`YYYY-MM-DD`) | `year` |
| `server` | `venue` (`bioRxiv`/`medRxiv`) |
| `category`, `version`, `license`, `published`, `author_corresponding*` | `extra{}` |

### OHBM record → AbstractRecord (FR-008 adapter, not yet landed)

| OHBM field (`normalize_abstract`) | AbstractRecord |
| --- | --- |
| `id` (submission_id) | `native_id`; `source="ohbm2026"` |
| `poster_id` | `display_id` |
| `title` | `title` |
| `responses[]` by `question_name` | `sections{}` (introduction/methods/results/conclusion/…) |
| `figure_urls` | `figure_urls` |
| `accepted_for`, `program_sessions`, `external_urls` | `extra{}` |
