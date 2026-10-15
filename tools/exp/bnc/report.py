"""report.py -- `REPORT.md` of a `run.py` output folder (#142, A3).

    "$TD_PY" tools/exp/bnc/report.py [<out>]        # default $TD_REPO/runs/exp/bnc_2026-10-15

Reads `<out>/<instance>/<arm>/result.json` and `<out>/instances/INDEX.json`; writes `<out>/REPORT.md`:
the instances (size, the exported group's checks), one row per (instance, arm) with status, time,
final gap, nodes, M1 of the group's districts on the merged full map and whether every district
of the group is in its dollar window, the lazy-callback probe, and the winner per instance (the
fastest arm with status `optimal`, else the best `feasible` objective, else "no arm finished").
"""
from __future__ import annotations

import glob
import json
import os
import sys

TD_REPO = os.environ.get("TD_REPO", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
OUT = os.path.join(TD_REPO, "runs", "exp", "bnc_2026-10-15")
ARM_NAMES = {"a": "a: draw.py complete model (dag False, flow + cuts)",
             "b": "b: HiGHS solve-separate-resolve (integer cuts)",
             "c": "c: PySCIPOpt constraint handler (lazy cuts)",
             "d": "d: HiGHS lazy-constraint callback"}


def _fmt(x, nd=1):
    return "-" if x is None else f"{x:.{nd}f}"


def _gap(x):
    return "-" if x is None else f"{100 * x:.3g}%"


def rows(out: str) -> list:
    res = []
    for path in sorted(glob.glob(os.path.join(out, "*", "*", "result.json"))):
        with open(path, encoding="utf-8") as fh:
            r = json.load(fh)
        res.append(r)
    return res


def table(rs: list) -> str:
    lines = ["| instance | arm | status | time (s) | gap | nodes | objective | M1 (group's districts) | in window |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rs, key=lambda r: (r["instance"], r["arm"])):
        g = r.get("gate")
        m1 = "no drawing" if g is None else (f"{g['m1']} (map: {g['map_m1']})" if g["m1"] == "pass"
                                              else f"**FAIL** ({len(g['m1_items'])} items)")
        win = "-" if g is None else ("yes" if g["in_window"] else "**NO**")
        lines.append(f"| {r['instance']} | {r['arm']} | {r['status']} | {_fmt(r['seconds'])} | {_gap(r['gap'])} | "
                     f"{r['nodes'] if r['nodes'] is not None else '-'} | {_fmt(r['objective'], 4)} | {m1} | {win} |")
    return "\n".join(lines)


def winners(rs: list) -> list:
    out = []
    for inst in sorted({r["instance"] for r in rs}):
        mine = [r for r in rs if r["instance"] == inst]
        ok = [r for r in mine if r["status"] == "optimal" and r.get("gate") and r["gate"]["m1"] == "pass"
              and r["gate"]["in_window"]]
        opt = [r for r in mine if r["status"] == "optimal"]
        feas = [r for r in mine if r["status"] == "feasible" and r["objective"] is not None]
        inf = [r for r in mine if r["status"] == "infeasible"]
        if ok:
            w = min(ok, key=lambda r: r["seconds"])
            out.append(f"- **{inst}**: arm {w['arm']} proved an optimum in {w['seconds']:.0f} s "
                       f"(objective {w['objective']:.6g}); its drawing passes M1 and the window.")
        elif opt:
            w = min(opt, key=lambda r: r["seconds"])
            out.append(f"- **{inst}**: arm {w['arm']} proved an optimum in {w['seconds']:.0f} s, but the drawing "
                       f"fails the gate (M1 {w.get('gate', {}).get('m1')}, window {w.get('gate', {}).get('in_window')}): a failure, not a result.")
        elif inf:
            w = min(inf, key=lambda r: r["seconds"])
            out.append(f"- **{inst}**: arm {w['arm']} proved that no connected drawing exists in the group "
                       f"under the model's rules ({w['seconds']:.0f} s).")
        elif feas:
            w = min(feas, key=lambda r: r["objective"])
            out.append(f"- **{inst}**: no arm proved an optimum; the best connected drawing is arm {w['arm']}'s "
                       f"(objective {w['objective']:.6g}, gap {_gap(w['gap'])}).")
        else:
            out.append(f"- **{inst}**: no arm finished (no connected drawing in the time limit).")
    return out


def write(out: str = OUT, instances: str | None = None) -> str:
    rs = rows(out)
    index = os.path.join(instances or os.path.join(out, "instances"), "INDEX.json")
    lines = ["# #142 phase 0: exact ZIP drawing by lazy connectivity cuts, report", ""]
    if rs:
        r0 = rs[0]
        lines += [f"Time limit {r0['time_limit']:g} s per run, {r0['threads']} thread(s) for the HiGHS arms "
                  f"(SCIP runs one), one process per run, `mip_rel_gap` 0, absolute gap 1e-6; "
                  f"code commit {r0['code_commit']}.", ""]
    if os.path.exists(index):
        with open(index, encoding="utf-8") as fh:
            idx = json.load(fh)
        lines += ["## Instances", "",
                  "| instance | host | districts | free ZCTAs | columns | rows | window ($M) | faithful to the run's group | round trip |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for k, m in idx.items():
            f, t = m["faithful"], m["roundtrip"]
            lines.append(f"| {k} | {m['host']} | {len(m['districts'])} | {m['free_zctas']} | {m['base_counts']['columns']} | "
                         f"{m['base_counts']['rows']} | {m['band'][0]:.0f}-{m['band'][1]:.0f} | "
                         f"{'yes' if f['ok'] else 'NO'} (columns {f['columns'][0]}/{f['columns'][1]}, rows {f['rows'][0]}/{f['rows'][1]}) | "
                         f"{'ok' if t['ok'] else 'FAILED'} (objective max |diff| {t['objective_max_abs_diff']:.2g}) |")
        lines.append("")
    lines += ["## Results", "", table(rs), "", "## Winner per instance", ""] + winners(rs) + [""]
    notes = [r for r in rs if r.get("note")]
    if notes:
        lines += ["## Notes", ""] + [f"- {r['instance']} arm {r['arm']}: {r['note']}" for r in sorted(
            notes, key=lambda r: (r["instance"], r["arm"]))] + [""]
    for r in rs:
        if r["arm"] == "d" and r.get("probe"):
            lines += ["## Arm d: the highspy lazy-constraint probe", "", r["probe"]["observed"], ""]
            break
    checks = sorted(glob.glob(os.path.join(out, "*", "verify*.json")))
    if checks:
        lines += ["## Independent checks (`verify.py`: SCIP on the flow formulation, no cuts)", ""]
        for path in checks:
            with open(path, encoding="utf-8") as fh:
                v = json.load(fh)
            lines.append(f"- {v['instance']}: SCIP status `{v['scip_status']}`, {v['seconds']:.0f} s, {v['nodes']} nodes, "
                         f"limit {v.get('time_limit', '?')} s" + ("" if v["objective"] is None else
                         f", objective {v['objective']:.6g}, connected {v['connected']}"))
        lines.append("")
    gaps = [r for r in rs if r.get("gate") and r["gate"]["other_districts_outside_window"]]
    if gaps:
        lines += ["## Context", "", "Districts of the source map outside the group (not the arm's):", ""] + [
            f"- {r['instance']}: {r['gate']['other_districts_outside_window']}" for r in gaps[:4]] + [""]
    path = os.path.join(out, "REPORT.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


if __name__ == "__main__":
    print(write(sys.argv[1] if len(sys.argv) > 1 else OUT))
