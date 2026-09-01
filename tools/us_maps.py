"""us_maps.py -- US bubble maps of the national-channel instance.

    .venv/bin/python3 tools/us_maps.py instance_descaled.json.gz --out figures/

writes `opportunity.png`, `firm_a.png`, `firm_b.png`, `contestability.png`.  Adding

    --districts battery/results/<run-id>/draw.csv

writes a fifth, `districts.png`: the stage-1 draw on the same basemap and the same area
encoding as `opportunity.png`, recoloured by district identity.  And

    --regions battery/results/<run-id>/draw.csv

writes `district_regions.png`: the same draw as **filled territory** rather than bubbles, and
the map the business is shown.  The fill is the **power (Laguerre) diagram** of the 13 district
centers, weighted by the transportation LP's mass-balance duals -- `k` convex regions with
exact straight borders, which is the territory a center-based balanced assignment actually
produces.  `--regions-voronoi` writes the superseded rendering (`district_regions_voronoi.png`,
each zip's Voronoi catchment dissolved by district) for comparison.  The four originals are
unaffected by any flag.

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


def _district_legend(fig, districts, values, colors, order, second=None, second_label=""):
    """Compact table in the right margin: swatch, district id, share of total M.

    Replaces the colourbar -- district identity is nominal, so a continuous ramp would be a
    category error; and the one number a reader wants per district is its share of the whole,
    which is the balance the draw exists to deliver.

    `second` adds one more numeric column, `{district: share in [0, 1]}` under the header
    `second_label`.  The territory map uses it for each district's share of the *map area*,
    which is where the power diagram's whole point lands: the shares of M are all 7.7% by
    construction, and the shares of area run from 0.06% to 28%.  Equal opportunity is not equal
    ground, and putting the two columns side by side is the only way to say so in a legend.
    """
    import matplotlib.patches as mpatches

    per = {}
    for z, d in districts.items():
        per[d] = per.get(d, 0.0) + float(values.get(z, 0.0))
    total = sum(per.values()) or 1.0
    wide = second is not None
    ax = fig.add_axes([0.868 if not wide else 0.855, 0.5 - 0.021 * len(order) - 0.02,
                       0.125 if not wide else 0.14, 0.042 * len(order) + 0.04])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, len(order) + 1)
    head = "district  M" + (f"   {second_label}" if wide else "     share of M")
    ax.text(0.0, len(order) + 0.45, head, color=TEXT, fontsize=8,
            fontweight="bold", va="center")
    x_first = 0.62 if wide else 1.0
    for i, d in enumerate(order):
        y = len(order) - 1 - i + 0.5
        ax.add_patch(mpatches.Rectangle((0.0, y - 0.28), 0.13, 0.56,
                                        facecolor=colors[d], edgecolor="white",
                                        linewidth=0.4, alpha=0.9))
        ax.text(0.2, y, str(d), color=TEXT, fontsize=8, va="center")
        ax.text(x_first, y, f"{100.0 * per.get(d, 0.0) / total:.1f}%", color=TEXT, fontsize=8,
                va="center", ha="right")
        if wide:
            v = float(second.get(d, 0.0))
            # two significant figures at the bottom of the range: 0.06% must not print as 0.1%
            txt = f"{100.0 * v:.2f}%" if v < 0.01 else f"{100.0 * v:.1f}%"
            ax.text(1.0, y, txt, color=TEXT, fontsize=8, va="center", ha="right")
    return ax


def draw_palette(districts, values, xy, *, n_near=4, palette=QUAL):
    """`(order, centroids, colors)` -- the identity encoding **both** district figures share.

    Factored out so `districts.png` and `district_regions.png` cannot drift: the colouring is a
    function of the draw, not of the figure, and a reader flipping between the two maps has to
    see D07 in the same hue on both.
    """
    order = sorted({d for z, d in districts.items() if z in xy}, key=str)
    centroids = district_centroids(districts, values, xy)
    adj = merge_adjacency(centroid_neighbors(centroids, n_near),
                          zip_neighbors(districts, xy, n_near + 2))
    return order, centroids, color_districts(adj, palette)


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
    order, centroids, colors = draw_palette(districts, values, xy, n_near=n_near,
                                            palette=palette)

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


# ------------------------------------------------------------------ the district regions map
# Bubbles answer "how much is here"; a business audience asks "where does my territory stop".
# The honest way to fill the plane from scattered points is the Voronoi diagram: every point of
# the country is coloured by its *nearest* zip's district.  That is a real statement -- the
# boundary between two adjacent zips of different districts is exactly their perpendicular
# bisector -- and it invents no value anywhere, unlike a KDE or an interpolated surface.
REGION_ALPHA = 0.45            # fills must stay light enough for the dark borders to read
CELL_EDGE = "white"            # the zip lattice inside a district: present, never assertive
CELL_EDGE_W = 0.4
CELL_EDGE_ALPHA = 0.5
BORDER = "#444444"             # district vs district: the one line a reader is meant to follow
BORDER_W = 1.4
STATE_W_REGIONS = 0.6          # heavier than the bubble maps: it is competing with a fill now
LABEL_SEP = 0.035              # minimum label separation, as a fraction of the frame width
_LAND_CACHE: dict = {}         # id(states) -> (states, unioned geometry); see `land_union`


def land_union(states):
    """The dissolved lower-48 landmass as one (multi)polygon, cached per basemap object.

    Cached because the union of 49 state polygons is the single most expensive geometry step
    here and the same basemap is reused across every figure in a run.  The cache holds a
    reference to `states` itself, so `id()` cannot be recycled underneath the key.
    """
    key = id(states)
    hit = _LAND_CACHE.get(key)
    if hit is not None and hit[0] is states:
        return hit[1]
    import shapely
    geom = shapely.union_all([_valid(g) for g in states.geometry])
    _LAND_CACHE[key] = (states, geom)
    return geom


def _valid(geom):
    """`make_valid` only where it is needed -- it is not free and most rings are already fine."""
    import shapely
    return geom if geom.is_valid else shapely.make_valid(geom)


def clip_region(pts, states, pad=0.05):
    """The polygon every Voronoi cell is trimmed to.

    With a basemap that is the landmass, which is what stops a coastal zip's cell from
    spilling a hundred miles into the Atlantic or across the Canadian border.  Without one
    (`states=None`, the test path) it is the convex hull of the points, padded by `pad` of the
    frame -- the cells still get a finite, point-respecting boundary, just not a real coastline.
    """
    if states is not None:
        return land_union(states)
    from shapely import MultiPoint
    hull = MultiPoint([tuple(p) for p in pts]).convex_hull
    x0, y0, x1, y1 = hull.bounds
    return _valid(hull.buffer(max(pad * max(x1 - x0, y1 - y0), 1e-9)))


def match_cells_to_points(cells, coords) -> list:
    """`[cell index for each point]` -- the bijection between Voronoi cells and generators.

    The fallback for when the diagram does not come back in input order.  Each generator lies
    in the closed cell of exactly one polygon, so the lookup is a tree query narrowed to a
    `covers` test; a point that lands on a shared edge (coincident inputs, or a snapped
    tolerance) can match two, and is broken in favour of a cell nothing has claimed yet, then
    by nearest centroid.  Both halves of "bijection" are asserted -- every point matched, no
    cell matched twice -- because the failure is silent otherwise: the map would still draw,
    with the wrong ground under the wrong district.

    The tree predicate is `intersects`, not `covers`, and that is not a slack choice.  Shapely
    applies the predicate as `input.predicate(tree_geometry)`, so `covers` here asks whether
    the *point* covers the polygon and matches nothing at all; the containment test has to be
    made explicitly on the candidates the bbox filter returns.
    """
    from shapely import Point, STRtree
    cells = list(cells)
    tree = STRtree(cells)
    idx, used = [], set()
    for c in coords:
        p = Point(c)
        hit = [j for j in (int(j) for j in tree.query(p, predicate="intersects"))
               if cells[j].covers(p)]
        free = [j for j in hit if j not in used] or hit or list(range(len(cells)))
        j = free[0] if len(free) == 1 else min(free, key=lambda j: cells[j].centroid.distance(p))
        idx.append(j)
        used.add(j)
    assert len(idx) == len(coords), (len(idx), len(coords))
    assert len(set(idx)) == len(idx), "two points claimed the same Voronoi cell"
    return idx


def voronoi_cells(keys, xy, clip) -> dict:
    """`{key: cell}` -- the Voronoi cell of each point, clipped to `clip`.

    Two things are easy to get wrong and both are checked rather than assumed.  First, the
    cells come back as a GeometryCollection whose order is **not** the input order unless
    `ordered=True` is both available (shapely >= 2.1, GEOS >= 3.12) and honoured; the result is
    verified point-by-point and falls back to an STRtree lookup otherwise.  Second, the
    matching must be a *bijection* -- one cell per point, no cell claimed twice -- which is
    asserted, because a silent off-by-one here mislabels territory rather than crashing.

    Clipping can empty a cell whose point falls in the sea on the generalised 1:20m coastline.
    Those keys are dropped from the result (their ground is covered by the neighbouring cells
    regardless) and the caller reports the count.
    """
    import shapely
    from shapely import MultiPoint, Point

    keys = list(keys)
    coords = [tuple(xy[k]) for k in keys]
    if len(coords) < 2:
        return {}
    env = _valid(clip.envelope.buffer(0.02 * max(clip.bounds[2] - clip.bounds[0],
                                                 clip.bounds[3] - clip.bounds[1]) + 1.0))
    cells = list(shapely.voronoi_polygons(MultiPoint(coords), extend_to=env,
                                          ordered=True).geoms)
    pts = [Point(c) for c in coords]
    ok = len(cells) == len(pts) and all(cells[i].covers(pts[i]) for i in range(len(pts)))
    if not ok:                                   # `ordered` unavailable or not honoured
        cells = [cells[j] for j in match_cells_to_points(cells, coords)]
    assert len(cells) == len(pts), (len(cells), len(pts))

    out = {}
    for k, cell in zip(keys, cells):
        g = _valid(shapely.intersection(_valid(cell), clip))
        if not g.is_empty and g.area > 0:
            out[k] = g
    return out


def dissolve(cells, districts) -> dict:
    """`{district: (multi)polygon}` -- the union of that district's zip cells.

    A district may come out **multi-part**, and legitimately so: stage 1 is centre-based, not
    contiguity-constrained, so another district's zips can interleave and split it.  Nothing
    here forces a single polygon; the map shows what the draw actually is.
    """
    import shapely
    groups = {}
    for k, g in cells.items():
        d = districts.get(k)
        if d is not None:
            groups.setdefault(d, []).append(g)
    return {d: _valid(shapely.union_all(gs)) for d, gs in groups.items()}


def _lines_of(geom, out=None) -> list:
    """Every LineString inside a geometry, as `(n, 2)` coordinate arrays.  Points dropped."""
    out = [] if out is None else out
    if geom is None or geom.is_empty:
        return out
    gt = geom.geom_type
    if gt in ("LineString", "LinearRing"):
        if geom.length > 0:
            out.append(np.asarray(geom.coords, float))
    elif gt == "Polygon":
        _lines_of(geom.exterior, out)
        for r in geom.interiors:
            _lines_of(r, out)
    elif hasattr(geom, "geoms"):
        for g in geom.geoms:
            _lines_of(g, out)
    return out


def district_borders(polys, eps=0.0) -> list:
    """The district-vs-district boundaries only: shared edges, never the coastline.

    Drawing each district's whole boundary would put the same heavy stroke on the Pacific coast
    and the Rio Grande as on the line between D03 and D05, and the internal borders -- the only
    thing this figure exists to show -- would stop reading.  So the shared edges are taken
    pairwise: `∂A ∩ ∂B` for districts whose bounding boxes meet.

    Since both polygons are unions of cells from one Voronoi diagram clipped by one polygon,
    the shared edges are numerically identical and the plain intersection finds them.  `eps`
    (a fraction of a pixel on the real map) is the fallback for the case where it does not.
    """
    ids = sorted(polys, key=str)
    buffered, segs = {}, []
    for i, a in enumerate(ids):
        pa = polys[a]
        if pa.is_empty:
            continue
        for b in ids[i + 1:]:
            pb = polys[b]
            if pb.is_empty:
                continue
            ax0, ay0, ax1, ay1 = pa.bounds
            bx0, by0, bx1, by1 = pb.bounds
            if ax1 + eps < bx0 or bx1 + eps < ax0 or ay1 + eps < by0 or by1 + eps < ay0:
                continue
            got = _lines_of(pa.boundary.intersection(pb.boundary))
            if not got and eps > 0:
                if b not in buffered:
                    buffered[b] = pb.buffer(eps)
                got = _lines_of(pa.boundary.intersection(buffered[b]))
            segs.extend(got)
    return segs


def _poly_paths(geom) -> list:
    """Matplotlib `Path`s for a (Multi)Polygon, one per part, **holes included**.

    Built by hand rather than via geopandas so the whole renderer runs with `states=None` and
    no geo stack at all, which is what keeps the tests network-free.
    """
    from matplotlib.path import Path
    out = []
    for poly in (geom.geoms if geom.geom_type == "MultiPolygon" else [geom]):
        if poly.is_empty:
            continue
        verts, codes = [], []
        for ring in [poly.exterior, *poly.interiors]:
            c = np.asarray(ring.coords, float)
            if len(c) < 3:
                continue
            verts.append(c)
            codes.append(np.r_[Path.MOVETO, np.full(len(c) - 1, Path.LINETO)])
        if verts:
            out.append(Path(np.concatenate(verts), np.concatenate(codes)))
    return out


def _largest_part(geom):
    return max(geom.geoms, key=lambda g: g.area) if geom.geom_type == "MultiPolygon" else geom


def _parts(geom) -> list:
    """A district's polygons, largest first."""
    gs = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    return sorted((g for g in gs if not g.is_empty), key=lambda g: -g.area)


