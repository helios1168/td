"""inst_io.py -- the standalone instance (JSON.gz) of one draw.py coupled group, and what the arms
do with it (#142, A0/A1): load it, rebuild its base MILP in HiGHS, evaluate a drawing.

An instance holds the group two ways, both written by `export.py` from draw.py's own
`_solve_group` (`capture.py`):

- `model`: the base MILP draw.py hands HiGHS before any connectivity row beyond its up-front
  "a ZCTA of a district needs a neighbour of it" rows (columns with cost, bounds and integrality;
  rows in CSR form) and `labels`, what each column is (x ZCTA→district, c border cut, y district
  holds unit, e land excess, s/f unused here).  Arms b, c and d start from this MILP and add
  integer a,b-separator rows; arm a gives the `draw` section back to draw.py (`capture.rebuild_args`).
- `graph`: the group graph `gadj` (free ZCTAs, and each district's fixed bodies as one vertex
  each, `@<district>#<i>`), the pruned allowed districts, the root body of every district that has
  one, and `lo`/`hi`.

Connectivity of a district is on `gadj` restricted to the vertices that district may own: its x
columns and its own body vertices (fixed to 1).
"""
from __future__ import annotations

import gzip
import json
import math
import os

import numpy as np

SCHEMA = 1


def _inf(x):
    return None if x is None or math.isinf(x) else x


def save(doc: dict, path: str) -> None:
    """Write `doc` as JSON.gz, infinite bounds as null."""
    m = doc["model"]
    for k in ("lb", "ub"):
        m[k] = [_inf(x) for x in m[k]]
    for k in ("lo", "hi"):
        m["rows"][k] = [_inf(x) for x in m["rows"][k]]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as fh:
        json.dump(doc, fh, separators=(",", ":"))


def load(path: str) -> "Inst":
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return Inst(json.load(fh), path)


