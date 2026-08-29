"""
test_twin.py -- battery/code/twin.py (PLAN.md C.3, unit U4).

Fast (< 5s).  Uses the committed `data/zcta_adjacency.npz` cache -- never geopandas --
and `twin.make_standin_twin` (a locally fabricated stand-in for U3's not-yet-landed
`twin_instance.json.gz`, built from real ZCTA ids/edges in the cached adjacency).

Acceptance (PLAN.md C.5, U4 row): reproducible adjacency build (see test_twin_build.py,
SLOW); loads a twin (the stand-in here); `edge_diff` detects a perturbed edge list.
"""
from __future__ import annotations

import gzip
import json
import os
import sys

import numpy as np
import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

import territory as T                # noqa: E402
import twin                          # noqa: E402

ADJ = os.path.join(ROOT, "data", "zcta_adjacency.npz")


def _write(obj, path):
    with gzip.open(path, "wt") as f:
        json.dump(obj, f)
    return path


def _standin(tmp="/tmp/td_test_twin_standin.json.gz", **kwargs):
    kwargs.setdefault("n", 800)
    kwargs.setdefault("seed", 11)
    kwargs.setdefault("n_rep_a", 6)
    kwargs.setdefault("n_rep_b", 6)
    obj = twin.make_standin_twin(**kwargs)
    return _write(obj, tmp), obj


# ------------------------------------------------------------------------ adjacency
def test_adjacency_cache_committed_and_sane():
    assert os.path.exists(ADJ), f"{ADJ} must be committed (PLAN.md C.5, U4)"
    assert os.path.getsize(ADJ) < 5_000_000, "adjacency cache should be ~2MB, not parquet-sized"
    adj = twin.load_adjacency(ADJ)
    n, m = len(adj["zcta"]), len(adj["edges"])
    assert n > 30000 and m > 50000, f"unexpectedly small national adjacency: n={n} m={m}"
    assert adj["zcta"].dtype.kind == "U" and all(len(z) == 5 for z in adj["zcta"][:100])
    assert list(adj["zcta"]) == sorted(adj["zcta"]), "zcta array must be ascending sorted"
    e = adj["edges"]
    assert e.dtype == np.int32 and e.ndim == 2 and e.shape[1] == 2
    assert (e[:, 0] != e[:, 1]).all(), "no self-edges"
    assert (e[:, 0] < e[:, 1]).all(), "edges stored as i < j"
    assert len(set(map(tuple, e.tolist()))) == m, "no duplicate edges"
    assert adj["x"].min() >= 0 and adj["y"].min() >= 0
    assert max(adj["x"].max(), adj["y"].max()) <= 1.0 + 1e-6, "[0,1]^2 rescale"
    assert adj["meta"]["vintage"] == "2020" and adj["meta"]["n"] == n and adj["meta"]["m"] == m


def test_load_adjacency_is_numpy_only():
    # np.load with allow_pickle=False must succeed -- the .npz carries no pickled objects.
    with np.load(ADJ, allow_pickle=False) as z:
        assert set(z.files) >= {"zcta", "edges", "lon", "lat", "x", "y", "meta_json"}


def test_save_load_adjacency_roundtrip(tmp_path=None):
    adj = twin.load_adjacency(ADJ)
    small = dict(zcta=adj["zcta"][:50], edges=adj["edges"][:0].copy(),
                lon=adj["lon"][:50], lat=adj["lat"][:50], x=adj["x"][:50], y=adj["y"][:50],
                meta=dict(vintage="2020", n=50, m=0))
    path = "/tmp/td_test_adjacency_roundtrip.npz"
    twin.save_adjacency(small, path)
    back = twin.load_adjacency(path)
    assert np.array_equal(back["zcta"], small["zcta"])
    assert back["meta"] == small["meta"]
    os.remove(path)


# --------------------------------------------------------------------------- standin
def test_make_standin_twin_deterministic():
    _, obj1 = _standin()
    _, obj2 = _standin()
    assert json.dumps(obj1, sort_keys=True) == json.dumps(obj2, sort_keys=True)


