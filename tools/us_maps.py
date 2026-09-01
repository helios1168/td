"""us_maps.py -- US bubble maps of the national-channel instance.

    .venv/bin/python3 tools/us_maps.py instance_descaled.json.gz --out figures/

writes `opportunity.png`, `firm_a.png`, `firm_b.png`, `contestability.png`.  Adding

    --districts battery/results/<run-id>/draw.csv

writes a fifth, `districts.png`: the stage-1 draw on the same basemap and the same area
encoding as `opportunity.png`, recoloured by district identity.  The four originals are
unaffected by the flag.

What the maps are for
---------------------
The open question in stage 1 is the balance ceiling, and the ceiling is decided by *where the
opportunity is* -- the footprint is disconnected, so a district cannot cross from California to
Florida and the regional totals settle `k` (docs/CHANNEL.md).  These maps are how those regions
are read off, and `contestability.png` is the second half of the same question: where the two
firms' books actually overlap is where stage 2's matching has anything to trade.

Cartography, and why each choice is forced
------------------------------------------
* **Points, not a surface.**  1,229 scattered ZCTAs.  A KDE or interpolated heatmap would
  paint value across the uncovered midwest, which is exactly the fact the map exists to show.
* **Area, not radius, proportional to value.**  Radius-proportional bubbles read as the square
  of the truth; the largest zip here is ~1% of the total and would swamp a metro.
* **Equal-area projection** (`td.geo.LAEA`), because area is the encoding.
* **log10 colour.**  The value distribution is heavy-tailed; a linear ramp puts 95% of the
  zips in the lightest two shades.  Area stays *linear* -- one channel per scale, and area is
  the one a reader integrates by eye.
* **One hue per sequential map, and the hue follows the entity.**  Firm A is Orange wherever it
  appears, firm B Purple, so `contestability.png`'s PuOr diverging scale needs no key beyond
  the two maps preceding it.  ("PuOr_r": purple at -1 = firm B, orange at +1 = firm A.)
* Text is dark grey, never a series colour, so no label can be misread as data.

Everything below `bubble_map` is importable and takes `(values, xy, states, ...)` with plain
dicts; `states=None` draws without the basemap, which is what the tests use so they need no
network.  The CLI is a thin wrapper.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "..")))

from td import geo                                                          # noqa: E402

# ------------------------------------------------------------------ house style
FIGSIZE = (12.0, 7.4)
DPI = 200
BG = "#fcfcfc"                 # light, but off-white so white bubble edges stay visible
TEXT = "#333333"
OUTLINE = "#cccccc"            # state boundaries
MAX_MARKER = 230.0             # pt^2 for the largest zip; a metro cluster stays legible
MIN_MARKER = 3.0               # floor, so a near-zero zip is still a dot rather than nothing
ALPHA = 0.6
EDGE_W = 0.3
FOOTER = "descaled units — no currency scale"

# the lower 48 in lon/lat; the instance carries no book outside it, but the gazetteer does
CONUS_BOX = (-125.0, -66.5, 24.0, 49.5)


# ------------------------------------------------------------------ geometry helpers
def conus_xy(zips, points, box=CONUS_BOX) -> tuple:
    """`(xy, missing, off_map)` -- projected points for `zips`, restricted to the lower 48.

    `missing` are zips the gazetteer does not carry (retired or non-ZCTA codes); `off_map` are
    zips it does carry but outside the frame.  Both are returned rather than raised: a handful
    of unmappable zips is a cartographic loss, not a data error, and the caller reports the
    share of value they take with them.
    """
    lo_lon, hi_lon, lo_lat, hi_lat = box
    have, missing, off_map = [], [], []
    for z in zips:
        p = points.get(z)
        if p is None:
            missing.append(z)
        elif lo_lon <= p[0] <= hi_lon and lo_lat <= p[1] <= hi_lat:
            have.append(z)
        else:
            off_map.append(z)
    if not have:
        return {}, missing, off_map
    x, y = geo.project([points[z][0] for z in have], [points[z][1] for z in have])
    return {z: (float(a), float(b)) for z, a, b in zip(have, x, y)}, missing, off_map


def drop_share(values, xy) -> tuple:
    """`(n_dropped, share)` of a value dict that has no plottable point."""
    total = sum(v for v in values.values() if v > 0)
    lost = sum(v for z, v in values.items() if v > 0 and z not in xy)
    n = sum(1 for z, v in values.items() if v > 0 and z not in xy)
    return n, (lost / total if total else 0.0)


def _aligned(values, xy):
    """Positive values with a point, as `(x, y, v)` arrays sorted small-first.

    Small-first so the big bubbles are drawn on top; with alpha 0.6 the reverse hides the
    metros that carry most of the value under a wash of surrounding small ones.
    """
    keep = [(z, v) for z, v in values.items() if v > 0 and z in xy]
    keep.sort(key=lambda kv: kv[1])
    x = np.array([xy[z][0] for z, _ in keep], float)
    y = np.array([xy[z][1] for z, _ in keep], float)
    v = np.array([v for _, v in keep], float)
    return x, y, v


def _sizes(v, vmax=None, max_marker=MAX_MARKER, min_marker=MIN_MARKER):
    """Marker **area** linear in value.  The floor is the one deliberate departure."""
    vmax = float(np.max(v)) if vmax is None else float(vmax)
    if vmax <= 0:
        return np.full(v.shape, min_marker)
    return np.maximum(min_marker, max_marker * (v / vmax))


def _fmt(v) -> str:
    return f"{v:,.3g}"


# ------------------------------------------------------------------ canvas
def _canvas(states, title, subtitle, footer=FOOTER):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=FIGSIZE, dpi=DPI, facecolor=BG)
    ax = fig.add_axes([0.015, 0.055, 0.845, 0.845])
    ax.set_facecolor(BG)
    if states is not None:
        states.boundary.plot(ax=ax, color=OUTLINE, linewidth=0.5)
    ax.set_aspect("equal")
    ax.set_axis_off()
    # "bold", not "semibold": DejaVu Sans (matplotlib's default) has no semibold face and
    # silently falls back with a warning on every figure
    fig.text(0.015, 0.955, title, color=TEXT, fontsize=15, fontweight="bold", va="top")
    fig.text(0.015, 0.912, subtitle, color=TEXT, fontsize=9.5, va="top", alpha=0.85)
    fig.text(0.015, 0.018, footer, color=TEXT, fontsize=8, alpha=0.7, va="bottom")
    return fig, ax


def _size_legend(ax, v, vmax, title, max_marker=MAX_MARKER):
    """Three reference bubbles: median, 90th percentile, largest.  Area is the only encoding."""
    refs = [float(np.quantile(v, 0.5)), float(np.quantile(v, 0.9)), float(np.max(v))]
    handles = [ax.scatter([], [], s=float(_sizes(np.array([r]), vmax, max_marker)[0]),
                          facecolor="none", edgecolor=TEXT, linewidth=0.6, label=_fmt(r))
               for r in refs]
    leg = ax.legend(handles=handles, loc="lower left", frameon=False, scatterpoints=1,
                    labelspacing=1.5, handletextpad=1.4, borderpad=0.8, fontsize=8.5,
                    title=title, title_fontsize=8.5, labelcolor=TEXT)
    leg.get_title().set_color(TEXT)
    return leg


def _colorbar(fig, mappable, label, ticks=None, ticklabels=None, extend="neither"):
    cax = fig.add_axes([0.885, 0.30, 0.013, 0.40])
    cb = fig.colorbar(mappable, cax=cax, extend=extend)
    cb.set_label(label, color=TEXT, fontsize=9)
    cb.outline.set_edgecolor(OUTLINE)
    cb.ax.tick_params(colors=TEXT, labelsize=8, length=2)
    if ticks is not None:
        cb.set_ticks(ticks)
    if ticklabels is not None:
        cb.set_ticklabels(ticklabels)
    return cb


def _save(fig, out):
    import matplotlib.pyplot as plt
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    fig.savefig(out, dpi=DPI, facecolor=BG)
    plt.close(fig)
    return out


# ------------------------------------------------------------------ the sequential maps
def bubble_map(values, xy, states, out, *, cmap="Blues", title="", subtitle="",
               cbar_label="", legend_title="value", max_marker=MAX_MARKER, alpha=ALPHA,
               footer=FOOTER, robust=(0.02, 0.98)):
    """One-hue bubble map: area linear in value, colour on log10 of the same value.

    Colour is redundant with area by construction.  That is the point -- it buys back the
    resolution area loses at the bottom of a heavy tail, without introducing a second variable
    a reader has to hold separately.

    `robust` clips the *colour* limits to those quantiles of log10.  Even on a log ramp the
    handful of near-zero zips stretch the scale by two decades below the bulk, which pushes
    every real zip into the darkest shades; the colourbar is drawn with `extend="both"` so the
    clipping is visible rather than silent.  Area is never clipped -- it stays exact.
    """
    x, y, v = _aligned(values, xy)
    fig, ax = _canvas(states, title, subtitle, footer)
    if v.size == 0:
        return _save(fig, out)
    vmax = float(v.max())
    lv = np.log10(v)
    lo, hi = (float(np.quantile(lv, robust[0])), float(np.quantile(lv, robust[1]))) \
        if robust else (float(lv.min()), float(lv.max()))
    if not hi > lo:
        lo, hi = float(lv.min()), float(lv.max()) or lo + 1.0
    sc = ax.scatter(x, y, s=_sizes(v, vmax, max_marker), c=lv, cmap=cmap, vmin=lo, vmax=hi,
                    alpha=alpha, linewidths=EDGE_W, edgecolors="white")
    _colorbar(fig, sc, cbar_label, extend="both" if robust else "neither")
    _size_legend(ax, v, vmax, legend_title, max_marker)
    return _save(fig, out)


def figure_opportunity(values, xy, states, out, **kw):
    """`M_z` -- the stage-1 objective's whole input, and the map the ceiling is read from."""
    kw.setdefault("cmap", "Blues")
    kw.setdefault("title", "Opportunity by ZIP — national channel footprint")
    kw.setdefault("subtitle", "bubble area ∝ M_z  ·  colour = log10 M_z  ·  "
                              "equal-area projection; no smoothing, so blank means no zip")
    kw.setdefault("cbar_label", "log10 M, descaled units")
    kw.setdefault("legend_title", "M (descaled)")
    return bubble_map(values, xy, states, out, **kw)


