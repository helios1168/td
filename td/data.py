"""data.py -- the v3 extract: load it, apply the CONUS rule, and the seeded sparse fixture.

The extract is `export/export_instance.py`'s `td_instance_descaled/3`: node columns `z,
channel, m_rel, share, share_free`, one row per (ZIP, channel) cell, `m_rel` = M over the median
positive cell M.  It carries no states, edges or geometry; a ZIP's state comes from the 2025
reference table (td#62).  Nothing here prints or raises with a row's values: errors and the
CONUS report carry counts and aggregates only (docs/memory/workflow/confidential-data.md).

**The CONUS rule.**  A ZIP is kept only if it is a row of `reference/2025/zcta_reference.csv.gz`
with a state.  That table holds the CONUS ZCTAs only, so AK, HI, territories, blank ids and ZIPs
with no ZCTA (placed by HUD in G2, td#63) all drop as "not a CONUS ZCTA".  The drops are
counted by reason, never listed.

**The fixture.**  About 4,000 CONUS ZCTAs drawn without replacement with probability
proportional to `pop2025`, so it is sparse where people are few, as a real extract is, and
lognormal masses independent of population.  Its ZIP graph is `geo.zip_graph` on the sampled
points, the rule the real graph uses; a ZIP whose state-clipped cell vanishes is not a vertex,
is listed in `graph["missing"]`, and is not in the fixture (trap 21).
"""
from __future__ import annotations

import gzip
import json
import math
import re
from dataclasses import dataclass, field

from td import geo

FORMAT = "td_instance_descaled/3"
COLUMNS = ("z", "channel", "m_rel", "share", "share_free")
DEFAULT_CHANNEL = "national"
SIG = 6                         # the exporter's significant figures

FIXTURE_ZIPS = 4000
# lognormal mean/median = exp(sigma^2 / 2) = 2.284, the v2 CONUS ratio (M 8,481.81 over 3,713
# ZIPs, median 1; mem:facts/instance-versions)
FIXTURE_SIGMA = 1.285

_ZIP = re.compile(r"\d{5}")


@dataclass
class Extract:
    """The extract's cells as parallel columns, in file order."""
    channels: tuple
    z: list
    channel: list
    m_rel: list
    share: list
    share_free: list
    firm: dict = field(default_factory=dict)
    meta: dict = field(default_factory=dict)
    dropped: dict = field(default_factory=dict)

    @property
    def zips(self) -> list:
        return sorted(set(self.z))

    def masses(self, channel: str | None = None) -> dict:
        """`{zip: m_rel}` in `channel`, or summed over every channel."""
        out: dict = {}
        for z, c, m in zip(self.z, self.channel, self.m_rel):
            if channel is None or c == channel:
                out[z] = out.get(z, 0.0) + m
        return out

    def subset(self, keep) -> "Extract":
        rows = [i for i, z in enumerate(self.z) if z in keep]
        return Extract(self.channels, [self.z[i] for i in rows],
                       [self.channel[i] for i in rows], [self.m_rel[i] for i in rows],
                       [self.share[i] for i in rows], [self.share_free[i] for i in rows],
                       dict(self.firm), dict(self.meta), dict(self.dropped))


@dataclass
class Fixture:
    extract: Extract
    graph: dict                 # geo.zip_graph's output; `vertices` are the fixture's ZIPs
    zip_state: dict


def rsig(x: float, sig: int = SIG) -> float:
    if x == 0 or not math.isfinite(x):
        return x
    return round(float(x), -int(math.floor(math.log10(abs(float(x))))) + (sig - 1))


# ------------------------------------------------------------------------------ the extract
def load(path: str) -> Extract:
    """Read a `td_instance_descaled/3` file.  Raises ValueError on any other format or on a
    malformed node table."""
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        payload = json.load(fh)
    return from_payload(payload)


def from_payload(payload: dict) -> Extract:
    fmt = payload.get("format")
    if fmt != FORMAT:
        raise ValueError(f"format {fmt!r}, expected {FORMAT!r}")
    nodes = payload.get("nodes", {})
    missing = [c for c in COLUMNS if c not in nodes]
    if missing:
        raise ValueError(f"node columns missing: {missing}")
    n = len(nodes["z"])
    if any(len(nodes[c]) != n for c in COLUMNS):
        raise ValueError("node columns differ in length")
    meta = payload.get("meta", {})
    channels = tuple(meta.get("channels") or dict.fromkeys(nodes["channel"]))
    bad = {
        "ZIP ids not 5-digit strings":
            sum(not (isinstance(z, str) and _ZIP.fullmatch(z)) for z in nodes["z"]),
        "channels not in the channel list": sum(c not in channels for c in nodes["channel"]),
        "m_rel not finite and >= 0":
            sum(not (isinstance(m, (int, float)) and math.isfinite(m) and m >= 0)
                for m in nodes["m_rel"]),
        "shares outside [0, 1]":
            sum(not all(0 <= s <= 1 for s in d.values()) for d in nodes["share"])
            + sum(not 0 <= s <= 1 for s in nodes["share_free"]),
        "duplicate cells": n - len(set(zip(nodes["z"], nodes["channel"]))),
    }
    bad = {k: v for k, v in bad.items() if v}
    if bad:
        raise ValueError("malformed extract: " + "; ".join(f"{v} {k}" for k, v in bad.items()))
    return Extract(channels, list(nodes["z"]), list(nodes["channel"]),
                   [float(m) for m in nodes["m_rel"]], [dict(d) for d in nodes["share"]],
                   [float(s) for s in nodes["share_free"]], dict(payload.get("firm", {})),
                   dict(meta))


