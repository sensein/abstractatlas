# Feature Specification: Book of Abstracts

**Feature Branch**: `011-abstracts-book`
**Created**: 2026-05-19
**Status**: Draft
**Input**: User description: "need to create a book of abstracts including figures and figure captions, no ai generated content, and perhaps proper references. this script should allow generating the book sorted by title, poster id, first author's last name, and should contain an author index with pages at the end. exports can be as md+fig_assets, pdf, docx. figures should have reasonable resolution for publication."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Canonical printable book in poster-id order (Priority: P1)

A program-committee member needs a single, citable, publication-quality
book that contains every accepted abstract of the conference — title,
authors with affiliations, full abstract text, every figure with its
caption, and any references the author supplied — laid out in the same
order the posters appear on the conference floor (by `poster_id`). They
run one command and get a PDF they can hand to the printer or upload to
an archive. None of the abstract content has been touched by an LLM:
captions are the authors' captions, references are the authors'
references, and the abstract text is exactly what authors submitted.

**Why this priority**: This is the organizer's primary deliverable —
a permanent, citable record of the conference that goes to attendees
and to the archive. Without it, this whole feature has no value.

**Independent Test**: Run the book generator targeting the current
accepted corpus with default sort (poster_id) and PDF output. Open the
resulting PDF; verify (a) the count of abstract entries matches the
accepted count from `data/primary/abstracts.json`, (b) at least three
randomly-sampled entries show the correct title, author list,
abstract text, embedded figures with the author-supplied captions,
and the author-supplied references block, and (c) the author index at
the end lists every distinct author with the page numbers their
abstracts appear on.

**Acceptance Scenarios**:

1. **Given** an accepted-abstract corpus with N entries, **When** the
   generator runs in poster-id order targeting PDF, **Then** the
   resulting PDF contains exactly N abstract entries ordered by
   ascending poster_id, each with title, authors+affiliations, full
   text, all author-supplied figures with their author-supplied
   captions, the author-supplied references block, and an author
   index at the back listing every distinct author with their page
   numbers.
2. **Given** an abstract whose figure asset is missing or unreadable,
   **When** the generator runs, **Then** the entry renders a clearly
   labelled "figure unavailable" block (with the reason) in place of
   the figure, rather than silently dropping it.
3. **Given** a withdrawn abstract present in
   `data/primary/abstracts_withdrawn.json`, **When** the generator
   runs, **Then** the withdrawn entry is excluded from both the body
   of the book and the author index.

---

### User Story 2 - Alternate sort orders (Priority: P2)

The same committee member needs the same book contents in two other
orders: alphabetised by title (so reviewers searching for a known
abstract can find it without knowing the poster_id) and alphabetised
by first-author surname (so attendees looking up a colleague's
contribution can scan the book linearly). They pass a `--sort` flag
and re-export.

**Why this priority**: Different consumers want different orderings;
once the P1 pipeline exists, adding sort permutations is small but
material to usability. Not blocking the MVP.

**Independent Test**: Run the generator three times with
`--sort poster_id`, `--sort title`, `--sort first_author`. Verify
each book contains the same set of abstracts and the same author
index, and verify the abstract ordering matches the requested sort
in each output.

**Acceptance Scenarios**:

1. **Given** the same input corpus, **When** the generator runs with
   `--sort title`, **Then** the abstracts appear in case-insensitive
   ascending lexicographic order of their titles.
2. **Given** the same input corpus, **When** the generator runs with
   `--sort first_author`, **Then** the abstracts appear in
   case-insensitive ascending lexicographic order of the first
   author's surname (family name); ties break on first-author given
   name then on title.

---

### User Story 3 - Multi-format export (markdown + figure assets, DOCX) (Priority: P3)

An editor wants to copy-edit the book before publishing, and a
downstream archiving pipeline wants a machine-readable source. The
same generator emits (a) a markdown bundle — a single `book.md` plus
a sibling `fig_assets/` directory with the high-resolution figure
files referenced by relative paths — and (b) a DOCX export the editor
can open in Word.

**Why this priority**: Useful for editorial review and archival but
not strictly needed for the printable PDF deliverable. Builds on the
same content pipeline as P1.

**Independent Test**: Run the generator with `--format md`, then
`--format docx`. Verify the markdown bundle's `book.md` references
figures via the relative
`fig_assets/<submission_id>-<poster_id>-<type>[-<index>].<ext>`
paths defined in FR-006, that those files exist at publication
resolution, and that an abstract with two figures of the same
type has both files present with the `-1` / `-2` index suffix;
verify the DOCX opens in Word and shows embedded figures with
captions and a working author index.

