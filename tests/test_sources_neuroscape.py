"""Behavioral tests for `src/ohbm2026/sources/neuroscape.py` (FR-008 adapter).

Phase 2 of the multi-source foundation (`specs/027-multi-source-foundation/`).
Tests are written first per Principle IV; they MUST fail before
`ohbm2026.sources.neuroscape` exists.

`NeuroScapeSource` adapts the identity fields the NeuroScape loader exposes
per article (`ArticleHeader`: pubmed_id / title / year / cluster_id) into the
canonical `AbstractRecord`. Bodies (abstract/authors/DOI) are deliberately
NOT stored locally by NeuroScape — they are fetched at view time via NCBI
EFetch — so the record's `abstract` is `None` and `sections` is empty; this
is faithful, not a gap. The adapter duck-types its input (a Mapping OR any
object exposing the four attributes) so the light `sources` layer never
imports the heavy loader (h5py/numpy).
"""

from __future__ import annotations

import unittest
from collections import namedtuple

from ohbm2026.sources.base import AbstractSource, SourceNormalizationError
from ohbm2026.sources.neuroscape import NeuroScapeSource

_NS_DICT = {"pubmed_id": 30001234, "title": "Default mode network review", "year": 2019, "cluster_id": 5}

# Stand-in for `ArticleHeader` — same field names, no heavy-dep import.
_FakeHeader = namedtuple("_FakeHeader", ["pubmed_id", "title", "year", "cluster_id"])


class TestNeuroScapeNormalize(unittest.TestCase):
    def setUp(self) -> None:
        self.src = NeuroScapeSource()

    def test_descriptor_is_corpus(self) -> None:
        self.assertEqual(self.src.descriptor.kind, "corpus")
        self.assertEqual(self.src.descriptor.name, "neuroscape")

    def test_maps_from_mapping(self) -> None:
        rec = self.src.normalize(_NS_DICT)
        self.assertEqual(rec.source, "neuroscape")
        self.assertEqual(rec.native_id, "30001234")
        self.assertEqual(rec.record_uid, "neuroscape:30001234")
        self.assertEqual(rec.display_id, "30001234")
        self.assertEqual(rec.title, "Default mode network review")
        self.assertEqual(rec.year, 2019)
        self.assertEqual(rec.url, "https://pubmed.ncbi.nlm.nih.gov/30001234/")

    def test_maps_from_attribute_object(self) -> None:
        rec = self.src.normalize(_FakeHeader(30001234, "Default mode network review", 2019, 5))
        self.assertEqual(rec.record_uid, "neuroscape:30001234")
        self.assertEqual(rec.extra["cluster_id"], 5)

    def test_body_is_absent_by_design(self) -> None:
        rec = self.src.normalize(_NS_DICT)
        self.assertIsNone(rec.abstract)
        self.assertEqual(dict(rec.sections), {})

    def test_provenance_recorded(self) -> None:
        rec = self.src.normalize(_NS_DICT)
        self.assertIsNotNone(rec.provenance)
        assert rec.provenance is not None
        self.assertTrue(rec.provenance.raw_digest)

    def test_missing_title_raises(self) -> None:
        with self.assertRaises(SourceNormalizationError):
            self.src.normalize({"pubmed_id": 1, "year": 2019, "cluster_id": 5})

    def test_missing_pubmed_id_raises(self) -> None:
        with self.assertRaises(SourceNormalizationError):
            self.src.normalize({"title": "x", "year": 2019, "cluster_id": 5})


class TestNeuroScapeRecords(unittest.TestCase):
    def test_records_over_in_memory_list(self) -> None:
        src = NeuroScapeSource()
        recs = list(src.records([_NS_DICT, _FakeHeader(2, "Second", 2020, 1)]))
        self.assertEqual([r.native_id for r in recs], ["30001234", "2"])

    def test_is_an_abstract_source(self) -> None:
        self.assertIsInstance(NeuroScapeSource(), AbstractSource)


if __name__ == "__main__":
    unittest.main()
