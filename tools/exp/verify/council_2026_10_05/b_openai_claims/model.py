"""Exact toy model of the support master (docs/MODEL.md §3, μ ≡ 0) and brute-force enumerators.

#91 verification, lane b_openai_claims. Everything here is small and exhaustive:

- `Inst`: units made of ZIPs with masses, a ZIP adjacency graph, modes, K, δ, η and a support
  family (connected unit sets up to a size cap, closed under connected subsets, or listed).
- `Inst.milp(...)`: the master as a highspy MILP with mip_rel_gap = mip_abs_gap = 0 and one thread
  (traps 12, 18), with optional F2 split binaries, Hall rows, F4 floor and η variants.
- `Inst.plans(...)`: every integer n over the family with Σ n = K that passes the n-only rows,
  each checked (or δ-minimised) by a share LP. This is the "brute force over all plans".
- `Inst.drawings(...)`: every partition of the ZIPs into exactly K blocks, each connected on the ZIP
  graph (the M1 maps), with optional mass band; `Inst.readback(...)` and `Inst.plan_violations(...)`
  check Proposition D's read-back row by row.
"""
import itertools
import math

import highspy
import numpy as np

INF = float("inf")
TOL = 1e-7


def solve(nvar, cost, lb, ub, rows, integer, sense_max=False):
    """rows: list of (dict col->coef, lo, hi). Returns (status, obj, x)."""
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("threads", 1)
    h.setOptionValue("mip_rel_gap", 0.0)
    h.setOptionValue("mip_abs_gap", 0.0)
    lp = highspy.HighsLp()
    lp.num_col_ = nvar
    lp.num_row_ = len(rows)
    lp.col_cost_ = np.array([(-c if sense_max else c) for c in cost], dtype=float)
    lp.col_lower_ = np.array(lb, dtype=float)
    lp.col_upper_ = np.array(ub, dtype=float)
    lp.row_lower_ = np.array([r[1] for r in rows], dtype=float)
    lp.row_upper_ = np.array([r[2] for r in rows], dtype=float)
    start, index, value = [0], [], []
    for coefs, _, _ in rows:
        for j, a in coefs.items():
            index.append(j)
            value.append(a)
        start.append(len(index))
    lp.a_matrix_.format_ = highspy.MatrixFormat.kRowwise
    lp.a_matrix_.start_ = np.array(start, dtype=np.int32)
    lp.a_matrix_.index_ = np.array(index, dtype=np.int32)
    lp.a_matrix_.value_ = np.array(value, dtype=float)
    if any(integer):
        lp.integrality_ = [highspy.HighsVarType.kInteger if i else highspy.HighsVarType.kContinuous
                           for i in integer]
    h.passModel(lp)
    h.run()
    st = h.getModelStatus()
    if st == highspy.HighsModelStatus.kOptimal:
        x = list(h.getSolution().col_value)
        obj = h.getInfo().objective_function_value
        return "optimal", (-obj if sense_max else obj), x
    if st == highspy.HighsModelStatus.kInfeasible:
        return "infeasible", None, None
    raise RuntimeError(f"unexpected HiGHS status {st}")


def connected(nodes, adj):
    nodes = set(nodes)
    if not nodes:
        return False
    start = next(iter(nodes))
    seen, stack = {start}, [start]
    while stack:
        x = stack.pop()
        for y in adj[x]:
            if y in nodes and y not in seen:
                seen.add(y)
                stack.append(y)
    return seen == nodes


