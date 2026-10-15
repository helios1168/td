"""export.py -- export one draw.py coupled group as a standalone instance JSON.gz (#142, A0).

    "$TD_PY" tools/exp/bnc/export.py --out runs/exp/bnc_2026-10-15/instances [--only FI_PA ...]
        [--m2-dir /tmp/bnc_in/m2]

The group is rebuilt by *replaying* the run that drew it: the same spec, plans cache and extract,
`draw.draw` (sequential, as the 2026-10-14 grid ran it) or `repair.solve_window` (the NY window),
with `draw._solve_group` wrapped.  Groups drawn before the target take their drawing from the run's
ledger, so each cluster's bodies are what the run saw; the target call is run by draw.py itself up
to its first MILP solve (`capture.capture_group`) and stopped.  Nothing of draw.py's rules is
written again here.  Each instance records

- `faithful`: the same call with the run's own flags (its `dag`, `flow`, `count`) captured and
  its column and row counts compared with the ones the run's `contig.json` recorded;
- the instance's base MILP (`dag` False, no flow, no repair rows, no neck cuts: the complete model
  the arms share), the group graph, the data to hand draw.py again (`capture.rebuild_args`);
- `widths`: the gate's width data (polygon borders, connectors, gap widths, land areas, relays) of
  the group's ZCTAs, bodies and neighbours, apart from the objective's border coefficients
  (`capture.width_data`);
- `roundtrip`: that MILP rebuilt from the instance alone by draw.py's code, compared column for
  column and row for row with the exported one (`roundtrip`).
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import capture  # noqa: E402
import inst_io  # noqa: E402

ROOT = capture.ROOT
TD_REPO = os.environ.get("TD_REPO", ROOT)
NAT = os.path.join(TD_REPO, "runs", "exp", "national_2026-10-14")
M2_DIR = "/tmp/bnc_in/m2"
EXTRACT = os.path.join(TD_REPO, "instance_descaled_usd.json.gz")


def instances(m2_dir: str = M2_DIR) -> dict:
    """The four groups of the issue's A0."""
    return {
        "FI_PA": dict(kind="draw", host="m5", channel="FI", group=4,
                      note="ne-48-bal FI group 4: 4 districts, PA (DC+PA+VA+WV, DE+MD+PA, NJ+PA, PA)",
                      run_dir=f"{NAT}/main/ne-48-bal/rest-FI-WH-national/draw",
                      spec=f"{NAT}/main/ne-48-bal/rest-FI-WH-national/spec.toml",
                      plans=f"{NAT}/main/_plans", extract=EXTRACT,
                      gate_base=f"{NAT}/warm/ne-48-bal/merged"),
        "FI_FL": dict(kind="draw", host="m5", channel="FI", group=2,
                      note="ne-50-bal FI group 2: 3 districts, FL (AL+FL, FL, FL+GA)",
                      run_dir=f"{NAT}/main/ne-50-bal/rest-FI-WH-national/draw",
                      spec=f"{NAT}/main/ne-50-bal/rest-FI-WH-national/spec.toml",
                      plans=f"{NAT}/main/_plans", extract=EXTRACT,
                      gate_base=f"{NAT}/warm/ne-50-bal/merged"),
        "FI_NY": dict(kind="repair", host="m5", channel="FI", shape="corridor", slack=1,
                      district="NY+PA+WV#1", h0=8, max_zctas=1700,
                      note="ne-50-bal FI_19 (NY+PA+WV#1, 4 pieces): repair pass 3's corridor window "
                           "at slack 1, the window of every pass that ended unknown",
                      run_dir=f"{NAT}/warm/ne-50-bal/r2", record=f"{NAT}/warm/ne-50-bal/r3/contig.json",
                      spec=f"{NAT}/main/ne-50-bal/rest-FI-WH-national/spec.toml",
                      plans=f"{NAT}/main/_plans", extract=EXTRACT,
                      gate_base=f"{NAT}/warm/ne-50-bal/merged"),
        "WIFI_MD": dict(kind="draw", host="m2", channel="WIFI", group=0,
                        note="nw49-50 WIFI group 0: 3 districts, MD (DC+MD, DE+MD+NJ, MD+PA+WV)",
                        run_dir=f"{m2_dir}/draw", spec=f"{m2_dir}/spec.toml",
                        plans=f"{m2_dir}/plans", extract=EXTRACT,
                        gate_base=f"{m2_dir}/merged"),
    }


