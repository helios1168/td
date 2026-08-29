"""
twin.py -- repo-side ingestion of the synthetic twin (PLAN.md Part C.3, unit U4).

Two independent jobs:

1.  Build and cache a national ZCTA Rook-adjacency graph from public TIGER geometry.
    `fetch_tiger()` downloads TIGER2020 ZCTA5 once; `build_rook_adjacency(shp)` computes
    the graph (geopandas/shapely only used here -- nowhere else in this module); the
    result is cached to `data/zcta_adjacency.npz` with `save_adjacency`/`load_adjacency`,
    numpy-only so the fast test suite never imports the geo stack.

2.  Load a twin instance (`twin_instance.json.gz`, produced on the work machine by
    `tools/twin_export/`, PLAN.md C.2) into the repo's networkx graph schema
    (`rep_a, rep_b, A, B, M, state, pos`), cross-checking its edge list against the
    cached TIGER adjacency (`edge_diff`, Jaccard >= 0.999) and selecting bilateral pairs
    for the T3a instance tier (`twin_pairs`).

U3 (the work-machine export) has not landed yet, so `make_standin_twin` builds a small
*locally fabricated* twin -- real ZCTA ids and real edges from the cached adjacency (a
connected region grown by BFS), synthetic A/B/M/rep maps -- so this module and its tests
do not block on U3.  It is not privacy-audited data and must never be treated as a twin
instance for anything beyond testing this loader.

CRS note: internal points (INTPTLON20/INTPTLAT20) are reprojected from TIGER's native
NAD83 (EPSG:4269) to EPSG:2163 ("US National Atlas Equal Area", a Lambert Azimuthal
Equal-Area projection centered at lat_0=45, lon_0=-100 on a sphere -- exactly the
`+proj=laea +lat_0=45 +lon_0=-100` form PLAN.md names) and then rescaled into [0, 1]^2
with aspect preserved (one axis fills [0, 1], the other is <= 1).  National scope pulls
Alaska/Hawaii/Puerto Rico into the same frame as CONUS, so the rescaled positions are a
correct equal-area embedding but not a pleasing one; that is a graphics-layer concern
(PLAN.md Part D / U7), not this module's.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import time

import numpy as np
import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for _p in (os.path.join(ROOT, "code"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import territory as T  # noqa: E402  -- read-only; territory.validate/census/zips_for_pair

TIGER_URL = "https://www2.census.gov/geo/tiger/TIGER2020/ZCTA520/tl_2020_us_zcta520.zip"
TIGER_VINTAGE = "2020"
TIGER_SHP_NAME = "tl_2020_us_zcta520.shp"
TIGER_ZIP_NAME = "tl_2020_us_zcta520.zip"
TIGER_ZIP_MIN_BYTES = 400_000_000       # the download is ~528 MB; guard a truncated fetch
LAEA_CRS = "EPSG:2163"                  # +proj=laea +lat_0=45 +lon_0=-100 +ellps=sphere
ADJACENCY_DEFAULT = os.path.join(ROOT, "data", "zcta_adjacency.npz")


# ------------------------------------------------------------------------- TIGER fetch
def fetch_tiger(dest: str = os.path.join(ROOT, "data", "tiger"), *, url: str = TIGER_URL,
                verbose: bool = True) -> str:
    """Download TIGER2020 ZCTA5 to `dest` (gitignored) unless already present; return
    the path to the extracted .shp.  Verifies the zip size and, on read, the
    `ZCTA5CE20` column.  Raises on network failure rather than trying a mirror."""
    os.makedirs(dest, exist_ok=True)
    shp_path = os.path.join(dest, TIGER_SHP_NAME)
    zip_path = os.path.join(dest, TIGER_ZIP_NAME)
    if os.path.exists(shp_path):
        if verbose:
            print(f"fetch_tiger: {shp_path} already present, skipping download")
        return shp_path
    if not os.path.exists(zip_path):
        import urllib.request
        if verbose:
            print(f"fetch_tiger: downloading {url} -> {zip_path}")
        try:
            urllib.request.urlretrieve(url, zip_path)
        except Exception as e:
            raise RuntimeError(f"fetch_tiger: download failed ({type(e).__name__}: {e}); "
                               "no mirror is configured, stop and report") from e
    size = os.path.getsize(zip_path)
    if size < TIGER_ZIP_MIN_BYTES:
        raise RuntimeError(f"fetch_tiger: {zip_path} is only {size} bytes "
                           f"(expected >= {TIGER_ZIP_MIN_BYTES}); truncated download")
    import zipfile
    if verbose:
        print(f"fetch_tiger: extracting {zip_path} -> {dest}")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    if not os.path.exists(shp_path):
        raise RuntimeError(f"fetch_tiger: {shp_path} missing after extraction")
    return shp_path


# --------------------------------------------------------------- Rook adjacency build
def build_rook_adjacency(shp: str, *, verbose: bool = True) -> dict:
    """Rook adjacency (shared-boundary length > 0) over every ZCTA in `shp`.

    geopandas/shapely/pyproj are imported only inside this function.  Returns a dict of
    plain numpy arrays plus `meta`:
        zcta   (n,) '<U5'    ZCTA5 ids, ascending sort order
        edges  (m,2) int32   index pairs into `zcta` (i < j)
        lon,lat(n,) float32  internal point (INTPTLON20/LAT20), degrees
        x,y    (n,) float32  internal point reprojected to EPSG:2163, rescaled to [0,1]^2
        meta   dict          vintage, build date, crs, n, m, build_seconds
    """
    import geopandas as gpd
    import shapely
    from pyproj import Transformer

    t0 = time.perf_counter()
    if verbose:
        print(f"build_rook_adjacency: reading {shp}")
    gdf = gpd.read_file(shp, columns=["ZCTA5CE20", "INTPTLAT20", "INTPTLON20", "geometry"])
    if "ZCTA5CE20" not in gdf.columns:
        raise RuntimeError(f"build_rook_adjacency: {shp} has no ZCTA5CE20 column "
                           f"(got {list(gdf.columns)})")
    gdf = gdf.sort_values("ZCTA5CE20").reset_index(drop=True)
    n = len(gdf)
    zcta = gdf["ZCTA5CE20"].to_numpy(dtype="<U5")
    lon = gdf["INTPTLON20"].astype(float).to_numpy(dtype=np.float32)
    lat = gdf["INTPTLAT20"].astype(float).to_numpy(dtype=np.float32)
    if verbose:
        print(f"build_rook_adjacency: {n} ZCTAs read ({time.perf_counter()-t0:.1f}s); "
              "querying spatial index for candidate boundary pairs")

    geoms = gdf.geometry.to_numpy()
    idx_a, idx_b = gdf.sindex.query(gdf.geometry, predicate="intersects")
    keep = idx_a < idx_b                # drop self-matches and the mirrored (j, i) half
    idx_a, idx_b = idx_a[keep], idx_b[keep]
    if verbose:
        print(f"build_rook_adjacency: {len(idx_a)} candidate pairs "
              f"({time.perf_counter()-t0:.1f}s); computing shared-boundary length "
              "(vectorised shapely 2.x)")

    CHUNK = 200_000                     # bound peak memory on the intersection buffers
    rook_a, rook_b = [], []
    for s in range(0, len(idx_a), CHUNK):
        ia = idx_a[s:s + CHUNK]
        ib = idx_b[s:s + CHUNK]
        inter = shapely.intersection(geoms[ia], geoms[ib])
        length = shapely.length(inter)
        rook = length > 0
        rook_a.append(ia[rook])
        rook_b.append(ib[rook])
        if verbose:
            print(f"  ... {min(s+CHUNK, len(idx_a))}/{len(idx_a)} candidates "
                  f"({time.perf_counter()-t0:.1f}s)")
    edges = np.stack([np.concatenate(rook_a), np.concatenate(rook_b)], axis=1).astype(np.int32)
    m = len(edges)
    if verbose:
        print(f"build_rook_adjacency: {m} rook edges ({time.perf_counter()-t0:.1f}s); "
              f"reprojecting internal points to {LAEA_CRS}")

    transformer = Transformer.from_crs(gdf.crs, LAEA_CRS, always_xy=True)
    xr, yr = transformer.transform(lon.astype(float), lat.astype(float))
    xr, yr = np.asarray(xr), np.asarray(yr)
    scale = max(xr.max() - xr.min(), yr.max() - yr.min())
    x = ((xr - xr.min()) / scale).astype(np.float32)
    y = ((yr - yr.min()) / scale).astype(np.float32)

    build_seconds = time.perf_counter() - t0
    meta = dict(vintage=TIGER_VINTAGE, build_date=time.strftime("%Y-%m-%d"),
               crs=LAEA_CRS, source_crs=str(gdf.crs), n=int(n), m=int(m),
               build_seconds=round(build_seconds, 1))
    if verbose:
        print(f"build_rook_adjacency: done, n={n} m={m} in {build_seconds:.1f}s")
    return dict(zcta=zcta, edges=edges, lon=lon, lat=lat, x=x, y=y, meta=meta)


def save_adjacency(data: dict, path: str = ADJACENCY_DEFAULT) -> str:
    """Write `build_rook_adjacency`'s dict to a numpy-only .npz (no pickling)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    meta_json = np.array([json.dumps(data["meta"])], dtype="<U8000")
    np.savez_compressed(path, zcta=data["zcta"], edges=data["edges"].astype(np.int32),
                        lon=data["lon"].astype(np.float32), lat=data["lat"].astype(np.float32),
                        x=data["x"].astype(np.float32), y=data["y"].astype(np.float32),
                        meta_json=meta_json)
    return path


