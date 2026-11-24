"""tools/maps/dashboard.py (issue #153): the run's interactive dashboard, ONE self-contained HTML file opened in Chrome from disk
(no server, no install, no network): the CONUS map of the run's ZIPs, the totals that tie out, a person's card, and tables whose
rows drive the map.  scenario_maps.py writes it next to maps.pdf with names (your screen only).  Dev, keys only, from a run's CSVs:

    python tools/maps/dashboard.py --dev data/safe/dev_dashboard --out data/safe/dev_dashboard/dashboard.html

build(geo, runs, out_path, names=None, products_label=..., sales=None) assembles dashboard.html + dashboard.css + dashboard.js (the
template, next to this file), the vendored MapLibre GL JS 6.19.0 (vendor/, BSD-3-Clause, the npm tarball's files: the library as an
inline module script (library()), its worker and stylesheet gzip + base64), the data (payload) and the shapes (gzip + base64: integers
only, so every name, key and dollar of the page stays readable in its text) into one file.  `runs` is
{scenario: {cell, pair, person, load, summary, seat, plan, today, cell_today}}, each the (columns, rows) table a run has (seat:
seat_prepare's masked table, plan: plan_prepare's, today and cell_today: fetch_today's; any of these four may be None); the scenario
is the key, a table's own SCENARIO column is not read.  `sales` is [(seller key, ZIP, $)] (fetch_sales): it goes into the page only.
Three views: the preliminary assignment (07's seven classes shown as four: CLASSES), and each firm's territories today (the holder
of SOURCE x ZIP x channel, 04's rule, by STATUS or by person).  The page computes every number on screen from the exported cells, so
what tests/test_dashboard.py ties out is what is shown.
Nothing here adds a name: `names` {key: name} comes from the caller (the owner's run), and without it people are keys R<n>.
In dev, today's territories and the sales the folder does not have are made up (made_up_today, made_up_sales) and the page says so.
State abbreviations and names, and the Census regions and divisions, are constants (2025 vintage, CONUS)."""
import argparse
import base64
import collections
import csv
import functools
import gzip
import json
import os
import random
import re
import sys
import zlib

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
MAX_BYTES = 15 * 1024 * 1024   # the page's size budget (issue #153): the owner shares the file.  A three-scenario run with every CONUS ZIP
                               # is 9.5 MB, and was 15.2 MB, over this, before its shapes were gzipped (review of #153, 2026-11-19)
Q = 10_000                     # coordinates are integers in 1/Q degree (about 11 m), a ring's first point then deltas
CHANNELS = sm.GAP_CH           # NATIONAL, REGIONAL, WH, OPEN
KINDS = {"cell": "gap_cell.csv", "pair": "gap_pair.csv", "person": "gap_person.csv", "load": "gap_load.csv", "summary": "gap_summary.csv",
         "seat": "seat_fit.csv", "plan": "seat_plan.csv", **sm.TODAY_FILES}
OPTIONAL = ("seat", "plan", *sm.TODAY_FILES)   # a run without 08, or a folder older than the today views, has none

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

# The four classes of the page (owner, 2026-11-19, #153, DATASET_LOG) over 07's seven (DETAIL, unchanged): label, colour, plain
# meaning, the 07 classes it holds.  Colours run from quiet to loud in the Corebridge palette (pm/docs/brand.md): three steps of the
# violets while someone covers the ZIP today (a tint of Violet, as the guidelines allow in charts: Light Violet itself is lost on the
# white land; Orchid; Violet), Dark Orange (a secondary colour, for data) when no one does or no one is assigned.
DETAIL = [c for c, *_ in sm.GAP_CLASSES]
CLASSES = [("Uncontested", "#C9C9F5", "The assigned person already covers it today, alone.", ("COVERED",)),
           ("Contested", "#C053EF", "Two or more people on the roster cover it today; one keeps it.", ("OVERLAP",)),
           ("Transition", "#4F00CA", "Someone other than the assigned person covers it today; it moves to the assigned person.", ("HELD BY ANOTHER", "GAP (HELD TODAY)")),
           ("Open", "#EC602F", "No one covers it today, or no one is assigned.", ("GAP (UNHELD)", "OPEN SEAT HELD", "OPEN SEAT UNHELD"))]
