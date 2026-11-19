"""Scenario maps (issue #147): one PDF per roster scenario, a CONUS page and the 9 census-division pages, each in three
views per channel.  Runs on the owner's terminal in ONE Snowflake login:

    .\\tools\\maps\\scenario_maps.ps1 -All          (or -Scenario CA1_R105N,CA2_R105N, or -List)

Per scenario: 03_assignments.sql with `SET scenario` set (and data/safe/03_edits.sql spliced into its owner block, as
run_03_04.ps1), then 04_assigned_coverage.sql, then it reads td_assignments and td_map_piece and draws
data/safe/maps/<run time>/<scenario>.pdf.  A scenario whose 03 result has a STATUS other than DEFAULT, EDITED or EDITED
(EITHER) is not drawn (its status counts are printed; the exit code is 1).  The PDFs hold names: they stay in data/safe.

Pages, per scenario, in the order geography (CONUS, then the divisions) x channel (NATIONAL, REGIONAL = role WIFI, WH) x view:
  A  whole states, each in its assigned person's colour (open seat hatched), the name on each state;
  B  the assigned states as a frame: the person's held in-role ZIPs solid, the rest of the assigned states in a light tint;
  C  today's in-role ZIPs of the kept holders with the role, one page per firm (CRBG, EQH); holders not kept hatched as open.
A ZIP belongs to a geography by its piece's STATE.
With tools/snowflake/07_overlap_gap.sql (issue #148) each scenario also runs it after 04, refuses its gap output when a MUST_BE_ZERO
row is not 0, and writes next to the PDF <scenario>_gap_cell.csv, _gap_pair.csv, _gap_person.csv, _gap_summary.csv (masked: holder
keys R<n> only, safe to send to an agent) and <scenario>_gaps.pdf (view D: a summary page, then geography x channel x estimate pages).  The shapes are read once (ST_SIMPLIFY in SQL), cached in data/safe/geo/
and drawn in EPSG:5070.  Pages are images (a vector page of 30,000 ZIPs runs to megabytes); scenarios draw in parallel.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import csv
import datetime
import gzip
import importlib.util
import io
import os
import re
import sys
import time
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")
import numpy as np
import shapely
import shapely.ops
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.collections import LineCollection, PatchCollection, PathCollection
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.patches import Patch, PathPatch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import look  # noqa: E402  (the shared look: palettes, colouring_far, place_labels, polygon_path)

SQL03 = os.path.join(ROOT, "tools", "snowflake", "03_assignments.sql")
SQL04 = os.path.join(ROOT, "tools", "snowflake", "04_assigned_coverage.sql")
SQL07 = os.path.join(ROOT, "tools", "snowflake", "07_overlap_gap.sql")
EDITS = os.path.join(ROOT, "data", "safe", "03_edits.sql")
GEO_DIR = os.path.join(ROOT, "data", "safe", "geo")
MAPS_DIR = os.path.join(ROOT, "data", "safe", "maps")
DB = "ssdb_integration.lr_strategy"
OK_STATUS = ("DEFAULT", "EDITED", "EDITED (EITHER)")
TOL_M = 250   # ST_SIMPLIFY tolerance (m): the notebook's 250 m look
DPI = 130
FIGSIZE = (20, 11.5)
AX = [0.005, 0.05, 0.74, 0.88]          # the map; the legend takes the right quarter
ROLE_OF = {"NATIONAL": "NATIONAL", "REGIONAL": "WIFI", "WH": "WH"}
TERR_OF = {"NATIONAL": ("WH", "FI"), "REGIONAL": ("WH", "FI"), "WH": ("WH",)}   # 04's in-role pieces
FIRMS = ("CRBG", "EQH")
VIEWS = [("A whole states", None), ("B held in assigned states", None)] + [(f"C today's territories {f}", f) for f in FIRMS]
LAND, OPEN_EDGE = "#f6f6f6", "#b8b8b8"
STATE_ABBR = {"01": "AL", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
              "13": "GA", "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
              "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV",
              "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH", "40": "OK", "41": "OR",
              "42": "PA", "44": "RI", "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA",
              "53": "WA", "54": "WV", "55": "WI", "56": "WY"}   # the CONUS states by FIPS; AK, HI, PR and the territories are not in it
GEO_TABLES = {"zcta": ("census_zip_codes_zcta", "RIGHT(geo_id, 5)"), "state": ("census_states", "RIGHT(geo_id, 2)"),
              "division": ("census_divisions", "geo_id || '|' || geo_name")}


# ---------------------------------------------------------------- the scenarios in 03

def list_scenarios(sql):
    """The scenario names of 03's key edits, in order of first appearance: the string in the `scenario` column of each
    VALUES tuple between `--key edits: begin` and `--key edits: end` (NULL is shared)."""
    block = re.search(r"--key edits: begin(.*?)--key edits: end", sql, re.S)
    if not block:
        raise SystemExit("03_assignments.sql has no `--key edits: begin` ... `--key edits: end` block")
    body = re.sub(r"--[^\n]*", "", block.group(1))
    names = []
    for ins in re.finditer(r"INSERT\s+INTO\s+\S+\s*\(([^)]*)\)\s*VALUES(.*?);", body, re.S | re.I):
        cols = [c.strip().lower() for c in ins.group(1).split(",")]
        if "scenario" not in cols:
            continue
        i = cols.index("scenario")
        for tup in re.finditer(r"\(((?:'[^']*'|[^()'])*)\)", ins.group(2)):
            vals = [v.strip() for v in re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", tup.group(1))]
            if len(vals) != len(cols):
                raise SystemExit(f"03 key edit {tup.group(0)!r}: {len(vals)} values for {len(cols)} columns")
            if vals[i].upper() != "NULL" and vals[i].strip("'") not in names:
                names.append(vals[i].strip("'"))
    return names


SET_RE = re.compile(r"(?im)^(\s*SET\s+scenario\s*=\s*)'[^']*'\s*;")
EDITS_RE = re.compile(r"(?s)(--owner edits: begin\r?\n).*?(--owner edits: end)")


def scenario_sql(sql03, scenario, edits=None):
    """03 with `SET scenario = '<scenario>';` and, when `edits` is given, data/safe/03_edits.sql between the owner markers."""
    if not re.fullmatch(r"\w+", scenario):
        raise SystemExit(f"scenario {scenario!r}: letters, digits and _ only")
    sql, n = SET_RE.subn(lambda m: f"{m.group(1)}'{scenario}';", sql03)
    if n != 1:
        raise SystemExit(f"03_assignments.sql has {n} lines `SET scenario = '';` (needs exactly 1): phase 1 of issue #147 is not in this checkout")
    if edits is not None:
        if re.search(r"[^\x00-\x7F]", edits):
            raise SystemExit("03_edits.sql has a non-ASCII character (an accent?): type the name as the data has it in plain ASCII")
        if not EDITS_RE.search(sql):
            raise SystemExit("03_assignments.sql has no owner edits block")
        sql = EDITS_RE.sub(lambda m: m.group(1) + edits.rstrip() + "\n" + m.group(2), sql, count=1)
    return sql


# ---------------------------------------------------------------- Snowflake (one connection; nothing here runs in the tests)

def run_sql_module():
    spec = importlib.util.spec_from_file_location("run_sql", os.path.join(ROOT, "tools", "snowflake", "run_sql.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def connect():
    import snowflake.connector
    return snowflake.connector.connect(connection_name="default", client_session_keep_alive=True)


def run_sql(conn, sql, split):
    """Every statement of `sql` in the session; the last result as (columns, rows) or None."""
    last = None
    for cur in conn.execute_stream(io.StringIO(run_sql_module().statements(sql, split))):
        if cur.description:
            last = ([d[0] for d in cur.description], cur.fetchall())
    return last


def query(conn, sql):
    cur = conn.cursor()
    try:
        cur.execute(sql)
        return cur.fetchall()
    finally:
        cur.close()


def fetch_scenario(conn, scenario, sql03, sql04, edits, split):
    """(roster, pieces) after 03 and 04 for `scenario`, or None when 03 reports a status outside OK_STATUS."""
    last = run_sql(conn, scenario_sql(sql03, scenario, edits), split)
    status = collections.Counter(r[0] for r in last[1]) if last else collections.Counter()
    if not last or set(status) - set(OK_STATUS):
        print(f"{scenario}: NOT DRAWN, 03's STATUS counts {dict(status) or 'none (no result)'}; fix the edits, nothing is drawn for it")
        return None
    r04 = run_sql(conn, sql04, split)
    bad = [] if r04 is None else [r for r in r04[1] if dict(zip(r04[0], r))["MUST_BE_ZERO"] == 1 and dict(zip(r04[0], r))["N"] not in (0, None)]
    if r04 is None or bad:
        print(f"{scenario}: NOT DRAWN, 04's must-be-zero checks not 0: "
              + ("no result" if r04 is None else "; ".join(f"{dict(zip(r04[0], r))['K1']} = {dict(zip(r04[0], r))['N']}" for r in bad)))
        return None
    roster = query(conn, f"SELECT source, wholesaler, kept, role, assigned_states FROM {DB}.td_assignments")
    pieces = query(conn, f"SELECT source, wholesaler, kept, role, zip_code, state, terr_channel, piece_in_role FROM {DB}.td_map_piece")
    return roster, pieces


def query_cols(conn, sql):
    """(columns, rows) of a query."""
    cur = conn.cursor()
    try:
        cur.execute(sql)
        return [d[0].upper() for d in cur.description], cur.fetchall()
    finally:
        cur.close()


def gap_failures(result):
    """The ITEMs of the 07 result's MUST_BE_ZERO = 1 rows whose N_ZIPS or MM_OPP is not 0 (within 0.5; NULL is 0)."""
    cols, rows = result
    out = []
    for r in (dict(zip(cols, x)) for x in rows):
        if r["MUST_BE_ZERO"] == 1 and any(abs(float(r[c] or 0)) > 0.5 for c in ("N_ZIPS", "MM_OPP")):
            out.append(f"{r['ITEM']} (N_ZIPS {r['N_ZIPS']}, MM_OPP {r['MM_OPP']})")
    return out


