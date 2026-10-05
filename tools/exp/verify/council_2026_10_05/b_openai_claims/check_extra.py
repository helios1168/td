"""The extra question (owner decision 1: a split is polygon ownership) and pass-2 C1.

(a) Is the master's s* (η > 0, μ = 0) a lower bound on the ownership split count of every M1 map
    (every ZIP owned, each district connected on the ZIP graph, drawn mass in band)? Here every
    unit is free and the family is every connected unit set, so modes and family match and η is
    the only difference between M1 and 𝒳_c(δ).
(b) Is the master's δ* a lower bound on the best drawn balance of M1 maps?

Three masters are compared, each by exhaustive plan enumeration with a δ-minimising share LP:
  std   MODEL §3 with η (t ≥ η n);
  zero  η only on positive-share copies: n_S = p + q, η p ≤ t ≤ p, Σ_S q_{v,S} ≤ #zero-mass ZIPs
        of v (a zero-share copy owns at least one zero-mass ZIP of v), contact cap ⌊1/η⌋ + that;
  eta0  η = 0 (a relaxation; Claim 1's decoding is lost, the bound is what is tested).
M1 drawings are classed by their smallest positive-or-zero footprint share: 'eta' (all ≥ η, i.e.
𝒳_c), 'zero' (some share exactly 0, the rest ≥ η) and 'tiny' (some share in (0, η)).
"""
import itertools
import math
import random
import sys

from common import fmt, report
from model import Inst, connected, solve, INF

ok_all = True


def chk(tag, ok, detail=""):
    global ok_all
    ok_all &= report(tag, ok, detail)


def names(I, d):
    return [[I.Z[i] for i in I.members(b)] for b in d]


def min_delta_zero(I, nv, zq):
    """δ-minimising share LP for the 'zero' variant with q fixed: zq[(v, s)] zero-share copies."""
    col, cost, lb, ub = {}, [], [], []
    for s, k in nv.items():
        for v in I.F[s]:
            col[(v, s)] = len(cost)
            q = zq.get((v, s), 0)
            cost.append(0.0)
            if I.modes[v] == "whole" or (I.modes[v] == "clipped" and len(I.F[s]) > 1):
                lb.append(float(k))
                ub.append(float(k))
            else:
                lb.append(I.eta * (k - q))
                ub.append(float(k - q))
    col["d"] = len(cost)
    cost.append(1.0)
    lb.append(0.0)
    ub.append(INF)
    rows = []
    for v in I.units:
        rows.append(({j: 1 for key, j in col.items() if key != "d" and key[0] == v}, 1, 1))
    for s, k in nv.items():
        mass = {col[(v, s)]: I.M[v] for v in I.F[s]}
        rows.append(({**mass, col["d"]: I.tau * k}, I.tau * k, INF))
        rows.append(({**mass, col["d"]: -I.tau * k}, -INF, I.tau * k))
        for v, c in I.corr[s].items():
            if c == INF:
                return None
            rows.append(({col[(v, s)]: I.M[v]}, c * k, INF))
    if any(lb[i] > ub[i] + 1e-12 for i in range(len(lb))):
        return None
    st, val, _ = solve(len(cost), cost, lb, ub, rows, [False] * len(cost))
    return val if st == "optimal" else None


