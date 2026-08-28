"""
mapviz.py -- shared "zip codes on a map" rendering for the battery figures.

The battery's _draw_map used to plot each zip as a small dot at its synthetic (x, y)
position, joined by thin grey adjacency edges -- a node-link graph, not a map. This
module instead tiles the plane with a bounded Voronoi diagram (one cell per zip) and
fills each cell with its assignment color, so a battery figure reads the way a real
ZCTA choropleth does: contiguous colored parcels with thin white seams, not a scatter
of points. Styling (spines off, tick direction, font sizes) matches mkfig_census.py so
every battery figure and the census-stress figure look like one family.

Public entry point: draw_zip_map(ax, G, color_of, title, legend=None).
"""
from __future__ import annotations
import numpy as np
from scipy.spatial import Voronoi
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D

METRO_MARKER = dict(marker="*", s=120, c="black", edgecolors="white",
                    linewidths=0.7, zorder=3)


def _draw_metros(ax, metro_pos):
    if metro_pos is None or len(metro_pos) == 0:
        return
    mp = np.asarray(metro_pos, float)
    ax.scatter(mp[:, 0], mp[:, 1], **METRO_MARKER)

MAP_RC = {
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 6, "ytick.labelsize": 6, "legend.fontsize": 7,
    "axes.spines.top": False, "axes.spines.right": False,
    "xtick.direction": "out", "ytick.direction": "out",
}


# --------------------------------------------------------------- bounded Voronoi
def _finite_polygons(vor, radius):
    """Reconstruct each Voronoi region as a finite polygon (standard 'close the
    infinite ridges at a far radius' recipe), indexed by input point order."""
    new_regions = []
    new_vertices = vor.vertices.tolist()
    center = vor.points.mean(axis=0)

    all_ridges = {}
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        all_ridges.setdefault(p1, []).append((p2, v1, v2))
        all_ridges.setdefault(p2, []).append((p1, v1, v2))

    for p1, region_idx in enumerate(vor.point_region):
        vertices = vor.regions[region_idx]
        if all(v >= 0 for v in vertices):
            new_regions.append(vertices)
            continue
        ridges = all_ridges.get(p1, [])
        new_region = [v for v in vertices if v >= 0]
        for p2, v1, v2 in ridges:
            if v2 < 0:
                v1, v2 = v2, v1
            if v1 >= 0:
                continue  # both finite, already included / interior ridge
            t = vor.points[p2] - vor.points[p1]
            t /= np.linalg.norm(t)
            n = np.array([-t[1], t[0]])
            midpoint = vor.points[[p1, p2]].mean(axis=0)
            direction = np.sign(np.dot(midpoint - center, n)) * n
            far_point = vor.vertices[v2] + direction * radius
            new_region.append(len(new_vertices))
            new_vertices.append(far_point.tolist())
        vs = np.asarray([new_vertices[v] for v in new_region])
        c = vs.mean(axis=0)
        angles = np.arctan2(vs[:, 1] - c[1], vs[:, 0] - c[0])
        new_region = np.array(new_region)[np.argsort(angles)]
        new_regions.append(new_region.tolist())
    return new_regions, np.asarray(new_vertices)


def _clip_poly(poly, xmin, xmax, ymin, ymax):
    """Sutherland-Hodgman clip of a convex polygon to an axis-aligned box."""
    def clip_edge(pts, inside, intersect):
        out = []
        n = len(pts)
        for i in range(n):
            cur, prv = pts[i], pts[i - 1]
            cur_in, prv_in = inside(cur), inside(prv)
            if cur_in:
                if not prv_in:
                    out.append(intersect(prv, cur))
                out.append(cur)
            elif prv_in:
                out.append(intersect(prv, cur))
        return out

    def isect(a, b, coord, val):
        t = (val - a[coord]) / (b[coord] - a[coord])
        p = a + t * (b - a)
        return p

    pts = [np.asarray(p, float) for p in poly]
    edges = [
        (lambda p: p[0] >= xmin, lambda a, b: isect(a, b, 0, xmin)),
        (lambda p: p[0] <= xmax, lambda a, b: isect(a, b, 0, xmax)),
        (lambda p: p[1] >= ymin, lambda a, b: isect(a, b, 1, ymin)),
        (lambda p: p[1] <= ymax, lambda a, b: isect(a, b, 1, ymax)),
    ]
    for inside, intersect in edges:
        if not pts:
            break
        pts = clip_edge(pts, inside, intersect)
    return pts


