"""replan.py -- #122's master re-solve: a scenario's master plans with supports banned, for
`run.py` to draw.

    "$TD_PY" -u tools/exp/contig/replan.py <spec.toml> --out-spec <copy.toml> --plans <dir>
        [--forbid CT-NJ [CT-PA ...]] [--free FI=CA,FL,NY,TX ...] [--widen FI ...]
        [--channels c ...] [--extract PATH] [--report replan.json]

A ban is a pair of units no district may hold together: the copy adds them to each channel's
`forbid_pairs` (`td.supports.family` drops every support holding both, so the family stays
closed).  A `--free` override replaces one channel's split list (`free`; every other unit of its
domain stays whole), and the stored TOML is never edited.  Per channel the master runs at the
declared δ; a channel with no plan there gets the smallest δ the master shows feasible (`td.master
.smallest_delta`, rounded up to 1e-4), written into the copy only when it is at most the channel's
`final_delta` (else the driver stops: the band is the owner's).  `--widen X` is the owner's
widening (2026-10-06): the copy sets X's `final_delta` to 0.15, so X plans at its smallest δ up to
0.15 and is judged in ±15%; every other channel keeps its own.  The plans (a channel moved to its
smallest δ re-planned there) are cached in `--plans` under the copy's sha256 (`run.plans_key`),
so `run.py <copy> --plans <dir>` draws exactly them.  `--report` lists per channel the δ declared
and used, the pairs banned in it (`bans`, after `--channels`) and the supports in use holding a
unit of one.  Neither the copy nor the report may be the stored TOML, by any path or link.

#124's keys (each off by default; only a copy turns one on): `--contact-min-km W` (A),
`--drawable-alone` (B) and `--replan-rounds R` (C) set them in every channel of the copy, and
`--keep` plans a copy that already carries them.  A channel with `drawable_alone` plans by
`plancheck.plan_checked` (B's lazy loop) instead of `td.master.plan`, and with no checked plan
at its δ moves to the smallest δ up to `final_delta` with one (`plancheck.checked_delta`); the
report's `plan_check` lists B's tests, cuts and unknowns, and `delta_change` what moved δ.
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

WIDE_FINAL_DELTA = 0.15      # the owner's ±15% eligibility frame on drawn mass (2026-10-06)
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


def free_list(text: str) -> tuple:
    """("FI", ("CA", "FL", "NY", "TX")) from "FI=CA,FL,NY,TX"; "FI=" gives an empty list."""
    c, sep, rest = text.partition("=")
    units = tuple(u for u in rest.split(",") if u)
    if not sep or not c or len(set(units)) != len(units):
        raise argparse.ArgumentTypeError(f"a split list is CHANNEL=U1,U2,..., not {text!r}")
    return c, units


def banned_text(text: str, pairs: list, channels=None, deltas: dict | None = None,
                extra: dict | None = None, free: dict | None = None,
                final_deltas: dict | None = None, keys: dict | None = None) -> str:
    """The TOML `text` with `pairs` added to the `forbid_pairs` of each `[channels.X]` section (of
    `channels` only when given), `extra` {X: pairs} to X's alone, each channel of `deltas` at
    that `delta`, each channel of `free` {X: units} with that split list in place of its own and
    each channel of `final_deltas` at that `final_delta` and each channel of `keys` {X: {key:
    TOML value}} with those lines (#124's keys); a channel with no line of its own (one
    inheriting `[scenario].delta`, say) gets one.  A section that already lists `forbid_pairs` is
    refused when pairs are added to it (one line per section keeps the copy readable)."""
    deltas, extra, free, finals = deltas or {}, extra or {}, free or {}, final_deltas or {}
    keys = keys or {}
    out, cur, seen, seen_final, seen_delta = [], None, set(), set(), set()
    seen_keys = set()

    def adds(c):
        return sorted(set((pairs if channels is None or c in channels else [])
                          + list(extra.get(c, ()))))

    def close():
        if cur is None:
            return
        if cur in deltas and cur not in seen_delta:
            out.append(f"delta = {deltas[cur]:g}")
        if cur in free and cur not in seen and free[cur]:
            out.append("free = [" + ", ".join(f'"{u}"' for u in free[cur]) + "]")
        if cur in finals and cur not in seen_final:
            out.append(f"final_delta = {finals[cur]:g}")
        for k, v in sorted(keys.get(cur, {}).items()):
            if (cur, k) not in seen_keys:
                out.append(f"{k} = {v}")
        mine = adds(cur)
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
        if cur is not None and re.match(r"^forbid_pairs\s*=", line) and adds(cur):
            raise ValueError(f"channel {cur}: forbid_pairs already set")
        key = re.match(r"^(\w+)\s*=", line)
        if cur in keys and key and key.group(1) in keys[cur]:
            if not line.rstrip().endswith("]") and line.rstrip().endswith("["):
                raise ValueError(f"channel {cur}: {key.group(1)} spans lines")
            seen_keys.add((cur, key.group(1)))
            line = f"{key.group(1)} = {keys[cur][key.group(1)]}"
        if cur in deltas and re.match(r"^delta\s*=", line):
            seen_delta.add(cur)
            line = f"delta = {deltas[cur]:g}"
        if cur in finals and re.match(r"^final_delta\s*=", line):
            seen_final.add(cur)
            line = f"final_delta = {finals[cur]:g}"
        if cur in free and re.match(r"^free\s*=", line):
            if not line.rstrip().endswith("]"):
                raise ValueError(f"channel {cur}: free spans lines")
            seen.add(cur)
            if not free[cur]:
                continue
            line = "free = [" + ", ".join(f'"{u}"' for u in free[cur]) + "]"
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    close()
    sections = {m.group(1) for m in map(SECTION.match, text.splitlines()) if m}
    if (set(free) | set(finals) | set(deltas) | set(keys)) - sections:
        raise ValueError("no channel section: "
                         f"{sorted((set(free) | set(finals) | set(deltas) | set(keys)) - sections)}")
    return "\n".join(out) + "\n"


def effective_bans(names, pairs: list, channels=None, extra: dict | None = None) -> dict:
    """{channel: ["A-B", ...]} of the pairs `banned_text` adds to each of `names`: `pairs` where
    `channels` (`--channels`) is not given or lists it, and its own `extra`."""
    extra = extra or {}
    return {c: ["-".join(p) for p in sorted(set((pairs if channels is None or c in channels
                                                 else []) + list(extra.get(c, ()))))]
            for c in sorted(names)}


def same_file(a: str, b: str) -> bool:
    """True when the paths name one file: one inode where both exist (a symlink or a hard link
    counts), else one real path."""
    if os.path.exists(a) and os.path.exists(b):
        return os.path.samefile(a, b)
    return os.path.realpath(a) == os.path.realpath(b)


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
    ap.add_argument("--forbid", nargs="+", type=pair, default=[])
    ap.add_argument("--free", action="append", type=free_list, default=[],
                    help="CHANNEL=U1,U2,...: that channel's split list (repeatable)")
    ap.add_argument("--widen", action="append", default=[],
                    help=f"CHANNEL: final_delta {WIDE_FINAL_DELTA:g} in the copy (owner's pick; "
                         "repeatable)")
    ap.add_argument("--channels", nargs="*", default=None)
    ap.add_argument("--extract", default=os.path.join(os.environ.get("TD_REPO", ROOT),
                                                      "instance_descaled.json.gz"))
    ap.add_argument("--report", default=None)
    ap.add_argument("--time-limit", type=float, default=600.0, help="seconds per master solve")
    ap.add_argument("--contact-min-km", type=float, default=None,
                    help="#124 A in every channel of the copy (M1's W is 10)")
    ap.add_argument("--drawable-alone", action="store_true", help="#124 B in every channel")
    ap.add_argument("--replan-rounds", type=int, default=None, help="#124 C in every channel")
    ap.add_argument("--keep", action="store_true",
                    help="plan the copy as it is (it already carries the #124 keys)")
    ap.add_argument("--check-time", type=float, default=120.0,
                    help="seconds per B test (plancheck.drawable)")
    a = ap.parse_args(argv)
    free = dict(a.free)
    if len(free) != len(a.free):
        raise SystemExit("--free names a channel twice")
    new_keys = {k: v for k, v in (("contact_min_km", a.contact_min_km and f"{a.contact_min_km:g}"),
                                  ("drawable_alone", "true" if a.drawable_alone else None),
                                  ("replan_rounds", a.replan_rounds is not None
                                   and str(a.replan_rounds))) if v}
    if not a.forbid and not free and not a.widen and not new_keys and not a.keep:
        raise SystemExit("nothing to change: give --forbid, --free, --widen, a #124 key or --keep")
    finals = dict.fromkeys(a.widen, WIDE_FINAL_DELTA)
    if same_file(a.out_spec, a.spec):
        raise SystemExit("the copy must not overwrite the stored TOML")
    if a.report and same_file(a.report, a.spec):
        raise SystemExit("the report must not overwrite the stored TOML")
    with open(a.spec, encoding="utf-8") as fh:
        src = fh.read()
    pairs = sorted({p for p in a.forbid if isinstance(p[1], str)})
    extra = {}
    for c, p in sorted(p for p in a.forbid if not isinstance(p[1], str)):
        extra.setdefault(c, []).append(p)
    head = (f"# #122 master re-solve: a copy of {os.path.abspath(a.spec)}"
            + (f"\n# with forbid_pairs {', '.join('-'.join(p) for p in pairs)} added"
               f"{' in ' + ', '.join(a.channels) if a.channels else ' in every channel'}"
               if pairs else "")
            + "".join(f"\n# with forbid_pairs {c}: {', '.join('-'.join(p) for p in ps)}"
                      for c, ps in extra.items())
            + "".join(f"\n# with {c}'s split list free = {', '.join(us) or 'none'}"
                      for c, us in sorted(free.items()))
            + "".join(f"\n# with {c}'s final_delta widened to {d:g} (owner, 2026-10-06)"
                      for c, d in sorted(finals.items()))
            + "".join(f"\n# with {k} = {v} in every channel (#124)" for k, v in new_keys.items())
            + "\n# (tools/exp/contig/replan.py).\n")
    deltas, plans, reports = {}, {}, {}
    sections = [m.group(1) for m in map(SECTION.match, src.splitlines()) if m]
    keys = {c: dict(new_keys) for c in sections} if new_keys else None

    def write():
        os.makedirs(os.path.dirname(os.path.abspath(a.out_spec)), exist_ok=True)
        with open(a.out_spec, "w", encoding="utf-8") as fh:
            fh.write(head + banned_text(src, pairs, a.channels, deltas, extra, free, finals, keys))
    write()
    s, inst = build(a.out_spec, a.extract)
    checks = ng = None
    if any(ch.spec.drawable_alone for ch in inst.channels.values()):
        from td import audit
        plancheck = _plancheck()
        checks, ng = plancheck.Checks(), audit.NeckGraph(inst.polygon)
    records = {}

    def plan_c(c):
        """The channel's plan at its copy's δ: B's lazy loop when the key is on."""
        if not inst.channels[c].spec.drawable_alone:
            return master.plan(inst, c, time_limit=a.time_limit)
        p, rep, rec = plancheck.plan_checked(inst, c, checks=checks, ng=ng,
                                             time_limit=a.time_limit, check_time=a.check_time)
        records[c] = rec
        return p, rep
    doc = {"source_spec": os.path.abspath(a.spec), "spec": os.path.abspath(a.out_spec),
           "forbid": ["-".join(p) for p in pairs],
           "forbid_in": {c: ["-".join(p) for p in ps] for c, ps in extra.items()},
           "free": {c: list(us) for c, us in sorted(free.items())},
           "widen": {c: d for c, d in sorted(finals.items())}, "channels": {},
           "bans": effective_bans(inst.channels, pairs, a.channels, extra)}
    for c, ch in inst.channels.items():
        p, rep = plan_c(c)
        plans[c], reports[c] = p, rep
        entry = {"declared_delta": ch.spec.delta, "final_delta": ch.spec.final_delta,
                 "status_at_declared": rep.get("status")}
        if c in records:
            entry["plan_check_at_declared"] = records[c]
        if p is None:
            d = master.smallest_delta(inst, c, time_limit=a.time_limit)
            entry["smallest_delta"] = {"status": d.status, "delta": d.delta, "lower": d.lower}
            if d.delta is not None and d.delta <= ch.spec.final_delta and c in records:
                # B: the master plans at d.delta, its checks may not; bisect with B inside
                cd = plancheck.checked_delta(inst, c, ch.spec.delta, d.delta, checks, ng,
                                             a.time_limit, a.check_time)
                below = [x for x in cd["steps"] if cd["delta"] is None or x["delta"] < cd["delta"]]
                entry["delta_change"] = {
                    **cd, "forced_by": max(below, key=lambda x: x["delta"])["bans"] if below else []}
                d = master.Delta(c, "bisection", cd["status"], cd["delta"], cd["lower"],
                                 master.DELTA_TOL)
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
        if checks is not None:      # the instance is rebuilt: its polygon graph is a new dict
            ng = audit.NeckGraph(inst.polygon)
        for c in deltas:
            plans[c], reports[c] = plan_c(c)
    key = run.plans_key(a.out_spec, a.extract, a.plans)
    if all(p is not None for p in plans.values()):     # `run.py --plans` reads them from here
        os.makedirs(a.plans, exist_ok=True)
        with open(key, "wb") as fh:
            pickle.dump((plans, reports), fh)
    doc["plans_file"] = key
    for c, p in plans.items():
        if p is None:
            raise SystemExit(f"{c}: no plan at δ {doc['channels'][c]['delta']:g} on re-solve")
        units = {u for ban in doc["bans"][c] for u in ban.split("-")}
        if c in records:
            doc["channels"][c]["plan_check"] = records[c]
        doc["channels"][c].update(
            status=reports[c].get("status"), objective=p.objective,
            supports=sorted(f"{cp.name} " + " ".join(f"{v}:{y:.3f}" for v, y in sorted(cp.share.items()))
                            for cp in p.copies if cp.support & units))
        for line in doc["channels"][c]["supports"]:
            print(f"  {c} {line}")
    _dump(a.report, doc)
    return 0


def _plancheck():
    if "contig_plancheck" not in sys.modules:
        spec = importlib.util.spec_from_file_location("contig_plancheck",
                                                      os.path.join(HERE, "plancheck.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["contig_plancheck"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["contig_plancheck"]


def _dump(path, doc):
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")


if __name__ == "__main__":
    sys.exit(main())