class Inst:
    def __init__(self, zips, edges, K, delta, eta, modes=None, size_cap=None, family=None,
                 pos=None, state=None, zstate=None, rows=("count", "border", "corridor"), name=""):
        """zips: list of (zip, unit, mass). edges: list of (zip, zip). modes: unit -> mode
        (default free). family: optional list of unit sets (closed under connected subsets is
        checked). pos: unit -> coordinate tuple for the diameter weight (default (index,))."""
        self.args = dict(zips=zips, edges=edges, K=K, delta=delta, eta=eta, modes=modes,
                         size_cap=size_cap, family=family, pos=pos, state=state, zstate=zstate,
                         rows=rows, name=name)
        self.name = name
        self.Z = [z for z, _, _ in zips]
        self.zi = {z: i for i, z in enumerate(self.Z)}
        self.uof = [u for _, u, _ in zips]
        self.m = [float(x) for _, _, x in zips]
        self.units = list(dict.fromkeys(self.uof))
        self.Zv = {u: [i for i in range(len(self.Z)) if self.uof[i] == u] for u in self.units}
        self.M = {u: sum(self.m[i] for i in self.Zv[u]) for u in self.units}
        self.zadj = {i: set() for i in range(len(self.Z))}
        for a, b in edges:
            self.zadj[self.zi[a]].add(self.zi[b])
            self.zadj[self.zi[b]].add(self.zi[a])
        self.uadj = {u: set() for u in self.units}
        for i, nb in self.zadj.items():
            for j in nb:
                if self.uof[i] != self.uof[j]:
                    self.uadj[self.uof[i]].add(self.uof[j])
        self.K, self.delta, self.eta = K, float(delta), float(eta)
        self.modes = {u: "free" for u in self.units}
        self.modes.update(modes or {})
        self.state = state or {u: u for u in self.units}
        # state of each ZIP: a metro piece may cross a state line (astra T6)
        self.zstate = [(zstate or {}).get(z, self.state[self.uof[i]]) for i, z in enumerate(self.Z)]
        self.rows = set(rows)
        self.total = sum(self.M.values())
        self.tau = self.total / K
        pos = pos or {u: (k,) for k, u in enumerate(self.units)}
        self.pos = pos
        if family is None:
            cap = size_cap or len(self.units)
            fam = []
            for k in range(1, cap + 1):
                for S in itertools.combinations(self.units, k):
                    if connected(S, self.uadj):
                        fam.append(frozenset(S))
        else:
            fam = [frozenset(S) for S in family]
            for S in fam:
                assert connected(S, self.uadj), S
                for k in range(1, len(S)):
                    for T in itertools.combinations(sorted(S), k):
                        if connected(T, self.uadj):
                            assert frozenset(T) in fam, f"family not closed: {S} ⊇ {T}"
        self.F = fam
        self.w = [self.diam(S) for S in self.F]
        # border ZIP sets ∂_u(v): ZIPs of v with an edge into unit u
        self.bd = {(u, v): {i for i in self.Zv[v] if any(self.uof[j] == u for j in self.zadj[i])}
                   for v in self.units for u in self.uadj[v]}
        self.corr = [self._corridor(S) for S in self.F]

    def variant(self, **changes):
        return Inst(**{**self.args, **changes})

    # ---------------------------------------------------------------- derived quantities
    def diam(self, S):
        return max((math.dist(self.pos[a], self.pos[b]) for a in S for b in S), default=0.0)

    def band(self, delta=None):
        d = self.delta if delta is None else delta
        return self.tau * (1 - d), self.tau * (1 + d)

    def splittable(self, v):
        return self.modes[v] in ("clipped", "free")

    def cap(self, v, eta=None, zero_contact=False):
        """U_v: a valid upper bound on r_v = Σ_{S∋v} n_S (F2)."""
        eta = self.eta if eta is None else eta
        c = self.K
        if eta > 0:
            e = math.floor(1 / eta + 1e-9)
            if zero_contact:
                e += sum(1 for i in self.Zv[v] if self.m[i] == 0)
            c = min(c, e)
        if "count" in self.rows:
            c = min(c, len(self.Zv[v]))
        if not self.splittable(v):
            c = 1
        return c

    def _corridor(self, S):
        """{v: c_v(S)} for every cut vertex v of G[S] (component-versus-rest floor, MODEL §4.2)."""
        out = {}
        if len(S) < 3:
            return out
        for v in S:
            rest = set(S) - {v}
            comps = []
            left = set(rest)
            while left:
                x = left.pop()
                comp, stack = {x}, [x]
                while stack:
                    y = stack.pop()
                    for nb in self.uadj[y]:
                        if nb in left:
                            left.discard(nb)
                            comp.add(nb)
                            stack.append(nb)
                comps.append(comp)
            if len(comps) < 2:
                continue
            dz = [{i for i in self.Zv[v] if any(self.uof[j] in A for j in self.zadj[i])} for A in comps]
            best = 0.0
            for k in range(len(comps)):
                src = dz[k]
                dst = set().union(*[dz[q] for q in range(len(comps)) if q != k])
                best = max(best, self._lightest_path(v, src, dst))
            out[v] = best
        return out

    def _lightest_path(self, v, src, dst):
        # node-weighted shortest path inside G_v (Dijkstra on tiny graphs)
        dist = {i: self.m[i] for i in src}
        done = set()
        while True:
            cand = [(d, i) for i, d in dist.items() if i not in done]
            if not cand:
                return INF
            d, i = min(cand)
            if i in dst:
                return d
            done.add(i)
            for j in self.zadj[i]:
                if self.uof[j] == v and j not in done:
                    nd = d + self.m[j]
                    if nd < dist.get(j, INF):
                        dist[j] = nd

    def hall_sets(self, v):
        """For free v: [(set of supports-index predicate W, rhs)] for every nonempty W ⊆ N(v)."""
        nb = sorted(self.uadj[v])
        out = []
        for k in range(1, len(nb) + 1):
            for W in itertools.combinations(nb, k):
                rhs = len(set().union(*[self.bd[(u, v)] for u in W]))
                idx = [s for s, S in enumerate(self.F)
                       if v in S and (S & self.uadj[v]) and (S & self.uadj[v]) <= set(W)]
                out.append((W, idx, rhs))
        return out

    # ---------------------------------------------------------------- n-only rows
    def n_rows(self, hall=False, eta=None, zero_contact=False):
        """Linear rows in n alone: list of (support indices with coef 1, rhs) meaning Σ ≤ rhs."""
        rows = []
        for v in self.units:
            idx = [s for s, S in enumerate(self.F) if v in S]
            rows.append((idx, self.cap(v, eta, zero_contact), f"contact {v}"))
            if self.modes[v] == "free" and "border" in self.rows:
                for u in self.uadj[v]:
                    jdx = [s for s in idx if (self.F[s] & self.uadj[v]) == {u}]
                    rows.append((jdx, len(self.bd[(u, v)]), f"border {u}->{v}"))
            if self.modes[v] == "free" and hall:
                for W, jdx, rhs in self.hall_sets(v):
                    rows.append((jdx, rhs, f"hall {v} {W}"))
        return rows

    def ub_n(self, s, eta=None, zero_contact=False):
        S = self.F[s]
        if any(self.modes[v] == "whole" for v in S) or (len(S) > 1 and any(self.modes[v] == "clipped" for v in S)):
            return 1
        return min(self.cap(v, eta, zero_contact) for v in S)

    # ---------------------------------------------------------------- the MILP
    def milp(self, objective="diam", pins=(), hall=False, rho=None, eta=None,
             zero_contact=False, delta=None, eps=None, fix_whole=(), forbid=(), pairwise=False,
             fix_n=None, extra_rows=(), state_splits=False):
        """Master MILP (μ ≡ 0). objective: 'diam', 'splits', 'cuts', 'lex' (splits + eps·diam).
        pins: list of ('splits'|'diam'|'cuts', lo, hi). fix_whole: units forced unsplit (F6).
        forbid: support indices fixed to 0 (F7 regions). zero_contact: η only on positive-share
        copies (extra question). pairwise: add s_v ≥ n_S + n_T − 1 for pairs S, T ∋ v (SU1)."""
        eta = self.eta if eta is None else eta
        L, U = self.band(delta)
        col, cost, lb, ub, integ = {}, [], [], [], []

        def add(key, lo, hi, c, isint):
            col[key] = len(cost)
            cost.append(c)
            lb.append(lo)
            ub.append(hi)
            integ.append(isint)

        for s, S in enumerate(self.F):
            add(("n", s), 0, 0 if s in forbid else self.ub_n(s, eta, zero_contact), 0.0, True)
        for s, S in enumerate(self.F):
            for v in S:
                add(("t", v, s), 0, 1, 0.0, False)
                if zero_contact and self.modes[v] == "free" and any(self.m[i] == 0 for i in self.Zv[v]):
                    add(("q", v, s), 0, self.ub_n(s, eta, zero_contact), 0.0, True)
        spl = [v for v in self.units if self.splittable(v)]
        for v in spl:
            add(("s", v), 0, 1, 0.0, True)
        rows = []
        n = lambda s: col[("n", s)]
        rows.append(({n(s): 1 for s in range(len(self.F))}, self.K, self.K))
        for v in self.units:
            rows.append(({col[("t", v, s)]: 1 for s, S in enumerate(self.F) if v in S}, 1, 1))
        for s, S in enumerate(self.F):
            mass = {}
            for v in S:
                t = col[("t", v, s)]
                mass[t] = self.M[v]
                q = col.get(("q", v, s))
                if self.modes[v] == "whole" or (self.modes[v] == "clipped" and len(S) > 1):
                    rows.append(({t: 1, n(s): -1}, 0, 0))
                    continue
                if q is None:
                    rows.append(({t: 1, n(s): -eta}, 0, INF))
                    rows.append(({t: 1, n(s): -1}, -INF, 0))
                else:  # n_S = p + q, t ≥ η p, t ≤ p
                    rows.append(({t: 1, n(s): -eta, q: eta}, 0, INF))
                    rows.append(({t: 1, n(s): -1, q: 1}, -INF, 0))
                    rows.append(({q: 1, n(s): -1}, -INF, 0))
                if rho is not None and self.modes[v] == "free":
                    rows.append(({t: self.M[v], n(s): -rho * self.tau}, 0, INF))
            rows.append(({**mass, n(s): -L}, 0, INF))
            rows.append(({**mass, n(s): -U}, -INF, 0))
            if "corridor" in self.rows:
                for v, c in self.corr[s].items():
                    if c == INF:
                        rows.append(({n(s): 1}, 0, 0))
                    else:
                        rows.append(({col[("t", v, s)]: self.M[v], n(s): -c}, 0, INF))
        for idx, rhs, _ in self.n_rows(hall=hall, eta=eta, zero_contact=zero_contact):
            if idx:
                rows.append(({n(s): 1 for s in idx}, -INF, rhs))
        if zero_contact:
            for v in self.units:
                qs = [col[k] for k in col if k[0] == "q" and k[1] == v]
                if qs:
                    rows.append(({q: 1 for q in qs}, -INF, sum(1 for i in self.Zv[v] if self.m[i] == 0)))
        # F2: 1 + s ≤ r ≤ 1 + (U_v − 1) s
        for v in spl:
            r = {n(s): 1 for s, S in enumerate(self.F) if v in S}
            Uv = self.cap(v, eta, zero_contact)
            rows.append(({**r, col[("s", v)]: -(Uv - 1)}, -INF, 1))
            rows.append(({**r, col[("s", v)]: -1}, 1, INF))
            if pairwise:
                idx = [s for s, S in enumerate(self.F) if v in S]
                for a, b in itertools.combinations_with_replacement(idx, 2):
                    if a != b:
                        rows.append(({col[("s", v)]: 1, n(a): -1, n(b): -1}, -1, INF))
        if fix_n is not None:
            for s in range(len(self.F)):
                lb[n(s)] = ub[n(s)] = fix_n.get(s, 0)
        for coefs, lo, hi in extra_rows:  # coefs keyed by support index
            rows.append(({n(s): a for s, a in coefs.items()}, lo, hi))
        sts = sorted(set(self.state.values()))
        if state_splits:  # one binary per state: 1 + σ ≤ Σ_{S∩P(σ)≠∅} n_S ≤ 1 + (K − 1)σ
            for st in sts:
                add(("st", st), 0, 1, 0.0, True)
                r = {n(s): 1 for s, S in enumerate(self.F) if any(self.state[u] == st for u in S)}
                rows.append(({**r, col[("st", st)]: -(self.K - 1)}, -INF, 1))
                rows.append(({**r, col[("st", st)]: -1}, 1, INF))
        for v in fix_whole:
            if ("s", v) in col:
                ub[col[("s", v)]] = 0
        expr = {
            "splits": {col[("s", v)]: 1.0 for v in spl},
            "diam": {n(s): self.w[s] for s in range(len(self.F))},
            "cuts": {n(s): float(len(S)) for s, S in enumerate(self.F)},
        }
        if state_splits:
            expr["states"] = {col[("st", st)]: 1.0 for st in sts}
        for key, lo, hi in pins:
            rows.append((dict(expr[key]), lo, hi))
        if objective == "lex":
            obj = {k: v for k, v in expr["splits"].items()}
            for k, v in expr["diam"].items():
                obj[k] = obj.get(k, 0) + eps * v
        else:
            obj = expr[objective]
        for k, v in obj.items():
            cost[k] = v
        st, val, x = solve(len(cost), cost, lb, ub, rows, integ)
        if st != "optimal":
            return st, None, None
        nsol = {s: int(round(x[n(s)])) for s in range(len(self.F)) if round(x[n(s)]) > 0}
        if objective == "cuts":
            val -= len(self.units)
        return st, val, nsol

    def bisect_delta(self, lo=0.0, hi=1.0, tol=1e-6, **kw):
        """Smallest δ at which the MILP is feasible (objective 'diam' kept, trap 19)."""
        if self.milp(delta=hi, **kw)[0] != "optimal":
            return None
        if self.milp(delta=lo, **kw)[0] == "optimal":
            return lo
        while hi - lo > tol:
            mid = (lo + hi) / 2
            if self.milp(delta=mid, **kw)[0] == "optimal":
                hi = mid
            else:
                lo = mid
        return hi

    # ---------------------------------------------------------------- plans by enumeration
    def nvectors(self, hall=False, eta=None):
        """Every n ∈ ℤ^F, Σ n = K, satisfying the n-only rows, whole/clipped ownership and coverage."""
        rows = self.n_rows(hall=hall, eta=eta)
        F = self.F
        order = list(range(len(F)))
        L, U = self.band()
        out = []
        cur = [0] * len(F)

        def ok_partial():
            for idx, rhs, _ in rows:
                if sum(cur[s] for s in idx) > rhs:
                    return False
            return True

        def rec(k, left):
            if k == len(order):
                if left:
                    return
                r = {v: sum(cur[s] for s, S in enumerate(F) if v in S) for v in self.units}
                if any(r[v] < 1 for v in self.units):
                    return
                if any(self.modes[v] == "whole" and r[v] != 1 for v in self.units):
                    return
                for v in self.units:
                    if self.modes[v] == "clipped":
                        multi = sum(cur[s] for s, S in enumerate(F) if v in S and len(S) > 1)
                        if multi and r[v] != 1:
                            return
                out.append({s: cur[s] for s in range(len(F)) if cur[s]})
                return
            s = order[k]
            for c in range(0, min(left, self.ub_n(s, eta)) + 1):
                cur[s] = c
                if ok_partial():
                    rec(k + 1, left - c)
            cur[s] = 0

        rec(0, self.K)
        return out

    def share_lp(self, nvec, delta=None, rho=None, minimize_delta=False, per_copy=False, eta=None):
        """Share LP for fixed n. Returns min δ (minimize_delta) or True/False feasibility.
        per_copy: one share variable per copy (explicit-copy form) instead of aggregate t."""
        eta = self.eta if eta is None else eta
        col, cost, lb, ub = {}, [], [], []
        copies = [(s, r) for s, c in nvec.items() for r in range(c if per_copy else 1)]
        for (s, r) in copies:
            for v in self.F[s]:
                col[(v, s, r)] = len(cost)
                cost.append(0.0)
                lb.append(0.0)
                ub.append(1.0 if per_copy else float(nvec[s]))
        if minimize_delta:
            col["d"] = len(cost)
            cost.append(1.0)
            lb.append(0.0)
            ub.append(INF)
        L, U = self.band(delta)
        rows = []
        for v in self.units:
            rows.append(({col[k]: 1 for k in col if k != "d" and k[0] == v}, 1, 1))
        for (s, r) in copies:
            S = self.F[s]
            k = 1 if per_copy else nvec[s]
            mass = {}
            for v in S:
                t = col[(v, s, r)]
                mass[t] = self.M[v]
                if self.modes[v] == "whole" or (self.modes[v] == "clipped" and len(S) > 1):
                    lb[t] = ub[t] = float(k)
                else:
                    lb[t] = max(lb[t], eta * k)
                if rho is not None and self.modes[v] == "free":
                    rows.append(({t: self.M[v]}, rho * self.tau * k, INF))
                if "corridor" in self.rows and v in self.corr[s]:
                    c = self.corr[s][v]
                    if c == INF:
                        return None if minimize_delta else False
                    rows.append(({t: self.M[v]}, c * k, INF))
            if minimize_delta:
                rows.append(({**mass, col["d"]: self.tau * k}, self.tau * k, INF))
                rows.append(({**mass, col["d"]: -self.tau * k}, -INF, self.tau * k))
            else:
                rows.append((mass, L * k, U * k))
        if any(lb[i] > ub[i] + TOL for i in range(len(lb))):
            return None if minimize_delta else False
        st, val, x = solve(len(cost), cost, lb, ub, rows, [False] * len(cost))
        if minimize_delta:
            return val if st == "optimal" else None
        return st == "optimal"

    def plans(self, delta=None, hall=False, rho=None, eta=None):
        """All feasible plans: list of n dicts."""
        return [nv for nv in self.nvectors(hall=hall, eta=eta)
                if self.share_lp(nv, delta=delta, rho=rho, eta=eta)]

    def r(self, nvec):
        return {v: sum(c for s, c in nvec.items() if v in self.F[s]) for v in self.units}

    def nsplits(self, nvec):
        return sum(1 for x in self.r(nvec).values() if x >= 2)

    def ncuts(self, nvec):
        return sum(x - 1 for x in self.r(nvec).values())

    def D(self, nvec):
        return sum(self.w[s] * c for s, c in nvec.items())

    # ---------------------------------------------------------------- drawings
    def drawings(self, delta=None, band=True):
        """All partitions of the ZIPs into exactly K blocks, each connected on the ZIP graph,
        with every block mass in the band when band=True. Yields tuples of bitmasks."""
        nZ = len(self.Z)
        L, U = self.band(delta)
        blocks_by_low = {i: [] for i in range(nZ)}
        for mask in range(1, 1 << nZ):
            members = [i for i in range(nZ) if mask >> i & 1]
            mass = sum(self.m[i] for i in members)
            if band and not (L - TOL <= mass <= U + TOL):
                continue
            if connected(members, self.zadj):
                blocks_by_low[members[0]].append(mask)
        full = (1 << nZ) - 1
        out = []

        def rec(covered, chosen):
            if covered == full:
                if len(chosen) == self.K:
                    out.append(tuple(chosen))
                return
            if len(chosen) == self.K:
                return
            low = (~covered & full & -(~covered & full)).bit_length() - 1
            for b in blocks_by_low[low]:
                if b & covered == 0:
                    rec(covered | b, chosen + [b])

        rec(0, [])
        return out

    def members(self, mask):
        return [i for i in range(len(self.Z)) if mask >> i & 1]

    def dmass(self, mask):
        return sum(self.m[i] for i in self.members(mask))

    def ddev(self, d):
        return max(abs(self.dmass(b) - self.tau) for b in d) / self.tau

    def footprint(self, mask):
        return frozenset(self.uof[i] for i in self.members(mask))

    def share(self, mask, v):
        return sum(self.m[i] for i in self.members(mask) if self.uof[i] == v) / self.M[v]

    def own_splits(self, d):
        """Polygon-ownership split units (owner decision 1): units owned by ≥ 2 districts."""
        return sum(1 for v in self.units if sum(1 for b in d if v in self.footprint(b)) >= 2)

    def pos_splits(self, d):
        """Positive-opportunity split units (SPLITS §2.1 ledger key)."""
        return sum(1 for v in self.units if sum(1 for b in d if self.share(b, v) > 0) >= 2)

    def state_splits(self, d):
        """States owned (any ZIP, polygon ownership) by ≥ 2 districts."""
        sts = set(self.zstate)
        return sum(1 for st in sts
                   if sum(1 for b in d if any(self.zstate[i] == st for i in self.members(b))) >= 2)

    def readback(self, d):
        nvec, t = {}, {}
        for b in d:
            S = self.footprint(b)
            if S not in self.F:
                return None, None
            s = self.F.index(S)
            nvec[s] = nvec.get(s, 0) + 1
            for v in S:
                t[(v, s)] = t.get((v, s), 0.0) + self.share(b, v)
        return nvec, t

    def in_X(self, d, eta=None):
        """d ∈ 𝒳_c(δ) (MODEL §4.1): footprints in the family, shares obey η and the modes.
        Connectivity and band are guaranteed by `drawings`."""
        eta = self.eta if eta is None else eta
        for b in d:
            S = self.footprint(b)
            if S not in self.F:
                return False
            for v in S:
                sh = self.share(b, v)
                if sh < eta - TOL:
                    return False
        return self.modes_ok(d)

    def modes_ok(self, d):
        for v in self.units:
            owners = [b for b in d if v in self.footprint(b)]
            if self.modes[v] == "whole" and len(owners) != 1:
                return False
            if self.modes[v] == "clipped" and len(owners) > 1 and any(len(self.footprint(b)) > 1 for b in owners):
                return False
        return True

    def plan_violations(self, nvec, t, hall=False, eta=None, delta=None):
        """Rows of §3 (μ ≡ 0) violated by (n, t)."""
        eta = self.eta if eta is None else eta
        L, U = self.band(delta)
        bad = []
        if sum(nvec.values()) != self.K:
            bad.append("sum n")
        for v in self.units:
            tot = sum(x for (u, s), x in t.items() if u == v)
            if abs(tot - 1) > 1e-6:
                bad.append(f"cover {v}")
        for s, c in nvec.items():
            S = self.F[s]
            mass = sum(self.M[v] * t[(v, s)] for v in S)
            if not (L * c - 1e-6 <= mass <= U * c + 1e-6):
                bad.append(f"band {sorted(S)}")
            for v in S:
                if t[(v, s)] < eta * c - 1e-9:
                    bad.append(f"eta {v} in {sorted(S)}")
                if (self.modes[v] == "whole" or (self.modes[v] == "clipped" and len(S) > 1)) and (
                        c > 1 or abs(t[(v, s)] - c) > 1e-9):
                    bad.append(f"mode {v}")
                if "corridor" in self.rows and v in self.corr[s] and self.M[v] * t[(v, s)] < self.corr[s][v] * c - 1e-9:
                    bad.append(f"corridor {v} in {sorted(S)}")
        for idx, rhs, name in self.n_rows(hall=hall, eta=eta):
            if name.startswith("contact"):
                continue  # the η-cap is implied by the η rows checked above; count cap below
            if sum(nvec.get(s, 0) for s in idx) > rhs:
                bad.append(name)
        if "count" in self.rows:
            for v in self.units:
                if sum(c for s, c in nvec.items() if v in self.F[s]) > len(self.Zv[v]):
                    bad.append(f"count {v}")
        return bad