def figure_firm_book(values, xy, states, out, *, firm="", cmap="Oranges", side="A", **kw):
    """A firm's booked production per zip: `S_F(z) = sum of S over that firm's reps`."""
    kw.setdefault("cmap", cmap)
    kw.setdefault("title", f"Firm {side} book by ZIP — masked label {firm}")
    kw.setdefault("subtitle", "bubble area ∝ S_F(z), summed over the firm's reps  ·  "
                              "colour = log10 S_F(z)  ·  zips with no book are not drawn")
    kw.setdefault("cbar_label", "log10 S_F, descaled units")
    kw.setdefault("legend_title", f"S_{side} (descaled)")
    return bubble_map(values, xy, states, out, **kw)


# ------------------------------------------------------------------ the diverging map
def figure_contestability(a_values, b_values, xy, states, out, *, firm_a="A", firm_b="B",
                          cmap="PuOr_r", max_marker=MAX_MARKER, alpha=ALPHA, footer=FOOTER,
                          title=None, subtitle=None):
    """Where the two firms' books meet: area = book at stake, colour = lean.

    Two variables on two channels, which is the one place it is worth it.  Area is `a + b`,
    the combined book the district draw is actually moving; colour is `(a - b)/(a + b)` in
    [-1, +1], orange at firm A's pole and purple at firm B's, near-white at parity -- so a
    *large pale* bubble is a genuinely contested metro and a large saturated one is a firm's
    stronghold.  The lean is scale-free on purpose: it must not re-encode size.
    """
    combined = {z: float(a_values.get(z, 0.0)) + float(b_values.get(z, 0.0))
                for z in set(a_values) | set(b_values)}
    combined = {z: v for z, v in combined.items() if v > 0}
    x, y, v = _aligned(combined, xy)
    order = [z for z, _ in sorted(((z, combined[z]) for z in combined if z in xy),
                                  key=lambda kv: kv[1])]
    lean = np.array([(float(a_values.get(z, 0.0)) - float(b_values.get(z, 0.0)))
                     / combined[z] for z in order], float)

    title = title or (f"Contestability — firm {firm_a} vs firm {firm_b}")
    subtitle = subtitle or ("bubble area ∝ combined book a + b  ·  colour = lean "
                            "(a − b)/(a + b)  ·  every zip carrying either firm's book")
    fig, ax = _canvas(states, title, subtitle, footer)
    if v.size == 0:
        return _save(fig, out)
    sc = ax.scatter(x, y, s=_sizes(v, float(v.max()), max_marker), c=lean, cmap=cmap,
                    vmin=-1.0, vmax=1.0, alpha=alpha, linewidths=EDGE_W, edgecolors="white")
    _colorbar(fig, sc, "lean  (a − b) / (a + b)", ticks=[-1.0, -0.5, 0.0, 0.5, 1.0],
              ticklabels=[f"all {firm_b}", "", "even", "", f"all {firm_a}"])
    _size_legend(ax, v, float(v.max()), "a + b (descaled)", max_marker)
    ax.text(0.015, 0.965, "large + pale = big book, evenly contested",
            transform=ax.transAxes, color=TEXT, fontsize=9, va="top", alpha=0.9)
    return _save(fig, out)


