"""sepcuts.py -- integer and fractional a,b-separator cuts for the districts of an instance (#142).

For a district j on its graph G_j (the ZCTAs it may own and its own body vertices, `Inst.adj`),
a vertex set S ⊆ V(G_j) ∖ {a, b} that separates a from b in G_j gives the valid inequality

    x_a + x_b − Σ_{s ∈ S} x_s ≤ 1                                              (Validi–Buchanan–Lykhovyd)

for every connected set of j containing a and b (any a-b path of the set crosses S).  A body
vertex has x = 1 and moves into the right-hand side.  `integer_cuts` takes a drawing, and for each
component C of a district's selected vertices other than the main one (the one with the root
body, else the heaviest) builds, for every a ∈ C and one b in the main component, the *minimal*
separator S ⊆ N(C) (Fischetti et al.; N(C) shrunk from b's side, then from a's): every s ∈ S has
a neighbour in the component of a and one in the component of b in G_j − S, so no vertex can be
dropped and the row is as strong as a separator row of this kind gets.  Every row cuts off the
drawing it was made for (its separator holds no selected vertex).  `fractional_cuts` separates
violated rows from a fractional x by max flow with vertex capacities x.
"""
from __future__ import annotations

import collections
import math

import numpy as np

Row = tuple     # (lo, hi, idx tuple, val tuple); lo or hi None for unbounded


