"""wholeplan.py -- #127's whole-unit plans: every district checked against M1 at plan time, a
failing one banned and the plan re-solved, with no drawing step and no repair.

    "$TD_PY" -u tools/exp/contig/wholeplan.py <spec.toml> --out <dir> --k K [--channel IFA]
        [--pieces NY,CA,...] [--extract PATH] [--time-limit S] [--max-rounds R]

The copy (`<out>/scenario.toml`, never the stored TOML) drops the channel's split list (`free`), so
every unit is held whole, sets K and, with `--pieces`, cuts each named state into county pieces
(`pieces.py`; a piece takes its state's `dist_km`).  With every unit whole the plan fixes every
ZIP: a district is the union of its units' ZIPs.  Each round:

1. the smallest δ the master is feasible at with the bans so far (`master.exact_delta`, exact for
   whole units), rounded up to 1e-4, with no cap: the owner accepts any band (2026-10-07);
2. the master's plan there (`master.plan(..., banned=)`);
3. each support in use, singletons included, checked once against M1 on its ZIP set (`m1_verdict`:
   `td.audit.district_pieces` on the polygon graph and `td.audit.district_necks`, the gate's own
   functions);
4. each support that fails is banned as its exact unit set, with the reason; one whose neck search
   stops on its time limit is `unknown` and never banned.

The loop ends with every district passing (or unknown), or with "no plan": the master infeasible
under the bans, listed in full with why each failed.  The run folder is run.py's (`contig_run`
on the final copy, which carries δ as `delta` and `final_delta` and the bans as `ban_supports`,
and on the plan pickled to `<out>/plans.pkl`): with no split unit the drawing is the units' ZIPs
and no solve runs.  `wholeplan.json` records each round (δ, objective, bans) and every verdict.
"""
from __future__ import annotations

import argparse
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

from td import audit, data, geo, master, supports  # noqa: E402
from td import spec as tdspec  # noqa: E402


