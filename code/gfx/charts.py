"""
gfx/charts.py -- axes-level chart primitives shared by the run-summary / trace / frontier
figures.

Annotation placement never uses a hand-tuned offset: `_dodge_texts` nudges overlapping
text artists apart by inspecting their rendered bounding boxes (the same mechanism
`gfx.style.lint_text_overlap` audits with), iterating until clear or a cap is hit.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import matplotlib.pyplot as plt

from . import style


# --------------------------------------------------------------------------- dodge
def _dodge_texts(ax, texts, *, max_iter: int = 40, step_frac: float = 0.012):
    """Nudge overlapping text artists apart in display space (vertical), in place.
    `step_frac` is a fraction of the axes height per nudge."""
    if len(texts) < 2:
        return
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bbox_ax = ax.get_window_extent(renderer)
    step = step_frac * bbox_ax.height
    for _ in range(max_iter):
        boxes = [t.get_window_extent(renderer) for t in texts]
        moved = False
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                if boxes[i].overlaps(boxes[j]):
                    moved = True
                    if boxes[i].y0 <= boxes[j].y0:
                        _shift(texts[i], -step)
                        _shift(texts[j], step)
                    else:
                        _shift(texts[i], step)
                        _shift(texts[j], -step)
        if not moved:
            break
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()


def dodge_texts(ax, texts, **kwargs):
    """Public entry point for `_dodge_texts`: resolve overlaps among an explicit list of
    text artists already placed on `ax` (e.g. label sets accumulated across several
    `frontier`/plot calls sharing one axes -- dodging each call in isolation would miss
    overlaps between them)."""
    return _dodge_texts(ax, texts, **kwargs)


def _shift(text, dy_px):
    x, y = text.get_position()
    # move in display space by converting a small px offset to data/axes offset via the
    # text's own transform; simplest robust approach is a points-based annotation offset
    trans = text.get_transform()
    inv = trans.inverted()
    x0, y0 = trans.transform((x, y))
    xn, yn = inv.transform((x0, y0 + dy_px))
    text.set_position((x, yn))


# --------------------------------------------------------------------------- bars / tables
def grouped_bars(ax, labels: Sequence[str], series: dict, *, colors: dict | None = None,
                 title=None, ylabel=None, width=0.8, rotation=30, fontsize=8):
    """One bar group per label, one bar per `series` key. `series`: {name: [values]},
    each aligned to `labels`."""
    names = list(series)
    k = len(names)
    x = np.arange(len(labels))
    bw = width / max(k, 1)
    for i, name in enumerate(names):
        color = (colors or {}).get(name)
        offset = (i - (k - 1) / 2) * bw
        ax.bar(x + offset, series[name], bw, label=name, color=color)
    ax.set_xticks(x, labels, fontsize=fontsize, rotation=rotation,
                  ha="right" if rotation else "center")
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=fontsize)
    if title:
        ax.set_title(title, fontsize=fontsize)
    if k > 1:
        ax.legend(fontsize=fontsize - 1, frameon=False)
    return ax


def cert_table(ax, header: Sequence[str], rows: Sequence[Sequence], *, title=None,
               fontsize=7, col_widths=None):
    """A plain monospace-ish table on an axes with ticks/spines off (the
    `case_pipeline.py` "text panel" idiom, shared)."""
    ax.axis("off")
    table = ax.table(cellText=list(rows), colLabels=list(header), loc="center",
                     cellLoc="left", colWidths=col_widths)
    table.auto_set_font_size(False)
    table.set_fontsize(fontsize)
    table.scale(1, 1.2)
    if title:
        ax.set_title(title, fontsize=fontsize + 1)
    return table


# --------------------------------------------------------------------------- curves
def sweep_curve(ax, x, y, *, band=None, color=None, label=None, marker="o", ms=3.5,
                title=None, xlabel=None, ylabel=None, fontsize=8):
    """A point/line curve with an optional min-max (or lo/hi) shaded band. `band`:
    (lo, hi) arrays aligned to `x`, or None."""
    color = style.PALETTE["A"] if color is None else color
    if band is not None:
        lo, hi = band
        ax.fill_between(x, lo, hi, color=color, alpha=0.15, lw=0)
    ax.plot(x, y, marker=marker, ms=ms, color=color, label=label)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=fontsize)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=fontsize)
    if title:
        ax.set_title(title, fontsize=fontsize, loc="left")
    if label:
        ax.legend(fontsize=fontsize - 1, frameon=False)
    return ax


def gap_vs_time(ax, traces: dict, *, cap: float | None = None, colors: dict | None = None,
                title=None, fontsize=8):
    """gap_nats = UB - LB vs time, one step curve per method. `traces`:
    {method: [(t, LB, UB), ...]} (the `Result.trace` / row `trace` field)."""
    colors = colors or style.method_colors(list(traces))
    for name, tr in traces.items():
        if not tr:
            continue
        t = np.array([r[0] for r in tr], float)
        lb = np.array([r[1] if r[1] is not None else np.nan for r in tr], float)
        ub = np.array([r[2] if r[2] is not None else np.nan for r in tr], float)
        gap = ub - lb
        ax.step(t, gap, where="post", color=colors.get(name), label=name)
    if cap is not None:
        ax.axvline(cap, color=style.PALETTE["neutral"], lw=0.7, ls="--")
    ax.set_yscale("log")
    ax.yaxis.set_minor_formatter(plt.NullFormatter())  # minor-tick mantissas clutter and
    # can overlap other subplots' text after tight_layout; major ticks are enough here
    ax.set_xlabel("time (s)", fontsize=fontsize)
    ax.set_ylabel("gap (nats)", fontsize=fontsize)
    if title:
        ax.set_title(title, fontsize=fontsize, loc="left")
    ax.legend(fontsize=fontsize - 1, frameon=False)
    return ax


def ecdf(ax, values_by_method: dict, *, colors: dict | None = None, title=None,
        xlabel=None, fontsize=8):
    """Empirical CDF, one step curve per method. Values with None/NaN are dropped."""
    colors = colors or style.method_colors(list(values_by_method))
    for name, vals in values_by_method.items():
        v = np.sort(np.array([x for x in vals if x is not None and np.isfinite(x)], float))
        if len(v) == 0:
            continue
        y = np.arange(1, len(v) + 1) / len(v)
        ax.step(v, y, where="post", color=colors.get(name), label=name)
    ax.set_ylim(0, 1.02)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel("fraction of instances", fontsize=fontsize)
    if title:
        ax.set_title(title, fontsize=fontsize, loc="left")
    ax.legend(fontsize=fontsize - 1, frameon=False)
    return ax


def box(ax, values_by_method: dict, *, colors: dict | None = None, title=None,
       ylabel=None, fontsize=8, rotation=90):
    """One box per method. Methods with no finite values still get an (empty) box so the
    x-axis stays aligned across panels. Vertical labels by default: with many methods in
    a narrow panel, a shallow rotation makes adjacent labels' bounding boxes touch."""
    colors = colors or style.method_colors(list(values_by_method))
    names = list(values_by_method)
    data = [[v for v in values_by_method[m] if v is not None and np.isfinite(v)]
            for m in names]
    bp = ax.boxplot(data, tick_labels=names, patch_artist=True, showfliers=False)
    for patch, name in zip(bp["boxes"], names):
        patch.set_facecolor(colors.get(name, "0.7"))
        patch.set_alpha(0.6)
    ha = "center" if rotation in (0, 90) else "right"
    ax.tick_params(axis="x", labelsize=fontsize, rotation=rotation)
    for lbl in ax.get_xticklabels():
        lbl.set_ha(ha)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=fontsize)
    if title:
        ax.set_title(title, fontsize=fontsize, loc="left")
    return bp


