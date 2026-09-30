"""spec.py -- a TOML scenario: its channels, domains, units, pieces and modes.

A scenario file has these tables (`scenarios/*.toml`):

    [scenario]    name, fine_channels (the scenario's universe F), delta (default 0.10, OD1)
    [sets]        named unit sets, for use wherever a unit list is expected
    [national]    channel, fine, units, fallback: which units have national, and where a unit
                  without it sends each national fine channel (owner comment on #67)
    [geography]   pieces = [{name, state, counties}], metros = [cbsa codes]; both optional (S13)
    [channels.X]  one section per planning channel: k, domain, modes, support parameters, hook

A unit list is an array of unit and set names, or a string `"a - b - ..."` where each term is
`all`, a set name or a unit name.  `all` is every unit of the scenario.

**The partition.**  The channels' domains partition V × F, where V is the scenario's units and
F its declared fine channels (`docs/MODEL.md` §1).  `load` rejects a gap or an overlap, naming
the cells.  An extract whose fine channels are not all in F is refused by `build`, naming them:
placing a new fine channel is #76's decision, never done here.

**Units** (`MODEL.md` §1, §6).  A unit is a state less its carved pieces, a county-built piece,
or a metro piece: the ZIPs whose G1 county has the metro's 2025 CBSA code (OD5).  `load` refuses a
metro code that is not a 2025 metropolitan CBSA: micropolitan, CSA, metro-division or unknown
codes are not metro units (OD5, #72).  A ZIP in two
pieces is an overlap and `load` or `build` rejects it.  After carving, `build` checks every unit
for ZIP connectivity (C11): a disconnected unit is listed, and a disconnected unit that is
`whole` in any channel stops the run, naming the unit and its components (OQ6).

**Modes.**  Each channel sets a default mode and lists the units that differ.  A metro is
classified once per channel against U_c: whole if its mass is at most U_c, else the channel's
`metro_mode` (OD5).  A unit or channel with zero opportunity is dropped before solving and
reported (#65 F1).

**Centroids.**  A unit's centroid p_u is the mean of its ZIPs' 2025 gazetteer points weighted by
their gazetteer land area, in km in EPSG:5070 (#67 decision; legacy used state polygon
centroids).  The distance cap reads it (`td.supports`).

**Hooks.**  A channel may name a hook; `hook(spec, channel)` looks it up in `td.hooks` by name.
"""
from __future__ import annotations

import functools
import importlib
import math
import tomllib
from dataclasses import dataclass, field

CONUS_STATES = (
    "AL AR AZ CA CO CT DC DE FL GA IA ID IL IN KS KY LA MA MD ME MI MN MO MS MT NC ND NE NH "
    "NJ NM NV NY OH OK OR PA RI SC SD TN TX UT VA VT WA WI WV WY").split()
MODES = ("whole", "clipped", "free")
SPLITTABLE = ("clipped", "free")
DEFAULT_DELTA = 0.10            # OD1: the default final band, declared per channel
DEFAULT_MAX_SIZE = 6
DEFAULT_MAX_DIST_KM = 900.0
DROPPED = "dropped: zero opportunity"
SHOW = 12                       # how many items an error message names


class SpecError(ValueError):
    """A scenario that cannot be run as written."""


def _show(items) -> str:
    items = list(items)
    more = f" (+{len(items) - SHOW} more)" if len(items) > SHOW else ""
    return ", ".join(str(i) for i in items[:SHOW]) + more


# ------------------------------------------------------------------------------ the spec
@dataclass(frozen=True)
class Piece:
    name: str
    state: str
    counties: frozenset


@dataclass(frozen=True)
class Metro:
    name: str
    cbsa: str


@dataclass(frozen=True)
class National:
    channel: str
    fine: frozenset
    units: frozenset
    fallback: dict              # national fine channel -> the fine channel it goes with