def _inside_points(poly) -> list:
    """A handful of points spread across one polygon, all guaranteed inside it.

    `representative_point` gives one, which is not enough: a label that has to move needs
    somewhere else in the *same* region to go, not a different region.  The quadrants of the
    bounding box supply the rest, and each quadrant's own representative point is inside the
    part by construction, so a concave or ring-shaped territory is still handled.
    """
    from shapely import box
    out = [poly.representative_point()]
    x0, y0, x1, y1 = poly.bounds
    mx, my = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    for bx0, by0, bx1, by1 in ((x0, my, mx, y1), (mx, my, x1, y1),
                               (x0, y0, mx, my), (mx, y0, x1, my)):
        piece = poly.intersection(box(bx0, by0, bx1, by1))
        if not piece.is_empty and piece.area > 0:
            out.append(_largest_part(piece).representative_point())
    return out


def label_points(order, polys, centroids, min_sep=0.0, min_part=0.15) -> dict:
    """`{district: (x, y)}` -- a label point **inside its own region** and clear of the labels
    already placed.

    The M-weighted centroid is the point we want (it lands where the district's business is),
    but on a filled map it is only usable if it is in the district: a multi-part district's
    weighted centroid can sit in a hole, or inside a neighbour.  So each district offers its
    centroid, then points spread across each part holding at least `min_part` of its area, and
    takes the first candidate `min_sep` clear of every label already down.  Districts are
    served largest-part-first, so the big regions keep the preferred point and the small
    interleaved ones move.

    `min_part` is the guard that matters.  Allowing *any* part as a fallback sends a crowded
    label off to a sliver -- on the real k=13 draw D09 landed on a hairline in Colorado while
    its territory is in southern California, which is a worse error than the overlap it was
    fixing.  A label may only move within the district's substantial ground; if that ground is
    genuinely crowded the label stays where separation is largest and merely touches.

    Without any of this, two districts whose value concentrates in the same metro print their
    labels on top of each other -- D01/D13 in New England, D02/D09 in southern California.
    """
    from shapely import Point
    out, placed = {}, []
    ranked = sorted((d for d in order if d in polys and not polys[d].is_empty),
                    key=lambda e: (-_largest_part(polys[e]).area, str(e)))
    for d in ranked:
        g = polys[d]
        cand = []
        c = centroids.get(d)
        if c is not None and g.covers(Point(c)):
            cand.append(Point(c))
        parts = _parts(g)
        floor = min_part * sum(p.area for p in parts)
        for p in parts:
            if p.area >= floor or p is parts[0]:
                cand.extend(_inside_points(p))
        far = [min((q.distance(p) for q in placed), default=float("inf")) for p in cand]
        pick = next((i for i, s in enumerate(far) if s >= min_sep),
                    max(range(len(cand)), key=lambda i: far[i]))
        out[d] = (cand[pick].x, cand[pick].y)
        placed.append(cand[pick])
    return out


