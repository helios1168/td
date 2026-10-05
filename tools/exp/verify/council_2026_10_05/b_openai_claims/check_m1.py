"""p1-sol T6, p1-astra T5, p1-astra T6 and the pass-2 C2/C3 instances that bear on them:
master feasibility versus M1 (connected drawings), per-unit connectivity, fixed-target lifts,
metro state counts and the Hall rows."""
import sys

from common import fmt, report, suites
from model import Inst

ok_all = True


def chk(tag, ok, detail=""):
    global ok_all
    ok_all &= report(tag, ok, detail)


def names(I, d):
    return [[I.Z[i] for i in I.members(b)] for b in d]


def star(prefix, unit, mass=1.0, leaves=5):
    zs = [(f"{prefix}c", unit, mass)] + [(f"{prefix}l{k}", unit, mass) for k in range(leaves)]
    ed = [(f"{prefix}c", f"{prefix}l{k}") for k in range(leaves)]
    return zs, ed


# --- sol T6 / astra T5 (1): six-ZIP unit-mass star + five isolated mass-3 units, K = 7 ----------
zs, ed = star("s", "v")
pads = [(f"p{k}", f"p{k}", 3.0) for k in range(5)]
for mode in ("clipped", "free"):
    I = Inst(zs + pads, ed, K=7, delta=0.15, eta=0.05,
             modes={"v": mode, **{f"p{k}": "whole" for k in range(5)}}, name=f"star-{mode}")
    st, val, nsol = I.milp(objective="splits")
    ds = I.drawings()
    chk(f"T6/T5 star ({mode}): master feasible (v in two mass-3 copies) but no connected in-band "
        "drawing exists", st == "optimal" and len(ds) == 0,
        f"plan {fmt(I, nsol)}, s* = {val}, M1 drawings {len(ds)} (of {len(I.drawings(band=False))} "
        "connected 7-partitions)")

# --- sol T6 (2): M1 does not need each district ∩ unit connected ------------------------------
I = Inst([("z1", "v", 1), ("z2", "v", 1.5), ("z3", "v", 1.5), ("z4", "v", 1.5), ("z5", "v", 1),
          ("A", "A", .5), ("B", "B", .5), ("C", "C", 1.5), ("P", "P", 4.5), ("Q", "Q", 4.5)],
         [("z1", "z2"), ("z2", "z3"), ("z3", "z4"), ("z4", "z5"), ("A", "z1"), ("B", "z5"),
          ("C", "z1"), ("C", "z5")],
         K=4, delta=0.15, eta=0.05, modes={u: "whole" for u in "ABCPQ"}, name="sol-T6-local")
ds = I.drawings()
inX = [d for d in ds if I.in_X(d)]


def local_ok(I, d):
    return all(len(I.members(b)) == 0 or
               all(__import__("model").connected([i for i in I.members(b) if I.uof[i] == v], I.zadj)
                   for v in I.footprint(b))
               for b in d)


loc = [d for d in ds if local_ok(I, d)]
target = [d for d in ds if sorted(map(sorted, names(I, d))) ==
          sorted(map(sorted, [["A", "B", "C", "z1", "z5"], ["z2", "z3", "z4"], ["P"], ["Q"]]))]
chk("T6 local connectivity: the drawing {z1,z5,A,B,C} | {z2,z3,z4} | {P} | {Q} is M1 (in band, "
    "connected) with a disconnected v-part; requiring connected parts removes it",
    len(target) == 1 and not local_ok(I, target[0]),
    f"M1 drawings {len(ds)} ({len(inX)} in 𝒳_c), with every district∩unit connected {len(loc)}: "
    f"{[names(I, d) for d in loc]}; target masses {[I.dmass(b) for b in target[0]]}")

# --- astra T5 (2) / astra C3: equal ZIP targets fail, the read-back fibre is not empty ----------
I = Inst([("a", "v", .9), ("b", "v", 1.1)] + [(f"p{k}", f"p{k}", 1.0) for k in range(5)],
         [("a", "b")], K=7, delta=0.15, eta=0.1,
         modes={f"p{k}": "whole" for k in range(5)}, name="astra-T5b")
