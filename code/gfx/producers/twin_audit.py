"""
gfx/producers/twin_audit.py -- the twin-export privacy-audit figure (PLAN.md Part D).

`twin_stats.json` (PLAN.md C.2) is produced by `tools/twin_export/` (U3).  This reader
targets the schema U3 actually emits (`tools/twin_export/stats.py::blocks`,
`check.py::twin_check`, `audit.py::audit`, reconciled 2026-08-29, U9) rather than an
earlier provisional guess -- see the per-panel docstrings below for the exact keys.  It
stays deliberately loose: every panel looks up its block by name and renders a
"not available" placeholder if the block, or a key inside it, is missing, so each panel is
independently degradable and the whole figure still renders on a partial or empty dict.

Panels: fitted-vs-empirical marginal for M (`marginals.M.coarse_cdf.{bin_p,bin_mean}`,
lognormal/dPlN overlays computed from `marginals.M.{lognormal,dpln}`) · share-by-decile
curves with +/-1sd bands (`conditional.{mean,sd}_log_{A,B}_over_M`) · Moran's I / hop-1
rank correlation bars per field (`spatial.moran_{M,A,B}`,
`spatial.rank_corr_by_hop_{M,A,B}`) · individual-vs-neighbourhood privacy sign-off bars
(`audit.fields.<M|A|B>.{pearson_log,corr_3hop_neighbourhood}`) · territory/census real-vs-
twin bars from `twin_check.rows` (there is no per-bin size histogram in the export, so this
is a bar-per-key comparison, not a histogram) · a text summary box (`twin_check.passed`,
`audit.verdict`, `graph`).

Usage:
    python -m gfx.producers.twin_audit <twin_stats.json> --out <png>
"""
from __future__ import annotations

import math
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from scipy.special import erfcx, ndtr, ndtri

from .. import charts, style
from . import _common

FIELDS = ("M", "A", "B")


def _placeholder(ax, msg, title):
    ax.axis("off")
    ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=8, transform=ax.transAxes,
            wrap=True)
    ax.set_title(title, fontsize=8, loc="left")


# ------------------------------------------------------------- dPlN quantile (duplicated)
# The normal-Laplace (dPlN, Reed & Jorgensen 2004) CDF and its bisection inverse, duplicated
# in miniature from `tools/twin_export/fit.py::nl_cdf`/`nl_ppf` -- gfx never imports
# tools/twin_export (that package is self-contained by design; see `_common.utilities` for
# the same convention with the solver module).  Only used to draw the fitted overlay curve.
def _log_mills(t):
    t = np.asarray(t, dtype=float)
    out = np.empty_like(t)
    big = t > -30.0
    out[big] = 0.5 * math.log(math.pi / 2.0) + np.log(erfcx(t[big] / math.sqrt(2.0)))
    out[~big] = 0.5 * t[~big] * t[~big] + 0.5 * math.log(2.0 * math.pi)
    return out


def _dpln_cdf(y, alpha, beta, nu, tau):
    z = (np.asarray(y, dtype=float) - nu) / tau
    lphi = -0.5 * z * z - 0.5 * math.log(2.0 * math.pi)
    t1 = beta * np.exp(lphi + _log_mills(alpha * tau - z))
    t2 = alpha * np.exp(lphi + _log_mills(beta * tau + z))
    return np.clip(ndtr(z) - (t1 - t2) / (alpha + beta), 0.0, 1.0)


def _dpln_ppf(p, alpha, beta, nu, tau, n_iter=60):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1.0 - 1e-6)
    sd = math.sqrt(tau * tau + 1.0 / alpha ** 2 + 1.0 / beta ** 2)
    mean = nu + 1.0 / alpha - 1.0 / beta
    lo = np.full_like(p, mean - 40.0 * sd)
    hi = np.full_like(p, mean + 40.0 * sd)
    for _ in range(n_iter):
        mid = 0.5 * (lo + hi)
        go = _dpln_cdf(mid, alpha, beta, nu, tau) < p
        lo = np.where(go, mid, lo)
        hi = np.where(go, hi, mid)
    return 0.5 * (lo + hi)


def _lognorm_ppf(p, mu, sigma):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1.0 - 1e-6)
    return mu + sigma * ndtri(p)


