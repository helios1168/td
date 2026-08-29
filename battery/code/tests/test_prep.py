"""
test_prep.py -- contig_methods/prep.py: Option E1 safe reductions + E3 component-quotient
fixing, as wrappers around any registered method (PLAN.md W8, OPTIONS.md #6).

Acceptance (PLAN.md W8 row, TEST_PLAN.md §7 E1/E3 rows):
  E1 -- optimum unchanged on T0/T1 (bit-identical `to_a` after expansion, up to the documented
        free choice inside a split chain); pass-through correctness when no rule fires.
  E3 -- cross-method gap reported; never labelled `optimal`.
T1 has no zero-value zips (CLAUDE.md / PLAN.md B.13), so E1 acceptance on "real" instances is
built here from T0-sized pairs with selected zips zeroed out (`p_active`-style instances), plus
the six named failures to confirm E1 is a documented no-op there.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

import synth, territory as T                        # noqa: E402
from contig_methods import REGISTRY, base, prep      # noqa: E402
from contig_methods import bounds as boundsmod       # noqa: E402
from instances import named_failures, build_pair     # noqa: E402

THETA, LAM = 0.40, 0.30


# ------------------------------------------------------------------------- hand instances
def path_instance(n=8):
    G = nx.path_graph(n)
    for i in range(n):
        A = 1.0 + 0.9 * (n - 1 - i) / (n - 1)
        B = 1.0 + 0.9 * i / (n - 1)
        G.nodes[i].update(A=A, B=B, M=4.0 + 0.1 * i, pos=(i / n, 0.5))
    return G


def glue_instance():
    """P6 with zips 2,3 zero-valued -- a length-2 chain, w=1, w'=4."""
    G = path_instance(6)
    for z in (2, 3):
        G.nodes[z].update(A=0.0, B=0.0, M=0.0)
    return G


def leaf_instance():
    """P6 with the endpoint zip 0 zero-valued -- a true degree-1 leaf."""
    G = path_instance(6)
    G.nodes[0].update(A=0.0, B=0.0, M=0.0)
    return G


def pendant_cycle_instance(k):
    """A normal P4 with a k-node zero-value cycle hanging off node 0 (w = w' = 0)."""
    G = path_instance(4)
    prev = 0
    cyc = [100 + i for i in range(k)]
    for c in cyc:
        G.add_edge(prev, c)
        G.nodes[c].update(A=0.0, B=0.0, M=0.0, pos=(0.0, 0.0))
        prev = c
    G.add_edge(prev, 0)
    return G


def two_component_instance():
    """Two disjoint paths -- the pair graph itself is disconnected (C.0 #1)."""
    G = path_instance(4)
    H = nx.relabel_nodes(path_instance(3), {0: 10, 1: 11, 2: 12})
    return nx.union(G, H)


def _brute(G, nodes, rho=0.0):
    return base.run_method(REGISTRY["brute"].solve, G, nodes, theta=THETA, lam=LAM, rho=rho,
                           time_limit=15.0)


def _spec_run(name, G, nodes, rho=0.0, time_limit=15.0, **extra_opts):
    spec = REGISTRY[name]
    kw = dict(spec.kwargs); kw.update(extra_opts)
    return spec, base.run_method(spec.solve, G, nodes, theta=THETA, lam=LAM, rho=rho,
                                 time_limit=time_limit, **kw)


# ============================================================================ registry
def test_registry_variants():
    for name in ("prep", "prep_e1_brute", "prep_e1_current_tight", "prep_e1_current_tu",
                 "prep_e1_flow", "prep_e3_current_tight", "prep_e13_current_tight"):
        assert name in REGISTRY, name
        assert REGISTRY[name].base_name == "prep"
        assert REGISTRY[name].exact               # module-level flag; E3's own runtime never
                                                    # returns status="optimal" regardless