def figure_district_regions(districts, values, xy, states, out, *, alpha=REGION_ALPHA,
                            footer=FOOTER, title=None, subtitle=None, n_near=4,
                            palette=QUAL, label=True, pad=0.05, report=None):
    """The draw as **filled territory**: each zip's Voronoi catchment, dissolved by district.

    **Superseded by `figure_power_regions`** as the business territory map, and kept because the
    comparison is worth having: this fill is a true statement about the *zips* (the line between
    two adjacent zips of different districts really is their perpendicular bisector) and a false
    one about the *method*, whose optimal territory is a power diagram of the centers, not a
    Voronoi diagram of anything.  Where the two disagree, this one shows the committed draw
    faithfully and the power diagram shows what compactness would have asked for.

    Colours come from `draw_palette`, the same call `figure_districts` makes, so the two maps
    agree hue-for-hue.  The z-order is the whole design: light fills, then the white zip
    lattice (so a reader can see the map is built of zips, not painted), then the district
    borders dark on top of it, then the state outlines -- which are lighter than the district
    borders on purpose, since a state line that fights a territory line is worse than no state
    line at all.

    `report` is an optional callable taking one string; the CLI passes `print`.
    """
    from matplotlib.collections import LineCollection
    from matplotlib.patches import PathPatch

    say = report or (lambda _s: None)
    keys = [z for z in sorted(districts, key=str) if z in xy]
    order, centroids, colors = draw_palette(districts, values, xy, n_near=n_near,
                                            palette=palette)
    title = title or f"District territories — {len(order)} regions on equal opportunity"
    subtitle = subtitle or (
        "fill = the Voronoi catchment of each ZIP: every point is coloured by its nearest "
        "ZIP's district  ·  boundaries between\nadjacent ZIPs of different districts are "
        "exact  ·  clipped to the US landmass  ·  colours match districts.png")
    fig, ax = _canvas(None, title, subtitle, footer)          # states drawn last, on top
    if len(keys) < 2:
        return _save(fig, out)

    clip = clip_region([xy[z] for z in keys], states, pad)
    cells = voronoi_cells(keys, xy, clip)
    if len(cells) < len(keys):
        say(f"regions: {len(keys) - len(cells)} zip(s) fell outside the clip polygon "
            f"(generalised coastline); their ground goes to the neighbouring cells")
    polys = dissolve(cells, districts)
    for d, g in polys.items():
        assert g.area > 0, f"district {d} dissolved to zero area"
    # Part counts are reported two ways on purpose.  The raw count is inflated by the
    # coastline -- clipping a single cell against islands and bays splits it -- so the number
    # that means "this district is genuinely in pieces" is the count of parts holding more than
    # 1% of its area, alongside the share the largest part carries.
    split = []
    for d in sorted(polys, key=str):
        ps = _parts(polys[d])
        tot = sum(p.area for p in ps) or 1.0
        big = sum(1 for p in ps if p.area / tot > 0.01)
        if len(ps) > 1:
            split.append(f"{d}: {big} part(s) >1% of {len(ps)}, largest {ps[0].area / tot:.0%}")
    if split:
        say("regions: districts in pieces (centre-based draw, drawn as it is) — "
            + "; ".join(split))

    x0, y0, x1, y1 = clip.bounds
    eps = 1e-4 * float(np.hypot(x1 - x0, y1 - y0))

    for d in order:                                            # 1. fills
        g = polys.get(d)
        if g is None:
            continue
        for path in _poly_paths(g):
            ax.add_patch(PathPatch(path, facecolor=colors[d], edgecolor="none",
                                   alpha=alpha, zorder=1))
    lattice = [seg for g in cells.values() for seg in _lines_of(g.boundary)]
    ax.add_collection(LineCollection(lattice, colors=CELL_EDGE, linewidths=CELL_EDGE_W,
                                     alpha=CELL_EDGE_ALPHA, zorder=2))   # 2. the zip lattice
    borders = district_borders(polys, eps)                     # 3. district vs district
    ax.add_collection(LineCollection(borders, colors=BORDER, linewidths=BORDER_W,
                                     capstyle="round", joinstyle="round", zorder=3))
    say(f"regions: {len(cells):,} cells, {len(polys)} districts, "
        f"{len(borders):,} shared border segments")
    if states is not None:                                     # 4. states, on top but light
        states.boundary.plot(ax=ax, color=OUTLINE, linewidth=STATE_W_REGIONS, zorder=4)

    if label:                                                  # 5. labels
        for d, (lx, ly) in label_points(order, polys, centroids,
                                        LABEL_SEP * (x1 - x0)).items():
            ax.text(lx, ly, str(d), color=LABEL_TEXT, fontsize=8, fontweight="bold",
                    ha="center", va="center", zorder=6,
                    bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                              edgecolor="none", alpha=0.82))
    _district_legend(fig, districts, values, colors, order)
    mx, my = 0.02 * (x1 - x0), 0.02 * (y1 - y0)
    ax.set_xlim(x0 - mx, x1 + mx)
    ax.set_ylim(y0 - my, y1 + my)
    return _save(fig, out)


