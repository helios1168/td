"""td.master: the support master, its decoding and the smallest δ (#68).

Brute force checks the master on small random toys: every explicit-copy plan (Claim 1(iii)) is
enumerated as a multiset of K supports, its integer rows are counted, and a per-copy LP decides
its shares.  The drawability rows bind on hand-built toys whose answers are worked out in the
test's docstrings.  The exact and bisection smallest δ agree on clipped toys and on the fixture's
51 scenario with its free units clipped (TIGER/Line 2025 state polygons needed; SKIP without).
"""
from __future__ import annotations

import collections
import itertools
import json
import math
import os
import random
import tempfile
import tomllib

from scipy.optimize import linprog

from td import audit, master, spec, supports

from tests import test_spec as ts

UNITS = ("AL", "AR", "AZ", "CA", "CO", "CT")


def _toy(unit_zips: dict, edges, mass: dict, xy: dict, modes=None, **channel):
    """A one-channel toy.  `xy` gives each ZIP's point in km; `modes` {unit: mode}."""
    raw = ts._toy_raw(max_dist_km=1e9, **channel)
    for m in ("clipped", "free"):
        listed = [u for u, v in (modes or {}).items() if v == m]
        if listed:
            raw["channels"]["X"][m] = listed
    s = spec.parse(raw)
    unit_of = {z: u for u, zs in unit_zips.items() for z in zs}
    units = spec.Units.from_graph(unit_of, edges, {z: (1000.0 * x, 1000.0 * y)
                                                   for z, (x, y) in xy.items()})
    return spec.assemble(s, units, {(z, "f"): m for z, m in mass.items()})


def _held(ch, v, s) -> bool:
    return ch.mode[v] == "whole" or (ch.mode[v] == "clipped" and len(s) > 1)


def _brute(inst, channel="X", delta=None):
    """The least Σ w_S over explicit-copy plans that obey the per-copy rows, or inf."""
    ch = inst.channels[channel]
    delta = ch.spec.delta if delta is None else delta
    fam = supports.family(inst, channel)
    floors = supports.corridor_floors(inst, fam)
    borders = supports.border_rows(inst, fam)
    lo, hi = ch.tau * (1 - delta), ch.tau * (1 + delta)
    best = math.inf
    for combo in itertools.combinations_with_replacement(fam.supports, ch.k):
        count = collections.Counter(combo)
        touch = collections.Counter(v for s in combo for v in s)
        if set(ch.units) - set(touch):
            continue
        if any(n > 1 and any(_held(ch, v, s) for v in s) for s, n in count.items()):
            continue
        if any(touch[v] > len(inst.units.zips[v]) for v in touch):
            continue
        if any(touch[v] > cap for v, cap in ch.spec.contact_caps.items()):
            continue
        if any(sum(count[s] for s in over) > b for b, over in borders.values()):
            continue
        cost = math.fsum(supports.diameter(inst, s) for s in combo)
        if cost >= best - 1e-9:
            continue
        # the per-copy LP: y_{j,v} ≥ η, held units at 1, the corridor floor as a lower bound
        cols, bounds = [], []
        for j, s in enumerate(combo):
            for v in sorted(s):
                low = ch.spec.eta
                if (s, v) in floors:
                    low = max(low, floors[s, v] / ch.M[v])
                cols.append((j, v))
                bounds.append((1.0, 1.0) if _held(ch, v, s) else (low, 1.0))
        if any(b[0] > 1.0 + 1e-12 for b in bounds):
            continue
        a_eq = [[1.0 if c[1] == v else 0.0 for c in cols] for v in ch.units]
        a_ub, b_ub = [], []
        for j, s in enumerate(combo):
            mu = supports.margin(inst, channel, s)
            row = [ch.M[c[1]] if c[0] == j else 0.0 for c in cols]
            a_ub += [row, [-a for a in row]]
            b_ub += [hi - mu, -(lo + mu)]
        res = linprog([0.0] * len(cols), A_ub=a_ub, b_ub=b_ub, A_eq=a_eq, b_eq=[1.0] * len(a_eq),
                      bounds=bounds, method="highs-ds", options={"presolve": True})
        if res.status == 0:
            best = cost
    return best