# --------------------------------------------------------------------------- panels
def _panel_marginal(ax, stats, var="M"):
    """Empirical coarse CDF (`bin_p`/`bin_mean`, raw scale) vs. the lognormal/dPlN fits
    (`lognormal`/`dpln`, fitted in log space -- overlays are exponentiated back)."""
    m = (stats.get("marginals") or {}).get(var)
    cdf = (m or {}).get("coarse_cdf")
    if not m or not cdf or not cdf.get("bin_p") or not cdf.get("bin_mean"):
        return _placeholder(ax, f"no marginals.{var}.coarse_cdf", f"{var} marginal fit")
    # `bin_p` is each bin's PROBABILITY MASS (count/n, `fit.py::coarse_cdf`), not a
    # cumulative position -- with ~200 equal-mass bins every entry is close to 1/200, so
    # plotting it directly as x clusters every point (and tick label) on top of itself.
    # The bins are already in ascending value order (built from a sorted array), so the
    # cumulative mid-bin mass is the quantile position each bin's mean actually sits at.
    bp = np.asarray(cdf["bin_p"], float)
    emp = np.asarray(cdf["bin_mean"], float)
    p = np.cumsum(bp) - 0.5 * bp
    ax.plot(p, emp, color=style.PALETTE["neutral"], lw=1.4, label="empirical")

    preferred = "dpln" if m.get("prefer_dpln") else "lognormal"
    ln = m.get("lognormal")
    if ln and ln.get("mu") is not None and ln.get("sigma"):
        ys = np.exp(_lognorm_ppf(p, float(ln["mu"]), float(ln["sigma"])))
        lab = "lognormal*" if preferred == "lognormal" else "lognormal"
        ax.plot(p, ys, "--", color=style.PALETTE["A"], lw=1.1, label=lab)
    dp = m.get("dpln")
    if dp and all(dp.get(k) is not None for k in ("alpha", "beta", "nu", "tau")):
        try:
            ys = np.exp(_dpln_ppf(p, float(dp["alpha"]), float(dp["beta"]),
                                  float(dp["nu"]), float(dp["tau"])))
            lab = "dpln*" if preferred == "dpln" else "dpln"
            ax.plot(p, ys, "-", color=style.PALETTE["B"], lw=1.1, label=lab)
        except (ValueError, ZeroDivisionError, FloatingPointError):
            pass                          # a degenerate fit must not break the figure

    ax.set_ylim(bottom=0)              # M/A/B are nonnegative -- no phantom negative tick
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.set_xlabel("probability", fontsize=8)
    ax.set_ylabel(var, fontsize=8)
    ax.set_title(f"{var} marginal (fit vs. empirical; * = preferred)", fontsize=7,
                loc="left")
    ax.legend(fontsize=6, frameon=False)


def _panel_share_curves(ax, stats):
    """Decile ladders of the demeaned log share, `conditional.mean_log_{A,B}_over_M` with
    a +/-1sd band from `conditional.sd_log_{A,B}_over_M` -- U3's residual fit, the one
    `synth.calibrate`'s `share_curves` override is built from."""
    cond = stats.get("conditional") or {}
    have_any = False
    for name in ("A", "B"):
        mu = cond.get(f"mean_log_{name}_over_M")
        sd = cond.get(f"sd_log_{name}_over_M")
        if not mu:
            continue
        have_any = True
        muv = np.array([np.nan if v is None else v for v in mu], float)
        sdv = (np.array([0.0 if v is None else v for v in sd], float)
               if sd else np.zeros_like(muv))
        d = np.arange(1, len(muv) + 1)
        color = style.PALETTE[name]
        charts.sweep_curve(ax, d, muv, band=(muv - sdv, muv + sdv), color=color, label=name,
                           xlabel="M decile", ylabel="mean log(share) [decile-demeaned]")
    if not have_any:
        return _placeholder(ax, "no conditional.mean_log_A_over_M / mean_log_B_over_M",
                           "share by M-decile")
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.set_title("share-by-decile curves", fontsize=8, loc="left")


def _panel_spatial(ax, stats):
    """Moran's I and hop-1 rank correlation, one bar pair per field, from
    `spatial.moran_{M,A,B}` and `spatial.rank_corr_by_hop_{M,A,B}` (index 0 = hop 1)."""
    sp = stats.get("spatial") or {}
    labels = [f for f in FIELDS if (f"moran_{f}" in sp or f"rank_corr_by_hop_{f}" in sp)]
    if not labels:
        return _placeholder(ax, "no spatial.moran_{M,A,B} / spatial.rank_corr_by_hop_{M,A,B}",
                           "Moran's I / hop-1 rank correlation")
    series = {}
    if any(f"moran_{f}" in sp for f in labels):
        series["Moran's I"] = [sp.get(f"moran_{f}", np.nan) for f in labels]
    if any(f"rank_corr_by_hop_{f}" in sp for f in labels):
        def hop1(f):
            v = sp.get(f"rank_corr_by_hop_{f}")
            return v[0] if v else np.nan
        series["hop-1 rank corr"] = [hop1(f) for f in labels]
    charts.grouped_bars(ax, labels, series, ylabel="value",
                        title="Moran's I / hop-1 rank correlation")


