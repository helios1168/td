"""Scenario maps (issue #147): ONE PDF for the run, data/safe/maps/<run time>/maps.pdf, with every chosen scenario, CONUS pages
(the 9 census-division pages too with --divisions), each in the views per channel.  Runs on the owner's terminal in ONE Snowflake login:

    .\\tools\\maps\\scenario_maps.ps1 -All          (or -Scenario CA1_R105N,CA2_R105N, or -List; add -Divisions for the division pages)

FIXED annuity is left out of the opportunity and the sales by default (owner, 2026-11-19: "default is exclude"): 04 and 08 get their
`SET exclude_products` line replaced with the run's list.  -IncludeFixed (--include-all-products) leaves it empty and adds `-allproducts`
to the run folder's name; --exclude-products INDEX RILA (repeatable) leaves out those PRODUCT_V2 values instead and adds `-exINDEX-RILA`.
The summary line and the gap summary page say "excluding FIXED" or "all products".

Nothing is repeated across scenarios (owner, 2026-11-18: "we don't ever duplicate something"): a page that comes out the same
in several scenarios is in the PDF once, its corner naming them ("all scenarios" when it is every one drawn), and each gap CSV
holds every scenario with each row once, SCENARIO the scenarios that have the row (dollars the same to the cent, other numbers
to 9 significant digits).

Per scenario: 03_assignments.sql with `SET scenario` set (and data/safe/03_edits.sql spliced into its owner block, as
run_03_04.ps1), then 04_assigned_coverage.sql, then it reads td_assignments and td_map_piece and draws
the pages.  A scenario whose 03 result has a STATUS other than DEFAULT, EDITED or EDITED
(EITHER) is not drawn (its status counts are printed; the exit code is 1).  The PDFs hold names: they stay in data/safe.

Pages, per scenario, in the order geography (CONUS, then the divisions) x channel (NATIONAL, REGIONAL = role WIFI, WH) x view:
  A  whole states, each in its assigned person's colour (open seat hatched), the name on each state;
  B  the assigned states as a frame: the person's held in-role ZIPs solid, the rest of the assigned states in a light tint;
  C  today's in-role ZIPs of the kept holders with the role, one page per firm (CRBG, EQH); holders not kept hatched as open.
A ZIP belongs to a geography by its piece's STATE.
With tools/snowflake/07_overlap_gap.sql (issue #148) each scenario also runs it after 04, refuses its gap output when a MUST_BE_ZERO
row is not 0, and writes next to the PDF gap_cell.csv, gap_pair.csv, gap_person.csv, gap_summary.csv, gap_load.csv (masked: holder
keys R<n> only, safe to send to an agent; one file each for the run, as above) and the view D pages after the maps in maps.pdf
(a summary page, one seat-fit page per estimate, then geography x channel x estimate pages).
With tools/snowflake/08_seat_fit.sql (issue #151) each scenario also runs it after 07 (after creating td_state_adj from the state
shapes, two states adjacent when their shapes buffered by 1,000 m meet), refuses its seat output when a TIE row is not 0, and writes
seat_fit.csv (masked: the open-seat ranking of 08 plus an opportunity-only LOAD_BAND, safe to send) and seat_fit_names.csv (names and
sales U, G, DNASH: your screen only); the seat-fit page shows ranks only.  The shapes are read once (ST_SIMPLIFY in SQL), cached in data/safe/geo/
and drawn in EPSG:5070.  Pages are images (a vector page of 30,000 ZIPs runs to megabytes); scenarios draw in parallel.

Draft mode (issue #152, phase 2): `.\\tools\\maps\\scenario_maps.ps1 -Draft results\\draft\\2026-11-19` (python: `--draft <folder>`, optionally
`--scenario`, `--divisions`) draws draft_assign.py's keys-only ledger as data/safe/maps/<run>/draft.pdf, one page per scenario x
channel with each person in their own colour, names on the page (one Snowflake connection, only to read key -> name and the shapes;
no 03, 04 or 07).
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import csv
import datetime
import decimal
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
SQL08 = os.path.join(ROOT, "tools", "snowflake", "08_seat_fit.sql")
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


PRODUCTS_RE = re.compile(r"(?im)^(\s*SET\s+exclude_products\s*=\s*)'[^']*'\s*;")
DEFAULT_EXCLUDE = ("FIXED",)


def product_list(values):
    """The PRODUCT_V2 values of `values` (strings, each possibly several words), upper case, sorted, once each."""
    text = " ".join(values)
    if not re.fullmatch(r"[A-Za-z0-9 ]*", text):
        raise SystemExit(f"exclude products {text!r}: letters, digits and spaces only")
    return tuple(sorted(set(text.upper().split())))


def products_sql(sql, exclude):
    """04 or 08 with `SET exclude_products = '<list>';`, the list being `exclude` (a tuple of PRODUCT_V2 values, empty for all)."""
    exclude = product_list(exclude)
    out, n = PRODUCTS_RE.subn(lambda m: f"{m.group(1)}'{' '.join(exclude)}';", sql)
    if n != 1:
        raise SystemExit(f"the SQL has {n} lines `SET exclude_products = '...';` (needs exactly 1)")
    return out


def products_text(exclude):
    return "excluding " + ", ".join(exclude) if exclude else "all products"


def run_suffix(exclude):
    """The run folder's suffix: none for the default (FIXED left out), -allproducts for none left out, else -ex<values>."""
    return "" if tuple(exclude) == DEFAULT_EXCLUDE else "-ex" + "-".join(exclude) if exclude else "-allproducts"


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


def gap_failures(result, count=("N_ZIPS", "MM_OPP"), item=lambda r: r["ITEM"]):
    """The items of a 07 (or, with count and item given, 08) result's MUST_BE_ZERO = 1 rows whose `count` columns are not 0
    (within 0.5; NULL is 0)."""
    cols, rows = result
    out = []
    for r in (dict(zip(cols, x)) for x in rows):
        if r["MUST_BE_ZERO"] == 1 and any(abs(float(r[c] or 0)) > 0.5 for c in count):
            out.append(f"{item(r)} ({', '.join(f'{c} {r[c]}' for c in count)})")
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
    got["names"] = fetch_names(conn)
    return got