def _random_toy(rng, n_units=None, modes=("whole", "clipped", "free"), k=None):
    names = UNITS[:n_units or rng.randint(3, 5)]
    unit_zips, edges, mass, xy = {}, [], {}, {}
    for u in names:
        zs = [f"{u.lower()}{i}" for i in range(rng.randint(2, 4))]
        unit_zips[u] = zs
        edges += list(zip(zs, zs[1:]))
        cx, cy = rng.uniform(0, 50), rng.uniform(0, 50)
        for z in zs:
            mass[z] = rng.choice([0.1, 0.15, 0.2, 0.4])
            xy[z] = (cx + rng.uniform(-1, 1), cy + rng.uniform(-1, 1))
    for i, u in enumerate(names[1:], 1):         # a random tree, plus one extra edge
        w = rng.choice(names[:i])
        edges.append((rng.choice(unit_zips[u]), rng.choice(unit_zips[w])))
    a, b = rng.sample(names, 2)
    edges.append((rng.choice(unit_zips[a]), rng.choice(unit_zips[b])))
    mode = {u: rng.choice(modes) for u in names}
    return _toy(unit_zips, edges, mass, xy, mode, k=k or rng.randint(2, 3),
                delta=rng.choice([0.4, 0.6, 0.9]), eta=rng.choice([0.05, 0.2]))


def _check_plan(inst, p):
    """Claim 1(i)–(ii) on a decoded plan: K copies, shares summing to 1, footprints exactly the
    supports, masses inside the band with margin, and no support with a held unit repeated."""
    ch = inst.channels[p.channel]
    lo, hi = ch.tau * (1 - p.delta), ch.tau * (1 + p.delta)
    assert len(p.copies) == ch.k
    got = collections.defaultdict(list)
    for c in p.copies:
        assert set(c.share) == set(c.support)
        assert all(y >= ch.spec.eta - master.FEAS_TOL for y in c.share.values())
        mu = supports.margin(inst, p.channel, c.support)
        slack = master.FEAS_TOL * ch.tau
        assert lo + mu - slack <= c.total <= hi - mu + slack, (sorted(c.support), c.total)
        for v, y in c.share.items():
            got[v].append(y)
    for v in ch.units:
        assert abs(math.fsum(got[v]) - 1.0) <= 1e-12, (v, got[v])
    for s, n in p.n.items():
        if any(_held(ch, v, s) for v in s):
            assert n == 1, sorted(s)
            assert all(c.share[v] == 1.0 for c in p.copies if c.support == s
                       for v in s if _held(ch, v, s))


# ------------------------------------------------------------------------------ the rows
def test_every_row_of_model_md_is_built():
    """§3's rows, one per key: cover per unit, η and t ≤ n per (v, S), two band rows per S, held
    units, the contact cap, the corridor floor per cut vertex, the corrected border cap (C7) and
    the count cap; n_S ≤ 1 wherever a unit is held."""
    unit_zips = {"AL": ["a1"], "AR": ["b1", "b2", "b3"], "AZ": ["c1", "c2"], "CA": ["d1"]}
    edges = [("a1", "b1"), ("b1", "b2"), ("b2", "b3"), ("b3", "c1"), ("c1", "c2"), ("c2", "d1")]
    mass = {"a1": 1.0, "b1": 0.5, "b2": 0.5, "b3": 0.5, "c1": 0.7, "c2": 0.3, "d1": 1.0}
    xy = {z: (i, 0.0) for i, z in enumerate(sorted(mass))}
    inst = _toy(unit_zips, edges, mass, xy, {"AR": "free", "AZ": "clipped"}, k=2, delta=0.4,
                contact_caps={"AR": 2})
    ch = inst.channels["X"]
    fam = supports.family(inst, "X")
    m = master.build(inst, "X", fam=fam)
    pairs = {(v, s) for s in fam.supports for v in s}
    assert set(m.rows_of("count")) == {()}
    assert set(m.rows_of("cover")) == {(v,) for v in ch.units}
    assert set(m.rows_of("eta")) == set(m.rows_of("share")) == pairs
    assert set(m.rows_of("band_lo")) == set(m.rows_of("band_hi")) == {(s,) for s in fam.supports}
    assert set(m.rows_of("hold")) == {(v, s) for v, s in pairs if _held(ch, v, s)}
    assert set(m.rows_of("contact")) == {("AR",)}
    floors = supports.corridor_floors(inst, fam)
    assert floors and set(m.rows_of("corridor")) == set(floors)
    border = {k for k, (_, over) in supports.border_rows(inst, fam).items() if over}
    assert border and set(m.rows_of("border")) == border
    assert set(m.rows_of("count_cap")) == {(v,) for v in ch.units}
    assert set(m.rows_of("eta_cap")) == {(v,) for v in ch.units}
    assert m.rows_of("eta_cap")[("AR",)].hi == master.eta_cap(ch.spec.eta)
    for s in fam.supports:
        assert m.upper[m.n_col[s]] == (1.0 if any(_held(ch, v, s) for v in s) else ch.k)
    # the rows carry MODEL.md's coefficients, in masses over τ
    s = frozenset(["AL", "AR", "AZ"])
    lo = m.rows_of("band_lo")[(s,)]
    mu = supports.margin(inst, "X", s)
    assert math.isclose(-lo.coef[m.n_col[s]], (1 - 0.4) + mu / ch.tau)
    assert math.isclose(lo.coef[m.t_col["AR", s]], ch.M["AR"] / ch.tau)
    c = m.rows_of("corridor")[(s, "AR")]
    assert math.isclose(-c.coef[m.n_col[s]], floors[s, "AR"] / ch.tau)
    assert m.rows_of("count_cap")[("AR",)].hi == 3


