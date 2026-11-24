"""Four static WH maps (PNG, keys only) of the owner's 2026-11-24 run without FIXED: today, room to grow, a whole-state sketch.

    $TD_REPO/.venv/bin/python3 tools/maps/wh_maps.py [--data DIR] [--out docs/figures] [--geo CACHE] [--public DIR]

Fixed: scenario CA1_R105R, the CRBG estimate, WH $ = MM_OPP of the gap_cell.csv rows with NEW_DIST 'WH' (NewCo's WH channel; Wells WH
is not counted).  The 7 shortlisted WH people are gap_person.csv's ROLE WH rows; a person's WH territory today is their
territory_today.csv rows with TERR_CHANNEL WH, and their "$ today" the WH $ of those ZIPs.  Shapes: dashboard.dev_geo (TIGER/Line 2025,
EPSG:5070, 250 m), CONUS.  A ZIP that is no ZCTA has no shape: its $ is counted and it is not drawn.
  1 today: the 7 territories at ZIP level, each assigned state in bold;   2 room to grow: WH $ by state, with a neighbours table;
  3 sketch: whole-state groups (GROUPS), arithmetic and not a solve;      4 map 1 zoomed to the Northeast, with New York City.
Prints the totals the figures show.  Colours: the Corebridge palette (pm docs/brand.md), secondary colours as data colours."""
import argparse
import collections
import csv
import os
import sys
import textwrap
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import dashboard  # noqa: E402  (dev_geo: the shapes)
import look  # noqa: E402  (polygon_path, place_labels)
import matplotlib  # noqa: E402
import numpy as np  # noqa: E402
import shapely  # noqa: E402
from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: E402
from matplotlib.cm import ScalarMappable  # noqa: E402
from matplotlib.collections import PatchCollection  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, PowerNorm, to_rgb  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import PathPatch, Rectangle  # noqa: E402

matplotlib.rcParams.update({"font.family": "Arial", "text.parse_math": False})   # the brand's PowerPoint face; "$" is a dollar

TD_REPO = os.environ.get("TD_REPO", os.path.normpath(os.path.join(HERE, "..", "..")))
SCENARIO, EST, DATE = "CA1_R105R", "CRBG", "2026-11-24"
SUBTITLE = "CRBG estimate, without fixed annuity, scenario CA1_R105R"
VIOLET, DARK, LIGHT, LINE = "#4F00CA", "#20113E", "#E0E0FB", "#8C8C8C"
COLOUR = {"R68": "#3562FF", "R13": "#42ACF6", "R131": "#EC602F", "R37": "#FA9454", "R16": "#C053EF", "R18": "#4CD6BB",
          "R72": "#008368"}                      # one per person on every map; people who touch get unlike colours
OVERLAP = DARK                                   # a ZIP in two of the 7's territories
RAMP = LinearSegmentedColormap.from_list("wh", [(0, "#F7F6FE"), (0.3, LIGHT), (0.65, "#A080E8"), (1, VIOLET)])
GROUPS = [("R18", "MD DC DE VA"), ("R16", "NC SC GA TN"), ("R37", "OH IN KY MI WV"), ("R13", "TX OK LA AR"),
          ("R68 · R131 · R72", "NJ NY PA MA CT RI NH ME VT"), ("new A", "FL AL MS"), ("new B", "IL MN WI MO IA KS NE ND SD"),
          ("new C", "CA"), ("new D", "AZ CO WA NV UT OR ID NM MT WY")]          # map 3 (the owner's sketch, 2026-11-24)