def fetch_gap(conn, scenario, sql07, split):
    """Run 07 for `scenario` (right after 04, in the same session) and read its tables: {summary, cell, pair, person}
    as (columns, rows) and names {key: name}; None when 07's MUST_BE_ZERO rows are not 0 (the failing ITEMs are printed)."""
    res = run_sql(conn, scenario_sql(sql07, scenario), split)
    bad = ["07 gave no result"] if res is None else gap_failures(res)
    if bad:
        print(f"{scenario}: GAP OUTPUT NOT WRITTEN, 07's must-be-zero checks not 0: " + "; ".join(bad))
        return None
    got = {"summary": res}
    for k in ("cell", "pair", "person"):
        got[k] = query_cols(conn, f"SELECT * FROM {DB}.td_gap_{k} WHERE scenario = '{scenario}'")
    # key -> name, on this machine only: td_holder_key's id is the UUID of the normalized name (02, 03)
    got["names"] = dict(query(conn, f"SELECT 'R' || k.holder_n, a.wholesaler FROM {DB}.td_assignments a JOIN {DB}.td_holder_key k "
                                    "ON k.source = a.source AND k.holder_id = UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', "
                                    r"NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(a.wholesaler), '\\s+', ' '))), ''))"))
    return got


def write_gap_csvs(out, scenario, gap):
    """<scenario>_gap_<cell|pair|person|summary>.csv in `out`: the paths."""
    paths = []
    for k in ("cell", "pair", "person", "summary"):
        path = os.path.join(out, f"{scenario}_gap_{k}.csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(gap[k][0])
            w.writerows(gap[k][1])
        paths.append(path)
    return paths


# ---------------------------------------------------------------- shapes

def wkb_bytes(x):
    return bytes.fromhex(x) if isinstance(x, str) else bytes(x)


def project(geoms):
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", look.CRS, always_xy=True)
    return shapely.transform(np.array(geoms, dtype=object), lambda c: np.column_stack(tr.transform(c[:, 0], c[:, 1])))


def load_table(conn, kind, cache_dir=GEO_DIR, tol=TOL_M):
    """{key: geometry in EPSG:5070} of a census table, simplified by `tol` m in SQL; cached by table and tolerance."""
    table, key = GEO_TABLES[kind]
    path = os.path.join(cache_dir, f"{table}_{tol:g}m_5070.tsv.gz")
    if not os.path.exists(path):
        print(f"reading {table} from Snowflake (once; cached in {path})", flush=True)
        query(conn, "ALTER SESSION SET GEOGRAPHY_OUTPUT_FORMAT='WKB'")
        # preserve_collapsed TRUE: by default a small polygon simplified away comes back NULL; the shape as is if it still does
        rows = query(conn, f"SELECT {key}, ST_ASWKB(COALESCE(ST_SIMPLIFY(geo_boundary, {tol}, TRUE), geo_boundary)) FROM {DB}.{table}")
        empty = [r[0] for r in rows if r[1] is None]
        if empty:
            print(f"{table}: {len(empty)} rows have no boundary, left out: {', '.join(map(str, empty[:20]))}"
                  + (" ..." if len(empty) > 20 else ""), flush=True)
        rows = [r for r in rows if r[1] is not None]
        keys = [r[0] for r in rows]
        geoms = shapely.from_wkb([wkb_bytes(r[1]) for r in rows])
        geoms = project(geoms)
        os.makedirs(cache_dir, exist_ok=True)
        with gzip.open(path + ".tmp", "wt", encoding="ascii") as f:
            for k, g in zip(keys, shapely.to_wkb(geoms, hex=True)):
                f.write(f"{k}\t{g}\n")
        os.replace(path + ".tmp", path)
    with gzip.open(path, "rt", encoding="utf-8") as f:
        pairs = [line.rstrip("\n").split("\t") for line in f]
    geoms = shapely.from_wkb([p[1] for p in pairs])
    bad = ~shapely.is_valid(geoms)
    geoms[bad] = shapely.buffer(geoms[bad], 0)
    return dict(zip((p[0] for p in pairs), geoms))


def assign_divisions(states, divs):
    """[(name, [states])] in division order: a state belongs to the division nearest its representative point (inside it)."""
    names = sorted(divs, key=lambda k: int(k.split("|")[0]))
    out = {k: [] for k in names}
    for s, g in sorted(states.items()):
        p = shapely.point_on_surface(g)
        out[min(names, key=lambda k: shapely.distance(p, divs[k]))].append(s)
    empty = [k for k in names if not out[k]]
    if empty or len(names) != 9:
        raise SystemExit(f"census_divisions: {len(names)} divisions, {empty} with no CONUS state; expected 9, each with states")
    return [(k.split("|", 1)[1], out[k]) for k in names]


def load_geo(conn, cache_dir=GEO_DIR):
    """SimpleNamespace(states, zips, divisions): CONUS only, EPSG:5070."""
    st = {STATE_ABBR[k]: g for k, g in load_table(conn, "state", cache_dir).items() if k in STATE_ABBR}
    zs = load_table(conn, "zcta", cache_dir)
    land = shapely.union_all(list(st.values())).buffer(5000)
    shapely.prepare(land)
    keys = list(zs)
    inside = shapely.intersects(land, shapely.point_on_surface(np.array([zs[k] for k in keys], dtype=object)))
    return make_geo(st, {k: zs[k] for k, i in zip(keys, inside) if i}, assign_divisions(st, load_table(conn, "division", cache_dir)))


def make_geo(states, zips, divisions):
    """The shapes with what every page needs: each state's label point and bounds, the geographies and their boxes."""
    geo = SimpleNamespace(states=states, zips=zips, divisions=divisions, path_cache={}, pt_cache={})
    geo.bounds = {s: g.bounds for s, g in states.items()}
    geo.geographies = []
    for name, codes in [("CONUS", sorted(states))] + list(divisions):
        x0, y0, x1, y1 = shapely.total_bounds([states[s] for s in codes])
        pad = (0.01 if name == "CONUS" else 0.04) * max(x1 - x0, y1 - y0)
        geo.geographies.append(SimpleNamespace(name=name, states=set(codes), box=fit((x0 - pad, y0 - pad, x1 + pad, y1 + pad))))
    geo.state_pt = {s: label_point(geo, g) for s, g in states.items()}
    geo.segs = {s: [np.asarray(r.coords)[:, :2] for r in shapely.get_rings(shapely.get_parts(g))] for s, g in states.items()}
    return geo


def fit(box, ratio=AX[2] * FIGSIZE[0] / (AX[3] * FIGSIZE[1])):
    """`box` widened (about its centre) to the width / height `ratio` of the map axes."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if w / h < ratio:
        x0, x1 = (x0 + x1) / 2 - h * ratio / 2, (x0 + x1) / 2 + h * ratio / 2
    else:
        y0, y1 = (y0 + y1) / 2 - w / ratio / 2, (y0 + y1) / 2 + w / ratio / 2
    return x0, y0, x1, y1


def label_point(geo, g):
    """The pole of inaccessibility of `g`'s largest polygon (cached on the geometry)."""
    k = id(g)
    if k not in geo.pt_cache:
        part = max(shapely.get_parts(g), key=lambda p: p.area)
        geo.pt_cache[k] = shapely.ops.polylabel(part, tolerance=3000) if part.geom_type == "Polygon" else part.representative_point()
    return geo.pt_cache[k]


# ---------------------------------------------------------------- the scenario's people and areas

def prepare(roster, pieces, geo):
    """ctx: the kept people with a role, each one's held in-role area by state, the open (not kept) area by firm, channel
    and state, one colour per person (colouring_far over their union shapes, so it holds on every page)."""
    geo.pt_cache.clear()  # keyed by id(): a geometry of the previous scenario may be gone and its id reused
    geo.path_cache.clear()
    people = {}
    for src, name, kept, role, states in roster:
        src, role = (src or "").upper(), (role or "").upper()
        if str(kept or "").upper() == "Y" and role in ROLE_OF.values():
            people[(src, name)] = SimpleNamespace(key=(src, name), source=src, name=name, role=role,
                                                  states=sorted(set(str(states or "").replace(",", " ").upper().split()) & set(geo.states)),
                                                  all_states=str(states or "").upper())
    held, opened = collections.defaultdict(set), collections.defaultdict(set)
    no_shape = set()
    for src, name, kept, role, z, st, tc, inrole in pieces:
        src, st, tc = (src or "").upper(), (st or "").upper(), (tc or "").upper()
        if st not in geo.states:
            continue                                            # not CONUS: not drawn by design
        if z not in geo.zips:
            no_shape.add(z)                                     # a CONUS ZIP that is no ZCTA: reported, not drawn
            continue
        if src not in FIRMS:
            raise SystemExit(f"td_map_piece has source {src!r}; the pages draw {FIRMS}")
        if str(kept or "").upper() == "Y":
            if inrole and (src, name) in people:
                held[(src, name), st].add(z)
        else:
            opened[(src, tc), st].add(z)
    union = lambda d: {k: shapely.union_all([geo.zips[z] for z in v]) for k, v in d.items()}
    ctx = SimpleNamespace(geo=geo, people=sorted(people.values(), key=lambda p: (p.name.upper(), p.source, p.name)),
                          held=collections.defaultdict(dict), opened=collections.defaultdict(dict), no_shape=len(no_shape))
    for (key, st), g in union(held).items():
        ctx.held[key][st] = g
    for (key, st), g in union(opened).items():
        ctx.opened[key][st] = g
    shape = {p.key: shapely.union_all(list(ctx.held[p.key].values()) + [geo.states[s] for s in p.states]).simplify(3000)
             for p in ctx.people}
    ctx.colour = look.colouring_far(shape, look.neighbours(shape), look.CLEAN_PALETTE) if shape else {}
    return ctx


# ---------------------------------------------------------------- drawing

def path_of(geo, g):
    k = id(g)
    if k not in geo.path_cache:
        geo.path_cache[k] = look.polygon_path(g)
    return geo.path_cache[k]


def layer(ax, geo, geoms, colours=None, gid=None, **kw):
    geoms = [g for g in geoms if g is not None and not g.is_empty]
    if not geoms:
        return
    col = PatchCollection([PathPatch(path_of(geo, g)) for g in geoms], **({"facecolors": colours} if colours else {}), **kw)
    col.set_gid(gid)
    ax.add_collection(col)


def biggest(geo, geoms):
    """The label point of the largest of `geoms`, or None."""
    geoms = [g for g in geoms if g is not None and not g.is_empty]
    return label_point(geo, max(geoms, key=lambda g: g.area)) if geoms else None


CAPTION = {"A": "Each state in its assigned person's colour (one colour per person in this scenario); hatched: open seat, no one assigned.",
           "B": "Solid: the person's held in-role ZIPs inside their assigned states.  Tint: assigned, not held today.  Hatched: open seat.",
           "C": "Today's in-role territories of the kept holders with the role, one colour per person; hatched: ZIPs of holders not kept (open)."}


def base_page(geo, g):
    """(figure, axes, the states in view) with the land drawn."""
    fig = Figure(figsize=FIGSIZE, dpi=DPI, facecolor="white")
    FigureCanvasAgg(fig)
    ax = fig.add_axes(AX)
    x0, y0, x1, y1 = g.box
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.axis("off")
    vis = [s for s, b in geo.bounds.items() if b[2] >= x0 and b[0] <= x1 and b[3] >= y0 and b[1] <= y1]
    layer(ax, geo, [geo.states[s] for s in vis], facecolor=LAND, edgecolor="none", zorder=0)
    return fig, ax, vis


def state_lines_and_labels(ax, geo, vis, items):
    """The dashed state lines, then the names at their points (x, y, name): placed, and a crowded-out one set anyway."""
    segs = [r for s in vis for r in geo.segs[s]]
    ax.add_collection(LineCollection(segs, colors="#606060", linewidths=0.5, linestyle=(0, (4, 2)), zorder=3))
    placed = look.place_labels(ax, items, fs=7, marker=False, near=[(0, 0, "center", "center")], color="#111111", fontweight="bold")
    left = collections.Counter(s for _, _, s in items) - collections.Counter(x.get_text() for x in placed)
    for x, y, s in items:                                       # crowded out: set at its point anyway, a name is never dropped
        if left[s] > 0:
            left[s] -= 1
            ax.text(x, y, s, fontsize=7, color="#111111", fontweight="bold", ha="center", va="center", zorder=6)


def draw_page(ctx, title, g, ch, view, firm):
    """One figure.  view[0] is A, B or C; `firm` is C's firm."""
    geo = ctx.geo
    fig, ax, vis = base_page(geo, g)
    people = [p for p in ctx.people if p.role == ROLE_OF[ch]]
    owners = collections.defaultdict(list)
    for p in people:
        for s in p.states:
            if s in g.states:
                owners[s].append(p)
    items, shown = [], []                                # label points (x, y, name), the people on the page
    v = view[0]
    if v in "AB":
        shown = [p for p in people if any(s in g.states for s in p.states)]
        open_ = [geo.states[s] for s in sorted(g.states) if s not in owners]
        layer(ax, geo, open_, facecolor=LAND, edgecolor=OPEN_EDGE, hatch="////", linewidth=0, zorder=1, gid="open")
        alpha = 0.75 if v == "A" else 0.28
        ss = [s for s in sorted(owners)]
        layer(ax, geo, [geo.states[s] for s in ss], [to_rgba(ctx.colour[owners[s][0].key], alpha) for s in ss], edgecolor="none", zorder=1)
        if v == "A":
            items = [(*geo.state_pt[s].coords[0], " / ".join(p.name for p in owners[s])) for s in ss]
        else:
            for p in shown:
                mine = [s for s in p.states if s in g.states]
                parts = [ctx.held[p.key][s] for s in mine if s in ctx.held[p.key]]
                layer(ax, geo, parts, facecolor=to_rgba(ctx.colour[p.key], 0.85), edgecolor=to_rgba(ctx.colour[p.key], 0.85),
                      linewidth=0.3, zorder=2)
                pt = biggest(geo, parts) or biggest(geo, [geo.states[s] for s in mine])
                items.append((pt.x, pt.y, p.name))
    else:
        for tc in TERR_OF[ch]:
            layer(ax, geo, [ctx.opened[firm, tc].get(s) for s in sorted(g.states)], facecolor=LAND, edgecolor=OPEN_EDGE,
                  hatch="////", linewidth=0, zorder=1, gid="open")
        for p in people:
            if p.source != firm:
                continue
            parts = [ctx.held[p.key][s] for s in sorted(g.states) if s in ctx.held[p.key]]
            if parts:
                shown.append(p)
                layer(ax, geo, parts, facecolor=to_rgba(ctx.colour[p.key], 0.75), edgecolor=to_rgba(ctx.colour[p.key], 0.75),
                      linewidth=0.3, zorder=2)
                pt = biggest(geo, parts)
                items.append((pt.x, pt.y, p.name))
    state_lines_and_labels(ax, geo, vis, items)
    n = len(shown)
    handles = [Patch(facecolor=ctx.colour[p.key], alpha=0.75, edgecolor="#202020",
                     label=(f"{p.name}\n" if n <= 20 else f"{p.name}  ") + f"{p.role} · {p.all_states or 'no states assigned'}") for p in shown]
    if v == "B":
        handles += [Patch(facecolor="#808080", alpha=0.85, label="held today, in role"), Patch(facecolor="#808080", alpha=0.28, label="assigned, not held today")]
    handles.append(Patch(facecolor=LAND, edgecolor=OPEN_EDGE, hatch="////", label="open (holder not kept)" if v == "C" else "open seat (no one assigned)"))
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.752, 0.95), fontsize=6.6 if n <= 20 else 5.8, frameon=False,
               handlelength=1.2, borderaxespad=0, labelspacing=0.55 if n <= 20 else 0.3)
    fig.suptitle(title, fontsize=17, fontweight="bold", y=0.975)
    fig.text(0.01, 0.015, CAPTION[v] + "  Dashed: state lines.", fontsize=9, color="#404040")
    return fig