@dataclass(frozen=True)
class ChannelSpec:
    name: str
    k: int
    delta: float                # planning band τ[1 − δ, 1 + δ]
    final_delta: float          # the final tolerance, ≥ delta (OD1)
    eta: float
    domain: dict                # unit -> frozenset of fine channels
    modes: dict                 # unit -> mode, for every unit of the domain
    metro_mode: str
    max_size: int
    max_dist_km: float
    dist_km: dict               # unit -> its own distance cap; R(u, v) = max of the three
    contact_caps: dict
    extra_supports: tuple       # frozensets of units, added with their connected subsets
    listed_only: bool           # the family is only the extras and their connected subsets
    forbid_pairs: frozenset     # frozensets {u, w}: no support holds both
    hook: str | None

    @property
    def units(self) -> frozenset:
        return frozenset(self.domain)

    def dist_cap(self, u: str, v: str) -> float:
        return max(self.max_dist_km, self.dist_km.get(u, 0.0), self.dist_km.get(v, 0.0))


@dataclass(frozen=True)
class Spec:
    name: str
    fine_channels: tuple
    units: tuple                # every unit name: states, pieces, metros
    pieces: tuple
    metros: tuple
    national: National | None
    channels: dict              # name -> ChannelSpec, in file order
    path: str | None = None

    def channel_of(self, unit: str, fine: str) -> str:
        return next(c.name for c in self.channels.values() if fine in c.domain.get(unit, ()))


def load(path: str) -> Spec:
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)
    return parse(raw, path)


def parse(raw: dict, path: str | None = None) -> Spec:
    known = {"scenario", "sets", "national", "geography", "channels"}
    if set(raw) - known:
        raise SpecError(f"unknown tables: {_show(sorted(set(raw) - known))}")
    sc = raw.get("scenario", {})
    name = sc.get("name") or (path and path.rsplit("/", 1)[-1].removesuffix(".toml"))
    fine = tuple(sc.get("fine_channels", ()))
    if not fine or len(set(fine)) != len(fine):
        raise SpecError("[scenario] fine_channels must list each fine channel once")
    delta = _number(sc.get("delta", DEFAULT_DELTA), "[scenario] delta")

    geo_raw = raw.get("geography", {})
    pieces = tuple(Piece(p["name"], p["state"], frozenset(map(str, p["counties"])))
                   for p in geo_raw.get("pieces", ()))
    metros = tuple(Metro(m, m) if isinstance(m, str) else Metro(m["name"], str(m["cbsa"]))
                   for m in geo_raw.get("metros", ()))
    metros = tuple(Metro(m.name if m.name != m.cbsa else f"M{m.cbsa}", m.cbsa) for m in metros)
    by_cbsa: dict = {}
    for m in metros:
        if m.cbsa in by_cbsa:
            raise SpecError(f"metros {by_cbsa[m.cbsa]} and {m.name} overlap: both are CBSA {m.cbsa}")
        by_cbsa[m.cbsa] = m.name
    check_metros(metros)
    units = tuple(CONUS_STATES) + tuple(p.name for p in pieces) + tuple(m.name for m in metros)
    if len(set(units)) != len(units):
        twice = sorted(u for u in set(units) if units.count(u) > 1)
        raise SpecError(f"unit names collide: {_show(twice)}")
    for p in pieces:
        if p.state not in CONUS_STATES:
            raise SpecError(f"piece {p.name}: {p.state!r} is not a CONUS state")
        wrong = [c for c in p.counties if not c.startswith(_STATEFP[p.state])]
        if wrong:
            raise SpecError(f"piece {p.name}: counties outside {p.state}: {_show(sorted(wrong))}")
    seen: dict = {}
    for p in pieces:
        for c in p.counties:
            if c in seen:
                raise SpecError(f"pieces {seen[c]} and {p.name} overlap in county {c}")
            seen[c] = p.name

    sets = {"all": frozenset(units)}
    for k, v in raw.get("sets", {}).items():
        if k in sets or k in units:
            raise SpecError(f"set name {k!r} collides with a unit or set")
        sets[k] = _units(v, sets, units, f"set {k}")

    channels = {}
    for cname, c in raw.get("channels", {}).items():
        channels[cname] = _channel(cname, c, sets, units, fine, delta)
    if not channels:
        raise SpecError("no [channels.X] sections")

    national = None
    if "national" in raw:
        n = raw["national"]
        national = National(n["channel"], frozenset(n["fine"]),
                            _units(n["units"], sets, units, "[national] units"),
                            dict(n.get("fallback", {})))
    spec = Spec(name, fine, units, pieces, metros, national, channels, path)
    check_partition(spec)
    check_national(spec)
    return spec


