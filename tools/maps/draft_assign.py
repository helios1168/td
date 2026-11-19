"""tools/maps/draft_assign.py (issue #152, step 1): a draft complete (ZCTA -> person) assignment per scenario and role, with an M1 audit.

    python tools/maps/draft_assign.py --cells gap_cell.csv --people gap_person.csv --out results/draft/<name> [--ref DIR]

Inputs are scenario_maps.py's gap_cell.csv and gap_person.csv (a row's SCENARIO is the scenarios that share it, space-separated).
`--out` is a folder (made if missing); `<name>` is its last part.  `--ref` is the reference folder of the M1 graph (default
$TD_REPO/reference/2025, else <repo>/reference/2025).  The graph is td.geo.polygon_graph (polygon rook edges plus the approved
connectors) and its own ZCTA -> state map (two-letter codes, as ASSIGNED_STATES).

Per scenario and role r (NATIONAL, WH, WIFI; REGIONAL channel = WIFI role) a territory map T_r from ZCTA to person key:
  1. a state with one role-r assignee goes whole to them, zero-opportunity ZCTAs too ('whole state');
  2. a state with two or more: seeds (a ZIP with a COVERED role-r cell held by exactly one assignee; two assignees on one ZIP: the
     one with more $ over both estimates; 'seed'), multi-source breadth-first growth inside the state, ties to the lowest key
     number ('grown'), then repair: each person keeps their piece with most $ (ties: most ZCTAs), every other piece goes to the
     assignee it shares most edges with inside the state ('repaired'), until no one has two pieces in the state or a piece touches
     no other assignee (it stays, and shows in M1 as a piece).  A ZCTA cut off from every seed goes to the assignee (with a seed in
     its state) holding most edges into it, any state ('cut off'), else stays with PERSON '' and REASON 'unreachable'.  An assignee
     with no seed has no territory there: NOTE 'no seed in <state>';
  3. a state with no role-r assignee is not in T_r.
Cells: PERSON = T_{role of CHANNEL}[ZIP]; an OPEN cell is 'OPEN <STATE>'; a ZIP not in the graph is 'no ZCTA'; a ZIP in no T_r entry
is 'no territory' ('unreachable' if it sits in an unreachable ZCTA).

Outputs in `--out`: <name>_ledger.csv.gz, <name>_cells.csv.gz, <name>_m1.csv (columns in LEDGER_COLS, CELL_COLS, M1_COLS), each row
once as write_gap_csvs does (write_dedup_csv).  M1: district_pieces on T_r, mass = the person's role cells' $ per ZCTA (CRBG; EQH in
the _EQH columns), the pieces in CRBG order.  A person's pieces are reported, never hidden: PIECE 1 is the largest."""
import argparse
import collections
import csv
import gzip
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
from td import audit, geo  # noqa: E402
import scenario_maps as sm  # noqa: E402  (ROLE_OF, K_OF, BASE_USD, FIRMS, write_dedup_csv)

ROLE_OF, CHANNEL_OF_ROLE, ROLES = sm.ROLE_OF, sm.CHANNEL_OF_ROLE, tuple(dict.fromkeys(sm.ROLE_OF.values()))
EST, EST2 = sm.FIRMS                      # CRBG (the audit's $) and EQH
LEDGER_COLS = ["SCENARIO", "ROLE", "ZIP_CODE", "STATE", "PERSON", "REASON"]
CELL_COLS = ["SCENARIO", "EST_SOURCE", "ZIP_CODE", "NEW_DIST", "CHANNEL", "PERSON", "MM_OPP"]
M1_COLS = ["SCENARIO", "ROLE", "PERSON", "N_PIECES", "PIECE", "N_ZCTAS", "CRBG_USD", "TAU_SHARE", "VERDICT", "NOTE", "EQH_USD", "TAU_SHARE_EQH"]   # *_USD: shared rows compare them to the cent



def m1_adjacency(graph):
    """The adjacency M1 is judged on: the polygon rook graph plus, unless switched off, the approved land gaps of one state
    (R5, #140), as tools/looks/score.py builds it."""
    return audit.adjacency(graph, gaps=audit.gap_width_on())

