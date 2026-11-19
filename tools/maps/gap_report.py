"""tools/maps/gap_report.py (issue #148): one markdown report on stdout from the CSVs scenario_maps.py writes for a run.

    python tools/maps/gap_report.py FILE [FILE ...]    (any of gap_summary.csv, gap_pair.csv, gap_person.csv, gap_load.csv)

A row's SCENARIO is the scenarios that share it, space-separated (ALL, from older runs, is not accepted: it does not say who).

Per estimate: scenario comparison, overlaps (for bargaining), gaps (for optimization), load, person.  MM_OPP and *_USD are raw
dollars, printed as $B.  Holder keys R<n> only: the input holds no names and nothing here adds one."""
import argparse
import collections
import csv
import sys

KINDS = ("summary", "pair", "person", "load")
CLASSES = ("COVERED", "OVERLAP", "HELD BY ANOTHER", "GAP (HELD TODAY)", "GAP (UNHELD)", "OPEN SEAT HELD", "OPEN SEAT UNHELD")


def b(x):
    return f"${float(x or 0) / 1e9:,.2f}B"


def num(r, c):
    return float(r.get(c) or 0)


def table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows]) + "\n"


def top(rows, key, n, rev=True):
    return sorted(rows, key=lambda r: num(r, key), reverse=rev)[:n]


def read(paths):
    """{kind: [row dict]} by file name suffix; an unrecognised name is an error."""
    data = collections.defaultdict(list)
    for p in paths:
        kind = next((k for k in KINDS if p.endswith(f"gap_{k}.csv")), None)
        if kind is None:
            sys.exit(f"gap_report: {p}: not a gap_summary/gap_pair/gap_person/gap_load .csv")
        with open(p, encoding="utf-8-sig", newline="") as f:
            data[kind] += list(csv.DictReader(f))
    if any(r["SCENARIO"] == "ALL" for rows in data.values() for r in rows):
        sys.exit("gap_report: a SCENARIO of ALL does not say which scenarios: rerun scenario_maps.py")
    # a shared row is one row per scenario again
    return collections.defaultdict(list, {k: [dict(r, SCENARIO=s) for r in rows for s in r["SCENARIO"].split()] for k, rows in data.items()})


def failing_checks(summary):
    """TIE rows with MUST_BE_ZERO 1 whose N_ZIPS is not 0 or whose |MM_OPP| is 1 dollar or more."""
    return [r for r in summary if num(r, "MUST_BE_ZERO") == 1 and (num(r, "N_ZIPS") != 0 or abs(num(r, "MM_OPP")) >= 1)]


def compare(rows, scens):
    cells = {(r["CHANNEL"], r["ITEM"], r["SCENARIO"]): r for r in rows if r["SECTION"] == "CLASS"}
    keys = sorted({k[:2] for k in cells}, key=lambda k: (k[0], CLASSES.index(k[1]) if k[1] in CLASSES else 99))
    out = []
    for ch, item in keys:
        got = [cells.get((ch, item, s)) for s in scens]
        dol = [num(g, "MM_OPP") if g else 0.0 for g in got]
        out.append([ch, item] + [f"{b(g['MM_OPP'])} ({num(g, 'PCT'):.1f}%)" if g else "-" for g in got] + [b(max(dol) - min(dol))])
    return table(["channel", "class"] + scens + ["max-min $B"], out)


def overlaps(summary, pairs):
    out = "Top 15 pairs by $:\n\n" + table(["channel", "A", "B", "ZIPs", "$B"], [[r["CHANNEL"], r["HOLDER_A"], r["HOLDER_B"], r["N_ZIPS"], b(r["MM_OPP"])] for r in top(pairs, "MM_OPP", 15)])
    out += "\nPairs are not additive: a cell held by 3 holders is in 3 pairs.\n"
    tot = collections.Counter()
    for r in summary:
        if r["SECTION"] == "CLASS" and r["ITEM"] in ("OVERLAP", "HELD BY ANOTHER"):
            tot[r["CHANNEL"]] += num(r, "MM_OPP")
    return out + "\nOVERLAP + HELD BY ANOTHER per channel:\n\n" + table(["channel", "$B"], [[c, b(v)] for c, v in sorted(tot.items())])