@functools.lru_cache(maxsize=1)
def _areas() -> dict:
    """{(layer, geoid): name} for the CBSA, CSA and metro-division rows of the committed 2025
    `areas.csv.gz` (#62)."""
    import csv
    import gzip
    import os

    from td import geo
    with gzip.open(os.path.join(geo.REFERENCE_DIR, "areas.csv.gz"), "rt", newline="") as fh:
        return {(r["layer"], r["geoid"]): r["name"] for r in csv.DictReader(fh)
                if r["layer"] in ("cbsa", "csa", "metdiv")}


def check_metros(metros, areas: dict | None = None) -> None:
    """Every metro is a 2025 metropolitan CBSA (OD5): its code must be a CBSA of the committed
    2025 areas table whose name ends ` Metro Area`.  A micropolitan CBSA, a CSA or metro-division
    code, or an unknown code is refused, naming it, before any ZIP is carved."""
    areas = _areas() if areas is None else areas
    bad = []
    for m in metros:
        name = areas.get(("cbsa", m.cbsa))
        if name is None:
            other = [layer for layer in ("csa", "metdiv") if (layer, m.cbsa) in areas]
            bad.append(f"{m.name} ({m.cbsa}): " + (f"a 2025 {other[0]} code, not a CBSA" if other
                                                    else "not a 2025 CBSA code"))
        elif not name.endswith(" Metro Area"):
            bad.append(f"{m.name} ({m.cbsa}): {name} is not a metropolitan CBSA")
    if bad:
        raise SpecError("metros must be 2025 metropolitan CBSAs (OD5): " + "; ".join(bad))


def _units(value, sets: dict, units: tuple, where: str) -> frozenset:
    def term(t):
        t = t.strip()
        if t in sets:
            return sets[t]
        if t in units:
            return frozenset([t])
        raise SpecError(f"{where}: {t!r} is not a unit or set")
    if isinstance(value, str):
        head, *rest = value.split(" - ")
        out = term(head)
        for r in rest:
            out = out - term(r)
        return out
    out = frozenset()
    for t in value:
        out |= _units(t, sets, units, where)
    return out


def _integer(value, where: str) -> int:
    """A count of at least 1.  TOML's `true` is refused: Python counts a bool as an int."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise SpecError(f"{where} must be an integer >= 1, not {value!r}")
    return value


def _number(value, where: str) -> float:
    """A number at least 0, as a float; a bool, a string or NaN is refused."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not value >= 0:
        raise SpecError(f"{where} must be a number >= 0, not {value!r}")
    return float(value)