def test_make_standin_twin_uses_real_ids_and_edges():
    _, obj = _standin()
    adj = twin.load_adjacency(ADJ)
    real_ids = set(adj["zcta"].tolist())
    zids = obj["nodes"]["z"]
    assert len(zids) == 800
    assert set(zids) <= real_ids, "stand-in must use real TIGER ZCTA ids"
    real_edges = {tuple(sorted((adj["zcta"][a], adj["zcta"][b]))) for a, b in adj["edges"]}
    obj_edges = {tuple(sorted((u, v))) for u, v in zip(obj["edges"]["u"], obj["edges"]["v"])}
    assert obj_edges <= real_edges, "stand-in edges must be a subset of the cached adjacency"
    # the induced subgraph on the region should be connected (BFS-grown)
    G = nx.Graph(); G.add_nodes_from(zids); G.add_edges_from(zip(obj["edges"]["u"], obj["edges"]["v"]))
    assert nx.number_connected_components(G) == 1


def test_make_standin_twin_headroom_and_meta():
    _, obj = _standin()
    A = np.array(obj["nodes"]["A"]); B = np.array(obj["nodes"]["B"]); M = np.array(obj["nodes"]["M"])
    theta = obj["meta"]["theta"]
    assert (M >= A + theta * B - 1e-9).all() and (M >= B + theta * A - 1e-9).all()
    for key in ("seed", "rank_sigma", "n_rep_a", "n_rep_b", "theta", "graph_hash", "tiger_vintage"):
        assert key in obj["meta"], f"missing meta.{key}"
    assert obj["meta"]["standin"] is True


# ------------------------------------------------------------------------ load_twin
def test_load_twin_validates_and_tags_graph():
    path, obj = _standin()
    G = twin.load_twin(path, check_edges=True)
    assert G.number_of_nodes() == len(obj["nodes"]["z"])
    assert G.number_of_edges() == len(obj["edges"]["u"])
    assert G.graph["twin"] is True
    assert G.graph["meta"]["seed"] == obj["meta"]["seed"]
    for z in list(G.nodes)[:5]:
        d = G.nodes[z]
        for k in ("rep_a", "rep_b", "A", "B", "M", "state", "pos"):
            assert k in d, f"node {z} missing {k}"
        assert isinstance(d["pos"], tuple) and len(d["pos"]) == 2
    assert T.validate(G) == []


def test_load_twin_edge_diff_is_exact_on_untouched_list():
    path, obj = _standin(tmp="/tmp/td_test_twin_exact.json.gz", seed=13)
    adj = twin.load_adjacency(ADJ)
    twin_set = set(obj["nodes"]["z"])
    cached = [(adj["zcta"][a], adj["zcta"][b]) for a, b in adj["edges"]
              if adj["zcta"][a] in twin_set and adj["zcta"][b] in twin_set]
    d = twin.edge_diff(zip(obj["edges"]["u"], obj["edges"]["v"]), cached)
    assert d["jaccard"] == 1.0, "stand-in edges are a straight copy of the cached adjacency"
    # and load_twin's own internal check must pass silently
    twin.load_twin(path, check_edges=True)


# ------------------------------------------------------------------------ edge_diff
def _perturb_edges(obj, frac=0.02, seed=0):
    """Drop a fraction of real edges and splice in the same number of fabricated
    (non-adjacent) pairs among the same node set -- large enough to clear the 0.999
    Jaccard floor with a small instance (0.5% of ~2000 edges is under 1 dropped edge)."""
    rng = np.random.default_rng(seed)
    u, v = list(obj["edges"]["u"]), list(obj["edges"]["v"])
    m = len(u)
    n_drop = max(1, int(round(frac * m)))
    drop_idx = set(rng.choice(m, size=n_drop, replace=False).tolist())
    real = {tuple(sorted((u[i], v[i]))) for i in range(m)}
    zids = obj["nodes"]["z"]
    keep_u = [u[i] for i in range(m) if i not in drop_idx]
    keep_v = [v[i] for i in range(m) if i not in drop_idx]
    fake = []
    while len(fake) < n_drop:
        a, b = rng.choice(zids, size=2, replace=False)
        pair = tuple(sorted((a, b)))
        if pair not in real and pair not in fake:
            fake.append(pair)
    obj2 = json.loads(json.dumps(obj))
    obj2["edges"]["u"] = keep_u + [p[0] for p in fake]
    obj2["edges"]["v"] = keep_v + [p[1] for p in fake]
    return obj2