def test_missing_inner_is_a_clean_error_row():
    # (was prep_e1_flow until W4 merged and `flow` became real -- use an inner that can
    # never exist)
    G = path_instance(8); nodes = sorted(G)
    from contig_methods import REGISTRY as _R
    res = base.run_method(_R["prep"].solve, G, nodes, theta=THETA, lam=LAM, rho=0.0,
                          time_limit=5.0, inner="no_such_method", rules=("e1",))
    row = base.evaluate(G, nodes, res, theta=THETA, lam=LAM, rho=0.0)
    assert res.status == "error" and row["valid"]
    assert "no_such_method" in res.message and "not registered" in res.message


# ============================================================================ hand: Rule L
def test_rule_l_leaf_reduction_and_expansion():
    G = leaf_instance(); nodes = sorted(G)
    Hr, nodes_r, leaf_assign, chain_records, fired = prep._reduce_e1(
        G.subgraph(nodes).copy(), nodes, THETA, LAM, 0.0)
    assert fired == {"L": 1, "C": 0}
    assert len(nodes_r) == 5 and leaf_assign == {0: 1} and chain_records == []

    _, res_p = _spec_run("prep_e1_brute", G, nodes, check=True)
    res_b = _brute(G, nodes)
    assert res_p.to_a == res_b.to_a                # no ambiguity: a pure leaf has one answer
    assert abs(res_p.LB - res_b.LB) < 1e-12
    row = base.evaluate(G, nodes, res_p, theta=THETA, lam=LAM, rho=0.0)
    assert row["valid"] and row["feasible"] and row["excess_pieces"] == 0


# ============================================================================ hand: Rule C
def test_rule_c_chain_reduction_and_expansion():
    G = glue_instance(); nodes = sorted(G)
    Hr, nodes_r, leaf_assign, chain_records, fired = prep._reduce_e1(
        G.subgraph(nodes).copy(), nodes, THETA, LAM, 0.0)
    assert fired == {"L": 0, "C": 1}
    assert len(nodes_r) == 4 and leaf_assign == {}
    assert chain_records == [dict(w=1, wprime=4, interior=[2, 3], loop=False)]

    _, res_p = _spec_run("prep_e1_brute", G, nodes, check=True)
    res_b = _brute(G, nodes)
    # objective matches exactly; to_a may legitimately differ only inside a split chain (the
    # module docstring's Rule C, w != w' case) -- here the optimum keeps 1 and 2,3,4 apart or
    # together depending on which side wins, so check both feasibility and objective, not to_a
    assert abs(res_p.LB - res_b.LB) < 1e-12
    row = base.evaluate(G, nodes, res_p, theta=THETA, lam=LAM, rho=0.0)
    assert row["valid"] and row["feasible"] and row["excess_pieces"] == 0
    assert row["product"] is not None and abs(row["product"] - (math.e ** res_b.LB)) < 1e-6


def test_pendant_cycle_both_ends_same_zip():
    for k in (2, 3):
        G = pendant_cycle_instance(k); nodes = sorted(G)
        Hr, nodes_r, leaf_assign, chain_records, fired = prep._reduce_e1(
            G.subgraph(nodes).copy(), nodes, THETA, LAM, 0.0)
        assert fired == {"L": 0, "C": 1}, (k, fired)
        assert len(nodes_r) == 4                    # the whole k-cycle collapses to nothing
        assert set(leaf_assign) == {100 + i for i in range(k)}
        assert all(w == 0 for w in leaf_assign.values())
        assert chain_records[0]["loop"] is True and chain_records[0]["w"] == 0 == \
            chain_records[0]["wprime"]

        _, res_p = _spec_run("prep_e1_brute", G, nodes, check=True)
        res_b = _brute(G, nodes)
        assert res_p.to_a == res_b.to_a             # w==w': no split ambiguity, unique answer
        assert abs(res_p.LB - res_b.LB) < 1e-12
        row = base.evaluate(G, nodes, res_p, theta=THETA, lam=LAM, rho=0.0)
        assert row["valid"] and row["feasible"]


