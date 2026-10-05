"""p1-sol T4, p1-astra T4 (F6 split-set search exact under μ = 0; F7 fixed regions exact only for
region-confined plans; the F7 counterexamples) and p1-sol T5 / p1-astra T4 part 3 (the F4 piece
floor keeps Claim 1 and Proposition D only for floor-obeying plans and drawings). Also the
up-closure and top-layer arguments of pass-2 C4 and C6."""
import itertools
import math
import sys

from common import fmt, report, suites
from model import Inst

ok_all = True


def chk(tag, ok, detail=""):
    global ok_all
    ok_all &= report(tag, ok, detail)


inst = suites()

# --- F6: min |F| over allowed split sets = s*; feasible sets form an up-set -------------------
bad, n_sets, n_inst, top_checks, c4_hits = [], 0, 0, 0, []
for I, ps in inst:
    P = [v for v in I.units if I.splittable(v)]
    s_star = round(I.milp(objective="splits")[1])
    feas = {}
    for k in range(len(P) + 1):
        for Fset in itertools.combinations(P, k):
            J = I.variant(modes={**I.modes, **{v: "whole" for v in P if v not in Fset}})
            feas[frozenset(Fset)] = J.milp(objective="diam")[0] == "optimal"
            n_sets += 1
    n_inst += 1
    fmin = min(len(F) for F, ok in feas.items() if ok)
    if fmin != s_star:
        bad.append((I.name, "min|F|", fmin, s_star))
    for F, ok in feas.items():
        if ok:
            for G in feas:
                if G >= F and not feas[G]:
                    bad.append((I.name, "up-closure", sorted(F), sorted(G)))
    # forced set Φ(δ): splittable units heavier than U_c; every feasible F contains it (C4, C6)
    L, U = I.band()
    phi = frozenset(v for v in P if I.M[v] > U + 1e-9)
    if any(ok and not phi <= F for F, ok in feas.items()):
        bad.append((I.name, "forced not contained"))
    if s_star > len(phi):
        top = [F for F in feas if phi <= F and len(F) == s_star - 1]
        top_checks += len(top)
        if len(top) != math.comb(len(P) - len(phi), s_star - 1 - len(phi)) or any(feas[F] for F in top):
            bad.append((I.name, "top layer"))
    # C4 caveat: a forced set taken at a tighter band (1.10τ) can be larger than Φ(δ); its
    # infeasibility then does not give s* ≥ |Φ(1.10)| + 1
    phi10 = frozenset(v for v in P if I.M[v] > I.tau * 1.10 + 1e-9)
    if phi < phi10 and not feas[phi10] and s_star <= len(phi10):
        c4_hits.append((I.name, sorted(phi), sorted(phi10), s_star))
chk("T4 F6: min |F| over feasible allowed-split sets = s* (MILP = enumeration); feasible sets are "
    "an up-set; every feasible F ⊇ Φ(δ); top layer {F ⊇ Φ, |F| = s*−1} has C(|P|−|Φ|, s*−1−|Φ|) "
    "sets, all infeasible", not bad,
    f"{n_inst} instances, {n_sets} allowed sets solved, {top_checks} top-layer sets; mismatches {bad[:3]}")
chk("C4 caveat search: forced set at 1.10τ ⊋ Φ(δ), infeasible as the only allowed set, yet "
    "s* ≤ |Φ(1.10τ)| (so '|Φ_1.10|+1' would be a false bound)", True,
    f"{len(c4_hits)} random instances show it: {c4_hits[:3]}")

# hand instance for the C4 caveat: v1 (1.12τ) is forced at 1.10τ but not at 1.15τ. Path x–w–v1,
# x whole .83 (borders w0 only), w free (w0 .17, w1 .88), v1 free (.56, .56); K = 3, τ = 1, δ = .15.
# With w whole, x has no in-band district, so allowing only Φ(1.10τ) = {v1} is infeasible; but
# splitting w alone works ({x,w0} 1.0 | {w1} .88 | {v1} 1.12), so s* = 1 = |Φ(1.10τ)|.
c4 = Inst([("x", "x", .83), ("w0", "w", .17), ("w1", "w", .88), ("v1a", "v1", .56), ("v1b", "v1", .56)],
          [("x", "w0"), ("w0", "w1"), ("w1", "v1a"), ("v1a", "v1b")],
          K=3, delta=0.15, eta=0.1, modes={"x": "whole"}, name="C4-caveat")
