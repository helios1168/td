"""replan.py -- #122's master re-solve: a scenario's master plans with supports banned, for
`run.py` to draw.

    "$TD_PY" -u tools/exp/contig/replan.py <spec.toml> --out-spec <copy.toml> --plans <dir>
        --forbid CT-NJ [CT-PA ...] [--channels c ...] [--extract PATH] [--report replan.json]

A ban is a pair of units no district may hold together: the copy adds them to each channel's
`forbid_pairs` (`td.supports.family` drops every support holding both, so the family stays
closed), and the stored TOML is never edited.  Per channel the master runs at the declared δ; a
channel with no plan there gets the smallest δ the master shows feasible (`td.master
.smallest_delta`, rounded up to 1e-4), written into the copy only when it is at most the channel's
`final_delta` (else the driver stops: the band is the owner's).  The plans (a channel moved to
its smallest δ re-planned there) are cached in `--plans` under the copy's sha256 (`run.plans_key`),
so `run.py <copy> --plans <dir>` draws exactly them.  `--report` lists per channel the δ declared
and used, the pairs banned and the supports in use holding a unit of a banned pair.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import pickle
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import data, geo, master  # noqa: E402
from td import spec as tdspec  # noqa: E402

_spec = importlib.util.spec_from_file_location("contig_run", os.path.join(HERE, "run.py"))
run = sys.modules.get("contig_run")
if run is None:
    run = importlib.util.module_from_spec(_spec)
    sys.modules["contig_run"] = run
    _spec.loader.exec_module(run)

SECTION = re.compile(r"^\[channels\.([^\]]+)\]\s*$")


def pair(text: str) -> tuple:
    """("CT", "NJ") from "CT-NJ" or "NJ-CT"; a "FI:AZ-UT" (one channel's ban) gives
    ("FI", ("AZ", "UT"))."""
    if ":" in text:
        c, _, rest = text.partition(":")
        return c, pair(rest)
    a, sep, b = text.partition("-")
    if not sep or not a or not b or a == b:
        raise argparse.ArgumentTypeError(f"a pair is two units joined by '-', not {text!r}")
    return tuple(sorted((a, b)))


def banned_text(text: str, pairs: list, channels=None, deltas: dict | None = None,
                extra: dict | None = None) -> str:
    """The TOML `text` with `pairs` added to the `forbid_pairs` of each `[channels.X]` section (of
    `channels` only when given), `extra` {X: pairs} to X's alone, and each channel of `deltas` at
    that `delta`.  A section that
    already lists `forbid_pairs` is refused (one line per section keeps the copy readable)."""
    deltas, extra = deltas or {}, extra or {}
    out, cur = [], None

    def close():
        if cur is None:
            return
        mine = sorted(set((pairs if channels is None or cur in channels else [])
                          + list(extra.get(cur, ()))))
        if mine:
            out.append("forbid_pairs = [" + ", ".join(f'["{a}", "{b}"]' for a, b in mine) + "]")
    for line in text.splitlines():
        m = SECTION.match(line)
        if m or (line.startswith("[") and cur is not None):
            while out and not out[-1].strip():
                out.pop()
            close()
            out.append("")
            cur = m.group(1) if m else None
            out.append(line)
            continue
        if cur is not None and re.match(r"^forbid_pairs\s*=", line):
            raise ValueError(f"channel {cur}: forbid_pairs already set")
        if cur in deltas and re.match(r"^delta\s*=", line):
            line = f"delta = {deltas[cur]:g}"
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    close()
    return "\n".join(out) + "\n"


def build(spec_path: str, extract_path: str):
    s = tdspec.load(spec_path)
    ref = geo.read_reference()
    ext = tdspec.scope(s, data.conus(data.load(extract_path), ref))
    return s, tdspec.build(s, ext, ref)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("spec")
    ap.add_argument("--out-spec", required=True)
    ap.add_argument("--plans", required=True, help="run.py's plan cache directory")
    ap.add_argument("--forbid", nargs="+", type=pair, required=True)
    ap.add_argument("--channels", nargs="*", default=None)
    ap.add_argument("--extract", default=os.path.join(os.environ.get("TD_REPO", ROOT),
                                                      "instance_descaled.json.gz"))
    ap.add_argument("--report", default=None)
    ap.add_argument("--time-limit", type=float, default=600.0, help="seconds per master solve")
    a = ap.parse_args(argv)
    if os.path.abspath(a.out_spec) == os.path.abspath(a.spec):
        raise SystemExit("the copy must not overwrite the stored TOML")
    with open(a.spec, encoding="utf-8") as fh:
        src = fh.read()
    pairs = sorted({p for p in a.forbid if isinstance(p[1], str)})
    extra = {}
    for c, p in sorted(p for p in a.forbid if not isinstance(p[1], str)):
        extra.setdefault(c, []).append(p)
    head = (f"# #122 master re-solve: a copy of {os.path.abspath(a.spec)}\n"
            f"# with forbid_pairs {', '.join('-'.join(p) for p in pairs)} added"
            f"{' in ' + ', '.join(a.channels) if a.channels else ' in every channel'}"
            + "".join(f", {c}: {', '.join('-'.join(p) for p in ps)}" for c, ps in extra.items())
            + " (tools/exp/contig/replan.py).\n")
    deltas, plans, reports = {}, {}, {}

    def write():
        os.makedirs(os.path.dirname(os.path.abspath(a.out_spec)), exist_ok=True)
        with open(a.out_spec, "w", encoding="utf-8") as fh:
            fh.write(head + banned_text(src, pairs, a.channels, deltas, extra))
    write()
    s, inst = build(a.out_spec, a.extract)
    doc = {"source_spec": os.path.abspath(a.spec), "spec": os.path.abspath(a.out_spec),
           "forbid": ["-".join(p) for p in pairs],
           "forbid_in": {c: ["-".join(p) for p in ps] for c, ps in extra.items()}, "channels": {}}
    for c, ch in inst.channels.items():
        p, rep = master.plan(inst, c, time_limit=a.time_limit)
        plans[c], reports[c] = p, rep
        entry = {"declared_delta": ch.spec.delta, "final_delta": ch.spec.final_delta,
                 "status_at_declared": rep.get("status")}
        if p is None:
            d = master.smallest_delta(inst, c, time_limit=a.time_limit)
            entry["smallest_delta"] = {"status": d.status, "delta": d.delta, "lower": d.lower}
            if d.delta is None or d.delta > ch.spec.final_delta:
                doc["channels"][c] = entry
                print(f"{c}: no plan up to final_delta {ch.spec.final_delta:g} ({d.status})")
                _dump(a.report, doc)
                return 1
            deltas[c] = math.ceil(d.delta * 1e4) / 1e4
        entry["delta"] = deltas.get(c, ch.spec.delta)
        doc["channels"][c] = entry
        print(f"{c}: δ {entry['delta']:g} (declared {ch.spec.delta:g})", flush=True)
    if deltas:                  # the channels moved to their smallest δ, re-planned there
        write()
        s, inst = build(a.out_spec, a.extract)
        for c in deltas:
            plans[c], reports[c] = master.plan(inst, c, time_limit=a.time_limit)
    key = run.plans_key(a.out_spec, a.extract, a.plans)
    if all(p is not None for p in plans.values()):     # `run.py --plans` reads them from here
        os.makedirs(a.plans, exist_ok=True)
        with open(key, "wb") as fh:
            pickle.dump((plans, reports), fh)
    doc["plans_file"] = key
    units = {u for p in pairs + [p for ps in extra.values() for p in ps] for u in p}
    for c, p in plans.items():
        if p is None:
            raise SystemExit(f"{c}: no plan at δ {doc['channels'][c]['delta']:g} on re-solve")
        doc["channels"][c].update(
            status=reports[c].get("status"), objective=p.objective,
            supports=sorted(f"{cp.name} " + " ".join(f"{v}:{y:.3f}" for v, y in sorted(cp.share.items()))
                            for cp in p.copies if cp.support & units))
        for line in doc["channels"][c]["supports"]:
            print(f"  {c} {line}")
    _dump(a.report, doc)
    return 0


def _dump(path, doc):
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")


if __name__ == "__main__":
    sys.exit(main())