def test_edge_diff_detects_a_perturbed_edge_list():
    path, obj = _standin(tmp="/tmp/td_test_twin_perturb_base.json.gz", seed=17, n=1200)
    perturbed = _perturb_edges(obj, frac=0.02, seed=0)   # 2% swap -> well past the floor
    ppath = _write(perturbed, "/tmp/td_test_twin_perturbed.json.gz")

    adj = twin.load_adjacency(ADJ)
    twin_set = set(obj["nodes"]["z"])
    cached = [(adj["zcta"][a], adj["zcta"][b]) for a, b in adj["edges"]
              if adj["zcta"][a] in twin_set and adj["zcta"][b] in twin_set]
    d = twin.edge_diff(zip(perturbed["edges"]["u"], perturbed["edges"]["v"]), cached)
    assert d["jaccard"] < 0.999, f"perturbation should drop jaccard below the floor, got {d['jaccard']}"
    assert d["only_a"], "the fabricated edges should show up as only-in-twin"

    raised = False
    try:
        twin.load_twin(ppath, check_edges=True)
    except AssertionError:
        raised = True
    assert raised, "load_twin(check_edges=True) must reject a perturbed edge list"

    # and the untouched twin still passes with check_edges=True at this call site
    twin.load_twin(path, check_edges=True)


# ------------------------------------------------------------------------ twin_pairs
def _multi_pair_standin():
    # n=4000, 6x6 reps, seed=7: verified offline to yield 3 clean 1-1 pairs
    # (sizes 320 / 643 / 692) at min_share=0.02 -- exercises real band selection.
    return _standin(tmp="/tmp/td_test_twin_multipair.json.gz", n=4000, seed=7,
                    n_rep_a=6, n_rep_b=6)


def test_twin_pairs_selects_bands_and_largest():
    path, obj = _multi_pair_standin()
    G = twin.load_twin(path, check_edges=False)
    pairs = twin.twin_pairs(G, min_share=0.02, bands=(50, 150, 300), per_band=2, largest=3)
    assert len(pairs) >= 1
    # cross-check every returned pair against territory.zips_for_pair directly
    for p in pairs:
        zips = T.zips_for_pair(G, p["rep_a"], p["rep_b"])
        assert len(zips) == p["n"], p
        assert p["name"] == f"twin_{p['rep_a']}_{p['rep_b']}_n{p['n']}"
    ns = [p["n"] for p in pairs]
    assert ns == sorted(ns), "twin_pairs must return pairs sorted by n ascending"
    assert len(set((p["rep_a"], p["rep_b"]) for p in pairs)) == len(pairs), "no duplicate pairs"
    # the single largest census pair must be included (largest>=1)
    census_pairs = [(r["reps_a"][0][1], r["reps_b"][0][1], len(T.zips_for_pair(G, r["reps_a"][0][1], r["reps_b"][0][1])))
                    for r in T.census(G, min_share=0.02) if r["shape"] == "1-1 pair"]
    if census_pairs:
        biggest = max(census_pairs, key=lambda t: t[2])
        assert (biggest[0], biggest[1]) in {(p["rep_a"], p["rep_b"]) for p in pairs}


def test_twin_pairs_deterministic():
    path, obj = _multi_pair_standin()
    G = twin.load_twin(path, check_edges=False)
    p1 = twin.twin_pairs(G, min_share=0.02, bands=(50, 150, 300), per_band=2, largest=3)
    p2 = twin.twin_pairs(G, min_share=0.02, bands=(50, 150, 300), per_band=2, largest=3)
    assert p1 == p2


def test_twin_pairs_nearest_to_band_is_closer_than_alternatives():
    path, obj = _multi_pair_standin()
    G = twin.load_twin(path, check_edges=False)
    all_pairs = []
    for r in T.census(G, min_share=0.02):
        if r["shape"] != "1-1 pair":
            continue
        ra, rb = r["reps_a"][0][1], r["reps_b"][0][1]
        all_pairs.append((ra, rb, len(T.zips_for_pair(G, ra, rb))))
    if len(all_pairs) < 2:
        return  # not enough structure in this fabricated instance to test ordering
    band = all_pairs[0][2]                              # target exactly one real pair's size
    chosen = twin.twin_pairs(G, min_share=0.02, bands=(band,), per_band=1, largest=0)
    assert chosen, "expected at least one pair nearest the chosen band"
    best_gap = min(abs(n - band) for _, _, n in all_pairs)
    assert abs(chosen[0]["n"] - band) == best_gap
