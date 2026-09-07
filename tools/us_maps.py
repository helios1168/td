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
each zip's Voronoi catchment dissolved by district) for comparison.  And

    --regions-fixed battery/results/<run-id>/draw.csv

writes the fixed-diagram pair, `district_regions_fixed_committed.png` and
`..._snapped.png`: **one** power diagram, built once from the committed draw, with the
committed labelling on it and then the labelling its own weights produce.  Every other
rendering recentroids from whatever draw it is handed, so none of them can show that the
snapped labelling has zero zips outside their own cell; this one holds the centres and the
weights fixed and can.  The four originals are unaffected by any flag.

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
def _canvas(states, title, subtitle, footer=FOOTER, *, state_w=0.5, state_color=OUTLINE,
           figsize=FIGSIZE, rect=(0.015, 0.055, 0.845, 0.845)):
    """`figsize`/`rect` default to the landscape overview canvas and its axes box (room held
    on the right for `_district_legend`); the state close-ups are the only caller that
    overrides either, since a portrait subject on that box wastes half the width.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=figsize, dpi=DPI, facecolor=BG)
    ax = fig.add_axes(rect)
    ax.set_facecolor(BG)
    if states is not None:
        states.boundary.plot(ax=ax, color=state_color, linewidth=state_w)
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

    Two decimals, not one.  At k = 18 an equal share is 5.56%, and a whole 5% band spans only
    5.29% to 5.83%, so one decimal collapses five distinct districts onto "5.8%" and hides which
    one actually sits outside the band.

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
        ax.text(x_first, y, f"{100.0 * per.get(d, 0.0) / total:.2f}%", color=TEXT, fontsize=8,
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


# ------------------------------------------------------------------ small-district labels
# Direct labelling breaks when a district's own ground is smaller than the label that would sit
# on it: the white box then covers the very territory it names.  It happens on both district
# figures: a sliver Voronoi cell in `figure_district_regions`, a tight cluster of small bubbles
# in `figure_districts`.  The fix is written once here and called from both, which is what keeps
# a district crossing the same threshold and getting the same leader-line treatment on either map.
LEADER_W = 0.7
LEADER_ALPHA = 0.8


def _label_box_wh(fig, ax, text, fontsize=8, pad=0.22) -> tuple:
    """`(w, h)` of one rendered label box, in the axes' current DATA units.

    Not approximated from the fontsize: 'D1' and 'D18' are not the same width in a bold face,
    and the threshold this feeds is a real area comparison, not a guess.  A throwaway text
    artist, in the same style every label is actually drawn in, is added at the axes centre,
    the figure is forced to draw so Agg computes its metrics, and the *patch's* pixel extent
    (the box, not just the glyphs) is read back and converted through the axes' data<->pixel
    transform.  Requires the axes' final data limits to already be set, since that transform is
    exactly what they fix, and is meant to be called once per figure, not once per label:
    every label here is the same fontsize and near enough the same width.
    """
    cx = 0.5 * sum(ax.get_xlim())
    cy = 0.5 * sum(ax.get_ylim())
    art = ax.text(cx, cy, text, fontsize=fontsize, fontweight="bold", ha="center", va="center",
                 bbox=dict(boxstyle=f"round,pad={pad}", facecolor="white", edgecolor="none"))
    fig.canvas.draw()
    bbox = art.get_bbox_patch().get_window_extent(fig.canvas.get_renderer())
    art.remove()
    (x0, y0), (x1, y1) = ax.transData.inverted().transform([[bbox.x0, bbox.y0],
                                                            [bbox.x1, bbox.y1]])
    return abs(x1 - x0), abs(y1 - y0)


def _box_overlap(a, b) -> float:
    """Overlap area of two `(x0, y0, x1, y1)` boxes; 0 when they do not intersect."""
    ox = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    oy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    return ox * oy


def _leader_spot(anchor, w, h, placed, radii, *, avoid_polys=None, land=None, n_dir=12) -> tuple:
    """Best label-centre near `anchor` for a label that will not fit under it.

    Tried on a compass ring of `n_dir` directions at each radius in `radii` (absolute, data
    units), and scored: overlap with an already-placed label's box dominates (a colliding tag
    is a worse failure than an ugly leader line), then, where given, a point on a *different*
    district's ground (`avoid_polys`, its own district already excluded by the caller) is
    penalised and a point off the landmass (`land`) is rewarded: open water is exactly where
    a tag belongs, since it reads as "nowhere" rather than "someone else's territory."  Neither
    is available on the bubble map, which has no territory polygons; the search still runs, it
    just no longer prefers water over a crowded label cluster.  Always returns a spot, the
    least-bad candidate when every one collides, because a misplaced label is still a smaller
    error than the one this function exists to fix.
    """
    from shapely import Point
    ax0, ay0 = anchor
    best, best_score = None, None
    for r in radii:
        for i in range(n_dir):
            ang = 2.0 * np.pi * i / n_dir
            x, y = ax0 + r * np.cos(ang), ay0 + r * np.sin(ang)
            box = (x - 0.5 * w, y - 0.5 * h, x + 0.5 * w, y + 0.5 * h)
            score = 100.0 * sum(_box_overlap(box, pb) for pb in placed)
            if land is not None or avoid_polys is not None:
                p = Point(x, y)
                if land is not None and not land.covers(p):
                    score -= 1.0
                elif avoid_polys is not None:
                    score += sum(1.0 for poly in avoid_polys.values() if poly.covers(p))
            if best_score is None or score < best_score:
                best, best_score = (x, y, box), score
    return best


def _place_labels(fig, ax, order, anchors, footprint, *, fontsize=8, avoid_polys=None,
                  land=None, min_ratio=1.0) -> None:
    """Direct-labels every district in `order` at `anchors[d]`, white-haloed exactly as the two
    district figures always have, unless `footprint[d]` is too small to hold the label box,
    in which case the label moves to nearby open ground and a thin leader line ties it back to
    `anchors[d]`, which both callers already guarantee is a point inside (or representative of)
    the district.

    'Too small' is a real area comparison: the label box is measured once (`_label_box_wh`) and
    compared to `footprint[d]`, the district's largest polygon part on the territory maps, the
    bounding box of its own plotted points on the bubble map, where there is no polygon at all.
    The two callers build `footprint` differently; this function does not care which.

    `min_ratio` is how many times the label box a footprint must be to keep its label on top.
    At the default of 1.0 the test is only whether the label fits at all, which is the right
    question on a national map, where the alternative to a covered district is a label with
    nowhere to go.  A caller that has zoomed in should ask for more: a label that fits inside a
    region can still hide most of it, and on a state close-up the district is the subject rather
    than one of eighteen.  `_figure_state_detail` passes `STATE_LABEL_ROOM` for that reason.

    Districts are served largest-footprint-first, so the ones with room keep their preferred
    spot and the small interleaved ones are the ones that move, matching `label_points`'s
    ordering, for the same reason.  Requires the axes' final data limits to already be set, and
    may expand them afterwards if a leader label would otherwise be clipped.
    """
    ranked = sorted((d for d in order if d in anchors),
                    key=lambda e: (-footprint.get(e, 0.0), str(e)))
    if not ranked:
        return
    w, h = _label_box_wh(fig, ax, max((str(d) for d in ranked), key=len), fontsize)
    label_area = w * h
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    radii = (0.05 * (x1 - x0), 0.09 * (x1 - x0))
    placed, reach = [], 0.0
    for d in ranked:
        anchor = anchors[d]
        if footprint.get(d, 0.0) >= min_ratio * label_area:
            lx, ly = anchor
        else:
            others = {e: p for e, p in avoid_polys.items() if e != d} if avoid_polys else None
            lx, ly, _ = _leader_spot(anchor, w, h, placed, radii, avoid_polys=others, land=land)
            ax.plot([anchor[0], lx], [anchor[1], ly], color=BORDER, linewidth=LEADER_W,
                   alpha=LEADER_ALPHA, zorder=4.5, solid_capstyle="round")
        box = (lx - 0.5 * w, ly - 0.5 * h, lx + 0.5 * w, ly + 0.5 * h)
        placed.append(box)
        reach = max(reach, x0 - box[0], box[2] - x1, y0 - box[1], box[3] - y1, 0.0)
        ax.text(lx, ly, str(d), color=LABEL_TEXT, fontsize=fontsize, fontweight="bold",
               ha="center", va="center", zorder=5,
               bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="none",
                         alpha=0.82))
    if reach > 0:
        pad = reach + 0.01 * (x1 - x0)
        ax.set_xlim(x0 - pad, x1 + pad)
        ax.set_ylim(y0 - pad, y1 + pad)


def figure_districts(districts, values, xy, states, out, *, max_marker=MAX_MARKER,
                     alpha=ALPHA, footer=FOOTER, title=None, subtitle=None, n_near=4,
                     palette=QUAL, label=True, state_w=0.5, state_color=OUTLINE):
    """The drawn districts: area ∝ M as on `opportunity.png`, colour = district identity.

    `state_w` / `state_color` are the state outline (`--bold-states` sets them heavy and dark
    for a map whose point is where the borders sit against state lines).

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
    fig, ax = _canvas(states, title, subtitle, footer, state_w=state_w, state_color=state_color)
    if v.size == 0:
        return _save(fig, out)

    c = [colors[districts[z]] for z, _ in keep]
    ax.scatter(x, y, s=_sizes(v, float(v.max()), max_marker), c=c, alpha=alpha,
               linewidths=EDGE_W, edgecolors="white")

    if label:
        # freeze the view before measuring anything in data units: a scatter autoscales lazily,
        # and a leader line drawn afterward must not nudge the limits and invalidate the scale
        # `_place_labels` just measured against.
        ax.autoscale_view()
        ax.set_xlim(*ax.get_xlim())
        ax.set_ylim(*ax.get_ylim())
        # there is no territory polygon on this map, so a district's footprint is approximated
        # as the bounding box of its own plotted bubbles, which is what a reader's eye actually
        # has to find the label under.
        by_district = {}
        for z, _ in keep:
            by_district.setdefault(districts[z], []).append(xy[z])
        footprint = {}
        for d, pts in by_district.items():
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            footprint[d] = (max(xs) - min(xs)) * (max(ys) - min(ys))
        land = land_union(states) if states is not None else None
        _place_labels(fig, ax, order, centroids, footprint, land=land)
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


