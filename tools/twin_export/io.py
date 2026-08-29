"""io.py -- reading the confidential inputs, and the two guarded writers.

Nothing here knows anything about the repo.  Graph readers cover, in order of preference:

    *.parquet / *.pq / *.feather / *.arrow   a cached edge table (the work-machine format:
                                             "networkx pyarrow cache, ZCTA 2025 vintage")
    *.csv / *.txt / *.tsv                    a two-column edge list
    *.gpickle / *.pkl                        a pickled networkx graph
    *.graphml / *.gml                        networkx's own formats
    *.npz                                    the repo's zcta_adjacency.npz layout
    --build-rook-from SHAPEFILE              geopandas, only if the user asks for it

Every ZCTA id is normalised with `zfill(5)` the moment it is read, so a source that dropped
leading zeros (00501 -> 501, the classic parquet/CSV integer-cast) still joins.

Two writers, two rule sets, no shared code path:

    write_json_guarded  ->  twin_stats.json   paranoid: k-anon already done upstream, plus
                            a list-length cap, a 5-digit-string veto, and 6-sig-fig rounding
    write_twin          ->  twin_instance.json.gz  a schema whitelist: exactly the keys
                            PLAN.md C.2 names, nothing else, reps asserted integer
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import re
import sys

import numpy as np
import networkx as nx

from .agg import LeakGuardError

ID_RE = re.compile(r"^\d{5}$")
STATE_KEYS = ("state", "STATE", "state_abbr", "STUSPS", "usps", "stusps")
COORD_KEYS = {"lon": ("lon", "longitude", "x", "INTPTLON", "INTPTLON20", "intptlon"),
              "lat": ("lat", "latitude", "y", "INTPTLAT", "INTPTLAT20", "intptlat")}
U_NAMES = ("u", "src", "source", "zcta_a", "a", "from", "node1", "zcta1")
V_NAMES = ("v", "dst", "target", "zcta_b", "b", "to", "node2", "zcta2")


class InputError(Exception):
    """A confidential input could not be read or joined; the CLI exits 4."""


# ---------------------------------------------------------------------------- ids
def normalize_id(x):
    """'501' -> '00501'; 501 -> '00501'; ' 00501 ' -> '00501'.  Longer ids pass through."""
    s = str(x).strip()
    if s.endswith(".0") and s[:-2].isdigit():        # float round-trip through parquet
        s = s[:-2]
    return s.zfill(5)


def normalize_ids(seq):
    return [normalize_id(x) for x in seq]


# ------------------------------------------------------------------------- hashes
def graph_hash(z, edges):
    """sha256 over the sorted ZCTA-string edge list (PLAN.md C.2 `meta.graph_hash`)."""
    lines = sorted("%s,%s" % (min(str(u), str(v)), max(str(u), str(v))) for u, v in edges)
    h = hashlib.sha256("\n".join(lines).encode("utf-8"))
    return h.hexdigest()


def file_sha256(path, cap=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


# -------------------------------------------------------------------- table reads
def _read_delimited(path):
    """Header + rows from a csv/tsv/txt, without pandas."""
    import csv
    delim = "\t" if path.endswith((".tsv", ".tab")) else ","
    with open(path, "r", newline="") as f:
        sample = f.readline()
        f.seek(0)
        if delim not in sample and " " in sample:
            rows = [ln.split() for ln in f if ln.strip()]
        else:
            rows = list(csv.reader(f, delimiter=delim))
    if not rows:
        raise InputError("%s is empty" % path)
    return rows


def _read_arrow(path):
    """Columnar file -> dict of column name -> list.  pyarrow first, then pandas."""
    ext = os.path.splitext(path)[1].lower()
    try:
        import pyarrow  # noqa: F401
        if ext in (".feather", ".arrow", ".ipc"):
            import pyarrow.feather as pf
            tbl = pf.read_table(path)
        else:
            import pyarrow.parquet as pq
            tbl = pq.read_table(path)
        return dict((str(nm), tbl.column(nm).to_pylist()) for nm in tbl.column_names)
    except ImportError:
        pass
    try:
        import pandas as pd
    except ImportError:
        raise InputError(
            "reading %s needs pyarrow (preferred) or pandas with a parquet engine; neither "
            "imported.  `pip install pyarrow`, or re-export the edge table as a two-column "
            "CSV and pass that instead (twin_export reads plain edge lists)." % path)
    try:
        df = pd.read_feather(path) if ext in (".feather", ".arrow", ".ipc") else pd.read_parquet(path)
    except Exception as e:
        raise InputError(
            "pandas could not read %s (%s: %s).  Install pyarrow, or re-export the edge "
            "table as a two-column CSV." % (path, type(e).__name__, e))
    return dict((str(c), df[c].tolist()) for c in df.columns)


def read_table(path, cols, id_col="zcta"):
    """Read a `zcta, <cols...>` table into dict(zcta -> tuple(values)).

    Accepts csv/tsv/txt and parquet/feather.  `cols` are matched case-insensitively; the id
    column is matched against `id_col` or falls back to the first column.
    """
    if not os.path.exists(path):
        raise InputError("no such file: %s" % path)
    ext = os.path.splitext(path)[1].lower()
    if ext in (".parquet", ".pq", ".feather", ".arrow", ".ipc"):
        table = _read_arrow(path)
        lower = dict((k.lower(), k) for k in table)
        idk = lower.get(str(id_col).lower(), list(table)[0])
        keys = []
        for c in cols:
            if c.lower() not in lower:
                raise InputError("%s has no column %r (columns: %s)"
                                 % (path, c, ", ".join(table)))
            keys.append(lower[c.lower()])
        ids = normalize_ids(table[idk])
        vals = [table[k] for k in keys]
        return dict((z, tuple(v[i] for v in vals)) for i, z in enumerate(ids))

    rows = _read_delimited(path)
    header = [str(h).strip() for h in rows[0]]
    lower = dict((h.lower(), i) for i, h in enumerate(header))
    has_header = any(c.lower() in lower for c in cols)
    if not has_header:
        raise InputError("%s: expected a header row containing %s (got %s)"
                         % (path, ", ".join(cols), ", ".join(header[:6])))
    idx_id = lower.get(str(id_col).lower(), 0)
    idx = []
    for c in cols:
        if c.lower() not in lower:
            raise InputError("%s has no column %r (columns: %s)"
                             % (path, c, ", ".join(header)))
        idx.append(lower[c.lower()])
    out = {}
    for r in rows[1:]:
        if not r or len(r) <= max(idx + [idx_id]):
            continue
        out[normalize_id(r[idx_id])] = tuple(r[i] for i in idx)
    if not out:
        raise InputError("%s has a header but no data rows" % path)
    return out


# -------------------------------------------------------------------- graph reads
def _edges_from_columns(table, u_col=None, v_col=None, path=""):
    lower = dict((k.lower(), k) for k in table)
    if u_col and v_col:
        if u_col not in table or v_col not in table:
            raise InputError("%s has no columns %r/%r (columns: %s)"
                             % (path, u_col, v_col, ", ".join(table)))
        uk, vk = u_col, v_col
    else:
        uk = vk = None
        for a, b in zip(U_NAMES, V_NAMES):
            if a in lower and b in lower:
                uk, vk = lower[a], lower[b]
                break
        if uk is None:
            names = list(table)
            if len(names) < 2:
                raise InputError("%s needs at least two columns to be an edge table "
                                 "(columns: %s)" % (path, ", ".join(names)))
            uk, vk = names[0], names[1]
    return normalize_ids(table[uk]), normalize_ids(table[vk]), (uk, vk)


def read_graph(path, states=None, id_col=None, fmt=None, u_col=None, v_col=None,
               build_rook_from=None, verbose=True):
    """Load the ZCTA adjacency graph.  Returns (nx.Graph, report dict).

    Every node attribute is stripped except a `state`-like key and (for the W11 territory
    radius only) lon/lat.  Nothing else from the source graph is ever looked at, so a
    pickled graph carrying confidential per-ZCTA payload cannot leak through it.
    """
    report = dict(source=None, format=None, n=0, m=0, columns=None, stripped=[])

    if build_rook_from:
        G = _rook_from_shapefile(build_rook_from, verbose=verbose)
        report.update(source=build_rook_from, format="shapefile-rook")
    else:
        if not os.path.exists(path):
            raise InputError("no such file: %s" % path)
        ext = (fmt or os.path.splitext(path)[1].lstrip(".")).lower()
        report.update(source=path, format=ext)
        if ext in ("parquet", "pq", "feather", "arrow", "ipc"):
            table = _read_arrow(path)
            us, vs, cols = _edges_from_columns(table, u_col, v_col, path)
            report["columns"] = list(cols)
            G = nx.Graph()
            G.add_edges_from(zip(us, vs))
            # a node column, if the cache carries one, keeps isolated ZCTAs alive
            lower = dict((k.lower(), k) for k in table)
            for cand in ("zcta", "node", "id"):
                if cand in lower:
                    G.add_nodes_from(normalize_ids(table[lower[cand]]))
                    break
        elif ext in ("csv", "txt", "tsv", "tab"):
            rows = _read_delimited(path)
            head = [str(h).strip().lower() for h in rows[0]]
            start = 1 if (head[0] in U_NAMES or head[0] in ("zcta", "zcta5")) else 0
            G = nx.Graph()
            for r in rows[start:]:
                if len(r) >= 2 and str(r[0]).strip():
                    G.add_edge(normalize_id(r[0]), normalize_id(r[1]))
        elif ext in ("gpickle", "pkl", "pickle"):
            G = _read_pickle_graph(path)
        elif ext in ("graphml", "gml"):
            G = nx.read_graphml(path) if ext == "graphml" else nx.read_gml(path)
            G = nx.relabel_nodes(nx.Graph(G), normalize_id)
        elif ext == "npz":
            G = _read_npz_graph(path)
        else:
            raise InputError(
                "unknown graph format %r for %s.  Supported: .parquet/.feather (an edge "
                "table cached from networkx -- the expected work-machine format), .csv "
                "edge list, .gpickle/.pkl, .graphml/.gml, .npz, or --build-rook-from a "
                "shapefile.  Override with --graph-format." % (ext, path))

    G = nx.Graph(G)
    G = nx.relabel_nodes(G, normalize_id, copy=True)
    G.remove_edges_from(nx.selfloop_edges(G))

    # --- attribute strip (whitelist) --------------------------------------------
    stripped = set()
    for n in G.nodes:
        d = G.nodes[n]
        keep = {}
        for k in list(d):
            if k in STATE_KEYS:
                keep["state"] = str(d[k]).strip()
            elif k in COORD_KEYS["lon"]:
                keep["lon"] = _as_float(d[k])
            elif k in COORD_KEYS["lat"]:
                keep["lat"] = _as_float(d[k])
            else:
                stripped.add(k)
            del d[k]
        d.update(keep)
    for u, v in G.edges:
        G.edges[u, v].clear()
    report["stripped"] = sorted(stripped)

    if states:
        st = read_table(states, ["state"], id_col=id_col or "zcta")
        miss = 0
        for n in G.nodes:
            row = st.get(n)
            if row is None:
                miss += 1
            else:
                G.nodes[n]["state"] = str(row[0]).strip()
        report["state_missing"] = miss
    report.update(n=G.number_of_nodes(), m=G.number_of_edges())
    if verbose:
        print("read_graph: %s  n=%d m=%d  format=%s%s"
              % (path or build_rook_from, report["n"], report["m"], report["format"],
                 ("  columns=%s" % report["columns"]) if report["columns"] else ""))
        if report["stripped"]:
            print("read_graph: stripped %d non-whitelisted node attributes: %s"
                  % (len(report["stripped"]), ", ".join(report["stripped"][:12])))
    return G, report


def _as_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def _read_pickle_graph(path):
    """networkx >= 3 removed read_gpickle; unpickle by hand and say so on failure."""
    import pickle
    try:
        with open(path, "rb") as f:
            obj = pickle.load(f)
    except Exception as e:
        raise InputError(
            "could not unpickle %s (%s: %s).  A pickle only loads under the same "
            "networkx/numpy it was written with -- the reliable escape hatch is to export "
            "the edge list once, in the session that has the graph:\n"
            "    import pandas as pd\n"
            "    pd.DataFrame(list(G.edges()), columns=['u','v']).to_parquet('edges.parquet')\n"
            "and pass --graph edges.parquet." % (path, type(e).__name__, e))
    if not isinstance(obj, nx.Graph):
        raise InputError("%s unpickled to %s, not a networkx graph" % (path, type(obj).__name__))
    return obj


def _read_npz_graph(path):
    with np.load(path, allow_pickle=False) as z:
        zcta = [str(s) for s in z["zcta"]]
        edges = z["edges"]
        G = nx.Graph()
        G.add_nodes_from(zcta)
        G.add_edges_from((zcta[int(a)], zcta[int(b)]) for a, b in edges)
        if "lon" in z and "lat" in z:
            for i, zz in enumerate(zcta):
                G.nodes[zz]["lon"] = float(z["lon"][i])
                G.nodes[zz]["lat"] = float(z["lat"][i])
    return G


def _rook_from_shapefile(shp, verbose=True):
    """Rook adjacency from polygon geometry.  geopandas/shapely imported here only."""
    try:
        import geopandas as gpd
        import shapely
    except ImportError:
        raise InputError("--build-rook-from needs geopandas and shapely installed")
    if verbose:
        print("read_graph: building Rook adjacency from %s (geopandas)" % shp)
    gdf = gpd.read_file(shp)
    idcol = None
    for c in gdf.columns:
        if c.upper().startswith("ZCTA5CE") or c.lower() in ("zcta", "zcta5", "geoid"):
            idcol = c
            break
    if idcol is None:
        raise InputError("%s has no ZCTA id column (columns: %s)" % (shp, list(gdf.columns)))
    gdf = gdf.sort_values(idcol).reset_index(drop=True)
    ids = normalize_ids(gdf[idcol].tolist())
    geoms = gdf.geometry.to_numpy()
    ia, ib = gdf.sindex.query(gdf.geometry, predicate="intersects")
    keep = ia < ib
    ia, ib = ia[keep], ib[keep]
    G = nx.Graph()
    G.add_nodes_from(ids)
    CH = 200000
    for s in range(0, len(ia), CH):
        a, b = ia[s:s + CH], ib[s:s + CH]
        ln = shapely.length(shapely.intersection(geoms[a], geoms[b]))
        for i, j in zip(a[ln > 0], b[ln > 0]):
            G.add_edge(ids[int(i)], ids[int(j)])
    try:
        pts = gdf.geometry.representative_point()
        ll = gpd.GeoSeries(pts, crs=gdf.crs).to_crs("EPSG:4326")
        for i, zz in enumerate(ids):
            G.nodes[zz]["lon"] = float(ll.iloc[i].x)
            G.nodes[zz]["lat"] = float(ll.iloc[i].y)
    except Exception:
        pass
    return G


# ------------------------------------------------------------------------ instance
class Instance(object):
    """The joined confidential instance, relabelled to 0..n-1 in ascending ZCTA order.

    Rep names are mapped to integers at load and the name maps stay on this object; the twin
    writer asserts the reps it writes are integers, so a rep's real name cannot leave.
    """

    def __init__(self, G, z, state, M, A, B, rep_a, rep_b,
                 rep_a_names=None, rep_b_names=None, lon=None, lat=None):
        self.G = G
        self.z = list(z)
        self.n = len(self.z)
        self.state = list(state) if state is not None else None
        self.M = np.asarray(M, dtype=float)
        self.A = np.asarray(A, dtype=float)
        self.B = np.asarray(B, dtype=float)
        self.rep_a = np.asarray(rep_a, dtype=np.int64)
        self.rep_b = np.asarray(rep_b, dtype=np.int64)
        self.rep_a_names = list(rep_a_names) if rep_a_names is not None else None
        self.rep_b_names = list(rep_b_names) if rep_b_names is not None else None
        self.lon = None if lon is None else np.asarray(lon, dtype=float)
        self.lat = None if lat is None else np.asarray(lat, dtype=float)
        self.scale = dict(M=1.0, A=1.0, B=1.0)

    @property
    def edges(self):
        return [(int(u), int(v)) for u, v in self.G.edges]

    def has_coords(self):
        return (self.lon is not None and self.lat is not None
                and np.isfinite(self.lon).all() and np.isfinite(self.lat).all())

    def to_schema_graph(self):
        """A networkx graph in the repo's node schema, for the vendored validate/census."""
        H = nx.Graph()
        for i in range(self.n):
            d = dict(rep_a=int(self.rep_a[i]), rep_b=int(self.rep_b[i]),
                     A=float(self.A[i]), B=float(self.B[i]), M=float(self.M[i]))
            if self.state is not None:
                d["state"] = self.state[i]
            H.add_node(i, **d)
        H.add_edges_from(self.G.edges)
        return H