**Acceptance Scenarios**:

1. **Given** the corpus, **When** the generator runs with
   `--format md`, **Then** the output is a self-contained directory
   containing one `book.md` and one `fig_assets/` directory; every
   figure reference in `book.md` resolves to a file in `fig_assets/`
   and every file in `fig_assets/` is referenced from `book.md`.
2. **Given** the corpus, **When** the generator runs with
   `--format docx`, **Then** the resulting `.docx` opens in a
   standard word processor, every abstract entry renders with its
   embedded figures and captions, and the author index at the back
   uses clickable anchor cross-references that navigate to each
   abstract section.

---

## Clarifications

### Session 2026-05-19

- Q: Markdown → PDF/DOCX rendering pipeline → A: pandoc + LaTeX, with an optional `tufte-book` document class for PDF styling. Markdown is the canonical intermediate; PDF and DOCX both derive from the same `.md` source via pandoc (no hand-written HTML→PDF or HTML→DOCX renderer path).

### Edge Cases

- **Withdrawn abstracts**: excluded from both the body and the author
  index. Discovery is via `data/primary/abstracts_withdrawn.json`.
- **Abstract with no figures**: renders as a text-only entry (no
  empty figure block, no placeholder).
- **Missing or unreadable figure asset**: renders a "figure
  unavailable: <reason>" block at the figure's position so the
  reader can see something was meant to be there. Per CA-006 — fail
  loudly, no silent skip.
- **Author appearing on multiple abstracts**: the author index
  aggregates page numbers, listed in ascending order.
- **Author name variants** (e.g. "J. Smith" vs "Jane Smith" vs
  "Smith, Jane"): the author index treats names as the exact strings
  the corpus provides — no canonicalisation in v1. A future
  enhancement may collapse variants, but that requires a curated
  alias map which is out of scope for this feature.
- **Special characters in titles / author names** (unicode, ligatures,
  LaTeX-style markup): pass through verbatim from the corpus into the
  rendered output; the renderer must handle UTF-8.
- **Empty body sections**: if an author left, say, "Methods" blank in
  the source, the section header is omitted (no empty heading).
- **Markdown-format author index**: page numbers are a render-time
  concept; for the markdown bundle the index uses linkable anchors
  (`[Title](#abstract-<poster_id>)`) instead of page numbers, since
  there is no fixed pagination.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The generator MUST read the accepted-abstract corpus
  from `data/primary/abstracts.json` and exclude every entry whose
  `submission_id` appears in `data/primary/abstracts_withdrawn.json`.

- **FR-002**: The book content MUST contain only author-supplied
  fields from the corpus. The generator MUST NOT include any
  AI/LLM-generated content — specifically, Stage-2 figure
  interpretations, extracted claims, ECO-code annotations,
  LLM-resolved reference metadata (DOI lookups, OpenAlex titles),
  and any other Stage-2 enrichment outputs are excluded.

- **FR-003**: Each abstract entry MUST include: title, ordered
  author list with each author's affiliations, the full body text
  preserving the introduction / methods / results / conclusion
  section structure as the author submitted it, every figure with
  its author-supplied caption, and the author-supplied references
  block rendered verbatim.

- **FR-004**: The generator MUST support three sort orders selectable
  per run via a `--sort` flag:
  - `poster_id` — numeric ascending (default).
  - `title` — case-insensitive lexicographic ascending.
  - `first_author` — case-insensitive lexicographic ascending on the
    first author's surname; ties break on first-author given name,
    then on title.

- **FR-005**: The generator MUST emit an author index at the end of
  the book listing every distinct author and the locations of every
  abstract they appear on. For the PDF the locations are page
  numbers (driven by LaTeX `\makeindex`). For DOCX and the markdown
  bundle the locations are clickable anchor cross-references that
  navigate to each abstract section — paginated DOCX would require
  post-process OOXML `PAGEREF` field-code injection, which is
  deferred to a future enhancement (plan.md research § R3
  alternatives).

