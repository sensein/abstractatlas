"""Sort strategies for the Book of Abstracts.

US1 ships `by_poster_id` (the default + MVP). US2 will add
`by_title` and `by_first_author`. The Protocol below pins the
contract so future strategies plug in without churning the call site.
"""

from __future__ import annotations

from typing import Callable, Protocol

from ohbm2026.book.model import BookEntry


class SortStrategy(Protocol):
    def __call__(self, entries: tuple[BookEntry, ...]) -> tuple[BookEntry, ...]: ...


def by_poster_id(entries: tuple[BookEntry, ...]) -> tuple[BookEntry, ...]:
    """Numeric ascending by `poster_id`. Stable."""
    return tuple(sorted(entries, key=lambda e: e.poster_id))


# Forward declarations — implemented in US2 (T030).
def by_title(entries: tuple[BookEntry, ...]) -> tuple[BookEntry, ...]:
    """Case-insensitive lexicographic by `title`, poster_id tie-break."""
    return tuple(sorted(entries, key=lambda e: (e.title.casefold(), e.poster_id)))


def by_first_author(entries: tuple[BookEntry, ...]) -> tuple[BookEntry, ...]:
    """First-author surname (case-insensitive), then given name, then title."""

    def _key(e: BookEntry) -> tuple[str, str, str]:
        if e.authors:
            a0 = e.authors[0]
            return (
                a0.last_name.casefold(),
                a0.first_name.casefold(),
                e.title.casefold(),
            )
        return ("", "", e.title.casefold())

    return tuple(sorted(entries, key=_key))


STRATEGIES: dict[str, Callable[[tuple[BookEntry, ...]], tuple[BookEntry, ...]]] = {
    "poster_id": by_poster_id,
    "title": by_title,
    "first_author": by_first_author,
}