# ------------------------------------------------------------------------------ brute force
def test_the_master_agrees_with_brute_force_on_random_toys():
    rng = random.Random(68)
    solved = infeasible = 0
    for _ in range(40):
        inst = _random_toy(rng)
        want = _brute(inst)
        p, rep = master.plan(inst, "X")
        if math.isinf(want):
            assert p is None and rep["status"] == "infeasible", rep
            infeasible += 1
            continue
        assert p is not None, rep
        assert math.isclose(p.objective, want, rel_tol=1e-7, abs_tol=1e-7), (p.objective, want)
        assert rep["status"] == "optimal" and audit.tier(rep) == "exact"
        _check_plan(inst, p)
        solved += 1
    assert solved >= 15 and infeasible >= 5, (solved, infeasible)


def test_whole_toys_are_set_partitions():
    """With every unit whole, a plan is a partition of the units into K supports in the band."""
    rng = random.Random(7)
    for _ in range(15):
        inst = _random_toy(rng, n_units=5, modes=("whole",))
        ch = inst.channels["X"]
        fam = supports.family(inst, "X")
        lo, hi = ch.tau * (1 - ch.spec.delta), ch.tau * (1 + ch.spec.delta)
        best = math.inf
        for blocks in itertools.combinations(fam.supports, ch.k):
            if sorted(v for b in blocks for v in b) == sorted(ch.units) and all(
                    lo <= math.fsum(ch.M[v] for v in b) <= hi for b in blocks):
                best = min(best, math.fsum(supports.diameter(inst, b) for b in blocks))
        p, _ = master.plan(inst, "X")
        assert (p is None) == math.isinf(best)
        if p is not None:
            assert math.isclose(p.objective, best, rel_tol=1e-9, abs_tol=1e-9)
            assert all(n == 1 for n in p.n.values())


