"""HTML → pandoc-markdown conversion (R2).

The Oxford form's rich-text editor stores all long-form values as HTML
fragments with `<p>`, `<sup>`, `<sub>`, `<ol>`, `<li>`, `<em>`,
`<strong>`, `<a>`, `<br>` and inline `style="..."`/`id="isPasted"`
attributes. The book renders from markdown, so the conversion happens
ONCE at corpus load (the in-memory model carries markdown, not HTML).

Pandoc-flavored superscripts (`^N^`) and subscripts (`~N~`) preserve
the scientific-citation markup that plain CommonMark cannot express.
"""

from __future__ import annotations

import re
import sys

from bs4 import BeautifulSoup
from markdownify import markdownify

# markdownify recurses through the BeautifulSoup tree; the Oxford
# rich-text editor produces deeply-nested HTML (especially for
# References/Citations <ol><li><p><span>... chains). Default 1000 is
# too tight; 5000 is plenty for the observed corpus.
_RECURSION_FLOOR = 5000


# Unicode superscript / subscript characters that authors paste in
# directly (instead of using `<sup>N</sup>`). Latin Modern lacks
# these glyphs and Tectonic refuses to fall through to a substitute
# font — so we normalise them BEFORE pandoc emits LaTeX. Each cluster
# of contiguous super/sub chars maps to a single `^...^` / `~...~`
# pandoc token; non-contiguous occurrences stay independent.
_SUPER_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"
_SUB_DIGITS = "₀₁₂₃₄₅₆₇₈₉"
_SUPER_SIGNS = {
    "⁺": "+",  # SUPERSCRIPT PLUS SIGN
    "⁻": "-",  # SUPERSCRIPT MINUS
    "⁼": "=",  # SUPERSCRIPT EQUALS SIGN
    "⁽": "(",
    "⁾": ")",
    "ⁿ": "n",  # SUPERSCRIPT LATIN SMALL LETTER N
}
_SUB_SIGNS = {
    "₊": "+",
    "₋": "-",
    "₌": "=",
    "₍": "(",
    "₎": ")",
}

_SUPER_RE = re.compile(
    "([" + _SUPER_DIGITS + "".join(_SUPER_SIGNS.keys()) + "]+)"
)
_SUB_RE = re.compile(
    "([" + _SUB_DIGITS + "".join(_SUB_SIGNS.keys()) + "]+)"
)

_SUPER_TRANS = str.maketrans(
    {ch: a for ch, a in zip(_SUPER_DIGITS, "0123456789")} | _SUPER_SIGNS
)
_SUB_TRANS = str.maketrans(
    {ch: a for ch, a in zip(_SUB_DIGITS, "0123456789")} | _SUB_SIGNS
)


def _normalise_unicode_super_sub(text: str) -> str:
    """Replace contiguous Unicode super/subscript runs with pandoc
    `^...^` / `~...~` literals so the LaTeX renderer never sees a
    glyph its font can't represent (Latin Modern lacks U+2074, etc.).
    """

    def _super(m: "re.Match[str]") -> str:
        return "^" + m.group(0).translate(_SUPER_TRANS) + "^"

    def _sub(m: "re.Match[str]") -> str:
        return "~" + m.group(0).translate(_SUB_TRANS) + "~"

    text = _SUPER_RE.sub(_super, text)
    text = _SUB_RE.sub(_sub, text)
    return text


# Greek letters that appear in body text (Latin Modern lacks every
# one of these). Wrap in `\(...\)` math markers so they fall through
# to Latin Modern Math, which DOES have Greek. Pandoc passes raw
# TeX (`\( \)`) through unchanged when `raw_tex` is enabled.
_GREEK_LATEX = {
    # Lowercase
    "α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "δ": r"\delta",
    "ε": r"\epsilon", "ζ": r"\zeta", "η": r"\eta", "θ": r"\theta",
    "ι": r"\iota", "κ": r"\kappa", "λ": r"\lambda", "μ": r"\mu",
    "ν": r"\nu", "ξ": r"\xi", "ο": "o", "π": r"\pi",
    "ρ": r"\rho", "σ": r"\sigma", "ς": r"\varsigma", "τ": r"\tau",
    "υ": r"\upsilon", "φ": r"\varphi", "ϕ": r"\phi", "χ": r"\chi",
    "ψ": r"\psi", "ω": r"\omega",
    "ϑ": r"\vartheta", "ϱ": r"\varrho", "ϖ": r"\varpi", "ε": r"\varepsilon",
    # Uppercase
    "Α": "A", "Β": "B", "Γ": r"\Gamma", "Δ": r"\Delta",
    "Ε": "E", "Ζ": "Z", "Η": "H", "Θ": r"\Theta",
    "Ι": "I", "Κ": "K", "Λ": r"\Lambda", "Μ": "M",
    "Ν": "N", "Ξ": r"\Xi", "Ο": "O", "Π": r"\Pi",
    "Ρ": "P", "Σ": r"\Sigma", "Τ": "T",
    "Υ": r"\Upsilon", "Φ": r"\Phi", "Χ": "X", "Ψ": r"\Psi",
    "Ω": r"\Omega",
}

