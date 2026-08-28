"""
capacity.py -- objection 2: does a concave sales-response function (capacity /
diminishing returns to territory size) change the allocation?

The linear model scores a zip z at u_a(z) regardless of how many other zips rep a
already holds -- a rep winning 40 zips is modelled as servicing all 40 at full
effectiveness. Skiera & Albers (1998) is the standard objection: territory alignment
should maximise a CONCAVE sales-response function of assigned volume, not a linear
proxy, because attention/capacity is finite.

Crudest honest way to test this without inventing a response-function estimation
exercise: apply a concave transform f to each rep's RAW pooled utility before scoring
the Nash product,
    G_a(S) = f_a( raw_a(S) - d_a ),   raw_a(S) = sum_{z in S} u_a(z)
and re-solve  max log G_a + log G_b.  f_a, f_b concave increasing recovers the linear
model at f = identity. Two response shapes, deliberately different in kind:

  POWER    f(y) = y**kappa, 0 < kappa <= 1        -- HOMOGENEOUS. See finding below:
           this is degenerate when kappa_a = kappa_b, and when it does bite, it is
           mathematically identical to an asymmetric-Nash weight (omega.py), not a
           new phenomenon. This is the "elasticity" framing of capacity and it
           collapses back into ground already surveyed (the omega instability).

  SATURATING  f(y) = K*(1 - exp(-y/K))            -- NOT homogeneous. K is a hard-ish
           capacity ceiling in raw-utility units. This is the genuine new case: it can
           move the allocation even when BOTH reps have the identical ceiling K, because
           the two reps' raw utility functions are not proportional to each other.

Both compose with the outer-approximation solver identically: log(f(y)) is concave
whenever f is concave increasing and y is linear in x (composition of a concave
nondecreasing function with a linear one is concave), so the tangent-cut machinery in
dzero.py generalises by swapping in log(f) and its derivative. Verified against brute
force below.
"""
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix, csr_matrix


def power_response(kappa):
    """f(x) = x**kappa on x>0.  log f = kappa*log x;  (log f)' = kappa/x."""
    def f(x): return 0.0 if x <= 0 else x**kappa
    def logf_prime(x): return np.inf if x <= 0 else kappa / x
    def logf(x): return -np.inf if x <= 0 else kappa * np.log(x)
    return f, logf, logf_prime


def saturating_response(K):
    """f(x) = K*(1-exp(-x/K)) on x>0, a capacity ceiling at K raw-utility units.
    log f = log K + log(1-exp(-x/K));  (log f)' = 1 / (K*(exp(x/K)-1))."""
    def f(x): return 0.0 if x <= 0 else K * (1 - np.exp(-x / K))
    def logf(x): return -np.inf if x <= 0 else np.log(K) + np.log(1 - np.exp(-x / K))
    def logf_prime(x):
        if x <= 1e-12: return 1.0 / K       # limit as x->0+
        return 1.0 / (K * np.expm1(x / K))
    return f, logf, logf_prime


IDENTITY = (lambda x: x, lambda x: np.log(x) if x > 0 else -np.inf,
            lambda x: 1.0 / x if x > 0 else np.inf)


