"""Item 5: the outputs.  plan.json keys, per-state coverage, the projections, state_shares.csv
row by row, staffing's rep order, and the failure record.

`target_mass` is recomputed from the aggregated cells, not from the CSV, and compared per row
and per district group, so a permutation across slots cannot pass.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                                    # noqa: E402
import toy                                                            # noqa: E402
import full_plan as cli                                               # noqa: E402
import state_splits as ss_cli                                         # noqa: E402
from td import channels, instance as descaled                         # noqa: E402
from td.solvers import level0, state_splits as ss                     # noqa: E402

STATES = ["AA", "BB", "CC", "DD"]
ADJ = {"AA": ("BB",), "BB": ("AA", "CC"), "CC": ("BB", "DD"), "DD": ("CC",)}
SPEC = {"AA": dict(national=0.5, wh=0.6, fi=0.4),
        "BB": dict(national=0.7, wh=0.5, fi=0.5),
        "CC": dict(national=0.4, wh=0.4, fi=0.6),
        "DD": dict(national=0.4, wh=0.5, fi=0.5)}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join(tmp, "inst.json.gz")
        zips_by_state = toy.write_v2_toy(inst, SPEC)
        out = os.path.join(tmp, "out")
        orig, td_geo = toy.patch_rook(ADJ)
        try:
            rc = cli.main([inst, "--route", "sequential", "--driver", "geo", "--engine",
                           "scipy", "--strategy", "direct", "--k", "2", "--time-limit", "60",
                           "--out", out])
        finally:
            toy.unpatch(orig, td_geo)
        print("rc:", rc)

        with open(os.path.join(out, "plan.json"), encoding="utf-8") as fh:
            plan = json.load(fh)
        print("plan keys:", sorted(plan))
        print("slot record keys:", sorted(plan["slots"][0]))

        d = channels.fine_split(descaled.load_descaled(inst))
        cells = channels.aggregate(d, STATES)
        M = np.asarray(cells.M, float)
        cidx = {c: i for i, c in enumerate(cells.channels)}
        bundle_of = {r["id"]: r["bundle"] for r in plan["slots"]}

        # (b) per-channel coverage <= 1, and the residual is 1 - coverage
        worst = 0.0
        for s, st in enumerate(STATES):
            cov = {c: 0.0 for c in channels.CHANNELS}
            for sid, share in plan["per_state"][st].items():
                if sid == "residual_by_channel":
                    continue
                for c in channels.BUNDLES[bundle_of[sid]]:
                    cov[c] += float(share)
            for c in channels.CHANNELS:
                worst = max(worst, cov[c] - 1.0)
                res = plan["per_state"][st]["residual_by_channel"][c]
                if abs((1.0 - cov[c]) - res) > 1e-6:
                    print(f"  RESIDUAL MISMATCH {st} {c}: 1-cov={1-cov[c]:.6f} vs {res}")
        print("max (coverage - 1) over cells:", worst)

        # (c)/(d) projections
        for bundle in sorted(os.listdir(os.path.join(out, "projections"))):
            cell = os.path.join(out, "projections", bundle)
            p = descaled.load_descaled(os.path.join(cell, "instance_descaled.json.gz"))
            recs = [r for r in plan["slots"]
                    if r["bundle"] == bundle and r["used"] and r["y"]]
            want_states = sorted({st for r in recs for st in r["y"]})
            want_zips = sorted(z for st in want_states for z in zips_by_state[st])
            got_zips = sorted(p.G)
            print(f"  projection {bundle}: loads={p.G.number_of_nodes()} zips, "
                  f"zips match states with positive share: {got_zips == want_zips}, "
                  f"channels field={p.channels}, meta bundle={p.meta.get('bundle')}")

            cols = [cidx[c] for c in channels.BUNDLES[bundle]]
            M_B = M[:, cols].sum(axis=1)
            # the projection's own mass, an independent path to the same number
            proj_mass = {st: sum(float(p.G.nodes[z]["M"]) for z in zips_by_state[st])
                         for st in want_states}
            for st in want_states:
                s = STATES.index(st)
                d_rel = abs(proj_mass[st] - M_B[s]) / max(1e-12, M_B[s])
                if d_rel > 1e-5:
                    print(f"    MASS MISMATCH {st}: projection {proj_mass[st]} vs cells {M_B[s]}")
            with open(os.path.join(cell, "state_shares.csv"), encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            by_district = {}
            bad_rows = 0
            for r in rows:
                s = STATES.index(r["state"])
                want = M_B[s] * float(r["share"])
                if abs(float(r["target_mass"]) - want) > 1e-9 * max(1.0, want):
                    bad_rows += 1
                    print("    ROW MISMATCH", r, "want", want)
                by_district.setdefault(r["district"], 0.0)
                by_district[r["district"]] += float(r["target_mass"])
            print(f"    rows={len(rows)} bad_rows={bad_rows}")
            # per district: the CSV group must equal that slot's own mass, in the slot order
            import run_draw
            for j, rec in enumerate(recs):
                did = run_draw.district_id(j)
                got = by_district.get(did, 0.0)
                ok = abs(got - rec["mass"]) <= 1e-9 * max(1.0, rec["mass"])
                print(f"    district {did} <- {rec['id']}: csv {got:.9f} vs slot mass "
                      f"{rec['mass']:.9f} equal={ok}")

        # (e) staffing rep order
        with open(os.path.join(out, "staffing.json"), encoding="utf-8") as fh:
            staffing = json.load(fh)
        print("staffing reps == sorted cell reps:", staffing["reps"] == list(cells.reps))
        print("staffing districts:", staffing["districts"],
              "unstaffed:", staffing["unstaffed_districts"])
        print("assignment reps unique:",
              len(set(staffing["assignment"].values())) == len(staffing["assignment"]))

    # (f) the failure record and timings.json on failure
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join(tmp, "inst.json.gz")
        toy.write_v2_toy(inst, SPEC)
        out = os.path.join(tmp, "out_fail")
        real = level0.solve_passes

        def boom(*a, **kw):
            raise ss.SolveFailure(2, "The problem is infeasible. (HiGHS Status 8)")

        level0.solve_passes = boom
        orig, td_geo = toy.patch_rook(ADJ)
        try:
            cli.main([inst, "--route", "joint", "--engine", "scipy", "--strategy", "direct",
                      "--k", "2", "--time-limit", "5", "--out", out])
            print("failure path: no raise (unexpected)")
        except ss.SolveFailure:
            print("failure path: re-raised, as designed")
        finally:
            level0.solve_passes = real
            toy.unpatch(orig, td_geo)
        ref = os.path.join(tmp, "ref")
        os.makedirs(ref)
        ss_cli._write_failure(ref, "d0.05", 0.05,
                              ss.SolveFailure(2, "The problem is infeasible. (HiGHS Status 8)"),
                              1.0)
        with open(os.path.join(ref, "failure.json"), encoding="utf-8") as fh:
            ref_rec = json.load(fh)
        with open(os.path.join(out, "failure.json"), encoding="utf-8") as fh:
            rec = json.load(fh)
        print("failure keys equal:", set(rec) == set(ref_rec), sorted(rec))
        print("failure record:", rec)
        print("timings.json on failure:", os.path.exists(os.path.join(out, "timings.json")))
        print("params.json on failure:", os.path.exists(os.path.join(out, "params.json")))


if __name__ == "__main__":
    main()