def test_disconnected_pair_graph_no_rule_fires():
    """Two-component hand instance (C.0 #1): no zero-value zips, so E1 is a clean no-op, and
    the wrapper still round-trips `current`'s documented unsound-bound fallback correctly."""
    G = two_component_instance(); nodes = sorted(G)
    _, _, leaf_assign, chain_records, fired = prep._reduce_e1(
        G.subgraph(nodes).copy(), nodes, THETA, LAM, 0.0)
    assert fired == {"L": 0, "C": 0} and not leaf_assign and not chain_records

    _, res_p = _spec_run("prep_e1_brute", G, nodes, check=True)
    res_b = _brute(G, nodes)
    assert res_p.to_a == res_b.to_a and abs(res_p.LB - res_b.LB) < 1e-12
    assert res_p.extra["n_before"] == res_p.extra["n_after"] == 7


# ============================================================================ T0 pass-through
def _t0_like_pairs(ns=(40, 50, 60), seeds=range(1, 11), lo=8, hi=20, limit=40):
    out = []
    for n in ns:
        for seed in seeds:
            G = synth.scenario("S1_aligned", n=n, seed=seed)
            O = T.overlap_graph(G)
            for edge in O.edges():
                ra, rb = T.pair_endpoints(edge)
                zips = T.zips_for_pair(G, ra, rb)
                if lo <= len(zips) <= hi:
                    H0, _ = base.filter_pair(G, sorted(zips), respect_state=False)
                    H, _ = base.rescale_pair(H0, sorted(H0), THETA, LAM)
                    out.append((H, sorted(H)))
                    if len(out) >= limit:
                        return out
    return out


def test_e1_pass_through_when_no_rule_fires():
    """No T0/T1 zip is zero-valued (PLAN.md B.13), so `prep_e1_current_tight` must reproduce
    `current_tight` exactly -- the reduction is a no-op."""
    pairs = _t0_like_pairs(limit=12)
    assert len(pairs) >= 8
    n_checked = 0
    for H, nodes in pairs:
        _, res_p = _spec_run("prep_e1_current_tight", H, nodes, time_limit=15.0)
        assert res_p.extra["rules_fired"] == {"L": 0, "C": 0}
        assert res_p.extra["n_before"] == res_p.extra["n_after"] == len(nodes)
        _, res_c = _spec_run("current_tight", H, nodes, time_limit=15.0)
        assert res_p.status == res_c.status and res_p.to_a == res_c.to_a
        if res_p.LB is not None and res_c.LB is not None:
            assert abs(res_p.LB - res_c.LB) < 1e-9
        n_checked += 1
    assert n_checked >= 8


# ============================================================================ T0 glue instances
def _find_leaf_pair(pairs, used):
    for i, (H, nodes) in enumerate(pairs):
        if i in used:
            continue
        sub = H.subgraph(nodes)
        deg1 = [z for z in nodes if sub.degree(z) == 1]
        if deg1:
            used.add(i)
            return i, H, nodes, deg1[:2]
    return None


def _find_chain_pair(pairs, used, want_len=2):
    for i, (H, nodes) in enumerate(pairs):
        if i in used:
            continue
        sub = H.subgraph(nodes)
        deg2 = {z for z in nodes if sub.degree(z) == 2}
        for z in deg2:
            for w in sub.neighbors(z):
                if w in deg2 and w != z:
                    chain = [z, w]
                    if want_len == 3:
                        # try to extend from w to a third degree-2 neighbour != z
                        ext = [x for x in sub.neighbors(w) if x in deg2 and x != z]
                        if not ext:
                            continue
                        chain = [z, w, ext[0]]
                    used.add(i)
                    return i, H, nodes, chain
    return None


