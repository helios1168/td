"""split_floor.py -- the split floor per channel and K (experimental, td#94).

    "$TD_PY" tools/exp/split_floor.py [--band 0.10 --band 0.15]

Prints, for each layout and each K the $ rule allows, the fewest channel-state splits any plan
can have and whether the K can balance at all.  Arithmetic on the units' masses only: no solve.

Layouts (the 2026-10-02 looks driver's `scenario()`, `runs/sweep/comb_2026-10-02/run3.py`, with
routing `stay` and every rest unit national): `none`, no combined channel; `ne`, New England
(CT MA ME NH RI VT) as a combined channel; `ne_plains`, New England plus the nine okks plains
states (ID KS MT ND NE NM OK SD WY).  National, WH and FI plan the rest units' NAT3, wh and fi;
the combined channel plans all five fine channels of its units.  IFA plans ifa over all 49 units
(`scenarios/50_ifa.toml`).

Per channel c with mass M_c over its units v (`td.spec.build`'s M_v) and K districts,
τ = M_c / K, at band δ:
- **forced splits**: a whole unit lies in one district, so a unit with M_v > (1 + δ)τ is split
  in every plan, into at least ⌈M_v / ((1 + δ)τ)⌉ pieces, that many minus one cuts.  The count of
  such units is the channel's split floor at K;
- **parts floor**: each connected component of the channel's units (the unit graph of the
  declared ZIP graph) takes a whole number k_i ≥ 1 of districts, Σ k_i = K, so no plan beats
  min over k of max_i |M_i / (k_i τ) − 1|.  A K whose parts floor exceeds δ has no plan at δ.

The $ rule: K is allowed when the channel's $ per district is within ±10% of its target
(national $1.25B, WH $1.0B, FI $900M, IFA $1.25B; `docs/problem/PROBLEM.md` row 2026-10-04).
A fine channel's $ per m_rel unit is the owner's 2026-10-01 total over the whole extract's m_rel,
as `runs/sweep/grid_2026-10-01/prep.py` set it; a channel's dollars sum its cells on the CONUS
units it plans.  The combined channel has no target (D11), so it is
listed at every K from 1 to the most districts any target of the channels it absorbs allows.
The s13 baseline's K values (`runs/sweep/comb_2026-10-02/s13/`) and IFA K 46-55 are listed too,
flagged when the $ rule does not allow them.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import data, geo, output                                # noqa: E402
from td import spec as tdspec                                   # noqa: E402

TD_REPO = os.environ.get("TD_REPO", "/Users/Shared/sv-ntlee/td")
EXTRACT = os.path.join(TD_REPO, "instance_descaled.json.gz")
PUBLIC = os.path.join(TD_REPO, "data", "public")

NAT3 = ["national_chase", "wells_wh", "wells_fi"]
NE6 = ["CT", "MA", "ME", "NH", "RI", "VT"]
OKKS = ["ID", "KS", "MT", "ND", "NE", "NM", "OK", "SD", "WY"]
LAYOUTS = {"none": [], "ne": NE6, "ne_plains": NE6 + OKKS}
# $ billion over the whole extract, the owner's 2026-10-01 figures
# (docs/memory/facts/scenario-sweeps-2026-10.md § Dollars and K)
OWNER_USD_B = {"wh": 11.36, "fi": 20.69, "wells_wh": 4.44, "wells_fi": 4.63,
               "national_chase": 8.55, "ifa": 62.14}
TARGET_USD_M = {"national": 1250.0, "WH": 1000.0, "FI": 900.0, "IFA": 1250.0}
USD_TOLERANCE = 0.10
# what the combined channel absorbs from each layout channel, for its K range
ABSORBED = ("national", "WH", "FI")
BASELINE_K = {"ne_plains": {"national": 15, "WH": 12, "FI": 20, "combined": 3}}   # s13
# td#94 lists IFA at K 46-55, its $ rule on the whole extract's $62.14B; on the CONUS units
# IFA plans the rule allows 45-54
LISTED_K = {"IFA": range(46, 56)}


def usd_factors(extract) -> dict:
    """$M per m_rel unit for each fine channel: the owner's total over the extract's total."""
    tot = dict.fromkeys(OWNER_USD_B, 0.0)
    for f, m in zip(extract.channel, extract.m_rel):
        if f in tot:
            tot[f] += m
    return {f: OWNER_USD_B[f] * 1e3 / tot[f] for f in OWNER_USD_B}


def layout_raw(combined: list) -> dict:
    """The main scenario of a layout: national, WH and FI over the rest units, the combined
    channel over `combined` when it is not empty."""
    rest = "all - combined" if combined else "all"
    raw = {"scenario": {"name": "split_floor", "fine_channels": NAT3 + ["wh", "fi"],
                        "planned_elsewhere": ["career", "edj", "ifa", "imo", "priafs"]},
           "sets": {"combined": combined} if combined else {},
           "national": {"channel": "national", "fine": NAT3, "units": rest,
                        "fallback": {"national_chase": "fi", "wells_fi": "fi",
                                     "wells_wh": "wh"}},
           "channels": {"national": {"k": 1, "eta": 0.05, "domain": [{"units": rest, "fine": NAT3}]},
                        "WH": {"k": 1, "eta": 0.05, "domain": [{"units": rest, "fine": ["wh"]}]},
                        "FI": {"k": 1, "eta": 0.05, "domain": [{"units": rest, "fine": ["fi"]}]}}}
    if combined:
        raw["channels"]["combined"] = {"k": 1, "eta": 0.05, "domain": [
            {"units": "combined", "fine": NAT3 + ["wh", "fi"]}]}
    return raw


def ifa_raw() -> dict:
    with open(os.path.join(ROOT, "scenarios", "50_ifa.toml"), "rb") as fh:
        return tomllib.load(fh)


def components(units, unit_adj) -> list:
    """The connected components of the unit graph induced on `units`, heaviest-first order is
    left to the caller."""
    inside, seen, comps = set(units), set(), []
    for u in sorted(inside):
        if u in seen:
            continue
        comp, stack = [], [u]
        seen.add(u)
        while stack:
            v = stack.pop()
            comp.append(v)
            for w in unit_adj[v]:
                if w in inside and w not in seen:
                    seen.add(w)
                    stack.append(w)
        comps.append(sorted(comp))
    return comps


def forced_splits(M: dict, tau: float, band: float) -> dict:
    """{unit: cuts} for each unit over (1 + band)τ: ⌈M_v / ((1 + band)τ)⌉ − 1 cuts."""
    cap = (1 + band) * tau
    return {v: math.ceil(m / cap) - 1 for v, m in M.items() if m > cap}


def parts_floor(masses: list, k: int) -> tuple:
    """(δ, allocation): min over k_i ≥ 1 with Σ k_i = k of max_i |masses_i / (k_i τ) − 1|,
    τ = Σ masses / k; (inf, None) when there are more parts than districts."""
    n = len(masses)
    if n > k:
        return math.inf, None
    tau = sum(masses) / k
    # best[s]: (worst deviation, allocation) over the parts so far using s districts
    best = {0: (0.0, ())}
    for i, m in enumerate(masses):
        nxt = {}
        left = n - i - 1                    # the later parts need a district each
        for s, (d, alloc) in best.items():
            for ki in range(1, k - left - s + 1):
                cand = (max(d, abs(m / (ki * tau) - 1)), alloc + (ki,))
                if s + ki not in nxt or cand[0] < nxt[s + ki][0]:
                    nxt[s + ki] = cand
        best = nxt
    return best[k]


def k_range(usd_m: float, targets: list, tolerance: float = USD_TOLERANCE) -> range:
    """The K whose $ per district is within ±tolerance of one of `targets` ($M)."""
    lo = min(math.ceil(usd_m / ((1 + tolerance) * t)) for t in targets)
    hi = max(math.floor(usd_m / ((1 - tolerance) * t)) for t in targets)
    return range(max(lo, 1), hi + 1)


def channel_rows(name: str, M: dict, unit_adj: dict, usd_m: float, ks, bands) -> list:
    """One row per K: $ per district, and per band the forced splits and the parts floor."""
    comps = sorted(components(M, unit_adj), key=lambda c: -sum(M[u] for u in c))
    masses = [sum(M[u] for u in c) for c in comps]
    labels = [max(c, key=M.get) + (f"+{len(c) - 1}" if len(c) > 1 else "") for c in comps]
    total = sum(M.values())
    target = TARGET_USD_M.get(name)
    rows = []
    for k in ks:
        tau = total / k
        row = {"channel": name, "k": k, "usd_per_district_m": usd_m / k,
               "usd_dev": None if target is None else usd_m / k / target - 1,
               "usd_ok": None if target is None
               else abs(usd_m / k / target - 1) <= USD_TOLERANCE + 1e-12,
               "parts": labels, "bands": {}}
        floor, alloc = parts_floor(masses, k)
        for b in bands:
            cuts = forced_splits(M, tau, b)
            row["bands"][b] = {"forced": dict(sorted(cuts.items(), key=lambda kv: -M[kv[0]])),
                               "n_forced": len(cuts), "cuts": sum(cuts.values()),
                               "parts_floor": floor, "allocation": alloc,
                               "feasible": floor <= b + 1e-12}
        rows.append(row)
    return rows


def channel_usd(spec, inst, ext, fac: dict) -> dict:
    """$M per planning channel over the instance's placed ZIPs."""
    usd: dict = {}
    for z, f, m in zip(ext.z, ext.channel, ext.m_rel):
        u = inst.units.unit_of.get(z)
        if u is not None:
            c = spec.channel_of(u, f)
            usd[c] = usd.get(c, 0.0) + m * fac[f]
    return usd