def specs(geo):
    """Every page as (geography, channel, view, firm), in order: geography, channel, view."""
    return [(g, ch, view, firm) for g in geo.geographies for ch in ROLE_OF for view, firm in VIEWS]


def pages(scenario, ctx, lo=0, hi=None):
    """(title, figure) for the pages lo..hi (all by default), in order."""
    for g, ch, view, firm in specs(ctx.geo)[lo:hi]:
        title = f"{scenario} · {view} · {ch} · {g.name}"
        yield title, draw_page(ctx, title, g, ch, view, firm)


def write_pdf(path, figs, inspect=None):
    """The pages as pictures, one at a time; `inspect(title, fig)` sees each figure before it is rasterised."""
    n = 0
    with PdfPages(path) as pdf:
        for title, fig in figs:
            if inspect:
                inspect(title, fig)
            fig.canvas.draw()
            pic = Figure(figsize=fig.get_size_inches(), dpi=DPI)
            axis = pic.add_axes([0, 0, 1, 1])
            axis.imshow(np.asarray(fig.canvas.buffer_rgba())[:, :, :3], interpolation="none", aspect="auto")
            axis.set_axis_off()
            pdf.savefig(pic, dpi=DPI)
            n += 1
    if n == 0:
        raise RuntimeError(f"{path}: no page to draw")
    return n