def voronoi_cells(keys, xy, clip, *, zip_state=None, state_polys=None) -> dict:
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

    `zip_state`/`state_polys`, given together (`--clip-states`), make it a Voronoi diagram
    **per state**: each state's polygon is tiled by that state's own zips, so every point in a
    state is coloured by its nearest in-state zip and no cell crosses a state line.  (Clipping
    the national diagram to state polygons instead leaves holes wherever ground is nearer to an
    out-of-state zip.)  Keys with no known state, or a state absent from `state_polys`, keep
    the land-clipped national cell.
    """
    import shapely

    keys = list(keys)
    if zip_state is None or state_polys is None:
        return _voronoi_clipped(keys, xy, clip)
    by_state: dict = {}
    loose = []
    for k in keys:
        s = zip_state.get(k)
        (by_state.setdefault(s, []) if s in state_polys else loose).append(k)
    out = _voronoi_clipped(loose, xy, clip)
    for s, ks in by_state.items():
        sclip = _valid(shapely.intersection(clip, _valid(state_polys[s])))
        if sclip.is_empty:
            continue
        if len(ks) == 1:                              # one zip owns the whole state
            out[ks[0]] = sclip
            continue
        out.update(_voronoi_clipped(ks, xy, sclip))
    return out


def _voronoi_clipped(keys, xy, clip) -> dict:
    """`voronoi_cells` for one clip polygon, no state logic: the national diagram of `keys`
    trimmed to `clip`, with the ordering and bijection checks described there."""
    import shapely
    from shapely import MultiPoint, Point

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
                            palette=QUAL, label=True, pad=0.05, report=None,
                            zip_state=None, state_polys=None,
                            state_w=STATE_W_REGIONS, state_color=OUTLINE):
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

    `report` is an optional callable taking one string; the CLI passes `print`.  `zip_state`/
    `state_polys`, passed through to `voronoi_cells`, are `--clip-states`'s plumbing;
    `state_w` / `state_color` are `--bold-states`'s (the state outline, heavy and dark when the
    map's point is where the borders sit against state lines).
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
        "exact  ·  " + ("each cell clipped to its own state" if state_polys is not None
                        else "clipped to the US landmass")
        + "  ·  colours match districts.png")
    fig, ax = _canvas(None, title, subtitle, footer)          # states drawn last, on top
    if len(keys) < 2:
        return _save(fig, out)

    clip = clip_region([xy[z] for z in keys], states, pad)
    cells = voronoi_cells(keys, xy, clip, zip_state=zip_state, state_polys=state_polys)
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
        states.boundary.plot(ax=ax, color=state_color, linewidth=state_w, zorder=4)

    # fixed here, before labelling, rather than after: `_place_labels` measures a label box in
    # data units, which needs the axes' final scale, and a leader label pushed out to open water
    # must still land inside the frame this sets.
    mx, my = 0.02 * (x1 - x0), 0.02 * (y1 - y0)
    ax.set_xlim(x0 - mx, x1 + mx)
    ax.set_ylim(y0 - my, y1 + my)

    if label:                                                  # 5. labels
        anchors = label_points(order, polys, centroids, LABEL_SEP * (x1 - x0))
        footprint = {d: _largest_part(g).area for d, g in polys.items()}
        _place_labels(fig, ax, order, anchors, footprint, avoid_polys=polys, land=clip)
    _district_legend(fig, districts, values, colors, order)
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

    Pass `targets="equal"` for the exactly-equal split, which is the right question when the
    diagram is being used to *produce* a labelling rather than to audit one: the snap
    measurements in `docs/OPTIONS_power-cell-contiguity.md` §4 are all at equal-split targets,
    and they reach about half the spread and a third of the gap of the own-masses snap.
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
    elif isinstance(targets, str):
        if targets != "equal":
            raise ValueError(f"targets: expected an array, None, or 'equal', got {targets!r}")
        targets = np.full(len(ids), float(M.sum()) / len(ids))
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
        split_zips={keys[i]: float(M[i]) for i in res["fractional"]},
    )


def figure_power_regions(districts, values, xy, states, out, *, alpha=REGION_ALPHA,
                         footer=FOOTER, title=None, subtitle=None, n_near=4, palette=QUAL,
                         label=True, pad=0.05, targets=None, report=None, dots=True,
                         diagram=None, palette_of=None, mark=None):
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
      The metro slivers are the extreme of that, not a rendering failure -- six of them at
      k=18, not the three the k=13 v1 draw had -- which is why
      every centre gets a marker and a leader line, so a district too small to see is still
      locatable;
    * and the discrepancy on the same page.  The zips are drawn as dots in their **committed**
      district's colour, over the cells.  A dot whose colour differs from the ground under it is
      a zip the draw assigned against compactness -- no extra encoding, the mismatch *is* the
      mark -- and the count goes in the subtitle rather than a footnote.

    Colours come from `draw_palette`, the call `figure_districts` also makes, so all three
    district figures agree hue-for-hue.  `report` is an optional callable taking one string.

    **The fixed-diagram mode.**  By default the diagram is rebuilt from `districts`, which is
    right for auditing a draw and wrong for exhibiting a labelling that *came from* a diagram:
    rebuilding recentroids first, so a snapped labelling is scored against the next iterate
    rather than against the weights that produced it, and the zero it is entitled to cannot
    appear (`docs/OPTIONS_power-cell-contiguity.md` §4).  Pass `diagram=` a dict from
    `power_diagram_of_draw` to hold the centres and weights fixed instead; the fill, the
    centres and the labels then come from that diagram and only the dots come from
    `districts`.  `palette_of` takes the labelling the hues are derived from, so a before/after
    pair on one diagram keeps D07 the same colour in both panels.  `mark` is an iterable of
    zips to ring in the border colour -- the LP's split zips, which have no single cell and
    whose rendered colour is the argmin's arbitrary choice between the two they straddle.
    """
    from matplotlib.collections import LineCollection
    from matplotlib.patches import PathPatch

    say = report or (lambda _s: None)
    keys = [z for z in sorted(districts, key=str) if z in xy]
    order, centroids, colors = draw_palette(palette_of or districts, values, xy, n_near=n_near,
                                            palette=palette)
    pd = (power_diagram_of_draw(districts, values, xy, targets=targets) if diagram is None
          else diagram)
    # against the diagram actually drawn, which is `pd["outside"]` in the default case and the
    # whole point of the figure when a fixed diagram was handed in
    cell_of = pd["cell_of"]
    outside = [z for z in keys if z in cell_of and cell_of[z] != districts[z]]
    n_out = len(outside)
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
    # 2. a sliver cell is real territory that no fill can show -- at k=18 D14's is 0.04% of the
    # map, a hairline over Los Angeles, and D01's 0.06% over New York; six cells are under
    # `SLIVER_SHARE` -- so anything under `SLIVER_SHARE` is additionally stroked in
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
        # a split zip sits on a bisector and belongs to no single cell; the argmin picked one
        # for it, so it is ringed rather than left to read as a settled assignment
        ringed = [z for z in (mark or ()) if z in xy]
        if ringed:
            ax.scatter([xy[z][0] for z in ringed], [xy[z][1] for z in ringed],
                       s=4.0 * DOT_MARKER, facecolor="none", edgecolors=BORDER,
                       linewidths=0.7, zorder=4.5)
            say(f"power: {len(ringed)} split zip(s) ringed: "
                + ", ".join(sorted(ringed, key=str)))
    if states is not None:                                   # 5. states, on top but light
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