class Graphs:
    """The per-district graphs of an `inst_io.Inst`, and cut generation on them."""

    def __init__(self, inst):
        self.inst = inst
        self.js = inst.js
        self.mass = inst.mass
        self.seen: set = set()

    # ---------------------------------------------------------------- components
    def selected(self, j: str, x) -> set:
        """j's vertices a 0/1 column vector `x` selects, its body vertices included."""
        i = self.inst
        return {z for (z, k), c in i.xcol.items() if k == j and x[c] > 0.5} | i.fixed[j]

    def components(self, j: str, sel: set) -> list:
        """The components of `sel` on G_j, main first: the one holding j's root body, else the
        heaviest (mass, then size, then smallest id)."""
        adj = self.inst.adj[j]
        seen, out = set(), []
        for s in sorted(sel):
            if s in seen:
                continue
            comp, stack = {s}, [s]
            seen.add(s)
            while stack:
                a = stack.pop()
                for b in adj[a]:
                    if b in sel and b not in seen:
                        seen.add(b)
                        comp.add(b)
                        stack.append(b)
            out.append(comp)
        root = self.inst.root.get(j)

        def key(c):
            return (root in c if root else False, math.fsum(self.mass.get(v, 0.0) for v in c),
                    len(c), min(c))
        return sorted(out, key=key, reverse=True)

    def detached(self, x) -> dict:
        """{district: [components after the main one]} of the drawing `x`, only those with some."""
        out = {}
        for j in self.js:
            comps = self.components(j, self.selected(j, x))
            if len(comps) > 1:
                out[j] = comps[1:]
        return out

    # ---------------------------------------------------------------- separators
    def _reach(self, j: str, start, blocked: set) -> set:
        adj = self.inst.adj[j]
        seen = {s for s in start if s not in blocked}
        stack = list(seen)
        while stack:
            for b in adj[stack.pop()]:
                if b not in seen and b not in blocked:
                    seen.add(b)
                    stack.append(b)
        return seen

    def _ring(self, j: str, comp: set) -> set:
        adj = self.inst.adj[j]
        return {b for a in comp for b in adj[a]} - comp

    def minimal_separator(self, j: str, comp_a: set, b: str) -> set:
        """A minimal a,b-separator in G_j for the connected set `comp_a` ∌ b with b ∉ N(comp_a):
        N(comp_a) cut down from b's side, then from a's."""
        s0 = self._ring(j, comp_a)
        cb = self._reach(j, [b], s0)
        s1 = self._ring(j, cb)
        ca = self._reach(j, comp_a, s1)
        return self._ring(j, ca)

    def row(self, j: str, a: str, b: str, sep) -> Row:
        """x_a + x_b − Σ_S x_s ≤ 1, with a body vertex's x = 1 moved to the bound."""
        i = self.inst
        rhs = 1.0
        idx, val = [], []
        for v in (a, b):
            if v in i.fixed[j]:
                rhs -= 1.0
            else:
                idx.append(i.xcol[v, j])
                val.append(1.0)
        for s in sorted(sep):
            if s in i.fixed[j]:         # never in a separator made from unselected vertices; kept valid
                rhs += 1.0
            else:
                idx.append(i.xcol[s, j])
                val.append(-1.0)
        return (None, rhs, tuple(idx), tuple(val))

    def integer_cuts(self, x, max_per_component: int | None = None) -> list:
        """New separator rows cutting off the 0/1 drawing `x`: one per ZCTA a of each detached
        component, with b the heaviest vertex of the main component that is a variable of j (its
        root body vertex when j has one).  Rows already produced are not repeated."""
        i = self.inst
        out = []
        for j, comps in self.detached(x).items():
            main = self.components(j, self.selected(j, x))[0]
            root = i.root.get(j)
            b = root if root else max(main, key=lambda v: (self.mass.get(v, 0.0), v))
            for comp in comps:
                sep = self.minimal_separator(j, comp, b)
                members = sorted(comp, key=lambda v: (-self.mass.get(v, 0.0), v))
                if max_per_component is not None:
                    members = members[:max_per_component]
                for a in members:
                    key = (j, a, b, tuple(sorted(sep)))
                    if key in self.seen:
                        continue
                    self.seen.add(key)
                    out.append(self.row(j, a, b, sep))
        return out

    # ---------------------------------------------------------------- fractional separation
    def fractional_cuts(self, x, eps: float = 1e-4, max_cuts: int = 50, min_x: float = 0.05) -> list:
        """Rows x_a + x_b − Σ_S x_s ≤ 1 violated by more than `eps` at the fractional `x`, from
        the minimum vertex cut (capacities x) between b and a: b is the root body vertex, else
        the district's vertex of largest x; a runs over the vertices with x ≥ `min_x`, largest
        first.  At most `max_cuts` rows."""
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import breadth_first_order, maximum_flow
        i = self.inst
        out = []
        scale = 10 ** 6
        big = 10 ** 9
        for j in self.js:
            nodes = sorted(i.nodes[j])
            ix = {v: k for k, v in enumerate(nodes)}
            val = {v: (1.0 if v in i.fixed[j] else float(x[i.xcol[v, j]])) for v in nodes}
            root = i.root.get(j)
            b = root if root else max(nodes, key=lambda v: (val[v], self.mass.get(v, 0.0), v))
            if val[b] < min_x:
                continue
            n = len(nodes)
            # vertex v: in = 2k, out = 2k + 1; arc in -> out has capacity x_v
            rows, cols, cap = [], [], []
            for v in nodes:
                k = ix[v]
                c = big if v in i.fixed[j] else max(0, int(round(val[v] * scale)))
                rows.append(2 * k), cols.append(2 * k + 1), cap.append(c)
                for w in i.adj[j][v]:
                    rows.append(2 * k + 1), cols.append(2 * ix[w]), cap.append(big)
            graph = csr_matrix((cap, (rows, cols)), shape=(2 * n, 2 * n), dtype=np.int32)
            targets = sorted((v for v in nodes if v != b and val[v] >= min_x),
                             key=lambda v: (-val[v], v))
            for a in targets:
                if len(out) >= max_cuts:
                    return out
                need = val[a] + val[b] - 1.0
                if need <= eps:
                    continue
                # flow from b's out-node to a's in-node: a and b do not bound it
                flow = maximum_flow(graph, 2 * ix[b] + 1, 2 * ix[a])
                if flow.flow_value / scale >= need - eps:
                    continue
                resid = (graph - flow.flow).tocsr()
                resid.data = np.where(resid.data > 0, 1, 0)
                resid.eliminate_zeros()
                reach = set(breadth_first_order(resid, 2 * ix[b] + 1, directed=True,
                                                return_predecessors=False).tolist())
                sep = {v for v in nodes if 2 * ix[v] in reach and 2 * ix[v] + 1 not in reach}
                if a in sep or b in sep:
                    continue
                row = self.row(j, a, b, sep)
                key = (j, a, b, tuple(sorted(sep)))
                if key in self.seen:
                    continue
                lhs = sum(v * x[k] for k, v in zip(row[2], row[3]))
                if lhs > row[1] + eps:
                    self.seen.add(key)
                    out.append(row)
        return out


def violated(row: Row, x, tol: float = 1e-6) -> bool:
    """Whether the row is broken by `x`."""
    lhs = sum(v * x[k] for k, v in zip(row[2], row[3]))
    return (row[0] is not None and lhs < row[0] - tol) or (row[1] is not None and lhs > row[1] + tol)
