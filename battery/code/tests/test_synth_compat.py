"""
test_synth_compat.py -- U5 guard: generator v2 must not move any existing instance.

Two layers.

**Layer A (bit identity).**  `anchors/synth_baseline.json` was generated from the
*untouched* `code/synth.py` (commit "U5 step 0") and records, per instance, the sha256 of
the raw bytes of every array `make_instance` produces (`M, A, B, pos, rep_a, rep_b,
state`) plus the `repr` of the scalar summaries.  Every new knob in generator v2 must be
a pure post-transform, a default-branch argument substitution, or a consumer of `rng2`
only -- so with all knobs off these hashes may never move.  **If this test fails, stop:
do not re-anchor.**  Regenerate deliberately with `--update` only when the *model* is
intended to change, and record why.

**Layer B (battery compatibility).**  Regenerates each `battery/figures/C*.json` case from
the hard-coded case table below (a copy of `run_battery.py::CASES`; that module is never
imported -- importing it once regenerated all 34 primary artifacts by accident) and checks
the recorded instance summaries, census, overlap pairs and free-Nash products.  Read-only:
nothing under `battery/figures/` is ever opened for writing.

Layer C: target statistics for the new scenarios (S8-S12).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for _p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ANCHOR = os.path.join(HERE, "anchors", "synth_baseline.json")
FIGS = os.path.join(ROOT, "battery", "figures")

import synth                                                       # noqa: E402
import territory as T                                              # noqa: E402


# --------------------------------------------------------------------- case table
# Verbatim copy of battery/code/run_battery.py::CASES (+ the C8 sweep's instance).
# NEVER import run_battery: it has a __main__ guard now, but the table is small and a
# copy keeps the test independent of that file entirely.
CASES = [
    dict(name="C1_aligned_seed1", scenario="S1_aligned", n=200, seed=1),
    dict(name="C1_aligned_seed2", scenario="S1_aligned", n=200, seed=2),
    dict(name="C2_entangled_a0", scenario="S2_entangled", n=200, seed=1),
    dict(name="C2_entangled_a05", scenario="S2_entangled", n=200, seed=1,
         overrides=dict(alpha=0.5)),
    dict(name="C3_slivers_ms005", scenario="S3_slivers", n=200, seed=1, min_share=0.005),
    dict(name="C3_slivers_ms02", scenario="S3_slivers", n=200, seed=1, min_share=0.02),
    dict(name="C3_slivers_ms08", scenario="S3_slivers", n=200, seed=1, min_share=0.08),
    dict(name="C4_separate", scenario="S4_separate", n=200, seed=1),
    dict(name="C4_contested", scenario="S4_separate", n=200, seed=1,
         overrides=dict(rho_books=1.0)),
    dict(name="C5_states_free", scenario="S5_states", n=200, seed=1),
    dict(name="C5_states_resp", scenario="S5_states", n=200, seed=1),
    dict(name="C6_tight", scenario="S6_tight", n=200, seed=1),
    dict(name="C6_loose", scenario=None, n=200, seed=1,
         overrides=dict(alpha=1.0, n_rep_a=4, n_rep_b=4, saturation=0.12)),
    dict(name="C7_scale_n400", scenario="S1_aligned", n=400, seed=1),
    dict(name="C9_heavytail_seed1", scenario="S7_heavytail", n=200, seed=1),
    dict(name="C9_heavytail_seed2", scenario="S7_heavytail", n=200, seed=2),
    dict(name="C8_rho_frontier", scenario="S1_aligned", n=200, seed=1),   # c8_rho_sweep.py
]

LEGACY_SCENARIOS = ["S1_aligned", "S2_entangled", "S3_slivers", "S4_separate",
                    "S5_states", "S6_tight", "S7_heavytail"]


def build(case):
    kw = dict(synth.SCENARIOS[case["scenario"]]) if case.get("scenario") else {}
    kw.update(case.get("overrides", {}))
    return synth.make_instance(n=case.get("n", 200), seed=case.get("seed", 1), **kw)


# ------------------------------------------------------------------- fingerprints
def _h(arr, dtype):
    return hashlib.sha256(np.ascontiguousarray(np.asarray(arr, dtype)).tobytes()).hexdigest()


def fingerprint(G):
    """sha256 of the raw bytes of every array make_instance produces, + scalar reprs."""
    nodes = list(G)
    f = {}
    for key in ("M", "A", "B"):
        f[key] = _h([G.nodes[z][key] for z in nodes], np.float64)
    f["P"] = _h([G.nodes[z]["pos"] for z in nodes], np.float64)
    for key in ("rep_a", "rep_b"):
        f[key] = _h([G.nodes[z][key] for z in nodes], np.int64)
    if all("state" in G.nodes[z] for z in nodes):
        f["state"] = _h([int(str(G.nodes[z]["state"])[1:]) for z in nodes], np.int64)
    else:
        f["state"] = None
    f["edges"] = _h(sorted((min(u, v), max(u, v)) for u, v in G.edges()), np.int64)
    for key in ("corr_AB", "Sa", "Sb", "Mtot"):
        f[key] = repr(G.graph[key])
    for key in ("cap_a", "cap_b"):
        f[key] = repr(G.graph[key])
    return f


def anchor_keys():
    """(key, case-dict) for every instance the anchor covers."""
    out = [(c["name"], c) for c in CASES]
    for s in LEGACY_SCENARIOS:
        for seed in (1, 2):
            out.append((f"{s}_seed{seed}", dict(scenario=s, n=200, seed=seed)))
    return out


def regenerate_anchor():
    return {k: fingerprint(build(c)) for k, c in anchor_keys()}


# ---------------------------------------------------------------- Layer A: identity
def test_bit_identity():
    """Every legacy instance is byte-for-byte what it was before generator v2."""
    with open(ANCHOR) as fh:
        want = json.load(fh)
    got = regenerate_anchor()
    assert set(got) == set(want["instances"]), (
        f"anchor covers {sorted(set(want['instances']) ^ set(got))} differently")
    bad = []
    for k in sorted(got):
        for field, v in got[k].items():
            if want["instances"][k].get(field) != v:
                bad.append(f"{k}.{field}: {want['instances'][k].get(field)!r} -> {v!r}")
    assert not bad, ("BIT IDENTITY BROKEN -- do NOT re-anchor; find the rng call that "
                     "moved:\n  " + "\n  ".join(bad[:20]))



# --------------------------------------------------------- Layer B: battery compat
def _load(name):
    with open(os.path.join(FIGS, name + ".json")) as fh:      # read-only, always
        return json.load(fh)


def _pairs(G, min_share):
    """(census rows, [(ra, rb, zips, dense)]) -- the pair enumeration of
    case_pipeline.pair_solves, re-implemented so the test never imports that module."""
    cen = T.census(G, min_share=min_share)
    O = T.overlap_graph(G)
    out = []
    for row in cen:
        dense = not row["shape"].startswith("1-1")
        if not dense:
            cand = [(row["reps_a"][0][1], row["reps_b"][0][1])]
        else:
            cand = [(u[1], v[1]) for u in row["reps_a"] for v in row["reps_b"]
                    if O.has_edge(u, v) and O[u][v]["M"] >= min_share * row["M"]]
        for ra, rb in cand:
            zips = T.zips_for_pair(G, ra, rb)
            if len(zips) < 4:
                continue
            out.append((ra, rb, zips, dense))
    return cen, out


def _close(got, want, rel, what):
    assert want == 0 or abs(got - want) <= rel * abs(want), \
        f"{what}: {got!r} vs recorded {want!r} (rel tol {rel})"


def test_battery_instances_match():
    """Every C*.json instance summary, census and pair list regenerates exactly.

    Recorded before U0c added four params keys, so the JSON's `params` must be a SUBSET of
    the regenerated one -- an added key is fine, a changed value is not.
    """
    for case in CASES:
        if case["name"] == "C8_rho_frontier":
            continue
        rec = _load(case["name"])
        G = build(case)
        params = G.graph["params"]
        for k, want in rec["params"].items():
            assert k in params, f"{case['name']}: params lost key {k!r}"
            assert params[k] == want, \
                f"{case['name']}: params[{k!r}] {params[k]!r} != recorded {want!r}"
        for k in ("corr_AB", "Sa", "Sb", "Mtot"):
            _close(G.graph[k], rec[k], 1e-12, f"{case['name']}.{k}")
        assert T.validate(G) == rec["validate"], f"{case['name']}: validate changed"

        cen, pairs = _pairs(G, case.get("min_share", 0.02))
        got_c = sorted((r["shape"], r["share"]) for r in cen)
        want_c = sorted((r["shape"], r["share"]) for r in rec["census"])
        assert [s for s, _ in got_c] == [s for s, _ in want_c], \
            f"{case['name']}: census shapes {[s for s, _ in got_c]} != {[s for s, _ in want_c]}"
        for (_, gs), (_, ws) in zip(got_c, want_c):
            _close(gs, ws, 1e-12, f"{case['name']}.census.share")

        got_p = {(ra, rb): (len(z), dense) for ra, rb, z, dense in pairs}
        want_p = {(p["ra"], p["rb"]): (p["n_zips"], p["dense"]) for p in rec["pairs"]}
        assert got_p == want_p, \
            f"{case['name']}: pairs {sorted(got_p)} != recorded {sorted(want_p)}"


SOLVER_FALLBACKS: list = []


def test_battery_products_match():
    """Free-Nash product per recorded pair, to 1e-9 relative.

    A pair whose exact solve no longer *certifies* is checked more weakly, and loudly:
    `territory.solve` then silently returns the prefix heuristic, whose product can only be
    <= the recorded optimum, so that is what is asserted.  This is a solver-environment
    issue, not a generator one -- the instance itself is byte-identical (Layer A) -- and
    `territory.py` is not U5's to fix.  See SOLVER_FALLBACKS / the printed banner.
    """
    SOLVER_FALLBACKS.clear()
    for case in CASES:
        if case["name"] == "C8_rho_frontier":
            continue
        rec = _load(case["name"])
        G = build(case)
        _, pairs = _pairs(G, case.get("min_share", 0.02))
        by = {(ra, rb): z for ra, rb, z, _ in pairs}
        for p in rec["pairs"]:
            res = T.solve(G, by[(p["ra"], p["rb"])], "nash")
            prod = res.get("product", res["g_a"] * res["g_b"])
            what = f"{case['name']} A{p['ra']}/B{p['rb']}"
            if res.get("exact"):
                _close(prod, p["nash"]["product"], 1e-9, what + ".product")
            else:
                SOLVER_FALLBACKS.append((what, len(by[(p["ra"], p["rb"])]),
                                         prod, p["nash"]["product"]))
                assert prod <= p["nash"]["product"] * (1 + 1e-9), (
                    f"{what}: heuristic fallback product {prod!r} EXCEEDS the recorded "
                    f"exact optimum {p['nash']['product']!r} -- the instance moved")
    if SOLVER_FALLBACKS:
        print("    " + "!" * 68)
        print("    SOLVER REGRESSION (not U5): territory.nash_exact no longer certifies")
        print("    these recorded pairs under scipy 1.18.1 / HiGHS 1.15.1 -- milp() comes")
        print("    back 'HiGHS Status 4: Solve error' after ~2 outer-approximation rounds,")
        print("    and territory.solve falls back to the prefix heuristic without saying")
        print("    so.  Suspect the two options scipy reports as unrecognized and passes")
        print("    to HiGHS verbatim (territory.py:223 mip_feasibility_tolerance=1e-9,")
        print("    primal_feasibility_tolerance=1e-9).  Owner: U2 / main session.")
        for what, nz, got, want in SOLVER_FALLBACKS:
            print(f"      {what}  n={nz}  prefix {got:.9f} vs recorded exact {want:.9f}")
        print("    " + "!" * 68)


def test_c8_pair_and_product():
    rec = _load("C8_rho_frontier")
    G = build([c for c in CASES if c["name"] == "C8_rho_frontier"][0])
    ra, rb, _ = T.largest_pair(G)
    zips = T.zips_for_pair(G, ra, rb)
    assert (ra, rb) == (rec["pair"]["ra"], rec["pair"]["rb"]), "C8 largest pair moved"
    assert len(zips) == rec["pair"]["n_zips"], "C8 pair size moved"
    res = T.solve(G, zips, "nash")
    _close(res["product"], rec["unconstrained"]["product"], 1e-9, "C8.product")


# ------------------------------------------------- Layer C: generator-v2 target stats
def test_S10_glue_active_frac():
    """S10_glue hits its active fraction and actually fragments the active subgraph."""
    seen = []
    for n in (200, 2000):
        for seed in (1, 2, 3):
            G = synth.scenario("S10_glue", n=n, seed=seed)
            r = synth.activity_report(G)
            seen.append((n, seed, r["active_frac"], r["active_pieces"]))
            assert abs(r["active_frac"] - synth.S10_ACTIVE_TARGET) <= 0.02, \
                f"S10_glue n={n} seed={seed}: active_frac {r['active_frac']:.3f}"
            assert r["M_share_untapped"] > 0, "untapped zips must keep their opportunity"
            assert r["glue_frac"] > 0 and r["untapped_frac"] > 0
            if n >= 2000:
                # a 200-node Delaunay graph often survives losing 45% of its nodes;
                # at 2000 the glue reliably cuts the active subgraph (26-47 pieces).
                assert r["active_pieces"] > 1, \
                    f"S10_glue n={n} seed={seed}: active_pieces={r['active_pieces']}"
    print("    S10 active_frac/pieces:", seen)


def test_S10_glue_validates():
    for seed in (1, 2, 3):
        G = synth.scenario("S10_glue", n=500, seed=seed)
        assert T.validate(G) == [], T.validate(G)
        A = [G.nodes[z]["A"] for z in G]; M = [G.nodes[z]["M"] for z in G]
        assert min(M) == 0.0 and min(A) == 0.0, "S10_glue must produce zero-value zips"


def test_S11_metro_gini():
    g = [synth.activity_report(synth.scenario("S11_metro", n=2000, seed=s))["gini_M"]
         for s in (1, 2, 3)]
    m = float(np.mean(g))
    print(f"    S11 gini_M per seed {[round(x, 3) for x in g]} mean {m:.3f}")
    assert abs(m - synth.S11_GINI_TARGET) <= 0.05, f"S11 mean Gini(M) {m:.3f}"


def test_S11_metro_concentration():
    for seed in (1, 2, 3):
        r = synth.activity_report(synth.scenario("S11_metro", n=2000, seed=seed))
        print(f"    S11 seed {seed}: top10={r['top10_share_M']:.3f} "
              f"top1={r['top1_share_M']:.3f} gini_u={r['gini_u']:.3f}")
        assert r["top10_share_M"] > 0.35, f"top-10% M share {r['top10_share_M']:.3f}"


def test_S9_dense_components():
    for seed in (1, 2, 3):
        G = synth.scenario("S9_dense", n=200, seed=seed)
        cen = T.census(G, min_share=0.02)
        dense = [r["shape"] for r in cen if not r["shape"].startswith("1-1")]
        print(f"    S9 seed {seed}: {dense}")
        assert len(dense) >= 2, f"S9_dense seed {seed}: only {dense}"
        assert T.validate(G) == []


def test_S8_twin_uncalibrated():
    """calibrate(None) must be usable, honest, and never raise."""
    c = synth.calibrate(None, n=2000)
    assert c["calibrated"] is False and c["calib_source"] == "literature"
    assert set(c["calib_missing"]) == set(synth.CALIB_MAP), "every key should have missed"
    assert set(c["variants"]) == {"ln", "ht"}
    for k in ("n_rep_a", "n_rep_b", "rho_books", "tail", "sales_tail", "activity"):
        assert k in c["overrides"], k
    G = synth.scenario("S8_twin", n=500, seed=1)
    assert G.graph["params"]["calibrated"] is False
    assert G.graph["params"]["calib_source"] == "literature"
    assert T.validate(G) == []
    try:
        synth.calibrate({}, strict=True)
    except KeyError:
        pass
    else:
        raise AssertionError("strict=True must raise on a stats file with no keys")


def test_calibrate_partial():
    """A stats file with a few keys -> calib_source 'partial' and those knobs honoured."""
    stats = dict(marginals=dict(M=dict(lognormal=dict(sigma=0.41))),
                 activity=dict(glue_frac=0.30),
                 territories=dict(reps_per_firm=50,
                                  census=dict(dense_share=0.25)))
    c = synth.calibrate(stats, n=2000, fit_rho=False)
    assert c["calibrated"] is True and c["calib_source"] == "partial"
    assert c["overrides"]["tail"] == 0.41
    assert c["overrides"]["activity"]["p_glue"] == 0.30
    assert c["overrides"]["n_rep_a"] == 50
    assert c["overrides"]["split_b"] >= 1 and c["overrides"]["split_a"] >= 0
    assert "M_sigma_log" not in c["calib_missing"]
    assert "corr_log_AB" in c["calib_missing"]
    G = synth.scenario("S8_twin", n=400, seed=1, stats=stats)
    assert G.graph["params"]["calibrated"] is True
    assert G.graph["params"]["calib_source"] == "partial"


def test_all_new_scenarios_validate():
    for name in ("S8_twin", "S8_twin_ln", "S8_twin_ht", "S9_dense", "S10_glue",
                 "S11_metro"):
        for seed in (1, 2):
            for n in (200, 2000):
                G = synth.scenario(name, n=n, seed=seed)
                assert T.validate(G) == [], f"{name} n={n} seed={seed}: {T.validate(G)}"
                assert G.number_of_nodes() == n
    try:
        synth.scenario("S12_regional")
    except NotImplementedError as e:
        assert "regions.py" in str(e)
    else:
        raise AssertionError("S12_regional must point at U8")


def test_assign_graph():
    """alpha=1 in graph mode: every B rep keeps A's base, so the partitions coincide."""
    G = synth.make_instance(n=300, seed=1, alpha=1.0, n_rep_a=4, n_rep_b=4, assign="graph")
    assert [G.nodes[z]["rep_a"] for z in G] == [G.nodes[z]["rep_b"] for z in G]
    assert T.validate(G) == []
    H = synth.make_instance(n=300, seed=1, alpha=0.4, n_rep_a=4, n_rep_b=5,
                            assign="graph", b_hops=4, sliver=0.03)
    assert [H.nodes[z]["rep_a"] for z in H] != [H.nodes[z]["rep_b"] for z in H]
    assert T.validate(H) == []
    # every territory is connected: that is the whole point of BFS Voronoi
    for key, k in (("rep_a", 4), ("rep_b", 4)):
        for r in range(k):
            sub = G.subgraph([z for z in G if G.nodes[z][key] == r])
            if sub.number_of_nodes():
                assert nx.is_connected(sub), f"{key}={r} is not connected"


