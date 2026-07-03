"""Stage 4 typed exception hierarchy — re-export surface.

The class definitions live in `abstractatlas.exceptions` next to the other
per-stage error hierarchies (`Stage1Error`, `Stage2Error`, `Stage3Error`)
so the project-wide import surface stays uniform. This module
re-exports them so Stage 4 callers can `from abstractatlas.analyze.errors
import AnalysisError` instead of reaching into `exceptions`.
"""

from __future__ import annotations

from abstractatlas.exceptions import (
    AnalysisError,
    CentroidTableMissing,
    CentroidTableVersionMismatch,
    CommunityResolutionDegenerate,
    InputBundleMissing,
    ProjectionDimensionMismatch,
    TopicGroupingHallucination,
    UnsupportedProjectionAlgorithm,
)

__all__ = [
    "AnalysisError",
    "CentroidTableMissing",
    "CentroidTableVersionMismatch",
    "CommunityResolutionDegenerate",
    "InputBundleMissing",
    "ProjectionDimensionMismatch",
    "TopicGroupingHallucination",
    "UnsupportedProjectionAlgorithm",
]
