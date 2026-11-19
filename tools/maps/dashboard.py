"""tools/maps/dashboard.py (issue #153): the run's interactive dashboard, ONE self-contained HTML file opened in Chrome from disk
(no server, no install, no network): the CONUS map of the run's ZIPs, the totals that tie out, a person's card, and tables whose
rows drive the map.  scenario_maps.py writes it next to maps.pdf with names (your screen only).  Dev, keys only, from a run's CSVs:

    python tools/maps/dashboard.py --dev data/safe/dev_dashboard --out data/safe/dev_dashboard/dashboard.html

build(geo, runs, out_path, names=None, products_label=...) assembles dashboard.html + dashboard.css + dashboard.js (the template,
next to this file), the vendored MapLibre GL JS 6.19.0 (vendor/, BSD-3-Clause, the npm tarball's files: the library as an inline
module script (library()), its worker and stylesheet gzip + base64) and the data (payload) into one file.  `runs` is {scenario: {cell, pair, person, load, summary, seat}}, each the (columns,
rows) table a run has (seat: seat_prepare's masked table, or None); the scenario is the key, a table's own SCENARIO column is not read.
The page computes every number on screen from the exported cells, so what tests/test_dashboard.py ties out is what is shown.
Nothing here adds a name: `names` {key: name} comes from the caller (the owner's run), and without it people are keys R<n>.
State abbreviations and names, and the Census regions and divisions, are constants (2025 vintage, CONUS)."""
import argparse
import base64
import collections
import csv
import functools
import gzip
import json
import os
import re
import sys

import numpy as np
import shapely

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import look  # noqa: E402  (CRS, colouring)
import scenario_maps as sm  # noqa: E402  (the classes and their colours, ROLE_OF, the shape loaders)

VENDOR = os.path.join(HERE, "vendor", "maplibre-gl-6.19.0")
VENDORED = {"v-worker": "maplibre-gl-worker.mjs", "v-css": "maplibre-gl.css"}   # element id -> file, embedded gzip + base64
LIBRARY = "maplibre-gl.mjs"                                                       # embedded as an inline module script (library())
MAX_BYTES = 25 * 1024 * 1024   # the page's size budget (issue #153)
Q = 10_000                     # coordinates are integers in 1/Q degree (about 11 m), a ring's first point then deltas
CHANNELS = sm.GAP_CH           # NATIONAL, REGIONAL, WH, OPEN
KINDS = {"cell": "gap_cell.csv", "pair": "gap_pair.csv", "person": "gap_person.csv", "load": "gap_load.csv",
         "summary": "gap_summary.csv", "seat": "seat_fit.csv"}

# The standard Census regions and divisions of the CONUS states and DC (Alaska and Hawaii, Pacific, are not on the map).
REGIONS = [("Northeast", [("New England", "CT ME MA NH RI VT"), ("Middle Atlantic", "NJ NY PA")]),
           ("Midwest", [("East North Central", "IL IN MI OH WI"), ("West North Central", "IA KS MN MO NE ND SD")]),
           ("South", [("South Atlantic", "DE DC FL GA MD NC SC VA WV"), ("East South Central", "AL KY MS TN"),
                      ("West South Central", "AR LA OK TX")]),
           ("West", [("Mountain", "AZ CO ID MT NV NM UT WY"), ("Pacific", "CA OR WA")])]
STATE_NAME = {"AL": "Alabama", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado", "CT": "Connecticut",
              "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "ID": "Idaho", "IL": "Illinois",
              "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
              "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
              "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
              "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
              "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
              "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"}