def _channel(name, c, sets, units, fine, delta) -> ChannelSpec:
    known = {"k", "delta", "final_delta", "eta", "domain", "mode", "whole", "clipped", "free",
             "metro_mode", "max_size", "max_dist_km", "dist_km", "contact_caps",
             "extra_supports", "supports", "confine", "forbid_pairs", "hook"}
    if set(c) - known:
        raise SpecError(f"channel {name}: unknown keys {_show(sorted(set(c) - known))}")
    k = _integer(c.get("k"), f"channel {name}: k")
    d = _number(c.get("delta", delta), f"channel {name}: delta")
    fd = _number(c.get("final_delta", d), f"channel {name}: final_delta")
    eta = _number(c.get("eta", 0.0), f"channel {name}: eta")
    if not (d >= 0 and fd >= d):
        raise SpecError(f"channel {name}: need 0 <= delta <= final_delta")
    if not 0 < eta <= 1:
        raise SpecError(f"channel {name}: eta must be in (0, 1] (Claim 1)")
    domain: dict = {}
    for rule in c.get("domain", ()):
        fs = frozenset(rule["fine"])
        if fs - set(fine):
            raise SpecError(f"channel {name}: fine channels outside [scenario] fine_channels: "
                            f"{_show(sorted(fs - set(fine)))}")
        for u in _units(rule["units"], sets, units, f"channel {name} domain"):
            both = domain.get(u, frozenset()) & fs
            if both:
                raise SpecError(f"channel {name}: domain lists ({u}, {_show(sorted(both))}) twice")
            domain[u] = domain.get(u, frozenset()) | fs
    if not domain:
        raise SpecError(f"channel {name}: empty domain")
    default = c.get("mode", "whole")
    if default not in MODES:
        raise SpecError(f"channel {name}: mode {default!r} is not one of {MODES}")
    modes = dict.fromkeys(domain, default)
    listed: dict = {}
    for m in MODES:
        for u in _units(c.get(m, ()), sets, units, f"channel {name} {m}"):
            if u in listed:
                raise SpecError(f"channel {name}: unit {u} listed as {listed[u]} and {m}")
            if u not in domain:
                raise SpecError(f"channel {name}: unit {u} has a mode but is not in the domain")
            listed[u] = m
            modes[u] = m
    metro_mode = c.get("metro_mode", "clipped")
    if metro_mode not in SPLITTABLE:
        raise SpecError(f"channel {name}: metro_mode must be clipped or free")

    extras = []
    for s in c.get("extra_supports", ()):
        s = _units(s, sets, units, f"channel {name} extra_supports")
        if s - set(domain):
            raise SpecError(f"channel {name}: extra support holds units outside the domain: "
                            f"{_show(sorted(s - set(domain)))}")
        extras.append(s)
    supports = c.get("supports", "enumerate")
    if supports not in ("enumerate", "listed"):
        raise SpecError(f"channel {name}: supports must be 'enumerate' or 'listed'")
    if supports == "listed" and not extras:
        raise SpecError(f"channel {name}: supports = 'listed' needs extra_supports")
    pairs = set()
    for rule in c.get("confine", ()):
        who = _units(rule["units"], sets, units, f"channel {name} confine")
        allowed = _units(rule["partners"], sets, units, f"channel {name} confine") | who
        pairs |= {frozenset((u, w)) for u in who for w in domain if w not in allowed}
    for p in c.get("forbid_pairs", ()):
        p = _units(p, sets, units, f"channel {name} forbid_pairs")
        if len(p) != 2:
            raise SpecError(f"channel {name}: forbid_pairs entry {sorted(p)} is not a pair")
        pairs.add(p)
    caps = {str(u): _integer(v, f"channel {name}: contact_caps {u}")
            for u, v in c.get("contact_caps", {}).items()}
    dist = {str(u): _number(v, f"channel {name}: dist_km {u}")
            for u, v in c.get("dist_km", {}).items()}
    for u in list(caps) + list(dist):
        if u not in domain:
            raise SpecError(f"channel {name}: {u} has a cap but is not in the domain")
    max_size = _integer(c.get("max_size", DEFAULT_MAX_SIZE), f"channel {name}: max_size")
    max_dist = _number(c.get("max_dist_km", DEFAULT_MAX_DIST_KM), f"channel {name}: max_dist_km")
    return ChannelSpec(name, k, d, fd, eta, domain, modes, metro_mode, max_size, max_dist, dist,
                       caps, tuple(extras), supports == "listed", frozenset(pairs), c.get("hook"))


def check_partition(spec: Spec) -> None:
    """The channels' domains partition V × F: every (unit, fine channel) cell is in exactly one
    channel.  Raises SpecError naming the gaps and overlaps."""
    gaps, overlaps = [], []
    for u in spec.units:
        for f in spec.fine_channels:
            held = [c.name for c in spec.channels.values() if f in c.domain.get(u, ())]
            if not held:
                gaps.append(f"({u}, {f})")
            elif len(held) > 1:
                overlaps.append(f"({u}, {f}) in {'+'.join(held)}")
    msg = []
    if gaps:
        msg.append(f"{len(gaps)} cells in no channel: {_show(gaps)}")
    if overlaps:
        msg.append(f"{len(overlaps)} cells in two channels: {_show(overlaps)}")
    if msg:
        raise SpecError("the domains do not partition V × F: " + "; ".join(msg))


