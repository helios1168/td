"""oracle_grid_cell.py -- independent oracle for BORDERS_PLAN Track 1, mappings 5 and 6.

Recomputes, from the instance and the written draw.csv files alone (plain dicts, no
`borders_report` code path), for every cell of
`battery/results/borders_k18_v2_20260907`:

  * the share of instance mass sitting outside its state's owner set, measured BOTH against the
    committed map's owner sets and against the cell's own -- to say which one the grid reports;
  * the split-state list and its exclusion rule (>=2 owner districts), checked to be computed
    rather than a hard-coded CA/TX/NY/FL;
  * for d0.02_lam100: each district's mass over the GEOMETRIC zips against tau(1 +- 0.02),
    with the overrun expressed in units of the largest single zip's mass.

Run:
  /Users/ntlee/projects/td/.venv/bin/python3 \
      /Users/ntlee/projects/td/.claude/worktrees/vbl/docs/verify/oracle_grid_cell.py
"""
from __future__ import annotations

import csv
import sys

ROOT = "/Users/ntlee/projects/td/.claude/worktrees/vbl"
sys.path.insert(0, ROOT)
sys.path.insert(0, ROOT + "/tools")

import numpy as np  # noqa: E402

from td import instance as descaled  # noqa: E402
import run_draw  # noqa: E402

RES = "/Users/ntlee/projects/td/battery/results/borders_k18_v2_20260907"
INST = "/Users/ntlee/projects/td/instance_descaled_v2.json.gz"
COMMITTED = "/Users/ntlee/projects/td/battery/results/draw_k18_v2_20260904/k18/draw.csv"
GEO = "/Users/ntlee/projects/td/data/geo"

STATES = sorted({"AL", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "ID", "IL", "IN", "IA",
                 "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV",
                 "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD",
                 "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"})
K = 18


def read_draw(path):
    with open(path, encoding="utf-8") as fh:
        return {r["zip"]: int(r["district"][1:]) - 1 for r in csv.DictReader(fh)}


def owner_sets_py(lab_of, state_of, M_of, zips):
    """Plain-Python plurality home + homeless fallback, over the given zips only."""
    W = {}
    for z in zips:
        s = state_of.get(z)
        if s is None:
            continue
        W[(s, lab_of[z])] = W.get((s, lab_of[z]), 0.0) + M_of[z]
    home = {}
    for j in range(K):
        col = {s: W.get((s, j), 0.0) for s in STATES}
        if sum(col.values()) > 0:
            home[j] = min(STATES, key=lambda s: (-col[s], STATES.index(s)))
        else:
            home[j] = None
    owners = {s: {j for j in range(K) if home[j] == s} for s in STATES}
    for s in STATES:
        if not owners[s]:
            col = {j: W.get((s, j), 0.0) for j in range(K)}
            if sum(col.values()) > 0:
                owners[s] = {min(range(K), key=lambda j: (-col[j], j))}
    return home, owners


def measure(full, home, owners, state_of, M_of, total):
    """(outside share, split-state list under the >=2-owners exclusion)."""
    outside = 0.0
    per_state = {}
    for z, j in full.items():
        s = state_of.get(z)
        if s is None:
            continue
        if j not in owners[s]:
            outside += M_of[z]
        d = per_state.setdefault(s, {})
        d[j] = d.get(j, 0.0) + M_of[z]
    split = []
    for s, d in per_state.items():
        tot = sum(d.values())
        if tot <= 0:
            continue
        if sum(1 for m in d.values() if m / tot >= 0.01) >= 2 and len(owners[s]) < 2:
            split.append(s)
    return outside / total, sorted(split)


