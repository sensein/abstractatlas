# Book of Abstracts — operator summary

Compose a publication-quality book of every accepted abstract —
title, authors with affiliations, full body text, embedded figures,
and the author-supplied references — sorted by `poster_id` (default),
`title`, or `first_author` surname, with a page-numbered author
index at the back.

**Markdown is the canonical intermediate.** `book.md` is always
emitted (the source-of-truth artefact). PDF and DOCX derive from it
via pandoc — PDF through xelatex with `\makeindex` /`\printindex` for
the page-numbered index; DOCX through pandoc's native docx writer
(clickable anchor cross-references; PAGEREF-based page numbers are
a documented future enhancement).

**No AI-generated content reaches the book.** Content sourced
exclusively from Stage-1 artefacts (`data/primary/abstracts.json` +
`authors.json` + `data/inputs/assets/`); never from Stage-2
enrichments. Verified by an SC-006 audit logged in
`provenance.json.no_ai_audit` and by a static import-graph check
that ensures no Stage-2 / enrich module appears in the book
package's source.

## Spec + design

Full spec, plan, research, data-model, CLI contract, and quickstart
live under `specs/011-abstracts-book/`:

- `spec.md` — FR-001..011, SC-001..007, CA-001..008.
- `plan.md` — pandoc subprocess pipeline; system-dep contract.
- `research.md` — seven decisions (no-captions reality,
  HTML→markdown once at load, pandoc-only rendering, body-section
  policy, figure-DPI handling, determinism via pikepdf+zipfile,
  optional Tufte styling).
- `data-model.md` — three layers (Stage-1 inputs → markdown-bearing
  in-memory model → outputs with figure-filename contract).
- `contracts/cli.md` — `ohbmcli book` flags, error path table,
  known limitations.
- `quickstart.md` — operator runbook for install + first run.

## Quick reference

```bash
# One-time install of the optional extra:
uv pip install --python .venv/bin/python ".[abstracts_book]"

# One-time install of system deps (macOS):
brew install pandoc tectonic

# Markdown-only first run (no system deps needed):
PYTHONPATH=src .venv/bin/python -m ohbm2026.cli book --format md

# Full PDF run:
PYTHONPATH=src .venv/bin/python -m ohbm2026.cli book --format pdf --sort poster_id

# All three formats + Tufte typography for the PDF:
PYTHONPATH=src .venv/bin/python -m ohbm2026.cli book --format all --sort poster_id --style tufte
```

Outputs land at `data/outputs/book/book__<state-key>/`. Figure
assets carry the filename pattern
`<submission_id>-<poster_id>-<type>[-<index>].<ext>` (flat
directory; index suffix only for multi-of-type).
