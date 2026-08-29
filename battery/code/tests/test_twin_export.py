"""test_twin_export.py -- the fast half of U3's acceptance (tools/twin_export).

Under 25 s.  Covers the vendored-code sync, both privacy guards, the normal-Laplace
density and its MLE, the quantile function, the spatial statistics, every graph input
format, the rep-map bisection, a planted leak, self-containment (the tool must run with the
repo nowhere on sys.path), Python 3.9 syntax compatibility, and a tiny end-to-end run
through the CLI.

The n=5000 stand-in and the zero-inflation fixture live in test_twin_export_e2e.py (SLOW).
"""
from __future__ import annotations

import ast
import difflib
import gzip
import inspect
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOLS = os.path.join(ROOT, "tools")
PKG = os.path.join(TOOLS, "twin_export")
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code"), TOOLS):
    if p not in sys.path:
        sys.path.insert(0, p)

import territory as T                                        # noqa: E402
from twin_export import _territory_vendored as V             # noqa: E402
from twin_export import agg as AG, check as CK, fit as F     # noqa: E402
from twin_export import io as IO, spatial as SP, stats as ST, synth as SY  # noqa: E402
from twin_export.config import Cfg                           # noqa: E402
from twin_export.tests import fixtures as FX                 # noqa: E402

PY = sys.executable
VENDORED = ("validate", "overlap_graph", "zips_for_pair", "pair_endpoints",
            "largest_pair", "census")


# ------------------------------------------------------------------ 1. vendoring
def _norm(src):
    return [ln.rstrip() for ln in src.splitlines() if ln.strip()]


def test_vendored_territory_in_sync():
    """Every vendored function must still be byte-identical to code/territory.py."""
    assert V.REQUIRED == T.REQUIRED
    drift = []
    for name in VENDORED:
        a = _norm(inspect.getsource(getattr(T, name)))
        b = _norm(inspect.getsource(getattr(V, name)))
        if a != b:
            drift.append("\n".join(difflib.unified_diff(
                a, b, fromfile="territory.%s" % name,
                tofile="_territory_vendored.%s" % name, lineterm="")))
    assert not drift, ("tools/twin_export/_territory_vendored.py has drifted from "
                       "code/territory.py; re-copy the function(s):\n\n"
                       + "\n\n".join(drift))
    with open(os.path.join(PKG, "_territory_vendored.py")) as f:
        head = f.read(2000)
    assert re.search(r"source commit  [0-9a-f]{40}", head), \
        "the vendored file must record the territory.py commit it was copied from"


# ------------------------------------------------------------------- 2. k-anon
def test_agg_kanon_guard():
    a = AG.Agg(min_support=20, enforce=True)
    a.put("fine", 1.0, 25)
    try:
        a.put("thin", 1.0, 19)
        raise AssertionError("Agg.put accepted a value backed by 19 ZCTAs")
    except AG.KAnonError as e:
        assert "thin" in str(e) and "19" in str(e)
    a.put("structural_zero", 0.0, 0)          # an empty category identifies nobody
    b = AG.Agg(min_support=20, enforce=False)
    b.put("thin", 1.0, 3)
    assert b.violations and b.violations[0]["n_support"] == 3
    with a.block("blk"):
        a.put("x", 2.0, 30)
    assert a.to_dict()["blk"]["x"] == 2.0
    assert a.to_dict()["_support"]["blk.x"] == 30
    v, s = AG.smoothed_quantiles(np.arange(1000.0), [0.0, 0.5, 1.0], 20)
    assert v[0] > 0.0 and v[2] < 999.0, "windowed quantiles must never return min or max"
    assert s >= 20


# ----------------------------------------------------------------- 3. json guard
def test_json_writer_guard():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "s.json")
    IO.write_json_guarded({"a": {"b": 1.23456789}}, path, verbose=False)
    assert json.load(open(path))["a"]["b"] == 1.23457, "must round to 6 significant figures"
    for bad, why in (({"x": list(range(300))}, "a list of 300"),
                     ({"z": "07030"}, "a 5-digit string"),
                     ({"07030": 1.0}, "a 5-digit dict key")):
        try:
            IO.write_json_guarded(bad, path, verbose=False)
            raise AssertionError("write_json_guarded accepted %s" % why)
        except AG.LeakGuardError:
            pass
    IO.write_json_guarded({"coarse_cdf": {"bin_p": [0.001] * 300}}, path, verbose=False)