# ------------------------------------------------------------------------------ binding rows
def _star_border_toy():
    """X1 and X2 whole (mass 1), U free (u1 0.1, u2 0.2, u3 0.2) and V free (six ZIPs of 0.25),
    with X1, X2 and V each touching U only at u1.  K = 2, τ = 2, δ = 0.3: band [1.4, 2.6].

    - {X1,U,V} + {X2,U,V}, cost 2·√26 ≈ 10.198: each copy has μ = 0.45, so mass in
      [1.85, 2.15]; 2 each works.  But V enters both copies through its one border ZIP v1, so
      the corrected border cap n_{X1UV} + n_{X2UV} ≤ b_{UV} = 1 (C7) excludes it.
    - {X1,U,X2} + {U,V}, cost 10 + 1 = 11: {X1,U,X2} holds 2 + 0.5a ≤ 2.4 and the corridor
      floor through u1 asks 0.5a ≥ 0.1; {U,V} holds 0.5(1 − a) + 1.5 ≥ 1.85, so a ∈ [0.2, 0.3].
    - Every other plan leaves a copy outside its band.
    So the answer is 11 on {X1,U,X2} and {U,V}, and 2√26 without the border rows."""
    unit_zips = {"AL": ["x1"], "AR": ["x2"], "AZ": ["u1", "u2", "u3"],
                 "CA": [f"v{i}" for i in range(1, 7)]}
    edges = [("x1", "u1"), ("x2", "u1"), ("u1", "u2"), ("u2", "u3"), ("v1", "u1")]
    edges += [(f"v{i}", f"v{i + 1}") for i in range(1, 6)]
    mass = {"x1": 1.0, "x2": 1.0, "u1": 0.1, "u2": 0.2, "u3": 0.2}
    mass.update({f"v{i}": 0.25 for i in range(1, 7)})
    xy = {"x1": (-5, 0), "x2": (5, 0), "u1": (0, 0), "u2": (0, 0), "u3": (0, 0)}
    xy.update({f"v{i}": (0, 1) for i in range(1, 7)})
    return _toy(unit_zips, edges, mass, xy, {"AZ": "free", "CA": "free"}, k=2, delta=0.3,
                eta=0.1)


def test_the_border_cap_binds_on_the_hand_checked_star():
    inst = _star_border_toy()
    p, rep = master.plan(inst, "X")
    assert math.isclose(p.objective, 11.0, rel_tol=1e-9)
    assert set(p.n) == {frozenset(["AL", "AR", "AZ"]), frozenset(["AZ", "CA"])}
    a = p.t["AZ", frozenset(["AL", "AR", "AZ"])]
    assert 0.2 - 1e-7 <= a <= 0.3 + 1e-7
    assert math.isclose(_brute(inst), 11.0, rel_tol=1e-9)
    m = master.build(inst, "X")
    assert m.rows_of("border")[("AZ", "CA")].hi == 1
    m.rows = [r for r in m.rows if r.kind != "border"]
    free = master.solve(m)
    assert math.isclose(free.objective, 2 * math.sqrt(26), rel_tol=1e-9)


def _c6_path_toy():
    """A and B whole (mass 4) at the ends of V, free, a unit-mass path z1…z5 (A–z1, z5–B).
    K = 2, τ = 6.5, δ = 0.5: band [3.25, 9.75], every margin 1.

    - {A,V,B} + {V}, cost 4 + 0 = 4, is feasible without the corridor floor: {A,V,B} holds
      8 + 5x ≤ 8.75 and {V} 5(1 − x) ≥ 4.25, so x ∈ [0.1, 0.15].  But V separates A from B, and
      the lightest path from z1 to z5 is all five ZIPs: c_V = 5 forces x = 1 and leaves {V} empty.
    - {A,V} + {V,B}, cost 4 + 3 = 7: 4 + 5t each, inside [4.25, 8.75].
    So the answer is 7, and 4 without the corridor rows."""
    unit_zips = {"AL": ["a"], "AR": ["b"], "AZ": [f"z{i}" for i in range(1, 6)]}
    edges = [("a", "z1"), ("z5", "b")] + [(f"z{i}", f"z{i + 1}") for i in range(1, 5)]
    mass = {"a": 4.0, "b": 4.0, **{f"z{i}": 1.0 for i in range(1, 6)}}
    xy = {"a": (0, 0), "b": (1, 0), **{f"z{i}": (i + 1, 0) for i in range(1, 6)}}
    return _toy(unit_zips, edges, mass, xy, {"AZ": "free"}, k=2, delta=0.5, eta=0.1)


def test_the_corridor_floor_binds_on_the_hand_checked_path():
    inst = _c6_path_toy()
    fam = supports.family(inst, "X")
    avb = frozenset(["AL", "AR", "AZ"])
    assert supports.corridor_floors(inst, fam)[avb, "AZ"] == 5.0
    p, _ = master.plan(inst, "X", fam=fam)
    assert math.isclose(p.objective, 7.0, rel_tol=1e-9)
    assert set(p.n) == {frozenset(["AL", "AZ"]), frozenset(["AR", "AZ"])}
    assert math.isclose(_brute(inst), 7.0, rel_tol=1e-9)
    m = master.build(inst, "X", fam=fam)
    m.rows = [r for r in m.rows if r.kind != "corridor"]
    free = master.solve(m)
    assert math.isclose(free.objective, 4.0, rel_tol=1e-9)
    n, t, _ = master.decode(inst, m, free.x)
    assert n == {avb: 1, frozenset(["AZ"]): 1}
    assert 0.1 - 1e-7 <= t["AZ", avb] <= 0.15 + 1e-7