# ---------------------------------------------------------------- view D: overlaps and gaps (issue #148)

# class, colour, hatch edge colour (None: solid), hatch; the order breaks ties for the class of a ZIP
GAP_CLASSES = [("COVERED", "#b9e6b0", None, None), ("OVERLAP", "#e8541f", None, None), ("HELD BY ANOTHER", "#8e5bb5", None, None),
               ("GAP", "#f2c200", None, None), ("OPEN SEAT HELD", "#c4c4c4", "#6a6a6a", "////"),
               ("OPEN SEAT UNHELD", "#efefef", "#a8a8a8", "////"), ("DOUBLE ASSIGNED", "#000000", None, None)]
GAP_CH = ("NATIONAL", "REGIONAL", "WH")           # the channels with a page; OPEN (no one assigned) is in the summary table only
GAP_ALL_CH = GAP_CH + ("OPEN",)
GAP_CAPTION = ("A ZIP has the class of its cells in this channel with the most $MM of opportunity (MM_OPP); a ZIP with no cell in the channel is blank.  "
               "Names: the person(s) assigned to the state in this channel.  Legend: ZIPs and the $MM of their cells in this channel, on this page.")


def gap_prepare(cell, pair, names):
    """What the pages need, from the TD_GAP_CELL and TD_GAP_PAIR results ((columns, rows)) and names {key: name}: ests,
    zips {(est, channel): {zip: (state, class, $MM)}} (class = the ZIP's cells' class with most MM_OPP), assigned {(channel, state):
    names}, table {(est, channel, class): $MM} over every cell, pairs {est: the top 15 by $MM as (channel, A, B, n, $MM)}."""
    order = [c for c, *_ in GAP_CLASSES]
    by_zip, assigned, table = {}, {}, {}
    for r in (dict(zip(cell[0], x)) for x in cell[1]):
        est, ch, cls, mm = r["EST_SOURCE"], r["CHANNEL"], r["CLASS"], float(r["MM_OPP"] or 0)
        if cls not in order or ch not in GAP_ALL_CH:
            raise SystemExit(f"TD_GAP_CELL has CLASS {cls!r}, CHANNEL {ch!r}; the pages know {order} and {GAP_ALL_CH}")
        table[est, ch, cls] = table.get((est, ch, cls), 0.0) + mm
        keys = str(r["ASSIGNED"] or "").replace(",", " ").split()
        if keys and ch in GAP_CH:
            assigned.setdefault((ch, str(r["STATE"]).upper()), set()).update(keys)
        z = by_zip.setdefault((est, ch), {}).setdefault(str(r["ZIP_CODE"]), [str(r["STATE"]).upper(), {}])
        z[1][cls] = z[1].get(cls, 0.0) + mm
    zips = {k: {z: (st, max(order, key=lambda c: d.get(c, -1.0)), sum(d.values())) for z, (st, d) in v.items()} for k, v in by_zip.items()}
    who = lambda k: f"{k} {names[k]}" if k in names else k
    pairs = {}
    for r in (dict(zip(pair[0], x)) for x in pair[1]):
        pairs.setdefault(r["EST_SOURCE"], []).append((r["CHANNEL"], who(r["HOLDER_A"]), who(r["HOLDER_B"]), r["N_ZIPS"] or 0, float(r["MM_OPP"] or 0)))
    return SimpleNamespace(ests=sorted({e for e, _, _ in table}), zips=zips, table=table,
                           assigned={k: " / ".join(sorted(names.get(x, x) for x in v)) for k, v in assigned.items()},
                           pairs={e: sorted(v, key=lambda t: -t[4])[:15] for e, v in pairs.items()})