def plan_profile(I, variant):
    """[(splits, min δ)] over every feasible plan of the variant master (any δ)."""
    out = []
    if variant == "std":
        for nv in I.nvectors():
            d = I.share_lp(nv, minimize_delta=True)
            if d is not None:
                out.append((I.nsplits(nv), d, nv))
    elif variant == "eta0":
        for nv in I.nvectors(eta=0.0):
            d = I.share_lp(nv, minimize_delta=True, eta=0.0)
            if d is not None:
                out.append((I.nsplits(nv), d, nv))
    else:  # zero: enumerate n with the widened contact cap, then the zero-share counts q
        J = I.variant()
        J.cap = lambda v, eta=None, zero_contact=False, _I=I: _I.cap(v, zero_contact=True)
        zeros = {v: sum(1 for i in I.Zv[v] if I.m[i] == 0) for v in I.units}
        for nv in J.nvectors():
            slots = [(v, s) for s in nv for v in I.F[s] if zeros[v] and I.modes[v] == "free"]
            best = None
            for qs in itertools.product(*[range(nv[s] + 1) for (v, s) in slots]):
                zq = dict(zip(slots, qs))
                if any(sum(q for (u, s), q in zq.items() if u == v) > zeros[v] for v in I.units):
                    continue
                d = min_delta_zero(I, nv, zq)
                if d is not None and (best is None or d < best):
                    best = d
            if best is not None:
                out.append((I.nsplits(nv), best, nv))
    return out


def draw_profile(I):
    """[(ownership splits, dev, class, drawing)] over every connected K-partition (no band)."""
    out = []
    for d in I.drawings(band=False):
        shares = [I.share(b, v) for b in d for v in I.footprint(b)]
        if all(x >= I.eta - 1e-12 for x in shares):
            cls = "eta"
        elif all(x == 0 or x >= I.eta - 1e-12 for x in shares):
            cls = "zero"
        else:
            cls = "tiny"
        out.append((I.own_splits(d), I.ddev(d), cls, d))
    return out


def gaps(I, plans, draws, classes):
    """Counterexamples: (a) a drawing with fewer ownership splits than every plan at its δ;
    (b) a drawing more balanced than δ*."""
    ca, cb = [], []
    dstar = min((p[1] for p in plans), default=INF)
    for sp, dev, cls, d in draws:
        if cls not in classes:
            continue
        best = min((p[0] for p in plans if p[1] <= dev + 1e-9), default=INF)
        if sp < best:
            ca.append((sp, best, dev, cls, d))
        if dev < dstar - 1e-9:
            cb.append((dev, dstar, cls, d))
    return ca, cb


ALLOWED = {"std": ("eta",), "zero": ("eta", "zero"), "eta0": ("eta", "zero", "tiny")}

# --- pass-2 C1 instances, both split keys ----------------------------------------------------
c1 = {
    "sol-C1": Inst([("A", "A", 5), ("z0", "v", 0), ("z10", "v", 10), ("B", "B", 5)],
                   [("A", "z0"), ("B", "z0"), ("z0", "z10")], K=2, delta=0.15, eta=0.05,
                   modes={"A": "whole", "B": "whole"}),
    "astra-C1": Inst([("a", "A", .5), ("b0", "B", 0), ("b1", "B", 1), ("c", "C", .5)],
                     [("a", "b0"), ("b0", "c"), ("b0", "b1")], K=2, delta=0.15, eta=0.1,
                     modes={"A": "whole", "C": "whole"}),
    "opus-C1": Inst([("a", "a", .5), ("z0", "v", 0), ("z1", "v", 1), ("b", "b", .5)],
                    [("a", "z0"), ("b", "z0"), ("z0", "z1")], K=2, delta=0.1, eta=0.05,
                    modes={"a": "whole", "b": "whole"}),
}
for name, I in c1.items():
    ds = I.drawings()
    st, s_star, nsol = I.milp(objective="splits")
    rows = [(names(I, d), I.pos_splits(d), I.own_splits(d), I.in_X(d)) for d in ds]
    pos_min = min(r[1] for r in rows)
    own_min = min(r[2] for r in rows)
    chk(f"C1 {name}: an M1 map has 0 positive-opportunity splits < s* = 1 (old key breaks the "
        "bound); its ownership count is 1 ≥ s* (decision 1 restores this instance)",
        pos_min == 0 and s_star == 1 and own_min >= s_star,
        f"M1 maps (map, pos splits, own splits, in 𝒳_c): {rows}; master {fmt(I, nsol)}")