def load_adjacency(path: str = ADJACENCY_DEFAULT) -> dict:
    """Load the cached adjacency.  numpy only -- no geopandas/shapely import."""
    with np.load(path, allow_pickle=False) as z:
        out = dict(zcta=z["zcta"], edges=z["edges"], lon=z["lon"], lat=z["lat"],
                   x=z["x"], y=z["y"], meta=json.loads(str(z["meta_json"][0])))
    return out


# --------------------------------------------------------------------------- edge_diff
def edge_diff(edges_a, edges_b, *, cap: int = 20, label_a: str = "a", label_b: str = "b",
             verbose: bool = True) -> dict:
    """Jaccard similarity of two edge lists (each an iterable of 2-tuples of node ids,
    any hashable/orderable type).  Prints up to `cap` differing edges per side.
    Returns dict(jaccard, only_a, only_b, n_a, n_b, n_intersection, n_union)."""
    a = {tuple(sorted((str(u), str(v)))) for u, v in edges_a}
    b = {tuple(sorted((str(u), str(v)))) for u, v in edges_b}
    inter = a & b
    union = a | b
    jaccard = (len(inter) / len(union)) if union else 1.0
    only_a = sorted(a - b)
    only_b = sorted(b - a)
    if verbose and (only_a or only_b):
        print(f"edge_diff: jaccard={jaccard:.6f}  |{label_a}|={len(a)}  |{label_b}|={len(b)}  "
              f"only_in_{label_a}={len(only_a)}  only_in_{label_b}={len(only_b)}")
        for e in only_a[:cap]:
            print(f"  - only in {label_a}: {e}")
        for e in only_b[:cap]:
            print(f"  - only in {label_b}: {e}")
    return dict(jaccard=jaccard, only_a=only_a, only_b=only_b,
               n_a=len(a), n_b=len(b), n_intersection=len(inter), n_union=len(union))


