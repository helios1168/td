"""Open seats chosen by optimisation (owner, 2026-11-19: "49. 2 no load cap, 3.yes, 4 yes"; settings in tools/snowflake/DATASET_LOG.md,
"2026-11-19: open seats chosen by optimisation, settings"), per scenario and per estimate, from td_seat_fit (08).

Every open seat goes whole to one option: a NEIGHBOUR (a kept person whose assigned states border it), a re-added HOLDER (not kept, with a
piece in it; one holder may take a set of seats connected in the state adjacency), or stays VACANT (only when no neighbour borders it).
  roster   at most ROSTER_CAP (49) people: the sheet's people plus the re-added holders, so P = 49 - sheet people re-adds at most;
           a sheet already over the cap (P < 0) has no plan: the caller refuses it
  scores   exact (unrounded) everywhere: the inner Nash, F, the trimming of holders and the ranking; rounding is for display only
  inner    with the re-added set fixed, the neighbours' seats maximise  sum_k ln(1 + U_k(X_k) / g_k)  (term 0 when g_k is NULL or <= 0)
  outer    maximise F = sum of the re-adds' U + the neighbours' U of that inner optimum; vacancy counts 0
  ranking  higher F, then higher inner Nash, then fewer re-adds, then lower key numbers; the inner problem's own ties: higher sum U, then lower key numbers
Exact: every set of seats given to re-adds is tried, the inner problem is solved by memoised recursion over people and seats, and the
re-add packings are enumerated depth-first with a bound (sum of the best U of every seat not yet fixed) against the 4th best F so far.
ponytail: ceiling MAX_SEATS open seats (2^seats per person); a longer list fails loudly.  A dense made-up 14-seat instance (45 people, 30 holders of
4 seats each, nearly equal F everywhere) takes ~40 s because the bound barely prunes; 12 seats with 4 neighbours each ~4 s.  Upgrade path: a tighter bound.
"""
from __future__ import annotations

import math

ROSTER_CAP = 49
ROLES = ("NATIONAL", "WH", "WIFI")
TOP = 4                 # the optimum and the next 3 distinct plans
MAX_SEATS = 14
EPS = 0.01              # dollars: slack on the pruning bound only (float noise in its sum); never in a comparison between plans


def keynum(k):
    return int(str(k)[1:])        # 'R12' -> 12


def sheet_count(person, est):
    """People on the sheet for `est`: distinct kept HOLDER keys with role NATIONAL, WH or WIFI in gap["person"] (dict rows)."""
    return len({p["HOLDER"] for p in person if p["EST_SOURCE"] == est and str(p["ROLE"] or "").upper() in ROLES})


def roster_room(person, est):
    """P: how many holders may be re-added; negative when the sheet is over ROSTER_CAP (not clamped: the caller refuses the plan).
    An estimate with no person row is an error, never 49."""
    n = sheet_count(person, est)
    if not n:
        raise ValueError(f"no person on the sheet for estimate {est}: gap_person is missing it")
    return ROSTER_CAP - n


def connected(mask, nb):
    """Is the set of seats `mask` connected, `nb[i]` the mask of the seats next to seat i?"""
    seen = todo = mask & -mask
    while todo:
        i = todo.bit_length() - 1
        todo &= ~(1 << i)
        new = nb[i] & mask & ~seen
        seen |= new
        todo |= new
    return seen == mask


def submasks(m):
    """Every submask of m, m first, 0 last."""
    x = m
    while True:
        yield x
        if not x:
            return
        x = (x - 1) & m