def random_inst(seed, n_units=(6, 8), zips_per=(1, 3), K=(2, 5), size_cap=(2, 3), n_free=(1, 3),
                masses=(0.0, 0.5, 1.0, 1.0, 1.5, 2.0, 3.0), deltas=(0.1, 0.15, 0.25), etas=(0.1, 0.2),
                clipped=True, rows=("count", "border", "corridor")):
    """A fixed-seed random toy: a random spanning tree on the ZIPs plus a few extra edges."""
    import random
    rng = random.Random(seed)
    nu = rng.randint(*n_units)
    zips, edges = [], []
    for k in range(nu):
        u = f"u{k}"
        nz = rng.randint(*zips_per)
        names = [f"{u}z{i}" for i in range(nz)]
        for i, z in enumerate(names):
            zips.append((z, u, rng.choice(masses)))
            if i:
                edges.append((names[rng.randrange(i)], z))  # unit stays connected (OQ6)
        if all(x[2] == 0 for x in zips[-nz:]):
            zips[-1] = (zips[-1][0], u, 1.0)  # M_v > 0 (MODEL §1)
    allz = [z for z, _, _ in zips]
    for i in range(1, nu):
        a = rng.choice([z for z, u, _ in zips if u == f"u{i}"])
        b = rng.choice([z for z, u, _ in zips if int(u[1:]) < i])
        edges.append((a, b))
    for _ in range(rng.randint(0, 3)):
        a, b = rng.sample(allz, 2)
        if (a, b) not in edges and (b, a) not in edges:
            edges.append((a, b))
    units = [f"u{k}" for k in range(nu)]
    free = rng.sample(units, rng.randint(*n_free))
    modes = {u: "whole" for u in units}
    for u in free:
        modes[u] = rng.choice(["free", "free", "clipped"]) if clipped else "free"
    pos = {u: (rng.random() * 4, rng.random() * 4) for u in units}
    return Inst(zips, edges, K=rng.randint(*K), delta=rng.choice(deltas), eta=rng.choice(etas),
                modes=modes, size_cap=rng.randint(*size_cap), pos=pos, rows=rows, name=f"rand{seed}")