NEW = {"new A": "#BDBDBD", "new B": "#EBEBEB", "new C": "#A6A6A6", "new D": "#D2D2D2"}
DPI = 110                                        # 16 in wide: 1760 px
BOX = (-2.41e6, 0.20e6, 2.50e6, 3.22e6)          # CONUS, with room in the Atlantic for the small states' labels
NE_BOX = (1.17e6, 1.88e6, 2.36e6, 3.04e6)        # NJ NY PA and New England
NYC_BOX = (1.795e6, 2.150e6, 1.880e6, 2.218e6)
# hand-set label places, EPSG:5070 metres: (the label's centre, the point its leader ends at or None)
AT1 = {"R68": ((1.60e6, 2.15e6), None), "R13": ((-0.25e6, 1.28e6), None), "R131": ((2.15e6, 2.08e6), (1.93e6, 2.21e6)),
       "R37": ((1.08e6, 2.00e6), None), "R16": ((1.47e6, 1.52e6), None), "R18": ((2.03e6, 1.79e6), (1.68e6, 1.94e6)),
       "R72": ((2.07e6, 2.80e6), None)}
AT3 = {"R18": ((2.06e6, 1.76e6), (1.60e6, 1.80e6)), "R16": ((1.25e6, 1.39e6), None), "R37": ((0.95e6, 2.16e6), None),
       "R13": ((-0.25e6, 1.05e6), None), "R68 · R131 · R72": ((1.52e6, 2.84e6), (1.60e6, 2.42e6)), "new A": ((0.78e6, 1.03e6), None),
       "new B": ((0.02e6, 2.15e6), None), "new C": ((-2.03e6, 1.80e6), None), "new D": ((-1.30e6, 2.22e6), None)}
AT4 = {"R68": ((1.62e6, 2.13e6), None), "R131": ((2.08e6, 2.11e6), (1.93e6, 2.215e6)), "R72": ((2.09e6, 2.78e6), None),
       "R18": ((1.50e6, 1.93e6), None), "R37": ((1.235e6, 2.05e6), None)}
AT_NYC = {"R68": ("Manhattan", (1.810e6, 2.207e6), (1.8275e6, 2.192e6)), "R131": ("Long Island", (1.862e6, 2.193e6), None)}   # the inset
OFF2 = {"VT": (1.76e6, 2.79e6, "center"), "NH": (2.215e6, 2.56e6, "left"), "MA": (2.215e6, 2.48e6, "left"),
        "RI": (2.10e6, 2.235e6, "left"), "CT": (2.03e6, 2.15e6, "left"), "NJ": (1.90e6, 2.045e6, "left"),
        "DE": (1.88e6, 1.955e6, "left"), "MD": (1.88e6, 1.875e6, "left"), "DC": (1.88e6, 1.80e6, "left")}   # map 2: set off the state
CODE_NEAR = [(dx, dy, "center", "center") for dx, dy in ((0, 0), (0, -13), (0, 13), (17, 0), (-17, 0), (15, -12), (-15, 12))]


def b(usd):
    return f"{usd / 1e9:.2f}"


def dots(items, width):
    """The items joined by ' · ' and wrapped to `width`, never inside an item."""
    return textwrap.fill(" · ".join(i.replace(" ", "\u00a0") for i in items), width)


def read(data):
    """The run's WH $ by ZIP and by state, the 7 with their assigned state, and their WH territory today (person -> state -> ZIPs)."""
    def rows(name):
        with open(os.path.join(data, name), newline="") as f:
            yield from (r for r in csv.DictReader(f) if SCENARIO in r["SCENARIO"].split())
    d = SimpleNamespace(usd=collections.Counter(), state=collections.Counter(), nostate=collections.Counter(),
                        today={p: collections.defaultdict(set) for p in COLOUR})
    for r in rows("gap_cell.csv"):
        if r["EST_SOURCE"] == EST and r["NEW_DIST"] == "WH":
            d.usd[r["ZIP_CODE"]] += float(r["MM_OPP"])
            d.state[r["STATE"]] += float(r["MM_OPP"])
            d.nostate[r["ZIP_CODE"]] += float(r["MM_OPP"]) * (not r["STATE"])
    d.assigned = {r["HOLDER"]: r["ASSIGNED_STATES"] for r in rows("gap_person.csv") if r["EST_SOURCE"] == EST and r["ROLE"] == "WH"}
    for r in rows("territory_today.csv"):
        if r["HOLDER"] in d.today and r["TERR_CHANNEL"] == "WH":
            d.today[r["HOLDER"]][r["STATE"]].add(r["ZIP_CODE"])
    d.zips = {p: set().union(*d.today[p].values()) for p in COLOUR}
    held = collections.Counter(z for zs in d.zips.values() for z in zs)
    d.shared = {z for z, n in held.items() if n > 1}
    d.total = sum(d.usd.values())
    d.sum = lambda zips: sum(d.usd[z] for z in zips)
    return d


