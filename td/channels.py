"""channels.py -- cells, bundles and projections for the multi-channel instance.

A cell is a (zip, channel) pair.  The file carries the three business channels every report
speaks in, `national`, `wh` and `fi` (`FILE_CHANNELS`); a newer file may carry `national` split
into its three sub-channels instead, `national_chase`, `national_wells_wh`, `national_wells_fi`
(`SUB_CHANNELS`), with `meta["channel_groups"] = {"national": [the three]}` and `BUSINESS_OF`
mapping each back to `national` for reporting.  Channel spellings are read case-insensitively
through `canonical_channel`.  The model reads four fine labels, `N_WH`, `N_FI`, `WH`, `FI`,
which exist only so a national district can be merged into a WH or an FI one.  `fine_split`
moves an instance from the file channels to the fine labels: exactly, from the sub-channels
(`national_wells_wh` to `N_WH`, `national_chase` and `national_wells_fi` to `N_FI`), or by a
ratio proxy on the zip's own WH:FI mass ratio when only plain `national` is present.

Per-channel node attributes on a v2 `Descaled` (the loader contract):

    M_c:      {channel: M_{z,c}}
    S_c:      {rep: {channel: S_i(z,c)}}          # rep-major, as in the loader contract
    S_free_c: {channel: S_free(z,c)}

and the totals `M`, `S`, `S_free`, `cand`, `state` are the sums over channels, exactly as a
format-1 instance carries them.  `Descaled.channels` names the channels in file order.

Every quantity the utility reads is additive over cells, so a bundle B of channels projects to
a single-channel instance by summing: `project(d, B)` returns a format-1-shaped `Descaled` that
every existing driver can take as its `instance` argument.

Note for callers: a projection and a per-cell file both have a median `m_rel` well below 1 by
construction, so `instance.check_descaled` and the exporter's `guard` reject them.  Neither is
applied here.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
from dataclasses import dataclass

import networkx as nx
import numpy as np

from .instance import Descaled

FORMAT_V1 = "td_instance_descaled/1"
FORMAT_V2 = "td_instance_descaled/2"

# what the file carries; the national row is exactly today's single-channel data
FILE_CHANNELS = ("national", "wh", "fi")

# accounting labels: national is split by the zip's WH:FI ratio so that a national district
# can be merged into a WH or an FI one without moving mass between channels
CHANNELS = ("N_WH", "N_FI", "WH", "FI")

# a newer file may carry these three in place of "national"; national_chase and
# national_wells_fi land on N_FI when merged, national_wells_wh lands on N_WH
SUB_CHANNELS = ("national_chase", "national_wells_wh", "national_wells_fi")

# which fine label a file channel's mass lands on once a merge folds it in
FINE_OF_SUB = {"national_chase": "N_FI", "national_wells_fi": "N_FI",
               "national_wells_wh": "N_WH", "wh": "WH", "fi": "FI"}

# the business channel a file channel reports under; every report still speaks in FILE_CHANNELS
BUSINESS_OF = {c: "national" for c in SUB_CHANNELS}
BUSINESS_OF.update({"national": "national", "wh": "wh", "fi": "fi"})

BUNDLES = {
    "N": ("N_WH", "N_FI"),
    "WH": ("WH",),
    "FI": ("FI",),
    "WH_PLUS": ("WH", "N_WH"),
    "FI_PLUS": ("FI", "N_FI"),
    "WHFI": ("WH", "FI"),
    "WHFI_PLUS": ("WH", "FI", "N_WH", "N_FI"),
}

# WHFI_PLUS is off by default (open decision B in docs/FULL_PROBLEM.md)
DEFAULT_BUNDLES = {k: v for k, v in BUNDLES.items() if k != "WHFI_PLUS"}

# synthetic multipliers: wh and fi cells are these fractions of the national cell
ALPHA = (0.15, 0.55)
BETA = (0.15, 0.55)

SIG = 6                                  # significant figures, as tools/instance_export

# lower 48 + DC, the order level 0 indexes states in.  A copy of `_STATE_LIST` at
# tools/borders_report.py:67-72; importing that module from `td` would pull its whole
# dependency set into every consumer.
STATE_LIST = tuple(sorted({
    "AL", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "ID", "IL", "IN", "IA", "KS", "KY",
    "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY", "DC",
}))


def _rsig(x, sig: int = SIG):
    """Round to `sig` significant figures: a copy of the exporter's `rsig` (line 137)."""
    if x is None or not isinstance(x, (int, float)) or not math.isfinite(x) or x == 0:
        return x
    return round(float(x), -int(math.floor(math.log10(abs(float(x))))) + (sig - 1))


