"""ifa_index_night.py -- IFA_INDEX.md of the night's K folders (K48..K54) under a sealed root.

    "$TD_PY" tools/exp/contig/ifa_index_night.py <ifa root> [K ...]

Per K: the M1 verdict (every neck or piece `tools/mandates/check.py` wrote to check.txt, with its
ZIPs, km and shares), districts in, under and over the window (run.json's `window`, m_rel
798.74-1148.19, $1,000-1,437.5M), the worst district's $ and distance outside, the split states
(a state whose ledger rows sit in 2+ districts), the mean $ per district and the page links.  A K is
`passes` when M1 fails only on the Manhattan district (owner exception, 2026-10-14) and every district
is in the window.
"""
from __future__ import annotations

import collections
import csv
import json
import os
import re
import sys

LO, HI = 1000.0, 1437.5


def load(root: str, k: int) -> dict:
    d = os.path.join(root, f"K{k}")
    run = json.load(open(os.path.join(d, "run.json")))
    dist = run["districts"]
    names = {r["district"]: r["district_name"] for r in csv.DictReader(open(os.path.join(d, "districts.csv")))}
    held = collections.defaultdict(set)
    for r in csv.DictReader(open(os.path.join(d, "ledger.csv"))):
        if r["district"]:
            held[r["state"]].add(r["district"])
    split = sorted(s for s, ds in held.items() if len(ds) > 1)
    issues = [ln.strip() for ln in open(os.path.join(d, "check.txt")).read().splitlines()[1:]
              if re.match(r"\s+IFA/\w+: (neck|detached|piece)", ln) and "mass neck" not in ln]
    usd = {j: v["usd_m"] for j, v in dist.items()}
    worst = max(usd, key=lambda j: max(usd[j] - HI, LO - usd[j]))
    over = [j for j, v in usd.items() if v > HI]
    under = [j for j, v in usd.items() if v < LO]
    failing = [j for j, v in dist.items() if v["m1"] == "fail"]
    manhattan = [j for j in failing if "Manhattan" in names[j] or "New York" in names[j]]
    return {"k": k, "issues": issues, "names": names, "split": split, "usd": usd, "worst": worst,
            "over": over, "under": under, "failing": failing, "manhattan": manhattan,
            "n": len(dist), "in": len(dist) - len(over) - len(under),
            "mean": sum(usd.values()) / len(usd),
            "region": json.load(open(os.path.join(d, "manifest.json"))).get("command", "")}


def main(argv) -> int:
    root = os.path.abspath(argv[0])
    ks = [int(x) for x in argv[1:]] or list(range(48, 55))
    out = ["# IFA K48..K54, night of 2026-10-14 (sealed root)", "",
           "Window $1,000-1,437.5M per district (m_rel 798.74-1,148.19). M1 under the water and empty-land",
           "gate (branch m5-studio/ifa-night); Manhattan is the only allowed exception (owner, 2026-10-14).",
           "A K `passes` when M1 fails only on the Manhattan district and every district is in the window.", ""]
    rows, notes = [], []
    for k in ks:
        r = load(root, k)
        worst = r["worst"]
        ok_m1 = len(r["failing"]) == 1 and r["failing"] == r["manhattan"]
        verdict = "passes" if ok_m1 and not r["over"] and not r["under"] else "FAILS"
        links = f"[zip_pages.pdf](K{k}/zip_pages.pdf), [zip_summary.png](K{k}/zip_summary.png)"
        rows.append(f"| {k} | {verdict} | {'Manhattan only' if ok_m1 else 'NOT Manhattan only: ' + ', '.join(r['failing'])} "
                    f"| {r['in']}/{len(r['under'])}/{len(r['over'])} | {worst} ${r['usd'][worst]:,.1f}M "
                    f"| {len(r['split'])}: {' '.join(r['split'])} | ${r['mean']:,.1f}M | {links} |")
        notes.append(f"### K{k}\n")
        notes += [f"- {i}" for i in r["issues"]] or ["- no neck or piece"]
        notes.append("")
    out += ["| K | verdict | M1 | districts in/under/over | worst district | split states | mean $/district | pages |",
            "|---|---|---|---|---|---|---|---|"] + rows + ["", "## M1 necks and pieces per K (from check.txt)", ""] + notes
    out += ["Paths are relative to this folder under `$TD_REPO/runs/exp/sealed_2026-10-14/ifa/` (gitignored, hub only)."]
    open(os.path.join(root, "IFA_INDEX.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out[:20]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
