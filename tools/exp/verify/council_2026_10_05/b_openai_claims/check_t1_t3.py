"""p1-sol T1, p1-astra T1 (F2 split indicator, projection, pairwise rows, state pieces) and
p1-sol T3, p1-astra T3 (cuts lower bound -> split lower bound)."""
import itertools
import sys

from common import fmt, report, suites
from model import Inst

ok_all = True


def chk(tag, ok, detail=""):
    global ok_all
    ok_all &= report(tag, ok, detail)


# --- T1(a): the indicator rows, both authors' forms, for every H ≤ 12 -----------------------
pairs = 0
for H in range(1, 13):
    for r in range(1, H + 1):
        for s in (0, 1):
            sol = 1 + s <= r <= 1 + (H - 1) * s
            astra = r <= 1 + (H - 1) * s and s <= r - 1
            want = s == (1 if r >= 2 else 0)
            pairs += 1
            if sol != want or astra != want:
                chk(f"indicator H={H} r={r} s={s}", False)
chk("T1 indicator: s = 1[r ≥ 2] ⇔ 1+s ≤ r ≤ 1+(H−1)s (sol) ⇔ r ≤ 1+(H−1)s, s ≤ r−1 (astra)", True,
    f"{pairs} (H, r, s) triples, H = 1..12")

# --- T1(b): projection unchanged, MILP with s_v against plan enumeration ---------------------
inst = suites()
n_vec = n_inst = 0
bad = []
for I, ps in inst:
    n_inst += 1
    best = min(I.nsplits(p) for p in ps)
    st, val, nsol = I.milp(objective="splits")
    if st != "optimal" or round(val) != best or I.nsplits(nsol) != best:
        bad.append((I.name, "split optimum", best, val))
    # caps valid: every feasible plan has r_v ≤ U_v, so s_v = 1 is always feasible
    for p in ps:
        r = I.r(p)
        if any(r[v] > I.cap(v) for v in I.units):
            bad.append((I.name, "cap", fmt(I, p)))
    # projection: every candidate n is MILP-feasible (with s_v) iff its share LP is feasible
    for nv in I.nvectors():
        n_vec += 1
        lp = I.share_lp(nv)
        mi = I.milp(objective="splits", fix_n=nv)[0] == "optimal"
        if lp != mi:
            bad.append((I.name, "projection", fmt(I, nv), lp, mi))
    dmin = min(I.D(p) for p in ps)
    st, val, _ = I.milp(objective="diam")
    if abs(val - dmin) > 1e-6:
        bad.append((I.name, "diam optimum", dmin, val))
chk("T1 projection: F2 rows leave the (n,t) projection unchanged; MILP split optimum = enumeration",
    not bad, f"{n_inst} instances (6-8 units), {n_vec} candidate n vectors; mismatches {bad[:3]}")

# --- T1(c): the pairwise row s_v ≥ n_S + n_T − 1 is invalid -----------------------------------
# sol fixture: free v (ZIPs 1, 1, .5 on a path, the .5 ZIP borders a), whole a .5, four whole
# isolated mass-1 units; K = 7, η = .1, δ = 0; supports {v}, {a}, {v,a} and four singletons.
sol = Inst([("v1", "v", 1), ("v2", "v", 1), ("v3", "v", .5), ("a", "a", .5),
            ("w1", "w1", 1), ("w2", "w2", 1), ("w3", "w3", 1), ("w4", "w4", 1)],
           [("v1", "v2"), ("v2", "v3"), ("v3", "a")], K=7, delta=0.0, eta=0.1,
           modes={"a": "whole", "w1": "whole", "w2": "whole", "w3": "whole", "w4": "whole"},
           name="sol-T1")
ps = sol.plans()
st, val, nsol = sol.milp(objective="splits")
pw = sol.milp(objective="splits", pairwise=True)[0]
ds = [d for d in sol.drawings() if sol.in_X(d)]
rb = [fmt(sol, sol.readback(d)[0]) for d in ds]
chk("T1 sol fixture: plan n_v = 2, n_va = 1 feasible, s* = 1; pairwise row makes the master infeasible",
    st == "optimal" and val == 1 and pw == "infeasible" and len(ps) == 1,
    f"plans {[fmt(sol, p) for p in ps]}, s* = {val}, pairwise MILP {pw}; "
    f"𝒳_c drawings {len(ds)}, read-backs {rb}")
astra = Inst([("v1", "v", 1), ("v2", "v", 1), ("v3", "v", 1)] +
             [(f"u{k}", f"u{k}", 1) for k in range(1, 6)],
             [("v1", "v2"), ("v2", "v3"), ("v3", "u1")], K=8, delta=0.0, eta=0.2,
             modes={f"u{k}": "whole" for k in range(1, 6)}, name="astra-T1")
ps = astra.plans()
st, val, nsol = astra.milp(objective="splits")
pw = astra.milp(objective="splits", pairwise=True)[0]
chk("T1 astra fixture: n_{v} = 3 with unused {v,u1}; pairwise row (3 + 0 − 1 = 2) infeasible",
    st == "optimal" and val == 1 and pw == "infeasible",
    f"plans {[fmt(astra, p) for p in ps]}, s* = {val}, pairwise MILP {pw}")

