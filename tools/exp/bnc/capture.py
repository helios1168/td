"""capture.py -- run `tools/exp/contig/draw.py`'s own `_solve_group` up to its first MILP solve and
keep what it built, so an instance is exactly the model draw.py draws (#142, A0).

`draw._solve_group` builds its MILP inline and solves it in the same function, and `draw.py` is
not ours to change.  `capture_group` therefore swaps the `highspy` module draw.py sees for a shim
whose `Highs.run` reads the model (`getLp`) and the caller's frame (the column maps `col`,
`ycol`, `ccol`, `lcol`, `scol`, `fcol`, which say what each column is) and stops the call.  The
rules (allowed districts, prune, the band, the split, border, moment and land terms, the up-front
neighbour rows) are all draw.py's, none is written again here.

`rebuild_args` is the inverse of `snapshot_args`: stand-ins for `inst`, `plan` and
`td.realize.centres` that carry only what `_solve_group` reads, so an exported instance is solved
by draw.py itself with no `td` instance (arm a), and rebuilt into the same MILP (the round-trip
check, `export.roundtrip`).
"""
from __future__ import annotations

import contextlib
import importlib.util
import inspect
import os
import sys
import types

import highspy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CONTIG = os.path.join(ROOT, "tools", "exp", "contig")


def _load(name: str, path: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


def load_draw():
    """`tools/exp/contig/draw.py` under the module name `run.py` and `repair.py` give it, so a
    patch made here is the one they see."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    return _load("contig_draw", os.path.join(CONTIG, "draw.py"))


class Captured(Exception):
    """Raised by the shim's `run` once the model is read."""


class Shim:
    """What draw.py sees as `highspy`: the real module, with `Highs` replaced."""

    def __init__(self, highs_cls):
        self.Highs = highs_cls

    def __getattr__(self, name):
        return getattr(highspy, name)


@contextlib.contextmanager
def patched(obj, **attrs):
    """`obj.<name> = value` for the block, then restored."""
    old = {k: getattr(obj, k) for k in attrs}
    for k, v in attrs.items():
        setattr(obj, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(obj, k, v)


def lp_arrays(h) -> dict:
    """`h`'s model as plain lists: column cost/bounds/integrality and rows in CSR form."""
    import scipy.sparse as sp
    lp = h.getLp()
    n, mrows = lp.num_col_, lp.num_row_
    start, index, value = (np.array(x) for x in (lp.a_matrix_.start_, lp.a_matrix_.index_,
                                                 lp.a_matrix_.value_))
    if lp.a_matrix_.format_ == highspy.MatrixFormat.kColwise:
        mat = sp.csc_matrix((value, index, start), shape=(mrows, n)).tocsr()
    else:
        mat = sp.csr_matrix((value, index, start), shape=(mrows, n))
    mat.sort_indices()
    integer = [int(x) != int(highspy.HighsVarType.kContinuous) for x in lp.integrality_]
    return {"cost": [float(x) for x in lp.col_cost_], "lb": [float(x) for x in lp.col_lower_],
            "ub": [float(x) for x in lp.col_upper_], "integer": integer,
            "rows": {"lo": [float(x) for x in lp.row_lower_], "hi": [float(x) for x in lp.row_upper_],
                     "start": mat.indptr.tolist(), "idx": mat.indices.tolist(),
                     "val": [float(x) for x in mat.data]}}


def column_labels(local: dict, n: int) -> list:
    """What each column is, from `_solve_group`'s maps: ["x", z, j], ["c", z, w], ["y", v, j],
    ["s", v], ["e", v, j, k], ["f", j, a, b]."""
    out = [None] * n
    for kind, name in (("x", "col"), ("y", "ycol"), ("c", "ccol"), ("e", "lcol"), ("s", "scol"),
                       ("f", "fcol")):
        for key, i in local.get(name, {}).items():
            out[i] = [kind, *(key if isinstance(key, tuple) else (key,))]
    if any(x is None for x in out):
        raise RuntimeError(f"{sum(x is None for x in out)} of {n} columns without a label")
    return out


def capture_group(draw, args: tuple, kwargs: dict, solve=None) -> dict:
    """Call `solve` (default `draw._solve_group`) with `args`, `kwargs` and stop at its first `Highs.run`; {"model",
    "labels", "graph", "start"}: the MILP draw.py built (`lp_arrays`), its column labels, the
    group graph (`gadj`, the body vertices, the root of each district, the pruned `allowed`) and
    the start vector it would give the solver (None when it has no connected drawing to start
    from)."""
    sink = {}

    class H(highspy.Highs):
        def run(self):
            frame = sys._getframe(1)
            if frame.f_code.co_name != "_solve_group":
                raise RuntimeError(f"Highs.run called from {frame.f_code.co_name}, not _solve_group")
            loc = frame.f_locals
            sink["model"] = lp_arrays(self)
            sink["labels"] = column_labels(loc, len(sink["model"]["cost"]))
            sink["graph"] = {
                "gadj": {a: sorted(b) for a, b in loc["gadj"].items()},
                "vert_of": dict(loc["vert_of"]),
                "root": dict(loc["root"]),
                "allowed": {z: list(js) for z, js in loc["allowed"].items()},
                "fixed_mass": dict(loc["fixed_mass"]),
                "js": list(loc["js"]), "lo": loc["lo"], "hi": loc["hi"]}
            raise Captured

        def setSolution(self, *a, **k):
            sink["start"] = [float(x) for x in a[0].col_value]
            return super().setSolution(*a, **k)

    try:
        with patched(draw, highspy=Shim(H)):
            (solve or draw._solve_group)(*args, **kwargs)
    except Captured:
        sink.setdefault("start", None)
        return sink
    raise RuntimeError("_solve_group returned without a MILP solve (it ended before the model "
                       "was solved: see its Group note)")


# ------------------------------------------------------------------------------ the call's inputs
def bind(fn, args: tuple, kwargs: dict) -> dict:
    """`_solve_group`'s (the real one, `fn`) arguments by name, defaults applied."""
    b = inspect.signature(fn).bind(*args, **kwargs)
    b.apply_defaults()
    return dict(b.arguments)


def snapshot_args(a: dict, centres: list) -> dict:
    """The part of a `_solve_group` call (`bind`) that the group reads, as JSON-able data.
    `centres` is the list of `td.realize.centres` calls made while the model was built."""
    zs, ch, units = a["zs"], a["inst"].channels[a["c"]], a["inst"].units
    zset = set(zs)
    js = sorted({j for z in zs for j in a["allowed"][z]})
    vs = sorted({a["unit_of"][z] for z in zs})
    unit_zips = {v: sorted(units.zips[v]) for v in vs}
    all_unit = {z for zz in unit_zips.values() for z in zz}
    body_z = {z for j in js for b in a["bodies"].get(j, ()) for z in b}
    touched = zset | body_z | {y for z in zs for y in a["adj"][z]}
    km = None
    if a["border"] is not None:
        km = [[x, y, v] for (x, y), v in sorted(a["border"].items())
              if (x in zset or y in zset) and x in touched and y in touched]
    land = a["land"]
    return {
        "c": a["c"], "zs": list(zs),
        "allowed": {z: list(a["allowed"][z]) for z in zs},
        "bodies": {j: [sorted(b) for b in a["bodies"].get(j, ())] for j in js},
        "fixed": {z: a["fixed"][z] for z in sorted(all_unit | body_z) if z in a["fixed"]},
        "adj": {z: sorted(a["adj"][z]) for z in zs},
        "m": {z: a["m"][z] for z in sorted(zset | body_z | all_unit) if z in a["m"]},
        "p": {z: list(a["p"][z]) for z in zs},
        "unit_of": {z: a["unit_of"][z] for z in sorted(touched | all_unit) if z in a["unit_of"]},
        "hold": {v: list(a["hold"].get(v, [])) for v in vs},
        "planned": [[v, j, x] for (v, j), x in sorted(a["planned"].items()) if v in vs and j in js],
        "support": {j: sorted(a["support"][j]) for j in js if j in a["support"]},
        "targets": {cp.name: cp.total for cp in a["plan"].copies if cp.name in js},
        "tau": ch.tau, "M": sorted(ch.M), "unit_zips": unit_zips,
        "lo": a["lo"], "hi": a["hi"], "arm": a["arm"], "fixed_targets": a["fixed_targets"],
        "extra": dict(a["extra"]) if a["extra"] else None,
        "sequential": a["sequential"], "border": km,
        "land": None if land is None else {
            "aland": {z: land["aland"][z] for z in sorted(all_unit | zset) if z in land["aland"]},
            "ratio": land["ratio"], "min_share": land.get("min_share")},
        "centres": centres}


def rebuild_args(snap: dict) -> tuple:
    """(args, kwargs): `_solve_group`'s call from `snapshot_args`, on stand-ins for `inst` and
    `plan`; the solve must run inside `centres_patch` (the recorded `td.realize.centres`)."""
    ns = types.SimpleNamespace
    c = snap["c"]
    units = ns(zips={v: list(zz) for v, zz in snap["unit_zips"].items()},
               unit_of=dict(snap["unit_of"]))
    ch = ns(tau=snap["tau"], M=dict.fromkeys(snap["M"], 0.0), m=snap["m"])
    inst = ns(channels={c: ch}, units=units)
    plan = ns(channel=c, copies=[ns(name=j, total=t) for j, t in snap["targets"].items()])
    bodies = {j: [frozenset(b) for b in bs] for j, bs in snap["bodies"].items()}
    body_of = {z: (j, i) for j, bs in bodies.items() for i, b in enumerate(bs) for z in b}
    border = None
    if snap["border"] is not None:
        border = {(x, y): v for x, y, v in snap["border"]}
    land = snap["land"]
    kw = dict(extra=snap["extra"], dag=False, start=None, count=None, layers=False, flow=False,
              sequential=snap["sequential"], border=border, necks=None, neck_seed=None,
              land=None if land is None else {
                  "aland": land["aland"], "ratio": land["ratio"],
                  **({} if land["min_share"] is None else {"min_share": land["min_share"]})})
    args = (c, list(snap["zs"]), {z: list(js) for z, js in snap["allowed"].items()}, bodies, body_of,
            dict(snap["fixed"]), {z: set(nb) for z, nb in snap["adj"].items()}, dict(snap["m"]),
            {z: tuple(xy) for z, xy in snap["p"].items()}, dict(snap["unit_of"]),
            {v: list(js) for v, js in snap["hold"].items()}, plan,
            {(v, j): x for v, j, x in snap["planned"]},
            {j: frozenset(s) for j, s in snap["support"].items()}, inst, snap["lo"], snap["hi"],
            snap["arm"], snap["fixed_targets"], 3600.0)
    return args, kw


def centres_patch(draw, snap: dict):
    """A context in which draw.py's `td.realize.centres` answers from the calls recorded at export."""
    table = {(r["v"], tuple(r["districts"])): {j: tuple(xy) for j, xy in r["centres"].items()}
             for r in snap["centres"]}

    def centres(_inst, _channel, v, support, _p):
        key = (v, tuple(sorted(support)))
        if key not in table:
            raise KeyError(f"centres({v}, {key[1]}) was not recorded at export")
        return table[key]
    return patched(draw.tdrealize, centres=centres)


@contextlib.contextmanager
def recording_centres(draw, store: list):
    """Record every `td.realize.centres` call draw.py makes in the block into `store`."""
    real = draw.tdrealize.centres

    def spy(inst, channel, v, support, p):
        out = real(inst, channel, v, support, p)
        store.append({"v": v, "districts": sorted(support),
                      "centres": {j: list(xy) for j, xy in out.items()}})
        return out
    draw.tdrealize.centres = spy
    try:
        yield
    finally:
        draw.tdrealize.centres = real


def rebuild_model(draw, snap: dict) -> dict:
    """The group's MILP rebuilt from a snapshot by draw.py's code (`capture_group`)."""
    args, kw = rebuild_args(snap)
    with centres_patch(draw, snap):
        return capture_group(draw, args, {**kw, "log": lambda *_: None})