# ------------------------------------------------------------------ the districts map
# A qualitative palette: tab20's even entries (the saturated member of each light/dark pair)
# plus two of tab20b's, with the two near-duplicate greys and the second olive dropped.  Hues
# only need to be *locally* distinguishable -- see `color_districts` -- so 12 is ample for
# k = 13 and the palette is chosen for separation at bubble size, not for a global ordering.
QUAL = [
    "#1f77b4",   # blue
    "#ff7f0e",   # orange
    "#2ca02c",   # green
    "#d62728",   # red
    "#9467bd",   # purple
    "#8c564b",   # brown
    "#e377c2",   # pink
    "#17becf",   # cyan
    "#bcbd22",   # olive
    "#393b79",   # indigo
    "#8c6d31",   # bronze
    "#7f7f7f",   # grey  (last on purpose: it reads as "other" and is the least wanted hue)
]
LABEL_TEXT = "#2b2b2b"         # district labels: dark grey, never the district's own colour


def district_centroids(districts, values, xy) -> dict:
    """`{district: (x, y)}` at the M-weighted centroid of its plottable zips.

    Weighted by value rather than by zip count so the label lands where the district's
    *business* is, which is where a reader's eye already is -- a district with one dense metro
    and a long rural tail would otherwise be labelled out in the tail.
    """
    acc = {}
    for z, d in districts.items():
        if z not in xy:
            continue
        w = max(float(values.get(z, 0.0)), 0.0)
        sx, sy, sw, n = acc.get(d, (0.0, 0.0, 0.0, 0))
        acc[d] = (sx + w * xy[z][0], sy + w * xy[z][1], sw + w, n + 1)
    out = {}
    for d, (sx, sy, sw, n) in acc.items():
        if sw > 0:
            out[d] = (sx / sw, sy / sw)
        elif n:                                   # a district of value-less zips: plain mean
            pts = [xy[z] for z, dd in districts.items() if dd == d and z in xy]
            out[d] = (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)
    return out


