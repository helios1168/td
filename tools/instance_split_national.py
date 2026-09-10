"""instance_split_national.py: national -> its three sub-channels at fixed shares.

    .venv/bin/python3 tools/instance_split_national.py \\
        /Users/ntlee/projects/td/instance_descaled_v3_conus.json.gz \\
        /Users/ntlee/projects/td/instance_descaled_v4synth_conus.json.gz

A stand-in for the real v4 export (`tools/instance_export/README.md`, "National
sub-channels"), built from an existing v2 instance that still carries plain `national`, `wh`
and `fi`, before that export lands.  Splits every cell's `national` mass into
`national_chase`, `national_wells_wh` and `national_wells_fi` at fixed shares (default 0.5 /
0.3 / 0.2), applied identically to `M_c`, every rep's `S_c` and `S_free_c`, so a cell's
per-rep shares are unchanged and the three sub-channels sum back to exactly the input's
`national` cell.  `wh` and `fi` pass through untouched.  The result carries the five canonical
channels and `meta["channel_groups"]` the way the real exporter would write them
(`td/channels.py`'s module docstring), plus `meta["synthetic_split"]` recording the shares and
source, so `fine_split` on it takes the exact sub-channel rule rather than the ratio proxy.
"""
from __future__ import annotations

import argparse
import os
import sys

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import channels as ch                                               # noqa: E402
from td import instance as inst                                             # noqa: E402

DEFAULT_SHARES = dict(chase=0.5, wells_wh=0.3, wells_fi=0.2)


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src", help="a v2 instance carrying national, wh and fi")
    ap.add_argument("dst", help="the file to write, national split into the three sub-channels")
    ap.add_argument("--chase", type=float, default=DEFAULT_SHARES["chase"])
    ap.add_argument("--wells-wh", type=float, default=DEFAULT_SHARES["wells_wh"])
    ap.add_argument("--wells-fi", type=float, default=DEFAULT_SHARES["wells_fi"])
    return ap


def _canon(per) -> dict:
    return {ch.canonical_channel(k): float(v) for k, v in dict(per or {}).items()}


def split_national(d: "inst.Descaled", *, chase: float, wells_wh: float,
                   wells_fi: float) -> "inst.Descaled":
    """`d` (channels national, wh, fi, any order) -> the same instance with `national` split
    into the three sub-channels at the given shares.  `M`, `S` and `S_free` totals, and every
    per-cell rep share, are untouched: only `national`'s own mass is divided three ways."""
    shares = dict(chase=chase, wells_wh=wells_wh, wells_fi=wells_fi)
    total = sum(shares.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"chase + wells_wh + wells_fi must sum to 1, got {total}")

    have = {ch.canonical_channel(c) for c in ch.channels_of(d)}
    if have != {"national", "wh", "fi"}:
        raise ValueError(f"split_national needs an instance carrying exactly national, wh, fi; "
                         f"got {sorted(have)}")

    sub_of = dict(chase="national_chase", wells_wh="national_wells_wh",
                  wells_fi="national_wells_fi")

    def split_one(per: dict) -> dict:
        per = _canon(per)
        nat = per.pop("national", 0.0)
        for key, name in sub_of.items():
            per[name] = shares[key] * nat
        return per

    G = nx.Graph()
    for z, a in d.G.nodes(data=True):
        attrs = dict(a)
        attrs["M_c"] = split_one(a.get("M_c"))
        attrs["S_c"] = {i: split_one(per) for i, per in dict(a.get("S_c") or {}).items()}
        attrs["S_free_c"] = split_one(a.get("S_free_c"))
        G.add_node(z, **attrs)
    G.add_edges_from(d.G.edges())

    meta = dict(d.meta)
    meta["channel_groups"] = {"national": list(ch.SUB_CHANNELS)}
    meta["synthetic_split"] = dict(shares)
    channels_out = ch.SUB_CHANNELS + ("wh", "fi")
    return inst.Descaled(G=G, contested=list(d.contested), uncontested=dict(d.uncontested),
                         vacant=list(d.vacant), untapped=list(d.untapped), firm=dict(d.firm),
                         meta=meta, channels=channels_out)


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    d = inst.load_descaled(args.src)
    if not d.channels:
        raise SystemExit(f"{args.src} carries one channel; split_national needs a format-2 "
                         f"file with national, wh and fi")
    out = split_national(d, chase=args.chase, wells_wh=args.wells_wh, wells_fi=args.wells_fi)
    path = ch.write_v2(out, args.dst)
    print(f"wrote {path}: channels {out.channels}, shares "
          f"chase={args.chase} wells_wh={args.wells_wh} wells_fi={args.wells_fi}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
