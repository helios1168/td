"""descaled.py -- load the descaled real instance written by tools/instance_export.

The export carries shares `s_i(z) = S_i(z)/M_z` and a relative opportunity
`m_rel(z) = M_z/kappa`, kappa being the median positive opportunity.  Reconstructing the
model's own fields is a multiplication::

    S_i(z) = s_i(z) * m_rel(z)          # == real S_i / kappa
    M(z)   = m_rel(z)                   # == real M   / kappa

so the loaded graph is the real instance divided throughout by one constant -- exactly, up
to the 6-significant-figure rounding the exporter applies on write (a relative error around
1e-6, orders of magnitude below anything the model resolves).  At rho = 0
the objective `sum_i log g_i` is invariant to that constant (it shifts by n*log kappa), so
this graph and the real one have the same optimal allocations, the same gaps and the same
certificates -- at every rho >= 0, not only at rho = 0.  Rescaling shifts `sum log g_i` by
`n log kappa`, the same constant for every partition, and the perimeter is a combinatorial
count, so every objective *difference* is untouched and rho transports unchanged.  (An earlier
note here claimed rho > 0 broke this; it does not -- the log term's scale dependence is
additive and constant, so it cancels in every comparison.)  What descaling does change is
conditioning: solver feasibility tolerances are absolute in gain units.

Four node classes come out of `cand(z) = {i : S_i(z) > 0}`, filler keys excluded:

    contested    >= 2 candidates   the actual decision problem
    uncontested  == 1 candidate    owner is forced; no binary, but the zip still carries
                                   utility into that rep's gain and occupies adjacency
    vacant       == 0 candidates   sales exist but only under a vacancy filler key -- real
                                   book, real firm, no incumbent person.  Nobody can claim
                                   it by legacy, which makes these the zips most genuinely
                                   up for grabs.
    untapped     == 0 candidates   no sales at all; opportunity with nobody's book on it

`load_descaled` returns all four, and the caller decides.  Silently dropping untapped or
vacant zips would change the graph's connectivity -- they are exactly the "zero-value glue"
of failure regime (d) -- so they stay in `G` and are named in the result instead.

Filler book arrives as the node attribute `S_free` and is *never* a candidate: an objective
term for a vacancy would have the solver bargaining on behalf of an empty chair.  It is
still real production, so it stays in the instance and every candidate capitalises it at a
rate set by `nway.utilities(filler_capture=...)` -- see NWAY.md 6.7.

Format 2 (`td_instance_descaled/2`) is the same file with the node table long by
(zip, channel): one row per cell, with a `channel` column beside `m_rel`, `share` and
`share_free`, which mean per cell exactly what they mean per zip in format 1.  The loader
sums a zip's cells, so `M`, `S`, `S_free` and `cand` are what format 1 would carry for the
summed row, and adds `M_c`, `S_c`, `S_free_c` for the split.  `Descaled.channels` names the
channels in file order, and is empty on format 1.
"""
from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field

import networkx as nx

FORMAT = "td_instance_descaled/1"
FORMAT_V2 = "td_instance_descaled/2"


@dataclass
class Descaled:
    G: "nx.Graph"                              # every zip, with cand/S/M/state
    contested: list = field(default_factory=list)    # >= 2 candidates
    uncontested: dict = field(default_factory=dict)  # zip -> its single forced owner
    vacant: list = field(default_factory=list)       # only filler book; no candidate
    untapped: list = field(default_factory=list)     # no sales at all
    firm: dict = field(default_factory=dict)         # rep -> firm label
    meta: dict = field(default_factory=dict)
    channels: tuple[str, ...] = ()                   # format 2 only; () on format 1

    @property
    def reps(self) -> list:
        return sorted({r for z in self.contested for r in self.G.nodes[z]["cand"]}
                      | set(self.uncontested.values()))

    def summary(self) -> str:
        return (f"{self.G.number_of_nodes():,} zips / {self.G.number_of_edges():,} edges; "
                f"{len(self.contested):,} contested, {len(self.uncontested):,} uncontested, "
                f"{len(self.vacant):,} vacant, {len(self.untapped):,} untapped; "
                f"{len(self.reps):,} reps")

    @property
    def undecided(self) -> list:
        """Zips no candidate can own: vacant plus untapped.  Needs an allocation rule."""
        return sorted(self.vacant + self.untapped)


def _zip_rows(zips, m_rel, shares, states, free):
    """Format 1: one row per zip, put into model units (`S_i = s_i * m_rel`)."""
    for z, m, sh, st, fr in zip(zips, m_rel, shares, states, free):
        m = float(m)
        yield z, m, {rep: float(s) * m for rep, s in sh.items()}, float(fr or 0.0) * m, st, {}