def nash_exact_capacity(A, B, M, theta=0.40, lam=0.30, da=0.0, db=0.0,
                        resp_a=IDENTITY, resp_b=IDENTITY, max_iter=80, tol=1e-6):
    """
    max f_a(raw_a(x)-da) * f_b(raw_b(x)-db)  over x in {0,1}^n, both args > 0.
    resp_a/resp_b = (f, logf, logf_prime) triples, e.g. from power_response(kappa) or
    saturating_response(K). resp=IDENTITY recovers plain maximum-Nash-welfare
    (dzero.nash_exact_d with da=db=0).
    """
    A, B, M = (np.asarray(v, float) for v in (A, B, M))
    n = len(A)
    c1, c2 = 1 - lam, theta * (1 - lam)
    ua, ub = c1 * A + c2 * B + lam * M, c2 * A + c1 * B + lam * M
    fa, logfa, logfa_p = resp_a
    fb, logfb, logfb_p = resp_b

    NV = n + 2; IA, IB = n, n + 1
    rows, rl, ru = [], [], []
    def add(pairs, lo, hi): rows.append(pairs); rl.append(lo); ru.append(hi)

    def tangent(side, yhat):
        if yhat <= 1e-12: return
        if side == "a":
            slope = logfa_p(yhat)
            rhs = logfa(yhat) - slope * yhat - slope * da
            add([(IA, 1.0)] + [(i, -slope * ua[i]) for i in range(n)], -np.inf, rhs)
        else:
            slope = logfb_p(yhat)
            rhs = logfb(yhat) - slope * yhat + slope * (ub.sum() - db)
            add([(IB, 1.0)] + [(i, slope * ub[i]) for i in range(n)], -np.inf, rhs)

    span = max(ua.sum() - da, ub.sum() - db)
    for g0 in np.geomspace(max(span * 1e-3, 1e-3), span, 10):
        tangent("a", g0); tangent("b", g0)

    c = np.zeros(NV); c[IA] = c[IB] = -1.0
    integ = np.zeros(NV); integ[:n] = 1
    lo = np.zeros(NV); hi = np.ones(NV); lo[IA] = lo[IB] = -60; hi[IA] = hi[IB] = 60
    def build():
        Am = lil_matrix((len(rows), NV))
        for k, pr in enumerate(rows):
            for cc, vv in pr: Am[k, cc] += vv
        return LinearConstraint(csr_matrix(Am), np.array(rl), np.array(ru))

    best = (-np.inf, None)
    for it in range(max_iter):
        res = milp(c=c, constraints=build(), integrality=integ, bounds=Bounds(lo, hi),
                   options=dict(time_limit=60, mip_rel_gap=0.0))
        if not res.success:
            return dict(status="fail", message=str(res.message))
        UB = res.x[IA] + res.x[IB]
        x = np.round(res.x[:n]).astype(bool)
        ya, yb = ua[x].sum() - da, ub[~x].sum() - db
        LB = (logfa(ya) + logfb(yb)) if (ya > 0 and yb > 0) else -np.inf
        if LB > best[0]: best = (LB, x.copy())
        added = 0
        gap = UB - best[0]
        if gap > tol:
            if ya > 0 and res.x[IA] - logfa(ya) > tol / 2: tangent("a", ya); added += 1
            if yb > 0 and res.x[IB] - logfb(yb) > tol / 2: tangent("b", yb); added += 1
        if added == 0 or gap <= tol:
            xb = best[1]; ya, yb = ua[xb].sum() - da, ub[~xb].sum() - db
            return dict(status="optimal", x=xb, y_a=float(ya), y_b=float(yb),
                        G_a=float(fa(ya)), G_b=float(fb(yb)), iters=it + 1,
                        gap=float(UB - best[0]))
    xb = best[1]; ya, yb = ua[xb].sum() - da, ub[~xb].sum() - db
    return dict(status="iterlimit", x=xb, y_a=float(ya), y_b=float(yb))


def brute_capacity(ua, ub, da, db, fa, fb):
    n = len(ua); best = (-np.inf, None)
    for mask in range(1 << n):
        x = np.array([(mask >> i) & 1 for i in range(n)], bool)
        ya, yb = ua[x].sum() - da, ub[~x].sum() - db
        if ya > 0 and yb > 0:
            val = fa(ya) * fb(yb)
            if val > best[0]: best = (val, x.copy())
    return best


if __name__ == "__main__":
    import pickle
    d = pickle.load(open("/tmp/z50.pkl", "rb"))
    Az, Bz, Mz, th, lam = d["Az"], d["Bz"], d["Mz"], d["th"], d["lam"]

    # validation 0: identity response reproduces plain maximum-Nash-welfare (d=0)
    r0 = nash_exact_capacity(Az, Bz, Mz, th, lam, 0., 0.)
    print(f"validation 0 (identity resp, d=0): G_a={r0['G_a']:.4f} G_b={r0['G_b']:.4f} "
          f"k={int(r0['x'].sum())} iters={r0['iters']} gap={r0['gap']:.2e}")

    # validation 1: brute force at n=12, power and saturating responses, several params
    rng = np.random.default_rng(5); ok = 0; tot = 0
    for _ in range(25):
        n = 12; M = rng.uniform(1, 10, n)
        A = M * rng.uniform(.02, .30, n); B = M * rng.uniform(.02, .30, n)
        if not (M >= np.maximum(A + th * B, B + th * A)).all(): continue
        c1, c2 = 1 - lam, th * (1 - lam)
        ua, ub = c1*A + c2*B + lam*M, c2*A + c1*B + lam*M
        for resp_a, resp_b, fa, fb in [
            (power_response(.6), power_response(.6), power_response(.6)[0], power_response(.6)[0]),
            (power_response(.4), power_response(.9), power_response(.4)[0], power_response(.9)[0]),
            (saturating_response(2.0), saturating_response(2.0),
             saturating_response(2.0)[0], saturating_response(2.0)[0]),
            (saturating_response(1.0), saturating_response(3.0),
             saturating_response(1.0)[0], saturating_response(3.0)[0]),
        ]:
            tot += 1
            s = nash_exact_capacity(A, B, M, th, lam, 0., 0., resp_a, resp_b)
            if s["status"] != "optimal": continue
            bp, bx = brute_capacity(ua, ub, 0., 0., fa, fb)
            sval = fa(s["y_a"]) * fb(s["y_b"])
            if abs(sval - bp) < 1e-6 * max(1, abs(bp)): ok += 1
            else: print(f"  MISMATCH solver={sval:.6f} brute={bp:.6f}")
    print(f"validation 1: solver matches brute force on {ok}/{tot} instances "
          f"(n=12, power + saturating, symmetric + asymmetric params)")
