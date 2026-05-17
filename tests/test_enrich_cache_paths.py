"""Tests for `ohbm2026.enrich.cache_paths` (Stage 5 / US1).

Covers `default_image_analysis_cache_path` + `default_claim_analysis_cache_path` —
the canonical cache-path helpers moved out of the legacy `enrichment.py`.
"""

from __future__ import annotations

import unittest
from pathlib import Path

# Warmup import to break the exceptions ↔ fetch circular cycle.
from ohbm2026.analyze import stage as _stage_warmup  # noqa: F401

from ohbm2026.enrich.cache_paths import (
    DEFAULT_CLLM_ANTHROPIC_MODEL,
    DEFAULT_CLLM_OPENAI_MODEL,
    DEFAULT_OPENAI_VISION_MODEL,
    DEFAULT_VISION_MODEL,
    default_claim_analysis_cache_path,
    default_image_analysis_cache_path,
)


class DefaultImageAnalysisCachePathTests(unittest.TestCase):
    def test_returns_path_under_figure_analysis(self) -> None:
        p = default_image_analysis_cache_path()
        self.assertIsInstance(p, Path)
        self.assertIn("figure_analysis", str(p))

    def test_openai_backend_carries_openai_in_filename(self) -> None:
        p = default_image_analysis_cache_path(backend="openai")
        self.assertIn("openai", str(p))

    def test_ollama_backend_carries_ollama_in_filename(self) -> None:
        p = default_image_analysis_cache_path(backend="ollama")
        self.assertIn("ollama", str(p))

    def test_deterministic_for_same_inputs(self) -> None:
        p1 = default_image_analysis_cache_path(backend="openai")
        p2 = default_image_analysis_cache_path(backend="openai")
        self.assertEqual(str(p1), str(p2))

    def test_different_backends_produce_different_paths(self) -> None:
        a = default_image_analysis_cache_path(backend="openai")
        b = default_image_analysis_cache_path(backend="ollama")
        self.assertNotEqual(str(a), str(b))


class DefaultClaimAnalysisCachePathTests(unittest.TestCase):
    def test_returns_path_under_claim_analysis(self) -> None:
        p = default_claim_analysis_cache_path()
        self.assertIsInstance(p, Path)
        self.assertIn("claim_analysis", str(p))

    def test_deterministic(self) -> None:
        p1 = default_claim_analysis_cache_path()
        p2 = default_claim_analysis_cache_path()
        self.assertEqual(str(p1), str(p2))


class ConstantsTests(unittest.TestCase):
    def test_constants_are_nonempty_strings(self) -> None:
        for c in (
            DEFAULT_VISION_MODEL,
            DEFAULT_OPENAI_VISION_MODEL,
            DEFAULT_CLLM_OPENAI_MODEL,
            DEFAULT_CLLM_ANTHROPIC_MODEL,
        ):
            self.assertIsInstance(c, str)
            self.assertTrue(c.strip())


if __name__ == "__main__":
    unittest.main()