s_c4 = c4.milp(objective="splits")
phi15 = [v for v in c4.units if c4.splittable(v) and c4.M[v] > c4.tau * 1.15 + 1e-9]
phi10 = [v for v in c4.units if c4.splittable(v) and c4.M[v] > c4.tau * 1.10 + 1e-9]
only10 = c4.variant(modes={**c4.modes, **{v: "whole" for v in c4.units
                                           if c4.splittable(v) and v not in phi10}}).milp()[0]
chk("C4 caveat (hand): Φ(1.15τ) = ∅ ⊊ Φ(1.10τ) = {v1}; allowing only {v1} is infeasible, yet "
    "s* = 1 = |Φ(1.10τ)| via split set {w}",
    phi15 == [] and phi10 == ["v1"] and only10 == "infeasible" and s_c4[1] == 1,
    f"τ = {c4.tau:.3f}, M = {c4.M}, plan {fmt(c4, s_c4[2])}")


# --- F7 counterexamples: six-unit paths, whole units, K = 3, ±15% ----------------------------
def path6(masses, size_cap, name):
    zs = [(f"z{k}", f"u{k}", m) for k, m in enumerate(masses, 1)]
    ed = [(f"z{k}", f"z{k + 1}") for k in range(1, 6)]
    return Inst(zs, ed, K=3, delta=0.15, eta=0.1, modes={f"u{k}": "whole" for k in range(1, 7)},
                size_cap=size_cap, name=name)


R1, R2 = {"u1", "u2", "u3"}, {"u4", "u5", "u6"}
for I, cap in ((path6([1] * 6, 2, "sol-F7"), 2), (path6([.6, .4, .6, .4, .6, .4], None, "astra-F7"), None)):
    st, val, nsol = I.milp(objective="splits")
    cross = [s for s, S in enumerate(I.F) if S & R1 and S & R2]
    allocs = {}
    for k1 in range(0, I.K + 1):
        rows = [({s: 1 for s, S in enumerate(I.F) if S <= R1}, k1, k1)]
        allocs[(k1, I.K - k1)] = I.milp(objective="splits", forbid=cross, extra_rows=rows)[0]
    chk(f"T4 F7 counterexample {I.name}: parent master feasible with s* = 0, regions "
        "{u1,u2,u3}/{u4,u5,u6} infeasible for every K allocation at parent τ",
        st == "optimal" and val == 0 and all(a == "infeasible" for a in allocs.values()),
        f"size cap {cap}, parent plan {fmt(I, nsol)}, allocations {allocs}")