def _hub_toy():
    """Six whole leaves of mass 1 around V, free, with two ZIPs: v1 (0.001) and v2 (0.1), both
    touching every leaf.  K = 3, τ ≈ 2.034, δ = 0.1; a leaf alone (1) is under the band, and three
    leaves (3) are over it, so every district is two leaves joined through V.  Three districts
    then touch V, which has two ZIPs: the count cap (C8) makes the master infeasible, and without
    it the plan is feasible (the corridor floor, 0.001, asks each copy for only ~1% of V)."""
    leaves = ("AL", "AR", "AZ", "CA", "CO", "CT")
    unit_zips = {u: [u.lower()] for u in leaves} | {"DE": ["v1", "v2"]}
    edges = [("v1", "v2")] + [(u.lower(), v) for u in leaves for v in ("v1", "v2")]
    mass = {u.lower(): 1.0 for u in leaves} | {"v1": 0.001, "v2": 0.1}
    xy = {u.lower(): (math.cos(i), math.sin(i)) for i, u in enumerate(leaves)}
    xy |= {"v1": (0, 0), "v2": (0, 0)}
    return _toy(unit_zips, edges, mass, xy, {"DE": "free"}, k=3, delta=0.1, eta=0.001)


def test_the_count_cap_binds_on_the_hand_checked_hub():
    inst = _hub_toy()
    p, rep = master.plan(inst, "X")
    assert p is None and rep["status"] == "infeasible"
    assert math.isinf(_brute(inst))
    m = master.build(inst, "X")
    assert m.rows_of("count_cap")[("DE",)].hi == 2
    m.rows = [r for r in m.rows if r.kind != "count_cap"]
    free = master.solve(m)
    n, _, copies = master.decode(inst, m, free.x)
    assert len(copies) == 3 and all("DE" in c.support and len(c.support) == 3 for c in copies)


def test_a_contact_cap_binds():
    """The C6 path toy with V capped at one contact: {A,V} + {V,B} touches V twice, so the plan
    must hold V in one copy.  {A,V,B} + anything is out (the floor), and {A,V} + {B} leaves B at
    4 + 0 = 4 < 4.25 or V over: no plan remains."""
    inst = _c6_path_toy()
    capped = _toy({"AL": ["a"], "AR": ["b"], "AZ": [f"z{i}" for i in range(1, 6)]},
                  [("a", "z1"), ("z5", "b")] + [(f"z{i}", f"z{i + 1}") for i in range(1, 5)],
                  {"a": 4.0, "b": 4.0, **{f"z{i}": 1.0 for i in range(1, 6)}},
                  {"a": (0, 0), "b": (1, 0), **{f"z{i}": (i + 1, 0) for i in range(1, 6)}},
                  {"AZ": "free"}, k=2, delta=0.5, eta=0.1, contact_caps={"AZ": 1})
    assert master.plan(inst, "X")[0] is not None
    p, rep = master.plan(capped, "X")
    assert p is None and rep["status"] == "infeasible"
    assert math.isinf(_brute(capped))


# ------------------------------------------------------------------------------ decoding
def test_decoding_sums_shares_to_one_and_stops_on_a_real_deficit():
    inst = _star_border_toy()
    m = master.build(inst, "X")
    sol = master.solve(m)
    x = list(sol.x)
    s = frozenset(["AL", "AR", "AZ"])
    x[m.t_col["AZ", s]] += 5e-7                   # a solver residual, within FEAS_TOL
    n, t, copies = master.decode(inst, m, x)
    for v in ("AZ", "CA"):
        assert abs(math.fsum(c.share[v] for c in copies if v in c.share) - 1.0) <= 1e-12
    x[m.t_col["AZ", s]] += 1e-3                   # a deficit the solver did not leave
    try:
        master.decode(inst, m, x)
    except master.MasterError as e:
        assert "AZ" in str(e) and "not 1" in str(e)
    else:
        raise AssertionError("no MasterError")