def check(geo, d):
    """The self-check: the 7 are the ROLE WH people with one state each, GROUPS is a partition of the map's states, the $ tie."""
    assert set(d.assigned) == set(COLOUR) and all(s in geo.states for s in d.assigned.values()), d.assigned
    grouped = [s for _, states in GROUPS for s in states.split()]
    assert sorted(grouped) == sorted(geo.states), set(grouped) ^ set(geo.states)
    assert set(d.state) <= set(geo.states) | {""}, set(d.state) - set(geo.states)
    assert abs(sum(d.state[s] for s in grouped) + d.state[""] - d.total) < 1, "the groups and the no-state $ do not add to the total"


def neighbours(geo, s, km=25):
    """The states sharing at least `km` of state line with `s` (NY and RI share 22 km, all water: left out)."""
    near = geo.states[s].buffer(2000)
    return [o for o, g in geo.states.items() if o != s and near.intersection(g.boundary).length > km * 1000]


def whole(geo, states):
    """The states as one outline: the slivers between two simplified states closed, holes dropped."""
    g = shapely.union_all([geo.states[s].buffer(2000) for s in states]).buffer(-2000)
    return shapely.union_all([shapely.Polygon(p.exterior) for p in shapely.get_parts(g)])


def stripes(g, n, w=30e3):
    """`g` cut into diagonal bands `w` m wide, dealt in turn into `n` shapes (a group shared by n people)."""
    x0, y0, x1, y1 = g.bounds
    h = y1 - y0
    bands = [shapely.Polygon([(x, y0), (x + w, y0), (x + w + h, y1), (x + h, y1)]) for x in np.arange(x0 - h, x1, w)]
    return [g.intersection(shapely.union_all(bands[i::n])) for i in range(n)]


# ---------------------------------------------------------------- drawing

def page(title, box=BOX, size=(16, 9.4), rect=(0.004, 0.05, 0.765, 0.835)):
    fig = Figure(figsize=size, dpi=DPI, facecolor="white")
    FigureCanvasAgg(fig)
    fig.text(0.012, 0.957, title, fontsize=21, fontweight="bold", color=DARK, va="center")
    fig.text(0.012, 0.915, SUBTITLE, fontsize=13, color=VIOLET, va="center")
    return fig, axes(fig, rect, box)


def axes(fig, rect, box):
    ax = fig.add_axes(rect)
    ax.set_xlim(box[0], box[2])
    ax.set_ylim(box[1], box[3])
    ax.set_aspect("equal")
    ax.set_anchor("NW")
    ax.axis("off")
    return ax


def draw(ax, geoms, **kw):
    ax.add_collection(PatchCollection([PathPatch(look.polygon_path(g)) for g in geoms], **kw))


def state_lines(ax, geo):
    draw(ax, geo.states.values(), facecolor="none", edgecolor=LINE, linewidth=0.6, zorder=3)


def bold(ax, g, colour):
    """A bold outline that shows on white and on its own colour (a white casing under it)."""
    draw(ax, [g], facecolor="none", edgecolor="white", linewidth=4.8, zorder=4, joinstyle="round")
    draw(ax, [g], facecolor="none", edgecolor=colour, linewidth=2.6, zorder=5, joinstyle="round")


def codes(ax, geo, avoid=()):
    """Every state's code at its label point, moved off `avoid` and off each other (the largest states first, so the small ones
    move); a crowded-out one is set anyway."""
    items = [(geo.state_pt[s].x, geo.state_pt[s].y, s) for s in sorted(geo.states, key=lambda s: -geo.states[s].area)]
    style = dict(color=DARK, alpha=0.75, fontweight="bold")
    done = {t.get_text() for t in look.place_labels(ax, items, fs=9, avoid=avoid, marker=False, near=CODE_NEAR, leader=[], **style)}
    for x, y, s in items:
        if s not in done:
            ax.text(x, y, s, fontsize=9, ha="center", va="center", zorder=9, clip_on=True, **style)