def gap_specs(geo, gd):
    """The gap pages after the summary as (geography, channel, estimate): geography, channel, estimate."""
    return [(g, ch, est) for g in geo.geographies for ch in GAP_CH for est in gd.ests]


def draw_gap_page(gd, geo, title, g, ch, est):
    fig, ax, vis = base_page(geo, g)
    by, mm = collections.defaultdict(list), collections.Counter()
    for z, (st, cls, m) in gd.zips.get((est, ch), {}).items():
        if st in g.states and z in geo.zips:
            by[cls].append(z)
            mm[cls] += m
    handles = []
    for cls, col, edge, hatch in GAP_CLASSES:
        paths = [path_of(geo, geo.zips[z]) for z in by[cls]]
        if paths:
            c = PathCollection(paths, facecolor=col, edgecolor=edge or col, linewidth=0 if hatch else 0.1, hatch=hatch, zorder=1)
            c.set_gid(cls)
            ax.add_collection(c)
        handles.append(Patch(facecolor=col, edgecolor=edge or "#202020", hatch=hatch, label=f"{cls}\n{len(by[cls]):,} ZIPs · ${mm[cls]:,.1f} MM"))
    items = [(*geo.state_pt[s].coords[0], gd.assigned[ch, s]) for s in sorted(g.states) if (ch, s) in gd.assigned]
    state_lines_and_labels(ax, geo, vis, items)
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.752, 0.95), fontsize=9, frameon=False, handlelength=1.4,
               borderaxespad=0, labelspacing=0.9, title=f"{ch} · {est} estimate · {g.name}", title_fontsize=9, alignment="left")
    fig.suptitle(title, fontsize=17, fontweight="bold", y=0.975)
    fig.text(0.01, 0.015, GAP_CAPTION, fontsize=8.5, color="#404040")
    return fig


