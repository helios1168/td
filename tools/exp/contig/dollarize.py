"""dollarize.py -- the dollar-scaled extract (G5/B1, the main-map overnight grid, 2026-10-13): every
cell's mass in $M, so the master, the draw, the repair and the audit balance dollars with their band
rows unchanged (one mass vector feeds every stage).

    "$TD_PY" tools/exp/contig/dollarize.py <instance_descaled.json.gz> <instance_descaled_usd.json.gz>

A cell's $M is its `m_rel` times its fine channel's rate, E1 as coded: the owner's dollar total over
the extract's `m_rel` total (`tools/looks/score.py`'s `dollar_rates`), in $M.  The output keeps
the format `td_instance_descaled/3`, so `td.data.load` reads it, and records `meta["dollar_scale"]`:
the unit, the rates, the source's file name and sha256, and the fine channels dropped, those with no
owner total (career, edj, imo, priafs, which every main-map scenario plans elsewhere), never mixed
into a file of another unit.  A run's `manifest.json` records the output's path and sha256
(`run.write_manifest`), so a run traces back through `dollar_scale` to its descaled source.

The written file carries no sales data (`state_extract.strip_sales`: empty per-rep shares, zero `share_free`, no firm
map; `scale` itself keeps them).  Its dollars are still the owner's, so `main` refuses a name `.gitignore`'s
`instance_descaled*.json.gz` does not cover, the source itself, and a source already in dollars.  `to_m_rel` is the reversal (`export_long.py`).  Nothing
here prints a row's values.
"""
from __future__ import annotations

import argparse
import fnmatch
import functools
import hashlib
import importlib.util
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import data  # noqa: E402

UNIT = "$M"
KEY = "dollar_scale"
IGNORED = "instance_descaled*.json.gz"      # .gitignore:18, the confidential extracts


def _score():
    """`tools/looks/score.py`, loaded by path once (`tools/mandates/check.py`'s module name)."""
    if "looks_score" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "looks_score", os.path.join(ROOT, "tools", "looks", "score.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["looks_score"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["looks_score"]


def _strip_sales(ext: data.Extract) -> data.Extract:
    """`state_extract.strip_sales`, loaded by path once (AGENTS.md, Masking)."""
    if "contig_state_extract" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "contig_state_extract", os.path.join(os.path.dirname(os.path.abspath(__file__)), "state_extract.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["contig_state_extract"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["contig_state_extract"].strip_sales(ext)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rates(extract: data.Extract) -> dict:
    """{fine channel: $M per m_rel}, E1 as coded, for the fine channels with an owner total."""
    return {f: r / 1e6 for f, r in _score().dollar_rates(extract).items()}


def scale(extract: data.Extract, source: str = "", source_sha256: str = "") -> data.Extract:
    """`extract` with every cell's mass in $M (module doc).  Raises ValueError on an extract
    already in dollars."""
    if KEY in extract.meta:
        raise ValueError(f"the extract is already in dollars ({extract.meta[KEY].get('unit')})")
    r = rates(extract)
    keep = [i for i, c in enumerate(extract.channel) if c in r]
    channels = tuple(c for c in extract.channels if c in r)
    meta = {**extract.meta, "channels": list(channels),
            KEY: {"unit": UNIT, "rates": dict(sorted(r.items())), "source": source,
                  "source_sha256": source_sha256,
                  "dropped_channels": sorted(set(extract.channels) - set(r))}}
    return data.Extract(channels, [extract.z[i] for i in keep], [extract.channel[i] for i in keep],
                        [extract.m_rel[i] * r[extract.channel[i]] for i in keep],
                        [dict(extract.share[i]) for i in keep], [extract.share_free[i] for i in keep],
                        dict(extract.firm), meta, dict(extract.dropped))


@functools.lru_cache(maxsize=None)
def rates_of(path: str) -> dict | None:
    """The {fine channel: $M per m_rel} a dollar extract at `path` was scaled by, or None for an
    extract in `m_rel`."""
    got = data.load(path).meta.get(KEY)
    return None if got is None else dict(got["rates"])


def to_m_rel(value: float, fine: str, rates_: dict | None) -> float:
    """A cell's mass back in `m_rel`: `value` over its fine channel's rate, or `value` itself
    when `rates_` is None (an extract in `m_rel`).  Raises KeyError on a fine channel with no
    rate."""
    return value if rates_ is None else value / rates_[fine]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", help="the descaled extract (td_instance_descaled/3, m_rel)")
    ap.add_argument("out", help=f"the dollar extract; its name must match {IGNORED}")
    a = ap.parse_args(argv)
    if not fnmatch.fnmatch(os.path.basename(a.out), IGNORED):
        sys.exit(f"{a.out}: the name must match {IGNORED} (.gitignore), the file is the owner's dollars")
    if os.path.exists(a.out) and os.path.samefile(a.source, a.out):
        sys.exit(f"{a.out} is the source")
    ext = data.load(a.source)
    try:
        usd = scale(ext, os.path.basename(a.source), sha256(a.source))
    except ValueError as e:
        sys.exit(f"{a.source}: {e}")
    usd = _strip_sales(usd)
    data.write(usd, a.out)
    info = usd.meta[KEY]
    print(f"{a.out}: {len(usd.z)} cells in {UNIT}, channels {', '.join(usd.channels)}; dropped "
          f"{', '.join(info['dropped_channels']) or 'none'}; rates "
          + ", ".join(f"{f} {x:.6g}" for f, x in info["rates"].items()) + f"; sha256 {sha256(a.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
