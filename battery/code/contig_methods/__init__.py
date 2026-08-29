"""
contig_methods -- plug-in contiguity solvers for the benchmark harness.

REGISTRY is built by auto-discovery: every module in this package that exposes `NAME` and
`solve` is registered under NAME, and under `f"{NAME}_{variant}"`-style keys given in its
optional `VARIANTS = {key: {kwargs}}` mapping (the key is used verbatim).  See base.py for
the contract.

    from contig_methods import REGISTRY
    spec = REGISTRY["current"]
    res = base.run_method(spec.solve, G, nodes, time_limit=60, **spec.kwargs)
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Callable, Optional

from . import base  # noqa: F401  (re-exported for convenience)


@dataclass(frozen=True)
class MethodSpec:
    name: str                 # registry key
    base_name: str            # module NAME
    module: str               # dotted module name
    solve: Callable
    exact: bool
    max_n: Optional[int] = None
    kwargs: dict = field(default_factory=dict)   # variant options passed to solve(**opts)


def discover() -> dict:
    reg: dict[str, MethodSpec] = {}
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_") or info.name == "base":
            continue
        mod = importlib.import_module(f"{__name__}.{info.name}")
        name = getattr(mod, "NAME", None)
        solve = getattr(mod, "solve", None)
        if name is None or solve is None:
            continue
        exact = bool(getattr(mod, "EXACT", False))
        max_n = getattr(mod, "MAX_N", None)
        if name in reg:
            raise RuntimeError(f"duplicate method NAME {name!r} ({mod.__name__} vs {reg[name].module})")
        reg[name] = MethodSpec(name, name, mod.__name__, solve, exact, max_n)
        for key, kw in (getattr(mod, "VARIANTS", None) or {}).items():
            if key in reg:
                raise RuntimeError(f"duplicate registry key {key!r} from {mod.__name__}")
            reg[key] = MethodSpec(key, name, mod.__name__, solve, exact, max_n, dict(kw))
    return reg


REGISTRY: dict[str, MethodSpec] = discover()

__all__ = ["REGISTRY", "MethodSpec", "discover", "base"]