def gaps(summary):
    st = [(r["CHANNEL"], *r["ITEM"].split(" | ", 1), r) for r in summary if r["SECTION"] == "STATE" and " | " in r["ITEM"]]
    out = ""
    for ch in sorted({s[0] for s in st} - {"OPEN"}):              # OPEN has no GAP: its seats are the table below
        g = collections.defaultdict(lambda: [0, 0.0, 0.0])        # state -> ZIPs, held today $, unheld $
        for c, s, cls, r in st:
            if c == ch and cls.startswith("GAP"):
                g[s][0] += num(r, "N_ZIPS")
                g[s][1 if "HELD TODAY" in cls else 2] += num(r, "MM_OPP")
        rows = sorted(g.items(), key=lambda kv: -(kv[1][1] + kv[1][2]))[:15]
        out += (f"Top 15 states by GAP, {ch} (held today: a hand-over; unheld: no one works it):\n\n"
                + table(["state", "ZIPs", "gap $B", "held today $B", "unheld $B"], [[s, int(n), b(h + u), b(h), b(u)] for s, (n, h, u) in rows]) + "\n")
    seat = collections.defaultdict(lambda: [0, 0.0])
    for ch, s, c, r in st:
        if c in ("OPEN SEAT HELD", "OPEN SEAT UNHELD"):
            seat[(ch, s)][0] += num(r, "N_ZIPS")
            seat[(ch, s)][1] += num(r, "MM_OPP")
    top15 = sorted(seat.items(), key=lambda kv: -kv[1][1])[:15]
    return out + "Top 15 states by OPEN SEAT HELD + UNHELD:\n\n" + table(["channel", "state", "ZIPs", "$B"], [[ch, s, int(n), b(v)] for (ch, s), (n, v) in top15])


def load(rows):
    out = ""
    for ch in sorted({r["CHANNEL"] for r in rows}):
        rr = [r for r in rows if r["CHANNEL"] == ch and r["LOAD_RATIO"] not in (None, "")]
        row = lambda r: [r["HOLDER"], r["ROLE"], f"{num(r, 'AREA_KM2'):,.0f}", b(r["ASSIGNED_USD"]), b(r["EXPECTED_USD"]), f"{num(r, 'LOAD_RATIO'):.2f}"]
        head = ["holder", "role", "km2", "$B", "expected $B", "ratio"]
        hi, lo = sum(num(r, "LOAD_RATIO") > 1.25 for r in rr), sum(num(r, "LOAD_RATIO") < 0.8 for r in rr)
        out += (f"{ch}: {hi} above 1.25, {lo} below 0.8 (of {len(rr)}).\n\nHighest 10:\n\n" + table(head, map(row, top(rr, "LOAD_RATIO", 10)))
                + "\nLowest 10:\n\n" + table(head, map(row, top(rr, "LOAD_RATIO", 10, False))) + "\n")
    return out


def person(rows):
    out = ""
    for col in ("OPP_GAP", "OPP_HELD_ELSEWHERE"):
        out += f"Top 10 by {col}:\n\n" + table(["holder", "source", "role", "states", "$B"], [[r["HOLDER"], r["SOURCE"], r["ROLE"], r["ASSIGNED_STATES"], b(r[col])] for r in top(rows, col, 10)]) + "\n"
    return out


def report(data):
    out = ["# Gap report\n"]
    bad = failing_checks(data["summary"])
    out += [f"**CHECK FAILED: {r['SCENARIO']} {r['EST_SOURCE']} {r['CHANNEL']} {r['ITEM']}: N_ZIPS {r['N_ZIPS']}, MM_OPP {r['MM_OPP']} (must be 0)**\n" for r in bad]
    ests = sorted({r["EST_SOURCE"] for k in KINDS for r in data[k]} - {""})   # the no-key TIE row has no estimate
    for est in ests:
        by = {k: [r for r in data[k] if r["EST_SOURCE"] == est] for k in KINDS}
        scens = sorted({r["SCENARIO"] for k in KINDS for r in by[k]})
        out.append(f"## {est}\n")
        if by["summary"]:
            out.append(f"### 1. Scenario comparison\n\n{compare(by['summary'], sorted({r['SCENARIO'] for r in by['summary']}))}")
        for n, title, kind, fn in ((2, "Overlaps, for bargaining", "summary", None), (3, "Gaps, for optimization", "summary", gaps),
                                   (4, "Load", "load", load), (5, "Person", "person", person)):
            out.append(f"### {n}. {title}\n")
            for s in scens:
                rows = [r for r in by[kind] if r["SCENARIO"] == s]
                if n == 2:
                    pr = [r for r in by["pair"] if r["SCENARIO"] == s]
                    if rows or pr:
                        out.append(f"#### {s}\n\n{overlaps(rows, pr)}")
                elif rows:
                    out.append(f"#### {s}\n\n{fn(rows)}")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+")
    print(report(read(ap.parse_args(argv).files)))


if __name__ == "__main__":
    main()
