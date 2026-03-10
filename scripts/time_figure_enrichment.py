from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from ohbm2026.enrichment import DEFAULT_VISION_MODEL, analyze_figures, load_json


def collect_candidate_assets(database: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for abstract in database.get("abstracts", []):
        for asset in abstract.get("local_assets", []):
            local_path = asset.get("local_path")
            if not local_path:
                continue
            path = Path(local_path)
            if not path.exists():
                continue
            candidates.append(
                {
                    "abstract_id": abstract.get("id"),
                    "question_name": asset.get("source_question_name"),
                    "local_path": str(path),
                }
            )
    return candidates


def build_subset_database(sampled_assets: list[dict[str, Any]]) -> dict[str, Any]:
    abstracts = []
    for index, asset in enumerate(sampled_assets, start=1):
        abstracts.append(
            {
                "id": asset["abstract_id"],
                "title": f"Benchmark Abstract {index}",
                "local_assets": [
                    {
                        "source_question_name": asset["question_name"],
                        "local_path": asset["local_path"],
                    }
                ],
            }
        )
    return {"abstracts": abstracts}


def benchmark_counts(
    database: dict[str, Any],
    counts: list[int],
    model: str,
    seed: int,
    start_index: int,
) -> dict[str, Any]:
    candidates = collect_candidate_assets(database)
    if not candidates:
        raise RuntimeError("No local figure assets found in input database")

    max_count = max(counts)
    if len(candidates) < max_count:
        raise RuntimeError(f"Requested up to {max_count} figures but only found {len(candidates)} local figures")

    rng = random.Random(seed)
    shuffled = candidates[:]
    rng.shuffle(shuffled)

    results = []
    for count in counts:
        sampled_assets = shuffled[start_index : start_index + count]
        subset_database = build_subset_database(sampled_assets)
        print(f"Starting benchmark for {count} figure(s)...", file=sys.stderr, flush=True)
        with tempfile.TemporaryDirectory(prefix=f"ohbm26-figure-bench-{count}-") as temp_dir:
            cache_path = Path(temp_dir) / "image_analyses.json"
            started = time.perf_counter()
            cache = analyze_figures(
                subset_database,
                cache_path,
                model=model,
                pull_model_if_missing=False,
                max_images=None,
            )
            elapsed = time.perf_counter() - started
        result = {
            "figure_count": count,
            "elapsed_seconds": round(elapsed, 3),
            "seconds_per_figure": round(elapsed / count, 3),
            "analysis_count": len(cache.get("analyses", {})),
            "sample": sampled_assets,
        }
        print(json.dumps(result), file=sys.stderr, flush=True)
        results.append(result)

    return {
        "model": model,
        "seed": seed,
        "start_index": start_index,
        "available_local_figures": len(candidates),
        "results": results,
    }


def benchmark_individual_prefix(
    database: dict[str, Any],
    counts: list[int],
    model: str,
    seed: int,
    start_index: int,
) -> dict[str, Any]:
    candidates = collect_candidate_assets(database)
    if not candidates:
        raise RuntimeError("No local figure assets found in input database")

    max_count = max(counts)
    end_index = start_index + max_count
    if len(candidates) < end_index:
        raise RuntimeError(f"Requested up to index {end_index - 1} but only found {len(candidates)} local figures")

    rng = random.Random(seed)
    shuffled = candidates[:]
    rng.shuffle(shuffled)

    per_figure_results = []
    for offset, asset in enumerate(shuffled[start_index:end_index], start=start_index):
        subset_database = build_subset_database([asset])
        print(f"Starting benchmark for figure index {offset}...", file=sys.stderr, flush=True)
        with tempfile.TemporaryDirectory(prefix=f"ohbm26-figure-bench-{offset}-") as temp_dir:
            cache_path = Path(temp_dir) / "image_analyses.json"
            started = time.perf_counter()
            cache = analyze_figures(
                subset_database,
                cache_path,
                model=model,
                pull_model_if_missing=False,
                max_images=None,
            )
            elapsed = time.perf_counter() - started
        result = {
            "figure_index": offset,
            "elapsed_seconds": round(elapsed, 3),
            "analysis_count": len(cache.get("analyses", {})),
            "sample": asset,
        }
        print(json.dumps(result), file=sys.stderr, flush=True)
        per_figure_results.append(result)

    cumulative_results = []
    for count in counts:
        selected = per_figure_results[:count]
        elapsed = sum(item["elapsed_seconds"] for item in selected)
        cumulative_results.append(
            {
                "figure_count": count,
                "elapsed_seconds": round(elapsed, 3),
                "seconds_per_figure": round(elapsed / count, 3),
                "analysis_count": count,
                "sample": [item["sample"] for item in selected],
            }
        )

    return {
        "model": model,
        "seed": seed,
        "start_index": start_index,
        "mode": "individual-prefix",
        "available_local_figures": len(candidates),
        "per_figure_results": per_figure_results,
        "results": cumulative_results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark local figure enrichment timing")
    parser.add_argument("--input", default="data/abstracts_enriched.json")
    parser.add_argument("--counts", nargs="+", type=int, default=[1, 2, 5, 10])
    parser.add_argument("--seed", type=int, default=20260309)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--model", default=DEFAULT_VISION_MODEL)
    parser.add_argument("--output", default=None)
    parser.add_argument("--individual-prefix", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database = load_json(Path(args.input))
    if args.individual_prefix:
        payload = benchmark_individual_prefix(database, args.counts, args.model, args.seed, args.start_index)
    else:
        payload = benchmark_counts(database, args.counts, args.model, args.seed, args.start_index)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