def callout(ax, text, at, to=None, colour=DARK, fs=11.5):
    """A boxed label centred on `at`, with a leader to `to`."""
    if to:
        ax.plot([at[0], to[0]], [at[1], to[1]], color=DARK, linewidth=1.0, zorder=9.5, solid_capstyle="round")
        ax.plot([to[0]], [to[1]], "o", markersize=3.5, color=DARK, zorder=9.5)
    return ax.text(*at, text, ha="center", va="center", fontsize=fs, fontweight="bold", color=DARK, zorder=10, linespacing=1.15, clip_on=True,
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=colour, linewidth=1.5, alpha=0.94))


def key(fig, y, colours, head, sub="", x=0.778, fs=11):
    """A legend row at figure height `y`: a swatch (one slice per colour), a bold line, plain lines under it.  The next row's y."""
    h = fig.get_figheight()
    for i, c in enumerate(colours):
        fig.add_artist(Rectangle((x + i * 0.016 / len(colours), y - 0.11 / h), 0.016 / len(colours), 0.22 / h, transform=fig.transFigure,
                                 facecolor=c, edgecolor="none"))
    fig.text(x + 0.022, y, head, fontsize=fs, fontweight="bold", color=DARK, va="center")
    if sub:
        fig.text(x + 0.022, y - 0.14 / h, sub, fontsize=fs - 1.5, color=DARK, va="top", linespacing=1.25)
    return y - (0.38 + (sub.count("\n") + 1 if sub else 0) * 0.168) / h


def note(fig, y, text, x=0.778, width=47):
    """Wrapped plain text in the legend column, top at `y`.  The next y."""
    text = "\n".join(textwrap.fill(part, width) for part in text.split("\n"))
    fig.text(x, y, text, fontsize=9.5, color=DARK, va="top", linespacing=1.3)
    return y - (text.count("\n") + 1) * 0.175 / fig.get_figheight() - 0.012


def foot(fig, text):
    fig.text(0.012, 0.014, textwrap.fill(text, 205), fontsize=9.5, color=DARK, va="bottom", linespacing=1.3)


def save(fig, out, name):
    path = os.path.abspath(os.path.join(out, f"{DATE}_{name}.png"))
    fig.savefig(path, dpi=DPI)
    print(path, flush=True)


def territories(ax, geo, d, edge=None):
    """Map 1's layers: white states, each person's ZIPs of today in their colour (a ZIP of two of them in OVERLAP), state lines, each
    assigned state in a bold outline of its person's colour.  `edge` draws the ZIP lines (the zoomed map)."""
    draw(ax, geo.states.values(), facecolor="white", edgecolor="none", zorder=0)
    for p, zips in d.zips.items():
        draw(ax, [geo.zips[z] for z in sorted(zips - d.shared) if z in geo.zips], facecolor=COLOUR[p], edgecolor=edge or COLOUR[p],
             linewidth=0.25, zorder=1)
    draw(ax, [geo.zips[z] for z in sorted(d.shared) if z in geo.zips], facecolor=OVERLAP, edgecolor=edge or OVERLAP, linewidth=0.25, zorder=2)
    state_lines(ax, geo)
    for p, s in d.assigned.items():
        bold(ax, geo.states[s], COLOUR[p])


def today_label(d, p):
    return f"{p} · ${b(d.sum(d.zips[p]))}B today · assigned {d.assigned[p]}"


def by_state(d, p, zips=False):
    """['PA 0.54', 'NY 0.38', 'NJ 0.33']: the person's $ today by state held, largest first."""
    rows = sorted(d.today[p].items(), key=lambda kv: -d.sum(kv[1]))
    return [f"{s} {len(zs):,} ZIPs ${b(d.sum(zs))}B" if zips else f"{s} {b(d.sum(zs))}" for s, zs in rows]