def keynum(k):
    """Sort key of a person key 'R<n>': its number, then the text."""
    m = re.search(r"\d+", k)
    return (int(m.group()) if m else 10 ** 9, k)


def pieces_of(owner, adj, mass):
    return audit.district_pieces(owner, adj, mass)


def repair(own, adj, mass):
    """`own` {zip: person} of one state, changed in place: every person with two or more pieces gives the others (smallest $ first) to the
    other assignee they share most edges with inside the state (ties: lowest key); a piece touching none stays.  The ZIPs moved."""
    moved, stuck = set(), set()
    while True:
        extra = [(math_sum(mass, c), len(c), min(c), p, c) for p, cs in pieces_of(own, adj, mass).items() for c in cs[1:] if min(c) not in stuck]
        if not extra:
            return moved
        _, _, _, p, c = min(extra)
        touch = collections.Counter(own[w] for z in c for w in adj[z] if w in own and own[w] != p)
        if not touch:
            stuck.add(min(c))
            continue
        q = min(touch, key=lambda k: (-touch[k], keynum(k)))
        for z in c:
            own[z] = q
        moved |= set(c)


def math_sum(mass, c):
    return sum(mass.get(z, 0.0) for z in c)


def territory(state_zips, adj, assignees, covered, mass, held=None):
    """One role's T: ({zip: (person, reason)}, no_seed [(state, person)], unreachable [zip]).  `state_zips` {state: [zips]} of the
    graph, `adj` its adjacency, `assignees` {state: [keys]}, `covered` {zip: {person: $}} (COVERED cells held by one person), `mass`
    {zip: $ over both estimates}, `held` {zip: set of people holding any of its cells today}: an assignee of a split state with no
    COVERED seed is seeded with the state's ZIPs they hold today that no one else's seed took (shared with others: OVERLAP, HELD BY
    ANOTHER), lowest key first (the first real data had five such people, each sharing all of their ZIPs with the other assignee)."""
    T, no_seed, split = {}, [], []
    eligible = {}
    for s, ps in sorted(assignees.items()):
        zs = state_zips.get(s, [])
        if len(ps) == 1:
            T.update({z: (ps[0], "whole state") for z in zs})
            continue
        zset, own = set(zs), {}
        for z in zs:
            c = {p: u for p, u in covered.get(z, {}).items() if p in ps}
            if c:
                own[z] = min(c, key=lambda p: (-c[p], keynum(p)))
        reason = {z: "seed" for z in own}
        for p in sorted(set(ps) - set(own.values()), key=keynum):
            got = {z: p for z in zs if z not in own and p in (held or {}).get(z, ())}
            own.update(got)
            reason.update({z: "held seed" for z in got})
        eligible[s] = set(own.values())
        no_seed += [(s, p) for p in sorted(ps, key=keynum) if p not in eligible[s]]
        frontier = sorted(own)
        while frontier:                       # the nearest seed's person; at a tie the lowest key
            claim = {}
            for z in frontier:
                for w in adj[z]:
                    if w in zset and w not in own and (w not in claim or keynum(own[z]) < keynum(claim[w])):
                        claim[w] = own[z]
            own.update(claim)
            reason.update({w: "grown" for w in claim})
            frontier = sorted(claim)
        reason.update({z: "repaired" for z in repair(own, adj, mass)})
        T.update({z: (p, reason[z]) for z, p in own.items()})
        split.append(s)
    left = {z for s in split for z in state_zips[s] if z not in T}
    state_of = {z: s for s in split for z in state_zips[s]}
    while True:                               # cut off from every seed: the neighbour assignee with most edges into it, any state
        got = {}
        for z in sorted(left):
            n = collections.Counter(T[w][0] for w in adj[z] if w in T and T[w][0] in eligible[state_of[z]])
            if n:
                got[z] = min(n, key=lambda k: (-n[k], keynum(k)))
        if not got:
            break
        T.update({z: (p, "cut off") for z, p in got.items()})
        left -= set(got)
    unreachable = sorted(left)
    T.update({z: ("", "unreachable") for z in unreachable})
    return T, no_seed, unreachable