def draw_gap_summary(scenario, gd):
    """The first page: $MM by channel x class per estimate, then each estimate's top 15 overlap pairs."""
    fig = Figure(figsize=FIGSIZE, dpi=DPI, facecolor="white")
    FigureCanvasAgg(fig)
    lines = []
    for est in gd.ests:
        lines += [f"{est} estimate: $MM of opportunity by channel and class (every cell)", f"{'':10}" + "".join(f"{c:>18}" for c, *_ in GAP_CLASSES)]
        lines += [f"{ch:10}" + "".join(f"{gd.table.get((est, ch, c), 0.0):>18,.1f}" for c, *_ in GAP_CLASSES) for ch in GAP_ALL_CH]
        lines += ["", f"{est} estimate: top 15 overlap pairs by $MM", f"{'channel':10}{'holder A':<34}{'holder B':<34}{'ZIPs':>8}{'$MM':>12}"]
        lines += [f"{ch:10}{a[:32]:<34}{b[:32]:<34}{n:>8,}{mm:>12,.1f}" for ch, a, b, n, mm in gd.pairs.get(est, [])] + [""]
    fig.suptitle(f"{scenario} · D overlaps and gaps · summary", fontsize=17, fontweight="bold", y=0.975)
    fig.text(0.02, 0.93, "\n".join(lines), family="monospace", fontsize=min(9.0, 560 / (1.3 * len(lines))), va="top")
    return fig