# ------------------------------------------------------------- 4. dPlN density
def test_normal_laplace_density():
    a, b, nu, tau = 1.5, 3.5, 0.0, 0.6
    from scipy.integrate import quad
    total, _ = quad(lambda y: float(np.exp(F.nl_logpdf(np.array([y]), a, b, nu, tau))[0]),
                    -60, 60, limit=600)
    assert abs(total - 1.0) < 1e-6, "density does not integrate to 1 (%g)" % total

    rng = np.random.default_rng(0)
    n = 200000
    Y = nu + tau * rng.standard_normal(n) + rng.exponential(1 / a, n) - rng.exponential(1 / b, n)
    ys = np.sort(Y)
    assert F.ks_stat(ys, F.nl_cdf(ys, a, b, nu, tau)) < 0.01
    assert abs(Y.mean() - F.nl_mean(a, b, nu, tau)) < 0.01
    assert abs(Y.var() - F.nl_var(a, b, nu, tau)) < 0.02

    z = np.linspace(-4, 4, 17)
    lognormal = np.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
    assert np.max(np.abs(np.exp(F.nl_logpdf(z, 1e6, 1e6, 0.0, 1.0)) - lognormal)) < 1e-8

    import mpmath as mp                       # reference only, never imported by the tool
    mp.mp.dps = 40

    def ref(y):
        y, A, B_, N, Tu = (mp.mpf(v) for v in (y, a, b, nu, tau))
        zz = (y - N) / Tu
        phi = lambda t: mp.e ** (-t * t / 2) / mp.sqrt(2 * mp.pi)
        Phi = lambda t: mp.mpf(0.5) * mp.erfc(-t / mp.sqrt(2))
        R = lambda t: (mp.mpf(0.5) * mp.erfc(t / mp.sqrt(2))) / phi(t)
        return Phi(zz) - phi(zz) * (B_ * R(A * Tu - zz) - A * R(B_ * Tu + zz)) / (A + B_)

    for y in (-3.0, -1.0, 0.0, 1.0, 4.0):
        assert abs(float(F.nl_cdf(np.array([y]), a, b, nu, tau)[0]) - float(ref(y))) < 1e-10

    far = F.nl_logpdf(np.array([-40.0, 40.0]), a, b, nu, tau)
    assert np.all(np.isfinite(far)), "logpdf must stay finite 40 sd out"
    mid = np.array([-5.0, 0.0, 5.0])
    assert np.allclose(F.nl_cdf(mid, a, b, nu, tau) + F.nl_sf(mid, a, b, nu, tau), 1.0)


# ---------------------------------------------------------------- 5. MLE recovery
def test_normal_laplace_mle():
    a, b, nu, tau = 1.5, 3.5, 0.0, 0.6
    rng = np.random.default_rng(3)

    def draw(n):
        return nu + tau * rng.standard_normal(n) + rng.exponential(1 / a, n) \
            - rng.exponential(1 / b, n)

    r = F.fit_normal_laplace(draw(8000))
    assert r["converged"]
    assert abs(r["alpha"] - a) / a < 0.10, r["alpha"]
    assert abs(r["tau"] - tau) / tau < 0.12, r["tau"]
    assert abs(r["mean_log"] - (nu + 1 / a - 1 / b)) < 0.05
    # beta (the lower tail) is the weakly identified parameter: with tau = 0.6 the lower
    # exponential has scale 0.29 and is largely swallowed by the normal, so at n = 8000 its
    # sampling spread is ~25%.  It tightens as it should at n = 40000.
    assert abs(r["beta"] - b) / b < 0.60, r["beta"]
    r2 = F.fit_normal_laplace(draw(40000))
    for k, want in (("alpha", a), ("beta", b), ("tau", tau)):
        assert abs(r2[k] - want) / want < 0.10, (k, r2[k])

    m = F.fit_marginal(np.exp(draw(8000)))
    assert m["prefer_dpln"] and m["lr_stat"] > 20
    m2 = F.fit_marginal(np.exp(rng.normal(0, 0.8, 8000)))
    assert not m2["prefer_dpln"], "a lognormal sample must not prefer dPlN"