def test_density_field():
    """External graph + positions + density field: a 20x20 grid, no Delaunay anywhere."""
    g = nx.grid_2d_graph(20, 20)
    pos = {z: (float(z[0]), float(z[1])) for z in g}
    order = sorted(g)
    df = np.array([1.0 + 8.0 * np.exp(-((u - 5) ** 2 + (v - 5) ** 2) / 20.0)
                   for u, v in order])
    G = synth.make_instance(n=400, graph=g, pos=pos, density_field=df, seed=3,
                            assign="graph", n_rep_a=3, n_rep_b=3,
                            activity=dict(p_glue=0.2, p_untapped=0.1))
    assert G.number_of_nodes() == 400 and G.number_of_edges() == g.number_of_edges()
    assert G.graph["node_labels"][0] == "(0, 0)"
    assert G.graph["params"]["density_field_hash"] and G.graph["params"]["graph_hash"]
    assert G.graph["params"]["n_metros"] == 0 and G.graph["metros"] == []
    assert T.validate(G) == []
    # M must follow the supplied field, not a Gaussian mixture of its own
    M = np.array([G.nodes[z]["M"] for z in G])
    assert np.corrcoef(M, df)[0, 1] > 0.6
    # real state labels win; asking for synthetic bands as well is an error
    nx.set_node_attributes(g, {z: ("E" if z[0] < 10 else "W") for z in g}, "state")
    G2 = synth.make_instance(n=400, graph=g, pos=pos, density_field=df, seed=3,
                             assign="graph", n_rep_a=3, n_rep_b=3)
    assert {G2.nodes[z]["state"] for z in G2} == {"E", "W"}
    try:
        synth.make_instance(n=400, graph=g, pos=pos, density_field=df, seed=3, n_states=4)
    except ValueError as e:
        assert "n_states" in str(e)
    else:
        raise AssertionError("n_states alongside real state labels must raise")


