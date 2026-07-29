"""Arc A'.2 — sections-aware component resolution + schema-mismatch gate.

Per `specs/027-multi-source-foundation/`: the Stage 3 component resolver
currently matches component names *only* against Oxford Abstracts'
``responses[].question_name``. Two consequences this module pins down:

1. A record from any other source cannot contribute component text at all,
   even though the canonical `AbstractRecord` carries an open ``sections``
   mapping. The resolver must read ``sections`` too.

2. Worse, a component that is empty across the WHOLE corpus is currently
   silent: `DEFAULT_COMPONENTS` are exempt from the partial-coverage gate
   (`embed/stage.py`), so asking a corpus whose sections are named
   "Background"/"Approach" for "methods" emits a **zero-row bundle with no
   error**. That is a schema mismatch, not partial coverage, and must fail
   loudly (Principle VI/VII).

Per-record empties stay legitimate — not every abstract has every section —
so only the corpus-wide-empty case raises.

Tests written first per Principle IV.
"""

from __future__ import annotations

import argparse
import unittest
from pathlib import Path

from ohbm2026.embed import components as embed_components
from ohbm2026.embed import stage as embed_stage
from ohbm2026.exceptions import ComponentAssemblyError


class TestSectionsAwareResolution(unittest.TestCase):
    def test_resolves_from_sections_mapping(self) -> None:
        record = {"id": 1, "title": "T", "sections": {"methods": "We used 7T fMRI."}}
        self.assertEqual(
            embed_components.assemble_component(record, "methods"), "We used 7T fMRI."
        )

    def test_sections_match_is_case_insensitive(self) -> None:
        record = {"id": 1, "sections": {"Methods": "Body text."}}
        self.assertEqual(embed_components.assemble_component(record, "methods"), "Body text.")

    def test_falls_back_to_oxford_responses(self) -> None:
        record = {
            "id": 1,
            "responses": [{"question_name": "Methods", "value": "Legacy path."}],
        }
        self.assertEqual(embed_components.assemble_component(record, "methods"), "Legacy path.")

    def test_sections_take_precedence_over_responses(self) -> None:
        record = {
            "id": 1,
            "sections": {"methods": "From sections."},
            "responses": [{"question_name": "Methods", "value": "From responses."}],
        }
        self.assertEqual(
            embed_components.assemble_component(record, "methods"), "From sections."
        )

    def test_absent_from_sections_falls_through_to_responses(self) -> None:
        record = {
            "id": 1,
            "sections": {"results": "Only results here."},
            "responses": [{"question_name": "Methods", "value": "Responses methods."}],
        }
        self.assertEqual(
            embed_components.assemble_component(record, "methods"), "Responses methods."
        )

    def test_whitespace_is_normalized_from_sections(self) -> None:
        record = {"id": 1, "sections": {"methods": "  spaced\n\nout   text  "}}
        self.assertEqual(embed_components.assemble_component(record, "methods"), "spaced out text")

    def test_html_in_sections_is_converted(self) -> None:
        record = {"id": 1, "sections": {"methods": "<p>Bold <b>claim</b></p>"}}
        out = embed_components.assemble_component(record, "methods")
        self.assertNotIn("<p>", out)
        self.assertIn("claim", out)

    def test_missing_component_still_returns_empty(self) -> None:
        record = {"id": 1, "sections": {"results": "r"}}
        self.assertEqual(embed_components.assemble_component(record, "methods"), "")

    def test_unknown_component_still_raises(self) -> None:
        with self.assertRaises(ValueError):
            embed_components.assemble_component({"id": 1}, "not_a_component")


def _args(**overrides) -> argparse.Namespace:
    defaults = dict(
        models=["minilm"],
        components=["methods"],
        embeddings_root="data/outputs/experiments/embeddings",
        cache_root="data/cache/embeddings",
        batch_size=64,
        long_input_strategy=[],
        failure_threshold=0.01,
        allow_partial=[],
        invalidate=[],
        dry_run=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class TestSchemaMismatchGate(unittest.TestCase):
    """A corpus-wide-empty component must abort, even for a DEFAULT component."""

    def _run(self, component_texts: dict, *, component: str = "methods"):
        records = [{"id": 1}, {"id": 2}, {"id": 3}]
        return embed_stage.run_single_bundle(
            model_key="minilm",
            component=component,
            records=records,
            component_texts=component_texts,
            corpus_state_key="deadbeef",
            corpus_source_path=Path("corpus.sqlite"),
            embeddings_root=Path("unused"),
            cache_root=Path("unused"),
            clients={},
            args=_args(),
        )

    def test_universally_empty_default_component_raises(self) -> None:
        # 'methods' is in DEFAULT_COMPONENTS, so today this silently
        # produces a zero-row bundle. It must raise instead.
        with self.assertRaises(ComponentAssemblyError):
            self._run({})

    def test_error_names_the_component(self) -> None:
        with self.assertRaises(ComponentAssemblyError) as ctx:
            self._run({})
        self.assertIn("methods", str(ctx.exception))

    def test_partial_coverage_is_not_a_schema_mismatch(self) -> None:
        # One of three present → legitimate partial coverage for a default
        # component; must NOT raise the schema-mismatch error. (It may fail
        # later for unrelated reasons — a missing client — so we only assert
        # that ComponentAssemblyError is not what surfaces.)
        try:
            self._run({(1, "methods"): "present text"})
        except ComponentAssemblyError as exc:  # pragma: no cover - guard
            self.fail(f"partial coverage wrongly treated as schema mismatch: {exc}")
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