# The classes (07's header) in sm.GAP_CLASSES order: plain label, what to do with it, what it means.  Colours, all from the
# Corebridge palette (pm/docs/brand.md; secondary colours are for data visualisation): hue says what to do (green nothing, blue
# bargain, violet fill a gap, orange fill an open seat), depth how pressing.  The four fill classes wear the owner-approved
# sm.FILL_CLASSES colours in every view; `fill` is a class's colour in the Fill view (sm.BARGAIN, sm.NO_FILL for the rest).
FILL_OF = {c: col for c, col, *_ in sm.FILL_CLASSES}
CLASSES = [("COVERED", "Covered", "covered", "#D2F5EE", sm.NO_FILL[1], "One shortlisted person works it, and it is assigned to them."),
           ("OVERLAP", "Overlap", "bargain", "#3562FF", sm.BARGAIN[1], "Two or more shortlisted people work it today: to bargain."),
           ("HELD BY ANOTHER", "Held by another", "bargain", "#42ACF6", sm.BARGAIN[1],
            "One shortlisted person works it, and it is assigned to someone else: to bargain."),
           ("GAP (HELD TODAY)", "Gap, held today", "fill", FILL_OF["GAP (HELD TODAY)"], FILL_OF["GAP (HELD TODAY)"],
            "Assigned, but no shortlisted person works it; someone off the shortlist does today: a hand-over."),
           ("GAP (UNHELD)", "Gap, unheld", "fill", FILL_OF["GAP (UNHELD)"], FILL_OF["GAP (UNHELD)"],
            "Assigned, and no one works it today: white space."),
           ("OPEN SEAT HELD", "Open seat, held today", "fill", FILL_OF["OPEN SEAT HELD"], FILL_OF["OPEN SEAT HELD"],
            "No one is assigned to the state in any channel; a shortlisted person works it today."),
           ("OPEN SEAT UNHELD", "Open seat, unheld", "fill", FILL_OF["OPEN SEAT UNHELD"], FILL_OF["OPEN SEAT UNHELD"],
            "No one is assigned to the state in any channel, and no shortlisted person works it today.")]
assert [c[0] for c in CLASSES] == [c for c, *_ in sm.GAP_CLASSES]
# One colour per person on the Territories view: the brand's data colours, alike hues apart in the list (Dark Orchid sits between
# Violet and Orchid and Dark Violet hides the state lines: both left out).  Touching people differ (look.colouring).
PEOPLE_COLOURS = ["#4F00CA", "#42ACF6", "#008368", "#FA9454", "#C053EF", "#4CD6BB", "#3562FF", "#EC602F"]


def keynum(k):
    """Sort key of a person key 'R<n>': its number, then the text."""
    d = "".join(ch for ch in k if ch.isdigit())
    return (int(d) if d else 10 ** 9, k)


def num(v, nd=2):
    """A cell value as a number rounded to `nd` places (an int when whole, to keep the file small); None for NULL or ''."""
    if v is None or v == "":
        return None
    x = round(float(v), nd)
    return int(x) if x == int(x) else x


def lonlat(geoms):
    """The EPSG:5070 geometries in lon/lat (EPSG:4326)."""
    from pyproj import Transformer
    tr = Transformer.from_crs(look.CRS, "EPSG:4326", always_xy=True)
    return shapely.transform(np.array(list(geoms), dtype=object), lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))


def encode(g):
    """A lon/lat (multi)polygon as [[ring, ...], ...], the outer ring first: a ring is flat integers in 1/Q degree, its first point
    then the steps, without the closing point.  A ring that rounds to under 3 points is dropped (a polygon with its outer ring); a
    shape that rounds away altogether is a 3-unit square at its representative point, so every ZIP with a cell can be pointed at."""
    out = []
    for poly in shapely.get_parts(g):
        if poly.geom_type != "Polygon":
            continue
        rings = []
        for i, ring in enumerate([poly.exterior, *poly.interiors]):
            pts = np.round(np.asarray(ring.coords)[:, :2] * Q).astype(np.int64)
            pts = pts[np.r_[True, (np.diff(pts, axis=0) != 0).any(axis=1)]]
            if len(pts) > 1 and (pts[0] == pts[-1]).all():
                pts = pts[:-1]
            if len(pts) < 3:
                if i == 0:
                    break
                continue
            rings.append(np.r_[pts[:1], np.diff(pts, axis=0)].ravel().tolist())
        if rings:
            out.append(rings)
    if not out:
        p = shapely.point_on_surface(g)
        x, y = int(round(p.x * Q)), int(round(p.y * Q))
        out = [[[x - 1, y - 1, 3, 0, 0, 3, -3, 0]]]
    return out


