"""td.solvers -- MILP engines and the harness contract they implement.

The registry is an **explicit** dict.  It used to auto-discover every module in this package
via `pkgutil.iter_modules`, which meant importing the package executed every sibling: that is
how `bounds.py`'s module-level `import territory` made the whole package depend on the legacy
two-player solver, and it silently re-arms every time a file is added.  With three engines and
no method bake-off left, listing them is both simpler and safer.

To add an engine: implement `solve` per `base.py`, then add a `_spec(...)` line below.

`scip_tree` imports `pyscipopt` at module scope and SCIP may not be installed, so it is
registered through a guarded import.  Its absence degrades the registry; it does not break it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from . import base  # noqa: F401  (re-exported for convenience)


@dataclass(frozen=True)
class MethodSpec:
    name: str                 # registry key
    base_name: str            # the engine's own NAME
    module: str               # dotted module name
    solve: Callable
    exact: bool
    max_n: Optional[int] = None
    kwargs: dict = field(default_factory=dict)   # variant options passed to solve(**opts)


def _build() -> dict:
    reg: dict[str, MethodSpec] = {}

    def add(mod, *, only=None):
        name, solve = getattr(mod, "NAME"), getattr(mod, "solve")
        exact, max_n = bool(getattr(mod, "EXACT", False)), getattr(mod, "MAX_N", None)
        if only is None or name in only:
            reg[name] = MethodSpec(name, name, mod.__name__, solve, exact, max_n)
        for key, kw in (getattr(mod, "VARIANTS", None) or {}).items():
            reg[key] = MethodSpec(key, name, mod.__name__, solve, exact, max_n, dict(kw))

    from . import brute
    add(brute)

    try:                                    # needs a SCIP build on the machine
        from . import scip_tree
    except ImportError:                     # noqa: S110 -- absence is a degraded registry
        pass
    else:
        add(scip_tree)

    return reg


REGISTRY: dict[str, MethodSpec] = _build()

__all__ = ["REGISTRY", "MethodSpec", "base"]