ps = I.plans()
ds = [d for d in I.drawings() if I.in_X(d)]
rbs = [fmt(I, I.readback(d)[0]) for d in ds]
# exact equal targets a_{v,j} = 1: some assignment of v's ZIPs to the two copies giving 1 and 1?
exact = [(x, 2 - x) for x in (0, .9, 1.1, 2.0) if abs(x - 1) < 1e-9]
chk("T5b fixed targets: plan n_{v} = 2 (targets 1/1) has no exact ZIP lift, yet the drawing "
    "{a} | {b} (0.9 / 1.1) is in 𝒳_c with the same read-back",
    not exact and len(ds) >= 1 and fmt(I, ps[0]) in rbs,
    f"plans {[fmt(I, p) for p in ps]}, drawings {[names(I, d) for d in ds]}, read-backs {rbs}")

# --- astra T6: a cross-state metro's (n, t) does not fix the state split count ----------------
I = Inst([("a1", "m", 1), ("a2", "m", 1), ("b1", "m", 1), ("b2", "m", 1)] +
         [(f"p{k}", f"p{k}", 2.0) for k in range(5)],
         [("a1", "a2"), ("b1", "b2"), ("a1", "b1"), ("a2", "b2")], K=7, delta=0.15, eta=0.1,
         modes={f"p{k}": "whole" for k in range(5)},
         zstate={"a1": "X", "a2": "X", "b1": "Y", "b2": "Y"}, name="astra-T6")
ds = [d for d in I.drawings() if I.in_X(d)]
by_rb = {}
for d in ds:
    key = (tuple(sorted(fmt(I, I.readback(d)[0]).items())),
           tuple(sorted((u, round(x, 9)) for (u, s), x in I.readback(d)[1].items())))
    by_rb.setdefault(key, set()).add(I.state_splits(d) - 0)
splits = sorted({I.state_splits(d) for d in ds})
chk("T6 metro: drawings with one read-back (n_m = 2, t = 1) have state split counts {0, 2}",
    len(by_rb) == 1 and splits == [0, 2],
    f"{len(ds)} drawings, read-backs {len(by_rb)}, state splits by drawing "
    f"{[(names(I, d)[:2], I.state_splits(d)) for d in ds]}")

# --- pass-2 C2: Hall rows are valid for every connected drawing; star instances ---------------
inst = suites()
viol, n_draw = [], 0
for I, ps in inst:
    for d in I.drawings():
        nv, t = I.readback(d)
        if nv is None or not I.modes_ok(d):
            continue  # footprint outside the family: no read-back in this master
        n_draw += 1
        # Hall rows and the n-only rows do not use η: check them on every connected drawing
        hv = [r for r in I.plan_violations(nv, t, hall=True, eta=0.0) if r.startswith(("hall", "border", "count"))]
        if hv:
            viol.append((I.name, fmt(I, nv), hv))
chk("C2 Hall rows: Σ_{S∋v, ∅≠N(v)∩S⊆W} n_S ≤ |∪_{u∈W} ∂_u(v)| holds on the read-back of every "
    "connected in-band drawing with footprints in the family (η not needed)", not viol,
    f"{n_draw} drawings; violations {viol[:2]}")


def hall_case(tag, I, expect_plain, expect_hall, expect_draw):
    p = I.milp(objective="splits")
    h = I.milp(objective="splits", hall=True)
    ds = I.drawings()
    got = (p[0] == "optimal", h[0] == "optimal", len(ds) > 0)
    chk(tag, got == (expect_plain, expect_hall, expect_draw),
        f"plain master {p[0]} {fmt(I, p[2]) if p[2] else ''} s*={p[1]}; with Hall {h[0]} "
        f"{fmt(I, h[2]) if h[2] else ''}; M1 drawings {[names(I, d) for d in ds][:2]}")


# sol C2: singleton clipped six-ZIP star, K = 2, band [2.55, 3.45]: no neighbours, no Hall rows
zs, ed = star("s", "v")
hall_case("C2 sol: lone six-ZIP star, K = 2: master feasible with or without Hall, no drawing",
          Inst(zs, ed, K=2, delta=0.15, eta=0.05, modes={"v": "clipped"}, name="sol-C2-star"),
          True, True, False)
path = [(f"z{k}", "v", 1.0) for k in range(6)]
hall_case("C2 sol: lone six-ZIP path, same summaries: drawable",
          Inst(path, [(f"z{k}", f"z{k + 1}") for k in range(5)], K=2, delta=0.15, eta=0.05,
               modes={"v": "clipped"}, name="sol-C2-path"), True, True, True)