def fetch_names(conn):
    """{key: name}, on this machine only: td_holder_key's id is the UUID of the normalized name (02, 03)."""
    return dict(query(conn, f"SELECT 'R' || k.holder_n, a.wholesaler FROM {DB}.td_assignments a JOIN {DB}.td_holder_key k "
                            "ON k.source = a.source AND k.holder_id = UUID_STRING('6ba7b810-9dad-11d1-80b4-00c04fd430c8', "
                            r"NULLIF(UPPER(TRIM(REGEXP_REPLACE(TRIM(a.wholesaler), '\\s+', ' '))), ''))"))


def state_adjacency(states, buf=1000):
    """[(a, b)] in both directions: two states are adjacent when their shapes (EPSG:5070, metres) buffered by `buf` m intersect."""
    big = {s: g.buffer(buf) for s, g in states.items()}
    return [(a, b) for a in sorted(big) for b in sorted(big) if a != b and big[a].intersects(big[b])]


def make_state_adj(conn, states):
    """Create or replace the permanent table td_state_adj (state_a, state_b), which 08 reads, from the state shapes."""
    pairs = state_adjacency(states)
    query(conn, f"CREATE OR REPLACE TABLE {DB}.td_state_adj (state_a VARCHAR, state_b VARCHAR)")
    query(conn, f"INSERT INTO {DB}.td_state_adj (state_a, state_b) VALUES " + ", ".join(f"('{a}', '{b}')" for a, b in pairs))
    print(f"td_state_adj: {len(pairs)} state pairs", flush=True)


def fetch_seat(conn, scenario, sql08, split):
    """Run 08 for `scenario` (after 07, in the same session): {result, fit} as (columns, rows), the result being 08's one result
    and fit td_seat_fit's rows for the scenario; None when a MUST_BE_ZERO (TIE) row is not 0 (the failing items are printed)."""
    res = run_sql(conn, scenario_sql(sql08, scenario), split)
    bad = ["08 gave no result"] if res is None else gap_failures(
        res, ("N",), lambda r: " ".join(str(r[c]) for c in ("SECTION", "EST_SOURCE", "SEAT", "KIND") if r.get(c)))
    if bad:
        print(f"{scenario}: SEAT OUTPUT NOT WRITTEN, 08's must-be-zero checks not 0: " + "; ".join(bad))
        return None
    return {"result": res, "fit": query_cols(conn, f"SELECT * FROM {DB}.td_seat_fit WHERE scenario = '{scenario}'")}


# Area-adjusted load (owner, 2026-11-18: "the larger your territory is by area the more opportunity you're allowed to have
# above target ... the smaller the territory is the smaller your opportunity can be"; "go with how you recommend"):
# expected $ = base x (area / the channel's median area) ^ BETA, load = assigned $ / expected $, reported, never a gate.
BETA = 0.5                                   # expected $ grows with the square root of area (travel across the territory)
BASE_USD = {"REGIONAL": 1.25e9}              # WIFI: the stakeholders' $1.25B per territory
K_OF = {"NATIONAL": 11, "WH": 12}            # national and WH: the channel's attributed $ / K (owner's 11 and 12)
CHANNEL_OF_ROLE = {v: k for k, v in ROLE_OF.items()}
LOAD_COLS = ["SCENARIO", "EST_SOURCE", "HOLDER", "ROLE", "CHANNEL", "AREA_KM2", "ASSIGNED_USD", "BASE_USD", "MEDIAN_AREA_KM2",
             "EXPECTED_USD", "LOAD_RATIO"]


