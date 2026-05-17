"""HTML ↔ Markdown text helpers for the Stage 2 enrichment pipeline.

Lifted verbatim from the legacy `src/ohbm2026/enrichment.py` as part of
the Stage 5 package reorganization (specs/007-package-reorg/). Leaf
module: stdlib only, no intra-package imports.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any


class HTMLToMarkdownParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.list_stack: list[dict[str, Any]] = []
        self.link_stack: list[str | None] = []
        self.format_stack: list[str] = []

    def _append(self, text: str) -> None:
        if text:
            self.parts.append(text)

    def _ensure_block_break(self) -> None:
        current = "".join(self.parts)
        if not current.endswith("\n\n"):
            if current.endswith("\n"):
                self.parts.append("\n")
            elif current:
                self.parts.append("\n\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag in {"p", "div"}:
            self._ensure_block_break()
        elif tag == "br":
            self._append("\n")
        elif tag in {"strong", "b"}:
            self._append("**")
            self.format_stack.append("**")
        elif tag in {"em", "i"}:
            self._append("_")
            self.format_stack.append("_")
        elif tag == "sup":
            self._append("^(")
            self.format_stack.append(")")
        elif tag == "ul":
            self.list_stack.append({"type": "ul", "index": 0})
            self._ensure_block_break()
        elif tag == "ol":
            self.list_stack.append({"type": "ol", "index": 1})
            self._ensure_block_break()
        elif tag == "li":
            self._append("\n")
            indent = "  " * max(len(self.list_stack) - 1, 0)
            if self.list_stack and self.list_stack[-1]["type"] == "ol":
                prefix = f"{self.list_stack[-1]['index']}. "
                self.list_stack[-1]["index"] += 1
            else:
                prefix = "- "
            self._append(indent + prefix)
        elif tag == "a":
            href = attr_map.get("href")
            self.link_stack.append(href)
            self._append("[")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div"}:
            self._ensure_block_break()
        elif tag in {"strong", "b", "em", "i", "sup"} and self.format_stack:
            self._append(self.format_stack.pop())
        elif tag in {"ul", "ol"}:
            if self.list_stack:
                self.list_stack.pop()
            self._ensure_block_break()
        elif tag == "a":
            href = self.link_stack.pop() if self.link_stack else None
            self._append(f"]({href})" if href else "]")

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data)
        if text.strip():
            self._append(text)

    def markdown(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def html_to_markdown(value: str | None) -> str:
    if not value:
        return ""
    if "<" not in value or ">" not in value:
        return value.strip()
    parser = HTMLToMarkdownParser()
    parser.feed(value)
    parser.close()
    return parser.markdown()