# ------------------------------------------------------------------ the power diagram
# `district_regions.png` above fills the plane from the *zips*: a Voronoi catchment each,
# dissolved by district.  That is a true statement about the zips and a false one about the
# method.  Stage 1 is center-based balanced assignment, and the optimal territory of a
# center-based balanced assignment is not a Voronoi diagram of anything -- it is the **power
# (Laguerre) diagram** of the k centers, weighted by the transportation LP's mass-balance duals
# (Aurenhammer-Hoffmann-Aronov; docs/RESEARCH_FINDINGS.md §9-A1).  Equal *opportunity*, not
# equal area, is what is being equalised, and the weights are exactly that correction: a
# district over thin country has to reach further, and its weight says how much further.
#
# The practical difference is that a power cell is **convex**, with straight borders, because
# cell j is the intersection of the half-planes `||x-c_j||^2 - w_j <= ||x-c_i||^2 - w_i` and
# each of those is linear -- the quadratic terms cancel.  So the territory map is 13 convex
# regions rather than a ragged union of 1,223 little cells, and it is exact rather than a
# rendering choice.
DOT_MARKER = 9.0               # zip dots on the region map: present, subordinate to the fill
DOT_EDGE_W = 0.25
SLIVER_SHARE = 0.01            # a cell under 1% of the map is stroked, not merely filled
SLIVER_W = 2.2