def gap_load(scenario, gap, state_area):
    """(columns, rows) of each assigned person's area-adjusted load per estimate.
    Assigned $: the cells attributed to them, all of a cell in a state they alone are assigned; in a split state (two or more of
    the channel's people assigned) all of a cell they alone hold (COVERED), an equal share of every other cell, so the people's
    $ add up to the channel's.  Area (km2, EPSG:5070, the cached state shapes, land and water): their assigned states, a
    split state shared equally, i.e. the territory they travel, not only its ZIPs with opportunity (the first run's areas were
    those ZIPs: 112,000 km2 for all of national)."""
    cell = [dict(zip(gap["cell"][0], r)) for r in gap["cell"][1]]
    person = [dict(zip(gap["person"][0], r)) for r in gap["person"][1]]
    usd, chan_usd = collections.Counter(), collections.Counter()
    for c in cell:
        est, ch, m = c["EST_SOURCE"], c["CHANNEL"], float(c["MM_OPP"] or 0)
        chan_usd[est, ch] += m
        keys = str(c["ASSIGNED"] or "").split()
        if not keys or ch == "OPEN":
            continue
        holders = str(c["HOLDERS"] or "").split()
        if c["CLASS"] == "COVERED" and len(holders) == 1 and holders[0] in keys:
            keys = holders
        for k in keys:
            usd[est, k] += m / len(keys)
    states = {(p["EST_SOURCE"], p["HOLDER"]): str(p["ASSIGNED_STATES"] or "").split() for p in person}
    n_on = collections.Counter((p["EST_SOURCE"], str(p["ROLE"] or "").upper(), s) for p in person for s in states[p["EST_SOURCE"], p["HOLDER"]])
    area = {(p["EST_SOURCE"], p["HOLDER"]): sum(state_area.get(s, 0.0) / n_on[p["EST_SOURCE"], str(p["ROLE"] or "").upper(), s]
                                                for s in states[p["EST_SOURCE"], p["HOLDER"]]) for p in person}
    rows, by_ch = [], collections.defaultdict(list)
    for p in person:
        ch = CHANNEL_OF_ROLE.get(str(p["ROLE"] or "").upper())
        if ch and usd[p["EST_SOURCE"], p["HOLDER"]] > 0:
            by_ch[p["EST_SOURCE"], ch].append(p)
    for (est, ch), ps in sorted(by_ch.items()):
        base = BASE_USD.get(ch) or chan_usd[est, ch] / K_OF[ch]
        areas = sorted(area[est, p["HOLDER"]] for p in ps if area[est, p["HOLDER"]] > 0)
        med = areas[len(areas) // 2] if len(areas) % 2 else (sum(areas[len(areas) // 2 - 1:len(areas) // 2 + 1]) / 2 if areas else 0.0)
        for p in sorted(ps, key=lambda p: p["HOLDER"]):
            a, u = area[est, p["HOLDER"]], usd[est, p["HOLDER"]]
            exp = base * (a / med) ** BETA if a > 0 and med > 0 else None
            rows.append((scenario, est, p["HOLDER"], p["ROLE"], ch, round(a, 1), round(u, 2), round(base, 2), round(med, 1),
                         None if exp is None else round(exp, 2), None if exp is None else round(u / exp, 3)))
    return LOAD_COLS, rows


def load_after(load, est, holder, seat_usd, seat_km2):
    """(ratio, band) of a person's load if they also took a seat: (assigned $ + seat $) / (base x ((area + seat's state km2) /
    median area) ^ BETA), opportunity only; band 'under 0.8', '0.8 to 1.25' or 'over 1.25'.  `load` is {(est, holder): the
    gap_load row as a dict}; (None, '') for a person with no load row (or no seat area)."""
    r = load.get((est, holder))
    if not r or seat_km2 is None or not r["MEDIAN_AREA_KM2"] or not r["BASE_USD"]:
        return None, ""
    ratio = (float(r["ASSIGNED_USD"]) + float(seat_usd)) / (float(r["BASE_USD"]) * ((float(r["AREA_KM2"]) + seat_km2) / float(r["MEDIAN_AREA_KM2"])) ** BETA)
    return ratio, "under 0.8" if ratio < 0.8 else "over 1.25" if ratio > 1.25 else "0.8 to 1.25"


def seat_prepare(seat, names, load, state_area):
    """What the seat page and CSVs need, from fetch_seat's {result, fit}, names {key: name}, gd.load (dicts) and state_area
    {state: km2}: cand (the SEAT rows as dicts, each with LOAD_BAND, for NEIGHBOUR rows), masked (the SEAT rows + LOAD_BAND, no
    names or sales) and sales (td_seat_fit's rows + NAME and LOAD_AFTER: your screen only), each (columns, rows)."""
    load = {(r["EST_SOURCE"], r["HOLDER"]): r for r in load}

    def after(r):
        if r["KIND"] != "NEIGHBOUR":
            return None, ""
        return load_after(load, r["EST_SOURCE"], r["HOLDER"], float(r["SEAT_MM_OPP"] or 0), state_area.get(r["SEAT"]))
    cols, rows = seat["result"]
    cand, masked = [], []
    for x in rows:
        r = dict(zip((c.upper() for c in cols), x))
        if r["SECTION"] == "SEAT":
            band = after(r)[1]
            cand.append(r | {"LOAD_BAND": band})
            masked.append(tuple(x) + (band,))
    fcols, frows = seat["fit"]
    sales = []
    for x in frows:
        r = dict(zip((c.upper() for c in fcols), x))
        ratio = after(r)[0]
        sales.append(tuple(x) + (names.get(r["HOLDER"], ""), None if ratio is None else round(ratio, 3)))
    return SimpleNamespace(cand=cand, masked=(list(cols) + ["LOAD_BAND"], masked), sales=(list(fcols) + ["NAME", "LOAD_AFTER"], sales))


def write_dedup_csv(path, per):
    """One CSV of {scenario: (columns, rows)}, each row once: its SCENARIO is the scenarios that have it, space-separated (always
    named, so a file read alone says who it covers).  Rows are compared with dollars (MM_OPP, OPP_*, *_USD) to the cent and other
    numbers to 9 significant digits, so float noise between runs merges and a ratio of 1.250 against 1.251 does not; a row a
    scenario has twice is kept twice."""
    cols, rows = None, {}
    for s, (c, got) in per.items():
        cols = cols or list(c)
        up = [x.upper() for x in cols]
        i, nth = up.index("SCENARIO"), collections.Counter()
        money = [u.endswith("MM_OPP") or u.startswith("OPP_") or u.endswith("_USD") for j, u in enumerate(up) if j != i]
        for r in got:
            rest = tuple(v for j, v in enumerate(r) if j != i)
            key = tuple((round(float(v), 2) if m else float(f"{float(v):.9g}")) if isinstance(v, (float, decimal.Decimal)) else v
                        for v, m in zip(rest, money))
            nth[key] += 1
            rows.setdefault((key, nth[key]), (rest, []))[1].append(s)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rest[:i] + (" ".join(ss),) + rest[i:] for rest, ss in rows.values())
    return path


def write_seat_csvs(out, seats):
    """seat_fit.csv (masked: keys and counts, safe to send) and seat_fit_names.csv (names and sales: your screen only) in `out`
    for {scenario: seat_prepare's result}, each row once as write_gap_csvs.  (the masked path, the names path)"""
    return (write_dedup_csv(os.path.join(out, "seat_fit.csv"), {s: v.masked for s, v in seats.items()}),
            write_dedup_csv(os.path.join(out, "seat_fit_names.csv"), {s: v.sales for s, v in seats.items()}))


def write_gap_csvs(out, gaps):
    """gap_<cell|pair|person|summary|load>.csv in `out` for {scenario: gap}, each row once: its SCENARIO is the scenarios that
    have it, space-separated (always named, so a file read alone says who it covers).  Rows are compared with dollars (MM_OPP,
    OPP_*, *_USD) to the cent and other numbers to 9 significant digits, so float noise between runs merges and a ratio of
    1.250 against 1.251 does not; a row a scenario has twice is kept twice (write_dedup_csv).  The paths."""
    return [write_dedup_csv(os.path.join(out, f"gap_{k}.csv"), {s: gap[k] for s, gap in gaps.items()}) for k in ("cell", "pair", "person", "summary", "load")]


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
        title = f"{view} · {ch} · {g.name}"   # the scenario is not drawn: the PDF's corner names who shares the page
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
               ("GAP (HELD TODAY)", "#f9e7a1", None, None), ("GAP (UNHELD)", "#f2b700", None, None), ("OPEN SEAT HELD", "#c4c4c4", "#6a6a6a", "////"),
               ("OPEN SEAT UNHELD", "#efefef", "#a8a8a8", "////")]
OPEN_CLASSES = ("OPEN SEAT HELD", "OPEN SEAT UNHELD")   # only on the OPEN page: an open seat has no channel (no one is assigned)
GAP_CH = ("NATIONAL", "REGIONAL", "WH", "OPEN")   # the channels with a page; OPEN is the open seats
GAP_ALL_CH = GAP_CH
GAP_CAPTION = ("A ZIP has the class of its cells in this channel with the most \\$MM of opportunity (MM_OPP); a ZIP with no cell in the channel is blank.  "
               "Names: the person(s) assigned to the state in this channel.  Legend: ZIPs and the \\$MM of their cells in this channel, on this page.")


