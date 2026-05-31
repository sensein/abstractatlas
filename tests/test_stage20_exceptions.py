"""Tests for Stage 20's typed exception hierarchy.

Spec: ``specs/020-cloudflare-r2-migration/`` — research R-9. Mirrors the
Stage 15 pattern (``tests/test_atlas_exceptions.py``) so the Stage 20
import surface stays auditable.

The Stage 20 subtree extends ``OhbmStageError`` with one base
(``Stage20Error``) and five concrete error classes. Each concrete class
carries structured kwargs so the uploader / compare CLI and tests can
inspect failure context without regex-matching message strings.
"""

from __future__ import annotations

import unittest

from ohbm2026 import exceptions


class Stage20ExceptionTreeTests(unittest.TestCase):
    def test_stage20_base_is_a_runtimeerror(self) -> None:
        self.assertTrue(issubclass(exceptions.Stage20Error, exceptions.OhbmStageError))
        self.assertTrue(issubclass(exceptions.Stage20Error, RuntimeError))

    def test_concrete_classes_subclass_stage20(self) -> None:
        for cls in (
            exceptions.R2CredentialsError,
            exceptions.R2UploadError,
            exceptions.ContentHashMismatchError,
            exceptions.ArtifactDiscoveryError,
            exceptions.HostingComparisonError,
        ):
            with self.subTest(cls=cls.__name__):
                self.assertTrue(issubclass(cls, exceptions.Stage20Error))

    def test_all_public_names_exported(self) -> None:
        expected = {
            "Stage20Error",
            "R2CredentialsError",
            "R2UploadError",
            "ContentHashMismatchError",
            "ArtifactDiscoveryError",
            "HostingComparisonError",
        }
        self.assertTrue(expected.issubset(set(exceptions.__all__)))


class R2CredentialsErrorContextTests(unittest.TestCase):
    def test_carries_var_kwarg(self) -> None:
        err = exceptions.R2CredentialsError("missing", var="R2_BUCKET")
        self.assertEqual(err.var, "R2_BUCKET")


class R2UploadErrorContextTests(unittest.TestCase):
    def test_carries_key_bucket_op_reason(self) -> None:
        err = exceptions.R2UploadError(
            "PUT failed",
            key="abc/neuroscape.parquet",
            bucket="aadata",
            op="upload",
            reason="AccessDenied",
        )
        self.assertEqual(err.key, "abc/neuroscape.parquet")
        self.assertEqual(err.bucket, "aadata")
        self.assertEqual(err.op, "upload")
        self.assertEqual(err.reason, "AccessDenied")


class ContentHashMismatchErrorContextTests(unittest.TestCase):
    def test_carries_key_expected_actual(self) -> None:
        err = exceptions.ContentHashMismatchError(
            "size mismatch at content-addressed key",
            key="abc/atlas.parquet",
            expected="1024",
            actual="2048",
        )
        self.assertEqual(err.key, "abc/atlas.parquet")
        self.assertEqual(err.expected, "1024")
        self.assertEqual(err.actual, "2048")


class ArtifactDiscoveryErrorContextTests(unittest.TestCase):
    def test_carries_path_missing_unexpected(self) -> None:
        err = exceptions.ArtifactDiscoveryError(
            "package dir mismatch",
            path="data/outputs/atlas-package__abc",
            missing=["atlas.parquet"],
            unexpected=["stray.parquet"],
        )
        self.assertEqual(err.path, "data/outputs/atlas-package__abc")
        self.assertEqual(err.missing, ["atlas.parquet"])
        self.assertEqual(err.unexpected, ["stray.parquet"])


class HostingComparisonErrorContextTests(unittest.TestCase):
    def test_carries_url_probe_reason(self) -> None:
        err = exceptions.HostingComparisonError(
            "cannot probe",
            url="https://example.invalid/x.parquet",
            probe="range",
            reason="malformed_url",
        )
        self.assertEqual(err.url, "https://example.invalid/x.parquet")
        self.assertEqual(err.probe, "range")
        self.assertEqual(err.reason, "malformed_url")


if __name__ == "__main__":
    unittest.main()