def test_glue_t0_instances_e1_matches_brute():
    """Six curated T0 pairs with selected zips zeroed (leaves / degree-2 chains): E1 fires on
    at least 3, and `prep_e1_brute` reproduces `brute`'s optimum on the modified graph exactly
    -- LB to 1e-12, feasibility, and (except on split chains) `to_a`."""
    pairs = _t0_like_pairs(limit=60)
    used: set = set()
    curated = []
    for _ in range(3):
        got = _find_leaf_pair(pairs, used)
        if got:
            curated.append(("leaf", got))
    for want_len in (2, 3, 2):
        got = _find_chain_pair(pairs, used, want_len=want_len)
        if got:
            curated.append(("chain", got))
    assert len(curated) >= 5, "not enough leaf/chain candidates among the T0-like sweep"

    n_fired = 0
    for kind, (i, H, nodes, target) in curated:
        H = H.copy()
        for z in target:
            H.nodes[z].update(A=0.0, B=0.0, M=0.0)
        _, _, leaf_assign, chain_records, fired = prep._reduce_e1(
            H.subgraph(nodes).copy(), nodes, THETA, LAM, 0.0)
        if fired["L"] > 0 or fired["C"] > 0:
            n_fired += 1

        _, res_p = _spec_run("prep_e1_brute", H, nodes, check=True)
        res_b = _brute(H, nodes)
        assert abs(res_p.LB - res_b.LB) < 1e-12, (kind, target)
        row = base.evaluate(H, nodes, res_p, theta=THETA, lam=LAM, rho=0.0)
        assert row["valid"] and row["feasible"], (kind, target, row["violations"])
        # to_a matches bit-identically whenever no chain was actually split across sides
        split = any((not rec["loop"]) and (rec["w"] in res_p.to_a) != (rec["wprime"] in res_p.to_a)
                    for rec in chain_records)
        if not split:
            assert res_p.to_a == res_b.to_a, (kind, target)
    assert n_fired >= 3, f"only {n_fired}/{len(curated)} curated instances fired a rule"


# ============================================================================ E3 quotient
def _find_stray_pairs(pairs, limit=5):
    out = []
    for H, nodes in pairs:
        ua, ub = base.utilities(H, nodes, THETA, LAM)
        free = boundsmod.ub_free_nash(H, nodes, THETA, LAM)["to_a"]
        cov = base.covariates(H, nodes, ua, ub, free_to_a=free)
        if cov["free_excess_pieces"] > 0:
            out.append((H, nodes))
            if len(out) >= limit:
                break
    return out


def test_e3_never_optimal_and_bounded_by_brute():
    pairs = _t0_like_pairs(limit=40)
    stray_pairs = _find_stray_pairs(pairs, limit=5)
    assert len(stray_pairs) >= 3, "not enough T0-like pairs with a fragmented free-Nash side"
    for H, nodes in stray_pairs:
        _, res_e3 = _spec_run("prep_e3_current_tight", H, nodes, time_limit=15.0)
        row = base.evaluate(H, nodes, res_e3, theta=THETA, lam=LAM, rho=0.0)
        assert row["valid"], row["violations"]
        assert res_e3.status != "optimal" and row["status_eff"] != "optimal"
        assert not row["valid_certificate"]
        assert res_e3.UB is None
        assert res_e3.extra["n_strays"] > 0

        res_b = _brute(H, nodes)
        if row["LB"] is not None:
            assert row["LB"] <= res_b.LB + 1e-9, (nodes, row["LB"], res_b.LB)


def test_e13_combines_both_rules():
    """`prep_e13_current_tight`: E1 first, E3 on the E1-reduced graph, then expand back through
    both.  Never optimal (E3 dominates the status/UB rule); LB stays a valid lower bound."""
    G = glue_instance(); nodes = sorted(G)
    _, res = _spec_run("prep_e13_current_tight", G, nodes, time_limit=15.0)
    row = base.evaluate(G, nodes, res, theta=THETA, lam=LAM, rho=0.0)
    assert row["valid"], row["violations"]
    assert res.UB is None
    res_b = _brute(G, nodes)
    if row["LB"] is not None:
        assert row["LB"] <= res_b.LB + 1e-9


