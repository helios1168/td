"""tools/maps/dashboard.py (issue #153): the run's dashboard, built from a made-up world (5 box states in 2 census regions and 3
divisions, 2 ZIPs each, 2 scenarios, 2 estimates, keys R1..R8, no Snowflake) and, when $TD_REPO/data/safe/dev_dashboard is there,
from the owner's last run (keys only).  The exported cells tie out (07's classes one by one to the run's summary, and the page's
four classes to their sum; region = its divisions = its states; today's cells to the same estimate), the today views cover every ZIP
with a territory piece, the counts add up, the sales are in the page and in no CSV, no name is in a dev build, the page holds no
http(s) URL outside the vendored library and licence, it is under the size bound, the build is the same bytes every time, and in
headless Chromium the page itself reports the tie-out and asks for nothing online."""
import base64
import collections
import contextlib
import glob
import gzip
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

from shapely.geometry import Polygon, box

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / "maps" / f"{name}.py")
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


sm = _load("scenario_maps")
dash = _load("dashboard")
DEV = os.path.join(os.environ.get("TD_REPO", str(ROOT)), "data", "safe", "dev_dashboard")
PUBLIC = os.path.join(os.environ.get("TD_REPO", str(ROOT)), "data", "public")
URL = re.compile(r"https?://[^\s\"'`<>)\\]*")

# ---- the made-up world: EPSG:5070 boxes in the West (CA, OR: Pacific; NV: Mountain) and the Northeast (NY, NJ: Middle Atlantic)
SIDE = 400_000.0
CORNER = {"CA": (-2.2e6, 1.6e6), "OR": (-2.2e6, 2.0e6), "NV": (-1.8e6, 1.6e6), "NY": (1.6e6, 2.2e6), "NJ": (1.6e6, 1.8e6)}
ZIPS = {"CA": ("90001", "90002"), "OR": ("91001", "91002"), "NV": ("92001", "92002"), "NY": ("93001", "93002"), "NJ": ("94001", "94002")}
NAMES = {f"R{i}": n for i, n in enumerate(("Ann Qalderz", "Bo Qbirchz", "Cy Qcedarz", "Di Qdogwoodz", "Ed Qelmz", "Flo Qfirz", "Gil Qgumz", "Hu Qhazelz"), 1)}   # made up, and not words of the page
CELL_COLS = ["SCENARIO", "EST_SOURCE", "ZIP_CODE", "STATE", "NEW_DIST", "MM_OPP", "CHANNEL", "ASSIGNED", "CLASS", "N_HOLDERS", "HOLDERS"]
PAIR_COLS = ["SCENARIO", "EST_SOURCE", "CHANNEL", "HOLDER_A", "HOLDER_B", "N_ZIPS", "MM_OPP"]
PERSON_COLS = ["SCENARIO", "EST_SOURCE", "HOLDER", "SOURCE", "ROLE", "ASSIGNED_STATES", "OPP_ASSIGNED", "OPP_COVERED", "OPP_OVERLAP", "OPP_GAP",
               "OPP_HELD_BY_ANOTHER", "OPP_HELD_ELSEWHERE", "N_ZIPS_ASSIGNED"]
SUMMARY_COLS = ["SECTION", "SCENARIO", "EST_SOURCE", "CHANNEL", "ITEM", "N_ZIPS", "MM_OPP", "PCT", "MUST_BE_ZERO"]
SEAT_COLS = ["SECTION", "SCENARIO", "EST_SOURCE", "SEAT", "KIND", "HOLDER", "RANK", "BORDERS", "SEAT_MM_OPP", "N", "MUST_BE_ZERO", "LOAD_BAND"]
ROSTER = [("R1", "CRBG", "WIFI", "CA"), ("R2", "EQH", "WIFI", "CA OR"), ("R3", "CRBG", "NATIONAL", "CA"), ("R4", "CRBG", "WH", "OR"),
          ("R5", "EQH", "WH", ""), ("R6", "EQH", "WIFI", "NY NJ")]
# zip, state, fine channel, $, channel, assigned, class, holders: every class, a split state (CA), a ZIP with two cells, a ZIP with
# no shape (99999), a cell with no state
BASE = [("90001", "CA", "FI", 100e6, "REGIONAL", "R1 R2", "COVERED", "R1"), ("90002", "CA", "FI", 50e6, "REGIONAL", "R1 R2", "OVERLAP", "R1 R2"),
        ("90002", "CA", "WELLS FI", 20e6, "NATIONAL", "R3", "GAP (HELD TODAY)", ""), ("91001", "OR", "FI", 30.25e6, "REGIONAL", "R2", "GAP (UNHELD)", ""),
        ("91002", "OR", "WH", 10e6, "WH", "R4", "HELD BY ANOTHER", "R5"), ("92001", "NV", "FI", 40e6, "OPEN", "", "OPEN SEAT HELD", "R1"),
        ("92002", "NV", "FI", 5e6, "OPEN", "", "OPEN SEAT UNHELD", ""), ("93001", "NY", "FI", 60e6, "REGIONAL", "R6", "COVERED", "R6"),
        ("94001", "NJ", "FI", 70e6, "REGIONAL", "R6", "COVERED", "R6"), ("99999", "NJ", "FI", 3e6, "REGIONAL", "R6", "COVERED", "R6"),
        ("94002", "", "FI", 2e6, "OPEN", "", "OPEN SEAT UNHELD", "")]


# Today's territories (source, key, ZIP, state, channel): R7 (CRBG) and R8 (EQH) hold territory and are on no roster; 91002 has two
# EQH WH holders; no CRBG FI territory in Oregon and no EQH territory on 92002 (no one); 99999 has no shape.  Seat plan 1 brings R7
# back for Nevada, the open seat (plan 2 does not, and is not shown).  Sales (seller, ZIP, $): R1 also sells outside California.
TODAY = [("CRBG", "R1", "90001", "CA", "WH"), ("CRBG", "R1", "90001", "CA", "FI"), ("CRBG", "R1", "90002", "CA", "WH"), ("CRBG", "R3", "90002", "CA", "FI"),
         ("CRBG", "R4", "91001", "OR", "WH"), ("CRBG", "R4", "91002", "OR", "WH"), ("CRBG", "R7", "92001", "NV", "WH"), ("CRBG", "R7", "92001", "NV", "FI"),
         ("CRBG", "R7", "92002", "NV", "WH"), ("CRBG", "R7", "92002", "NV", "FI"), ("CRBG", "R7", "93001", "NY", "FI"),
         ("EQH", "R2", "90001", "CA", "WH"), ("EQH", "R2", "90002", "CA", "FI"), ("EQH", "R2", "91001", "OR", "FI"), ("EQH", "R2", "91002", "OR", "WH"),
         ("EQH", "R5", "91002", "OR", "WH"), ("EQH", "R8", "92001", "NV", "FI"), ("EQH", "R6", "93001", "NY", "WH"), ("EQH", "R6", "93001", "NY", "FI"),
         ("EQH", "R6", "93002", "NY", "FI"), ("EQH", "R6", "94001", "NJ", "FI"), ("EQH", "R6", "94002", "NJ", "FI"), ("EQH", "R6", "99999", "NJ", "FI")]