# ----------------------------------------------------------------------------- loader
def load_twin(path: str, *, check_edges: bool = True, adjacency: str = ADJACENCY_DEFAULT,
             jaccard_min: float = 0.999) -> nx.Graph:
    """Load a `twin_instance.json.gz` (PLAN.md C.2) into the repo's graph schema.

    Cross-checks the twin's edge list against the cached TIGER adjacency restricted to
    the twin's own ZCTA set (`edge_diff`), asserting Jaccard >= `jaccard_min`, unless
    `check_edges=False` or the cache is absent.  Runs `territory.validate` and asserts
    it returns [].  Sets `G.graph["twin"]=True`, `G.graph["meta"]=meta`.
    """
    with gzip.open(path, "rt") as f:
        obj = json.load(f)
    meta = obj["meta"]
    nodes = obj["nodes"]
    edges = obj["edges"]

    z = [str(v) for v in nodes["z"]]
    G = nx.Graph()
    for i, zid in enumerate(z):
        attrs = dict(rep_a=nodes["rep_a"][i], rep_b=nodes["rep_b"][i],
                    A=float(nodes["A"][i]), B=float(nodes["B"][i]), M=float(nodes["M"][i]))
        state = nodes.get("state")
        if state is not None:
            attrs["state"] = state[i]
        G.add_node(zid, **attrs)
    edge_pairs = [(str(u), str(v)) for u, v in zip(edges["u"], edges["v"])]
    G.add_edges_from(edge_pairs)

    if os.path.exists(adjacency):
        adj = load_adjacency(adjacency)
        pos_idx = {zz: k for k, zz in enumerate(adj["zcta"])}
        for zid in G.nodes:
            k = pos_idx.get(zid)
            if k is not None:
                G.nodes[zid]["pos"] = (float(adj["x"][k]), float(adj["y"][k]))
        if check_edges:
            twin_set = set(G.nodes)
            cached_edges = [(adj["zcta"][a], adj["zcta"][b]) for a, b in adj["edges"]
                            if adj["zcta"][a] in twin_set and adj["zcta"][b] in twin_set]
            d = edge_diff(edge_pairs, cached_edges, label_a="twin", label_b="cached_adjacency")
            assert d["jaccard"] >= jaccard_min, (
                f"load_twin: edge_diff jaccard {d['jaccard']:.6f} < {jaccard_min} against "
                f"{adjacency} -- twin edge list does not match the cached TIGER adjacency")
    elif check_edges:
        print(f"load_twin: WARNING adjacency cache {adjacency} not found, skipping edge_diff")

    G.graph["twin"] = True
    G.graph["meta"] = meta
    problems = T.validate(G)
    assert problems == [], f"load_twin: territory.validate failed: {problems}"
    return G