def test_decoding_stops_when_the_residual_carries_a_copy_past_its_band():
    """Whole units of mass 10, 1 and 1, K = 3, so τ = 4.  At δ = 1.5 − 1.25e-6 the band's top is
    9.999995.  A t_{AL} = 1 − 5e-7 passes every row (mass 9.999995, cover short by 5e-7), but
    decoding holds AL whole at t = n = 1, mass 10: past the band by 1.25e-6 in τ units, more than
    FEAS_TOL.  The decoder must stop and name the band row."""
    inst = _toy({"AL": ["a"], "AR": ["b"], "AZ": ["c"]}, [], {"a": 10.0, "b": 1.0, "c": 1.0},
                {"a": (0, 0), "b": (1, 0), "c": (2, 0)}, k=3, delta=1.5)
    x = list(master.solve(master.build(inst, "X")).x)
    m = master.build(inst, "X", delta=1.5 - 1.25e-6)
    x[m.t_col["AL", frozenset(["AL"])]] -= 5e-7
    assert master.violations(m, x) == []
    try:
        master.decode(inst, m, x)
    except master.MasterError as e:
        assert "band_hi (AL)" in str(e), e
    else:
        raise AssertionError("no MasterError")


def _zero_share_toy(eta):
    """AL = {a} and AR = {b} (mass 4 each) both touch z0 (mass 0), the end of AZ's free path
    z0 … z5 (z1 … z5 of mass 1).  K = 2, so τ = 6.5, and δ = 5/13 makes the band [4, 9]."""
    zs = [f"z{i}" for i in range(6)]
    return _toy({"AL": ["a"], "AR": ["b"], "AZ": zs}, [("a", "z0"), ("b", "z0")] + list(zip(zs, zs[1:])),
                {"a": 4.0, "b": 4.0, "z0": 0.0, **{z: 1.0 for z in zs[1:]}},
                {"a": (0, 0), "b": (1, 0), **{z: (4, 0) for z in zs}}, {"AZ": "free"},
                k=2, delta=5.0 / 13.0, eta=eta)


def test_decoding_stops_on_a_member_at_share_zero():
    """The plan {AZ} (mass 5) + {AL, AR, AZ} with AZ's share 0 (mass 8) meets every row but the
    η rows: AZ's corridor floor in {AL, AR, AZ} is z0, of mass 0.  With the η rows vacuous, as an
    η below FEAS_TOL makes them, the decoder alone must refuse the copy whose footprint misses AZ
    (Claim 1)."""
    inst = _zero_share_toy(0.1)
    m = master.build(inst, "X")
    s1, s3 = frozenset(["AZ"]), frozenset(["AL", "AR", "AZ"])
    x = [0.0] * len(m.cost)
    x[m.n_col[s1]] = x[m.n_col[s3]] = 1.0
    x[m.t_col["AZ", s1]] = x[m.t_col["AL", s3]] = x[m.t_col["AR", s3]] = 1.0
    assert {k for k, _, _ in master.violations(m, x)} == {"eta"}
    m.rows = [r for r in m.rows if r.kind != "eta"]
    assert master.violations(m, x) == []
    try:
        master.decode(inst, m, x)
    except master.MasterError as e:
        assert "unit AZ share 0 in support AL+AR+AZ" in str(e), e
    else:
        raise AssertionError("no MasterError")


def test_an_incumbent_that_breaks_a_row_is_found():
    inst = _c6_path_toy()
    m = master.build(inst, "X")
    x = list(master.solve(m).x)
    assert master.violations(m, x) == []
    s = frozenset(["AL", "AZ"])
    x[m.t_col["AZ", s]] += 0.5
    kinds = {k for k, _, _ in master.violations(m, x)}
    assert {"cover", "band_hi"} <= kinds, kinds


# ------------------------------------------------------------------------------ smallest δ
def test_exact_and_bisection_smallest_delta_agree_on_clipped_toys():
    rng = random.Random(3)
    checked = 0
    for _ in range(25):
        inst = _random_toy(rng, modes=("whole", "clipped"))
        e = master.exact_delta(inst, "X")
        b = master.bisect_delta(inst, "X", tol=1e-4)
        assert e.scope == b.scope == master.SCOPE
        if e.status == "infeasible":
            assert b.status == "infeasible", b
            continue
        assert e.status == "exact" and b.status == "converged", (e, b)
        assert e.delta - master.FEAS_TOL <= b.delta <= e.delta + 1e-4, (e.delta, b.delta)
        assert b.lower is None or b.lower <= e.delta
        assert master.plan(inst, "X", delta=e.delta)[0] is not None
        if e.delta > 1e-3:
            assert master.plan(inst, "X", delta=e.delta - 1e-3)[0] is None
        checked += 1
    assert checked >= 10


