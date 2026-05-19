# Phase 1 — Data Model: Book of Abstracts

Three layers: (1) input shapes consumed from Stage-1 artefacts,
(2) in-memory model the renderer operates on (now
**markdown-bearing**, per R2), (3) output shapes the book emits.

## Layer 1 — Input shapes (read-only)

### `data/primary/abstracts.json`

```text
{
  "fetched_at": str,
  "event_ids": list[int],
  "abstract_count": int,
  "abstracts": [Abstract]
}

Abstract = {
  "id":           int,            # Oxford submission_id (joins authors)
  "poster_id":    str | None,     # "0503"; None for the test row
  "title":        str,
  "accepted_for": str,            # "Poster" | "Oral"
  "authors":      list[AuthorRef],
  "responses":    list[Response], # form fields, HTML for science content
  "figure_urls":  list[FigureUrl],
  "external_urls": list[str],
  "program_sessions": list,
  "local_assets": list[LocalAsset]
}

AuthorRef = {"author_order": int, "id": int}

Response = {
  "question_name": str,   # e.g. "Methods", "References/Citations"
  "value":         str    # HTML for scientific content
}

FigureUrl = {
  "question_name": str,   # "Methods Figure" | "Results Figure"
  "source_url":   str
}

LocalAsset = {
  "source_url":            str,
  "source_question_name":  str,
  "local_path":            str,
  "content_type":          str,
  "downloaded":            bool,
  "error":                 str | None
}
```

### `data/primary/authors.json`

```text
Author = {
  "id":               int,
  "first_name":       str,
  "middle_initial":   str | None,
  "last_name":        str,
  "title":            str | None,
  "degree":           str | None,
  "orcid_id":         str | None,
  "presenting":       bool,
  "submission_id":    int,
  "affiliations":     list[Affiliation]
}

Affiliation = {
  "id":                 int,
  "affiliation_order":  int,
  "institution":        str,
  "city":               str,
  "state":              str | None,
  "country":            str
}
```

### `data/primary/abstracts_withdrawn.json`

Same shape; the book consumes only `abstracts[].id`.

### `data/inputs/assets/`

Flat directory of figure files; referenced by absolute
`Abstract.local_assets[].local_path`.

## Layer 2 — In-memory model (markdown-bearing)

`@dataclass(frozen=True, slots=True)` under
`src/ohbm2026/book/model.py`. Constructed by `corpus.py` and
consumed by `render_markdown.py` (which is also the input to
`render_via_pandoc.py`).

```python
@dataclass(frozen=True, slots=True)
class AuthorAffiliation:
    institution: str
    city: str
    state: str | None
    country: str

@dataclass(frozen=True, slots=True)
class Author:
    submission_id: int
    author_order: int
    first_name: str
    middle_initial: str | None
    last_name: str
    affiliations: tuple[AuthorAffiliation, ...]
    sort_key_last_first: tuple[str, str]   # (last.casefold(),
                                           #  first.casefold())
    display_name: str                       # "First M. Last"
    latex_index_key: str                    # "Last, First M." —
                                            # the canonical form
                                            # used as the
                                            # \index{...} argument

@dataclass(frozen=True, slots=True)
class FigureBlock:
    question_name: str          # "Methods Figure" | "Results Figure"
    local_path: pathlib.Path    # the high-res original asset
    content_type: str
    pixel_width: int | None
    pixel_height: int | None
    error: str | None           # non-None → render the
                                # "figure unavailable" block (FR-008)

@dataclass(frozen=True, slots=True)
class BodySection:
    name: str                   # "Introduction" | "Methods" | ...
    markdown: str               # pandoc-flavored markdown
                                # (converted from HTML at corpus
                                # load — R2). Source-of-truth.

@dataclass(frozen=True, slots=True)
class ReferencesBlock:
    markdown: str               # pandoc-flavored markdown (typically
                                # a `1. ...` numbered list). Empty
                                # string if author didn't supply.

@dataclass(frozen=True, slots=True)
class BookEntry:
    submission_id: int          # Oxford id (provenance only; not rendered)
    poster_id: int              # int form for ordering; display
                                # zero-pads to 4 chars
    title: str                  # plain text (no HTML markers
                                # observed in corpus title field)
    accepted_for: str           # "Poster" | "Oral"
    authors: tuple[Author, ...]                       # in author_order
    body_sections: tuple[BodySection, ...]            # filtered + ordered
    figures: tuple[FigureBlock, ...]                  # in figure_urls order
    references: ReferencesBlock | None

@dataclass(frozen=True, slots=True)
class AuthorIndexEntry:
    display_name: str           # canonical rendered string
    latex_index_key: str        # the \index{...} argument form
    sort_key: tuple[str, str]
    poster_ids: tuple[int, ...] # sorted ascending — used by the
                                # markdown bundle (anchor links)
                                # and the DOCX render (hyperlinks).
                                # PDF index uses LaTeX \makeindex
                                # which reads embedded \index{...}
                                # markers, NOT this field.

@dataclass(frozen=True, slots=True)
class Book:
    sort_order: str             # "poster_id" | "title" | "first_author"
    format: str                 # "md" | "pdf" | "docx" | "all"
    style: str                  # "plain" | "tufte"
    entries: tuple[BookEntry, ...]
    author_index: tuple[AuthorIndexEntry, ...]
    corpus_state_key: str
```