def halfplane_clip(verts: np.ndarray, a: np.ndarray, b: float) -> np.ndarray:
    """Sutherland-Hodgman: the part of convex polygon `verts` satisfying `a·x <= b`.

    Exact for a convex input, which is all this is ever handed -- the running intersection of
    half-planes stays convex by construction.  Returns an empty `(0, 2)` array when the
    half-plane misses the polygon entirely, which is a real case: a district can be squeezed
    out of the frame by its neighbours' weights.
    """
    if len(verts) == 0:
        return verts
    s = verts @ a - b
    out = []
    for i in range(len(verts)):
        j = (i + 1) % len(verts)
        si, sj = s[i], s[j]
        if si <= 0:
            out.append(verts[i])
        if (si < 0) != (sj < 0) and si != sj:
            out.append(verts[i] + (si / (si - sj)) * (verts[j] - verts[i]))
    return np.asarray(out, float).reshape(-1, 2)


def power_cell(j: int, centers: np.ndarray, weights: np.ndarray, box) -> np.ndarray:
    """Cell `j` of the power diagram, as a convex polygon clipped to the rectangle `box`.

    `box` is `(x0, y0, x1, y1)`.  The bisector of cells `i` and `j` is
    `2(c_i - c_j)·x = |c_i|^2 - w_i - |c_j|^2 + w_j` -- a straight line, since the `|x|^2` terms
    cancel -- so the cell is `box` cut by `k - 1` half-planes and nothing more.  With `k = 13`
    that is 12 clips; there is no reason to reach for a convex-hull or lifting routine.
    """
    C = np.asarray(centers, float)
    w = np.asarray(weights, float)
    x0, y0, x1, y1 = box
    verts = np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], float)
    cj, wj = C[j], w[j]
    for i in range(len(C)):
        if i == j:
            continue
        a = 2.0 * (C[i] - cj)
        b = float(C[i] @ C[i] - w[i] - cj @ cj + wj)
        verts = halfplane_clip(verts, a, b)
        if len(verts) == 0:
            break
    return verts