PLAN_COLS = ["SCENARIO", "EST_SOURCE", "PLAN", "SEAT", "CHOICE", "HOLDER", "BUNDLE", "LOAD_BAND"]
SALE = 7654321.25          # a sale no other number of the made-up world looks like
SALES = [("R1", "90001", SALE), ("R1", "91001", 5000.0), ("R2", "90002", 250.4), ("R7", "92001", 300.0), ("R6", "93001", -20.0), ("R6", "99999", 40.0),
         ("R4", "91001", 0.0), ("", "90001", 7.0)]


def fake_geo():
    states = {s: box(x, y, x + SIDE, y + SIDE) for s, (x, y) in CORNER.items()}
    zips = {}
    for s, (x, y) in CORNER.items():
        zips[ZIPS[s][0]], zips[ZIPS[s][1]] = box(x, y, x + SIDE / 2, y + SIDE), box(x + SIDE / 2, y, x + SIDE, y + SIDE)
    return sm.make_geo(states, zips, [])


def fake_cells(scenario):
    """S2 differs from S1 in one cell: Oregon's unheld gap is covered by R2."""
    rows = []
    for est, k in (("CRBG", 1.0), ("EQH", 0.9)):
        for z, st, dist, usd, ch, asg, cls, held in BASE:
            if scenario == "S2" and z == "91001":
                cls, held = "COVERED", "R2"
            rows.append((scenario, est, z, st, dist, round(usd * k, 2), ch, asg or None, cls, len(held.split()), held or None))
    return rows


def fake_today(scenario):
    """fetch_today's two tables: the pieces with the scenario's roster on them, and the opportunity by the cell's channel today (the
    fine channel's own, but New York's 93001 sits in IFA today: in no WH or FI territory)."""
    roster = {k: role for k, _, role, _ in fake_roster(scenario)}
    cells = collections.Counter()
    for _, est, z, st, dist, usd, *_ in fake_cells(scenario):
        cells[scenario, est, z, st, "IFA" if z == "93001" else "WH" if dist == "WH" else "FI"] += usd
    return ((sm.TODAY_COLS, [(scenario, src, k, "Y" if k in roster else "N", roster.get(k, ""), z, st, ch) for src, k, z, st, ch in TODAY]),
            (sm.CELL_TODAY_COLS, [(*k, v) for k, v in cells.items()]))


def fake_roster(scenario):
    """S2's sheet differs from S1's in one person: R5 (EQH, WH) has Nevada."""
    return [(k, src, role, "NV" if (scenario, k) == ("S2", "R5") else states) for k, src, role, states in ROSTER]


def fake_run(scenario, summary_off=0.0):
    """The tables a run has for `scenario`; `summary_off` dollars are added to the summary's first row (a run that does not tie)."""
    cells = fake_cells(scenario)
    by = collections.Counter()
    pairs = []
    for _, est, z, st, dist, usd, ch, asg, cls, n, held in cells:
        by[est, ch, cls] += usd
        if cls == "OVERLAP":
            pairs.append((scenario, est, ch, *held.split(), 1, usd))
    summary = [("CLASS", scenario, est, ch, cls, 1, usd, None, 0) for (est, ch, cls), usd in by.items()]
    summary[0] = summary[0][:6] + (summary[0][6] + summary_off,) + summary[0][7:]
    summary.append(("TIE", scenario, None, None, "KEPT HOLDERS WITH NO td_holder_key ROW", 0, None, None, 1))
    person = [(scenario, est, k, src, role, states, 1e6, 1e6, 0.0, 0.0, 0.0, 0.0, 1) for est in ("CRBG", "EQH") for k, src, role, states in fake_roster(scenario)]
    gap = {"cell": (CELL_COLS, cells), "pair": (PAIR_COLS, pairs), "person": (PERSON_COLS, person), "summary": (SUMMARY_COLS, summary)}
    gap["load"] = sm.gap_load(scenario, gap, {s: SIDE * SIDE / 1e6 for s in CORNER})
    gap["seat"] = (SEAT_COLS, [("SEAT", scenario, est, "NV", kind, "R1", 1, 1, 45e6, None, 0, "0.8 to 1.25" if kind == "NEIGHBOUR" else "")
                               for est in ("CRBG", "EQH") for kind in ("NEIGHBOUR", "HOLDER")])
    gap["plan"] = (PLAN_COLS, [(scenario, est, no, "NV", choice, k, bundle, band) for est in ("CRBG", "EQH")
                               for no, choice, k, bundle, band in ((1, "READD", "R7", "NV", ""), (2, "NEIGHBOUR", "R1", "", "0.8 to 1.25"))])
    gap["today"], gap["cell_today"] = fake_today(scenario)
    return gap


def fake_runs(**kw):
    return {s: fake_run(s, **kw) for s in ("S1", "S2")}


@contextlib.contextmanager
def built(runs=None, names=None, geo=None, sales=SALES, made_up=()):
    """(the page's text, its payload) of a build in a temporary folder."""
    with tempfile.TemporaryDirectory() as d:
        path = dash.build(geo or fake_geo(), runs or fake_runs(), os.path.join(d, "dashboard.html"), names, "excluding FIXED", "2026-11-19-0200", sales, made_up)
        text = open(path, encoding="utf-8").read()
        yield text, json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', text, re.S).group(1)), path