# --- F7 positive side: exact when no support crosses; a restriction otherwise ------------------
bad, n_eq, n_lt, n_inf, n_inst = [], 0, 0, 0, 0
for I, ps in inst:
    half = set(I.units[: len(I.units) // 2])
    cross = [s for s, S in enumerate(I.F) if S & half and S - half]
    s_star = round(I.milp(objective="splits")[1])
    best = None
    for k1 in range(I.K + 1):
        rows = [({s: 1 for s, S in enumerate(I.F) if S <= half}, k1, k1)]
        st, val, _ = I.milp(objective="splits", forbid=cross, extra_rows=rows)
        if st == "optimal":
            best = val if best is None else min(best, val)
    # noncrossing family: F7 with every allocation = the master on that family
    fam = [S for S in I.F if not (S & half and S - half)]
    J = I.variant(family=fam)
    st, jval, _ = J.milp(objective="splits")
    vals = []
    for k1 in range(J.K + 1):
        rows = [({s: 1 for s, S in enumerate(J.F) if S <= half}, k1, k1)]
        st2, v2, _ = J.milp(objective="splits", extra_rows=rows)
        if st2 == "optimal":
            vals.append(v2)
    if (st == "optimal") != bool(vals) or (vals and abs(min(vals) - jval) > 1e-9):
        bad.append((J.name, "noncrossing F7 ≠ master"))
    n_inst += 1
    region_opt = [p for p in ps if I.nsplits(p) == s_star and not any(s in cross for s in p)]
    if best is None:
        n_inf += 1
        if region_opt:
            bad.append((I.name, "F7 infeasible but a confined optimum exists"))
        continue
    if best < s_star:
        bad.append((I.name, "F7 below s*", best, s_star))
    if (round(best) == s_star) != bool(region_opt):
        bad.append((I.name, "exact iff confined optimum", best, s_star, len(region_opt)))
    n_eq += round(best) == s_star
    n_lt += round(best) > s_star
chk("T4 F7: region solve (parent τ, all K allocations) ≥ s*; equal iff some optimal plan uses no "
    "crossing support; on a noncrossing family it equals the master", not bad,
    f"{n_inst} instances (regions = first half / second half of units); F7 exact on {n_eq}, "
    f"strictly worse on {n_lt}, infeasible on {n_inf} (parent feasible); mismatches {bad[:3]}")

# --- F4 piece floor ρτ: aggregate ⇔ explicit per-copy; MILP = enumeration; Prop D for floor-obeying
rho = 0.3
bad, n_vec, n_draw, n_inst = [], 0, 0, 0
for I, ps in inst:
    n_inst += 1
    feas = []
    for nv in I.nvectors():
        a = I.share_lp(nv, rho=rho)
        b = I.share_lp(nv, rho=rho, per_copy=True)
        n_vec += 1
        if a != b:
            bad.append((I.name, "aggregate vs per-copy", fmt(I, nv), a, b))
        if a:
            feas.append(nv)
    st, val, _ = I.milp(objective="splits", rho=rho)
    if (st == "optimal") != bool(feas) or (feas and round(val) != min(I.nsplits(p) for p in feas)):
        bad.append((I.name, "F4 MILP vs enumeration", st, val))
    for d in I.drawings():
        if not I.in_X(d):
            continue
        floor_ok = all(I.share(b, v) * I.M[v] >= rho * I.tau - 1e-9
                       for b in d for v in I.footprint(b) if I.modes[v] == "free")
        if floor_ok:
            n_draw += 1
            nv, _ = I.readback(d)
            if I.milp(objective="splits", rho=rho, fix_n=nv)[0] != "optimal":
                bad.append((I.name, "floor-obeying drawing rejected", fmt(I, nv)))
chk(f"T5 F4 (ρ = {rho}): aggregate row ⇔ explicit per-copy floor for every n; F4 MILP = "
    "enumeration; every floor-obeying 𝒳_c drawing's read-back is F4-feasible", not bad,
    f"{n_inst} instances, {n_vec} n vectors, {n_draw} floor-obeying drawings; mismatches {bad[:3]}")

# hand: a drawing in 𝒳_c that breaks the floor, while the F4 master is infeasible
f4 = Inst([("a", "a", .8), ("z0", "v", .2), ("z1", "v", 1.0)], [("a", "z0"), ("z0", "z1")],
          K=2, delta=0.05, eta=0.1, modes={"a": "whole"}, name="F4-hand")
ds = [d for d in f4.drawings() if f4.in_X(d)]
chk("T5 F4 scope: 𝒳_c(0.05) holds {a,z0} | {z1} (masses 1.0/1.0, v-piece 0.2 < ρτ = 0.3); the "
    "master without F4 is feasible (s* = 1), with F4 infeasible",
    len(ds) == 1 and f4.milp(objective="splits")[1] == 1 and f4.milp(objective="splits", rho=rho)[0] == "infeasible",
    f"drawings {[[f4.Z[i] for i in f4.members(b)] for b in ds[0]]}")

print("ALL OK" if ok_all else "SOME MISMATCH")
sys.exit(0 if ok_all else 1)