# ------------------------------------------------------------------------------ source data
def read_csv(path: str) -> list:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def ledger_owners(run_dir: str, channel: str) -> dict:
    """{zip: copy name} of a run folder's ledger for one planning channel."""
    copy = {(r["channel"], r["district"]): r["copy"] for r in read_csv(os.path.join(run_dir, "districts.csv"))}
    out = {}
    for r in read_csv(os.path.join(run_dir, "ledger.csv")):
        if r["model_channel"] == channel and r["district"]:
            out[r["zip_code"]] = copy[channel, r["district"]]
    return out


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def run_params(run_dir: str) -> dict:
    with open(os.path.join(run_dir, "manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)["params"]


def commit() -> str:
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                       text=True).strip()
    except Exception:
        return "unknown"


# ------------------------------------------------------------------------------ the capture
class Found(Exception):
    """Raised inside draw.py's call chain once the target group is captured."""

    def __init__(self, out):
        self.out = out


def _original_kwargs(a: dict, dag: bool | None = None) -> dict:
    kw = dict(a)
    if dag is not None:
        kw["dag"] = dag
    kw["log"] = lambda *_: None
    kw["time_limit"] = 3600.0
    return kw


def _base_kwargs(a: dict) -> dict:
    """The call as the instance's complete model: no DAG, no start, no flow, no repair rows, no
    neck cuts."""
    kw = dict(a)
    kw.update(dag=False, start=None, count=None, layers=False, flow=False, necks=None,
              neck_seed=None, log=lambda *_: None, time_limit=3600.0)
    return kw


def capture_call(draw, real, a: dict, record_dag: bool) -> dict:
    """Both captures of one `_solve_group` call `a` (by name): `faithful` with the run's own flags
    (its recorded `dag`), and `base`, the instance's model."""
    faithful = capture.capture_group(draw, (), _original_kwargs(a, record_dag), real)
    centres = []
    with capture.recording_centres(draw, centres):
        base = capture.capture_group(draw, (), _base_kwargs(a), real)
    snap = capture.snapshot_args(a, centres)
    return {"faithful": faithful, "base": base, "snap": snap}


def replay_draw(cfg: dict, ctx: dict, draw) -> dict:
    """Replay a sequential `draw.draw` of the run until the group `cfg['group']`."""
    c = cfg["channel"]
    with open(os.path.join(cfg["run_dir"], "contig.json"), encoding="utf-8") as fh:
        recorded = json.load(fh)["channels"][c]["groups"]
    target = recorded[cfg["group"]]
    drawn = ledger_owners(cfg["run_dir"], c)
    real = draw._solve_group

    def fake(*args, **kw):
        a = capture.bind(real, args, kw)
        js = sorted({j for z in a["zs"] for j in a["allowed"][z]})
        key = (js, len(a["zs"]))
        if key == (sorted(target["districts"]), target["free_zctas"]):
            raise Found({**capture_call(draw, real, a, bool(target["dag"])), "recorded": target})
        rec = next((g for g in recorded if (sorted(g["districts"]), g["free_zctas"]) == key), None)
        if rec is None:
            raise RuntimeError(f"a group the run did not record: {key[0]} with {key[1]} ZCTAs")
        owner = {z: drawn[z] for z in a["zs"] if z in drawn} if rec["status"] in ("optimal", "connected") else {}
        g = draw.Group(js, rec["units"], len(a["zs"]), rec["columns"], rec["rows"], rec["status"],
                       owner=owner)
        return g
    try:
        with capture.patched(draw, _solve_group=fake):
            draw.draw(ctx["inst"], ctx["plan"], ctx["xy"], arm="arm1", fixed_targets=False,
                      time_limit=1e7, sequential=True, log=lambda *_: None, border=ctx["border"],
                      land=ctx["land"])
    except Found as f:
        return f.out
    raise RuntimeError("the replay ended without reaching the target group")


def replay_repair(cfg: dict, ctx: dict, draw, repair) -> dict:
    """Replay `repair.solve_window` on the corridor window of the cluster holding `district`."""
    c, inst, plan, owner = cfg["channel"], ctx["inst"], ctx["plan"], ctx["owner"]
    adj, m = inst.units.zip_adj, inst.channels[c].m
    _, free, _ = draw.split_fixed(inst, plan)
    free = free & set(owner)
    pieces = repair.detached(owner, adj, m)
    group = next(g for g in repair.clusters(pieces) if g[0][0] == cfg["district"])
    steps = repair.steps(group, owner, free, adj, cfg["h0"], cfg["max_zctas"])
    W = next(w for sh, k, w in steps if sh == cfg["shape"] and k == cfg["slack"])
    with open(cfg["record"], encoding="utf-8") as fh:
        recs = json.load(fh)["channels"][c]["repair"]
    rec = next(r for r in recs if r["shape"] == cfg["shape"] and r.get("slack") == cfg["slack"] and r["cap"])
    target = ast.literal_eval(rec["group"]) if isinstance(rec["group"], str) else rec["group"]
    if rec["window_zctas"] != len(W):
        raise RuntimeError(f"the window has {len(W)} ZCTAs, the record {rec['window_zctas']}")

    real = draw._solve_group

    def fake(*args, **kw):
        a = capture.bind(real, args, kw)
        raise Found({**capture_call(draw, real, a, bool(target["dag"])), "recorded": target,
                     "window": sorted(W)})
    try:
        with capture.patched(draw, _solve_group=fake):
            repair.solve_window(inst, plan, owner, W, ctx["p"], 1e7, True, lambda *_: None, True,
                                True, {j for j, _ in group}, ctx["border"], None, frozenset())
    except Found as f:
        return f.out
    raise RuntimeError("solve_window ended without a solve")


def context(cfg: dict, draw) -> dict:
    """The run's instance, plan, coordinates, border and land term (as `run.contig_run` and
    `repair.main` build them)."""
    from td import data, geo
    from td import spec as tdspec
    run = capture._load("contig_run", os.path.join(capture.CONTIG, "run.py"))
    params = run_params(cfg["run_dir"])
    states = tuple(x for x in (params.get("states") or "").split(",") if x)
    out = {"run": run, "states": states, "params": params}
    if cfg["kind"] == "repair":
        repair = capture._load("contig_repair", os.path.join(capture.CONTIG, "repair.py"))
        s, ref, ext, polygon, inst, plans, reports, owners, src = repair.load(
            cfg["run_dir"], cfg["extract"], cfg["plans"], None, states)
        out["repair"] = repair
        out["owner"] = owners[cfg["channel"]]
        out["land"] = None
    else:
        s = tdspec.load(cfg["spec"])
        ref = geo.read_reference()
        extract = data.load(cfg["extract"])
        ext = tdspec.scope(s, data.conus(extract, ref))
        polygon = geo.polygon_graph()
        planning = run.induced_graph(polygon, states) if states else None
        inst = tdspec.build(s, ext, ref, graph=planning)
        plans, _ = run.plans_for(inst, cfg["spec"], cfg["extract"], cfg["plans"])
        ratio = params.get("land_ratio")
        out["land"] = None if ratio is None else draw.land_term(planning or polygon, ratio)
    planning = run.induced_graph(polygon, states) if states else None
    rows = ref.set_index("zcta").loc[sorted(inst.units.unit_of)]
    out.update(inst=inst, plan=plans[cfg["channel"]], polygon=polygon,
               border=draw.border_km(planning or polygon),
               xy=dict(zip(rows.index, zip(rows["x"].astype(float), rows["y"].astype(float)))),
               p={z: (float(x) / 1000.0, float(y) / 1000.0)
                  for z, x, y in zip(rows.index, rows["x"], rows["y"])})
    return out


# ------------------------------------------------------------------------------ checks
def counts(cap: dict) -> dict:
    return {"columns": len(cap["model"]["cost"]), "rows": len(cap["model"]["rows"]["lo"])}


def roundtrip(doc: dict, draw) -> dict:
    """Rebuild the instance's MILP from the instance's `draw` section with draw.py's code and
    compare it with the exported model: same columns (labels, bounds, integrality), same rows
    (bounds, pattern, coefficients), objective vector equal to 1e-12 relative.  {"ok", "columns",
    "rows", "objective_max_abs_diff", "problems"}."""
    again = capture.rebuild_model(draw, doc["draw"])
    a, b = doc["model"], again["model"]
    problems = []
    if again["labels"] != doc["labels"]:
        problems.append("column labels differ")
    for k in ("lb", "ub", "integer"):
        x = [None if (isinstance(v, float) and np.isinf(v)) else v for v in b[k]]
        y = [None if (isinstance(v, float) and np.isinf(v)) else v for v in a[k]]
        if x != y:
            problems.append(f"column {k} differ")
    ra, rb = a["rows"], b["rows"]
    for k in ("start", "idx"):
        if ra[k] != rb[k]:
            problems.append(f"row {k} differ")
    for k in ("lo", "hi"):
        x = [None if (v is not None and np.isinf(v)) else v for v in ra[k]]
        y = [None if np.isinf(v) else v for v in rb[k]]
        if not _close(x, y):
            problems.append(f"row {k} differ")
    if not _close(ra["val"], rb["val"]):
        problems.append("row coefficients differ")
    ca, cb = np.array(a["cost"]), np.array(b["cost"])
    diff = float(np.max(np.abs(ca - cb))) if len(ca) == len(cb) else float("inf")
    if len(ca) != len(cb) or not np.allclose(ca, cb, rtol=1e-12, atol=1e-12):
        problems.append("objective vector differs")
    return {"ok": not problems, "columns": [len(ca), len(cb)], "rows": [len(ra["lo"]), len(rb["lo"])],
            "objective_max_abs_diff": diff, "problems": problems}


def _close(x, y) -> bool:
    if len(x) != len(y):
        return False
    for u, v in zip(x, y):
        if (u is None) != (v is None):
            return False
        if u is not None and abs(u - v) > 1e-12 * max(1.0, abs(u)):
            return False
    return True


# ------------------------------------------------------------------------------ the document
def build_doc(name: str, cfg: dict, cap: dict, widths: dict) -> dict:
    snap, base, faithful, rec = cap["snap"], cap["base"], cap["faithful"], cap["recorded"]
    g = base["graph"]
    window = {j: [g["lo"] - g["fixed_mass"][j], g["hi"] - g["fixed_mass"][j]] for j in g["js"]}
    want = {"columns": rec["columns"], "rows": rec["rows"]}
    got = counts(faithful)
    return {
        "schema": inst_io.SCHEMA, "id": name,
        "meta": {"note": cfg["note"], "kind": cfg["kind"], "host": cfg["host"],
                 "channel": cfg["channel"], "run_dir": cfg["run_dir"], "exported": time.strftime("%Y-%m-%dT%H:%M:%S"),
                 "code_commit": commit(), "extract_sha256": sha256(cfg["extract"]),
                 "spec_sha256": sha256(cfg["spec"]), "sequential": snap["sequential"],
                 "districts": g["js"], "free_zctas": len(snap["zs"]), "band": [g["lo"], g["hi"]],
                 "recorded_group": {k: rec.get(k) for k in ("districts", "free_zctas", "columns", "rows",
                                                           "status", "seconds", "dag", "delta")},
                 "faithful": {"columns": [got["columns"], want["columns"]],
                              "rows": [got["rows"], want["rows"]],
                              "ok": got == want, "dag": bool(rec["dag"]),
                              "note": "the run's own call (its dag, flow, count flags) rebuilt now against "
                                      "the columns and rows its contig.json recorded"},
                 "window": window, "window_zctas": cap.get("window"),
                 "base_counts": counts(base),
                 "widths": {k: len(v) for k, v in widths.items()},
                 "start_vector": "none: draw.py's construct found no connected drawing"
                 if base["start"] is None else "present (constructed)"},
        "model": base["model"], "labels": base["labels"], "graph": g,
        "widths": widths, "draw": snap, "start": base["start"]}


def export_one(name: str, cfg: dict, out_dir: str, log=print) -> dict:
    draw = capture.load_draw()
    t0 = time.time()
    ctx = context(cfg, draw)
    log(f"{name}: context built in {time.time() - t0:.0f}s")
    if cfg["kind"] == "draw":
        cap = replay_draw(cfg, ctx, draw)
    else:
        cap = replay_repair(cfg, ctx, draw, ctx["repair"])
    doc = build_doc(name, cfg, cap, capture.width_data(ctx["polygon"], cap["snap"]))
    f = doc["meta"]["faithful"]
    log(f"{name}: faithful columns {f['columns']} rows {f['rows']} ok={f['ok']}")
    if not f["ok"]:
        raise RuntimeError(f"{name}: the replayed call does not reproduce the run's group "
                           f"(columns {f['columns']}, rows {f['rows']})")
    rt = roundtrip(doc, draw)
    doc["meta"]["roundtrip"] = rt
    log(f"{name}: round trip ok={rt['ok']} columns {rt['columns']} rows {rt['rows']} "
        f"objective max |diff| {rt['objective_max_abs_diff']:.3g}")
    if not rt["ok"]:
        raise RuntimeError(f"{name}: round trip failed: {rt['problems']}")
    path = os.path.join(out_dir, f"{name}.json.gz")
    inst_io.save(doc, path)
    log(f"{name}: wrote {path} ({os.path.getsize(path) / 1e6:.1f} MB) in {time.time() - t0:.0f}s")
    return doc["meta"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--m2-dir", default=M2_DIR)
    a = ap.parse_args(argv)
    table = instances(a.m2_dir)
    names = a.only or list(table)
    os.makedirs(a.out, exist_ok=True)
    metas = {}
    for name in names:
        metas[name] = export_one(name, table[name], a.out)
    path = os.path.join(a.out, "INDEX.json")
    old = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            old = json.load(fh)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({k: {**old, **metas}[k] for k in table if k in {**old, **metas}}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