FIXED_COMMITTED = "district_regions_fixed_committed.png"
FIXED_SNAPPED = "district_regions_fixed_snapped.png"


def figures_fixed_diagram(districts, values, xy, states, outdir, *, targets="equal",
                          report=None, rebuild=True, **kw) -> list:
    """The before/after pair that shows the zero-mismatch guarantee: **one** diagram, two
    labellings.

    Every other power-diagram figure recomputes centres from the labelling it is handed, so
    rendering a snapped draw builds a *new* diagram from the snapped labels and scores the
    labelling against that one -- 16 of 3,704 outside rather than the zero the snap is entitled
    to (`docs/OPTIONS_power-cell-contiguity.md` §4).  Here the diagram is built once, from the
    committed draw, and both panels are drawn on it:

    * `district_regions_fixed_committed.png` -- the committed labelling on its own diagram, the
      drift this route exists to remove (266 of 3,704 at the equal-split targets used here; the
      register's 258 is the same count at the own-masses targets, and the two are not the same
      question);
    * `district_regions_fixed_snapped.png` -- the same centres, the same weights, the same
      hues, with the dots recoloured by the labelling those weights produced.  Zero outside,
      and the subtitle says what the zero is relative to.

    `targets="equal"` by default, matching the snap measurements in §4 rather than the
    own-masses audit `power_diagram_of_draw` defaults to; the two are not interchangeable.  The
    LP's `k - 1` split zips straddle a bisector and are ringed in both panels, since the cell
    each one is drawn in is the argmin's arbitrary pick between the two it sits between.

    `rebuild=True` costs a second transportation LP and buys the qualification the zero needs:
    the count the *next* iterate reports, i.e. what happens when the diagram is rebuilt from
    the snapped labels.  It goes in the snapped panel's subtitle measured rather than quoted,
    so the figure cannot be read as claiming the snapped labelling is its own fixed point.
    """
    say = report or (lambda _s: None)
    pd = power_diagram_of_draw(districts, values, xy, targets=targets)
    snapped = dict(pd["cell_of"])
    split = sorted(pd["split_zips"], key=str)
    n_committed = sum(1 for z, d in snapped.items() if districts[z] != d)
    n_snapped = sum(1 for z, d in snapped.items() if snapped[z] != d)
    n = pd["n_zips"]
    tname = "exactly-equal split" if targets == "equal" else "the draw's own district masses"
    say(f"fixed diagram: centres and weights held at the committed draw's, targets = {tname}; "
        f"committed labelling {n_committed} of {n} outside ({n_committed / max(n, 1):.1%}), "
        f"snapped labelling {n_snapped} of {n} ({n_snapped / max(n, 1):.1%}); "
        f"{len(split)} split zip(s)")

    # the subtitle is set in one column of the frame, so each line has to stay near 120
    # characters; past that it runs under the legend and the qualification is what gets lost
    caveat = "the zero is relative to this diagram, and is not a fixed-point claim"
    if rebuild:
        again = power_diagram_of_draw(snapped, values, xy, targets=targets)
        say(f"fixed diagram: rebuilt from the snapped labels the centres move and "
            f"{len(again['outside'])} of {again['n_zips']} fall outside again, on "
            f"{again['n_fractional']} split zip(s) — which is why no recentroiding figure can "
            f"show the zero")
        caveat += (f": rebuilt from these labels the centres move, and "
                   f"{len(again['outside'])} of {again['n_zips']:,} fall outside again")

    common = dict(diagram=pd, palette_of=districts, mark=split, report=report, **kw)
    held = ("fill, centres and weights held fixed at the diagram the committed draw implies, "
            f"solved at the {tname}")
    return [
        figure_power_regions(
            districts, values, xy, states, os.path.join(outdir, FIXED_COMMITTED),
            title=f"Committed draw on its own power diagram — {n_committed} of {n:,} outside",
            subtitle=(f"{held}\ndots = the committed labelling; a dot whose colour differs "
                      "from the ground under it was assigned against compactness\n"
                      f"the {len(split)} ringed zips are the LP's split zips — they straddle "
                      "a bisector and belong to no single cell"),
            **common),
        figure_power_regions(
            snapped, values, xy, states, os.path.join(outdir, FIXED_SNAPPED),
            title=f"Snapped to that same diagram — {n_snapped} of {n:,} outside",
            subtitle=(f"{held}\nthe same cells as the panel before, not rebuilt; dots = the "
                      "labelling those weights produced, so every dot is on its own ground\n"
                      f"{caveat}"),
            **common),
    ]