def dev_runs():
    """(geo, runs) of the owner's last run under data/safe/dev_dashboard (keys only), or None with a SKIP line when it is not there."""
    if not os.path.exists(os.path.join(DEV, "gap_cell.csv")):
        print(f"SKIP  the owner's run: {DEV} is not there (the made-up world is still tested)")
        return None
    if not (glob.glob(os.path.join(DEV, "geo", "*zcta*")) or os.path.exists(os.path.join(PUBLIC, "tl_2025_us_zcta520.zip"))):
        print(f"SKIP  the owner's run: no shapes in {DEV}/geo or {PUBLIC}")
        return None
    geo, runs = dash.dev_geo(PUBLIC, os.path.join(DEV, "geo")), dash.read_dev(DEV, ("pair", "load", "seat"))      # those three may be another run's
    for s, run in runs.items():
        run["load"] = sm.gap_load(s, run, {st: g.area / 1e6 for st, g in geo.states.items()})
    if not all("today" in r and "cell_today" in r for r in runs.values()):
        dash.made_up_today(geo, runs)
    return geo, runs


def sums(p, scenario, est):
    """{(state or '', channel, 07's class): $} of the exported cells of a scenario and estimate, as the page adds them."""
    c, bit, e, out = p["cells"], 1 << p["scenarios"].index(scenario), p["ests"].index(est), collections.Counter()
    for i in range(len(c["m"])):
        if c["m"][i] & bit and c["e"][i] == e:
            out[p["states"][c["s"][i]]["id"] if c["s"][i] >= 0 else "", p["channels"][c["c"][i]], p["detail"][c["j"][i]]] += c["u"][i]
    return out


# The owner's four classes (2026-11-19, #153, DATASET_LOG) over 07's seven.
FOUR = {"Uncontested": {"COVERED"}, "Contested": {"OVERLAP"}, "Transition": {"HELD BY ANOTHER", "GAP (HELD TODAY)"},
        "Open": {"GAP (UNHELD)", "OPEN SEAT HELD", "OPEN SEAT UNHELD"}}


def ties_out(p, runs):
    """The asserts of the tie-out on a payload and the tables it was built from; the number of (scenario, estimate) pairs checked."""
    four = {c["label"]: {p["detail"][j] for j in c["of"]} for c in p["classes"]}
    assert four == FOUR and list(four) == list(FOUR) and p["detail"] == [c for c, *_ in sm.GAP_CLASSES], four          # the owner's labels, in order, over 07's classes
    assert sorted(d for of in four.values() for d in of) == sorted(p["detail"]), "a class of 07 is in no class of the page, or in two"
    in_division = [s for _, divs in p["regions"] for _, codes in divs for s in codes]
    assert len(in_division) == len(set(in_division)), "a state is in two divisions"
    assert set(in_division) == {s["id"] for s in p["states"] if s["inDivision"]} == {s["id"] for s in p["states"]}, "a state on the map is in no division"
    n = 0
    for scenario in p["scenarios"]:
        summary = [dict(zip(runs[scenario]["summary"][0], r)) for r in runs[scenario]["summary"][1]]
        for est in p["ests"]:
            got = sums(p, scenario, est)
            want, states = collections.Counter(), collections.Counter()
            for r in summary:
                if r["EST_SOURCE"] == est and r["SECTION"] == "CLASS":
                    want[r["CHANNEL"], r["ITEM"]] += float(r["MM_OPP"])
                if r["EST_SOURCE"] == est and r["SECTION"] == "STATE":
                    states[r["ITEM"].split(" | ")[0].replace("(NO STATE)", ""), r["CHANNEL"], r["ITEM"].split(" | ")[1]] += float(r["MM_OPP"])
            by_class = collections.Counter()
            for (st, ch, cls), v in got.items():
                by_class[ch, cls] += v
            assert set(by_class) == set(want) and all(abs(by_class[k] - want[k]) < 1 for k in want), (scenario, est, "the classes do not add to gap_summary's CLASS rows")
            total = sum(got.values())
            assert abs(total - sum(want.values())) < 1, (scenario, est, total)
            for label, of in four.items():                          # each of the page's four classes is the sum of its 07 classes in gap_summary
                mine = sum(v for (st, ch, cls), v in got.items() if cls in of)
                assert abs(mine - sum(v for (ch, cls), v in want.items() if cls in of)) < 1, (scenario, est, label)
            assert abs(sum(sum(v for (st, ch, cls), v in got.items() if cls in of) for of in four.values()) - total) < 0.01, (scenario, est, "the four classes are not the estimate")
            if states:                                              # the run's own per-state rows: the cells sit in the states 07 says
                assert set(states) == set(got) and all(abs(states[k] - got[k]) < 1 for k in got), (scenario, est, "the states differ from gap_summary's STATE rows")
            by_state = collections.Counter()
            for (st, ch, cls), v in got.items():
                by_state[st] += v
            conus = 0.0
            for region, divs in p["regions"]:
                of_divs = [sum(by_state[s] for s in codes) for _, codes in divs]
                of_region = sum(by_state[s] for _, codes in divs for s in codes)
                assert abs(of_region - sum(of_divs)) < 0.01, (scenario, est, region)          # a region = its divisions = its states
                conus += of_region
            assert abs(conus - sum(v for s, v in by_state.items() if s)) < 0.01 and abs(conus + by_state[""] - total) < 0.01, (scenario, est, "CONUS + no state is not the estimate")
            tc, bit, e = p["tc"], 1 << p["scenarios"].index(scenario), p["ests"].index(est)          # today's cells: the same estimate, state by state
            now = collections.Counter()
            for i in range(len(tc["m"])):
                if tc["m"][i] & bit and tc["e"][i] == e:
                    now[p["states"][tc["s"][i]]["id"] if tc["s"][i] >= 0 else ""] += tc["u"][i]
            if tc["m"]:
                assert set(now) == set(by_state) and all(abs(now[s] - by_state[s]) < 1 for s in by_state), (scenario, est, "today's cells are not the assignment's, state by state")
            n += 1
    return n


def payload_of(text):
    return json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', text, re.S).group(1))


def write_run(d, runs):
    """The CSVs a run writes for `runs` into folder `d`, with scenario_maps.main's own writers."""
    sm.write_gap_csvs(d, runs)
    for kind in ("seat", "plan", *sm.TODAY_FILES):
        sm.write_dedup_csv(os.path.join(d, dash.KINDS[kind]), {s: r[kind] for s, r in runs.items()})


