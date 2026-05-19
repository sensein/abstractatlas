# Implementation Plan: Book of Abstracts

**Branch**: `011-abstracts-book` | **Date**: 2026-05-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-abstracts-book/spec.md`

## Summary

Deterministic CLI that composes a publication-quality book of every
accepted abstract — title, authors with affiliations, full body
text, embedded figures with question-name labels, and the
author-supplied references — sorted by `poster_id` (default),
`title`, or `first_author` surname, with a paginated author index
at the end. The **markdown bundle is the canonical intermediate**
(spec FR-006a from the 2026-05-19 clarification): HTML → markdown
happens once at corpus load, the `.md` source-of-truth is what
lands on disk, and **PDF + DOCX are derived from the same `.md`
via pandoc** — PDF through xelatex (optional `tufte-book`
document class via `--style tufte`), DOCX through pandoc's native
docx writer. Content sourced exclusively from Stage-1 artefacts
(`data/primary/abstracts.json` + `authors.json` +
`data/inputs/assets/`); zero Stage-2 / LLM enrichment touches the
book.

## Technical Context

**Language/Version**: Python 3.14 (repository `.venv`).

**Primary Dependencies**:
- *In-process Python*: existing project stdlib + `Pillow` (already
  present for `image_quality.py`). New optional extra
  `[abstracts_book]` in `pyproject.toml`: `markdownify>=0.13`
  (HTML → markdown for the body sections + references), `beautifulsoup4`
  (HTML sanitisation pre-conversion). `pypandoc` is **not** required
  — pandoc is invoked via `subprocess.run` so we control argv and
  stderr capture directly.
- *System binaries* (operator install): `pandoc >= 3.1` on `PATH`
  for both PDF and DOCX; a LaTeX distribution providing `xelatex`
  for PDF only — recommend **Tectonic** (~250 MB, fetches packages
  on demand) over TeX Live (~4 GB). Tufte styling is supported by
  both Tectonic and TeX Live via the `tufte-book` class.

**Storage**: read-only from `data/primary/` + `data/inputs/assets/`;
output to gitignored `data/outputs/book/book__<state-key>/`.

**Testing**: `unittest` (project convention); fixture corpus under
`tests/fixtures/book/` with 4-6 synthetic abstracts covering the
edge cases (no figures, missing figure asset, multiple authors,
HTML-tagged body, unicode title, references block as `<ol>`).
The PDF/DOCX rendering tests detect pandoc + xelatex on `PATH` and
`unittest.skip` if either is absent — so contributors without the
system deps can still run the rest of the suite, but CI must
install both (added to the workflow).

**Target Platform**: macOS / Linux developer + CI environment.
pandoc + Tectonic are easy one-line installs on both (`brew
install pandoc tectonic` / `apt-get install pandoc` +
Tectonic-via-curl).

**Project Type**: Track-A canonical pipeline addition (single
`ohbmcli book` subcommand). Mirrors Stage 2 / Stage 3 patterns:
`enrich_stage.py` / `embed_matrix.py` shape.

**Performance Goals**: SC-001 — full ~3,200-abstract book renders
to PDF in < 10 minutes on a typical laptop. Composition (Python
side) is ~30 s; pandoc + xelatex is ~6-9 min, dominated by image
inclusion + LaTeX index emission (`\makeindex` + `\printindex`).
DOCX runs in ~90 s.

**Constraints**: zero LLM calls at runtime (SC-006); byte-identical
markdown bundle on re-run (SC-007a); content-identical PDF / DOCX
on re-run with metadata stripped (SC-007b); minimum effective
resolution 300 DPI at display size for figures in PDF/DOCX
(SC-004); operators MAY enable the optional `tufte-book` document
class for the PDF via `--style tufte`.

**Scale/Scope**: 3,244 abstracts in the current corpus; ~5,800
figures across them; ~22,000 authors. The author index is dense
but each entry is short — expected ~50 pages of back-matter,
~600 pages total PDF.

## Constitution Check

- **I. Venv-only Python**: Every entrypoint runs through
  `.venv/bin/python` or `uv --python .venv/bin/python`. CLI wired
  into `ohbmcli` (`src/ohbm2026/cli.py`) so the existing dispatch
  enforces this. The pandoc + xelatex calls are `subprocess`-level
  shell-outs; they are **not** Python interpreters and the venv-only
  rule doesn't apply to them.
- **II. Immutable evidence, no committed data**: Output lands under
  `data/outputs/book/book__<state-key>/` — gitignored by the
  existing `data/` rule. No artefacts are committed.
- **III. Resumable, auditable**: One-shot batch. Re-runs produce
  byte-identical `book.md` (SC-007a); pandoc-emitted PDF and DOCX
  have their format-imposed timestamps overwritten (R6) so re-runs
  are content-identical (SC-007b).
- **IV. Plan-first, test-first**: Failing tests land before
  renderer code, per US (see `tasks.md` once `/speckit-tasks`
  produces it). The four load-bearing tests:
  (a) no-Stage-2-content audit on `book.md` (SC-006);
  (b) sort order per `--sort` value (SC-005);
  (c) figure-resolution probe ≥ 300 DPI at display size for sampled
  figures (SC-004);
  (d) every accepted author appears in the author index (SC-003).
- **V. Secret-safe**: No credentials used; no `.env` reads.
- **VI. Fail loudly**: Missing figure asset → "figure unavailable:
  <reason>" rendered block (visible failure in the output).
  Malformed corpus → typed `BookBuildError` (added to
  `exceptions.py` as a sibling to `Stage1Error` / `Stage2Error`).
  Pandoc non-zero exit → `BookBuildError` carrying pandoc's stderr.
  Missing `pandoc` or `xelatex` on `PATH` → typed `BookBuildError`
  at startup, before any expensive composition work. No bare
  `except`.
- **VII. Discover external state, don't hardcode**: Body-section
  question_names live as a documented module-level constant
  `BODY_SECTION_NAMES` (editorial policy, not external schema);
  `--include-section` flag extends the set per run.
- **VIII. Provenance for organizer-facing outputs**: Every
  produced book carries a sibling `provenance.json` (FR-010) with
  `corpus_state_key`, `corpus_path` (project-relative),
  `sort_order`, `format`, `style` (`plain` / `tufte`),
  `code_revision_short` + `code_revision_full`, `command_line`,
  `built_at` (ISO-8601 UTC), `abstract_count`, `figure_count`,
  `figures_below_resolution_threshold`, `pandoc_version`,
  `xelatex_version` (when used). No absolute or `~/` paths.

**Re-evaluation (post-design)**: Pass. The shift to pandoc adds
two system deps but those are operator-installable and explicitly
called out in the quickstart and the Assumptions section of the
spec; no constitutional carve-outs needed.

## Project Structure

### Documentation (this feature)

```text
specs/011-abstracts-book/
├── plan.md              # this file
├── research.md          # discovery + technical decisions
├── data-model.md        # entity shapes consumed + emitted
├── quickstart.md        # operator runbook
├── contracts/
│   └── cli.md           # `ohbmcli book` command contract
├── checklists/
│   └── requirements.md  # spec quality checklist (already filled)
└── tasks.md             # produced by /speckit-tasks
```

### Source Code (repository root)

```text
src/ohbm2026/
├── book/                       # new package
│   ├── __init__.py             # re-exports the public surface
│   ├── corpus.py               # load_accepted_abstracts(): filters
│   │                           # withdrawn + null-poster-id +
│   │                           # non-Poster/non-Oral.
│   ├── model.py                # dataclasses: BookEntry, Author,
│   │                           # AuthorAffiliation, FigureBlock,
│   │                           # ReferencesBlock, AuthorIndexEntry.
│   │                           # Body sections + references store
│   │                           # MARKDOWN (post-conversion), not HTML.
│   ├── sections.py             # BODY_SECTION_NAMES constant +
│   │                           # ordering policy.
│   ├── html_to_md.py           # HTML → pandoc-markdown conversion;
│   │                           # uses markdownify with a tuned
│   │                           # config: <sup>N</sup> → ^N^,
│   │                           # <sub>...</sub> → ~...~,
│   │                           # <ol>/<li> → numbered list,
│   │                           # strip id="isPasted" + inline style.
│   ├── sort.py                 # by_poster_id / by_title /
│   │                           # by_first_author strategies.
│   ├── author_index.py         # build index (author → entry list);
│   │                           # locations rendered per format.
│   ├── figure_check.py         # Pillow-backed resolution probe.
│   ├── render_markdown.py      # emit canonical book.md + copy
│   │                           # figures to fig_assets/.
│   ├── render_via_pandoc.py    # subprocess wrapper around pandoc;
│   │                           # PDF path adds --pdf-engine=xelatex
│   │                           # + optional --template tufte-book
│   │                           # when --style tufte; DOCX path uses
│   │                           # pandoc's native writer. Strips
│   │                           # metadata for determinism (R6).
│   ├── provenance.py           # write provenance.json + capture
│   │                           # pandoc/xelatex versions via
│   │                           # subprocess --version.
│   └── cli.py                  # `ohbmcli book` dispatch + arg parse.
├── exceptions.py               # add BookBuildError (OhbmStageError
│                               # subtree).
└── cli.py                      # wire `book` subcommand into the
                                # existing dispatch.