def join_inputs(G, opportunity, sales, reps, cfg):
    """Join the four confidential inputs onto the graph.  Returns (Instance, report)."""
    opp = read_table(opportunity, ["M"])
    sal = read_table(sales, ["A", "B"])
    rep = read_table(reps, ["rep_a", "rep_b"])

    gnodes = set(G.nodes)
    vnodes = set(opp) & set(sal) & set(rep)
    only_graph = sorted(gnodes - vnodes)
    only_values = sorted(vnodes - gnodes)
    both = sorted(gnodes & vnodes)
    frac = len(both) / float(max(1, len(gnodes)))
    report = dict(n_graph=len(gnodes), n_values=len(vnodes), n_joined=len(both),
                  join_fraction=frac,
                  only_in_graph=dict(count=len(only_graph), examples=only_graph[:3]),
                  only_in_values=dict(count=len(only_values), examples=only_values[:3]))
    msg = ("join: %d/%d graph ZCTAs matched values (%.4f); %d graph-only (e.g. %s), "
           "%d values-only (e.g. %s)"
           % (len(both), len(gnodes), frac, len(only_graph), only_graph[:3],
              len(only_values), only_values[:3]))
    cfg.log(msg)
    if frac < 0.99 and not cfg.allow_partial:
        raise InputError(msg + "\n  below the 0.99 floor -- check the id vintage (leading "
                               "zeros? ZCTA 2020 vs 2025?) or pass --allow-partial.")
    if not both:
        raise InputError("no ZCTA joined between the graph and the value tables")

    H = G.subgraph(both).copy()
    z = sorted(H.nodes)
    idx = dict((zz, i) for i, zz in enumerate(z))
    H = nx.relabel_nodes(H, idx, copy=True)

    M = np.array([float(opp[zz][0]) for zz in z])
    A = np.array([float(sal[zz][0]) for zz in z])
    B = np.array([float(sal[zz][1]) for zz in z])
    ra_raw = [str(rep[zz][0]) for zz in z]
    rb_raw = [str(rep[zz][1]) for zz in z]
    a_names = sorted(set(ra_raw))
    b_names = sorted(set(rb_raw))
    a_of = dict((s, i) for i, s in enumerate(a_names))
    b_of = dict((s, i) for i, s in enumerate(b_names))
    rep_a = [a_of[s] for s in ra_raw]
    rep_b = [b_of[s] for s in rb_raw]

    st = None
    if any("state" in G.nodes[zz] for zz in z):
        st = [str(G.nodes[zz].get("state", "??")) for zz in z]
    lon = lat = None
    if all("lon" in G.nodes[zz] and "lat" in G.nodes[zz] for zz in z):
        lon = [G.nodes[zz]["lon"] for zz in z]
        lat = [G.nodes[zz]["lat"] for zz in z]

    inst = Instance(H, z, st, M, A, B, rep_a, rep_b, a_names, b_names, lon, lat)
    report["n_rep_a"] = len(a_names)
    report["n_rep_b"] = len(b_names)
    report["n_states"] = len(set(st)) if st else 0
    report["negative_values"] = int((M < 0).sum() + (A < 0).sum() + (B < 0).sum())
    if report["negative_values"]:
        raise InputError("%d negative values in M/A/B -- fix upstream, the model is "
                         "defined on nonnegative dollars" % report["negative_values"])
    return inst, report