def merged(per):
    """[(mask, row)] of {scenario: [row tuples]} in order of first appearance: a row several scenarios have is there once, bit i
    of its mask set for the i-th scenario (as write_dedup_csv shares rows; a row a scenario has twice is kept twice)."""
    rows = {}
    for i, got in enumerate(per.values()):
        nth = collections.Counter()
        for r in got:
            nth[r] += 1
            k = (r, nth[r])
            rows[k] = rows.get(k, 0) | 1 << i
    return [(m, r) for (r, _), m in rows.items()]


def people_colours(geo, persons):
    """{key: colour}: people of one role whose assigned states touch or coincide, in any scenario, wear different colours (as far
    as PEOPLE_COLOURS goes).  `persons` is [(key, role, [states])]."""
    adj = collections.defaultdict(set)
    for a, b in sm.state_adjacency(geo.states):
        adj[a].add(b)
    near = collections.defaultdict(set)
    by_role = collections.defaultdict(list)
    for key, role, states in persons:
        near[key]
        by_role[role].append((key, set(states), set(states).union(*(adj[s] for s in states))))
    for ps in by_role.values():
        for key, mine, reach in ps:
            near[key].update(k for k, theirs, _ in ps if k != key and reach & theirs)
    return look.colouring(dict.fromkeys(sorted(near, key=keynum)), near, PEOPLE_COLOURS)