# Math operators / relations that Latin Modern's text font also
# doesn't carry. Latin Modern Math has them in math mode.
_MATH_OP_LATEX = {
    "→": r"\to", "←": r"\gets", "↔": r"\leftrightarrow",
    "⇒": r"\Rightarrow", "⇐": r"\Leftarrow", "⇔": r"\Leftrightarrow",
    "≥": r"\geq", "≤": r"\leq", "≠": r"\neq", "≈": r"\approx",
    "≡": r"\equiv", "∼": r"\sim", "∝": r"\propto",
    "∞": r"\infty", "∂": r"\partial", "∇": r"\nabla",
    "∑": r"\sum", "∏": r"\prod", "∫": r"\int",
    "∈": r"\in", "∉": r"\notin", "⊂": r"\subset", "⊃": r"\supset",
    "∩": r"\cap", "∪": r"\cup", "∅": r"\emptyset",
    "±": r"\pm", "∓": r"\mp", "×": r"\times", "÷": r"\div",
    "√": r"\surd", "∗": r"\ast",
    "−": "-",  # MINUS SIGN U+2212 → ASCII hyphen
    "‐": "-", "‑": "-", "‒": "-",  # various dash glyphs
}

_GREEK_RE = re.compile("([" + "".join(_GREEK_LATEX.keys()) + "])")
_MATH_OP_RE = re.compile("([" + "".join(re.escape(c) for c in _MATH_OP_LATEX.keys()) + "])")


def _normalise_greek_and_math(text: str) -> str:
    """Wrap Greek letters and math operators in `\\(...\\)` math
    markers so they fall through to Latin Modern Math (which has
    Greek + math symbols) instead of choking the text-mode font.

    Contiguous runs collapse into a single math span — `α + β` →
    `\\(\\alpha + \\beta\\)` is cleaner than three separate spans.
    Pandoc treats `\\(...\\)` as raw inline math.
    """

    def _greek(m: "re.Match[str]") -> str:
        return f"\\({_GREEK_LATEX[m.group(0)]}\\)"

    def _mathop(m: "re.Match[str]") -> str:
        repl = _MATH_OP_LATEX[m.group(0)]
        # ASCII fallback (e.g. − → -) doesn't need math mode.
        if repl.startswith("\\"):
            return f"\\({repl}\\)"
        return repl

    text = _GREEK_RE.sub(_greek, text)
    text = _MATH_OP_RE.sub(_mathop, text)
    return text


def html_to_pandoc_md(html: str) -> str:
    """Convert an Oxford-corpus HTML fragment to pandoc markdown.

    Pure function, no I/O. Returns a stripped string; empty input
    yields empty output.
    """
    if not html or not html.strip():
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Pre-pass: convert sup/sub to pandoc literals BEFORE markdownify
    # collapses them into stray HTML islands. We replace each
    # <sup>x</sup> node with a NavigableString containing `^x^` (and
    # likewise for sub). Markdownify then sees plain text and leaves
    # the literal alone.
    for tag in soup.find_all("sup"):
        text = tag.get_text()
        # Pandoc superscript syntax disallows whitespace inside;
        # backslash-escape if necessary to keep the marker valid.
        text = re.sub(r"\s+", r"\\ ", text)
        tag.replace_with(f"^{text}^")
    for tag in soup.find_all("sub"):
        text = tag.get_text()
        text = re.sub(r"\s+", r"\\ ", text)
        tag.replace_with(f"~{text}~")

    # Strip the rich-text-editor artefacts before markdownify sees them.
    for tag in soup.find_all(attrs={"id": "isPasted"}):
        del tag.attrs["id"]
    for tag in soup.find_all(style=True):
        del tag.attrs["style"]

    prior_limit = sys.getrecursionlimit()
    if prior_limit < _RECURSION_FLOOR:
        sys.setrecursionlimit(_RECURSION_FLOOR)
    try:
        md = markdownify(
            str(soup),
            heading_style="ATX",
            bullets="-",
            strip=["span"],
        )
    finally:
        if prior_limit < _RECURSION_FLOOR:
            sys.setrecursionlimit(prior_limit)

    # Normalise direct Unicode super/subscript glyphs into pandoc
    # `^...^` / `~...~` literals. Run AFTER markdownify so we operate
    # on plain text — any `<sup>`/`<sub>` already became `^...^` /
    # `~...~` in the BeautifulSoup pre-pass above.
    md = _normalise_unicode_super_sub(md)
    # Wrap Greek letters + math operators in `\(...\)` so the LaTeX
    # renderer sees them via Latin Modern Math (the text-mode font
    # lacks the codepoints).
    md = _normalise_greek_and_math(md)

    # markdownify leaves trailing whitespace per line + collapses
    # multiple blank lines unevenly; tighten the output so re-runs
    # are byte-deterministic (SC-007a).
    lines = [ln.rstrip() for ln in md.splitlines()]
    out: list[str] = []
    blank = False
    for ln in lines:
        if ln == "":
            if blank:
                continue
            blank = True
        else:
            blank = False
        out.append(ln)
    return "\n".join(out).strip() + "\n"