# ------------------------------------------------------------------ per-district close-ups
# Business users want to inspect one territory at a time.  Everything a close-up needs, the
# tessellation, the borders, the palette, is the same for all eighteen of them, so it is built
# **once**, here, and every `district_<id>.png` is a different window and a different subject
# onto the identical `cells`/`polys`.
CONTEXT_FILL = "#d6d6d6"       # every district but the one this figure names: present, mute
CONTEXT_ALPHA = 0.9            # solid, not translucent: at REGION_ALPHA it reads as background
DETAIL_PAD = 0.08              # zoom padding, as a fraction of the district's own larger side


def _pad_bounds(bounds, pad) -> tuple:
    """`(x0, y0, x1, y1)` padded by `pad` of its own larger dimension. Shared by the district
    and the state close-ups, so the two zoom the same way."""
    x0, y0, x1, y1 = bounds
    m = pad * max(x1 - x0, y1 - y0)
    return x0 - m, y0 - m, x1 + m, y1 + m


def _district_window(polys, d, pad=DETAIL_PAD) -> tuple:
    """`(x0, y0, x1, y1)` -- the zoom window for one district's close-up: its own territory's
    bounds, padded by `pad` of its own larger dimension so a slice of its neighbours shows too.
    """
    g = polys.get(d)
    if g is None or g.is_empty:
        raise ValueError(f"district {d}: no territory to zoom to")
    return _pad_bounds(g.bounds, pad)