def zip_polygons(G, pad=0.035):
    """Bounded Voronoi cell (list of (x, y) vertices) per node of G, clipped to the
    layout's bounding box padded by `pad`. Returns {node: polygon_vertices}."""
    nodes = list(G)
    P = np.array([G.nodes[z]["pos"] for z in nodes], float)
    xmin, ymin = P.min(axis=0) - pad
    xmax, ymax = P.max(axis=0) + pad
    if len(P) < 4:
        # degenerate: fall back to a shared box, unused in practice (battery n>=44)
        box = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        return {z: box for z in nodes}
    vor = Voronoi(P)
    radius = max(xmax - xmin, ymax - ymin) * 4
    regions, vertices = _finite_polygons(vor, radius)
    out = {}
    for z, region in zip(nodes, regions):
        poly = vertices[region]
        out[z] = _clip_poly(poly, xmin, xmax, ymin, ymax)
    return out, (xmin, xmax, ymin, ymax)


# ------------------------------------------------------------------ drawing
def draw_zip_map(ax, G, color_of, title, legend=None, polys=None, edge_lw=0.25,
                 edge_color="white", fontsize=9, metro_pos=None):
    """Fill each zip's Voronoi cell with color_of(z); thin light seams between
    cells so adjoining zips read as separate parcels, the way a real ZCTA
    choropleth does. `polys` lets callers precompute geometry once and reuse it
    across the several panels that share one instance's layout. `metro_pos`
    (G.graph["metros"], an (n_metros, 2) array of the synthetic-geography Gaussian
    mixture centers -- the closest analogue this synthetic data has to real
    metropolitan cores) overlays a star marker at each one, so the choropleth
    panels show where the underlying population/opportunity density is centered,
    not just the resulting territory colors."""
    if polys is None:
        polys, bounds = zip_polygons(G)
    else:
        polys, bounds = polys
    nodes = list(G)
    verts = [polys[z] for z in nodes if len(polys[z]) >= 3]
    cols = [color_of(z) for z in nodes if len(polys[z]) >= 3]
    pc = PolyCollection(verts, facecolors=cols, edgecolors=edge_color,
                        linewidths=edge_lw, zorder=2)
    ax.add_collection(pc)
    xmin, xmax, ymin, ymax = bounds
    ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=fontsize)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    _draw_metros(ax, metro_pos)
    if legend:
        if metro_pos is not None and len(metro_pos):
            legend = list(legend) + [
                Line2D([], [], marker="*", ls="", color="black",
                      markeredgecolor="white", markersize=8, label="metro center")]
        ax.legend(handles=legend, fontsize=6, loc="lower left", frameon=False,
                  ncol=2, handletextpad=0.3, columnspacing=0.8)
    return (polys, bounds)


def draw_zip_heatmap(ax, G, values, title, cmap="Blues", polys=None,
                     metro_pos=None, vmin=None, vmax=None, fontsize=9,
                     cbar_label=None):
    """Fill each zip's Voronoi cell by a continuous scalar (e.g. the pointwise
    gains field u_a(z) or u_b(z) that g_a/g_b sum over an assignment) using a
    single-hue sequential colormap, light->dark, with an inline colorbar --
    same geometry and framing conventions as draw_zip_map so heatmap and
    choropleth panels read as one figure family. `values`: {node: float}."""
    if polys is None:
        polys, bounds = zip_polygons(G)
    else:
        polys, bounds = polys
    nodes = list(G)
    keep = [z for z in nodes if len(polys[z]) >= 3]
    verts = [polys[z] for z in keep]
    vals = np.array([values[z] for z in keep], float)
    vmin = float(vals.min()) if vmin is None else vmin
    vmax = float(vals.max()) if vmax is None else vmax
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap_obj = plt.get_cmap(cmap)
    cols = cmap_obj(norm(vals))
    pc = PolyCollection(verts, facecolors=cols, edgecolors="white",
                        linewidths=0.2, zorder=2)
    ax.add_collection(pc)
    xmin, xmax, ymin, ymax = bounds
    ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=fontsize)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    _draw_metros(ax, metro_pos)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap_obj)
    sm.set_array([])
    cb = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.02)
    cb.ax.tick_params(labelsize=6)
    if cbar_label:
        cb.set_label(cbar_label, fontsize=6)
    return (polys, bounds)