def test_share_curve_recovers_sd():
    """The per-decile sd of log(A/M) comes back, i.e. the mixing really is unit-variance."""
    sd = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
    G = synth.make_instance(n=4000, seed=1,
                            share_curve=dict(mu=[-2.5] * 10, sd=sd, w_spatial=0.6))
    A = np.array([G.nodes[z]["A"] for z in G]); M = np.array([G.nodes[z]["M"] for z in G])
    d = synth._deciles(M)
    got = [float(np.log(A[d == k] / M[d == k]).std()) for k in range(10)]
    print("    share_curve sd:", [round(x, 3) for x in got])
    for k in range(10):
        assert abs(got[k] - sd[k]) <= 0.15, f"decile {k}: {got[k]:.3f} vs {sd[k]}"
    assert got == sorted(got), "per-decile sd must stay monotone"


def test_calibrated_kwarg_raises():
    try:
        synth.make_instance(n=50, calibrated=True)
    except TypeError as e:
        assert "scenario()" in str(e)
    else:
        raise AssertionError("make_instance(calibrated=...) must raise TypeError")


def test_runtime_n8000():
    t0 = time.time()
    synth.make_instance(n=8000, seed=1)
    dt = time.time() - t0
    print(f"    n=8000 build: {dt:.2f}s")
    assert dt < 5.0, f"n=8000 took {dt:.1f}s"