def _figure_district_detail(d, districts, values, xy, states, zip_state, polys, colors,
                            lattice, borders, per, total, out, *, vmax, max_marker=MAX_MARKER,
                            alpha=REGION_ALPHA, pad=DETAIL_PAD, footer=FOOTER):
    """One district's own close-up, drawn from a tessellation the caller built once.

    The subject district keeps its `draw_palette` hue; every other district is the same muted
    grey, so the borders around it read as context rather than as districts a reader has to
    tell apart.  The zip lattice and the district borders are exactly `figure_district_regions`'s,
    passed in rather than rebuilt, so a reader who has seen the overview map recognises this one.
    Zips are drawn as dots sized by M exactly as `figure_districts` sizes them (`vmax` is that
    map's own maximum, so a dot the same size here and there really is the same M).
    """
    from matplotlib.collections import LineCollection
    from matplotlib.patches import PathPatch

    x0, y0, x1, y1 = _district_window(polys, d, pad)

    def hits(b):                       # does a bbox `(x0, y0, x1, y1)` meet the zoom window
        return not (b[2] < x0 or x1 < b[0] or b[3] < y0 or y1 < b[1])

    share = 100.0 * per.get(d, 0.0) / total
    equal = 100.0 / max(len(per), 1)
    zips = sorted(z for z, dd in districts.items() if dd == d)
    zip_states = sorted({zip_state.get(z) for z in zips if zip_state.get(z)})

    title = f"District {d} — close-up"
    subtitle = (f"{share:.2f}% of national opportunity ({share - equal:+.2f} pp vs. the "
               f"{equal:.2f}% equal share)  ·  "
               f"{', '.join(zip_states) if zip_states else 'state unknown'}  ·  "
               f"{len(zips):,} zips")
    fig, ax = _canvas(None, title, subtitle, footer)

    for e, g in polys.items():                                 # 1. fills: subject vs. context
        if g is None or g.is_empty or not hits(g.bounds):
            continue
        fc, fa, z = (colors[d], alpha, 1) if e == d else (CONTEXT_FILL, CONTEXT_ALPHA, 0)
        for path in _poly_paths(g):
            ax.add_patch(PathPatch(path, facecolor=fc, edgecolor="none", alpha=fa, zorder=z))
    def seg_hits(segs):
        return [s for s in segs
               if hits((s[:, 0].min(), s[:, 1].min(), s[:, 0].max(), s[:, 1].max()))]

    ax.add_collection(LineCollection(seg_hits(lattice), colors=CELL_EDGE, linewidths=CELL_EDGE_W,
                                     alpha=CELL_EDGE_ALPHA, zorder=2))        # 2. the zip lattice
    ax.add_collection(LineCollection(seg_hits(borders), colors=BORDER, linewidths=BORDER_W,
                                     capstyle="round", joinstyle="round", zorder=3))  # 3. borders
    if states is not None:                                     # 4. states, on top but light
        states.boundary.plot(ax=ax, color=OUTLINE, linewidth=STATE_W_REGIONS, zorder=4)

    keep = sorted(((z, float(values.get(z, 0.0))) for z in zips
                  if z in xy and values.get(z, 0.0) > 0), key=lambda kv: kv[1])
    if keep:                                                   # 5. the district's own zips
        px = np.array([xy[z][0] for z, _ in keep], float)
        py = np.array([xy[z][1] for z, _ in keep], float)
        pv = np.array([v for _, v in keep], float)
        ax.scatter(px, py, s=_sizes(pv, vmax, max_marker), c=colors[d], alpha=ALPHA,
                  linewidths=EDGE_W, edgecolors="white", zorder=5)

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    return _save(fig, out)


def figures_district_detail(districts, values, xy, states, outdir, *, zip_state=None,
                            state_polys=None, n_near=4, palette=QUAL, pad=DETAIL_PAD,
                            max_marker=MAX_MARKER, report=None) -> list:
    """One `district_<id>.png` per district: a close-up on its own territory, its context
    muted, its zips sized by M, built from a **single** Voronoi tessellation, computed once
    here and reused for all of them, since the tessellation does not depend on which district
    is being zoomed to.
    """
    say = report or (lambda _s: None)
    keys = [z for z in sorted(districts, key=str) if z in xy]
    order, _, colors = draw_palette(districts, values, xy, n_near=n_near, palette=palette)
    clip = clip_region([xy[z] for z in keys], states, 0.05)
    cells = voronoi_cells(keys, xy, clip, zip_state=zip_state, state_polys=state_polys)
    polys = dissolve(cells, districts)
    eps = 1e-4 * float(np.hypot(clip.bounds[2] - clip.bounds[0], clip.bounds[3] - clip.bounds[1]))
    lattice = [seg for g in cells.values() for seg in _lines_of(g.boundary)]
    borders = district_borders(polys, eps)

    per = {}
    for z, dd in districts.items():
        per[dd] = per.get(dd, 0.0) + float(values.get(z, 0.0))
    total = sum(per.values()) or 1.0
    vmax = max((float(values.get(z, 0.0)) for z in districts
               if float(values.get(z, 0.0)) > 0), default=1.0)

    os.makedirs(outdir, exist_ok=True)
    written = []
    for d in order:
        out = os.path.join(outdir, f"district_{d}.png")
        path = _figure_district_detail(d, districts, values, xy, states, zip_state or {}, polys,
                                       colors, lattice, borders, per, total, out,
                                       vmax=vmax, max_marker=max_marker, pad=pad)
        written.append(path)
        say(f"{os.path.basename(path):<20} ({os.path.getsize(path) / 1024:.0f} KB)")
    return written