def today_covers_every_piece(p, runs, geo=None):
    """Asserts: for each firm and channel the page gives a holder to exactly the ZIPs with a territory piece, the holders the pieces
    name; a ZIP with a piece and a shape is one of the drawn ZIPs, and every drawn ZIP gets a colour (its holder's, or "no one").
    A line for the log."""
    want = collections.defaultdict(set)
    for run in runs.values():
        cols = [c.upper() for c in run["today"][0]]
        for r in run["today"][1]:
            r = dict(zip(cols, r))
            want[r["SOURCE"], r["TERR_CHANNEL"], str(r["ZIP_CODE"])].add(r["HOLDER"])
    got, drawn, zix = {}, len(p["zipGeom"]), {z: i for i, z in enumerate(p["zips"])}
    for name, h in p["today"]["h"].items():
        assert len(h) == len(p["zips"]), name
        for i, si in enumerate(h):
            if si >= 0:
                got[(*name.split("|"), p["zips"][i])] = {p["keys"][k] for k in p["sets"][si]}
    assert got == dict(want) and want, "the page's holders today are not the territory pieces'"
    assert sorted(p["today"]["h"]) == sorted(f"{f}|{c}" for f in p["today"]["firms"] for c in p["today"]["chans"]) and p["today"]["chans"] == ["WH", "FI"]
    if geo is not None:
        assert all(zix[z] < drawn for _, _, z in want if z in geo.zips) and all(zix[z] >= drawn for _, _, z in want if z not in geo.zips)
    held = {name: sum(1 for i in range(drawn) if h[i] >= 0) for name, h in p["today"]["h"].items()}
    return f"{len(want):,} pieces on {len({z for _, _, z in want}):,} ZIPs; of the {drawn:,} drawn ZIPs, held: {held}"


def test_the_exported_cells_tie_out_class_by_class_and_region_by_region():
    runs = fake_runs()
    with built(runs) as (_, p, _):
        assert ties_out(p, runs) == 4
        got = sums(p, "S1", "CRBG")
        assert sum(got.values()) == sum(r[3] for r in BASE) and got["", "OPEN", "OPEN SEAT UNHELD"] == 2e6          # the cell with no state is in the estimate
        west = sum(v for (st, _, _), v in got.items() if st in ("CA", "OR", "NV"))
        assert [r for r, _ in p["regions"]] == ["Northeast", "West"] and west == 255.25e6, (p["regions"], west)
        assert p["zips"][len(p["zipGeom"]):] == ["99999"] and len(p["zipGeom"]) == 10         # the ZIP with no shape is in the totals, not on the map; 93002 has a piece and no cell
        try:
            ties_out(p, fake_runs(summary_off=5.0))                # a summary that is $5 off is caught
            raise AssertionError("a summary $5 off tied out")
        except AssertionError as e:
            assert "CLASS rows" in str(e), e


def test_the_owners_run_ties_out_is_under_the_size_bound_and_builds_the_same_twice():
    got = dev_runs()
    if got is None:
        return
    geo, runs = got
    with built(runs, geo=geo) as (text, p, path), built(runs, geo=geo) as (again, _, _):
        assert ties_out(p, runs) == len(p["scenarios"]) * len(p["ests"]) >= 2
        size = os.path.getsize(path)
        print(f"      the owner's run: {size / 2 ** 20:.2f} MB, {len(p['zipGeom']):,} ZIPs drawn, {len(p['cells']['m']):,} cell rows for {len(p['scenarios'])} scenarios")
        assert size <= 25 * 1024 * 1024 == dash.MAX_BYTES, size
        assert text == again
        assert p["names"] == {} and all(re.fullmatch(r"R\d+", k) for k in p["keys"])
        assert all(re.fullmatch(r"[A-Z]{2}: R\d+ \((CRBG|EQH)\) (national|regional|WH)(, R\d+ \((CRBG|EQH)\) (national|regional|WH))*( · [A-Z]{2}: .*)?", v) for v in p["labels"].values()), p["labels"]
        covered = today_covers_every_piece(p, runs)                # the today views: every ZIP with a piece, and every shape when the territories cover the country
        print(f"      today: {covered}")
        assert URL.findall(text.replace(licence_of(text), "").replace(library_of(text), "")) == []


def test_shared_rows_are_exported_once_with_the_scenarios_that_have_them():
    with built() as (_, p, _):
        c = p["cells"]
        masks = collections.Counter(c["m"])
        assert masks == {3: 2 * (len(BASE) - 1), 1: 2, 2: 2}, masks              # every cell but Oregon's is shared by S1 and S2
        assert all(sum(1 for m in c["m"] if m & bit) == 2 * len(BASE) for bit in (1, 2))
    assert dash.merged({"A": [("x",), ("x",), ("y",)], "B": [("x",), ("z",)]}) == [(3, ("x",)), (1, ("x",)), (1, ("y",)), (2, ("z",))]   # twice in A: kept twice


def test_no_names_in_dev_mode_and_names_only_from_the_caller():
    with built() as (text, p, _):
        assert p["names"] == {} and p["keys"] == ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"]
        assert not any(n in text or n.split()[1] in text for n in NAMES.values())
        assert p["labels"] == {"S1": "no state: R5 (EQH) WH", "S2": "NV: R5 (EQH) WH"}          # a scenario is told by what differs, by key
    with built(names=NAMES | {"R99": "Not In The Run"}) as (text, p, _):
        assert p["names"] == NAMES and all(n in text for n in NAMES.values()) and "Not In The Run" not in text
        assert p["labels"]["S2"] == "NV: Ed Qelmz (EQH) WH"                                      # and by name only when the caller gave names
    with built(names={"R1": "</script><b>Ann"}) as (text, p, _):                  # a name cannot close the data's <script>
        assert p["names"] == {"R1": "</script><b>Ann"} and "</script><b>Ann" not in text