def overlap_note(d):
    """What the legend says of overlap: the ZIPs two of the 7 share, and who holds ZIPs in a state assigned to another of them."""
    out = [f"Overlap (dark): {len(d.shared):,} ZIPs, ${b(d.sum(d.shared))}B, are in two of the 7's WH territories today." if d.shared
           else "No ZIP is in two of the 7's WH territories today: there is no ZIP-level overlap to shade."]
    owner = {s: p for p, s in d.assigned.items()}
    for p in COLOUR:
        for s, zs in d.today[p].items():
            q = owner.get(s, p)
            if q != p:
                out.append(f"In {s}, assigned to {q}: {p} holds {len(zs):,} ZIPs, ${b(d.sum(zs))}B; {q} holds {len(d.today[q][s]):,}, "
                           f"${b(d.sum(d.today[q][s]))}B.")
    return "\n".join(out)


def no_shape_note(geo, d, people):
    rows = [(p, d.sum(z for z in d.zips[p] if z not in geo.zips)) for p in people]
    return ("A ZIP that is not a ZCTA has no shape: its $ is counted, it is not drawn ("
            + ", ".join(f"{p} ${b(v)}B" for p, v in rows if v >= 5e6) + "; under $0.01B for the others).")


def no_state_note(d):
    """Where the $ with no state sits: who of the 7 holds those ZIPs today, and in which state of their territory."""
    rows = [(sum(d.nostate[z] for z in zs), s, p) for p in COLOUR for s, zs in d.today[p].items()]
    return ", ".join(f"${b(v)}B in {s} ZIPs {p} holds today" for v, s, p in sorted(rows, reverse=True) if v >= 5e6)


WH_NOTE = "WH $ = the opportunity of NewCo's WH channel (${}B in total; Wells WH is not counted).  A person's $ today is the WH $ in the ZIPs of their WH territory today.  "


def map_today(geo, d, out):
    fig, ax = page("WH today: the 7 shortlisted wholesalers' current WH territories")
    territories(ax, geo, d)
    labels = [callout(ax, f"{p}\n${b(d.sum(d.zips[p]))}B", *AT1[p], colour=COLOUR[p]) for p in COLOUR]
    codes(ax, geo, labels)
    y = note(fig, 0.875, "Key · WH $ today · preliminary-assignment state\nunder it: the $B today by state held")
    for p in COLOUR:
        y = key(fig, y - 0.008, [COLOUR[p]], today_label(d, p), dots(by_state(d, p), 40))
    y = note(fig, y, "Bold outline: the person's preliminary-assignment state, in their colour.  White: every other ZIP.")
    note(fig, y, overlap_note(d))
    foot(fig, WH_NOTE.format(b(d.total)) + no_shape_note(geo, d, COLOUR))
    save(fig, out, "wh_1_today")