# ------------------------------------------------------------------ per-state close-ups
# A district close-up names one district and mutes the rest.  A state close-up asks the other
# question, not "what does D06 look like" but "what does California look like", where the
# answer is several districts at once, and the point of the figure is to show every one of them
# in its own hue inside the state, plus whatever other states those same districts also carry.
STATE_HOLD_ETA = 0.01     # a district "holds" a state at >=1% of that state's own M, the same
                          # threshold td.solvers.state_splits.build_milp uses for "state s is in
                          # district j" (its eta, default 0.01), reused here so a state figure's
                          # notion of "carves up" and "reaches into" matches the model's own
STATE_FIG_AREA = FIGSIZE[0] * FIGSIZE[1]   # same pixel budget as the landscape overview canvas
STATE_FIG_MIN_SIDE = 6.0
STATE_FIG_MAX_SIDE = 16.0
STATE_LABEL_ROOM = 4.0    # a district keeps its label on top only if its territory in frame is at
                          # least this many times the label box, so the label covers at most a
                          # quarter of it; below that the label moves off and takes a leader line.
                          # Measured on the four split states, every district is either under 2x
                          # or over 36x, so the exact value inside that gap changes nothing


def state_holdings(districts, values, zip_state, eta=STATE_HOLD_ETA) -> dict:
    """`{state: {district: share}}`: for every state with a zip in `districts`, the districts
    holding at least `eta` of that state's own M, and the exact share each holds.

    A district below `eta` in a state is a boundary zip or two, not a real presence there, so it
    is dropped from both questions this feeds: which districts carve up a state, and which
    other states those same districts reach into.  `eta` matches
    `td.solvers.state_splits.build_milp`'s own state-anchoring threshold (see that module's
    docstring); it is not a value chosen for this file.
    """
    totals, per = {}, {}
    for z, dd in districts.items():
        s = zip_state.get(z)
        if s is None:
            continue
        v = float(values.get(z, 0.0))
        totals[s] = totals.get(s, 0.0) + v
        by_d = per.setdefault(s, {})
        by_d[dd] = by_d.get(dd, 0.0) + v
    out = {}
    for s, by_d in per.items():
        tot = totals.get(s, 0.0) or 1.0
        out[s] = {dd: m / tot for dd, m in by_d.items() if m / tot >= eta}
    return out


def connected_states(state, holdings) -> set:
    """Every state reachable from `state` by one shared district: the districts holding
    `state` (per `holdings`), then every other state those same districts hold.  Always
    includes `state` itself."""
    via = set(holdings.get(state, {}))
    return {s for s, by_d in holdings.items() if via & set(by_d)}


def split_states(holdings) -> list:
    """States held by two or more districts, sorted: the default `--state-figures` subject
    list when none is named on the command line."""
    return sorted(s for s, by_d in holdings.items() if len(by_d) >= 2)


def _fit_figsize(window, area=STATE_FIG_AREA, min_side=STATE_FIG_MIN_SIDE,
                 max_side=STATE_FIG_MAX_SIDE) -> tuple:
    """`(w, h)` inches for a canvas whose aspect ratio matches `window`'s `(x0, y0, x1, y1)`, at
    roughly the landscape overview canvas's own pixel budget.  A portrait subject like
    California gets a portrait page instead of losing half a landscape one to blank margin, and
    a very elongated chain of connected states is clamped to a sane width or height rather than
    growing without bound.
    """
    x0, y0, x1, y1 = window
    aspect = (x1 - x0) / (y1 - y0) if y1 > y0 else 1.0
    w = (area * aspect) ** 0.5
    h = area / w
    if w < min_side:
        w, h = min_side, area / min_side
    elif w > max_side:
        w, h = max_side, area / max_side
    return round(w, 2), round(h, 2)


def _states_window(state_polys, codes, pad=DETAIL_PAD) -> tuple:
    """`(x0, y0, x1, y1)`: the zoom window for a set of states, the union of their own
    polygons' bounds, padded exactly as `_district_window` pads a district's."""
    import shapely
    geoms = [state_polys[c] for c in codes if c in state_polys]
    if not geoms:
        raise ValueError(f"no known polygon for any of {sorted(codes)}")
    return _pad_bounds(shapely.union_all(geoms).bounds, pad)