def _fold_cells(path, zips, chan, m_rel, shares, states, free):
    """Format 2: sum each zip's (zip, channel) cells, keeping the per-channel split.

    Every quantity the model reads is additive over cells, so a zip's totals are exactly
    what format 1 carries for the summed row.  The breakdown rides along as the node
    attributes `M_c`, `S_c` and `S_free_c`, each keyed by the channels that zip has.
    """
    M, S, S_free, state = {}, {}, {}, {}
    M_c, S_c, S_free_c = {}, {}, {}
    for z, c, m, sh, st, fr in zip(zips, chan, m_rel, shares, states, free):
        m = float(m)
        f = float(fr or 0.0) * m
        if z not in M:
            M[z], S[z], S_free[z], state[z] = 0.0, {}, 0.0, ""
            M_c[z], S_c[z], S_free_c[z] = {}, {}, {}
        if c in M_c[z]:
            raise ValueError(f"{path}: zip {z} carries channel {c!r} twice")
        M[z] += m
        S_free[z] += f
        if st and not state[z]:
            state[z] = st
        M_c[z][c], S_free_c[z][c] = m, f
        for rep, s in sh.items():
            v = float(s) * m
            S[z][rep] = S[z].get(rep, 0.0) + v
            S_c[z].setdefault(rep, {})[c] = v
    for z in M:
        yield (z, M[z], S[z], S_free[z], state[z],
               dict(M_c=M_c[z], S_c=S_c[z], S_free_c=S_free_c[z]))


def load_descaled(path, keep_untapped: bool = True) -> Descaled:
    """Read `instance_descaled.json.gz` into the N-way graph schema (`cand`, `S`, `M`)."""
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as fh:
        obj = json.load(fh)

    fmt = obj.get("format")
    if fmt not in (FORMAT, FORMAT_V2):
        raise ValueError(f"{path}: format {fmt!r}, expected {FORMAT!r} or {FORMAT_V2!r}")

    n = obj["nodes"]
    zips, m_rel, shares = n["z"], n["m_rel"], n["share"]
    states = n.get("state") or [""] * len(zips)
    free = n.get("share_free") or [0.0] * len(zips)
    if not (len(zips) == len(m_rel) == len(shares) == len(states) == len(free)):
        raise ValueError(f"{path}: node columns have mismatched lengths")

    if fmt == FORMAT_V2:
        chan = n["channel"]
        if len(chan) != len(zips):
            raise ValueError(f"{path}: node columns have mismatched lengths")
        channels = tuple(dict.fromkeys(chan))
        # A sparse export emits no row for a cell a zip lacks, so first appearance over the
        # rows need not be the writer's own channel order.  `meta["channels"]` is that order;
        # honour it when it names the same set, and fall back to first appearance otherwise.
        declared = tuple(obj.get("meta", {}).get("channels") or ())
        if declared and set(declared) == set(channels):
            channels = declared
        rows = _fold_cells(path, zips, chan, m_rel, shares, states, free)
    else:
        channels = ()
        rows = _zip_rows(zips, m_rel, shares, states, free)

    G = nx.Graph()
    contested, uncontested, vacant, untapped = [], {}, [], []
    for z, m, S, s_free, st, extra in rows:
        cand = tuple(sorted(S))
        attrs = dict(cand=cand, S=S, M=m, S_free=s_free)
        if st:
            attrs["state"] = st
        attrs.update(extra)
        G.add_node(z, **attrs)
        if len(cand) >= 2:
            contested.append(z)
        elif len(cand) == 1:
            uncontested[z] = cand[0]
        elif s_free > 0:
            vacant.append(z)
        else:
            untapped.append(z)

    known = set(G)
    for u, v in zip(obj["edges"]["u"], obj["edges"]["v"]):
        if u in known and v in known:
            G.add_edge(u, v)

    if not keep_untapped:
        G.remove_nodes_from(untapped)

    return Descaled(G=G, contested=sorted(contested),
                    uncontested=dict(sorted(uncontested.items())),
                    vacant=sorted(vacant), untapped=sorted(untapped),
                    firm=dict(obj.get("firm") or {}), meta=dict(obj.get("meta") or {}),
                    channels=channels)


def check_descaled(d: Descaled, theta: float = 0.40) -> list:
    """Model validity on the loaded graph; empty list means clean.

    Headroom is checked in the descaled units, which is equivalent to the share form
    `1 >= max_i(s_i + theta*(t - s_i))` because both sides carry one factor of M.
    """
    from . import model

    problems = []
    # the export format rounds to 6 significant figures and t sums up to ~100 rounded
    # shares, so deficits up to a few 1e-5 are format rounding, not data violations
    bad = model.headroom_violations(d.G, theta=theta, tol=5e-5)
    if bad:
        worst = max(need - M for _, M, need in bad)
        problems.append(f"{len(bad)} zip(s) violate pointwise headroom at theta={theta} "
                        f"(worst deficit {worst:.6g})")
    neg = [z for z in d.G if any(v < 0 for v in d.G.nodes[z]["S"].values())
           or d.G.nodes[z]["M"] < 0]
    if neg:
        problems.append(f"{len(neg)} zip(s) with a negative S or M (e.g. {neg[:3]})")
    ms = sorted(d.G.nodes[z]["M"] for z in d.G)
    if ms:
        med = ms[len(ms) // 2]
        if not (0.5 <= med <= 2.0):
            problems.append(f"median M is {med:.6g}, expected ~1.0 -- this does not look "
                            f"like a descaled instance")
    stray = [z for z in d.contested
             if set(d.G.nodes[z]["cand"]) != set(d.G.nodes[z]["S"])]
    if stray:
        problems.append(f"{len(stray)} zip(s) whose cand and S disagree (e.g. {stray[:3]})")
    return problems


def subproblem(d: Descaled, nodes) -> list:
    """The contested nodes of `nodes`, in a stable order -- what a solver actually decides.

    Uncontested and untapped zips are not decisions, but they are still part of the graph
    the contiguity constraints see, so callers pass the full node set to `nway.pieces` and
    this list to the engine.
    """
    keep = set(nodes)
    return [z for z in d.contested if z in keep]
