"""U1-cert verification A -- the instance numbers, recomputed from scratch.

Independent of `docs/artifacts/U1-cert/{eg,instance_numbers}.py`: the utilities are rebuilt
from the raw JSON columns of `instance_descaled.json.gz` (not through `td.instance`), the
delivered value is recomputed by hand from `draw.csv` (not through `channel.gain_matrix`),
and the EG bracket is evaluated with `math.fsum` and with 50-digit mpmath so that a claimed
bracket width of 1.3e-13 nats cannot be an artefact of float summation order.

Two solvers are run for EG_S: proportional response (own implementation, own init) and
L-BFGS-B on a softmax parametrisation (a genuinely different algorithm).  Neither is trusted:
what is *reported* is the pair (primal at a feasible X, dual at a strictly positive p), each
checkable in O(nk) arithmetic, which brackets EG_S whatever the algorithms did.

Run:  /Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/U1-cert/verify_instance.py
from /Users/ntlee/projects/td/.claude/worktrees/A1 .
"""
from __future__ import annotations

import csv
import gzip
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[3]
INST = ROOT / "instance_descaled.json.gz"
DRAW = ROOT / "battery/results/draw_k13_20260901"
LAM, THETA = 0.30, 0.40
FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'ok ' if ok else 'FAIL'}] {name}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


# ------------------------------------------------------------------ raw instance, by hand
def raw_utilities(filler: str = "theta"):
    with gzip.open(INST, "rt", encoding="utf-8") as fh:
        obj = json.load(fh)
    nodes = obj["nodes"]
    zips = list(nodes["z"])
    M = np.array([float(v) for v in nodes["m_rel"]], float)
    shares = nodes["share"]
    free_sh = nodes.get("share_free") or [0.0] * len(zips)
    reps = sorted({r for sh in shares for r in sh})
    n, m = len(zips), len(reps)
    ir = {r: i for i, r in enumerate(reps)}
    S = np.zeros((n, m))
    for z, sh in enumerate(shares):
        for r, s in sh.items():
            S[z, ir[r]] = float(s) * M[z]
    S_free = np.array([float(f or 0.0) for f in free_sh]) * M
    c1, c2 = 1.0 - LAM, THETA * (1.0 - LAM)
    c_free = {"theta": c2, "full": c1, "opportunity": LAM}[filler]
    common = c2 * S.sum(axis=1) + c_free * S_free + LAM * M
    U = common[:, None] + (c1 - c2) * S            # u_i(z), unmasked
    return zips, reps, M, S, S_free, U


# ------------------------------------------------------------------------- EG primal/dual
def primal_fsum(U, X):
    """sum_i log g_i with exact (fsum) accumulation of every g_i."""
    n, k = U.shape
    g = np.array([math.fsum(U[z, i] * X[z, i] for z in range(n)) for i in range(k)])
    return math.fsum(math.log(v) for v in g), g


def dual_fsum(U, p):
    """sum_z p_z - k + sum_i log max_z (u_iz/p_z).  Upper bound on EG for every p > 0."""
    assert np.all(p > 0)
    k = U.shape[1]
    r = (U / p[:, None]).max(axis=0)
    return math.fsum(p.tolist()) - k + math.fsum(math.log(v) for v in r), r


def prop_response(U, iters=200_000, seed=0):
    """Proportional response, own implementation, randomised (not uniform) initialisation."""
    n, k = U.shape
    rng = np.random.default_rng(seed)
    b = rng.random((n, k)) + 0.1
    b /= b.sum(axis=0, keepdims=True)             # each buyer's budget is 1
    for _ in range(iters):
        p = b.sum(axis=1)
        X = b / p[:, None]
        g = (U * X).sum(axis=0)
        b = (U * X) / g[None, :]
    p = b.sum(axis=1)
    X = b / p[:, None]
    return X, p