# --------------------------------------------------------------- channel name canonicalization
_CHANNEL_ALIASES = {
    "national": "national",
    "wh": "wh",
    "fi": "fi",
    "chase": "national_chase",
    "national_chase": "national_chase",
    "wells_wh": "national_wells_wh",
    "national_wells_wh": "national_wells_wh",
    "wells_fi": "national_wells_fi",
    "national_wells_fi": "national_wells_fi",
}


def canonical_channel(name: str) -> str:
    """A file channel spelling, any case, to its canonical name.

    Strips, lowercases, folds any run of spaces, hyphens, slashes, parentheses or dots to one
    underscore, and trims leading and trailing underscores; the result is looked up in a short
    alias table: "chase" and "national_chase" both give "national_chase"; "wells_wh" and
    "national_wells_wh" both give "national_wells_wh"; "wells_fi" and "national_wells_fi" both
    give "national_wells_fi"; "wh", "fi" and "national" map to themselves.  A spelling outside
    this table raises `ValueError` naming the accepted ones.
    """
    s = re.sub(r"[ \-/().]+", "_", name.strip().lower()).strip("_")
    if s not in _CHANNEL_ALIASES:
        raise ValueError(f"unknown channel {name!r}; accepted spellings: "
                         f"{sorted(_CHANNEL_ALIASES)}")
    return _CHANNEL_ALIASES[s]


# ------------------------------------------------------------------ the channels attribute
def channels_of(d: Descaled) -> tuple:
    """`d.channels`, tolerating a `Descaled` built before the field existed."""
    return tuple(getattr(d, "channels", ()) or ())


# ---------------------------------------------------------------------- synthetic channels
def _alpha_beta(seed: int, z: str) -> tuple:
    """Two deterministic draws in [0.15, 0.55] from sha256(f"{seed}:{z}").

    hashlib, never `hash()`: the built-in is salted per process and would make the instance
    different on every run.
    """
    h = hashlib.sha256(f"{seed}:{z}".encode()).digest()
    a = int.from_bytes(h[:8], "big") / 2.0 ** 64
    b = int.from_bytes(h[8:16], "big") / 2.0 ** 64
    return (ALPHA[0] + a * (ALPHA[1] - ALPHA[0]),
            BETA[0] + b * (BETA[1] - BETA[0]))


def _sub_shares(seed: int, z: str) -> tuple:
    """Three deterministic shares in (0, 1) summing to 1, from sha256(f"{seed}:sub:{z}").

    Order is (chase, wells_wh, wells_fi).  Three uniform draws normalised by their sum, so the
    shares are exact (float rounding aside) and never zero.
    """
    h = hashlib.sha256(f"{seed}:sub:{z}".encode()).digest()
    draws = [int.from_bytes(h[i:i + 8], "big") / 2.0 ** 64 + 1e-9 for i in (0, 8, 16)]
    total = sum(draws)
    return tuple(x / total for x in draws)