assert sorted(c for *_, of in CLASSES for c in of) == sorted(DETAIL)
# A holder's status in the today views, in this order of precedence, then a ZIP no one holds.
STATUS = [("On the roster", "#4F00CA", "Kept, with a role, in the chosen scenario."),
          ("Proposed", "#C053EF", "Not on the roster; seat plan 1 of the chosen scenario and estimate brings them back for an open seat."),
          ("Not on the roster", "#FA9454", "Holds the territory today and is not on the roster of the chosen scenario."),
          ("No one", "#E5E5E5", "No territory of this firm and channel covers the ZIP today.")]
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


ROLE_WORD = {"NATIONAL": "national", "WIFI": "regional", "WH": "WH", "FI": "FI"}
keysets = lambda v: str(v or "").replace(",", " ").split()


def scenario_labels(people, names=None):
    """{scenario: what sets it apart}, built from what differs: for each person whose role or states are not the same in every
    scenario, the (state, role) pairs this scenario has and not all of them do, by state, e.g. 'CA: R47 (CRBG) national, R108 (EQH)
    regional · TX: R105 (EQH) national' (owner, 2026-11-19: "easy to tell exactly what it is instead of the identifiers").  A name
    stands for its key when `names` has it (the owner's run: screen only).  '' when nothing sets the scenario apart.
    `people` is {scenario: [TD_GAP_PERSON rows as dicts]}."""
    has = {}
    for s, rows in people.items():
        has[s] = {}
        for r in rows:
            pairs = has[s].setdefault(r["HOLDER"], (str(r.get("SOURCE") or ""), set()))[1]
            pairs.update((st, str(r.get("ROLE") or "").upper()) for st in keysets(r.get("ASSIGNED_STATES")) or [""])
    out = {}
    for s in has:
        by_state = collections.defaultdict(list)
        for k in sorted(set().union(*has.values()), key=keynum):
            mine = has[s].get(k, ("", set()))[1]
            for st, role in sorted(mine - set.intersection(*(has[x].get(k, ("", set()))[1] for x in has))):
                src = has[s][k][0]
                by_state[st or "no state"].append(f"{(names or {}).get(k) or k}{f' ({src})' if src else ''} {ROLE_WORD.get(role, role.lower() or 'no role')}")
        out[s] = " · ".join(f"{st}: {', '.join(v)}" for st, v in sorted(by_state.items()))
    return out


