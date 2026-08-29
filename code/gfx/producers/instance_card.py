"""
gfx/producers/instance_card.py -- the instance card (PLAN.md Part D "Common figure set",
redesigned U11).

Panels (2x6 GridSpec, no blank cells):
  row 1: pair-in-context (the pair's zips inside the whole synthetic instance, legacy
         A/B territories outlined+coloured) · free-Nash map · best contiguous incumbent
         (grey = unsolved)
  row 2: log(u_a/u_b) ratio map (wide -- the quantity that actually drives the
         allocation; a shared-scale u_a/u_b heat map is dominated by the common lam*M
         term and looks near-identical for both reps) · u_a heatmap · u_b heatmap
         (shared scale) · covariate box

U11 replaced the old "pre-merger firm A / firm B territories" panels (two uniform,
information-free blocks -- inside a pair every zip belongs to the pair's two reps by
construction) with one pair-context panel, and added the log-ratio map.

Usage:
    python -m gfx.producers.instance_card <instance.json> --out <png>
    python -m gfx.producers.instance_card <instance.json> --rows <rows.jsonl> --out <png>
"""
from __future__ import annotations

import sys

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D

from .. import geom, maps, schemas, style
from . import _common

# diverging colormap for the log(u_a/u_b) panel: A-blue at the positive end, B-red at the
# negative end (matplotlib's "RdBu" runs red-white-blue low-to-high, i.e. exactly this way
# round) -- defined here, not in style.py, since this producer owns it (no new shared
# primitive needed).
CMAP_RATIO = "RdBu"


def _ab_legend(k, n):
    return [Line2D([], [], marker="s", ls="", color=style.PALETTE["A"], label=f"A (|A|={k})"),
            Line2D([], [], marker="s", ls="", color=style.PALETTE["B"],
                   label=f"B (|B|={n - k})")]


def _lighten(hex_color, amount=0.55):
    """Blend `hex_color` toward white by `amount` in [0, 1] -- used for the two legacy
    territories in the context panel so the pair's own outline still pops."""
    r, g, b = mcolors.to_rgb(hex_color)
    return (r + (1 - r) * amount, g + (1 - g) * amount, b + (1 - b) * amount)


def _blend(hex_a, hex_b):
    ra, ga, ba = mcolors.to_rgb(hex_a)
    rb, gb, bb = mcolors.to_rgb(hex_b)
    return ((ra + rb) / 2, (ga + gb) / 2, (ba + bb) / 2)


def _best_contiguous_row(rows):
    """Best contiguous allocation among `rows` (row schema from contig_methods.base.evaluate):
    a valid row with zero excess pieces (truly contiguous, not merely `feasible` -- a row can
    be feasible/valid with excess_pieces > 0, e.g. a time-limited fragmented iterate), then
    prefer status_eff == 'optimal'(_rooted), else the highest LB."""
    if not rows:
        return None
    feasible = [r for r in rows if r.get("valid") and r.get("excess_pieces") == 0
               and r.get("to_a")]
    if not feasible:
        return None
    def key(r):
        pref = 0 if str(r.get("status_eff", r.get("status"))).startswith("optimal") else 1
        lb = r.get("LB")
        return (pref, -(lb if lb is not None else float("-inf")))
    return sorted(feasible, key=key)[0]


# --------------------------------------------------------------------------- panels
def _context_panel(ax, d, ra, rb):
    """Row-1 col-1: the pair's zips drawn inside the whole synthetic instance. All zips
    of the parent graph in grey; the pair's two legacy territories (every zip whose
    pre-merger firm-A owner is `ra`, resp. firm-B owner is `rb`) filled A-blue / B-red;
    their overlap -- which is exactly the pair's own zips, by `zips_for_pair`'s
    definition -- blended, with a bold outline around it; metro seeds if present.
    "no context in JSON" when the (optional) `context` block is absent."""
    ctx = d.get("context")
    if not ctx:
        ax.axis("off")
        ax.text(0.5, 0.5, "no context in JSON", ha="center", va="center", fontsize=8,
                transform=ax.transAxes)
        return
    nodes_c = ctx["nodes"]
    polys_c, bounds_c = geom.polys_from_pos(nodes_c, ctx["pos"])
    rep_a_c = dict(zip(nodes_c, ctx["rep_a"]))
    rep_b_c = dict(zip(nodes_c, ctx["rep_b"]))
    a_light, b_light = _lighten(style.PALETTE["A"]), _lighten(style.PALETTE["B"])
    overlap_color = _blend(style.PALETTE["A"], style.PALETTE["B"])

    def color_of(z):
        in_a = rep_a_c.get(z) == ra
        in_b = rep_b_c.get(z) == rb
        if in_a and in_b:
            return overlap_color
        if in_a:
            return a_light
        if in_b:
            return b_light
        return style.PALETTE["unsolved"]

    legend = [Line2D([], [], marker="s", ls="", color=style.PALETTE["A"],
                     label=f"A legacy (rep {ra})"),
             Line2D([], [], marker="s", ls="", color=style.PALETTE["B"],
                    label=f"B legacy (rep {rb})")]
    maps.choropleth(ax, polys_c, color_of, bounds=bounds_c, title="pair in context",
                    legend=legend)

    edges_c = ctx.get("edges")
    if edges_c:
        pos_dict = {z: ctx["pos"][i] for i, z in enumerate(nodes_c)}
        edge_pairs = [(nodes_c[i], nodes_c[j]) for i, j in edges_c]
        pair_zips = set(d["nodes"])
        seg = geom.partition_boundary(edge_pairs, pos_dict, lambda z: z in pair_zips)
        maps.boundary(ax, seg, color=style.PALETTE["neutral"], lw=1.6)

    metros = ctx.get("metros")
    if metros:
        maps.seeds(ax, metros, n=len(nodes_c))


