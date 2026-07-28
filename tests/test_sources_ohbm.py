"""Behavioral tests for `src/ohbm2026/sources/ohbm.py` (FR-008 adapter).

Phase 2 of the multi-source foundation (`specs/027-multi-source-foundation/`).
Tests are written first per Principle IV; they MUST fail before
`ohbm2026.sources.ohbm` exists.

`OhbmSource` is a READ-ONLY adapter over the shape
`assets.normalize_abstract` already produces (the Stage 1 corpus record).
It changes no on-disk artifact — it only re-expresses the existing dict as
the canonical `AbstractRecord`, proving the incumbent fits behind the
`AbstractSource` interface. The suite runs entirely offline (in-memory
records; no `data/` read).
"""

from __future__ import annotations

import unittest

from ohbm2026.sources.base import AbstractSource, SourceNormalizationError
from ohbm2026.sources.ohbm import OhbmSource

# Mirrors `assets.normalize_abstract` output (assets.py:326-337).
_OHBM_RAW = {
    "id": 12345,
    "poster_id": "P042",
    "title": "Hemodynamic coupling in visual cortex",
    "accepted_for": "Poster",
    "authors": [{"author_order": 0, "id": 9001}, {"author_order": 1, "id": 9002}],
    "responses": [
        {"question_name": "Introduction", "value": "We ask whether ..."},
        {"question_name": "Methods", "value": "7T fMRI in 20 subjects."},
        {"question_name": "Results", "value": "We find ..."},
    ],
    "external_urls": ["https://example.org/data"],
    "figure_urls": [
        {"question_name": "Results Figure", "source_url": "https://cdn.example.org/fig1.png"},
    ],
    "program_sessions": [{"session_id": 7, "session_name": "Vision"}],
    "local_assets": [],
}


class TestOhbmNormalize(unittest.TestCase):
    def setUp(self) -> None:
        self.src = OhbmSource()

    def test_descriptor_is_conference(self) -> None:
        self.assertEqual(self.src.descriptor.kind, "conference")
        self.assertEqual(self.src.descriptor.name, "ohbm2026")

    def test_maps_identity(self) -> None:
        rec = self.src.normalize(_OHBM_RAW)
        self.assertEqual(rec.source, "ohbm2026")
        self.assertEqual(rec.native_id, "12345")
        self.assertEqual(rec.record_uid, "ohbm2026:12345")
        self.assertEqual(rec.display_id, "P042")
        self.assertEqual(rec.title, "Hemodynamic coupling in visual cortex")
        self.assertEqual(rec.venue, "OHBM 2026")

    def test_responses_become_named_sections(self) -> None:
        rec = self.src.normalize(_OHBM_RAW)
        self.assertEqual(rec.sections["Introduction"], "We ask whether ...")
        self.assertEqual(rec.sections["Methods"], "7T fMRI in 20 subjects.")
        self.assertEqual(rec.sections["Results"], "We find ...")

    def test_figure_urls_flattened(self) -> None:
        rec = self.src.normalize(_OHBM_RAW)
        self.assertEqual(rec.figure_urls, ("https://cdn.example.org/fig1.png",))

    def test_ohbm_specific_fields_in_extra(self) -> None:
        rec = self.src.normalize(_OHBM_RAW)
        self.assertEqual(rec.extra["accepted_for"], "Poster")
        self.assertEqual(rec.extra["external_urls"], ["https://example.org/data"])
        self.assertEqual(rec.extra["program_sessions"][0]["session_name"], "Vision")
        # Author stubs (order+id only in the Stage-1 record) are preserved, not lost.
        self.assertEqual(len(rec.extra["author_refs"]), 2)

    def test_provenance_recorded(self) -> None:
        rec = self.src.normalize(_OHBM_RAW)
        self.assertIsNotNone(rec.provenance)
        assert rec.provenance is not None
        self.assertEqual(rec.provenance.source, "ohbm2026")
        self.assertTrue(rec.provenance.raw_digest)

    def test_missing_title_raises(self) -> None:
        bad = {k: v for k, v in _OHBM_RAW.items() if k != "title"}
        with self.assertRaises(SourceNormalizationError):
            self.src.normalize(bad)

    def test_missing_id_raises(self) -> None:
        bad = {k: v for k, v in _OHBM_RAW.items() if k != "id"}
        with self.assertRaises(SourceNormalizationError):
            self.src.normalize(bad)


class TestOhbmRecords(unittest.TestCase):
    def test_records_over_in_memory_list(self) -> None:
        src = OhbmSource()
        recs = list(src.records([_OHBM_RAW]))
        self.assertEqual([r.record_uid for r in recs], ["ohbm2026:12345"])

    def test_records_over_corpus_envelope(self) -> None:
        src = OhbmSource()
        recs = list(src.records({"abstracts": [_OHBM_RAW, _OHBM_RAW]}))
        self.assertEqual(len(recs), 2)

    def test_is_an_abstract_source(self) -> None:
        self.assertIsInstance(OhbmSource(), AbstractSource)


if __name__ == "__main__":
    unittest.main()
