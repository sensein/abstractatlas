"""Stage 11 — Book of Abstracts exporter.

Composes a publication-quality book of every accepted abstract from
Stage-1 corpus artefacts (`data/primary/abstracts.json` +
`authors.json` + `data/inputs/assets/`). Markdown is the canonical
intermediate; PDF and DOCX are derived via pandoc.

Spec: `specs/011-abstracts-book/`.
"""

from abstractatlas.book.model import (
    Author,
    AuthorAffiliation,
    AuthorIndexEntry,
    BodySection,
    Book,
    BookEntry,
    FigureBlock,
    ReferencesBlock,
)

__all__ = [
    "Author",
    "AuthorAffiliation",
    "AuthorIndexEntry",
    "BodySection",
    "Book",
    "BookEntry",
    "FigureBlock",
    "ReferencesBlock",
]