def _load(name: str, file: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


run = _load("contig_run", "run.py")
replan = _load("contig_replan", "replan.py")

FORMULATION = "wholeplan"
DELTA_STEP = 1e-4           # the planned δ is the exact smallest δ rounded up to this


def _name(s) -> str:
    return "+".join(sorted(s))


def m1_verdict(zips: set, mass: dict, adj: dict, ng, time_limit: float = audit.NECK_TIME) -> dict:
    """M1 on one district's ZIP set, as the gate judges it (`td.audit.check_m1`): one piece on the
    polygon graph `adj` and no neck.  {"status": pass | fail | unknown, "why"}; a neck search that
    stops on its time limit is `unknown`, never a failure."""
    comps = audit.district_pieces(dict.fromkeys(zips, "S"), adj, mass)["S"]
    if len(comps) > 1:
        rest = sorted(comps[1:], key=lambda c: -len(c))
        return {"status": "fail", "why": f"{len(comps)} pieces on the polygon graph; detached "
                + ", ".join(f"{len(c)} ZIPs from {min(c)}" for c in rest[:4])}
    necks = audit.district_necks(set(zips), mass, ng, time_limit)
    proved = [nk for nk in necks if nk.status == "proved"]
    if proved:
        nk = min(proved, key=lambda n: n.width_km)
        return {"status": "fail", "why": f"neck {nk.width_km:.2f} km wide cuts off {len(nk.zips)} "
                f"ZIPs ({nk.zips[0]}...), {nk.area:.1%} of the land area",
                "neck_zip": nk.zips[0]}
    if necks:
        return {"status": "unknown", "why": audit.neck_item("", "", necks[0]).split(": ", 1)[1]}
    return {"status": "pass", "why": f"one piece of {len(zips)} ZIPs, no neck"}


def loop(inst, c: str, polygon: dict, time_limit: float | None = None, max_rounds: int = 200,
         fam=None, check=m1_verdict, log=print) -> dict:
    """The check-and-ban loop (module docstring) on channel `c`, every unit whole.  Returns
    {"status": passed | unknown | no plan | rounds, "plan", "report", "delta", "rounds",
    "bans": [{"support", "why", "round"}], "verdicts": {support: verdict}}."""
    ch, units = inst.channels[c], inst.units
    split = sorted(v for v in ch.units if ch.mode[v] != "whole")
    if split:
        raise ValueError(f"{c}: units not whole: {split}")
    fam = supports.family(inst, c) if fam is None else fam
    adj = audit.adjacency(polygon)
    ng = audit.NeckGraph(polygon)
    verdicts, bans, rounds = {}, [], []
    out = {"status": None, "plan": None, "report": None, "delta": None, "rounds": rounds,
           "bans": bans, "verdicts": verdicts}
    for r in range(1, max_rounds + 1):
        banned = [frozenset(b["support"].split("+")) for b in bans]
        t0 = time.time()
        d = master.exact_delta(inst, c, fam, time_limit, banned=banned)
        rec = {"round": r, "bans_in": len(banned), "exact_delta": d.delta,
               "delta_status": d.status}
        rounds.append(rec)
        if d.status != "exact":
            out["status"] = "no plan" if d.status == "infeasible" else "unknown delta"
            log(f"{c} round {r}: smallest δ {d.status} with {len(banned)} bans")
            return out
        delta = math.ceil(d.delta / DELTA_STEP - 1e-9) * DELTA_STEP
        p, rep = master.plan(inst, c, delta, fam, time_limit=time_limit, banned=banned)
        rec.update(delta=delta, status=rep.get("status"), objective=p and p.objective,
                   seconds=round(time.time() - t0, 1))
        if p is None:
            out["status"] = f"no plan at δ {delta:g} ({rep.get('status')})"
            return out
        out.update(plan=p, report=rep, delta=delta)
        new, unknown = [], []
        for s in sorted(p.n, key=lambda s: (len(s), sorted(s))):
            key = _name(s)
            if key not in verdicts:
                zips = {z for v in s for z in units.zips[v]}
                verdicts[key] = check(zips, ch.m, adj, ng)
            v = verdicts[key]
            if v["status"] == "fail":
                new.append({"support": key, "why": v["why"], "round": r})
            elif v["status"] == "unknown":
                unknown.append(key)
        rec.update(new_bans=[b["support"] for b in new], unknown=unknown)
        log(f"{c} round {r}: δ {delta:g}, objective {p.objective:.1f}, {len(p.n)} supports, "
            f"{len(new)} fail M1" + "".join(f"\n  ban {b['support']}: {b['why']}" for b in new))
        if not new:
            out["status"] = "unknown" if unknown else "passed"
            return out
        bans += new
    out["status"] = "rounds"
    return out


def copy_text(src: str, c: str, k: int, delta: float, final_delta: float, bans=(),
              pieces=(), source: str = "") -> str:
    """The copy of the scenario TOML `src`: channel `c` with no split list (every unit whole), K
    `k`, `delta`, `final_delta`, `ban_supports` `bans` (unit sets) and the county `pieces`
    ([`pieces.Piece`]) as `[geography] pieces`, each with its state's `dist_km`."""
    if "[geography]" in src:
        raise ValueError("the stored TOML already has a [geography] table")
    keys = {"k": str(k)}
    if bans:
        keys["ban_supports"] = "[" + ", ".join(
            "[" + ", ".join(f'"{u}"' for u in sorted(b)) + "]" for b in bans) + "]"
    if pieces:
        dist = dict(tdspec.parse(_toml(src)).channels[c].dist_km)
        dist.update({p.name: dist[p.state] for p in pieces if p.state in dist})
        keys["dist_km"] = "{ " + ", ".join(f"{u} = {x:g}" for u, x in dist.items()) + " }"
    head = (f"# #127 whole-unit plan: a copy of {source}\n# with {c} every unit whole, K {k}"
            f"{', bans ' + str(len(bans)) if bans else ''}"
            f"{', county pieces of ' + ','.join(sorted({p.state for p in pieces})) if pieces else ''}"
            "\n# (tools/exp/contig/wholeplan.py).\n")
    text = replan.banned_text(src, [], free={c: ()}, deltas={c: delta},
                              final_deltas={c: final_delta}, keys={c: keys})
    if pieces:
        text += "\n[geography]\npieces = [\n" + "".join(
            f'  {{ name = "{p.name}", state = "{p.state}", counties = ['
            + ", ".join(f'"{x}"' for x in sorted(p.counties)) + "] },\n" for p in pieces) + "]\n"
    return head + text


def _toml(text: str) -> dict:
    import tomllib
    return tomllib.loads(text)


def build(spec_path: str, extract_path: str):
    s = tdspec.load(spec_path)
    ref = geo.read_reference()
    ext = tdspec.scope(s, data.conus(data.load(extract_path), ref))
    return s, ext, ref, tdspec.build(s, ext, ref)


def wholeplan(spec_path: str, out: str, k: int, extract_path: str, c: str = "IFA",
              piece_states=(), time_limit: float | None = 600.0, max_rounds: int = 200,
              log=print) -> dict:
    """Plan (`loop`) and write the run folder (module docstring); wholeplan.json's dict."""
    with open(spec_path, encoding="utf-8") as fh:
        src = fh.read()
    os.makedirs(out, exist_ok=True)
    copy = os.path.join(out, "scenario.toml")
    if replan.same_file(copy, spec_path):
        raise SystemExit("the copy must not overwrite the stored TOML")
    src_abs = os.path.abspath(spec_path)
    cut, piece_rec = [], {}
    if piece_states:
        pieces = _load("contig_pieces", "pieces.py")
        _, _, ref0, inst0 = build(spec_path, extract_path)
        cut, piece_rec = pieces.state_pieces(inst0, ref0, c, k, piece_states, m1_verdict)
    top = float(k)              # any band: the planning copy caps nothing
    with open(copy, "w", encoding="utf-8") as fh:
        fh.write(copy_text(src, c, k, 0.0, top, (), cut, src_abs))
    _, _, _, inst = build(copy, extract_path)
    polygon = geo.polygon_graph()
    t0 = time.time()
    res = loop(inst, c, polygon, time_limit, max_rounds, log=log)
    doc = {"source_spec": src_abs, "spec": os.path.abspath(copy), "channel": c, "k": k,
           "status": res["status"], "delta": res["delta"], "rounds": res["rounds"],
           "bans": res["bans"], "verdicts": res["verdicts"], "pieces": piece_rec,
           "seconds": round(time.time() - t0, 1)}
    path = os.path.join(out, "wholeplan.json")
    if res["status"] not in ("passed", "unknown"):
        _dump(path, doc)
        log(f"{c} K {k}: {res['status']} after {len(res['rounds'])} rounds, "
            f"{len(res['bans'])} bans")
        return doc
    bans = [frozenset(b["support"].split("+")) for b in res["bans"]]
    with open(copy, "w", encoding="utf-8") as fh:
        fh.write(copy_text(src, c, k, res["delta"], res["delta"], bans, cut, src_abs))
    plans_file = os.path.join(out, "plans.pkl")
    with open(plans_file, "wb") as fh:
        pickle.dump(({c: res["plan"]}, {c: res["report"]}), fh)
    doc["plans_file"] = plans_file
    _dump(path, doc)
    keep = tuple(os.listdir(out))
    contig = run.contig_run(copy, extract_path, out, plans_file=plans_file,
                            source=os.path.basename(extract_path), keep=keep, log=log)
    doc["m1"] = contig["m1"]
    doc["drawn"] = {x: contig["channels"][c][x] for x in ("worst_dev", "mean_dev", "split_units")}
    _dump(path, doc)
    return doc


def _dump(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True, default=str)
        fh.write("\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("spec")
    ap.add_argument("--out", required=True)
    ap.add_argument("--k", type=int, required=True)
    ap.add_argument("--channel", default="IFA")
    ap.add_argument("--pieces", default="", help="STATE,STATE,...: cut into county pieces")
    ap.add_argument("--extract", default=os.path.join(os.environ.get("TD_REPO", ROOT),
                                                      "instance_descaled.json.gz"))
    ap.add_argument("--time-limit", type=float, default=600.0, help="seconds per master solve")
    ap.add_argument("--max-rounds", type=int, default=200)
    a = ap.parse_args(argv)
    states = tuple(x for x in a.pieces.split(",") if x)
    params = {k: v for k, v in vars(a).items() if k not in ("spec", "out")}
    from td import output
    output.check_out(a.out)
    copy = os.path.join(a.out, "scenario.toml")
    # the manifest names the copy; it is written (and its sha256 taken) before the plan
    with open(a.spec, encoding="utf-8") as fh:
        src = fh.read()
    os.makedirs(a.out, exist_ok=True)
    with open(copy, "w", encoding="utf-8") as fh:
        fh.write(copy_text(src, a.channel, a.k, 0.0, float(a.k), (), (), os.path.abspath(a.spec)))
    run.write_manifest(a.out, FORMULATION, copy, a.extract, params)
    try:
        doc = wholeplan(a.spec, a.out, a.k, a.extract, a.channel, states, a.time_limit,
                        a.max_rounds)
    except Exception as e:
        run.write_manifest(a.out, FORMULATION, copy, a.extract, params, status="failed",
                           stop_reason=f"{type(e).__name__}: {e}")
        raise
    run.write_manifest(a.out, FORMULATION, copy, a.extract, params,
                       status="done" if "m1" in doc else "failed", stop_reason=doc["status"],
                       m1=(doc.get("m1") or {}).get("status"),
                       scenario={"path": os.path.abspath(copy), "sha256": run.sha256(copy)},
                       wholeplan={"status": doc["status"], "delta": doc["delta"],
                                  "rounds": len(doc["rounds"]), "bans": doc["bans"]})
    return 0 if (doc.get("m1") or {}).get("status") == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
