"""
gfx/producers/method_trace.py -- the method x instance trace figure (PLAN.md Part D).

Panels: gap-vs-time (LB/UB in nats, cap line) · cuts/tangents per round · pieces per
round. The frozen contract (`contig_methods/base.py`) guarantees only `trace = [(t, LB,
UB), ...]` on every row; per-round cuts/tangents/pieces are optional diagnostics a method
may additionally log under `row["extra"]["iter_log"]` (a list of dicts with any of `it,
n_cuts, n_tangents, pieces_a, pieces_b`). When a method doesn't provide that, the panel
says so rather than fabricating data.

Usage:
    python -m gfx.producers.method_trace <rows.jsonl> --instance <name> --out <png>
    [--methods m1,m2,...] [--cap 60]
"""
from __future__ import annotations

import sys

import matplotlib.pyplot as plt

from .. import charts, style
from . import _common


def _placeholder(ax, msg, title):
    ax.axis("off")
    ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=8, transform=ax.transAxes,
            wrap=True)
    ax.set_title(title, fontsize=8, loc="left")


def build(rows: list, instance: str, methods: list | None = None,
         cap: float | None = None) -> plt.Figure:
    style.use_rc()
    rows = [r for r in rows if r.get("instance") == instance]
    if methods:
        rows = [r for r in rows if r.get("method") in methods]
    if not rows:
        raise ValueError(f"no rows for instance {instance!r}"
                         + (f" and methods {methods!r}" if methods else ""))
    names = sorted({r["method"] for r in rows})
    colors = style.method_colors(names)

    fig, axes = plt.subplots(1, 3, figsize=style.FIGSIZE["paper_wide"])
    fig.suptitle(f"trace: {instance}", fontsize=10)

    traces = {r["method"]: r.get("trace") or [] for r in rows}
    if cap is None:
        cap = max((r.get("cap") for r in rows if r.get("cap")), default=None)
    charts.gap_vs_time(axes[0], traces, cap=cap, colors=colors, title="gap vs. time")
    axes[0].set_xlim(left=0)  # autoscale's negative margin tick ("-10") sits right on top
    # of the log-scale y-axis's bottom major tick at the origin corner; t is never < 0

    logs = {r["method"]: (r.get("extra") or {}).get("iter_log") for r in rows}
    have_log = {m: lg for m, lg in logs.items() if lg}
    if have_log:
        ax = axes[1]
        for m, lg in have_log.items():
            it = [e.get("it", i) for i, e in enumerate(lg)]
            if any("n_cuts" in e or "n_tangents" in e for e in lg):
                cuts = [e.get("n_cuts") for e in lg]
                tangents = [e.get("n_tangents") for e in lg]
                if any(c is not None for c in cuts):
                    ax.step(it, cuts, where="post", color=colors[m], label=f"{m} cuts")
                if any(t is not None for t in tangents):
                    ax.step(it, tangents, where="post", color=colors[m], ls="--",
                            label=f"{m} tangents")
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.set_xlabel("round", fontsize=8)
        ax.set_ylabel("count", fontsize=8)
        ax.set_title("cuts / tangents per round", fontsize=8, loc="left")
        ax.legend(fontsize=6, frameon=False)
    else:
        _placeholder(axes[1], "no per-round cut/tangent log\n(extra.iter_log) for this method",
                    "cuts / tangents per round")

    if have_log and any(any("pieces_a" in e or "pieces_b" in e for e in lg)
                        for lg in have_log.values()):
        ax = axes[2]
        for m, lg in have_log.items():
            it = [e.get("it", i) for i, e in enumerate(lg)]
            pa = [e.get("pieces_a") for e in lg]
            pb = [e.get("pieces_b") for e in lg]
            if any(x is not None for x in pa):
                ax.step(it, pa, where="post", color=colors[m], label=f"{m} pieces_a")
            if any(x is not None for x in pb):
                ax.step(it, pb, where="post", color=colors[m], ls="--", label=f"{m} pieces_b")
        ax.axhline(1, color=style.PALETTE["neutral"], lw=0.6, ls=":")
        ax.set_xlim(left=0)
        ax.set_xlabel("round", fontsize=8)
        ax.set_ylabel("pieces", fontsize=8)
        ax.set_title("pieces per round", fontsize=8, loc="left")
        ax.legend(fontsize=6, frameon=False)
    else:
        _placeholder(axes[2], "no per-round pieces log\n(extra.iter_log) for this method",
                    "pieces per round")

    style.tight_layout(fig)
    return fig


def main(argv=None):
    p = _common.base_parser(__doc__)
    p.add_argument("rows_jsonl")
    p.add_argument("--instance", required=True)
    p.add_argument("--methods", default=None, help="comma-separated method filter")
    p.add_argument("--cap", type=float, default=None)
    args = p.parse_args(argv)
    rows = _common.load_jsonl(args.rows_jsonl)
    methods = args.methods.split(",") if args.methods else None
    fig = build(rows, args.instance, methods, args.cap)
    style.check_text_overlap(fig)
    style.save(fig, args.out, inputs=[args.rows_jsonl], producer="method_trace")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
