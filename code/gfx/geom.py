"""
gfx/geom.py -- polygon and segment geometry for the map primitives in `gfx.maps`.

Replaces `battery/code/mapviz.py::zip_polygons`: pad is relative to the bounding box
(not an absolute unit-square constant), the box clip is vectorised per polygon (numpy
ops across a polygon's vertices, not a Python float-by-float loop), and the `len(P) < 4`
degenerate case returns one polygon per node instead of a single unusable shared box.

Dependency policy: matplotlib + numpy + scipy only, except `polys_from_shapes`, which
imports shapely lazily inside the function body (PLAN.md Part D / the U7 brief's rule 6).
This module never imports networkx: `G` arguments are duck-typed -- anything with an
`.edges()` method (a networkx graph) or a plain iterable of `(u, v)` pairs works.
"""
from __future__ import annotations

import warnings

import numpy as np
from scipy.spatial import Voronoi


# --------------------------------------------------------------------------- scale rules
def seam_width(n: int) -> float:
    """Cell-border linewidth: 0.25 for n <= 500, linearly down to 0 at n >= 5000 (no seam
    haze at scale -- PLAN.md Part D scale rules)."""
    if n <= 500:
        return 0.25
    if n >= 5000:
        return 0.0
    t = (n - 500) / (5000 - 500)
    return 0.25 * (1.0 - t)


def marker_scale(n: int, base: float = 120.0) -> float:
    """Marker size (matplotlib `s`, points^2) scaled by 1/sqrt(n), floored so a single
    marker never vanishes."""
    return max(base / max(np.sqrt(max(n, 1)), 1.0), 6.0)


def assert_equal_area(pos) -> None:
    """Raise if `pos` looks like unprojected lon/lat degrees rather than an equal-area xy
    projection. Heuristic only (PLAN.md: "auto aspect (equal-area xy assumed; raise on
    lon/lat)"): degrees span at most 360x180 and typically sit in familiar lon/lat ranges;
    a genuine equal-area projection rescaled to [0, 1]^2 or in metres does not."""
    P = np.asarray(pos, float)
    if P.size == 0:
        return
    xmin, ymin = P.min(axis=0)
    xmax, ymax = P.max(axis=0)
    looks_lonlat = (-180.5 <= xmin <= 180.5 and -180.5 <= xmax <= 180.5
                    and -90.5 <= ymin <= 90.5 and -90.5 <= ymax <= 90.5
                    and (xmax - xmin) > 1.0)
    if looks_lonlat:
        raise ValueError(
            "positions look like unprojected lon/lat degrees "
            f"(bbox x=[{xmin:.2f},{xmax:.2f}] y=[{ymin:.2f},{ymax:.2f}]); "
            "gfx assumes an equal-area xy projection (twin.load_twin supplies LAEA)"
        )


def _pair_edges(G):
    """Normalise a duck-typed graph-or-edge-iterable to a list of (u, v) pairs."""
    if hasattr(G, "edges"):
        return list(G.edges())
    return list(G)


# --------------------------------------------------------------------------- Voronoi cells
def _finite_regions(vor: Voronoi, radius: float):
    """Reconstruct each Voronoi region as a finite (possibly unclipped) polygon, indexed
    by input point order. Standard "close the infinite ridges at a far radius" recipe."""
    new_regions = []
    new_vertices = vor.vertices.tolist()
    center = vor.points.mean(axis=0)

    all_ridges: dict = {}
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        all_ridges.setdefault(p1, []).append((p2, v1, v2))
        all_ridges.setdefault(p2, []).append((p1, v1, v2))

    for p1, region_idx in enumerate(vor.point_region):
        vertices = vor.regions[region_idx]
        if vertices and all(v >= 0 for v in vertices):
            new_regions.append(vertices)
            continue
        ridges = all_ridges.get(p1, [])
        new_region = [v for v in vertices if v >= 0]
        for p2, v1, v2 in ridges:
            if v2 < 0:
                v1, v2 = v2, v1
            if v1 >= 0:
                continue  # both finite: interior ridge, already included
            t = vor.points[p2] - vor.points[p1]
            norm = np.linalg.norm(t)
            if norm == 0:
                continue
            t = t / norm
            n = np.array([-t[1], t[0]])
            midpoint = vor.points[[p1, p2]].mean(axis=0)
            direction = np.sign(np.dot(midpoint - center, n)) * n
            far_point = vor.vertices[v2] + direction * radius
            new_region.append(len(new_vertices))
            new_vertices.append(far_point.tolist())
        if len(new_region) >= 3:
            vs = np.asarray([new_vertices[v] for v in new_region])
            c = vs.mean(axis=0)
            angles = np.arctan2(vs[:, 1] - c[1], vs[:, 0] - c[0])
            new_region = np.array(new_region)[np.argsort(angles)].tolist()
        new_regions.append(new_region)
    return new_regions, np.asarray(new_vertices)


