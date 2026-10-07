"""plancheck.py -- #124's plan checks: plan only districts that draw connected without a neck.

    "$TD_PY" -u tools/exp/contig/plancheck.py <copy.toml> --root <dir> --name <run id>
        --parent <run> --plans <dir> [--round0 <folder>] [--budget 1200] [--extract PATH]

**B, drawable alone** (`drawable_alone = true`, `docs/MODEL.md` §4.9).  `drawable` asks whether
one district can be drawn with footprint exactly S: every whole unit of S owned in full (a clipped
unit of a multi-unit S is held whole, §3.4), each free unit giving a share of at least η_c (so a
non-empty one), drawn mass in [L_c, U_c], connected on the ZIP graph and with no M1 neck
(`td.audit.district_necks`).  A support of held units alone is one fixed ZIP set, judged directly.
Otherwise it is one MILP on S's ZIPs: x_z per ZIP of a free unit, the held units' components
contracted to bodies, a single-commodity flow from the heaviest body (or from a chosen root ZIP
when S holds no held unit) keeping the district connected, as `draw._solve_group`'s `flow` and
`audit.district_necks`' rooted flow do, and its necks cut lazily by `draw.NeckCut` rows
(`repair.neck_cuts`, valid for every connected district without a neck).  Its objective is the
district's perimeter in km of shared border (trap 19: never a zero objective), and the solve
stops at a 5% gap: only feasibility matters.  `infeasible` is HiGHS's proof on the cut-augmented
model; a time limit, a neck the check leaves unresolved or a cut its own drawing meets is
`unknown`, never a cut.  `Checks` caches verdicts monotonically in δ: an infeasible verdict at δ
holds at every narrower band, a drawable one at every wider band.

`plan_checked` runs B lazily: the master at δ, then `drawable` on each multi-unit support it
uses, n_S = 0 (`master.build`'s `banned`) for each proved infeasible, and a re-solve, until every
support in use passes or is unknown.  `checked_delta` is replan.py's rule for a channel with no
plan at its δ: the smallest δ up to `final_delta` at which `plan_checked` finds one, by bisection
to `master.DELTA_TOL` with B inside each probe; each δ change records the B bans that forced it.

**C, close the loop** (`replan_rounds = R`, this CLI).  Round 0 plans the copy (replan.py, which
runs B when the key is on), draws it (run.py, arm 1, sequential, border term) and repairs it
(repair.py, `--keep-support --flow`, unchanged), or reads the folder `--round0`.  Each detached
piece and neck left on the repaired map gets its cause from the repair's own record (`causes`):
the last window tried on it, and "budget spent" when the repair's log says a window of it was
not tried.  A support whose district is left with a cause "window infeasible (outside fixed)"
in a channel whose `replan_rounds` is not used up gets `ban_supports` in the next round's copy
(an exact unit set, never a state pair), and the round re-plans, redraws and repairs.  A window
proved infeasible is conditional on everything outside it being fixed: the ban is a policy, not a
proof that S cannot be drawn.  An unknown window, a spent budget or no window is listed, never
cut.  Each ban records the channel, the window (attempt, shape, size, |W|, whether the
`--max-zctas` cap stopped its growth) and its cost: δ, the master's objective, the drawn map's
splits and cuts, before and after.  The loop stops when a round finds nothing to ban or R rounds
are used.  Every folder's run.json and manifest.json gain a `plan_check` block (the copy's keys,
B's cuts, unknowns and δ changes, C's bans so far).
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import time

import highspy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import audit, master, supports  # noqa: E402


def _load(name: str, file: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


draw = _load("contig_draw", "draw.py")
repair = _load("contig_repair", "repair.py")

CHECK_TIME = 120.0          # seconds per `drawable` test
CHECK_GAP = 0.2             # the test's perimeter objective only steers it: a 20% gap
BAND_TOL = 1e-9             # relative slack on a fixed ZIP set's band, as `audit.BAND_SLACK`
INFEASIBLE = "window infeasible (outside fixed)"


# ------------------------------------------------------------------------------ B: one district
class Checks:
    """`drawable` verdicts by (channel, support), monotone in δ: a proof of infeasibility at δ
    stands at every δ' ≤ δ, a drawing at δ at every δ' ≥ δ (the band only widens)."""

    def __init__(self):
        self.seen = collections.defaultdict(list)       # (c, S) -> [(δ, verdict)]

    def get(self, c: str, s, delta: float):
        for d, v in self.seen[c, frozenset(s)]:
            if v["status"] == "infeasible" and delta <= d + 1e-12:
                return v
            if v["status"] == "drawable" and delta >= d - 1e-12:
                return v
            if v["status"] == "unknown" and abs(delta - d) <= 1e-12:
                return v
        return None

    def put(self, c: str, s, delta: float, verdict: dict) -> None:
        self.seen[c, frozenset(s)].append((delta, verdict))


def _name(s) -> str:
    return "+".join(sorted(s))


def drawable(inst, c: str, s, delta: float, ng, time_limit: float = CHECK_TIME,
             log=print) -> dict:
    """B's test (module docstring) of support `s` in channel `c` at δ: {"support", "delta",
    "status" (drawable | infeasible | unknown), "why", "seconds", "solves", "neck_cuts"}."""
    t0 = time.time()
    ch, units = inst.channels[c], inst.units
    adj, m = units.zip_adj, ch.m
    lo, hi = ch.tau * (1 - delta), ch.tau * (1 + delta)
    slack = BAND_TOL * ch.tau
    held = sorted(v for v in s if ch.mode[v] != "free")
    free_units = sorted(v for v in s if ch.mode[v] == "free")
    fixed = {z for v in held for z in units.zips[v]}
    F = sorted(z for v in free_units for z in units.zips[v])
    out = {"support": _name(s), "delta": delta, "status": "unknown", "why": "", "seconds": 0.0,
           "solves": 0, "neck_cuts": 0}

    def done(status, why):
        out.update(status=status, why=why, seconds=round(time.time() - t0, 2))
        return out

    def judge(X):
        """(status, why) of a connected candidate X from its necks."""
        nks = audit.district_necks(set(X), m, ng)
        if not nks:
            return "drawable", f"a district of {len(X)} ZIPs with no neck"
        nk = nks[0]
        return ("neck", nks) if all(n.status == "proved" for n in nks) else \
            ("unresolved", f"neck check unresolved ({nk.width_km:.2f} km, {len(nk.zips)} ZIPs)")
    mass_fixed = math.fsum(m.get(z, 0.0) for z in fixed)
    if not F:                       # held units only: one ZIP set
        if not lo - slack <= mass_fixed <= hi + slack:
            return done("infeasible", f"mass {mass_fixed / ch.tau:.4f} τ outside the band")
        comps = draw.components(fixed, adj)
        if len(comps) > 1:
            return done("infeasible", f"{len(comps)} components on the ZIP graph")
        st, why = judge(fixed)
        if st == "neck":
            nk = why[0]
            return done("infeasible", f"neck {nk.width_km:.2f} km cutting off {len(nk.zips)} ZIPs "
                                      f"from {min(nk.zips)}")
        return done("drawable" if st == "drawable" else "unknown", why)
    X = grow(inst, c, s, fixed, F, lo)
    if X is not None and lo - slack <= math.fsum(m.get(z, 0.0) for z in X) <= hi + slack \
            and len(draw.components(X, adj)) == 1 and judge(X)[0] == "drawable":
        return done("drawable", f"grown: a district of {len(X)} ZIPs with no neck")
    # bodies: the held units' components; nodes: free ZIPs and bodies
    bodies = draw.components(fixed, adj) if fixed else []
    bodies = sorted(bodies, key=lambda b: (-math.fsum(m.get(z, 0.0) for z in b), -len(b), min(b)))
    body_of = {z: i for i, b in enumerate(bodies) for z in b}
    fset = set(F)
    nodes = list(F) + [f"@{i}" for i in range(len(bodies))]
    ix = {v: i for i, v in enumerate(nodes)}
    nb = collections.defaultdict(set)
    for z in F:
        for y in adj[z]:
            if y in fset:
                nb[z].add(y)
            elif y in body_of:
                b = f"@{body_of[y]}"
                nb[z].add(b)
                nb[b].add(z)
    n_x, n_b = len(F), len(bodies)
    root = "@0" if bodies else None
    arcs = [(a, b) for a in nodes for b in sorted(nb[a]) if b != root]
    cap = float(n_x + n_b)
    km = {}
    for z in F:
        for y in adj[z]:
            km[z, y] = ng.border.get(z, {}).get(y, 0.0)
    pairs = sorted((z, y) for z in F for y in adj[z] if y in fset and z < y and km[z, y] > 0)
    # columns: x (n_x), c per free pair, f per arc, then without bodies r (n_x) and supply (n_x)
    x0, c0 = 0, n_x
    f0 = c0 + len(pairs)
    r0 = f0 + len(arcs)
    s0 = r0 + n_x
    nv = r0 + (0 if bodies else 2 * n_x)
    inf = highspy.kHighsInf
    lower, upper, cost = np.zeros(nv), np.ones(nv), np.zeros(nv)
    upper[f0:f0 + len(arcs)] = cap
    if not bodies:
        upper[s0:s0 + n_x] = cap
    for z in F:                     # the perimeter: border to S's held units and to outside S
        for y in adj[z]:
            if y in body_of:
                cost[ix[z]] -= km[z, y]
            elif y not in fset:
                cost[ix[z]] += km[z, y]
    for k, (z, y) in enumerate(pairs):
        cost[c0 + k] = km[z, y]
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("mip_rel_gap", CHECK_GAP)
    h.addVars(nv, lower, upper)
    h.changeColsCost(nv, np.arange(nv, dtype=np.int32), cost)
    ints = list(range(n_x)) + ([] if bodies else list(range(r0, r0 + n_x)))
    h.changeColsIntegrality(len(ints), np.array(ints, dtype=np.int32),
                            np.array([highspy.HighsVarType.kInteger] * len(ints)))

    def row(lo_, hi_, idx, val):
        h.addRow(lo_, hi_, len(idx), np.array(idx, dtype=np.int32), np.array(val, dtype=float))
    for k, (z, y) in enumerate(pairs):              # c ≥ |x_z − x_y|
        row(0.0, inf, [c0 + k, ix[z], ix[y]], [1.0, -1.0, 1.0])
        row(0.0, inf, [c0 + k, ix[z], ix[y]], [1.0, 1.0, -1.0])
    for v in free_units:                            # each free unit: a share of at least η
        zs = [z for z in units.zips[v] if m.get(z, 0.0) > 0]
        row(ch.spec.eta * ch.M[v], inf, [ix[z] for z in zs], [m[z] for z in zs])
    zs = [z for z in F if m.get(z, 0.0) > 0]        # the band
    row(lo - mass_fixed, hi - mass_fixed, [ix[z] for z in zs], [m[z] for z in zs])
    into, outs = collections.defaultdict(list), collections.defaultdict(list)
    for a, (u, v) in enumerate(arcs):
        into[v].append(f0 + a)
        outs[u].append(f0 + a)
        for w in (u, v):                            # flow only inside the district
            if w in fset:
                row(-inf, 0.0, [f0 + a, ix[w]], [1.0, -cap])
    for v in nodes:
        if v == root:
            continue
        idx = into[v] + outs[v]
        val = [1.0] * len(into[v]) + [-1.0] * len(outs[v])
        if v in fset:                               # each of its ZIPs consumes one unit
            if bodies:
                row(0.0, 0.0, idx + [ix[v]], val + [-1.0])
            else:
                i = ix[v]
                row(0.0, 0.0, idx + [i, s0 + i], val + [-1.0, 1.0])
                row(-inf, 0.0, [s0 + i, r0 + i], [1.0, -cap])     # supply at the root
                row(-inf, 0.0, [r0 + i, i], [1.0, -1.0])          # the root is the district's
        else:
            row(1.0, 1.0, idx, val)                 # every other body is reached
    if not bodies:
        row(1.0, 1.0, list(range(r0, r0 + n_x)), [1.0] * n_x)
    out["wide_pairs"] = wide_rows(inst, c, s, F, fixed, bodies, body_of, ix, nb, ng, h, nv, row)
    nv = h.getNumCol()
    owner = dict.fromkeys(fixed, "S")
    keys = set()

    def add_cut(cut) -> bool:
        """`draw.NeckCut`'s rows (as `draw._solve_group.add_neck_cut` builds them) for the one
        district "S"; False when the cut is known or never binds."""
        nonlocal nv
        big = cut.a_min - cut.share * cut.area_fixed
        if cut.const >= cut.need or big <= 0:
            return False
        key = (cut.const, cut.single, cut.pair, cut.anchors, cut.a_min)
        if key in keys:
            return False
        keys.add(key)
        single = collections.Counter()
        for z, w in cut.single:
            if w > 0:
                single[ix[z]] += w
        pr = [(u, v, w) for u, v, w in cut.pair if w > 0]
        k0 = nv
        h.addVars(len(pr) + 1, np.zeros(len(pr) + 1), np.ones(len(pr) + 1))
        nv += len(pr) + 1
        t = k0 + len(pr)
        h.changeColsIntegrality(1, np.array([t], dtype=np.int32),
                                np.array([highspy.HighsVarType.kInteger]))
        for i, (u, v, w) in enumerate(pr):          # y ≤ x_u, y ≤ x_v
            row(-inf, 0.0, [k0 + i, ix[u]], [1.0, -1.0])
            row(-inf, 0.0, [k0 + i, ix[v]], [1.0, -1.0])
            single[k0 + i] += w
        row(-cut.const, inf, list(single) + [t], list(single.values()) + [-cut.need])
        lhs = collections.Counter()
        for z, a in cut.area:
            if a > 0:
                lhs[ix[z]] += cut.share * a
        for z in cut.anchors:
            lhs[ix[z]] -= big
        lhs[t] += big
        row(cut.a_min - cut.share * cut.area_fixed - big * len(cut.anchors), inf,
            list(lhs), list(lhs.values()))
        return True
    deadline = t0 + time_limit
    while True:
        left = deadline - time.time()
        if left <= 1.0:
            return done("unknown", f"time limit after {out['solves']} solves")
        h.setOptionValue("time_limit", float(left))
        h.run()
        out["solves"] += 1
        st, info = h.getModelStatus(), h.getInfo()
        if st == highspy.HighsModelStatus.kInfeasible:
            return done("infeasible", f"proved at solve {out['solves']} with "
                                      f"{out['neck_cuts']} neck cuts")
        if info.primal_solution_status != 2:
            return done("unknown", f"no incumbent ({h.modelStatusToString(st)})")
        xs = h.getSolution().col_value
        X = fixed | {z for z in F if xs[ix[z]] > 0.5}
        if len(draw.components(X, adj)) > 1:        # the flow forbids it; a tolerance corner
            return done("unknown", "a disconnected incumbent")
        st2, why = judge(X)
        if st2 == "drawable":
            return done("drawable", why)
        if st2 == "unresolved":
            return done("unknown", why)
        own = {z: ("S" if z in X else "-") for z in F}
        cuts, _ = repair.neck_cuts(c, owner, fset, m, ng, own, {"S"})
        added = [cut for cut in cuts if add_cut(cut)]
        if not added or all(cut.holds(own) for cut in added):
            return done("unknown", f"a neck no new cut separates ({why[0].width_km:.2f} km)")
        out["neck_cuts"] += len(added)
        log(f"    {c} {_name(s)}: solve {out['solves']} has {len(why)} neck(s), "
            f"{len(added)} cuts added")


def certain_states(inst, s, fixed: set, ng) -> frozenset:
    """States every district with footprint S owns ZIPs in: those of its held ZIPs, and the state
    of each free unit lying in one state."""
    units = inst.units
    out = {ng.state.get(z, "") for z in fixed}
    for v in s:
        st = {ng.state.get(z, "") for z in units.zips[v]}
        if len(st) == 1:
            out |= st
    return frozenset(out)


def wide_rows(inst, c: str, s, F: list, fixed: set, bodies: list, body_of: dict, ix: dict,
              nb: dict, ng, h, nv: int, row) -> int:
    """B's wide-passage rows: for the heaviest body b0 and each other body b, a flow from b0 to b
    of at least `repair.NECK_KM`, each edge carrying at most its width (as M1 counts it, with the
    states certain to be the district's: `certain_states`, `repair._edge_km`) and only when both
    ends are the district's, required (q_b = 1) unless the smaller of the two bodies' land is
    below the share of the district's.  Valid for every connected district without a neck: when
    both bodies hold the share, a b0-b edge cut of width w gives a connected part (b0's side, or
    when that is more than half, b's) holding the share and no more than the rest, cut off by at
    most w, so w is at least 10 km and so is the flow (max-flow min-cut; contracting a body only
    removes cuts).  Returns the number of pairs."""
    if len(bodies) < 2:
        return 0
    inf = highspy.kHighsInf
    fset = set(F)
    states = certain_states(inst, s, fixed, ng)
    area = {z: ng.aland.get(z, 0.0) / 1e6 for z in list(F) + sorted(fixed)}
    area_fixed = math.fsum(area[z] for z in fixed)

    def node(z):
        return z if z in fset else f"@{body_of[z]}"
    width = collections.Counter()
    for z in list(F) + sorted(fixed):
        for y in set(ng.border.get(z, ())) | ng.connector.get(z, set()):
            if (y in fset or y in body_of) and node(z) != node(y):
                width[node(z), node(y)] += repair._edge_km(ng, z, y, states)
    width = {e: min(w, repair.NECK_KM) for e, w in width.items() if w > 0}
    arcs = sorted(width)
    b_area = [math.fsum(area[z] for z in b) for b in bodies]
    k = 0
    for bi in range(1, len(bodies)):
        src, dst = "@0", f"@{bi}"
        amin = min(b_area[0], b_area[bi])
        g0 = nv
        h.addVars(len(arcs) + 1, np.zeros(len(arcs) + 1),
                  np.array([width[e] for e in arcs] + [1.0]))
        q = g0 + len(arcs)
        nv += len(arcs) + 1
        h.changeColsIntegrality(1, np.array([q], dtype=np.int32),
                                np.array([highspy.HighsVarType.kInteger]))
        bal = collections.defaultdict(lambda: ([], []))
        for i, (a, b) in enumerate(arcs):
            bal[b][0].append(g0 + i)
            bal[a][1].append(g0 + i)
            for w in (a, b):                    # an edge carries flow only inside the district
                if w in fset:
                    row(-inf, 0.0, [g0 + i, ix[w]], [1.0, -width[a, b]])
        for v in list(F) + [f"@{i}" for i in range(len(bodies))]:
            ins, outs = bal[v]
            idx, val = ins + outs, [1.0] * len(ins) + [-1.0] * len(outs)
            if v == src:                        # out - in >= the limit when q = 1
                row(0.0, inf, idx + [q], [-x for x in val] + [-repair.NECK_KM])
            elif v != dst:
                row(0.0, 0.0, idx, val)
        # q = 0 only when the smaller body holds no more than the share of the district's land
        zs = [z for z in F if area[z] > 0]
        share = audit.NECK_SHARE * (1 - audit.NECK_TOL)
        row(amin - share * area_fixed, inf, [ix[z] for z in zs] + [q],
            [share * area[z] for z in zs] + [amin])
        k += 1
    return k


def grow(inst, c: str, s, fixed: set, F: list, lo: float):
    """A quick candidate for `drawable`, or None: from the held ZIPs (else the heaviest free
    ZIP), free ZIPs of S in breadth-first order (a compact ball) until each free unit holds η of
    its mass and the district holds `lo`.  It proves nothing; `drawable` judges it."""
    ch, units = inst.channels[c], inst.units
    adj, m = units.zip_adj, ch.m
    fset, unit_of = set(F), units.unit_of
    X = set(fixed) or {max(F, key=lambda z: (m.get(z, 0.0), z))}
    need = {v: ch.spec.eta * ch.M[v] * 1.001 for v in s if ch.mode[v] == "free"}
    have = collections.Counter()
    for z in X:
        have[unit_of[z]] += m.get(z, 0.0)
    total = math.fsum(m.get(z, 0.0) for z in X)
    for v in sorted(need, key=lambda v: (not any(y in X for z in units.zips[v] for y in adj[z]), v)):
        seen, queue = set(X), collections.deque(sorted(X))
        while have[v] < need[v] and queue:
            for y in sorted(adj[queue.popleft()]):
                if y in fset and y not in seen:
                    seen.add(y)
                    queue.append(y)
                    if unit_of[y] == v or have[v] < need[v]:
                        X.add(y)
                        have[unit_of[y]] += m.get(y, 0.0)
                        total += m.get(y, 0.0)
        if have[v] < need[v]:
            return None
    seen, queue = set(X), collections.deque(sorted(X))
    while total < lo and queue:
        for y in sorted(adj[queue.popleft()]):
            if y in fset and y not in seen and total < lo:
                seen.add(y)
                queue.append(y)
                X.add(y)
                total += m.get(y, 0.0)
    return X if total >= lo else None


def _record_verdict(v: dict) -> dict:
    return {k: v[k] for k in ("support", "delta", "status", "why", "seconds", "solves",
                              "neck_cuts")}


def plan_checked(inst, c: str, delta: float | None = None, fam=None, checks: Checks | None = None,
                 ng=None, time_limit: float | None = None, check_time: float = CHECK_TIME,
                 log=print) -> tuple:
    """(Plan or None, solver report, record): B's lazy loop (module docstring) at δ.  The record
    lists each test (`tested`), the supports cut with the master's objective before and after
    (`bans`), the unknown ones (`unknown`) and the loop's `status`: `passed` (every multi-unit
    support in use drawable or unknown), or the master's status when it ends without a plan."""
    ch = inst.channels[c]
    delta = ch.spec.delta if delta is None else delta
    fam = supports.family(inst, c) if fam is None else fam
    checks = Checks() if checks is None else checks
    banned, rec = [], {"delta": delta, "iterations": 0, "tested": [], "bans": [], "unknown": []}
    seen, pending = set(), []
    while True:
        rec["iterations"] += 1
        p, rep = master.plan(inst, c, delta, fam, time_limit=time_limit, banned=banned)
        for b in pending:                   # the cost of the last iteration's cuts
            b["objective_after"] = None if p is None else p.objective
        if p is None:
            rec["status"] = rep.get("status")
            return None, rep, rec
        pending = []
        for s in sorted(p.n, key=lambda s: (len(s), sorted(s))):
            if len(s) < 2 or s in seen:
                continue
            seen.add(s)
            v = checks.get(c, s, delta)
            if v is None:
                v = drawable(inst, c, s, delta, ng, check_time, log)
                checks.put(c, s, delta, v)
            rec["tested"].append(_record_verdict(v))
            log(f"  {c} B: {_name(s)} at δ {delta:g}: {v['status']} ({v['why']})")
            if v["status"] == "infeasible":
                pending.append({**_record_verdict(v), "objective_before": p.objective})
            elif v["status"] == "unknown":
                rec["unknown"].append(_record_verdict(v))
        if not pending:
            rec["status"] = "passed"
            return p, rep, rec
        rec["bans"] += pending
        banned += [frozenset(b["support"].split("+")) for b in pending]


def checked_delta(inst, c: str, lo: float, first: float | None, checks: Checks, ng,
                  time_limit=None, check_time: float = CHECK_TIME, log=print) -> dict:
    """replan.py's rule under B: the smallest δ in (lo, final_delta] at which `plan_checked` finds
    a plan (`lo` has none), probing `first` (the master's own smallest δ) first, then
    `final_delta`, then bisecting to `master.DELTA_TOL`.  {"status" (converged | infeasible |
    unknown), "delta" (a δ shown to have a checked plan), "lower", "steps": [{δ, loop status, B
    bans}]}."""
    top = inst.channels[c].spec.final_delta
    fam = supports.family(inst, c)
    steps = []

    def probe(d):
        p, rep, rec = plan_checked(inst, c, d, fam, checks, ng, time_limit, check_time, log)
        steps.append({"delta": d, "status": rec["status"],
                      "bans": [b["support"] for b in rec["bans"]]})
        return "feasible" if p is not None else ("infeasible" if rec["status"] == "infeasible"
                                                 else "unknown")
    if first is not None and lo < first < top:
        v = probe(first)
        if v == "feasible":
            return {"status": "converged", "delta": first, "lower": lo, "steps": steps}
        if v == "unknown":
            return {"status": "unknown", "delta": None, "lower": lo, "steps": steps}
        lo = first
    v = probe(top)
    if v != "feasible":
        return {"status": v, "delta": None, "lower": lo, "steps": steps}
    hi = top
    while hi - lo > master.DELTA_TOL:
        mid = (lo + hi) / 2
        v = probe(mid)
        if v == "unknown":
            return {"status": "unknown", "delta": hi, "lower": lo, "steps": steps}
        if v == "feasible":
            hi = mid
        else:
            lo = mid
    return {"status": "converged", "delta": hi, "lower": lo, "steps": steps}


# ------------------------------------------------------------------------------ C: the loop
PIECE_LINE = re.compile(r"^budget spent: (\S+) (?:ball|corridor) \S+ of (\S+) not tried", re.M)
NECK_LINE = re.compile(r"^budget spent: (\S+) neck of (\S+), ", re.M)


def causes(inst, plan, owner: dict, attempts: list, log_text: str, ng, h0: int,
           max_zctas: int) -> list:
    """Each detached piece and neck left on a repaired channel's map `owner`, with its cause from
    the repair's `attempts` (contig.json's `repair`) and log: "budget spent" when the log says a
    window of its district was not tried, else the last window on it ("window infeasible (outside
    fixed)", "window unknown at its time limit", a drawing not kept), or "no window tried".  The
    window: its attempt index, shape, size, |W| and whether the `max_zctas` cap stopped its growth
    (the ball one hop past the last tried exceeds it)."""
    c = plan.channel
    ch = inst.channels[c]
    adj, m = inst.units.zip_adj, ch.m
    _, free, _ = draw.split_fixed(inst, plan)
    free &= set(owner)
    support = {cp.name: cp.support for cp in plan.copies}
    spent_piece = {j for cc, j in PIECE_LINE.findall(log_text) if cc == c}
    spent_neck = {j for cc, j in NECK_LINE.findall(log_text) if cc == c}
    left = [("piece", j, cc) for j, cc in repair.detached(owner, adj, m)]
    left += [("neck", j, side) for j, side, _ in repair.necks(owner, m, ng)]
    out = []
    for kind, j, zs in left:
        mine = [(i, t) for i, t in enumerate(attempts)
                if (t.get("kind") == "neck") == (kind == "neck")
                and any(x.startswith(f"{j} ") for x in t.get("cluster", ()))]
        exact = [(i, t) for i, t in mine if any(x.startswith(f"{j} {min(zs)} ") for x in t["cluster"])]
        mine = exact or mine
        rec = {"channel": c, "kind": kind, "district": j, "support": sorted(support[j]),
               "zips": len(zs), "first": min(zs),
               "tau": round(math.fsum(m.get(z, 0.0) for z in zs) / ch.tau, 4),
               "windows": dict(collections.Counter(t["status"] for _, t in mine))}
        if j in (spent_neck if kind == "neck" else spent_piece):
            rec["cause"] = "budget spent"
        elif not mine:
            rec["cause"] = "no window tried"
        else:
            i, t = mine[-1]
            st = t["status"]
            rec["cause"] = (INFEASIBLE if st == "infeasible" else
                            "window unknown at its time limit" if st == "unknown" else
                            f"window {st}, drawing not kept")
            size_key = next(k for k in ("h", "slack", "zctas") if k in t)
            balls = [x.get("h") for _, x in mine if x.get("shape") == "ball"]
            capped = None
            if kind == "piece" and balls:
                pcs = [(j, zs)]
                capped = len(repair.ball(pcs, free, adj, max(balls) + 1, max_zctas // 2)) > max_zctas
            rec["window"] = {"attempt": i, "shape": t["shape"], size_key: t[size_key],
                             "window_zctas": t["window_zctas"], "status": st,
                             "cap": t.get("cap"), "max_zctas": max_zctas,
                             "cap_stopped_growth": capped}
        out.append(rec)
    return out


def new_bans(found: list, inst, done: dict, banned: dict) -> list:
    """The supports to ban next round: each district left with `INFEASIBLE` in a channel whose
    `replan_rounds` exceeds its rounds `done`, not banned already; one record per support (its
    first piece or neck as the evidence)."""
    out, seen = [], set()
    for f in found:
        c, s = f["channel"], frozenset(f["support"])
        if f["cause"] != INFEASIBLE or (c, s) in seen or s in banned.get(c, set()):
            continue
        if done.get(c, 0) >= inst.channels[c].spec.replan_rounds:
            continue
        seen.add((c, s))
        out.append({"channel": c, "support": sorted(s), "evidence": {
            "district": f["district"], "kind": f["kind"], "zips": f["zips"], "first": f["first"],
            "tau": f["tau"], "cause": INFEASIBLE, **f["window"]}})
    return out


def close_round(entry: dict, prev: dict | None, inst, done: dict, banned: dict, last: bool) -> list:
    """C's bookkeeping after a round's repair: the cost of the previous round's bans (`cost`
    before, in `prev`, and after, in `entry`), this round's bans (`new_bans` on `entry["left"]`)
    and, unless the loop stops (`entry["stop"]`: nothing to ban, or the `last` round), those bans
    added to `banned` {channel: set of supports} and a round counted in `done` per channel."""
    if prev is not None:
        for b in prev["bans"]:
            b["cost"] = {"before": prev["cost"][b["channel"]], "after": entry["cost"][b["channel"]]}
    nb = new_bans(entry["left"], inst, done, banned)
    entry["bans"] = nb
    if not nb or last:
        entry["stop"] = ("no window proved infeasible: nothing to ban" if not nb
                         else "replan_rounds used; bans listed, not applied")
        return nb
    for b in nb:
        banned.setdefault(b["channel"], set()).add(frozenset(b["support"]))
    for c in {b["channel"] for b in nb}:
        done[c] = done.get(c, 0) + 1
    return nb


def map_cost(folder: str, plans: dict) -> dict:
    """{channel: {"delta", "objective", "splits", "cuts"}} of a run folder: the plan's δ and the
    master's objective, and the drawn map's split states and extra holders per state (as
    `repair.map_figures` counts them) from its ledger."""
    from td import output
    states = collections.defaultdict(lambda: collections.defaultdict(set))
    for r in output.read_ledger(os.path.join(folder, "ledger.csv")):
        if r["district"]:
            states[r["model_channel"]][r["state"]].add(r["district"])
    out = {}
    for c, p in plans.items():
        split = [s for s, ds in states[c].items() if len(ds) > 1]
        out[c] = {"delta": p.delta, "objective": p.objective, "splits": len(split),
                  "cuts": sum(len(states[c][s]) - 1 for s in split)}
    return out


def spec_keys(spec_path: str) -> dict:
    from td import spec as tdspec
    return {c: {"contact_min_km": cs.contact_min_km, "drawable_alone": cs.drawable_alone,
                "replan_rounds": cs.replan_rounds,
                "ban_supports": sorted(_name(s) for s in cs.ban_supports)}
            for c, cs in tdspec.load(spec_path).channels.items()}


def stamp(folder: str, block: dict) -> None:
    """Add `plan_check` to the folder's run.json and manifest.json, keeping every other field."""
    for f in ("run.json", "manifest.json"):
        path = os.path.join(folder, f)
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        doc["plan_check"] = block
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")


def _python() -> str:
    return sys.executable


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("spec", help="the copy with the #124 keys (never a stored TOML)")
    ap.add_argument("--root", required=True, help="where the run folders and copies go")
    ap.add_argument("--name", required=True, help="the run id; rounds add -c1, -c2, ...")
    ap.add_argument("--parent", required=True, help="the run the copy derives from (manifest)")
    ap.add_argument("--plans", required=True)
    ap.add_argument("--round0", default=None,
                    help="a repaired folder of the same plan to read as round 0 instead of drawing")
    ap.add_argument("--planned", default=None,
                    help="replan.py's report: the copy is planned already (its plans cached)")
    ap.add_argument("--extract", default=os.path.join(os.environ.get("TD_REPO", ROOT),
                                                      "instance_descaled.json.gz"))
    ap.add_argument("--budget", type=float, default=1200.0, help="repair seconds per channel")
    ap.add_argument("--h0", type=int, default=8)
    ap.add_argument("--max-zctas", type=int, default=2000)
    ap.add_argument("--time-limit", type=float, default=300.0)
    ap.add_argument("--neck-time-limit", type=float, default=240.0)
    ap.add_argument("--check-time", type=float, default=CHECK_TIME)
    ap.add_argument("--label", default="#124 plan check")
    a = ap.parse_args(argv)
    from td import geo, output
    replan = _load("contig_replan", "replan.py")
    run = _load("contig_run", "run.py")
    specs = os.path.join(a.root, "_specs")
    os.makedirs(specs, exist_ok=True)
    polygon = geo.polygon_graph()
    ng = audit.NeckGraph(polygon)
    keys0 = spec_keys(a.spec)
    rounds = max((k["replan_rounds"] for k in keys0.values()), default=0)
    with open(a.spec, encoding="utf-8") as fh:
        base = fh.read()
    banned = collections.defaultdict(set)       # channel -> supports banned so far (C)
    history, done = [], collections.Counter()
    parent, prev = a.parent, None
    for r in range(rounds + 1):
        name = a.name if r == 0 else f"{a.name}-c{r}"
        folder = os.path.join(a.root, name)
        if r == 0:
            spec_r = a.spec
        else:
            spec_r = os.path.join(specs, f"{name}.toml")
            extra = {c: {"ban_supports": "[" + ", ".join(
                "[" + ", ".join(f'"{u}"' for u in sorted(s)) + "]"
                for s in sorted(ss, key=sorted)) + "]"} for c, ss in banned.items() if ss}
            with open(spec_r, "w", encoding="utf-8") as fh:
                fh.write(f"# #124 C round {r}: a copy of {os.path.abspath(a.spec)} with the support "
                         "bans of rounds before (tools/exp/contig/plancheck.py)\n"
                         + replan.banned_text(base, [], keys=extra))
        report = os.path.join(specs, f"{name}.json")
        if r == 0 and a.round0:
            folder = os.path.abspath(a.round0)
            with open(os.path.join(folder, "run.json")) as fh:
                spec_r = json.load(fh)["spec"]
            report = re.sub(r"(-planned)?\.toml$", ".json", spec_r)
        else:
            if r == 0 and a.planned:
                rc, report = 0, a.planned
            else:
                rc = replan.main([spec_r, "--out-spec", os.path.join(specs, f"{name}-planned.toml"),
                                  "--plans", a.plans, "--report", report, "--keep",
                                  "--check-time", str(a.check_time)])
                spec_r = os.path.join(specs, f"{name}-planned.toml")
            if rc != 0:
                history.append({"round": r, "folder": None, "spec": spec_r,
                                "stop": f"no plan (replan.py exit {rc}, {report})"})
                break
            cmd = [_python(), "-u", os.path.join(HERE, "run.py"), spec_r, "--plans", a.plans,
                   "--out", folder + "-draw", "--arm", "arm1", "--sequential", "--parent", parent]
            with open(folder + "-draw.log", "w") as lg:
                subprocess.run(cmd, stdout=lg, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            if not os.path.exists(os.path.join(folder + "-draw", "ledger.csv")):
                history.append({"round": r, "folder": None, "spec": spec_r, "stop": "draw failed"})
                break
            cmd = [_python(), "-u", os.path.join(HERE, "repair.py"), folder + "-draw", "--out",
                   folder, "--plans", a.plans, "--keep-support", "--flow", "--max-zctas",
                   str(a.max_zctas), "--budget", str(a.budget), "--h0", str(a.h0), "--time-limit",
                   str(a.time_limit), "--neck-time-limit", str(a.neck_time_limit), "--label",
                   f"{a.label} round {r}"]
            with open(folder + ".log", "w") as lg:
                subprocess.run(cmd, stdout=lg, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
            if not os.path.exists(os.path.join(folder, "ledger.csv")):
                history.append({"round": r, "folder": None, "spec": spec_r, "stop": "repair failed"})
                break
        s, ref, ext, _, inst, plans, _, owners, _ = repair.load(folder, a.extract, a.plans)
        with open(os.path.join(folder, "contig.json")) as fh:
            contig = json.load(fh)
        log_path = folder + ".log"
        log_text = open(log_path).read() if os.path.exists(log_path) else ""
        found = []
        for c, p in plans.items():
            found += causes(inst, p, owners[c], contig["channels"][c].get("repair", []),
                            log_text, ng, a.h0, a.max_zctas)
        cost = map_cost(folder, plans)
        rep = {"channels": {}}
        if os.path.exists(report):
            with open(report) as fh:
                rep = json.load(fh)
        entry = {"round": r, "folder": folder, "spec": spec_r, "replan_report": report,
                 "plan_check_B": {c: e.get("plan_check") for c, e in rep["channels"].items()},
                 "cost": cost, "left": found, "bans_applied": {c: sorted(_name(x) for x in ss)
                                                                for c, ss in banned.items()}}
        nb = close_round(entry, prev, inst, done, banned, r == rounds)
        history.append(entry)

        def block(stop=None):
            return {"keys": spec_keys(spec_r), "stop": stop, "left": found,
                    "rounds": [{k: v for k, v in e.items() if k != "left"} for e in history]}
        mine = [e for e in history if e["folder"] != (a.round0 and os.path.abspath(a.round0))]
        if prev is not None and prev in mine:   # a reused round 0 keeps its own record
            stamp(prev["folder"], {**block(prev.get("stop")), "left": prev["left"],
                                   "keys": spec_keys(prev["spec"])})
        if entry in mine:
            stamp(folder, block(entry.get("stop")))
        if entry.get("stop"):
            break
        prev, parent = entry, folder
    with open(os.path.join(a.root, f"{a.name}-plancheck.json"), "w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2, sort_keys=True, default=str)
        fh.write("\n")
    print(f"{a.name}: {len(history)} round(s); last {history[-1].get('folder')}; "
          f"{history[-1].get('stop', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
