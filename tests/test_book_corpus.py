"""T011 — corpus loader filter + author resolution."""

from __future__ import annotations

import pathlib
import unittest

from ohbm2026.book.corpus import load_book
from ohbm2026.exceptions import BookBuildError

_FIX = pathlib.Path(__file__).parent / "fixtures" / "book"


def _load() -> "Book":
    from ohbm2026.book.model import Book

    return load_book(
        corpus_path=_FIX / "abstracts.json",
        authors_path=_FIX / "authors.json",
        withdrawn_path=_FIX / "abstracts_withdrawn.json",
        assets_root=_FIX / "assets",
    )


class TestCorpusFilter(unittest.TestCase):
    def test_filters_withdrawn_null_and_nonposter(self) -> None:
        book = _load()
        ids = {e.submission_id for e in book.entries}
        # Survivors: 0001-0005 (sub ids 9000001..9000005).
        self.assertEqual(
            ids, {9000001, 9000002, 9000003, 9000004, 9000005}
        )
        # Filtered out: withdrawn (9000099), null-poster (9000098),
        # non-Poster|Oral (9000097).
        self.assertNotIn(9000099, ids)
        self.assertNotIn(9000098, ids)
        self.assertNotIn(9000097, ids)

    def test_authors_joined_by_submission_id(self) -> None:
        book = _load()
        by_poster = {e.poster_id: e for e in book.entries}
        # 0001 has two authors in author_order.
        self.assertEqual(len(by_poster[1].authors), 2)
        self.assertEqual(by_poster[1].authors[0].last_name, "Smith")
        self.assertEqual(by_poster[1].authors[1].last_name, "Johnson")
        # 0004 has two authors — Quinn Lee + Maria Brown.
        a4 = by_poster[4].authors
        self.assertEqual({a.last_name for a in a4}, {"Lee", "Brown"})
        # 0003 has one author (Davis).
        self.assertEqual(by_poster[3].authors[0].last_name, "Davis")

    def test_state_key_is_12_hex_chars(self) -> None:
        book = _load()
        self.assertRegex(book.corpus_state_key, r"^[0-9a-f]{12}$")

    def test_missing_corpus_raises(self) -> None:
        with self.assertRaises(BookBuildError) as cm:
            load_book(
                corpus_path=_FIX / "_does_not_exist.json",
                authors_path=_FIX / "authors.json",
                withdrawn_path=_FIX / "abstracts_withdrawn.json",
                assets_root=_FIX / "assets",
            )
        self.assertIn("not found", str(cm.exception))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
