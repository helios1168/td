"""check.py -- the run-folder gate for mandate M1, ZIP contiguity (#108, `docs/problem/MANDATES.md`).

    "$TD_PY" tools/mandates/check.py <run_dir> [<run_dir> ...]
    "$TD_PY" tools/mandates/check.py --rescore <root> [--out DIR] [--write-register]
    "$TD_PY" tools/mandates/check.py --tracking [--base DIR] [--registry PATH] [--write-register]

`m1(run_dir)` reads a drawn run's `ledger.csv` and `districts.csv` (the layout `python -m td run`
writes) and returns M1's verdict: `td.audit.check_m1` on the ledger with the committed polygon graph
and its owner-approved connectors only (`td.geo.polygon_graph`).  It is strict: a detached piece,
a neck (#121) or a CONUS ZCTA not owned once per fine channel fails the run, with no tolerance;
`necks` lists each neck as `td.audit.neck_item` words it, and `mass_necks` the necks by mass
the check lists beside M1 for the owner (#121), which fail nothing.  The fine
channels are the scenario's, from `run.json` (#116); a run from before #116 has none there, and
its summary says the ledger's were read instead.  It also gives
each district's largest detached piece as the looks scorer sizes it (`tools/looks/score.py`), in
mass over τ_c: on the ledger, which owns every ZCTA since #116, so no display fill sizes a piece
and the scorer's pieces are the check's.  The CLI prints one line per run and exits 1 when any run fails
or is diagnostic (#121, `td.audit.diagnostic`: printed DIAGNOSTIC, never a deliverable).

`--rescore <root>` gates and scores every run folder under `root` (a folder with `ledger.csv` and
`districts.csv`), writes `TABLE.md` and `rescore.json` to `--out`, and with `--write-register`
writes M1's latest value into `docs/problem/MANDATES.md`: the scorer's rank-1 run over all
rescored runs and its largest detached piece, and the smallest largest piece across runs (owner,
2026-10-05).  This is the only writer of that field.

`--tracking` is mandate T1's check (#120, `tracking`): it fails a run folder under
`<base>/runs/exp/` with a `ledger.csv` and no `manifest.json`; a shortlist entry
(`tools/shortlist/shortlist.json`) whose run folder, manifest or an image is missing, whose image
is not `tools/maps/render.py`'s output in its run folder (outside the folder, not in its
`render.json`, no `render.json`, or a stale one), or whose recorded M1 differs from a fresh run of
the gate; and an id used by more than one entry.  `<base>` is `$TD_REPO` by default.  With
`--write-register` it writes the result as T1's latest value, the only writer of that field.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import importlib.util
import json
import os
import platform
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import audit                       # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "looks_score", os.path.join(ROOT, "tools", "looks", "score.py"))
score = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score)

REGISTER = os.path.join(ROOT, "docs", "problem", "MANDATES.md")
COMMAND = "tools/mandates/check.py --rescore"
TRACKING = "tools/mandates/check.py --tracking"


def _read(run_dir: str, name: str) -> list:
    with open(os.path.join(run_dir, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def run_dirs(root: str) -> list:
    """Every folder under `root` holding a `ledger.csv` and a `districts.csv`, sorted."""
    return sorted(d for d, _, fs in os.walk(root) if {"ledger.csv", "districts.csv"} <= set(fs))


def m1(run_dir: str, g=None) -> dict:
    """M1 on one run folder: `status` (`pass`, `fail` or `unverified`), the strict check, the
    scorer's pieces and the largest (`largest`: channel, district, ZIPs, mass / τ, states), or
    None when no district is in pieces; `diagnostic`, `td.audit.diagnostic`'s record or None (a
    diagnostic folder is never a deliverable: the CLI prints DIAGNOSTIC and exits 1, #121).  `g` defaults to the committed geography."""
    g = g or score.geography()
    ledger, districts = _read(run_dir, "ledger.csv"), _read(run_dir, "districts.csv")
    ks = {}
    for r in districts:
        ks[r["channel"]] = ks.get(r["channel"], 0) + 1
    check = score.m1_check(ledger, ks, g, score.fine_channels(run_dir))
    pieces = []
    if g.polygon_adj is not None:
        for ch in sorted(ks):
            looks = score.channel_looks(ch, ledger, districts, g)
            pieces += [(ch, *p) for p in looks["pieces"]]
    largest = max(pieces, key=lambda p: (p[3], p[2], p[1]), default=None)
    return {"run": run_dir, "status": check.status, "summary": check.summary, "check": check,
            "diagnostic": audit.diagnostic(run_dir),
            "scorer_pieces": len(pieces), "largest": largest,
            "necks": [i for i in check.items if score.NECK.search(i)],
            "mass_necks": [i for i in check.items if audit.MASS_NECK in i]}


def _piece(p) -> str:
    return "none" if p is None else f"{p[3]:.3f} τ ({p[0]}/{p[1]}, {p[2]} ZIPs in {p[4]})"