# The FILL page (owner, 2026-11-18: "how do I see exactly where we need to fill to cover the all opportunity for CONUS in a single
# view"): every channel at once, a ZIP in the colour of its unfilled class with most $; covered, overlap and held by another are
# not fill: a ZIP with no unfilled $ is TO BARGAIN when it has OVERLAP or HELD BY ANOTHER $, else COVERED.  Colours: the Corebridge
# brand palette (pm/docs/brand.md, Brand Guidelines v2.1: secondary colours are for data visualisation; "use color to clarify, not
# decorate"): the fill classes strong (violets: gaps, oranges: open seats), the rest quiet (Blue 25%, 5% Black) (owner, 2026-11-18).
FILL_CLASSES = [("GAP (UNHELD)", "#4F00CA", None, None), ("GAP (HELD TODAY)", "#C053EF", None, None),
                ("OPEN SEAT UNHELD", "#EC602F", None, None), ("OPEN SEAT HELD", "#FA9454", None, None)]
BARGAIN = ("TO BARGAIN (overlap or held by another, no fill)", "#D0EAFD", None, None)
NO_FILL = ("COVERED (every cell, no fill)", "#F2F2F2", None, None)
FILL_CAPTION = ("Every channel at once: a ZIP has the colour of its unfilled class (GAP or OPEN SEAT, any channel) with the most \\$MM; a ZIP with no unfilled \\$ is "
                "TO BARGAIN if any cell is OVERLAP or HELD BY ANOTHER, else COVERED.\nLegend: ZIPs in that colour, the \\$MM of that class on this page; "
                "the CONUS page adds the unfilled \\$MM not on the map (no state, or no ZCTA shape).")


USD_PER_MM = 1e6   # MM_OPP is in dollars despite its name (04's result, e.g. 41,337,760,848.76 for $41.3B): the pages show $MM


def gap_prepare(cell, pair, names):
    """What the pages need, from the TD_GAP_CELL and TD_GAP_PAIR results ((columns, rows)) and names {key: name}: ests,
    zips {(est, channel): {zip: (state, class, $MM)}} (class = the ZIP's cells' class with most MM_OPP), assigned {(channel, state):
    names}, table {(est, channel, class): $MM} over every cell, pairs {est: the top 15 by $MM as (channel, A, B, n, $MM)}."""
    order = [c for c, *_ in GAP_CLASSES]
    by_zip, assigned, table = {}, {}, {}
    for r in (dict(zip(cell[0], x)) for x in cell[1]):
        est, ch, cls, mm = r["EST_SOURCE"], r["CHANNEL"], r["CLASS"], float(r["MM_OPP"] or 0) / USD_PER_MM
        if cls not in order or ch not in GAP_ALL_CH:
            raise SystemExit(f"TD_GAP_CELL has CLASS {cls!r}, CHANNEL {ch!r}; the pages know {order} and {GAP_ALL_CH}")
        table[est, ch, cls] = table.get((est, ch, cls), 0.0) + mm
        keys = str(r["ASSIGNED"] or "").replace(",", " ").split()
        if keys and ch in GAP_CH:
            assigned.setdefault((ch, str(r["STATE"]).upper()), set()).update(keys)
        for k in (ch, "FILL"):                             # FILL: the ZIP's cells of every channel
            z = by_zip.setdefault((est, k), {}).setdefault(str(r["ZIP_CODE"]), [str(r["STATE"]).upper(), {}])
            z[1][cls] = z[1].get(cls, 0.0) + mm
    zips = {k: {z: (st, max(order, key=lambda c: d.get(c, -1.0)), sum(d.values())) for z, (st, d) in v.items()} for k, v in by_zip.items() if k[1] != "FILL"}
    fill_order = [c for c, *_ in FILL_CLASSES]
    def fill_class(d):
        if any(d.get(c, 0) > 0 for c in fill_order):
            return max(fill_order, key=lambda c: d.get(c, -1.0))
        return BARGAIN[0] if d.get("OVERLAP", 0) > 0 or d.get("HELD BY ANOTHER", 0) > 0 else NO_FILL[0]
    fill = {est: {z: (st, fill_class(d), d) for z, (st, d) in v.items()} for (est, k), v in by_zip.items() if k == "FILL"}
    fill_total = {est: sum(v for (e, _, c), v in table.items() if e == est and c in fill_order) for est in {e for e, _, _ in table}}
    who = lambda k: f"{k} {names[k]}" if k in names else k
    pairs = {}
    for r in (dict(zip(pair[0], x)) for x in pair[1]):
        pairs.setdefault(r["EST_SOURCE"], []).append((r["CHANNEL"], who(r["HOLDER_A"]), who(r["HOLDER_B"]), r["N_ZIPS"] or 0, float(r["MM_OPP"] or 0) / USD_PER_MM))
    return SimpleNamespace(ests=sorted({e for e, _, _ in table}), seat=None, seat_pages=False, zips=zips, fill=fill, fill_total=fill_total, table=table, names=dict(names), load=[],
                           assigned={k: " / ".join(sorted(names.get(x, x) for x in v)) for k, v in assigned.items()},
                           pairs={e: sorted(v, key=lambda t: -t[4])[:15] for e, v in pairs.items()})


def gap_specs(geo, gd):
    """The gap pages after the seat pages as (geography, channel, estimate): geography, then the FILL pages (every channel), then
    channel x estimate."""
    return [(g, ch, est) for g in geo.geographies for ch in ("FILL",) + GAP_CH for est in gd.ests]


def gap_all(geo, gd):
    """Every gap page in order: None (the summary), ("SEAT", estimate) per estimate when 08 is in the run (gd.seat_pages), then gap_specs."""
    return [None] + ([("SEAT", est) for est in gd.ests] if gd.seat_pages else []) + gap_specs(geo, gd)


