"""
gfx/maps.py -- axes-level map primitives, built on `gfx.geom` polygons/segments.

Every function draws into an existing `ax` and returns it (or a small extra artist, e.g.
a colorbar) so callers compose multi-panel figures themselves. No dpi/rcParams/palette
choices live here -- those come from `gfx.style` only.
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection

from . import geom, style


def _apply_frame(ax, bounds, title=None, fontsize=9):
    xmin, xmax, ymin, ymax = bounds
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    if title:
        ax.set_title(title, fontsize=fontsize)


# default keyword arguments for an axes legend on a map panel. `choropleth(legend_kw=...)`
# overrides them per call -- U12 moved the card's map legends *outside* the axes
# (`loc="upper center"`, anchored just under the axes) because a legend at `loc="lower left"`
# sits on top of the cells it describes.
LEGEND_KW = dict(fontsize=6, loc="lower left", frameon=False, ncol=2, handletextpad=0.3,
                 columnspacing=0.8, borderaxespad=0.2)


def choropleth(ax, polys, color_of, *, bounds=None, legend=None, legend_kw=None, title=None,
               edge_color="white", edge_lw=None, fontsize=9):
    """Fill each node's polygon with `color_of(node)`. `polys`: {node: (m,2) ndarray}
    from `geom.polys_from_pos` / `geom.polys_from_shapes`. `edge_lw=None` derives the
    seam width from `geom.seam_width(len(polys))` (0 at n >= 5000: no seam haze).
    `legend_kw` overrides `LEGEND_KW` for this call (placement, columns, frame)."""
    nodes = list(polys)
    keep = [z for z in nodes if len(polys[z]) >= 3]
    verts = [polys[z] for z in keep]
    cols = [color_of(z) for z in keep]
    lw = geom.seam_width(len(nodes)) if edge_lw is None else edge_lw
    pc = PolyCollection(verts, facecolors=cols,
                        edgecolors=edge_color if lw > 0 else "none",
                        linewidths=lw, zorder=2)
    ax.add_collection(pc)
    if bounds is None:
        allv = np.concatenate(verts) if verts else np.array([[0, 0], [1, 1]])
        bounds = (allv[:, 0].min(), allv[:, 0].max(), allv[:, 1].min(), allv[:, 1].max())
    _apply_frame(ax, bounds, title, fontsize)
    if legend:
        kw = dict(LEGEND_KW)
        kw.update(legend_kw or {})
        ax.legend(handles=legend, **kw)
    return pc


def heatmap(ax, polys, values: dict, *, bounds=None, cmap="Blues", vmin=None, vmax=None,
           cbar=True, title=None, fontsize=9, cbar_label=None):
    """Fill each node's polygon by a continuous scalar with a single-hue sequential
    colormap and an inline colorbar. `values`: {node: float}."""
    nodes = list(polys)
    keep = [z for z in nodes if len(polys[z]) >= 3 and z in values]
    verts = [polys[z] for z in keep]
    vals = np.array([values[z] for z in keep], float)
    vmin = float(vals.min()) if vmin is None else vmin
    vmax = float(vals.max()) if vmax is None else vmax
    if vmax <= vmin:
        vmax = vmin + 1e-9
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    cmap_obj = plt.get_cmap(cmap)
    cols = cmap_obj(norm(vals))
    lw = geom.seam_width(len(nodes))
    pc = PolyCollection(verts, facecolors=cols,
                        edgecolors="white" if lw > 0 else "none",
                        linewidths=lw, zorder=2)
    ax.add_collection(pc)
    if bounds is None:
        allv = np.concatenate(verts) if verts else np.array([[0, 0], [1, 1]])
        bounds = (allv[:, 0].min(), allv[:, 0].max(), allv[:, 1].min(), allv[:, 1].max())
    _apply_frame(ax, bounds, title, fontsize)
    cb = None
    if cbar:
        sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap_obj)
        sm.set_array([])
        cb = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.02)
        cb.ax.tick_params(labelsize=6)
        if cbar_label:
            cb.set_label(cbar_label, fontsize=6)
    return pc, cb


def boundary(ax, segments, *, color=None, lw=1.3, zorder=4, **kwargs):
    """Bold line(s) along `segments` (from `geom.partition_boundary`), overlaid on a
    `choropleth` to make a partition's cut visible over the fill colours."""
    color = style.PALETTE["neutral"] if color is None else color
    segments = np.asarray(segments, float)
    lc = LineCollection(segments if len(segments) else [], colors=color, linewidths=lw,
                        zorder=zorder, **kwargs)
    ax.add_collection(lc)
    return lc


def adjacency(ax, segments, *, color="0.6", lw=0.3, alpha=0.6, zorder=1, **kwargs):
    """Thin line(s) along every adjacency edge (from `geom.edge_segments`); the node-link
    view `mapviz.py` used to draw by default, now an optional overlay."""
    segments = np.asarray(segments, float)
    lc = LineCollection(segments if len(segments) else [], colors=color, linewidths=lw,
                        alpha=alpha, zorder=zorder, **kwargs)
    ax.add_collection(lc)
    return lc


def seeds(ax, pos, *, n=None, size=None, marker="*", color="black", edgecolor="white",
          zorder=5, label=None):
    """Star marker(s) at `pos` ((k,2) array-like), sized by `geom.marker_scale(n)` --
    metro centers / rep bases, scaled so they stay legible from n~10 to n~30000. `size`
    (matplotlib `s`, points^2) overrides the derived size when a caller needs a legible
    marker on a panel with many cells but few seeds (U12: 5 metro stars on a 400-zip
    context map rendered as near-invisible dots)."""
    P = np.asarray(pos, float)
    if P.size == 0:
        return None
    if P.ndim == 1:
        P = P[None, :]
    s = size if size is not None else geom.marker_scale(n if n is not None else len(P))
    return ax.scatter(P[:, 0], P[:, 1], marker=marker, s=s, c=color,
                      edgecolors=edgecolor, linewidths=0.6, zorder=zorder, label=label)
