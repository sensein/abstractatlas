"""Arc A'.1 — source-scoped artifact paths and state keys.

Per `specs/027-multi-source-foundation/` FR-009: give the artifact layer a
`source` dimension so two corpora can coexist in one data tree, replacing the
implicit single-corpus assumption in `artifacts.py`.

Tests are written first per Principle IV; they MUST fail before the `source`
parameter exists.

THE LOAD-BEARING GUARANTEE, asserted here first: **omitting `source` must
reproduce today's exact paths and today's exact state keys.** Every artifact on
disk was named by the current code; if adding the parameter perturbed the
no-source path or the no-source hash, every cached artifact in every clone
would silently invalidate. The regression tests below pin the current values
literally rather than deriving them, so a future refactor cannot quietly move
them.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from ohbm2026 import artifacts


class TestNoSourceIsUnchanged(unittest.TestCase):
    """Back-compat: the no-source call sites must not move."""

    def test_dependency_basis_without_source_is_unchanged(self) -> None:
        basis = artifacts.build_dependency_basis(
            input_sources=["a", "b"], backend="voyage", model="voyage-3"
        )
        self.assertNotIn("source", basis)
        self.assertEqual(
            basis, {"input_sources": ["a", "b"], "backend": "voyage", "model": "voyage-3"}
        )

    def test_state_key_without_source_is_stable(self) -> None:
        # Pinned literal: this is the hash today's code produces. If this
        # changes, every state-keyed artifact on disk is invalidated.
        basis = artifacts.build_dependency_basis(input_sources=["x"], model="m")
        self.assertEqual(artifacts.build_state_key(basis), "9729952adb87")

    def test_paths_without_source_are_unchanged(self) -> None:
        self.assertEqual(
            artifacts.build_cache_path("fetch_abstracts", "checkpoint", "KEY"),
            Path("data/cache/fetch_abstracts/checkpoint__KEY.json"),
        )
        self.assertEqual(
            artifacts.build_output_path("experiments", "bundle", "KEY"),
            Path("data/outputs/experiments/bundle__KEY"),
        )
        self.assertEqual(
            artifacts.build_input_snapshot_path("abstracts_graphql", "KEY"),
            Path("data/inputs/abstracts_graphql__KEY.json"),
        )
        self.assertEqual(
            artifacts.build_primary_abstracts_path(), artifacts.PRIMARY_ABSTRACTS_PATH
        )


class TestSourceScoping(unittest.TestCase):
    """With an explicit source, artifacts nest under a source segment."""

    def test_dependency_basis_includes_source(self) -> None:
        basis = artifacts.build_dependency_basis(input_sources=["x"], source="biorxiv")
        self.assertEqual(basis["source"], "biorxiv")

    def test_source_changes_the_state_key(self) -> None:
        plain = artifacts.build_state_key(artifacts.build_dependency_basis(input_sources=["x"]))
        scoped = artifacts.build_state_key(
            artifacts.build_dependency_basis(input_sources=["x"], source="biorxiv")
        )
        self.assertNotEqual(plain, scoped)

    def test_two_sources_get_distinct_state_keys(self) -> None:
        a = artifacts.build_state_key(
            artifacts.build_dependency_basis(input_sources=["x"], source="ohbm2026")
        )
        b = artifacts.build_state_key(
            artifacts.build_dependency_basis(input_sources=["x"], source="biorxiv")
        )
        self.assertNotEqual(a, b)

    def test_cache_path_nests_under_source(self) -> None:
        self.assertEqual(
            artifacts.build_cache_path("fetch", "checkpoint", "KEY", source="biorxiv"),
            Path("data/cache/biorxiv/fetch/checkpoint__KEY.json"),
        )

    def test_output_path_nests_under_source(self) -> None:
        self.assertEqual(
            artifacts.build_output_path("experiments", "bundle", "KEY", source="biorxiv"),
            Path("data/outputs/experiments/biorxiv/bundle__KEY"),
        )

    def test_input_snapshot_nests_under_source(self) -> None:
        self.assertEqual(
            artifacts.build_input_snapshot_path("snap", "KEY", source="biorxiv"),
            Path("data/inputs/biorxiv/snap__KEY.json"),
        )

    def test_primary_abstracts_nests_under_source(self) -> None:
        self.assertEqual(
            artifacts.build_primary_abstracts_path(source="biorxiv"),
            Path("data/primary/biorxiv/abstracts.json"),
        )


class TestSourceNameValidation(unittest.TestCase):
    """A source name becomes a path segment, so it must be constrained —
    a separator or traversal component would escape the artifact root."""

    def test_rejects_path_separators(self) -> None:
        for bad in ("a/b", "a\\b"):
            with self.assertRaises(ValueError):
                artifacts.build_cache_path("w", "n", "KEY", source=bad)

    def test_rejects_traversal(self) -> None:
        for bad in ("..", ".", "../etc"):
            with self.assertRaises(ValueError):
                artifacts.build_output_path("experiments", "n", "KEY", source=bad)

    def test_rejects_blank(self) -> None:
        with self.assertRaises(ValueError):
            artifacts.build_input_snapshot_path("n", "KEY", source="   ")

    def test_accepts_ordinary_names(self) -> None:
        for good in ("ohbm2026", "biorxiv", "med_rxiv", "sfn-2027"):
            self.assertIn(good, str(artifacts.build_cache_path("w", "n", "K", source=good)))


if __name__ == "__main__":
    unittest.main()
