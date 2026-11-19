"""tools/maps/dashboard.py (issue #153): the run's dashboard, built from a made-up world (5 box states in 2 census regions and 3
divisions, 2 ZIPs each, 2 scenarios, 2 estimates, keys R1..R6, no Snowflake) and, when $TD_REPO/data/safe/dev_dashboard is there,
from the owner's last run (keys only).  The exported cells tie out (class by class to the run's summary; region = its divisions =
its states; fill = gap + open seat), no name is in a dev build, the page holds no http(s) URL outside the vendored licence, it is
under the size bound, the build is the same bytes every time, and in headless Chromium the page itself reports the tie-out and asks
for nothing online."""
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
NAMES = {f"R{i}": n for i, n in enumerate(("Ann Qalderz", "Bo Qbirchz", "Cy Qcedarz", "Di Qdogwoodz", "Ed Qelmz", "Flo Qfirz"), 1)}   # made up, and not words of the page
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
    person = [(scenario, est, k, src, role, states, 1e6, 1e6, 0.0, 0.0, 0.0, 0.0, 1) for est in ("CRBG", "EQH") for k, src, role, states in ROSTER]
    gap = {"cell": (CELL_COLS, cells), "pair": (PAIR_COLS, pairs), "person": (PERSON_COLS, person), "summary": (SUMMARY_COLS, summary)}
    gap["load"] = sm.gap_load(scenario, gap, {s: SIDE * SIDE / 1e6 for s in CORNER})
    gap["seat"] = (SEAT_COLS, [("SEAT", scenario, est, "NV", kind, "R1", 1, 1, 45e6, None, 0, "0.8 to 1.25" if kind == "NEIGHBOUR" else "")
                               for est in ("CRBG", "EQH") for kind in ("NEIGHBOUR", "HOLDER")])
    return gap


def fake_runs(**kw):
    return {s: fake_run(s, **kw) for s in ("S1", "S2")}


@contextlib.contextmanager
def built(runs=None, names=None, geo=None):
    """(the page's text, its payload) of a build in a temporary folder."""
    with tempfile.TemporaryDirectory() as d:
        path = dash.build(geo or fake_geo(), runs or fake_runs(), os.path.join(d, "dashboard.html"), names, "excluding FIXED", "2026-11-19-0200")
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
    return dash.dev_geo(PUBLIC, os.path.join(DEV, "geo")), dash.read_dev(DEV)


def sums(p, scenario, est):
    """{(state or '', channel, class): $} of the exported cells of a scenario and estimate, as the page adds them."""
    c, bit, e, out = p["cells"], 1 << p["scenarios"].index(scenario), p["ests"].index(est), collections.Counter()
    for i in range(len(c["m"])):
        if c["m"][i] & bit and c["e"][i] == e:
            out[p["states"][c["s"][i]]["id"] if c["s"][i] >= 0 else "", p["channels"][c["c"][i]], p["classes"][c["k"][i]]["id"]] += c["u"][i]
    return out


def ties_out(p, runs):
    """The asserts of the tie-out on a payload and the tables it was built from; the number of (scenario, estimate) pairs checked."""
    fill = [c["id"] for c in p["classes"] if c["group"] == "fill"]
    assert set(fill) == {c for c, *_ in sm.FILL_CLASSES} == {c["id"] for c in p["classes"] if c["id"].startswith(("GAP", "OPEN SEAT"))}, fill
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
            of = lambda pred: sum(v for (st, ch, cls), v in got.items() if pred(cls))
            assert abs(of(lambda c: c in fill) - of(lambda c: c.startswith("GAP")) - of(lambda c: c.startswith("OPEN SEAT"))) < 0.01          # fill = gap + open seat
            assert abs(of(lambda c: c in fill) - sum(v for (ch, cls), v in want.items() if cls in fill)) < 1, (scenario, est, "fill")
            n += 1
    return n