def test_the_today_views_cover_every_zip_that_has_a_piece():
    runs, geo = fake_runs(), fake_geo()
    with built(runs, geo=geo) as (_, p, _):
        today_covers_every_piece(p, runs, geo)
        h = {name: [p["zips"][i] for i, si in enumerate(hs) if si >= 0] for name, hs in p["today"]["h"].items()}
        assert h["CRBG|FI"] == ["90001", "90002", "92001", "92002", "93001"] and "99999" in h["EQH|FI"] and len(h["EQH|WH"]) == 3, h
        both = p["sets"][p["today"]["h"]["EQH|WH"][p["zips"].index("91002")]]
        assert [p["keys"][k] for k in both] == ["R2", "R5"]                                          # a ZIP with two holders keeps both
        assert [p["states"][s]["id"] if s >= 0 else "" for s in p["zst"]] == ["CA", "CA", "OR", "OR", "NV", "NV", "NY", "NY", "NJ", "NJ", "NJ"], p["zst"]   # 94002: its cell has no state, its territory piece says New Jersey
        roster = {(p["scenarios"][i], p["keys"][k]): (src, kept, role) for m, k, src, kept, role in p["roster"] for i in range(2) if m >> i & 1}
        assert roster["S1", "R7"] == ("CRBG", "N", "") and roster["S2", "R4"] == ("CRBG", "Y", "WH") and len(roster) == 2 * 8, roster
        assert p["plan"] == [[3, e, "NV", "READD", p["keys"].index("R7")] for e in (0, 1)]          # seat plan 1 only
        tc = collections.Counter()
        for i in range(len(p["tc"]["m"])):
            if p["tc"]["m"][i] & 1 and p["tc"]["e"][i] == 0:
                tc[p["tc"]["c"][i]] += p["tc"]["u"][i]
        assert tc == {0: 10e6, 1: 320.25e6, -1: 60e6}, tc                                            # WH, FI, and New York's 93001 in neither (IFA today)


def test_the_sales_are_in_the_page_and_in_no_csv():
    runs = fake_runs()
    with tempfile.TemporaryDirectory() as d:
        write_run(d, runs)
        dash.build(fake_geo(), runs, os.path.join(d, "dashboard.html"), NAMES, sales=SALES)
        texts = {f: open(os.path.join(d, f), encoding="utf-8").read() for f in os.listdir(d)}
        assert sorted(texts) == sorted([*dash.KINDS.values(), "dashboard.html"])                     # every file a run sends, and the page
        assert [f for f, x in texts.items() if str(int(SALE)) in x] == ["dashboard.html"]
        assert not any(re.search("SALE|AMT|AMOUNT", texts[f].splitlines()[0], re.I) for f in texts if f.endswith(".csv"))
        p = payload_of(texts["dashboard.html"])
        got = [(p["keys"][k], p["zips"][z], v) for k, z, v in zip(p["sales"]["k"], p["sales"]["z"], p["sales"]["v"])]
        assert got == [("R1", "90001", 7654321), ("R1", "91001", 5000), ("R2", "90002", 250), ("R6", "93001", -20), ("R6", "99999", 40), ("R7", "92001", 300)], got
        assert p["salesNoKey"] == 7                                                                  # a seller with no key is in no person's row, and is said
        assert set(dash.read_dev(d)["S1"]) == set(dash.KINDS)                                        # a run folder read back has no sales: dev makes them up
    with built(sales=None) as (text, p, _):
        assert p["sales"] == {"k": [], "z": [], "v": []} and str(int(SALE)) not in text


def test_the_dev_command_reads_a_run_folder_and_writes_keys_only():
    keep = dash.dev_geo
    dash.dev_geo = lambda public, cache: fake_geo()

    def dev(d, *more):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            assert dash.main(["--dev", d, "--out", os.path.join(d, "out.html"), "--products", "excluding FIXED", *more]) == 0
        text = open(os.path.join(d, "out.html"), encoding="utf-8").read()
        return buf.getvalue(), text, payload_of(text)
    try:
        with tempfile.TemporaryDirectory() as d:                   # a folder from before the today views: the gap files and seat_fit.csv
            sm.write_gap_csvs(d, fake_runs())
            sm.write_dedup_csv(os.path.join(d, "seat_fit.csv"), {s: r["seat"] for s, r in fake_runs().items()})
            runs = dash.read_dev(d)
            assert list(runs) == ["S1", "S2"] and {k: len(v[1]) for k, v in runs["S1"].items()}["cell"] == 2 * len(BASE)
            out, text, p = dev(d)
            assert "keys only (no names)" in out and p["names"] == {} and p["products"] == "excluding FIXED"
            assert "MADE-UP, not the run's: today's territories, 2025 sales" in out and p["madeUp"] == ["today's territories", "2025 sales"]
            assert all(re.fullmatch(r"R\d+", k) for k in p["keys"]) and not any(n in text or n.split()[1] in text for n in NAMES.values())
            assert ties_out(p, {s: {"summary": r["summary"]} for s, r in fake_runs().items()}) == 4          # a CSV round trip changes no dollar
            drawn = len(p["zipGeom"])
            assert drawn == 10 and all(any(h[i] >= 0 for h in p["today"]["h"].values()) for i in range(drawn))   # made-up territories: every shape is someone's in a firm
            assert dev(d)[1] == text                                 # the made-up parts are the same every time
            assert p["has"] == {"pair": True, "load": True, "plan": False, "today": True} and not dev(d, "--without", "pair", "load")[2]["has"]["pair"]
            os.remove(os.path.join(d, "gap_pair.csv"))
            try:
                dash.read_dev(d)
                raise AssertionError("a run folder with no gap_pair.csv was read")
            except SystemExit as e:
                assert "gap_pair.csv" in str(e), e
        with tempfile.TemporaryDirectory() as d, built() as (_, direct, _):      # a folder with the run's own territory files: only the sales are made up
            write_run(d, fake_runs())
            out, text, p = dev(d)
            assert p["madeUp"] == ["2025 sales"] and "today's territories" not in out and p["today"] == direct["today"] and p["tc"] == direct["tc"] and p["plan"] == direct["plan"]
            today_covers_every_piece(p, fake_runs(), fake_geo())
    finally:
        dash.dev_geo = keep
    a, b = fake_runs(), fake_runs()                                # made_up_today and made_up_sales: the same for the same run
    for runs in (a, b):
        for r in runs.values():
            del r["today"], r["cell_today"]
        dash.made_up_today(fake_geo(), runs)
    assert a == b and dash.made_up_sales(a) == dash.made_up_sales(b) and dash.made_up_sales(a, seed=1) != dash.made_up_sales(a)
    assert all(re.fullmatch(r"R\d+|", k) for k, _, _ in dash.made_up_sales(a))


def licence_of(text):
    return re.search(r'<script type="text/plain" id="licence">(.*?)</script>', text, re.S).group(1)