def power_cells(centers: dict, weights: dict, clip) -> dict:
    """`{district: polygon}` -- the power diagram, clipped to `clip` (the landmass or the hull).

    `centers` and `weights` are keyed by district id so the caller never has to hold a parallel
    index.  A cell that misses `clip` entirely is dropped rather than returned empty; on a real
    draw that does not happen, because every center is itself a point of the country.
    """
    from shapely import Polygon
    ids = sorted(centers, key=str)
    C = np.array([centers[d] for d in ids], float)
    w = np.array([float(weights[d]) for d in ids], float)
    x0, y0, x1, y1 = clip.bounds
    pad = 0.05 * max(x1 - x0, y1 - y0) + 1.0
    box = (x0 - pad, y0 - pad, x1 + pad, y1 + pad)
    out = {}
    for j, d in enumerate(ids):
        verts = power_cell(j, C, w, box)
        if len(verts) < 3:
            continue
        g = _valid(shapely_intersection(Polygon(verts), clip))
        if not g.is_empty and g.area > 0:
            out[d] = g
    return out


def shapely_intersection(a, b):
    import shapely
    return shapely.intersection(_valid(a), _valid(b))


def cell_borders(cells, clip, eps) -> list:
    """Each cell's boundary **minus the coastline**: the district-vs-district lines only.

    `district_borders` takes the pairwise `∂A ∩ ∂B`, which is right when both polygons are
    unions of cells from one Voronoi diagram and therefore share numerically identical edges.
    Power cells are clipped independently, half-plane by half-plane, so their shared edges agree
    only to floating point and a pairwise intersection can come back empty.  Subtracting the
    clip's own boundary is robust to that: what is left of a convex cell's outline once the
    coastline is removed is exactly its borders with other districts.  Each internal border is
    drawn twice, once from each side, which is invisible -- they coincide.
    """
    outline = clip.boundary.buffer(eps)
    segs = []
    for g in cells.values():
        segs.extend(_lines_of(g.boundary.difference(outline)))
    return segs


def power_diagram_of_draw(districts, values, xy, targets=None) -> dict:
    """The power diagram a `{zip: district}` draw implies: centers, weights, and the audit.

    The centers are recovered rather than read from a file, and exactly: `centers.draw` returns
    the M-weighted centroids of its final labels, so recomputing them from the draw and the
    instance reproduces the run's own centers bit for bit -- which is why `metrics.json` does
    not need to carry them.  The weights then come from one transportation LP
    (`centers.power_weights`).

    `outside` is the honest number this figure exists to expose: the zips whose committed
    district is not the district whose power cell they sit in.  Zero would mean the draw is a
    power diagram, i.e. compactness-optimal at its own centers.  A positive count is where the
    Nash polish bought balance with compactness -- the open lexicographic decision, made
    visible instead of averaged away.

    `targets` defaults to the draw's **own** district masses, which is what makes that
    comparison fair: the cells and the committed draw then hold identical masses district for
    district, and the only thing that differs is which zips.  Asking at the exactly-equal split
    instead would mix in a balance difference the draw never claimed to have (its max-deviation
    is 0.4% of target, not zero), and the fill would be answering a question the dots are not.
    """
    from td.solvers import centers as _centers

    keys = sorted((z for z in districts if z in xy), key=str)
    ids = sorted({districts[z] for z in keys}, key=str)
    lut = {d: i for i, d in enumerate(ids)}
    pts = np.array([xy[z] for z in keys], float)
    M = np.array([max(float(values.get(z, 0.0)), 0.0) for z in keys], float)
    lab = np.array([lut[districts[z]] for z in keys], int)
    if (M <= 0).any():
        raise ValueError("the power-diagram duals divide by M_z; every drawn zip needs M > 0")

    C = _centers._centroids(pts, M, lab, len(ids))
    if targets is None:
        targets = np.bincount(lab, weights=M, minlength=len(ids))
    res = _centers.power_weights(pts, M, C, targets=targets)
    cell = np.asarray(res["labels"], int)
    return dict(
        centers={d: (float(C[i][0]), float(C[i][1])) for d, i in lut.items()},
        weights={d: float(res["weights"][i]) for d, i in lut.items()},
        cell_of={z: ids[int(c)] for z, c in zip(keys, cell)},
        outside=[z for z, c in zip(keys, cell) if ids[int(c)] != districts[z]],
        n_zips=len(keys),
        lp_bound=float(res["lp_bound"]),
        max_dual_violation_rel=float(res["max_dual_violation_rel"]),
        n_fractional=int(res["n_fractional"]),
    )