def _panel_privacy(ax, stats):
    """The privacy sign-off: `audit.fields.<M|A|B>.pearson_log` (individual level, must be
    weak) vs. `audit.fields.<M|A|B>.corr_3hop_neighbourhood` (neighbourhood level, must be
    strong)."""
    flds = ((stats.get("audit") or {}).get("fields")) or {}
    labels = [f for f in FIELDS if f in flds]
    if not labels:
        return _placeholder(ax, "no audit.fields.{M,A,B}",
                           "privacy sign-off: individual vs. neighbourhood corr")
    series = {
        "individual (pearson, log)": [flds[f].get("pearson_log", np.nan) for f in labels],
        "3-hop neighbourhood": [flds[f].get("corr_3hop_neighbourhood", np.nan)
                                for f in labels],
    }
    charts.grouped_bars(ax, labels, series, ylabel="correlation",
                        title="privacy sign-off: individual vs. neighbourhood corr")


# the twin_check.rows keys this panel looks for -- census/territory structure, real vs
# twin, with a short display label
_CENSUS_ROWS = (
    ("territories.census_0.02.share_1_1", "1-1 share"),
    ("territories.census_0.02.n_components", "n comps"),
    ("territories.misalignment_jaccard", "Jaccard"),
    ("territories.zips_per_rep_a_q[1]", "zips/rep"),
)


def _panel_census_hist(ax, stats):
    """Real vs. twin territory/census structure, read off `twin_check.rows` (each row is
    `{key, real, predicted, twin, tol, ok}`).  There is no per-bin pair-size histogram in
    the export -- this is a bar-per-key comparison instead, dropped to a placeholder if
    none of the expected rows are present."""
    rows = {r.get("key"): r for r in (stats.get("twin_check") or {}).get("rows") or []}
    present = [(k, lab) for k, lab in _CENSUS_ROWS if k in rows and rows[k].get("real") is not None
              and rows[k].get("twin") is not None]
    if not present:
        return _placeholder(ax, "no twin_check.rows for the territories/census keys",
                           "census/territories: real vs. twin")
    x = np.arange(len(present))
    real = [rows[k]["real"] for k, _ in present]
    twin = [rows[k]["twin"] for k, _ in present]
    ax.bar(x - 0.18, real, 0.36, color=style.PALETTE["neutral"], label="real")
    ax.bar(x + 0.18, twin, 0.36, color=style.PALETTE["A"], label="twin")
    ax.set_xticks(x, [lab for _, lab in present], fontsize=6, rotation=0, ha="center")
    ax.set_ylabel("value", fontsize=8)
    ax.set_title("census/territories: real vs. twin", fontsize=8, loc="left")
    ax.legend(fontsize=6, frameon=False)


def _panel_text(ax, stats):
    ax.axis("off")
    tc = stats.get("twin_check") or {}
    au = stats.get("audit") or {}
    g = stats.get("graph") or {}
    lines = []
    if "passed" in tc:
        lines.append(f"twin_check.passed = {tc['passed']}")
    if "verdict" in au:
        lines.append(f"audit.verdict:")
        lines.append(f"  {au['verdict']}")
    for k in ("n", "m", "n_components", "n_articulation_points", "state_cross_share"):
        if k in g:
            v = g[k]
            lines.append(f"graph.{k} = {v:.3g}" if isinstance(v, float) else f"graph.{k} = {v}")
    if not lines:
        lines = ["no twin_check / audit / graph blocks present"]
    ax.text(0.0, 1.0, "\n".join(lines), family="monospace", fontsize=7, va="top",
           transform=ax.transAxes)
    ax.set_title("summary", fontsize=8, loc="left")


def build(stats: dict) -> plt.Figure:
    style.use_rc()
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    _panel_marginal(axes[0, 0], stats, "M")
    _panel_share_curves(axes[0, 1], stats)
    _panel_spatial(axes[0, 2], stats)
    _panel_privacy(axes[1, 0], stats)
    _panel_census_hist(axes[1, 1], stats)
    _panel_text(axes[1, 2], stats)
    fig.suptitle("twin export: privacy audit", fontsize=11)
    # extra vertical padding: the top-row panels' y-axis auto-margin can otherwise place a
    # tick label close enough to the bottom-row panel above/below it to overlap on some
    # data draws (varying value ranges across real twin_stats.json instances)
    style.tight_layout(fig, h_pad=4.5)
    return fig


def main(argv=None):
    p = _common.base_parser(__doc__)
    p.add_argument("twin_stats_json")
    args = p.parse_args(argv)
    stats = _common.load_json(args.twin_stats_json)
    fig = build(stats)
    style.check_text_overlap(fig)
    style.save(fig, args.out, inputs=[args.twin_stats_json], producer="twin_audit")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
