"""
gfx/style.py -- the single palette / rcParams / dpi / save policy for every gfx figure.

Rules (PLAN.md Part D): A is always blue, B always red, everywhere; palette and dpi come
only from this module; per-rep colours use a fixed 20-colour cycle with a warning past 20;
every producer calls `lint_text_overlap`.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import warnings
from typing import Iterable, Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt

# --------------------------------------------------------------------------- palette
PALETTE = {
    "A": "#2166ac",
    "B": "#b2182b",
    "neutral": "#4d4d4d",
    "unsolved": (0.9, 0.9, 0.9),
    "status": {
        "optimal": "#1a9850",
        "optimal_rooted": "#66bd63",
        "gap_limit": "#fee08b",
        "time_limit": "#fdae61",
        "iteration_limit": "#f46d43",
        "heuristic": "#abd9e9",
        "infeasible": "#d73027",
        "error": "#878787",
        None: "#e0e0e0",
    },
    "cmap_ua": "Blues",
    "cmap_ub": "Reds",
    "cmap_M": "YlOrBr",
}

# fixed 20-colour cycle for per-rep territory maps (tab20 has exactly 20 distinct colours)
REP_CYCLE = [mpl.colors.to_hex(c) for c in plt.get_cmap("tab20").colors]


def rep_color(i: int) -> str:
    """Colour for rep index `i` in a per-rep territory map; warns past the 20-colour cycle."""
    if i >= len(REP_CYCLE):
        warnings.warn(
            f"rep index {i} exceeds the {len(REP_CYCLE)}-colour cycle; colours repeat",
            stacklevel=2,
        )
    return REP_CYCLE[i % len(REP_CYCLE)]


def status_color(status) -> str:
    return PALETTE["status"].get(status, PALETTE["status"][None])


def method_colors(methods: Sequence[str]) -> dict:
    """Method -> colour, tab10 cycled in the order `methods` is given (REGISTRY order)."""
    tab10 = [mpl.colors.to_hex(c) for c in plt.get_cmap("tab10").colors]
    return {m: tab10[i % len(tab10)] for i, m in enumerate(methods)}


# --------------------------------------------------------------------------- rcParams
MAP_RC = {
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "legend.fontsize": 7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.direction": "out",
    "ytick.direction": "out",
}

RC = dict(MAP_RC)
RC.update({
    "figure.titlesize": 10,
    "savefig.dpi": 200,
})

FIGSIZE = {
    "paper_wide": (11, 3.7),
    "card": (13, 8),
}


def tight_layout(fig, **kwargs):
    """`fig.tight_layout` with generous padding: a bare `tight_layout()` can leave tick
    labels from adjacent stacked panels a pixel or two apart, which `lint_text_overlap`
    (correctly) flags. Also reserves top margin automatically when the figure has a
    suptitle, so it never collides with the top row's panel titles / colorbar ticks."""
    kwargs.setdefault("h_pad", 2.2)
    kwargs.setdefault("w_pad", 2.6)
    if getattr(fig, "_suptitle", None) is not None and "rect" not in kwargs:
        kwargs["rect"] = (0, 0, 1, 0.93)
    fig.tight_layout(**kwargs)


def use_rc():
    """Apply RC on top of matplotlib's defaults. Call once per process (producers do)."""
    mpl.rcParams.update(RC)


# --------------------------------------------------------------------------- text-overlap lint
def lint_text_overlap(fig) -> list:
    """Pairs of (text, text) whose rendered bounding boxes overlap, after a draw.

    Same idea as `mkfig_census.py`'s inline check, promoted to a shared helper. Ignores
    empty / invisible text artists. Requires a renderer, so this draws the figure (Agg
    backend; cheap, idempotent).
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = [
        (t, t.get_window_extent(renderer))
        for t in fig.findobj(mpl.text.Text)
        if t.get_text().strip() and t.get_visible()
    ]
    overlaps = []
    for i, (t1, b1) in enumerate(texts):
        for t2, b2 in texts[i + 1:]:
            if b1.overlaps(b2):
                overlaps.append((t1.get_text(), t2.get_text()))
    return overlaps


def check_text_overlap(fig, *, warn: bool = False) -> list:
    """Run `lint_text_overlap` and raise (default) or warn on any overlap. Every producer
    calls this right before / after saving."""
    overlaps = lint_text_overlap(fig)
    if overlaps:
        msg = f"{len(overlaps)} overlapping text pair(s): {overlaps[:5]}"
        if warn:
            warnings.warn(msg, stacklevel=2)
        else:
            raise RuntimeError(msg)
    return overlaps


# --------------------------------------------------------------------------- save policy
def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def save(fig, path: str, *, inputs: Iterable[str] = (), producer: str | None = None,
          dpi: float | None = None, close: bool = True) -> str:
    """Write `path` (PNG) and `path + '.json'` (sidecar: input hashes, producer, git commit,
    dpi). Single dpi/bbox policy for every gfx figure: dpi from RC unless overridden here,
    bbox_inches='tight'."""
    dpi = RC["savefig.dpi"] if dpi is None else dpi
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    sidecar = {
        "inputs": {os.path.basename(p): _sha256(p) for p in inputs if os.path.exists(p)},
        "producer": producer,
        "git_commit": _git_commit(),
        "dpi": dpi,
    }
    with open(path + ".json", "w") as f:
        json.dump(sidecar, f, indent=2, sort_keys=True)
    if close:
        plt.close(fig)
    return path