# astra C2 border-star: v = hub + 2 leaves (unit mass), a, b (.5) attach to the hub only; K = 2, ±15%
bs = [("h", "v", 1), ("l1", "v", 1), ("l2", "v", 1), ("a", "a", .5), ("b", "b", .5)]
bse = [("h", "l1"), ("h", "l2"), ("a", "h"), ("b", "h")]
I = Inst(bs, bse, K=2, delta=0.15, eta=0.05, modes={"a": "whole", "b": "whole"}, name="astra-C2")
pair = {I.F.index(frozenset({"a", "v"})): 1, I.F.index(frozenset({"b", "v"})): 1}
chk("C2 astra border-star: Hall rejects the plan {a,v}+{b,v} (2 > |{h}| = 1) that C7 passes",
    I.milp(objective="splits", fix_n=pair)[0] == "optimal"
    and I.milp(objective="splits", fix_n=pair, hall=True)[0] == "infeasible")
hall_case("C2 astra border-star: plain master feasible ({a,v}+{b,v}); with Hall still feasible "
          "through {a,v,b}+{v}; no drawing", I, True, True, False)
# opus C2: masses 1/3, K = 2, δ = .1: Hall + corridor close it
os_ = [("h", "v", 1 / 3), ("l1", "v", 1 / 3), ("l2", "v", 1 / 3), ("a", "a", .5), ("b", "b", .5)]
hall_case("C2 opus star (1/3 masses, δ = .1): plain master feasible, with Hall infeasible, no drawing",
          Inst(os_, bse, K=2, delta=0.1, eta=0.05, modes={"a": "whole", "b": "whole"}, name="opus-C2"),
          True, False, False)
# opus C2 path: v = z1–z2–z3 (.1/.8/.1), a at z1, b at z3, K = 2, δ = .2: Hall passes, no drawing
op = [("z1", "v", .1), ("z2", "v", .8), ("z3", "v", .1), ("a", "a", .5), ("b", "b", .5)]
ope = [("z1", "z2"), ("z2", "z3"), ("a", "z1"), ("b", "z3")]
hall_case("C2 opus path (.1/.8/.1, δ = .2): master feasible with Hall, no drawing",
          Inst(op, ope, K=2, delta=0.2, eta=0.05, modes={"a": "whole", "b": "whole"}, name="opus-C2-path"),
          True, True, False)
op3 = [("z1", "v", 1 / 3), ("z2", "v", 1 / 3), ("z3", "v", 1 / 3), ("a", "a", .5), ("b", "b", .5)]
hall_case("C2 opus path (1/3 each): same statistics, drawable",
          Inst(op3, ope, K=2, delta=0.2, eta=0.05, modes={"a": "whole", "b": "whole"}, name="opus-C2-path3"),
          True, True, True)
# fable C2: path u–v–w, v a star c, l1..l4 (unit), u at l1, w at l2, M_u = M_w = 3, K = 2, δ = .15
fs = [("c", "v", 1)] + [(f"l{k}", "v", 1) for k in range(1, 5)] + [("u", "u", 3), ("w", "w", 3)]
fse = [("c", f"l{k}") for k in range(1, 5)] + [("u", "l1"), ("w", "l2")]
hall_case("C2 fable star: master feasible with Hall (2 ≤ |{l1,l2}|), no drawing",
          Inst(fs, fse, K=2, delta=0.15, eta=0.05, modes={"u": "whole", "w": "whole"}, size_cap=2,
               name="fable-C2"), True, True, False)
fp = [(f"p{k}", "v", 1) for k in range(1, 6)] + [("u", "u", 3), ("w", "w", 3)]
fpe = [(f"p{k}", f"p{k + 1}") for k in range(1, 5)] + [("u", "p1"), ("w", "p5")]
hall_case("C2 fable path (5 unit ZIPs, ends attached): drawable",
          Inst(fp, fpe, K=2, delta=0.15, eta=0.05, modes={"u": "whole", "w": "whole"}, size_cap=2,
               name="fable-C2-path"), True, True, True)

print("ALL OK" if ok_all else "SOME MISMATCH")
sys.exit(0 if ok_all else 1)
