"""CLI wrapper for the Stage 15 atlas-package build.

Spec: ``specs/015-neuroscape-context/`` —
``contracts/cli-build-atlas-package.md``.

Exposed entry points:

- :func:`build_parser` — returns the argparse parser the
  top-level ``ohbmcli`` dispatches into. Subcommand name in the
  parent CLI is ``build-atlas-package``.
- :func:`main` — argv-driven dispatch. Returns the documented
  exit code (0 success, 2..7 per typed exception).

The CLI loads the OHBM 2026 corpus by:

1. Reading ``ohbm2026.parquet``'s manifest row to recover the
   corpus ``state_key``.
2. Reading the abstracts row group to recover ``(submission_id,
   poster_id, title)`` triples.
3. Calling :func:`ohbm2026.embed.compose.compose_recipe` with the
   five-component voyage_stage2_published recipe to land the
   per-abstract Stage-2 vectors.
4. Joining the two by ``submission_id``.

The result is the ``list[OhbmInputRecord]`` the orchestrator
expects.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from ohbm2026.exceptions import (
    AtlasLinkCheckError,
    AtlasProvenanceError,
    CrossParquetDriftError,
    NeuroScapeInputError,
    OhbmProjectionError,
    UmapFitError,
)

from .orchestrator import (
    AtlasBuildConfig,
    OhbmInputRecord,
    build_atlas_package,
)
from . import umap_fit
from .provenance import normalise_path


__all__ = [
    "build_parser",
    "main",
    "load_ohbm_corpus",
    "read_ohbm2026_state_key",
]


# Standard five-component voyage_stage2_published recipe per
# CLAUDE.md memory — mean of {title, introduction, methods, results,
# conclusion} of the NeuroScape Stage-2 per-component bundles.
_STAGE2_RECIPE = ("title", "introduction", "methods", "results", "conclusion")


# ---------------------------------------------------------------------------
# Argparse surface
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for ``build-atlas-package``.

    Argument names match ``contracts/cli-build-atlas-package.md``.
    Defaults match the contract too.
    """

    p = argparse.ArgumentParser(
        prog="build-atlas-package",
        description=(
            "Stage 15 — build the three-parquet atlas package "
            "(ohbm2026.parquet renamed + new neuroscape.parquet + "
            "new atlas.parquet) from the NeuroScape v1.0.1 release "
            "+ the OHBM 2026 voyage_stage2_published recipe."
        ),
    )
    p.add_argument(
        "--neuroscape-source",
        type=Path,
        required=True,
        help="Unzipped NeuroScape v1.0.1 release root (gitignored).",
    )
    p.add_argument(
        "--voyage-bundle",
        default="voyage_stage2_published",
        help="Voyage→Stage-2 recipe id used to project the OHBM 2026 overlay.",
    )
    p.add_argument(
        "--ohbm2026-parquet",
        type=Path,
        required=True,
        help="Path to the canonical (renamed) ohbm2026.parquet — its manifest's state_key is embedded into atlas.parquet's sibling_state_keys.",
    )
    p.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Directory to write neuroscape.parquet + atlas.parquet + provenance into.",
    )
    p.add_argument(
        "--umap-cache-root",
        type=Path,
        default=Path("data/cache/atlas-umap"),
        help="UMAP fit cache root.",
    )
    p.add_argument(
        "--projection-cache-root",
        type=Path,
        default=Path("data/cache/atlas-projection"),
        help="Per-OHBM-2026-abstract projection cache root.",
    )
    p.add_argument(
        "--decimated-backdrop-size",
        type=int,
        default=50_000,
        help="Target row count for the decimated backdrop in atlas.parquet (R-011).",
    )
    p.add_argument(
        "--neighbors-k",
        type=int,
        default=20,
        help="k for the NeuroScape k-NN table (R-008).",
    )
    p.add_argument(
        "--link-check-rate",
        type=float,
        default=3.0,
        help="Requests/second for the fixed-set build-time link check (R-013).",
    )
    p.add_argument(
        "--ncbi-api-key-env",
        default="NCBI_API_KEY",
        help="Env var name to read the NCBI API key from (unused by link_check at present; reserved for future rate-limit raise).",
    )
    p.add_argument(
        "--force-rebuild",
        choices=("umap", "projection", "neighbors", "all"),
        default=None,
        help="Invalidate the named cache region (and downstream) before this run.",
    )
    p.add_argument(
        "--no-link-check",
        action="store_true",
        help="Skip the build-time link check. DEV ONLY — refused under CI=true.",
    )
    return p


