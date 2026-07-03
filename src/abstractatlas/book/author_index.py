"""Build the author index from the post-sort BookEntry tuple.

Aggregates by (display_name, sort_key_last_first) — exact-string
match (no canonicalisation in v1 per the spec's Assumptions
section). Each `AuthorIndexEntry.poster_ids` is the ascending sorted
tuple of poster_ids where the author appears.
"""

from __future__ import annotations

from abstractatlas.book.model import AuthorIndexEntry, BookEntry


def build_author_index(
    entries: tuple[BookEntry, ...],
) -> tuple[AuthorIndexEntry, ...]:
    """Return a sorted tuple of one `AuthorIndexEntry` per distinct author.

    Sort key: `(last_name.casefold(), first_name.casefold())`. Ties
    on those break on the latex_index_key (which is more specific
    because it folds in the middle initial). Stable for deterministic
    output.
    """
    # Aggregate keyed by `display_name` (exact string match — no
    # canonicalisation in v1 per the spec's Assumptions section).
    # First-seen wins for latex_index_key + sort_key when the same
    # display name appears with variant middle initials.
    bucket: dict[str, dict] = {}
    for entry in entries:
        for author in entry.authors:
            slot = bucket.setdefault(
                author.display_name,
                {
                    "display_name": author.display_name,
                    "latex_index_key": author.latex_index_key,
                    "sort_key": author.sort_key_last_first,
                    "poster_ids": set(),
                },
            )
            slot["poster_ids"].add(entry.poster_id)

    rows = [
        AuthorIndexEntry(
            display_name=slot["display_name"],
            latex_index_key=slot["latex_index_key"],
            sort_key=slot["sort_key"],
            poster_ids=tuple(sorted(slot["poster_ids"])),
        )
        for slot in bucket.values()
    ]
    rows.sort(key=lambda r: (r.sort_key, r.latex_index_key))
    return tuple(rows)