# ------------------------------------------------------------- 6. quantile function
def test_quantile_function():
    rng = np.random.default_rng(5)
    x = np.exp(rng.normal(0.0, 0.9, 20000))
    cc = F.coarse_cdf(x, n_bins=200, min_support=20)
    assert cc["min_bin_count"] >= 20
    fitm = F.fit_marginal(x)
    q = F.quantile_fn_from_coarse(cc, fitm)
    u = np.linspace(0.02, 0.98, 60)
    got = q(u)
    assert np.all(np.diff(got) > 0), "quantile function must be monotone"
    want = np.quantile(x, u)
    assert np.max(np.abs(np.log(got) - np.log(want))) < 0.02
    lo, hi = q(np.array([1e-4])), q(np.array([1 - 1e-4]))
    assert lo[0] < want[0] and hi[0] > want[-1], "the tails must come from the fit"
    heavy = np.concatenate([x, np.array([2000.0])])    # ~70x the sample max
    cc2 = F.coarse_cdf(heavy, n_bins=200, min_support=20)
    assert cc2["n_bins_merged"] >= 1, "one dominating value must trigger the tail merge"
    assert cc2["top_bin_share"] < 0.5 and cc2["tail_dominance_resolved"]
    # a value that dominates the whole sample cannot be hidden by merging; say so
    cc3 = F.coarse_cdf(np.concatenate([x, np.array([1e6])]), n_bins=200, min_support=20)
    assert not cc3["tail_dominance_resolved"] and cc3["n_bins"] == 1


# --------------------------------------------------------------- 6b. gini_M (U9)
def test_gini_M():
    """`scale.gini_M` is the Gini coefficient of M over positive-M ZCTAs, k-anonymised at
    full instance support -- verify it against a direct Gini computation on the same
    positive-M values `stats.blocks` sees."""
    G = FX.lattice_instance(side=20, n_rep_a=4, n_rep_b=4, n_states=2, seed=2, p_zero=0.15)
    d = tempfile.mkdtemp()
    paths = FX.write_inputs(G, d)
    cfg = Cfg(min_support=5, min_state=100, verbose=False)
    g, _ = IO.read_graph(paths["graph_csv"], states=paths["states"], verbose=False)
    inst, _ = IO.join_inputs(g, paths["opportunity"], paths["sales"], paths["reps"], cfg)
    st = ST.blocks(inst, cfg, AG.Agg(min_support=cfg.min_support))

    assert "gini_M" in st["scale"], "scale.gini_M is missing from the export"
    got = st["scale"]["gini_M"]
    assert st["_support"]["scale.gini_M"] == inst.n

    pos = np.sort(inst.M[inst.M > 0].astype(float))
    m, s = pos.size, float(pos.sum())
    direct = float((2.0 * np.arange(1, m + 1) - m - 1).dot(pos) / (m * s))
    assert abs(got - direct) < 1e-9, (got, direct)
    assert 0.0 <= got < 1.0
    assert (inst.M <= 0).any(), "fixture must actually exercise zero/glue M for this check"


# ------------------------------------------------------------------- 7. spatial
def test_spatial():
    G = nx.convert_node_labels_to_integers(nx.grid_2d_graph(30, 30))
    n = G.number_of_nodes()
    W = SP.row_normalized_adj(G, n)
    rng = np.random.default_rng(0)
    white = rng.standard_normal(n)
    assert abs(SP.morans_i(W, white)) < 0.10
    smooth = SP.smooth_field(W, white, k=2, w=1.0)
    assert SP.morans_i(W, smooth) > 0.4
    w = SP.fit_smoothing(W, 0.45, k=2, n=n)
    got = SP.morans_i(W, SP.smooth_field(W, rng.standard_normal(n), k=2, w=w))
    assert abs(got - 0.45) < 0.06, got
    hop = SP.hop_rank_corr(G, smooth, hops=4, n_sources=400,
                           rng=np.random.default_rng(1), n=n)
    rhos = [hop[h]["rho"] for h in (1, 2, 3, 4)]
    assert rhos[0] > rhos[1] > rhos[2], rhos
    rc, m = SP.neighbour_rank_corr(G, smooth, n)
    assert m == G.number_of_edges() and abs(rc - rhos[0]) < 0.10
    d = SP.haversine_km(-74.0, 40.7, -73.9, 40.7)
    assert 8.0 < float(d) < 9.0, d