def gap_pages(scenario, gd, geo, lo=0, hi=None):
    """(title, figure) for the gap pages lo..hi: page 0 is the summary, then geography x channel x estimate."""
    allp = [None] + gap_specs(geo, gd)
    for spec in allp[lo:hi]:
        if spec is None:
            title = f"{scenario} · D overlaps and gaps · summary"
            yield title, draw_gap_summary(scenario, gd)
        else:
            g, ch, est = spec
            title = f"{scenario} · D overlaps and gaps · {ch} · {est} estimate · {g.name}"
            yield title, draw_gap_page(gd, geo, title, g, ch, est)


# ---------------------------------------------------------------- the run

_GEO = None


def _init(geo):
    global _GEO
    _GEO = geo


CHUNK = 10    # pages per task: a scenario's 120 pages spread over every worker
_CTX = {}


def draw_chunk(scenario, roster, pieces, lo, hi):
    """Pages lo..hi of `scenario` as PNG bytes, with the count of CONUS ZIPs that have no shape.  A worker builds a
    scenario's areas (prepare) once and keeps only the last scenario's."""
    if scenario not in _CTX:
        _CTX.clear()
        _CTX[scenario] = prepare(roster, pieces, _GEO)
    ctx, out = _CTX[scenario], []
    for _, fig in pages(scenario, ctx, lo, hi):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=DPI, facecolor="white")
        out.append(buf.getvalue())
    return lo, out, ctx.no_shape


def draw_gap_chunk(scenario, gd, lo, hi):
    """Gap pages lo..hi of `scenario` as PNG bytes: (lo, pngs)."""
    out = []
    for _, fig in gap_pages(scenario, gd, _GEO, lo, hi):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=DPI, facecolor="white")
        out.append(buf.getvalue())
    return lo, out


def assemble(path, pngs):
    """The PDF of the pages (PNG bytes, in order), each a picture."""
    import matplotlib.image
    with PdfPages(path) as pdf:
        for png in pngs:
            pic = Figure(figsize=FIGSIZE, dpi=DPI)
            axis = pic.add_axes([0, 0, 1, 1])
            axis.imshow(matplotlib.image.imread(io.BytesIO(png), format="png"), interpolation="none", aspect="auto")
            axis.set_axis_off()
            pdf.savefig(pic, dpi=DPI)
    if not pngs:
        raise RuntimeError(f"{path}: no page to draw")
    return len(pngs)