def test_exact_and_bisection_agree_on_the_fixtures_51_scenario_clipped():
    raw = tomllib.load(open(ts.S51, "rb"))
    raw["channels"]["national"]["clipped"] = raw["channels"]["national"].pop("free")
    s = spec.parse(raw, ts.S51)
    fx = ts._fixture(tuple(s.fine_channels))
    if fx is None:
        return
    inst = spec.build(s, fx.extract, ts._reference(), fx.graph)
    for c in ("WIFI", "national"):
        fam = supports.family(inst, c)
        e = master.exact_delta(inst, c, fam)
        b = master.bisect_delta(inst, c, fam, tol=1e-3)
        assert e.status == "exact" and b.status == "converged", (c, e, b)
        assert e.delta - master.FEAS_TOL <= b.delta <= e.delta + 1e-3, (c, e.delta, b.delta)
        assert b.lower <= e.delta
        p, rep = master.plan(inst, c, delta=e.delta, fam=fam)
        _check_plan(inst, p)
        print(f"      smallest δ, fixture 51 clipped, {c}: exact {e.delta:.6f}, "
              f"bisection ({b.lower:.6f}, {b.delta:.6f}] in {len(b.steps)} steps")


def _eta_toy(eta):
    """One clipped unit of three unit-mass ZIPs on a path, K = 3, so τ = 1."""
    return _toy({"AL": ["a", "b", "c"]}, [("a", "b"), ("b", "c")], {"a": 1.0, "b": 1.0, "c": 1.0},
                {"a": (0, 0), "b": (1, 0), "c": (2, 0)}, {"AL": "clipped"}, k=3, delta=1.0, eta=eta)


def test_exact_bisection_and_plan_agree_at_the_eta_boundary():
    """Three copies of {AL} need η ≤ 1/3.  At η = 1/3 + 1e-8 the η row misses by 3e-8, inside
    HiGHS's tolerance, so without the explicit ⌊1/η⌋ cap the master would plan three copies that
    the exact δ-MILP excludes.  With it, all three paths say infeasible; at η = 1/3 exactly, all
    three say feasible, each copy holding a third."""
    inst = _eta_toy(1.0 / 3.0 + 1e-8)
    assert list(master._k_range(inst, inst.channels["X"], "AL")) == [1, 2]
    assert master.exact_delta(inst, "X").status == "infeasible"
    assert master.bisect_delta(inst, "X").status == "infeasible"
    p, rep = master.plan(inst, "X", delta=1.0)
    assert p is None and rep["status"] == "infeasible", rep
    inst = _eta_toy(1.0 / 3.0)
    e, b = master.exact_delta(inst, "X"), master.bisect_delta(inst, "X")
    assert e.status == "exact" and b.status == "converged", (e, b)
    assert e.delta - master.FEAS_TOL <= b.delta <= e.delta + master.DELTA_TOL, (e.delta, b.delta)
    p, _ = master.plan(inst, "X", delta=1.0)
    assert [c.share for c in p.copies] == [{"AL": 1.0 / 3.0}] * 3


def test_an_eta_below_eta_min_is_refused():
    """At η = 1e-8 the η rows sit below FEAS_TOL, and the master once planned the zero-share copy
    of `test_decoding_stops_on_a_member_at_share_zero` as optimal.  Every path now refuses such an
    η and names the channel; η = ETA_MIN itself is accepted."""
    for call in (lambda: master.build(_zero_share_toy(1e-8), "X"),
                 lambda: master.plan(_zero_share_toy(1e-8), "X"),
                 lambda: master.bisect_delta(_zero_share_toy(1e-8), "X"),
                 lambda: master.exact_delta(_eta_toy(1e-8), "X")):
        try:
            call()
        except master.MasterError as e:
            assert "channel X" in str(e) and "eta = 1e-08" in str(e), e
        else:
            raise AssertionError("no MasterError")
    assert math.isclose(master.ETA_MIN, 100 * master.FEAS_TOL)
    master.build(_zero_share_toy(master.ETA_MIN), "X")
    assert master.exact_delta(_eta_toy(master.ETA_MIN), "X").status == "exact"