def to_payload(extract: Extract) -> dict:
    return {"format": FORMAT,
            "nodes": {"z": extract.z, "channel": extract.channel, "m_rel": extract.m_rel,
                      "share": extract.share, "share_free": extract.share_free},
            "firm": extract.firm,
            "meta": {**extract.meta, "channels": list(extract.channels)}}


def write(extract: Extract, path: str) -> None:
    """Write `extract` in the exporter's layout; the same extract writes the same bytes."""
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0,
                                                filename="") as gz:
        gz.write(json.dumps(to_payload(extract), separators=(",", ":"),
                            sort_keys=True).encode())


def conus(extract: Extract, reference=None) -> Extract:
    """The extract less its ZIPs outside the CONUS ground set; `dropped` counts them by reason:
    `{reason: {"zips", "cells", "m_rel_share"}}`."""
    ref = geo.read_reference() if reference is None else reference
    state = dict(zip(ref["zcta"], ref["state"]))
    reason = {}
    for z in set(extract.z):
        if z not in state:
            reason[z] = "not a CONUS ZCTA"
        elif not state[z]:
            reason[z] = "no state"
    total = sum(extract.m_rel)
    dropped: dict = {}
    for z, m in zip(extract.z, extract.m_rel):
        if z in reason:
            d = dropped.setdefault(reason[z], {"zips": set(), "cells": 0, "m_rel": 0.0})
            d["zips"].add(z)
            d["cells"] += 1
            d["m_rel"] += m
    out = extract.subset(set(extract.z) - set(reason))
    out.dropped = {r: {"zips": len(d["zips"]), "cells": d["cells"],
                       "m_rel_share": rsig(d["m_rel"] / total) if total else 0.0}
                   for r, d in sorted(dropped.items())}
    return out


# ------------------------------------------------------------------------------ the fixture
def state_polygons(public: str = geo.PUBLIC_DIR) -> dict:
    """`{USPS: polygon}` in `geo.CRS` for the CONUS states, from TIGER/Line 2025 state."""
    st = geo._read(geo.cached(geo.SOURCES["state"][0], public), ["STATEFP", "STUSPS"])
    st = st[st["STATEFP"].isin(geo.CONUS_STATEFP)]
    return dict(zip(st["STUSPS"], st.geometry))


def sample(seed: int = 0, n_zips: int = FIXTURE_ZIPS, channels=(DEFAULT_CHANNEL,),
           reference=None) -> Extract:
    """`n_zips` CONUS ZCTAs drawn by population, each with a lognormal mass in every channel,
    scaled so the median cell is 1 as the exporter's is.  No rep book: every cell is untapped."""
    import numpy as np
    ref = geo.read_reference() if reference is None else reference
    ref = ref[(ref["state"] != "") & (ref["pop2025"].astype(float) > 0)]
    ref = ref.sort_values("zcta").reset_index(drop=True)
    pop = ref["pop2025"].astype(float).to_numpy()
    rng = np.random.default_rng(seed)
    rows = np.sort(rng.choice(len(ref), size=n_zips, replace=False, p=pop / pop.sum()))
    m = rng.lognormal(0.0, FIXTURE_SIGMA, size=(n_zips, len(channels)))
    m /= np.median(m)
    zips = ref["zcta"].to_numpy()[rows]
    cells = [(str(z), c, rsig(float(m[i, j])))
             for i, z in enumerate(zips) for j, c in enumerate(channels)]
    return Extract(tuple(channels), [z for z, _, _ in cells], [c for _, c, _ in cells],
                   [v for _, _, v in cells], [{} for _ in cells], [0.0 for _ in cells],
                   meta={"channels": list(channels),
                         "fixture": {"seed": seed, "n_zips": n_zips, "sigma": FIXTURE_SIGMA}})


def fixture(seed: int = 0, n_zips: int = FIXTURE_ZIPS, channels=(DEFAULT_CHANNEL,),
            reference=None, state_polys=None, public: str = geo.PUBLIC_DIR) -> Fixture:
    """`sample`, its ZIP graph, and the sample restricted to the graph's vertices."""
    ref = geo.read_reference() if reference is None else reference
    ext = sample(seed, n_zips, channels, ref)
    ref = ref.set_index("zcta").loc[ext.zips]
    points = dict(zip(ref.index, zip(ref["x"].astype(float), ref["y"].astype(float))))
    zip_state = dict(zip(ref.index, ref["state"]))
    polys = state_polygons(public) if state_polys is None else state_polys
    graph = geo.zip_graph(points, zip_state, polys)
    ext = ext.subset(set(graph["vertices"]))
    return Fixture(ext, graph, {z: zip_state[z] for z in graph["vertices"]})