def _log_ratio_panel(ax, polys, bounds, nodes, ua, ub):
    """Row-2 col-1 (wide): log(u_a/u_b) on a diverging blue-red scale centred at 0 -- the
    quantity that actually drives the allocation, unlike the shared-scale u_a/u_b heat
    maps (both dominated by the common lam*M term; ratio spans only ~0.95-1.15 there).
    Zero-value zips (u_a = u_b = 0) are drawn in the `unsolved` grey, not on the scale."""
    ua = np.asarray(ua, float)
    ub = np.asarray(ub, float)
    zero_mask = (ua <= 0) & (ub <= 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = np.log(ua) - np.log(ub)
    raw = np.where(zero_mask, np.nan, raw)
    finite = raw[np.isfinite(raw)]
    if finite.size:
        L = float(np.max(np.abs(finite)))
        rmin, rmax = float(finite.min()), float(finite.max())
    else:
        L, rmin, rmax = 1e-9, 0.0, 0.0
    if L <= 0:
        L = 1e-9
    clipped = np.clip(np.nan_to_num(raw, nan=0.0, posinf=L, neginf=-L), -L, L)

    grey_zips = [z for i, z in enumerate(nodes) if zero_mask[i] and z in polys]
    values = {z: float(clipped[i]) for i, z in enumerate(nodes)
             if not zero_mask[i] and z in polys}

    title = f"log $u_a/u_b$ ∈ [{rmin:+.2f}, {rmax:+.2f}]"
    if grey_zips:
        maps.choropleth(ax, {z: polys[z] for z in grey_zips}, lambda z: style.PALETTE["unsolved"],
                        bounds=bounds)
    if values:
        maps.heatmap(ax, {z: polys[z] for z in values}, values, bounds=bounds,
                    cmap=CMAP_RATIO, vmin=-L, vmax=L, title=title,
                    cbar_label="log($u_a/u_b$)")
    else:
        ax.axis("off")
        ax.text(0.5, 0.5, "all $u_a = u_b = 0$", ha="center", va="center", fontsize=8,
                transform=ax.transAxes)


def build(d: dict) -> plt.Figure:
    v = schemas.validate_instance_json(d)
    if v:
        raise ValueError(f"invalid instance JSON: {v[:5]}")
    style.use_rc()
    nodes = d["nodes"]
    polys, bounds = geom.polys_from_pos(nodes, d["pos"])
    spec = d["spec"]
    theta = spec.get("params", {}).get("theta", 0.40)
    lam = spec.get("params", {}).get("lam", 0.30)
    ra, rb = spec.get("rep_a"), spec.get("rep_b")
    ua, ub = _common.utilities(d["A"], d["B"], d["M"], theta, lam)
    ua_map = dict(zip(nodes, ua.tolist()))
    ub_map = dict(zip(nodes, ub.tolist()))
    vmin, vmax = float(min(ua.min(), ub.min())), float(max(ua.max(), ub.max()))

    # `constrained_layout` (not `style.tight_layout`): with a GridSpec of equal-aspect map
    # panels, `Figure.tight_layout()` reserves generic tick/label margins that go unused
    # once `ax.set_aspect("equal")` shrinks each panel, leaving wide top/bottom bands
    # (measured ~17% of the canvas with `tight_layout`, one of this unit's fixes) --
    # `constrained_layout` sizes each row from the panels actually placed in it instead.
    fig = plt.figure(figsize=style.FIGSIZE["card"], layout="constrained")
    fig.suptitle(spec.get("name", "instance"), fontsize=11)
    gs = GridSpec(2, 6, figure=fig, hspace=0.12, wspace=0.12)
    ax_ctx = fig.add_subplot(gs[0, 0:2])
    ax_free = fig.add_subplot(gs[0, 2:4])
    ax_inc = fig.add_subplot(gs[0, 4:6])
    ax_ratio = fig.add_subplot(gs[1, 0:3])
    ax_ua = fig.add_subplot(gs[1, 3])
    ax_ub = fig.add_subplot(gs[1, 4])
    ax_cov = fig.add_subplot(gs[1, 5])

    # -- pair in context ------------------------------------------------------
    _context_panel(ax_ctx, d, ra, rb)

    # -- free-Nash map ---------------------------------------------------------
    free = set(d.get("free_to_a") or [])
    k_free = sum(1 for z in nodes if z in free)
    maps.choropleth(ax_free, polys,
                    lambda z: style.PALETTE["A"] if z in free else style.PALETTE["B"],
                    bounds=bounds, title="free Nash", legend=_ab_legend(k_free, len(nodes)))

    # -- best contiguous incumbent (grey = unsolved) --------------------------
    best = _best_contiguous_row(d.get("rows"))
    if best is None:
        maps.choropleth(ax_inc, polys, lambda z: style.PALETTE["unsolved"], bounds=bounds,
                        title="best contiguous incumbent\n(unsolved)")
    else:
        to_a = set(best["to_a"])
        k_inc = sum(1 for z in nodes if z in to_a)
        pa, pb = best.get("pieces_a"), best.get("pieces_b")
        pieces_str = f"{pa}/{pb}" if pa is not None and pb is not None else "?/?"
        maps.choropleth(ax_inc, polys,
                        lambda z: style.PALETTE["A"] if z in to_a else style.PALETTE["B"],
                        bounds=bounds, legend=_ab_legend(k_inc, len(nodes)),
                        title=f"best contiguous incumbent\n{best.get('method','?')}, "
                              f"{best.get('status_eff', best.get('status','?'))}, "
                              f"pieces {pieces_str}")

    # -- log(u_a/u_b) ratio map (the panel that explains the allocation) -----
    _log_ratio_panel(ax_ratio, polys, bounds, nodes, ua, ub)

    # -- u_a / u_b heatmaps on a shared scale ---------------------------------
    maps.heatmap(ax_ua, polys, ua_map, bounds=bounds, cmap=style.PALETTE["cmap_ua"],
                vmin=vmin, vmax=vmax, title=r"$u_a(z)$", cbar_label="value")
    maps.heatmap(ax_ub, polys, ub_map, bounds=bounds, cmap=style.PALETTE["cmap_ub"],
                vmin=vmin, vmax=vmax, title=r"$u_b(z)$", cbar_label="value")

    # -- covariate box ---------------------------------------------------------
    ax_cov.axis("off")
    cov = d.get("covariates") or {}
    lines = [f"n = {len(nodes)}", f"tier = {spec.get('tier')}", f"seed = {spec.get('seed')}"]
    for kk in ("pair_components", "articulation_points", "block_tree_is_path",
              "active_frac", "gini_u", "top5_share_u", "n_states"):
        if kk in cov:
            val = cov[kk]
            lines.append(f"{kk} = {val:.3g}" if isinstance(val, float) else f"{kk} = {val}")
    ax_cov.text(0.0, 1.0, "\n".join(lines), family="monospace", fontsize=6.5, va="top",
               transform=ax_cov.transAxes)
    ax_cov.set_title("covariates", fontsize=8)

    return fig


def main(argv=None):
    p = _common.base_parser(__doc__)
    p.add_argument("instance_json")
    p.add_argument("--rows", help="rows.jsonl to join by instance name, for the 'best "
                   "contiguous incumbent' panel -- phase-1 instance JSONs carry rows=null "
                   "by design (PLAN.md ★1 Q5)")
    args = p.parse_args(argv)
    d = _common.load_json(args.instance_json)
    if args.rows and d.get("rows") is None:
        name = (d.get("spec") or {}).get("name")
        joined = [r for r in _common.load_jsonl(args.rows) if r.get("instance") == name]
        d = dict(d, rows=joined)
    fig = build(d)
    style.check_text_overlap(fig)
    style.save(fig, args.out, inputs=[args.instance_json], producer="instance_card")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