def _figure_state_detail(code, conn, districts, values, xy, states, zip_state, cells, lattice,
                         colors, state_polys, state_names, clip, holdings, state_totals, grand,
                         out, *, vmax, max_marker=MAX_MARKER, pad=DETAIL_PAD, footer=FOOTER):
    """One state's own close-up: every district active in `code` or one of its connected
    states (`conn`) in its own hue, everything else the muted context grey, the same fill rule
    a district close-up uses except keyed by state membership rather than by one subject
    district.

    Colouring is done at the zip-cell level, not the whole-district level: `cells` restricted to
    `conn` are dissolved by district for the coloured fill, and every other cell is dissolved
    into one grey blob, so a district that reaches beyond `conn` (D17 out of California into
    Idaho, say) is coloured only where it is actually inside `conn` and grey everywhere else in
    the frame.  Labels reuse `_place_labels`, since several of these regions are as small as the
    smallest district close-up's, but at `STATE_LABEL_ROOM` rather than the default threshold:
    here the district is the subject of the figure, so a label that merely fits on top of it is
    still hiding the thing the reader opened the page to see.  Only `code`'s own zips are drawn as dots, matching the
    district close-up's convention of drawing only the subject's own zips.
    """
    from matplotlib.collections import LineCollection
    from matplotlib.patches import PathPatch

    window = _states_window(state_polys, conn, pad)
    x0, y0, x1, y1 = window
    figsize = _fit_figsize(window)

    def hits(b):                       # does a bbox `(x0, y0, x1, y1)` meet the zoom window
        return not (b[2] < x0 or x1 < b[0] or b[3] < y0 or y1 < b[1])

    target_cells = {z: g for z, g in cells.items() if zip_state.get(z) in conn}
    colored_polys = dissolve(target_cells, districts)
    context_parts = [g for z, g in cells.items()
                     if zip_state.get(z) not in conn and hits(g.bounds)]
    local_districts = {z: districts[z] for z in target_cells}
    local_centroids = district_centroids(local_districts, values, xy)

    by_d = holdings.get(code, {})
    share_state = 100.0 * state_totals.get(code, 0.0) / grand
    dist_bits = ", ".join(f"{dd} {100.0 * s:.1f}%"
                          for dd, s in sorted(by_d.items(), key=lambda kv: str(kv[0])))
    others = sorted(conn - {code})
    n = len(by_d)
    title = f"{state_names.get(code, code)} — split across {n} district{'s' if n != 1 else ''}"
    # one clause per line rather than one long run: a portrait canvas is narrower in inches than
    # the landscape overview, at the same fontsize, and a long "reaches into" list (New York
    # reaches into ten states) would otherwise run off the right edge unread
    import textwrap
    chars = max(20, round(120 * figsize[0] / FIGSIZE[0]))
    subtitle = "\n".join(textwrap.fill(line, chars) for line in (
        f"{share_state:.2f}% of national opportunity",
        f"{dist_bits or 'no district holds at least 1% of it'} of {code}'s own opportunity",
        f"reaches into {', '.join(others) if others else 'no other state'}"))
    fig, ax = _canvas(None, title, subtitle, footer, figsize=figsize,
                      rect=(0.02, 0.065, 0.96, 0.80))

    if context_parts:                                          # 1a. context, one grey blob
        import shapely
        context_geom = _valid(shapely.union_all(context_parts))
        for path in _poly_paths(context_geom):
            ax.add_patch(PathPatch(path, facecolor=CONTEXT_FILL, edgecolor="none",
                                   alpha=CONTEXT_ALPHA, zorder=0))
    for dd, g in colored_polys.items():                        # 1b. fills, coloured by district
        if g is None or g.is_empty:
            continue
        for path in _poly_paths(g):
            ax.add_patch(PathPatch(path, facecolor=colors[dd], edgecolor="none",
                                   alpha=REGION_ALPHA, zorder=1))

    def seg_hits(segs):
        return [s for s in segs
               if hits((s[:, 0].min(), s[:, 1].min(), s[:, 0].max(), s[:, 1].max()))]

    ax.add_collection(LineCollection(seg_hits(lattice), colors=CELL_EDGE, linewidths=CELL_EDGE_W,
                                     alpha=CELL_EDGE_ALPHA, zorder=2))        # 2. the zip lattice
    eps = 1e-4 * float(np.hypot(x1 - x0, y1 - y0))
    borders = district_borders(colored_polys, eps)
    ax.add_collection(LineCollection(borders, colors=BORDER, linewidths=BORDER_W,
                                     capstyle="round", joinstyle="round", zorder=3))  # 3. borders
    if states is not None:                                     # 4. states, on top but light
        states.boundary.plot(ax=ax, color=OUTLINE, linewidth=STATE_W_REGIONS, zorder=4)

    keep = sorted(((z, float(values.get(z, 0.0))) for z in districts
                  if zip_state.get(z) == code and z in xy and values.get(z, 0.0) > 0),
                 key=lambda kv: kv[1])
    if keep:                                                   # 5. code's own zips
        px = np.array([xy[z][0] for z, _ in keep], float)
        py = np.array([xy[z][1] for z, _ in keep], float)
        pv = np.array([v for _, v in keep], float)
        c = [colors[districts[z]] for z, _ in keep]
        ax.scatter(px, py, s=_sizes(pv, vmax, max_marker), c=c, alpha=ALPHA,
                  linewidths=EDGE_W, edgecolors="white", zorder=5)

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    order_local = sorted(colored_polys, key=str)               # 6. labels, leader lines if small
    anchors = label_points(order_local, colored_polys, local_centroids, LABEL_SEP * (x1 - x0))
    footprint = {dd: _largest_part(g).area for dd, g in colored_polys.items()}
    _place_labels(fig, ax, order_local, anchors, footprint, avoid_polys=colored_polys, land=clip,
                  min_ratio=STATE_LABEL_ROOM)
    return _save(fig, out)