# The npm tarball maplibre-gl-6.19.0.tgz (sha512-3bOrnfddggUYudLGJFsYFvqulUyvSxy4iQzd/uURI7ZhgYEZifdSrECujRSghaCpc+v/ZsFI0Y6ZsGSilEtE+w==,
# `npm view maplibre-gl@6.19.0 dist.integrity`, checked on 2026-11-19): its files' sha256.  6.x ships ES modules only: no maplibre-gl.js.
VENDORED_SHA256 = {"LICENSE.txt": "ee5fc05a0677eaf69601d2c7db0d9ecd6cc27c3abc1d0733bc9ed34707cf8ef2",
                   "maplibre-gl.mjs": "01590c9875ea5bb0e8cdc534479f607f7d1695ca5debbccaf730edf5fa5f39e5",
                   "maplibre-gl-worker.mjs": "c8564c4a4147326a587c9cc4c2a871c4b02a6c37c3f1ea51da55be3220d4b112",
                   "maplibre-gl.css": "a90798a1953017790e590f7e1bd35ff103a8a4263972cb47290b78adf86f8c20"}
# Every http(s) address in the vendored library: XML namespaces, links in its own messages and licence header, a placeholder base.
# None is asked for when the page runs (the Chromium test below counts the requests).
VENDORED_URLS = {"http://www.w3.org/2000/svg", "http://www.w3.org/1999/xhtml", "https://maplibre.org/", "https://maplibre.invalid/",
                 "https://wiki.openstreetmap.org/wiki/This_map_requires_WebGL", "https://github.com/maplibre/maplibre-gl-js/blob/v6.19.0/LICENSE.txt",
                 "https://github.com/mapbox/mapbox-gl-js/issues/2907"}


def library_of(text):
    """The inline module script that is the vendored library (the one before the page's own)."""
    return re.search(r'<script type="module">\n(/\*\*\n\* MapLibre GL JS\n.*?)</script>', text, re.S).group(1)


def test_the_page_has_no_url_outside_the_vendored_library_and_licence_and_embeds_the_library_untouched():
    with built(names=NAMES) as (text, p, _):
        licence, lib = licence_of(text), library_of(text)
        assert licence == open(os.path.join(dash.VENDOR, "LICENSE.txt"), encoding="utf-8").read() and "Redistribution" in licence
        ours = text.replace(licence, "").replace(lib, "")
        assert len(ours) == len(text) - len(licence) - len(lib) and URL.findall(ours) == [], URL.findall(ours)[:5]
        assert not re.search(r"<(script|link|img|iframe)[^>]*\s(src|href)\s*=", text, re.I) and "@import" not in ours and "url(" not in ours
        assert "import(" not in ours and not re.search(r"^\s*import\s", ours, re.M)          # nothing is imported: no blob: module (owner's bug, 2026-11-19)
        # the library is its file's code, character for character, up to the closing export{...}; that became the page's global with the same names
        raw = open(os.path.join(dash.VENDOR, dash.LIBRARY), encoding="utf-8").read()
        code, _, tail = raw.rpartition("export{")
        names = [x.split(" as ") for x in tail.split("}")[0].split(",")]
        assert lib.startswith(code) and lib[len(code):] == "globalThis.maplibregl={" + ",".join(f"{pub}:{loc}" for loc, pub in names) + "};\n\n"
        assert {"Map", "NavigationControl", "setWorkerUrl"} <= {pub for _, pub in names} and len(names) > 50 and tail.split("}", 1)[1].strip() == "};\n//# sourceMappingURL=maplibre-gl.mjs.map"[1:]
        assert set(URL.findall(raw)) <= VENDORED_URLS, sorted(set(URL.findall(raw)) - VENDORED_URLS)
        for el, name in dash.VENDORED.items():                     # the worker and the stylesheet are in the page gzip + base64
            blob = re.search(rf'<script type="text/plain" id="{el}">([A-Za-z0-9+/=]+)</script>', text).group(1)
            raw = open(os.path.join(dash.VENDOR, name), "rb").read()
            if el == "v-worker":                                   # as a classic script: the file's code up to its closing export, in a strict function
                raw = b'(function(){"use strict";' + raw[:raw.rindex(b"export{")] + b"})();\n"
                assert raw.count(b"export{") == 0 and b"import.meta" not in raw          # nothing a classic script cannot hold
            assert gzip.decompress(base64.b64decode(blob)) == raw, name
            assert set(URL.findall(raw.decode("utf-8"))) <= VENDORED_URLS, sorted(set(URL.findall(raw.decode("utf-8"))) - VENDORED_URLS)
    for name, sha in VENDORED_SHA256.items():
        assert hashlib.sha256(open(os.path.join(dash.VENDOR, name), "rb").read()).hexdigest() == sha, f"{name} is not the npm tarball's file"
    assert sorted(os.listdir(dash.VENDOR)) == sorted(VENDORED_SHA256)


def test_the_page_is_under_the_size_bound_and_a_page_over_it_is_refused():
    keep = dash.MAX_BYTES
    with built() as (text, _, path):
        assert os.path.getsize(path) < dash.MAX_BYTES == 25 * 1024 * 1024
    try:
        dash.MAX_BYTES = 1000
        with built():
            raise AssertionError("a page over the bound was written")
    except SystemExit as e:
        assert "over the" in str(e), e
    finally:
        dash.MAX_BYTES = keep


def test_the_build_is_the_same_bytes_every_time():
    with built(names=NAMES) as (a, _, _), built(names=NAMES) as (b, _, _):
        assert a == b and hashlib.sha256(a.encode()).hexdigest() == hashlib.sha256(b.encode()).hexdigest()
    with built(runs=dict(reversed(list(fake_runs().items())))) as (c, p, _):          # the scenarios keep the order they were given in
        assert p["scenarios"] == ["S2", "S1"] and c != a


def test_a_shape_is_stored_as_integer_steps_and_comes_back_to_11_m():
    ring = lambda a: [(sum(a[0:i + 2:2]) / dash.Q, sum(a[1:i + 2:2]) / dash.Q) for i in range(0, len(a), 2)]          # dashboard.js's `ring`, without the closing point
    outer = [(-100.00004, 40.0), (-99.5, 40.0), (-99.5, 40.25), (-100.0, 40.25)]
    hole, speck = [(-99.9, 40.1), (-99.8, 40.1), (-99.8, 40.2)], [(-99.70001, 40.10001), (-99.70002, 40.10001), (-99.70002, 40.10002)]
    enc = dash.encode(Polygon(outer, [hole, speck]))
    assert len(enc) == 1 and len(enc[0]) == 2 and all(isinstance(v, int) for r in enc[0] for v in r)          # the speck rounds to one point: dropped
    assert ring(enc[0][0]) == [(-100.0, 40.0), (-99.5, 40.0), (-99.5, 40.25), (-100.0, 40.25)] and ring(enc[0][1]) == hole
    tiny = dash.encode(box(-99.000001, 40.000001, -99.000002, 40.000002))          # a shape under 11 m: a square to point at, not nothing
    assert len(tiny) == 1 and len(ring(tiny[0][0])) == 4 and ring(tiny[0][0])[0] == (-99.0001, 39.9999)
    with built() as (_, p, _):
        ca = next(s for s in p["states"] if s["id"] == "CA")
        w, s, e, n = ca["box"]
        assert -125 < w < e < -110 and 30 < s < n < 45 and len(ca["g"][0][0]) == 8 and w <= ca["pt"][0] <= e          # EPSG:5070 box -> lon/lat, 4 corners