# ---------------------------------------------------------------------------
# OHBM corpus loader
# ---------------------------------------------------------------------------


def read_ohbm2026_state_key(ohbm2026_parquet: Path) -> str:
    """Read the ``state_key`` from ``ohbm2026.parquet``'s manifest row.

    Reuses the Stage-10 ``parquet_single`` outer/inner shape: the
    outer table has one ``manifest`` row whose ``table_bytes`` is an
    inner Parquet table with a single ``manifest_json`` string column.
    """

    import pyarrow.parquet as pq

    table = pq.read_table(ohbm2026_parquet)
    names = table.column("table_name").to_pylist()
    bodies = table.column("table_bytes").to_pylist()
    for name, blob in zip(names, bodies):
        if name == "manifest":
            inner = pq.read_table(io.BytesIO(bytes(blob)))
            manifest = json.loads(inner.column("manifest_json").to_pylist()[0])
            return str(manifest.get("build_info", {}).get("state_key", ""))
    raise NeuroScapeInputError(
        "ohbm2026.parquet has no manifest row",
        file=str(ohbm2026_parquet),
        expected="manifest outer row",
        actual="<missing>",
    )


def _read_ohbm_articles(
    ohbm2026_parquet: Path,
) -> dict[int, tuple[int, str]]:
    """Read ``(poster_id, title)`` for every abstract in ``ohbm2026.parquet``,
    keyed by submission_id.
    """

    import pyarrow.parquet as pq

    table = pq.read_table(ohbm2026_parquet)
    names = table.column("table_name").to_pylist()
    bodies = table.column("table_bytes").to_pylist()
    for name, blob in zip(names, bodies):
        if name == "abstracts":
            inner = pq.read_table(io.BytesIO(bytes(blob)))
            # Stage 10 schema: the abstracts inner table carries
            # `submission_id` (or `id`), `poster_id`, and `title`.
            cols = set(inner.column_names)
            sub_col = "submission_id" if "submission_id" in cols else "id"
            sub_ids = inner.column(sub_col).to_pylist()
            poster_ids = inner.column("poster_id").to_pylist()
            titles = inner.column("title").to_pylist()
            return {
                int(s): (int(p), str(t))
                for s, p, t in zip(sub_ids, poster_ids, titles)
            }
    raise NeuroScapeInputError(
        "ohbm2026.parquet has no abstracts row",
        file=str(ohbm2026_parquet),
        expected="abstracts outer row",
        actual="<missing>",
    )


