"""
gfx/producers/calib_compare.py -- the synth-calibration comparison figure (PLAN.md Part D).

Compares S1_aligned vs S8_twin vs the real twin (once U5/U3 exist) on M/A/B marginals,
active fraction, corr(A, B), and headroom slack. There is no frozen file format for this
yet (U5 owns `code/synth.py::calibrate`); this producer reads its own minimal schema --
documented here, provisional until U5 lands:

    {"scenarios": {"<name>": {
        "M": {"quantiles": {"<p>": v, ...}}, "A": {...}, "B": {...},
        "active_frac": float, "corr_AB": float,
        "headroom_slack": {"quantiles": {"<p>": v, ...}}
    }, ...}}

Missing scenarios/keys degrade a panel to a placeholder rather than raising.

Usage:
    python -m gfx.producers.calib_compare <calib.json> --out <png>
"""
from __future__ import annotations

import sys

import numpy as np
import matplotlib.pyplot as plt

from .. import charts, style
from . import _common

SCENARIO_ORDER = ("S1_aligned", "S8_twin", "twin")


def _placeholder(ax, msg, title):
    ax.axis("off")
    ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=8, transform=ax.transAxes,
            wrap=True)
    ax.set_title(title, fontsize=8, loc="left")


def _scenario_order(scenarios: dict) -> list:
    known = [s for s in SCENARIO_ORDER if s in scenarios]
    rest = [s for s in scenarios if s not in known]
    return known + sorted(rest)


def _panel_quantiles(ax, scenarios, key, colors, title):
    any_line = False
    for name, color in colors.items():
        block = (scenarios.get(name) or {}).get(key)
        if not block or not block.get("quantiles"):
            continue
        q = block["quantiles"]
        xs = sorted(float(k) for k in q)
        ys = [q[str(x) if str(x) in q else x] for x in xs]
        ax.plot(xs, ys, "o-", ms=3, color=color, label=name)
        any_line = True
    if not any_line:
        return _placeholder(ax, f"no scenario has '{key}.quantiles'", title)
    ax.set_xlabel("probability", fontsize=8)
    ax.set_title(title, fontsize=8, loc="left")
    ax.legend(fontsize=6, frameon=False)


def _panel_scalar_bar(ax, scenarios, key, colors, title, ylabel):
    names = [n for n in colors if (scenarios.get(n) or {}).get(key) is not None]
    if not names:
        return _placeholder(ax, f"no scenario has '{key}'", title)
    vals = [scenarios[n][key] for n in names]
    ax.bar(names, vals, color=[colors[n] for n in names])
    ax.tick_params(axis="x", labelsize=7, rotation=20)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.set_title(title, fontsize=8, loc="left")


def build(calib: dict) -> plt.Figure:
    style.use_rc()
    scenarios = calib.get("scenarios") or {}
    order = _scenario_order(scenarios)
    colors = style.method_colors(order)  # reuse the tab10-by-order convention
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    _panel_quantiles(axes[0, 0], scenarios, "M", colors, "M marginal (quantiles)")
    _panel_quantiles(axes[0, 1], scenarios, "A", colors, "A marginal (quantiles)")
    _panel_quantiles(axes[0, 2], scenarios, "B", colors, "B marginal (quantiles)")
    _panel_scalar_bar(axes[1, 0], scenarios, "active_frac", colors, "active fraction",
                      "active_frac")
    _panel_scalar_bar(axes[1, 1], scenarios, "corr_AB", colors, "corr(A, B)", "corr_AB")
    _panel_quantiles(axes[1, 2], scenarios, "headroom_slack", colors,
                     "headroom slack (quantiles)")
    fig.suptitle("synth calibration: S1 vs. S8_twin vs. twin", fontsize=11)
    style.tight_layout(fig)
    return fig


def main(argv=None):
    p = _common.base_parser(__doc__)
    p.add_argument("calib_json")
    args = p.parse_args(argv)
    calib = _common.load_json(args.calib_json)
    fig = build(calib)
    style.check_text_overlap(fig)
    style.save(fig, args.out, inputs=[args.calib_json], producer="calib_compare")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