def lbfgs_softmax(U, seed=1):
    """max sum_i log g_i over the product of simplices, by L-BFGS-B on x = softmax(theta)."""
    n, k = U.shape
    rng = np.random.default_rng(seed)

    def negf(th):
        T = th.reshape(n, k)
        T = T - T.max(axis=1, keepdims=True)
        E = np.exp(T)
        Ssum = E.sum(axis=1, keepdims=True)
        X = E / Ssum
        g = (U * X).sum(axis=0)
        f = np.log(g).sum()
        # dF/dx_zi = u_zi / g_i ; softmax jacobian
        Gx = U / g[None, :]
        dot = (Gx * X).sum(axis=1, keepdims=True)
        grad = X * (Gx - dot)
        return -f, -grad.ravel()

    th0 = 0.1 * rng.standard_normal(n * k)
    res = minimize(negf, th0, jac=True, method="L-BFGS-B",
                   options=dict(maxiter=40_000, maxfun=60_000, ftol=1e-18, gtol=1e-14))
    T = res.x.reshape(n, k)
    T = T - T.max(axis=1, keepdims=True)
    E = np.exp(T)
    return E / E.sum(axis=1, keepdims=True)


def attack_integral(U, M, seed=7, restarts=6, sweeps=60):
    """Greedy/local-search maximiser of sum_i log g_i over *integral* assignments.

    A falsification attempt against P1: if any integral coverage with im sigma = S beat
    EG_S, P1 would be refuted on the real instance.  Starts from random labellings and from
    the argmax-utility labelling, then sweeps single-zip moves accepting any improvement.
    """
    n, k = U.shape
    rng = np.random.default_rng(seed)
    best = -np.inf
    for r in range(restarts):
        lab = (U / M[:, None]).argmax(axis=1) if r == 0 else rng.integers(0, k, n)
        g = np.zeros(k)
        for z in range(n):
            g[lab[z]] += U[z, lab[z]]
        if (g <= 0).any():
            continue
        for _ in range(sweeps):
            moved = 0
            for z in rng.permutation(n):
                a = lab[z]
                if g[a] - U[z, a] <= 0:
                    continue
                base = math.log(g[a] - U[z, a]) - math.log(g[a])
                gains = np.log(g + U[z]) - np.log(g)
                gains[a] = -np.inf
                j = int(np.argmax(gains + base))
                if gains[j] + base > 1e-15:
                    g[a] -= U[z, a]
                    g[j] += U[z, j]
                    lab[z] = j
                    moved += 1
            if not moved:
                break
        best = max(best, float(np.log(g).sum()))
    return best