def test_the_exported_cells_tie_out_class_by_class_and_region_by_region():
    runs = fake_runs()
    with built(runs) as (_, p, _):
        assert ties_out(p, runs) == 4
        got = sums(p, "S1", "CRBG")
        assert sum(got.values()) == sum(r[3] for r in BASE) and got["", "OPEN", "OPEN SEAT UNHELD"] == 2e6          # the cell with no state is in the estimate
        west = sum(v for (st, _, _), v in got.items() if st in ("CA", "OR", "NV"))
        assert [r for r, _ in p["regions"]] == ["Northeast", "West"] and west == 255.25e6, (p["regions"], west)
        assert p["zips"][len(p["zipGeom"]):] == ["99999"] and len(p["zipGeom"]) == 9          # the ZIP with no shape is in the totals, not on the map
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
        assert URL.findall(text.replace(licence_of(text), "")) == []


def test_shared_rows_are_exported_once_with_the_scenarios_that_have_them():
    with built() as (_, p, _):
        c = p["cells"]
        masks = collections.Counter(c["m"])
        assert masks == {3: 2 * (len(BASE) - 1), 1: 2, 2: 2}, masks              # every cell but Oregon's is shared by S1 and S2
        assert all(sum(1 for m in c["m"] if m & bit) == 2 * len(BASE) for bit in (1, 2))
    assert dash.merged({"A": [("x",), ("x",), ("y",)], "B": [("x",), ("z",)]}) == [(3, ("x",)), (1, ("x",)), (1, ("y",)), (2, ("z",))]   # twice in A: kept twice


def test_no_names_in_dev_mode_and_names_only_from_the_caller():
    with built() as (text, p, _):
        assert p["names"] == {} and p["keys"] == ["R1", "R2", "R3", "R4", "R5", "R6"]
        assert not any(n in text or n.split()[1] in text for n in NAMES.values())
    with built(names=NAMES | {"R99": "Not In The Run"}) as (text, p, _):
        assert p["names"] == NAMES and all(n in text for n in NAMES.values()) and "Not In The Run" not in text
    with built(names={"R1": "</script><b>Ann"}) as (text, p, _):                  # a name cannot close the data's <script>
        assert p["names"] == {"R1": "</script><b>Ann"} and "</script><b>Ann" not in text


def test_the_dev_command_reads_a_run_folder_and_writes_keys_only():
    keep = dash.dev_geo
    with tempfile.TemporaryDirectory() as d:
        sm.write_gap_csvs(d, fake_runs())
        sm.write_dedup_csv(os.path.join(d, "seat_fit.csv"), {s: r["seat"] for s, r in fake_runs().items()})
        runs = dash.read_dev(d)
        assert list(runs) == ["S1", "S2"] and {k: len(v[1]) for k, v in runs["S1"].items()}["cell"] == 2 * len(BASE)
        dash.dev_geo = lambda public, cache: fake_geo()
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                assert dash.main(["--dev", d, "--out", os.path.join(d, "out.html"), "--products", "excluding FIXED"]) == 0
        finally:
            dash.dev_geo = keep
        text = open(os.path.join(d, "out.html"), encoding="utf-8").read()
        p = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', text, re.S).group(1))
        assert "keys only (no names)" in buf.getvalue() and p["names"] == {} and p["products"] == "excluding FIXED"
        assert ties_out(p, {s: {"summary": r["summary"]} for s, r in fake_runs().items()}) == 4          # a CSV round trip changes no dollar
        os.remove(os.path.join(d, "gap_pair.csv"))
        try:
            dash.read_dev(d)
            raise AssertionError("a run folder with no gap_pair.csv was read")
        except SystemExit as e:
            assert "gap_pair.csv" in str(e), e


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


