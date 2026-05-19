# Phase 0 — Research: Book of Abstracts

Seven decisions with Decision / Rationale / Alternatives entries.
Supersedes the prior HTML-canonical research (the 2026-05-19
clarification flipped the source-of-truth to markdown and named
pandoc as the renderer).

## R1 — No author-supplied figure captions in the corpus

**Discovery** (verified against `data/primary/abstracts.json`,
2026-05-19, corpus state-key `f0c51e80dc0e`):

- Each abstract's `figure_urls[]` carries only `{question_name,
  source_url}`. The only two `question_name` values in use across
  all 3,244 abstracts are `Results Figure` and `Methods Figure`.
- The `responses[]` array does NOT contain a sibling
  `Results Figure Caption` / `Methods Figure Caption` field. No
  caption text is collected by the Oxford submission form.
- The body sections (`Methods`, `Results`) describe the figures
  inline.

**Decision**: render each figure with its `question_name` as the
caption label (e.g. "Figure 1 — Methods Figure"). Do NOT
synthesise caption text from the body or any external source.

**Rationale**: honours the no-AI constraint (no LLM extraction of
captions from body text), surfaces the only field the corpus
actually provides, and matches the conference's own poster layout
convention.

**Alternatives considered**:
- *Extract captions from the surrounding body via heuristic*:
  rejected — even a deterministic regex would frequently grab the
  wrong sentence; the result would look authoritative but be
  unverified.
- *Leave figures unlabelled*: rejected — readers need to know
  which section a figure belongs to.

## R2 — HTML → markdown happens once, at corpus load

**Decision**: convert every `responses[].value` whose
`question_name` is in `BODY_SECTION_NAMES` from HTML to
pandoc-flavored markdown at the **point the in-memory model is
built**, not at render time. The `BookEntry.body_sections[].text`
field stores the markdown; the same applies to
`BookEntry.references.text`. This is the structural consequence
of the 2026-05-19 clarification — markdown is the canonical
intermediate, so the conversion must happen exactly once on the
input path.

**HTML → markdown rules** (encoded in `book/html_to_md.py`):

| HTML | pandoc-markdown |
|---|---|
| `<p>...</p>` | paragraph (blank-line separated) |
| `<br>` | hard line break (two trailing spaces) |
| `<sup>1,2</sup>` | `^1,2^` (pandoc superscript) |
| `<sub>...</sub>` | `~...~` (pandoc subscript) |
| `<strong>` / `<b>` | `**...**` |
| `<em>` / `<i>` | `*...*` |
| `<ol><li>...</li></ol>` | `1. ...` (numbered list) |
| `<ul><li>...</li></ul>` | `- ...` |
| `<a href="...">` | `[text](url)` |
| `id="isPasted"` / inline `style="..."` | dropped |
| `&nbsp;` / `&plusmn;` / `&micro;` | unicode (` `, `±`, `µ`) |
| HTML elements not in the table above | passed through as raw HTML islands (pandoc handles raw HTML in markdown) |

The two-trailing-spaces hard-break form is required because the
corpus uses `<br>` to denote intra-paragraph breaks (e.g. between
list-of-acknowledgements items).

**Library**: `markdownify` with a small wrapper that applies the
sup/sub transformation manually (markdownify doesn't ship a
sup/sub converter out of the box; the wrapper runs a BeautifulSoup
pre-pass that swaps `<sup>x</sup>` → `^x^` literally in the HTML
before markdownify converts the rest).

**Rationale**: doing the conversion once at the corpus boundary
keeps the markdown bundle authoritative and avoids HTML→MD→HTML
round-trips that would lose `<sup>` superscripts on the
math-and-citation-heavy science content. The pandoc-flavored
output renders correctly in pandoc's PDF (xelatex) and DOCX
writers; it also renders sensibly in plain CommonMark viewers
(GitHub, VSCode preview) — `^1,2^` shows as literal `^1,2^` but
the content is intact, and the user can choose to view the PDF
for the typographically-correct rendering.

**Alternatives considered**:
- *Keep raw HTML inline in the markdown*: rejected — defeats the
  "markdown is canonical" mandate; the operator opening `book.md`
  would see a lot of `<p>...<sup>...</sup></p>` noise.
- *Convert to GitHub-flavored markdown (no native sup/sub)*:
  rejected — citation superscripts are load-bearing in scientific
  abstracts.
- *Convert at render time per format*: rejected — that's the
  pre-clarification HTML-canonical design.

## R3 — Rendering pipeline: pandoc subprocess

**Decision**:
- **Markdown bundle**: hand-written emitter assembles `book.md`
  from the in-memory model + a top-level skeleton at
  `src/ohbm2026/book/templates/book.md.template`. Figures copied
  to a **flat** `fig_assets/` directory using the filename
  contract from `data-model.md § Layer 3`:
  `<submission_id>-<poster_id>-<type>[-<index>].<ext>` (e.g.
  `1196698-0042-methods.png`, `1196698-0042-results-1.png`,
  `1196698-0042-results-2.png`). The figure reference in
  `book.md` is then
  `![Figure N — Methods Figure](fig_assets/1196698-0042-methods.png){#fig-0042-methods}`
  — pandoc consumes the trailing `{#id}` syntax as a real
  identifier the LaTeX `makeindex` machinery can cross-reference.
- **PDF**: `subprocess.run(["pandoc", "book.md",
  "--from=markdown+pandoc_title_block+raw_tex+inline_code_attributes",
  "--to=pdf", "--pdf-engine=xelatex",
  "-H", "header-includes.tex",
  "--resource-path=<book_dir>",
  "--standalone", "--toc",
  "-o", "book.pdf"])`. The `-H` file injects
  `\usepackage{makeidx}`, `\makeindex` in the preamble, and the
  author-index emit fires from raw-LaTeX `\index{Lastname, F.}`
  markers the markdown emitter injects beside each abstract's
  author list. The index renders at the end via `\printindex`.
- **DOCX**: `subprocess.run(["pandoc", "book.md",
  "--from=markdown",
  "--to=docx",
  "--reference-doc=<reference.docx>",
  "-o", "book.docx"])`. The reference doc carries paragraph styles
  for `Heading 1`, body text, figure captions. pandoc emits
  bookmarks for headings; the author index in DOCX uses
  `[Lastname, F.](#abstract-0042)` markdown anchor links which
  pandoc translates into hyperlink cross-references. Page numbers
  in the docx index are NOT available (pandoc's docx writer
  doesn't emit PAGEREF field codes); the index links are
  clickable, and the spec acknowledges paginated locations in DOCX
  are best-effort — this is documented in the data-model.

**Why `\index{}` markers in the markdown source**: LaTeX's
`makeindex` needs index entries to be embedded inline at the
location each name appears. The cleanest way is for the markdown
emitter to add `\index{Lastname, Firstname}` raw-LaTeX strings
beside each author's display name; pandoc passes raw LaTeX through
when the input format enables `raw_tex`. The author index at the
back is then a single `\printindex` line at the bottom of the
markdown source. This produces a real, page-numbered, sorted
LaTeX index in the PDF output — no two-pass dance needed.

**Rationale**:
- pandoc is the industry-standard markdown-to-publishing tool;
  the user explicitly chose it (clarification 2026-05-19).
- Using `\index{}` + `\makeindex` is the simplest way to get a
  real page-numbered index in a pandoc-emitted PDF.
- DOCX gets clickable cross-refs instead of page numbers; this is
  a documented limitation acknowledged in the data-model.

**Alternatives considered**:
- *python-docx with manual PAGEREF field codes*: rejected per the
  clarification — DOCX must also derive from the same markdown
  source.
- *pandoc-docx + post-process XML to inject PAGEREF*: technically
  possible (we'd read the docx, walk `<w:hyperlink>` elements,
  rewrite them as `<w:fldSimple>` PAGEREF), but adds ~150 LOC of
  XML manipulation for marginal value when the markdown anchor
  links are already useful. Deferred to a future enhancement if
  the editor asks.
- *Two-pass LaTeX via `latexmk -xelatex`*: not needed — pandoc
  invokes xelatex once with the `-pdf-engine-opt=-interaction=nonstopmode`
  defaults; `makeindex` runs as part of the same pipeline when
  pandoc detects the `\makeindex` directive. (Verified on pandoc
  3.5 / Tectonic 0.15.)

## R4 — Body-section selection list

Same six question_names as before — `Introduction`, `Methods`,
`Results`, `Conclusion`, `Acknowledgement`, `References/Citations`
— with `--include-section <name>` as the forward-compatibility
escape hatch.

**Rationale**: editorial policy, not external schema. CA-007
applies to genuine external enumerations; the project chooses
which submitter responses are publication-worthy.

## R5 — Figure-resolution policy

Same as before — Pillow probe, log `figures_below_resolution_threshold`
in provenance, no silent upscale, no rejection. The
target-display-width is derived from the rendered LaTeX page
geometry (`6.5"` for plain `book` class; `4.21"` for `tufte-book`
in body text — because Tufte's body column is narrower, allowing
slightly smaller raster figures to still hit 300 DPI). The probe
uses the active style's body-width for the threshold computation.

## R6 — Determinism with pandoc

**Decision**: after pandoc emits the PDF / DOCX, post-process to
fix the timestamps to `1970-01-01T00:00:00Z`.

- **PDF post-process**: open with `pikepdf`; overwrite
  `/CreationDate` and `/ModDate` in the trailer info dict to
  `D:19700101000000Z`; save. Pikepdf preserves the body content
  byte-perfectly — only the trailer changes.
- **DOCX post-process**: open the `.docx` as a `zipfile.ZipFile`;
  rewrite `docProps/core.xml` to set
  `dcterms:created` and `dcterms:modified` to
  `1970-01-01T00:00:00Z`; re-zip with deterministic compression
  level + sorted entry order + zeroed mtimes on every member file.

**Pandoc internal determinism**: pandoc itself is deterministic
given the same input markdown — confirmed in upstream issue
discussions. Output drift between runs is purely from the
embedded timestamps stripped by R6.

**Escape hatch**: `--no-determinism-strip` disables the
post-process for debug runs (PDF and DOCX then carry the real
build timestamps in their metadata; the canonical run timestamp
remains in `provenance.json` either way).

**Rationale**: SC-007b asks for content-identical PDF / DOCX
re-runs. Pandoc + pikepdf + zipfile-rebuild is a well-known
reproducible-build pattern.

## R7 — Optional Tufte styling

**Decision**: add `--style {plain,tufte}` CLI flag (default
`plain`). Implementation differs only at the pandoc invocation:

| Flag value | Pandoc invocation difference |
|---|---|
| `plain` (default) | `-H header-includes.tex` (loads `book` class, makeidx, graphicx) |
| `tufte` | `-H header-includes-tufte.tex` (loads `tufte-book` class with `nobib,nofonts` options + ET-Book font with TeX-Gyre fallback + still `makeidx`/`graphicx`) |

The `tufte-book` class provides ET-Book serif body type, ragged-right
setting, generous outer margin (where future sidenote work could
land), section heading style without numbering, and Tufte's
hand-set rules around figures. Body content is unchanged — no
content transformation is applied for Tufte (no auto-conversion of
superscript citations to sidenotes; the user signalled "optional",
meaning typography only).

**Provenance**: the chosen style lands in `provenance.json.style`.

**Rationale**: respects the user's "optional styling" signal —
typography polish only, zero content rework. Operators choose
per-run.

**Alternatives considered**:
- *Always use `tufte-book`*: rejected — operators may want a
  plainer look for distribution to attendees; "optional" was the
  user's word.
- *Full Tufte sidenote conversion of every citation*: deferred —
  requires parsing the references block and matching every
  superscript numeral to its target reference entry, then emitting
  `\sidenote{...}` per occurrence. Substantial complexity for
  marginal aesthetic value; not in scope for v1.

## Pandoc + xelatex preflight (operational note)

`book/cli.py` runs a startup preflight when `--format` is
`pdf|docx|all`:

- `pandoc --version` must succeed (any format that touches pandoc).
- `xelatex --version` must succeed (PDF only).
- Versions captured for `provenance.json.pandoc_version` /
  `provenance.json.xelatex_version`.

If either is missing, exit with `BookBuildError` exit code 2 and
a one-line install hint pointing at `quickstart.md` step 2.

## SC-006 audit: how to verify "no AI-generated content"

Post-render audit (lives in `tests/test_book_no_ai_audit.py`,
CI gate; also runs at end of `ohbmcli book` as a soft check
whose result is logged in `provenance.json.no_ai_audit`):

- Open `book.md`.
- Assert it does NOT contain any ECO code identifier from
  `src/ohbm2026/data/eco_top_codes.json` (e.g. `ECO:0000352`).
- Assert it does NOT contain any Stage-2 cache-key prefix or known
  agent-tool name from `stage2_claims.py` (`verify_source_quote`,
  `lookup_eco_code`, `dedupe_check`).
- Assert it does NOT contain LLM-generated reference fields (only
  meaningful if a Stage-2 reference-resolution artefact exists on
  disk; when absent, the audit logs `checked: false, reason:
  no_stage2_reference_artefact` and moves on).

The book code never imports `stage2_*` modules; an import-graph
walk in the audit test enforces this statically.
