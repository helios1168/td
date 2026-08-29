"""
gfx/schemas.py -- the per-instance JSON schema the `instance_card` producer consumes
(PLAN.md U7 brief, additional binding detail #1). U1b (the harness) writes to this shape;
`make_fixture_instance` builds a synthetic stand-in (random planar points + Delaunay, no
solver, no networkx) for tests and for `fixtures_make.py`.

Shape (all node-aligned arrays have length len(nodes); `edges` are *index* pairs into
`nodes`, not node ids, to keep the JSON compact):

    {
      "spec": {"name": str, "tier": str, "scenario": str|null, "n": int, "seed": int,
               "rep_a": ..., "rep_b": ..., "params": {...}},
      "nodes": [id, ...],
      "pos":   [[x, y], ...],                 # in [0, 1]^2, equal-area
      "edges": [[i, j], ...],                 # indices into `nodes`
      "A": [float, ...], "B": [float, ...], "M": [float, ...],
      "state":  [str, ...] | null,             # optional
      "rep_a":  [id, ...] | null,              # optional: pre-merger owner, whole-instance
      "rep_b":  [id, ...] | null,              # optional
      "free_to_a": [id, ...] | null,           # free-Nash allocation ids (subset of nodes)
      "covariates": {...} | null,              # base.covariates(...) dict, if computed
      "rows": [ {method, to_a: [id,...], status, ...}, ... ] | null   # evaluate() rows
    }

`battery/code/instances.py::write_instance_json` writes `rows: null` by decision (PLAN.md ★1
Q5) -- the phase-1 instance JSON does not carry a copy of the run's results. `instance_card`'s
`--rows <rows.jsonl>` flag joins them in by `spec.name == row["instance"]` at render time
instead, so a valid instance JSON with `rows: null` is expected, not a bug.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

REQUIRED_TOP = ("spec", "nodes", "pos", "edges", "A", "B", "M")
NODE_ALIGNED = ("pos", "A", "B", "M", "state", "rep_a", "rep_b")


def validate_instance_json(d: dict) -> list:
    """Return a list of violation strings (empty <=> valid). Tolerant of every optional
    key being absent or None."""
    v = []
    if not isinstance(d, dict):
        return ["instance JSON is not an object"]
    for k in REQUIRED_TOP:
        if k not in d:
            v.append(f"missing top-level key {k!r}")
    if v:
        return v
    nodes = d["nodes"]
    n = len(nodes)
    if len(set(nodes)) != n:
        v.append("nodes contains duplicate ids")
    for k in NODE_ALIGNED:
        val = d.get(k)
        if val is not None and len(val) != n:
            v.append(f"{k!r} has length {len(val)}, expected {n} (len(nodes))")
    pos = d.get("pos") or []
    for i, p in enumerate(pos):
        if len(p) != 2:
            v.append(f"pos[{i}] is not an [x, y] pair")
            break
    nodeset = set(nodes)
    for e in d.get("edges") or []:
        if len(e) != 2 or not (0 <= e[0] < n) or not (0 <= e[1] < n):
            v.append(f"edge {e!r} is not a valid index pair into nodes (n={n})")
            break
    if not isinstance(d.get("spec"), dict):
        v.append("spec must be an object")
    ft = d.get("free_to_a")
    if ft is not None:
        bad = [z for z in ft if z not in nodeset]
        if bad:
            v.append(f"free_to_a contains {len(bad)} id(s) outside nodes (e.g. {bad[:3]!r})")
    rows = d.get("rows")
    if rows is not None:
        for i, row in enumerate(rows):
            if "method" not in row:
                v.append(f"rows[{i}] missing 'method'")
            to_a = row.get("to_a")
            if to_a is not None:
                bad = [z for z in to_a if z not in nodeset]
                if bad:
                    v.append(f"rows[{i}].to_a contains {len(bad)} id(s) outside nodes")
    v.extend(_validate_context(d.get("context"), nodeset))
    return v


def _validate_context(ctx, pair_nodeset: set) -> list:
    """Validate the optional whole-instance `context` block (U11): tolerant of absence
    entirely (older instance JSONs, or a run that skipped it) -- only checked when present."""
    if ctx is None:
        return []
    v = []
    if not isinstance(ctx, dict):
        return ["context is not an object"]
    required = ("nodes", "pos", "rep_a", "rep_b")
    for k in required:
        if k not in ctx:
            v.append(f"context missing key {k!r}")
    if any(k not in ctx for k in required):
        return v
    cnodes = ctx["nodes"]
    n = len(cnodes)
    if len(set(cnodes)) != n:
        v.append("context.nodes contains duplicate ids")
    for k in ("pos", "rep_a", "rep_b"):
        if len(ctx[k]) != n:
            v.append(f"context.{k!r} has length {len(ctx[k])}, expected {n} (len(context.nodes))")
    for i, p in enumerate(ctx.get("pos") or []):
        if len(p) != 2:
            v.append(f"context.pos[{i}] is not an [x, y] pair")
            break
    edges = ctx.get("edges")
    if edges is not None:
        for e in edges:
            if len(e) != 2 or not (0 <= e[0] < n) or not (0 <= e[1] < n):
                v.append(f"context.edge {e!r} is not a valid index pair into context.nodes (n={n})")
                break
    cnodeset = set(cnodes)
    bad = [z for z in pair_nodeset if z not in cnodeset]
    if bad:
        v.append(f"nodes contains {len(bad)} id(s) not present in context.nodes (e.g. {bad[:3]!r})")
    return v


# --------------------------------------------------------------------------- fixtures
def _delaunay_edges(pos: np.ndarray) -> list:
    from scipy.spatial import Delaunay

    if len(pos) < 4:
        return [(i, j) for i in range(len(pos)) for j in range(i + 1, len(pos))]
    tri = Delaunay(pos)
    edges = set()
    for simplex in tri.simplices:
        for i in range(3):
            a, b = int(simplex[i]), int(simplex[(i + 1) % 3])
            edges.add((min(a, b), max(a, b)))
    return sorted(edges)


def _connected_components(n: int, edges) -> list:
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i, j in edges:
        union(i, j)
    comps: dict = {}
    for i in range(n):
        comps.setdefault(find(i), []).append(i)
    return list(comps.values())


def _gini(v: np.ndarray) -> float:
    v = np.sort(np.asarray(v, float))
    n = len(v)
    s = v.sum()
    if n == 0 or s <= 0:
        return 0.0
    return float((2.0 * np.arange(1, n + 1) - n - 1).dot(v) / (n * s))


def make_fixture_instance(seed: int = 0, n: int = 40, *, name: Optional[str] = None,
                          tier: str = "T0", with_rows: bool = True) -> dict:
    """Build a synthetic instance in the schema above: random planar points, Delaunay
    adjacency, lognormal A/B/M, a ratio-threshold "free_to_a" (the discrete-OT / prefix
    heuristic, CLAUDE.md's `nash_exact` alternative -- not a solver call), simple hand-
    rolled covariates, and (optionally) a couple of illustrative rows with different
    methods/statuses so producers have something to render. No networkx, no solver
    import (`territory`/`districting`/`contig_methods`)."""
    rng = np.random.default_rng(seed)
    pos = rng.uniform(0.02, 0.98, size=(n, 2))
    edges = _delaunay_edges(pos)
    theta, lam = 0.40, 0.30
    A = rng.lognormal(mean=0.0, sigma=0.6, size=n)
    B = rng.lognormal(mean=0.0, sigma=0.6, size=n)
    M = (A + theta * B) * rng.uniform(1.05, 1.6, size=n) + (B + theta * A) * 0.0
    M = np.maximum(M, np.maximum(A + theta * B, B + theta * A) * 1.01)
    nodes = [f"z{seed}_{i:03d}" for i in range(n)]

    c1, c2 = 1 - lam, theta * (1 - lam)
    ua = c1 * A + c2 * B + lam * M
    ub = c2 * A + c1 * B + lam * M
    # a ratio-threshold prefix (CLAUDE.md's fast heuristic, not a solver call): sort by
    # exchange rate, evaluate every prefix's product, keep the best -- just enough
    # structure for a plausible-looking "free Nash" fixture allocation.
    order = np.argsort(-(ua / np.where(ub > 0, ub, 1e-12)))
    ga_cum = np.cumsum(ua[order])
    gb_cum = ub.sum() - np.cumsum(ub[order])
    prod = ga_cum * np.concatenate([[ub.sum()], gb_cum[:-1]]) if n else np.array([0.0])
    k = int(np.argmax(prod)) if n else 0
    free_to_a = [nodes[i] for i in order[:k]]
    ga_free = float(ga_cum[k - 1]) if k > 0 else 0.0
    gb_free = float(ub.sum() - ub[order][:k].sum())

    comps = _connected_components(n, edges)
    articulation = 0  # not computed for the fixture; instance_card tolerates absence
    u = ua + ub
    covariates = dict(
        n=n, n_edges=len(edges), pair_components=len(comps),
        articulation_points=articulation, block_tree_is_path=len(comps) == 1,
        gini_u=_gini(u), top5_share_u=float(np.sort(u)[-5:].sum() / u.sum()) if u.sum() > 0 else 0.0,
        active_frac=float((u > 0).mean()) if n else 0.0, n_states=0,
    )

    rows = None
    if with_rows:
        half = nodes[: n // 2]
        rows = [
            dict(method="current", status="optimal", status_eff="optimal", to_a=free_to_a,
                LB=float(math.log(max(ga_free, 1e-9)) + math.log(max(gb_free, 1e-9))),
                UB=None, feasible=True, valid=True, violations=[],
                trace=[[0.01, None, None], [0.5, 1.0, 3.0], [1.2, 1.8, 1.9]]),
            dict(method="brute", status="time_limit", status_eff="time_limit", to_a=half,
                LB=None, UB=5.0, feasible=False, valid=True, violations=[],
                trace=[[0.02, None, 6.0], [1.0, None, 5.0]]),
        ]

    # `context` stand-in (U11): this fixture has no real "parent instance" the pair was
    # cut from, so the pair itself doubles as its own context -- every zip legacy-owned
    # by the same (rep_a="A0", rep_b="B0") pair, which exercises the schema and the
    # pair-context panel's overlap-fill/outline path without needing a second generator.
    context = dict(nodes=list(nodes), pos=pos.tolist(),
                   rep_a=["A0"] * n, rep_b=["B0"] * n,
                   edges=[[i, j] for i, j in edges])

    return {
        "spec": dict(name=name or f"fixture_seed{seed}_n{n}", tier=tier,
                    scenario="fixture", n=n, seed=seed, rep_a="A0", rep_b="B0",
                    params=dict(theta=theta, lam=lam)),
        "nodes": nodes,
        "pos": pos.tolist(),
        "edges": [[i, j] for i, j in edges],
        "A": A.tolist(), "B": B.tolist(), "M": M.tolist(),
        "state": None,
        "rep_a": None, "rep_b": None,
        "free_to_a": free_to_a,
        "covariates": covariates,
        "rows": rows,
        "context": context,
    }