### Construction rules (`corpus.py → Book`)

1. **Filter**:
   - Drop abstracts whose `id` ∈ withdrawn-id-set.
   - Drop abstracts whose `poster_id` is `None`.
   - Drop abstracts whose `accepted_for` ∉ `{"Poster", "Oral"}`.
2. **Author lookup**: `authors_by_submission_id: dict[int,
   list[Author]]` sorted by `author_order`. `latex_index_key`
   computed as `"{last_name}, {first_name}{ ' ' + middle_initial + '.' if middle_initial else ''}"`,
   stripping LaTeX-special characters (`#`, `$`, `%`, `&`, `_`, `{`, `}`)
   by backslash-escaping.
3. **HTML → markdown conversion** (per R2): every body section
   value + the references-block value is passed through
   `book/html_to_md.py::html_to_pandoc_md`. The conversion is
   pure function — same HTML in → same markdown out.
4. **Body sections**: walk `responses[]`, keep entries whose
   `question_name` ∈ `BODY_SECTION_NAMES` (plus any
   `--include-section` extensions). Sort by the canonical
   `BODY_SECTION_NAMES` order, NOT by corpus order.
5. **Figures**: for each `figure_urls[]` entry, look up the
   matching `local_assets[]` entry. If `downloaded == False`
   OR `local_path` doesn't exist on disk OR Pillow raises when
   reading dimensions, build the FigureBlock with `error` set
   and render the "unavailable" block at that position.
6. **References**: pick the `References/Citations` response;
   convert HTML → markdown via the same path as body sections.
7. **Sort**: stable `sorted(..., key=...)`:
   - `poster_id`: `key=lambda e: e.poster_id`
   - `title`: `key=lambda e: (e.title.casefold(), e.poster_id)`
   - `first_author`: `key=lambda e: (e.authors[0].sort_key_last_first
     + (e.title.casefold(),))`
8. **Author index**: walk all (entry, author) pairs; aggregate by
   `(display_name, sort_key_last_first)` — exact-string match per
   the spec's "no canonicalisation in v1" policy.

## Layer 3 — Output shapes

### Markdown bundle (`--format md|all`)

```text
data/outputs/book/book__<state-key>/
├── book.md                                # always — canonical
├── fig_assets/                            # always emitted; ships
│   ├── 1196698-0503-methods.png           # alongside book.md
│   ├── 1196698-0503-results.png           # regardless of --format
│   ├── 1196700-0504-results.png
│   ├── 1196701-0505-results-1.png         # index suffix only
│   ├── 1196701-0505-results-2.png         # when an abstract has
│   ...                                    # >1 figure of the type
└── provenance.json
```

**Figure filename pattern** (the contract): each figure is named
`<submission_id>-<poster_id>-<type>[-<index>].<ext>` where:

- `<submission_id>` is the Oxford `Abstract.id` (numeric).
- `<poster_id>` is the four-digit zero-padded poster_id (e.g. `0503`).
- `<type>` is derived from `FigureUrl.question_name` by stripping
  the trailing " Figure" suffix and lower-casing the remainder
  (`Methods Figure` → `methods`, `Results Figure` → `results`).
  For any future question_name the same rule applies; non-word
  characters are dash-replaced.
- `<index>` is a 1-based integer suffix appended **only** when the
  same abstract supplies more than one figure of the same `<type>`;
  a single-figure-of-type carries no index. Ordering within a type
  follows `figure_urls[]` order in the corpus.
- `<ext>` is taken from `LocalAsset.content_type` (`image/png` →
  `png`, `image/jpeg` → `jpg`).

The directory is **flat** — no per-abstract subdirectories.

`book.md` structure — verbatim sketch:

```markdown
---
title: "OHBM 2026 — Book of Abstracts"
date: "2026-05-19"
sort: "poster_id"
---

\makeindex

# OHBM 2026 — Book of Abstracts

> Built from corpus state-key `f0c51e80dc0e`.
> Sorted by `poster_id`. 3,243 entries.

\clearpage

## Abstract 0001 — <title> {#abstract-0001}

**Authors**: First M. Last\index{Last, First M.}, F2 L2\index{L2, F2}
(<institution>, <city>, <country>; <institution2>, ...)

### Introduction
<markdown converted from HTML — superscripts as ^N^>

### Methods
...

![Figure 1 — Methods Figure](fig_assets/1196698-0001-methods.png){#fig-0001-methods}

### Results
...

![Figure 2 — Results Figure](fig_assets/1196698-0001-results.png){#fig-0001-results}

### Conclusion
...

### Acknowledgement
...

### References
1. ...
2. ...

\clearpage

## Abstract 0002 — <title> {#abstract-0002}
...

# Author Index

\printindex

<!-- For the markdown-bundle reader, an anchor-link version of the
     index follows so the .md is useful standalone (the LaTeX
     \printindex above is consumed by pandoc → PDF). -->

<details>
<summary>Author Index (anchor links)</summary>

- Aaronson, Alex → [0042](#abstract-0042), [0581](#abstract-0581)
- ...

</details>
```

