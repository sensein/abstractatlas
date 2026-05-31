"""Tests for Stage 20 content-addressed key derivation.

Spec: ``specs/020-cloudflare-r2-migration/`` — research R-1, data-model
validation table.
"""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ohbm2026.atlas_hosting import content_hash


class Sha256FileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_streamed_hash_matches_whole_file_hash(self) -> None:
        # Use > 1 MiB so the chunked read loops more than once.
        payload = b"neuroscape" * (200 * 1024)  # ~2 MiB
        path = self.root / "neuroscape.parquet"
        path.write_bytes(payload)
        self.assertEqual(
            content_hash.sha256_file(path),
            hashlib.sha256(payload).hexdigest(),
        )

    def test_empty_file_hash(self) -> None:
        path = self.root / "empty.parquet"
        path.write_bytes(b"")
        self.assertEqual(
            content_hash.sha256_file(path),
            hashlib.sha256(b"").hexdigest(),
        )


class DeriveObjectKeyTests(unittest.TestCase):
    def test_key_is_sha_then_filename(self) -> None:
        sha = "a" * 64
        self.assertEqual(
            content_hash.derive_object_key(sha, "atlas.parquet"),
            f"{sha}/atlas.parquet",
        )

    def test_prefix_is_normalised(self) -> None:
        sha = "b" * 64
        self.assertEqual(
            content_hash.derive_object_key(sha, "atlas.parquet", prefix="/atlas/"),
            f"atlas/{sha}/atlas.parquet",
        )
        # Empty prefix yields no leading segment.
        self.assertEqual(
            content_hash.derive_object_key(sha, "atlas.parquet", prefix=""),
            f"{sha}/atlas.parquet",
        )

    def test_identical_bytes_same_key_distinct_bytes_distinct_key(self) -> None:
        sha_a = hashlib.sha256(b"same").hexdigest()
        sha_a2 = hashlib.sha256(b"same").hexdigest()
        sha_b = hashlib.sha256(b"different").hexdigest()
        self.assertEqual(
            content_hash.derive_object_key(sha_a, "x.parquet"),
            content_hash.derive_object_key(sha_a2, "x.parquet"),
        )
        self.assertNotEqual(
            content_hash.derive_object_key(sha_a, "x.parquet"),
            content_hash.derive_object_key(sha_b, "x.parquet"),
        )


class PublicUrlTests(unittest.TestCase):
    def test_joins_with_single_slash(self) -> None:
        self.assertEqual(
            content_hash.public_url(
                "https://aadata.cirrusscience.org/", "/abc/atlas.parquet"
            ),
            "https://aadata.cirrusscience.org/abc/atlas.parquet",
        )
        self.assertEqual(
            content_hash.public_url(
                "https://aadata.cirrusscience.org", "abc/atlas.parquet"
            ),
            "https://aadata.cirrusscience.org/abc/atlas.parquet",
        )


if __name__ == "__main__":
    unittest.main()
