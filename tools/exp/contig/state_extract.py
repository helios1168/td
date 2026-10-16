"""state_extract.py -- the descaled extract cut to the ZIPs of some states, the `--extract` of a
`run.py --states` / `repair.py --states` regional run (the `_inst/*.json.gz` of the K-grid regions).

    "$TD_PY" tools/exp/contig/state_extract.py <out.json.gz> <STATE,STATE,...> [--base PATH]
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import data, geo  # noqa: E402


def strip_sales(ext: data.Extract) -> data.Extract:
    """`ext` without the sales data (AGENTS.md, Masking): empty per-rep share dicts, zero
    `share_free`, empty `firm`.  The model reads only `m_rel`."""
    return data.Extract(ext.channels, list(ext.z), list(ext.channel), list(ext.m_rel),
                        [{} for _ in ext.share], [0.0 for _ in ext.share_free], {},
                        dict(ext.meta), dict(ext.dropped))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out")
    ap.add_argument("states")
    ap.add_argument("--base", default=os.path.join(os.environ.get("TD_REPO", ROOT),
                                                   "instance_descaled.json.gz"))
    a = ap.parse_args(argv)
    want = set(a.states.split(","))
    ref = geo.read_reference()
    state = dict(zip(ref["zcta"], ref["state"]))
    ext = data.load(a.base)
    keep = {z for z in set(ext.z) if state.get(z) in want}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    data.write(strip_sales(ext.subset(keep)), a.out)
    print(f"{a.out}: {len(keep)} ZIPs in {','.join(sorted(want))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
