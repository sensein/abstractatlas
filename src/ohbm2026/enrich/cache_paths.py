"""Canonical cache-path helpers + JSON I/O for the Stage 2 enrichment pipeline.

Lifted verbatim from the legacy `src/ohbm2026/enrichment.py` as part of
the Stage 5 package reorganization (specs/007-package-reorg/). Leaf
module: stdlib + `ohbm2026.artifacts` (which is also a leaf utility).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ohbm2026 import artifacts

# Default model identifiers — referenced by the cache-path helpers below to
# compute deterministic on-disk locations. Kept here (rather than in a
# separate constants module) so a future contributor finds the cache key's
# inputs alongside the path function.
DEFAULT_VISION_MODEL = "qwen3.5:35b"
DEFAULT_OPENAI_VISION_MODEL = "gpt-4.1-mini"
DEFAULT_CLLM_PROVIDER = "openai"
DEFAULT_CLLM_OPENAI_MODEL = "gpt-4o-2024-08-06"
DEFAULT_CLLM_ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def default_image_analysis_cache_path(
    input_path: Path = artifacts.PRIMARY_ABSTRACTS_PATH,
    *,
    backend: str = "ollama",
    model: str | None = None,
    max_images: int | None = None,
) -> Path:
    resolved_model = model or (DEFAULT_OPENAI_VISION_MODEL if backend == "openai" else DEFAULT_VISION_MODEL)
    basis = artifacts.build_dependency_basis(
        input_sources=[str(input_path)],
        backend=backend,
        model=resolved_model,
        options={"max_images": max_images} if max_images is not None else None,
        env_boundary=["OPENAI_API_KEY"] if backend == "openai" else None,
    )
    return artifacts.build_cache_path("figure_analysis", f"image_analyses_{backend}", artifacts.build_state_key(basis))


def default_claim_analysis_cache_path(
    input_path: Path = artifacts.PRIMARY_ABSTRACTS_PATH,
    *,
    llm_provider: str = DEFAULT_CLLM_PROVIDER,
    model: str | None = None,
    max_abstracts: int | None = None,
) -> Path:
    resolved_model = model or (DEFAULT_CLLM_OPENAI_MODEL if llm_provider == "openai" else DEFAULT_CLLM_ANTHROPIC_MODEL)
    env_boundary = ["OPENAI_API_KEY"] if llm_provider == "openai" else ["ANTHROPIC_API_KEY"]
    basis = artifacts.build_dependency_basis(
        input_sources=[str(input_path)],
        backend=llm_provider,
        model=resolved_model,
        options={"max_abstracts": max_abstracts} if max_abstracts is not None else None,
        env_boundary=env_boundary,
    )
    return artifacts.build_cache_path("claim_analysis", "claim_analyses_cllm", artifacts.build_state_key(basis))


def load_image_analysis_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"analyses": {}, "model": None, "updated_at": None}
    return load_json(path)


def load_claim_analysis_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"analyses": {}, "updated_at": None}
    return load_json(path)


def refresh_analysis_cache_stats(cache: dict[str, Any]) -> None:
    analyses = cache.get("analyses") or {}
    cache["processed_count"] = len(analyses)
    cache["error_count"] = sum(1 for entry in analyses.values() if isinstance(entry, dict) and entry.get("error"))
