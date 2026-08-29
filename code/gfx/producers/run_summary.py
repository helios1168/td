"""
gfx/producers/run_summary.py -- the benchmark-run summary figure (PLAN.md Part D).

Default panels: certified share per method x tier (bars) · time-to-certificate ECDF ·
gap@cap box per method · named-failure status grid (6 x methods) · mechanism matrix
(method x (a)-(d), share certified) · cost-of-contiguity vs. articulation points / active
frac (scatter). `--rho` switches to the rho-frontier figure instead: product vs perimeter
per method with rho labels (the C8 pattern, auto-dodged).

Every panel is tolerant of missing columns (instances.csv/summary.csv shapes are still
being designed in U1b in parallel) -- it renders a "not available" placeholder rather
than raising.

Usage:
    python -m gfx.producers.run_summary <rows.jsonl> <instances.csv> <summary.csv> --out <png>
    python -m gfx.producers.run_summary <rows.jsonl> <instances.csv> <summary.csv> --out <png> --rho
"""
from __future__ import annotations

import sys
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt

from .. import charts, style
from . import _common

NAMED_FAILURES = (
    "C1-seed2_A0_B0", "C5-respect_state_A2_B2", "C7_125_205", "C7_A3_B3",
    "C9-seed2_A2_B2", "C9-seed2_A0_B0",
)


def _placeholder(ax, msg, title):
    ax.axis("off")
    ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=8, transform=ax.transAxes,
            wrap=True)
    ax.set_title(title, fontsize=8, loc="left")


