"""run.py -- #109's run: a scenario's master plans drawn by the contiguity-aware realizer
(`tools/exp/contig/draw.py`) into a full run folder that `python -m td maps`,
`tools/mandates/check.py` and `tools/looks/score.py` read like a `python -m td run` folder.

    "$TD_PY" -u tools/exp/contig/run.py <spec.toml> --out <dir> [--extract PATH]
        [--arm arm1|band|split|move] [--fixed-targets] [--sequential] [--time-limit S]
        [--group-limit S] [--plans PATH] [--plans-file PKL] [--parent RUN] [--maps] [--jobs N]

Or as the `contig` formulation of `tools/exp/sweep.py` (#92's tracker): params `scenario`,
`arm`, `time_limit` (seconds per channel), `group_limit`, `fixed_targets`, `sequential`, `plans`.

The steps are `td.output.run`'s with the realizer swapped: the instance on M1's polygon graph,
each channel's master (`td.master.plan_all`, cached in `--plans` when given, keyed by the spec's
and the extract's sha256; or `--plans-file`, the pickled plans a source run drew, kept as they
are on the current graph), then per channel `draw.draw` at the arm's rules with the border shape
term over the polygon graph's borders (#121), the ledger, the audit, names and `districts.csv`.
With `--jobs N` above 1 each channel is drawn in its own process, N at once, HiGHS on one thread
each (`draw_parallel`, #123); a channel's drawing reads only its plan, so the folder is the
sequential run's whenever no solve stops on a time limit.
The CLI writes `manifest.json` (mandate T1, `write_manifest`) at the start and the end.  A group with no connected drawing keeps `td.realize` and
`td.territory`'s owners there, so the ledger stays full and M1 fails on them, never patched.

Arms (#109; what gives way is the owner's, #112, so each remedy is its own run):
- `arm1`: the master's support fixed, shares recomputed inside the plan's band;
- `band`: as arm1, a group without a drawing retried at δ = 0.05, 0.10, 0.15 (`WIDER`);
- `split`: a split unit's ZCTAs may also go to the districts owning a ZCTA next to the unit
  (each extra holder a split, reported);
- `move`: as `split`, with no more holders per unit than the plan.
`--delta` starts every group at that internal band instead of the plan's δ.  `--fixed-targets`
adds each (unit, district) mass within the unit's heaviest ZCTA of the plan's share (the triage's
"fixed targets alone", row 15).  `--sequential` draws one split unit at a time
(`draw._sequential`, adjacent units together when one district enters the second only through
the first), for coupled groups too large to solve jointly: neither a restriction nor a relaxation
of the joint model, so only the audit's M1 judges its maps, and its failures prove nothing.

`contig.json` holds what #109 reports per channel: each group's size, solve status ("optimal"
is proved, "connected" is connected and feasible, "infeasible" is proved, "unknown" is the time
limit), solves, cuts, seconds and gap, the δ each group needed, share-only districts (U61),
exclave splits (D2), districts whose connectivity rests on one connector (U63), and drawn
deviations against τ, and both shape terms per channel (`shape`: the border between districts
inside the drawing's models and the moment tie-break) beside the whole map's border between
districts (`cut_border_km`).
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import hashlib
import importlib.util
import json
import math
import os
import pickle
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import audit, data, geo, master, output, realize, territory  # noqa: E402
from td import spec as tdspec  # noqa: E402


def _load_draw():
    if "contig_draw" in sys.modules:
        return sys.modules["contig_draw"]
    spec = importlib.util.spec_from_file_location("contig_draw", os.path.join(HERE, "draw.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["contig_draw"] = mod
    spec.loader.exec_module(mod)
    return mod


draw = _load_draw()
WIDER = (0.05, 0.10, 0.15)
LANE = "contig"
ARMS = ("arm1", "band", "split", "move")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def plans_for(inst, spec_path: str, extract_path: str | None, cache: str | None, time_limit=None):
    """The master's plans and reports, from `cache` when it holds this spec on this extract and
    this connector list (the polygon graph the master plans on)."""
    key = plans_key(spec_path, extract_path, cache)
    if key:
        if os.path.exists(key):
            with open(key, "rb") as fh:
                return pickle.load(fh)
    plans, reports = master.plan_all(inst, time_limit=time_limit)
    if key and all(p is not None for p in plans.values()):
        os.makedirs(cache, exist_ok=True)
        with open(key, "wb") as fh:
            pickle.dump((plans, reports), fh)
    return plans, reports


def plans_key(spec_path: str, extract_path: str | None, cache: str | None) -> str | None:
    """The pickle `plans_for` caches this spec's plans in, on this extract and connector list."""
    if not (cache and extract_path):
        return None
    graph = sha256(os.path.join(geo.REFERENCE_DIR, "connectors.csv"))[:12]
    return os.path.join(cache, f"{sha256(spec_path)[:16]}_{sha256(extract_path)[:16]}_{graph}.pkl")