def _clip_poly_to_box(verts: np.ndarray, xmin, xmax, ymin, ymax) -> np.ndarray:
    """Sutherland-Hodgman clip of a convex polygon to an axis-aligned box, vectorised
    across a polygon's vertices per box edge (4 edges total, not one comparison per
    vertex in a Python loop)."""
    pts = verts
    for coord, val, keep_ge in ((0, xmin, True), (0, xmax, False),
                                (1, ymin, True), (1, ymax, False)):
        if len(pts) == 0:
            break
        cur = pts
        prv = np.roll(pts, 1, axis=0)
        if keep_ge:
            cur_in = cur[:, coord] >= val
            prv_in = prv[:, coord] >= val
        else:
            cur_in = cur[:, coord] <= val
            prv_in = prv[:, coord] <= val
        denom = cur[:, coord] - prv[:, coord]
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(denom != 0, (val - prv[:, coord]) / denom, 0.0)
        isect = prv + t[:, None] * (cur - prv)
        out = []
        for i in range(len(cur)):
            if cur_in[i]:
                if not prv_in[i]:
                    out.append(isect[i])
                out.append(cur[i])
            elif prv_in[i]:
                out.append(isect[i])
        pts = np.asarray(out, float) if out else np.empty((0, 2))
    return pts


def polys_from_pos(nodes, pos, pad_frac: float = 0.035):
    """Bounded Voronoi cell per node, clipped to the bbox of `pos` padded by `pad_frac`
    (a fraction of the bbox's larger dimension -- relative, not the absolute 0.035 units
    `mapviz.zip_polygons` used).

    `nodes`: sequence of node ids. `pos`: array-like (n, 2) or {node: (x, y)}, aligned
    to `nodes` if a dict. Returns (polys, bounds) where `polys` is {node: (m, 2) ndarray}
    (degenerate/empty polygons are dropped by callers via `len(polys[z]) >= 3`) and
    `bounds = (xmin, xmax, ymin, ymax)`.
    """
    nodes = list(nodes)
    if isinstance(pos, dict):
        P = np.array([pos[z] for z in nodes], float)
    else:
        P = np.asarray(pos, float)
    assert_equal_area(P)
    n = len(nodes)
    if n == 0:
        return {}, (0.0, 1.0, 0.0, 1.0)
    xmin0, ymin0 = P.min(axis=0)
    xmax0, ymax0 = P.max(axis=0)
    span = max(xmax0 - xmin0, ymax0 - ymin0, 1e-9)
    pad = pad_frac * span
    xmin, xmax, ymin, ymax = xmin0 - pad, xmax0 + pad, ymin0 - pad, ymax0 + pad
    if n < 4:
        box = np.array([(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)])
        return {z: box for z in nodes}, (xmin, xmax, ymin, ymax)
    vor = Voronoi(P)
    radius = span * 4
    regions, vertices = _finite_regions(vor, radius)
    out = {}
    for z, region in zip(nodes, regions):
        if len(region) < 3:
            out[z] = np.empty((0, 2))
            continue
        verts = vertices[region]
        out[z] = _clip_poly_to_box(verts, xmin, xmax, ymin, ymax)
    return out, (xmin, xmax, ymin, ymax)


def polys_from_shapes(gdf):
    """Node id -> (m, 2) ndarray exterior-ring vertices, from a geopandas GeoDataFrame
    (or any object with `.geometry` and an index of node ids) of TIGER polygons.
    Replaces Voronoi outright for the twin -- real geometry, not an approximation. A
    MultiPolygon contributes its largest part. Shapely/geopandas imported lazily here
    only (Part D dependency rule)."""
    from shapely.geometry import MultiPolygon, Polygon

    out = {}
    index = list(gdf.index)
    geoms = gdf.geometry if hasattr(gdf, "geometry") else gdf
    for z, geom in zip(index, geoms):
        if geom is None or geom.is_empty:
            out[z] = np.empty((0, 2))
            continue
        if isinstance(geom, MultiPolygon):
            geom = max(geom.geoms, key=lambda g: g.area)
        if isinstance(geom, Polygon):
            out[z] = np.asarray(geom.exterior.coords, float)
        else:
            out[z] = np.empty((0, 2))
    xs = np.concatenate([p[:, 0] for p in out.values() if len(p)]) if out else np.array([0, 1])
    ys = np.concatenate([p[:, 1] for p in out.values() if len(p)]) if out else np.array([0, 1])
    bounds = (float(xs.min()), float(xs.max()), float(ys.min()), float(ys.max()))
    return out, bounds