# --------------------------------------------------------------------------- twin_pairs
def twin_pairs(G: nx.Graph, *, min_share: float = 0.02, bands=(200, 400, 800),
              per_band: int = 2, largest: int = 4) -> list:
    """1-1 bilateral pairs for the T3a instance tier: `per_band` pairs nearest each of
    `bands` (by zip count) plus the `largest` largest pairs overall, deduplicated,
    sorted by n ascending.  Deterministic given (G, min_share, bands, per_band, largest).
    """
    rows = T.census(G, min_share=min_share)
    pairs = []
    for r in rows:
        if r["shape"] != "1-1 pair":
            continue
        rep_a = r["reps_a"][0][1]
        rep_b = r["reps_b"][0][1]
        n = len(T.zips_for_pair(G, rep_a, rep_b))
        pairs.append(dict(rep_a=rep_a, rep_b=rep_b, n=n))
    pairs.sort(key=lambda p: (-p["n"], str(p["rep_a"]), str(p["rep_b"])))

    chosen, seen = [], set()

    def _take(p):
        key = (p["rep_a"], p["rep_b"])
        if key in seen:
            return False
        seen.add(key)
        chosen.append(p)
        return True

    for p in pairs[:largest]:
        _take(p)
    for b in bands:
        cand = sorted(pairs, key=lambda p: (abs(p["n"] - b), str(p["rep_a"]), str(p["rep_b"])))
        picked = 0
        for p in cand:
            if (p["rep_a"], p["rep_b"]) in seen:
                continue
            if _take(p):
                picked += 1
            if picked >= per_band:
                break

    for p in chosen:
        p["name"] = f"twin_{p['rep_a']}_{p['rep_b']}_n{p['n']}"
    chosen.sort(key=lambda p: (p["n"], str(p["rep_a"]), str(p["rep_b"])))
    return chosen


