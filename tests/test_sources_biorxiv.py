"""Behavioral tests for `src/ohbm2026/sources/biorxiv.py`.

Arc A of the multi-source foundation (per
`specs/027-multi-source-foundation/`). Tests are written first per
Principle IV; they MUST fail before `ohbm2026.sources.biorxiv` exists.

The bioRxiv source is exercised entirely OFFLINE by injecting a fake
page-fetcher (Principle I — no network in the suite; Principle VII —
field presence is discovered from the payload and mismatches surface
as `SourceNormalizationError`, never silent skips).

Covers, per contracts/abstract-source.md:

  - `normalize`: maps a real-shaped bioRxiv detail record into the
    canonical `AbstractRecord` (doi→native_id, semicolon author list,
    year from date, sections, opaque extras, provenance digest).
  - loud failure when a required field (doi / title) is missing.
  - `records`: cursor pagination over the injected fetcher, composing
    `fetch_raw` + `normalize` and satisfying the `AbstractSource`
    Protocol.
"""

from __future__ import annotations

import unittest

from ohbm2026.sources.base import AbstractSource, SourceNormalizationError
from ohbm2026.sources.biorxiv import BiorxivSource

_RAW_A = {
    "doi": "10.1101/2024.01.15.575000",
    "title": "Cortical dynamics under a test paradigm",
    "authors": "Doe, Jane; Smith, John A.",
    "author_corresponding": "Jane Doe",
    "author_corresponding_institution": "Test University",
    "date": "2024-01-15",
    "version": "1",
    "category": "neuroscience",
    "abstract": "We show that the test paradigm reveals a robust effect.",
    "published": "10.1038/s41586-024-00000-0",
    "server": "biorxiv",
    "license": "cc_by",
}

_RAW_B = {
    "doi": "10.1101/2024.01.16.575111",
    "title": "A second preprint",
    "authors": "Roe, Richard",
    "date": "2024-01-16",
    "version": "2",
    "category": "neuroscience",
    "abstract": "Second body.",
    "server": "biorxiv",
    "license": "cc_by_nc",
}


def _one_page_fetcher(collection: list[dict[str, object]]):
    """Return a fetch_page callable that serves `collection` as a single
    terminal page (cursor + count >= total)."""

    def fetch_page(server: str, interval: str, cursor: int) -> dict[str, object]:
        return {
            "messages": [
                {"status": "ok", "count": len(collection), "total": len(collection), "cursor": cursor}
            ],
            "collection": collection,
        }

    return fetch_page


class TestBiorxivNormalize(unittest.TestCase):
    def setUp(self) -> None:
        self.src = BiorxivSource(fetch_page=_one_page_fetcher([_RAW_A]))

    def test_descriptor_is_preprint(self) -> None:
        self.assertEqual(self.src.descriptor.kind, "preprint")
        self.assertEqual(self.src.descriptor.name, "biorxiv")

    def test_maps_core_fields(self) -> None:
        rec = self.src.normalize(_RAW_A)
        self.assertEqual(rec.source, "biorxiv")
        self.assertEqual(rec.native_id, "10.1101/2024.01.15.575000")
        self.assertEqual(rec.record_uid, "biorxiv:10.1101/2024.01.15.575000")
        self.assertEqual(rec.display_id, "10.1101/2024.01.15.575000")
        self.assertEqual(rec.title, "Cortical dynamics under a test paradigm")
        self.assertEqual(rec.year, 2024)
        self.assertEqual(rec.venue, "bioRxiv")
        self.assertEqual(rec.url, "https://doi.org/10.1101/2024.01.15.575000")

    def test_abstract_becomes_section(self) -> None:
        rec = self.src.normalize(_RAW_A)
        self.assertEqual(rec.abstract, _RAW_A["abstract"])
        self.assertEqual(rec.sections["abstract"], _RAW_A["abstract"])

    def test_parses_semicolon_author_list(self) -> None:
        rec = self.src.normalize(_RAW_A)
        self.assertEqual(len(rec.authors), 2)
        self.assertEqual(rec.authors[0].family, "Doe")
        self.assertEqual(rec.authors[0].given, "Jane")
        self.assertEqual(rec.authors[0].order, 0)
        self.assertEqual(rec.authors[1].family, "Smith")

    def test_source_specific_fields_land_in_extra(self) -> None:
        rec = self.src.normalize(_RAW_A)
        self.assertEqual(rec.extra["category"], "neuroscience")
        self.assertEqual(rec.extra["version"], "1")
        self.assertEqual(rec.extra["license"], "cc_by")
        self.assertEqual(rec.extra["published_doi"], "10.1038/s41586-024-00000-0")

    def test_provenance_recorded(self) -> None:
        rec = self.src.normalize(_RAW_A)
        self.assertIsNotNone(rec.provenance)
        assert rec.provenance is not None
        self.assertEqual(rec.provenance.source, "biorxiv")
        self.assertTrue(rec.provenance.raw_digest)

    def test_missing_doi_raises(self) -> None:
        bad = {k: v for k, v in _RAW_A.items() if k != "doi"}
        with self.assertRaises(SourceNormalizationError):
            self.src.normalize(bad)

    def test_missing_title_raises(self) -> None:
        bad = {k: v for k, v in _RAW_A.items() if k != "title"}
        with self.assertRaises(SourceNormalizationError):
            self.src.normalize(bad)


class TestBiorxivRecords(unittest.TestCase):
    def test_records_over_injected_fetch(self) -> None:
        src = BiorxivSource(fetch_page=_one_page_fetcher([_RAW_A, _RAW_B]))
        recs = list(src.records({"interval": "2024-01-01/2024-01-31"}))
        self.assertEqual([r.native_id for r in recs], [_RAW_A["doi"], _RAW_B["doi"]])

    def test_is_an_abstract_source(self) -> None:
        src = BiorxivSource(fetch_page=_one_page_fetcher([]))
        self.assertIsInstance(src, AbstractSource)

    def test_missing_collection_raises(self) -> None:
        def bad_fetch(server: str, interval: str, cursor: int) -> dict[str, object]:
            return {"messages": [{"status": "no results"}]}

        src = BiorxivSource(fetch_page=bad_fetch)
        with self.assertRaises(SourceNormalizationError):
            list(src.records({"interval": "1900-01-01/1900-01-02"}))


if __name__ == "__main__":
    unittest.main()