def payload(geo, runs, names=None, products_label="products not recorded", run_label="", sales=None, made_up=()):
    """The page's data as one JSON-ready dict; see dashboard.js for how each part is read.  Rows shared by scenarios are there once
    with a scenario bit mask (merged); dollars are to the cent, sales too (a $0.25 sale is a sale: the page rounds only what it shows);
    people are indices into `keys`, ZIPs into `zips`; `geom` is the shapes, which html() embeds apart from the rest."""
    scenarios = list(runs)
    dicts = lambda s, kind: [dict(zip((c.upper() for c in t[0]), r)) for r in t[1]] if (t := runs[s].get(kind)) else []
    cells = {s: dicts(s, "cell") for s in scenarios}
    ests = sorted({r["EST_SOURCE"] for rs in cells.values() for r in rs})
    ests = [e for e in sm.FIRMS if e in ests] + [e for e in ests if e not in sm.FIRMS]          # CRBG first: the default estimate
    table = lambda s, kind: [r for r in dicts(s, kind) if r.get("EST_SOURCE") in ests]         # a row of no estimate (a TIE row) is not data
    people = {s: table(s, "person") for s in scenarios}
    today = {s: dicts(s, "today") for s in scenarios}                                           # today's WH and FI territory pieces
    tcells = {s: table(s, "cell_today") for s in scenarios}                                     # the opportunity by the cell's channel today
    plan = {s: [r for r in table(s, "plan") if str(r["PLAN"]) == "1"] for s in scenarios}       # seat plan 1: the optimum
    sales = sorted(((str(k), str(z), num(v)) for k, z, v in sales or []), key=lambda r: (keynum(r[0]), r[1]))
    keys = sorted({k for rs in cells.values() for r in rs for c in ("ASSIGNED", "HOLDERS") for k in keysets(r.get(c))}
                  | {r["HOLDER"] for kind in ("person", "load", "seat") for s in scenarios for r in table(s, kind) if r.get("HOLDER")}
                  | {r["HOLDER"] for rs in (*today.values(), *plan.values()) for r in rs if r.get("HOLDER")} | {k for k, _, v in sales if k and v}
                  | {r[c] for s in scenarios for r in table(s, "pair") for c in ("HOLDER_A", "HOLDER_B")}, key=keynum)
    kix = {k: i for i, k in enumerate(keys)}
    states = sorted(geo.states)
    six = {s: i for i, s in enumerate(states)}
    st_of = lambda r: six.get(str(r.get("STATE") or "").upper(), -1)
    mapped = {str(r["ZIP_CODE"]) for rs in (*cells.values(), *today.values()) for r in rs}      # a ZIP with a cell or a piece is on the map when it has a shape
    drawn = sorted(mapped & set(geo.zips))
    zips = drawn + sorted(mapped - set(geo.zips) | {str(r["ZIP_CODE"]) for rs in tcells.values() for r in rs} - set(drawn) | {z for _, z, v in sales if v} - set(drawn))
    zix = {z: i for i, z in enumerate(zips)}
    zst = [-1] * len(zips)                                    # a ZIP's state: its cells', else its pieces' (the first that names one)
    for rs in (*cells.values(), *tcells.values(), *today.values()):
        for r in rs:
            if zst[i := zix[str(r["ZIP_CODE"])]] < 0:
                zst[i] = st_of(r)
    sets, dists = {}, {}
    intern = lambda d, v: d.setdefault(v, len(d))

    def cell_row(r):
        if r["CLASS"] not in DETAIL or r["CHANNEL"] not in CHANNELS:
            raise SystemExit(f"TD_GAP_CELL has CLASS {r['CLASS']!r}, CHANNEL {r['CHANNEL']!r}; the dashboard knows {DETAIL} and {CHANNELS}")
        return (ests.index(r["EST_SOURCE"]), zix[str(r["ZIP_CODE"])], st_of(r),
                intern(dists, str(r.get("NEW_DIST") or "")), num(r["MM_OPP"]) or 0, CHANNELS.index(r["CHANNEL"]),
                intern(sets, tuple(kix[k] for k in keysets(r.get("ASSIGNED")))), DETAIL.index(r["CLASS"]),
                intern(sets, tuple(kix[k] for k in keysets(r.get("HOLDERS")))))
    e_of = lambda r: ests.index(r["EST_SOURCE"])
    firms = sorted({r["SOURCE"] for rs in today.values() for r in rs}, key=lambda f: (f not in sm.FIRMS, f))
    tch = [c for c in sm.TODAY_CH if any(r["TERR_CHANNEL"] == c for rs in today.values() for r in rs)]
    hold = collections.defaultdict(set)                       # (firm, channel, ZIP) -> its holders today: the territories are the same in every scenario
    for rs in today.values():
        for r in rs:
            hold[r["SOURCE"], r["TERR_CHANNEL"], zix[str(r["ZIP_CODE"])]].add(kix[r["HOLDER"]])
    cell_today = collections.Counter()
    for s in scenarios:
        for r in tcells[s]:
            cell_today[s, e_of(r), zix[str(r["ZIP_CODE"])], st_of(r), tch.index(r["DIST_CH"]) if r["DIST_CH"] in tch else -1] += float(r["MM_OPP"] or 0)
    rows = {
        "cells": {s: [cell_row(r) for r in cells[s]] for s in scenarios},
        "tc": {s: [(*k[1:], num(v)) for k, v in cell_today.items() if k[0] == s] for s in scenarios},
        "pairs": {s: [(e_of(r), CHANNELS.index(r["CHANNEL"]), kix[r["HOLDER_A"]], kix[r["HOLDER_B"]], num(r.get("N_ZIPS"), 0), num(r["MM_OPP"]))
                      for r in table(s, "pair")] for s in scenarios},
        "people": {s: [(e_of(r), kix[r["HOLDER"]], str(r.get("SOURCE") or ""), str(r.get("ROLE") or "").upper(),
                        " ".join(keysets(r.get("ASSIGNED_STATES"))).upper(), num(r.get("OPP_HELD_ELSEWHERE"))) for r in people[s]] for s in scenarios},
        "roster": {s: sorted({(kix[r["HOLDER"]], str(r["SOURCE"]), str(r.get("KEPT") or ""), str(r.get("ROLE") or "")) for r in today[s]}) for s in scenarios},
        "plan": {s: [(e_of(r), str(r["SEAT"]), str(r["CHOICE"]), kix.get(r.get("HOLDER"), -1)) for r in plan[s]] for s in scenarios},
        "load": {s: [(e_of(r), kix[r["HOLDER"]], str(r["CHANNEL"]), num(r["AREA_KM2"], 1), num(r["ASSIGNED_USD"]), num(r["BASE_USD"]),
                      num(r["MEDIAN_AREA_KM2"], 1), num(r["EXPECTED_USD"]), num(r["LOAD_RATIO"], 3)) for r in table(s, "load")] for s in scenarios},
        "seat": {s: [(e_of(r), str(r["SEAT"]), str(r["KIND"]), kix[r["HOLDER"]], num(r["RANK"], 0), num(r.get("BORDERS"), 0) or 0,
                      num(r.get("SEAT_MM_OPP")), str(r.get("LOAD_BAND") or "")) for r in table(s, "seat") if r.get("SECTION", "SEAT") == "SEAT"]
                 for s in scenarios},
        "summary": {s: [(e_of(r), CHANNELS.index(r["CHANNEL"]), DETAIL.index(r["ITEM"]), num(r.get("N_ZIPS"), 0), num(r["MM_OPP"]))
                        for r in table(s, "summary") if r.get("SECTION") == "CLASS"] for s in scenarios},
    }
    out = {k: [[m, *r] for m, r in merged(v)] for k, v in rows.items()}
    for name, cols in (("cells", "mezsducajh"), ("tc", "mezscu")):         # columnar: mask, est, zip, state, dist, usd, channel, assigned, 07's class, holders
        got = out.pop(name)
        out[name] = {c: [r[i] for r in got] for i, c in enumerate(cols)}
    role_states = collections.defaultdict(set)
    for s in scenarios:
        for r in people[s]:
            role_states[r["HOLDER"], str(r.get("ROLE") or "").upper()].update(set(keysets(r.get("ASSIGNED_STATES"))) & set(states))
    colour = people_colours(geo, [(k, role, sorted(st)) for (k, role), st in sorted(role_states.items())] + [(k, "", []) for k in keys])
    in_state = collections.defaultdict(set)                   # today's holders of a firm in a state wear different colours (as far as the colours go)
    for (f, _, z), ks in hold.items():
        in_state[f, zst[z]].update(ks)
    near = {i: set() for i in range(len(keys))}
    for ks in in_state.values():
        for k in ks:
            near[k].update(ks - {k})
    tcolour = look.colouring(near, near, PEOPLE_COLOURS)      # ponytail: by shared state, not by touching ZIPs; two holders across a state line can match
    ll = dict(zip(states, lonlat(geo.states[s] for s in states)))
    pts = lonlat(geo.state_pt[s] for s in states)
    in_div = {s for _, divs in REGIONS for _, codes in divs for s in codes.split()}
    out.update(
        run=run_label, products=products_label, scenarios=scenarios, ests=ests, channels=list(CHANNELS), roleOf=dict(sm.ROLE_OF),
        labels=scenario_labels(people, names), madeUp=list(made_up), has={"pair": any(runs[s].get("pair") for s in scenarios)},        # no pair table (dev, a file of another run left out): no pair tie-out
        detail=DETAIL, classes=[{"label": c, "color": col, "help": text, "of": [DETAIL.index(d) for d in of]} for c, col, text, of in CLASSES],
        status=[dict(zip(("label", "color", "help"), s)) for s in STATUS],
        keys=keys, names={k: str(names[k]) for k in keys if names and names.get(k)}, colour=[colour[k] for k in keys], tcolour=[tcolour[i] for i in range(len(keys))],
        dists=list(dists), q=Q,
        regions=[[reg, [[div, [s for s in codes.split() if s in six]] for div, codes in divs if set(codes.split()) & set(six)]]
                 for reg, divs in REGIONS if any(set(codes.split()) & set(six) for _, codes in divs)],
        states=[{"id": s, "name": STATE_NAME.get(s, s), "box": [round(v, 3) for v in ll[s].bounds], "pt": [round(p.x, 3), round(p.y, 3)],
                 "inDivision": s in in_div} for s, p in zip(states, pts)],
        zips=zips, zst=zst, nShape=len(drawn),                # the first nShape ZIPs have a shape: geom.zips, in that order; geom.states as `states`
        geom={"zips": [encode(g) for g in lonlat(geo.zips[z] for z in drawn)], "states": [encode(ll[s]) for s in states]},
        today={"firms": firms, "chans": tch, "h": {f"{f}|{c}": [intern(sets, tuple(sorted(hold[f, c, i]))) if (f, c, i) in hold else -1 for i in range(len(zips))]
                                                    for f in firms for c in tch}},
        sales={"k": [kix[k] for k, _, v in sales if k and v], "z": [zix[z] for k, z, v in sales if k and v], "v": [v for k, _, v in sales if k and v]},
        salesNoKey=num(sum(v for k, _, v in sales if not k)),
        base=dict(sm.BASE_USD), beta=sm.BETA)
    out["sets"] = [list(t) for t in sets]                     # after `today`, which adds its holder sets
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