def synthesize_channels(d: Descaled, *, seed: int = 0, sub_channels: bool = False) -> Descaled:
    """A deterministic stand-in for the real multi-channel data.

    The real file keeps the national rows exactly as today and adds WH and FI rows, so the
    `national` cell of every zip is the input zip unchanged and the `wh` and `fi` cells are
    `alpha_z` and `beta_z` times it.  The same multiplier hits `M`, every `S_i` and `S_free`
    at that zip, so per-cell headroom holds exactly wherever it held on the input.  Totals
    are `(1 + alpha_z + beta_z)` times the input, summed over the cells.

    With `sub_channels=True`, the national cell is further split into `national_chase`,
    `national_wells_wh` and `national_wells_fi` by three deterministic shares that sum to one
    (`_sub_shares`), so the three still sum to exactly the national cell above; the instance
    then carries five channels and `meta["channel_groups"] = {"national": [the three]}`, the
    shape the real exporter is expected to write.
    """
    G = nx.Graph()
    for z, a in d.G.nodes(data=True):
        al, be = _alpha_beta(seed, z)
        M0 = float(a["M"])
        S0 = {i: float(v) for i, v in dict(a.get("S") or {}).items()}
        F0 = float(a.get("S_free", 0.0))
        if sub_channels:
            cs, ws, fs = _sub_shares(seed, z)
            M_c = {"national_chase": cs * M0, "national_wells_wh": ws * M0,
                   "national_wells_fi": fs * M0, "wh": al * M0, "fi": be * M0}
            S_c = {i: {"national_chase": cs * v, "national_wells_wh": ws * v,
                       "national_wells_fi": fs * v, "wh": al * v, "fi": be * v}
                   for i, v in S0.items()}
            F_c = {"national_chase": cs * F0, "national_wells_wh": ws * F0,
                   "national_wells_fi": fs * F0, "wh": al * F0, "fi": be * F0}
        else:
            M_c = {"national": M0, "wh": al * M0, "fi": be * M0}
            S_c = {i: {"national": v, "wh": al * v, "fi": be * v} for i, v in S0.items()}
            F_c = {"national": F0, "wh": al * F0, "fi": be * F0}
        attrs = dict(a)
        # totals are the float sum of the cells, which is what a v2 load recomputes; that is
        # not bit-identical to M0*(1 + alpha + beta)
        attrs["M"] = sum(M_c.values())
        attrs["S"] = {i: sum(per.values()) for i, per in S_c.items()}
        attrs["S_free"] = sum(F_c.values())
        attrs["M_c"], attrs["S_c"], attrs["S_free_c"] = M_c, S_c, F_c
        G.add_node(z, **attrs)
    G.add_edges_from(d.G.edges())

    channels = (SUB_CHANNELS + ("wh", "fi")) if sub_channels else FILE_CHANNELS
    meta = dict(d.meta)
    meta["synthetic"] = {"seed": seed, "alpha": list(ALPHA), "beta": list(BETA)}
    if sub_channels:
        meta["channel_groups"] = {"national": list(SUB_CHANNELS)}
    return Descaled(G=G, contested=list(d.contested), uncontested=dict(d.uncontested),
                    vacant=list(d.vacant), untapped=list(d.untapped),
                    firm=dict(d.firm), meta=meta, channels=channels)


def _canon_dict(per) -> dict:
    """A file-channel dict (`M_c`, one rep's `S_c` row, or `S_free_c`), keys canonicalised."""
    return {canonical_channel(k): float(v) for k, v in dict(per or {}).items()}


