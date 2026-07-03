"""Tests for `abstractatlas.enrich.markdown_render` (Stage 5 / US1).

Covers the manuscript/section markdown builders moved out of the legacy
`enrichment.py`. These helpers are consumed by Stage 2.1's claim-extraction
runner (`enrich/claims.py`) and the Stage 2 orchestrator (`enrich/stage.py`).
"""

from __future__ import annotations

import unittest

# Warmup import to break the exceptions ↔ fetch circular cycle.
from abstractatlas.analyze import stage as _stage_warmup  # noqa: F401

from abstractatlas.enrich.markdown_render import (
    SECTION_ORDER,
    build_claim_manuscript_markdown,
    build_sections_markdown,
    filter_content_questions_markdown,
    is_content_question,
    normalize_question_name,
    parse_list_value,
    question_to_section,
    render_abstract_markdown,
)


class NormalizeQuestionNameTests(unittest.TestCase):
    def test_lowercases_and_strips(self) -> None:
        self.assertEqual(normalize_question_name("  Methods  "), "methods")
        self.assertEqual(normalize_question_name("INTRODUCTION"), "introduction")

    def test_handles_none(self) -> None:
        self.assertEqual(normalize_question_name(None), "")


class QuestionToSectionTests(unittest.TestCase):
    def test_title(self) -> None:
        self.assertEqual(question_to_section("Title"), "title")

    def test_introduction(self) -> None:
        self.assertEqual(question_to_section("Introduction:"), "introduction")

    def test_methods(self) -> None:
        self.assertEqual(question_to_section("Methods"), "methods")

    def test_results(self) -> None:
        self.assertEqual(question_to_section("Results:"), "results")

    def test_conclusion(self) -> None:
        self.assertEqual(question_to_section("Conclusion"), "conclusion")

    def test_methods_figure_excluded(self) -> None:
        # Figure questions are NOT mapped to methods/results
        self.assertIsNone(question_to_section("Methods Figure"))
        self.assertIsNone(question_to_section("Results Figure"))

    def test_unmapped_returns_none(self) -> None:
        self.assertIsNone(question_to_section("Keywords"))


class ParseListValueTests(unittest.TestCase):
    def test_json_list(self) -> None:
        self.assertEqual(parse_list_value('["a", "b"]'), ["a", "b"])

    def test_plain_string(self) -> None:
        self.assertEqual(parse_list_value("just a phrase"), ["just a phrase"])

    def test_empty(self) -> None:
        self.assertEqual(parse_list_value(""), [])
        self.assertEqual(parse_list_value(None), [])


class IsContentQuestionTests(unittest.TestCase):
    def test_known_content_question(self) -> None:
        self.assertTrue(is_content_question("Keywords"))

    def test_section_question_not_content(self) -> None:
        self.assertFalse(is_content_question("Title"))

    def test_none(self) -> None:
        self.assertFalse(is_content_question(None))


class BuildSectionsMarkdownTests(unittest.TestCase):
    def test_synthetic_abstract_produces_section_dict(self) -> None:
        abstract = {
            "responses": [
                {"question_name": "Title", "value": "<p>Hi</p>"},
                {"question_name": "Introduction", "value": "<p>Intro body</p>"},
                {"question_name": "Methods", "value": "<p>Method body</p>"},
                {"question_name": "Results", "value": "<p>Result body</p>"},
                {"question_name": "Conclusion", "value": "<p>Concl body</p>"},
            ],
        }
        sections, unmapped = build_sections_markdown(abstract)
        # Title is NOT in the sections dict (it's the heading)
        self.assertNotIn("title", sections)
        self.assertIn("Intro body", sections["introduction"])
        self.assertIn("Method body", sections["methods"])
        self.assertIn("Result body", sections["results"])
        self.assertIn("Concl body", sections["conclusion"])
        self.assertEqual(unmapped, [])

    def test_unmapped_response_lands_in_unmapped(self) -> None:
        abstract = {
            "responses": [
                {"question_name": "Random Q", "value": "<p>v</p>"},
            ],
        }
        sections, unmapped = build_sections_markdown(abstract)
        self.assertEqual(sections, {})
        self.assertEqual(len(unmapped), 1)
        self.assertEqual(unmapped[0]["question_name"], "Random Q")


class FilterContentQuestionsTests(unittest.TestCase):
    def test_filters_to_content_only(self) -> None:
        items = [
            {"question_name": "Keywords", "markdown": "fmri; dmn", "response_index": 0},
            {"question_name": "Title", "markdown": "title body", "response_index": 1},
        ]
        out = filter_content_questions_markdown(items)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["question_name"], "Keywords")


class RenderAbstractMarkdownTests(unittest.TestCase):
    def test_renders_title_and_sections(self) -> None:
        out = render_abstract_markdown(
            "My Title",
            {"introduction": "Intro body", "methods": "Methods body"},
        )
        self.assertIn("# My Title", out)
        self.assertIn("## Introduction", out)
        self.assertIn("Intro body", out)
        self.assertIn("## Methods", out)


class BuildClaimManuscriptMarkdownTests(unittest.TestCase):
    def test_minimal_inputs(self) -> None:
        out = build_claim_manuscript_markdown(
            "Title",
            {"introduction": "Body"},
            additional_content_questions=[],
            figure_analyses=None,
        )
        self.assertIn("# Title", out)
        self.assertIn("Body", out)

    def test_empty_inputs_returns_placeholder(self) -> None:
        out = build_claim_manuscript_markdown("", {}, additional_content_questions=[], figure_analyses=None)
        self.assertEqual(out, "Untitled abstract")


class SectionOrderTests(unittest.TestCase):
    def test_known_section_keys_present(self) -> None:
        keys = [k for k, _ in SECTION_ORDER]
        for expected in ("introduction", "methods", "results", "discussion", "conclusion"):
            self.assertIn(expected, keys)


if __name__ == "__main__":
    unittest.main()