# ---------------------------------------------------------- stand-in twin (U3 not landed)
def _bfs_region(adj_nodes_neighbors: dict, start: int, n: int) -> list:
    """Deterministic BFS out to `n` nodes (sorted-neighbour order, so it only depends on
    `start` and the graph, not on dict/set iteration order)."""
    seen = {start}
    order = [start]
    frontier = [start]
    while frontier and len(order) < n:
        nxt = set()
        for u in frontier:
            for v in sorted(adj_nodes_neighbors.get(u, ())):
                if v not in seen:
                    seen.add(v)
                    nxt.add(v)
        frontier = sorted(nxt)
        for v in frontier:
            if len(order) >= n:
                break
            order.append(v)
    return order[:n]


def _multi_source_labels(neighbors: dict, region: list, seeds: list) -> dict:
    """Multi-source BFS Voronoi: label every node in `region` by the seed that reaches
    it first (ties -> lowest seed index), restricted to `region`."""
    region_set = set(region)
    label = {s: i for i, s in enumerate(seeds)}
    frontier = list(seeds)
    while frontier:
        nxt = []
        for u in frontier:
            for v in sorted(neighbors.get(u, ())):
                if v in region_set and v not in label:
                    label[v] = label[u]
                    nxt.append(v)
        frontier = sorted(nxt)
    # anything unreached (shouldn't happen on a connected region) gets seed 0
    for z in region:
        label.setdefault(z, 0)
    return label


def _graph_hash(zids: list, edges: list) -> str:
    h = hashlib.sha256()
    h.update("|".join(sorted(zids)).encode())
    h.update(b"#")
    h.update("|".join(f"{min(u, v)}-{max(u, v)}" for u, v in
                      sorted((str(a), str(b)) for a, b in edges)).encode())
    return h.hexdigest()[:16]


