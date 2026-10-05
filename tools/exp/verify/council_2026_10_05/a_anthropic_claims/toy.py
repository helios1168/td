"""Independent toy MODEL §3 master; no td imports or private data.

Mass units arbitrary, tau = total/K; all unit masses positive. Family contains
all connected unit subsets up to size_cap. Optional Hall and Menger rows.
LP enumeration builds share constraints independently of MILP assembly.
"""
from dataclasses import dataclass, field, replace
from itertools import combinations, combinations_with_replacement
from math import factorial, floor, inf, isfinite
import warnings

import networkx as nx
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp

# scipy forwards these options to HiGHS; same thread count throughout process.
warnings.filterwarnings("ignore", message="Unrecognized options detected.*")
TOL = 1e-7  # Assertion tolerance only; no change to solver feasibility defaults.


def subsets(items):
    items = tuple(sorted(items))
    for k in range(1, len(items) + 1):
        yield from combinations(items, k)


@dataclass
class Toy:
    name: str
    units: tuple  # ZIP -> unit
    masses: tuple  # ZIP -> nonnegative opportunity
    edges: tuple
    K: int
    delta: float = .15
    eta: float = .05
    modes: tuple = ()
    size_cap: int = 3
    caps: dict = field(default_factory=dict)
    margin: bool = False
    hall: bool = False
    menger: bool = True

    def __post_init__(self):
        self.V = tuple(sorted(set(self.units)))
        assert self.V == tuple(range(len(self.V)))
        assert len(self.units) == len(self.masses)
        assert all(m >= 0 for m in self.masses) and self.K > 0
        assert 0 <= self.eta <= 1
        self.Z = {v: tuple(z for z, u in enumerate(self.units) if u == v) for v in self.V}
        self.M = {v: sum(self.masses[z] for z in self.Z[v]) for v in self.V}
        assert all(m > 0 for m in self.M.values())
        self.tau = sum(self.masses) / self.K
        self.L, self.U = self.tau * (1 - self.delta), self.tau * (1 + self.delta)
        self.modes = self.modes or ("free",) * len(self.V)
        assert len(self.modes) == len(self.V)
        self.zipgraph = nx.Graph()
        self.zipgraph.add_nodes_from(range(len(self.units)))
        self.zipgraph.add_edges_from(self.edges)
        self.graph = nx.Graph()
        self.graph.add_nodes_from(self.V)
        self.graph.add_edges_from((self.units[a], self.units[b]) for a, b in self.edges
                                  if self.units[a] != self.units[b])
        self.family = tuple(s for s in subsets(self.V)
                            if len(s) <= self.size_cap and nx.is_connected(self.graph.subgraph(s)))
        self.weights = {s: max(s) - min(s) for s in self.family}  # Collinear unit centroids.
        self.border = {(v, u): frozenset(z for z in self.Z[v]
                                       if any(self.units[q] == u for q in self.zipgraph[z]))
                       for v in self.V for u in self.graph[v]}
        self.corridor, self.kappa = {}, {}
        for s in self.family:
            g = self.graph.subgraph(s)
            for v in nx.articulation_points(g):
                parts = list(nx.connected_components(g.subgraph(set(s) - {v})))
                boundaries = [set().union(*(self.border[v, u] for u in p if (v, u) in self.border))
                              for p in parts]
                floors, cuts = [], []
                for i, source in enumerate(boundaries):
                    target = set().union(*(b for j, b in enumerate(boundaries) if j != i))
                    # ponytail: exhaustive subset paths/cuts; toy units <= 6 ZIPs.
                    paths = [set(p) for p in subsets(self.Z[v]) if set(p) & source and set(p) & target
                             and nx.is_connected(self.zipgraph.subgraph(p))]
                    floors.append(min((sum(self.masses[z] for z in p) for p in paths), default=inf))
                    cuts.append(next((len(c) for c in ((), *subsets(self.Z[v]))
                                      if all(set(c) & p for p in paths)), 0))
                self.corridor[s, v] = max(floors)
                self.kappa[s, v] = min(cuts)
        self.nrows = []
        for v in self.V:
            self.nrows.append((tuple(s for s in self.family if v in s), self.contact_cap(v)))
            if self.modes[v] == "free":
                for u in self.graph[v]:
                    self.nrows.append((tuple(s for s in self.family if v in s
                                             and set(self.graph[v]) & set(s) == {u}), len(self.border[v, u])))
                if self.hall:
                    for h in subsets(self.graph[v]):
                        h = set(h)
                        used = tuple(s for s in self.family if v in s
                                     and set(self.graph[v]) & set(s)
                                     and set(self.graph[v]) & set(s) <= h)
                        self.nrows.append((used, len(set().union(*(self.border[v, u] for u in h)))))
        for (s, v), c in self.corridor.items():
            if not isfinite(c):
                self.nrows.append(((s,), 0))
            if self.menger:
                self.nrows.append(((s,), self.kappa[s, v]))

    def contact_cap(self, v):
        eta_cap = floor(1 / self.eta + 1e-12) if self.eta else self.K
        return min(self.K, eta_cap, self.caps.get(v, self.K), len(self.Z[v]))

    def held(self, v, s):
        return self.modes[v] == "whole" or (self.modes[v] == "clipped" and len(s) > 1)

    def mu(self, s):
        return sum(max(self.masses[z] for z in self.Z[v]) for v in s
                   if self.modes[v] != "whole") if self.margin else 0

    def counts(self, n):
        return {v: sum(k for s, k in n.items() if v in s) for v in self.V}

    def key(self, n):
        r = self.counts(n)
        return (sum(k >= 2 for k in r.values()), sum(self.weights[s] * k for s, k in n.items()))