# --- T1(d): state-level count with pieces ---------------------------------------------------
# state S has two free pieces p1, p2, adjacent through one ZIP edge, and a whole unit x of state X.
# η = 0.5: p1, p2 have two unit-mass ZIPs each, x has mass 1, K = 5, δ = 0; ⌊1/η⌋ = 2 per unit,
# yet S is touched 4 times, so the unit η cap is not a state cap. η = 0.25: p1, p2 have three
# 0.5-mass ZIPs each, K = 4; the plan {p1}, {p1,p2}, {p2}, {x} has a {p1,p2} copy, counted once.
def pieces_inst(eta):
    if eta == 0.5:
        zs = [("p1z0", "p1", 1), ("p1z1", "p1", 1), ("p2z0", "p2", 1), ("p2z1", "p2", 1)]
        ed = [("p1z0", "p1z1"), ("p1z1", "p2z0"), ("p2z0", "p2z1"), ("p2z1", "x")]
        K = 5
    else:
        zs = [(f"p{k}z{i}", f"p{k}", .5) for k in (1, 2) for i in range(3)]
        ed = [("p1z0", "p1z1"), ("p1z1", "p1z2"), ("p1z2", "p2z0"), ("p2z0", "p2z1"),
              ("p2z1", "p2z2"), ("p2z2", "x")]
        K = 4
    return Inst(zs + [("x", "x", 1)], ed, K=K, delta=0.0, eta=eta, modes={"x": "whole"},
                state={"p1": "S", "p2": "S", "x": "X"}, name=f"pieces-eta{eta}")


def touches(I, nv, st):
    return sum(c for s, c in nv.items() if any(I.state[u] == st for u in I.F[s]))


for eta in (0.5, 0.25):
    pieces = pieces_inst(eta)
    ps = pieces.plans()
    mism = []
    draw = [d for d in pieces.drawings() if pieces.in_X(d)]
    for d in draw:
        nv, _ = pieces.readback(d)
        owners = sum(1 for b in d if any(pieces.zstate[i] == "S" for i in pieces.members(b)))
        if touches(pieces, nv, "S") != owners:
            mism.append(fmt(pieces, nv))
    enum_min = min(sum(1 for st in "SX" if touches(pieces, p, st) >= 2) for p in ps)
    st, val, _ = pieces.milp(objective="states", state_splits=True)
    max_touch = max(touches(pieces, p, "S") for p in ps)
    once = [(fmt(pieces, p), touches(pieces, p, "S"), pieces.r(p)["p1"] + pieces.r(p)["p2"])
            for p in ps if any(pieces.F[s] == frozenset({"p1", "p2"}) for s in p)]
    chk(f"T1 state rows (η = {eta}): Σ_{{S∩P(σ)≠∅}} n_S = districts owning a ZIP of σ in every 𝒳_c "
        "drawing; MILP state-split min = enumeration", not mism and round(val) == enum_min,
        f"{len(ps)} plans, {len(draw)} drawings, state min {val} (enum {enum_min}), max touches of S "
        f"{max_touch}; plans with a {{p1,p2}} copy (plan, state count, Σ r_v): {once[:2]}")
    if eta == 0.5:
        capped = pieces.milp(objective="states", state_splits=True, extra_rows=[
            ({s: 1 for s, S in enumerate(pieces.F) if S & {"p1", "p2"}}, 0, 2)])[0]
        chk("T1 state cap: ⌊1/η⌋ = 2 as a state cap is invalid (master becomes infeasible); K is valid",
            capped == "infeasible" and max_touch == 4, f"S touched {max_touch} times; capped master {capped}")
    else:
        chk("T1 state rows: a {p1,p2} copy is counted once (state count < Σ_{v∈P(σ)} r_v)",
            any(a < b for _, a, b in once), f"{once[:1]}")

# --- T3: cuts lower bound B -> split lower bound q (both authors) -----------------------------
nT3 = tight = 0
bad = []
for I, ps in inst:
    B = min(I.ncuts(p) for p in ps)
    st, cval, _ = I.milp(objective="cuts")
    if round(cval) != B:
        bad.append((I.name, "cuts milp", B, cval))
    caps = sorted((I.cap(v) - 1 for v in I.units if I.splittable(v)), reverse=True)
    q = next((k for k in range(len(caps) + 1) if sum(caps[:k]) >= B), None)
    smin = min(I.nsplits(p) for p in ps)
    nT3 += 1
    if q is None or smin < q:
        bad.append((I.name, "bound", B, q, smin))
    tight += smin == q
    # the per-plan inequality C ≤ Σ_split (H_v − 1)
    for p in ps:
        r = I.r(p)
        if I.ncuts(p) > sum(I.cap(v) - 1 for v in I.units if r[v] >= 2):
            bad.append((I.name, "per-plan", fmt(I, p)))
chk("T3: split count ≥ least q with top-q (H_v − 1) summing to ≥ B (B = exact min cuts)", not bad,
    f"{nT3} instances, bound tight on {tight}; mismatches {bad[:3]}")

print("ALL OK" if ok_all else "SOME MISMATCH")
sys.exit(0 if ok_all else 1)