def role_of_channel(ch):
    if ch not in ROLE_OF:
        raise ValueError(f"CHANNEL {ch!r} is not NATIONAL, REGIONAL, WH or OPEN")
    return ROLE_OF[ch]


def one_scenario(graph, adj, cells, people):
    """(ledger rows, cell rows, m1 rows, report) of one scenario; `cells` and `people` are lists of the CSV rows as dicts."""
    state_zips = collections.defaultdict(list)
    for z in graph["vertices"]:
        state_zips[graph["state"][z]].append(z)
    pers = {}
    for p in people:
        role, key = str(p["ROLE"] or "").upper(), p["HOLDER"]
        if role not in ROLES:
            continue
        states = sorted(set(str(p["ASSIGNED_STATES"] or "").split()))
        if pers.setdefault((role, key), states) != states:
            raise ValueError(f"{key} ({role}) has two different ASSIGNED_STATES: {pers[role, key]} and {states}")
    ledger, m1, report = [], [], {}
    mass = {r: {e: collections.Counter() for e in (EST, EST2)} for r in ROLES}
    covered = {r: collections.defaultdict(collections.Counter) for r in ROLES}
    held = {r: collections.defaultdict(set) for r in ROLES}
    chan_usd = collections.Counter()
    for c in cells:
        ch, usd, est = c["CHANNEL"], float(c["MM_OPP"] or 0), c["EST_SOURCE"]
        chan_usd[est, ch] += usd
        if ch == "OPEN":
            continue
        r, z = role_of_channel(ch), c["ZIP_CODE"]
        mass[r].setdefault(est, collections.Counter())[z] += usd
        holders = str(c["HOLDERS"] or "").split()
        held[r][z].update(holders)
        if c["CLASS"] == "COVERED" and len(holders) == 1:
            covered[r][z][holders[0]] += usd
    T = {}
    for r in ROLES:
        assignees = collections.defaultdict(list)
        for (role, key), states in sorted(pers.items(), key=lambda kv: keynum(kv[0][1])):
            if role == r:
                for s in states:
                    assignees[s].append(key)
        cov = {z: dict(d) for z, d in covered[r].items() if z in graph["state"] and graph["state"][z] in assignees}
        both = collections.Counter()
        for e in mass[r]:
            both.update(mass[r][e])
        T[r], no_seed, unreach = territory(state_zips, adj, assignees, cov, both, held[r])
        owner = {z: p for z, (p, _) in T[r].items() if p}
        pcs = pieces_of(owner, adj, mass[r][EST])
        ch = CHANNEL_OF_ROLE[r]
        tau = {e: sm.BASE_USD[ch] if ch in sm.BASE_USD else chan_usd[e, ch] / sm.K_OF[ch] for e in (EST, EST2)}

        def share(u, e):
            return round(u / tau[e], 6) if tau[e] else ""
        notes = collections.defaultdict(list)
        for s, p in no_seed:
            notes[p].append(f"no seed in {s}")
        extra = 0.0
        n_pass = 0
        for key in sorted({k for (role, k) in pers if role == r}, key=keynum):
            states = pers[r, key]
            missing = [s for s in states if s not in state_zips]
            note = notes[key] + ([f"no graph ZCTAs in {' '.join(missing)}"] if missing else [])
            cs = pcs.get(key, [])
            if not states:
                note.append("no assigned states")
            n_pass += len(cs) == 1
            if not cs:
                m1.append((r, key, 0, "", 0, 0.0, "", "FAIL", "; ".join(note), 0.0, ""))
            for i, c in enumerate(cs, 1):
                u, u2 = (math_sum(mass[r][e], c) for e in (EST, EST2))
                extra += u if i > 1 else 0.0
                m1.append((r, key, len(cs), i, len(c), round(u, 2), share(u, EST), "PASS" if len(cs) == 1 else "FAIL",
                           "; ".join(note) if i == 1 else "", round(u2, 2), share(u2, EST2)))
        n_people = len({k for (role, k) in pers if role == r})
        report[r] = dict(people=n_people, passed=n_pass, failed=n_people - n_pass, extra_usd=extra, no_seed=no_seed, unreachable=unreach)
        ledger += [(r, z, graph["state"][z], p, why) for z, (p, why) in sorted(T[r].items())]
    out, lost = [], collections.Counter()
    for c in cells:
        ch, z = c["CHANNEL"], c["ZIP_CODE"]
        if ch == "OPEN":
            who = "OPEN " + c["STATE"]
        elif z not in graph["state"]:
            who = "no ZCTA"
        else:
            p, why = T[role_of_channel(ch)].get(z, ("", "no territory"))
            who = p or why
        if who in ("no ZCTA", "no territory", "unreachable"):
            lost[who] += float(c["MM_OPP"] or 0) if c["EST_SOURCE"] == EST else 0.0
        out.append((c["EST_SOURCE"], z, c["NEW_DIST"], ch, who, c["MM_OPP"]))
    report["lost_usd"] = dict(lost)
    return ledger, out, m1, report