def rescore(root: str, g=None) -> dict:
    """M1 and the looks scorer on every run folder under `root`; `best` is the scorer's rank-1
    run and `smallest` the run with the smallest largest piece."""
    g = g or score.geography()
    rows = []
    for d in run_dirs(root):
        gate = m1(d, g)
        try:
            s = score.score(d, g)
            err = None
        except Exception as e:              # a run the scorer cannot read still gets M1
            s, err = None, f"{type(e).__name__}: {e}"
        rows.append({"run": os.path.relpath(d, root), "m1": gate["status"],
                     "diagnostic": gate["diagnostic"],
                     "summary": gate["summary"], "largest": gate["largest"],
                     "scorer_pieces": gate["scorer_pieces"], **gate["check"].counts,
                     "neck_items": gate["necks"], "mass_neck_items": gate["mass_necks"],
                     "score": s, "scorer_error": err})
    scored = score.rank([r["score"] for r in rows if r["score"] is not None])
    order = {id(s): i for i, s in enumerate(scored, 1)}
    for r in rows:
        r["rank"] = order.get(id(r["score"])) if r["score"] is not None else None
    best = next((r for r in rows if r["rank"] == 1), None)
    smallest = min(rows, key=lambda r: (r["largest"][3] if r["largest"] else 0.0, r["run"]),
                   default=None)
    return {"root": root, "rows": rows, "best": best, "smallest": smallest}


def table(res: dict) -> str:
    rows = sorted(res["rows"], key=lambda r: (r["rank"] is None, r["rank"] or 0, r["run"]))
    n_fail = sum(r["m1"] == "fail" for r in rows)
    lines = [f"# M1 rescore of `{res['root']}` ({datetime.date.today().isoformat()}, `{COMMAND}`)",
             "", f"{len(rows)} runs, {n_fail} fail M1, {len(rows) - n_fail} do not fail.  M1 is strict, "
             "on the ledger and the committed polygon graph with approved connectors only, with no "
             "display fill (#116); the largest piece is in mass over τ_c.", "",
             "| rank | run | M1 | largest detached piece | necks | districts in pieces / pieces / "
             "channel ZCTAs with no owner / (ZCTA, fine channel) cells with no row |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        diag = " DIAGNOSTIC" if r.get("diagnostic") else ""
        lines.append(f"| {r['rank'] or '-'} | `{r['run']}` | {r['m1']}{diag} | {_piece(r['largest'])} | "
                     f"{r.get('necks', '-')} | {r.get('split', '-')} / {r.get('pieces', '-')} / "
                     f"{r.get('no_owner', '-')} / {r.get('no_row', '-')} |")
    errors = [r for r in rows if r["scorer_error"]]
    if errors:
        lines += ["", "Not ranked (the scorer could not read the run):", ""]
        lines += [f"- `{r['run']}`: {r['scorer_error']}" for r in errors]
    return "\n".join(lines) + "\n"


def latest_value(res: dict) -> str:
    """M1's latest value for the register (module doc)."""
    rows, best, small = res["rows"], res["best"], res["smallest"]
    n_fail = sum(r["m1"] == "fail" for r in rows)
    text = (f"{n_fail} of {len(rows)} drawn runs fail ({datetime.date.today().isoformat()}, "
            f"`{COMMAND}`, #108).")
    if best:
        text += (f" Best map, the scorer's rank 1: `{best['run']}`, M1 {best['m1']}, largest "
                 f"detached piece {_piece(best['largest'])}; on the ledger {best.get('pieces', 0)} "
                 f"detached pieces, {best.get('necks', 0)} necks, {best.get('no_owner', 0)} channel "
                 f"ZCTAs with no owner and {best.get('no_row', 0)} (ZCTA, fine channel) cells with "
                 "no row.")
    text += f" Runs with a neck (#121): {sum(1 for r in rows if r.get('necks'))} of {len(rows)}."
    if small:
        text += f" Smallest largest piece across runs: {_piece(small['largest'])}, `{small['run']}`."
    return text


def _load(name: str, *parts):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *parts))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


