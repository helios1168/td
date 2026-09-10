"""instance_conus.py: a raw export -> its CONUS-only cut, the v2 rule generalised.

    .venv/bin/python3 tools/instance_conus.py \\
        /Users/ntlee/projects/td/instance_descaled_v4.json.gz \\
        /Users/ntlee/projects/td/instance_descaled_v4_conus.json.gz

Keeps the 49 CONUS + DC state codes (`td.channels.STATE_LIST`), drops every zip whose `state`
is outside that set, induces the edges on the kept zips, and records the filter in
`meta["conus_filter"]`.  Works column-generically: a row is `zip(*[nodes[c] for c in
nodes])`, so a format-1 file (columns `z, m_rel, share, share_free, state`) and a format-2 file
long by cell (`z, channel, m_rel, share, share_free, state`) are filtered the same way, no
channel-specific logic needed.  This is the same rule that produced
`instance_descaled_v3_conus.json.gz` (job 610589f0, `conus_v3.py`), now parameterised on SRC and
DST instead of pinned to v3.

After writing, the result is loaded back, `geo.assert_conus` is checked, and the per-channel
mass, the `fine_split` fallback count, tau at k=18 and the per-bundle slot counts are printed,
exactly as `conus_v3.py` did, so a v4 CONUS file can be sanity-checked against the v3 numbers
before anything is built on it.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import geo, instance as inst, channels as ch                        # noqa: E402

DEFAULT_SRC = "/Users/ntlee/projects/td/instance_descaled_v4.json.gz"
DEFAULT_DST = "/Users/ntlee/projects/td/instance_descaled_v4_conus.json.gz"

CONUS = set(ch.STATE_LIST)
assert len(CONUS) == 49


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src", nargs="?", default=DEFAULT_SRC, help="the raw export")
    ap.add_argument("dst", nargs="?", default=DEFAULT_DST, help="the CONUS-filtered file to write")
    ap.add_argument("--k", type=int, default=18, help="k for the printed tau (default 18)")
    return ap


def filter_conus(raw: dict, src_name: str) -> dict:
    """Drop every node row whose state is outside `CONUS`, induce the edges, record the
    filter in `meta["conus_filter"]`.  Mutates and returns `raw`."""
    n = raw["nodes"]
    cols = list(n.keys())
    rows = list(zip(*[n[c] for c in cols]))
    zi, si = cols.index("z"), cols.index("state")
    keep_rows = [r for r in rows if r[si] in CONUS]
    dropped = sorted({r[zi] for r in rows if r[si] not in CONUS})
    dropped_states = sorted({r[si] for r in rows if r[si] not in CONUS})
    keep_z = {r[zi] for r in keep_rows}
    raw["nodes"] = {c: [r[i] for r in keep_rows] for i, c in enumerate(cols)}

    e = raw["edges"]
    if isinstance(e, dict):
        ek = list(e.keys())
        erows = list(zip(*[e[k] for k in ek]))
        erows = [r for r in erows if r[0] in keep_z and r[1] in keep_z]
        raw["edges"] = {k: [r[i] for r in erows] for i, k in enumerate(ek)}
    else:
        raw["edges"] = [r for r in e if r[0] in keep_z and r[1] in keep_z]

    import datetime
    raw["meta"]["conus_filter"] = dict(
        source=src_name, rule="state in the 49 CONUS+DC codes",
        dropped_states=dropped_states, dropped_zips=dropped,
        date=datetime.date.today().isoformat())
    print("dropped states", dropped_states, "dropped zips", len(dropped),
          "kept rows", len(keep_rows), flush=True)
    return raw


def report(d, k: int) -> None:
    """The per-channel mass, `fine_split` fallback count, tau(k) and per-bundle slot counts --
    `conus_v3.py`'s own checks, so a new CONUS file can be compared to the v3 numbers."""
    import networkx as nx

    geo.assert_conus(d)
    G = d.G
    print("conus zips", G.number_of_nodes(), "edges", G.number_of_edges(),
          "components", nx.number_connected_components(G), flush=True)

    mass = defaultdict(float)
    for _, a in G.nodes(data=True):
        for c, m in a["M_c"].items():
            mass[c] += m
    print("mass per channel", {c: round(v, 1) for c, v in mass.items()},
          "total", round(sum(mass.values()), 1), flush=True)

    f = ch.fine_split(d)
    fb = f.meta.get("fine_split_fallback", {})
    print("fine_split fallbacks", len(fb), Counter(fb.values()), flush=True)
    print("fine_split rule", f.meta.get("fine_split"), flush=True)

    national_mass = sum(mass[c] for c in mass if ch.BUSINESS_OF.get(c, c) == "national")
    nat_fb = sum(G.nodes[z]["M_c"].get(c, 0.0) for z in fb
                for c in G.nodes[z]["M_c"] if ch.BUSINESS_OF.get(c, c) == "national")
    print("national mass under fallback", round(nat_fb, 1), "of", round(national_mass, 1),
          flush=True)

    cells = ch.aggregate(f, ch.STATE_LIST)
    tau = national_mass / k
    print(f"tau(k={k})", round(tau, 2), flush=True)
    ci = {c: i for i, c in enumerate(cells.channels)}
    for b, t in ch.DEFAULT_BUNDLES.items():
        m = float(cells.M[:, [ci[c] for c in t]].sum())
        print(f"  {b:8s} mass {m:8.1f}  K_B at L=0.8tau {int(-(-m // (0.8 * tau)))}", flush=True)
    total_slots = sum(int(-(-float(cells.M[:, [ci[c] for c in t]].sum()) // (0.8 * tau)))
                      for t in ch.DEFAULT_BUNDLES.values())
    print("total slots", total_slots, flush=True)

    st = [(s, cells.M[i, ci["N_WH"]] + cells.M[i, ci["N_FI"]], cells.M[i, ci["WH"]],
           cells.M[i, ci["FI"]]) for i, s in enumerate(cells.state_list)]
    if any(r[0] == "AZ" for r in st):
        print("AZ", [round(float(x), 1) for x in next(r[1:] for r in st if r[0] == "AZ")],
              flush=True)
    below = [s for s, nn, w, ff in st if nn < 0.8 * tau]
    print("states with national < L", below, "count", len(below), flush=True)


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    raw = json.load(gzip.open(args.src, "rt"))
    filter_conus(raw, os.path.basename(args.src))
    with gzip.open(args.dst, "wt", encoding="utf-8") as fh:
        json.dump(raw, fh, separators=(",", ":"))

    d = inst.load_descaled(args.dst)
    report(d, args.k)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