src/ohbm2026/book/templates/
├── book.md.template            # top-level book.md skeleton (title,
│                               # date, abstract iteration loop,
│                               # author-index emission). Plain
│                               # f-string / Python composition —
│                               # NOT a templating-engine file. Lives
│                               # in src/ for code-locality; the
│                               # emitter loads it via importlib.resources.
├── header-includes.tex         # LaTeX preamble injected via
│                               # pandoc -H: \usepackage{makeidx},
│                               # \makeindex, \graphicspath, and
│                               # micro-typography fixes.
└── header-includes-tufte.tex   # tufte-book variant — sets ET-Book
                                # falls back to TeX Gyre if absent,
                                # ragged-right outer-margin.

tests/
├── fixtures/book/              # 4-6 synthetic abstracts + tiny
│   │                           # PNG figures (committed, < 100 KB
│   │                           # total — fixtures don't fall under
│   │                           # the "no committed data" rule).
│   ├── abstracts.json
│   ├── authors.json
│   ├── abstracts_withdrawn.json
│   └── assets/*.png
├── test_book_corpus.py         # filter logic, withdrawn exclusion.
├── test_book_html_to_md.py     # HTML → markdown conversion: <sup>
│                               # → ^...^, <ol> → 1. ..., inline
│                               # style stripped, unicode preserved.
├── test_book_sort.py           # three sort orders.
├── test_book_author_index.py   # every author present, location
│                               # aggregation, anchor-link spec.
├── test_book_figure_check.py   # resolution probe + DPI calculation.
├── test_book_no_ai_audit.py    # SC-006: no Stage-2 strings leak
│                               # into book.md.
├── test_book_markdown.py       # markdown bundle determinism (SC-007a),
│                               # figure copy-out, anchor stability.
├── test_book_render_pdf.py     # PDF via pandoc — skip if pandoc /
│                               # xelatex unavailable; assert page
│                               # count > 0, sampled figures hit
│                               # ≥ 300 DPI at display size.
└── test_book_render_docx.py    # DOCX via pandoc — skip if pandoc
                                # unavailable; assert file opens with
                                # python-docx and has PAGEREF fields
                                # in the index.

scripts/
└── run_build_book.py           # thin shim for ad-hoc dev runs.

pyproject.toml                  # new optional extra
                                # `[abstracts_book]`:
                                # markdownify + beautifulsoup4 +
                                # python-docx (test-only dep to
                                # introspect pandoc's docx output).
                                # Existing Pillow dep already covers
                                # the resolution probe.

README.md                       # +stage entry; +invocation example;
                                # +link to specs/011-abstracts-book/.
docs/abstracts-book-plan.md     # operator-facing summary that links
                                # to the spec dir.
```

**Structure Decision**: single Track-A pipeline package
(`src/ohbm2026/book/`) following the Stage 2 / Stage 6 conventions
— one module per concern, a thin orchestrator (`cli.py`), and a
single public entry point `ohbmcli book`. The pandoc shell-out
lives in one module (`render_via_pandoc.py`) so the system-dep
boundary is sharp and easy to mock in tests. The
`book/templates/` subdirectory holds the markdown skeleton + the
LaTeX header-includes that pandoc consumes via `-H` — these are
code-adjacent assets, not runtime data.

## Phase 0 — research

See `research.md`. Resolves seven decisions in light of the
2026-05-19 clarification (markdown is canonical; pandoc is the
renderer):

- **R1**: Corpus has no author-supplied figure captions — use
  `question_name` as the figure label. (Unchanged from prior
  research; restated for completeness.)
- **R2**: HTML → markdown conversion happens **once at corpus
  load**. The in-memory model carries markdown, not HTML. All
  three rendered formats consume the same markdown source.
- **R3**: Rendering pipeline — pandoc for both PDF (xelatex
  engine) and DOCX. Single command per format. No hand-written
  HTML→PDF or HTML→DOCX path.
- **R4**: Body-section selection list (the same six question_names
  + the `--include-section` flag). Unchanged.
- **R5**: Figure-resolution policy — Pillow probe; provenance
  logs `figures_below_resolution_threshold`; no silent upscale.
  Unchanged from prior research.
- **R6**: Determinism with pandoc — pandoc embeds timestamps in
  both PDF (`/CreationDate`, `/ModDate`) and DOCX
  (`docProps/core.xml`). Post-process with `pikepdf` (PDF) and
  `zipfile` (DOCX) to overwrite both to a fixed
  `D:19700101000000Z` / `1970-01-01T00:00:00Z`. Body content is
  thereby content-identical re-run to re-run.
- **R7**: Optional Tufte styling — selected via `--style tufte`
  (default `plain`). Implementation: pandoc's `-H` flag injects
  `header-includes-tufte.tex` which sets `\documentclass{tufte-book}`
  + ET-Book / TeX-Gyre fallback. The DOCX writer ignores the flag
  (Tufte is a print-typography concept).

## Phase 1 — design artefacts

- **data-model.md** — input shapes (Stage-1 corpus + authors
  lookup + asset directory), in-memory dataclasses (now
  markdown-bearing, not HTML-bearing), and output shapes
  (book.md skeleton, provenance.json schema, fig_assets layout).
- **contracts/cli.md** — `ohbmcli book` flags, inputs, outputs,
  exit codes, error-path table. Adds the `--style {plain,tufte}`
  flag and the pandoc / xelatex preflight check.
- **quickstart.md** — operator runbook: install the optional
  extra; install pandoc + Tectonic; run the command; verify
  provenance. Includes the two extra system-dep install steps the
  HTML-pipeline plan didn't have.

## Complexity Tracking

> No constitutional violations — table omitted.