def layout_tables(raw: dict, extract, ref, fac: dict, bands, baseline: dict, graph=None) -> tuple:
    """(rows, graph) for one scenario: each channel at its $-rule K and its baseline K."""
    s = tdspec.parse(raw)
    ext = tdspec.scope(s, extract)
    if graph is None:
        graph = output.declared_graph(ext, ref, PUBLIC)
    inst = tdspec.build(s, ext, ref, graph)
    usd = channel_usd(s, inst, ext, fac)
    rows = []
    for name, ch in inst.channels.items():
        if name in TARGET_USD_M:
            ks = set(k_range(usd[name], [TARGET_USD_M[name]]))
        else:
            ks = set(range(1, k_range(usd[name], [TARGET_USD_M[c] for c in ABSORBED]).stop))
        if name in baseline:
            ks.add(baseline[name])
        ks.update(LISTED_K.get(name, ()))
        rows += channel_rows(name, ch.M, inst.units.unit_adj, usd[name], sorted(ks), bands)
    return rows, graph


def markdown(title: str, rows: list, band: float, baseline: dict) -> str:
    pct = f"±{band * 100:g}%"
    lines = [f"### {title} at {pct}", "",
             "| channel | K | $M / district | vs target | forced | cuts | forced states (cuts) "
             "| parts floor | allocation | plan at " + pct + " |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        b = r["bands"][band]
        vs = "no target" if r["usd_dev"] is None else f"{r['usd_dev'] * 100:+.1f}%"
        if r["usd_ok"] is False:
            vs += " (fails $ rule)"
        if baseline.get(r["channel"]) == r["k"]:
            vs += " s13"
        states = " ".join(v if c == 1 else f"{v}({c})" for v, c in b["forced"].items()) or "—"
        alloc = "—" if b["allocation"] is None else ", ".join(
            f"{p} {a}" for p, a in zip(r["parts"], b["allocation"]))
        floor = "∞" if math.isinf(b["parts_floor"]) else f"{b['parts_floor'] * 100:.1f}%"
        lines.append(f"| {r['channel']} | {r['k']} | {r['usd_per_district_m']:,.0f} | {vs} "
                     f"| {b['n_forced']} | {b['cuts']} | {states} | {floor} | {alloc} "
                     f"| {'yes' if b['feasible'] else 'no'} |")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--band", type=float, action="append",
                    help="a plan band δ, repeatable (default: 0.10 and 0.15)")
    ap.add_argument("--extract", default=EXTRACT, help="the extract (default: $TD_REPO's)")
    a = ap.parse_args(argv)
    bands = a.band or [0.10, 0.15]
    ref = geo.read_reference()
    raw_extract = data.load(a.extract)
    fac = usd_factors(raw_extract)
    extract = data.conus(raw_extract, ref)
    tables, graph = [], None
    for layout, combined in LAYOUTS.items():
        rows, graph = layout_tables(layout_raw(combined), extract, ref, fac, bands,
                                    BASELINE_K.get(layout, {}), graph)
        tables.append((f"Layout `{layout}`", rows, BASELINE_K.get(layout, {})))
    rows, _ = layout_tables(ifa_raw(), extract, ref, fac, bands, {})
    tables.append(("IFA", rows, {}))
    for band in bands:
        print(f"## Split floor at ±{band * 100:g}%\n")
        for title, rows, baseline in tables:
            print(markdown(title, rows, band, baseline) + "\n")
    s13 = {r["channel"]: r for r in tables[2][1]
           if BASELINE_K["ne_plains"].get(r["channel"]) == r["k"]}
    for band in bands:
        forced = [f"{c} " + " ".join(s13[c]["bands"][band]["forced"]) for c in s13
                  if s13[c]["bands"][band]["forced"]]
        n = sum(s13[c]["bands"][band]["n_forced"] for c in s13)
        print(f"s13 (ne_plains, national 15, WH 12, FI 20, combined 3) at ±{band * 100:g}%: "
              f"{n} forced splits: " + "; ".join(forced))
    return 0


if __name__ == "__main__":
    sys.exit(main())
