"""Tests for `abstractatlas.enrich.text` (Stage 5 / US1).

Covers `html_to_markdown` + `HTMLToMarkdownParser` — the HTML→Markdown
conversion helpers moved out of the legacy `enrichment.py`.
"""

from __future__ import annotations

import unittest

# Warmup import to break the exceptions ↔ fetch circular cycle
# (same pattern as tests/test_analyze_stage.py).
from abstractatlas.analyze import stage as _stage_warmup  # noqa: F401

from abstractatlas.enrich.text import HTMLToMarkdownParser, html_to_markdown


class HtmlToMarkdownTests(unittest.TestCase):
    def test_simple_paragraph(self) -> None:
        self.assertEqual(html_to_markdown("<p>hello</p>"), "hello")

    def test_strong_renders_as_bold(self) -> None:
        self.assertIn("**bold**", html_to_markdown("<p>this is <strong>bold</strong></p>"))

    def test_emphasis_renders_as_italic(self) -> None:
        self.assertIn("_italic_", html_to_markdown("<p>this is <em>italic</em></p>"))

    def test_unordered_list(self) -> None:
        result = html_to_markdown("<ul><li>one</li><li>two</li></ul>")
        self.assertIn("- one", result)
        self.assertIn("- two", result)

    def test_ordered_list_uses_numbers(self) -> None:
        result = html_to_markdown("<ol><li>first</li><li>second</li></ol>")
        self.assertIn("1. first", result)
        self.assertIn("2. second", result)

    def test_link_with_href(self) -> None:
        result = html_to_markdown('<p>see <a href="https://example.com">here</a></p>')
        self.assertIn("[here](https://example.com)", result)

    def test_entities_decoded(self) -> None:
        # convert_charrefs=True in the parser → &amp; becomes &
        result = html_to_markdown("<p>A &amp; B</p>")
        self.assertIn("&", result)
        self.assertNotIn("&amp;", result)

    def test_empty_input_returns_empty_string(self) -> None:
        self.assertEqual(html_to_markdown(""), "")
        self.assertEqual(html_to_markdown(None), "")

    def test_plain_text_no_tags_passes_through(self) -> None:
        self.assertEqual(html_to_markdown("just plain text"), "just plain text")

    def test_parser_class_directly(self) -> None:
        """HTMLToMarkdownParser can be instantiated and produces the same
        output as the function wrapper for HTML inputs."""
        parser = HTMLToMarkdownParser()
        parser.feed("<p>direct parser <strong>use</strong></p>")
        parser.close()
        self.assertIn("**use**", parser.markdown())


if __name__ == "__main__":
    unittest.main()