def centroid_neighbors(centroids, n_near=4) -> dict:
    """Symmetric nearest-neighbour graph over district centroids: `{district: set(...)}`.

    A proper district adjacency would need the zip adjacency, which is shattered on this
    instance (547 components) and would leave most district pairs unrelated.  The centroid
    kNN graph is the honest stand-in: it is exactly the relation the colouring has to respect,
    "these two districts sit next to each other on the page".
    """
    ids = sorted(centroids)
    adj = {d: set() for d in ids}
    for d in ids:
        x0, y0 = centroids[d]
        order = sorted((e for e in ids if e != d),
                       key=lambda e: ((centroids[e][0] - x0) ** 2
                                      + (centroids[e][1] - y0) ** 2, str(e)))
        for e in order[:max(int(n_near), 0)]:
            adj[d].add(e)
            adj[e].add(d)                          # symmetrised: kNN is not itself symmetric
    return adj


def zip_neighbors(districts, xy, n_near=6) -> dict:
    """District adjacency read off the *zips*: two districts are neighbours when a zip of one
    is among the `n_near` nearest zips of the other.  `{district: set(...)}`, symmetric.

    This is the graph a reader's eye actually builds.  It is kept alongside the centroid graph
    rather than instead of it because a district here need not be one blob -- stage 1 is
    center-based, not contiguous -- and the M-weighted centroid of a scattered district can
    land in empty country (D04's sits in west Texas, where it holds nothing), which makes the
    centroid graph blind to exactly the pairs whose bubbles interleave on the page.

    Measured on the real k=13 draw: degrees 2-5, i.e. far sparser than the 12-colour palette
    needs -- the districts really are spatially separated at zip level even when their
    centroids are not informative.
    """
    ids = sorted({districts[z] for z in districts if z in xy}, key=str)
    zs = [z for z in sorted(districts, key=str) if z in xy]
    adj = {d: set() for d in ids}
    if len(zs) < 2:
        return adj
    P = np.array([xy[z] for z in zs], float)
    lab = [districts[z] for z in zs]
    k = min(int(n_near) + 1, len(zs))
    for lo in range(0, len(zs), 256):                    # chunked: n^2 in one array is avoidable
        hi = min(lo + 256, len(zs))
        d2 = ((P[lo:hi, None, :] - P[None, :, :]) ** 2).sum(axis=2)
        idx = np.argpartition(d2, k - 1, axis=1)[:, :k]
        for r in range(hi - lo):
            a = lab[lo + r]
            for b in (lab[int(j)] for j in idx[r]):
                if b != a:
                    adj[a].add(b)
                    adj[b].add(a)
    return adj


