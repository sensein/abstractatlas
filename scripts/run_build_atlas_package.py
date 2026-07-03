#!/usr/bin/env python3
"""Stage 15 entry-point wrapper — build neuroscape.parquet +
atlas.parquet from the NeuroScape v1.0.1 release + the OHBM 2026
voyage_stage2_published recipe.

Canonical invocation from a fresh repo:

    PYTHONPATH=src .venv/bin/python scripts/run_build_atlas_package.py [options]

This wrapper exists so the README's Stage 15 section has a single
copy-pasteable invocation that does not depend on the ``aacli``
entry point's installation state. It forwards ``sys.argv[1:]`` to
:func:`abstractatlas.atlas_package.cli.main` and returns its exit code.

All flags + exit codes are documented in
``specs/015-neuroscape-context/contracts/cli-build-atlas-package.md``
and exercised by ``tests/test_atlas_cli.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
if _SRC_DIR.exists() and str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from abstractatlas.atlas_package.cli import main  # noqa: E402  (post sys.path setup)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