def main() -> int:
    print("=" * 78)
    print("A. instance rebuilt from raw JSON columns")
    zips, reps, M, S, S_free, U_all = raw_utilities("theta")
    n, m = len(zips), len(reps)
    T = math.fsum(M.tolist())
    print(f"  n = {n}, reps = {m}, T = M(Z) = {T:.6f}")
    check("n = 1229", n == 1229)
    check("reps = 111", m == 111)
    check("T = 2745.611187", abs(T - 2745.611187) < 5e-7, f"{T!r}")
    check("min_z M_z > 0 (P1b)", M.min() > 0, f"min M_z = {M.min():.6e}")
    check("min_z M_z = 1.80577e-3", abs(M.min() - 1.80577e-3) < 5e-9, f"{M.min():.8e}")

    ratio = (U_all / M[:, None]).max()
    print(f"  max_(i,z) u_i(z)/M_z, filler='theta' = {ratio:.9f}")
    check("headroom holds to export rounding (<= 1 + 4.3e-7)", ratio <= 1 + 4.3e-7,
          f"excess = {ratio - 1:.3e}")
    check("strong headroom u_i(z) <= M_z FAILS on the instance (69 zips)", ratio > 1.0)
    n_over = int((U_all > M[:, None] + 0).any(axis=1).sum())
    print(f"  zips with some u_i(z) > M_z: {n_over}")
    _, _, _, _, _, U_full = raw_utilities("full")
    ratio_full = (U_full / M[:, None]).max()
    print(f"  max u/M, filler='full' = {ratio_full:.7f}  (headroom FAILS)")
    check("filler='full' ratio = 1.2948988", abs(ratio_full - 1.2948988) < 5e-8,
          f"{ratio_full!r}")

    k = 13
    ceiling = k * math.log(T / k)
    print(f"  k log(T/k) = {ceiling:.10f}")
    check("ceiling = 69.5865251441", abs(ceiling - 69.5865251441) < 5e-10, f"{ceiling!r}")

    print("=" * 78)
    print("B. V(delivered) recomputed by hand from draw.csv")
    with open(DRAW / "draw.csv") as fh:
        to_d = {row["zip"]: row["district"] for row in csv.DictReader(fh)}
    metrics = json.loads((DRAW / "metrics.json").read_text())
    assign = metrics["winner"]["assignment"]           # district -> rep
    iz = {z: i for i, z in enumerate(zips)}
    ir = {r: i for i, r in enumerate(reps)}
    districts = sorted(assign)
    S13 = [assign[d] for d in districts]
    check("13 distinct delivered reps", len(set(S13)) == 13)
    parts = {d: [] for d in districts}
    for z, d in to_d.items():
        parts[d].append(iz[z])
    check("draw covers every zip exactly once", sum(len(v) for v in parts.values()) == n
          and len(to_d) == n)
    terms = []
    for d in districts:
        i = ir[assign[d]]
        terms.append(math.fsum(U_all[z, i] for z in parts[d]))
    V = math.fsum(math.log(t) for t in terms)
    print(f"  V(delivered) = {V!r}")
    check("V = metrics winner.stage2_value to 1e-12",
          abs(V - metrics["winner"]["stage2_value"]) < 1e-12,
          f"delta = {V - metrics['winner']['stage2_value']:.3e}")
    check("V = 59.9374697984", abs(V - 59.9374697984) < 5e-10)

    Md = np.array([math.fsum(M[z] for z in parts[d]) for d in districts])
    spread_M = (Md.max() - Md.min()) / (T / k)
    g_del = np.array(terms)
    spread_g = (g_del.max() - g_del.min()) / g_del.mean()
    print(f"  M-spread {100*spread_M:.4f}%   g-spread {100*spread_g:.2f}%   "
          f"ratio {spread_g/spread_M:.2f}")
    check("M-spread = 0.7813%", abs(100 * spread_M - 0.7813) < 5e-4)
    check("g-spread = 60.65%", abs(100 * spread_g - 60.65) < 5e-3)
    check("min_i g_i delivered = 81.869", abs(g_del.min() - 81.869) < 5e-4,
          f"{g_del.min():.6f}")

    print("=" * 78)
    print("C. EG_{S13}: bracket by weak duality, two independent solvers")
    cols = [ir[r] for r in S13]
    U = np.ascontiguousarray(U_all[:, cols])
    check("U > 0 everywhere (P1b: u_i >= lam M_z > 0)", bool((U > 0).all()),
          f"min u = {U.min():.6e}, lam*min M = {LAM*M.min():.6e}")
    check("u_i(z) >= lam M_z for all i,z", bool((U >= LAM * M[:, None] - 1e-15).all()))

    X1, p1 = prop_response(U, iters=200_000, seed=0)
    # --- feasibility of X1, checked, not assumed
    rowsum = X1.sum(axis=1)
    check("X (prop-response) >= 0", bool((X1 >= 0).all()))
    check("X row sums = 1 to 1e-14", float(np.abs(rowsum - 1).max()) < 1e-14,
          f"max |rowsum-1| = {np.abs(rowsum-1).max():.2e}")
    check("prices p > 0", bool((p1 > 0).all()), f"min p = {p1.min():.3e}")

    pr, g_star = primal_fsum(U, X1)
    du, _ = dual_fsum(U, p1)
    width = du - pr
    print(f"  primal (feasible X)  = {pr!r}")
    print(f"  dual   (p > 0)       = {du!r}")
    print(f"  bracket width        = {width:.4e} nats")
    check("dual >= primal (weak duality holds on the returned pair)", width >= 0)
    check("EG bracket width <= 1.3e-13", width <= 1.3e-13, f"{width:.3e}")
    check("EG_{S13} = 60.6974156139 (primal)", abs(pr - 60.6974156139) < 5e-10, f"{pr!r}")
    check("EG_{S13} = 60.6974156139 (dual)", abs(du - 60.6974156139) < 5e-10, f"{du!r}")

    # mpmath at 50 digits: is the bracket real or a float-summation artefact?
    try:
        from mpmath import mp, mpf, log as mlog
        mp.dps = 50
        gm = [sum((mpf(float(U[z, i])) * mpf(float(X1[z, i])) for z in range(n)), mpf(0))
              for i in range(k)]
        pr_hi = sum((mlog(v) for v in gm), mpf(0))
        rr = [max((mpf(float(U[z, i])) / mpf(float(p1[z])) for z in range(n)))
              for i in range(k)]
        du_hi = sum((mpf(float(v)) for v in p1), mpf(0)) - k + sum((mlog(v) for v in rr),
                                                                  mpf(0))
        print(f"  mpmath(50): primal = {pr_hi}\n              dual   = {du_hi}")
        print(f"  mpmath bracket width = {float(du_hi - pr_hi):.4e}")
        check("mpmath bracket width also <= 1.3e-13 and >= 0",
              0 <= float(du_hi - pr_hi) <= 1.3e-13)
        check("float primal agrees with mpmath primal to 1e-12",
              abs(float(pr_hi) - pr) < 1e-12, f"delta {float(pr_hi)-pr:.2e}")
    except ImportError:
        print("  (mpmath unavailable -- skipped the high-precision recheck)")

    X2 = lbfgs_softmax(U, seed=1)
    pr2, _ = primal_fsum(U, X2)
    print(f"  independent solver (L-BFGS-B on softmax): primal = {pr2!r}")
    check("second solver lands inside the bracket (<= dual)", pr2 <= du + 1e-12,
          f"dual - primal2 = {du - pr2:.3e}")
    check("second solver is within 1e-2 of the bracket from below", du - pr2 < 1e-2,
          f"gap {du - pr2:.3e}")

    print(f"  EG - V = {du - V!r}  (upper) / {pr - V!r} (lower)")
    check("EG - V = 0.7599458154", abs(pr - V - 0.7599458154) < 5e-10)
    check("ceiling - EG = 8.8891095303", abs(ceiling - pr - 8.8891095303) < 5e-10)
    check("ceiling - V = 9.6490553457", abs(ceiling - V - 9.6490553457) < 5e-10)
    tf = (ceiling - V) / (du - V)
    check("tightness factor = 12.6970", abs(tf - 12.6970) < 5e-5, f"{tf:.6f}")
    check("EG < ceiling (P1c bites on the instance)", pr < ceiling)

    # P1c's corrected form at filler='full', where headroom fails
    U_full13 = U_full[:, cols]
    nu = (U_full13 / M[:, None]).max(axis=0)
    corr = float(np.log(nu).sum())
    print(f"  filler='full': sum_i log nu_i = {corr:.6f} nats (P1c correction)")
    coarse_full = k * math.log(ratio_full)
    print(f"  filler='full': k log(nu_max)      = {coarse_full:.6f} nats (the COARSE form)")
    nu_all_full = (U_full / M[:, None]).max(axis=0)
    best13 = float(np.sort(np.log(nu_all_full))[-13:].sum())
    print(f"  filler='full': max_S sum_(i in S) log nu_i over all 111 reps = {best13:.6f}")
    check("model's +3.360 is k log(nu_max), not sum_i log nu_i at S13",
          abs(coarse_full - 3.360) < 5e-3, f"coarse {coarse_full:.4f} vs sharp {corr:.4f}")
    check("sharp per-agent correction at S13 is an order below the coarse one",
          corr < 0.30)
    check("even max over staff sets of sum log nu_i is below the coarse 3.360",
          best13 < coarse_full, f"best13 = {best13:.4f}")
    nu_t = (U / M[:, None]).max(axis=0)
    corr_t = float(np.log(nu_t).sum())
    print(f"  filler='theta': sum_i log nu_i = {corr_t:.4e} nats")
    coarse_t = k * math.log(ratio)
    print(f"  filler='theta': k log(nu_max)     = {coarse_t:.4e} nats (the COARSE form)")
    check("model's 5.46e-6 is k log(nu_max)", abs(coarse_t - 5.46e-6) < 5e-9,
          f"{coarse_t:.4e}")
    check("coarse theta-slack above tier 1 (1e-8), below tier 2 (5e-3)",
          1e-8 < coarse_t < 5e-3)
    check("EG <= k log(T/k) + k log(nu_max) (coarse P1c, filler=theta)",
          du <= ceiling + coarse_t)
    # and the *corrected* ceiling does bound EG even with the rounding excess
    check("EG <= k log(T/k) + sum_i log nu_i (corrected P1c, filler=theta)",
          du <= ceiling + corr_t)

    print("=" * 78)
    print("D. ATTACK: try to find an integral coverage on S13 that beats EG_{S13}")
    best = attack_integral(U, M, seed=7, restarts=6)
    print(f"  best integral V found by local search = {best!r}")
    check("no integral coverage found above EG (P1 not falsified)", best <= du + 1e-12,
          f"EG - best = {du - best:.6e}")
    check("the attack does beat the delivered draw (search is not toothless)", best > V,
          f"best - V = {best - V:.4f}")

    print("=" * 78)
    print("FAILURES:", "none" if not FAILURES else FAILURES)
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    sys.exit(main())
