"""p1-sol T2, p1-astra T2: splits-then-diameter is lexicographic (pinned two-pass and one-pass
scalarisation with ε < 1/W), and with μ = 0 the extended optimum bounds every connected drawing in
the matching policy class 𝒳_c(δ) (Proposition D with s_v = 1[r̂_v ≥ 2])."""
import sys

from common import fmt, report, suites
from model import Inst

ok_all = True


def chk(tag, ok, detail=""):
    global ok_all
    ok_all &= report(tag, ok, detail)


inst = suites()
bad, n_lex, n_multi, n_eps_fail = [], 0, 0, 0
for I, ps in inst:
    pairs = sorted((I.nsplits(p), I.D(p)) for p in ps)
    lex = pairs[0]
    W = I.K * max(I.w)  # every feasible plan has 0 ≤ D ≤ W because Σ n = K
    n_lex += 1
    n_multi += len({s for s, _ in pairs}) > 1
    # pinned two-pass
    st, s1, _ = I.milp(objective="splits")
    st2, d2, n2 = I.milp(objective="diam", pins=[("splits", s1, s1)])
    if round(s1) != lex[0] or abs(d2 - lex[1]) > 1e-6 or I.nsplits(n2) != lex[0]:
        bad.append((I.name, "two-pass", lex, s1, d2))
    # one pass, ε = 0.999 / W (W > 0) or splits alone (W = 0)
    if W > 0:
        st, val, n1 = I.milp(objective="lex", eps=0.999 / W)
        got = (I.nsplits(n1), I.D(n1))
        if got[0] != lex[0] or abs(got[1] - lex[1]) > 1e-6:
            bad.append((I.name, "scalarised", lex, got))
        # the condition matters: a large ε can buy diameter with a split
        st, val, nb = I.milp(objective="lex", eps=1000.0 / W)
        n_eps_fail += I.nsplits(nb) != lex[0]
chk("T2 lexicographic: pinned two-pass and one pass with ε = 0.999/W both return the enumerated "
    "lex optimum (min splits, then min diameter)", not bad,
    f"{n_lex} instances ({n_multi} with several split levels); ε = 1000/W departs from lex on "
    f"{n_eps_fail}; mismatches {bad[:3]}")

# W = 0: every support has diameter 0 (all centroids coincide); then splits alone decide
I0 = Inst([("v1", "v", 1), ("v2", "v", 1), ("a", "a", 1), ("b", "b", 1)],
          [("v1", "v2"), ("v2", "a"), ("a", "b")], K=2, delta=0.0, eta=0.1,
          pos={"v": (0,), "a": (0,), "b": (0,)}, modes={"a": "whole", "b": "whole"}, name="W0")
ps = I0.plans()
st, s1, _ = I0.milp(objective="splits")
st2, d2, _ = I0.milp(objective="diam", pins=[("splits", s1, s1)])
chk("T2 W = 0: D ≡ 0, splits alone; two-pass returns D = 0", max(I0.w) == 0 and d2 == 0 and
    round(s1) == min(I0.nsplits(p) for p in ps), f"s* = {s1}, D = {d2}, {len(ps)} plans")

# --- Proposition D extended with s_v: every 𝒳_c drawing's read-back is feasible -----------------
viol, n_draw, n_inst, below, outside_below = [], 0, 0, [], 0
for I, ps in inst:
    lex = min((I.nsplits(p), I.D(p)) for p in ps)
    ds = I.drawings()
    n_inst += 1
    for d in ds:
        if not I.in_X(d):
            if I.own_splits(d) < lex[0]:
                outside_below += 1
            continue
        n_draw += 1
        nv, t = I.readback(d)
        v = I.plan_violations(nv, t)
        if v:
            viol.append((I.name, fmt(I, nv), v))
        if I.milp(objective="splits", fix_n=nv)[0] != "optimal":
            viol.append((I.name, "MILP rejects read-back", fmt(I, nv)))
        sp = I.own_splits(d)
        if sp != I.pos_splits(d) or sp != I.nsplits(nv):
            viol.append((I.name, "split count differs", sp, I.pos_splits(d), I.nsplits(nv)))
        Dd = sum(I.w[I.F.index(I.footprint(b))] for b in d)
        if (sp, Dd) < (lex[0], lex[1] - 1e-9):
            below.append((I.name, (sp, Dd), lex))
chk("T2 Prop D with s_v: every 𝒳_c(δ) drawing's read-back (with s_v = 1[r̂_v ≥ 2]) is MILP-feasible, "
    "its split count (ownership = positive opportunity, since η > 0) equals the read-back's, and "
    "(splits, D) ≥lex the master's", not viol and not below,
    f"{n_inst} instances, {n_draw} drawings in 𝒳_c; violations {viol[:2]}; below {below[:2]}; "
    f"connected in-band drawings outside 𝒳_c with fewer splits than s*: {outside_below}")

print("ALL OK" if ok_all else "SOME MISMATCH")
sys.exit(0 if ok_all else 1)
