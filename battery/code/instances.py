"""
instances.py -- the benchmark instance set for the contiguity harness (PLAN.md C.1, C.5).

An *instance* here is one (rep_a, rep_b) overlap pair of one synthetic case: the unit every
contiguity method is run on.  This module turns a case name into a reproducible list of
`InstanceSpec`s (tiers T0-T4), and an `InstanceSpec` into a `PairInstance` -- the filtered,
rescaled pair subgraph with covariates and method-independent bounds.

Design notes
------------
*Nothing is pickled but the spec.*  Regenerating an instance from `synth.make_instance` costs
0.01 s at n=200/400 and 0.04 s at n=800, and census + pair extraction + rescale another ~0.01 s,
so workers rebuild from `params_json` rather than receiving graphs over a pipe.

*`params_json` is the regeneration key.*  `G.graph["params"]`'s keys are exactly
`make_instance`'s kwargs (U0c added the four that were missing), so
`synth.make_instance(**json.loads(spec.params_json))` reproduces the stored `battery/figures/
C*.json` instances bit-identically.  `check_case_params` is the drift guard.

*Pair order is deterministic here, unlike `case_pipeline.pair_solves`.*  `census` builds
`reps_a` / `reps_b` by iterating a Python `set` of `(str, int)` tuples, so the *order* of the
pairs enumerated inside a dense component depends on `PYTHONHASHSEED` (four different orders of
the same ten pairs were observed on `C2_entangled_a0` under `PYTHONHASHSEED in {0,1,2,12345}`);
the *set* is stable.  `select_pairs` therefore sorts the dense enumeration, and
`tests/test_instances.py` compares sets of `(ra, rb, n_zips, dense)` against the stored JSONs.

Never writes anything under `battery/figures/` -- those are primary artifacts, read-only here.
"""
from __future__ import annotations

import inspect
import json
import signal
import sys
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional

