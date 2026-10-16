"""glue.py -- glue repair (owner, #140 addendum (b), 2026-10-14) of a drawn contig run folder:
a district's detached pieces joined through zero-opportunity ZCTAs that other districts hold.

    "$TD_PY" -u tools/exp/contig/glue.py <run_dir> --out <dir> [--extract PATH] [--plans PATH]
        [--states S1,S2,...] [--label TEXT] [--channels c ...] [--tries N]

Per planning channel, for each district with a detached piece under `td.audit.district_pieces`
(M1's pieces, on the polygon graph with the approved connectors): the shortest path from the piece
to the district's other ZCTAs whose every ZCTA has zero mass in the channel (`mass.get(z, 0) == 0`)
and is held by another district of the run; the path goes to the district.  It is applied only if
every donor district keeps its failures by identity and size: a clean donor stays clean, and each
detached piece and each neck (the gate's, `necks_gate.gate_necks`, the part cut off) it has afterwards lies
inside a different one it had before, so a new or enlarged piece or neck is refused even when the
counts do not rise; the district itself ends with fewer pieces and no more necks than before.  On a refusal the donor that failed is kept off the next
path, up to `--tries` paths per piece; a piece still detached is left as it is and listed under
`left` with the reason, its τ share and its size, for the owner.  A ZCTA with positive mass in the
channel is never moved, and the check at the end of `glue_channel` stops the run if one was.

The graph is the gate's: `audit.adjacency` of the full polygon graph with the land-only gap edges when gap width
is on (`gate_adjacency`, as `td.audit.check_m1` joins pieces, R5), for the glue paths, the donor and district
piece checks and the pieces left; only ZCTAs of the run's ledger can change owner, so on a `--states` region run
a path stays inside the region.  A neck check the search could not settle (`status` "unresolved", which the gate
lists and fails) stays unresolved here (`UnresolvedNeck`); a donor whose check after the move is unresolved
refuses the move.

The output is a full run folder (`run.write_folder`, as `repair.py` writes it) when a ZCTA moved,
with `glue.json` (per channel: `glued`, each path with its donors; `left`; `moved`) beside
`contig.json`; with nothing moved only `glue.json` and the manifest are written and the source
folder stays the one to go on from.
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import audit, geo, output  # noqa: E402

TRIES = 4                       # paths tried per piece, each after the last one's failing donors are barred


def _load(name: str, file: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


necks_gate = _load("contig_necks_gate", "necks_gate.py")


# ------------------------------------------------------------------------------ the search
def _pieces(zips, adj: dict, mass: dict) -> list:
    """The components of `zips` on `adj`, the main piece first (`audit.district_pieces`'s order)."""
    return audit.district_pieces(dict.fromkeys(zips, "d"), adj, mass).get("d", [])


def shortest_path(start: set, targets: set, allowed, adj: dict) -> list | None:
    """The fewest ZCTAs, in order from `start`, that join `start` to a ZCTA of `targets` when each
    must satisfy `allowed` (a function of a ZCTA); None when there is no such path.  Breadth
    first, neighbours in sorted order, so the answer is the same on every run."""
    prev, frontier = {z: None for z in sorted(start)}, sorted(start)
    while frontier:
        nxt = []
        for z in frontier:
            for y in sorted(adj.get(z, ())):
                if y in prev:
                    continue
                if y in targets:
                    path = []
                    while z not in start:
                        path.append(z)
                        z = prev[z]
                    return path[::-1]
                if allowed(y):
                    prev[y] = z
                    nxt.append(y)
        frontier = nxt
    return None


def _inside(after: list, before: list) -> bool:
    """True when every set of `after` lies inside a different set of `before` (a `None` is a set of
    unknown identity: it matches only a `None`)."""
    free = list(before)
    for a in sorted(after, key=lambda x: -len(x or ())):
        fits = [b for b in free if (a is None and b is None) or (a is not None and b is not None and a <= b)]
        if not fits:
            return False
        free.remove(min(fits, key=lambda x: len(x or ())))
    return True


class UnresolvedNeck(frozenset):
    """A neck the gate's search stopped on without proof (`audit.Neck.status` "unresolved"): the ZCTAs of its
    side, marked so that no check reads it as a proved part cut off."""


def glue_channel(owner: dict, adj: dict, mass: dict, necks_of, tries: int = TRIES,
                 tau: float | None = None) -> tuple:
    """(owner after, report) of one planning channel: `owner` {zip: district}, `adj` {zip: set of
    neighbours} (M1's graph), `mass` {zip: mass in the channel}, `necks_of(frozenset of zips)` the
    M1 necks of a district holding them, each as the frozenset of ZCTAs of the part cut off (an
    `UnresolvedNeck` for a neck the search could not settle; a number n stands for n necks of unknown
    identity).  The report holds `glued` [{district, piece,
    path, donors}], `left` [{district, first, zips, mass, tau_share, reason}] for the pieces
    still detached at the end, and `moved` {zip: [from, to]}."""
    owner = dict(owner)
    start = dict(owner)
    memo = {}

    def necks(zs):
        zs = frozenset(zs)
        if zs not in memo:
            got = necks_of(zs)
            memo[zs] = [None] * got if isinstance(got, int) else [
                x if isinstance(x, UnresolvedNeck) else frozenset(x) for x in got]
        return memo[zs]

    def detached(zs):
        return [frozenset(c) for c in _pieces(zs, adj, mass)[1:]]

    def held(own, j):
        return {z for z, d in own.items() if d == j}

    glued, why, failed = [], {}, set()
    while True:
        pieces = audit.district_pieces(owner, adj, mass)
        todo = sorted((j, min(c)) for j, comps in pieces.items() for c in comps[1:]
                      if (j, min(c)) not in failed)
        if not todo:
            break
        j, first = todo[0]
        comp = next(c for c in pieces[j][1:] if min(c) == first)
        others = held(owner, j) - comp
        barred, reason, done = set(), "no path", False
        for _ in range(max(1, tries)):
            path = shortest_path(comp, others, lambda z: z in owner and owner[z] != j
                                 and owner[z] not in barred and mass.get(z, 0.0) == 0.0, adj)
            if path is None:
                reason = ("no path of zero-opportunity ZCTAs held by other districts" if not barred else
                          f"{reason}; no other path once {', '.join(sorted(barred))} are kept out")
                break
            donors = sorted({owner[z] for z in path})
            trial = dict(owner)
            trial.update(dict.fromkeys(path, j))
            bad = []
            for d in donors:
                before, after = held(owner, d), held(trial, d)
                if not after:
                    bad.append((d, "would be left with no ZCTA"))
                elif not _inside(detached(after), detached(before)):
                    bad.append((d, "would gain a piece"))
                elif any(isinstance(x, UnresolvedNeck) for x in necks(after)):
                    bad.append((d, "would have an unresolved neck check"))
                elif not _inside(necks(after), necks(before)):
                    bad.append((d, "would gain a neck"))
            if bad:
                barred |= {d for d, _ in bad}
                reason = "; ".join(f"donor {d} {w}" for d, w in bad)
                continue
            mine_before, mine_after = held(owner, j), held(trial, j)
            if len(_pieces(mine_after, adj, mass)) >= len(_pieces(mine_before, adj, mass)):
                reason = "the path does not reduce the district's pieces"
                break
            if len(necks(mine_after)) > len(necks(mine_before)):
                reason = "the path would give the district a neck"
                break
            glued.append({"district": j, "piece": first, "path": path,
                          "donors": dict(sorted(collections.Counter(owner[z] for z in path).items()))})
            owner, done = trial, True
            break
        if not done:
            failed.add((j, first))
            why[j, first] = reason
    moved = {z: [start[z], owner[z]] for z in owner if owner[z] != start[z]}
    positive = sorted(z for z in moved if mass.get(z, 0.0) != 0.0)
    if positive:
        raise RuntimeError(f"glue moved ZCTAs with positive mass: {positive[:5]}")
    left = []
    for j, comps in audit.district_pieces(owner, adj, mass).items():
        for c in comps[1:]:
            m = math.fsum(mass.get(z, 0.0) for z in c)
            left.append({"district": j, "first": min(c), "zips": len(c), "mass": m,
                         "tau_share": (m / tau) if tau else None,
                         "reason": why.get((j, min(c)), "not attempted")})
    return owner, {"glued": glued, "left": sorted(left, key=lambda r: (r["district"], r["first"])),
                   "moved": dict(sorted(moved.items()))}


# ------------------------------------------------------------------------------ the run
def gate_adjacency(polygon: dict, gap_width: bool | None = None) -> dict:
    """`audit.adjacency` as `audit.check_m1` builds it: with the land-only gap edges (R5) when gap width is on
    (`gap_width` None reads `audit.gap_width_on()`, as `necks_gate.gate_graph` does)."""
    return audit.adjacency(polygon, gaps=audit.gap_width_on() if gap_width is None else gap_width)


def neck_counter(polygon: dict, mass: dict):
    """necks_of(zips) -> the M1 necks the gate finds (`necks_gate.gate_necks`; each as the frozenset
    of ZCTAs of the part cut off, an `UnresolvedNeck` when the search left it unresolved), on the gate's graph (`necks_gate.gate_graph`: gap width on unless
    `TD_NECK_GAP_WIDTH` is "0", the connector rule of #140) with the zero-opportunity ZCTAs of
    `mass` as relays (`necks_gate.channel_mass`)."""
    ng = necks_gate.gate_graph(polygon)
    return (lambda zs: [frozenset(n.zips) if n.status == "proved" else UnresolvedNeck(n.zips)
                        for n in necks_gate.gate_necks(zs, mass, ng)]), ng


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run_dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--extract", default=os.path.join(os.environ.get("TD_REPO", ROOT),
                                                      "instance_descaled.json.gz"))
    ap.add_argument("--plans", default=None, help="the plan cache of `run.py`")
    ap.add_argument("--plans-file", default=None)
    ap.add_argument("--states", default="", help="as `run.py --states` drew the run")
    ap.add_argument("--label", default="")
    ap.add_argument("--channels", nargs="*", default=None)
    ap.add_argument("--tries", type=int, default=TRIES)
    a = ap.parse_args(argv)
    repair = _load("contig_repair", "repair.py")
    run, draw = repair.run, repair.draw
    output.check_out(a.out)
    with open(os.path.join(a.run_dir, "run.json"), encoding="utf-8") as fh:
        spec_path = json.load(fh)["spec"]
    params = {k: v for k, v in vars(a).items() if k not in ("run_dir", "out")}
    params["plan"] = run.spec_plan(spec_path)
    run.write_manifest(a.out, "contig_glue", spec_path, a.extract, params, a.plans_file, a.run_dir)
    states = tuple(x for x in a.states.split(",") if x)
    s, ref, ext, polygon, inst, plans, reports, owners, src = repair.load(
        a.run_dir, a.extract, a.plans, a.plans_file, states)
    adj = gate_adjacency(polygon)
    report, owner_after = {"channels": {}, "source": os.path.abspath(a.run_dir), "states": list(states)}, {}
    for c in plans:
        m = necks_gate.channel_mass(inst, c)        # every ZCTA of the channel: the gate's relays
        if a.channels is not None and c not in a.channels:
            owner_after[c] = owners[c]
            continue
        necks_of, _ = neck_counter(polygon, m)
        owner_after[c], rep = glue_channel(owners[c], adj, m, necks_of, a.tries, inst.channels[c].tau)
        report["channels"][c] = rep
        print(f"{c}: glued {len(rep['glued'])}, left {len(rep['left'])}, moved {len(rep['moved'])} ZCTAs", flush=True)
    moved = sum(len(r["moved"]) for r in report["channels"].values())
    with open(os.path.join(a.out, "glue.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
        fh.write("\n")
    if not moved:
        run.write_manifest(a.out, "contig_glue", spec_path, a.extract, params, status="done",
                           stop_reason="nothing to glue")
        print("nothing moved; the source folder stays the one to go on from", flush=True)
        return 0
    border = draw.border_km(run.induced_graph(polygon, states) if states else polygon)
    connectors = set(geo.approved_connectors(geo.read_connectors()))
    with open(os.path.join(a.run_dir, "contig.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    drawings = {}
    for c, plan in plans.items():
        res = draw.Result(c, owner_after[c], [], set(), [], [], plan.delta, "repair", False)
        drawings[c] = d = draw.drawing(inst, plan, res)
        entry = doc["channels"][c]
        left = repair.detached(owner_after[c], adj, inst.channels[c].m)
        if c in report["channels"] and report["channels"][c]["moved"]:
            entry["glue"] = {k: v for k, v in report["channels"][c].items() if k != "moved"}
            entry["glue"]["moved_zctas"] = len(report["channels"][c]["moved"])
            entry["connected"] = not left
        entry.update(run.drawn_stats(inst, plan, d, connectors, not left, border))
    rep, m1 = run.write_folder(a.out, s, inst, ext, ref, polygon, plans, reports, drawings,
                               f"{s.name} ({doc['arm']} + glue repair{', ' + a.label if a.label else ''})",
                               f"tools/exp/contig ({doc['arm']} + glue)", src.get("source", ""), False)
    doc.update({"arm": doc["arm"] + "+glue", "glue_of": os.path.abspath(a.run_dir), "m1": rep["m1"]})
    with open(os.path.join(a.out, "contig.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    run.write_manifest(a.out, "contig_glue", spec_path, a.extract, params, status="done",
                       stop_reason="glued", audit=rep["verdict"], m1=m1.status)
    print(f"{s.name} (glue of {a.run_dir}): {moved} ZCTAs moved; M1 {m1.status} ({m1.summary})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
