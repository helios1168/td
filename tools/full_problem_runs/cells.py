"""Cell files for the full-problem grids on v4, the input of `tools/full_grid.py`, carrying the
rules the forced-national sweep of 2026-09-11 settled on (`HANDOFF.md`, `PLAN.md`).

    python3 tools/full_problem_runs/cells.py --n 10-16 --wh 11 --fi 21 --group G1 --out cells.json

`--group none` is full rules as `grid_20260911_v4/full/` ran them: split caps CA 3, TX 2, NY 3;
band break on CA and TX; the level-0 sweep and plus pair; MT, WA and WY in the other-first
district; 900 km and six states per district; each bundle's band 10% either side of its own
mean; the counts are ceilings (`--k-mode cap`).

`--group G1` adds `--force-national` on group 1 without CO, whose best N district stays below
the floor at every k from 10 to 16 while UT sits in the other-first district, and puts TX in one
N district (`--tx 1`, the default for both forced groups): under TX=2, k 10 to 13 are infeasible.

`--group G2` forces group 2 (group 1 plus WA UT IN LA MN CT) with no other-first district (MT
and WY cannot reach its floor once WA and UT are forced) and WA's pair cap at 1,200 km.  CO is
forced only at k 15 and above (the user's rule) and LA only at k 14 and above: at k 13 and below
TX and LA together overfill the TX district and LA reaches no floor elsewhere.  G2 at k 14 to 16
solved under TX=2 at FI 20; TX=1 there is untested.

`--rule pure` is the default above.  `--rule cover` covers both national channels in the
planned stages through any national-carrying bundle, for all of G1 or G2 at every k.  It keeps
the other-first district and default caps, with no WA distance override or `--tx` option.
Its tags are C1_n{k}w{wh}f{fi} and C2_n{k}w{wh}f{fi}; group none is not allowed.
`--caps ST=N,...` replaces the split caps (taking precedence over `--tx`), and
`--band-break ST,...` replaces the band-break states, under either rule.

Every cell reads `$TD_ROOT/instance_descaled_v4_conus.json.gz` and `$TD_ROOT/data/geo`,
`TD_ROOT` defaulting to the repo root.
"""
import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
G1 = "TX NY FL NJ IL AZ NC PA MI OH VA GA CO MD".split()
G2 = G1 + "WA UT IN LA MN CT".split()


def defaults(td_root: str) -> dict:
    """Full rules, as `grid_20260911_v4/full/X_n16w11f20_d100_d900n6_full` ran."""
    return {
        "instance": os.path.join(td_root, "instance_descaled_v4_conus.json.gz"),
        "geo_cache": os.path.join(td_root, "data", "geo"),
        "route": "sequential", "driver": "geo", "warm": "greedy", "anchor": "greedy",
        "centers": "seeds", "eta": 0.05, "k": 18, "engine": "highs", "strategy": "direct",
        "threads": 2, "time_limit": 180, "band_mode": "per-bundle", "k_mode": "cap",
        "bundles": "N,WH,WH_PLUS,FI,FI_PLUS,WHFI,WHFI_PLUS", "delta": 0.1, "catch_all": True,
        "catch_all_bundle": "all", "dist_max": 900, "n_max": 6, "other_first": "MT,WA,WY",
        "other_floor": 0.5, "max_splits": "CA=3,TX=2,NY=3", "band_break": "CA,TX",
        "sweep": True, "plus_pair": True}


def parse_ks(spec: str) -> list[int]:
    """`10-16` or `10,12,14`."""
    if "-" in spec:
        lo, hi = spec.split("-")
        return list(range(int(lo), int(hi) + 1))
    return [int(k) for k in spec.split(",")]


def cell(group: str, k: int, wh: int, fi: int, tx: int, rule: str = "pure") -> dict:
    flags = {"k_fixed": f"N={k},WH={wh},FI={fi}"}
    if rule == "cover":
        flags["cover_national"] = ",".join({"G1": G1, "G2": G2}[group])
        return {"tag": f"C{group[1]}_n{k}w{wh}f{fi}", "flags": flags}
    tag = {"none": "U", "G1": "F1", "G2": "F2"}[group] + f"_n{k}w{wh}f{fi}"
    if tx != 2:
        flags["max_splits"] = f"CA=3,TX={tx},NY=3"
    if group != "none":
        if group == "G1":
            listed = G1
            forced = [s for s in G1 if s != "CO"]
        else:
            listed = G2
            forced = [s for s in G2 if not (s == "CO" and k < 15) and not (s == "LA" and k < 14)]
            flags.update(other_first=None, dist_max_state="WA=1200")
        flags["force_national"] = ",".join(forced)
        tag += "".join(f"_no{s}" for s in listed if s not in forced)
    return {"tag": tag + f"_tx{tx}", "flags": flags}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", required=True, help="national counts, 10-16 or 10,12,14")
    ap.add_argument("--wh", type=int, required=True)
    ap.add_argument("--fi", type=int, required=True)
    ap.add_argument("--group", choices=["none", "G1", "G2"], required=True)
    ap.add_argument("--rule", choices=["pure", "cover"], default="pure")
    ap.add_argument("--caps", help="split caps ST=N,..., replacing the defaults and --tx")
    ap.add_argument("--band-break", help="band-break states ST,..., replacing the defaults")
    ap.add_argument("--tx", type=int, default=None,
                    help="TX's N split cap (default 2 for none, 1 for G1 and G2)")
    ap.add_argument("--time-limit", type=int, default=None, help="seconds per pass (default 180)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.rule == "cover" and args.group == "none":
        ap.error("--rule cover requires --group G1 or G2")
    if args.rule == "cover" and args.tx is not None:
        ap.error("--rule cover uses --caps, not --tx")
    tx = args.tx if args.tx is not None else (2 if args.group == "none" else 1)
    spec = {"defaults": defaults(os.environ.get("TD_ROOT", ROOT)),
            "cells": [cell(args.group, k, args.wh, args.fi, tx, args.rule)
                      for k in parse_ks(args.n)]}
    if args.caps is not None:
        spec["defaults"]["max_splits"] = args.caps
        for rec in spec["cells"]:
            rec["flags"].pop("max_splits", None)
    if args.band_break is not None:
        spec["defaults"]["band_break"] = args.band_break
    if args.time_limit:
        spec["defaults"]["time_limit"] = args.time_limit
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=1)
    print("wrote", args.out, len(spec["cells"]), "cells:",
          " ".join(c["tag"] for c in spec["cells"]))


if __name__ == "__main__":
    main()