def payload(geo, runs, names=None, products_label="products not recorded", run_label=""):
    """The page's data as one JSON-ready dict; see dashboard.js for how each part is read.  Rows shared by scenarios are there once
    with a scenario bit mask (merged); dollars are to the cent; people are indices into `keys`."""
    scenarios = list(runs)
    dicts = lambda s, kind: [dict(zip((c.upper() for c in t[0]), r)) for r in t[1]] if (t := runs[s].get(kind)) else []
    cells = {s: dicts(s, "cell") for s in scenarios}
    ests = sorted({r["EST_SOURCE"] for rs in cells.values() for r in rs})
    ests = [e for e in sm.FIRMS if e in ests] + [e for e in ests if e not in sm.FIRMS]          # CRBG first: the default estimate
    table = lambda s, kind: [r for r in dicts(s, kind) if r.get("EST_SOURCE") in ests]         # a row of no estimate (a TIE row) is not data
    keysets = lambda v: str(v or "").replace(",", " ").split()
    people = {s: table(s, "person") for s in scenarios}
    keys = sorted({k for rs in cells.values() for r in rs for c in ("ASSIGNED", "HOLDERS") for k in keysets(r.get(c))}
                  | {r["HOLDER"] for kind in ("person", "load", "seat") for s in scenarios for r in table(s, kind) if r.get("HOLDER")}
                  | {r[c] for s in scenarios for r in table(s, "pair") for c in ("HOLDER_A", "HOLDER_B")}, key=keynum)
    kix = {k: i for i, k in enumerate(keys)}
    states = sorted(geo.states)
    six = {s: i for i, s in enumerate(states)}
    cell_zips = {str(r["ZIP_CODE"]) for rs in cells.values() for r in rs}
    drawn = sorted(cell_zips & set(geo.zips))                 # the ZIPs with a cell and a shape: the map's; the rest follow, in the totals only
    zips = drawn + sorted(cell_zips - set(geo.zips))
    zix = {z: i for i, z in enumerate(zips)}
    cls = [c[0] for c in CLASSES]
    sets, dists = {}, {}
    intern = lambda d, v: d.setdefault(v, len(d))

    def cell_row(r):
        if r["CLASS"] not in cls or r["CHANNEL"] not in CHANNELS:
            raise SystemExit(f"TD_GAP_CELL has CLASS {r['CLASS']!r}, CHANNEL {r['CHANNEL']!r}; the dashboard knows {cls} and {CHANNELS}")
        return (ests.index(r["EST_SOURCE"]), zix[str(r["ZIP_CODE"])], six.get(str(r["STATE"] or "").upper(), -1),
                intern(dists, str(r.get("NEW_DIST") or "")), num(r["MM_OPP"]) or 0, CHANNELS.index(r["CHANNEL"]),
                intern(sets, tuple(kix[k] for k in keysets(r.get("ASSIGNED")))), cls.index(r["CLASS"]),
                intern(sets, tuple(kix[k] for k in keysets(r.get("HOLDERS")))))
    e_of = lambda r: ests.index(r["EST_SOURCE"])
    rows = {
        "cells": {s: [cell_row(r) for r in cells[s]] for s in scenarios},
        "pairs": {s: [(e_of(r), CHANNELS.index(r["CHANNEL"]), kix[r["HOLDER_A"]], kix[r["HOLDER_B"]], num(r.get("N_ZIPS"), 0), num(r["MM_OPP"]))
                      for r in table(s, "pair")] for s in scenarios},
        "people": {s: [(e_of(r), kix[r["HOLDER"]], str(r.get("SOURCE") or ""), str(r.get("ROLE") or "").upper(),
                        " ".join(keysets(r.get("ASSIGNED_STATES"))).upper(),
                        *(num(r.get(c)) for c in ("OPP_ASSIGNED", "OPP_COVERED", "OPP_OVERLAP", "OPP_GAP", "OPP_HELD_BY_ANOTHER", "OPP_HELD_ELSEWHERE")),
                        num(r.get("N_ZIPS_ASSIGNED"), 0)) for r in people[s]] for s in scenarios},
        "load": {s: [(e_of(r), kix[r["HOLDER"]], str(r["CHANNEL"]), num(r["AREA_KM2"], 1), num(r["ASSIGNED_USD"]), num(r["BASE_USD"]),
                      num(r["MEDIAN_AREA_KM2"], 1), num(r["EXPECTED_USD"]), num(r["LOAD_RATIO"], 3)) for r in table(s, "load")] for s in scenarios},
        "seat": {s: [(e_of(r), str(r["SEAT"]), str(r["KIND"]), kix[r["HOLDER"]], num(r["RANK"], 0), num(r.get("BORDERS"), 0) or 0,
                      num(r.get("SEAT_MM_OPP")), str(r.get("LOAD_BAND") or "")) for r in table(s, "seat") if r.get("SECTION", "SEAT") == "SEAT"]
                 for s in scenarios},
        "summary": {s: [(e_of(r), CHANNELS.index(r["CHANNEL"]), cls.index(r["ITEM"]), num(r.get("N_ZIPS"), 0), num(r["MM_OPP"]))
                        for r in table(s, "summary") if r.get("SECTION") == "CLASS"] for s in scenarios},
    }
    out = {k: [[m, *r] for m, r in merged(v)] for k, v in rows.items()}
    cm = out.pop("cells")
    out["cells"] = {c: [r[i] for r in cm] for i, c in enumerate("mezsducakh")}          # columnar: mask, est, zip, state, dist, usd, channel, assigned, class, holders
    role_states = collections.defaultdict(set)
    for s in scenarios:
        for r in people[s]:
            role_states[r["HOLDER"], str(r.get("ROLE") or "").upper()].update(set(keysets(r.get("ASSIGNED_STATES"))) & set(states))
    colour = people_colours(geo, [(k, role, sorted(st)) for (k, role), st in sorted(role_states.items())] + [(k, "", []) for k in keys])
    ll = dict(zip(states, lonlat(geo.states[s] for s in states)))
    pts = lonlat(geo.state_pt[s] for s in states)
    in_div = {s for _, divs in REGIONS for _, codes in divs for s in codes.split()}
    out.update(
        run=run_label, products=products_label, scenarios=scenarios, ests=ests, channels=list(CHANNELS), roleOf=dict(sm.ROLE_OF),
        classes=[dict(zip(("id", "label", "group", "color", "fill", "help"), c)) for c in CLASSES],
        keys=keys, names={k: str(names[k]) for k in keys if names and names.get(k)}, colour=[colour[k] for k in keys],
        sets=[list(t) for t in sets], dists=list(dists), q=Q,
        regions=[[reg, [[div, [s for s in codes.split() if s in six]] for div, codes in divs if set(codes.split()) & set(six)]]
                 for reg, divs in REGIONS if any(set(codes.split()) & set(six) for _, codes in divs)],
        states=[{"id": s, "name": STATE_NAME.get(s, s), "box": [round(v, 3) for v in ll[s].bounds], "pt": [round(p.x, 3), round(p.y, 3)],
                 "g": encode(ll[s]), "inDivision": s in in_div} for s, p in zip(states, pts)],
        zips=zips, zipGeom=[encode(g) for g in lonlat(geo.zips[z] for z in drawn)],
        base={"REGIONAL": sm.BASE_USD["REGIONAL"]}, kOf=dict(sm.K_OF), beta=sm.BETA)
    return out