def check_national(spec: Spec) -> None:
    """The owner's purity and fallback rule (#67): a unit with national keeps its national fine
    channels in the national channel; a unit without it sends each to the planning channel that
    holds its fallback fine channel there."""
    n = spec.national
    if n is None:
        return
    if n.channel not in spec.channels:
        raise SpecError(f"[national] channel {n.channel!r} is not a channel")
    if n.fine - set(spec.fine_channels) or set(n.fallback) - n.fine:
        raise SpecError("[national] fine and fallback must name national fine channels of F")
    targets = set(n.fallback.values()) - (set(spec.fine_channels) - n.fine)
    if targets:
        raise SpecError(f"[national] fallback targets must be fine channels of F that are not "
                        f"national: {_show(sorted(targets))}")
    if set(spec.units) - n.units and set(n.fallback) != n.fine:
        raise SpecError(f"[national] units without national need a fallback for every national "
                        f"fine channel; none for {_show(sorted(n.fine - set(n.fallback)))}")
    bad = []
    for u in spec.units:
        for f in sorted(n.fine):
            got = spec.channel_of(u, f)
            if u in n.units:
                if got != n.channel:
                    bad.append(f"({u}, {f}) has national but is in {got}")
            else:
                if got == n.channel:
                    bad.append(f"({u}, {f}) has no national but is in {n.channel}")
                elif got != spec.channel_of(u, n.fallback[f]):
                    bad.append(f"({u}, {f}) is in {got}, not with {n.fallback[f]}")
    if bad:
        raise SpecError(f"[national] purity/fallback broken: {_show(bad)}")


def hook(spec: Spec, channel: str):
    """The channel's hook, looked up by name in `td.hooks`; None when it names none."""
    name = spec.channels[channel].hook
    if name is None:
        return None
    try:
        mod = importlib.import_module("td.hooks")
    except ImportError as e:
        raise SpecError(f"channel {channel}: hook {name!r} but td.hooks does not import") from e
    fn = getattr(mod, name, None)
    if not callable(fn):
        raise SpecError(f"channel {channel}: td.hooks has no hook {name!r}")
    return fn


# ------------------------------------------------------------------------------ the instance
@dataclass
class Units:
    """The units over a placed ZIP set and the ZIP graph among them."""
    unit_of: dict               # zip -> unit
    zips: dict                  # unit -> sorted tuple of its ZIPs
    zip_adj: dict               # zip -> set of adjacent ZIPs
    unit_adj: dict              # unit -> set of adjacent units
    centroid: dict              # unit -> (x_km, y_km)
    components: dict            # disconnected unit -> its ZIP components, largest first

    @classmethod
    def from_graph(cls, unit_of: dict, edges, xy: dict, weight: dict | None = None) -> "Units":
        zips: dict = {}
        for z in sorted(unit_of):
            zips.setdefault(unit_of[z], []).append(z)
        zips = {u: tuple(zs) for u, zs in zips.items()}
        zip_adj = {z: set() for z in unit_of}
        unit_adj = {u: set() for u in zips}
        for a, b, *_ in edges:
            if a in zip_adj and b in zip_adj and a != b:
                zip_adj[a].add(b)
                zip_adj[b].add(a)
                ua, ub = unit_of[a], unit_of[b]
                if ua != ub:
                    unit_adj[ua].add(ub)
                    unit_adj[ub].add(ua)
        centroid = {}
        for u, zs in zips.items():
            w = [1.0 if weight is None else float(weight.get(z, 0.0)) for z in zs]
            if sum(w) <= 0:
                w = [1.0] * len(zs)
            tot = sum(w)
            centroid[u] = (sum(wi * xy[z][0] for wi, z in zip(w, zs)) / tot / 1000.0,
                           sum(wi * xy[z][1] for wi, z in zip(w, zs)) / tot / 1000.0)
        components = {}
        for u, zs in zips.items():
            comps = zip_components(zs, zip_adj)
            if len(comps) > 1:
                components[u] = comps
        return cls(unit_of, zips, zip_adj, unit_adj, centroid, components)

    def distance_km(self, u: str, v: str) -> float:
        return math.dist(self.centroid[u], self.centroid[v])


def zip_components(zs, zip_adj) -> list:
    """The connected components of the ZIP graph induced on `zs`, largest first."""
    inside, seen, comps = set(zs), set(), []
    for z in sorted(zs):
        if z in seen:
            continue
        comp, stack = [], [z]
        seen.add(z)
        while stack:
            a = stack.pop()
            comp.append(a)
            for b in zip_adj[a]:
                if b in inside and b not in seen:
                    seen.add(b)
                    stack.append(b)
        comps.append(tuple(sorted(comp)))
    return sorted(comps, key=lambda c: (-len(c), c))