def optimize(rows, adj, p, top=TOP):
    """The best `top` plans of one estimate as dicts {F, nash, readds, gap, choices: [{seat, choice, holder, bundle, u}]}, best first.
    rows: td_seat_fit's rows of the estimate (dicts: SEAT, KIND, HOLDER, KEPT, U, G); adj: {(a, b)} state pairs; p: re-adds allowed."""
    seats = sorted({r["SEAT"] for r in rows})
    n = len(seats)
    if p < 0:
        raise ValueError(f"P = {p}: the sheet is over the roster cap of {ROSTER_CAP}, there is no plan")
    if n > MAX_SEATS:
        raise ValueError(f"{n} open seats: seat_optimize is exact up to {MAX_SEATS}")
    if not n:
        return []
    ix = {s: i for i, s in enumerate(seats)}
    nb = [sum(1 << ix[b] for b in seats if b != a and ((a, b) in adj or (b, a) in adj)) for a in seats]
    num = lambda v: 0.0 if v is None else float(v)
    neigh, hold, gk = {}, {}, {}
    for r in rows:
        if r["KIND"] == "NEIGHBOUR":
            neigh.setdefault(r["HOLDER"], {})[ix[r["SEAT"]]] = num(r["U"])
            gk[r["HOLDER"]] = None if r["G"] is None else float(r["G"])
        elif r["KIND"] == "HOLDER" and str(r["KEPT"]).upper() == "N":
            hold.setdefault(r["HOLDER"], {})[ix[r["SEAT"]]] = num(r["U"])
    people = sorted(neigh, key=keynum)
    pmask = {k: sum(1 << i for i in neigh[k]) for k in people}
    has_nb = sum(1 << i for i in range(n) if any(i in neigh[k] for k in people))

    def term(k, x):
        g = gk[k]
        if not x or g is None or g <= 0:
            return 0.0
        u = sum(neigh[k][i] for i in range(n) if x >> i & 1)
        return math.log1p(u / g) if u / g > -1 else -math.inf

    def usum(table, x):
        return sum(table[i] for i in range(n) if x >> i & 1)

    def better(a, b):       # higher Nash, then higher sum U, then lower key numbers (takers sorted by seat)
        return (a[0], a[1]) > (b[0], b[1]) or ((a[0], a[1]) == (b[0], b[1]) and a[2] < b[2])

    memo = {}

    def inner(i, rest):
        """(nash, sum U, takers) of the best way for people i.. to take exactly the seats `rest`: takers ((seat, key number), ...) sorted."""
        if not rest:
            return 0.0, 0.0, ()
        if i == len(people):
            return None
        if (i, rest) in memo:
            return memo[i, rest]
        k = people[i]
        best = None
        for x in submasks(rest & pmask[k]):
            sub = inner(i + 1, rest & ~x)
            if sub is None:
                continue
            cand = (sub[0] + term(k, x), sub[1] + usum(neigh[k], x),
                    tuple(sorted(sub[2] + tuple((s, keynum(k)) for s in range(n) if x >> s & 1))))
            if best is None or better(cand, best):
                best = cand
        memo[i, rest] = best
        return best

    # re-add bundles: per holder the connected subsets of its seats; per bundle only the best n + top - 1 holders can sit in a top plan
    cands = {}
    for h, us in hold.items():
        own = sum(1 << i for i in us)
        for b in submasks(own):
            if b and connected(b, nb):
                cands.setdefault(b, []).append((-usum(us, b), keynum(h), h))
    by_low = {}
    for b, hs in cands.items():
        for u, kn, h in sorted(hs)[:n + top - 1]:
            by_low.setdefault((b & -b).bit_length() - 1, []).append((-u, kn, h, b))
    for v in by_low.values():
        v.sort(key=lambda t: (-t[0], t[1], t[3]))
    best_n = [max([neigh[k][i] for k in people if i in neigh[k]], default=0.0) for i in range(n)]
    best_h = [max([hold[h][i] for h in hold if i in hold[h]], default=0.0) for i in range(n)]

    pool = []      # sorted: (-F, -nash, readds, key numbers, plan data), exact

    def leaf(covered, packs, uh):
        rest = has_nb & ~covered
        sol = inner(0, rest)
        f = uh + sol[1]
        take = dict(sol[2])
        keys = tuple(next((keynum(h) for h, b in packs if b >> s & 1), take.get(s, 10 ** 9)) for s in range(n))
        entry = (-f, -sol[0], len(packs), keys, (f, sol[0], tuple(packs), take))
        pool.append(entry)
        pool.sort(key=lambda e: e[:4])
        del pool[top:]

    def rec(i, covered, packs, uh):
        if len(pool) == top:
            bound = uh + sum(max(best_n[j], best_h[j]) if j >= i else best_n[j] for j in range(n) if not covered >> j & 1)
            if bound < -pool[-1][0] - EPS:
                return
        if i == n:
            return leaf(covered, packs, uh)
        if covered >> i & 1:
            return rec(i + 1, covered, packs, uh)
        if len(packs) < p:
            used = {h for h, _ in packs}
            for u, _, h, b in by_low.get(i, []):
                if h not in used and not b & covered:
                    rec(i + 1, covered | b, packs + [(h, b)], uh + u)
        rec(i + 1, covered, packs, uh)

    rec(0, 0, [], 0.0)
    best_f = pool[0][4][0]
    plans = []
    for _, _, _, _, (f, nash, packs, take) in pool:
        who = {s: (h, b) for h, b in packs for s in range(n) if b >> s & 1}
        ch = []
        for s in range(n):
            if s in who:
                h, b = who[s]
                ch.append({"seat": seats[s], "choice": "READD", "holder": h, "u": hold[h][s], "bundle": tuple(seats[t] for t in range(n) if b >> t & 1)})
            elif s in take:
                k = next(k for k in people if keynum(k) == take[s])
                ch.append({"seat": seats[s], "choice": "NEIGHBOUR", "holder": k, "u": neigh[k][s], "bundle": ()})
            else:
                ch.append({"seat": seats[s], "choice": "VACANT", "holder": "", "u": 0.0, "bundle": ()})
        plans.append({"F": f, "nash": nash, "readds": len(packs), "gap": (best_f - f) / best_f if best_f else 0.0, "choices": ch})
    return plans


def summary(est, plan, p):
    """One line for a scenario's estimate (the caller prefixes the scenario): re-adds out of P, vacancies, the plan."""
    ch = plan[0]["choices"]
    seat = lambda c: f"{c['seat']}={c['holder'] or 'vacant'}" + ("*" if c["choice"] == "READD" else "")
    return (f"{est}: re-adds {plan[0]['readds']} of {p}, vacancies {sum(c['choice'] == 'VACANT' for c in ch)}, plan "
            + " ".join(seat(c) for c in ch) + " (* re-added)")
