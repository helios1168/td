"""
gfx/producers/instance_card.py -- the instance card (PLAN.md Part D "Common figure set",
redesigned U11; geometry, legends and layout fixed U12).

Panels (nested GridSpecs, no blank cells):
  row 1: pair-in-context (the pair's zips inside the whole synthetic instance, the two
         legacy territories coloured, the pair traced along the actual cell boundary) ·
         free-Nash map · best contiguous incumbent (grey = unsolved) -- three columns
  row 2: log(u_a/u_b) ratio map (wide -- the quantity that actually drives the
         allocation; a shared-scale u_a/u_b heat map is dominated by the common lam*M
         term and looks near-identical for both reps) · u_a heatmap · u_b heatmap
         (shared scale) · covariate box -- width_ratios=[3, 1.5, 1.5, 1], so u_a/u_b
         render close to half of the log-ratio panel's height instead of a sliver

**One tessellation for the whole card (U12).** When the instance JSON carries the optional
`context` block (the whole parent instance the pair was cut from), the Voronoi cells are
built *once* from the parent's positions and every panel reuses them: the context panel
draws all of them, the pair panels draw the same polygons windowed on the pair's bounding
box, with the non-pair cells in `style.PALETTE["outside"]` so the pair keeps its true
silhouette. Before U12 the pair panels re-tessellated the pair's own positions, so the
pair's cells stretched to fill the pair's bounding box and the pair rendered as a full
rectangle of a completely different shape from the region outlined in the context panel --
the same zips, two irreconcilable geometries on one card. Without a `context` block
(pre-U11 JSONs, fixtures) the pair-only tessellation is the fallback and every panel title
says so.

U11 replaced the old "pre-merger firm A / firm B territories" panels (two uniform,
information-free blocks -- inside a pair every zip belongs to the pair's two reps by
construction) with one pair-context panel, and added the log-ratio map.

Usage:
    python -m gfx.producers.instance_card <instance.json> --out <png>
    python -m gfx.producers.instance_card <instance.json> --rows <rows.jsonl> --out <png>
"""
from __future__ import annotations

import os
import sys