# ------------------------------------------------------------------------------ fine split
def fine_split(d: Descaled) -> Descaled:
    """File channels -> the fine labels, by one of two rules.

    If the instance carries the sub-channels (`SUB_CHANNELS`), the split is exact, on `M_c`,
    every `S_c[rep]` and `S_free_c`:

        N_WH = national_wells_wh
        N_FI = national_chase + national_wells_fi
        WH   = wh
        FI   = fi

    (`FINE_OF_SUB` is the source of this mapping.)  A missing sub-channel counts as zero, and
    `meta["fine_split"] = "sub-channels"` with `meta["fine_split_fallback"] = {}`.  An instance
    carrying both `national` and a sub-channel is ambiguous and raises.

    Otherwise, if the instance carries `national`, the split is the ratio proxy:

        N_WH(z) = national(z) * wh(z) / (wh(z) + fi(z)),      N_FI(z) likewise

    `wh` and `fi` pass through as `WH` and `FI`.  A zip with national mass and no WH or FI mass
    falls back to its state's WH:FI ratio, then to 50/50; the fallback zips are listed in
    `meta["fine_split_fallback"]` as zip -> which rule fired, and `meta["fine_split"] =
    "ratio proxy"`.

    Either way the totals `M`, `S`, `S_free`, `cand` are untouched, and channel names are read
    case-insensitively through `canonical_channel`.
    """
    have = tuple(canonical_channel(c) for c in channels_of(d))
    has_national = "national" in have
    has_sub = any(c in SUB_CHANNELS for c in have)
    if has_national and has_sub:
        raise ValueError(f"fine_split is ambiguous: instance carries both 'national' and a "
                         f"sub-channel, got {have}")
    if not has_national and not has_sub:
        raise ValueError(f"fine_split needs a 'national' channel or the sub-channels "
                         f"{SUB_CHANNELS} to split, got {have}; call synthesize_channels on "
                         f"a format-1 instance first")

    if has_sub:
        def split_exact(per):
            per = _canon_dict(per)
            out = {"N_WH": 0.0, "N_FI": 0.0, "WH": 0.0, "FI": 0.0}
            for c, fine in FINE_OF_SUB.items():
                out[fine] += per.get(c, 0.0)
            return out

        G = nx.Graph()
        for z, a in d.G.nodes(data=True):
            attrs = dict(a)
            attrs["M_c"] = split_exact(a.get("M_c"))
            attrs["S_c"] = {i: split_exact(per) for i, per in dict(a.get("S_c") or {}).items()}
            attrs["S_free_c"] = split_exact(a.get("S_free_c"))
            G.add_node(z, **attrs)
        G.add_edges_from(d.G.edges())

        meta = dict(d.meta)
        meta["fine_split"] = "sub-channels"
        meta["fine_split_fallback"] = {}
        meta["channels"] = list(CHANNELS)
        return Descaled(G=G, contested=list(d.contested), uncontested=dict(d.uncontested),
                        vacant=list(d.vacant), untapped=list(d.untapped),
                        firm=dict(d.firm), meta=meta, channels=CHANNELS)

    st_wh, st_fi = {}, {}                       # state -> mass, for the first fallback
    for z, a in d.G.nodes(data=True):
        M_c = _canon_dict(a.get("M_c"))
        st = a.get("state", "")
        st_wh[st] = st_wh.get(st, 0.0) + M_c.get("wh", 0.0)
        st_fi[st] = st_fi.get(st, 0.0) + M_c.get("fi", 0.0)

    fallback = {}
    G = nx.Graph()
    for z, a in d.G.nodes(data=True):
        M_c = _canon_dict(a.get("M_c"))
        w, f = M_c.get("wh", 0.0), M_c.get("fi", 0.0)
        nat = M_c.get("national", 0.0)
        if w + f > 0:
            r = w / (w + f)
        else:
            st = a.get("state", "")
            sw, sf = st_wh.get(st, 0.0), st_fi.get(st, 0.0)
            if sw + sf > 0:
                r, rule = sw / (sw + sf), "state"
            else:
                r, rule = 0.5, "even"
            if nat > 0:                          # a zip with no national mass needs no ratio
                fallback[z] = rule

        def split(per):
            per = _canon_dict(per)
            v = per.get("national", 0.0)
            return {"N_WH": r * v, "N_FI": (1.0 - r) * v,
                    "WH": per.get("wh", 0.0), "FI": per.get("fi", 0.0)}

        attrs = dict(a)
        attrs["M_c"] = split(a.get("M_c"))
        attrs["S_c"] = {i: split(per) for i, per in dict(a.get("S_c") or {}).items()}
        attrs["S_free_c"] = split(a.get("S_free_c"))
        G.add_node(z, **attrs)
    G.add_edges_from(d.G.edges())

    meta = dict(d.meta)
    meta["fine_split"] = "ratio proxy"
    meta["fine_split_fallback"] = dict(sorted(fallback.items()))
    meta["channels"] = list(CHANNELS)
    return Descaled(G=G, contested=list(d.contested), uncontested=dict(d.uncontested),
                    vacant=list(d.vacant), untapped=list(d.untapped),
                    firm=dict(d.firm), meta=meta, channels=CHANNELS)


# ------------------------------------------------------------------------ state x channel
@dataclass
class CellTable:
    """Cells aggregated to (state, channel), the granularity level 0 decides on."""

    state_list: tuple                          # the 49 CONUS states, in order
    channels: tuple                            # fine labels, in CHANNELS order
    reps: tuple                                # sorted rep ids
    M: "np.ndarray"                            # (S, C)
    S: "np.ndarray"                            # (R, S, C)
    S_free: "np.ndarray"                       # (S, C)