def figures_state_detail(districts, values, xy, states, outdir, *, zip_state, codes=None,
                         n_near=4, palette=QUAL, pad=DETAIL_PAD, max_marker=MAX_MARKER,
                         eta=STATE_HOLD_ETA, report=None) -> list:
    """One `state_<code>.png` per split state: `codes` defaults to `split_states`, every state
    two or more districts hold at `eta`.

    The Voronoi diagram is always built per state (`--clip-states`'s own clipping, regardless of
    whether that flag was passed for the other figures), since a state close-up is making a
    claim about exactly where a state line falls, and a cell that bleeds across it under the
    national diagram would draw that claim wrong.
    """
    say = report or (lambda _s: None)
    holdings = state_holdings(districts, values, zip_state, eta)
    codes = list(codes) if codes else split_states(holdings)
    if not codes:
        say("state figures: no state is held by two or more districts at this eta")
        return []

    keys = [z for z in sorted(districts, key=str) if z in xy]
    _, _, colors = draw_palette(districts, values, xy, n_near=n_near, palette=palette)
    state_polys = dict(zip(states["STUSPS"], states.geometry))
    state_names = dict(zip(states["STUSPS"], states["NAME"]))
    clip = clip_region([xy[z] for z in keys], states, 0.05)
    cells = voronoi_cells(keys, xy, clip, zip_state=zip_state, state_polys=state_polys)
    lattice = [seg for g in cells.values() for seg in _lines_of(g.boundary)]

    per = {}
    for z, dd in districts.items():
        per[dd] = per.get(dd, 0.0) + float(values.get(z, 0.0))
    grand = sum(per.values()) or 1.0
    state_totals = {}
    for z, s in zip_state.items():
        if s is None or z not in districts:
            continue
        state_totals[s] = state_totals.get(s, 0.0) + float(values.get(z, 0.0))
    vmax = max((float(values.get(z, 0.0)) for z in districts
               if float(values.get(z, 0.0)) > 0), default=1.0)

    os.makedirs(outdir, exist_ok=True)
    written = []
    for code in codes:
        conn = connected_states(code, holdings)
        path = _figure_state_detail(code, conn, districts, values, xy, states, zip_state, cells,
                                    lattice, colors, state_polys, state_names, clip, holdings,
                                    state_totals, grand,
                                    os.path.join(outdir, f"state_{code}.png"),
                                    vmax=vmax, max_marker=max_marker, pad=pad)
        written.append(path)
        say(f"{os.path.basename(path):<16} connects to "
            f"{', '.join(sorted(conn - {code})) or 'no other state'} "
            f"({os.path.getsize(path) / 1024:.0f} KB)")
    return written


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
    ap.add_argument("--clip-states", action="store_true",
                    help="with --regions-voronoi, intersect each zip's cell with its own "
                         "state's polygon; off by default, off path unchanged")
    ap.add_argument("--bold-states", action="store_true",
                    help="draw state boundaries heavy and dark on --districts and "
                         "--regions-voronoi (1.6 pt, #555555); off by default")
    ap.add_argument("--regions-fixed", default=None, metavar="DRAW_CSV",
                    help="the same draw.csv; adds the fixed-diagram pair "
                         "(district_regions_fixed_committed.png / _snapped.png): one diagram, "
                         "the committed labelling and the labelling its weights produced")
    ap.add_argument("--district-figures", default=None, metavar="DRAW_CSV",
                    help="the same draw.csv; adds one district_<id>.png per district, a "
                         "close-up on that district's own territory (honours --clip-states)")
    ap.add_argument("--state-figures", nargs="+", default=None,
                    metavar=("DRAW_CSV", "STATES"),
                    help="the same draw.csv, optionally followed by a comma list of state "
                         "codes (default: every state two or more districts hold); adds one "
                         "state_<code>.png per state, always clipped per state regardless of "
                         "--clip-states")
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
                       ("regions_voronoi", "district_regions_voronoi.png"),
                       ("regions_fixed", "district_regions_fixed_*.png"),
                       ("district_figures", "district_<id>.png")):
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
        if flag == "regions_fixed":                # one diagram, two panels, so not a builder
            written.extend(figures_fixed_diagram(draw, M, xy, states, args.out, report=print))
            continue
        if flag == "district_figures":             # one tessellation, 18 close-ups
            dfkw = {}
            if args.clip_states and states is not None:
                dfkw["state_polys"] = dict(zip(states["STUSPS"], states.geometry))
            if states is not None:
                dfkw["zip_state"] = {z: d.G.nodes[z].get("state") for z in draw}
            written.extend(figures_district_detail(draw, M, xy, states, args.out,
                                                   report=print, **dfkw))
            continue
        dest = os.path.join(args.out, name)
        builder = {"districts": figure_districts,
                   "regions": figure_power_regions,
                   "regions_voronoi": figure_district_regions}[flag]
        kw = {} if flag == "districts" else dict(report=print)
        if flag == "regions_voronoi" and args.clip_states:
            if states is not None:
                kw["zip_state"] = {z: d.G.nodes[z].get("state") for z in draw}
                kw["state_polys"] = dict(zip(states["STUSPS"], states.geometry))
            else:
                print("WARNING: --clip-states has no effect with --no-basemap")
        if flag in ("districts", "regions_voronoi") and args.bold_states:
            kw.update(state_w=1.6, state_color="#555555")
        written.append(builder(draw, M, xy, states, dest, **kw))

    if args.state_figures:                     # its own block: DRAW_CSV plus an optional
                                                 # comma list of states, not a plain path
        sf_path = args.state_figures[0]
        sf_codes = [c.strip().upper() for c in ",".join(args.state_figures[1:]).split(",")
                   if c.strip()] or None
        draw = read_draw(sf_path)
        stray = [z for z in draw if z not in M]
        if stray:
            print(f"WARNING: {len(stray)} zip(s) in the draw are not in the instance, "
                  f"ignored e.g. {stray[:5]}")
            draw = {z: dd for z, dd in draw.items() if z in M}
        if states is None:
            print("WARNING: --state-figures has no effect with --no-basemap")
        else:
            zip_state = {z: d.G.nodes[z].get("state") for z in draw}
            written.extend(figures_state_detail(draw, M, xy, states, args.out,
                                                zip_state=zip_state, codes=sf_codes,
                                                report=print))

    for p in written:
        print(f"wrote {p}  ({os.path.getsize(p) / 1024:.0f} KB)")
    return 0


def share_of(zips, values) -> float:
    total = sum(values.values())
    return (sum(values.get(z, 0.0) for z in zips) / total) if total else 0.0


if __name__ == "__main__":
    sys.exit(main())