def _done(x):
    f = concurrent.futures.Future()
    f.set_result(x)
    return f


def chunks(n, size=CHUNK):
    return [(lo, min(lo + size, n)) for lo in range(0, n, size)]


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true", help="print the scenario names in 03_assignments.sql")
    ap.add_argument("--scenario", action="append", default=[], help="a scenario to draw (repeatable)")
    ap.add_argument("--all", action="store_true", help="draw every scenario")
    ap.add_argument("--jobs", type=int, help="drawing processes (default: the CPUs less one, at most 8); 1 draws in this process")
    args = ap.parse_args(argv)
    with open(SQL03, encoding="utf-8") as f:
        sql03 = f.read()
    names = list_scenarios(sql03)
    if args.list:
        print("\n".join(names))
        return 0
    if args.all == bool(args.scenario):
        ap.error("name --scenario NAME (repeatable) or --all, or --list")
    chosen = names if args.all else [s for a in args.scenario for s in a.split(",") if s]
    if not names:
        ap.error("03_assignments.sql lists no scenario (no scenario column in its key edits)")
    if set(chosen) - set(names):
        ap.error(f"unknown scenario {sorted(set(chosen) - set(names))}; 03 has {names}")
    with open(SQL04, encoding="utf-8") as f:
        sql04 = f.read()
    sql07 = None
    if os.path.exists(SQL07):
        with open(SQL07, encoding="utf-8") as f:
            sql07 = f.read()
    else:
        print("07_overlap_gap.sql is not in this checkout: no overlap and gap output")
    edits = None
    if os.path.exists(EDITS):
        with open(EDITS, encoding="utf-8") as f:
            edits = f.read()
        print("03: edits from data/safe/03_edits.sql")
    else:
        print("03: no data/safe/03_edits.sql, so the scenario's key edits only")
    from snowflake.connector.util_text import split_statements
    out = os.path.join(MAPS_DIR, datetime.datetime.now().strftime("%Y-%m-%d-%H%M"))
    os.makedirs(out, exist_ok=True)
    jobs = args.jobs or max(1, min((os.cpu_count() or 2) - 1, 8))   # ponytail: 8 at most, each worker holds the shapes
    t0, refused, futs, pool, n_pages, started, gaps = time.time(), [], {}, None, None, {}, {}
    with connect() as conn:
        for name in chosen:
            got = fetch_scenario(conn, name, sql03, sql04, edits, split_statements)
            print(f"{name}: 03 and 04 done at {time.time() - t0:.0f} s; drawing", flush=True)
            if got is None:
                refused.append(name)
                continue
            gap = fetch_gap(conn, name, sql07, split_statements) if sql07 else None   # right after 04: 07 reads its temp tables
            if sql07 and gap is None:
                refused.append(name + " (gap output only)")
            if n_pages is None:
                geo = load_geo(conn)
                n_pages = len(specs(geo))
                _init(geo)
                if jobs > 1:
                    pool = concurrent.futures.ProcessPoolExecutor(jobs, initializer=_init, initargs=(geo,))
            submit = (lambda fn, *a: pool.submit(fn, *a)) if pool else (lambda fn, *a: _done(fn(*a)))
            started[name] = time.time()
            for lo, hi in chunks(n_pages):
                futs[name, lo] = submit(draw_chunk, name, got[0], got[1], lo, hi)
            if gap:
                for p in write_gap_csvs(out, name, gap):
                    print(os.path.relpath(p, ROOT))
                print(f"{name}: the _gap_*.csv files hold holder keys R<n> and counts only: safe to send to an agent")
                gd = gap_prepare(gap["cell"], gap["pair"], gap["names"])
                skipped = len({z for z_ in gd.zips.values() for z, (st, _, _) in z_.items() if st in geo.states and z not in geo.zips})
                gaps[name] = (gd, skipped, time.time())
                for lo, hi in chunks(1 + len(gap_specs(geo, gd))):
                    futs[name + "_gaps", lo] = submit(draw_gap_chunk, name, gd, lo, hi)
    for name in [s for s in chosen if s in started]:
        parts = sorted(futs[k].result() for k in futs if k[0] == name)
        path = os.path.join(out, f"{name}.pdf")
        n = assemble(path, [png for _, pngs, _ in parts for png in pngs])
        print(f"{os.path.relpath(path, ROOT)}: {n} pages, drawn in {time.time() - started[name]:.0f} s; "
              f"{parts[0][2]} CONUS ZIPs in td_map_piece have no ZCTA shape, not drawn", flush=True)
    for name, (gd, skipped, t) in gaps.items():
        path = os.path.join(out, f"{name}_gaps.pdf")
        n = assemble(path, [png for _, pngs in sorted(futs[k].result() for k in futs if k[0] == name + "_gaps") for png in pngs])
        print(f"{os.path.relpath(path, ROOT)}: {n} pages, drawn in {time.time() - t:.0f} s; {skipped} CONUS ZIPs of the gap cells have no ZCTA shape, not drawn", flush=True)
    if pool:
        pool.shutdown()
    print(f"done in {time.time() - t0:.0f} s" + (f"; NOT DRAWN: {', '.join(refused)}" if refused else ""))
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