def attach_coords(inst, coords_path, cfg):
    """Optional zcta,lon,lat table (only used for the W11 km radius; never exported)."""
    tab = read_table(coords_path, ["lon", "lat"])
    lon, lat, miss = [], [], 0
    for zz in inst.z:
        row = tab.get(zz)
        if row is None:
            miss += 1
            lon.append(float("nan"))
            lat.append(float("nan"))
        else:
            lon.append(float(row[0]))
            lat.append(float(row[1]))
    inst.lon = np.array(lon)
    inst.lat = np.array(lat)
    cfg.log("coords: %d/%d ZCTAs located (%d missing)" % (inst.n - miss, inst.n, miss))
    return inst


# ------------------------------------------------------------------- json writers
def round_sig(x, sig=6):
    if x is None or isinstance(x, bool) or isinstance(x, str):
        return x
    if isinstance(x, int):
        return x
    f = float(x)
    if not math.isfinite(f):
        return None
    if f == 0.0:
        return 0.0
    return float("%.*g" % (sig, f))


def _guard(obj, path, max_list, allow_long, sig, forbid_id_like, problems):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            ks = str(k)
            if forbid_id_like and ID_RE.match(ks):
                problems.append("%s: dict key %r looks like a ZCTA id" % (path, ks))
            out[ks] = _guard(v, "%s.%s" % (path, ks), max_list, allow_long, sig,
                             forbid_id_like, problems)
        return out
    if isinstance(obj, (list, tuple)):
        leaf = path.rsplit(".", 1)[-1]
        if len(obj) > max_list and leaf not in allow_long:
            problems.append("%s: list of length %d exceeds the %d cap (allowed only for %s)"
                            % (path, len(obj), max_list, ", ".join(sorted(allow_long))))
        return [_guard(v, path, max_list, allow_long, sig, forbid_id_like, problems)
                for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        obj = float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, str):
        if forbid_id_like and ID_RE.match(obj):
            problems.append("%s: the string %r looks like a ZCTA id" % (path, obj))
        return obj
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, float):
        if not math.isfinite(obj):
            return None
        return round_sig(obj, sig)
    if isinstance(obj, int):
        return obj
    problems.append("%s: value of type %s is not JSON-exportable" % (path, type(obj).__name__))
    return None