class Inst:
    """One instance, with the lookups the arms use."""

    def __init__(self, doc: dict, path: str = ""):
        if doc.get("schema") != SCHEMA:
            raise ValueError(f"{path}: schema {doc.get('schema')!r}, expected {SCHEMA}")
        self.doc, self.path = doc, path
        self.id = doc["id"]
        g = doc["graph"]
        self.js = list(g["js"])
        self.gadj = {a: list(b) for a, b in g["gadj"].items()}
        self.vert_of = dict(g["vert_of"])
        self.root = dict(g["root"])
        self.lo, self.hi = g["lo"], g["hi"]
        self.mass = {z: float(x) for z, x in doc["draw"]["m"].items()}
        m = doc["model"]
        self.n = len(m["cost"])
        self.cost = np.array(m["cost"], dtype=float)
        self.lb = np.array([-np.inf if x is None else x for x in m["lb"]], dtype=float)
        self.ub = np.array([np.inf if x is None else x for x in m["ub"]], dtype=float)
        self.integer = np.array(m["integer"], dtype=bool)
        r = m["rows"]
        self.row_lo = np.array([-np.inf if x is None else x for x in r["lo"]], dtype=float)
        self.row_hi = np.array([np.inf if x is None else x for x in r["hi"]], dtype=float)
        self.row_start = np.array(r["start"], dtype=np.int32)
        self.row_idx = np.array(r["idx"], dtype=np.int32)
        self.row_val = np.array(r["val"], dtype=float)
        self.labels = doc["labels"]
        self.xcol, self.ycol = {}, {}
        for i, lab in enumerate(self.labels):
            if lab[0] == "x":
                self.xcol[lab[1], lab[2]] = i
            elif lab[0] == "y":
                self.ycol[lab[1], lab[2]] = i
        self.zs = list(doc["draw"]["zs"])
        # per district: its vertices (x columns and own body vertices) and the graph on them
        self.nodes = {j: {z for (z, k) in self.xcol if k == j}
                      | {b for b, k in self.vert_of.items() if k == j} for j in self.js}
        self.adj = {j: {a: [b for b in self.gadj.get(a, ()) if b in self.nodes[j]]
                        for a in self.nodes[j]} for j in self.js}
        self.fixed = {j: {b for b, k in self.vert_of.items() if k == j} for j in self.js}

    @property
    def n_rows(self) -> int:
        return len(self.row_lo)

    def owner_of(self, x) -> dict:
        """{ZCTA: district} of a column vector `x` (the x column at its highest)."""
        best = {}
        for (z, j), i in self.xcol.items():
            if z not in best or x[i] > x[self.xcol[z, best[z]]]:
                best[z] = j
        return best

    def vector_of(self, owner: dict) -> np.ndarray:
        """The 0/1 vector of x columns for `owner`, other columns 0."""
        x = np.zeros(self.n)
        for z, j in owner.items():
            x[self.xcol[z, j]] = 1.0
        return x

    def highs(self, extra_rows=(), threads: int | None = None, time_limit: float | None = None,
              abs_gap: float = 1e-6, log: bool = False):
        """A HiGHS model of the base MILP plus `extra_rows` [(lo, hi, idx, val)], at
        `mip_rel_gap` 0 (trap 12)."""
        import highspy
        h = highspy.Highs()
        h.setOptionValue("output_flag", bool(log))
        h.setOptionValue("mip_rel_gap", 0.0)
        h.setOptionValue("mip_abs_gap", abs_gap)
        if threads is not None:
            h.setOptionValue("threads", int(threads))
        if time_limit is not None:
            h.setOptionValue("time_limit", float(time_limit))
        lp = highspy.HighsLp()
        lp.num_col_, lp.num_row_ = self.n, self.n_rows
        lp.col_cost_, lp.col_lower_, lp.col_upper_ = self.cost, self.lb, self.ub
        lp.row_lower_, lp.row_upper_ = self.row_lo, self.row_hi
        lp.a_matrix_.format_ = highspy.MatrixFormat.kRowwise
        lp.a_matrix_.start_, lp.a_matrix_.index_, lp.a_matrix_.value_ = (
            self.row_start, self.row_idx, self.row_val)
        lp.integrality_ = [highspy.HighsVarType.kInteger if i else highspy.HighsVarType.kContinuous
                           for i in self.integer]
        h.passModel(lp)
        add_rows(h, extra_rows)
        return h

    def evaluate(self, owner: dict) -> tuple:
        """(objective, "") of the group's MILP with the x columns fixed to `owner`'s drawing, the
        other columns free; (None, why) when `owner` breaks a row (the band, a unit row) or leaves
        a ZCTA of the group out.  The rules are the model's, so a drawing is judged by the same
        rows and cost as the arms'."""
        missing = [z for z in self.zs if z not in owner]
        if missing:
            return None, f"{len(missing)} ZCTAs of the group without an owner ({missing[0]}...)"
        bad = [(z, j) for z, j in owner.items() if (z, j) not in self.xcol]
        if bad:
            return None, f"{bad[0][0]} given to {bad[0][1]}, which may not own it"
        import highspy
        h = self.highs(time_limit=60.0)
        for (z, j), i in self.xcol.items():
            v = 1.0 if owner[z] == j else 0.0
            h.changeColBounds(i, v, v)
        h.run()
        st = h.getModelStatus()
        if st != highspy.HighsModelStatus.kOptimal:
            return None, f"the drawing breaks a row ({h.modelStatusToString(st)})"
        return float(h.getInfo().objective_function_value), ""


def add_rows(h, rows) -> None:
    """Add [(lo, hi, idx, val)] to a HiGHS model in one call."""
    rows = list(rows)
    if not rows:
        return
    import highspy
    inf = highspy.kHighsInf
    lo = np.array([-inf if r[0] is None else r[0] for r in rows], dtype=float)
    hi = np.array([inf if r[1] is None else r[1] for r in rows], dtype=float)
    start = np.cumsum([0] + [len(r[2]) for r in rows[:-1]]).astype(np.int32)
    idx = np.array([i for r in rows for i in r[2]], dtype=np.int32)
    val = np.array([v for r in rows for v in r[3]], dtype=float)
    h.addRows(len(rows), lo, hi, len(idx), start, idx, val)