def map_room(geo, d, out):
    fig, ax = page("Room to grow: WH $ by state")
    norm = PowerNorm(0.6, 0, max(d.state[s] for s in geo.states) / 1e9)
    shade = {s: RAMP(norm(d.state[s] / 1e9)) for s in geo.states}
    draw(ax, geo.states.values(), facecolors=[shade[s] for s in geo.states], edgecolor="none", zorder=0)
    state_lines(ax, geo)
    for p, s in d.assigned.items():
        bold(ax, geo.states[s], COLOUR[p])
    style = dict(fontsize=9.5, fontweight="bold", va="center", zorder=9, linespacing=1.0)
    for s, g in geo.states.items():
        pt, v = geo.state_pt[s], b(d.state[s])
        if s in OFF2:
            x, y, ha = OFF2[s]
            ax.annotate(f"{s} {v}", (pt.x, pt.y), xytext=(x, y), ha=ha, color=DARK,
                        arrowprops=dict(arrowstyle="-", color=DARK, linewidth=0.7, shrinkA=1, shrinkB=0), **style)
        else:
            dark = float(np.dot(shade[s][:3], (0.2126, 0.7152, 0.0722))) < 0.45
            ax.text(pt.x, pt.y, f"{s} {v}" if g.bounds[2] - g.bounds[0] > 4e5 else f"{s}\n{v}", ha="center",
                    color="white" if dark else DARK, **style)
    y = note(fig, 0.875, "Person · assigned state, WH $B\nunder it: the states sharing a border with it, WH $B")
    for p in COLOUR:
        s = d.assigned[p]
        near = sorted(neighbours(geo, s), key=lambda o: -d.state[o])
        y = key(fig, y - 0.008, [COLOUR[p]], f"{p} · {s} {b(d.state[s])}",
                dots([f"{o} {b(d.state[o])}" for o in near], 40))
    note(fig, y, "Bold outline: the 7 assigned states, in the person's colour of map 1.")
    cax = fig.add_axes((0.78, 0.105, 0.19, 0.018))
    bar = fig.colorbar(ScalarMappable(norm, RAMP), cax=cax, orientation="horizontal", ticks=[0, 0.1, 0.25, 0.5, 0.75, 1.0])
    bar.outline.set_edgecolor(LINE)
    cax.tick_params(labelsize=9, colors=DARK, length=3)
    cax.set_title("WH $B by state", fontsize=10, fontweight="bold", color=DARK, loc="left")
    foot(fig, f"WH $ = the opportunity of NewCo's WH channel, ${b(d.total)}B in total (Wells WH is not counted); ${b(d.state[''])}B of it has no "
              f"state and is not on the map ({no_state_note(d)}).  A neighbour shares at least 25 km of state line (NY and RI share 22 km, all water: left out).")
    save(fig, out, "wh_2_room_to_grow")


def map_sketch(geo, d, out):
    fig, ax = page("Whole-state sketch: grow the 7 to about $1.0B, carve the rest (11 territories)")
    tint = lambda c: tuple(0.6 * v + 0.4 for v in to_rgb(c))    # noqa: E731  (a tint: the labels stay legible)
    labels, rows, usd = [], [], {}
    for name, states in GROUPS:
        states = sorted(states.split(), key=lambda s: -d.state[s])
        g, usd[name] = whole(geo, states), sum(d.state[s] for s in states)
        people = name.split(" · ") if name.startswith("R") else []
        cols = [tint(COLOUR[p]) for p in people] or [NEW[name]]
        draw(ax, stripes(g, len(cols)) if len(cols) > 1 else [g], facecolors=cols, edgecolor="none", zorder=0)
        draw(ax, [g], facecolor="none", edgecolor=DARK, linewidth=1.9, zorder=4, joinstyle="round")
        text = (f"{name}: ${b(usd[name])}B,\nabout ${b(usd[name] / len(people))}B each" if len(people) > 1 else f"{name} · ${b(usd[name])}B")
        labels.append(callout(ax, text, *AT3[name]))
        rows.append((cols, f"{name} · ${b(usd[name])}B", dots([f"{s} {b(d.state[s])}" for s in states], 40)))
    state_lines(ax, geo)
    codes(ax, geo, labels)
    y = note(fig, 0.875, "Group · WH $B, under it its states' WH $B\nstriped: shared by the three; grey: a new territory")
    for cols, head, sub in rows:
        y = key(fig, y - 0.004, cols, head, sub)
    note(fig, y, f"No state: ${b(d.state[''])}B, in no group.  Total ${b(d.total)}B.")
    foot(fig, "Whole-state arithmetic on the WH $ by state, not a solve.  11 territories: the 7 (R68, R131 and R72 share the Northeast) and new A, B, "
              f"C and D; a 12th would come from one more split of C + D (${b(usd['new C'] + usd['new D'])}B together).  "
              f"${b(d.state[''])}B of the ${b(d.total)}B has no state and is in no group ({no_state_note(d)}).  WH $ = the opportunity of NewCo's WH channel (Wells WH is not counted).")
    save(fig, out, "wh_3_sketch")
    return usd