def share_lp(toy, n):
    """Fixed integer plan; active shares only, independent of MILP row builder."""
    if any(sum(n.get(s, 0) for s in ss) > cap for ss, cap in toy.nrows):
        return None
    cols = [(v, s) for s in n for v in s]
    if any(not any(u == v for u, _ in cols) for v in toy.V):
        return None
    index = {x: i for i, x in enumerate(cols)}
    bounds = []
    for v, s in cols:
        k = n[s]
        if toy.held(v, s):
            if k > 1:
                return None
            bounds.append((1, 1))
        else:
            bounds.append((toy.eta * k, min(k, 1)))
            if bounds[-1][0] > bounds[-1][1]:
                return None
    eq, rhs, ub, upper = [], [], [], []
    for v in toy.V:
        eq.append([float(u == v) for u, _ in cols])
        rhs.append(1)
    for s, k in n.items():
        row = [toy.M[v] if t == s else 0 for v, t in cols]
        ub.extend([row, [-x for x in row]])
        upper.extend([(toy.U - toy.mu(s)) * k, -(toy.L + toy.mu(s)) * k])
        for v in s:
            c = toy.corridor.get((s, v), 0)
            if not isfinite(c):
                return None
            if c:
                row = [0.] * len(cols)
                row[index[v, s]] = -toy.M[v]
                ub.append(row)
                upper.append(-c * k)
    out = linprog(np.arange(1, len(cols) + 1, dtype=float), A_ub=ub, b_ub=upper,
                  A_eq=eq, b_eq=rhs, bounds=bounds, method="highs-ds", options={"threads": 1})
    assert out.status in (0, 2), out.message
    return dict(zip(cols, out.x)) if out.status == 0 else None


def enumerate_plans(toy):
    feasible, tested = [], 0
    for copies in combinations_with_replacement(toy.family, toy.K):
        tested += 1
        n = {s: copies.count(s) for s in set(copies)}
        t = share_lp(toy, n)
        if t is not None:
            feasible.append((toy.key(n), n, t))
    return feasible, tested