# ------------------------------------------------------------------ 8. graph io
def test_graph_io_formats():
    d = tempfile.mkdtemp()
    G = FX.lattice_instance(side=8, n_rep_a=2, n_rep_b=2, n_states=2, seed=0)
    paths = FX.write_inputs(G, d)
    zids = paths["zids"]
    assert any(z.startswith("00") for z in zids), "the fixture must exercise leading zeros"

    base, rep = IO.read_graph(paths["graph_csv"], verbose=False)
    want = IO.graph_hash(sorted(base.nodes), list(base.edges))
    assert rep["format"] == "csv"

    # a pickled networkx graph, carrying an attribute that must be stripped
    import pickle
    H = nx.relabel_nodes(G, dict(zip(sorted(G.nodes), zids)))
    for z in H.nodes:
        H.nodes[z]["geometry"] = "POLYGON((0 0,1 1,1 0,0 0))"
        H.nodes[z]["secret_sales"] = 12345.6
    pk = os.path.join(d, "g.gpickle")
    with open(pk, "wb") as f:
        pickle.dump(H, f)
    g2, rep2 = IO.read_graph(pk, verbose=False)
    assert IO.graph_hash(sorted(g2.nodes), list(g2.edges)) == want
    assert set(rep2["stripped"]) >= {"geometry", "secret_sales", "rep_a", "A", "B", "M"}
    for z in g2.nodes:
        assert set(g2.nodes[z]) <= {"state", "lon", "lat"}

    gm = os.path.join(d, "g.graphml")
    nx.write_graphml(nx.Graph([(u, v) for u, v in base.edges]), gm)
    g3, _ = IO.read_graph(gm, verbose=False)
    assert IO.graph_hash(sorted(g3.nodes), list(g3.edges)) == want

    # leading zeros survive an integer round trip
    intcsv = os.path.join(d, "int.csv")
    with open(intcsv, "w") as f:
        f.write("u,v\n")
        for u, v in base.edges:
            f.write("%d,%d\n" % (int(u), int(v)))
    g4, _ = IO.read_graph(intcsv, verbose=False)
    assert IO.graph_hash(sorted(g4.nodes), list(g4.edges)) == want

    try:
        import pandas as pd
        pq = os.path.join(d, "g.parquet")
        pd.DataFrame(list(base.edges), columns=["src", "dst"]).to_parquet(pq, index=False)
    except Exception as e:                     # pyarrow absent in this venv; work machine has it
        print("  (skipping the parquet leg: %s)" % type(e).__name__)
    else:
        g5, rep5 = IO.read_graph(pq, verbose=False)
        assert IO.graph_hash(sorted(g5.nodes), list(g5.edges)) == want
        assert rep5["columns"] == ["src", "dst"]

    # join diagnostics
    cfg = Cfg(min_support=5, verbose=False)
    short = os.path.join(d, "opp_short.csv")
    rows = open(paths["opportunity"]).read().splitlines()
    with open(short, "w") as f:
        f.write("\n".join(rows[:len(rows) // 2]) + "\n")
    try:
        IO.join_inputs(base, short, paths["sales"], paths["reps"], cfg)
        raise AssertionError("join_inputs accepted a 50% join")
    except IO.InputError as e:
        assert "0.99 floor" in str(e)
    inst, jr = IO.join_inputs(base, paths["opportunity"], paths["sales"], paths["reps"], cfg)
    assert jr["join_fraction"] == 1.0 and jr["n_rep_a"] == 2
    assert inst.rep_a.dtype.kind == "i", "rep names must be integers on the Instance"


# ---------------------------------------------------------- 9. rep-map bisection
def test_rep_map_bisection():
    G = FX.lattice_instance(side=20, n_rep_a=5, n_rep_b=5, n_states=2, seed=4)
    d = tempfile.mkdtemp()
    paths = FX.write_inputs(G, d)
    cfg = Cfg(min_support=5, min_state=100, verbose=False)
    g, _ = IO.read_graph(paths["graph_csv"], states=paths["states"], verbose=False)
    inst, _ = IO.join_inputs(g, paths["opportunity"], paths["sales"], paths["reps"], cfg)
    st = ST.blocks(inst, cfg, AG.Agg(min_support=cfg.min_support))

    def run():
        return SY.rep_maps(inst.G, inst.M, inst.state, st, cfg,
                           np.random.default_rng([cfg.seed, 105]),
                           np.random.default_rng([cfg.seed, 106]), n=inst.n)

    la1, lb1, r1 = run()
    la2, lb2, r2 = run()
    assert np.array_equal(la1, la2) and np.array_equal(lb1, lb2), "rep_maps is not deterministic"
    assert r1["alpha"] == r2["alpha"] and r1["jaccard"] == r2["jaccard"]

    # the achieved Jaccard must move monotonically with the requested one
    got = []
    for target in (0.50, 0.60, 0.70, 0.80):
        s2 = json.loads(json.dumps(st))
        s2["territories"]["misalignment_jaccard"] = target
        got.append(SY.rep_maps(inst.G, inst.M, inst.state, s2, cfg,
                               np.random.default_rng([cfg.seed, 105]),
                               np.random.default_rng([cfg.seed, 106]),
                               n=inst.n)[2]["jaccard"])
    assert all(got[i] <= got[i + 1] + 1e-9 for i in range(len(got) - 1)), got
    assert max(abs(g - t) for g, t in zip(got, (0.50, 0.60, 0.70, 0.80))) < 0.10, got
    # An unreachable target must clamp at the construction's floor, not raise.  On a
    # five-rep lattice that floor is high: the B seeds are already drawn independently
    # (b_hops = -1) and every boundary ZCTA is slivered (sliver = 1), and a best-match
    # Jaccard over five large territories still cannot fall below ~0.5.
    s3 = json.loads(json.dumps(st))
    s3["territories"]["misalignment_jaccard"] = 0.01
    floor = SY.rep_maps(inst.G, inst.M, inst.state, s3, cfg,
                        np.random.default_rng([cfg.seed, 105]),
                        np.random.default_rng([cfg.seed, 106]), n=inst.n)[2]
    assert floor["b_hops"] == -1 and floor["sliver"] > 0.9 and 0.0 < floor["jaccard"] < 1.0


# --------------------------------------------------------------- 10. planted leak
def test_planted_leak_is_caught():
    d = tempfile.mkdtemp()
    G = FX.lattice_instance(side=14, n_rep_a=3, n_rep_b=3, n_states=3, seed=6)
    lonely = sorted(G.nodes)[0]
    G.nodes[lonely]["state"] = "ZZ"                     # a state with exactly one ZCTA
    paths = FX.write_inputs(G, d)
    argv = ["stats", "--graph", paths["graph_csv"], "--opportunity", paths["opportunity"],
            "--sales", paths["sales"], "--reps", paths["reps"], "--states", paths["states"],
            "--min-support", "5", "--out", d, "--quiet"]

    code, out, err = _cli(argv + ["--min-state", "1"], cwd=d)
    assert code == 2, "a one-ZCTA per-state block must exit 2 (got %d)\n%s%s" % (code, out, err)
    assert "per_state.ZZ" in (out + err), (out + err)

    code, out, err = _cli(argv + ["--min-state", "100"], cwd=d)
    assert code == 0, out + err
    st = json.load(open(os.path.join(d, "twin_stats.json")))
    assert "ZZ" not in st["per_state"] and "OTHER" in st["per_state"]


# ------------------------------------------------------------- 11. self-contained
def test_tool_is_self_contained():
    """The tool must run with the repo nowhere on sys.path, and never import it."""
    banned = {"territory", "districting", "synth", "battery", "contig_methods", "zip50",
              "mkfig_zip50", "code"}
    for fn in sorted(os.listdir(PKG)):
        if not fn.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(PKG, fn)).read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for al in node.names:
                    assert al.name.split(".")[0] not in banned, (fn, al.name)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                root = (node.module or "").split(".")[0]
                assert root not in banned, (fn, node.module)

    tmp = tempfile.mkdtemp()
    shutil.copytree(PKG, os.path.join(tmp, "twin_export"))
    env = dict(os.environ)
    env["PYTHONPATH"] = tmp
    env.pop("PYTHONHOME", None)
    r = subprocess.run([PY, "-m", "twin_export", "--help"], cwd=tmp, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "twin_stats.json" in r.stdout


# ------------------------------------------------------------ 12. py3.9 syntax
def test_python39_compatible():
    banned_attrs = {"trapz", "trapezoid", "pairwise"}
    for fn in sorted(os.listdir(PKG)) + ["tests/fixtures.py"]:
        if not fn.endswith(".py"):
            continue
        path = os.path.join(PKG, fn)
        src = open(path).read()
        try:
            tree = ast.parse(src, filename=path, feature_version=(3, 9))
        except SyntaxError as e:
            raise AssertionError("%s is not Python 3.9 syntax: %s" % (fn, e))
        if "annotations" not in src.split("\n")[0:40][0] and "import" in src:
            assert "from __future__ import annotations" in src, \
                "%s must carry `from __future__ import annotations`" % fn
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in banned_attrs:
                raise AssertionError("%s uses %s, which is not in numpy 1.24" % (fn, node.attr))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id == "zip":
                for kw in node.keywords:
                    assert kw.arg != "strict", "%s uses zip(strict=), which is 3.10+" % fn


# ------------------------------------------------------------------- 13. tiny e2e
def test_tiny_end_to_end():
    d = tempfile.mkdtemp()
    G = FX.lattice_instance(side=25, n_rep_a=6, n_rep_b=6, n_states=4, seed=1)
    assert G.number_of_nodes() == 625
    paths = FX.write_inputs(G, d)
    common = ["--graph", paths["graph_csv"], "--opportunity", paths["opportunity"],
              "--sales", paths["sales"], "--reps", paths["reps"], "--states", paths["states"],
              "--min-support", "5", "--min-state", "100", "--out", d, "--quiet"]
    for argv in (["validate"] + common, ["stats"] + common + ["--explain"],
                 ["twin"] + common + ["--stats", os.path.join(d, "twin_stats.json"), "--yes"],
                 ["validate", "--twin", os.path.join(d, "twin_instance.json.gz"),
                  "--stats", os.path.join(d, "twin_stats.json"), "--quiet"]):
        code, out, err = _cli(argv, cwd=d)
        assert code == 0, "`%s` exited %d\n%s%s" % (argv[0], code, out, err)
    st = json.load(open(os.path.join(d, "twin_stats.json")))
    bad = [r["key"] for r in st["twin_check"]["rows"] if r["ok"] is False]
    assert st["twin_check"]["passed"], "twin_check failed on: %s" % bad
    assert os.path.getsize(os.path.join(d, "leaving.txt")) > 500
    with gzip.open(os.path.join(d, "twin_instance.json.gz"), "rt") as f:
        tw = json.load(f)
    assert set(tw) >= {"meta", "nodes", "edges"}
    assert len(tw["nodes"]["z"]) == 625
    assert all(isinstance(x, int) for x in tw["nodes"]["rep_a"])
    assert tw["meta"]["tiger_vintage"] == "2025"
    assert len(tw["meta"]["graph_hash"]) == 64


def _cli(argv, cwd):
    env = dict(os.environ)
    env["PYTHONPATH"] = TOOLS + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([PY, "-m", "twin_export"] + argv, cwd=cwd, env=env,
                       capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def _unused():
    return CK