def make_standin_twin(*, n: int = 2000, seed: int = 0, adjacency: str = ADJACENCY_DEFAULT,
                      theta: float = 0.40, n_rep_a: int = 6, n_rep_b: int = 6,
                      alpha: float = 0.5, out: str | None = None) -> dict | str:
    """A locally-fabricated stand-in for `twin_instance.json.gz` (PLAN.md C.2), so U4's
    loader and tests do not block on U3.  Real ZCTA ids and real edges (a connected
    region of `n` ZCTAs grown by BFS from a seed-derived start in the cached TIGER
    adjacency); synthetic A, B, M (lognormal, headroom-repaired to
    M >= max(A+theta*B, B+theta*A)) and rep_a/rep_b (multi-source BFS Voronoi seeded
    within the region).  NOT privacy-audited data -- test fixture only.

    Returns the twin dict; if `out` is given, also writes it gzipped JSON there and
    returns `out`.
    """
    adj = load_adjacency(adjacency)
    zcta = adj["zcta"]
    edges = adj["edges"]
    n_total = len(zcta)
    if n > n_total:
        raise ValueError(f"make_standin_twin: n={n} exceeds the cached adjacency ({n_total} ZCTAs)")

    neighbors: dict = {}
    for a, b in edges:
        a, b = int(a), int(b)
        neighbors.setdefault(a, []).append(b)
        neighbors.setdefault(b, []).append(a)

    rng = np.random.default_rng(seed)
    start = int(rng.integers(0, n_total))
    region = _bfs_region(neighbors, start, n)
    if len(region) < n:
        raise RuntimeError(f"make_standin_twin: BFS from index {start} only reached "
                           f"{len(region)} < {n} ZCTAs (adjacency may be disconnected there)")
    region_sorted = sorted(region)                     # index-space region, ascending
    zids = [str(zcta[i]) for i in region_sorted]
    region_set = set(region_sorted)
    region_edges = [(int(a), int(b)) for a, b in edges
                    if int(a) in region_set and int(b) in region_set]

    # --- rep maps: multi-source BFS Voronoi, independently seeded for A and B
    rng_a, rng_b, rng_v, rng_s = (np.random.default_rng([seed, i]) for i in (1, 2, 3, 4))
    order = list(region_sorted)
    rng_a.shuffle(order)
    seeds_a = order[:n_rep_a]
    seeds_b = []
    pool = [z for z in order if z not in seeds_a]
    for i in range(n_rep_b):
        if rng_b.random() < alpha and seeds_a:
            # random-walk a few hops from one of A's seeds (spec: "4 hops")
            u = seeds_a[i % len(seeds_a)]
            for _ in range(4):
                nbrs = [v for v in neighbors.get(u, ()) if v in region_set]
                if not nbrs:
                    break
                u = nbrs[int(rng_b.integers(0, len(nbrs)))]
            seeds_b.append(u)
        elif pool:
            seeds_b.append(pool.pop(int(rng_b.integers(0, len(pool)))))
        else:
            seeds_b.append(order[int(rng_b.integers(0, len(order)))])

    label_a = _multi_source_labels(neighbors, region_sorted, seeds_a)
    label_b = _multi_source_labels(neighbors, region_sorted, seeds_b)
    rep_a = [f"A{label_a[z]}" for z in region_sorted]
    rep_b = [f"B{label_b[z]}" for z in region_sorted]

    # --- synthetic values: lognormal A, B; M repaired to satisfy net headroom
    A = rng_v.lognormal(mean=1.0, sigma=0.8, size=len(region_sorted))
    B = rng_v.lognormal(mean=1.0, sigma=0.8, size=len(region_sorted))
    m_min = np.maximum(A + theta * B, B + theta * A)
    slack = rng_v.uniform(0.10, 1.00, size=len(region_sorted))
    M = m_min * (1.0 + slack)

    # --- synthetic state: coarse geographic grid over the cached x, y (placeholder --
    # the real twin carries actual state membership; this is a test fixture only)
    x = adj["x"][region_sorted]
    y = adj["y"][region_sorted]
    gx = np.clip((3 * (x - x.min()) / max(x.max() - x.min(), 1e-9)).astype(int), 0, 2)
    gy = np.clip((2 * (y - y.min()) / max(y.max() - y.min(), 1e-9)).astype(int), 0, 1)
    states = [f"S{gxi*2+gyi}" for gxi, gyi in zip(gx, gy)]

    meta = dict(seed=seed, rank_sigma=0.10, coarsen=None, swap_rounds=0, alpha=alpha,
               n_rep_a=n_rep_a, n_rep_b=n_rep_b, theta=theta,
               graph_hash=_graph_hash(zids, region_edges), tiger_vintage=TIGER_VINTAGE,
               standin=True)
    nodes = dict(z=zids, state=states, A=A.tolist(), B=B.tolist(), M=M.tolist(),
                rep_a=rep_a, rep_b=rep_b)
    idx_of = {i: k for k, i in enumerate(region_sorted)}
    edges_out = dict(u=[zids[idx_of[a]] for a, b in region_edges],
                     v=[zids[idx_of[b]] for a, b in region_edges])
    audit = dict(note="make_standin_twin: locally fabricated test fixture, not "
                      "privacy-audited data; see twin.py docstring")
    obj = dict(meta=meta, nodes=nodes, edges=edges_out, audit=audit)

    if out is not None:
        os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
        with gzip.open(out, "wt") as f:
            json.dump(obj, f)
        return out
    return obj


# ------------------------------------------------------------------------------- CLI
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cmd", choices=["fetch", "build", "standin"])
    p.add_argument("--dest", default=os.path.join(ROOT, "data", "tiger"))
    p.add_argument("--out", default=ADJACENCY_DEFAULT)
    p.add_argument("--n", type=int, default=2000)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args()
    if args.cmd == "fetch":
        print(fetch_tiger(args.dest))
    elif args.cmd == "build":
        shp = fetch_tiger(args.dest)
        data = build_rook_adjacency(shp)
        save_adjacency(data, args.out)
        print(f"wrote {args.out} ({os.path.getsize(args.out)} bytes)")
    elif args.cmd == "standin":
        path = make_standin_twin(n=args.n, seed=args.seed, out="/tmp/twin_standin.json.gz")
        print(path)