I = c1["opus-C1"]
z = I.milp(objective="splits", delta=0.0)
zh = I.milp(objective="splits", delta=0.0, hall=True)
d0 = [names(I, d) for d in I.drawings(delta=0.0)]
chk("C1 opus δ = 0: the MODEL §3 master is FEASIBLE ({a,v}+{v,b}, t = .5, masses 1/1), so the "
    "claimed infeasibility is false as stated; it holds once the C2 Hall rows are added",
    z[0] == "optimal" and zh[0] == "infeasible" and d0,
    f"plain {z[0]} {fmt(I, z[2])}; with Hall {zh[0]}; exact M1 maps {d0}")

# --- hand counterexamples under the ownership key ---------------------------------------------
# CE1 (zero share): a .9 – z0 0 – b .1 with z0 – z1 1; a, b whole, v = {z0, z1} free; K = 2, η = .15.
ce1 = Inst([("a", "a", .9), ("z0", "v", 0), ("z1", "v", 1), ("b", "b", .1)],
           [("a", "z0"), ("b", "z0"), ("z0", "z1")], K=2, delta=0.0, eta=0.15,
           modes={"a": "whole", "b": "whole"}, name="CE1")
# CE2 (tiny positive share): a .9 whole, v = {z0 .1, z1 1.0} free; a – z0 – z1; K = 2, η = .15.
ce2 = Inst([("a", "a", .9), ("z0", "v", .1), ("z1", "v", 1.0)], [("a", "z0"), ("z0", "z1")],
           K=2, delta=0.0, eta=0.15, modes={"a": "whole"}, name="CE2")
for I, cls in ((ce1, "zero"), (ce2, "tiny")):
    draws = draw_profile(I)
    best = min((x for x in draws if x[2] == cls), key=lambda x: x[1])
    res = {}
    for var in ("std", "zero", "eta0"):
        pl = plan_profile(I, var)
        dstar = min(p[1] for p in pl)
        at = min((p[0] for p in pl if p[1] <= best[1] + 1e-9), default=INF)
        res[var] = (round(dstar, 6), at)
    # MILP cross-checks: δ* by bisection (std master); the three masters at the map's δ
    bis = I.bisect_delta(objective="splits")
    expect = {"zero": {"std": False, "zero": True, "eta0": True},
              "tiny": {"std": False, "zero": False, "eta0": True}}[cls]
    good = all((res[v][0] <= best[1] + 1e-9) == expect[v] and (res[v][1] <= best[0]) == expect[v]
               for v in res)
    milps = {"std": I.milp(objective="splits", delta=best[1])[:2],
             "zero": I.milp(objective="splits", delta=best[1], zero_contact=True)[:2],
             "eta0": I.milp(objective="splits", delta=best[1], eta=0.0)[:2]}
    good &= all((m[0] == "optimal" and m[1] <= best[0]) == expect[v] for v, m in milps.items())
    chk(f"{I.name} ({cls} share): M1 map {names(I, best[3])} has dev {best[1]:.3f} and "
        f"{best[0]} ownership split; per master (δ*, s* at that δ): {res}", good and abs(bis - res['std'][0]) < 1e-5,
        f"std δ* by MILP bisection {bis:.6f}; MILPs at the map's δ {milps}; bound holds for "
        f"{[v for v in expect if expect[v]]}")

# CE3 (zero share, finite gap): a = {a0 .85, a1 .05} free, v = {z0 0, z1 1} free, b .1 whole;
# a0–a1, a0–z0, a1–z1, z0–b, z0–z1; K = 2, η = .15, δ = 0. The M1 map {a0,a1,z0,b} | {z1} is exact
# with one ownership split (v); the std master needs two splits ({a,v} + {a,v,b}).
ce3 = Inst([("a0", "a", .85), ("a1", "a", .05), ("z0", "v", 0), ("z1", "v", 1), ("b", "b", .1)],
           [("a0", "a1"), ("a0", "z0"), ("a1", "z1"), ("z0", "b"), ("z0", "z1")],
           K=2, delta=0.0, eta=0.15, modes={"b": "whole"}, name="CE3")