def solve(toy, objective="splits", pin=None, cutoff=None, fixed_n=None):
    """F2 MILP with all shares. Solver defaults except both MIP gaps and threads."""
    nc = {s: i for i, s in enumerate(toy.family)}
    tc = {(v, s): len(nc) + i for i, (v, s) in
          enumerate((v, s) for s in toy.family for v in s)}
    sc = {v: len(nc) + len(tc) + i for i, v in enumerate(toy.V)}
    size = len(nc) + len(tc) + len(sc)
    lo, hi = np.zeros(size), np.ones(size)
    integer, cost = np.zeros(size), np.zeros(size)
    for s, i in nc.items():
        integer[i], hi[i] = 1, toy.K
        if any(toy.held(v, s) for v in s):
            hi[i] = 1
        if fixed_n is not None:
            lo[i] = hi[i] = fixed_n.get(s, 0)
    for v, i in sc.items():
        integer[i] = 1
        if toy.modes[v] == "whole":
            hi[i] = 0
    if objective == "splits":
        cost[list(sc.values())] = 1
    elif objective in ("diameter", "blend"):
        eps = .5 / (toy.K * max(toy.weights.values(), default=0)) if objective == "blend" else 1
        for s, i in nc.items():
            cost[i] = eps * toy.weights[s]
        if objective == "blend":
            cost[list(sc.values())] = 1
    else:
        raise ValueError(objective)
    rows, lower, upper = [], [], []

    def row(coefs, low=-inf, high=inf):
        a = np.zeros(size)
        for i, c in coefs.items():
            a[i] = c
        rows.append(a)
        lower.append(low)
        upper.append(high)

    row({i: 1 for i in nc.values()}, toy.K, toy.K)
    for v in toy.V:
        row({i: 1 for (u, s), i in tc.items() if u == v}, 1, 1)
        r = {i: 1 for s, i in nc.items() if v in s}
        row({**r, sc[v]: -(toy.contact_cap(v) - 1)}, high=1)
    for s, ni in nc.items():
        for v in s:
            ti = tc[v, s]
            row({ti: 1, ni: -toy.eta}, low=0)
            row({ti: 1, ni: -1}, high=0)
            if toy.held(v, s):
                row({ti: 1, ni: -1}, 0, 0)
            c = toy.corridor.get((s, v), 0)
            if c and isfinite(c):
                row({ti: toy.M[v], ni: -c}, low=0)
        mass = {tc[v, s]: toy.M[v] for v in s}
        row({**mass, ni: -(toy.L + toy.mu(s))}, low=0)
        row({**mass, ni: -(toy.U - toy.mu(s))}, high=0)
    for ss, cap in toy.nrows:
        row({nc[s]: 1 for s in ss}, high=cap)
    if pin is not None:
        row({i: 1 for i in sc.values()}, pin, pin)
    if cutoff is not None:
        row({i: 1 for i in sc.values()}, high=cutoff)
    a, lower, upper = np.array(rows), np.array(lower), np.array(upper)
    result = milp(cost, integrality=integer, bounds=Bounds(lo, hi),
                  constraints=LinearConstraint(a, lower, upper),
                  options={"mip_rel_gap": 0., "mip_abs_gap": 0., "threads": 1})
    assert result.status in (0, 2), result.message
    if result.status == 2:
        return None
    x = result.x
    assert max(np.max(lower - a @ x), np.max(a @ x - upper),
               np.max(lo - x), np.max(x - hi)) <= TOL
    assert max(abs(x[i] - round(x[i])) for i in np.flatnonzero(integer)) <= TOL
    n = {s: int(round(x[i])) for s, i in nc.items() if x[i] > .5}
    return toy.key(n), n, {v: int(round(x[i])) for v, i in sc.items()}


def colourings(N, K):
    """All surjective K-colourings modulo colour permutations (restricted growth).

    Every unlabelled plan represents exactly K! labelled colourings; no geography
    or balance pruning. Non-surjective colourings cannot have K nonempty districts.
    """
    def visit(prefix, top):
        if len(prefix) == N:
            if top == K - 1:
                yield tuple(prefix)
            return
        for c in range(min(K - 1, top + 1) + 1):
            yield from visit(prefix + [c], max(top, c))
    yield from visit([0], 0)