def aggregate(d: Descaled, state_list=STATE_LIST) -> CellTable:
    """Sum the node cells of `d` by state.  `d` must already carry the fine labels."""
    chans = channels_of(d)
    if not chans or any(c not in CHANNELS for c in chans):
        raise ValueError(f"aggregate needs the fine labels {CHANNELS}, got {chans!r}; call "
                         f"fine_split first")
    chans = tuple(c for c in CHANNELS if c in chans)
    states = tuple(state_list)
    s_idx = {s: k for k, s in enumerate(states)}
    c_idx = {c: k for k, c in enumerate(chans)}
    reps = sorted({i for z in d.G for i in (d.G.nodes[z].get("S_c") or {})})
    r_idx = {i: k for k, i in enumerate(reps)}

    M = np.zeros((len(states), len(chans)), float)
    S = np.zeros((len(reps), len(states), len(chans)), float)
    F = np.zeros((len(states), len(chans)), float)
    for z, a in d.G.nodes(data=True):
        k = s_idx.get(a.get("state", ""))
        if k is None:
            if float(a.get("M", 0.0)) > 0 or any(float(v) > 0
                                                 for v in (a.get("S") or {}).values()):
                raise ValueError(f"zip {z} is in state {a.get('state', '')!r}, which is not in "
                                 f"state_list, and carries mass or book")
            continue
        for c, j in c_idx.items():
            M[k, j] += float((a.get("M_c") or {}).get(c, 0.0))
            F[k, j] += float((a.get("S_free_c") or {}).get(c, 0.0))
        for i, per in (a.get("S_c") or {}).items():
            for c, j in c_idx.items():
                S[r_idx[i], k, j] += float(dict(per).get(c, 0.0))
    return CellTable(state_list=states, channels=chans, reps=tuple(reps), M=M, S=S, S_free=F)


def _bundle_channels(bundle) -> tuple:
    """A bundle name or an iterable of channels -> the tuple of channels."""
    if isinstance(bundle, str):
        if bundle not in BUNDLES:
            raise ValueError(f"unknown bundle {bundle!r}; known: {sorted(BUNDLES)}")
        return BUNDLES[bundle]
    return tuple(bundle)


def slot_weights(cells: CellTable, bundle_of) -> "np.ndarray":
    """`W[s, j] = sum_{c in bundle_of[j]} M[s, c]`, one mass per (state, slot)."""
    c_idx = {c: k for k, c in enumerate(cells.channels)}
    W = np.zeros((len(cells.state_list), len(bundle_of)), float)
    for j, b in enumerate(bundle_of):
        for c in _bundle_channels(b):
            if c not in c_idx:
                raise ValueError(f"slot {j} wants channel {c!r}, absent from {cells.channels}")
            W[:, j] += cells.M[:, c_idx[c]]
    return W


# ------------------------------------------------------------------------------ projection
def project(d: Descaled, bundle, *, states=None) -> Descaled:
    """Sum a bundle's cells into a format-1-shaped instance every existing driver can take.

    `M = sum_{c in B} M_c`, `S_i` and `S_free` likewise; `cand` is recomputed the way
    `load_descaled` does (the reps with positive book), edges are induced on the kept zips,
    and `meta["bundle"]` names the bundle.  `states` keeps only the zips of those states;
    zero-mass zips of a kept state stay, as they do on load, because dropping them would
    change the graph's connectivity.
    """
    chans = _bundle_channels(bundle)
    have = channels_of(d)
    missing = [c for c in chans if c not in have]
    if missing:
        raise ValueError(f"bundle {bundle!r} wants {missing}, absent from {have}")
    keep_states = None if states is None else set(states)

    G = nx.Graph()
    contested, uncontested, vacant, untapped = [], {}, [], []
    for z, a in d.G.nodes(data=True):
        if keep_states is not None and a.get("state", "") not in keep_states:
            continue
        M_c = dict(a.get("M_c") or {})
        F_c = dict(a.get("S_free_c") or {})
        M = sum(float(M_c.get(c, 0.0)) for c in chans)
        free = sum(float(F_c.get(c, 0.0)) for c in chans)
        S = {}
        for i, per in (a.get("S_c") or {}).items():
            per = dict(per)
            v = sum(float(per.get(c, 0.0)) for c in chans)
            if v > 0:
                S[i] = v
        cand = tuple(sorted(S))
        attrs = dict(cand=cand, S=S, M=M, S_free=free)
        if a.get("state", ""):
            attrs["state"] = a["state"]
        G.add_node(z, **attrs)
        if len(cand) >= 2:
            contested.append(z)
        elif len(cand) == 1:
            uncontested[z] = cand[0]
        elif free > 0:
            vacant.append(z)
        else:
            untapped.append(z)
    G.add_edges_from((u, v) for u, v in d.G.edges() if u in G and v in G)

    meta = dict(d.meta)
    meta.pop("channels", None)
    meta["bundle"] = bundle if isinstance(bundle, str) else list(chans)
    return Descaled(G=G, contested=sorted(contested),
                    uncontested=dict(sorted(uncontested.items())),
                    vacant=sorted(vacant), untapped=sorted(untapped),
                    firm=dict(d.firm), meta=meta, channels=())


