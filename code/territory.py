"""
territory.py -- fair wholesaler territory division on a ZCTA adjacency graph.

Bridges the discrete formulation to a networkx graph whose nodes are ZCTAs with
Rook adjacency. Expected node attributes:

    rep_a   : legacy firm A's wholesaler id covering this ZCTA
    rep_b   : legacy firm B's wholesaler id
    A       : firm A sales in this ZCTA
    B       : firm B sales in this ZCTA
    M       : total market opportunity in this ZCTA
    state   : two-letter state code            (optional, for the state-border constraint)

Conventions follow the notes: headroom is NET, so with transfer capture theta and
headroom credit lam,
    c1 = 1 - lam,  c2 = theta*(1 - lam)
    u_a(z) = c1*A_z + c2*B_z + lam*M_z
    u_b(z) = c2*A_z + c1*B_z + lam*M_z
"""
from __future__ import annotations
import numpy as np, networkx as nx
from collections import Counter
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix, csr_matrix

REQUIRED = ("rep_a", "rep_b", "A", "B", "M")


# ----------------------------------------------------------------- validation
def validate(G, theta=0.40, lam=0.30):
    """Check attributes and the pointwise non-negative-headroom condition."""
    problems = []
    missing = [n for n in G if any(k not in G.nodes[n] for k in REQUIRED)]
    if missing:
        problems.append(f"{len(missing)} nodes missing required attributes (e.g. {missing[:3]})")
    A = np.array([G.nodes[n].get("A", 0.0) for n in G])
    B = np.array([G.nodes[n].get("B", 0.0) for n in G])
    M = np.array([G.nodes[n].get("M", 0.0) for n in G])
    bad = (M < A + theta * B) | (M < B + theta * A)
    if bad.any():
        problems.append(f"{int(bad.sum())} ZCTAs violate non-negative headroom "
                        f"(M_z < max(A+theta*B, B+theta*A)); worst deficit "
                        f"{float((np.minimum(M-A-theta*B, M-B-theta*A)).min()):.4f}")
    iso = list(nx.isolates(G))
    if iso:
        problems.append(f"{len(iso)} isolated ZCTAs in the adjacency graph")
    ncc = nx.number_connected_components(G)
    if ncc > 1:
        problems.append(f"adjacency graph has {ncc} components (islands / non-contiguous states)")
    return problems


# ------------------------------------------------------- overlap graph & census
def overlap_graph(G):
    """Bipartite graph of (firm-A rep, firm-B rep) pairs, edge weight = shared opportunity."""
    O = nx.Graph()
    for n, d in G.nodes(data=True):
        a, b = ("A", d["rep_a"]), ("B", d["rep_b"])
        O.add_node(a, side="A"); O.add_node(b, side="B")
        if O.has_edge(a, b):
            O[a][b]["M"] += d["M"]; O[a][b]["zips"] += 1
            O[a][b]["A"] += d["A"]; O[a][b]["B"] += d["B"]
        else:
            O.add_edge(a, b, M=d["M"], zips=1, A=d["A"], B=d["B"])
    return O


def zips_for_pair(G, rep_a, rep_b):
    """ZCTAs covered by firm-A rep `rep_a` and firm-B rep `rep_b` simultaneously."""
    return [n for n, d in G.nodes(data=True)
            if d["rep_a"] == rep_a and d["rep_b"] == rep_b]


def pair_endpoints(edge):
    """Normalise an overlap-graph edge to (rep_a_id, rep_b_id); endpoints are ('A'|'B', id)."""
    u, v = edge[0], edge[1]
    a, b = (u, v) if u[0] == "A" else (v, u)
    return a[1], b[1]


def largest_pair(G):
    """The (rep_a, rep_b) pair sharing the most opportunity."""
    O = overlap_graph(G)
    e = max(O.edges(data=True), key=lambda x: x[2]["M"])
    return pair_endpoints(e) + (e[2],)


