"""warm.py -- warm start (owner, 2026-10-14) of a sealed point whose strict drawing did not finish:
exact window repair from the first attempt's full drawing, then glue, merge, gate and label.

    "$TD_PY" -u tools/exp/contig/warm.py point ID --main DIR --root DIR [--partition P.json]
        [--run-name N] [--jobs 2] [--budget 3600] [--wait-r1]
    "$TD_PY" tools/exp/contig/warm.py index --root DIR
    "$TD_PY" tools/exp/contig/warm.py render ID --root DIR [--maps DIR]

`point` takes `<main>/<ID>/<run-name>/draw/` (the sealed driver's first draw: `run.py`'s ledger with
`draw.py`'s non-contiguous fallback in the groups it left undrawn) and the point's other runs'
finals from `<main>/SEALED.json` (a run whose drawing finished), and does in `<root>/<ID>/`:

1. `r1/`: `repair.py` pass 1 (`overnight.REPAIR[1]`, `--keep-support --flow`, `--budget`), then `r2/` (pass 2,
   from `r1/`) when a channel of `r1/` is still in pieces or necked.  Every window is exact, with the
   channel's final band, which under the window band is its dollar window.
2. `glue/`: `glue.py` on the last pass.
3. `sealed.Driver.finish` on that folder and the other runs' finals: merge, gate, `score.py` (with `--extract` the
   full dollar extract: the merged extract's rates are 2% off, see `point_state`), `land.py`
   and the shape measures, the label of `sealed.label_point`.  `warm.json` holds the label, the
   undrawn ZCTAs the final ledger still carries per channel (`undrawn_zctas` of the final `contig.json`),
   the pieces and necks left, and the dollar window verdict.

A point whose final ledger still holds ZCTAs `draw.py` handed to the fallback is labelled
`gate-clean, fallback-filled` when the gate passes, never `passes`: the solver did not draw those
ZCTAs and the map is not a deliverable.  `index` writes `<root>/INDEX.md` from the `warm.json` files;
`render` runs `tools/maps/zip_pages.py` on a `passes` point's merged folder into `<root>/<ID>/final/` and, with
`--maps`, copies the summary and the pages PDF there as `MAIN_<ID>_summary.png` and `MAIN_<ID>_pages.pdf`.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import importlib.util
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load(name: str, path: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


sealed = _load("contig_sealed", os.path.join(HERE, "sealed.py"))
overnight = sealed.overnight
HUB = overnight.HUB
FALLBACK = "gate-clean, fallback-filled"
WARM_JSON = "warm.json"
CLEAR = ("passes", FALLBACK)


def warm_repair_cmd(src: str, out: str, plans: str, extract: str, jobs: int, npass: int, label: str, states,
                    budget: float) -> list:
    """`sealed.repair_cmd` with the budget given (sealed's is its stage cap less one window)."""
    cmd = overnight.repair_cmd(src, out, plans, extract, jobs, npass, label)
    return sealed._patched(cmd, "--budget", f"{budget:g}") + ["--states", ",".join(states)]


_SCORE_CMD = overnight.score_cmd


def _score_cmd(folder: str, extract: str) -> list:
    return _SCORE_CMD(folder) + ["--extract", extract]


def run_stage(drv, pid: str, name: str, cmd: list, log: str, cap: float, env=None) -> dict:
    info = drv.stage(pid, name, cmd, log, cap, env)
    print(f"[{pid}] {name}: rc {info['rc']}, stop {info['stop']}", flush=True)
    return info


def point_state(a, pt: dict, rdir: str):
    """(Driver, run name -> final folder) on a grid file of its own in `<root>/<ID>/`."""
    pid = pt["id"]
    with open(os.path.join(a.main, sealed.STATE_JSON), encoding="utf-8") as fh:
        main = json.load(fh)
    extract = main["extract"]
    doc = {"grid": sealed.NAME, "host": main["host"], "created_at": overnight.now(),
           "deadline": datetime.datetime.fromtimestamp(
               datetime.datetime.now().timestamp() + 3600.0 * a.hours, datetime.timezone.utc).isoformat(
               timespec="seconds"),
           "extract": extract, "extract_sha256": main["extract_sha256"], "window_band": True,
           "partition": main["partition"], "code": overnight._sweep().code_state(),
           "limits": {"hours": a.hours, "caps_s": sealed.CAPS}, "points": {}}
    grid = overnight.Grid(os.path.join(rdir, "WARM_STATE.json"), doc)
    grid.add({"id": pid, "structure": pt["structure"], "host": main["host"], "status": "running", "label": None,
              "reason": None, "runs": {}, "stages": {}, "final": None, "summary": None, "started_at": None,
              "finished_at": None,
              "regions": {r["name"]: {"states": list(r["states"]), "ks": r["ks"]} for r in pt["runs"]}})
    cells = overnight.state_cells(extract)
    drv = sealed.Driver(grid, os.path.dirname(rdir), main["host"], extract, cells, {pid: pt}, dict(sealed.CAPS),
                        set(), None, sealed.load_limits(None), True, True)
    drv.plans = os.path.join(a.main, "_plans")
    # the merged extract holds the CONUS cells only, so its rates (owner total over its m_rel total) are 1.02e6, not
    # the dollar extract's 1e6, and score.py would read every district 2% high; the full extract's rates are the ones
    # the plans' windows are in (score.py's docstring: "on a dollar extract that rate is 1e6")
    overnight.score_cmd = lambda folder: _score_cmd(folder, extract)
    return drv, main["points"][pid]


def final_undrawn(folder: str) -> dict:
    """{channel: undrawn ZCTAs} of a folder's contig.json, the channels with some."""
    with open(os.path.join(folder, "contig.json"), encoding="utf-8") as fh:
        ch = json.load(fh)["channels"]
    return {c: v["undrawn_zctas"] for c, v in sorted(ch.items()) if v.get("undrawn_zctas")}


def left_over(folder: str) -> dict:
    """{channel: {"connected", "pieces", "necks_left"}} of a folder's contig.json."""
    with open(os.path.join(folder, "contig.json"), encoding="utf-8") as fh:
        ch = json.load(fh)["channels"]
    return {c: {"connected": v.get("connected"), "necks_left": v.get("necks_left"),
                "repair": [{k: x.get(k) for k in ("kind", "status", "pieces_before", "pieces_after", "h", "zctas",
                                                  "seconds") if k in x}
                           for x in (v.get("repair") or [])][-3:]}
            for c, v in sorted(ch.items())}


def cmd_point(a) -> int:
    pid = a.id
    a.main, a.root = os.path.abspath(a.main), os.path.abspath(a.root)
    pt = next((p for p in sealed.load_partition(a.partition) if p["id"] == pid), None)
    if pt is None:
        raise SystemExit(f"{a.partition}: no point {pid}")
    pdir = os.path.join(a.root, pid)
    os.makedirs(pdir, exist_ok=True)
    drv, rec = point_state(a, pt, pdir)
    run = next(r for r in pt["runs"] if r["name"] == a.run_name)
    src = os.path.join(a.main, pid, run["name"], "draw")
    if not sealed.finished(src):
        raise SystemExit(f"{src}: no finished first drawing to start from")
    plans, extract = drv.plans, drv.extract
    label = f"warm {pid}"
    for npass in (1, 2):
        out = os.path.join(pdir, f"r{npass}")
        if npass == 2 and sealed.clean(src):
            break
        if not sealed.repair_done(out):
            if a.wait_r1 and npass == 1:
                while not sealed.repair_done(out):
                    time.sleep(30)
            else:
                overnight.set_aside(out)
                run_stage(drv, pid, f"r{npass}", warm_repair_cmd(src, out, plans, extract, a.jobs, npass, label,
                                                                run["states"], a.budget),
                          os.path.join(pdir, f"r{npass}.log"), a.budget * 3 + 600)
        if sealed.repair_done(out):
            src = out
    gout = os.path.join(pdir, "glue")
    if not sealed.glue_done(gout):
        overnight.set_aside(gout)
        info = run_stage(drv, pid, "glue", sealed.glue_cmd(src, gout, plans, extract, label, run["states"]),
                         os.path.join(pdir, "glue.log"), 1800.0, sealed.GAP_ENV)
        if info["rc"] != 0:
            raise SystemExit(f"glue.py exited {info['rc']}: see {pdir}/glue.log")
    if os.path.exists(os.path.join(gout, "ledger.csv")):
        src = gout
    finals = {run["name"]: src}
    for r in pt["runs"]:
        if r["name"] != run["name"]:
            fin = rec["runs"][r["name"]].get("final")
            if rec["runs"][r["name"]].get("status") != "done" or not fin:
                raise SystemExit(f"run {r['name']} of {pid} has no finished final in {a.main}")
            finals[r["name"]] = os.path.join(a.main, fin)
    for name, fin in finals.items():
        ks = (rec["runs"][name].get("ks_used") or rec["runs"][name].get("ks"))
        drv.note(pid, name, status="done", final=fin, ks_used=ks)
    drv.finish(pt)
    got = drv.grid.get(pid)
    merged = os.path.join(pdir, "merged")
    undrawn = final_undrawn(src)
    lab = got["label"]
    if lab == "passes" and undrawn:
        lab = FALLBACK
    doc = {"id": pid, "label": lab, "driver_label": got["label"], "reason": got["reason"],
           "run_final": os.path.relpath(src, a.root), "undrawn_zctas": undrawn, "left": left_over(src),
           "summary": got.get("summary"), "merged": os.path.relpath(merged, a.root) if got.get("final") else None,
           "finished_at": overnight.now()}
    overnight._write_json(os.path.join(pdir, WARM_JSON), doc)
    print(f"[{pid}] {lab}" + (f" ({got['reason']})" if got["reason"] else ""), flush=True)
    return 0


# ------------------------------------------------------------------------------ the index
def dollar_rows(merged: str) -> list:
    return overnight.read_dollars(os.path.join(merged, "dollars.csv"))


def worst_position(rows: list) -> str:
    """Per channel, the district nearest a window edge as the fraction of the window it sits at (0 = L, 1 = U)."""
    out = []
    for c in sorted({r["channel"] for r in rows}):
        best = None
        for r in rows:
            if r["channel"] != c or r["usd"] is None or r["lo"] is None:
                continue
            hi = r["cap"] or r["hi"]
            pos = (r["usd"] - r["lo"]) / (hi - r["lo"])
            edge = min(pos, 1 - pos)
            if best is None or edge < best[0]:
                best = (edge, pos, r["district"])
        if best:
            out.append(f"{c} {best[1]:.2f}")
    return ", ".join(out)


def m1_detail(merged: str) -> str:
    with open(os.path.join(merged, "m1.json"), encoding="utf-8") as fh:
        m1 = json.load(fh)
    g = m1["gap_width"]
    return f"{g['status']}: {g['summary']}"


def cmd_index(a) -> int:
    a.root = os.path.abspath(a.root)
    lines = ["# Warm start (2026-10-14): the unsealed grid's undrawn points", "",
             f"Written by `tools/exp/contig/warm.py index` at {overnight.now()}.  A label is `passes` only when the final gate "
             "passes M1 (Manhattan the one allowed exception), every district is inside its channel's dollar window "
             "and no ZCTA in the final ledger is left to `draw.py`'s fallback; `gate-clean, fallback-filled` is not a "
             "deliverable.", "",
             "| point | label | M1 | districts in window | worst $ position in window (0 = L, 1 = U) | split states | undrawn ZCTAs in the final ledger |",
             "|---|---|---|---|---|---|---|"]
    notes = []
    for pid in sorted(d for d in os.listdir(a.root) if os.path.exists(os.path.join(a.root, d, WARM_JSON))):
        with open(os.path.join(a.root, pid, WARM_JSON), encoding="utf-8") as fh:
            w = json.load(fh)
        merged = os.path.join(a.root, w["merged"]) if w["merged"] else None
        if merged and os.path.exists(os.path.join(merged, "dollars.csv")):
            rows = dollar_rows(merged)
            inw = ", ".join(f"{c} {sum(1 for r in rows if r['channel'] == c and r['ok'])}/"
                            f"{sum(1 for r in rows if r['channel'] == c)}" for c in sorted({r['channel'] for r in rows}))
            worst, m1 = worst_position(rows), m1_detail(merged)
            spl = (w.get("summary") or {}).get("splits")
        else:
            inw = worst = m1 = spl = "—"
        und = ", ".join(f"{c} {n}" for c, n in w["undrawn_zctas"].items()) or "0"
        lines.append(f"| {pid} | **{w['label']}** | {m1} | {inw} | {worst} | {spl} | {und} |")
        notes.append(f"- **{pid}**: {w['reason'] or 'no reason'}; final `{w['run_final']}`; merged `{w['merged']}`")
    lines += ["", "## Details", *notes, ""]
    with open(os.path.join(a.root, "INDEX.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(os.path.join(a.root, "INDEX.md"))
    return 0


def cmd_render(a) -> int:
    a.root = os.path.abspath(a.root)
    zp = _load("maps_zip_pages", os.path.join(ROOT, "tools", "maps", "zip_pages.py"))
    fac = overnight.fac_file(a.root)
    with open(os.path.join(a.root, a.id, WARM_JSON), encoding="utf-8") as fh:
        w = json.load(fh)
    if w["label"] not in a.labels:
        raise SystemExit(f"{a.id}: label {w['label']!r} is not one of {a.labels}; not rendered")
    out = os.path.join(a.root, a.id, "final")
    os.makedirs(out, exist_ok=True)
    paths = zp.main([os.path.join(a.root, w["merged"]), f"{a.id}: {w['label']}", out, "--fac", fac])
    print("\n".join(map(str, paths)))
    if a.maps:
        os.makedirs(a.maps, exist_ok=True)
        shutil.copy(os.path.join(out, "zip_summary.png"), os.path.join(a.maps, f"MAIN_{a.id}_summary.png"))
        shutil.copy(os.path.join(out, "zip_pages.pdf"), os.path.join(a.maps, f"MAIN_{a.id}_pages.pdf"))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tools/exp/contig/warm.py", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("point", help="repair, glue, merge, gate and label one point")
    p.add_argument("id")
    p.add_argument("--main", required=True, help="the sealed root holding the first attempt (SEALED.json, _plans)")
    p.add_argument("--root", required=True, help="where the warm start writes <ID>/")
    p.add_argument("--partition", default=None, help="default the one SEALED.json names")
    p.add_argument("--run-name", default="rest-FI-WH-national")
    p.add_argument("--jobs", type=int, default=2)
    p.add_argument("--budget", type=float, default=3600.0, help="repair.py --budget per channel per pass")
    p.add_argument("--hours", type=float, default=12.0)
    p.add_argument("--wait-r1", action="store_true", help="r1/ is being written by a repair.py already running")
    p.set_defaults(func=cmd_point)
    i = sub.add_parser("index", help="write <root>/INDEX.md")
    i.add_argument("--root", required=True)
    i.set_defaults(func=cmd_index)
    r = sub.add_parser("render", help="zip_pages.py on a passing point's merged folder")
    r.add_argument("id")
    r.add_argument("--root", required=True)
    r.add_argument("--maps", default=None, help="copy zip_summary.png and zip_pages.pdf here as MAIN_<ID>_*")
    r.add_argument("--labels", nargs="*", default=["passes"])
    r.set_defaults(func=cmd_render)
    a = ap.parse_args(argv)
    if a.cmd == "point" and a.partition is None:
        with open(os.path.join(a.main, sealed.STATE_JSON), encoding="utf-8") as fh:
            a.partition = json.load(fh)["partition"]["path"]
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