# --------------------------------------------------------------------------- matrices
def status_grid(ax, methods: Sequence[str], instances: Sequence[str], status,
                *, title=None, fontsize=7):
    """methods x instances grid, one cell per (method, instance) coloured by
    `gfx.style.status_color`. `status`: dict[(method, instance)] -> status string, or a
    2-D array-like of status strings aligned to (instances, methods)."""
    n_i, n_m = len(instances), len(methods)
    if isinstance(status, dict):
        grid = [[status.get((m, i)) for m in methods] for i in instances]
    else:
        grid = status
    colors = np.empty((n_i, n_m, 4))
    for r in range(n_i):
        for c in range(n_m):
            colors[r, c] = plt.matplotlib.colors.to_rgba(style.status_color(grid[r][c]))
    ax.imshow(colors, aspect="auto", interpolation="none")
    ax.set_xticks(range(n_m), methods, fontsize=fontsize, rotation=90, ha="center")
    ax.set_yticks(range(n_i), instances, fontsize=fontsize)
    if title:
        ax.set_title(title, fontsize=fontsize + 1, loc="left")
    return ax


def heat_matrix(ax, rows: Sequence[str], cols: Sequence[str], values, *, cmap="Blues",
                title=None, fontsize=7, cbar=True, vmin=None, vmax=None, fmt=None):
    """rows x cols numeric matrix as a heatmap with an inline colorbar and optional
    per-cell value labels (`fmt`, e.g. '{:.0%}')."""
    V = np.asarray(values, float)
    im = ax.imshow(V, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(cols)), cols, fontsize=fontsize, rotation=90, ha="center")
    ax.set_yticks(range(len(rows)), rows, fontsize=fontsize)
    if fmt:
        for r in range(V.shape[0]):
            for c in range(V.shape[1]):
                if np.isfinite(V[r, c]):
                    ax.text(c, r, fmt.format(V[r, c]), ha="center", va="center",
                            fontsize=fontsize - 1)
    if cbar:
        cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
        cb.ax.tick_params(labelsize=6)
    if title:
        ax.set_title(title, fontsize=fontsize + 1, loc="left")
    return im


def frontier(ax, pts: Sequence[tuple], labels: Sequence[str] | None = None, *,
            color=None, xlabel=None, ylabel=None, title=None, fontsize=8,
            text_collector: list | None = None):
    """Scatter of (x, y) points with dodged text labels (the C8 rho-frontier pattern,
    generalised: no hand offsets, `_dodge_texts` resolves overlaps).

    When several `frontier` calls share one axes (e.g. one series per method), pass the
    same `text_collector` list to every call and dodge once yourself afterwards via
    `charts.dodge_texts(ax, text_collector)` -- dodging each call in isolation cannot see
    another call's labels and so cannot resolve overlaps between them.
    """
    color = style.PALETTE["A"] if color is None else color
    pts = np.asarray(pts, float)
    ax.plot(pts[:, 0], pts[:, 1], "o-", color=color, ms=4)
    texts = []
    if labels is not None:
        yspan = float(np.ptp(pts[:, 1])) or 1.0
        dy0 = 0.03 * yspan  # one uniform nudge so labels start off the marker; the
        # actual overlap resolution is `_dodge_texts`, not this constant
        for (x, y), lab in zip(pts, labels):
            texts.append(ax.text(x, y + dy0, str(lab), fontsize=fontsize - 1,
                                 ha="center", va="bottom"))
        if text_collector is not None:
            text_collector.extend(texts)
        else:
            _dodge_texts(ax, texts)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=fontsize)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=fontsize)
    if title:
        ax.set_title(title, fontsize=fontsize, loc="left")
    return ax