def code_of(name):
    """(a vendored module's code up to its closing `export{...}`, the exported names [[local, public]])."""
    with open(os.path.join(VENDOR, name), encoding="utf-8") as f:
        text = f.read()
    head, mark, tail = text.rpartition("export{")
    pairs = [p.split(" as ") for p in tail.partition("}")[0].split(",")]
    if not mark or not all(len(p) in (1, 2) and all(re.fullmatch(r"[\w$]+", n) for n in p) for p in pairs) or "<!--" in text:
        raise SystemExit(f"{name}: no closing `export{{a as B, ...}}` (or it holds `<!--`)")
    return head, pairs


@functools.lru_cache(maxsize=None)
def library():
    """maplibre-gl.mjs as the text of an inline module script: its code as it is up to its closing `export{...}`, which becomes
    `globalThis.maplibregl={...}` with the same names; the source-map comment after it is dropped.  The page's own script reads that
    object: an inline module cannot be imported, and the dynamic import of a blob: URL v1 used is refused by sandboxed viewers (mail
    and file previews) and by some browser policies (owner's bug, 2026-11-19: "failed to fetch dynamically imported module")."""
    head, pairs = code_of(LIBRARY)
    return head + "globalThis.maplibregl={" + ",".join(f"{p[-1]}:{p[0]}" for p in pairs) + "};\n"


@functools.lru_cache(maxsize=None)
def blob(name):
    """A vendored file gzipped (mtime 0, so the build is the same bytes every time) and base64-coded: no '<' in it.  The worker is
    made a classic script, its code up to the closing `export{...}` inside a strict function: a page opened from disk (origin "null")
    cannot start a module worker from a blob: URL, and MapLibre's own way round that, a data: URL, is refused where only blob:
    workers are allowed; a classic blob: worker runs in both (measured in headless Chromium, 2026-11-19)."""
    if name == VENDORED["v-worker"]:
        data = ('(function(){"use strict";' + code_of(name)[0] + "})();\n").encode("utf-8")
    else:
        with open(os.path.join(VENDOR, name), "rb") as f:
            data = f.read()
    return base64.b64encode(gzip.compress(data, 9, mtime=0)).decode("ascii")