ds = ce3.drawings()
m3 = {"std": ce3.milp(objective="splits"), "zero": ce3.milp(objective="splits", zero_contact=True),
      "eta0": ce3.milp(objective="splits", eta=0.0)}
chk("CE3 (zero share, finite gap): exact M1 map with 1 ownership split; std s* = 2 at δ = 0; "
    "zero-contact and η = 0 masters give 1",
    [ce3.own_splits(d) for d in ds] == [1] and m3["std"][1] == 2 and m3["zero"][1] == 1 and m3["eta0"][1] == 1,
    f"maps {[names(ce3, d) for d in ds]}; masters "
    f"{ {k: (v[1], fmt(ce3, v[2])) for k, v in m3.items()} }")

# --- exhaustive search on ≤ 3 ZIPs: smallest counterexamples -----------------------------------
GRID = (0.0, 0.1, 0.5, 0.9, 1.0)
found = {"std": {}, "zero": {}, "eta0": {}}
n_inst = 0
for nZ in (2, 3):
    zn = [f"z{i}" for i in range(nZ)]
    all_edges = list(itertools.combinations(range(nZ), 2))
    for k in range(nZ - 1, len(all_edges) + 1):
        for E in itertools.combinations(all_edges, k):
            adj = {i: set() for i in range(nZ)}
            for a, b in E:
                adj[a].add(b)
                adj[b].add(a)
            if not connected(range(nZ), adj):
                continue
            # unit labels: restricted growth strings, every unit connected
            for lab in itertools.product(range(nZ), repeat=nZ):
                if lab[0] != 0 or any(lab[i] > max(lab[:i]) + 1 for i in range(1, nZ)):
                    continue
                groups = {}
                for i, u in enumerate(lab):
                    groups.setdefault(u, []).append(i)
                if not all(connected(g, adj) for g in groups.values()):
                    continue
                for ms in itertools.product(GRID, repeat=nZ):
                    if any(sum(ms[i] for i in g) == 0 for g in groups.values()):
                        continue
                    for K in (2, 3):
                        if K > nZ:
                            continue
                        I = Inst([(zn[i], f"u{lab[i]}", ms[i]) for i in range(nZ)],
                                 [(zn[a], zn[b]) for a, b in E], K=K, delta=0.0, eta=0.15,
                                 rows=("count", "border", "corridor"))
                        n_inst += 1
                        draws = draw_profile(I)
                        for var in ("std", "eta0"):
                            pl = plan_profile(I, var)
                            for cls in ("eta", "zero", "tiny"):
                                ca, cb = gaps(I, pl, draws, (cls,))
                                for tag, lst in (("a", ca), ("b", cb)):
                                    if lst:
                                        found[var].setdefault((tag, cls), []).append(
                                            (I, lst[0]))
summary = {var: {k: len(v) for k, v in d.items()} for var, d in found.items()}
std = found["std"]
first = {}
for key in (("a", "tiny"), ("b", "tiny")):
    if std.get(key):
        I, x = min(std[key], key=lambda p: (len(p[0].Z), len(p[0].units)))
        first[key] = (len(I.Z), len(I.units), [(z, I.uof[i], I.m[i]) for i, z in enumerate(I.Z)],
                      sorted((I.Z[a], I.Z[b]) for a in I.zadj for b in I.zadj[a] if a < b), I.K,
                      names(I, x[-1]))
chk("Search ≤ 3 ZIPs (all units free, all connected supports, η = .15, masses in {0,.1,.5,.9,1}, "
    "K ∈ {2,3}): std master has (a) and (b) counterexamples only from 'tiny' shares, none from "
    "𝒳_c or 'zero'; the η = 0 master has none",
    not std.get(("a", "eta")) and not std.get(("b", "eta")) and not std.get(("a", "zero"))
    and not std.get(("b", "zero")) and std.get(("a", "tiny")) and std.get(("b", "tiny"))
    and not found["eta0"],
    f"{n_inst} instances; counterexample counts {summary}; smallest (ZIPs, units, zips, edges, K, "
    f"map): {first}")