def test_touching_people_of_a_role_wear_different_colours():
    with built() as (_, p, _):
        colour = dict(zip(p["keys"], p["colour"]))
        assert colour["R1"] != colour["R2"] and set(p["colour"]) <= set(dash.PEOPLE_COLOURS)          # R1 and R2 share California
        today = dict(zip(p["keys"], p["tcolour"]))
        assert today["R1"] != today["R3"] and today["R2"] != today["R5"] and set(p["tcolour"]) <= set(dash.PEOPLE_COLOURS)   # holders of one firm in one state
        assert [c["color"] for c in p["classes"]] == ["#C9C9F5", "#C053EF", "#4F00CA", "#EC602F"]     # quiet to loud: a Violet tint, Orchid, Violet, Dark Orange
        assert [s["label"] for s in p["status"]] == ["On the roster", "Proposed", "Not on the roster", "No one"] and len({s["color"] for s in p["status"]}) == 4


def test_the_census_regions_and_divisions_are_tigers():
    path = os.path.join(PUBLIC, "tl_2025_us_state.zip")
    if not os.path.exists(path):
        print(f"SKIP  the census regions against TIGER/Line: {path} is not there")
        return
    import geopandas as gpd
    st = gpd.read_file("zip://" + path, engine="pyogrio", ignore_geometry=True)
    st = st[st["STATEFP"].isin(sm.STATE_ABBR)]
    want = {r["STUSPS"]: (int(r["REGION"]), int(r["DIVISION"])) for _, r in st.iterrows()}
    got, d = {}, 0
    for ri, (_, divs) in enumerate(dash.REGIONS, 1):
        for _, codes in divs:
            d += 1
            got.update({s: (ri, d) for s in codes.split()})
    assert got == want and len(got) == 49 and set(got) == set(dash.STATE_NAME) == set(sm.STATE_ABBR.values())
    assert {r["STUSPS"]: r["NAME"] for _, r in st.iterrows()} == dash.STATE_NAME


def chromium():
    """(node, the shot script), or None with a SKIP line when there is no node or no browser."""
    node = shutil.which("node")
    shot = str(ROOT / "tools" / "maps" / "dashboard_shot.mjs")
    if not node or subprocess.run([node, shot, "--which"], capture_output=True).returncode != 0:
        print("SKIP  the page in headless Chromium: no node, or no browser (set TD_CHROME)")
        return None
    return node, shot


def in_chromium(path, *steps):
    """The `dump:` values of the steps run on the page at `path`; the page threw nothing and asked for nothing that is not local."""
    node, shot = chromium()
    r = subprocess.run([node, shot, path, "-", "--size=1400x900", *steps], capture_output=True, text=True, timeout=240)
    assert r.returncode == 0 and "EXCEPTION" not in r.stdout and "requests not local: []" in r.stdout, r.stdout + r.stderr
    return [json.loads(line[6:]) for line in r.stdout.splitlines() if line.startswith("dump: ")]


LOOK = ("--dump=({check: document.querySelector('.check').className, tie: document.querySelector('.check').textContent.trim(), screen: document.querySelector('.capsule').textContent,"
        " legend: [...document.querySelectorAll('.cl[data-go]')].map((e) => e.querySelector('span').firstChild.textContent + ' ' + e.querySelector('b').textContent),"
        " rows: document.querySelectorAll('#t-main tbody tr').length, card: document.querySelector('#card').hidden ? '' : document.querySelector('#card').textContent,"
        " map: document.querySelector('#map canvas') !== null, title: document.title, zips: document.body.dataset.zips, lit: document.body.dataset.lit,"
        " est: document.querySelector('#c-est [aria-pressed=true]').textContent, hash: location.hash,"
        " n: Object.fromEntries(['total', 'ch', 'st'].map((k) => [k, [...document.querySelectorAll(`[data-n=${k}]`)].map((e) => +e.textContent)]))})")


def test_the_page_opens_in_chromium_ties_out_and_asks_for_nothing_online():
    if chromium() is None:
        return
    with built(names=NAMES) as (_, p, path):
        first, pairs, west = in_chromium(path, LOOK, "--hash=tab=pairs", LOOK, "--hash=focus=West&ch=REGIONAL&est=EQH&sc=S2&sel=R1-R2&tab=pairs", LOOK)
        assert (first["check"], first["tie"], first["screen"]) == ("check", "✓Ties to the run’s CRBG summary: $390.3MM, class by class, and pair by pair.", "$388.3MM"), first   # $2.0MM has no state
        assert first["legend"] == ["Uncontested $233.0MM", "Contested $50.0MM", "Transition $30.0MM", "Open $75.3MM"], first["legend"]      # the four classes, quiet to loud
        assert (first["rows"], first["card"], first["map"], first["title"], first["zips"]) == (7, "", True, "Territory coverage: CONUS, S1", "8"), first   # 6 on the sheet and plan 1's re-add; 8 ZIPs have a shape and a cell with a state
        assert pairs["rows"] == 1 and pairs["hash"] == "#tab=pairs", pairs                           # one contested pair
        got = sums(p, "S2", "EQH")
        regional_west = sum(v for (st, ch, _), v in got.items() if st in ("CA", "OR", "NV") and ch == "REGIONAL")
        assert west["screen"] == f"${regional_west / 1e6:.1f}MM" == "$162.2MM" and west["rows"] == 1 and "contested" in west["card"], west
        assert west["legend"] == ["Uncontested $117.2MM", "Contested $45.0MM"], west["legend"]       # S2: Oregon is covered; a class with $0 on screen is not listed
    with built(fake_runs(summary_off=5.0)) as (_, _, path):
        (bad,) = in_chromium(path, LOOK)
        assert bad["check"] == "check bad" and bad["tie"].startswith("Does not tie to the run’s summary."), bad


