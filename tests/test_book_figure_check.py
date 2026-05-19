"""T014 — Pillow figure-resolution probe + DPI helper."""

from __future__ import annotations

import pathlib
import tempfile
import unittest

from ohbm2026.book.figure_check import (
    PUBLICATION_DPI_THRESHOLD,
    effective_dpi,
    probe_figure,
)

_FIX = pathlib.Path(__file__).parent / "fixtures" / "book" / "assets"


class TestProbeFigure(unittest.TestCase):
    def test_probes_real_png(self) -> None:
        w, h, err = probe_figure(_FIX / "9000001_methods.png")
        self.assertEqual(err, None)
        self.assertEqual(w, 2400)
        self.assertEqual(h, 2400)

    def test_missing_returns_asset_missing(self) -> None:
        w, h, err = probe_figure(_FIX / "_definitely_not_here.png")
        self.assertEqual((w, h), (None, None))
        self.assertEqual(err, "asset missing")

    def test_unreadable_returns_typed_error(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"this is not a PNG file")
            corrupt = pathlib.Path(f.name)
        try:
            w, h, err = probe_figure(corrupt)
            self.assertEqual((w, h), (None, None))
            self.assertTrue(
                err and err.startswith("unreadable:"),
                f"expected unreadable: prefix, got {err!r}",
            )
        finally:
            corrupt.unlink(missing_ok=True)


class TestEffectiveDpi(unittest.TestCase):
    def test_dpi_math(self) -> None:
        self.assertAlmostEqual(effective_dpi(3000, 6.5), 461.538, places=2)

    def test_fixture_clears_300dpi_at_letter_body_width(self) -> None:
        # 2400 px / 6.5 in ≈ 369.2 DPI — clears the 300 DPI threshold.
        self.assertGreaterEqual(
            effective_dpi(2400, 6.5), PUBLICATION_DPI_THRESHOLD
        )

    def test_below_threshold(self) -> None:
        # 1500 px / 6.5 in ≈ 230.8 DPI — below threshold.
        self.assertLess(effective_dpi(1500, 6.5), PUBLICATION_DPI_THRESHOLD)

    def test_zero_width_rejected(self) -> None:
        with self.assertRaises(ValueError):
            effective_dpi(2400, 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
