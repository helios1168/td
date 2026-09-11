"""Build the published artifact: splice a generated firm-territory SVG into the template.

Reads  state-atoms.tpl.html   (the hand-edited source, carrying <!--MAP--> and <!--MAPSTATS-->)
Writes state-atoms.html       (what gets published)

The map shows, per zip, which of the two masked firms holds book there:

    fa   only F0 has book          fas  both have book, F0 leads
    fb   only F1 has book          fbs  both have book, F1 leads
    fn   no book at all (untapped / vacant)

Bubble area is proportional to M(z), so the map reads as opportunity, not as headcount.
"""
import os
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
# the descaled instance is gitignored and hub-only (CLAUDE.md); a worktree carries none, so
# TD_DATA_ROOT points a run there at the hub's copy.
DATA_ROOT = Path(os.environ.get("TD_DATA_ROOT", REPO))

sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from td import geo, instance
import us_maps

# the template lives beside this script (state-atoms.tpl.html); the old literal pointed at a
# now-gone Claude-session job tmp dir, which was never the tracked source.
TPL = HERE / "state-atoms.tpl.html"
OUT = HERE / "state-atoms.html"

W, H = 1000.0, 620.0          # viewBox; the LAEA frame is fitted into this with a margin
PAD = 14.0
R_MAX, R_MIN = 13.0, 1.15

d = instance.load_descaled(str(DATA_ROOT / "instance_descaled_v2.json.gz"))
G = d.G

# ---- per-zip firm book -------------------------------------------------------------------
cls_of, M_of = {}, {}
for z in G.nodes:
    S = G.nodes[z].get("S") or {}
    M_of[z] = float(G.nodes[z].get("M") or 0.0)
    byf = defaultdict(float)
    for rep, v in S.items():
        byf[d.firm.get(rep, "?")] += float(v)
    f0, f1 = byf.get("F0", 0.0), byf.get("F1", 0.0)
    if f0 <= 0 and f1 <= 0:
        cls_of[z] = "fn"
    elif f0 > 0 and f1 > 0:
        cls_of[z] = "fas" if f0 >= f1 else "fbs"
    else:
        cls_of[z] = "fa" if f0 > 0 else "fb"

# ---- projection --------------------------------------------------------------------------
pts = geo.zcta_points()
xy, missing, off_map = us_maps.conus_xy(list(G.nodes), pts)
gdf = geo.states_outline()

xs = [p[0] for p in xy.values()]
ys = [p[1] for p in xy.values()]
b = gdf.total_bounds                      # minx, miny, maxx, maxy in LAEA
minx, miny = min(b[0], min(xs)), min(b[1], min(ys))
maxx, maxy = max(b[2], max(xs)), max(b[3], max(ys))
span_x, span_y = maxx - minx, maxy - miny
s = min((W - 2 * PAD) / span_x, (H - 2 * PAD) / span_y)
ox = (W - span_x * s) / 2.0
oy = (H - span_y * s) / 2.0


def T(x, y):
    """LAEA metres to SVG user units, y flipped."""
    return (ox + (x - minx) * s, H - oy - (y - miny) * s)


def ring_path(coords):
    out = []
    for i, (x, y) in enumerate(coords):
        px, py = T(x, y)
        out.append(("M" if i == 0 else "L") + f"{px:.1f} {py:.1f}")
    return "".join(out) + "Z"


def poly_paths(geom):
    kind = geom.geom_type
    if kind == "Polygon":
        return [ring_path(list(geom.exterior.coords))]
    if kind == "MultiPolygon":
        return [ring_path(list(g.exterior.coords)) for g in geom.geoms]
    return []


# state outlines, simplified so the path data stays small
paths = []
for geom in gdf.geometry:
    paths.extend(poly_paths(geom.simplify(2500)))
outline = "".join(f'<path d="{p}"/>' for p in paths)

# ---- bubbles -----------------------------------------------------------------------------
mmax = max(M_of[z] for z in xy) or 1.0
drawn = defaultdict(lambda: [0, 0.0])
circles = []
for z in sorted(xy, key=lambda z: -M_of[z]):        # big first, small painted on top
    px, py = T(*xy[z])
    r = R_MIN + (R_MAX - R_MIN) * (M_of[z] / mmax) ** 0.5
    c = cls_of[z]
    drawn[c][0] += 1
    drawn[c][1] += M_of[z]
    circles.append(f'<circle class="{c}" cx="{px:.1f}" cy="{py:.1f}" r="{r:.2f}"/>')

order = ["fa", "fas", "fbs", "fb", "fn"]      # A through B, neutral last
svg = (
    f'<svg viewBox="0 0 {W:.0f} {H:.0f}" role="img" '
    f'aria-label="Booked territory by firm across the lower 48, one bubble per ZIP, '
    f'area proportional to opportunity">'
    f'<g class="outline">{outline}</g>'
    f'<g class="dots">{"".join(circles)}</g>'
    f"</svg>"
)

# ---- stats strip under the map -------------------------------------------------------------
LABEL = {
    "fa": "Firm A only",
    "fas": "Both, A leads",
    "fbs": "Both, B leads",
    "fb": "Firm B only",
    "fn": "No book",
}
tot_M = sum(v[1] for v in drawn.values())
cells = []
for c in order:
    n, m = drawn[c]
    cells.append(
        f'<div class="mapstat"><span class="sw {c}"></span>'
        f'<span class="mk">{LABEL[c]}</span>'
        f'<span class="mv">{m:,.0f}<span class="mpc">{m / tot_M:.1%}</span></span>'
        f'<span class="mn">{n:,} zips</span></div>'
    )
shared_n = drawn["fas"][0] + drawn["fbs"][0]
shared_m = drawn["fas"][1] + drawn["fbs"][1]
cells.append(
    f'<div class="mapstat"><span class="sw fboth"></span>'
    f'<span class="mk">Both firms</span>'
    f'<span class="mv">{shared_m:,.0f}<span class="mpc">{shared_m / tot_M:.1%}</span></span>'
    f'<span class="mn">{shared_n:,} zips</span></div>'
)
stats = "".join(cells)

note = (
    f"Shares are of mapped opportunity. {len(xy):,} of {G.number_of_nodes():,} zips are drawn; "
    f"{len(missing)} carry no gazetteer point and {len(off_map)} fall outside the lower 48. "
    f"The last tile double-counts: it is the two shared classes added together."
)

html = open(TPL, encoding="utf-8").read()
assert "<!--MAP-->" in html and "<!--MAPSTATS-->" in html and "<!--MAPNOTE-->" in html
html = html.replace("<!--MAP-->", svg).replace("<!--MAPSTATS-->", stats).replace("<!--MAPNOTE-->", note)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(html)

print("drawn:", len(xy), "missing:", len(missing), "off_map:", len(off_map))
for c in order:
    n, m = drawn[c]
    print(f"  {LABEL[c]:<16} {n:5d} zips  M {m:9.1f}  {m / tot_M:6.1%}")
print("svg bytes:", len(svg), " out bytes:", len(html))