def merge_adjacency(*graphs) -> dict:
    """Union of several `{node: set}` graphs over the union of their nodes."""
    out = {}
    for g in graphs:
        for d, nbrs in g.items():
            out.setdefault(d, set()).update(nbrs)
            for e in nbrs:
                out.setdefault(e, set()).add(d)
    return out


def color_districts(adj, palette=QUAL) -> dict:
    """Greedy graph colouring: `{district: colour}` with **no two neighbours sharing a hue**.

    Only neighbour-distinctness is guaranteed.  Global uniqueness is best-effort -- with 13
    districts over a 12-colour palette two of them *must* repeat, and the point of colouring
    the spatial graph is that the repeat is then guaranteed to be somewhere far away on the
    map, e.g. a Californian and a Floridian district, where no reader can confuse them.

    Vertices are taken in Welsh-Powell order (highest degree first, id as tie-break).  Each
    takes the **least-used** palette entry no already-coloured neighbour holds -- not the
    first free one: first-fit is equally valid but collapses onto the head of the palette (5
    hues for 13 districts on the real draw), which throws away the best-effort half of the
    promise for nothing.  If the palette runs out -- it does not on a graph this sparse, but
    the branch is real -- the vertex takes the globally least-used colour, so the failure
    degrades to a duplicate rather than an exception.
    """
    ids = sorted(adj, key=lambda d: (-len(adj[d]), str(d)))
    rank = {c: i for i, c in enumerate(palette)}
    used, out = {c: 0 for c in palette}, {}
    for d in ids:
        taken = {out[e] for e in adj[d] if e in out}
        free = [c for c in palette if c not in taken] or list(palette)
        c = min(free, key=lambda c: (used[c], rank[c]))
        out[d] = c
        used[c] += 1
    return out


def _district_legend(fig, districts, values, colors, order):
    """Compact table in the right margin: swatch, district id, share of total M.

    Replaces the colourbar -- district identity is nominal, so a continuous ramp would be a
    category error; and the one number a reader wants per district is its share of the whole,
    which is the balance the draw exists to deliver.
    """
    import matplotlib.patches as mpatches

    per = {}
    for z, d in districts.items():
        per[d] = per.get(d, 0.0) + float(values.get(z, 0.0))
    total = sum(per.values()) or 1.0
    ax = fig.add_axes([0.868, 0.5 - 0.021 * len(order) - 0.02, 0.125,
                       0.042 * len(order) + 0.04])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, len(order) + 1)
    ax.text(0.0, len(order) + 0.45, "district   share of M", color=TEXT, fontsize=8,
            fontweight="bold", va="center")
    for i, d in enumerate(order):
        y = len(order) - 1 - i + 0.5
        ax.add_patch(mpatches.Rectangle((0.0, y - 0.28), 0.13, 0.56,
                                        facecolor=colors[d], edgecolor="white",
                                        linewidth=0.4, alpha=0.9))
        ax.text(0.2, y, str(d), color=TEXT, fontsize=8, va="center")
        ax.text(1.0, y, f"{100.0 * per.get(d, 0.0) / total:.1f}%", color=TEXT, fontsize=8,
                va="center", ha="right")
    return ax