def test_adjacency_hoist():
    """The hoisted median/component list must not have changed _adjacency's output."""
    rng = np.random.default_rng(7)
    P = rng.random((400, 2))
    G = synth._adjacency(P)
    tri = __import__("scipy.spatial", fromlist=["Delaunay"]).Delaunay(P)
    E = set()
    for s in tri.simplices:
        for i in range(3):
            u, v = int(s[i]), int(s[(i + 1) % 3])
            E.add((min(u, v), max(u, v)))
    E = list(E)
    L = np.array([np.linalg.norm(P[u] - P[v]) for u, v in E])
    keep = {e for e, l in zip(E, L) if l <= 2.5 * np.median(L)}
    assert keep <= set(map(lambda e: (min(e), max(e)), G.edges()))
    assert nx.is_connected(G)


if __name__ == "__main__":
    if "--update" in sys.argv:
        print("=" * 72)
        print("WARNING: rewriting the U5 bit-identity anchor.")
        print("This is only legitimate when the generator's DEFAULT model is")
        print("deliberately changed.  A failing test_bit_identity is NOT a reason.")
        print("=" * 72)
        payload = dict(
            note=("sha256 of make_instance's raw output arrays with every generator-v2 "
                  "knob off; generated from the pre-U5 code/synth.py"),
            instances=regenerate_anchor())
        with open(ANCHOR, "w") as fh:
            json.dump(payload, fh, indent=1, sort_keys=True)
        print(f"wrote {ANCHOR}  ({len(payload['instances'])} instances)")
    else:
        test_bit_identity()
        print("bit identity OK")