def map_northeast(geo, d, out):
    trio = ("R68", "R131", "R72")
    fig, ax = page("WH today in the Northeast: where R68, R131 and R72 hold WH territory", NE_BOX, (16, 11), (0.004, 0.06, 0.61, 0.825))
    territories(ax, geo, d, edge="white")
    labels = [callout(ax, f"{p}\n${b(d.sum(d.zips[p]))}B", *AT4[p], colour=COLOUR[p], fs=12.5) for p in AT4]
    codes(ax, geo, labels)
    x0, y0, x1, y1 = NYC_BOX
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=DARK, linewidth=1.3, zorder=8))
    x = 0.625
    y = note(fig, 0.875, "Key · WH $ today · preliminary-assignment state\nunder it: the ZIPs and $ today by state held", x, 80)
    for p in trio:
        y = key(fig, y - 0.006, [COLOUR[p]], today_label(d, p), dots(by_state(d, p, zips=True), 66), x, 12)
    for p in AT4:
        if p not in trio:
            y = key(fig, y - 0.002, [COLOUR[p]], today_label(d, p) + " (in part on this map)", "", x, 10.5)
    note(fig, y - 0.004, "Each ZIP is drawn with its outline.  Bold outline: the person's preliminary-assignment state, in their colour.  "
         "White: every other ZIP.\n" + overlap_note(d), x, 80)
    ins = axes(fig, (x, 0.05, 0.36, 0.345), NYC_BOX)
    territories(ins, geo, d, edge="white")
    ins.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=DARK, linewidth=2.2, zorder=8, clip_on=False))
    zip3 = {p: sorted({z[:3] for z in d.today[p]["NY"]}) for p in AT_NYC}
    assert zip3 == {"R68": ["100", "101", "102"], "R131": ["110", "115", "117", "118", "119"]}, zip3   # what AT_NYC's place names rest on
    for p, (place, at, to) in AT_NYC.items():
        zs = d.today[p]["NY"]
        callout(ins, f"{p} · {place}\n{len(zs):,} ZIPs, ${b(d.sum(zs))}B", at, to, COLOUR[p], 10.5)
    fig.text(x, 0.428, "New York City (the box on the map)", fontsize=11.5, fontweight="bold", color=DARK, va="bottom")
    fig.text(x, 0.405, "NY ZIPs held, by their first three digits: " + "; ".join(f"{p} {' '.join(v)}" for p, v in zip3.items()) + ".",
             fontsize=9.5, color=DARK, va="bottom")
    foot(fig, WH_NOTE.format(b(d.total)) + no_shape_note(geo, d, trio))
    save(fig, out, "wh_4_northeast")


def report(d, groups):
    """The numbers the figures show, as text."""
    out = [f"WH ${b(d.total)}B total; no state ${b(d.state[''])}B", "person  assigned  $B today  ZIPs  by state"]
    out += [f"{p:<7} {d.assigned[p]:<9} {b(d.sum(d.zips[p])):<9} {len(d.zips[p]):<5} {' · '.join(by_state(d, p))}" for p in COLOUR]
    out += ["group: $B = states"] + [f"{name}: {b(groups[name])} = {states}" for name, states in GROUPS]
    out += ["state $B: " + " ".join(f"{s} {b(v)}" for s, v in sorted(d.state.items(), key=lambda kv: -kv[1]) if s)]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", default=os.path.join(TD_REPO, "data", "safe", "wh_2026-11-24"), help="the run folder: gap_cell.csv, gap_person.csv, territory_today.csv")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "docs", "figures"), help="where the four PNGs go")
    ap.add_argument("--geo", default=os.path.join(TD_REPO, "data", "safe", "dev_dashboard", "geo"), help="the shape cache (dashboard.dev_geo makes it)")
    ap.add_argument("--public", default=os.path.join(TD_REPO, "data", "public"), help="the folder of the TIGER/Line 2025 zips")
    args = ap.parse_args(argv)
    geo = dashboard.dev_geo(args.public, args.geo)
    d = read(args.data)
    check(geo, d)
    map_today(geo, d, args.out)
    map_room(geo, d, args.out)
    groups = map_sketch(geo, d, args.out)
    map_northeast(geo, d, args.out)
    print(report(d, groups))
    return 0


if __name__ == "__main__":
    sys.exit(main())