- **FR-006**: The generator MUST support three export formats
  selectable per run via a `--format` flag:
  - `md` — a directory containing `book.md` and a sibling
    `fig_assets/` directory with the original high-resolution figure
    files. The directory is **flat**; each file is named
    `<submission_id>-<poster_id>-<type>[-<index>].<ext>` where
    `<type>` is the figure question_name with the trailing
    " Figure" stripped and lower-cased (e.g. `methods`, `results`),
    and `<index>` (1-based) is appended **only** when the same
    abstract supplies more than one figure of that type.
    `book.md` references figures via the corresponding relative
    `fig_assets/<filename>` paths.
  - `pdf` — a single PDF file with embedded figures and a
    page-numbered author index.
  - `docx` — a single DOCX file with embedded figures and a
    page-numbered author index.

- **FR-006a**: The markdown bundle is the **canonical intermediate
  representation**. PDF and DOCX outputs MUST be derived from the
  same `book.md` source via pandoc (PDF through xelatex; DOCX via
  pandoc's native docx writer). No format renders directly from the
  in-memory HTML / object model — every export path passes through
  the markdown layer first. The HTML-fragment values from the
  corpus (body sections, references block) are converted to
  pandoc-flavored markdown once, at corpus load.

- **FR-006b**: The PDF rendering MAY apply the LaTeX `tufte-book`
  document class for typography and margin styling (sidenote-style
  reference column, ET-Book-family serif body, ragged-right setting).
  This is an optional polish step controlled by a CLI flag
  (`--style {plain,tufte}`, default `plain`); operators choose
  whether to enable it per run. The DOCX export ignores this flag.

- **FR-007**: Figures in PDF and DOCX outputs MUST embed at a
  resolution suitable for print publication — sourced from the
  full-resolution original figure asset (not the Stage-2
  JPEG-q85@1024px compressed thumbnail) and rendered at a minimum
  effective resolution of 300 DPI at the figure's display size.

- **FR-008**: When a figure asset is missing or unreadable, the
  entry MUST render a clearly labelled "figure unavailable:
  <reason>" block rather than silently omitting it (CA-006).

- **FR-009**: The generator MUST be a command-line entry point
  invoked through `ohbmcli` (canonical) or a standalone script under
  `scripts/`. Inputs MUST be discovered from the canonical artefact
  paths (`data/primary/abstracts.json`,
  `data/primary/abstracts_withdrawn.json`, and the figure-asset
  directory); outputs MUST land under a gitignored output root
  (defaulting to `data/outputs/book/`).

- **FR-010**: Every produced book MUST ship with a machine-readable
  provenance file co-located with the output that records: corpus
  state-key, sort order, export format, code revision (short + full
  SHA), command line, build timestamp, and the count of included
  abstracts. No absolute or user-home paths (CA-008).

- **FR-011**: The README's pipeline-stage listing and the project
  charter (`docs/reproducibility-vision.md`) MUST be updated in the
  same change so the new book-export step is discoverable.

### Key Entities *(include if feature involves data)*

- **Book**: the unified document. Has a sort order, an export
  format, a list of `BookEntry` rows in that sort order, and one
  `AuthorIndex`.
- **BookEntry**: one abstract entry. Composed of title, ordered
  list of `Author`, full body text (with section structure), ordered
  list of `Figure`, and a `ReferencesBlock`.
- **Author**: name (as the corpus supplies it), list of
  affiliations.
- **Figure**: high-resolution image bytes (sourced from the figure
  asset directory, not the Stage-2 compressed copy), the
  author-supplied caption, and a stable position within its entry.
- **ReferencesBlock**: the author-supplied references rendered
  verbatim — the markdown text the author submitted; this is **not**
  the Stage-2 LLM-parsed reference list.
- **AuthorIndex**: a sorted list of `AuthorIndexEntry`.
- **AuthorIndexEntry**: an author name and the list of locations
  (page numbers for PDF/DOCX, anchor links for the markdown bundle)
  at which their abstracts appear, in ascending order.

### Constitution Alignment *(mandatory)*

- **CA-001**: All Python execution for this feature MUST use the
  repository-local `.venv/bin/python` interpreter or `uv` targeting
  that interpreter.
- **CA-002**: The plan and tasks documents MUST identify the unit
  and integration tests that are added (or named existing tests
  that are tightened) before the behaviour-changing code lands —
  notably, tests asserting (a) absence of Stage-2 enrichment
  content in the book, (b) correct sort-order for each `--sort`
  value, (c) figure resolution ≥ 300 DPI at display size in the
  PDF, and (d) every accepted abstract appears in the author index.
- **CA-003**: Adding the book-export step changes the canonical
  pipeline surface; the README's pipeline-stage list and
  `docs/reproducibility-vision.md` MUST be updated in the same
  change (FR-011).
- **CA-004**: This feature uses no external credentials (it reads
  local artefacts only); no env vars or secret boundaries apply.
- **CA-005**: Generated books, intermediate figure copies, and
  provenance files MUST land under a gitignored output root
  (default `data/outputs/book/`).
- **CA-006**: Failures (missing figure assets, malformed corpus
  entries, unwritable output paths) MUST be surfaced as explicit
  errors or "unavailable" labelled blocks in the output — never as
  silent skips.
- **CA-007**: External-schema dependencies (the Oxford GraphQL
  field set, vendor enumerations, asset-directory layout) MUST be
  read at runtime from the corpus envelope, not hardcoded — a
  schema-shape mismatch surfaces as a precise error, not a silent
  skip. Note: the editorial choice of which submitter responses
  count as publishable "body sections" (Introduction, Methods,
  Results, Conclusion, Acknowledgement, References/Citations) is a
  project-policy decision, not external-schema state, and lives as
  `BODY_SECTION_NAMES` in `src/ohbm2026/book/sections.py` with
  `--include-section <name>` as the forward-compatibility escape
  hatch.
- **CA-008**: Every produced book MUST ship with a machine-readable
  provenance file (named in FR-010) that lives next to the output
  artefact and contains no absolute or user-home paths.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An organizer can produce a publication-quality PDF
  containing every accepted abstract from a single command in under
  **15 minutes** on a typical laptop (~3,000 abstracts including
  high-resolution figures). The 10-minute mark is the design
  target; the 15-minute ceiling absorbs LaTeX-package-fetch latency
  on first run with Tectonic and pandoc-vs-xelatex variance across
  machines. T041 captures the actual wall time in
  `provenance.json.built_at` minus run start.
- **SC-002**: 100% of accepted, non-withdrawn abstracts in
  `data/primary/abstracts.json` appear exactly once in the produced
  book.
- **SC-003**: Every author who appears on at least one accepted
  abstract is listed in the author index, with at least one
  location reference (page number for PDF/DOCX, anchor link for
  markdown).
- **SC-004**: For 20 randomly-sampled figures, 100% render at an
  effective resolution of ≥ 300 DPI when measured at their display
  size in the PDF output.
- **SC-005**: For each of the three `--sort` values, the abstract
  rows in the produced book are in the asserted order (verifiable
  by inspecting the output and comparing to the corpus).
- **SC-006**: The book contains zero LLM-generated content — a
  string-match audit of the output against the Stage-2 enrichment
  artefacts (figure interpretations, claims, LLM-resolved reference
  titles) returns no hits.
- **SC-007**: Re-running the generator with the same inputs and
  flags produces (a) byte-identical markdown bundles and (b)
  content-identical PDF/DOCX bodies — i.e. the same abstracts in
  the same order with the same figures; format-imposed metadata
  like generation timestamp may differ.

## Assumptions

- The accepted-abstract corpus at `data/primary/abstracts.json` is
  the canonical source and contains, per abstract, the title,
  ordered author list with affiliations, body text with section
  structure, figure metadata (including the author-supplied
  caption), and an author-supplied references block. If any of
  these fields is in fact missing from the corpus and not
  recoverable from another canonical artefact, that becomes a hard
  failure surfaced before the book renders (CA-006).
- High-resolution figure assets are available locally at the
  paths the corpus records (the Stage-1 fetch + refresh-assets
  workflow already maintains this); the Stage-2 JPEG-q85@1024px
  thumbnails are explicitly NOT used for book figures.
- The committee runs the generator after Stage 1 (fetch +
  refresh-assets) completes for a given snapshot; Stage 2
  enrichment is **not** a prerequisite (the book uses no Stage-2
  outputs).
- "No AI-generated content" applies to the book's **content**: no
  LLM-derived text or interpretation reaches the reader. The
  generator itself is a deterministic compositor — it does not
  invoke any LLM at runtime.
- Author-name canonicalisation across variants is out of scope for
  v1; the index uses the exact strings the corpus provides.
- The markdown bundle is the source-of-truth representation for
  archival and re-rendering; PDF and DOCX are convenience exports
  derived from it via pandoc (FR-006a). Operators MUST have
  `pandoc` and a LaTeX distribution (TeX Live or Tectonic)
  available on `PATH` to produce PDF; DOCX needs only `pandoc`.
  Both system deps are documented in the quickstart.