@dataclass
class Channel:
    """One planning channel on the instance: V_c, masses, modes and bands."""
    spec: ChannelSpec
    units: tuple                # V_c, zero-opportunity units dropped
    m: dict                     # zip -> m_z, for the ZIPs of V_c
    M: dict                     # unit -> M_v, for V_c
    mode: dict                  # unit -> mode, for V_c
    tau: float
    band: tuple                 # (L_c, U_c)
    final_band: tuple
    dropped_units: tuple        # units of the domain with M_v = 0

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def k(self) -> int:
        return self.spec.k

    def splittable(self, v: str) -> bool:
        return self.mode[v] in SPLITTABLE


@dataclass
class Instance:
    spec: Spec
    units: Units
    channels: dict              # name -> Channel, channels dropped for zero opportunity left out
    dropped_channels: tuple
    report: dict = field(default_factory=dict)


def build(spec: Spec, extract, reference=None, graph: dict | None = None) -> Instance:
    """The scenario on an extract: units from the 2025 reference table, the ZIP graph among the
    extract's placed ZIPs (`graph`: `{"vertices", "edges"}`, as `geo.zip_graph` returns), and
    per-channel masses.  Raises SpecError on a fine channel outside F, a disconnected whole
    unit, or pieces that overlap on the ZIPs.

    With no `graph`, the committed all-CONUS graph is used only when the extract holds every one
    of its vertices.  The graph is the Voronoi rook graph of the placed points (`td.geo`), so
    inducing the committed graph on a sparse extract would invent disconnections; a sparse
    extract must pass the graph `geo.zip_graph` builds on its own placed ZIPs."""
    from td import geo
    extra = sorted(set(extract.channels) - set(spec.fine_channels))
    if extra:
        raise SpecError(f"the extract has fine channels outside {spec.name}'s fine_channels: "
                        f"{_show(extra)}; placing them in a planning channel is #76's decision")
    ref = geo.read_reference() if reference is None else reference
    ref = ref.set_index("zcta")
    if graph is not None:
        vertices = set(graph["vertices"])
    else:
        vertices = set(ref.index[ref["graph_vertex"].astype(int) == 1])     # trap 21
        missing = vertices - set(extract.zips)
        if missing:
            raise SpecError(
                f"the extract is sparse: it lacks {len(missing)} of the committed graph's "
                f"{len(vertices)} vertices ({_show(sorted(missing))}), so the committed all-CONUS "
                "graph does not apply; pass the graph geo.zip_graph builds on its placed points")
    placed = [z for z in extract.zips if z in vertices and z in ref.index]
    off_graph = sorted(set(extract.zips) - set(placed))
    rows = ref.loc[placed]
    unit_of = carve(spec, dict(zip(placed, rows["state"])), dict(zip(placed, rows["county"])),
                    dict(zip(placed, rows["cbsa"])))
    xy = dict(zip(placed, zip(rows["x"].astype(float), rows["y"].astype(float))))
    land = dict(zip(placed, rows["aland_gaz"].astype(float)))
    edges = graph["edges"] if graph is not None else _reference_edges()
    cells = {}
    for z, f, m in zip(extract.z, extract.channel, extract.m_rel):
        if z in unit_of:
            cells[z, f] = cells.get((z, f), 0.0) + m
    return assemble(spec, Units.from_graph(unit_of, edges, xy, land), cells,
                    {"off_graph": off_graph})


def _reference_edges():
    import os

    import pandas as pd

    from td import geo
    e = pd.read_csv(os.path.join(geo.REFERENCE_DIR, "zcta_graph_edges.csv.gz"), dtype=str)
    return list(zip(e["a"], e["b"]))


