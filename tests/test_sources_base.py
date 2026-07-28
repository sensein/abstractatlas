"""Behavioral tests for `src/ohbm2026/sources/base.py`.

Arc A of the multi-source foundation (per
`specs/027-multi-source-foundation/`). Tests are written first per
Principle IV; they MUST fail before `ohbm2026.sources.base` exists.

Covers, per data-model.md and contracts/abstract-source.md:

  - `AbstractRecord`: source-neutral canonical record; computed
    `record_uid`; immutability; loud validation of required fields;
    read-only `sections` / `extra` mappings.
  - `AbstractAuthor`, `SourceDescriptor` (kind validation),
    `SourceProvenance`.
  - `build_record_uid`: `<source>:<native_id>` with loud rejection of
    empty parts and colon-bearing source names.
  - `AbstractSource` Protocol (structural) + `BaseAbstractSource`
    default `records()` composing `fetch_raw` + `normalize`.
"""

from __future__ import annotations

import dataclasses
import unittest

from ohbm2026.sources import base
from ohbm2026.sources.base import (
    AbstractAuthor,
    AbstractRecord,
    AbstractSource,
    BaseAbstractSource,
    SourceDescriptor,
    SourceNormalizationError,
    SourceProvenance,
    build_record_uid,
)


class TestBuildRecordUid(unittest.TestCase):
    def test_composes_source_and_native_id(self) -> None:
        self.assertEqual(build_record_uid("biorxiv", "10.1101/abc"), "biorxiv:10.1101/abc")

    def test_rejects_empty_parts(self) -> None:
        with self.assertRaises(SourceNormalizationError):
            build_record_uid("", "x")
        with self.assertRaises(SourceNormalizationError):
            build_record_uid("biorxiv", "")

    def test_rejects_colon_in_source(self) -> None:
        # The colon is the reserved delimiter; a source name may not carry one.
        with self.assertRaises(SourceNormalizationError):
            build_record_uid("bio:rxiv", "x")


class TestSourceDescriptor(unittest.TestCase):
    def test_valid_kind(self) -> None:
        d = SourceDescriptor(name="biorxiv", kind="preprint", title="bioRxiv")
        self.assertEqual(d.kind, "preprint")

    def test_invalid_kind_raises(self) -> None:
        with self.assertRaises(SourceNormalizationError):
            SourceDescriptor(name="x", kind="journal-of-nonsense", title="X")


class TestAbstractRecord(unittest.TestCase):
    def _record(self, **overrides: object) -> AbstractRecord:
        kwargs: dict[str, object] = {
            "source": "biorxiv",
            "native_id": "10.1101/abc",
            "title": "A title",
        }
        kwargs.update(overrides)
        return AbstractRecord(**kwargs)  # type: ignore[arg-type]

    def test_record_uid_is_derived(self) -> None:
        self.assertEqual(self._record().record_uid, "biorxiv:10.1101/abc")

    def test_is_immutable(self) -> None:
        rec = self._record()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            rec.title = "mutated"  # type: ignore[misc]

    def test_missing_required_fields_raise_loudly(self) -> None:
        with self.assertRaises(SourceNormalizationError):
            self._record(title="")
        with self.assertRaises(SourceNormalizationError):
            self._record(native_id="")
        with self.assertRaises(SourceNormalizationError):
            self._record(source="")

    def test_sections_and_extra_are_read_only(self) -> None:
        rec = self._record(sections={"abstract": "body"}, extra={"category": "neuro"})
        self.assertEqual(rec.sections["abstract"], "body")
        self.assertEqual(rec.extra["category"], "neuro")
        with self.assertRaises(TypeError):
            rec.sections["abstract"] = "x"  # type: ignore[index]
        with self.assertRaises(TypeError):
            rec.extra["category"] = "x"  # type: ignore[index]

    def test_authors_tuple(self) -> None:
        rec = self._record(authors=(AbstractAuthor(name="Doe, Jane", family="Doe", given="Jane", order=0),))
        self.assertEqual(rec.authors[0].family, "Doe")


class _FakeSource(BaseAbstractSource):
    """Minimal in-memory source proving the Protocol composes offline."""

    def __init__(self, raws: list[dict[str, object]]) -> None:
        self._raws = raws

    @property
    def descriptor(self) -> SourceDescriptor:
        return SourceDescriptor(name="fake", kind="corpus", title="Fake")

    def fetch_raw(self, query: object) -> object:
        return iter(self._raws)

    def normalize(self, raw: dict[str, object]) -> AbstractRecord:
        return AbstractRecord(
            source="fake",
            native_id=str(raw["id"]),
            title=str(raw["title"]),
            provenance=SourceProvenance(
                source="fake",
                descriptor=self.descriptor,
                fetched_at=None,
                raw_digest=base.digest_raw(raw),
            ),
        )


class TestAbstractSourceProtocol(unittest.TestCase):
    def test_base_source_satisfies_protocol_structurally(self) -> None:
        src = _FakeSource([])
        self.assertIsInstance(src, AbstractSource)

    def test_records_composes_fetch_and_normalize(self) -> None:
        src = _FakeSource([{"id": "1", "title": "One"}, {"id": "2", "title": "Two"}])
        recs = list(src.records(query=None))
        self.assertEqual([r.record_uid for r in recs], ["fake:1", "fake:2"])
        self.assertTrue(all(r.provenance and r.provenance.raw_digest for r in recs))


if __name__ == "__main__":
    unittest.main()
