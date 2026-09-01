"""
cert_exact.py -- W6c: an *exact* post-hoc optimality certificate for a contiguous
allocation.  Standalone: it imports `base` for the model definitions and nothing else
from the harness, defines no `solve`, and so is never registered as a method.

Why this exists
---------------
Every certificate the harness has today is a *floating-point* certificate: `scip_tree`
stops when SCIP's own primal and dual bounds meet at its feasibility tolerance, so a
recomputed residual of 1.1e-7 nats at 124 zips may be tolerance rather than search and
nothing in the harness can tell the two apart (CLAUDE.md trap 15).  This module answers
the question the harness cannot: *is the stored allocation the global optimum?* -- with a
proof carried out entirely in exact integer arithmetic over the float data.

The three ideas that make an exact proof possible
-------------------------------------------------
**1. No logarithm ever appears.**  `obj = log g_a + log g_b` is transcendental and cannot
be evaluated in rational arithmetic, but it does not have to be: `obj` is monotone in the
*product* `g_a*g_b`, which is an exact rational in the (dyadic) float data.  With
`P* = g_a*·g_b*` the incumbent's product, the certificate question is purely rational:

    is there a contiguous x with  g_a(x) * g_b(x) > P*  ?

**2. The concave objective has a rational outer approximation.**  For *any* rationals
p, q > 0 with `p*q >= 1`,

    sqrt(g_a*g_b)  <=  (p*g_a + q*g_b) / 2                                     (AM-GM)

because `(p*g_a + q*g_b)/2 >= sqrt(p*q*g_a*g_b) >= sqrt(g_a*g_b)`.  The family
`{(p, q) : p*q >= 1}` sweeps out exactly the tangent envelope of the geometric mean, so a
finite set of them is the usual outer approximation -- but with *rational* coefficients we
choose ourselves, and with a validity condition (`p*q >= 1`) that is one exact integer
comparison rather than a floating-point tangency computation.  `s <= (p*g_a + q*g_b)/2` is
therefore a valid relaxation for every (p, q) in the set, whatever rounding produced them.
The certificate is complete when the relaxation's optimum `s` satisfies `s^2 <= P*`.

**3. The LP arithmetic does not have to be exact -- only the pruning.**  Each node's LP is
solved by HiGHS in floating point purely as an *oracle*; the number it returns is never
trusted.  What is trusted is the Neumaier-Shcherbina safe bound: for `max c'z` over
`Az <= b`, `l <= z <= u` and **any** `y >= 0`,

    c'z  <=  y'b + sum_j max( r_j*l_j , r_j*u_j ),      r = c - A'y

which holds for any y whatsoever -- dual feasibility is not required, so no exact LP solve
and no dual-feasibility check is needed.  The float duals are rounded to dyadic rationals,
clamped to y >= 0, and the bound is then evaluated in Python integers.  A node is pruned
only when that *integer* bound is <= sqrt(P*) (compared as `bound^2 <= P*`, exactly).
Every quantity that a pruning decision depends on is an integer; the floats only decide
*where* to branch, which cannot affect correctness.

Consequences and limits
-----------------------
* A "certified" answer means: **no** contiguous allocation has a larger product than the
  stored one.  `gap_exact` is then exactly 0 -- not 1e-8, not 1e-16.
* An "improved" answer means the certifier found a strictly better contiguous allocation,
  i.e. the stored incumbent was **not** optimal.  This is a real finding, not an error.
* A "cap" answer carries the exact upper bound proved so far (the maximum over the open
  frontier of the integer safe bounds), so `gap_exact` is still rigorous, just not zero.
* The proof is of the *rescaled* pair instance the harness solves (`base.rescale_pair`),
  which is the instance the row's `LB` refers to.  Rescaling multiplies both gains by the
  same positive float, so the argmax is identical; the certificate is about the allocation.
* Contiguity is component-wise (`base.pieces`, PLAN.md C.0 #1) and the cuts are the same
  root-free minimal-separator family `scip_tree` uses -- `sum_{w in C} y_w >= y_u + y_v - 1`
  -- with integer +-1 coefficients, so they are exact by construction and valid for *any*
  choice of u, v and separator C.

Two things dominate the runtime, and both were surprises
--------------------------------------------------------
**Almost every node's LP is infeasible, and pruning it needs its own certificate.**
Branching fixes zips into the separator cuts, so a partial assignment usually admits no
contiguous completion at all: 108,468 of 108,759 nodes on the 44-zip C7 pair.  Refusing to
prune an infeasible node without proof (the safe conservative choice) turns the search into
an exhaustive enumeration -- 660,000 nodes and no answer, against 1,752 nodes and 1.0 s
once `infeasible_exact` verifies HiGHS' Farkas ray over the integers.  The ray, like the
duals, needs no verification of its own: *any* y >= 0 with `min_box (y'A) z > y'b` proves
emptiness, so the float ray is simply rounded and the one resulting inequality checked
exactly.

**The cut pool has to be aged.**  Cuts are never wrong to keep, but the pool grows
monotonically (10,464 rows after 69k nodes on the 61-zip C4 pair) and every resolve pays
for it; dropping rows unused for `purge_every` nodes roughly doubles the node rate and
costs only re-separation.  Dropping a valid inequality can never invalidate anything.

Cost, and what it bought (W6c runs, 2026-08-30/31)
--------------------------------------------------
The exact bound is evaluated only from rows whose dual is nonzero, so a node costs one
warm-started HiGHS resolve plus a few hundred Python integer multiply-adds -- ~0.1 ms and
~0.3-0.6 ms respectively at n = 124, i.e. about 1,000 nodes/s in pure Python.  What varies
is the *node count*, and it tracks instance hardness, not n:

    n=8..20   13 T0 pairs        certified   <= 0.03 s   (UB_exact == brute, rationally)
    n=44..77  8 pairs            certified   0.5-12 s
    n=114     C7b_s1 A3/B3       certified   0.04 s
    n=125     C7 A0/B0           certified   0.02 s
    n=82      C1_s2 A3/B3        certified   172 s
    n=135     C7b_s2 A3/B3       certified   187 s     (174,348 nodes)
    n=61      C4_contested A2/B2 certified   324 s     (437,242 nodes)
    n=124     C7b_s2 A1/B1       certified   1,692 s   (1,739,273 nodes)
    n=82      C9_s2 A3/B3        certified   2,529 s   (3,119,543 nodes)
    n=320     C7b_s1 A1/B1       open after 3,600 s, rigorous gap 1.7e-4

`C4_contested` A2/B2 and `C9_s2` A3/B3 are pairs `scip_tree` does *not* close inside its
own cap, and both turn out to have optimal incumbents; `C9_s2` A3/B3 is the named
value-concentration failure (mechanism (c), CLAUDE.md trap 11).

The two headline rows settle CLAUDE.md trap 15 for the pairs it names: the 124- and
135-zip `scip_tree` incumbents are the **exact global optima**, so their reported residuals
of 1.09e-7 and 2.96e-8 nats were floating-point tolerance, not an unclosed search gap.

One caveat on a `cap` row's `gap_exact`.  The search is depth-first (bounded memory: the
frontier is at most the depth), so the reported bound is the maximum over a frontier that
still holds one shallow, weakly-bounded sibling from early in the dive -- and it therefore
*plateaus* rather than descending smoothly (1.7e-4 on the 320-zip pair from 20k nodes to
3M).  The number is rigorous either way; it just understates how much of the tree is done.
Best-first (or a bounded-width hybrid) would report a descending gap, at the cost of the
memory DFS was chosen to avoid; it is the obvious next step if capped gaps matter more
than completed certificates.

CLI
---
    python3 battery/code/contig_methods/cert_exact.py RUN_DIR [--instances REGEX]
        [--methods a,b] [--cap SECONDS] [--slack REL] [--out DIR]

reads `RUN_DIR/rows_scored.jsonl`, certifies the best stored allocation of each selected
instance and writes `rows_certified.jsonl` (every input row, plus a `cert` block on the
rows carrying that allocation) and `cert_summary.csv` into `--out` (default `RUN_DIR`).
Existing artifacts are never modified.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import time
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Optional

import networkx as nx
import numpy as np

try:
    from . import base
except ImportError:                      # run directly as a script, not as a package member
    _root = Path(__file__).resolve().parents[2]        # repo root; td/ lives under it
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from td.solvers import base          # noqa: PLC0415

NAME_CERT = "cert_exact"          # deliberately NOT `NAME`: this module is not a method
KP = 30                           # fractional bits of the tangent coefficients p, q
FY = 40                           # fractional bits the float duals are rounded to
TANGENT_SPAN = 0.35               # initial tangent grid: p in r0*[1-span, 1+span]
TANGENT_GRID = 41


# ============================================================ exact (dyadic) data helpers
def dyadic_bits(x: float) -> int:
    """Number of fractional bits of the exact value of the float `x` (0 for integers)."""
    f = Fraction(x)
    d = f.denominator
    if d == 1:
        return 0
    return d.bit_length() - 1          # denominators of a binary float are powers of two


def to_int_scaled(xs, bits: int) -> list:
    """Exact integers `round(x * 2**bits)`; raises if any x is not representable there."""
    out = []
    for x in xs:
        f = Fraction(x) * (1 << bits)
        if f.denominator != 1:
            raise ValueError(f"{x!r} is not exact at 2**-{bits}")
        out.append(int(f))
    return out


def tangent_pq(p_float: float, kp: int = KP) -> tuple:
    """Dyadic (Pn, Qn) with p = Pn/2**kp, q = Qn/2**kp and p*q >= 1 exactly.

    Validity of `sqrt(ga*gb) <= (p*ga + q*gb)/2` needs only p, q > 0 and p*q >= 1, so Qn is
    rounded *up*: any rounding error makes the relaxation looser, never invalid.
    """
    Pn = max(1, int(round(p_float * (1 << kp))))
    Qn = -((-(1 << (2 * kp))) // Pn)                       # ceil(2**(2kp) / Pn)
    assert Pn * Qn >= 1 << (2 * kp)
    return Pn, Qn


# ===================================================================== the exact model
@dataclass
class _Row:
    """One inequality `A_int . z <= b_int`, where A_true = A_int / 2**e.

    `cols`/`vals` are the *integer* coefficients over the model's variables
    (0..n-1 are the x's, n is s).  `e` is the row's exponent; tangents have e = FA and
    cuts e = 0, and the dual pairing scales each row's dual accordingly.
    """
    cols: list
    vals: list
    b: int
    e: int
    is_tangent: bool = False


class _Model:
    """The float LP (HiGHS, the oracle) and its exact integer shadow, kept in step."""

    def __init__(self, n: int, ia: list, ib: list, fu: int, s_max: int):
        import highspy                                       # local: optional at import time

        self.hs = highspy
        self.n = n
        self.ia, self.ib, self.fu = ia, ib, fu
        self.IUb = sum(ib)
        self.fa = KP + fu + 1                                # tangent row exponent
        self.s_max = int(s_max)
        self.rows: list[_Row] = []
        self.rowkey: list = []                   # parallel to rows, for cutkeys bookkeeping
        self.touched: list = []                  # parallel to rows: clock of last nonzero dual
        self.clock = 0
        self.cutkeys: set = set()
        self.n_tangents = 0
        self.n_cuts = 0
        self.n_purged = 0
        self._dual_sign: Optional[int] = None
        self._ray_sign: Optional[int] = None
        self._cur_fixed: dict = {}
        self.last_ray = None
        self.check_x: Optional[list] = None      # audit vector: every cut must accept it

        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("presolve", "off")
        lp = highspy.HighsLp()
        lp.num_col_ = n + 1
        lp.col_cost_ = np.array([0.0] * n + [-1.0])          # HiGHS minimises: min -s
        lp.col_lower_ = np.zeros(n + 1)
        lp.col_upper_ = np.array([1.0] * n + [float(s_max)])
        lp.num_row_ = 0
        lp.row_lower_ = np.array([])
        lp.row_upper_ = np.array([])
        lp.a_matrix_.format_ = highspy.MatrixFormat.kRowwise
        lp.a_matrix_.start_ = np.array([0])
        lp.a_matrix_.index_ = np.array([], dtype=np.int32)
        lp.a_matrix_.value_ = np.array([])
        h.passModel(lp)
        self.h = h
        self.inf = highspy.kHighsInf

    # ------------------------------------------------------------------ row construction
    def add_tangent(self, p_float: float) -> bool:
        """`s <= (p*ga + q*gb)/2` for a dyadic (p, q) with p*q >= 1.  Exact row:

            2**fa * s  -  sum_j (Pn*ia_j - Qn*ib_j) x_j  <=  Qn * IUb
        """
        Pn, Qn = tangent_pq(p_float)
        cols = list(range(self.n)) + [self.n]
        vals = [-(Pn * self.ia[j] - Qn * self.ib[j]) for j in range(self.n)] + [1 << self.fa]
        row = _Row(cols, vals, Qn * self.IUb, self.fa, is_tangent=True)
        key = ("t", Pn, Qn)
        if key in self.cutkeys:
            return False
        self.cutkeys.add(key)
        self.rows.append(row)
        self.rowkey.append(key)
        self.touched.append(self.clock)
        self.n_tangents += 1
        scale = float(1 << self.fa)
        self.h.addRow(-self.inf, row.b / scale, len(cols),
                      np.array(cols, dtype=np.int32),
                      np.array([v / scale for v in vals], dtype=float))
        return True

    def add_cut(self, cols, vals, b, audit: bool = True) -> bool:
        """A `sum a_j x_j <= b` row with integer (here +-1) coefficients.

        `audit=False` marks a row that is valid for the *decision* problem only -- the
        no-good that removes an already-evaluated allocation whose product is <= P*.  Such
        a row may legitimately exclude an optimum that ties with the incumbent, so it is
        exempt from the `check_x` audit (and `UB_exact` is clamped at P* to compensate).
        """
        key = ("c", tuple(cols), tuple(vals), b)
        if key in self.cutkeys:
            return False
        if audit and self.check_x is not None:
            lhs = sum(int(v) * self.check_x[c] for c, v in zip(cols, vals))
            if lhs > b:
                raise AssertionError(
                    f"cert_exact: cut {list(zip(cols, vals))} <= {b} excludes the reference "
                    f"optimum (lhs={lhs}) -- the cut family is invalid, not merely loose")
        self.cutkeys.add(key)
        self.rows.append(_Row(list(cols), [int(v) for v in vals], int(b), 0))
        self.rowkey.append(key)
        self.touched.append(self.clock)
        self.n_cuts += 1
        self.h.addRow(-self.inf, float(b), len(cols),
                      np.array(cols, dtype=np.int32), np.array(vals, dtype=float))
        return True

    # ------------------------------------------------------------------------- solving
    def set_bounds(self, fixed: dict) -> None:
        """Move the node's column bounds, touching only the columns that changed."""
        cur = self._cur_fixed
        for j in cur:
            if fixed.get(j) != cur[j]:
                self.h.changeColBounds(j, 0.0, 1.0)
        for j, v in fixed.items():
            if cur.get(j) != v:
                self.h.changeColBounds(j, float(v), float(v))
        self._cur_fixed = dict(fixed)

    def solve(self):
        """(status, s_float, x_float, row_duals) -- all floats, none of them trusted.

        status is "optimal", "infeasible" (a Farkas ray is left in `self.last_ray`) or
        "other".  Branching fixes variables into separator cuts, so the great majority of
        the nodes in a run are LP-infeasible -- 108,468 of 108,759 on the 44-zip C7 pair --
        and refusing to prune them without a certificate is the difference between a tree
        that closes in seconds and one that never does.
        """
        self.last_ray = None
        self.h.run()
        st = self.h.getModelStatus()
        if st == self.hs.HighsModelStatus.kInfeasible:
            try:
                _s, has_ray, ray = self.h.getDualRay()
            except Exception:                                # noqa: BLE001
                has_ray, ray = False, None
            if has_ray and ray is not None:
                r = np.asarray(ray, dtype=float)
                mx = float(np.max(np.abs(r))) if r.size else 0.0
                self.last_ray = r / mx if mx > 0 else None
            return ("infeasible", None, None, None)
        if st != self.hs.HighsModelStatus.kOptimal:
            return ("other", None, None, None)
        sol = self.h.getSolution()
        v = np.asarray(sol.col_value)
        d = np.asarray(sol.row_dual)
        return ("optimal", -self.h.getInfo().objective_function_value, v[:self.n], d)

    # ------------------------------------------------- exact Farkas infeasibility check
    def infeasible_exact(self, ray, fixed: dict) -> bool:
        """True if `ray` proves, in exact integer arithmetic, that the node is empty.

        For any y >= 0, `min_{z in box} (y'A) z > y'b` implies `{Az <= b, box}` is empty.
        Any y works, so the float ray needs no verification of its own -- it is rounded to
        dyadic rationals (the same scaling the safe bound uses) and the single resulting
        inequality is checked over the integers.  Both sign conventions are tried.
        """
        if ray is None:
            return False
        n, fa = self.n, self.fa
        r = np.asarray(ray, dtype=float)
        nz = np.nonzero(r)[0]
        signs = (self._ray_sign, -self._ray_sign) if self._ray_sign else (+1, -1)
        for sign in signs:
            w = [0] * (n + 1)
            B = 0
            used = False
            for i in nz:
                row = self.rows[i]
                y = sign * float(r[i])
                if not (y > 0.0) or not math.isfinite(y):
                    continue
                Y = int(y * (1 << FY)) if row.is_tangent else int(y * (1 << (fa + FY)))
                if Y <= 0:
                    continue
                used = True
                B += Y * row.b
                for c, v in zip(row.cols, row.vals):
                    w[c] += Y * v
            if not used:
                continue
            lo = 0
            for j in range(n):
                wj = w[j]
                if j in fixed:
                    if fixed[j]:
                        lo += wj
                elif wj < 0:
                    lo += wj
            if w[n] < 0:
                lo += w[n] * self.s_max
            if B < lo:
                self._ray_sign = sign
                return True
        return False

    # ------------------------------------------------------------------- cut pool ageing
    def touch(self, duals, clock: int) -> None:
        """Mark every row that carried a dual at this node as still in use.

        `clock` is the *node* counter, not a count of calls: only the LP-optimal nodes
        reach here (the infeasible ones, ~99% of the tree, carry a ray instead), so an age
        measured in calls would be two orders of magnitude off.
        """
        self.clock = clock
        d = np.asarray(duals, dtype=float)
        tch = self.touched
        for i in np.nonzero(d)[0]:
            tch[i] = clock

    def purge(self, clock: int, age: int, keep_min: int = 500) -> int:
        """Drop cut rows unused for `age` node-visits.  Dropping a *valid* inequality can
        only loosen the relaxation, never invalidate it, and separation will regenerate the
        cut if it is needed again -- so this is a pure performance knob.  Without it the
        pool grows monotonically (10,464 rows after 69k nodes on the 61-zip C4 pair) and
        every LP resolve pays for it.
        """
        cut_idx = [i for i, r in enumerate(self.rows) if not r.is_tangent]
        if len(cut_idx) <= keep_min:
            return 0
        drop = [i for i in cut_idx if clock - self.touched[i] > age]
        drop = drop[:max(len(cut_idx) - keep_min, 0)]
        if not drop:
            return 0
        self.h.deleteRows(len(drop), np.array(sorted(drop), dtype=np.int32))
        dset = set(drop)
        for i in dset:
            self.cutkeys.discard(self.rowkey[i])
        self.rows = [r for i, r in enumerate(self.rows) if i not in dset]
        self.rowkey = [k for i, k in enumerate(self.rowkey) if i not in dset]
        self.touched = [t for i, t in enumerate(self.touched) if i not in dset]
        self.n_cuts -= len(drop)
        self.n_purged += len(drop)
        return len(drop)

    # --------------------------------------------------------------- exact safe bound
    def safe_bound(self, duals, fixed: dict) -> int:
        """Neumaier-Shcherbina bound as an integer numerator over 2**(fa + FY).

        Valid for ANY y >= 0, so the float duals need no feasibility check: they are
        clamped, rounded to dyadic rationals, and the tangent block is renormalised so the
        reduced cost of `s` is exactly zero (otherwise s's large upper bound would swamp
        the bound).  Both sign conventions are tried once and the tighter kept -- each is
        independently valid, so the minimum of the two is valid too.
        """
        if self._dual_sign is None:
            b1 = self._safe_bound_signed(duals, fixed, +1)
            b2 = self._safe_bound_signed(duals, fixed, -1)
            self._dual_sign = +1 if b1 <= b2 else -1
            return min(b1, b2)
        return self._safe_bound_signed(duals, fixed, self._dual_sign)

    def _safe_bound_signed(self, duals, fixed: dict, sign: int) -> int:
        n, fa = self.n, self.fa
        shift_t = 1 << FY                       # tangent rows: e = fa -> scale 2**FY
        shift_c = 1 << (fa + FY)                # cut rows:     e = 0  -> scale 2**(fa+FY)
        Yt: list = []                           # (row, Y) for tangents
        Yc: list = []                           # (row, Y) for cuts
        d = np.asarray(duals, dtype=float)
        for i in np.nonzero(d)[0]:               # only the basic rows carry a dual
            row = self.rows[i]
            y = sign * float(d[i])
            if not (y > 0.0) or not math.isfinite(y):
                continue
            if row.is_tangent:
                Y = int(y * shift_t)
                if Y > 0:
                    Yt.append((row, Y))
            else:
                Y = int(y * shift_c)
                if Y > 0:
                    Yc.append((row, Y))
        tot = sum(Y for _, Y in Yt)
        if tot <= 0:
            # no tangent is active: fall back to the single tightest tangent, weight 1
            trows = [r for r in self.rows if r.is_tangent]
            if not trows:
                return (1 << (fa + FY)) * self.s_max     # vacuous but valid
            Yt = [(trows[0], 1 << FY)]
            tot = 1 << FY
        # renormalise the tangent block to sum exactly to 2**FY  =>  reduced cost of s is 0
        target = 1 << FY
        Yt = [(r, (Y * target) // tot) for r, Y in Yt]
        rest = target - sum(Y for _, Y in Yt)
        if rest:
            r0, Y0 = Yt[0]
            Yt[0] = (r0, Y0 + rest)

        r = [0] * (n + 1)
        acc = 0
        for row, Y in Yt:
            acc += Y * row.b
            for c, v in zip(row.cols, row.vals):
                r[c] -= Y * v
        for row, Y in Yc:
            acc += Y * row.b
            for c, v in zip(row.cols, row.vals):
                r[c] -= Y * v
        # r[n] (the reduced cost of s) is  1*2**(fa+FY) - sum_t Y_t * 2**fa  ==  0 by
        # construction; add its box contribution anyway in case a cut ever touches s.
        r[n] += 1 << (fa + FY)
        if r[n] > 0:
            acc += r[n] * self.s_max
        for j in range(n):
            rj = r[j]
            if j in fixed:
                if fixed[j]:
                    acc += rj
            elif rj > 0:
                acc += rj
        return acc


# ============================================================== separation (exact cuts)
def _pair_structure(G, nodes):
    """Index-space adjacency and component membership.

    Separation runs at (nearly) every node of the tree, so it is done on integer indices
    with plain lists rather than through networkx subgraph construction -- on the 61-zip
    pairs that is the difference between separation and the LP dominating the runtime.
    """
    idxof = {z: i for i, z in enumerate(nodes)}
    sub = G.subgraph(nodes)
    adj = [[] for _ in nodes]
    for u, v in sub.edges():
        iu, iv = idxof[u], idxof[v]
        adj[iu].append(iv)
        adj[iv].append(iu)
    comps = [sorted(idxof[z] for z in c) for c in nx.connected_components(sub)]
    return idxof, adj, comps


def _separate(adj, comps, xint, model: _Model, scratch) -> int:
    """Root-free minimal-separator cuts for the (thresholded) assignment `xint`.

    Side a uses y = x, side b uses y = 1 - x; for a non-largest piece P of side y inside a
    pair component K, with u in P, v in the largest piece and C = N_K(P) a u,v-separator,

        sum_{w in C} y_w >= y_u + y_v - 1

    Both forms are written as `<=` rows with integer +-1 coefficients:
        side a:   -sum_C x_w + x_u + x_v <= 1
        side b:    sum_C x_w - x_u - x_v <= |C| - 1

    Validity does not depend on how u, v and C were chosen -- every u,v-path inside K meets
    N_K(P) -- so the cut is valid for every contiguous allocation, and in particular the
    same family may be generated from a *fractional* point thresholded at 1/2.
    """
    added = 0
    seen = scratch
    for K in comps:
        for side in (0, 1):
            want = 1 if side == 0 else 0
            members = [i for i in K if xint[i] == want]
            if len(members) < 2:
                continue
            for i in members:
                seen[i] = 0
            pieces = []
            for start in members:
                if seen[start]:
                    continue
                seen[start] = 1
                piece = [start]
                head = 0
                while head < len(piece):
                    z = piece[head]; head += 1
                    for w in adj[z]:
                        if xint[w] == want and not seen[w]:
                            seen[w] = 1
                            piece.append(w)
                pieces.append(piece)
            for i in members:
                seen[i] = 0
            if len(pieces) <= 1:
                continue
            bi = max(range(len(pieces)), key=lambda k: len(pieces[k]))
            cv = min(pieces[bi])
            for k, P in enumerate(pieces):
                if k == bi:
                    continue
                inP = set(P)
                C = set()
                for z in P:
                    for w in adj[z]:
                        if w not in inP:
                            C.add(w)
                if not C:
                    continue
                cu = min(P)
                cols = sorted(C)
                if cu in C or cv in C:
                    continue                      # degenerate; the cut would be malformed
                if side == 0:
                    added += model.add_cut(cols + [cu, cv],
                                           [-1] * len(cols) + [1, 1], 1)
                else:
                    added += model.add_cut(cols + [cu, cv],
                                           [1] * len(cols) + [-1, -1], len(cols) - 1)
    return added


# ==================================================================== the certifier
@dataclass
class CertResult:
    status: str                      # certified | improved | cap | error
    n: int
    UB_exact: Fraction               # exact upper bound on g_a*g_b over contiguous x
    incumbent_exact: Fraction        # exact g_a*g_b of the stored allocation
    gap_exact: float                 # log(UB_exact) - log(incumbent_exact), >= 0
    n_nodes: int = 0
    n_cut_rounds: int = 0
    n_cuts: int = 0
    n_tangents: int = 0
    wall: float = 0.0
    better_to_a: Optional[list] = None
    message: str = ""
    extra: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        d = dict(status=self.status, n=self.n,
                 UB_exact=[self.UB_exact.numerator, self.UB_exact.denominator],
                 incumbent_exact=[self.incumbent_exact.numerator,
                                  self.incumbent_exact.denominator],
                 gap_exact=self.gap_exact, n_nodes=self.n_nodes,
                 n_cut_rounds=self.n_cut_rounds, n_cuts=self.n_cuts,
                 n_tangents=self.n_tangents, wall=self.wall,
                 better_to_a=self.better_to_a, message=self.message, extra=self.extra)
        return d


def certify(G, nodes, to_a, *, theta: float = 0.40, lam: float = 0.30, kappa: float = 0.0,
            time_limit: float = 3600.0, tangent_grid: int = TANGENT_GRID,
            tangent_span: float = TANGENT_SPAN, max_sep_rounds: int = 4,
            slack_rel: float = 0.0, purge_every: int = 1000, check_opt=None,
            progress=None) -> CertResult:
    """Prove (or refute) that `to_a` maximises g_a*g_b over contiguous allocations.

    Everything a pruning decision rests on is exact integer arithmetic; HiGHS is used only
    to pick branching variables and to supply candidate duals.

    `slack_rel` (a *rational*, exact) relaxes the claim from "nothing beats P*" to
    "nothing beats P*(1 + slack_rel)", i.e. a rigorous gap of at most `log1p(slack_rel)`
    nats.  It is not a tolerance in the floating-point sense -- the comparison stays an
    exact integer one -- but it is the lever that makes the search finish: at
    `slack_rel = 0` a node whose *true* LP bound equals sqrt(P*) exactly (a tie, and the
    rho = 0 objective is full of them -- CLAUDE.md trap 4) cannot be pruned, because the
    safe bound is the exact value of a *rounded* dual and therefore sits a few ulps above
    the LP's own optimum.  Such a node must then be branched to the bottom.  Any
    `slack_rel` above the dual-rounding noise (~1e-13 relative) removes that, at the cost
    of a stated, rigorous, and tiny residual.
    """
    t0 = time.perf_counter()
    nodes = list(nodes)
    n = len(nodes)
    ua, ub = base.utilities(G, nodes, theta, lam, kappa)
    if float(np.min(ua)) < 0 or float(np.min(ub)) < 0:
        return CertResult("error", n, Fraction(0), Fraction(0), math.inf,
                          message="negative utilities (kappa > 0 is out of scope for W6c)")
    fu = max([dyadic_bits(float(v)) for v in ua] + [dyadic_bits(float(v)) for v in ub] + [0])
    ia = to_int_scaled([float(v) for v in ua], fu)
    ib = to_int_scaled([float(v) for v in ub], fu)
    den = Fraction(1, 1 << (2 * fu))

    star = base.mask(nodes, set(to_a))
    Ga = sum(ia[j] for j in range(n) if star[j])
    Gb = sum(ib[j] for j in range(n) if not star[j])
    Pstar_num = Ga * Gb                                   # over 2**(2*fu)
    Pstar = Fraction(Pstar_num) * den
    if Ga <= 0 or Gb <= 0:
        return CertResult("error", n, Fraction(0), Pstar, math.inf,
                          message="incumbent has a non-positive gain")
    if not base.is_feasible(G, nodes, set(to_a)):
        return CertResult("error", n, Fraction(0), Pstar, math.inf,
                          message="incumbent allocation is not contiguous")

    idxof, adj, comps = _pair_structure(G, nodes)
    scratch = [0] * n
    s_max = int(math.ceil(0.5 * (float(ua.sum()) + float(ub.sum())))) + 1
    m = _Model(n, ia, ib, fu, s_max)
    if check_opt is not None:
        ref = set(check_opt)
        m.check_x = [1 if z in ref else 0 for z in nodes] + [0]
    r0 = math.sqrt(float(Gb) / float(Ga))
    for t in range(tangent_grid):
        f = 1.0 + tangent_span * (2.0 * t / max(tangent_grid - 1, 1) - 1.0)
        m.add_tangent(r0 * f)

    # ---- pruning test, exact:  bound_num / 2**(fa+FY)  <=  sqrt(Pstar * (1 + slack)) ?
    shift2 = 2 * (m.fa + FY)
    sl = Fraction(slack_rel)
    if sl < 0:
        raise ValueError("slack_rel must be >= 0")
    sl_num, sl_den = (sl + 1).numerator, (sl + 1).denominator
    target_prod = Pstar * (1 + sl)

    def prunes(bound_num: int) -> bool:
        if bound_num <= 0:
            return True
        return (bound_num * bound_num * (1 << (2 * fu)) * sl_den
                <= Pstar_num * (1 << shift2) * sl_num)

    def bound_product(bound_num: int) -> Fraction:
        """The bound expressed as an upper bound on g_a*g_b (i.e. bound^2)."""
        return Fraction(max(bound_num, 0)) ** 2 / (1 << shift2)

    # ---- depth-first branch and bound; every open node carries a proved exact bound
    root_bound = Fraction(s_max) ** 2
    stack = [({}, root_bound)]
    n_nodes = 0
    n_rounds = 0
    n_infeas_certified = 0
    n_infeas_unproved = 0
    n_purged = 0
    next_purge = purge_every
    better = None
    status = "certified"
    msg = ""
    while stack:
        if time.perf_counter() - t0 > time_limit:
            status = "cap"
            msg = f"time limit {time_limit:g}s"
            break
        fixed, _parent_bound = stack.pop()
        if purge_every and n_nodes >= next_purge:
            next_purge = n_nodes + purge_every
            n_purged += m.purge(n_nodes, age=max(purge_every // 2, 1))
        m.set_bounds(fixed)
        node_done = False
        sep_rounds = 0
        while not node_done:
            if time.perf_counter() - t0 > time_limit:
                stack.append((fixed, _parent_bound))
                status = "cap"
                msg = f"time limit {time_limit:g}s"
                node_done = True
                break
            n_nodes += 1
            if progress is not None and n_nodes % 20000 == 0:
                ub_now = max([b for _f, b in stack] + [Pstar], default=Pstar)
                progress(n_nodes, len(stack), time.perf_counter() - t0,
                         max(math.log(float(ub_now)) - math.log(float(Pstar)), 0.0))
            st, sval, xv, duals = m.solve()
            if st != "optimal":
                if st == "infeasible" and m.infeasible_exact(m.last_ray, fixed):
                    n_infeas_certified += 1
                    node_done = True
                    break
                # An LP verdict the exact arithmetic cannot confirm is never a licence to
                # prune: branch on, and if everything is fixed, decide the point directly.
                n_infeas_unproved += 1
                free = [j for j in range(n) if j not in fixed]
                if not free:
                    xint = np.zeros(n, dtype=int)
                    for j, v in fixed.items():
                        xint[j] = int(v)
                    cand = {nodes[j] for j in range(n) if xint[j]}
                    ga_i = sum(ia[j] for j in range(n) if xint[j])
                    gb_i = sum(ib[j] for j in range(n) if not xint[j])
                    if (ga_i * gb_i > Pstar_num
                            and base.is_feasible(G, nodes, cand)):
                        better = sorted(cand, key=base._sort_key)
                        status = "improved"
                    node_done = True
                    break
                j = free[0]
                for v in (0, 1):
                    f2 = dict(fixed); f2[j] = v
                    stack.append((f2, _parent_bound))
                node_done = True
                break
            m.touch(duals, n_nodes)
            bnum = m.safe_bound(duals, fixed)
            if prunes(bnum):
                node_done = True
                break
            node_bound = bound_product(bnum)
            frac = np.minimum(xv, 1.0 - xv)
            jmax = int(np.argmax(frac)) if n else 0
            if n == 0 or float(frac[jmax]) <= 1e-9:
                xint = (xv > 0.5).astype(int)
                for j, v in fixed.items():
                    xint[j] = int(v)
                if _separate(adj, comps, xint, m, scratch):
                    n_rounds += 1
                    continue
                ga_i = sum(ia[j] for j in range(n) if xint[j])
                gb_i = sum(ib[j] for j in range(n) if not xint[j])
                cand = {nodes[j] for j in range(n) if xint[j]}
                if ga_i * gb_i > Pstar_num and base.is_feasible(G, nodes, cand):
                    better = sorted(cand, key=base._sort_key)
                    status = "improved"
                    node_done = True
                    break
                # feasible but no better: tighten the envelope at its own gains, so the
                # relaxation stops returning it (and fall back to a no-good if it does).
                # No-good:  sum_{x*=0} x_j + sum_{x*=1} (1 - x_j) >= 1, i.e.
                #           sum_{x*=1} x_j - sum_{x*=0} x_j <= sum(x*) - 1.
                cut_it = False
                if ga_i > 0 and gb_i > 0:
                    cut_it = m.add_tangent(math.sqrt(float(gb_i) / float(ga_i)))
                if not cut_it:
                    m.add_cut(list(range(n)),
                              [(1 if xint[j] else -1) for j in range(n)],
                              int(sum(xint)) - 1, audit=False)
                n_rounds += 1
                continue
            # fractional separation: the LP point thresholded at 1/2 is the side the LP has
            # committed to, and any separator cut it violates is valid for every allocation
            # (the cut family does not depend on how u, v and C were chosen)
            if sep_rounds < max_sep_rounds:
                xthr = (xv > 0.5).astype(int)
                for j, v in fixed.items():
                    xthr[j] = int(v)
                if _separate(adj, comps, xthr, m, scratch):
                    sep_rounds += 1
                    n_rounds += 1
                    continue
            f0 = dict(fixed); f0[jmax] = 0
            f1 = dict(fixed); f1[jmax] = 1
            stack.append((f0, node_bound))
            stack.append((f1, node_bound))
            node_done = True
        if status == "improved":
            break

    if status == "cap":
        # the incumbent is attainable, so the true optimum is >= P* whatever the frontier
        # says (a no-good may have removed a tie); clamp so UB_exact is a real bound
        ub_exact = max([b for _f, b in stack] + [Pstar], default=Pstar)
    elif status == "improved":
        ub_exact = Fraction(0)
    else:
        ub_exact = target_prod
    if status == "improved":
        gap = math.inf
    elif ub_exact > 0:
        gap = max(math.log(float(ub_exact)) - math.log(float(Pstar)), 0.0)
    else:
        gap = 0.0
    return CertResult(status=status, n=n, UB_exact=ub_exact, incumbent_exact=Pstar,
                      gap_exact=gap, n_nodes=n_nodes, n_cut_rounds=n_rounds,
                      n_cuts=m.n_cuts, n_tangents=m.n_tangents,
                      wall=time.perf_counter() - t0, better_to_a=better, message=msg,
                      extra=dict(open_nodes=len(stack), fu=fu, s_max=s_max,
                                 slack_rel=float(slack_rel),
                                 infeasible_certified=n_infeas_certified,
                                 infeasible_unproved=n_infeas_unproved,
                                 cuts_purged=n_purged))


# ================================================================================== CLI
def _load_rows(path: Path) -> list:
    return [json.loads(line) for line in path.open() if line.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="exact post-hoc optimality certificates (W6c)")
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--instances", default=None, help="regex over the instance name")
    ap.add_argument("--methods", default=None, help="comma-separated method keys")
    ap.add_argument("--cap", type=float, default=3600.0, help="seconds per row")
    ap.add_argument("--slack", type=float, default=0.0,
                    help="rigorous relative slack on the product (gap becomes log1p(slack))")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    try:
        import instances as I                                # noqa: PLC0415
    except ImportError:
        raise SystemExit(
            "cert_exact's CLI needs battery/code/instances.py, which was not carried into "
            "this worktree (it pulls synth -> territory -> the two-player battery). Recover "
            "it with `git show contiguity-harness:battery/code/instances.py`, or call "
            "cert_exact.certify(G, nodes, to_a, ...) directly -- that path has no such "
            "dependency and is what tests/test_engines.py exercises.")

    rows_path = a.run_dir / "rows_scored.jsonl"
    if not rows_path.exists():
        rows_path = a.run_dir / "rows.jsonl"
    rows = _load_rows(rows_path)
    pat = re.compile(a.instances) if a.instances else None
    meths = set(a.methods.split(",")) if a.methods else None
    out_dir = a.out or a.run_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    specs = {s.name: s for s in I.specs_for_tiers(["T0", "T1", "T2", "hand"])}
    todo = [r for r in rows
            if r.get("to_a") and r.get("feasible")
            and (pat is None or pat.search(r.get("instance", "")))
            and (meths is None or r.get("method") in meths)]
    # certify the best incumbent per instance only (the allocation, not the method, is
    # what a certificate is about)
    best: dict = {}
    for r in todo:
        k = r["instance"]
        if k not in best or (r.get("LB") or -math.inf) > (best[k].get("LB") or -math.inf):
            best[k] = r

    certs = {}
    for name, r in sorted(best.items()):
        if name not in specs:
            certs[name] = dict(status="error", message="instance spec not found")
            continue
        pi = I.build_pair(specs[name])
        res = certify(pi.G, pi.nodes, set(r["to_a"]), kappa=float(r.get("kappa") or 0.0),
                      time_limit=a.cap, slack_rel=a.slack)
        certs[name] = res.to_json()
        if not a.quiet:
            print(f"{name:42s} n={res.n:4d} {res.status:10s} "
                  f"gap_exact={res.gap_exact:.3e} nodes={res.n_nodes} "
                  f"cuts={res.n_cuts} t={res.wall:.1f}s", flush=True)

    # a certificate is a property of the *allocation*, not of the method that found it, so
    # it is copied onto every row carrying that same allocation and onto no other
    with (out_dir / "rows_certified.jsonl").open("w") as fh:
        for r in rows:
            out = dict(r)
            inst = r.get("instance")
            c = certs.get(inst)
            same = (c is not None and inst in best and r.get("to_a") is not None
                    and set(r["to_a"]) == set(best[inst]["to_a"]))
            out["cert"] = c if same else None
            out["gap_exact"] = c["gap_exact"] if same else None
            fh.write(json.dumps(out) + "\n")
    with (out_dir / "cert_summary.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["instance", "n", "status", "gap_exact", "n_nodes", "n_cut_rounds",
                    "n_cuts", "n_tangents", "wall"])
        for name, c in sorted(certs.items()):
            w.writerow([name, c.get("n"), c.get("status"), c.get("gap_exact"),
                        c.get("n_nodes"), c.get("n_cut_rounds"), c.get("n_cuts"),
                        c.get("n_tangents"), c.get("wall")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