def html(data):
    """The page: the template with the stylesheet, the script, the data, the vendored library and its licence put in, each at its
    one mark, in one pass (nothing put in is read for marks)."""
    read = lambda *name: open(os.path.join(HERE, *name), encoding="utf-8").read()
    text = json.dumps(data, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    parts = {"CSS": read("dashboard.css"), "JS": read("dashboard.js"), "LICENCE": read(VENDOR, "LICENSE.txt"), "LIBRARY": library(),
             "DATA": text.replace("</", "<\\/").replace("<!--", "<\\u0021--"),                  # nothing in the data can close or confuse its <script>
             "VENDOR": "\n".join(f'<script type="text/plain" id="{i}">{blob(f)}</script>' for i, f in VENDORED.items())}
    page, marks = read("dashboard.html"), re.compile("<!--(" + "|".join(parts) + ")-->")
    if sorted(marks.findall(page)) != sorted(parts) or any("</script" in parts[k].lower() for k in ("CSS", "JS", "LICENCE", "LIBRARY")):
        raise SystemExit(f"dashboard.html needs each of the marks {sorted(parts)} once (has {sorted(marks.findall(page))}), and no part may hold </script")
    return marks.sub(lambda m: parts[m.group(1)], page)


def build(geo, runs, out_path, names=None, products_label="products not recorded", run_label=""):
    """Write the dashboard of `runs` to `out_path` and return the path.  The file holds `names` when given: your screen only."""
    page = html(payload(geo, runs, names, products_label, run_label)).encode("utf-8")
    if len(page) > MAX_BYTES:
        raise SystemExit(f"{out_path}: the dashboard is {len(page) / 2 ** 20:.1f} MB, over the {MAX_BYTES / 2 ** 20:.0f} MB budget")
    with open(out_path, "wb") as f:
        f.write(page)
    return out_path


# ---------------------------------------------------------------- dev: a run's CSVs and the public shapes, keys only

def read_dev(folder):
    """{scenario: {kind: (columns, rows)}} from a run folder's CSVs; a row's SCENARIO is the scenarios that share it."""
    runs = {}
    for kind, name in KINDS.items():
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            if kind == "seat":
                continue
            raise SystemExit(f"{path}: not there; scenario_maps.py writes it")
        with open(path, encoding="utf-8-sig", newline="") as f:
            rd = csv.reader(f)
            cols = next(rd)
            i = [c.upper() for c in cols].index("SCENARIO")
            for r in rd:
                for s in r[i].split():
                    runs.setdefault(s, {}).setdefault(kind, (cols, []))[1].append(r)
    return runs


def dev_geo(public, cache):
    """The owner's-run shapes (sm.load_geo) rebuilt from the TIGER/Line 2025 files in `public`: projected to EPSG:5070 and simplified
    to 250 m, written once to `cache` in load_table's format, then read by sm.load_geo itself (no connection is used)."""
    import geopandas as gpd
    made = {k: os.path.join(cache, f"{t}_{sm.TOL_M:g}m_5070.tsv.gz") for k, (t, _) in sm.GEO_TABLES.items()}

    def write(kind, keys, geoms):
        os.makedirs(cache, exist_ok=True)
        with gzip.open(made[kind] + ".tmp", "wt", encoding="ascii") as f:
            for k, g in zip(keys, shapely.to_wkb(np.array(list(geoms), dtype=object), hex=True)):
                f.write(f"{k}\t{g}\n")
        os.replace(made[kind] + ".tmp", made[kind])
    if not os.path.exists(made["state"]) or not os.path.exists(made["division"]):
        st = gpd.read_file("zip://" + os.path.join(public, "tl_2025_us_state.zip"), engine="pyogrio").to_crs(look.CRS)
        st = st[st["STATEFP"].isin(sm.STATE_ABBR)]
        write("state", st["STATEFP"], st.geometry.simplify(sm.TOL_M))
        names = [d for _, divs in REGIONS for d, _ in divs]
        div = st.dissolve("DIVISION")
        write("division", [f"{int(c)}|{names[int(c) - 1]}" for c in div.index], div.geometry.simplify(sm.TOL_M))
    if not os.path.exists(made["zcta"]):
        print(f"reading the ZCTA shapes (once; cached in {made['zcta']})", flush=True)
        z = gpd.read_file("zip://" + os.path.join(public, "tl_2025_us_zcta520.zip"), engine="pyogrio", columns=["ZCTA5CE20"],
                          bbox=(-125.5, 24.0, -66.5, 49.8)).to_crs(look.CRS)
        write("zcta", z["ZCTA5CE20"], z.geometry.simplify(sm.TOL_M))
    return sm.load_geo(None, cache)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dev", required=True, metavar="FOLDER", help="a run folder's gap_*.csv and seat_fit.csv (keys only)")
    ap.add_argument("--out", required=True, help="the HTML to write (under data/safe: it is the run's data)")
    ap.add_argument("--public", default=os.path.join(os.environ.get("TD_REPO", sm.ROOT), "data", "public"), help="the folder of the TIGER/Line 2025 zips")
    ap.add_argument("--products", default="products not recorded", help="the run's product label, e.g. 'excluding FIXED'")
    args = ap.parse_args(argv)
    geo = dev_geo(args.public, os.path.join(args.dev, "geo"))
    path = build(geo, read_dev(args.dev), args.out, None, args.products, os.path.basename(os.path.normpath(args.dev)))
    print(f"{os.path.abspath(path)}: {os.path.getsize(path) / 2 ** 20:.1f} MB, keys only (no names)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
