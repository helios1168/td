"""run_atoms.py -- the state-atom stage-1 draw: instance in, a contiguous map out.

    PYTHONHASHSEED=0 .venv/bin/python3 tools/run_atoms.py instance_descaled_v2.json.gz \\
        --k 18 --reference --out battery/results/atoms_k18_v2_20260906

The state-atom counterpart of `run_draw.py`.  Where that route draws power cells on zip
geometry and abandons contiguity, this one pre-aggregates zips into state atoms and draws
contiguous districts on the TIGER state rook graph::

    load instance          td.instance.load_descaled
    coordinates            run_draw.coordinates          (cached under data/geo/, no network)
    atoms                  td.atoms.build                whole states; CA/TX/NY+NJ/FL cut
    stage 1                td.solvers.atom_draw.draw     one contiguous k-district draw
    the bound              td.solvers.cert_draw.cert_balance_ceiling
    reference (--reference) td.solvers.atom_draw.free_search

It writes the same shapes `run_draw.py` does -- `k<kk>/draw.csv` and `k<kk>/metrics.json` --
so `tools/us_maps.py --districts` and `tools/measure/premium.py` read its output unchanged.
`us_maps.py --regions` does **not** apply: atom districts are not a power diagram.

Why a separate script rather than a `--atoms` flag on `run_draw.py`.  `run_draw` draws on the
zips the gazetteer has points for and places the rest afterwards by state plurality
(`channel.place_by_state`).  The atom route has no such gap: a zip with no coordinate still has
a state, so it still has an atom and follows it.  Routing those zips through `place_by_state`
would put some of them in a different district and change the draw's value, so the two
pipelines are kept apart rather than merged behind a flag.

`PYTHONHASHSEED=0` is **required**, not advisory.  The search tie-breaks on set iteration over
atom names, so without a fixed hash seed the answer moves by about 0.015 nats, and under a
process pool every worker would draw under a different seed.  See `td.solvers.atom_draw`.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import sys

import networkx as nx
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import run_draw                                                            # noqa: E402
from td import atoms as atoms_mod                                          # noqa: E402
from td import instance as descaled                                        # noqa: E402
from td.solvers import atom_draw, cert_draw                                # noqa: E402


def check_hash_seed(env=None) -> None:
    """Refuse to run without `PYTHONHASHSEED=0`.

    Python randomises string hashing per process, and this search tie-breaks on set iteration
    over atom names, so the result is not reproducible without it.  The variable has to be set
    before the interpreter starts, so this can only check, not fix.
    """
    env = os.environ if env is None else env
    if env.get("PYTHONHASHSEED") != "0":
        raise SystemExit(
            "run_atoms.py requires PYTHONHASHSEED=0 (see td/solvers/atom_draw.py).\n"
            "Re-run as:  PYTHONHASHSEED=0 .venv/bin/python3 tools/run_atoms.py ...")


def unit_arrays(res: dict, mass: dict):
    """`(M, labels)` per atom, with the stateless bucket appended as one more unit.

    The certificate has to be computed over the same mass the draw was scored on, so the
    stateless opportunity enters as a unit rather than being dropped.
    """
    M = [mass[a] for a in res["atoms"]]
    labels = list(res["labels"])
    if res["stateless_mass"]:
        M.append(float(res["stateless_mass"]))
        labels.append(int(res["stateless_district"]))
    return np.array(M, float), np.array(labels, int)


def write_run(out_dir: str, k: int, to_name: dict, metrics: dict) -> None:
    """`k<kk>/draw.csv` (zip,district) and `k<kk>/metrics.json` -- run_draw's layout."""
    kdir = os.path.join(out_dir, f"k{k:02d}")
    os.makedirs(kdir, exist_ok=True)
    with open(os.path.join(kdir, "draw.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["zip", "district"])
        for z in sorted(to_name):
            w.writerow([z, to_name[z]])
    with open(os.path.join(kdir, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2, default=float)
        fh.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("instance", nargs="?", default="instance_descaled_v2.json.gz")
    ap.add_argument("--k", type=int, default=18, help="district count (default 18)")
    ap.add_argument("--cut", action="append", default=None,
                    help=f"ST[,ST]:N -- a state group cut into N pieces, repeatable "
                         f"(default {' '.join(atoms_mod.DEFAULT_CUTS)})")
    ap.add_argument("--seed", type=int, default=0, help="draw seed (default 0)")
    ap.add_argument("--cut-seed", type=int, default=atoms_mod.CUT_SEED,
                    help="seed for the within-group cut (default 2)")
    ap.add_argument("--restarts", type=int, default=250,
                    help="seeded grow+polish restarts; the draw is their argmax (default 250)")
    ap.add_argument("--border-tol", type=float, default=atoms_mod.BORDER_TOL,
                    help="metres within which a cut piece touches a neighbouring state")
    ap.add_argument("--reference", action="store_true",
                    help="also run the contiguity-dropped local search (a reference, NOT a bound)")
    ap.add_argument("--out", default=None,
                    help="output directory (default battery/results/atoms_k<k>_<YYYYMMDD>/)")
    ap.add_argument("--geo-cache", default=run_draw.geo.DEFAULT_DEST)
    args = ap.parse_args(argv)

    check_hash_seed()
    cuts = atoms_mod.parse_cuts(args.cut or atoms_mod.DEFAULT_CUTS)
    out_dir = args.out or os.path.join(
        "battery", "results", f"atoms_k{args.k}_{_dt.date.today():%Y%m%d}")
    os.makedirs(out_dir, exist_ok=True)

    d = descaled.load_descaled(args.instance)
    print(f"instance: {d.summary()}")
    zips = list(d.G)                       # the instance's own order -- see td/atoms.py
    M_by_zip = {z: float(d.G.nodes[z]["M"]) for z in zips}
    states = {z: d.G.nodes[z].get("state") or "" for z in zips}
    xy, missing = run_draw.coordinates(zips, args.geo_cache)
    print(f"coordinates: {len(xy)} of {len(zips)} zips ({len(missing)} without a gazetteer "
          f"point -- they keep their state, so they keep their atom)")

    A = atoms_mod.build(zips, M_by_zip, states, xy, cuts,
                        seed=args.cut_seed, tol=args.border_tol, cache=args.geo_cache)
    total = sum(A.mass.values()) + A.stateless_mass
    target = total / args.k
    print(f"atoms: {len(A.mass)}, edges {A.graph.number_of_edges()}, "
          f"components {nx.number_connected_components(A.graph)}")
    print("pieces: " + "  ".join(f"{p} {A.mass[p] / target:.3f}x"
                                 for g in cuts for p in sorted(A.pieces[g])))
    if A.merged:
        print("merged: " + ", ".join(f"{k}->{v}" for k, v in sorted(A.merged.items())))
    if A.stateless:
        print(f"stateless: {len(A.stateless)} zips, {A.stateless_mass:.1f} "
              f"({A.stateless_mass / total:.1%}) -- added to the lightest district")

    res = atom_draw.draw(A.graph, A.mass, args.k, seed=args.seed, restarts=args.restarts,
                         stateless_mass=A.stateless_mass)
    M_arr, lab_arr = unit_arrays(res, A.mass)
    cert = cert_draw.cert_balance_ceiling(M_arr, lab_arr, args.k)

    to_d = atom_draw.to_district(A.zips_of, res["atom_district"],
                                 A.stateless, res["stateless_district"])
    to_name = {z: run_draw.district_id(v) for z, v in to_d.items()}
    if set(to_name) != set(zips):
        raise SystemExit(f"draw covers {len(to_name)} zips, instance has {len(zips)}")

    print(f"\nCONTIGUOUS  Sigma log M {res['nash']:.6f}   "
          f"ceiling {cert['ceiling_nash']:.6f}   gap {cert['gap_nats']:.6f} nats")
    print(f"mass x target: max {res['max'] / target:.3f}  min {res['min'] / target:.3f}  "
          f"spread {res['spread_rel']:.1%}")
    reference = None
    if args.reference:
        parts = [{a for a, dd in res["atom_district"].items() if dd == j} for j in range(args.k)]
        reference = atom_draw.free_search(A.mass, args.k, init=parts)
        print(f"REFERENCE (contiguity dropped, NOT a bound) {reference:.6f}   "
              f"{reference - res['nash']:+.6f} vs the draw")

    rows = run_draw.summary_rows(to_name, M_by_zip, states, target=target)
    print()
    run_draw.print_summary(rows)

    metrics = dict(
        engine="atoms", k=args.k, seed=args.seed, cut_seed=args.cut_seed,
        restarts=args.restarts, border_tol=args.border_tol,
        cuts={g: {"states": list(s), "pieces": n} for g, (s, n) in cuts.items()},
        atom_mass={a: A.mass[a] for a in sorted(A.mass)},
        merged=A.merged, n_stateless=len(A.stateless), stateless_mass=A.stateless_mass,
        stage1={key: res[key] for key in
                ("nash", "masses", "sizes", "min", "max", "mean", "total", "spread_rel",
                 "max_dev_rel", "best_restart", "rounds_used", "converged", "n_components",
                 "seats_per_component", "stateless_district")},
        certificate=cert,
        free_search_reference=reference,
        districts=rows,
        versions={m.__name__: getattr(m, "__version__", "") for m in _versions()},
    )
    write_run(out_dir, args.k, to_name, metrics)
    print(f"\nwrote {os.path.join(out_dir, f'k{args.k:02d}')}/")
    return 0


def _versions():
    """The libraries whose behaviour the atoms depend on -- the cut is an LP, so record them."""
    import scipy
    return (np, scipy, nx)


if __name__ == "__main__":
    raise SystemExit(main())