def test_the_page_has_no_url_outside_the_vendored_licence_and_embeds_the_library_untouched():
    with built(names=NAMES) as (text, p, _):
        licence = licence_of(text)
        assert licence == open(os.path.join(dash.VENDOR, "LICENSE.txt"), encoding="utf-8").read() and "Redistribution" in licence
        assert URL.findall(text.replace(licence, "")) == [], URL.findall(text.replace(licence, ""))[:5]
        assert not re.search(r"<(script|link|img|iframe)[^>]*\s(src|href)\s*=", text, re.I) and "@import" not in text and "url(" not in text.replace(licence, "")
        for el, name in dash.VENDORED.items():                     # the library is in the page byte for byte (gzip, base64)
            blob = re.search(rf'<script type="text/plain" id="{el}">([A-Za-z0-9+/=]+)</script>', text).group(1)
            raw = open(os.path.join(dash.VENDOR, name), "rb").read()
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
        assert [c["fill"] for c in p["classes"]][3:] == [c["color"] for c in p["classes"]][3:] == ["#C053EF", "#4F00CA", "#FA9454", "#EC602F"]   # the owner's fill colours
        assert [c["fill"] for c in p["classes"]][:3] == [sm.NO_FILL[1], sm.BARGAIN[1], sm.BARGAIN[1]]


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


def test_the_page_opens_in_chromium_ties_out_and_asks_for_nothing_online():
    node = shutil.which("node")
    shot = str(ROOT / "tools" / "maps" / "dashboard_shot.mjs")
    if not node or subprocess.run([node, shot, "--which"], capture_output=True).returncode != 0:
        print("SKIP  the page in headless Chromium: no node, or no browser (set TD_CHROME)")
        return
    look = ("--dump=[document.querySelector('.check').className, document.querySelector('.check').textContent.trim(), document.querySelector('.capsule').textContent,"
            " document.querySelectorAll('#t-pairs tbody tr').length, document.querySelectorAll('#t-fill tbody tr').length, document.querySelector('#card').hidden,"
            " document.querySelector('#map canvas') !== null, document.title]")

    def run(path, *steps):
        r = subprocess.run([node, shot, path, "-", "--size=1400x900", *steps], capture_output=True, text=True, timeout=180)
        assert r.returncode == 0 and "EXCEPTION" not in r.stdout and "requests not local: []" in r.stdout, r.stdout + r.stderr
        return [json.loads(line[6:]) for line in r.stdout.splitlines() if line.startswith("dump: ")]
    with built(names=NAMES) as (_, p, path):
        west = "--hash=focus=West&ch=REGIONAL&est=EQH&sc=S2&sel=R1-R2"
        first, second = run(path, look, west, look)
        assert first[:3] == ["check", "✓Ties to the run’s CRBG summary: $390.3MM in S1, class by class, and pair by pair.", "$388.3MM"], first   # $2.0MM has no state
        assert first[3:] == [1, 3, True, True, "Territory coverage: CONUS, S1"], first              # 1 pair; CA, OR and NV to fill; no card; a map
        got = sums(p, "S2", "EQH")
        regional_west = sum(v for (st, ch, _), v in got.items() if st in ("CA", "OR", "NV") and ch == "REGIONAL")
        assert second[2] == f"${regional_west / 1e6:.1f}MM" == "$162.2MM" and second[3:6] == [1, 0, False], second   # S2: Oregon covered, nothing to fill; the pair's card
    with built(fake_runs(summary_off=5.0)) as (_, _, path):
        (bad,) = run(path, look)
        assert bad[0] == "check bad" and bad[1].startswith("Does not tie to the run’s summary."), bad


def test_a_state_assigned_in_a_channel_with_no_cell_there_still_shows_its_person():
    """Review of #153: assignments come from the people's roles and states, not the cells.  R3 (NATIONAL) is assigned CA and NV;
    NV has no NATIONAL cell, yet NV's state card (focus=NV) names R3 for National."""
    node = shutil.which("node")
    shot = str(ROOT / "tools" / "maps" / "dashboard_shot.mjs")
    if not node or subprocess.run([node, shot, "--which"], capture_output=True).returncode != 0:
        print("SKIP  the page in headless Chromium: no node, or no browser (set TD_CHROME)")
        return
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