def tracking(base: str, registry: str | None = None, gate=None) -> list:
    """Mandate T1's failures (module doc) under `base`, one line each; [] passes.  `gate(run_dir)`
    gives a fresh M1 status (default `m1`'s)."""
    build = _load("shortlist_build", "tools", "shortlist", "build.py")
    render = _load("maps_render", "tools", "maps", "render.py")
    if gate is None:
        g = score.geography()
        gate = lambda d: m1(d, g)["status"]       # noqa: E731
    out = []
    exp = os.path.join(base, "runs", "exp")
    for d, _, fs in sorted(os.walk(exp)):
        if "ledger.csv" in fs and "manifest.json" not in fs:
            out.append(f"run folder with a ledger and no manifest.json: {os.path.relpath(d, base)}")
    cfg = build.load(registry or build.REGISTRY)
    seen = {}
    for e in cfg["maps"]:
        seen.setdefault(e["id"], []).append(str(e["tier"]))
    out += [f"shortlist id {i} used by {len(ts)} entries (tiers {', '.join(ts)})"
            for i, ts in sorted(seen.items()) if len(ts) > 1]
    for e in cfg["maps"]:
        run, who = build.path(e["run"], base), f"shortlist {e['id']} (tier {e['tier']})"
        if not os.path.isdir(run):
            out.append(f"{who}: run folder {e['run']} missing")
            continue
        if not os.path.exists(os.path.join(run, "manifest.json")):
            out.append(f"{who}: no manifest.json in {e['run']}")
        if not e.get("images"):
            out.append(f"{who}: no images")
        rec = render.read(run)
        for p in e.get("images", []):
            img = build.path(p, base)
            if not os.path.exists(img):
                out.append(f"{who}: image {p} missing")
            elif os.path.dirname(os.path.abspath(img)) != os.path.abspath(run):
                out.append(f"{who}: image {p} is not in its run folder")
            elif rec is not None and os.path.basename(img) not in rec.get("images", {}):
                out.append(f"{who}: image {p} is not the renderer's output")
        ok, why = render.current(run, build.render_label(e))
        if not ok:
            out.append(f"{who}: render not current: {why}")
        elif rec["m1"]["status"] != (fresh := gate(run)):
            out.append(f"{who}: render records M1 {rec['m1']['status']}, the gate now says {fresh}")
    return out


def tracking_value(failures: list, base: str, registry: str | None = None) -> str:
    """T1's latest value for the register."""
    build = _load("shortlist_build", "tools", "shortlist", "build.py")
    n = len(build.load(registry or build.REGISTRY)["maps"])
    exp = os.path.join(base, "runs", "exp")
    runs = sum(1 for _, _, fs in os.walk(exp) if "ledger.csv" in fs)
    text = (f"{'pass' if not failures else 'fail'} ({datetime.date.today().isoformat()}, `{TRACKING}` "
            f"on {platform.node()}'s runs/, #120): {runs} run folders with a ledger under runs/exp, {n} shortlist "
            f"entries, {len(failures)} failures.")
    if failures:
        text += " " + "; ".join(failures[:5]) + ("; …" if len(failures) > 5 else "") + "."
    return text


def write_latest_value(text: str, path: str = REGISTER, row: str = "M1") -> None:
    """Replace the `latest value` field of mandate `row` in the register with `text`."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.startswith(f"## {row}:"))
    field = next(i for i in range(start, len(lines)) if lines[i].startswith("- **latest value:**"))
    end = field + 1
    while end < len(lines) and lines[end].startswith("  ") and lines[end].strip():
        end += 1
    words, out, line = text.split(), [], "- **latest value:**"
    for w in words:
        if len(line) + 1 + len(w) > 100:
            out.append(line)
            line = " "
        line += " " + w
    out.append(line)
    lines[field:end] = out
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dirs", nargs="*")
    ap.add_argument("--rescore", metavar="ROOT", help="gate and score every run folder under ROOT")
    ap.add_argument("--out", help="where --rescore writes TABLE.md and rescore.json")
    ap.add_argument("--tracking", action="store_true", help="mandate T1's check (#120)")
    ap.add_argument("--base", default=os.environ.get("TD_REPO", ROOT),
                    help="where runs/ is, for --tracking (default $TD_REPO)")
    ap.add_argument("--registry", default=None, help="the shortlist (default tools/shortlist/shortlist.json)")
    ap.add_argument("--write-register", action="store_true",
                    help="write M1's (or with --tracking T1's) latest value into docs/problem/MANDATES.md")
    a = ap.parse_args(argv)
    if a.tracking:
        failures = tracking(a.base, a.registry)
        for f in failures:
            print(f)
        value = tracking_value(failures, a.base, a.registry)
        print(f"T1 latest value: {value}")
        if a.write_register:
            write_latest_value(value, row="T1")
        return 1 if failures else 0
    if a.rescore:
        res = rescore(a.rescore)
        text = table(res)
        sys.stdout.write(text)
        if a.out:
            os.makedirs(a.out, exist_ok=True)
            with open(os.path.join(a.out, "TABLE.md"), "w", encoding="utf-8") as fh:
                fh.write(text)
            with open(os.path.join(a.out, "rescore.json"), "w", encoding="utf-8") as fh:
                json.dump([{k: v for k, v in r.items() if k != "score"} for r in res["rows"]], fh,
                          indent=1, default=str)
        value = latest_value(res)
        print(f"\nM1 latest value: {value}")
        if a.write_register:
            write_latest_value(value)
        return 1 if any(r["m1"] != "pass" or r["diagnostic"] for r in res["rows"]) else 0
    worst = 0
    for d in a.run_dirs:
        got = m1(d)
        diag = got["diagnostic"]
        print(f"{d}: {'DIAGNOSTIC (' + (diag['label'] or 'diagnostic band') + '), not a deliverable; ' if diag else ''}"
              f"M1 {got['status']}: {got['summary']}; largest detached piece {_piece(got['largest'])}")
        for n in got["necks"] + got["mass_necks"]:
            print(f"  {n}")
        worst = max(worst, got["status"] != "pass" or diag is not None)
    return worst


if __name__ == "__main__":
    sys.exit(main())
