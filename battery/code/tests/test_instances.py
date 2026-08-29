"""
test_instances.py -- the benchmark instance set and the bench driver (PLAN.md U1b).

The acceptance gate is `test_select_pairs_reproduces_every_battery_json`: the harness must
rebuild, from `params` alone, exactly the pairs the stored `battery/figures/C*.json` recorded.
Everything else is fast structure checks plus one end-to-end smoke on the `fake` methods.

Nothing here writes under `battery/figures/`; the smoke writes to a per-pid run id under
`battery/results/contiguity/` and removes it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

import networkx as nx                            # noqa: E402

import contiguity_bench as CB                    # noqa: E402
import instances as I                            # noqa: E402
from contig_methods import REGISTRY, base        # noqa: E402

# `select_pairs` sorts the dense enumeration, so the pair order no longer depends on
# PYTHONHASHSEED (it did in `case_pipeline.pair_solves`).  Frozen from the sorted order.
C2_A0_ORDER = [(0, 2, 13), (0, 3, 14), (1, 0, 15), (1, 2, 22), (1, 4, 13),
               (2, 1, 25), (2, 4, 34), (3, 1, 13), (3, 2, 9), (3, 3, 40)]
U0C_KEYS = ("book_ratio", "theta", "lam", "n_metros")


def _pairset(pairs):
    return {(p["ra"], p["rb"], p["n_zips"], p["dense"]) for p in pairs}


# ------------------------------------------------------------------- 1. the acceptance gate
def test_select_pairs_reproduces_every_battery_json():
    """Regenerate each battery case from `params` and match the stored pair list exactly.

    `C8_rho_frontier.json` is a different schema (one pair, a rho sweep) and is excluded.
    """
    checked = 0
    for case, cs in I.BATTERY_CASES.items():
        if not cs.has_json:
            continue
        G = I._graph_for(I.params_key(I.resolve_params(cs)))
        got = _pairset(I.select_pairs(G, cs.min_share))
        want = _pairset(I.load_case_json(case)["pairs"])
        assert got == want, f"{case}: extra {got - want}, missing {want - got}"
        checked += 1
    assert checked == 16, f"expected 16 battery JSONs with a params block, saw {checked}"


# ------------------------------------------------------------------------ 2. params drift
def test_resolve_params_matches_stored_and_fills_the_u0c_keys():
    for case, cs in I.BATTERY_CASES.items():
        if not cs.has_json:
            continue
        assert I.check_case_params(case) == [], I.check_case_params(case)
        resolved = I.resolve_params(cs)
        stored = I.load_case_json(case)["params"]
        for k in U0C_KEYS:
            assert k in resolved, f"{case}: {k} missing from resolve_params"
            assert k not in stored, f"{case}: stored JSON unexpectedly has {k}"
    # the four U0c keys take make_instance's own defaults
    d = I._make_instance_defaults()
    assert (d["book_ratio"], d["theta"], d["lam"], d["n_metros"]) == (5 / 3, 0.40, 0.30, None)


# --------------------------------------------------------------------- 3. deterministic order
def test_pair_order_is_hash_seed_independent():
    cs = I.BATTERY_CASES["C2_entangled_a0"]
    G = I._graph_for(I.params_key(I.resolve_params(cs)))
    got = [(p["ra"], p["rb"], p["n_zips"]) for p in I.select_pairs(G, cs.min_share)]
    assert got == C2_A0_ORDER, got
    code = ("import sys; sys.path.insert(0, %r)\n"
            "import instances as I\n"
            "cs = I.BATTERY_CASES['C2_entangled_a0']\n"
            "G = I._graph_for(I.params_key(I.resolve_params(cs)))\n"
            "print([(p['ra'], p['rb'], p['n_zips']) for p in I.select_pairs(G, cs.min_share)])\n"
            % os.path.join(ROOT, "battery", "code"))
    env = dict(os.environ, PYTHONHASHSEED="12345")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=env, cwd=ROOT, timeout=180)
    assert out.returncode == 0, out.stderr
    assert eval(out.stdout.strip()) == C2_A0_ORDER, out.stdout


# ------------------------------------------------------------------------ 4. named failures
def test_named_failures_resolve_with_the_right_sizes():
    nf = I.named_failures()
    assert [s.name for s in nf] == list(I.NAMED_FAILURE_NAMES)
    assert [s.n_expected for s in nf] == [69, 61, 205, 125, 44, 31]
    by = {s.name: s for s in nf}
    assert by["C5_states_resp__A2_B2"].respect_state is True
    assert all(s.named_failure for s in nf)


# ----------------------------------------------------------------------------- 5. tier T0
def test_T0_is_a_size_ladder_and_T0_full_is_the_sweep():
    t0, full = I.build_T0(), I.build_T0_full()
    sizes = [s.n_expected for s in t0]
    assert sizes == sorted(sizes) and len(set(sizes)) == len(sizes)
    assert all(8 <= s <= 20 for s in sizes)
    assert sizes == list(range(8, 21)) and len(t0) == 13
    assert len(full) == 90
    assert all(s.tier == "T0" for s in full)
    assert {s.name for s in t0} <= {s.name for s in full}


# ----------------------------------------------------------------------------- 6. tier T2
def test_T2_sizes():
    t2 = {s.name: s.n_expected for s in I.build_T2()}
    assert len(t2) == 12
    assert sorted(v for k, v in t2.items() if k.startswith("C7_")) == [26, 44, 125, 205]
    assert sorted(v for k, v in t2.items() if "seed1" in k) == [114, 169, 197, 320]
    assert sorted(v for k, v in t2.items() if "seed2" in k) == [77, 124, 135, 464]
    assert len(I.build_T1()) == 63 and len(I.build_T4()) == 8


# ------------------------------------------------------------------------- 7. build_pair
def test_build_pair_on_the_state_respecting_named_failure():
    sp = {s.name: s for s in I.build_T4()}["C5_states_resp__A2_B2"]
    pi = I.build_pair(sp)
    assert pi.n == 61
    comps = sorted((len(c) for c in nx.connected_components(pi.G)), reverse=True)
    assert comps == [35, 12, 11, 2, 1], comps
    assert abs(pi.edge_share_deleted - 0.22916666666666666) < 1e-12
    ua, ub = base.utilities(pi.G, pi.nodes, I.THETA, I.LAM)
    assert abs(float(ua.sum() + ub.sum()) - base.RESCALE_TARGET) < 1e-9
    assert base.check_state_filter(pi.G, True) == []
    assert pi.covariates["pair_components"] == 5
    assert I.build_pair(sp, rescale=False).scale == 1.0
    # the free bounds are a soft dependency on U2's bounds.py
    assert pi.bounds["free_status"] in ("ok", "not_requested", "bounds_module_missing")


# ------------------------------------------------------------------------ 8. hand graphs
def test_hand_graphs_block_tree_shapes():
    got = {s.name: I.build_pair(s).covariates["block_tree_is_path"] for s in I.build_hand()}
    assert got == {"hand_p8": True, "hand_trident": False, "hand_cycle10": True}, got
    assert set(got) == I.HAND_GRAPHS.keys()


# -------------------------------------------------------------------- 9. instance JSON
def test_instance_json_schema():
    run = CB.RESULTS_ROOT / f"_test_json_{os.getpid()}"
    try:
        sp = I.build_T0()[0]
        pi = I.build_pair(sp, with_bounds=True, bounds_cap=30.0)
        p = I.write_instance_json(pi, run / "instances" / f"{sp.name}.json")
        d = json.load(open(p))
        assert tuple(d) == I.INSTANCE_JSON_KEYS, tuple(d)
        assert d["schema_version"] == I.SCHEMA_VERSION
        assert d["rows"] is None                       # the card joins rows.jsonl by name
        n = len(d["nodes"])
        assert n == pi.n == sp.n_expected
        for k in ("pos", "A", "B", "M", "state", "rep_a", "rep_b"):
            assert len(d[k]) == n, k
        assert all(len(e) == 2 for e in d["edges"])
        assert d["spec"]["name"] == sp.name and d["covariates"]["n"] == n
        assert set(d["rep_a"]) == {sp.rep_a} and set(d["rep_b"]) == {sp.rep_b}
        assert "free_to_a" not in d["bounds"]
    finally:
        shutil.rmtree(run, ignore_errors=True)


# ---------------------------------------------------------------------------- 10. dry run
def test_dry_run_counts_and_writes_nothing():
    before = sorted(os.listdir(CB.RESULTS_ROOT)) if CB.RESULTS_ROOT.exists() else None
    rc = CB.main(["--tiers", "T0", "--methods", "fake_optimal,fake_time_limit",
                  "--dry-run", "--quiet", "--run-id", "_never_written"])
    assert rc == 0
    assert not (CB.RESULTS_ROOT / "_never_written").exists()
    after = sorted(os.listdir(CB.RESULTS_ROOT)) if CB.RESULTS_ROOT.exists() else None
    assert after == before
    plan = CB.resolve_plan(CB.build_parser().parse_args(
        ["--stage", "S0", "--methods", "fake_optimal"]))
    specs = CB.collect_specs(plan)
    rep = CB.dry_run_report(specs, plan, (0.0,), CB.Log(None, quiet=True))
    assert rep["specs"] == 19            # T0 (13) + the six named failures
    assert rep["jobs"] == 19
    # a preset method list is intersected with the registry, never invented
    plan2 = CB.resolve_plan(CB.build_parser().parse_args(["--stage", "S0"]))
    assert all(m in REGISTRY for m in plan2["methods"])
    assert set(plan2["missing_methods"]) <= set(PRESET_S0_METHODS)


PRESET_S0_METHODS = CB.PRESETS["S0"].methods


# ------------------------------------------------------------------------ 11. output guard
def test_output_guard_refuses_figures_and_outside_paths():
    for bad in (I.FIGURES_DIR / "x.png", I.FIGURES_DIR, ROOT, os.path.join(ROOT, "code", "x")):
        try:
            CB._assert_safe_out(bad)
        except RuntimeError:
            continue
        raise AssertionError(f"_assert_safe_out accepted {bad}")
    CB._assert_safe_out(CB.RESULTS_ROOT / "some_run" / "rows.jsonl")


# ------------------------------------------------------------------------- 12. smoke run
def test_end_to_end_smoke():
    run_id = f"_test_{os.getpid()}"
    run = CB.RESULTS_ROOT / run_id
    # fake_optimal's UB is a *lie* on general graphs (best feasible prefix); once brute is
    # registered its true optimum exceeds that UB and the phase-3 post-pass rightly files a
    # bug.  So use the honest fakes alongside brute, and check certificates on brute.
    have_brute = "brute" in REGISTRY
    methods = (["fake_heuristic", "fake_time_limit"] if have_brute      # UB None / UB loose
               else ["fake_optimal", "fake_time_limit"])
    methods += [m for m in ("brute", "current_tight") if m in REGISTRY]
    cert_method = "brute" if have_brute else "fake_optimal"
    names = [s.name for s in I.build_T0()[:3]]
    rx = "|".join(names)
    try:
        rc = CB.main(["--tiers", "T0", "--instances", rx, "--methods", ",".join(methods),
                      "--cap", "5", "--workers", "2", "--quiet", "--run-id", run_id])
        assert rc == 0
        jobs = json.load(open(run / "jobs.json"))
        rows = [json.loads(l) for l in open(run / "rows.jsonl") if l.strip()]
        assert jobs["n_instances"] == 3
        assert len(rows) == jobs["n_jobs"] == 3 * len(methods) - len(jobs["skipped"])
        assert "skipped" in jobs
        for r in rows:
            assert "valid" in r and "violations" in r
            assert r["instance"] in names and r["run_id"] == run_id
        opt = [r for r in rows if r["method"] == cert_method]
        assert len(opt) == 3
        for r in opt:
            assert r["valid"] and r["valid_certificate"], r["violations"]
            assert r["excess_pieces"] == 0
        with open(run / "summary.csv") as f:
            header = f.readline().strip().split(",")
        assert header == CB.SUMMARY_COLS, header
        with open(run / "instances.csv") as f:
            icols = f.readline().strip().split(",")
        assert "UB_star_global" in icols
        assert (run / "rows_scored.jsonl").exists() and (run / "bugs.json").exists()
        assert json.load(open(run / "bugs.json")) == []
        assert not any(p.name == "figures" for p in run.rglob("*"))
    finally:
        shutil.rmtree(run, ignore_errors=True)
