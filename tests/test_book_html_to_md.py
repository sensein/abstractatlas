"""T012 — HTML → pandoc-markdown conversion (R2)."""

from __future__ import annotations

import unittest

from ohbm2026.book.html_to_md import html_to_pandoc_md


class TestHtmlToMd(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(html_to_pandoc_md(""), "")
        self.assertEqual(html_to_pandoc_md("   "), "")

    def test_superscript_becomes_pandoc_caret(self) -> None:
        md = html_to_pandoc_md("<p>cite<sup>1,2</sup></p>")
        self.assertIn("^1,2^", md)
        # Single-char form too.
        md = html_to_pandoc_md("<p>x<sup>1</sup></p>")
        self.assertIn("^1^", md)

    def test_subscript_becomes_pandoc_tilde(self) -> None:
        md = html_to_pandoc_md("<p>H<sub>2</sub>O</p>")
        self.assertIn("~2~", md)

    def test_ordered_list_becomes_numbered(self) -> None:
        md = html_to_pandoc_md("<ol><li>A</li><li>B</li></ol>")
        self.assertIn("1. A", md)
        self.assertIn("2. B", md)

    def test_inline_style_and_ispasted_stripped(self) -> None:
        md = html_to_pandoc_md(
            '<p style="font-family:Arial" id="isPasted">hello</p>'
        )
        self.assertIn("hello", md)
        self.assertNotIn("style", md)
        self.assertNotIn("isPasted", md)
        self.assertNotIn("font-family", md)

    def test_strong_em(self) -> None:
        md = html_to_pandoc_md(
            "<p><strong>bold</strong> and <em>italic</em></p>"
        )
        self.assertIn("**bold**", md)
        # markdownify uses underscore or asterisk for em; either is fine
        self.assertTrue("*italic*" in md or "_italic_" in md)

    def test_html_entity_resolves(self) -> None:
        md = html_to_pandoc_md("<p>x&plusmn;y</p>")
        # The entity decodes to U+00B1 (±) which the math-operator
        # normaliser then wraps in `\(\pm\)` so it falls through to
        # Latin Modern Math at LaTeX-compile time.
        self.assertIn(r"$\pm$", md)

    def test_unicode_superscript_normalised(self) -> None:
        # Authors sometimes paste literal Unicode super/subscript
        # glyphs instead of using <sup>/<sub>. Latin Modern lacks the
        # codepoints, so we coerce them to pandoc literals before
        # LaTeX sees the input.
        md = html_to_pandoc_md("<p>fMRI⁴ data is processed in H₂O</p>")
        self.assertIn("^4^", md)
        self.assertIn("~2~", md)
        # Multi-char run collapses into a single pandoc token.
        md = html_to_pandoc_md("<p>x²⁰²⁶ years</p>")
        self.assertIn("^2026^", md)

    def test_greek_letters_wrapped_in_math(self) -> None:
        md = html_to_pandoc_md("<p>The α-value is 0.05; ρ = 0.42; Δ change</p>")
        self.assertIn(r"$\alpha$", md)
        self.assertIn(r"$\rho$", md)
        self.assertIn(r"$\Delta$", md)

    def test_math_operators_wrapped_in_math(self) -> None:
        md = html_to_pandoc_md("<p>A → B with p ≤ 0.05; ratio ≈ 1.5</p>")
        self.assertIn(r"$\to$", md)
        self.assertIn(r"$\leq$", md)
        self.assertIn(r"$\approx$", md)

    def test_math_italic_greek_folded(self) -> None:
        # 𝜌 (U+1D70C) is MATHEMATICAL ITALIC SMALL RHO — different
        # codepoint from basic ρ (U+03C1). Folder maps it to the
        # basic Greek; then the Greek normaliser wraps it in math.
        md = html_to_pandoc_md("<p>The 𝜌 value is 0.42</p>")
        self.assertIn(r"$\rho$", md)
        # 𝑥 (U+1D465) is MATHEMATICAL ITALIC SMALL X — folds to ASCII x.
        md = html_to_pandoc_md("<p>variable 𝑥</p>")
        self.assertIn("x", md)
        self.assertNotIn("𝑥", md)

    def test_minus_sign_normalised_to_ascii(self) -> None:
        md = html_to_pandoc_md("<p>Result: −0.42</p>")
        # MINUS SIGN (U+2212) → ASCII hyphen (no math wrap needed)
        self.assertIn("-0.42", md)
        self.assertNotIn("−", md)

    def test_deterministic(self) -> None:
        html = (
            '<p style="x" id="isPasted">A<sup>1</sup></p>'
            "<p>B<sub>2</sub></p><ol><li>r1</li><li>r2</li></ol>"
        )
        self.assertEqual(html_to_pandoc_md(html), html_to_pandoc_md(html))


class TestCaretSuperscriptToLatex(unittest.TestCase):
    """Stage 12.1 — `normalise_for_latex` converts pandoc text-
    superscript syntax `^X^` to explicit `\\textsuperscript{X}` so
    the dominant cluster of "Double superscript" LaTeX errors (76
    failed abstracts in Stage 11.1's provenance) is eliminated.
    """

    def test_simple_caret_to_textsuperscript(self) -> None:
        from ohbm2026.book.html_to_md import normalise_for_latex

        self.assertIn("\\textsuperscript{3}", normalise_for_latex("4 mm^3^"))
        self.assertIn("\\textsuperscript{1,2}", normalise_for_latex("Doe^1,2^"))

    def test_caret_survives_math_span_adjacency(self) -> None:
        # The exact pattern that broke Stage 11.1: `$\times$3 mm^3^`.
        from ohbm2026.book.html_to_md import normalise_for_latex

        out = normalise_for_latex("3$\\times$3$\\times$4 mm^3^;")
        # No bare `^3^` remains — pandoc's math-mode parser can't
        # confuse the result anymore.
        self.assertNotIn("mm^3^", out)
        self.assertIn("\\textsuperscript{3}", out)

    def test_escaped_caret_not_touched(self) -> None:
        # Already-escaped `\^X^` (rare; usually authors who want a
        # literal caret) should NOT be re-converted. The regex uses
        # a negative lookbehind on `\\`.
        from ohbm2026.book.html_to_md import normalise_for_latex

        out = normalise_for_latex("a \\^x^ b")
        self.assertNotIn("\\textsuperscript{x}", out)

    def test_idempotent(self) -> None:
        from ohbm2026.book.html_to_md import normalise_for_latex

        once = normalise_for_latex("k^c^")
        twice = normalise_for_latex(once)
        self.assertEqual(once, twice)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