def split_rows(rows):
    """{scenario: [row dict]} from rows whose SCENARIO is space-separated names."""
    out = collections.defaultdict(list)
    for r in rows:
        if not str(r.get("SCENARIO") or "").strip():
            raise ValueError("a row with no SCENARIO (ALL is not accepted: it does not say who)")
        for s in r["SCENARIO"].split():
            out[s].append(r)
    return out


def run(graph, cells, people):
    """{scenario: (ledger, cell rows, m1 rows, report)} for cell and person rows (dicts) of any scenarios."""
    adj = m1_adjacency(graph)
    cs, ps = split_rows(cells), split_rows(people)
    got = {}
    for s in sorted(set(cs) | set(ps)):
        l, c, m, rep = one_scenario(graph, adj, cs.get(s, []), ps.get(s, []))
        got[s] = ([(s, *x) for x in l], [(s, *x) for x in c], [(s, *x) for x in m], rep)
    return got


def write(out, name, got):
    """The three files for run's result; the paths."""
    os.makedirs(out, exist_ok=True)
    paths = []
    for i, (cols, kind, gz) in enumerate(((LEDGER_COLS, "ledger", True), (CELL_COLS, "cells", True), (M1_COLS, "m1", False))):
        path = os.path.join(out, f"{name}_{kind}.csv" + (".gz" if gz else ""))
        tmp = path[:-3] if gz else path
        sm.write_dedup_csv(tmp, {s: (cols, v[i]) for s, v in got.items()})
        if gz:
            with open(tmp, "rb") as f, gzip.open(path, "wb") as g:
                g.write(f.read())
            os.remove(tmp)
        paths.append(path)
    return paths


def summary(got):
    lines = []
    for s, (_, _, _, rep) in got.items():
        lost = ", ".join(f"{k} ${v / 1e9:,.3f}B" for k, v in sorted(rep["lost_usd"].items())) or "none"
        lines.append(f"{s}: CRBG cell $ with no person: {lost}")
        for r in ROLES:
            x = rep[r]
            lines.append(f"  {r}: {x['people']} people, {x['passed']} PASS, {x['failed']} FAIL, ${x['extra_usd'] / 1e9:,.3f}B CRBG in non-largest pieces; "
                         f"unreachable ZCTAs {len(x['unreachable'])}" + (f" ({' '.join(x['unreachable'][:20])})" if x["unreachable"] else "")
                         + "; no seed: " + (", ".join(f"{p} in {st}" for st, p in x["no_seed"]) or "none"))
    return "\n".join(lines)


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cells", required=True)
    ap.add_argument("--people", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref", default=os.path.join(os.environ.get("TD_REPO", ROOT), "reference", "2025"))
    a = ap.parse_args(argv)
    got = run(geo.polygon_graph(a.ref), read_csv(a.cells), read_csv(a.people))
    paths = write(a.out, os.path.basename(os.path.normpath(a.out)), got)
    print(summary(got))
    print("wrote " + " ".join(paths))


if __name__ == "__main__":
    main()
