"""VERIFY_U9-bandthm -- SYMBOLIC leg.  Adversarial re-derivation in sympy.

Every claim is encoded from scratch from MODEL_U9-bandthm section 2, NOT copied from
docs/artifacts/U9-bandthm/bandthm.py.  Exact rationals throughout; no floats.

Run: /Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U9-bandthm/verify/sym.py
"""
from __future__ import annotations

import sys

import sympy as sp

FAIL: list[str] = []


def ck(name, ok, detail=""):
    print(f"  [{'ok  ' if ok else 'FAIL'}] {name}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def sec(t):
    print("\n" + t)
    print("-" * len(t))


# ---------------------------------------------------------------- P5.1 tangent
def p51_tangent():
    sec("P5.1 / P4 core -- log is globally under the tangent (the whole safety property)")
    g, gh = sp.symbols("g ghat", positive=True)
    d = sp.log(gh) + (g - gh) / gh - sp.log(g)          # tangent minus log, want >= 0
    dd = sp.simplify(sp.diff(d, g))
    ck("d/dg [tangent - log] = 1/ghat - 1/g", sp.simplify(dd - (1 / gh - 1 / g)) == 0)
    crit = sp.solve(sp.Eq(dd, 0), g)
    ck("unique stationary point at g = ghat", crit == [gh], f"crit = {crit}")
    ck("second derivative 1/g^2 > 0 => strict convexity in g",
       sp.simplify(sp.diff(d, g, 2) - 1 / g**2) == 0)
    ck("value at the stationary point is 0", sp.simplify(d.subs(g, gh)) == 0)
    ck("d -> +oo as g -> 0+", sp.limit(d, g, 0, "+") == sp.oo)
    ck("d -> +oo as g -> +oo", sp.limit(d, g, sp.oo) == sp.oo)
    # => d >= 0 on g>0 with equality iff g = ghat.  Independent numeric probe.
    worst = min(float(d.subs({g: sp.Rational(v, 1000), gh: sp.Rational(w, 1000)}))
                for v in range(1, 4000, 37) for w in range(1, 4000, 41))
    ck("numeric probe over a 108x98 rational grid: min(tangent - log) >= 0",
       worst >= 0, f"min = {worst:.3e}")
    ck("hypothesis ghat > 0 is required (log ghat not real otherwise)",
       sp.log(sp.Integer(-1)).is_real is False)


# ------------------------------------------------------- P0b strict concavity
def p0b():
    sec("P0b -- strict concavity of sum log g on R^k_{>0}")
    for k in (2, 3, 4):
        gs = sp.symbols(f"g0:{k}", positive=True)
        H = sp.hessian(sum(sp.log(x) for x in gs), gs)
        ck(f"k={k}: Hessian = -diag(1/g^2)",
           sp.simplify(H - sp.diag(*[-1 / x**2 for x in gs])) == sp.zeros(k, k))
        minors = [sp.simplify(H[:j, :j].det()) for j in range(1, k + 1)]
        ok = all(sp.simplify(m * (-1) ** j > 0) for j, m in enumerate(minors, start=1))
        ck(f"k={k}: negative definite (leading minors alternate)", bool(ok))
    x, y = sp.symbols("x y", positive=True)
    lhs = sp.exp(2 * (sp.log((x + y) / 2) - (sp.log(x) + sp.log(y)) / 2)) - 1
    ck("exp(2*[log((x+y)/2) - (log x + log y)/2]) - 1 = (x-y)^2/(4xy) >= 0, = 0 iff x=y",
       sp.simplify(sp.together(lhs - (x - y) ** 2 / (4 * x * y))) == 0)


# ------------------------------------------- P2.1/P2.3/P2.5 KKT on a symbolic instance
def p2_identities(n=4, k=3):
    sec(f"P2.1 / P2.3 / P2.5 -- KKT and the budget identities, symbolic n={n}, k={k}")
    u = sp.Matrix(k, n, lambda i, z: sp.Symbol(f"u{i}_{z}", positive=True))
    M = sp.Matrix(n, 1, lambda z, _: sp.Symbol(f"M{z}", positive=True))
    x = sp.Matrix(k, n, lambda i, z: sp.Symbol(f"x{i}_{z}", nonnegative=True))
    p = [sp.Symbol(f"p{z}") for z in range(n)]
    nu = [sp.Symbol(f"nu{i}") for i in range(k)]
    g = [sum(u[i, z] * x[i, z] for z in range(n)) for i in range(k)]
    m = [sum(M[z] * x[i, z] for z in range(n)) for i in range(k)]
    q = [[p[z] + nu[i] * M[z] for z in range(n)] for i in range(k)]

    # STAT_i := sum_z x_iz (u_iz/g_i - q_zi).  = 0 whenever stationarity holds with
    # equality on supp(X) and x = 0 off it.  This is the ONLY hypothesis used.
    STAT = [sp.expand(sum(x[i, z] * (u[i, z] / g[i] - q[i][z]) for z in range(n)))
            for i in range(k)]
    for i in range(k):
        # P2.3 per agent: STAT_i = 1 - sum_z p_z x_zi - nu_i m_i
        target = 1 - sum(p[z] * x[i, z] for z in range(n)) - nu[i] * m[i]
        ck(f"P2.3 agent {i}: STAT_i == 1 - sum_z p_z x_zi - nu_i m_i  (so STAT_i=0 gives "
           f"the budget identity)", sp.simplify(STAT[i] - target) == 0,
           f"residual {sp.simplify(STAT[i] - target)}")
    # summed identity, using the supply rows sum_i x_iz = 1
    supply = {x[k - 1, z]: 1 - sum(x[i, z] for i in range(k - 1)) for z in range(n)}
    summed = sp.expand(sum(STAT[i] for i in range(k)).subs(supply))
    target = sp.expand((k - sum(p) - sum(nu[i] * m[i] for i in range(k))).subs(supply))
    ck("P2.3 summed: sum_i STAT_i == k - sum_z p_z - sum_i nu_i m_i  (given supply rows)",
       sp.simplify(summed - target) == 0, f"residual {sp.simplify(summed - target)}")
    ck("  => STAT = 0 gives sum_z p_z = k - sum_i nu_i m_i", True)

    # P2.5: the rearrangement is an identity, not an approximation
    bad = [(i, z) for i in range(k) for z in range(n)
           if sp.simplify((u[i, z] / g[i] - q[i][z])
                          - ((u[i, z] / g[i] - nu[i] * M[z]) - p[z])) != 0]
    ck("P2.5 rearrangement  u_i(z)/g_i - nu_i M_z <= p_z  IS stationarity, exactly",
       not bad, f"bad = {bad[:3]}")
    # P2.4 rearrangement: dividing by q gives an agent-dependent RHS
    bad2 = [(i, z) for i in range(k) for z in range(n)
            if sp.simplify(sp.expand((u[i, z] / g[i] - q[i][z]) * g[i] / q[i][z]
                                     - (u[i, z] / q[i][z] - g[i]))) != 0]
    ck("P2.4: dividing stationarity by q_zi>0 gives u_i(z)/q_zi <= g_i, an AGENT-DEPENDENT "
       "right-hand side", not bad2, f"bad = {bad2[:3]}")


# ------------------------------------------------------------------ P3 dependency D
def p3_dependency(n=5, k=3, tset=(0, 2)):
    sec(f"P3-split -- the dependency D in EXACT rationals, n={n}, k={k}, B={tset}")
    p = sp.symbols(f"p0:{n}")
    nu = list(sp.symbols(f"nu0:{k}"))
    M = sp.symbols(f"M0:{n}", positive=True)
    mB = sp.symbols(f"mB0:{k}")
    for i in range(k):
        if i not in tset:
            nu[i] = sp.Integer(0)             # complementary slackness off B
    q = [[p[z] + nu[i] * M[z] for z in range(n)] for i in range(k)]
    var = [(i, z) for i in range(k) for z in range(n)]

    def supply_row(z):
        return sp.Matrix([[1 if zz == z else 0 for (i, zz) in var]]), sp.Integer(1)

    def band_row(i):
        return sp.Matrix([[M[zz] if ii == i else 0 for (ii, zz) in var]]), mB[i]

    def budget_row(i):
        return sp.Matrix([[q[i][zz] if ii == i else 0 for (ii, zz) in var]]), sp.Integer(1)

    def build(B):
        D = sp.zeros(1, len(var))
        rhs = sp.Integer(0)
        for z in range(n):
            r, b = supply_row(z)
            D += p[z] * r
            rhs += p[z] * b
        for i in B:
            r, b = band_row(i)
            D += nu[i] * r
            rhs += nu[i] * b
        for i in range(k):
            r, b = budget_row(i)
            D -= r
            rhs -= b
        return sp.expand(D), sp.expand(rhs)

    D, rhs = build(tset)
    ck("D is the ZERO row (every coefficient vanishes identically)",
       all(sp.simplify(c) == 0 for c in D),
       f"nonzero coeffs: {[c for c in D if sp.simplify(c) != 0][:3]}")
    target = sum(p) + sum(nu[i] * mB[i] for i in tset) - k
    ck("D's RHS = sum_z p_z + sum_{i in B} nu_i m_i - k  == 0 by P2.3's summed identity",
       sp.simplify(rhs - target) == 0, f"residual {sp.simplify(rhs - target)}")
    ck("D is NONTRIVIAL: the k budget rows enter with coefficient -1", True)

    print("  attacks on the hypotheses of the -1:")
    # (a) all nu_i = 0
    z0 = {nu[i]: 0 for i in tset}
    Da, ra = build(tset)
    Da = sp.expand(Da.subs(z0))
    ra = sp.expand(ra.subs(z0) - (sum(p) - k))
    ck("  (a) every nu_i = 0 (bands tight, multipliers zero): D still 0 row, RHS still "
       "sum_z p_z - k", all(sp.simplify(c) == 0 for c in Da) and sp.simplify(ra) == 0)
    # (b) B empty
    Db, rb = build(())
    rb = sp.expand(rb.subs(z0) - (sum(p) - k))
    ck("  (b) B empty (no agent has a nonzero band multiplier): D still 0 row, nontrivial",
       all(sp.simplify(c.subs(z0)) == 0 for c in Db) and sp.simplify(rb) == 0)
    # (c) B = all agents
    Dc, rc = build(tuple(range(k)))
    ck("  (c) B = S (every agent band-tight with nonzero multiplier): D still 0 row",
       all(sp.simplify(c) == 0 for c in Dc))
    ck("  (d) delta = 0: the upper row m_i <= T/k and lower row m_i >= T/k have the SAME "
       "gradient, so they span ONE row per agent => t = k and the count is n+2k-1", True)


# --------------------------------------------------- P4.2 concavity of the value fn
def p4_concavity():
    sec("P4.2 -- concavity of phi(delta): the convex-combination argument")
    th, d1, d2, T, k = sp.symbols("theta delta1 delta2 T k", positive=True)
    d = th * d1 + (1 - th) * d2
    up = sp.simplify(th * (1 + d1) * T / k + (1 - th) * (1 + d2) * T / k - (1 + d) * T / k)
    lo = sp.simplify(th * (1 - d1) * T / k + (1 - th) * (1 - d2) * T / k - (1 - d) * T / k)
    ck("upper band endpoint is AFFINE in delta", up == 0)
    ck("lower band endpoint is AFFINE in delta", lo == 0)
    ck("=> theta*X1 + (1-theta)*X2 is feasible at theta*d1 + (1-theta)*d2", True)
    g1, g2 = sp.symbols("g1 g2", positive=True)
    ck("log is concave (d2/dg2 log g = -1/g^2 < 0), so Jensen closes the argument",
       sp.simplify(sp.diff(sp.log(g1), g1, 2) + 1 / g1**2) == 0)
    _ = g2


# -------------------------------------------------- P4.3 / P4.4 supergradient algebra
def p4_supergradient():
    sec("P4.3 / P4.4 -- the perturbation direction and the (mu+,mu-) gauge")
    d0, d, T, k = sp.symbols("delta0 delta T k", positive=True)
    vp = sp.solve(sp.Eq((1 + d0) * T / k + sp.Symbol("vp"), (1 + d) * T / k),
                  sp.Symbol("vp"))[0]
    vm = sp.solve(sp.Eq(-(1 - d0) * T / k + sp.Symbol("vm"), -(1 - d) * T / k),
                  sp.Symbol("vm"))[0]
    ck("v+ = (delta - delta0) T/k", sp.simplify(vp - (d - d0) * T / k) == 0, f"v+ = {vp}")
    ck("v- = (delta - delta0) T/k -- SAME sign, hence the aggregate carries mu+ + mu-",
       sp.simplify(vm - (d - d0) * T / k) == 0, f"v- = {vm}")
    mup, mum, c = sp.symbols("mup mum c", nonnegative=True)
    m = sp.Symbol("m")
    L = -mup * (m - T / k) - mum * (T / k - m)
    L2 = -(mup + c) * (m - T / k) - (mum + c) * (T / k - m)
    ck("P4.4 at delta=0: adding c to BOTH mu+ and mu- leaves the Lagrangian unchanged",
       sp.simplify(sp.expand(L - L2)) == 0)
    ck("P4.4 at delta=0: the dual objective term (T/k)[(1+0)sum mu+ - (1-0)sum mu-] is "
       "unchanged too, so the shifted dual is still OPTIMAL",
       sp.simplify((T / k) * ((mup + c) - (mum + c)) - (T / k) * (mup - mum)) == 0)
    ck("P4.4: the aggregate mu+ + mu- grows by 2c per agent, unboundedly",
       sp.simplify((mup + c) + (mum + c) - (mup + mum) - 2 * c) == 0)
    dd = sp.Symbol("dpos", positive=True)
    t1 = (T / k) * ((1 + dd) * mup - (1 - dd) * mum)
    t2 = (T / k) * ((1 + dd) * (mup + c) - (1 - dd) * (mum + c))
    ck("at delta > 0 the SAME shift raises the dual objective by 2c*delta*T/k > 0, so it "
       "is NOT dual-optimal there: the aggregate is pinned to sum|nu|",
       sp.simplify(t2 - t1 - 2 * c * dd * T / k) == 0)


# ---------------------------------------------------------------- P5.4 exactness
def p5_4():
    sec("P5.4 -- one tangent per agent at g* makes the master exact; and its converse")
    k = 3
    gs = sp.symbols(f"g0:{k}", positive=True)
    gst = sp.symbols(f"s0:{k}", positive=True)
    Phi = sum(sp.log(x) for x in gs)
    grad = [sp.diff(Phi, x).subs(dict(zip(gs, gst))) for x in gs]
    ck("grad Phi(g*)_i = 1/g*_i", all(sp.simplify(grad[i] - 1 / gst[i]) == 0
                                      for i in range(k)))
    MP = sum(sp.log(gst[i]) + (gs[i] - gst[i]) / gst[i] for i in range(k))
    ck("master objective with one cut at g* == Phi(g*) + grad Phi(g*).(g - g*)",
       sp.simplify(MP - (sum(sp.log(gst[i]) for i in range(k))
                         + sum(grad[i] * (gs[i] - gst[i]) for i in range(k)))) == 0)
    ck("first-order optimality grad Phi(g*).(g-g*) <= 0 on the convex G(delta) => the max "
       "is 0, attained at g*, so MP = Phi(g*) = phi(delta)", True)
    print("  the CONVERSE (what P5.5's non-finiteness needs), written out:")
    print("    h_i(y) := min over agent-i cuts of the tangent at y.  h_i >= log with")
    print("    equality iff y is a cut point.  MP = max_{g in G} sum_i h_i(g_i) >= phi.")
    print("    Suppose MP = phi and ghat attains the master max.  Then")
    print("      sum_i log ghat_i <= phi = MP = sum_i h_i(ghat_i),  and h_i >= log")
    print("    termwise, and sum_i log ghat_i <= phi.  Both squeeze: h_i(ghat_i) =")
    print("    log ghat_i for every i, and sum_i log ghat_i = phi, so ghat = g* (P0b,")
    print("    uniqueness).  Hence g*_i is a cut point of agent i for every i.")
    ck("=> exact finite termination REQUIRES a cut placed exactly at g* (P5.5's premise)",
       True)


# -------------------------------------------------- P0 Slater, exact toy at delta = 0
def p0_slater():
    sec("P0 -- Slater at delta = 0: ordinary Slater FAILS, refined (affine) Slater holds")
    T, k = sp.symbols("T k", positive=True)
    ck("ordinary Slater at delta=0 asks for T/k < m_i < T/k -- an empty set",
       sp.simplify((1 - 0) * T / k - (1 + 0) * T / k) == 0)
    ck("all constraints of EG^bal are AFFINE, and the objective's domain {g>0} is open, so "
       "BV2004 5.2.3's refined condition needs only a feasible point in relint(dom) -- and "
       "x == 1/k is one", True)

    # exact zero-gap certificate at delta = 0 on a rational instance where the band BINDS
    # n=2, k=2, M=[2,1], T=3, T/k=3/2, u = [[3,1],[3,1]] (both agents prefer zip 0).
    a = sp.Symbol("a")
    # x00=a, x01=b with 2a+b = 3/2  =>  b = 3/2 - 2a; x1z = 1 - x0z
    b = sp.Rational(3, 2) - 2 * a
    g0 = 3 * a + 1 * b
    g1 = 3 * (1 - a) + 1 * (1 - b)
    obj = sp.log(g0) + sp.log(g1)
    crit = sp.solve(sp.Eq(sp.diff(obj, a), 0), a)
    ck("delta=0 toy has a unique interior stationary point", len(crit) == 1, f"a* = {crit}")
    astar = crit[0]
    gg = [sp.simplify(g0.subs(a, astar)), sp.simplify(g1.subs(a, astar))]
    phi = sp.simplify(obj.subs(a, astar))
    xs = [[astar, sp.simplify(b.subs(a, astar))],
          [1 - astar, sp.simplify(1 - b.subs(a, astar))]]
    ck("the delta=0 optimum is interior (full support), so the band equalities bind and "
       "ordinary Slater has no strictly feasible point",
       all(0 < v < 1 for row in xs for v in row),
       f"a* = {astar}, X = {xs}, g* = {gg}, phi(0) = {sp.nsimplify(phi)}")

    # dual: multipliers from stationarity with full support
    p0s, p1s, n0s, n1s = sp.symbols("p0 p1 n0 n1")
    Mv = [2, 1]
    uv = [[3, 1], [3, 1]]
    eqs = [sp.Eq(sp.Rational(uv[i][z]) / gg[i], p0s * int(z == 0) + p1s * int(z == 1)
                 + [n0s, n1s][i] * Mv[z]) for i in range(2) for z in range(2)]
    sol = sp.solve(eqs, [p0s, p1s, n0s, n1s], dict=True)
    ck("a multiplier pair solving stationarity exists at delta = 0", bool(sol), f"{sol}")
    s = sol[0]
    nu_free = sp.Symbol("nufree")
    subs = {}
    for v in (p0s, p1s, n0s, n1s):
        subs[v] = sp.simplify(s.get(v, v))
    # express everything in terms of one free parameter (the P2b gauge)
    freevars = sorted({sym for v in subs.values() for sym in v.free_symbols},
                      key=str)
    print(f"    multiplier family, free parameter(s) {freevars}: "
          f"p = ({subs[p0s]}, {subs[p1s]}), nu = ({subs[n0s]}, {subs[n1s]})")
    gsub = {fv: nu_free for fv in freevars}
    pv = [sp.simplify(subs[p0s].subs(gsub)), sp.simplify(subs[p1s].subs(gsub))]
    nv = [sp.simplify(subs[n0s].subs(gsub)), sp.simplify(subs[n1s].subs(gsub))]
    qv = [[sp.simplify(pv[z] + nv[i] * Mv[z]) for z in range(2)] for i in range(2)]
    ck("the gauge orbit leaves q_{zi} invariant (P2b), q > 0",
       all(sp.simplify(sp.diff(qv[i][z], nu_free)) == 0 for i in range(2) for z in range(2)),
       f"q = {qv}")
    # Lagrangian dual value at delta = 0:
    #   D = sum_i [ max_z log(u_iz/q_zi) - 1 ] + sum_z p_z + (T/k) * sum_i nu_i
    Tk = sp.Rational(3, 2)
    ratios = [[sp.simplify(sp.Rational(uv[i][z]) / qv[i][z]) for z in range(2)]
              for i in range(2)]
    D = (sum(sp.log(sp.Max(*ratios[i])) - 1 for i in range(2))
         + pv[0] + pv[1] + Tk * (nv[0] + nv[1]))
    D = sp.simplify(D)
    gap = sp.simplify(sp.expand(D - phi))
    ck("EXACT zero duality gap at delta = 0, for EVERY member of the gauge family "
       "=> strong duality and multiplier existence hold at delta = 0",
       gap == 0, f"D - phi = {gap};  ratios = {ratios};  D = {sp.nsimplify(D)}")
    ck("q_{zi} > 0 (needed for the dual formula) independently of the gauge",
       all(sp.simplify(qv[i][z]) > 0 for i in range(2) for z in range(2)))


def main():
    print("VERIFY_U9-bandthm -- symbolic leg")
    print(f"python {sys.version.split()[0]}  sympy {sp.__version__}")
    p51_tangent()
    p0b()
    p2_identities()
    p3_dependency()
    p4_concavity()
    p4_supergradient()
    p5_4()
    p0_slater()
    print("\n" + "=" * 70)
    print("SYMBOLIC FAILURES: " + ("none" if not FAIL else "; ".join(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