def load_ohbm_corpus(
    ohbm2026_parquet: Path,
    voyage_bundle_id: str,
    *,
    bundles_root: Path | None = None,
) -> tuple[list[OhbmInputRecord], str]:
    """Build the ``list[OhbmInputRecord]`` the orchestrator expects.

    Returns ``(records, ohbm2026_state_key)``.

    Pulls Stage-2 vectors via the existing
    :func:`ohbm2026.embed.compose.compose_recipe` five-component
    recipe. Abstracts present in ``ohbm2026.parquet`` but missing a
    Stage-2 vector are dropped here — the orchestrator's projector
    would otherwise mark them as failures; dropping at corpus-load
    time keeps the failure semantics tighter (an abstract without a
    Stage-2 vector isn't a *projection* failure, it's an *input*
    omission).
    """

    from ohbm2026.embed.compose import compose_recipe

    ohbm2026_state_key = read_ohbm2026_state_key(ohbm2026_parquet)
    headers = _read_ohbm_articles(ohbm2026_parquet)

    composed = compose_recipe(
        list(_STAGE2_RECIPE),
        model_key="neuroscape",  # 64-dim Stage-2 vectors live here
        bundles_root=bundles_root,
        corpus_state_key=ohbm2026_state_key,
    )
    matrix = np.asarray(composed["matrix"], dtype=np.float32)
    ids = list(composed["ids"])

    records: list[OhbmInputRecord] = []
    for i, sub_id in enumerate(ids):
        sub_id = int(sub_id)
        header = headers.get(sub_id)
        if header is None:
            continue
        poster_id, title = header
        records.append(
            OhbmInputRecord(
                submission_id=sub_id,
                poster_id=poster_id,
                title=title,
                stage2_vector=matrix[i],
            )
        )
    return records, ohbm2026_state_key


# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------


_EXIT_CODES: dict[type[BaseException], int] = {
    NeuroScapeInputError: 2,
    UmapFitError: 3,
    OhbmProjectionError: 4,
    CrossParquetDriftError: 5,
    AtlasProvenanceError: 6,
    AtlasLinkCheckError: 7,
}


def _write_provenance(prov: dict[str, Any]) -> Path:
    """Write the provenance JSON to ``<cwd>/data/provenance/...``.

    Filename follows the contract's
    ``neuroscape_context_provenance__<state-key>.json`` pattern. The
    parent directory is resolved against ``Path.cwd()`` explicitly so
    tests can patch the cwd to a tempdir.
    """

    state_key = prov.get("state_key", "unknown")
    out_dir = Path.cwd() / "data" / "provenance"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"neuroscape_context_provenance__{state_key}.json"
    out_path.write_text(json.dumps(prov, indent=2, sort_keys=True))
    return out_path


def _read_code_revision() -> str:
    """Best-effort ``git rev-parse HEAD``; falls back to ``"unknown"``."""

    import subprocess

    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except Exception:
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    """Argv-driven entry point.

    Returns the exit code documented in
    ``contracts/cli-build-atlas-package.md``.
    """

    parser = build_parser()
    args = parser.parse_args(argv)

    # `--no-link-check` is refused under CI per the contract.
    if args.no_link_check:
        import os

        if os.environ.get("CI", "").strip().lower() in ("1", "true", "yes"):
            sys.stderr.write(
                "build-atlas-package: --no-link-check is refused under CI=true "
                "(contracts/cli-build-atlas-package.md).\n"
            )
            return 7

    command_line = " ".join(["ohbmcli", "build-atlas-package", *(argv or sys.argv[1:])])

    try:
        ohbm_records, ohbm2026_state_key = load_ohbm_corpus(
            args.ohbm2026_parquet, args.voyage_bundle
        )

        cfg = AtlasBuildConfig(
            neuroscape_source_root=args.neuroscape_source,
            ohbm_corpus=ohbm_records,
            ohbm2026_state_key=ohbm2026_state_key,
            output_root=args.output_root,
            cache_root=args.umap_cache_root.parent,
            voyage_bundle_id=args.voyage_bundle,
            decimated_backdrop_size=args.decimated_backdrop_size,
            neighbors_k=args.neighbors_k,
            link_check_rate=args.link_check_rate,
            skip_link_check=args.no_link_check,
            code_revision=_read_code_revision(),
            command_line=command_line,
        )
        prov = build_atlas_package(cfg)
        _write_provenance(prov)
        return 0
    except tuple(_EXIT_CODES.keys()) as exc:  # type: ignore[misc]
        code = _EXIT_CODES[type(exc)]
        sys.stderr.write(f"build-atlas-package: {type(exc).__name__}: {exc}\n")
        return code


if __name__ == "__main__":
    raise SystemExit(main())