def main():
    d = descaled.load_descaled(INST)
    zips_all = sorted(d.G)
    M_of = {z: float(d.G.nodes[z]["M"]) for z in zips_all}
    state_of = {z: (d.G.nodes[z].get("state") or "") for z in zips_all}
    state_of = {z: (s if s in STATES else None) for z, s in state_of.items()}
    total = sum(M_of.values())

    xy_dict, missing = run_draw.coordinates(zips_all, GEO)
    geo_zips = [z for z in zips_all if z in xy_dict]

    committed = read_draw(COMMITTED)
    home_c, owners_c = owner_sets_py(committed, state_of, M_of, geo_zips)
    multi = sorted(s for s in STATES if len(owners_c[s]) >= 2)
    print(f"instance: {len(zips_all)} zips, {len(geo_zips)} with coordinates, "
          f"{len(missing)} without; total M = {total:.6g}")
    print(f"committed owner sets: states with >=2 owner districts = {multi}")
    print(f"  (plan names CA,TX,NY,FL; NJ has {len(owners_c['NJ'])} -> not excluded)")

    with open(f"{RES}/grid.csv", encoding="utf-8") as fh:
        grid = {r["name"]: r for r in csv.DictReader(fh)}

    print("\ncell            grid_share   mine(committed)  mine(own owner sets)   split-list match")
    ok = True
    for name, row in grid.items():
        full = read_draw(f"{RES}/{name}/draw.csv")
        share_c, split_c = measure(full, home_c, owners_c, state_of, M_of, total)
        h_o, o_o = owner_sets_py({z: full[z] for z in geo_zips}, state_of, M_of, geo_zips)
        share_o, _ = measure(full, h_o, o_o, state_of, M_of, total)
        g = float(row["outside_owner_share"])
        gs = sorted(x for x in row["states_split"].split(",") if x)
        d_c, d_o = abs(g - share_c), abs(g - share_o)
        print(f"{name:15s} {g:.6f}    {share_c:.6f} ({d_c:.1e})  {share_o:.6f} ({d_o:.1e})   "
              f"{'OK' if gs == split_c else 'DIFF ' + str((gs, split_c))}")
        ok &= d_c < 1e-9 and gs == split_c
        if any(s in gs for s in multi):
            print(f"    !! excluded state appears in states_split: {gs}")
            ok = False

    # ---- mapping 6: the band on the d0.02_lam100 cell, over the geometric zips
    name, delta = "d0.02_lam100", 0.02
    full = read_draw(f"{RES}/{name}/draw.csv")
    Mg = np.array([M_of[z] for z in geo_zips])
    lab = np.array([full[z] for z in geo_zips])
    tau = Mg.sum() / K
    mass = np.bincount(lab, weights=Mg, minlength=K)
    lo, hi = (1 - delta) * tau, (1 + delta) * tau
    over = np.maximum(mass - hi, 0.0) + np.maximum(lo - mass, 0.0)
    zmax = Mg.max()
    print(f"\n[band] {name}: tau(geometric) = {tau:.6g}, band [{lo:.6g}, {hi:.6g}], "
          f"largest zip M = {zmax:.6g} ({zmax / tau:.4%} of tau)")
    print(f"  masses/tau: {np.array2string(mass / tau, precision=4, max_line_width=100)}")
    print(f"  worst overrun beyond the band = {over.max():.6g} "
          f"= {over.max() / zmax:.4f} largest-zip masses, "
          f"{over.max() / tau:.4%} of tau")
    print(f"  districts outside the band: {int((over > 0).sum())}; "
          f"n_fractional recorded = {grid[name]['n_fractional']}")
    band_ok = over.max() <= zmax + 1e-6
    ok &= band_ok
    print(f"  within band + one zip: {band_ok}")

    # the grid's own spread, on the COMPLETED instance, for reference
    Ma = np.array([M_of[z] for z in zips_all])
    laba = np.array([full[z] for z in zips_all])
    ma = np.bincount(laba, weights=Ma, minlength=K)
    print(f"  completed-instance spread_rel = {(ma.max() - ma.min()) / ma.mean():.6g} "
          f"vs grid {grid[name]['spread_rel']}")

    print("\nALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
