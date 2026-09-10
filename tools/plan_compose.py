"""plan_compose.py -- one multi-channel plan assembled from independent single-channel runs.

    .venv/bin/python3 tools/plan_compose.py --out battery/results/full_problem/composed \\
        --instance instance_descaled_v2.json.gz \\
        battery/results/full_problem/stage_N \\
        battery/results/full_problem/stage_WH \\
        battery/results/full_problem/stage_FI --realise --geo-cache data/geo

`docs/FULL_PROBLEM.md` section 4(b): with the channel plan's bundles fixed, the stage-1 problems
of two bundles share no constraint, so one `tools/full_plan.py` run per bundle group is the same
plan as one run over all of them.  Section 4(c): the only coupling is the rep injection, and
stage 2 over the union of all districts is one Hungarian.  This driver is that consequence made
runnable. A grid solves each channel alone, once, and every combination of those solves is
assembled here in minutes rather than re-solved.

What it does, in order:

    1. reads each input run's `plan.json`, `params.json` and `staffing.json`, and refuses inputs
       that do not agree on the instance, the state list or the synthetic-channel seed, or whose
       *used* bundles are not disjoint (two inputs writing one `projections/<bundle>/`);
    2. writes `plan.json` over the union of the inputs' used slots, with `per_state` and every
       state's `residual_by_channel` recomputed against the union, not against one run;
    3. copies each input's `projections/<bundle>/` into the composed run, so the composed
       directory is what `tools/plan_realise.py` reads and its `cell_graph.json` cache lands
       here rather than in an input;
    4. staffs the union in one `td.stage2_state.state_stage2` pass.  The inputs each staffed
       their own channel from the whole rep pool, so one rep can hold a district in two of them;
       the union's staffing is the honest count and the report names the difference.

An input's own `staffing.json` is read for that comparison and for nothing else; it is not
carried into the composed run.

Overlaps.  Level 0's cover row is per (state, channel) within one run, so nothing stops a WH
run's `WH_PLUS` slot and a national run's `N` slot from both taking a share of one state's
`N_WH`.  Composing them is a plan the projections cannot express (`tools/plan_realise.py` awards
such a cell to the first bundle in sorted order), so the compose refuses unless `--allow-overlap`
says the caller means it.

Deviation from the composed-plan sketch, deliberate: `passes`, `moves` and `anchors` are flat
lists of the inputs' records with a `run` key added, not dicts keyed by run name.
`tools/full_grid.py` reads `plan["passes"]` as a list of dicts and would raise on a dict; the
grouping is recoverable from the tag, so nothing is lost by keeping the shape.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import channels, geo, stage2_state, telemetry                       # noqa: E402
from td import instance as descaled                                         # noqa: E402
import borders_report                                                       # noqa: E402
import full_plan                                                            # noqa: E402

# a state's shares over one channel sum to 1 up to plan.json's 6 decimal places
SHARE_EPS = 1e-6


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("runs", nargs="+", metavar="RUN",
                    help="finished tools/full_plan.py output directories over disjoint bundles")
    ap.add_argument("--out", required=True, help="where the composed run is written")
    ap.add_argument("--instance", required=True,
                    help="the per-cell instance the joint staffing is priced on; must be the "
                         "one the inputs planned against")
    ap.add_argument("--theta", type=float, default=borders_report.THETA)
    ap.add_argument("--lam", type=float, default=borders_report.LAM)
    ap.add_argument("--filler-capture", choices=("theta", "full", "opportunity"),
                    default=borders_report.FILLER_CAPTURE)
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--allow-overlap", action="store_true", default=False,
                    help="compose even when two inputs both take a share of one (state, "
                         "channel) cell; level 2 then awards the cell to one of them")
    ap.add_argument("--realise", action="store_true", default=False,
                    help="run tools/plan_realise.py on the composed directory")
    ap.add_argument("--maps", action="store_true", default=False,
                    help="implies --realise, then tools/plan_maps.py and tools/plan_summary.py")
    return ap


def _read(run_dir: str, name: str, required: bool) -> dict:
    path = os.path.join(run_dir, name)
    if not os.path.exists(path):
        if required:
            raise FileNotFoundError(f"{run_dir} carries no {name}; it is not a finished "
                                    f"tools/full_plan.py run")
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _used(plan: dict) -> list:
    """The slot records level 2 can realise, in plan order.

    Order matters: `tools/full_plan.py::_write_projections` numbered each bundle's
    `state_shares.csv` districts by their position among that bundle's used slots, and
    `tools/plan_realise.py::used_by_bundle` recovers the numbering the same way.  Keeping each
    input's own order inside its bundles is what makes the copied projections still line up.
    """
    return [rec for rec in plan["slots"] if rec["used"] and rec["y"]]


def _load_inputs(run_dirs: list) -> list:
    """One record per input run, checked for the agreements a compose needs."""
    inputs = []
    for run_dir in run_dirs:
        run_dir = os.path.abspath(run_dir)
        plan = _read(run_dir, "plan.json", True)
        params = _read(run_dir, "params.json", False)
        staffing = _read(run_dir, "staffing.json", False)
        used = _used(plan)
        bundles = sorted({rec["bundle"] for rec in used})
        inputs.append(dict(dir=run_dir, name=os.path.basename(run_dir.rstrip(os.sep)),
                           plan=plan, params=params, staffing=staffing, used=used,
                           bundles=bundles,
                           tag="+".join(bundles) or os.path.basename(run_dir.rstrip(os.sep))))

    # a run's basename names it in the report and in `plan["sources"]`; two grid cells can share
    # one, and then the full path is the only name that tells them apart
    names = [inp["name"] for inp in inputs]
    for inp in inputs:
        if names.count(inp["name"]) > 1:
            inp["name"] = inp["dir"]

    seen: dict[str, str] = {}
    for inp in inputs:
        for b in inp["bundles"]:
            if b in seen:
                raise ValueError(f"{inp['dir']} and {seen[b]} both use bundle {b!r}; the inputs "
                                 f"must be runs over disjoint bundles, or one would overwrite "
                                 f"the other's projections/{b}/")
            seen[b] = inp["dir"]
        if not inp["used"]:
            print(f"{inp['name']}: no used slot; its passes are kept and it contributes no "
                  f"district", flush=True)

    for key in ("instance", "synthesize", "seed"):
        vals = {inp["name"]: inp["params"].get(key) for inp in inputs if key in inp["params"]}
        if len({json.dumps(v, sort_keys=True) for v in vals.values()}) > 1:
            raise ValueError(f"the inputs disagree on params[{key!r}]: {vals}; they are not "
                             f"runs over one instance and cannot be composed")

    states = {inp["name"]: (inp["params"].get("state_list") or inp["plan"]["state_list"])
              for inp in inputs}
    if len({tuple(v) for v in states.values()}) > 1:
        raise ValueError(f"the inputs disagree on the state list: "
                         f"{ {n: len(v) for n, v in states.items()} } state(s) each")
    return inputs


def _band(inputs: list):
    """The plan's mass band, carried only when every input solved to the same one.

    Two runs at different `k` have different `tau` and so different `[L, U]`; there is no one
    band for the union, and `tools/plan_realise.py` reads `params["L"]`/`params["U"]` as the
    guard its repair may not push a district outside.  Disagreement leaves it unset.
    """
    bands = {inp["name"]: (inp["params"].get("L"), inp["params"].get("U")) for inp in inputs}
    distinct = set(bands.values())
    if len(distinct) == 1:
        L, U = distinct.pop()
        if L is not None and U is not None:
            return float(L), float(U), bands
    return None, None, bands


def _compose(inputs: list, state_list: list, channel_list: list) -> tuple[dict, list]:
    """The composed `plan.json` and the (state, channel) cells two inputs both take."""
    counts: dict[str, int] = {}
    for inp in inputs:
        for rec in inp["used"]:
            counts[rec["id"]] = counts.get(rec["id"], 0) + 1
    collide = any(n > 1 for n in counts.values())

    slots = []
    for inp in inputs:
        for rec in inp["used"]:
            out = dict(rec)
            if collide:
                out["id"] = f"{inp['tag']}:{rec['id']}"
            out["run"] = inp["name"]
            slots.append(out)

    chans_of = {rec["bundle"]: full_plan._bundle_channels(rec["bundle"]) for rec in slots}

    # a cell two inputs both take is a plan the per-bundle projections cannot express
    by_cell: dict[tuple, dict] = {}
    for inp in inputs:
        for rec in inp["used"]:
            for c in chans_of[rec["bundle"]]:
                for st, share in rec["y"].items():
                    row = by_cell.setdefault((st, c), dict(runs={}, share=0.0))
                    row["runs"].setdefault(inp["name"], []).append(rec["bundle"])
                    row["share"] += float(share)
    overlaps = [dict(state=st, channel=c,
                     runs={n: sorted(set(bs)) for n, bs in row["runs"].items()},
                     share=round(row["share"], 6))
                for (st, c), row in sorted(by_cell.items()) if len(row["runs"]) > 1]

    per_state: dict[str, dict] = {}
    for st in state_list:
        row = {rec["id"]: rec["y"][st] for rec in slots if st in rec["y"]}
        row["residual_by_channel"] = {
            c: round(max(0.0, 1.0 - sum(float(rec["y"].get(st, 0.0)) for rec in slots
                                        if c in chans_of[rec["bundle"]])), 6)
            for c in channel_list}
        per_state[st] = row

    passes, moves, anchors, sources = [], [], [], []
    for inp in inputs:
        passes.extend(dict(p, run=inp["name"]) for p in inp["plan"].get("passes") or ())
        moves.extend(dict(m, run=inp["name"]) for m in inp["plan"].get("moves") or ())
        anchors.extend(dict(a, run=inp["name"]) for a in inp["plan"].get("anchors") or ())
        sources.append(dict(name=inp["name"], dir=inp["dir"], tag=inp["tag"],
                            bundles=inp["bundles"], used_slots=len(inp["used"]),
                            params=inp["params"]))

    bundles = sorted({b for inp in inputs for b in inp["plan"].get("bundles") or inp["bundles"]})
    plan = dict(state_list=list(state_list), bundles=bundles, slots=slots, per_state=per_state,
                passes=passes, moves=moves, anchors=anchors, sources=sources,
                overlaps=overlaps)
    return plan, overlaps


def _copy_projections(inputs: list, out: str) -> list:
    """Each input's `projections/<bundle>/` into the composed run.

    Copied, not linked: `tools/plan_realise.py` caches the bundle's contiguity graph inside the
    projection directory, and a link would write that cache into the input run.
    """
    written = []
    for inp in inputs:
        for bundle in inp["bundles"]:
            src = os.path.join(inp["dir"], "projections", bundle)
            for name in ("instance_descaled.json.gz", "state_shares.csv"):
                if not os.path.exists(os.path.join(src, name)):
                    raise FileNotFoundError(
                        f"{inp['dir']} uses bundle {bundle!r} but has no "
                        f"projections/{bundle}/{name}; level 2 has nothing to cut")
            dest = os.path.join(out, "projections", bundle)
            shutil.copytree(src, dest, dirs_exist_ok=True)
            written.append(dest)
    return written


def run_tool(name: str, argv: list) -> int:
    """One of this repo's own drivers as a subprocess, skipped with a word if it has not landed.

    `tools/plan_summary.py` is written on a sibling track; a compose that asked for it before it
    exists says so and carries on rather than dying after the plan is already on disk.
    """
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        print(f"tools/{name} has not landed yet; skipping it", flush=True)
        return 0
    print(f"running tools/{name} {' '.join(argv)}", flush=True)
    return subprocess.run([sys.executable, "-u", path, *argv], check=True).returncode


def _main(args, T: telemetry.Timings) -> int:
    out = os.path.abspath(args.out)
    inputs = _load_inputs(args.runs)
    state_list = list(inputs[0]["params"].get("state_list")
                      or inputs[0]["plan"]["state_list"])

    named = {inp["params"].get("instance") for inp in inputs if inp["params"].get("instance")}
    if named and os.path.abspath(args.instance) not in {os.path.abspath(p) for p in named}:
        print(f"warning: --instance {os.path.abspath(args.instance)} is not the instance the "
              f"inputs planned against ({sorted(named)}); the joint staffing prices the union "
              f"on the file you passed", flush=True)

    with T.phase("load"):
        print(f"loading {args.instance}...", flush=True)
        d = descaled.load_descaled(args.instance)
        if not d.channels:
            raise ValueError(f"{args.instance} carries one channel; the joint staffing needs a "
                             f"format-2 file (the run's own instance_v2.json.gz will do)")
        if tuple(d.channels) != tuple(channels.CHANNELS):
            d = channels.fine_split(d)
        cells = channels.aggregate(d, state_list)
    channel_list = list(cells.channels)

    plan, overlaps = _compose(inputs, state_list, channel_list)
    L, U, bands = _band(inputs)

    params = dict(driver="plan_compose", instance=os.path.abspath(args.instance),
                  inputs=[inp["dir"] for inp in inputs],
                  theta=args.theta, lam=args.lam, filler_capture=args.filler_capture,
                  criterion="nash", allow_overlap=bool(args.allow_overlap),
                  geo_cache=os.path.abspath(args.geo_cache), out=out,
                  state_list=state_list, channels=channel_list,
                  L=L, U=U, bands_by_input={n: list(b) for n, b in bands.items()})
    with open(os.path.join(out, "params.json"), "w", encoding="utf-8") as fh:
        json.dump(params, fh, indent=2, default=float)
        fh.write("\n")
    if L is None:
        print(f"band: the inputs disagree ({bands}); the composed run carries none and "
              f"tools/plan_realise.py repairs without a band guard", flush=True)

    if overlaps and not args.allow_overlap:
        raise ValueError(
            f"{len(overlaps)} (state, channel) cell(s) are taken by two inputs, the first being "
            f"{overlaps[0]}; the per-bundle projections cannot express that plan (level 2 would "
            f"award the cell to one bundle). Re-run a stage on the residual, or pass "
            f"--allow-overlap to compose anyway")

    with open(os.path.join(out, "plan.json"), "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=2, default=float)
        fh.write("\n")
    _copy_projections(inputs, out)

    with T.phase("stage2"):
        staffing = stage2_state.state_stage2(
            cells, full_plan._plan_object(plan["slots"], state_list),
            theta=args.theta, lam=args.lam, filler_capture=args.filler_capture,
            criterion="nash", candidacy=False)
    with open(os.path.join(out, "staffing.json"), "w", encoding="utf-8") as fh:
        json.dump(staffing, fh, indent=2, default=float)
        fh.write("\n")

    _report(inputs, plan, overlaps, staffing, cells, channel_list)
    print(f"wrote {out}", flush=True)

    if args.realise or args.maps:
        run_tool("plan_realise.py", [out, "--geo-cache", args.geo_cache])
    if args.maps:
        run_tool("plan_maps.py", [out, "--geo-cache", args.geo_cache])
        run_tool("plan_summary.py", [out])
    return 0


def _report(inputs: list, plan: dict, overlaps: list, staffing: dict, cells,
            channel_list: list) -> None:
    """What the compose is worth: the districts, the rep pool, and what is still unserved."""
    per_bundle: dict[str, int] = {}
    for rec in plan["slots"]:
        per_bundle[rec["bundle"]] = per_bundle.get(rec["bundle"], 0) + 1
    print("districts: " + ", ".join(f"{b}={n}" for b, n in sorted(per_bundle.items()))
          + f" (total {len(plan['slots'])})", flush=True)

    alone = {inp["name"]: dict(inp["staffing"].get("assignment") or {}) for inp in inputs}
    twice: dict[str, list] = {}
    for name, assign in alone.items():
        for rep in assign.values():
            twice.setdefault(rep, []).append(name)
    doubled = sorted(r for r, ns in twice.items() if len(ns) > 1)
    print(f"staffed: {len(staffing['assignment'])} of {len(plan['slots'])} against the union, "
          f"{sum(len(a) for a in alone.values())} summed over the inputs staffed alone; "
          f"{len(doubled)} rep(s) held a district in two inputs"
          + (f" ({', '.join(doubled[:8])}{', ...' if len(doubled) > 8 else ''})"
             if doubled else ""), flush=True)
    print(f"reps: {len(staffing['reps'])} in the pool, {len(staffing['unmatched_reps'])} idle, "
          f"{len(staffing['unstaffed_districts'])} district(s) unstaffed; "
          f"value={staffing['value']:.6g}", flush=True)

    if overlaps:
        print(f"overlaps: {len(overlaps)} (state, channel) cell(s) taken by two inputs, "
              f"composed anyway", flush=True)
        for row in overlaps[:8]:
            print(f"  {row['state']}/{row['channel']}: "
                  + ", ".join(f"{n} {'+'.join(bs)}" for n, bs in sorted(row["runs"].items()))
                  + f", share {row['share']:g}", flush=True)
    else:
        print("overlaps: none", flush=True)

    M = np.asarray(cells.M, float)
    for i, c in enumerate(channel_list):
        frac = np.array([float(plan["per_state"][st]["residual_by_channel"][c])
                         for st in cells.state_list], float)
        mass = float((M[:, i] * frac).sum())
        total = float(M[:, i].sum())
        states = sum(1 for st in cells.state_list
                     if plan["per_state"][st]["residual_by_channel"][c] > SHARE_EPS)
        print(f"residual {c}: mass {mass:.6g} of {total:.6g} "
              f"({(mass / total if total > 0 else 0.0):.1%}), {states} state(s)", flush=True)


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    T = telemetry.Timings("plan_compose")
    try:
        return _main(args, T)
    finally:
        T.write(args.out)


if __name__ == "__main__":
    sys.exit(main())
