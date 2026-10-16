"""The night drivers' small tools (tools/exp/contig): state_extract.py writes no sales data, the
IFA index's pass verdict, warm.py's extracts and stage cleanup, the regional shell scripts."""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import sys
import tempfile
import types

from td import audit, data, geo

HERE = os.path.dirname(os.path.abspath(__file__))
CONTIG = os.path.join(HERE, "..", "tools", "exp", "contig")


def _import(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(CONTIG, file))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


state_extract = _import("contig_state_extract", "state_extract.py")


# ------------------------------------------------------------------------------ B1: masking
def _sales_extract() -> data.Extract:
    return data.Extract(("IFA",), ["10001", "10002", "20001"], ["IFA"] * 3, [1.0, 2.0, 3.0],
                        [{"R1": 0.4, "R2": 0.6}, {"R1": 1.0}, {"R2": 0.5}], [0.1, 0.2, 0.3],
                        {"R1": "F1", "R2": "F2"}, {"source": "toy"})


def test_a_state_extract_carries_no_rep_shares_share_free_or_firm_map():
    ref = {"zcta": ["10001", "10002", "20001"], "state": ["NY", "NY", "DC"]}
    real = geo.read_reference
    geo.read_reference = lambda *a, **k: ref
    try:
        with tempfile.TemporaryDirectory() as tmp:
            base, out = os.path.join(tmp, "base.json.gz"), os.path.join(tmp, "x", "ny.json.gz")
            data.write(_sales_extract(), base)
            assert data.load(base).firm and any(data.load(base).share)       # the source does carry them
            assert state_extract.main([out, "NY", "--base", base]) == 0
            got = data.load(out)
    finally:
        geo.read_reference = real
    assert got.z == ["10001", "10002"] and got.m_rel == [1.0, 2.0]           # the model's column is kept
    assert got.share == [{}, {}] and got.share_free == [0.0, 0.0] and got.firm == {}


# ------------------------------------------------------------------------------ C1, C2: the IFA index
ifa_index = _import("contig_ifa_index_night", "ifa_index_night.py")
score = ifa_index.check_gate().score

# 10001 is New York County (36061); 10002 is not (a Bronx stand-in); the rest are elsewhere
REF = {"zcta": ["10001", "10002", "20001", "20002", "30001", "30002", "30003", "40001"],
       "county": ["36061", "36005", "11111", "11111", "22222", "22222", "22222", "33333"]}
MANHATTAN = ifa_index.manhattan_zips(REF)


def _toy_geo() -> "score.Geography":
    """Chains 10001-10002-20001-20002, 30001-30002-30003-40001, every border 30 km (no neck)."""
    state = {"10001": "NY", "10002": "NY", "20001": "B", "20002": "B", "30001": "C", "30002": "C",
             "30003": "C", "40001": "D"}
    xy = {z: (float(i), 0.0) for i, z in enumerate(sorted(state))}
    edge = {z: {} for z in state}
    for a, b in (("10001", "10002"), ("10002", "20001"), ("20001", "20002"), ("30001", "30002"),
                 ("30002", "30003"), ("30003", "40001")):
        edge[a][b] = edge[b][a] = 30.0
    polygon = {"vertices": sorted(state), "edges": [(a, b) for a in edge for b in edge[a] if a < b],
               "state": state, "border": {(a, b): 30e3 for a in edge for b in edge[a] if a < b},
               "connectors": [], "aland": dict.fromkeys(state, 1e8)}
    return score.Geography(state, xy, edge, polygon)