def census(G, min_share=0.02, split=True):
    """
    Decompose the national problem. Returns per-component structure and a verdict on
    whether the two-player theory applies directly.

    With split=True (default), edges under min_share of their component's opportunity
    are trimmed BEFORE componentization, so map slivers cannot glue clean 1-1 pairs
    into one spurious "dense" component. (The original behaviour -- split=False --
    trimmed weak edges only when labelling a component's shape, never to split it,
    which made min_share decorative: under any boundary noise the census could only
    ever answer "dense". Demonstrated in census_stress.py.) Weak edges INSIDE a
    surviving group still count toward its M (same reps, same solve); weak edges
    CROSSING groups are orphaned -- their opportunity appears in no row, so
    1 - sum(r["share"]) is the orphaned share needing manual adjudication.
    """
    O = overlap_graph(G)
    totM = sum(d["M"] for _, d in G.nodes(data=True))
    out = []
    for comp in nx.connected_components(O):
        sub = O.subgraph(comp)
        Mc = sum(d["M"] for *_, d in sub.edges(data=True))
        strong_all = [(u, v) for u, v, d in sub.edges(data=True)
                      if d["M"] >= min_share * Mc]
        if split:
            H = nx.Graph(); H.add_nodes_from(comp); H.add_edges_from(strong_all)
            groups = list(nx.connected_components(H))
        else:
            groups = [set(comp)]
        for g in groups:
            gsub = O.subgraph(g)
            if gsub.number_of_edges() == 0:
                continue                      # rep isolated by trimming -> orphaned
            Mg = sum(d["M"] for *_, d in gsub.edges(data=True))
            reps_a = [x for x in g if x[0] == "A"]; reps_b = [x for x in g if x[0] == "B"]
            strong = [(u, v) for u, v, d in gsub.edges(data=True)
                      if d["M"] >= min_share * Mc]
            shape = ("1-1 pair" if len(reps_a) == 1 and len(reps_b) == 1
                     else f"dense ({len(reps_a)}A x {len(reps_b)}B, {len(strong)} strong edges)")
            out.append(dict(reps_a=reps_a, reps_b=reps_b, M=Mg, share=Mg / totM,
                            edges=gsub.number_of_edges(), strong_edges=len(strong),
                            shape=shape))
    out.sort(key=lambda r: -r["M"])
    return out


# --------------------------------------------------------------- the core solve
def _fields(G, nodes, theta, lam):
    A = np.array([G.nodes[n]["A"] for n in nodes], float)
    B = np.array([G.nodes[n]["B"] for n in nodes], float)
    M = np.array([G.nodes[n]["M"] for n in nodes], float)
    c1, c2 = 1 - lam, theta * (1 - lam)
    return A, B, M, c1 * A + c2 * B + lam * M, c2 * A + c1 * B + lam * M