def draw_fill_page(gd, geo, title, g, est):
    """Every channel's unfilled opportunity on one map: each ZIP in its unfilled class with most $ (NO_FILL when none)."""
    fig, ax, vis = base_page(geo, g)
    by, mm = collections.defaultdict(list), collections.Counter()
    for z, (st, cls, d) in gd.fill.get(est, {}).items():
        if st in g.states and z in geo.zips:
            by[cls].append(z)
            for c, v in d.items():
                mm[c] += v
    handles = []
    for cls, col, edge, hatch in FILL_CLASSES + [BARGAIN, NO_FILL]:
        paths = [path_of(geo, geo.zips[z]) for z in by[cls]]
        if paths:
            c = PathCollection(paths, facecolor=col, edgecolor=edge or col, linewidth=0 if hatch else 0.1, hatch=hatch, zorder=1)
            c.set_gid(cls)
            ax.add_collection(c)
        dollars = "" if cls in (NO_FILL[0], BARGAIN[0]) else f" · ${mm[cls]:,.1f} MM"
        handles.append(Patch(facecolor=col, edgecolor=edge or "#202020", hatch=hatch, label=f"{cls}\n{len(by[cls]):,} ZIPs{dollars}"))
    state_lines_and_labels(ax, geo, vis, [])
    total = sum(mm[c] for c, *_ in FILL_CLASSES)
    if g.name == "CONUS":                                  # the unfilled $ the map cannot show, so the page ties to gap_summary
        off = round(gd.fill_total.get(est, 0.0) - total, 6) + 0.0   # summation round-off is not a -0.0; a real negative still shows
        handles.append(Patch(facecolor="white", edgecolor="white", label=f"not on the map (no state, or no ZCTA shape)\n${off:,.1f} MM unfilled"))
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.752, 0.95), fontsize=9, frameon=False, handlelength=1.4, borderaxespad=0,
               labelspacing=0.9, title=f"where to fill, every channel · {est} estimate · {g.name}\nunfilled ${total:,.1f} MM", title_fontsize=9, alignment="left")
    fig.suptitle(title, fontsize=17, fontweight="bold", y=0.975)
    fig.text(0.01, 0.015, FILL_CAPTION, fontsize=8.5, color="#404040")
    return fig


def draw_gap_page(gd, geo, title, g, ch, est):
    fig, ax, vis = base_page(geo, g)
    by, mm = collections.defaultdict(list), collections.Counter()
    for z, (st, cls, m) in gd.zips.get((est, ch), {}).items():
        if st in g.states and z in geo.zips:
            by[cls].append(z)
            mm[cls] += m
    handles = []
    for cls, col, edge, hatch in GAP_CLASSES:
        if (cls in OPEN_CLASSES) != (ch == "OPEN"):
            continue                                       # a class that cannot be on this page is not in its legend
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
        load = sorted((r for r in getattr(gd, "load", []) if r["EST_SOURCE"] == est and r["LOAD_RATIO"] is not None),
                      key=lambda r: -r["LOAD_RATIO"])
        if load:
            who = lambda k: f"{k} {gd.names.get(k, '')}".strip()
            fmt = lambda r: (f"{r['CHANNEL']:10}{who(r['HOLDER'])[:32]:<34}{r['AREA_KM2']:>12,.0f}{r['ASSIGNED_USD'] / USD_PER_MM:>12,.1f}"
                             f"{r['EXPECTED_USD'] / USD_PER_MM:>12,.1f}{r['LOAD_RATIO']:>8.2f}")
            head = f"{'channel':10}{'person':<34}{'area km2':>12}{'$MM':>12}{'expect $MM':>12}{'load':>8}"
            lines += [f"{est} estimate: load = $ / expected $ for the area (base x (area/median)^{BETA}); over 1: heavy for its area", head]
            lines += [fmt(r) for r in load[:8]] + ["  ..."] + [fmt(r) for r in load[-8:]] + [""]
    lines = [f"Products: {getattr(gd, 'products', 'not recorded')}", ""] + lines
    fig.suptitle("D overlaps and gaps · summary", fontsize=17, fontweight="bold", y=0.975)
    fig.text(0.02, 0.93, "\n".join(lines), family="monospace", fontsize=min(9.0, 560 / (1.3 * len(lines))), va="top")
    return fig


SEAT_CAPTION = ("Open seats by \\$MM of opportunity; per seat the 3 best-ranked NEIGHBOUR candidates (rank, key and name, borders = the person's states touch "
                "the seat, load band = their opportunity load if they also took it: under 0.8, 0.8 to 1.25, over 1.25) and the 3 best-ranked HOLDER "
                "candidates.  Ranks only: no sales figures.")