def carve(spec: Spec, state: dict, county: dict, cbsa: dict) -> dict:
    """zip -> unit: a metro's ZIPs by CBSA, a piece's by county, the rest by state."""
    metro_of = {m.cbsa: m.name for m in spec.metros}
    piece_of = {c: p.name for p in spec.pieces for c in p.counties}
    out, both = {}, []
    for z, s in state.items():
        m, p = metro_of.get(cbsa.get(z, "")), piece_of.get(county.get(z, ""))
        if m and p:
            both.append(f"{z} ({m}, {p})")
        out[z] = m or p or s
    if both:
        raise SpecError(f"a metro and a piece overlap on {len(both)} ZIPs: {_show(both)}")
    return out


def assemble(spec: Spec, units: Units, cells: dict, report: dict | None = None) -> Instance:
    """Channels from `cells` `{(zip, fine): M}`: masses, drops, metro classes, the national
    checks and the connectivity check."""
    report = dict(report or {})
    unknown = sorted(set(units.zips) - set(spec.units))
    if unknown:
        raise SpecError(f"units not in {spec.name}: {_show(unknown)}")
    metros = {m.name for m in spec.metros}
    channels, dropped_channels = {}, []
    for c in spec.channels.values():
        m = {}
        for u, fs in c.domain.items():
            for z in units.zips.get(u, ()):
                m[z] = sum(cells.get((z, f), 0.0) for f in fs)
        M = {u: sum(m[z] for z in units.zips[u]) for u in c.domain if u in units.zips}
        keep = tuple(sorted(u for u, v in M.items() if v > 0))
        dropped = tuple(sorted(set(c.domain) - set(keep)))
        if not keep:
            dropped_channels.append(c.name)
            continue
        tau = sum(M[u] for u in keep) / c.k
        band = (tau * (1 - c.delta), tau * (1 + c.delta))
        mode = {}
        for u in keep:
            mode[u] = c.modes[u]
            if u in metros:         # OD5: classified once, against the declared U_c
                mode[u] = "whole" if M[u] <= band[1] else c.metro_mode
        channels[c.name] = Channel(
            c, keep, {z: m[z] for u in keep for z in units.zips[u]}, {u: M[u] for u in keep},
            mode, tau, band, (tau * (1 - c.final_delta), tau * (1 + c.final_delta)), dropped)
    report["dropped_units"] = {c.name: c.dropped_units for c in channels.values()
                               if c.dropped_units}
    report["dropped_channels"] = tuple(dropped_channels)
    report.update(national_report(spec, units, cells))
    report["disconnected"] = {u: [len(c) for c in comps]
                              for u, comps in units.components.items()}
    whole = sorted(u for u in units.components
                   if any(ch.mode.get(u) == "whole" for ch in channels.values()))
    if whole:
        raise SpecError("whole units that are not ZIP-connected (OQ6): " + "; ".join(
            f"{u}: {len(units.components[u])} components "
            + " | ".join(f"{len(c)} ZIPs {_show(c)}" for c in units.components[u])
            for u in whole))
    return Instance(spec, units, channels, tuple(dropped_channels), report)


def national_report(spec: Spec, units: Units, cells: dict) -> dict:
    """The owner's checks 1 and 2 (#67): national mass moved to fallback per unit without
    national, and units declared with national that have none."""
    n = spec.national
    if n is None:
        return {}
    mass = {u: sum(cells.get((z, f), 0.0) for z in zs for f in n.fine)
            for u, zs in units.zips.items()}
    return {"national_moved": {u: m for u, m in sorted(mass.items())
                               if u not in n.units and m > 0},
            "national_warnings": sorted(u for u, m in mass.items() if u in n.units and m == 0)}


_STATEFP = {
    "AL": "01", "AR": "05", "AZ": "04", "CA": "06", "CO": "08", "CT": "09", "DC": "11",
    "DE": "10", "FL": "12", "GA": "13", "IA": "19", "ID": "16", "IL": "17", "IN": "18",
    "KS": "20", "KY": "21", "LA": "22", "MA": "25", "MD": "24", "ME": "23", "MI": "26",
    "MN": "27", "MO": "29", "MS": "28", "MT": "30", "NC": "37", "ND": "38", "NE": "31",
    "NH": "33", "NJ": "34", "NM": "35", "NV": "32", "NY": "36", "OH": "39", "OK": "40",
    "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46", "TN": "47", "TX": "48",
    "UT": "49", "VA": "51", "VT": "50", "WA": "53", "WI": "55", "WV": "54", "WY": "56"}