# --------------------------------------------------------------------------------- writers
def _edges_firm_meta(d: Descaled, meta: dict) -> dict:
    edges = sorted(tuple(sorted(e)) for e in d.G.edges())
    return dict(edges=dict(u=[u for u, _ in edges], v=[v for _, v in edges]),
                firm=dict(d.firm), meta=meta)


def _dump(payload, path) -> str:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"), sort_keys=True)
    return str(path)


def write_v2(d: Descaled, path) -> str:
    """Write a per-cell instance: the v1 layout with node rows long by (zip, channel).

    Columns `z, channel, m_rel, share, share_free, state`; `share` is the fraction of that
    cell's `m_rel`, `share_free` the free fraction of it.  Every (zip, channel) pair is
    emitted, zero cells included: a zip missing from the node table would silently drop its
    graph edges on load.
    """
    chans = channels_of(d)
    if not chans:
        raise ValueError("write_v2 needs an instance with channels; call synthesize_channels "
                         "or load a v2 file")
    zc, cc, mc, sc, fc, stc = [], [], [], [], [], []
    for z in sorted(d.G):
        a = d.G.nodes[z]
        M_c = dict(a.get("M_c") or {})
        S_c = dict(a.get("S_c") or {})
        F_c = dict(a.get("S_free_c") or {})
        for c in chans:
            m = float(M_c.get(c, 0.0))
            share, free = {}, 0.0
            if m > 0:
                for rep, per in S_c.items():
                    v = float(dict(per).get(c, 0.0))
                    if v > 0:
                        share[rep] = _rsig(v / m)
                free = _rsig(float(F_c.get(c, 0.0)) / m)
            zc.append(z); cc.append(c); mc.append(_rsig(m))
            sc.append({r: share[r] for r in sorted(share)}); fc.append(free)
            stc.append(a.get("state", ""))
    meta = dict(d.meta)
    meta["channels"] = list(chans)
    payload = dict(format=FORMAT_V2,
                   nodes=dict(z=zc, channel=cc, m_rel=mc, share=sc, share_free=fc, state=stc),
                   **_edges_firm_meta(d, meta))
    return _dump(payload, path)


def write_v1(d: Descaled, path) -> str:
    """Write a format-1 file, so every existing driver can take a projection as `instance`."""
    zips = sorted(d.G)
    nodes = dict(z=zips, m_rel=[], share=[], share_free=[], state=[])
    for z in zips:
        a = d.G.nodes[z]
        m = float(a["M"])
        share, free = {}, 0.0
        if m > 0:
            for rep, v in sorted(dict(a.get("S") or {}).items()):
                if float(v) > 0:
                    share[rep] = _rsig(float(v) / m)
            free = _rsig(float(a.get("S_free", 0.0)) / m)
        nodes["m_rel"].append(_rsig(m))
        nodes["share"].append(share)
        nodes["share_free"].append(free)
        nodes["state"].append(a.get("state", ""))
    payload = dict(format=FORMAT_V1, nodes=nodes, **_edges_firm_meta(d, dict(d.meta)))
    return _dump(payload, path)