def draw_seat_page(gd, title, est):
    """The seat-fit page of one estimate: the seats by $MM, each with its top 3 NEIGHBOUR and top 3 HOLDER candidates (ranks, no
    sales); a page saying so when the scenario has no seat output (08 missing or refused)."""
    fig = Figure(figsize=FIGSIZE, dpi=DPI, facecolor="white")
    FigureCanvasAgg(fig)
    fig.suptitle(title, fontsize=17, fontweight="bold", y=0.975)
    seats = collections.defaultdict(list)
    for r in (gd.seat.cand if gd.seat else []):
        if r["EST_SOURCE"] == est:
            seats[r["SEAT"]].append(r)
    if not gd.seat:
        fig.text(0.02, 0.9, "No open-seat ranking for this scenario: 08_seat_fit.sql is not in this checkout, or its checks were refused (see the run's output).",
                 fontsize=12, va="top")
        return fig
    who = lambda k: f"{k} {gd.names.get(k, '')}".strip()[:26]
    usd = {s: float(rs[0]["SEAT_MM_OPP"] or 0) for s, rs in seats.items()}
    blocks = []
    for seat in sorted(seats, key=lambda s: (-usd[s], s)):
        rs = sorted(seats[seat], key=lambda r: r["RANK"])
        lines = [f"{seat}   \\${usd[seat] / USD_PER_MM:,.1f} MM"]
        lines += [f"  N{r['RANK']} {who(r['HOLDER']):<27}{'borders' if r['BORDERS'] else '':<9}{r['LOAD_BAND']}" for r in [r for r in rs if r["KIND"] == "NEIGHBOUR"][:3]]
        lines += [f"  H{r['RANK']} {who(r['HOLDER'])}" for r in [r for r in rs if r["KIND"] == "HOLDER"][:3]]
        blocks.append(lines + [""])
    per = max(1, -(-len(blocks) // 3))
    size = min(9.0, 560 / (1.3 * max(1, max((sum(len(b) for b in blocks[i:i + per]) for i in range(0, len(blocks), per)), default=1))))
    for c, i in enumerate(range(0, len(blocks), per)):
        fig.text(0.02 + 0.33 * c, 0.93, "\n".join(line for b in blocks[i:i + per] for line in b), family="monospace", fontsize=size, va="top")
    fig.text(0.01, 0.015, SEAT_CAPTION, fontsize=8.5, color="#404040")
    return fig


def gap_pages(scenario, gd, geo, lo=0, hi=None):
    """(title, figure) for the gap pages lo..hi: page 0 is the summary, then a seat-fit page per estimate, then geography x
    channel x estimate."""
    for spec in gap_all(geo, gd)[lo:hi]:
        if spec is None:
            title = "D overlaps and gaps · summary"
            yield title, draw_gap_summary(scenario, gd)
        elif spec[0] == "SEAT":
            title = f"D overlaps and gaps · seat fit · {spec[1]} estimate"
            yield title, draw_seat_page(gd, title, spec[1])
        else:
            g, ch, est = spec
            title = f"D overlaps and gaps · {ch} · {est} estimate · {g.name}"
            yield title, (draw_fill_page(gd, geo, title, g, est) if ch == "FILL" else draw_gap_page(gd, geo, title, g, ch, est))


# ---------------------------------------------------------------- the draft assignment (issue #152, phase 2)

# The Corebridge brand palette (pm/docs/brand.md, secondary colours for data visualisation), one colour per person; cycled when a
# person's neighbours wear them all (look.colouring: the colour fewest neighbours already wear).
BRAND = ["#4F00CA", "#C053EF", "#902BF8", "#3562FF", "#42ACF6", "#008368", "#4CD6BB", "#EC602F", "#FA9454", "#20113E"]
TOUCH_M = 250    # two ZCTAs touch when their shapes buffered by this many m meet (the 250 m simplification leaves slivers between them)
DRAFT_CAPTION = ("Draft assignment (#152): whole states to their one assignee; split states grown from each person's own ZIPs today, provisional "
                 "until bargaining (#149). Pieces per M1 on the drawn 2025 ZCTA graph.")
DRAFT_FILES = {"draft_ledger.csv.gz": ("SCENARIO", "ROLE", "ZIP_CODE", "STATE", "PERSON", "REASON"),
               "draft_m1.csv": ("SCENARIO", "ROLE", "PERSON", "N_PIECES", "PIECE", "N_ZCTAS", "CRBG_USD", "TAU_SHARE", "VERDICT", "NOTE")}


def read_draft(folder):
    """(ledger rows, m1 rows) as dicts from draft_assign.py's draft_ledger.csv.gz and draft_m1.csv in `folder`."""
    out = []
    for name, need in DRAFT_FILES.items():
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            raise SystemExit(f"{path}: not there; tools/maps/draft_assign.py writes it")
        with (gzip.open if name.endswith(".gz") else open)(path, "rt", encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            rows = list(rd)
        if set(need) - set(rd.fieldnames or ()):
            raise SystemExit(f"{path}: columns {rd.fieldnames}, needs {list(need)}")
        out.append(rows)
    return out


def zip_touch(geo):
    """geo.touch (built once): ids, each ZCTA's shape buffered by TOUCH_M, index {zip: i}, nbrs {zip: [zips that touch it]}."""
    if not hasattr(geo, "touch"):
        ids = sorted(geo.zips)
        buf = shapely.buffer(np.array([geo.zips[z] for z in ids], dtype=object), TOUCH_M, quad_segs=1)
        a, b = shapely.STRtree(buf).query(buf, predicate="intersects")
        nbrs = collections.defaultdict(list)
        for i, j in zip(a, b):
            if i != j:
                nbrs[ids[i]].append(ids[j])
        geo.touch = SimpleNamespace(ids=ids, buf=buf, index={z: i for i, z in enumerate(ids)}, nbrs=nbrs)
    return geo.touch


def draft_role(geo, ledger, m1, scenario, role):
    """What a draft page needs for one scenario and role (WIFI is the REGIONAL page): zips {zip: (state, person or '')} on drawn ZCTAs,
    m1 {person: {verdict, n, usd, note}} (FAIL when any piece fails; usd the CRBG $ over the pieces), people (every one with area or an
    M1 row), placed (people with a drawn ZCTA), colour {person: hex} (touching people differ), sig (equal for equal pages)."""
    zips = {r["ZIP_CODE"]: (r["STATE"], r["PERSON"]) for r in ledger
            if r["ROLE"] == role and scenario in r["SCENARIO"].split() and r["ZIP_CODE"] in geo.zips and r["STATE"] in geo.states}
    m = {}
    for r in m1:
        if r["ROLE"] == role and scenario in r["SCENARIO"].split():
            d = m.setdefault(r["PERSON"], {"verdict": "PASS", "n": 0, "usd": 0.0, "note": ""})
            d["n"] = int(r["N_PIECES"] or 0)
            d["usd"] += float(r["CRBG_USD"] or 0)
            d["note"] = d["note"] or r["NOTE"]
            if r["VERDICT"] != "PASS":
                d["verdict"] = r["VERDICT"]
    placed = {p for _, p in zips.values() if p}
    people = sorted(placed | set(m), key=lambda p: (int(p[1:]) if p[1:].isdigit() else 0, p))
    near = {p: set() for p in people}
    for a, nb in zip_touch(geo).nbrs.items():
        if a in zips and zips[a][1]:
            near[zips[a][1]].update(p for p in (zips[b][1] for b in nb if b in zips) if p and p != zips[a][1])
    colour = look.colouring({p: None for p in people}, near, BRAND) if people else {}
    sig = (tuple(sorted((z, *v) for z, v in zips.items())), tuple(sorted((p, tuple(d.items())) for p, d in m.items())))
    return SimpleNamespace(zips=zips, m1=m, people=people, placed=placed, colour=colour, sig=sig)


def largest_piece_point(geo, zs):
    """The label point of the largest (by area) group of touching ZCTAs of `zs`."""
    t, left, best = zip_touch(geo), set(zs), None
    while left:
        comp, todo = set(), [left.pop()]
        while todo:
            z = todo.pop()
            comp.add(z)
            new = [n for n in t.nbrs[z] if n in left]
            left.difference_update(new)
            todo += new
        area = sum(geo.zips[z].area for z in comp)
        if best is None or area > best[0]:
            best = (area, comp)
    part = max(shapely.get_parts(shapely.union_all([geo.zips[z] for z in best[1]])), key=lambda p: p.area)   # drawn shapes, not the buffers
    return shapely.ops.polylabel(part, tolerance=3000)


def draw_draft_page(geo, dd, names, title, g):
    """One page: each person's ZCTAs in their colour, states with no one in this role white, unreachable ZCTAs black."""
    fig, ax, vis = base_page(geo, g)
    by, lost = collections.defaultdict(list), []
    for z, (st, p) in sorted(dd.zips.items()):
        if st in g.states:
            (by[p] if p else lost).append(z)
    have = {st for st, p in dd.zips.values() if p}
    layer(ax, geo, [geo.states[s] for s in sorted(g.states - have)], facecolor="white", edgecolor=OPEN_EDGE, linewidth=0.8, zorder=1, gid="open")
    items = []
    for p in dd.people:
        if by.get(p):
            layer(ax, geo, [geo.zips[z] for z in by[p]], facecolor=dd.colour[p], edgecolor=dd.colour[p], linewidth=0.15, zorder=2, gid=p)
            pt = largest_piece_point(geo, by[p])
            items.append((pt.x, pt.y, f"{p} {names.get(p, '')}".strip()))
    layer(ax, geo, [geo.zips[z] for z in lost], facecolor="black", edgecolor="black", linewidth=0.15, zorder=2, gid="unreachable")
    state_lines_and_labels(ax, geo, vis, items)
    shown = [p for p in dd.people if by.get(p) or (g.name == "CONUS" and p not in dd.placed)]   # a person with no ZCTA is on CONUS only
    n = len(shown)
    handles = []
    for p in shown:
        d = dd.m1.get(p, {"verdict": "no M1 row", "n": 0, "usd": 0.0, "note": ""})
        info = f"{d['verdict']} · {d['n']} piece{'' if d['n'] == 1 else 's'} · \\${d['usd'] / USD_PER_MM:,.0f} MM CRBG" + (f" · {d['note']}" if d["note"] else "")
        handles.append(Patch(facecolor=dd.colour[p], edgecolor="#202020", label=f"{p} {names.get(p, '')}".strip() + ("\n" if n <= 20 else "  ") + info))
    handles.append(Patch(facecolor="white", edgecolor=OPEN_EDGE, label="open in this role"))
    if lost:
        handles.append(Patch(facecolor="black", edgecolor="black", label=f"unreachable ZCTAs ({len(lost):,})"))
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.752, 0.95), fontsize=6.6 if n <= 20 else 5.8, frameon=False,
               handlelength=1.2, borderaxespad=0, labelspacing=0.55 if n <= 20 else 0.3)
    fig.suptitle(title, fontsize=17, fontweight="bold", y=0.975)
    fig.text(0.01, 0.015, DRAFT_CAPTION, fontsize=9, color="#404040")
    return fig


def draft_figs(geo, ledger, m1, names, chosen):
    """{scenario: [(title, figure)]} in order geography x channel (NATIONAL, REGIONAL, WH).  Scenarios whose page is the same share
    one figure, drawn once, its title naming them (merge_pages then puts it in the PDF once)."""
    dds = {(s, role): draft_role(geo, ledger, m1, s, role) for s in chosen for role in ROLE_OF.values()}
    per, made = {s: [] for s in chosen}, {}
    for g in geo.geographies:
        for ch, role in ROLE_OF.items():
            for s in chosen:
                key = (g.name, role, dds[s, role].sig)
                if key not in made:
                    who = ", ".join(x for x in chosen if dds[x, role].sig == key[2])
                    title = f"Draft · {ch} · {who} · {g.name}"
                    made[key] = (title, draw_draft_page(geo, dds[s, role], names, title, g))
                per[s].append(made[key])
    return per


def main_draft(args):
    ledger, m1 = read_draft(args.draft)
    have = list(dict.fromkeys(s for r in ledger for s in r["SCENARIO"].split()))
    chosen = [s for a in args.scenario for s in a.split(",") if s] or have
    if set(chosen) - set(have):
        raise SystemExit(f"unknown scenario {sorted(set(chosen) - set(have))}; {args.draft} has {have}")
    keys = {r["PERSON"] for r in ledger + m1 if r["PERSON"] and set(r["SCENARIO"].split()) & set(chosen)}
    with connect() as conn:
        names = fetch_names(conn)
        geo = load_geo(conn)
    if not args.divisions:
        geo.geographies = geo.geographies[:1]
    per, png = {}, {}
    for s, figs in draft_figs(geo, ledger, m1, names, chosen).items():
        for _, fig in figs:
            if id(fig) not in png:
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=DPI, facecolor="white")
                png[id(fig)] = buf.getvalue()
        per[s] = [png[id(fig)] for _, fig in figs]
    out = os.path.join(MAPS_DIR, datetime.datetime.now().strftime("%Y-%m-%d-%H%M"))
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "draft.pdf")
    print(f"{os.path.abspath(path)}: {assemble(path, merge_pages(per))} pages (a page the same in several scenarios is there once), names: your screen only", flush=True)
    missing = sorted(keys - set(names), key=lambda k: (len(k), k))
    if missing:
        print(f"NO NAME for {', '.join(missing)}: td_assignments has no holder with that key, drawn by key only")
    return 1 if missing else 0