import networkx as nx
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
for _p in (str(ROOT / "code"), str(ROOT / "battery" / "code")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import synth                                    # noqa: E402
import territory as T                           # noqa: E402
from contig_methods import base                 # noqa: E402

SCHEMA_VERSION = 1
DEFAULT_MIN_SHARE = 0.02
THETA, LAM = 0.40, 0.30
FIGURES_DIR = ROOT / "battery" / "figures"      # READ-ONLY: never written by this harness

_BOUNDS_WARNED = False


# ============================================================== case table (battery mirror)
@dataclass(frozen=True)
class CaseSpec:
    """A synthetic case: `run_battery.CASES` plus the per-case harness settings."""
    name: str
    scenario: Optional[str] = None
    n: int = 200
    seed: int = 1
    overrides: dict = field(default_factory=dict)
    min_share: float = DEFAULT_MIN_SHARE
    respect_state: bool = False
    has_json: bool = True                       # a battery/figures/<name>.json exists
    n_expected: Optional[dict] = None           # {(ra, rb): n_zips} when has_json is False


# `run_battery.CASES` verbatim (defaults n=200, seed from the row), plus C7b: the n=800
# scale pair that has no battery JSON -- its sizes are frozen literals (PLAN.md Q8).
BATTERY_CASES: dict[str, CaseSpec] = {c.name: c for c in [
    CaseSpec("C1_aligned_seed1",  "S1_aligned",   seed=1),
    CaseSpec("C1_aligned_seed2",  "S1_aligned",   seed=2),
    CaseSpec("C2_entangled_a0",   "S2_entangled", seed=1),
    CaseSpec("C2_entangled_a05",  "S2_entangled", seed=1, overrides=dict(alpha=0.5)),
    CaseSpec("C3_slivers_ms005",  "S3_slivers",   seed=1, min_share=0.005),
    CaseSpec("C3_slivers_ms02",   "S3_slivers",   seed=1, min_share=0.02),
    CaseSpec("C3_slivers_ms08",   "S3_slivers",   seed=1, min_share=0.08),
    CaseSpec("C4_separate",       "S4_separate",  seed=1),
    CaseSpec("C4_contested",      "S4_separate",  seed=1, overrides=dict(rho_books=1.0)),
    CaseSpec("C5_states_free",    "S5_states",    seed=1, respect_state=False),
    CaseSpec("C5_states_resp",    "S5_states",    seed=1, respect_state=True),
    CaseSpec("C6_tight",          "S6_tight",     seed=1),
    CaseSpec("C6_loose",          None,           seed=1,
             overrides=dict(alpha=1.0, n_rep_a=4, n_rep_b=4, saturation=0.12)),
    CaseSpec("C7_scale_n400",     "S1_aligned",   seed=1, n=400),
    CaseSpec("C9_heavytail_seed1", "S7_heavytail", seed=1),
    CaseSpec("C9_heavytail_seed2", "S7_heavytail", seed=2),
    # -- T2 extension, no battery JSON: sizes frozen at the U1b ★1 review -----------------
    CaseSpec("C7b_scale_n800_seed1", "S1_aligned", n=800, seed=1, has_json=False,
             n_expected={(1, 1): 320, (2, 2): 197, (0, 0): 169, (3, 3): 114}),
    CaseSpec("C7b_scale_n800_seed2", "S1_aligned", n=800, seed=2, has_json=False,
             n_expected={(0, 0): 464, (3, 3): 135, (1, 1): 124, (2, 2): 77}),
]}


@lru_cache(maxsize=None)
def _make_instance_defaults() -> dict:
    return {k: v.default for k, v in inspect.signature(synth.make_instance).parameters.items()
            if v.default is not inspect.Parameter.empty}


def resolve_params(case: str | CaseSpec) -> dict:
    """Full `make_instance` kwargs for a case: signature defaults | scenario | overrides | n,seed."""
    cs = BATTERY_CASES[case] if isinstance(case, str) else case
    kw = dict(_make_instance_defaults())
    if cs.scenario is not None:
        kw.update(synth.SCENARIOS[cs.scenario])
    kw.update(cs.overrides)
    kw.update(n=cs.n, seed=cs.seed)
    return kw


def params_key(params: dict) -> str:
    return json.dumps(params, sort_keys=True)


def load_case_json(case: str) -> dict:
    """The stored battery metrics JSON (read-only)."""
    with open(FIGURES_DIR / f"{case}.json") as f:
        return json.load(f)


def check_case_params(case: str) -> list:
    """Drift guard: every key the stored JSON records must survive `resolve_params` unchanged."""
    cs = BATTERY_CASES[case]
    if not cs.has_json:
        return []
    stored = load_case_json(case).get("params", {})
    resolved = resolve_params(cs)
    bad = []
    for k, v in stored.items():
        if k not in resolved:
            bad.append(f"{case}: resolved params missing stored key {k!r}")
        elif resolved[k] != v:
            bad.append(f"{case}: {k} resolved {resolved[k]!r} != stored {v!r}")
    return bad


def case_n_expected(case: str) -> dict:
    """{(ra, rb): n_zips} from the stored JSON, or the frozen literals for a JSON-less case."""
    cs = BATTERY_CASES[case]
    if not cs.has_json:
        return dict(cs.n_expected or {})
    return {(p["ra"], p["rb"]): p["n_zips"] for p in load_case_json(case)["pairs"]}


# ================================================================== graph construction
def _hand_p8():
    """P_8 with a monotone utility ratio (block tree is a path)."""
    G = nx.path_graph(8)
    for i in range(8):
        G.nodes[i].update(A=1.0 + 0.9 * (7 - i) / 7, B=1.0 + 0.9 * i / 7,
                          M=4.0 + 0.1 * i, pos=(i / 8, 0.5), rep_a=0, rep_b=0)
    return G


def _hand_trident():
    """Three P_3 legs off a common centre: the block-cut tree has a degree-3 node."""
    G = nx.Graph()
    G.add_node(0)
    for leg in range(3):
        prev = 0
        for j in range(3):
            z = 1 + 3 * leg + j
            G.add_edge(prev, z)
            prev = z
    ang = {0: (0.5, 0.5)}
    for leg in range(3):
        for j in range(3):
            z = 1 + 3 * leg + j
            th = 2 * np.pi * leg / 3
            ang[z] = (0.5 + 0.12 * (j + 1) * np.cos(th), 0.5 + 0.12 * (j + 1) * np.sin(th))
    for z in sorted(G):
        G.nodes[z].update(A=1.0 + 0.1 * z, B=1.0 + 0.1 * (9 - z), M=4.0 + 0.05 * z,
                          pos=ang[z], rep_a=0, rep_b=0)
    return G


def _hand_cycle10():
    """C_10: one biconnected block, so the block tree is a single node (a path)."""
    G = nx.cycle_graph(10)
    for i in range(10):
        th = 2 * np.pi * i / 10
        G.nodes[i].update(A=1.0 + 0.9 * (9 - i) / 9, B=1.0 + 0.9 * i / 9, M=4.0 + 0.1 * i,
                          pos=(0.5 + 0.3 * np.cos(th), 0.5 + 0.3 * np.sin(th)),
                          rep_a=0, rep_b=0)
    return G


HAND_GRAPHS: dict[str, Callable[[], nx.Graph]] = {
    "hand_p8": _hand_p8, "hand_trident": _hand_trident, "hand_cycle10": _hand_cycle10,
}
HAND_PREFIX = "hand:"


@lru_cache(maxsize=8)
def _graph_for(params_json: str):
    """The full instance graph for a regeneration key.  Cached: workers rebuild, never unpickle."""
    if params_json.startswith(HAND_PREFIX):
        return HAND_GRAPHS[params_json[len(HAND_PREFIX):]]()
    return synth.make_instance(**json.loads(params_json))


# ======================================================================== pair selection
def select_pairs(G, min_share: float = DEFAULT_MIN_SHARE) -> list:
    """`case_pipeline.pair_solves` (:42-77) minus the solve, with a deterministic pair order.

    Returns one dict per pair worth solving, in census order (components by descending
    opportunity, dense pairs sorted by (rep_a, rep_b)).
    """
    cen = T.census(G, min_share=min_share)
    O = T.overlap_graph(G)
    out = []
    for row in cen:
        dense = not row["shape"].startswith("1-1")
        if not dense:
            pairs = [(row["reps_a"][0][1], row["reps_b"][0][1])]
        else:
            Mc = row["M"]
            pairs = sorted((u[1], v[1]) for u in row["reps_a"] for v in row["reps_b"]
                           if O.has_edge(u, v) and O[u][v]["M"] >= min_share * Mc)
        for ra, rb in pairs:
            zips = T.zips_for_pair(G, ra, rb)
            if len(zips) < 4:
                continue
            out.append(dict(ra=ra, rb=rb, n_zips=len(zips), dense=dense,
                            comp_share=row["share"], comp_M=row["M"]))
    return out


# ========================================================================= instance specs
@dataclass(frozen=True)
class InstanceSpec:
    """One benchmark instance: a (rep_a, rep_b) pair of one regenerable case.

    `name` is the key everywhere -- rows, `instances.csv`, `instances/<name>.json`, assignment
    files, `--instances REGEX` -- and is filesystem-safe by construction.
    """
    name: str
    tier: str
    case: str
    scenario: Optional[str]
    n: int                                   # zips in the *whole* instance graph
    seed: int
    overrides: dict                          # provenance only; params_json is authoritative
    params_json: str                         # the regeneration key
    min_share: float
    rep_a: int
    rep_b: int
    n_expected: Optional[int]                # zips in the pair, from the stored JSON / literals
    dense: bool
    respect_state: bool
    named_failure: bool = False
    notes: str = ""
    comp_share: float = 1.0                  # census component's share of national opportunity

    @property
    def params(self) -> dict:
        if self.params_json.startswith(HAND_PREFIX):
            return {}
        return json.loads(self.params_json)

    @property
    def is_hand(self) -> bool:
        return self.params_json.startswith(HAND_PREFIX)


def _pair_name(case: str, ra, rb) -> str:
    return f"{case}__A{ra}_B{rb}"


def specs_for_case(case: str | CaseSpec, tier: str, *, sizes: Optional[tuple] = None,
                   named: frozenset = frozenset()) -> list:
    """Every pair of one case as an `InstanceSpec` (census order).

    `sizes` optionally restricts to pairs whose zip count is in the (lo, hi) range.
    """
    cs = BATTERY_CASES[case] if isinstance(case, str) else case
    pj = params_key(resolve_params(cs))
    G = _graph_for(pj)
    expect = case_n_expected(cs.name) if (cs.has_json or cs.n_expected) else {}
    out = []
    for p in select_pairs(G, cs.min_share):
        if sizes is not None and not (sizes[0] <= p["n_zips"] <= sizes[1]):
            continue
        name = _pair_name(cs.name, p["ra"], p["rb"])
        out.append(InstanceSpec(
            name=name, tier=tier, case=cs.name, scenario=cs.scenario, n=cs.n, seed=cs.seed,
            overrides=dict(cs.overrides), params_json=pj, min_share=cs.min_share,
            rep_a=p["ra"], rep_b=p["rb"],
            n_expected=expect.get((p["ra"], p["rb"]), p["n_zips"]),
            dense=p["dense"], respect_state=cs.respect_state,
            named_failure=name in named, comp_share=float(p["comp_share"])))
    return out


# --------------------------------------------------------------------------- the tiers
T0_CASES = tuple(CaseSpec(f"T0_n{n}_s{s}", "S1_aligned", n=n, seed=s, has_json=False)
                 for n in (40, 50, 60) for s in range(1, 11))
T1_CASES = ("C1_aligned_seed1", "C1_aligned_seed2", "C2_entangled_a0", "C2_entangled_a05",
            "C3_slivers_ms02", "C4_separate", "C4_contested", "C5_states_free",
            "C6_tight", "C6_loose", "C9_heavytail_seed1", "C9_heavytail_seed2")
T2_CASES = ("C7_scale_n400", "C7b_scale_n800_seed1", "C7b_scale_n800_seed2")
T4_CASES = ("C5_states_resp",)

# The six named contiguity failures (CLAUDE.md Trap 11 / TEST_PLAN §2); sizes asserted below.
NAMED_FAILURE_NAMES = ("C1_aligned_seed2__A0_B0", "C5_states_resp__A2_B2",
                       "C7_scale_n400__A3_B3", "C7_scale_n400__A0_B0",
                       "C7_scale_n400__A1_B1", "C9_heavytail_seed2__A2_B2")
NAMED_FAILURE_SIZES = (69, 61, 205, 125, 44, 31)
_NAMED = frozenset(NAMED_FAILURE_NAMES)


def build_T0_full() -> list:
    """Every S1_aligned n in {40,50,60}, seeds 1-10 pair with 8-20 zips (90 pairs)."""
    out = []
    for cs in T0_CASES:
        for sp in specs_for_case(cs, "T0", sizes=(8, 20)):
            out.append(replace(sp, name=f"T0_n{cs.n}_s{cs.seed}__A{sp.rep_a}_B{sp.rep_b}"))
    return out


def build_T0() -> list:
    """The curated ground-truth tier: one pair per distinct zip count in 8..20 (13 instances).

    `(n, seed, rep_a, rep_b)` order picks the representative, so the tier is a deterministic
    ladder of sizes rather than 90 near-duplicates.  `build_T0_full` is the full sweep.
    """
    seen, out = set(), []
    for sp in build_T0_full():
        if sp.n_expected in seen:
            continue
        seen.add(sp.n_expected)
        out.append(sp)
    return sorted(out, key=lambda s: (s.n_expected, s.name))


def build_T1() -> list:
    out = []
    for case in T1_CASES:
        out += specs_for_case(case, "T1", named=_NAMED)
    return out


def build_T2() -> list:
    out = []
    for case in T2_CASES:
        out += specs_for_case(case, "T2", named=_NAMED)
    return out


def build_T3() -> list:
    """Twin-derived pairs (PLAN.md C.3 / U6).

    Extension point only: U6 (main session) wires `twin.load_twin` + `twin.twin_pairs` in once
    a twin instance exists on disk.  Until then this tier is empty by design.
    """
    try:                                    # U6: replace the body, not the import guard
        from twin import load_twin, twin_pairs   # noqa: F401
    except ImportError:
        return []
    return []                               # U6 wires T3a/T3b here


def build_T4() -> list:
    out = []
    for case in T4_CASES:
        out += specs_for_case(case, "T4", named=_NAMED)
    return out + [replace(s, tier="T4") for s in build_T3() if s.respect_state]


def build_hand() -> list:
    """Tiny hand graphs for the unit tests (never part of a stage preset)."""
    out = []
    for name in sorted(HAND_GRAPHS):
        G = HAND_GRAPHS[name]()
        out.append(InstanceSpec(name=name, tier="hand", case=name, scenario=None,
                                n=G.number_of_nodes(), seed=0, overrides={},
                                params_json=HAND_PREFIX + name, min_share=DEFAULT_MIN_SHARE,
                                rep_a=0, rep_b=0, n_expected=G.number_of_nodes(),
                                dense=False, respect_state=False))
    return out


TIERS: dict[str, Callable[[], list]] = {
    "T0": build_T0, "T0_full": build_T0_full, "T1": build_T1, "T2": build_T2,
    "T3": build_T3, "T4": build_T4, "hand": build_hand,
}


@lru_cache(maxsize=1)
def named_failures() -> list:
    """The six named failures, resolved out of T1/T2/T4 by name; sizes asserted."""
    by_name = {s.name: s for s in build_T1() + build_T2() + build_T4()}
    out = []
    for name, n_exp in zip(NAMED_FAILURE_NAMES, NAMED_FAILURE_SIZES):
        sp = by_name.get(name)
        if sp is None:
            raise AssertionError(f"named failure {name!r} not produced by T1/T2/T4")
        if sp.n_expected != n_exp:
            raise AssertionError(f"named failure {name}: n_expected {sp.n_expected} != {n_exp}")
        out.append(sp)
    return out


def specs_for_tiers(tiers) -> list:
    """Specs for a list of tier names, de-duplicated by `name`, in tier order."""
    seen, out = set(), []
    for t in tiers:
        if t not in TIERS:
            raise KeyError(f"unknown tier {t!r}; known: {sorted(TIERS)}")
        for sp in TIERS[t]():
            if sp.name in seen:
                continue
            seen.add(sp.name)
            out.append(sp)
    return out


# ==================================================================== the built instance
@dataclass
class PairInstance:
    """A spec realised: the filtered, rescaled pair subgraph plus covariates and bounds."""
    spec: InstanceSpec
    G: nx.Graph                     # pair subgraph, state-filtered and rescaled
    nodes: list
    scale: float
    edge_share_deleted: float
    covariates: dict
    bounds: dict

    @property
    def n(self) -> int:
        return len(self.nodes)

    @property
    def free_to_a(self):
        return self.bounds.get("free_to_a")

    @property
    def product_free(self):
        return self.bounds.get("product_free")


NO_BOUNDS = dict(UB_free_frac=None, UB_free_nash=None, product_free=None, free_to_a=None,
                 free_status="bounds_module_missing")


def bounds_module():
    """`contig_methods.bounds` if U2 has landed, else None (soft dependency, PLAN.md C.5)."""
    try:
        from contig_methods import bounds       # noqa: PLC0415
    except ImportError:
        return None
    return bounds


def warn_bounds_missing(log=None) -> bool:
    """One-time CLI warning that the method-independent bounds are unavailable."""
    global _BOUNDS_WARNED
    if bounds_module() is not None:
        return False
    if not _BOUNDS_WARNED:
        _BOUNDS_WARNED = True
        msg = ("contig_methods.bounds not importable (U2 has not landed): UB_free_frac, "
               "UB_free_nash, product_free and cost_of_contiguity will be null on every row")
        (log or (lambda m: print(m, file=sys.stderr)))(msg)
    return True


class _Timeout(Exception):
    pass


def _run_capped(fn, seconds: Optional[float]):
    """Run `fn()` under a SIGALRM cap (the bounds solve has no internal global limit)."""
    if not seconds or not hasattr(signal, "SIGALRM"):
        return fn()

    def _fire(signum, frame):
        raise _Timeout(f"exceeded {seconds:g}s")

    old = signal.signal(signal.SIGALRM, _fire)
    signal.setitimer(signal.ITIMER_REAL, max(float(seconds), 0.01))
    try:
        return fn()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def compute_bounds(G, nodes, ua, ub, *, theta=THETA, lam=LAM, kappa=0.0,
                   bounds_cap: Optional[float] = 120.0) -> dict:
    """Method-independent upper bounds on the contiguous optimum (PLAN.md C.1 `bounds.py`).

    Both bound `obj` from above because contiguity only shrinks the feasible set and
    rho*perimeter >= 0.  `free_status` records why a bound is missing.
    """
    if kappa:
        # bounds.ub_free_nash has no kappa argument: the free bounds are only valid for the
        # kappa = 0 utilities, so a travel-cost run (W11) reports them as skipped.
        return dict(NO_BOUNDS, free_status="skipped_kappa")
    mod = bounds_module()
    if mod is None:
        return dict(NO_BOUNDS)
    out = dict(NO_BOUNDS, free_status="ok")
    try:
        out["UB_free_frac"] = float(mod.ub_free_frac(ua, ub))
    except Exception as e:                                    # noqa: BLE001
        out["free_status"] = f"frac_error: {type(e).__name__}: {e}"
    try:
        d = _run_capped(lambda: mod.ub_free_nash(G, nodes, theta, lam), bounds_cap)
        out["UB_free_nash"] = None if d.get("UB") is None else float(d["UB"])
        out["product_free"] = None if d.get("product") is None else float(d["product"])
        out["free_to_a"] = None if d.get("to_a") is None else sorted(d["to_a"], key=base._sort_key)
        out["free_gap"] = d.get("gap")
    except _Timeout as e:
        out["free_status"] = f"nash_timeout: {e}"
    except Exception as e:                                    # noqa: BLE001
        out["free_status"] = f"nash_error: {type(e).__name__}: {e}"
    return out


def mechanism_tag(spec: InstanceSpec, cov: dict) -> str:
    """Failure-mechanism tag (CLAUDE.md trap 11 / `research/contiguity/OPTIONS.md`): a string
    concatenating one letter per mechanism this instance's covariates exhibit --

      a  pre-existing disconnection   pair_components > 1
      b  pure scale                   n >= 125
      c  value concentration          "heavytail" in the case name, or top5_share_u >= 0.35
      d  sparse active zips / glue    active_frac < 1   (what real data adds; U8/twin-only
                                       so far -- no T0-T2 synthetic instance sets it)

    Letters concatenate in a-b-c-d order (e.g. "ab"); "" if none apply.  A gap-reporting
    aggregate only, not a solver hint -- `run_summary`'s mechanism panel groups rows by it.
    """
    letters = []
    if cov.get("pair_components", 1) > 1:
        letters.append("a")
    if cov.get("n", 0) >= 125:
        letters.append("b")
    if "heavytail" in (spec.case or "") or cov.get("top5_share_u", 0.0) >= 0.35:
        letters.append("c")
    if cov.get("active_frac", 1.0) < 1:
        letters.append("d")
    return "".join(letters)


def build_pair(spec: InstanceSpec, *, theta: float = THETA, lam: float = LAM,
               rescale: bool = True, kappa: float = 0.0,
               distances: Optional[Callable] = None, with_bounds: bool = False,
               bounds_cap: Optional[float] = 120.0) -> PairInstance:
    """Regenerate a spec's pair subgraph: filter (state) -> rescale -> covariates [-> bounds].

    `distances(G_full, zips) -> {zip: (d_a, d_b)}` supplies the W11 travel-cost attributes.
    Rescaling is *always* computed at kappa = 0 so the recorded `scale` is a property of the
    instance, not of the kappa sweep (PLAN.md ★1 Q4).
    """
    G0 = _graph_for(spec.params_json)
    zips = sorted(T.zips_for_pair(G0, spec.rep_a, spec.rep_b), key=base._sort_key)
    if spec.n_expected is not None and len(zips) != spec.n_expected:
        raise AssertionError(
            f"{spec.name}: regenerated pair has {len(zips)} zips, expected {spec.n_expected} "
            "(generator drift -- see instances.check_case_params)")
    H, edge_share_deleted = base.filter_pair(G0, zips, respect_state=spec.respect_state)
    if distances is not None:
        dd = distances(G0, zips)
        for z in zips:
            da, db = dd[z]
            H.nodes[z]["d_a"] = float(da)
            H.nodes[z]["d_b"] = float(db)
    nodes = sorted(H, key=base._sort_key)
    if rescale:
        H, scale = base.rescale_pair(H, nodes, theta, lam, kappa=0.0)
    else:
        scale = 1.0
        H.graph["scale"] = 1.0
    ua, ub = base.utilities(H, nodes, theta, lam, kappa)
    bnd = (compute_bounds(H, nodes, ua, ub, theta=theta, lam=lam, kappa=kappa,
                          bounds_cap=bounds_cap) if with_bounds else dict(NO_BOUNDS,
                                                                          free_status="not_requested"))
    cov = base.covariates(H, nodes, ua, ub, free_to_a=bnd.get("free_to_a"))
    cov.update(edge_share_deleted=float(edge_share_deleted), scale=float(scale),
               n_expected=spec.n_expected, dense=bool(spec.dense),
               comp_share=float(spec.comp_share))
    cov["mechanism"] = mechanism_tag(spec, cov)
    return PairInstance(spec=spec, G=H, nodes=nodes, scale=float(scale),
                        edge_share_deleted=float(edge_share_deleted), covariates=cov,
                        bounds=bnd)


# ================================================================== instance JSON (gfx input)
INSTANCE_JSON_KEYS = ("schema_version", "spec", "nodes", "pos", "edges", "A", "B", "M",
                      "state", "rep_a", "rep_b", "free_to_a", "covariates", "scale",
                      "edge_share_deleted", "bounds", "rows")


def _jsonable(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, frozenset)):
        return sorted(o, key=base._sort_key)
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON-serialisable: {type(o).__name__}")