def single_connector(owner: dict, adj: dict, connectors: set) -> dict:
    """U63: {district: [connector edges]} for each district whose ZCTAs fall apart without one of
    its internal connector edges."""
    by = collections.defaultdict(set)
    for z, j in owner.items():
        by[j].add(z)
    out = {}
    for j, zs in by.items():
        inside = [(a, b) for a, b in connectors if a in zs and b in zs]
        hit = []
        for a, b in inside:
            seen, stack = {a}, [a]
            while stack:
                x = stack.pop()
                for y in adj[x]:
                    if y in zs and y not in seen and {x, y} != {a, b}:
                        seen.add(y)
                        stack.append(y)
            if b not in seen:
                hit.append(f"{a}-{b}")
        if hit:
            out[j] = sorted(hit)
    return out


def exclave_splits(inst, plan, owner: dict, exclave: set) -> list:
    """D2: (unit, district) for each district owning an exclave ZCTA of a unit it holds no share
    of; each is a split the proposed in-state connectors would save."""
    held = {(v, cp.name) for cp in plan.copies for v in cp.support if cp.mass[v] > 0}
    unit_of = inst.units.unit_of
    return sorted({(unit_of[z], owner[z]) for z in exclave if (unit_of[z], owner[z]) not in held})


def contig_run(spec_path: str, extract_path: str, out: str, arm: str = "arm1",
               fixed_targets: bool = False, time_limit: float = 900.0,
               group_limit: float | None = None, plans_cache: str | None = None,
               source: str = "", keep=(), maps: bool = False, sequential: bool = False,
               delta: float | None = None, log=print, plans_file: str | None = None,
               jobs: int = 1) -> dict:
    if arm not in ARMS:
        raise ValueError(f"arm {arm!r} not in {ARMS}")
    s = tdspec.load(spec_path)
    output.check_file_names("planning channel", s.channels)
    output.check_out(out, keep)
    ref = geo.read_reference()
    extract = data.load(extract_path)
    conus = data.conus(extract, ref)
    ext = tdspec.scope(s, conus)
    polygon = geo.polygon_graph()
    inst = tdspec.build(s, ext, ref)
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    if plans_file:              # the plans a source run drew, on another connector list
        with open(plans_file, "rb") as fh:
            plans, reports = pickle.load(fh)
    else:
        plans, reports = plans_for(inst, spec_path, extract_path, plans_cache)
    plan_seconds = time.time() - t0
    none = sorted(c for c, p in plans.items() if p is None)
    output.write_solver(os.path.join(out, "solver.json"), reports, {},
                        inst.report["components"])
    if none:
        raise output.RunError("no plan for " + ", ".join(none) + " at the declared δ")
    rows = ref.set_index("zcta").loc[sorted(inst.units.unit_of)]
    xy = dict(zip(rows.index, zip(rows["x"].astype(float), rows["y"].astype(float))))
    state = dict(zip(rows.index, rows["state"]))
    connectors = set(geo.approved_connectors(geo.read_connectors()))
    border = draw.border_km(polygon)
    contig, drawings = {}, {}
    drawn = {}
    if jobs > 1:
        drawn = draw_parallel(inst, plans, xy, jobs, border, arm="arm1" if arm == "band" else arm,
                              fixed_targets=fixed_targets, time_limit=time_limit,
                              wider=WIDER if arm == "band" else (), group_limit=group_limit,
                              sequential=sequential, delta=delta)
    for c, p in plans.items():
        log(f"{c}: drawing ({arm}{', fixed targets' if fixed_targets else ''}"
            f"{', sequential' if sequential else ''})")
        res = drawn[c] if c in drawn else draw.draw(
            inst, p, xy, arm="arm1" if arm == "band" else arm, fixed_targets=fixed_targets,
            time_limit=time_limit, wider=WIDER if arm == "band" else (), group_limit=group_limit,
            sequential=sequential, delta=delta, log=log, border=border)
        fallback = None
        if res.undrawn:
            fallback = realize.realize(inst, p, xy)
            territory.own_territory(inst, p, fallback, xy, state)
        d = draw.drawing(inst, p, res, fallback)
        drawings[c] = d
        contig[c] = {
            "status": res.status, "connected": res.connected, "undrawn_zctas": len(res.undrawn),
            "plan_delta": p.delta, "master_status": reports[c]["status"],
            "groups": [g.report() for g in res.groups],
            "group_delta_needed": max((g.delta for g in res.groups if g.delta is not None),
                                      default=p.delta),
            "fixed_split": res.fixed_split, "share_only": res.share_only,
            "shape": shape_terms(res.groups),
            **drawn_stats(inst, p, d, connectors, res.connected, border)}
    report, m1 = write_folder(out, s, inst, ext, ref, polygon, plans, reports, drawings,
                              f"{s.name} (contig {arm}, {source or 'extract'})",
                              f"tools/exp/contig ({arm})", source, maps)
    doc = {"scenario": s.name, "arm": arm, "fixed_targets": fixed_targets,
           "sequential": sequential, "internal_delta": delta, "plans_file": plans_file,
           "plan_seconds": round(plan_seconds, 1), "m1": report["m1"], "channels": contig}
    with open(os.path.join(out, "contig.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    log(f"{s.name} ({arm}): M1 {m1.status} ({m1.summary}); audit {report['verdict']}")
    return doc


# ------------------------------------------------------------------------------ in parallel (#123)
WORKER = "contig_run_worker"        # the name a worker process runs this file under
STOP_GRACE = 30.0                   # seconds a stopped worker gets before its group is killed


def spawn(path: str, name: str, args: tuple, daemon: bool = True) -> tuple:
    """(process, connection) of a worker process running the file `path` under the module name
    `name`, with `WORKER_ARGS` (its end of the connection, *`args`); spawned (macOS), and by
    `runpy`, since a file loaded by path is no importable module."""
    import multiprocessing
    import runpy
    ctx = multiprocessing.get_context("spawn")
    here, there = ctx.Pipe()
    proc = ctx.Process(target=runpy.run_path, args=(path,),
                       kwargs={"run_name": name, "init_globals": {"WORKER_ARGS": (there, *args)}},
                       daemon=daemon)
    proc.start()
    there.close()
    return proc, here


def receive(conn, what: str):
    """A worker's ("done", result) as the result; its ("error", traceback) or death raised."""
    try:
        kind, msg = conn.recv()
    except EOFError:
        raise RuntimeError(f"a {what} worker process died") from None
    if kind == "error":
        raise RuntimeError(f"a {what} worker process failed:\n{msg}")
    return msg


def stop(procs: list, grace: float | None = None) -> None:
    """Stop the worker processes `procs` (`spawn`, none of them joined yet) and join them all.
    Each gets SIGTERM, on which a repair channel closes its `WindowPool` (`repair._serve`); once
    each has exited or `grace` seconds (`STOP_GRACE`) have passed, each one's process group is
    killed, so a worker that leads its own (`os.setpgrp`) takes its descendants with it.  An
    unjoined worker keeps its pid, so its group id is never another's."""
    import signal
    from multiprocessing.connection import wait
    for proc in procs:
        proc.terminate()
    end = time.time() + (STOP_GRACE if grace is None else grace)
    left = [proc.sentinel for proc in procs]
    while left and time.time() < end:
        done = wait(left, max(0.0, end - time.time()))
        left = [s for s in left if s not in done]
    for proc in procs:
        if proc._popen.returncode is None:     # not reaped by `multiprocessing`: still its pid
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()                     # it never led a group
        proc.join()


def pin_threads() -> None:
    """Size this process's HiGHS thread pool at one thread before any other solve (trap 18):
    `draw`'s solves then set `threads` 1, and `td.audit`'s, at HiGHS's default, run in that pool."""
    import highspy
    draw.THREADS = 1
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("threads", 1)
    h.addVar(0.0, 1.0)
    h.run()


def _serve(conn, shared: str, log: bool) -> None:
    """A worker process: `draw.draw` of one channel, HiGHS on one thread; sends the Result."""
    import traceback
    os.setpgrp()                # its own process group, for `stop`
    try:
        with open(shared, "rb") as fh:
            sh = pickle.load(fh)
        pin_threads()
        c, kw = conn.recv()
        conn.send(("done", draw.draw(sh["inst"], sh["plans"][c], sh["xy"], border=sh["border"],
                                     log=lambda line: log and print(line, flush=True), **kw)))
    except BaseException:
        conn.send(("error", traceback.format_exc()))
        raise


def draw_parallel(inst, plans: dict, xy: dict, jobs: int, border=None, log: bool = True,
                  **kw) -> dict:
    """{channel: `draw.Result`} of `draw.draw` with `kw`, each channel in its own process, at
    most `jobs` at once (#123): a channel's drawing reads only its own plan, so the dict is the
    sequential loop's whenever no solve stops on a time limit.  With `log` false the processes
    print nothing."""
    import shutil
    import tempfile
    from multiprocessing.connection import wait
    tmp = tempfile.mkdtemp(prefix="td-draw-")
    out, todo, running = {}, list(plans), {}
    try:
        shared = os.path.join(tmp, "shared.pkl")
        with open(shared, "wb") as fh:
            pickle.dump({"inst": inst, "plans": plans, "xy": xy, "border": border}, fh,
                        protocol=pickle.HIGHEST_PROTOCOL)
        while todo or running:
            while todo and len(running) < jobs:
                c = todo.pop(0)
                proc, conn = spawn(os.path.abspath(__file__), WORKER, (shared, log))
                conn.send((c, kw))
                running[conn] = (c, proc)
            for conn in wait(list(running)):
                c, proc = running[conn]
                out[c] = receive(conn, f"{c} draw")
                del running[conn]               # a failed one stays, for `stop`
                proc.join()
    finally:
        stop([proc for _, proc in running.values()])
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def shape_terms(groups) -> dict:
    """Both shape terms of a channel's drawing (#121), summed over its groups: the border between
    districts inside each group's model (km) and the moment tie-break, unscaled."""
    return {"border_km": math.fsum(g.border_km or 0.0 for g in groups),
            "moment": math.fsum(g.moment or 0.0 for g in groups)}


def drawn_stats(inst, p, d, connectors: set, connected: bool, border: dict | None = None) -> dict:
    """contig.json's per-channel figures of the drawn map `d`: exclave splits (D2), districts
    resting on one connector (U63, when `connected`), deviations against τ, split units,
    vanished shares and, given `border` (`draw.border_km`), the total border between districts on
    the whole map (`cut_border_km`, #121)."""
    _, _, exclave = draw.split_fixed(inst, p)
    ch = inst.channels[p.channel]
    dev = {j: (x - ch.tau) / ch.tau for j, x in d.mass.items()}
    held = collections.defaultdict(set)
    for z, j in d.owner.items():
        held[inst.units.unit_of[z]].add(j)
    return {
        "exclave_splits": [f"{v} {j}" for v, j in exclave_splits(inst, p, d.owner, exclave)],
        "single_connector": single_connector(d.owner, inst.units.zip_adj, connectors)
        if connected else None,
        "worst_dev": max(abs(x) for x in dev.values()),
        "mean_dev": sum(abs(x) for x in dev.values()) / len(dev),
        "split_units": sorted(v for v, js in held.items() if len(js) > 1),
        "vanished_shares": [f"{v} {j}" for v, j in d.vanished],
        "cut_border_km": None if border is None else draw.cut_border(d.owner, inst.units.zip_adj, border)}


def write_folder(out: str, s, inst, ext, ref, polygon, plans, reports, drawings, title: str,
                 realizer: str, source: str, maps: bool, diagnostic: dict | None = None,
                 scenario_bands: dict | None = None) -> tuple:
    """The run folder's ledger, scorecard, districts.csv and run.json from `drawings`;
    (run.json's dict, the M1 check).  A `diagnostic` folder (#121, `audit.diagnostic`'s record)
    says so in run.json; held to a diagnostic band, its scorecard's bands row also gives the
    result at the scenario's bands, `scenario_bands` {channel: (lo, hi, delta)}."""
    areas = output.read_areas()
    led = output.ledger(inst, drawings, ext, ref)
    names = output.name_districts(led, output.cbsa_titles(areas))
    for r in led:
        r["district_name"] = names.get(r["district"], "")
    lpath = output.write_ledger(os.path.join(out, "ledger.csv"), led)
    led = output.read_ledger(lpath)
    with open(os.path.join(geo.REFERENCE_DIR, "MANIFEST.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    split = output.ledger_pieces(led, polygon, drawings)
    arun = output.audit_run(inst, led, drawings, ext, reports, polygon, names, manifest, ref, split,
                            polygon)
    checks = audit.audit(arun)
    if diagnostic is not None and scenario_bands:
        scen = audit.check_bands(dataclasses.replace(arun, channels={
            c: audit.Channel(ch.k, *scenario_bands[c][:2]) if c in scenario_bands else ch
            for c, ch in arun.channels.items()}))
        deltas = "/".join(f"{100 * d:g}%" for d in sorted({b[2] for b in scenario_bands.values()}))
        checks = audit.diagnostic_band_row(checks, diagnostic["band"], scen, deltas)
    audit.write_scorecard(out, checks, title)
    output.write_districts(os.path.join(out, "districts.csv"), inst, plans, drawings, names, split)
    m1 = next(ch for ch in checks if ch.name == audit.M1_CHECK)
    report = {
        "scenario": s.name, "spec": s.path, "source": source, "verdict": audit.verdict(checks),
        "realizer": realizer, "fine_channels": list(s.fine_channels),
        "cells": len(led), "zips": len({r["zip_code"] for r in led}),
        "dropped_units": {c: list(u) for c, u in inst.report.get("dropped_units", {}).items()},
        "dropped_channels": list(inst.dropped_channels),
        "channels": {c: {"k": inst.channels[c].k, "delta": plans[c].delta,
                         "final_delta": inst.channels[c].spec.final_delta,
                         "margin": inst.channels[c].spec.margin,
                         "tier": audit.tier(reports[c]), "status": reports[c]["status"],
                         "vanished": len(d.vanished), **output.piece_counts(split, c)}
                     for c, d in drawings.items()},
        "m1": {"status": m1.status, "summary": m1.summary,
               "coverage": "footprint coverage (D3)"}}
    if diagnostic is not None:
        report.update(diagnostic=True, diagnostic_band=diagnostic["band"],
                      diagnostic_label=diagnostic["label"])
    if maps and output.zcta_file(geo.PUBLIC_DIR) is not None:
        output.draw_maps(lpath, out, ref, areas, geo.PUBLIC_DIR, root=out)
        report["maps"] = "drawn"
    else:
        report["maps"] = "not drawn (python -m td maps <dir> draws them)"
    with open(os.path.join(out, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return report, m1


def _sweep():
    if "exp_sweep" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "exp_sweep", os.path.join(ROOT, "tools", "exp", "sweep.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["exp_sweep"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["exp_sweep"]


def spec_plan(spec_path: str) -> dict:
    """The plan the spec asks for, so a re-planned run's manifest shows its bans, split lists and
    bands (#122)."""
    return {c: {"delta": cs.delta, "final_delta": cs.final_delta,
                "forbid_pairs": sorted("-".join(sorted(p)) for p in cs.forbid_pairs),
                "free": sorted(u for u, m in cs.modes.items() if m == "free")}
            for c, cs in tdspec.load(spec_path).channels.items()}


def write_manifest(out: str, formulation: str, spec_path: str, extract_path: str, params: dict,
                   plans_file: str | None = None, parent: str | None = None,
                   status: str = "running", **more) -> dict:
    """Mandate T1's record of a hand-launched map run (#92's manifest fields): the code's commit
    and dirty flag, the command line, the scenario TOML's path and sha256, the instance and its
    sha256, the plan file and `parent_run` (the run a redraw or repair derives from; manifests
    written before #120 call it `parent`).  Called at the start with status `running` and again at
    the end with `done` or `failed`.  A child of a diagnostic folder (`audit.diagnostic`) is
    diagnostic too (#121)."""
    sw = _sweep()
    path = os.path.join(out, sw.MANIFEST)
    m = sw.read_manifest(out) if os.path.exists(path) else {
        "run_id": os.path.basename(os.path.normpath(out)), "lane": LANE,
        "formulation": formulation, "folder": os.path.abspath(out), "stop_reason": None,
        "params": params, "command": " ".join([sys.executable] + sys.argv),
        "scenario": {"path": os.path.abspath(spec_path), "sha256": sha256(spec_path)},
        "extract": os.path.abspath(extract_path), "plans_file": plans_file,
        "parent_run": parent and os.path.abspath(parent),
        "provenance": {**sw.code_state(), "instance": os.path.abspath(extract_path),
                       "instance_sha256": sha256(extract_path), "host": sw.platform.node(),
                       "queued_at": sw.now()},
        "started_at": sw.now()}
    m.update(status=status, **more)
    up = audit.diagnostic(parent) if parent and not m.get("diagnostic") else None
    if up is not None:
        m.update(diagnostic=True, diagnostic_band=up["band"],
                 diagnostic_label=f"child of the diagnostic folder {os.path.abspath(parent)}")
    if status in sw.FINISHED:
        m["finished_at"] = sw.now()
    os.makedirs(out, exist_ok=True)
    sw.write_manifest(out, m)
    return m


def run_contig(m: dict, folder: str) -> None:
    """The `contig` formulation of `tools/exp/sweep.py`."""
    p = m["params"]
    spec_path = os.path.join(folder, "scenario.toml")
    contig_run(spec_path, m["extract"], folder, p.get("arm", "arm1"),
               bool(p.get("fixed_targets", False)), float(p.get("time_limit", 900)),
               p.get("group_limit"), p.get("plans"), m["provenance"]["instance"],
               keep=tuple(os.listdir(folder)), maps=bool(p.get("maps", False)),
               sequential=bool(p.get("sequential", False)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("spec")
    ap.add_argument("--out", required=True)
    ap.add_argument("--extract", default=os.path.join(os.environ.get("TD_REPO", ROOT),
                                                      "instance_descaled.json.gz"))
    ap.add_argument("--arm", default="arm1", choices=ARMS)
    ap.add_argument("--fixed-targets", action="store_true")
    ap.add_argument("--sequential", action="store_true")
    ap.add_argument("--delta", type=float, default=None,
                    help="the internal band to start from instead of the plan's δ")
    ap.add_argument("--time-limit", type=float, default=900.0)
    ap.add_argument("--group-limit", type=float, default=None)
    ap.add_argument("--plans", default=None, help="a directory caching the master's plans")
    ap.add_argument("--plans-file", default=None,
                    help="a pickle of the plans to draw (a source run's), instead of the master")
    ap.add_argument("--parent", default=None, help="the run this one redraws, for the manifest")
    ap.add_argument("--jobs", type=int, default=1,
                    help="processes (#123): each channel drawn in its own, at most this many at "
                         "once; 1 is the sequential loop")
    ap.add_argument("--maps", action="store_true")
    a = ap.parse_args(argv)
    params = {k: v for k, v in vars(a).items() if k not in ("spec", "out")}
    params["plan"] = spec_plan(a.spec)
    output.check_out(a.out)
    write_manifest(a.out, "contig", a.spec, a.extract, params, a.plans_file, a.parent)
    try:
        doc = contig_run(a.spec, a.extract, a.out, a.arm, a.fixed_targets, a.time_limit,
                         a.group_limit, a.plans, os.path.basename(a.extract), maps=a.maps,
                         sequential=a.sequential, delta=a.delta, plans_file=a.plans_file,
                         keep=("manifest.json",), jobs=a.jobs)
    except Exception as e:
        write_manifest(a.out, "contig", a.spec, a.extract, params, status="failed",
                       stop_reason=f"{type(e).__name__}: {e}")
        raise
    with open(os.path.join(a.out, "run.json"), encoding="utf-8") as fh:
        verdict = json.load(fh)["verdict"]
    write_manifest(a.out, "contig", a.spec, a.extract, params, status="done",
                   stop_reason="drawn", audit=verdict, m1=doc["m1"]["status"])
    return 0 if doc["m1"]["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
elif __name__ == WORKER:
    _serve(*WORKER_ARGS)     # noqa: F821 (set by `spawn`)