def test_exact_delta_refuses_free_units():
    inst = _c6_path_toy()
    try:
        master.exact_delta(inst, "X")
    except master.MasterError as e:
        assert "bisection" in str(e)
    else:
        raise AssertionError("no MasterError")
    d = master.smallest_delta(inst, "X")
    assert d.method == "bisection" and d.status == "converged"


def test_a_step_that_times_out_without_an_incumbent_is_unknown():
    inst = _star_border_toy()
    verdict, rep = master.step(inst, "X", 0.3, time_limit=0.0)
    assert verdict == "unknown" and rep["status"] == "time limit" and rep["objective"] is None
    d = master.bisect_delta(inst, "X", time_limit=0.0)
    assert d.status == "unknown" and d.delta is None and d.lower is None
    assert [v for _, v, _ in d.steps] == ["unknown"]
    e = master.exact_delta(_random_toy(random.Random(1), modes=("whole",)), "X", time_limit=0.0)
    assert e.status == "unknown" and e.delta is None


def test_an_unknown_step_mid_search_keeps_the_bracket():
    """A step with no verdict stops the bisection: the bracket so far stands, and nothing below
    the unknown δ is called infeasible (C4)."""
    inst = _star_border_toy()
    exact = master.bisect_delta(inst, "X", tol=1e-4)
    real = master.step

    def flaky(inst_, channel, delta, *a, **k):
        if 0 < delta < exact.delta:
            return "unknown", {"status": "time limit", "objective": None}
        return real(inst_, channel, delta, *a, **k)

    master.step = flaky
    try:
        d = master.bisect_delta(inst, "X", tol=1e-4)
    finally:
        master.step = real
    assert d.status == "unknown"
    assert d.steps[-1][1] == "unknown"
    assert d.lower is not None and d.delta is not None and d.lower < d.delta
    assert all(v != "infeasible" for x, v, _ in d.steps if 0 < x < exact.delta)


def test_an_infeasible_channel_is_infeasible_at_every_delta():
    """Three districts on one free unit of two ZIPs break the count cap at any δ."""
    inst = _toy({"AL": ["a", "b"]}, [("a", "b")], {"a": 1.0, "b": 1.0}, {"a": (0, 0), "b": (1, 0)},
                {"AL": "free"}, k=3, eta=0.05)
    d = master.bisect_delta(inst, "X")
    assert d.status == "infeasible" and d.delta is None
    assert [v for _, v, _ in d.steps] == ["infeasible", "infeasible"]


# ------------------------------------------------------------------------------ the report
def test_the_solver_report_earns_the_exact_tier_in_the_audit():
    inst = _star_border_toy()
    plans, reports = master.plan_all(inst)
    rep = reports["X"]
    assert rep["mip_rel_gap"] == 0 and rep["gap"] == 0 and rep["status"] == "optimal"
    run = audit.Run(cells=[], channels={"X": audit.Channel(2)}, solver=reports)
    solver, tier = audit.check_solver(run)
    assert solver.status == "listed" and tier.status == "pass" and tier.items == ["X: exact"]
    none = master.plan(inst, "X", time_limit=0.0)[1]
    assert audit.tier(none) == "none"


def test_write_report_records_the_smallest_delta_as_a_property_of_the_master():
    inst = _c6_path_toy()
    _, reports = master.plan_all(inst)
    deltas = {"X": master.smallest_delta(inst, "X", tol=1e-3)}
    with tempfile.TemporaryDirectory() as tmp:
        path = master.write_report(os.path.join(tmp, "solver.json"), reports, deltas)
        with open(path, encoding="utf-8") as fh:
            out = json.load(fh)
    x = out["X"]
    assert x["solver"]["status"] == "optimal"
    sd = x["smallest_delta"]
    assert sd["method"] == "bisection" and sd["status"] == "converged"
    assert sd["scope"] == master.SCOPE and "C4" in sd["scope"]
    assert sd["steps"] and all(s["verdict"] in ("feasible", "infeasible") for s in sd["steps"])
