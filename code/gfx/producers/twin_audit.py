"""
gfx/producers/twin_audit.py -- the twin-export privacy-audit figure (PLAN.md Part D).

`twin_stats.json` (PLAN.md C.2) is produced by `tools/twin_export/` (U3, in parallel) and
does not exist in this worktree yet, so this producer's *reader* is deliberately loose:
it looks up each block by name and renders a "not available" placeholder if a block, or a
key inside it, is missing -- every panel is independently degradable. The block shapes it
expects (documented per-panel below) are this unit's best-effort reading of PLAN.md C.2;
treat them as provisional until U3 lands and adjust the lookups, not the panel layout.

Panels: fitted-vs-empirical marginals (quantile plot from `marginals.<var>.coarse_cdf`,
lognormal/dPlN overlays from `marginals.<var>.fits.<name>.quantiles`) · share-by-decile
curves with bands (`share_curves.<A|B>`) · Moran's I / hop-correlation bars (`spatial`) ·
individual-vs-neighbourhood correlation bars, the privacy sign-off panel (`audit`) ·
census pair-size histogram real vs twin (`twin_check`) · a text summary box
(`twin_check.pass`, `graph`).

Usage:
    python -m gfx.producers.twin_audit <twin_stats.json> --out <png>
"""
from __future__ import annotations

import sys

import numpy as np
import matplotlib.pyplot as plt

from .. import charts, style
from . import _common


def _placeholder(ax, msg, title):
    ax.axis("off")
    ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=8, transform=ax.transAxes,
            wrap=True)
    ax.set_title(title, fontsize=8, loc="left")


def _panel_marginal(ax, stats, var="M"):
    m = (stats.get("marginals") or {}).get(var)
    if not m or not m.get("coarse_cdf"):
        return _placeholder(ax, f"no marginals.{var}.coarse_cdf", f"{var} marginal fit")
    cdf = m["coarse_cdf"]
    p, emp = np.asarray(cdf["p"], float), np.asarray(cdf["bin_mean"], float)
    ax.plot(p, emp, color=style.PALETTE["neutral"], lw=1.4, label="empirical")
    for name, ls in (("lognormal", "--"), ("dpln", "-")):
        fit = (m.get("fits") or {}).get(name)
        if fit and fit.get("quantiles"):
            q = fit["quantiles"]
            xs = sorted(float(k) for k in q)
            ys = [q[str(x) if str(x) in q else x] for x in xs]
            ax.plot(xs, ys, ls, color=style.PALETTE["A" if name == "lognormal" else "B"],
                    lw=1.1, label=name)
    star = " (dPlN preferred)" if m.get("prefer_dpln") else " (lognormal preferred)"
    ax.set_xlabel("probability", fontsize=8)
    ax.set_ylabel(var, fontsize=8)
    ax.set_title(f"{var} marginal: fitted vs. empirical{star}", fontsize=8, loc="left")
    ax.legend(fontsize=6, frameon=False)


def _panel_share_curves(ax, stats):
    curves = stats.get("share_curves") or {}
    if not curves:
        return _placeholder(ax, "no share_curves.A / share_curves.B", "share by M-decile")
    for name in ("A", "B"):
        c = curves.get(name)
        if not c:
            continue
        d = np.asarray(c["decile"], float)
        mu = np.asarray(c["mean_log_share"], float)
        sd = np.asarray(c.get("sd_log_share", np.zeros_like(mu)), float)
        color = style.PALETTE[name]
        charts.sweep_curve(ax, d, mu, band=(mu - sd, mu + sd), color=color, label=name,
                           xlabel="M decile", ylabel="mean log(share)")
    ax.set_title("share-by-decile curves", fontsize=8, loc="left")


def _panel_spatial(ax, stats):
    sp = stats.get("spatial") or {}
    moran = sp.get("moran_I") or {}
    hop = sp.get("rank_corr_by_hop") or {}
    if not moran and not hop:
        return _placeholder(ax, "no spatial.moran_I / spatial.rank_corr_by_hop",
                           "Moran's I / hop correlation")
    series = {}
    labels = []
    if moran:
        labels = list(moran)
        series["Moran's I"] = [moran[k] for k in labels]
    if hop:
        hop_labels = [f"hop{k}" for k in sorted(hop, key=lambda k: int(k))]
        labels = labels or hop_labels
        if len(hop_labels) == len(labels) or not moran:
            series["hop rank corr"] = [hop[k] for k in sorted(hop, key=lambda k: int(k))]
    charts.grouped_bars(ax, labels, series, ylabel="value",
                        title="Moran's I / hop-rank correlation")


def _panel_privacy(ax, stats):
    a = stats.get("audit") or {}
    pearson = a.get("pearson_log") or {}
    neigh = a.get("neighborhood_corr_3hop") or {}
    if not pearson and not neigh:
        return _placeholder(ax, "no audit.pearson_log / audit.neighborhood_corr_3hop",
                           "privacy sign-off: individual vs. neighbourhood corr")
    labels = sorted(set(pearson) | set(neigh))
    series = {}
    if pearson:
        series["individual (pearson, log)"] = [pearson.get(k, np.nan) for k in labels]
    if neigh:
        series["3-hop neighbourhood"] = [neigh.get(k, np.nan) for k in labels]
    charts.grouped_bars(ax, labels, series, ylabel="correlation",
                        title="privacy sign-off: individual vs. neighbourhood corr")


def _panel_census_hist(ax, stats):
    tc = stats.get("twin_check") or {}
    bins = tc.get("census_pair_size_bins")
    real = tc.get("census_pair_size_hist_real")
    twin = tc.get("census_pair_size_hist_twin")
    if not (bins and real and twin):
        return _placeholder(ax, "no twin_check.census_pair_size_hist_{real,twin}",
                           "census pair-size: real vs. twin")
    x = np.arange(len(bins))
    ax.bar(x - 0.18, real, 0.36, color=style.PALETTE["neutral"], label="real")
    ax.bar(x + 0.18, twin, 0.36, color=style.PALETTE["A"], label="twin")
    ax.set_xticks(x, [str(b) for b in bins], fontsize=6, rotation=45, ha="right")
    ax.set_ylabel("count", fontsize=8)
    ax.set_title("census pair-size: real vs. twin", fontsize=8, loc="left")
    ax.legend(fontsize=6, frameon=False)


def _panel_text(ax, stats):
    ax.axis("off")
    tc = stats.get("twin_check") or {}
    g = stats.get("graph") or {}
    lines = []
    if "pass" in tc:
        lines.append(f"twin_check.pass = {tc['pass']}")
    for k in ("n", "m", "components", "articulation_points", "state_cross_share"):
        if k in g:
            v = g[k]
            lines.append(f"graph.{k} = {v:.3g}" if isinstance(v, float) else f"graph.{k} = {v}")
    if not lines:
        lines = ["no twin_check / graph blocks present"]
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
    style.tight_layout(fig)
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