The `\makeindex` / `\printindex` directives are raw LaTeX that
**pandoc passes through** when emitting PDF (input format
`markdown+raw_tex`). When the same `book.md` is consumed by a
plain-markdown reader (GitHub, VSCode) the LaTeX lines render as
literal text in a paragraph — acceptable degradation. The
`<details>` anchor-link version below is the human-readable index
for the md-bundle audience.

When emitted via pandoc → DOCX, raw-LaTeX is dropped (pandoc
gracefully ignores LaTeX it can't translate); the anchor-link
index inside `<details>` survives and renders as a collapsible
section.

### PDF (`--format pdf|all`)

`book.pdf` — single A4-portrait PDF with:

- pandoc-generated title page from the YAML metadata block at top
  of `book.md`.
- One section per abstract, headings styled by the `book` (plain)
  or `tufte-book` (tufte) document class.
- Figures embedded at native resolution; pandoc's `\includegraphics`
  invocation sets `width=\textwidth` so figures fill the body
  column.
- LaTeX-generated, page-numbered author index at the end via
  `\printindex` consuming the `\index{...}` markers the markdown
  emitter placed beside each author.
- Stripped `/CreationDate` + `/ModDate` for determinism (R6).
- Optional `tufte-book` typography when `--style tufte` was
  selected.

### DOCX (`--format docx|all`)

`book.docx` with:

- pandoc-generated styles applied (Heading 1 per abstract, body
  text, figure captions).
- Embedded figures via pandoc's docx-image emission.
- Heading-level bookmarks for every abstract anchor.
- Author index in the back: the `<details>` anchor-link block
  becomes a regular collapsible content section; each
  `[Lastname, F.](#abstract-NNNN)` markdown link becomes a real
  Word hyperlink cross-reference (clickable, navigates within
  the document).
- Page numbers in the DOCX index are NOT available (pandoc's
  docx writer doesn't emit PAGEREF field codes — see R3
  alternatives). The data-model and the contracts/cli.md note
  this as a documented limitation; PDF is the format for true
  paginated index.
- Fixed `docProps/core.xml` `dcterms:created` / `dcterms:modified`
  for determinism (R6).

### `provenance.json`

```json
{
  "version": 1,
  "corpus_state_key": "f0c51e80dc0e",
  "corpus_path": "data/primary/abstracts.json",
  "authors_path": "data/primary/authors.json",
  "withdrawn_path": "data/primary/abstracts_withdrawn.json",
  "sort_order": "poster_id",
  "format": "pdf",
  "style": "plain",
  "code_revision_short": "abc1234",
  "code_revision_full":  "abc1234abc1234abc1234abc1234abc1234abc1",
  "command_line": "ohbmcli book --format pdf --sort poster_id",
  "built_at": "2026-05-19T13:42:11Z",
  "abstract_count": 3243,
  "figure_count": 5781,
  "figures_below_resolution_threshold": [
    {"poster_id": 17, "figure_index": 0, "effective_dpi": 142.3}
  ],
  "pandoc_version": "3.5",
  "xelatex_version": "XeTeX 3.141592653-2.6-0.999996",
  "no_ai_audit": {
    "checked": true,
    "matches_found": 0,
    "checked_against": ["eco_top_codes", "stage2_tool_names"]
  }
}
```

`xelatex_version` is `null` when format ∈ `{md, docx}`.

## State transitions

No state machine — one-shot batch render.

## Validation rules

`corpus.py::load_book` raises typed `exceptions.BookBuildError`:

- `corpus_path` missing → exits 2 with "corpus path X not found;
  run `ohbmcli fetch-abstracts` first".
- `authors.json` missing or empty → exits 2.
- Empty filtered entry set → exits 2.
- Output root not writable → exits 2 **before** any expensive
  composition / pandoc work.
- Pandoc missing on `PATH` when `--format pdf|docx|all` → exits 2
  with install hint from the quickstart.
- xelatex missing on `PATH` when `--format pdf|all` → exits 2.
- Pandoc returns non-zero → exits 2; the BookBuildError carries
  pandoc's stderr verbatim.
- Single missing figure asset → FigureBlock.error set; renders
  visibly (FR-008). No exit.
- Single figure below 300 DPI → logged in
  `provenance.figures_below_resolution_threshold`. No exit.
- Body section absent for an abstract → heading silently skipped.
- `--include-section` names an unseen question_name → WARN once,
  continue.
- Pillow can't read figure → FigureBlock.error set; renders
  visibly.