def figure_power_regions(districts, values, xy, states, out, *, alpha=REGION_ALPHA,
                         footer=FOOTER, title=None, subtitle=None, n_near=4, palette=QUAL,
                         label=True, pad=0.05, targets=None, report=None, dots=True):
    """The draw as **power-diagram territory**: `k` convex cells, weights from the LP duals.

    This replaces the Voronoi-catchment fill as the territory map, because it is the shape the
    method actually produces.  What a reader gets that the old figure could not give them:

    * a border that is a *straight line* with a meaning -- "beyond here the other district's
      center is closer, once the weights correct for how much opportunity each has to cover";
    * one region per district instead of a ragged interleave, so "where does my territory stop"
      has an answer that fits in a sentence;
    * the shape of the trade, in the legend.  Every cell holds the same share of M and between
      0.06% and 28% of the ground, so the two columns say the thing the map is for: a district
      is an equal slice of *opportunity*, and opportunity is not spread evenly over the country.
      The three metro slivers are the extreme of that, not a rendering failure -- which is why
      every centre gets a marker and a leader line, so a district too small to see is still
      locatable;
    * and the discrepancy on the same page.  The zips are drawn as dots in their **committed**
      district's colour, over the cells.  A dot whose colour differs from the ground under it is
      a zip the draw assigned against compactness -- no extra encoding, the mismatch *is* the
      mark -- and the count goes in the subtitle rather than a footnote.

    Colours come from `draw_palette`, the call `figure_districts` also makes, so all three
    district figures agree hue-for-hue.  `report` is an optional callable taking one string.
    """
    from matplotlib.collections import LineCollection
    from matplotlib.patches import PathPatch

    say = report or (lambda _s: None)
    keys = [z for z in sorted(districts, key=str) if z in xy]
    order, centroids, colors = draw_palette(districts, values, xy, n_near=n_near,
                                            palette=palette)
    pd = power_diagram_of_draw(districts, values, xy, targets=targets)
    n_out = len(pd["outside"])
    say(f"power: weights from the transportation duals, max dual violation "
        f"{pd['max_dual_violation_rel']:.1e} relative, {pd['n_fractional']} split zip(s); "
        f"{n_out} of {pd['n_zips']} zips ({n_out / max(pd['n_zips'], 1):.1%}) lie outside "
        f"their own district's cell")

    title = title or f"District territories — {len(order)} power cells on equal opportunity"
    if len(keys) < 2:
        fig, _ = _canvas(None, title, subtitle or "", footer)
        return _save(fig, out)

    clip = clip_region([xy[z] for z in keys], states, pad)
    cells = power_cells(pd["centers"], pd["weights"], clip)
    missing = [d for d in order if d not in cells]
    if missing:
        say(f"power: {len(missing)} cell(s) fell outside the clip polygon entirely: {missing}")
    area_total = sum(g.area for g in cells.values()) or 1.0
    shares = sorted(g.area / area_total for g in cells.values()) or [0.0]
    say("power: cell area shares run " + ", ".join(
        f"{d}={100 * cells[d].area / area_total:.2f}%" for d in sorted(cells, key=str)))

    subtitle = subtitle or (
        "fill = each district's power (Laguerre) cell — its centre plus a weight from the "
        "transportation LP's duals, so every border is an exact straight line\nequal "
        f"opportunity is not equal ground: every cell holds {100.0 / max(len(cells), 1):.1f}% "
        f"of M and between {100 * shares[0]:.2f}% and {100 * shares[-1]:.0f}% of the map  ·  "
        f"dots = the committed draw, {n_out} of {pd['n_zips']} outside their own cell")
    fig, ax = _canvas(None, title, subtitle, footer)          # states drawn last, on top

    x0, y0, x1, y1 = clip.bounds
    eps = 1e-4 * float(np.hypot(x1 - x0, y1 - y0))

    for d in order:                                            # 1. fills
        g = cells.get(d)
        if g is None:
            continue
        for path in _poly_paths(g):
            ax.add_patch(PathPatch(path, facecolor=colors[d], edgecolor="none",
                                   alpha=alpha, zorder=1))
    # 2. a sliver cell is real territory that no fill can show -- D09's is 0.06% of the map, a
    # hairline over Los Angeles -- so anything under `SLIVER_SHARE` is additionally stroked in
    # its own colour.  The stroke is the only mark that survives at that size; without it the
    # district simply is not on the map.
    tiny = [d for d, g in cells.items() if g.area / area_total < SLIVER_SHARE]
    for d in tiny:
        ax.add_collection(LineCollection(_lines_of(cells[d].boundary), colors=colors[d],
                                         linewidths=SLIVER_W, capstyle="round", zorder=2))
    if tiny:
        say(f"power: {len(tiny)} sliver cell(s) stroked in their own colour: "
            + ", ".join(f"{d} ({100 * cells[d].area / area_total:.2f}%)" for d in sorted(tiny)))
    borders = cell_borders(cells, clip, eps)                   # 3. cell vs cell
    ax.add_collection(LineCollection(borders, colors=BORDER, linewidths=BORDER_W,
                                     capstyle="round", joinstyle="round", zorder=3))
    say(f"power: {len(cells)} cells, {len(borders):,} border segments")

    if dots:                                                   # 4. the committed draw
        px = np.array([xy[z][0] for z in keys], float)
        py = np.array([xy[z][1] for z in keys], float)
        ax.scatter(px, py, s=DOT_MARKER, c=[colors[districts[z]] for z in keys],
                   linewidths=DOT_EDGE_W, edgecolors="white", zorder=4)
    if states is not None:                                     # 5. states, on top but light
        states.boundary.plot(ax=ax, color=OUTLINE, linewidth=STATE_W_REGIONS, zorder=5)

    # 6. a marker at every centre.  The centre is the one point of a district that always
    # exists and always reads, so it anchors the label; a leader line closes the gap whenever
    # the label had to move.  A sliver's label is *forced* off its centre -- a box sitting on a
    # hairline hides the only mark the district has -- and the leader is what puts it back.
    cen = pd["centers"]
    for d in order:
        if d in cen:
            ax.scatter([cen[d][0]], [cen[d][1]], s=26, facecolor="white", edgecolor=BORDER,
                       linewidths=0.9, zorder=6)
    if label:
        min_sep = LABEL_SEP * (x1 - x0)
        anchors = {d: p for d, p in cen.items() if d not in tiny}
        spots = label_points(order, cells, anchors, min_sep)
        for d, (lx, ly) in spots.items():
            if d in tiny:                       # push clear of the hairline, then point back
                cx, cy = cen[d]
                ang = np.arctan2(cy - 0.5 * (y0 + y1), cx - 0.5 * (x0 + x1))
                lx, ly = cx + 1.2 * min_sep * np.cos(ang), cy + 1.2 * min_sep * np.sin(ang)
            if d in cen and float(np.hypot(lx - cen[d][0], ly - cen[d][1])) > 0.35 * min_sep:
                ax.plot([cen[d][0], lx], [cen[d][1], ly], color=BORDER, linewidth=0.7,
                        alpha=0.8, zorder=6, solid_capstyle="round")
            ax.text(lx, ly, str(d), color=LABEL_TEXT, fontsize=8, fontweight="bold",
                    ha="center", va="center", zorder=7,
                    bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                              edgecolor="none", alpha=0.82))
    _district_legend(fig, districts, values, colors, order,
                     second={d: g.area / area_total for d, g in cells.items()},
                     second_label="area")
    mx, my = 0.02 * (x1 - x0), 0.02 * (y1 - y0)
    ax.set_xlim(x0 - mx, x1 + mx)
    ax.set_ylim(y0 - my, y1 + my)
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
    ap.add_argument("--regions", default=None, metavar="DRAW_CSV",
                    help="the same draw.csv; adds district_regions.png (power-diagram "
                         "territories)")
    ap.add_argument("--regions-voronoi", default=None, metavar="DRAW_CSV",
                    help="the superseded zip-catchment rendering, as "
                         "district_regions_voronoi.png")
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

    for flag, name in (("districts", "districts.png"),
                       ("regions", "district_regions.png"),
                       ("regions_voronoi", "district_regions_voronoi.png")):
        path = getattr(args, flag)
        if not path:
            continue
        draw = read_draw(path)
        stray = [z for z in draw if z not in M]
        if stray:
            print(f"WARNING: {len(stray)} zip(s) in the draw are not in the instance, "
                  f"ignored e.g. {stray[:5]}")
            draw = {z: d for z, d in draw.items() if z in M}
        unplaced = [z for z in M if z not in draw]
        ids = sorted(set(draw.values()), key=str)
        n_off, share = drop_share({z: M[z] for z in draw}, xy)
        print(f"{name:<20} {len(draw):>5,} zips in {len(ids)} districts; "
              f"{n_off} unplottable ({share:.2%} of their M); "
              f"{len(unplaced)} instance zip(s) not in the draw")
        dest = os.path.join(args.out, name)
        builder = {"districts": figure_districts,
                   "regions": figure_power_regions,
                   "regions_voronoi": figure_district_regions}[flag]
        kw = {} if flag == "districts" else dict(report=print)
        written.append(builder(draw, M, xy, states, dest, **kw))

    for p in written:
        print(f"wrote {p}  ({os.path.getsize(p) / 1024:.0f} KB)")
    return 0


def share_of(zips, values) -> float:
    total = sum(values.values())
    return (sum(values.get(z, 0.0) for z in zips) / total) if total else 0.0


if __name__ == "__main__":
    sys.exit(main())
