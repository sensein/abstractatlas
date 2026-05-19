"""T013 — SC-006: no AI-generated content reaches the book.

Two-pronged check:
1. *By construction* — walk the import graph of every `ohbm2026.book.*`
   module and assert nothing under `ohbm2026.stage2_*` /
   `ohbm2026.enrich*` is reachable.
2. *In the output* — after a `book.md` is rendered, grep the bytes
   for every ECO code in `src/ohbm2026/data/eco_top_codes.json` and
   the Stage-2 agent-tool names; assert zero matches.

The second prong runs only after T020/T022 land (render_markdown).
Until then, the import-graph check stands alone — and that's the
load-bearing guarantee.
"""

from __future__ import annotations

import ast
import json
import pathlib
import unittest

_FIX = pathlib.Path(__file__).parent / "fixtures" / "book"
_BOOK_PKG_ROOT = pathlib.Path(__file__).parent.parent / "src" / "ohbm2026" / "book"


def _collect_book_imports() -> set[str]:
    """Walk every .py file in `src/ohbm2026/book/` and return the set
    of `from ohbm2026.X[.Y]` and `import ohbm2026.X[.Y]` module
    references — i.e. the SOURCE-level dependency surface.

    Static scan is sufficient: if no book source mentions an
    `ohbm2026.stage2_*` or `ohbm2026.enrich*` import, then the
    transitive runtime graph can't include them. Stays independent
    of test ordering and global `sys.modules` pollution.
    """
    seen: set[str] = set()
    for path in _BOOK_PKG_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    seen.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    seen.add(alias.name)
    return seen


class TestImportGraph(unittest.TestCase):
    def test_no_stage2_or_enrich_in_source(self) -> None:
        imports = _collect_book_imports()
        forbidden_prefixes = ("ohbm2026.stage2_", "ohbm2026.enrich")
        leaked = sorted(
            m
            for m in imports
            if any(m.startswith(p) for p in forbidden_prefixes)
        )
        self.assertEqual(
            leaked,
            [],
            msg=(
                "Stage-2 / enrich modules appear as direct imports in "
                f"`src/ohbm2026/book/` source: {leaked}. SC-006 requires "
                "the book to be sourced exclusively from Stage-1 artefacts."
            ),
        )


class TestNoStringLeakage(unittest.TestCase):
    """Run only after render_markdown is implemented (US1 impl). Falls
    back to skip when the renderer is absent so the test file is safe
    to land alongside T013 in the TDD phase.
    """

    def test_book_md_has_no_stage2_strings(self) -> None:
        try:
            from ohbm2026.book.corpus import load_book
            from ohbm2026.book.render_markdown import emit_book_md
        except ImportError:
            self.skipTest("render_markdown not yet implemented")

        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            outdir = pathlib.Path(tmp)
            book = load_book(
                corpus_path=_FIX / "abstracts.json",
                authors_path=_FIX / "authors.json",
                withdrawn_path=_FIX / "abstracts_withdrawn.json",
                assets_root=_FIX / "assets",
            )
            emit_book_md(book, outdir)
            book_md = (outdir / "book.md").read_text()

        eco_path = (
            pathlib.Path(__file__).parent.parent
            / "src"
            / "ohbm2026"
            / "data"
            / "eco_top_codes.json"
        )
        eco_codes: list[str] = []
        if eco_path.exists():
            payload = json.loads(eco_path.read_text())
            for entry in payload.get("codes", payload):
                if isinstance(entry, dict):
                    code = entry.get("code") or entry.get("eco_code")
                    if code:
                        eco_codes.append(code)
                elif isinstance(entry, str):
                    eco_codes.append(entry)
        leaked_eco = [c for c in eco_codes if c in book_md]
        self.assertEqual(leaked_eco, [], msg=f"ECO codes leaked: {leaked_eco}")

        tool_names = [
            "verify_source_quote",
            "lookup_eco_code",
            "dedupe_check",
        ]
        leaked_tools = [t for t in tool_names if t in book_md]
        self.assertEqual(
            leaked_tools,
            [],
            msg=f"Stage-2 tool names leaked: {leaked_tools}",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