def write_json_guarded(obj, path, max_list=250, allow_long=("coarse_cdf", "bin_p", "bin_mean"),
                       round_sig_digits=6, forbid_id_like=True, verbose=True):
    """The `twin_stats.json` writer.  Refuses to write anything that smells like a leak."""
    problems = []
    clean = _guard(obj, "", max_list, set(allow_long), round_sig_digits, forbid_id_like,
                   problems)
    if problems:
        raise LeakGuardError("write_json_guarded refused %s:\n  %s"
                             % (path, "\n  ".join(problems[:20])))
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(clean, f, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)
    if verbose:
        print("wrote %s (%d bytes)" % (path, os.path.getsize(path)))
    return path


TWIN_SCHEMA = {
    "meta": ("seed", "rank_sigma", "coarsen", "swap_rounds", "alpha", "n_rep_a", "n_rep_b",
             "theta", "lam", "graph_hash", "tiger_vintage", "zcta_vintage", "n", "m",
             "twin_export_version", "built", "min_support", "min_state", "strip_scale",
             "scale_convention", "jitter_smooth", "sigma_effective"),
    "nodes": ("z", "state", "A", "B", "M", "rep_a", "rep_b"),
    "edges": ("u", "v"),
}


def write_twin(obj, path, verbose=True):
    """The `twin_instance.json.gz` writer: a hard schema whitelist, then gzip.

    Independent of `write_json_guarded` on purpose -- the instance file is *meant* to carry
    per-node numbers (synthetic ones) and public ZCTA ids, so the stats-file rules would be
    wrong here.  What this enforces instead: exactly the keys PLAN.md C.2 names, integer
    reps, equal column lengths, and edges that close on the node set.
    """
    out = {}
    for section in ("meta", "nodes", "edges"):
        if section not in obj:
            raise LeakGuardError("write_twin: missing section %r" % section)
        allowed = TWIN_SCHEMA[section]
        extra = [k for k in obj[section] if k not in allowed]
        if extra:
            raise LeakGuardError("write_twin: section %r carries non-schema keys %s"
                                 % (section, extra))
        out[section] = dict(obj[section])
    if "audit" in obj:
        out["audit"] = obj["audit"]

    nodes = out["nodes"]
    n = len(nodes["z"])
    for k, v in nodes.items():
        if len(v) != n:
            raise LeakGuardError("write_twin: nodes.%s has %d entries, expected %d"
                                 % (k, len(v), n))
    for k in ("rep_a", "rep_b"):
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in nodes[k]):
            raise LeakGuardError("write_twin: nodes.%s must be integers (rep names never "
                                 "leave the work machine)" % k)
    zset = set(nodes["z"])
    if len(zset) != n:
        raise LeakGuardError("write_twin: duplicate ZCTA ids in nodes.z")
    us, vs = out["edges"]["u"], out["edges"]["v"]
    if len(us) != len(vs):
        raise LeakGuardError("write_twin: edges.u and edges.v differ in length")
    bad = [e for e in zip(us, vs) if e[0] not in zset or e[1] not in zset][:3]
    if bad:
        raise LeakGuardError("write_twin: edges reference unknown ZCTAs, e.g. %s" % bad)
    for k in ("A", "B", "M"):
        nodes[k] = [round_sig(x, 6) for x in nodes[k]]

    tmp = path + ".tmp"
    with gzip.open(tmp, "wt") as f:
        json.dump(out, f, separators=(",", ":"), sort_keys=True)
    os.replace(tmp, path)
    if verbose:
        print("wrote %s (%d bytes, n=%d m=%d)" % (path, os.path.getsize(path), n, len(us)))
    return path


def read_twin(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt") as f:
        return json.load(f)


def twin_to_instance(obj):
    """A twin dict -> Instance, so `blocks()` can be recomputed on it for `twin_check`."""
    nodes = obj["nodes"]
    z = [str(x) for x in nodes["z"]]
    idx = dict((zz, i) for i, zz in enumerate(z))
    G = nx.Graph()
    G.add_nodes_from(range(len(z)))
    G.add_edges_from((idx[str(u)], idx[str(v)])
                     for u, v in zip(obj["edges"]["u"], obj["edges"]["v"]))
    st = nodes.get("state")
    return Instance(G, z, st, nodes["M"], nodes["A"], nodes["B"],
                    nodes["rep_a"], nodes["rep_b"])