def drawings(toy, policy=True, band=True):
    N = len(toy.units)
    mass, connected, foot, shares = {}, {}, {}, {}
    for mask in range(1, 1 << N):
        zs = [z for z in range(N) if mask >> z & 1]
        mass[mask] = sum(toy.masses[z] for z in zs)
        connected[mask] = nx.is_connected(toy.zipgraph.subgraph(zs))
        foot[mask] = tuple(sorted({toy.units[z] for z in zs}))
        shares[mask] = {v: sum(toy.masses[z] for z in zs if toy.units[z] == v) / toy.M[v]
                        for v in foot[mask]}
    kept, tested = [], 0
    for col in colourings(N, toy.K):
        tested += 1
        masks = [0] * toy.K
        for z, c in enumerate(col):
            masks[c] |= 1 << z
        if not all(connected[m] and (not band or toy.L - TOL <= mass[m] <= toy.U + TOL)
                   for m in masks):
            continue
        r = {v: sum(v in foot[m] for m in masks) for v in toy.V}
        if policy:
            if any(foot[m] not in toy.family or any(t + TOL < toy.eta for t in shares[m].values())
                   for m in masks):
                continue
            if any(r[v] > toy.caps.get(v, toy.K) or (toy.modes[v] == "whole" and r[v] != 1)
                   or (toy.modes[v] == "clipped" and r[v] > 1
                       and any(v in foot[m] and len(foot[m]) > 1 for m in masks)) for v in toy.V):
                continue
        key = (sum(k >= 2 for k in r.values()), sum(toy.weights.get(foot[m], 0) for m in masks))
        n = {s: sum(foot[m] == s for m in masks) for s in set(foot[m] for m in masks)}
        kept.append((key, col, n, max(abs(mass[m] / toy.tau - 1) for m in masks)))
    return kept, tested


def check_instance(toy, draw=True):
    plans, tested = enumerate_plans(toy)
    assert plans, toy.name
    optimum = min(p[0] for p in plans)
    a = solve(toy)
    b = solve(toy, "diameter", pin=optimum[0])
    assert a[0][0] == optimum[0] and b[0] == optimum
    if max(toy.weights.values()) > 0:
        assert solve(toy, "blend")[0] == optimum
    assert solve(toy, cutoff=optimum[0] - 1) is None
    # Check every integer plan, including LP-infeasible ones, against fixed-n MILP.
    feasible = {tuple(n.get(s, 0) for s in toy.family): key for key, n, _ in plans}
    for copies in combinations_with_replacement(toy.family, toy.K):
        n = {s: copies.count(s) for s in set(copies)}
        key = feasible.get(tuple(n.get(s, 0) for s in toy.family))
        out = solve(toy, fixed_n=n)
        assert (out is None) == (key is None), (toy.name, n)
        if out is not None:
            assert out[0][0] == key[0]
            assert sum(out[2].values()) == key[0]
    ds, colours = drawings(toy) if draw else ([], 0)
    for key, col, n, delta in ds:
        assert key >= optimum
        assert share_lp(toy, n) is not None
    print(f"{toy.name}: units={len(toy.V)} ZIPs={len(toy.units)} integer_plans={tested} "
          f"feasible={len(plans)} lex={optimum} drawings={len(ds)}/{colours} "
          f"labelled_surjective={colours * factorial(toy.K)}")
    return plans, optimum, ds


def path_toy(N=6, K=3):
    masses = ((.6, .4), (.9, .5), (.5, .3), (.8, .4), (.5, .1), (.6, .4))
    units = tuple(v for v in range(N) for _ in range(2))
    ms = tuple(x for pair in (masses if N == 6 else ((.6, .4),) * N) for x in pair)
    return Toy(f"path{N}_K{K}", units, ms, tuple((z, z + 1) for z in range(2 * N - 1)), K,
               size_cap=3)


def pad(toy):
    """Three isolated whole units, each of mass tau; preserves original obstruction."""
    extra = 6 - len(toy.V)
    return replace(toy, name=toy.name + "_six", units=toy.units + tuple(range(len(toy.V), 6)),
                   masses=toy.masses + (toy.tau,) * extra, K=toy.K + extra,
                   modes=toy.modes + ("whole",) * extra)
