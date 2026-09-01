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
certificates.  Only rho > 0 mixes a log-scale term with a raw perimeter count and therefore
notices the scale -- see NWAY.md.

Three node classes come out of `cand(z) = {i : S_i(z) > 0}`:

    contested    >= 2 candidates   the actual decision problem
    uncontested  == 1 candidate    owner is forced; no binary, but the zip still carries
                                   utility into that rep's gain and occupies adjacency
    untapped     == 0 candidates   opportunity with nobody's book on it; no candidate can
                                   own it, so it is carried for adjacency only

`load_descaled` returns all three, and the caller decides.  Silently dropping the untapped
zips would change the graph's connectivity -- they are exactly the "zero-value glue" of
failure regime (d) -- so they stay in `G` and are named in the result instead.
"""
from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field

import networkx as nx

FORMAT = "td_instance_descaled/1"


@dataclass
class Descaled:
    G: "nx.Graph"                              # every zip, with cand/S/M/state
    contested: list = field(default_factory=list)    # >= 2 candidates
    uncontested: dict = field(default_factory=dict)  # zip -> its single forced owner
    untapped: list = field(default_factory=list)     # no candidate at all
    firm: dict = field(default_factory=dict)         # rep -> firm label
    meta: dict = field(default_factory=dict)

    @property
    def reps(self) -> list:
        return sorted({r for z in self.contested for r in self.G.nodes[z]["cand"]}
                      | set(self.uncontested.values()))

    def summary(self) -> str:
        return (f"{self.G.number_of_nodes():,} zips / {self.G.number_of_edges():,} edges; "
                f"{len(self.contested):,} contested, {len(self.uncontested):,} uncontested, "
                f"{len(self.untapped):,} untapped; {len(self.reps):,} reps")


def load_descaled(path, keep_untapped: bool = True) -> Descaled:
    """Read `instance_descaled.json.gz` into the N-way graph schema (`cand`, `S`, `M`)."""
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as fh:
        obj = json.load(fh)

    fmt = obj.get("format")
    if fmt != FORMAT:
        raise ValueError(f"{path}: format {fmt!r}, expected {FORMAT!r}")

    n = obj["nodes"]
    zips, m_rel, shares = n["z"], n["m_rel"], n["share"]
    states = n.get("state") or [""] * len(zips)
    if not (len(zips) == len(m_rel) == len(shares) == len(states)):
        raise ValueError(f"{path}: node columns have mismatched lengths")

    G = nx.Graph()
    contested, uncontested, untapped = [], {}, []
    for z, m, sh, st in zip(zips, m_rel, shares, states):
        m = float(m)
        S = {rep: float(s) * m for rep, s in sh.items()}       # S_i = s_i * m_rel
        cand = tuple(sorted(S))
        attrs = dict(cand=cand, S=S, M=m)
        if st:
            attrs["state"] = st
        G.add_node(z, **attrs)
        if len(cand) >= 2:
            contested.append(z)
        elif len(cand) == 1:
            uncontested[z] = cand[0]
        else:
            untapped.append(z)

    known = set(G)
    for u, v in zip(obj["edges"]["u"], obj["edges"]["v"]):
        if u in known and v in known:
            G.add_edge(u, v)

    if not keep_untapped:
        G.remove_nodes_from(untapped)

    return Descaled(G=G, contested=sorted(contested), uncontested=dict(sorted(uncontested.items())),
                    untapped=sorted(untapped), firm=dict(obj.get("firm") or {}),
                    meta=dict(obj.get("meta") or {}))


def check_descaled(d: Descaled, theta: float = 0.40) -> list:
    """Model validity on the loaded graph; empty list means clean.

    Headroom is checked in the descaled units, which is equivalent to the share form
    `1 >= max_i(s_i + theta*(t - s_i))` because both sides carry one factor of M.
    """
    from contig_methods import nway

    problems = []
    bad = nway.headroom_violations(d.G, theta=theta)
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