# ---------------------------------------------------------------- the run

_GEO = None


def _init(geo):
    global _GEO
    _GEO = geo


CHUNK = 10    # pages per task: a scenario's pages spread over every worker
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


def merge_pages(per, every=None):
    """{scenario: [PNG bytes in page order]} -> [(png, label)]: page by page, scenarios whose page is the same picture share
    one page, labelled with their names, or "all scenarios" when they are all of `every` (default: the keys of `per`; the
    gap pages pass every scenario drawn, so a scenario whose gap output was refused is not hidden under "all")."""
    every = list(per) if every is None else list(every)
    n = {len(v) for v in per.values()}
    if len(n) != 1:
        raise RuntimeError(f"scenarios with different page counts {sorted(n)}")
    out = []
    for i in range(n.pop()):
        groups = {}
        for s in per:
            groups.setdefault(per[s][i], []).append(s)
        out += [(png, "all scenarios" if set(ss) == set(every) and len(ss) > 1 else " · ".join(ss)) for png, ss in groups.items()]
    return out


def assemble(path, pages):
    """The PDF of the pages [(PNG bytes, label)], in order, each a picture with its label (the scenarios) in the corner."""
    import matplotlib.image
    with PdfPages(path) as pdf:
        for png, label in pages:
            pic = Figure(figsize=FIGSIZE, dpi=DPI)
            axis = pic.add_axes([0, 0, 1, 1])
            axis.imshow(matplotlib.image.imread(io.BytesIO(png), format="png"), interpolation="none", aspect="auto")
            axis.set_axis_off()
            pic.text(0.006, 0.975, label, fontsize=13, fontweight="bold", color="#1f4e9e", va="center")
            pdf.savefig(pic, dpi=DPI)
    if not pages:
        raise RuntimeError(f"{path}: no page to draw")
    return len(pages)


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
    ap.add_argument("--divisions", action="store_true", help="draw the 9 census-division pages too (off: CONUS only, for speed)")
    ap.add_argument("--draft", metavar="FOLDER", help="draw the draft assignment of draft_assign.py's folder (no 03, 04 or 07; --scenario optional)")
    ap.add_argument("--exclude-products", action="append", default=[], metavar="PRODUCT",
                    help="PRODUCT_V2 values left out of the opportunity and sales (repeatable or space-separated; default FIXED)")
    ap.add_argument("--include-all-products", action="store_true", help="leave no product out (the default leaves FIXED out)")
    ap.add_argument("--jobs", type=int, help="drawing processes (default: the CPUs less one, at most 8); 1 draws in this process")
    args = ap.parse_args(argv)
    if args.draft:
        return main_draft(args)
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
    if args.include_all_products and args.exclude_products:
        ap.error("--include-all-products and --exclude-products are opposites")
    exclude = () if args.include_all_products else product_list(args.exclude_products) or DEFAULT_EXCLUDE
    products = products_text(exclude)
    print(f"products: {products}")
    with open(SQL04, encoding="utf-8") as f:
        sql04 = products_sql(f.read(), exclude)
    sql08 = None
    if os.path.exists(SQL08):
        with open(SQL08, encoding="utf-8") as f:
            sql08 = products_sql(f.read(), exclude)
    else:
        print("08_seat_fit.sql is not in this checkout: no open-seat ranking")
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
    out = os.path.join(MAPS_DIR, datetime.datetime.now().strftime("%Y-%m-%d-%H%M") + run_suffix(exclude))
    os.makedirs(out, exist_ok=True)
    jobs = args.jobs or max(1, min((os.cpu_count() or 2) - 1, 8))   # ponytail: 8 at most, each worker holds the shapes
    send = []
    t0, refused, futs, pool, n_pages, started, gaps, adj = time.time(), [], {}, None, None, {}, {}, False
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
                if not args.divisions:
                    geo.geographies = geo.geographies[:1]   # CONUS only (owner, 2026-11-18: stop the region maps for now, for speed)
                n_pages = len(specs(geo))
                _init(geo)
                if jobs > 1:
                    pool = concurrent.futures.ProcessPoolExecutor(jobs, initializer=_init, initargs=(geo,))
            submit = (lambda fn, *a: pool.submit(fn, *a)) if pool else (lambda fn, *a: _done(fn(*a)))
            seat = None
            if gap and sql08:
                if not adj:
                    make_state_adj(conn, geo.states)
                    adj = True
                seat = fetch_seat(conn, name, sql08, split_statements)
                if seat is None:
                    refused.append(name + " (seat output only)")
            started[name] = time.time()
            for lo, hi in chunks(n_pages):
                futs[name, lo] = submit(draw_chunk, name, got[0], got[1], lo, hi)
            if gap:
                gap["load"] = gap_load(name, gap, {s: g.area / 1e6 for s, g in geo.states.items()})
                gd = gap_prepare(gap["cell"], gap["pair"], gap["names"])
                gd.products = products
                gd.load = [dict(zip(gap["load"][0], r)) for r in gap["load"][1]]
                gd.seat_pages = bool(sql08)         # 08 in the run: every scenario has the seat pages (a page saying so when its output was refused)
                if seat:
                    gd.seat = seat_prepare(seat, gd.names, gd.load, {s: g.area / 1e6 for s, g in geo.states.items()})
                skipped = len({z for z_ in gd.zips.values() for z, (st, _, _) in z_.items() if st in geo.states and z not in geo.zips})
                gaps[name] = (gd, skipped, gap)
                for lo, hi in chunks(len(gap_all(geo, gd))):
                    futs[name + "_gaps", lo] = submit(draw_gap_chunk, name, gd, lo, hi)
    maps, per = [s for s in chosen if s in started], {}
    for name in maps:
        parts = sorted(futs[k].result() for k in futs if k[0] == name)
        per[name] = [png for _, pngs, _ in parts for png in pngs]
        print(f"{name}: {len(per[name])} map pages; {parts[0][2]} CONUS ZIPs in td_map_piece have no ZCTA shape, not drawn", flush=True)
    pages = merge_pages(per) if per else []
    gper = {name: [png for _, pngs in sorted(futs[k].result() for k in futs if k[0] == name + "_gaps") for png in pngs] for name in gaps}
    for name, (_, skipped, _) in gaps.items():
        print(f"{name}: {len(gper[name])} gap pages; {skipped} CONUS ZIPs of the gap cells have no ZCTA shape, not drawn", flush=True)
    pages += merge_pages(gper, maps) if gper else []
    if pages:
        path = os.path.join(out, "maps.pdf")
        print(f"{os.path.abspath(path)}: {assemble(path, pages)} pages (a page the same in several scenarios is there once), names: your screen only", flush=True)
    if gaps:
        send = write_gap_csvs(out, {name: gap for name, (_, _, gap) in gaps.items()})
    seats = {name: gd.seat for name, (gd, _, _) in gaps.items() if gd.seat}
    screen = []
    if seats:
        masked, names_csv = write_seat_csvs(out, seats)
        send.append(masked)
        screen.append(names_csv)
    if pool:
        pool.shutdown()
    print(f"done in {time.time() - t0:.0f} s ({products})" + (f"; NOT DRAWN: {', '.join(refused)}" if refused else ""))
    print(f"maps folder: {os.path.abspath(out)}")
    if send:
        print("safe to send to an agent (holder keys R<n> and counts only, no names):")
        for p in send:
            print(f"  {os.path.abspath(p)}" + ("   (large, one row per cell: not needed unless asked)" if p.endswith("gap_cell.csv") else ""))
    if screen:
        print("names and sales: your screen only:")
        for p in screen:
            print(f"  {os.path.abspath(p)}")
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