def _toy_run(tmp: str, owners: dict) -> str:
    """A run folder: channel IFA, one fine channel `ifa`, every ZIP at m_rel 1.0, `owners` {district: ZIPs}."""
    state = _toy_geo().state
    rows = [{"zip_code": z, "current_channel": "ifa", "state": state[z], "model_channel": "IFA", "district": j,
             "m_rel": "1.0"} for j, zs in owners.items() for z in zs]
    d = os.path.join(tmp, "K0")
    os.makedirs(d)
    for name, recs in (("ledger.csv", rows),
                       ("districts.csv", [{"channel": "IFA", "district": j, "drawn_mass": str(len(zs))}
                                          for j, zs in owners.items()])):
        with open(os.path.join(d, name), "w", newline="") as fh:
            w = csv.DictWriter(fh, list(recs[0]))
            w.writeheader()
            w.writerows(recs)
    json.dump({"fine_channels": ["ifa"]}, open(os.path.join(d, "run.json"), "w"))
    return d


def _gate(owners: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        d = _toy_run(tmp, owners)
        with ifa_index.recorded_sides() as sides:
            got = ifa_index.check_gate().m1(d, _toy_geo())
        chk = got["check"]
        return {"status": chk.status, "verdict": ifa_index.m1_verdict(
            chk.status, chk.summary, chk.items, sides, MANHATTAN, got["diagnostic"]), "items": chk.items}


def test_the_manhattan_exception_is_read_from_the_pieces_the_gate_names_not_from_a_district_name():
    # X holds 10001 away from its 20001-20002 body (10002 is another district's): a detached Manhattan piece
    only = _gate({"IFA_01": ["20001", "20002", "10001"], "IFA_02": ["10002"], "IFA_03": ["30001", "30002"],
                  "IFA_04": ["30003", "40001"]})
    assert only["status"] == "fail" and only["verdict"]["passes"]
    (item, hit), = only["verdict"]["excepted"]
    assert item.startswith("IFA/IFA_01: detached piece of 1 ZIPs (10001...)") and hit == ["10001"]
    assert not only["verdict"]["blocking"]
    # a second piece, 10002 (not county 36061) held by IFA_03, is not excepted
    both = _gate({"IFA_01": ["20001", "20002", "10001"], "IFA_03": ["30001", "30002", "10002"],
                  "IFA_04": ["30003", "40001"]})
    v = both["verdict"]
    assert not v["passes"] and [h for _, h in v["excepted"]] == [["10001"]]
    assert v["excepted"][0][0].startswith("IFA/IFA_01: detached piece of 1 ZIPs (10001...)")
    assert len(v["blocking"]) == 1 and v["blocking"][0].startswith("IFA/IFA_03: detached piece of 1 ZIPs (10002...)")


def test_a_coverage_or_ownership_item_or_an_unverified_gate_blocks_the_pass_beside_the_manhattan_items():
    manhattan_piece = {"IFA_01": ["20001", "20002", "10001"], "IFA_02": ["10002"], "IFA_03": ["30001", "30002"]}
    got = _gate(manhattan_piece)                           # 30003 and 40001 have no owner and no row
    assert not got["verdict"]["passes"] and got["verdict"]["excepted"]
    assert any("no row" in b for b in got["verdict"]["blocking"])
    v = ifa_index.m1_verdict("unverified", "no polygon graph: M1 is not checked", [], {"necks": {}, "pieces": {}},
                             MANHATTAN)
    assert not v["passes"] and "unverified" in v["blocking"][0]
    v = ifa_index.m1_verdict("pass", "ok", [], {"necks": {}, "pieces": {}}, MANHATTAN, {"label": "tau 5%"})
    assert not v["passes"] and "diagnostic" in v["blocking"][0]
    assert ifa_index.m1_verdict("pass", "ok", [], {"necks": {}, "pieces": {}}, MANHATTAN)["passes"]


def test_a_neck_is_excepted_only_when_its_proved_side_holds_a_manhattan_zcta():
    neck = lambda zs, status="proved": audit.Neck(8.5, tuple(zs), 0.05, 0.4, (("a", "b", 1.0),), status)
    with ifa_index.recorded_sides() as sides:
        item_m = audit.neck_item("IFA", "IFA_12", neck(["10001", "10002", "20001"]))
        item_o = audit.neck_item("IFA", "IFA_13", neck(["30001", "30002"]))
        item_u = audit.neck_item("IFA", "IFA_14", neck(["10001"], "unresolved"))
        mass = audit.neck_item("IFA", "IFA_12", neck(["10001"]), audit.MASS_NECK)
    assert audit.neck_item is not None and audit.neck_item.__name__ == "neck_item"   # restored, not the wrapper
    v = ifa_index.m1_verdict("fail", "3 necks", [item_m, item_o, item_u, mass], sides, MANHATTAN)
    assert [(i, h) for i, h in v["excepted"]] == [(item_m, ["10001"])]
    assert v["blocking"] == [item_o, item_u] and not v["passes"]       # the mass neck fails nothing; unresolved never excepted


def test_the_recorder_restores_the_audit_functions_even_when_the_gate_raises():
    real = audit.neck_item, audit.district_pieces
    try:
        with ifa_index.recorded_sides():
            raise RuntimeError("gate died")
    except RuntimeError:
        pass
    assert (audit.neck_item, audit.district_pieces) == real


def test_window_verdict_uses_the_unrounded_mass_not_the_rounded_dollars():
    rate = ifa_index.RATE
    in_rounded = {"under": 798.741, "over": 1148.1922}    # usd_m rounds to 1000.0 and 1437.5, the window's edges
    for kind, m in in_rounded.items():
        assert round(m * rate, 1) in (1000.0, 1437.5)
        assert (m * rate < 1000.0) or (m * rate > 1437.5)
    dist = {"A": {"m_rel": 798.741, "usd_m": 1000.0, "window": "in"},          # 999.9966M: under
            "B": {"m_rel": 1148.1922, "usd_m": 1437.5, "window": "in"},        # 1437.50002M: over
            "C": {"m_rel": 800.0, "usd_m": 1001.6, "window": "in"},
            "D": {"m_rel": 900.0, "usd_m": 1126.8, "window": "over"}}          # the recorded verdict is kept
    assert ifa_index.window_verdict(dist) == (["B", "D"], ["A"])


def test_window_verdict_rejects_a_sub_dollar_breach_and_keeps_the_edges():
    rate = ifa_index.RATE
    under = {"U": {"m_rel": 999_999_999.75 / 1e6 / rate, "window": "in"}}      # $999,999,999.75: rounds up to the floor
    over = {"O": {"m_rel": 1_437_500_000.25 / 1e6 / rate, "window": "in"}}     # $1,437,500,000.25
    assert round(under["U"]["m_rel"] * rate * 1e6) == 1_000_000_000 and round(over["O"]["m_rel"] * rate * 1e6) == 1_437_500_000
    assert ifa_index.window_verdict(under) == ([], ["U"])
    assert ifa_index.window_verdict(over) == (["O"], [])
    ifa_index.RATE = 1.0                  # a rate with exact products: m_rel 1000 and 1437.5 are $1,000M and $1,437.5M
    try:
        edge = {"E": {"m_rel": 1000.0}, "F": {"m_rel": 1437.5}}
        assert ifa_index.window_verdict(edge) == ([], [])                      # the edges are in
    finally:
        ifa_index.RATE = rate


def _ledger(rows):
    return [{"zip_code": z, "current_channel": f, "district": d} for z, f, d in rows]


def _mass_extract() -> data.Extract:
    return data.Extract(("ifa", "wh"), ["10001", "10002", "10002", "20001"], ["ifa", "ifa", "wh", "ifa"],
                        [1.5, 2.25, 9.0, 4.0], [{}] * 4, [0.0] * 4)


def test_current_masses_join_the_ledger_to_the_extract_and_refuse_a_cell_it_lacks():
    ext = _mass_extract()
    ledger = _ledger([("10001", "ifa", "IFA_01"), ("10002", "ifa", "IFA_01"), ("20001", "ifa", "IFA_02"),
                      ("10002", "wh", "")])                                    # an unassigned cell holds no mass
    assert ifa_index.current_masses(ledger, ext) == {"IFA_01": 3.75, "IFA_02": 4.0}
    try:
        ifa_index.current_masses(_ledger([("30001", "ifa", "IFA_01")]), ext)
    except ValueError as e:
        assert "30001/ifa" in str(e)
    else:
        raise AssertionError("a ledger cell with no extract mass was accepted")


def test_saved_district_masses_that_disagree_with_current_ownership_are_rejected():
    saved = {"IFA_01": {"m_rel": 3.75, "window": "in"}, "IFA_02": {"m_rel": 4.0, "window": "in"}}
    got = ifa_index.checked_districts(saved, {"IFA_01": 3.75 * (1 + 1e-12), "IFA_02": 4.0})
    assert got["IFA_01"]["m_rel"] == 3.75 * (1 + 1e-12) and got["IFA_02"]["window"] == "in"
    for now in ({"IFA_01": 3.75, "IFA_02": 4.0 + 1e-3},                         # ownership moved a ZCTA's mass
                {"IFA_01": 3.75},                                               # a district the ledger lacks
                {"IFA_01": 3.75, "IFA_02": 4.0, "IFA_03": 1.0}):                # a district run.json lacks
        try:
            ifa_index.checked_districts(saved, now)
        except ValueError:
            continue
        raise AssertionError(f"accepted stale saved masses against {now}")


def test_load_judges_the_window_on_the_current_ledger_not_on_run_json():
    ext = data.Extract(("ifa",), ["10001", "10002"], ["ifa", "ifa"], [800.0, 1.0], [{}, {}], [0.0, 0.0])
    real = (ifa_index.check_gate, ifa_index.manhattan_zips)
    ifa_index.check_gate = lambda: types.SimpleNamespace(m1=lambda d, g=None: {
        "check": types.SimpleNamespace(status="pass", summary="ok", items=[]), "diagnostic": None})
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root, base = os.path.join(tmp, "root"), os.path.join(tmp, "full.json.gz")
            data.write(ext, base)
            d = os.path.join(root, "K48")
            os.makedirs(d)
            cols = "zip_code,current_channel,state,district\n"
            open(os.path.join(d, "districts.csv"), "w").write("district,district_name\nIFA_01,one\n")
            open(os.path.join(d, "manifest.json"), "w").write("{}")

            def folder(rows, saved_m):
                open(os.path.join(d, "ledger.csv"), "w").write(cols + "".join(f"{z},ifa,NY,{j}\n" for z, j in rows))
                json.dump({"districts": {"IFA_01": {"m_rel": saved_m, "usd_m": saved_m * ifa_index.RATE,
                                                    "window": "in"}}}, open(os.path.join(d, "run.json"), "w"))

            folder([("10001", "IFA_01"), ("10002", "IFA_01")], 801.0)            # 801 m_rel = $1,002.8M: in
            r = ifa_index.load(root, 48, frozenset(), extract=base)
            assert r["over"] == [] and r["under"] == [] and r["in"] == 1
            folder([("10001", "IFA_01")], 801.0)                                 # ZIP 10002 left: $1,001.6M, run.json stale
            try:
                ifa_index.load(root, 48, frozenset(), extract=base)
            except ValueError as e:
                assert "differs from the ledger" in str(e)
            else:
                raise AssertionError("a stale run.json mass kept the pass")
            folder([("10001", "IFA_01")], 800.0)                                 # run.json agrees: $1,001.6M, in
            assert ifa_index.load(root, 48, frozenset(), extract=base)["in"] == 1
    finally:
        ifa_index.check_gate, ifa_index.manhattan_zips = real


# ------------------------------------------------------------------------------ C7, C8: warm.py
warm = _import("contig_warm", "warm.py")


def _done_folder(path: str, contig: dict | None = None) -> str:
    os.makedirs(path, exist_ok=True)
    json.dump({"status": "done"}, open(os.path.join(path, "manifest.json"), "w"))
    open(os.path.join(path, "ledger.csv"), "w").write("zip_code\n")
    json.dump(contig or {"channels": {"WIFI": {"connected": True, "necks_left": [], "undrawn_zctas": 0, "groups": []}}},
               open(os.path.join(path, "contig.json"), "w"))
    return path


class _Grid:
    def get(self, pid):
        return {"label": "passes", "reason": "", "final": None, "summary": {}}


class _Drv:
    def __init__(self, extract, plans):
        self.extract, self.plans, self.grid = extract, plans, _Grid()

    def note(self, *a, **k):
        pass

    def finish(self, pt):
        pass


def _run_warm_point(main: str, root: str, cut: bool) -> tuple:
    """Run `warm._point` with the stages stubbed; the commands it issued, in order, and the full extract."""
    full = "/hub/instance_descaled_usd.json.gz"
    _done_folder(os.path.join(main, "p1", "south", "draw"))
    if cut:
        open(os.path.join(main, "p1", "south", sealed_mod.RUN_EXTRACT), "w").write("cut")
    json.dump({"extract": full, "extract_sha256": "x", "host": "m5", "partition": {"path": "P"},
               "points": {"p1": {"runs": {}}}}, open(os.path.join(main, sealed_mod.STATE_JSON), "w"))
    pt = {"id": "p1", "structure": "s", "runs": [{"name": "south", "states": ["TX"], "ks": {"WIFI": 2}}]}
    issued = []
    saved = warm.sealed.load_partition, warm.point_state, warm.run_stage
    warm.sealed.load_partition = lambda path: [pt]
    warm.point_state = lambda a, p, rdir: (_Drv(full, os.path.join(main, "_plans")),
                                              {"runs": {"south": {"ks": {"WIFI": 2}}}})
    warm.run_stage = lambda drv, pid, name, cmd, log, cap, env=None: issued.append((name, cmd)) or {"rc": 0, "stop": None}
    try:
        a = types.SimpleNamespace(id="p1", main=main, root=root, partition="P", run_name="south", jobs=1, budget=60.0,
                                  hours=1.0, wait_r1=False)
        warm._point(a)
    finally:
        warm.sealed.load_partition, warm.point_state, warm.run_stage = saved
    return issued, full


sealed_mod = warm.sealed


def test_warm_repairs_and_glues_on_the_extract_the_run_was_drawn_on():
    for cut in (True, False):
        with tempfile.TemporaryDirectory() as tmp:
            main, root = os.path.join(tmp, "main"), os.path.join(tmp, "root")
            os.makedirs(main)
            os.makedirs(root)
            issued, full = _run_warm_point(main, root, cut)
        names = [n for n, _ in issued]
        assert names == ["r1", "r2", "glue"] or names == ["r1", "glue"], names
        want = os.path.join(main, "p1", "south", sealed_mod.RUN_EXTRACT) if cut else full
        for name, cmd in issued:
            assert cmd[cmd.index("--extract") + 1] == want, (name, cmd)
    assert warm.source_extract("/m", "p1", "south", "/full") == "/full"


def test_an_interrupt_in_a_warm_point_ends_the_stages_still_running():
    calls, real = [], (warm._point, warm.overnight.stop_all)
    warm._point = lambda a: (_ for _ in ()).throw(KeyboardInterrupt())
    warm.overnight.stop_all = lambda: calls.append("stop_all")
    try:
        try:
            warm.cmd_point(types.SimpleNamespace())
        except KeyboardInterrupt:
            pass
        else:
            raise AssertionError("the interrupt was swallowed")
    finally:
        warm._point, warm.overnight.stop_all = real
    assert calls == ["stop_all"]


# ------------------------------------------------------------------------------ C10, C11: the regional scripts
import subprocess

STUB_PY = '''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
if a[:1] == ["-"]:                      # the drawing check, a heredoc
    sys.argv = ["-"] + a[1:]
    exec(compile(sys.stdin.read(), "<stdin>", "exec"), {"__name__": "__main__"})
    sys.exit(0)
script = next(x for x in a if x.endswith(".py"))
rest = a[a.index(script) + 1:]
if script.endswith("state_extract.py"):
    if os.environ.get("FAIL_EXTRACT"):
        print("extract boom")
        sys.exit(4)
    open(rest[0], "w").write("extract")
elif script.endswith("run.py"):
    out = rest[rest.index("--out") + 1]
    os.makedirs(out, exist_ok=True)
    json.dump({"channels": {"IFA": {"undrawn_zctas": 0, "status": "connected", "connected": True}}},
              open(os.path.join(out, "contig.json"), "w"))
elif script.endswith("repair.py"):
    sys.exit(int(os.environ.get("REPAIR_RC", "0")))
'''


def _script(name: str, args: list, tmp: str, spec: str, env: dict, sa: bool = False) -> tuple:
    """Run tools/exp/contig/<name> from a scratch repo root with stubbed python and a pass-through gtimeout;
    (exit status, the sa folder)."""
    cwd, hub = os.path.join(tmp, "repo"), os.path.join(tmp, "hub")
    os.makedirs(os.path.join(cwd, "scenarios", "regions", "ifa"))
    os.makedirs(hub)
    open(os.path.join(cwd, "scenarios", "regions", "ifa", spec), "w").write("[x]\ndelta = 0.1\n")
    stub, gt = os.path.join(tmp, "td_py"), os.path.join(tmp, "bin", "gtimeout")
    os.makedirs(os.path.dirname(gt))
    open(stub, "w").write(STUB_PY)
    open(gt, "w").write('#!/bin/sh\nshift\nexec "$@"\n')
    os.chmod(stub, 0o755)
    os.chmod(gt, 0o755)
    sa_dir = os.path.join(hub, "runs", "exp", "sealed_2026-10-14", "ifa", "sa")
    if sa:
        os.makedirs(sa_dir)
    got = subprocess.run(["bash", os.path.abspath(os.path.join(CONTIG, name)), *args], cwd=cwd, capture_output=True, text=True,
                         env={**os.environ, "TD_PY": stub, "TD_REPO": hub, "PATH": os.path.dirname(gt) + os.pathsep + os.environ["PATH"],
                              **env})
    return got.returncode, sa_dir, got


def test_region_night_makes_its_extract_folder_stops_on_a_failed_extract_and_returns_the_repair_status():
    with tempfile.TemporaryDirectory() as tmp:                      # no runs/ yet: the script makes _inst itself
        rc, sa, got = _script("region_night.sh", ["t", "TX"], tmp, "ifa_night_t.toml", {})
        assert rc == 0, got.stderr
        assert os.path.isfile(os.path.join(sa, "_inst", "t.json.gz")) and "repair exit 0" in open(os.path.join(sa, "t.rep.log")).read()
    with tempfile.TemporaryDirectory() as tmp:
        rc, sa, got = _script("region_night.sh", ["t", "TX"], tmp, "ifa_night_t.toml", {"REPAIR_RC": "5"})
        assert rc == 5 and "repair exit 5" in open(os.path.join(sa, "t.rep.log")).read()
    with tempfile.TemporaryDirectory() as tmp:                      # a failed extract: stop, no drawing, no repair
        rc, sa, got = _script("region_night.sh", ["t", "TX"], tmp, "ifa_night_t.toml", {"FAIL_EXTRACT": "1"})
        assert rc == 2 and "extract" in got.stderr and "failed (exit 4)" in got.stderr, (rc, got.stderr)
        assert "extract boom" in open(os.path.join(sa, "t.run.log")).read()
        assert not os.path.exists(os.path.join(sa, "t", "contig.json")) and not os.path.exists(os.path.join(sa, "t.rep.log"))


def test_sa_night_returns_the_repair_status():
    for rc_want in (0, 7):
        with tempfile.TemporaryDirectory() as tmp:
            rc, sa, got = _script("sa_night.sh", ["50"], tmp, "ifa_night_sa_k50.toml", {"REPAIR_RC": str(rc_want)}, sa=True)
            assert rc == rc_want, (rc, got.stderr)
            assert f"repair exit {rc_want}" in open(os.path.join(sa, "k50.rep.log")).read()
