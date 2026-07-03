#!/usr/bin/env python
"""Thin shim for ad-hoc dev runs of `aacli book`.

Re-exports `abstractatlas.book.cli:main` so contributors can iterate
without the `aacli` dispatch indirection. Matches the pattern of
`scripts/run_enrich_abstracts.py`.

Usage (from repo root):

    PYTHONPATH=src .venv/bin/python scripts/run_build_book.py \
        --format pdf --sort poster_id
"""

from __future__ import annotations

import sys

from abstractatlas.book.cli import main


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
