"""fit.py -- marginal fits: lognormal vs double Pareto-lognormal, and the coarse CDF.

Everything is fitted in log space on strictly positive values, so "double Pareto-lognormal"
(dPlN, Reed 2001/2002; Reed & Jorgensen 2004) is exactly the **normal-Laplace** law in
`y = log x`:

    Y = nu + tau*Z + E1/alpha - E2/beta,     Z ~ N(0,1),  E1, E2 ~ Exp(1) independent

with, writing z = (y - nu)/tau and R(t) = Phi^c(t)/phi(t) (Mills' ratio),

    f(y) = alpha*beta/(alpha+beta) * phi(z) * [R(alpha*tau - z) + R(beta*tau + z)]
    F(y) = Phi(z) - phi(z) * [beta*R(alpha*tau - z) - alpha*R(beta*tau + z)] / (alpha+beta)
    E[Y] = nu + 1/alpha - 1/beta
    Var[Y] = tau^2 + 1/alpha^2 + 1/beta^2

alpha governs the upper (Pareto) tail, beta the lower one; as both go to infinity the law
converges to N(nu, tau^2), so it nests the lognormal exactly and the likelihood-ratio
comparison is a nested one.

Numerics: the Mills ratio is assembled in logs off `erfcx`, which is what keeps the density
finite forty standard deviations out --

    log R(t) = 0.5*log(pi/2) + log(erfcx(t/sqrt(2)))          t > -30
             = 0.5*t^2 + 0.5*log(2*pi)                        otherwise (erfcx overflows)

KS and AD are reported as **statistics only, never p-values**: the parameters are estimated
from the same sample, so the null distributions are not the tabulated ones.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import optimize
from scipy.special import erfcx, log_ndtr, ndtr
from scipy.interpolate import PchipInterpolator

LOG_SQRT_2PI = 0.5 * math.log(2.0 * math.pi)
HALF_LOG_PI_2 = 0.5 * math.log(math.pi / 2.0)
LOG_A_BOUNDS = (math.log(0.05), math.log(200.0))


# --------------------------------------------------------------------- primitives
def log_mills(t):
    """log R(t) = log(Phi^c(t)/phi(t)), stable for t in [-inf, +inf]."""
    t = np.asarray(t, dtype=float)
    out = np.empty_like(t)
    big = t > -30.0
    if np.any(big):
        out[big] = HALF_LOG_PI_2 + np.log(erfcx(t[big] / math.sqrt(2.0)))
    small = ~big
    if np.any(small):
        ts = t[small]
        out[small] = 0.5 * ts * ts + LOG_SQRT_2PI
    return out


def _logphi(z):
    return -0.5 * z * z - LOG_SQRT_2PI


def nl_logpdf(y, alpha, beta, nu, tau):
    z = (np.asarray(y, dtype=float) - nu) / tau
    return (math.log(alpha) + math.log(beta) - math.log(alpha + beta)
            + _logphi(z)
            + np.logaddexp(log_mills(alpha * tau - z), log_mills(beta * tau + z)))


def nl_cdf(y, alpha, beta, nu, tau):
    z = (np.asarray(y, dtype=float) - nu) / tau
    lp = _logphi(z)
    t1 = beta * np.exp(lp + log_mills(alpha * tau - z))
    t2 = alpha * np.exp(lp + log_mills(beta * tau + z))
    return np.clip(ndtr(z) - (t1 - t2) / (alpha + beta), 0.0, 1.0)


def nl_sf(y, alpha, beta, nu, tau):
    """Survival by the mirror identity  Y(a,b,nu,tau) =d -Y(b,a,-nu,tau)."""
    return nl_cdf(-np.asarray(y, dtype=float), beta, alpha, -nu, tau)


def nl_mean(alpha, beta, nu, tau):
    return nu + 1.0 / alpha - 1.0 / beta


def nl_var(alpha, beta, nu, tau):
    return tau * tau + 1.0 / (alpha * alpha) + 1.0 / (beta * beta)


def nl_ppf(u, alpha, beta, nu, tau, tol=1e-10):
    """Quantile by bisection on the CDF (monotone, so this is safe and needs no derivative)."""
    u = np.atleast_1d(np.asarray(u, dtype=float))
    sd = math.sqrt(nl_var(alpha, beta, nu, tau))
    lo = np.full(u.shape, nl_mean(alpha, beta, nu, tau) - 40.0 * sd)
    hi = np.full(u.shape, nl_mean(alpha, beta, nu, tau) + 40.0 * sd)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        c = nl_cdf(mid, alpha, beta, nu, tau)
        go = c < u
        lo = np.where(go, mid, lo)
        hi = np.where(go, hi, mid)
        if np.max(hi - lo) < tol:
            break
    return 0.5 * (lo + hi)


# -------------------------------------------------------------- goodness of fit
def ks_stat(y_sorted, cdf):
    n = y_sorted.size
    i = np.arange(1, n + 1, dtype=float)
    f = np.clip(cdf, 0.0, 1.0)
    return float(np.max(np.maximum(i / n - f, f - (i - 1.0) / n)))


def ad_stat(y_sorted, logcdf, logsf):
    n = y_sorted.size
    i = np.arange(1, n + 1, dtype=float)
    lc = np.clip(logcdf, -700.0, -1e-300)
    ls = np.clip(logsf[::-1], -700.0, -1e-300)
    return float(-n - np.sum((2.0 * i - 1.0) * (lc + ls)) / n)


# --------------------------------------------------------------------- lognormal
def fit_lognormal(y):
    y = np.asarray(y, dtype=float)
    n = y.size
    mu = float(y.mean())
    sigma = float(y.std(ddof=0)) or 1e-9
    ll = float(np.sum(-0.5 * ((y - mu) / sigma) ** 2 - math.log(sigma) - LOG_SQRT_2PI))
    ys = np.sort(y)
    zs = (ys - mu) / sigma
    return dict(family="lognormal", mu=mu, sigma=sigma, loglik=ll, n=int(n),
                ks=ks_stat(ys, ndtr(zs)),
                ad=ad_stat(ys, log_ndtr(zs), log_ndtr(-zs)))


# ---------------------------------------------------------------- normal-Laplace
def _hill_start(ys, frac):
    n = ys.size
    k = max(5, int(math.ceil(frac * n)))
    k = min(k, n - 1)
    top = ys[n - k:]
    bot = ys[:k]
    a = 1.0 / max(1e-9, float(np.mean(top - ys[n - k])))
    b = 1.0 / max(1e-9, float(np.mean(ys[k] - bot)))
    a = float(np.clip(a, 0.06, 190.0))
    b = float(np.clip(b, 0.06, 190.0))
    ybar = float(ys.mean())
    s = float(ys.std(ddof=0)) or 1e-9
    nu = ybar - 1.0 / a + 1.0 / b
    tau = math.sqrt(max(s * s - 1.0 / (a * a) - 1.0 / (b * b), (0.1 * s) ** 2))
    return a, b, nu, tau


def fit_normal_laplace(y, starts_frac=(0.05, 0.10, 0.20), maxiter=200):
    """L-BFGS-B MLE over (log alpha, log beta, nu, log tau) from Hill starts."""
    y = np.asarray(y, dtype=float)
    ys = np.sort(y)
    n = ys.size
    ybar = float(ys.mean())
    s = float(ys.std(ddof=0)) or 1e-9

    def nll(p):
        a, b, nu, tau = math.exp(p[0]), math.exp(p[1]), p[2], math.exp(p[3])
        lp = nl_logpdf(y, a, b, nu, tau)
        if not np.all(np.isfinite(lp)):
            return 1e18
        return -float(np.sum(lp))

    bounds = [LOG_A_BOUNDS, LOG_A_BOUNDS,
              (ybar - 5.0 * s, ybar + 5.0 * s),
              (math.log(0.01 * s), math.log(5.0 * s))]

    inits = []
    for f in starts_frac:
        a, b, nu, tau = _hill_start(ys, f)
        inits.append([math.log(a), math.log(b), nu, math.log(max(tau, 0.011 * s))])
    inits.append([math.log(10.0), math.log(10.0), ybar, math.log(max(s, 0.011 * s))])

    best, results = None, []
    for x0 in inits:
        x0 = [float(np.clip(v, lo, hi)) for v, (lo, hi) in zip(x0, bounds)]
        try:
            r = optimize.minimize(nll, x0, method="L-BFGS-B", bounds=bounds,
                                  options=dict(maxiter=maxiter, ftol=1e-11, gtol=1e-8))
        except Exception:
            continue
        if not np.isfinite(r.fun):
            continue
        results.append(float(-r.fun))
        if best is None or r.fun < best.fun:
            best = r
    if best is None:
        raise RuntimeError("normal-Laplace MLE failed from every start")

    a, b, nu, tau = math.exp(best.x[0]), math.exp(best.x[1]), best.x[2], math.exp(best.x[3])
    cdf = nl_cdf(ys, a, b, nu, tau)
    logc = np.log(np.clip(cdf, 1e-300, 1.0))
    logs = np.log(np.clip(nl_sf(ys, a, b, nu, tau), 1e-300, 1.0))
    spread = float(max(results) - min(results)) if len(results) > 1 else 0.0
    return dict(family="dpln", alpha=a, beta=b, nu=nu, tau=tau,
                loglik=float(-best.fun), n=int(n), converged=bool(best.success),
                n_starts=len(results), start_spread_ll=spread,
                mean_log=nl_mean(a, b, nu, tau), var_log=nl_var(a, b, nu, tau),
                ks=ks_stat(ys, cdf), ad=ad_stat(ys, logc, logs))


# ------------------------------------------------------------------- the marginal
def fit_marginal(x, name="", starts_frac=(0.05, 0.10, 0.20)):
    """Fit both families to the positive part of `x` and pick between them.

    prefer_dpln = converged and 2*dLL > 20 and AD_dpln <= AD_lognormal and min(a,b) < 20.
    """
    x = np.asarray(x, dtype=float)
    pos = x[np.isfinite(x) & (x > 0)]
    n_pos = pos.size
    out = dict(name=name, n=int(x.size), n_positive=int(n_pos),
               p_positive=float(n_pos) / max(1, x.size))
    if n_pos < 50:
        out.update(prefer_dpln=False, note="too few positive values to fit")
        return out
    y = np.log(pos)
    ln = fit_lognormal(y)
    try:
        dp = fit_normal_laplace(y, starts_frac=starts_frac)
    except Exception as e:                                    # keep the lognormal result
        out.update(lognormal=ln, dpln=None, prefer_dpln=False,
                   note="dPlN fit failed: %s" % type(e).__name__)
        return out
    dll = dp["loglik"] - ln["loglik"]
    prefer = bool(dp["converged"] and 2.0 * dll > 20.0 and dp["ad"] <= ln["ad"]
                  and min(dp["alpha"], dp["beta"]) < 20.0)
    out.update(lognormal=ln, dpln=dp, delta_loglik=float(dll),
               lr_stat=float(2.0 * dll), prefer_dpln=prefer,
               note="ks/ad are statistics only; parameters were estimated from the same "
                    "sample, so tabulated p-values do not apply")
    return out


def marginal_ppf(mfit, u):
    """Quantile function of the *selected* fitted family, in the original (x) units."""
    u = np.asarray(u, dtype=float)
    if mfit.get("prefer_dpln") and mfit.get("dpln"):
        d = mfit["dpln"]
        return np.exp(nl_ppf(u, d["alpha"], d["beta"], d["nu"], d["tau"]))
    ln = mfit["lognormal"]
    from scipy.special import ndtri
    return np.exp(ln["mu"] + ln["sigma"] * ndtri(np.clip(u, 1e-12, 1 - 1e-12)))


# -------------------------------------------------------------------- coarse CDF
def coarse_cdf(x, n_bins=200, min_support=20, tail_dominance=0.5):
    """Equal-probability bins over the positive values, with a tail-dominance merge.

    The exported summary of a bin is its **mean**.  If one ZCTA supplies half or more of the
    top bin's mass, that mean is close to a single confidential number, so the top bin is
    merged downward until `max(bin)/sum(bin) < tail_dominance`.  Bin counts are also floored
    at `min_support` by reducing the number of bins.
    """
    x = np.asarray(x, dtype=float)
    pos = np.sort(x[np.isfinite(x) & (x > 0)])
    n = pos.size
    if n == 0:
        return dict(n=0, n_bins=0, bin_p=[], bin_mean=[], n_bins_merged=0)
    n_bins = int(max(1, min(n_bins, n // max(1, min_support))))
    edges = np.linspace(0, n, n_bins + 1).astype(int)
    bins = [pos[edges[i]:edges[i + 1]] for i in range(n_bins)]
    bins = [b for b in bins if b.size]

    merged = 0
    while len(bins) > 1:
        top = bins[-1]
        tot = float(top.sum())
        if tot <= 0 or float(top.max()) / tot < tail_dominance:
            break
        bins[-2] = np.concatenate([bins[-2], top])
        bins.pop()
        merged += 1
    while len(bins) > 1 and bins[-1].size < min_support:
        bins[-2] = np.concatenate([bins[-2], bins[-1]])
        bins.pop()
        merged += 1

    counts = np.array([b.size for b in bins], dtype=float)
    means = np.array([b.mean() for b in bins], dtype=float)
    share = float(bins[-1].max() / max(bins[-1].sum(), 1e-30))
    return dict(n=int(n), n_bins=int(len(bins)),
                bin_p=[float(c / n) for c in counts],
                bin_mean=[float(m) for m in means],
                n_bins_merged=int(merged),
                min_bin_count=int(counts.min()),
                top_bin_share=share,
                # False only when a single value dominates the *entire* sample, so that
                # merging every bin together still leaves it above the threshold.  Merging
                # has no further lever there; the run reports it rather than pretending.
                tail_dominance_resolved=bool(share < tail_dominance))


def quantile_fn_from_coarse(block, tail_fit=None):
    """Monotone PCHIP through (cumulative bin-midpoint probability, log bin mean).

    Outside the first and last bin midpoints the fitted parametric family takes over, so the
    tails of the synthetic draw come from the fit rather than from an extrapolated spline.
    Returns a callable u (in (0,1)) -> x.
    """
    p = np.asarray(block["bin_p"], dtype=float)
    m = np.asarray(block["bin_mean"], dtype=float)
    if p.size == 0:
        return lambda u: np.zeros_like(np.asarray(u, dtype=float))
    cum = np.cumsum(p)
    mid = cum - 0.5 * p
    order = np.argsort(mid)
    mid, m = mid[order], m[order]
    m = np.maximum.accumulate(np.maximum(m, 1e-300))          # enforce monotone bin means
    if mid.size == 1:
        const = float(m[0])
        return lambda u: np.full(np.shape(u), const, dtype=float)
    spline = PchipInterpolator(mid, np.log(m), extrapolate=False)
    lo, hi = float(mid[0]), float(mid[-1])

    def q(u):
        u = np.atleast_1d(np.asarray(u, dtype=float))
        out = np.empty_like(u)
        inner = (u >= lo) & (u <= hi)
        out[inner] = np.exp(spline(u[inner]))
        outer = ~inner
        if np.any(outer):
            if tail_fit is not None:
                out[outer] = marginal_ppf(tail_fit, np.clip(u[outer], 1e-9, 1 - 1e-9))
            else:
                out[outer] = np.exp(np.interp(u[outer], mid, np.log(m)))
        return np.maximum(out, 0.0)

    return q
