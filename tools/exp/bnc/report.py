"""report.py -- `REPORT.md` of a `run.py` output folder (#142, A3).

    "$TD_PY" tools/exp/bnc/report.py [<out>]        # default $TD_REPO/runs/exp/bnc_2026-10-15

Reads `<out>/<instance>/<arm>/result.json` and `<out>/instances/INDEX.json`; writes `<out>/REPORT.md`:
the instances (size, the exported group's checks), one row per (instance, arm) with status, time,
final gap, nodes, M1 of the merged full map (less pre-existing failures outside the group) and whether every district
of the group is in its dollar window, the lazy-callback probe, and the winner per instance (the
fastest arm with status `optimal`, else the best `feasible` objective, else "no arm finished").

Only results of one campaign are tabled: the newest result (`finished`) names the code commit and
dirty flag, the source fingerprint (`export.source_fingerprint`, recorded before the solve: the content
of the sources, which a commit and a dirty flag do not fix), time limit and threads, and a result is
stale when it records no fingerprint, when any of them differs, when its settings differ from the
newest result of the same arm, or when it cannot be tied to its instance: no recorded sha256, or no
file with that sha256 (looked for in the `instances` argument, else the path the run recorded, else
`<out>/instances`).  Stale results (an arm not rerun after a subset rerun) are listed
under "Stale results excluded" and never reach the table or the winners.

An independent check (`verify.py`'s `verify*.json`) is listed only when it recorded its code commit,
its source fingerprint and the sha256 of its instance, that file is available and still has the
sha256, no tabled result of the instance was made on another file, and its fingerprint is the
campaign's (that of the tabled results); the others are listed under "Independent checks
excluded".
"""
from __future__ import annotations

import glob
import hashlib
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


def drew(r: dict) -> bool:
    """The arm returned a drawing."""
    return r["status"] in ("optimal", "feasible")


def passes(r: dict) -> bool:
    """The drawing has a gate result and passes M1 and the dollar windows."""
    g = r.get("gate")
    return bool(g) and g["m1"] == "pass" and bool(g["in_window"])


def _load(out: str) -> list:
    res = []
    for path in sorted(glob.glob(os.path.join(out, "*", "*", "result.json"))):
        with open(path, encoding="utf-8") as fh:
            res.append(json.load(fh))
    return res


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _instance_why(r: dict, out: str, instances: str | None, name: str) -> str:
    """Why `r` (a result or a check, naming its instance) cannot be tied to its instance file, else ''."""
    want = r.get("instance_sha256")
    if not want:
        return "no instance sha256 recorded"
    path = (os.path.join(instances, f"{name}.json.gz") if instances else r.get("instance_path")
            or os.path.join(out, "instances", f"{name}.json.gz"))
    if not os.path.isfile(path):
        return f"instance file {path} not available"
    if _sha256(path) != want:
        return "instance file changed"
    return ""


def split(out: str, instances: str | None = None) -> tuple:
    """(results of the campaign, [(stale result, why)]) of the results under `out`."""
    allr = _load(out)
    if not allr:
        return [], []
    newest = max(allr, key=lambda r: r.get("finished", ""))
    arm_newest = {}
    for r in sorted(allr, key=lambda r: r.get("finished", "")):
        arm_newest[r["arm"]] = r
    fresh, stale = [], []
    for r in allr:
        why = [] if r.get("source_sha256") else ["no source fingerprint recorded"]
        why += [f"{k} {r.get(k)!r} != {newest.get(k)!r}"
                for k in ("code_commit", "code_dirty", "source_sha256", "time_limit", "threads")
                if r.get(k) != newest.get(k)]
        if r.get("settings") != arm_newest[r["arm"]].get("settings"):
            why.append(f"settings {r.get('settings')!r} != {arm_newest[r['arm']].get('settings')!r}")
        bad = _instance_why(r, out, instances, r["instance"])
        if bad:
            why.append(bad)
        (stale if why else fresh).append((r, "; ".join(why)) if why else r)
    return fresh, stale


def checks(out: str, instances: str | None = None, rs: list | None = None) -> tuple:
    """([verification results to list], [(path, why not)]) of `<out>/*/verify*.json`; `rs` are the
    tabled results (default: those of `split`)."""
    rs = rows(out, instances) if rs is None else rs
    shas = {}
    for r in rs:
        shas.setdefault(r["instance"], set()).add(r.get("instance_sha256"))
    sources = {r.get("source_sha256") for r in rs}
    ok, bad = [], []
    for path in sorted(glob.glob(os.path.join(out, "*", "verify*.json"))):
        try:
            with open(path, encoding="utf-8") as fh:
                v = json.load(fh)
            why = [] if v.get("code_commit") else ["no code commit recorded"]
            if not v.get("source_sha256"):
                why.append("no source fingerprint recorded")
            elif sources and sources != {v["source_sha256"]}:
                why.append("made on other source code than the tabled results")
            why += [w for w in (_instance_why(v, out, instances, v["instance"]),) if w]
            if v.get("instance_sha256") and shas.get(v["instance"], {v["instance_sha256"]}) != {v["instance_sha256"]}:
                why.append("the tabled results of the instance were made on another file")
        except (OSError, ValueError, KeyError) as e:
            v, why = None, [f"unreadable ({type(e).__name__}: {e})"]
        (bad if why else ok).append((path, "; ".join(why)) if why else v)
    return ok, bad