def packed(data):
    """Bytes gzipped (mtime 0, so the build is the same bytes every time) and base64-coded: no '<' in it."""
    return base64.b64encode(gzip.compress(data, 9, mtime=0)).decode("ascii")


@functools.lru_cache(maxsize=None)
def blob(name):
    """A vendored file, packed.  The worker is made a classic script, its code up to the closing `export{...}` inside a strict function:
    a page opened from disk (origin "null") cannot start a module worker from a blob: URL, and MapLibre's own way round that, a data:
    URL, is refused where only blob: workers are allowed; a classic blob: worker runs in both (measured in headless Chromium, 2026-11-19)."""
    if name == VENDORED["v-worker"]:
        data = ('(function(){"use strict";' + code_of(name)[0] + "})();\n").encode("utf-8")
    else:
        with open(os.path.join(VENDOR, name), "rb") as f:
            data = f.read()
    return packed(data)


def html(data):
    """The page: the template with the stylesheet, the script, the data, the shapes, the vendored library and its licence put in, each
    at its one mark, in one pass (nothing put in is read for marks).  The shapes (`geom`) are most of the page and go in packed, every
    ZIP and every integer of them: the map, which already unpacks its worker, reads them when it starts; the totals and tables do not."""
    read = lambda *name: open(os.path.join(HERE, *name), encoding="utf-8").read()
    dumps = lambda v: json.dumps(v, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    text = dumps({k: v for k, v in data.items() if k != "geom"})
    parts = {"CSS": read("dashboard.css"), "JS": read("dashboard.js"), "LICENCE": read(VENDOR, "LICENSE.txt"), "LIBRARY": library(),
             "GEOM": packed(dumps(data["geom"]).encode("ascii")),
             "DATA": text.replace("</", "<\\/").replace("<!--", "<\\u0021--"),                  # nothing in the data can close or confuse its <script>
             "VENDOR": "\n".join(f'<script type="text/plain" id="{i}">{blob(f)}</script>' for i, f in VENDORED.items())}
    page, marks = read("dashboard.html"), re.compile("<!--(" + "|".join(parts) + ")-->")
    if sorted(marks.findall(page)) != sorted(parts) or any("</script" in parts[k].lower() for k in ("CSS", "JS", "LICENCE", "LIBRARY")):
        raise SystemExit(f"dashboard.html needs each of the marks {sorted(parts)} once (has {sorted(marks.findall(page))}), and no part may hold </script")
    return marks.sub(lambda m: parts[m.group(1)], page)


def build(geo, runs, out_path, names=None, products_label="products not recorded", run_label="", sales=None, made_up=()):
    """Write the dashboard of `runs` to `out_path` and return the path.  The file holds `names` and `sales` when given: your screen only."""
    page = html(payload(geo, runs, names, products_label, run_label, sales, made_up)).encode("utf-8")
    with open(out_path, "wb") as f:
        f.write(page)
    if len(page) > MAX_BYTES:   # warn, never stop: a stopped build would lose the rest of the run (the folder line, the CSV list)
        print(f"WARNING {out_path}: the dashboard is {len(page) / 2 ** 20:.1f} MB, over the {MAX_BYTES / 2 ** 20:.0f} MB budget: too big to share easily")
    return out_path


# ---------------------------------------------------------------- dev: a run's CSVs and the public shapes, keys only

def read_dev(folder, without=()):
    """{scenario: {kind: (columns, rows)}} from a run folder's CSVs; a row's SCENARIO is the scenarios that share it.  The kinds in
    `without` are not read (a file left from another run)."""
    runs = {}
    for kind, name in KINDS.items():
        path = os.path.join(folder, name)
        if kind in without:
            continue
        if not os.path.exists(path):
            if kind in OPTIONAL:
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


REACH_M = 40_000   # made_up_today: a roster person's made-up territory reaches this far from the ZIPs they are known to cover


def made_up_today(geo, runs):
    """Dev only, for a run folder with no territory_today.csv: MADE-UP territories and cells in fetch_today's shape, put into `runs`
    as `today` and `cell_today`.  A roster person holds, in their firm's WH and FI (a WH person: WH only), the ZIPs gap_cell's HOLDERS
    name them on and every ZIP within REACH_M of those; elsewhere a firm's holder is a person off the roster (a key the seat files
    name, one per state and firm), and a few states have no one in one channel.  A cell's channel today is WH for the fine channels
    WH and Wells WH, else FI.  No real territory or channel is read: the page says "made-up"."""
    rows = lambda s, kind: [dict(zip((c.upper() for c in t[0]), r)) for r in t[1]] if (t := runs[s].get(kind)) else []
    person, zst, known = {}, {}, {}
    for s in runs:
        for r in rows(s, "person"):
            person.setdefault(r["HOLDER"], (str(r["SOURCE"]), str(r["ROLE"]).upper()))
    for s in runs:
        for r in rows(s, "cell"):
            if r["STATE"]:
                zst.setdefault(str(r["ZIP_CODE"]), str(r["STATE"]))
            for k in sorted(keysets(r["HOLDERS"]), key=keynum):
                if k in person and str(r["ZIP_CODE"]) in geo.zips:
                    for ch in (("WH",) if person[k][1] == "WH" else sm.TODAY_CH):
                        known.setdefault((person[k][0], ch, str(r["ZIP_CODE"])), k)
    off = sorted({r["HOLDER"] for s in runs for kind in ("seat", "plan") for r in rows(s, kind) if r.get("HOLDER")} - set(person), key=keynum) + [f"R{9001 + i}" for i in range(24)]      # and keys no run has
    codes, every = sorted(geo.states), sorted(geo.zips)
    pts = shapely.point_on_surface(np.array([geo.zips[z] for z in every], dtype=object))
    for z, i in zip(every, shapely.STRtree([geo.states[c] for c in codes]).nearest(pts)):
        zst.setdefault(z, codes[i])
    at = dict(zip(every, pts))
    hold, firms = {}, sorted({src for src, _ in person.values()})
    for n, f in enumerate(firms):
        mine_off = off[n::len(firms)] or off                    # the off-roster keys are dealt out to the firms
        for ch in sm.TODAY_CH:
            mine = sorted(z for (f2, c2, z) in known if (f2, c2) == (f, ch))
            near = dict(zip(*shapely.STRtree([at[z] for z in mine]).query_nearest(pts, max_distance=REACH_M, all_matches=False))) if mine else {}
            for i, z in enumerate(every):
                hold[f, ch, z] = (known[f, ch, mine[near[i]]] if i in near else None if zlib.crc32(f"{f}{ch}{zst[z]}".encode()) % 17 == 0
                                  else mine_off[zlib.crc32(f"{f}{zst[z]}".encode()) % len(mine_off)])
    for s in runs:
        roster = {r["HOLDER"]: str(r["ROLE"]).upper() for r in rows(s, "person")}
        runs[s]["today"] = (sm.TODAY_COLS, [(s, f, k, "Y" if k in roster else "N", roster.get(k, ""), z, zst[z], ch) for (f, ch, z), k in hold.items() if k])
        cells = collections.Counter()
        for r in rows(s, "cell"):
            cells[s, r["EST_SOURCE"], str(r["ZIP_CODE"]), str(r["STATE"] or ""), "WH" if str(r["NEW_DIST"]).upper() in ("WH", "WELLS WH") else "FI"] += float(r["MM_OPP"] or 0)
        runs[s]["cell_today"] = (sm.CELL_TODAY_COLS, [(*k, v) for k, v in cells.items()])
    return runs


def made_up_sales(runs, seed=153):
    """Dev only: MADE-UP sales [(seller key, ZIP, $)], the same for a seed: each holder of today's territories (the first scenario's)
    sells in about half of their ZIPs with opportunity and a few without, and in a few ZIPs that are not theirs; some sales are negative
    (returns) and a few have no key.  No real sale is read, here or anywhere an agent runs: the page says "made-up"."""
    rnd, first = random.Random(seed), next(iter(runs))
    usd, mine = collections.Counter(), collections.defaultdict(set)
    for r in runs[first]["cell"][1]:
        r = dict(zip((c.upper() for c in runs[first]["cell"][0]), r))
        usd[str(r["ZIP_CODE"])] += float(r["MM_OPP"] or 0) / 2
    for _, _, k, _, _, z, *_ in runs[first]["today"][1]:
        mine[k].add(z)
    market, out = sorted(usd), []
    for k in sorted(mine, key=keynum):
        for z in sorted(mine[k]):
            if rnd.random() < (0.55 if usd[z] else 0.03):
                out.append((k, z, round((0.03 * usd[z] or 20_000) * rnd.lognormvariate(0, 0.9) * (-0.2 if rnd.random() < 0.02 else 1))))
        for z in rnd.sample(market, min(len(market), len(mine[k]) // 40)):
            out.append((k, z, round(0.01 * usd[z] * rnd.lognormvariate(0, 0.9))))
    return out + [("", z, round(0.01 * usd[z])) for z in rnd.sample(market, min(len(market), 40))]


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
    ap.add_argument("--dev", required=True, metavar="FOLDER", help="a run folder's CSVs (keys only): gap_*.csv, and when it has them seat_fit.csv, seat_plan.csv, territory_today.csv, cell_today.csv")
    ap.add_argument("--out", required=True, help="the HTML to write (under data/safe: it is the run's data)")
    ap.add_argument("--public", default=os.path.join(os.environ.get("TD_REPO", sm.ROOT), "data", "public"), help="the folder of the TIGER/Line 2025 zips")
    ap.add_argument("--products", default="products not recorded", help="the run's product label, e.g. 'excluding FIXED'")
    ap.add_argument("--without", nargs="*", default=[], choices=["pair", "load", "seat", "plan"], metavar="KIND",
                    help="files of the folder not to read (left from another run): pair, load, seat, plan; the load is then worked out again from the cells")
    args = ap.parse_args(argv)
    geo = dev_geo(args.public, os.path.join(args.dev, "geo"))
    runs = read_dev(args.dev, args.without)
    made = []
    for s, run in runs.items():
        if "load" not in run:                                   # as the owner's run does it (scenario_maps.main)
            run["load"] = sm.gap_load(s, run, {st: g.area / 1e6 for st, g in geo.states.items()})
    if not all("today" in r and "cell_today" in r for r in runs.values()):
        made_up_today(geo, runs)
        made.append("today's territories")
    sales = made_up_sales(runs)                                 # an agent never sees a real sale
    made.append("2025 sales")
    path = build(geo, runs, args.out, None, args.products, os.path.basename(os.path.normpath(args.dev)), sales, made)
    print(f"{os.path.abspath(path)}: {os.path.getsize(path) / 2 ** 20:.1f} MB, keys only (no names); MADE-UP, not the run's: {', '.join(made)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