# ============================================================================ named failures
def test_named_failures_e1_current_tu():
    """The six named contiguity failures (CLAUDE.md trap 11): report n_before/n_after through
    `prep_e1_current_tu` (PLAN.md W8 row).  No zero-value zips on real synthetic instances, so
    no reduction is expected -- that is the finding, not a failure.  `n_before`/`n_after` are
    fixed by the reduction step alone, before `inner` ever runs, so they do not depend on the
    time cap; the brief's literal "cap 20 s" was spot-checked by hand (RESULTS.md-style: every
    named failure still time-limits/heuristic-downgrades exactly as `current_tu`'s own S0 row
    does, `n_after == n_before` in every case) and is not re-run here at 20 s x 6 because
    `current_tu` is deliberately unbounded-iteration (runs to the wall on these instances by
    design -- RESULTS.md), which would push this file's suite past the "fast" budget; 2 s is
    enough to exercise the same code path and get a real (if partial) inner status."""
    n_seen = 0
    for spec in named_failures():
        pi = build_pair(spec, theta=THETA, lam=LAM, rescale=True, with_bounds=False)
        _, res = _spec_run("prep_e1_current_tu", pi.G, pi.nodes, time_limit=2.0)
        row = base.evaluate(pi.G, pi.nodes, res, theta=THETA, lam=LAM, rho=0.0)
        assert row["valid"], (spec.name, row["violations"])
        assert res.extra["n_before"] == spec.n_expected
        assert res.extra["n_after"] == spec.n_expected, \
            f"{spec.name}: unexpected E1 reduction on a real instance ({res.extra['n_after']} " \
            f"!= {res.extra['n_before']}) -- if zero-value zips have appeared, note it, don't " \
            f"just relax this assertion"
        assert res.extra["rules_fired"] == {"L": 0, "C": 0}
        n_seen += 1
    assert n_seen == 6


# ============================================================================ harness run
def test_harness_run_t0():
    """`contiguity_bench.py --methods prep_e1_current_tight,prep_e3_current_tight --tiers T0
    --cap 30`: every row validates, and no `prep_e3_*` row ever claims a certificate (TEST_PLAN
    §7 E1/E3 acceptance).  Writes under `battery/results/contiguity/` only, cleaned up after."""
    run_id = "w8_test_prep_smoke"
    run_dir = os.path.join(ROOT, "battery", "results", "contiguity", run_id)
    if os.path.isdir(run_dir):
        shutil.rmtree(run_dir)
    try:
        cmd = [sys.executable, os.path.join(ROOT, "battery", "code", "contiguity_bench.py"),
              "--methods", "prep_e1_current_tight,prep_e3_current_tight",
              "--tiers", "T0", "--cap", "30", "--workers", "4",
              "--run-id", run_id, "--quiet"]
        out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
        assert out.returncode == 0, out.stderr[-4000:]
        rows_path = os.path.join(run_dir, "rows_scored.jsonl")
        assert os.path.isfile(rows_path), out.stderr[-2000:]
        rows = [json.loads(line) for line in open(rows_path)]
        assert len(rows) >= 20
        by_method = {}
        for r in rows:
            by_method.setdefault(r["method"], []).append(r)
        assert set(by_method) == {"prep_e1_current_tight", "prep_e3_current_tight"}
        for r in rows:
            assert r["valid"], (r["method"], r["instance"], r.get("violations"))
            if r["method"] == "prep_e3_current_tight":
                assert not r.get("valid_certificate")
                assert r["status"] != "optimal"
                assert r.get("UB") is None
    finally:
        if os.path.isdir(run_dir):
            shutil.rmtree(run_dir)
