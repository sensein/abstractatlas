"""Deprecated shim: the ``ohbm2026`` package was renamed to ``abstractatlas``
(spec 027). Importing ``ohbm2026`` or any ``ohbm2026.*`` submodule warns with
a clear rename pointer and transparently redirects to the ``abstractatlas``
equivalent, so existing external scripts keep working for one transition
cycle.

FOLLOW-UP (root cause: package rename): delete ``src/ohbm2026/`` once no
external caller imports the old name. This shim exists only to satisfy the
"legacy name → clear pointer, never a silent/partial failure" guarantee
(spec 027 FR-003 / SC-007). The canonical package is ``abstractatlas``.
"""

from __future__ import annotations

import importlib
import sys
import warnings
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec

warnings.warn(
    "The 'ohbm2026' package was renamed to 'abstractatlas'; update your imports "
    "(e.g. 'from abstractatlas.X import Y'). This compatibility shim will be "
    "removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

_OLD = "ohbm2026"
_NEW = "abstractatlas"


class _RedirectLoader(Loader):
    def __init__(self, target: str) -> None:
        self._target = target

    def create_module(self, spec: ModuleSpec):  # noqa: D401
        module = importlib.import_module(self._target)
        sys.modules[spec.name] = module
        return module

    def exec_module(self, module) -> None:  # already executed on import
        return None


class _RedirectFinder(MetaPathFinder):
    """Map ``ohbm2026`` / ``ohbm2026.*`` onto ``abstractatlas`` / ``abstractatlas.*``."""

    def find_spec(self, fullname: str, path=None, target=None):  # noqa: D401
        if fullname == _OLD or fullname.startswith(_OLD + "."):
            redirected = _NEW + fullname[len(_OLD) :]
            return ModuleSpec(fullname, _RedirectLoader(redirected))
        return None


sys.meta_path.insert(0, _RedirectFinder())
# Alias the top-level package object itself to abstractatlas.
sys.modules[__name__] = importlib.import_module(_NEW)