def test_the_today_views_the_counts_and_the_zips_with_sales_in_chromium():
    """The today views colour every drawn ZIP and tie to the same estimate; the counts strip adds up (total = by channel = by
    status) in each view and focus; "ZIPs with sales" keeps a ZIP only where its covering person sold above $0."""
    if chromium() is None:
        return
    with built(names=NAMES) as (_, p, path):
        new, crbg, eqh, sold, one, assigned = in_chromium(path, LOOK, "--hash=of=CRBG", LOOK, "--hash=of=EQH&tch=FI&focus=Pacific", LOOK, "--hash=of=CRBG&sold=1", LOOK,
                                                          "--hash=of=CRBG&sold=1&sel=R1", LOOK, "--hash=ch=REGIONAL&sold=1", LOOK)
    for got in (new, crbg, eqh, sold, one, assigned):               # the counts add up, whatever the view and focus
        assert got["n"]["total"] == [sum(got["n"]["ch"])] == [sum(got["n"]["st"])] and len(got["n"]["st"]) == 3, got["n"]
        assert got["check"] == "check" and got["map"], got
    assert new["n"] == {"total": [7], "ch": [1, 2, 3, 1], "st": [6, 1, 0]}, new["n"]                 # national, WH, regional, for an open seat; on the roster, proposed, not
    # CRBG today, WH: R1 and R4 are on the roster, plan 1 brings R7 back, four drawn ZIPs have no CRBG WH territory; only Oregon's 91002 is WH opportunity today
    assert crbg["zips"] == str(len(p["zipGeom"])) == "10" and crbg["screen"] == "$10.0MM" and crbg["est"] == "CRBG" and crbg["hash"] == "#of=CRBG", crbg
    assert crbg["legend"] == ["On the roster $10.0MM", "Proposed $0", "No one $0"] and crbg["tie"].startswith("✓Ties to the preliminary assignment: the same $390.3MM"), crbg
    assert crbg["n"] == {"total": [4], "ch": [1, 1, 2], "st": [3, 1, 0]} and crbg["rows"] == 3, crbg      # WH only R4, FI only R3, both R1 and R7; three hold WH
    # EQH today, FI, Pacific: the estimate is the firm's own unless chosen; R2 holds both channels there, R5 WH only
    assert eqh["est"] == "EQH" and eqh["hash"] == "#of=EQH&tch=FI&focus=Pacific" and eqh["screen"] == "$180.2MM", eqh
    assert eqh["n"] == {"total": [2], "ch": [1, 0, 1], "st": [2, 0, 0]} and eqh["rows"] == 1 and eqh["title"] == "Territory coverage: Pacific, EQH today", eqh
    # ZIPs with sales: R1 sold in 90001 and R7 in 92001 (R4's $0 in 91001 is no sale); R1 alone: 90001 of their two ZIPs, their Oregon sale is outside
    assert (sold["lit"], one["lit"], new["lit"]) == ("2", "1", "") and "Outside it$5K" in one["card"] and "In the ZIPs they hold in WH$7.7MM" in one["card"], (sold, one)
    assert assigned["lit"] == "2", assigned                         # the assignment: 90001 (R1) and 90002 (R2); R1's Oregon sale is not where R1 is assigned


CSP = "<meta http-equiv=\"Content-Security-Policy\" content=\"script-src 'unsafe-inline'; worker-src {}\">"


def test_the_map_starts_under_a_policy_that_refuses_blob_imports_and_says_what_to_do_when_it_cannot():
    """Owner's bug, 2026-11-19: a stakeholder's viewer refused v1's dynamic import of a blob: URL ("failed to fetch dynamically imported
    module").  The page imports nothing now: under a policy with inline scripts and blob: workers only, the map starts; with no worker
    allowed at all it says what to do, in the map's place, and does not wait for ever (every run here has a timeout)."""
    if chromium() is None:
        return
    node, shot = chromium()
    look = "--dump=[document.body.dataset.map, document.querySelector('#map canvas') !== null, (document.querySelector('.nomap') || {}).textContent || '', document.querySelector('.capsule').textContent]"
    with built(names=NAMES) as (text, _, path):
        got = {}
        for name, policy in (("none", None), ("blob workers", "blob:"), ("no workers", "'none'")):
            copy = os.path.join(os.path.dirname(path), "copy.html")
            with open(copy, "w", encoding="utf-8") as f:
                f.write(text if policy is None else text.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + CSP.format(policy), 1))
            r = subprocess.run([node, shot, copy, "-", "--size=1400x900", look], capture_output=True, text=True, timeout=120)
            assert "requests not local: []" in r.stdout and "TIMED OUT" not in r.stdout, (name, r.stdout + r.stderr)
            got[name] = json.loads(next(line[6:] for line in r.stdout.splitlines() if line.startswith("dump: ")))
    assert got["none"] == ["idle", True, "", "$388.3MM"] == got["blob workers"], got          # the map draws with no policy and under the sandbox's
    state, canvas, said, total = got["no workers"]
    assert state == "failed" and not canvas and total == "$388.3MM", got["no workers"]          # the totals are there without the map
    assert "The map could not start here." in said and "Save the file, then open it in Chrome or Edge (not in a Teams or email preview)." in said, said


def test_a_state_assigned_in_a_channel_with_no_cell_there_still_shows_its_person():
    """Review of #153: assignments come from the people's roles and states, not the cells.  R3 (NATIONAL) is assigned CA and NV;
    NV has no NATIONAL cell, yet NV's state card (focus=NV) names R3 for National."""
    if chromium() is None:
        return
    node, shot = chromium()
    global ROSTER
    keep = ROSTER
    ROSTER = [(k, s, r, "CA NV" if k == "R3" else st) for k, s, r, st in keep]
    try:
        with built(names=NAMES) as (_, _, path):
            r = subprocess.run([node, shot, path, "-", "--size=1400x900", "--hash=focus=NV",
                                "--dump=document.querySelector('#detail').textContent"], capture_output=True, text=True, timeout=180)
    finally:
        ROSTER = keep
    assert r.returncode == 0, r.stdout + r.stderr
    card = json.loads(next(l[6:] for l in r.stdout.splitlines() if l.startswith("dump: ")))
    flat = " ".join(card.split())
    assert "National R3 Cy Qcedarz" in flat.replace("NationalR3", "National R3") or "NationalR3 Cy Qcedarz" in flat, flat