def figure_districts(districts, values, xy, states, out, *, max_marker=MAX_MARKER,
                     alpha=ALPHA, footer=FOOTER, title=None, subtitle=None, n_near=4,
                     palette=QUAL, label=True):
    """The drawn districts: area ∝ M as on `opportunity.png`, colour = district identity.

    `districts` is `{zip: district_id}` -- exactly the mapping stage 2 consumes, so the figure
    is drawn from the same object the staffing was computed on and cannot drift from it.

    Sizing is deliberately identical to `figure_opportunity` (same `_sizes`, same
    `_size_legend`), so the two maps overlay in the reader's memory: the districts map is the
    opportunity map recoloured, and nothing about the value encoding changed.

    Colour is *nominal*, so there is no colourbar and no ordering to read into the hues --
    only "these two bubbles are in different districts".  Districts are direct-labelled at
    their M-weighted centroids in a white-haloed box, which removes the legend round-trip for
    the identity question and leaves the margin table to carry the one quantity that matters,
    each district's share of total M.
    """
    vals = {z: float(values.get(z, 0.0)) for z in districts}
    # `keep` is built once and everything (positions, sizes, colours) is read off it in the
    # same order -- recomputing the small-first sort separately for the colours would put a
    # silent mis-pairing one equal-value tie away.
    keep = sorted(((z, v) for z, v in vals.items() if v > 0 and z in xy),
                  key=lambda kv: kv[1])
    x = np.array([xy[z][0] for z, _ in keep], float)
    y = np.array([xy[z][1] for z, _ in keep], float)
    v = np.array([w for _, w in keep], float)
    order = sorted({d for z, d in districts.items() if z in xy}, key=str)
    centroids = district_centroids(districts, values, xy)
    adj = merge_adjacency(centroid_neighbors(centroids, n_near),
                          zip_neighbors(districts, xy, n_near + 2))
    colors = color_districts(adj, palette)

    title = title or f"Drawn districts — {len(order)} territories on equal opportunity"
    subtitle = subtitle or ("bubble area ∝ M_z  ·  colour = district (nominal; adjacent "
                            "districts never share a hue)  ·  labels at M-weighted centroids")
    fig, ax = _canvas(states, title, subtitle, footer)
    if v.size == 0:
        return _save(fig, out)

    c = [colors[districts[z]] for z, _ in keep]
    ax.scatter(x, y, s=_sizes(v, float(v.max()), max_marker), c=c, alpha=alpha,
               linewidths=EDGE_W, edgecolors="white")

    if label:
        for d in order:
            if d not in centroids:
                continue
            cx, cy = centroids[d]
            ax.text(cx, cy, str(d), color=LABEL_TEXT, fontsize=8, fontweight="bold",
                    ha="center", va="center", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                              edgecolor="none", alpha=0.82))
    _district_legend(fig, districts, values, colors, order)
    _size_legend(ax, v, float(v.max()), "M (descaled)", max_marker)
    return _save(fig, out)


def read_draw(path) -> dict:
    """`{zip: district}` from a `draw.csv` written by `tools/run_draw.py` (`zip,district`)."""
    import csv as _csv
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(_csv.DictReader(fh))
    if not rows or "zip" not in rows[0] or "district" not in rows[0]:
        raise ValueError(f"{path}: expected a CSV with columns zip,district")
    return {r["zip"].strip(): r["district"].strip() for r in rows}


# ------------------------------------------------------------------ instance -> value dicts
def firm_books(d) -> dict:
    """`{firm: {zip: book}}` from the instance's rep -> firm map.  Reps with no firm are kept
    under the key `""`, so the totals below still add up to the instance's book."""
    out = {}
    for z in d.G:
        for rep, s in d.G.nodes[z]["S"].items():
            per_zip = out.setdefault(d.firm.get(rep, ""), {})
            per_zip[z] = per_zip.get(z, 0.0) + float(s)
    return out


def top_two_firms(books) -> tuple:
    """The two firms with the largest instance-wide book, plus every firm's share."""
    totals = {f: sum(m.values()) for f, m in books.items() if f}
    grand = sum(totals.values())
    order = sorted(totals, key=lambda f: -totals[f])
    shares = {f: (totals[f] / grand if grand else 0.0) for f in order}
    if len(order) < 2:
        raise ValueError(f"need two firms with book, found {order}")
    return order[0], order[1], shares