# --------------------------------------------------------------------------- segments
def _pos_dict(G, pos) -> dict:
    """Normalise `pos` to a {node: (x, y)} dict, using `G`'s node order when `pos` is a
    bare array-like (only possible when `G` exposes node iteration, i.e. a real graph)."""
    if isinstance(pos, dict):
        return pos
    nodes = list(G)
    P = np.asarray(pos, float)
    return {z: P[i] for i, z in enumerate(nodes)}


def edge_segments(G, pos):
    """(m, 2, 2) ndarray of [[x1, y1], [x2, y2]] per edge of `G`, for a `LineCollection`.

    `pos`: array-like aligned to `list(G)` (only when `G` exposes node iteration) or a
    {node: (x, y)} dict -- a dict is required when `G` is a plain edge iterable.
    """
    edges = _pair_edges(G)
    d = _pos_dict(G, pos)
    segs = np.array([[d[u], d[v]] for u, v in edges], float)
    return segs if len(segs) else np.empty((0, 2, 2))


def partition_boundary(G, pos=None, side_of=None):
    """(m, 2, 2) ndarray of segments on the boundary between assignment sides. Two calling
    conventions:

        partition_boundary(G, pos, side_of)   -- schematic: graph edges (u, v) with
            `side_of(u) != side_of(v)`, drawn as the straight segment between the two
            nodes' positions (not the exact shared polygon ridge -- adequate for
            highlighting where a partition cuts the graph).

        partition_boundary(polys, side_of=fn) -- exact: the true shared ridge between
            every pair of *geometrically* adjacent polygons in `polys` ({node: (m, 2)
            ndarray}, from `polys_from_pos`/`polys_from_shapes`) whose `side_of` differs.
            Detected from shared polygon vertices, so it needs no graph/edge list at all
            (works even when the caller has none) and traces the actual cell boundary
            instead of a straight line between centers.

    `maps.boundary` draws either result bold over a `choropleth`.
    """
    if pos is None:
        return _polygon_ridge_boundary(G, side_of)
    d = _pos_dict(G, pos)
    edges = _pair_edges(G)
    cut = [(u, v) for u, v in edges if side_of(u) != side_of(v)]
    return edge_segments(cut, d)


def _polygon_ridge_boundary(polys: dict, side_of) -> np.ndarray:
    """The exact segment shared by every pair of geometrically adjacent polygons in
    `polys` whose `side_of` differs. Two polygons are Voronoi/tiling-adjacent iff they
    share >= 2 vertices (the ridge endpoints); vertices are matched by rounding to a
    tolerance scaled to the overall extent, absorbing the float noise `_clip_poly_to_box`
    introduces. No adjacency graph is needed -- purely a function of the polygon geometry.
    """
    verts_by_node = {z: np.asarray(v, float) for z, v in polys.items() if len(v) >= 3}
    if not verts_by_node:
        return np.empty((0, 2, 2))
    allv = np.concatenate(list(verts_by_node.values()))
    span = float(max(np.ptp(allv[:, 0]), np.ptp(allv[:, 1]))) if len(allv) else 1.0
    decimals = max(0, int(round(-np.log10(max(span * 1e-7, 1e-12)))))

    owners_by_vertex: dict = {}
    for z, vs in verts_by_node.items():
        for p in vs:
            key = (round(float(p[0]), decimals), round(float(p[1]), decimals))
            owners_by_vertex.setdefault(key, {})[z] = p

    shared_by_pair: dict = {}
    for owners in owners_by_vertex.values():
        if len(owners) < 2:
            continue
        zs = list(owners)
        for i in range(len(zs)):
            for j in range(i + 1, len(zs)):
                key = frozenset((zs[i], zs[j]))
                shared_by_pair.setdefault(key, []).append(owners[zs[i]])

    segs = []
    for pair, pts in shared_by_pair.items():
        a, b = tuple(pair)
        if side_of(a) == side_of(b):
            continue
        if len(pts) < 2:
            continue
        pts = np.asarray(pts, float)
        if len(pts) > 2:
            best, best_d = (0, 1), -1.0
            for i in range(len(pts)):
                for j in range(i + 1, len(pts)):
                    dd = float(np.linalg.norm(pts[i] - pts[j]))
                    if dd > best_d:
                        best_d, best = dd, (i, j)
            pts = pts[list(best)]
        segs.append(pts[:2])
    return np.asarray(segs, float) if segs else np.empty((0, 2, 2))
