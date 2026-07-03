"""T015 — author-index aggregation (FR-005 / SC-003)."""

from __future__ import annotations

import pathlib
import unittest

from abstractatlas.book.corpus import load_book

_FIX = pathlib.Path(__file__).parent / "fixtures" / "book"


def _book():
    return load_book(
        corpus_path=_FIX / "abstracts.json",
        authors_path=_FIX / "authors.json",
        withdrawn_path=_FIX / "abstracts_withdrawn.json",
        assets_root=_FIX / "assets",
    )


class TestAuthorIndex(unittest.TestCase):
    def setUp(self) -> None:
        try:
            from abstractatlas.book.author_index import build_author_index
        except ImportError:
            self.skipTest("author_index not yet implemented")
        self.build = build_author_index
        self.book = _book()
        self.index = self.build(self.book.entries)

    def test_every_distinct_author_present(self) -> None:
        expected_displays = {
            "Jane A. Smith",
            "Karl Johnson",
            "Maria B. Brown",
            "Paul Davis",
            "Quinn Lee",
            "Ravi Wilson",
        }
        got = {e.display_name for e in self.index}
        self.assertEqual(got, expected_displays)

    def test_shared_author_lists_both_posters(self) -> None:
        brown = next(e for e in self.index if e.display_name == "Maria B. Brown")
        # Brown is on poster 0002 (sub 9000002) and 0004 (sub 9000004).
        self.assertEqual(brown.poster_ids, (2, 4))

    def test_poster_ids_sorted_ascending(self) -> None:
        for entry in self.index:
            self.assertEqual(
                list(entry.poster_ids),
                sorted(entry.poster_ids),
                msg=f"{entry.display_name}: poster_ids not sorted",
            )

    def test_index_sorted_by_last_then_first(self) -> None:
        keys = [e.sort_key for e in self.index]
        self.assertEqual(keys, sorted(keys))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