def instance_json(pi: PairInstance) -> dict:
    """The `gfx.producers.instance_card` input.  `rows` is null: the card joins `rows.jsonl`
    by instance name rather than carrying a copy of the run's results (PLAN.md ★1 Q5).

    `edges` are *index* pairs into `nodes` (`gfx.schemas.validate_instance_json`'s contract,
    matched by `gfx.schemas.make_fixture_instance` and every gfx consumer) -- not zip ids, so
    they must be remapped through `nodes`'s position order."""
    G0 = _graph_for(pi.spec.params_json)
    nodes, H = pi.nodes, pi.G
    node_idx = {z: i for i, z in enumerate(nodes)}
    d = dict.fromkeys(INSTANCE_JSON_KEYS)
    d.update(
        schema_version=SCHEMA_VERSION,
        spec={k: v for k, v in vars(pi.spec).items()},
        nodes=list(nodes),
        pos=[list(H.nodes[z].get("pos", (0.0, 0.0))) for z in nodes],
        edges=[[node_idx[u], node_idx[v]]
               for u, v in sorted(H.edges(), key=lambda e: (base._sort_key(e[0]),
                                                            base._sort_key(e[1])))],
        A=[float(H.nodes[z]["A"]) for z in nodes],
        B=[float(H.nodes[z]["B"]) for z in nodes],
        M=[float(H.nodes[z]["M"]) for z in nodes],
        state=[H.nodes[z].get("state") for z in nodes],
        rep_a=[G0.nodes[z].get("rep_a") for z in nodes],     # unfiltered graph: pre-merger map
        rep_b=[G0.nodes[z].get("rep_b") for z in nodes],
        free_to_a=pi.bounds.get("free_to_a"),
        covariates=pi.covariates,
        scale=pi.scale,
        edge_share_deleted=pi.edge_share_deleted,
        bounds={k: v for k, v in pi.bounds.items() if k != "free_to_a"},
        rows=None,
    )
    return d


def write_instance_json(pi: PairInstance, path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(instance_json(pi), f, default=_jsonable)
    return path


if __name__ == "__main__":                       # quick census of the tiers
    for t in ("T0", "T0_full", "T1", "T2", "T3", "T4", "hand"):
        sp = TIERS[t]()
        sizes = sorted({s.n_expected for s in sp})
        print(f"{t:<8} {len(sp):>3} instances   sizes {sizes[:6]}{' ...' if len(sizes) > 6 else ''}")
    print("named failures:", [(s.name, s.n_expected) for s in named_failures()])