# ------------------------------------------------------------------ CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("instance", nargs="?", default="instance_descaled.json.gz")
    ap.add_argument("--out", default="figures", help="output directory (created if absent)")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--no-basemap", action="store_true", help="skip the state outlines")
    ap.add_argument("--districts", default=None, metavar="DRAW_CSV",
                    help="a draw.csv from tools/run_draw.py; adds districts.png")
    args = ap.parse_args(argv)

    from td import instance as descaled
    d = descaled.load_descaled(args.instance)
    print(f"instance: {d.summary()}")

    points = geo.zcta_points(args.geo_cache)
    print(f"gazetteer: {len(points):,} ZCTA internal points")
    xy, missing, off_map = conus_xy(sorted(d.G), points)
    M = {z: float(d.G.nodes[z]["M"]) for z in d.G}
    if missing:
        print(f"WARNING: {len(missing)} zip(s) absent from the 2020 gazetteer, skipped "
              f"({share_of(missing, M):.2%} of M) e.g. {missing[:5]}")
    if off_map:
        print(f"non-CONUS: {len(off_map)} zip(s) outside the lower 48, dropped "
              f"({share_of(off_map, M):.2%} of M) e.g. {off_map[:5]}")
    print(f"plotted:   {len(xy):,} of {d.G.number_of_nodes():,} zips")

    states = None if args.no_basemap else geo.states_outline(args.geo_cache)

    books = firm_books(d)
    fa, fb, shares = top_two_firms(books)
    print(f"firms:     A = {fa} ({shares[fa]:.1%} of book), B = {fb} ({shares[fb]:.1%}); "
          f"all shares { {f: round(s, 4) for f, s in shares.items()} }")

    os.makedirs(args.out, exist_ok=True)
    written = []
    for name, values, builder, kw in (
        ("opportunity.png", M, figure_opportunity, {}),
        ("firm_a.png", books[fa], figure_firm_book, dict(firm=fa, cmap="Oranges", side="A")),
        ("firm_b.png", books[fb], figure_firm_book, dict(firm=fb, cmap="Purples", side="B")),
    ):
        n, share = drop_share(values, xy)
        print(f"{name:<18} {len([v for v in values.values() if v > 0]):>5,} zips with value; "
              f"{n} unplottable ({share:.2%} of it)")
        written.append(builder(values, xy, states, os.path.join(args.out, name), **kw))

    combined = {z: books[fa].get(z, 0.0) + books[fb].get(z, 0.0)
                for z in set(books[fa]) | set(books[fb])}
    n, share = drop_share(combined, xy)
    both = sum(1 for z in combined if books[fa].get(z, 0) > 0 and books[fb].get(z, 0) > 0)
    print(f"{'contestability.png':<18} {len(combined):>5,} zips with either firm's book, "
          f"{both:,} with both; {n} unplottable ({share:.2%} of it)")
    written.append(figure_contestability(books[fa], books[fb], xy, states,
                                         os.path.join(args.out, "contestability.png"),
                                         firm_a=fa, firm_b=fb))

    if args.districts:
        draw = read_draw(args.districts)
        stray = [z for z in draw if z not in M]
        if stray:
            print(f"WARNING: {len(stray)} zip(s) in the draw are not in the instance, "
                  f"ignored e.g. {stray[:5]}")
            draw = {z: d for z, d in draw.items() if z in M}
        unplaced = [z for z in M if z not in draw]
        ids = sorted(set(draw.values()), key=str)
        n_off, share = drop_share({z: M[z] for z in draw}, xy)
        print(f"{'districts.png':<18} {len(draw):>5,} zips in {len(ids)} districts; "
              f"{n_off} unplottable ({share:.2%} of their M); "
              f"{len(unplaced)} instance zip(s) not in the draw")
        written.append(figure_districts(draw, M, xy, states,
                                        os.path.join(args.out, "districts.png")))

    for p in written:
        print(f"wrote {p}  ({os.path.getsize(p) / 1024:.0f} KB)")
    return 0


def share_of(zips, values) -> float:
    total = sum(values.values())
    return (sum(values.get(z, 0.0) for z in zips) / total) if total else 0.0


if __name__ == "__main__":
    sys.exit(main())
