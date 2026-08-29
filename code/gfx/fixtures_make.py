"""
gfx/fixtures_make.py -- builds the small, committed fixtures under
`battery/code/tests/fixtures/gfx/` that `battery/code/tests/test_gfx.py` renders every
producer from. Deterministic (fixed seeds); total output is well under the 500 KB budget
(PLAN.md U7 brief: "keep fixtures small, < 500 KB total").

The 30k-cell scale fixture used by `test_gfx_scale.py` is NOT written here -- it is built
on the fly inside that test (PLAN.md U7 binding detail #2) so it never touches the repo.

Run from the repo root:
    .venv/bin/python3 code/gfx/fixtures_make.py [--out-dir battery/code/tests/fixtures/gfx]

Every file here is this unit's own provisional schema for data U1b/U3/U5 will eventually
produce for real (documented in each producer's docstring); regenerate with this script
if those schemas change rather than hand-editing the JSON.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os

import numpy as np

from . import schemas

INSTANCES = [
    ("T0_s7_pairA0B0", "T0"),
    ("T0_s8_pairA1B0", "T0"),
    ("T1_C1_seed1", "T1"),
    ("C1-seed2_A0_B0", "T1"),   # named failure
    ("C9-seed2_A2_B2", "T2"),   # named failure
]
METHODS = ["current", "current_inout", "brute", "scip", "cbc", "eps_pwl"]
MECHANISM_OF = {  # instance -> failure-mechanism tag (a)-(d), PLAN.md CLAUDE.md trap 11
    "T0_s7_pairA0B0": "none", "T0_s8_pairA1B0": "none",
    "T1_C1_seed1": "none", "C1-seed2_A0_B0": "a", "C9-seed2_A2_B2": "c",
}


def _rng_for(name, method):
    # a stable hash: builtin hash() is salted per-process for strings (PYTHONHASHSEED),
    # which would make these "fixed seed" fixtures non-reproducible across runs
    digest = hashlib.sha256(f"{name}|{method}".encode()).digest()
    seed = int.from_bytes(digest[:4], "big")
    return np.random.default_rng(seed)


def make_rows(instance_defs) -> list:
    rows = []
    for name, tier in instance_defs:
        n = 40 if tier == "T0" else (60 if tier == "T1" else 150)
        for method in METHODS:
            rng = _rng_for(name, method)
            certifies = rng.random() < (0.7 if MECHANISM_OF.get(name, "none") == "none" else 0.25)
            t_total = float(rng.uniform(0.05, 55.0))
            n_steps = int(rng.integers(3, 8))
            ts = np.sort(rng.uniform(0, t_total, n_steps))
            lb0 = float(rng.uniform(1.0, 4.0))
            ub0 = lb0 + float(rng.uniform(0.5, 3.0))
            trace = []
            for i, t in enumerate(ts):
                lb = lb0 + i * (ub0 - lb0) / (2 * n_steps)
                ub = ub0 - i * (ub0 - lb0) / (2 * n_steps)
                if certifies and i == n_steps - 1:
                    lb = ub = (lb0 + ub0) / 2
                trace.append([round(float(t), 4), round(float(lb), 6), round(float(ub), 6)])
            g_a = float(rng.uniform(5, 40))
            g_b = float(rng.uniform(5, 40))
            product = g_a * g_b
            product_free = product * float(rng.uniform(1.0, 1.15))
            perimeter = int(rng.integers(2, 30))
            excess = 0 if certifies else int(rng.integers(0, 3))
            status = "optimal" if certifies else rng.choice(
                ["time_limit", "iteration_limit", "gap_limit"])
            iter_log = None
            if method in ("current", "current_inout"):
                rounds = int(rng.integers(4, 10))
                iter_log = [
                    dict(it=i, n_cuts=int(rng.integers(0, 5)) + i,
                        n_tangents=int(rng.integers(0, 3)) + i // 2,
                        pieces_a=max(1, int(rng.integers(1, 4)) - i // 3),
                        pieces_b=max(1, int(rng.integers(1, 4)) - i // 4))
                    for i in range(rounds)
                ]
            rows.append(dict(
                run_id="fixture_run", instance=name, tier=tier, method=method,
                rho=float(rng.choice([0.0, 2e-3])), kappa=0.0, seed=int(rng.integers(0, 9999)),
                cap=60.0, scale=1.0,
                status=str(status), status_eff=str(status),
                ub_scope="global" if method != "current" else "rooted",
                UB=round(trace[-1][2], 6) if trace[-1][2] is not None else None,
                LB=round(trace[-1][1], 6) if trace[-1][1] is not None else None,
                eps=0.0, iters=len(trace), n_cuts=int(rng.integers(0, 20)),
                n_tangents=int(rng.integers(0, 12)), nodes=n,
                t_first_feasible=trace[0][0], t_total=t_total,
                g_a=g_a, g_b=g_b, product=product, perimeter=perimeter,
                pair_components=1, pieces_a=1 + excess, pieces_b=1, excess_pieces=excess,
                k=int(n // 2), cost_of_contiguity=max(0.0, 1.0 - product / product_free),
                gap_nats=round(trace[-1][2] - trace[-1][1], 6) if trace[-1][1] is not None else None,
                gap_rel=None, gap_star_nats=None,
                valid_certificate=bool(certifies and excess == 0),
                valid=True, violations=[], message="", extra={"iter_log": iter_log} if iter_log else {},
                trace=trace,
            ))
    return rows


def make_instances_csv(instance_defs) -> list:
    rows = []
    for name, tier in instance_defs:
        rng = _rng_for(name, "covariates")
        n = 40 if tier == "T0" else (60 if tier == "T1" else 150)
        rows.append(dict(
            instance=name, tier=tier, n=n,
            n_edges=int(n * 2.2),
            pair_components=1, articulation_points=int(rng.integers(0, 6)),
            block_tree_is_path=bool(rng.random() < 0.7),
            gini_u=round(float(rng.uniform(0.15, 0.5)), 4),
            top5_share_u=round(float(rng.uniform(0.1, 0.4)), 4),
            active_frac=round(float(rng.uniform(0.6, 1.0)), 4),
            n_states=int(rng.integers(0, 3)),
            mechanism=MECHANISM_OF.get(name, "none"),
            UB_star_global=round(float(rng.uniform(6.0, 9.0)), 4),
            UB_free_frac=round(float(rng.uniform(6.5, 9.5)), 4),
            UB_free_nash=round(float(rng.uniform(6.0, 9.2)), 4),
            product_free=round(float(rng.uniform(200, 900)), 2),
        ))
    return rows


def make_summary_csv(instance_defs) -> list:
    rows = []
    tiers = sorted({t for _, t in instance_defs})
    for method in METHODS:
        for tier in tiers:
            rng = _rng_for(f"summary_{tier}", method)
            rows.append(dict(
                method=method, rho=0.0, tier=tier,
                certified_frac=round(float(rng.uniform(0.2, 0.95)), 3),
                rooted_optimal_frac=round(float(rng.uniform(0.0, 0.3)), 3),
                feasible_frac=round(float(rng.uniform(0.7, 1.0)), 3),
                median_t_to_cert=round(float(rng.uniform(1.0, 40.0)), 2),
                median_gap_nats_at_cap=round(float(rng.uniform(0.0, 0.5)), 4),
                worst_gap=round(float(rng.uniform(0.1, 2.0)), 4),
                mean_cost_of_contiguity=round(float(rng.uniform(0.0, 0.1)), 4),
                ef1_frac=round(float(rng.uniform(0.7, 1.0)), 3),
                named_failures_certified="2/6",
                errors=0,
                gap_at_5=round(float(rng.uniform(0, 3)), 3),
                gap_at_20=round(float(rng.uniform(0, 2)), 3),
                gap_at_60=round(float(rng.uniform(0, 1)), 3),
                gap_at_300=round(float(rng.uniform(0, 0.5)), 3),
                gap_at_1200=round(float(rng.uniform(0, 0.2)), 3),
            ))
    return rows


def make_twin_stats(seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    ps = [0.05, 0.25, 0.5, 0.75, 0.95]

    def marginal(mu, sigma):
        qs = {str(p): float(math.exp(mu + sigma * math.sqrt(2) * math.erf(2 * p - 1)))
              for p in ps}
        dpln_q = {k: v * float(rng.uniform(0.95, 1.05)) for k, v in qs.items()}
        return {
            "fits": {"lognormal": {"mu": mu, "sigma": sigma, "quantiles": qs},
                    "dpln": {"alpha": 1.5, "beta": 1.2, "quantiles": dpln_q}},
            "prefer_dpln": bool(rng.random() < 0.5),
            "coarse_cdf": {"p": ps, "bin_mean": [qs[str(p)] for p in ps]},
        }

    deciles = list(range(1, 11))
    return {
        "marginals": {"M": marginal(2.0, 0.8), "A": marginal(1.2, 0.9), "B": marginal(1.1, 0.9)},
        "share_curves": {
            "A": {"decile": deciles, "mean_log_share": (rng.normal(-1.0, 0.3, 10)).tolist(),
                 "sd_log_share": (0.1 + 0.05 * rng.random(10)).tolist()},
            "B": {"decile": deciles, "mean_log_share": (rng.normal(-1.1, 0.3, 10)).tolist(),
                 "sd_log_share": (0.1 + 0.05 * rng.random(10)).tolist()},
        },
        "spatial": {
            "moran_I": {"M": 0.42, "A": 0.31, "B": 0.29, "activity": 0.18},
            "rank_corr_by_hop": {str(h): round(0.6 / h, 3) for h in range(1, 6)},
        },
        "audit": {
            "pearson_log": {"M": 0.31, "A": 0.28, "B": 0.27},
            "neighborhood_corr_3hop": {"M": 0.71, "A": 0.68, "B": 0.66},
            "activity_flag_agreement": {"A": 0.93, "B": 0.91},
        },
        "twin_check": {
            "pass": True,
            "census_pair_size_bins": ["1-10", "11-50", "51-200", "201-800"],
            "census_pair_size_hist_real": [120, 340, 210, 40],
            "census_pair_size_hist_twin": [118, 335, 205, 44],
        },
        "graph": {"n": 32800, "m": 96400, "components": 1, "articulation_points": 412,
                 "state_cross_share": 0.041},
    }


def make_twin_instance(seed: int = 0, n: int = 60) -> dict:
    d = schemas.make_fixture_instance(seed=seed, n=n, name="twin_stand_in", tier="T3",
                                      with_rows=False)
    rng = np.random.default_rng(seed + 1)
    n_rep_a, n_rep_b = 4, 4
    rep_a = [f"A{int(x)}" for x in rng.integers(0, n_rep_a, n)]
    rep_b = [f"B{int(x)}" for x in rng.integers(0, n_rep_b, n)]
    return {
        "meta": {"seed": seed, "rank_sigma": 0.10, "n_rep_a": n_rep_a, "n_rep_b": n_rep_b,
                "theta": 0.40, "graph_hash": f"stand_in_{seed:04d}", "tiger_vintage": "2020"},
        "nodes": {"z": d["nodes"], "state": [None] * n, "A": d["A"], "B": d["B"], "M": d["M"],
                 "rep_a": rep_a, "rep_b": rep_b, "pos": d["pos"]},
        "edges": {"u": [d["nodes"][i] for i, j in d["edges"]],
                 "v": [d["nodes"][j] for i, j in d["edges"]]},
        "audit": {"note": "synthetic stand-in, not a real twin export"},
    }


def make_calib(seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    ps = [0.1, 0.3, 0.5, 0.7, 0.9]

    def block(base):
        return {"quantiles": {str(p): base * (0.5 + p) * float(rng.uniform(0.9, 1.1)) for p in ps}}

    scenarios = {}
    for name, base_m, base_a, base_b, act, corr in (
        ("S1_aligned", 5.0, 3.0, 3.0, 0.85, 0.10),
        ("S8_twin", 6.0, 2.6, 2.7, 0.78, 0.31),
        ("twin", 6.2, 2.5, 2.8, 0.76, 0.33),
    ):
        scenarios[name] = {
            "M": block(base_m), "A": block(base_a), "B": block(base_b),
            "active_frac": act, "corr_AB": corr,
            "headroom_slack": block(1.2),
        }
    return {"scenarios": scenarios}


def build_all(out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)

    inst = schemas.make_fixture_instance(seed=7, n=42, name="T0_s7_pairA0B0", tier="T0")
    with open(os.path.join(out_dir, "instance_t0.json"), "w") as f:
        json.dump(inst, f)

    rows = make_rows(INSTANCES)
    assert len(rows) == 30, len(rows)
    with open(os.path.join(out_dir, "rows.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    import csv
    inst_rows = make_instances_csv(INSTANCES)
    with open(os.path.join(out_dir, "instances.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(inst_rows[0]))
        w.writeheader(); w.writerows(inst_rows)

    summ_rows = make_summary_csv(INSTANCES)
    with open(os.path.join(out_dir, "summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(summ_rows[0]))
        w.writeheader(); w.writerows(summ_rows)

    with open(os.path.join(out_dir, "twin_stats.json"), "w") as f:
        json.dump(make_twin_stats(), f)

    twin_inst = make_twin_instance()
    with gzip.open(os.path.join(out_dir, "twin_instance.json.gz"), "wt") as f:
        json.dump(twin_inst, f)

    with open(os.path.join(out_dir, "calib.json"), "w") as f:
        json.dump(make_calib(), f)

    total = sum(os.path.getsize(os.path.join(out_dir, fn)) for fn in os.listdir(out_dir))
    print(f"wrote fixtures to {out_dir} ({total/1024:.1f} KB total)")


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_out = os.path.join(here, "..", "..", "battery", "code", "tests", "fixtures", "gfx")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out-dir", default=os.path.normpath(default_out))
    args = p.parse_args(argv)
    build_all(args.out_dir)


if __name__ == "__main__":
    main()