def _num(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- default panels
def build_summary(rows: list, instances: list, summary: list) -> plt.Figure:
    style.use_rc()
    methods = sorted({r.get("method") for r in summary if r.get("method")}) or \
        sorted({r.get("method") for r in rows if r.get("method")})
    colors = style.method_colors(methods)
    inst_by_name = {r.get("instance") or r.get("name"): r for r in instances}

    fig, axes = plt.subplots(2, 3, figsize=(13, 8))

    # 1. certified share per method x tier
    ax = axes[0, 0]
    if summary and any("tier" in r for r in summary):
        tiers = sorted({r["tier"] for r in summary})
        series = {m: [_num(next((r.get("certified_frac") for r in summary
                                 if r.get("method") == m and r.get("tier") == t), None)) or 0.0
                     for t in tiers] for m in methods}
        charts.grouped_bars(ax, tiers, series, colors=colors, ylabel="certified fraction",
                            title="certified share per method x tier")
    else:
        _placeholder(ax, "summary.csv has no 'tier'/'certified_frac' columns",
                    "certified share per method x tier")

    # 2. time-to-certificate ECDF
    ax = axes[0, 1]
    cert = defaultdict(list)
    for r in rows:
        eff = r.get("status_eff", r.get("status"))
        if eff and str(eff).startswith("optimal") and r.get("t_total") is not None:
            cert[r["method"]].append(r["t_total"])
    if cert:
        charts.ecdf(ax, cert, colors=colors, title="time-to-certificate ECDF",
                    xlabel="t_total (s)")
    else:
        _placeholder(ax, "no certified rows (status_eff == optimal*) with t_total",
                    "time-to-certificate ECDF")

    # 3. gap@cap box per method
    ax = axes[0, 2]
    gaps = defaultdict(list)
    for r in rows:
        g = _num(r.get("gap_nats"))
        if g is not None and r.get("method"):
            gaps[r["method"]].append(g)
    if gaps:
        charts.box(ax, gaps, colors=colors, ylabel="gap_nats @ cap", title="gap@cap")
        ax.set_yscale("log")
    else:
        _placeholder(ax, "no rows with a finite gap_nats", "gap@cap")

    # 4. named-failure status grid
    ax = axes[1, 0]
    grid_rows = [n for n in NAMED_FAILURES if any(r.get("instance") == n for r in rows)]
    if grid_rows:
        status = {}
        for r in rows:
            if r.get("instance") in grid_rows:
                status[(r["method"], r["instance"])] = r.get("status_eff", r.get("status"))
        charts.status_grid(ax, methods, grid_rows, status, title="named failures")
    else:
        _placeholder(ax, "none of the six named-failure instances\nappear in rows.jsonl",
                    "named failures")

    # 5. mechanism matrix (method x (a)-(d), share certified)
    ax = axes[1, 1]
    mech_of = {name: rec.get("mechanism") for name, rec in inst_by_name.items()
              if rec.get("mechanism")}
    if mech_of:
        mechs = sorted(set(mech_of.values()))
        mat = np.full((len(methods), len(mechs)), np.nan)
        for i, m in enumerate(methods):
            for j, mech in enumerate(mechs):
                pool = [r for r in rows if r.get("method") == m
                       and mech_of.get(r.get("instance")) == mech]
                if pool:
                    cert_n = sum(1 for r in pool
                                if str(r.get("status_eff", r.get("status"))).startswith("optimal"))
                    mat[i, j] = cert_n / len(pool)
        charts.heat_matrix(ax, methods, mechs, mat, title="mechanism (a-d): share certified",
                           fmt="{:.0%}", vmin=0, vmax=1)
    else:
        _placeholder(ax, "instances.csv has no 'mechanism' column\n(failure regime (a)-(d))",
                    "mechanism (a-d): share certified")

    # 6. cost-of-contiguity vs. articulation points / active frac
    ax = axes[1, 2]
    xs, ys, cs = [], [], []
    for r in rows:
        c = _num(r.get("cost_of_contiguity"))
        rec = inst_by_name.get(r.get("instance"), {})
        ap = _num(rec.get("articulation_points"))
        if c is not None and ap is not None:
            xs.append(ap); ys.append(c); cs.append(colors.get(r.get("method"), "0.5"))
    if xs:
        ax.scatter(xs, ys, c=cs, s=14, alpha=0.7, edgecolors="none")
        ax.set_xlabel("articulation points", fontsize=8)
        ax.set_ylabel("cost of contiguity", fontsize=8)
        ax.set_title("cost of contiguity vs. structure", fontsize=8, loc="left")
    else:
        _placeholder(ax, "no rows with both cost_of_contiguity\nand instances.csv "
                    "articulation_points", "cost of contiguity vs. structure")

    style.tight_layout(fig)
    return fig


# --------------------------------------------------------------------------- rho frontier
def build_rho_frontier(rows: list) -> plt.Figure:
    style.use_rc()
    methods = sorted({r.get("method") for r in rows if r.get("method")
                      and r.get("rho") is not None})
    colors = style.method_colors(methods)
    fig, ax = plt.subplots(figsize=(11, 5))
    any_pts = False
    texts: list = []
    for m in methods:
        pool = sorted((r for r in rows if r.get("method") == m and r.get("rho") is not None
                      and _num(r.get("product")) is not None
                      and _num(r.get("perimeter")) is not None),
                     key=lambda r: r["rho"])
        if not pool:
            continue
        pts = [(r["perimeter"], r["product"]) for r in pool]
        labels = [f"{m}: rho={r['rho']:g}" for r in pool]
        charts.frontier(ax, pts, labels, color=colors[m], xlabel="perimeter",
                        ylabel="product (g_a * g_b)", title="rho frontier: product vs. perimeter",
                        text_collector=texts)
        any_pts = True
    if any_pts:
        charts.dodge_texts(ax, texts)  # one pass over every method's labels together
    else:
        _placeholder(ax, "no rows with rho, product and perimeter all present",
                    "rho frontier: product vs. perimeter")
    style.tight_layout(fig)
    return fig


def main(argv=None):
    p = _common.base_parser(__doc__)
    p.add_argument("rows_jsonl")
    p.add_argument("instances_csv")
    p.add_argument("summary_csv")
    p.add_argument("--rho", action="store_true", help="render the rho-frontier figure instead")
    args = p.parse_args(argv)
    rows = _common.load_jsonl(args.rows_jsonl)
    instances = _common.load_csv(args.instances_csv)
    summary = _common.load_csv(args.summary_csv)
    inputs = [args.rows_jsonl, args.instances_csv, args.summary_csv]
    if args.rho:
        fig = build_rho_frontier(rows)
        producer = "run_summary --rho"
    else:
        fig = build_summary(rows, instances, summary)
        producer = "run_summary"
    style.check_text_overlap(fig)
    style.save(fig, args.out, inputs=inputs, producer=producer)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