def rows(out: str, instances: str | None = None) -> list:
    """The results of the campaign (`split`)."""
    return split(out, instances)[0]


def table(rs: list) -> str:
    lines = ["| instance | arm | status | time (s) | gap | nodes | objective | M1 | in window |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rs, key=lambda r: (r["instance"], r["arm"])):
        g = r.get("gate")
        if g is None:
            m1 = win = "**UNGATED**" if drew(r) else "-"
        else:
            m1 = (f"{g['m1']} (map: {g['map_m1']})" if g["m1"] == "pass"
                  else "**UNGATED**" if g["m1"] == "ungated" else f"**FAIL** ({len(g['m1_items'])} items)")
            win = "yes" if g["in_window"] else "**NO**"
        lines.append(f"| {r['instance']} | {r['arm']} | {r['status']} | {_fmt(r['seconds'])} | {_gap(r['gap'])} | "
                     f"{r['nodes'] if r['nodes'] is not None else '-'} | {_fmt(r['objective'], 4)} | {m1} | {win} |")
    return "\n".join(lines)


def winners(rs: list) -> list:
    out = []
    for inst in sorted({r["instance"] for r in rs}):
        mine = [r for r in rs if r["instance"] == inst]
        ok = [r for r in mine if r["status"] == "optimal" and passes(r)]
        feas = [r for r in mine if r["status"] == "feasible" and r["objective"] is not None and passes(r)]
        inf = [r for r in mine if r["status"] == "infeasible"]
        bad = [r for r in mine if drew(r) and not passes(r)]
        if ok:
            w = min(ok, key=lambda r: r["seconds"])
            out.append(f"- **{inst}**: arm {w['arm']} proved an optimum in {w['seconds']:.0f} s "
                       f"(objective {w['objective']:.6g}); its drawing passes M1 and the window.")
        elif inf:
            w = min(inf, key=lambda r: r["seconds"])
            out.append(f"- **{inst}**: arm {w['arm']} proved that no connected drawing exists in the group "
                       f"under the model's rules ({w['seconds']:.0f} s).")
        elif feas:
            w = min(feas, key=lambda r: r["objective"])
            out.append(f"- **{inst}**: no arm proved an optimum; the best connected drawing that passes M1 and "
                       f"the window is arm {w['arm']}'s (objective {w['objective']:.6g}, gap {_gap(w['gap'])}).")
        else:
            out.append(f"- **{inst}**: no arm finished (no drawing that passes M1 and the window in the time limit).")
        for r in sorted(bad, key=lambda r: r["arm"]):
            g = r.get("gate")
            what = ("UNGATED: no gate result, so the drawing counts for nothing" if g is None else
                    "UNGATED: the gate could not verify the merged map, so the drawing counts for nothing"
                    if g["m1"] == "ungated" else
                    f"fails the gate (M1 {g['m1']}, in window {g['in_window']}): a failure, not a result")
            out.append(f"  - arm {r['arm']} ({r['status']}, objective {_fmt(r['objective'], 6)}): {what}.")
    return out


def write(out: str = OUT, instances: str | None = None) -> str:
    rs, stale = split(out, instances)
    index = os.path.join(instances or os.path.join(out, "instances"), "INDEX.json")
    lines = ["# #142 phase 0: exact ZIP drawing by lazy connectivity cuts, report", ""]
    if rs:
        r0 = rs[0]
        lines += [f"Time limit {r0['time_limit']:g} s per run, {r0['threads']} thread(s) for the HiGHS arms "
                  f"(SCIP runs one), one process per run, `mip_rel_gap` 0, absolute gap 1e-6; "
                  f"code commit {r0['code_commit']}, source fingerprint {r0['source_sha256'][:12]}.", ""]
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
    if stale:
        lines += ["## Stale results excluded", "", "Not of the campaign of the newest result; rerun the arm to table it:", ""]
        lines += [f"- {r['instance']} arm {r['arm']} ({r.get('finished', '?')}): {why}" for r, why in sorted(
            stale, key=lambda t: (t[0]["instance"], t[0]["arm"]))] + [""]
    notes = [r for r in rs if r.get("note")]
    if notes:
        lines += ["## Notes", ""] + [f"- {r['instance']} arm {r['arm']}: {r['note']}" for r in sorted(
            notes, key=lambda r: (r["instance"], r["arm"]))] + [""]
    for r in rs:
        if r["arm"] == "d" and r.get("probe"):
            lines += ["## Arm d: the highspy lazy-constraint probe", "", r["probe"]["observed"], ""]
            break
    good, unverified = checks(out, instances, rs)
    if good:
        lines += ["## Independent checks (`verify.py`: SCIP on the flow formulation, no cuts)", ""]
        for v in good:
            lines.append(f"- {v['instance']}: SCIP status `{v['scip_status']}`, {v['seconds']:.0f} s, {v['nodes']} nodes, "
                         f"limit {v.get('time_limit', '?')} s" + ("" if v["objective"] is None else
                         f", objective {v['objective']:.6g}, connected {v['connected']}"))
        lines.append("")
    if unverified:
        lines += ["## Independent checks excluded", "",
                  "Not tied to the instance file and code of the campaign; rerun `verify.py`:", ""]
        lines += [f"- {os.path.relpath(p, out)}: {why}" for p, why in unverified] + [""]
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