# --- random search 4-6 ZIPs: zero-share counterexamples exist; the 'zero' master closes them ---
rng = random.Random(91)
counts = {var: {} for var in ALLOWED}
n_inst = 0
small_zero = None
finite = []
milp_bad = []
for trial in range(700):
    nu = rng.randint(2, 4)
    zs, ed = [], []
    for k in range(nu):
        nz = rng.randint(1, 2)
        for i in range(nz):
            zs.append((f"u{k}z{i}", f"u{k}", rng.choice((0.0, 0.0, 0.1, 0.5, 0.9, 1.0))))
        if nz == 2:
            ed.append((f"u{k}z0", f"u{k}z1"))
        if sum(m for _, u, m in zs if u == f"u{k}") == 0:
            zs[-1] = (zs[-1][0], f"u{k}", 1.0)
    for k in range(1, nu):
        ed.append((rng.choice([z for z, u, _ in zs if u == f"u{k}"]),
                   rng.choice([z for z, u, _ in zs if int(u[1:]) < k])))
    if rng.random() < 0.5:
        a, b = rng.sample([z for z, _, _ in zs], 2)
        if (a, b) not in ed and (b, a) not in ed:
            ed.append((a, b))
    if len(zs) < 4:
        continue
    I = Inst(zs, ed, K=rng.choice((2, 3)), delta=0.0, eta=0.15)
    n_inst += 1
    draws = draw_profile(I)
    for var in ALLOWED:
        pl = plan_profile(I, var)
        # the MILP form of each master agrees with its enumeration at δ = .15
        kw = {"std": {}, "zero": {"zero_contact": True}, "eta0": {"eta": 0.0}}[var]
        st, val, _ = I.milp(objective="splits", delta=0.15, **kw)
        en = min((p[0] for p in pl if p[1] <= 0.15 + 1e-9), default=None)
        if (st == "optimal") != (en is not None) or (en is not None and round(val) != en):
            milp_bad.append((var, I.K, zs, ed, st, val, en))
        for cls in ("eta", "zero", "tiny"):
            ca, cb = gaps(I, pl, draws, (cls,))
            for tag, lst in (("a", ca), ("b", cb)):
                if lst:
                    counts[var][(tag, cls)] = counts[var].get((tag, cls), 0) + 1
                    if var == "std" and tag == "a" and any(x[1] < INF for x in lst):
                        finite.append((I.K, [(z, I.uof[i], I.m[i]) for i, z in enumerate(I.Z)], ed,
                                       [(x[0], x[1], round(x[2], 4), names(I, x[-1])) for x in lst if x[1] < INF][:1]))
                    if var == "std" and cls == "zero" and (small_zero is None or len(I.Z) < small_zero[0]):
                        small_zero = (len(I.Z), [(z, I.uof[i], I.m[i]) for i, z in enumerate(I.Z)],
                                      ed, I.K, tag, names(I, lst[0][-1]))
viol = [(var, k) for var in ALLOWED for k in counts[var] if k[1] in ALLOWED[var]]
chk("MILP forms of std / zero / eta0 masters = their plan enumerations at δ = .15", not milp_bad,
    f"{n_inst} instances × 3 masters; mismatches {milp_bad[:2]}")
chk("Random 4-6 ZIPs (700 seeded draws, all free): std breaks on 'zero' and 'tiny' maps only; the "
    "'zero' master (η on positive contact, zero-share copies on zero-mass ZIPs) breaks on 'tiny' "
    "only; η = 0 never", not viol and counts["std"].get(("a", "zero")) and counts["zero"].get(("a", "tiny")),
    f"{n_inst} instances; counts {counts}; smallest std 'zero' counterexample {small_zero}; "
    f"(a) cases where the std master is feasible at the map's δ but needs more splits: {len(finite)} {finite[:1]}")

print("ALL OK" if ok_all else "SOME MISMATCH")
sys.exit(0 if ok_all else 1)