# run either as `python -m gfx.producers.instance_card` or as a plain script path
# (`python code/gfx/producers/instance_card.py ...`, the form the harness runbooks use):
# the latter gives the module no package, so the `from .. import ...` below would fail with
# "attempted relative import with no known parent package". PEP 366's fix -- put `code/` on
# the path and name the package -- makes both invocations work.
if __name__ == "__main__" and __package__ in (None, ""):  # pragma: no cover - CLI only
    sys.path.insert(0, os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    __package__ = "gfx.producers"
    import gfx.producers  # noqa: F401

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

from .. import geom, maps, schemas, style
from . import _common

# diverging colormap for the log(u_a/u_b) panel: A-blue at the positive end, B-red at the
# negative end (matplotlib's "RdBu" runs red-white-blue low-to-high, i.e. exactly this way
# round) -- defined here, not in style.py, since this producer owns it (no new shared
# primitive needed).
CMAP_RATIO = "RdBu"

# legend placement for every map panel on the card: centred just *below* the axes. A legend
# inside the axes (maps.LEGEND_KW's "lower left" default) sits on top of the cells it
# describes -- on a pair whose region reaches the bottom-left corner it is unreadable and
# hides data (U12 item 4). Both row-1 legends use the same anchor so the three panels keep
# a common footprint.
LEGEND_BELOW = dict(loc="upper center", bbox_to_anchor=(0.5, -0.012), frameon=False,
                    fontsize=6, borderaxespad=0.0)

# window padding around the pair's cells in the pair panels, as a fraction of the pair's
# larger bbox dimension
PAIR_PAD_FRAC = 0.02

# gap (figure fraction) between an aspect-shrunk map panel and its colorbar
CBAR_PAD = 0.006


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


# ------------------------------------------------------------------- shared geometry
def _bbox_of(polys, clip=None, pad_frac=PAIR_PAD_FRAC):
    """(xmin, xmax, ymin, ymax) over `polys`'s vertices, padded by `pad_frac` of the larger
    dimension and clipped to `clip` (the parent tessellation's bounds) so the window never
    shows empty space outside the instance."""
    verts = [v for v in polys.values() if len(v) >= 3]
    if not verts:
        return clip if clip else (0.0, 1.0, 0.0, 1.0)
    allv = np.concatenate(verts)
    xmin, ymin = allv.min(axis=0)
    xmax, ymax = allv.max(axis=0)
    pad = pad_frac * max(xmax - xmin, ymax - ymin, 1e-9)
    b = [xmin - pad, xmax + pad, ymin - pad, ymax + pad]
    if clip:
        b = [max(b[0], clip[0]), min(b[1], clip[1]), max(b[2], clip[2]), min(b[3], clip[3])]
    return tuple(float(x) for x in b)


def _geometry(d):
    """The card's single tessellation (U12).

    With a usable `context` block the cells come from the *parent* instance's positions, so
    the pair's polygons are literally the same objects in the context panel and in every
    pair panel; `bounds` windows the pair panels onto the pair. Without one, each panel
    falls back to the pre-U11 pair-only tessellation (`shared=False`), which is a different
    geometry -- flagged in the panel titles rather than silently mixed.
    """
    nodes = list(d["nodes"])
    pairset = set(nodes)
    ctx = d.get("context")
    if ctx and pairset.issubset(set(ctx["nodes"])):
        ctx_polys, ctx_bounds = geom.polys_from_pos(ctx["nodes"], ctx["pos"])
        polys = {z: ctx_polys[z] for z in nodes if z in ctx_polys}
        outside = {z: p for z, p in ctx_polys.items() if z not in pairset}
        seg = geom.partition_boundary(ctx_polys, side_of=lambda z: z in pairset)
        return dict(shared=True, ctx=ctx, ctx_polys=ctx_polys, ctx_bounds=ctx_bounds,
                    polys=polys, outside=outside, bounds=_bbox_of(polys, ctx_bounds),
                    pairset=pairset, pair_boundary=seg)
    polys, bounds = geom.polys_from_pos(nodes, d["pos"])
    return dict(shared=False, ctx=None, ctx_polys=None, ctx_bounds=None,
                polys=polys, outside={}, bounds=bounds, pairset=pairset,
                pair_boundary=np.empty((0, 2, 2)))


def _pair_title(gg, title):
    """Panel title, marked when the card fell back to the pair-only tessellation so the
    reader is never left to assume the panels share the context panel's geometry."""
    return title if gg["shared"] else f"{title}\n(pair-only cells; no context in JSON)"


def _outside_layer(ax, gg):
    """Draw the parent instance's non-pair cells behind a pair panel, in the neutral
    `outside` fill. Same polygons as the context panel, so the pair's silhouette in a pair
    panel matches the outlined region in the context panel exactly."""
    if not gg["shared"] or not gg["outside"]:
        return
    maps.choropleth(ax, gg["outside"], lambda z: style.PALETTE["outside"],
                    bounds=gg["bounds"])


def _pair_outline(ax, gg, lw=0.9):
    """The pair's boundary traced along the real cell ridges (`geom.partition_boundary`'s
    polygon form), overlaid on a pair panel so the pair reads as one region even where the
    allocation colours run right up to the outside fill."""
    if gg["shared"] and len(gg["pair_boundary"]):
        maps.boundary(ax, gg["pair_boundary"], color=style.PALETTE["neutral"], lw=lw)


# --------------------------------------------------------------------------- panels
def _context_panel(ax, d, gg, ra, rb):
    """Row-1 col-1: the pair's zips drawn inside the whole synthetic instance. Every zip of
    the parent graph that neither legacy rep owns in the neutral `outside` fill; the zips
    owned by the pair's firm-A rep `ra` only, resp. its firm-B rep `rb` only, in light
    A-blue / B-red; their overlap -- exactly the pair's own zips, by `zips_for_pair`'s
    definition -- blended, with the pair's cell-ridge outline over it; metro seeds if
    present.

    The legend lists only the classes that actually have cells, each with its count (U12
    item 2): in the *aligned* scenarios (C1/C7/C9) the two legacy territories coincide
    exactly, so "A legacy only" and "B legacy only" are empty by construction and the old
    fixed three-entry legend promised colours that never appeared. That is a data fact, not
    a `color_of` bug -- the subtitle says so when it happens.

    "no context in JSON" when the (optional) `context` block is absent."""
    ctx = gg["ctx"]
    if not ctx:
        # top-aligned, not centred: with the other row-1 panels anchored north an
        # explanation floating in the middle of the cell reads as a stray caption
        ax.axis("off")
        ax.text(0.5, 1.0, "no context in JSON\n(pair-only cells in every panel)",
                ha="center", va="top", fontsize=8, transform=ax.transAxes)
        return
    nodes_c = ctx["nodes"]
    polys_c = gg["ctx_polys"]
    rep_a_c = dict(zip(nodes_c, ctx["rep_a"]))
    rep_b_c = dict(zip(nodes_c, ctx["rep_b"]))
    a_light, b_light = _lighten(style.PALETTE["A"]), _lighten(style.PALETTE["B"])
    overlap_color = _blend(style.PALETTE["A"], style.PALETTE["B"])

    def class_of(z):
        return (rep_a_c.get(z) == ra, rep_b_c.get(z) == rb)

    fills = {(True, True): overlap_color, (True, False): a_light,
             (False, True): b_light, (False, False): style.PALETTE["outside"]}
    counts = {k: 0 for k in fills}
    for z in polys_c:
        counts[class_of(z)] += 1
    n_pair, n_ctx = counts[(True, True)], len(nodes_c)

    labels = {
        (True, True): f"this pair = A-rep {ra} ∩ B-rep {rb}: {n_pair} zips",
        (True, False): f"A-rep {ra} legacy only: {counts[(True, False)]} zips",
        (False, True): f"B-rep {rb} legacy only: {counts[(False, True)]} zips",
        (False, False): f"other reps' zips: {counts[(False, False)]}",
    }
    order = [(True, True), (True, False), (False, True), (False, False)]
    legend = [Line2D([], [], marker="s", ls="", color=fills[k], markeredgecolor="0.7",
                     markeredgewidth=0.4, label=labels[k])
              for k in order if counts[k]]
    metros = ctx.get("metros")
    if metros:
        # the stars were unlegended before U12 (item 3): unexplained markers on a map are a
        # defect whether or not the marker is meaningful. They are the generator's metro
        # seeds -- the centres the synthetic value field is built around.
        legend.append(Line2D([], [], marker="*", ls="", color="black",
                             markeredgecolor="white", markeredgewidth=0.4, markersize=6,
                             label=f"metro seed ({len(metros)})"))

    coincide = counts[(True, False)] == 0 and counts[(False, True)] == 0
    sub = f"{n_pair} of {n_ctx} zips ({100.0 * n_pair / max(n_ctx, 1):.0f}%)"
    if coincide:
        sub += f" — A-rep {ra} and B-rep {rb} hold identical territories"
    maps.choropleth(ax, polys_c, lambda z: fills[class_of(z)], bounds=gg["ctx_bounds"],
                    title=f"pair in context\n{sub}", legend=legend,
                    legend_kw=dict(LEGEND_BELOW, ncol=1))

    # the pair's own outline, traced along the actual Voronoi/cell boundary (the ridge
    # between in-pair and out-of-pair polygons) rather than schematic straight lines
    # between adjacency-graph node centers -- avoids the "spiky segments sticking out of
    # the region" artifact edge-based tracing produced, and needs no `context.edges` at
    # all (works purely from `polys_c`'s geometry). Thinner since U12: at lw=1.5 the
    # irregular ridge read as a spiky drawing error rather than as the region's edge.
    _pair_outline(ax, gg, lw=1.0)

    if metros:
        maps.seeds(ax, metros, size=26)


def _log_ratio_panel(ax, gg, nodes, ua, ub):
    """Row-2 col-1 (wide): log(u_a/u_b) on a diverging blue-red scale centred at 0 -- the
    quantity that actually drives the allocation, unlike the shared-scale u_a/u_b heat
    maps (both dominated by the common lam*M term; ratio spans only ~0.95-1.15 there).
    Zero-value zips (u_a = u_b = 0) are drawn in the `unsolved` grey, not on the scale."""
    polys, bounds = gg["polys"], gg["bounds"]
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

    title = _pair_title(gg, f"log $u_a/u_b$ ∈ [{rmin:+.2f}, {rmax:+.2f}]")
    _outside_layer(ax, gg)
    if grey_zips:
        maps.choropleth(ax, {z: polys[z] for z in grey_zips}, lambda z: style.PALETTE["unsolved"],
                        bounds=bounds)
    if values:
        _, cb = maps.heatmap(ax, {z: polys[z] for z in values}, values, bounds=bounds,
                            cmap=CMAP_RATIO, vmin=-L, vmax=L, title=title,
                            cbar_label="log($u_a/u_b$)")
        _pair_outline(ax, gg)
        return cb
    ax.axis("off")
    ax.text(0.5, 0.5, "all $u_a = u_b = 0$", ha="center", va="center", fontsize=8,
            transform=ax.transAxes)
    return None


def _align_panel_tops(fig, map_axes, cbars, fit_to_row=()):
    """Pin every map panel to the top of its gridspec cell and cut each colorbar down to
    its panel's rendered height (U12 item 5).

    Two things fight the reader here. (i) A map panel is aspect-locked, so matplotlib
    shrinks its axes box inside its cell; the default centre anchor then floats a wide
    (landscape) pair panel in the middle of a row whose other panel is square, and the
    row's titles stop lining up. (ii) `Figure.colorbar(ax=...)` *re-sets the parent's
    anchor* (to left-centre for a right-hand colorbar) as it steals space, so the anchor
    has to be (re)applied after every panel is drawn, not at axes-creation time.

    The colorbars are sized against the cell, not the shrunken panel, so they tower over
    the maps they annotate. Fixing that needs the panels' *rendered* geometry, which only
    exists after a draw -- hence: draw once, freeze the layout engine, then match each
    colorbar's vertical extent to its panel's.

    `fit_to_row` -- (ax, [row panels]) pairs -- does the same for a text-only panel (the
    covariate box), which has no aspect to shrink it and would otherwise keep its full-cell
    height: `savefig(bbox_inches="tight")` measures *that* box and leaves a band of blank
    canvas under the whole figure once the colorbars no longer fill the row.
    """
    for ax in map_axes:
        ax.set_anchor("N")
    fig.canvas.draw()
    fig.set_layout_engine("none")
    for ax, cb in cbars:
        if cb is None:
            continue
        p, q = ax.get_position(), cb.ax.get_position()
        # ...and pull it back against the panel: an aspect-shrunk panel leaves a gap up to
        # the width of its cell between map and colorbar, which reads as an unrelated strip
        cb.ax.set_position([min(q.x0, p.x1 + CBAR_PAD), p.y0, q.width, p.height])
    for ax, row in fit_to_row:
        boxes = [a.get_position() for a in row]
        if not boxes:
            continue
        y0, y1 = min(b.y0 for b in boxes), max(b.y1 for b in boxes)
        q = ax.get_position()
        ax.set_position([q.x0, y0, q.width, y1 - y0])


def build(d: dict) -> plt.Figure:
    v = schemas.validate_instance_json(d)
    if v:
        raise ValueError(f"invalid instance JSON: {v[:5]}")
    style.use_rc()
    nodes = d["nodes"]
    gg = _geometry(d)
    polys, bounds = gg["polys"], gg["bounds"]
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
    # (measured ~17% of the canvas with `tight_layout`, one of U11's fixes) --
    # `constrained_layout` sizes each row from the panels actually placed in it instead.
    fig = plt.figure(figsize=style.FIGSIZE["card"], layout="constrained")
    fig.suptitle(spec.get("name", "instance"), fontsize=11)
    # Nested gridspecs (not one shared 2x6 grid): row 1's three equal panels and row 2's
    # log-ratio/u_a/u_b/covariates mix need different column proportions, and row 2's
    # panels are aspect-locked squares whose *rendered* size is set by the narrower of
    # (their column width, the row height) -- giving u_a/u_b only 1/6 of the row's width
    # (the original 6-column grid) made them render far smaller than "half the log-ratio
    # panel's height": they were width-limited to a square a fraction of log-ratio's size,
    # not height-limited like log-ratio itself. width_ratios=[3, 1.5, 1.5, 1] here fixes
    # that -- u_a/u_b now get enough column width to render close to half of log-ratio's
    # rendered height (both are still ultimately height-limited or width-limited by their
    # own cell, never stretched past their data's equal-area aspect).
    outer = fig.add_gridspec(2, 1, hspace=0.12)
    gs_top = outer[0].subgridspec(1, 3, wspace=0.12)
    gs_bot = outer[1].subgridspec(1, 4, wspace=0.12, width_ratios=[3, 1.5, 1.5, 1])
    ax_ctx = fig.add_subplot(gs_top[0, 0])
    ax_free = fig.add_subplot(gs_top[0, 1])
    ax_inc = fig.add_subplot(gs_top[0, 2])
    ax_ratio = fig.add_subplot(gs_bot[0, 0])
    ax_ua = fig.add_subplot(gs_bot[0, 1])
    ax_ub = fig.add_subplot(gs_bot[0, 2])
    ax_cov = fig.add_subplot(gs_bot[0, 3])

    # -- pair in context ------------------------------------------------------
    _context_panel(ax_ctx, d, gg, ra, rb)

    # -- free-Nash map ---------------------------------------------------------
    free = set(d.get("free_to_a") or [])
    k_free = sum(1 for z in nodes if z in free)
    _outside_layer(ax_free, gg)
    maps.choropleth(ax_free, polys,
                    lambda z: style.PALETTE["A"] if z in free else style.PALETTE["B"],
                    bounds=bounds, title=_pair_title(gg, "free Nash"),
                    legend=_ab_legend(k_free, len(nodes)), legend_kw=LEGEND_BELOW)
    _pair_outline(ax_free, gg)

    # -- best contiguous incumbent (grey = unsolved) --------------------------
    best = _best_contiguous_row(d.get("rows"))
    _outside_layer(ax_inc, gg)
    if best is None:
        maps.choropleth(ax_inc, polys, lambda z: style.PALETTE["unsolved"], bounds=bounds,
                        title=_pair_title(gg, "best contiguous incumbent\n(unsolved)"))
    else:
        to_a = set(best["to_a"])
        k_inc = sum(1 for z in nodes if z in to_a)
        pa, pb = best.get("pieces_a"), best.get("pieces_b")
        pieces_str = f"{pa}/{pb}" if pa is not None and pb is not None else "?/?"
        maps.choropleth(ax_inc, polys,
                        lambda z: style.PALETTE["A"] if z in to_a else style.PALETTE["B"],
                        bounds=bounds, legend=_ab_legend(k_inc, len(nodes)),
                        legend_kw=LEGEND_BELOW,
                        title=_pair_title(
                            gg, f"best contiguous incumbent\n{best.get('method','?')}, "
                                f"{best.get('status_eff', best.get('status','?'))}, "
                                f"pieces {pieces_str}"))
    _pair_outline(ax_inc, gg)

    # -- log(u_a/u_b) ratio map (the panel that explains the allocation) -----
    cb_ratio = _log_ratio_panel(ax_ratio, gg, nodes, ua, ub)

    # -- u_a / u_b heatmaps on a shared scale ---------------------------------
    cbars = [(ax_ratio, cb_ratio)]
    for ax, vals, cmap, title in ((ax_ua, ua_map, style.PALETTE["cmap_ua"], r"$u_a(z)$"),
                                  (ax_ub, ub_map, style.PALETTE["cmap_ub"], r"$u_b(z)$")):
        _outside_layer(ax, gg)
        _, cb = maps.heatmap(ax, polys, vals, bounds=bounds, cmap=cmap, vmin=vmin, vmax=vmax,
                             title=_pair_title(gg, title), cbar_label="value")
        _pair_outline(ax, gg)
        cbars.append((ax, cb))

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

    _align_panel_tops(fig, (ax_ctx, ax_free, ax_inc, ax_ratio, ax_ua, ax_ub), cbars,
                      fit_to_row=((ax_cov, (ax_ratio, ax_ua, ax_ub)),))
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
