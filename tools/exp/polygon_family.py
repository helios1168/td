"""polygon_family.py -- each channel's support family on the polygon graph against the Voronoi
build (td#114).

    "$TD_PY" tools/exp/polygon_family.py <spec.toml> [<spec.toml> ...] [--extract PATH] [--full]

For each scenario, the instance on the OD2 Voronoi graph that runs declared before #114
(`output.declared_graph`, over the extract's positive ZIPs) and on M1's polygon graph
(`td.spec.build`'s default: every CONUS ZCTA, rook polygon edges and approved connectors), then per
channel: the unit-graph edges the polygon graph adds and drops, the supports in one family only,
and the border rows (b_uv) and corridor floors c_v(S) that differ.  Then the whole units the
polygon graph disconnects, and, as a what-if that no check uses, which states would be connected
and which dropped supports would return if the owner approved the connectors #114 proposed
(`geo.state_connectors`, `geo.pair_connectors`).  `--full` lists every differing support;
otherwise the first `SHOW`.  No solve.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import data, geo, output, supports                      # noqa: E402
from td import spec as tdspec                                   # noqa: E402

TD_REPO = os.environ.get("TD_REPO", "/Users/Shared/sv-ntlee/td")
EXTRACT = os.path.join(TD_REPO, "instance_descaled.json.gz")
PUBLIC = os.path.join(TD_REPO, "data", "public")
SHOW = 20


def _support(s) -> str:
    return "{" + " ".join(sorted(s)) + "}"


def _edges(adj: dict) -> set:
    return {(u, v) for u in adj for v in adj[u] if u < v}


def channel_diff(old, new, channel: str) -> dict:
    """The family, unit-graph, border-row and corridor-floor differences of `channel` between the
    instances `old` and `new`."""
    fo, fn = supports.family(old, channel), supports.family(new, channel)
    bo, bn = supports.border_rows(old, fo), supports.border_rows(new, fn)
    co, cn = supports.corridor_floors(old, fo), supports.corridor_floors(new, fn)
    return {
        "units": len(new.channels[channel].units),
        "edges_added": sorted(_edges(fn.adj) - _edges(fo.adj)),
        "edges_dropped": sorted(_edges(fo.adj) - _edges(fn.adj)),
        "family": (len(fo), len(fn)),
        "only_voronoi": sorted(set(fo.supports) - set(fn.supports), key=lambda s: (len(s), sorted(s))),
        "only_polygon": sorted(set(fn.supports) - set(fo.supports), key=lambda s: (len(s), sorted(s))),
        "border_rows": (len(bo), len(bn)),
        "border_b_changed": sorted((k, bo[k][0], bn[k][0]) for k in set(bo) & set(bn)
                                   if bo[k][0] != bn[k][0]),
        "border_rows_only_voronoi": sorted(set(bo) - set(bn)),
        "border_rows_only_polygon": sorted(set(bn) - set(bo)),
        "corridor_rows": (len(co), len(cn)),
        "corridor_changed": sum(1 for k in set(co) & set(cn) if co[k] != cn[k]),
        "corridor_old_positive": sum(1 for v in co.values() if v > 0),
        "corridor_new_positive": sum(1 for v in cn.values() if v > 0),
    }


def what_if_graph() -> dict:
    """The polygon graph with every connector #114 proposed taken as approved: a what-if for the
    owner's review, read by no check."""
    return geo.polygon_graph(connectors=[dict(r, status="approved") if r["source"] == geo.STATE_PROPOSAL
                                         else r for r in geo.read_connectors()])


def what_if_connected(states, g: dict) -> dict:
    """{state: connected within?} for `states` on the what-if graph `g`."""
    still = geo.state_groups(g["vertices"], g["edges"], g["state"])
    return {s: s not in still for s in sorted(states)}


def report(path: str, extract, ref, full: bool = False) -> str:
    s = tdspec.load(path)
    ext = tdspec.scope(s, extract)
    old = tdspec.build(s, ext, ref, output.declared_graph(ext, ref, PUBLIC))
    new = tdspec.build(s, ext, ref)
    g = what_if_graph()
    wif = tdspec.build(s, ext, ref, g)
    show = None if full else SHOW
    out = [f"## {s.name}", "",
           f"Voronoi: {len(old.units.unit_of)} ZIPs; polygon: {len(new.units.unit_of)} ZCTAs.", ""]
    groups = new.report["disconnected"]
    whole = new.report["disconnected_whole"]
    out.append("Units not connected on the polygon graph: " + (", ".join(
        f"{u} {groups[u]}" + (" (whole in a channel)" if u in whole else "") for u in sorted(groups))
        or "none") + ".")
    if groups:
        wi = what_if_connected(groups, g)
        out.append("What-if (no check uses it): with the connectors #114 proposed approved, "
                   + ", ".join(f"{u} {'connected' if ok else 'still not connected'}"
                               for u, ok in wi.items()) + ".")
    out.append("")
    for c in new.channels:
        d = channel_diff(old, new, c)
        out += [f"### {c} ({d['units']} units)", "",
                f"- unit graph: {len(d['edges_added'])} edges added "
                f"{' '.join(f'{a}-{b}' for a, b in d['edges_added']) or ''}; "
                f"{len(d['edges_dropped'])} dropped "
                f"{' '.join(f'{a}-{b}' for a, b in d['edges_dropped']) or ''}",
                f"- family: {d['family'][0]} on Voronoi, {d['family'][1]} on polygon; "
                f"{len(d['only_voronoi'])} only on Voronoi, {len(d['only_polygon'])} only on polygon"]
        back = sorted(set(d["only_voronoi"]) & set(supports.family(wif, c).supports),
                      key=lambda x: (len(x), sorted(x)))
        out.append(f"- what-if (no check uses it): with the connectors #114 proposed approved, "
                   f"{len(back)} of the {len(d['only_voronoi'])} return")
        d["what_if_back"] = back
        for key, label in (("only_voronoi", "only on Voronoi"), ("only_polygon", "only on polygon"),
                           ("what_if_back", "return in the what-if")):
            if d[key]:
                listed = d[key][:show]
                more = len(d[key]) - len(listed)
                out.append(f"  - {label}: " + ", ".join(map(_support, listed))
                           + (f", … {more} more" if more else ""))
        out += [f"- border rows: {d['border_rows'][0]} → {d['border_rows'][1]}; "
                f"b_uv changed on {len(d['border_b_changed'])} common rows; "
                f"{len(d['border_rows_only_voronoi'])} rows only on Voronoi, "
                f"{len(d['border_rows_only_polygon'])} only on polygon",
                f"- corridor rows: {d['corridor_rows'][0]} → {d['corridor_rows'][1]}; "
                f"c_v(S) changed on {d['corridor_changed']} common rows; positive floors "
                f"{d['corridor_old_positive']} → {d['corridor_new_positive']}", ""]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("specs", nargs="+", help="scenario TOML files")
    ap.add_argument("--extract", default=EXTRACT, help="the extract (default: $TD_REPO's)")
    ap.add_argument("--full", action="store_true", help="list every differing support")
    a = ap.parse_args(argv)
    ref = geo.read_reference()
    extract = data.conus(data.load(a.extract), ref)
    for path in a.specs:
        print(report(path, extract, ref, a.full))
    return 0


if __name__ == "__main__":
    sys.exit(main())
