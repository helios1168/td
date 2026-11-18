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
A ZIP belongs to a geography by its piece's STATE.  The shapes are read once (ST_SIMPLIFY in SQL), cached in data/safe/geo/
and drawn in EPSG:5070.  Pages are images (a vector page of 30,000 ZIPs runs to megabytes); scenarios draw in parallel.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
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
from matplotlib.collections import LineCollection, PatchCollection
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
    run_sql(conn, sql04, split)
    roster = query(conn, f"SELECT source, wholesaler, kept, role, assigned_states FROM {DB}.td_assignments")
    pieces = query(conn, f"SELECT source, wholesaler, kept, role, zip_code, state, terr_channel, piece_in_role FROM {DB}.td_map_piece")
    return roster, pieces


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
        rows = query(conn, f"SELECT {key}, ST_ASWKB(ST_SIMPLIFY(geo_boundary, {tol})) FROM {DB}.{table}")
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
    people = {}
    for src, name, kept, role, states in roster:
        src, role = (src or "").upper(), (role or "").upper()
        if str(kept or "").upper() == "Y" and role in ROLE_OF.values():
            people[(src, name)] = SimpleNamespace(key=(src, name), source=src, name=name, role=role,
                                                  states=sorted(set(str(states or "").replace(",", " ").upper().split()) & set(geo.states)),
                                                  all_states=str(states or "").upper())
    held, opened = collections.defaultdict(set), collections.defaultdict(set)
    for src, name, kept, role, z, st, tc, inrole in pieces:
        src, st, tc = (src or "").upper(), (st or "").upper(), (tc or "").upper()
        if st not in geo.states or z not in geo.zips:
            continue                                            # not CONUS, or no ZCTA shape
        if src not in FIRMS:
            raise SystemExit(f"td_map_piece has source {src!r}; the pages draw {FIRMS}")
        if str(kept or "").upper() == "Y":
            if inrole and (src, name) in people:
                held[(src, name), st].add(z)
        else:
            opened[(src, tc), st].add(z)
    union = lambda d: {k: shapely.union_all([geo.zips[z] for z in v]) for k, v in d.items()}
    ctx = SimpleNamespace(geo=geo, people=sorted(people.values(), key=lambda p: (p.name.upper(), p.source, p.name)),
                          held=collections.defaultdict(dict), opened=collections.defaultdict(dict))
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


def draw_page(ctx, title, g, ch, view, firm):
    """One figure.  view[0] is A, B or C; `firm` is C's firm."""
    geo = ctx.geo
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
    segs = [r for s in vis for r in geo.segs[s]]
    ax.add_collection(LineCollection(segs, colors="#606060", linewidths=0.5, linestyle=(0, (4, 2)), zorder=3))
    look.place_labels(ax, items, fs=7, marker=False, near=[(0, 0, "center", "center")], color="#111111", fontweight="bold")
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


def pages(scenario, ctx):
    """(title, figure) for every page, in order: geography, channel, view."""
    for g in ctx.geo.geographies:
        for ch in ROLE_OF:
            for view, firm in VIEWS:
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


# ---------------------------------------------------------------- the run

_GEO = None


def _init(geo):
    global _GEO
    _GEO = geo


def draw_scenario(scenario, roster, pieces, path):
    t = time.time()
    n = write_pdf(path, pages(scenario, prepare(roster, pieces, _GEO)))
    return path, n, time.time() - t


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true", help="print the scenario names in 03_assignments.sql")
    ap.add_argument("--scenario", action="append", default=[], help="a scenario to draw (repeatable)")
    ap.add_argument("--all", action="store_true", help="draw every scenario")
    ap.add_argument("--jobs", type=int, help="PDFs drawn at once (default: one per scenario, up to the CPUs)")
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
    jobs = args.jobs or min(len(chosen), os.cpu_count() or 1)
    t0, refused, futs, pool = time.time(), [], {}, None
    with connect() as conn:
        for name in chosen:
            got = fetch_scenario(conn, name, sql03, sql04, edits, split_statements)
            print(f"{name}: 03 and 04 done at {time.time() - t0:.0f} s", flush=True)
            if got is None:
                refused.append(name)
                continue
            if _GEO is None and pool is None:
                geo = load_geo(conn)
                if jobs > 1:
                    pool = concurrent.futures.ProcessPoolExecutor(jobs, initializer=_init, initargs=(geo,))
                else:
                    _init(geo)
            args_ = (name, got[0], got[1], os.path.join(out, f"{name}.pdf"))
            if pool:
                futs[name] = pool.submit(draw_scenario, *args_)
            else:
                futs[name] = concurrent.futures.Future()
                futs[name].set_result(draw_scenario(*args_))
    for name, fut in futs.items():
        path, n, secs = fut.result()
        print(f"{os.path.relpath(path, ROOT)}: {n} pages in {secs:.0f} s")
    if pool:
        pool.shutdown()
    print(f"done in {time.time() - t0:.0f} s" + (f"; NOT DRAWN: {', '.join(refused)}" if refused else ""))
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