def ratio_guard(ua, ub):
    """u_a/u_b with the zero-value-zip guard (PLAN.md C.0 #9).

    Identical to ua/ub wherever ub > 0.  A zip with ub == 0 < ua ranks first (+inf);
    a zip with ua == ub == 0 (regime (d) glue) gets ratio 1 -- neutral.
    """
    ua = np.asarray(ua, float); ub = np.asarray(ub, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(ub > 0, ua / ub, np.where(ua > 0, np.inf, 1.0))


def prefix_table(G, nodes, theta=0.40, lam=0.30):
    """
    Sort by utility ratio, then cumulative gains for every prefix k = 0..n.
    This is the whole optimisation; every criterion reads off this table.
    """
    nodes = list(nodes)
    A, B, M, ua, ub = _fields(G, nodes, theta, lam)
    Sa, Sb = 0.0, 0.0   # disagreement point d=(0,0): gains ARE bundle utilities
    order = np.argsort(-ratio_guard(ua, ub))
    ga = np.concatenate([[0.0], np.cumsum(ua[order])]) - Sa
    gb = np.concatenate([[ub.sum()], ub.sum() - np.cumsum(ub[order])]) - Sb
    return dict(nodes=nodes, order=order, ga=ga, gb=gb,
                Amax=ua.sum() - Sa, Bmax=ub.sum() - Sb,
                ua=ua, ub=ub, A=A, B=B, M=M, Sa=Sa, Sb=Sb)


CRITERIA = {
    "equal_gain":  lambda t: np.argmin(np.abs(t["ga"] - t["gb"])),
    "egalitarian": lambda t: np.argmax(np.minimum(t["ga"], t["gb"])),
    "ks":          lambda t: np.argmin(np.abs(t["ga"] / t["Amax"] - t["gb"] / t["Bmax"])),
    "nash":        lambda t: int(np.argmax(np.where((t["ga"] > 0) & (t["gb"] > 0),
                                                    t["ga"] * t["gb"], -np.inf))),
    "utilitarian": lambda t: np.argmax(t["ga"] + t["gb"]),
    "equal_opportunity": lambda t: int(np.searchsorted(
        np.cumsum(t["M"][t["order"]]) / t["M"].sum(), 0.5)),
}


def nash_exact(A, B, M, theta=0.40, lam=0.30, graph=None, nodes=None,
               contiguity=False, rho=0.0, max_iter=60, tol=1e-9, verbose=False):
    A = np.asarray(A, float); B = np.asarray(B, float); M = np.asarray(M, float)
    n = len(A)
    c1, c2 = 1 - lam, theta * (1 - lam)
    ua, ub = c1*A + c2*B + lam*M, c2*A + c1*B + lam*M
    Sa, Sb = 0.0, 0.0   # disagreement point d=(0,0): gains ARE bundle utilities
    E = []
    if contiguity:
        nodes = list(nodes); idx = {z: i for i, z in enumerate(nodes)}
        H = graph.subgraph(nodes)
        E = [(idx[u], idx[v]) for u, v in H.edges()]
    m = len(E)
    NV = n + 2 + m; IA, IB = n, n + 1
    rows, rl, ru = [], [], []
    def add(pairs, lo, hi): rows.append(pairs); rl.append(lo); ru.append(hi)
    for e, (i, j) in enumerate(E):
        add([(n+2+e, 1.0), (i, -1.0), (j, 1.0)], 0, np.inf)
        add([(n+2+e, 1.0), (i, 1.0), (j, -1.0)], 0, np.inf)

    def tangent(side, gh):
        if gh <= 1e-12: return
        if side == "a":
            add([(IA, 1.0)] + [(i, -ua[i]/gh) for i in range(n)],
                -np.inf, np.log(gh) - 1.0 - Sa/gh)
        else:
            add([(IB, 1.0)] + [(i, ub[i]/gh) for i in range(n)],
                -np.inf, np.log(gh) - 1.0 + (ub.sum() - Sb)/gh)
    span = max(ua.sum() - Sa, ub.sum() - Sb)
    for g0 in np.geomspace(max(span*1e-3, 1e-3), span, 8): tangent("a", g0); tangent("b", g0)

    c = np.zeros(NV); c[IA] = c[IB] = -1.0; c[n+2:] = rho
    integ = np.zeros(NV); integ[:n] = 1
    lo = np.zeros(NV); hi = np.ones(NV); lo[IA] = lo[IB] = -60; hi[IA] = hi[IB] = 60
    def build():
        Am = lil_matrix((len(rows), NV))
        for k, pr in enumerate(rows):
            for cc, vv in pr: Am[k, cc] += vv
        return LinearConstraint(csr_matrix(Am), np.array(rl), np.array(ru))

    best = (-np.inf, None)
    for it in range(max_iter):
        res = milp(c=c, constraints=build(), integrality=integ, bounds=Bounds(lo, hi),
                   options=dict(time_limit=30, mip_rel_gap=0.0,
                                # HiGHS default integrality tol 1e-6 lets x_i sit
                                # ~1e-7 off {0,1}; the rounded incumbent then looks
                                # to violate its own tangent by ~1e-7 > tol and the
                                # loop stalls re-adding an identical cut forever.
                                mip_feasibility_tolerance=1e-9,
                                primal_feasibility_tolerance=1e-9))
        if not res.success: return dict(status="solver failed", message=str(res.message))
        UB = -(res.fun) if rho == 0 else -(res.x[IA] + res.x[IB]) * -1
        UB = res.x[IA] + res.x[IB]
        x = np.round(res.x[:n]).astype(bool)
        ga, gb = ua[x].sum() - Sa, ub[~x].sum() - Sb
        LB = np.log(ga) + np.log(gb) if (ga > 0 and gb > 0) else -np.inf
        if LB > best[0]: best = (LB, x.copy())
        added = 0
        if contiguity:
            for side in ("a", "b"):
                sel = [nodes[i] for i in range(n) if x[i] == (side == "a")]
                comps = sorted(nx.connected_components(graph.subgraph(sel)), key=len, reverse=True)
                for S in comps[1:]:
                    nb = {w for z in S for w in graph.neighbors(z)} - set(S)
                    nb = {w for w in nb if w in idx}
                    if not nb: continue
                    k_ = len(S)
                    if side == "a":
                        add([(idx[w], float(k_)) for w in nb] + [(idx[v], -1.0) for v in S], 0, np.inf)
                    else:
                        add([(idx[w], -float(k_)) for w in nb] + [(idx[v], 1.0) for v in S],
                            k_ - k_*len(nb), np.inf)
                    added += 1
        if ga > 0 and res.x[IA] - np.log(ga) > tol: tangent("a", ga); added += 1
        if gb > 0 and res.x[IB] - np.log(gb) > tol: tangent("b", gb); added += 1
        if verbose:
            print(f"    it{it:>3} UB={UB:.8f} LB={LB:.8f} gap={UB-LB:.2e} cuts+={added}")
        if added == 0:
            xb = best[1]
            ga, gb = ua[xb].sum() - Sa, ub[~xb].sum() - Sb
            return dict(status="optimal", x=xb, g_a=float(ga), g_b=float(gb),
                        product=float(ga*gb), iters=it+1, gap=float(UB - best[0]))
    xb = best[1]; ga, gb = ua[xb].sum() - Sa, ub[~xb].sum() - Sb
    return dict(status="iteration limit", x=xb, product=float(ga*gb))


def solve(G, nodes, criterion="nash", theta=0.40, lam=0.30, exact=True):
    """
    Set of ZCTAs assigned to rep A, plus diagnostics.

    For criterion="nash" the default is the EXACT outer-approximation solve. The
    prefix table is an approximation: it is optimal only about half the time, though
    the shortfall shrinks with n (mean 0.02% at n=50, 0.002% at n=100). Pass
    exact=False for the fast prefix answer.
    """
    t = prefix_table(G, nodes, theta, lam)
    if criterion == "nash" and exact:
        r = nash_exact(t["A"], t["B"], t["M"], theta, lam)
        if r.get("status") == "optimal":
            to_a = {t["nodes"][i] for i in range(len(t["nodes"])) if r["x"][i]}
            ga, gb = r["g_a"], r["g_b"]
            return dict(to_a=to_a, k=int(r["x"].sum()), g_a=ga, g_b=gb,
                        product=r["product"], exact=True, iters=r["iters"],
                        bound_gap=r["gap"],
                        frac_a=float(ga/t["Amax"]), frac_b=float(gb/t["Bmax"]),
                        ks_gap=float(abs(ga/t["Amax"] - gb/t["Bmax"])),
                        M_a=float(t["M"][r["x"]].sum()), M_total=float(t["M"].sum()),
                        table=t)
    k = int(CRITERIA[criterion](t))
    to_a = {t["nodes"][i] for i in t["order"][:k]}
    ga, gb = t["ga"][k], t["gb"][k]
    return dict(to_a=to_a, k=k, g_a=float(ga), g_b=float(gb), exact=False,
                frac_a=float(ga / t["Amax"]), frac_b=float(gb / t["Bmax"]),
                ks_gap=float(abs(ga / t["Amax"] - gb / t["Bmax"])),
                M_a=float(t["M"][t["order"][:k]].sum()), M_total=float(t["M"].sum()),
                table=t)


def compare_criteria(G, nodes, theta=0.40, lam=0.30):
    t = prefix_table(G, nodes, theta, lam)
    rows = {}
    for name, sel in CRITERIA.items():
        k = int(sel(t))
        ga, gb = t["ga"][k], t["gb"][k]
        rows[name] = dict(k=k, g_a=float(ga), g_b=float(gb),
                          min_g=float(min(ga, gb)), product=float(ga * gb),
                          ks_gap=float(abs(ga / t["Amax"] - gb / t["Bmax"])),
                          M_a_share=float(t["M"][t["order"][:k]].sum() / t["M"].sum()))
    return rows


# ------------------------------------------------------------------ contiguity
def contiguity_report(G, nodes, to_a, respect_state=False):
    """Connected components of each wholesaler's territory on the Rook graph."""
    sub = G.subgraph(nodes)
    if respect_state:
        sub = nx.Graph((u, v) for u, v in sub.edges()
                       if G.nodes[u].get("state") == G.nodes[v].get("state"))
        sub.add_nodes_from(nodes)
    Sa_ = sub.subgraph([n for n in nodes if n in to_a])
    Sb_ = sub.subgraph([n for n in nodes if n not in to_a])
    def frag(H):
        if H.number_of_nodes() == 0: return 0, []
        cc = sorted(nx.connected_components(H), key=len, reverse=True)
        return len(cc), [len(c) for c in cc]
    na, sa = frag(Sa_); nb, sb = frag(Sb_)
    return dict(components_a=na, sizes_a=sa[:6], components_b=nb, sizes_b=sb[:6],
                largest_share_a=(sa[0] / max(sum(sa), 1)) if sa else 0.0,
                largest_share_b=(sb[0] / max(sum(sb), 1)) if sb else 0.0)


def enforce_contiguity(G, nodes, res, theta=0.40, lam=0.30, criterion="ks", max_moves=None):
    """
    Greedy repair: repeatedly reassign the cheapest island (smallest fairness damage
    per ZCTA) into the neighbouring territory, until each side is connected.
    Returns the repaired assignment and the fairness cost paid.
    """
    t = res["table"]; idx = {n: i for i, n in enumerate(t["nodes"])}
    to_a = set(res["to_a"]); Amax, Bmax = t["Amax"], t["Bmax"]
    def gaps(S):
        ga = sum(t["ua"][idx[n]] for n in S) - t["Sa"]
        gb = sum(t["ub"][idx[n]] for n in t["nodes"] if n not in S) - t["Sb"]
        return abs(ga / Amax - gb / Bmax)
    start = gaps(to_a); moves = 0
    sub = G.subgraph(nodes)
    while True:
        rep = contiguity_report(G, nodes, to_a)
        if rep["components_a"] <= 1 and rep["components_b"] <= 1: break
        if max_moves is not None and moves >= max_moves: break
        best = None
        for side, S in (("a", [n for n in nodes if n in to_a]),
                        ("b", [n for n in nodes if n not in to_a])):
            H = sub.subgraph(S)
            cc = sorted(nx.connected_components(H), key=len, reverse=True)
            for island in cc[1:]:
                cand = set(to_a) - island if side == "a" else set(to_a) | island
                cost = gaps(cand) - gaps(to_a)
                if best is None or cost / len(island) < best[0]:
                    best = (cost / len(island), cand, len(island), side)
        if best is None: break
        to_a = best[1]; moves += 1
    return dict(to_a=to_a, moves=moves, ks_gap_before=float(start),
                ks_gap_after=float(gaps(to_a)))


# --------------------------------------------------------------- contestability
def contestability(G, nodes, theta=0.40, lam=0.30, criterion="ks",
                   theta_rng=(0.20, 0.60), lam_rng=(0.10, 0.50),
                   cv_sales=0.10, cv_opp=0.06, draws=600, seed=0):
    """stake x doubt per ZCTA. Stake uses the attainable maxima; doubt is the flip rate."""
    rng = np.random.default_rng(seed)
    base = solve(G, nodes, criterion, theta, lam); t = base["table"]
    stake = t["ua"] / t["Amax"] + t["ub"] / t["Bmax"]
    votes = np.zeros(len(t["nodes"]))
    H = G.copy()
    for _ in range(draws):
        th_ = rng.uniform(*theta_rng); lm_ = rng.uniform(*lam_rng)
        for i, n in enumerate(t["nodes"]):
            a_ = t["A"][i] * rng.lognormal(0, cv_sales)
            b_ = t["B"][i] * rng.lognormal(0, cv_sales)
            m_ = max(t["M"][i] * rng.lognormal(0, cv_opp), (a_ + b_) * 1.02)
            H.nodes[n].update(A=a_, B=b_, M=m_)
        s = solve(H, nodes, criterion, th_, lm_)["to_a"]
        votes += np.array([1.0 if n in s else 0.0 for n in t["nodes"]])
    p = votes / draws
    doubt = 2 * np.minimum(p, 1 - p)
    con = stake * doubt
    return {n: dict(stake=float(stake[i]), doubt=float(doubt[i]),
                    contestability=float(con[i]),
                    assigned=("A" if t["nodes"][i] in base["to_a"] else "B"))
            for i, n in enumerate(t["nodes"])}


def write_back(G, nodes, to_a, contest=None, key="assigned"):
    """Attach results to the graph for mapping."""
    for n in nodes:
        G.nodes[n][key] = "A" if n in to_a else "B"
        if contest and n in contest:
            G.nodes[n]["stake"] = contest[n]["stake"]
            G.nodes[n]["doubt"] = contest[n]["doubt"]
            G.nodes[n]["contestability"] = contest[n]["contestability"]
    return G
