"""Exact Group 2 geography repair, validation, and certificate helpers.

The functions in this module operate only on aggregate planning units. They do not load or
write customer-level records. A candidate is accepted only after a policy-level semantic audit
and reconstruction against the complete target MILP.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import networkx as nx
import numpy as np
from scipy import sparse

from td.solvers import level0
from td.solvers import milp_engines
from td.solvers import state_splits
from tools import group2_checkpoint


@dataclass(frozen=True)
class GeographyPolicy:
    """Explicit business and geography contract for one pure-bundle target."""

    bundle: str = "N"
    expected_count: int | None = 14
    maximum_count: int | None = None
    contact_cap: int = 6
    distance_km: float = 900.0
    distance_overrides_km: Mapping[str, float] = field(
        default_factory=lambda: {"WA": 1200.0})
    unit_parent: Mapping[str, str] = field(default_factory=dict)
    allowed_units: frozenset[str] | None = None
    split_caps: Mapping[str, int] = field(default_factory=dict)
    macro_contact_cap: int | None = 2
    band_allowance: Mapping[str, float] = field(default_factory=dict)
    tolerance: float = 1e-6


@dataclass(frozen=True)
class CandidateWitness:
    """Full-precision contact and share blocks before auxiliary reconstruction."""

    z: np.ndarray
    y: np.ndarray
    source: str = ""

    @classmethod
    def from_result(cls, result: Mapping[str, Any], source: str = "solver") -> "CandidateWitness":
        z = result.get("_raw_z", result.get("z"))
        y = result.get("_raw_y", result.get("y"))
        if z is None or y is None:
            raise ValueError("candidate result needs z and y")
        return cls(np.asarray(z, float), np.asarray(y, float), source)


@dataclass(frozen=True)
class ValidationReport:
    """Independent semantic and original-matrix acceptance result."""

    accepted: bool
    issues: tuple[str, ...]
    metrics: Mapping[str, Any]
    districts: tuple[Mapping[str, Any], ...]
    matrix: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class RepairAttempt:
    radius: int | None
    seconds_limit: float
    status: str
    seconds: float
    objective: float | None = None
    dual_bound: float | None = None
    nodes: int | None = None
    accepted: bool = False
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class RepairOutcome:
    result: Mapping[str, Any] | None
    attempts: tuple[RepairAttempt, ...]


def _policy_record(policy: GeographyPolicy) -> dict[str, Any]:
    record = dataclasses.asdict(policy)
    allowed = record.get("allowed_units")
    record["allowed_units"] = None if allowed is None else sorted(allowed)
    return record


def _bundle_slots(problem: level0.Level0Problem, bundle: str) -> list[int]:
    if bundle not in problem.slots:
        raise ValueError(f"unknown bundle {bundle!r}; expected one of {list(problem.slots)}")
    start, stop = problem.slots[bundle]
    return list(range(start, stop))


def require_full_bundle_coverage(problem: level0.Level0Problem,
                                 bundle: str = "N") -> level0.Level0Problem:
    """Require every positive-mass planning unit to put its full share in ``bundle``."""
    slots = _bundle_slots(problem, bundle)
    active = np.any(np.asarray(problem.W[:, slots], float) > 0.0, axis=1)
    changed = problem
    for s in np.flatnonzero(active):
        changed = level0.require_cover(changed, int(s), problem.bundles[bundle])
    return changed


def _parent(unit: str, policy: GeographyPolicy) -> str:
    return policy.unit_parent.get(unit, unit)


def _shape_witness(problem: level0.Level0Problem, witness: CandidateWitness
                   ) -> tuple[np.ndarray, np.ndarray]:
    shape = (problem.n_state, problem.k)
    z = np.asarray(witness.z, float)
    y = np.asarray(witness.y, float)
    if z.shape != shape or y.shape != shape:
        raise ValueError(f"candidate z and y must both have shape {shape}, got {z.shape} and {y.shape}")
    return z, y


def canonicalize_reference(problem: level0.Level0Problem, witness: CandidateWitness,
                           bundle: str = "N") -> CandidateWitness:
    """Put interchangeable reference columns in the model's nonincreasing-mass order."""
    z, y = _shape_witness(problem, witness)
    slots = _bundle_slots(problem, bundle)
    ordered = sorted(
        slots,
        key=lambda j: (
            -float((problem.W[:, j] * y[:, j]).sum()),
            tuple(int(v) for v in np.flatnonzero(z[:, j] > 0.5)),
            j,
        ),
    )
    out_z, out_y = z.copy(), y.copy()
    for target, source in zip(slots, ordered):
        out_z[:, target] = z[:, source]
        out_y[:, target] = y[:, source]
    return CandidateWitness(out_z, out_y, witness.source)


def load_reference(path: Path | str, problem: level0.Level0Problem,
                   bundle: str = "N") -> CandidateWitness:
    """Load a full-precision checkpoint, z/y JSON, or plan.json as a repair reference."""
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    shape = (problem.n_state, problem.k)
    if isinstance(payload, dict) and "warm_start" in payload:
        vector = np.asarray(payload["warm_start"], float)
        if vector.shape != (problem.n_var,):
            raise ValueError(f"reference warm_start has shape {vector.shape}, expected {(problem.n_var,)}")
        z = vector[problem.off_z:problem.off_z + problem.n_state * problem.k].reshape(shape)
        y = vector[problem.off_y:problem.off_y + problem.n_state * problem.k].reshape(shape)
    elif isinstance(payload, dict) and "z" in payload and "y" in payload:
        z = np.asarray(payload["z"], float).reshape(shape)
        y = np.asarray(payload["y"], float).reshape(shape)
    elif isinstance(payload, dict) and isinstance(payload.get("slots"), list):
        records = [rec for rec in payload["slots"] if rec.get("bundle") == bundle]
        slots = _bundle_slots(problem, bundle)
        if len(records) != len(slots):
            raise ValueError(f"reference plan has {len(records)} {bundle} slots, expected {len(slots)}")
        records.sort(key=lambda rec: (-float(rec.get("mass", 0.0)), str(rec.get("id", ""))))
        state_index = {unit: s for s, unit in enumerate(problem.state_list)}
        z, y = np.zeros(shape), np.zeros(shape)
        for j, rec in zip(slots, records):
            for unit, share in dict(rec.get("y") or {}).items():
                if unit not in state_index:
                    raise ValueError(f"reference plan names unknown planning unit {unit!r}")
                s = state_index[unit]
                y[s, j] = float(share)
                z[s, j] = 1.0
    else:
        raise ValueError("reference must contain warm_start, z/y, or plan slots")
    if not np.isfinite(z).all() or not np.isfinite(y).all():
        raise ValueError("reference contains non-finite contacts or shares")
    if np.max(np.abs(z - np.rint(z)), initial=0.0) > 1e-6:
        raise ValueError("reference contacts are materially fractional")
    return canonicalize_reference(problem, CandidateWitness(z, y, str(source)), bundle)


def hamming_problem(problem: level0.Level0Problem, reference: CandidateWitness,
                    radius: int | None, bundle: str = "N") -> tuple[level0.Level0Problem, int]:
    """Return a model minimizing contact Hamming distance, optionally inside a radius."""
    z_ref, _ = _shape_witness(problem, reference)
    slots = _bundle_slots(problem, bundle)
    c = np.zeros(problem.n_var)
    constant = 0
    cols: list[int] = []
    vals: list[float] = []
    for s in range(problem.n_state):
        for j in slots:
            col = problem.off_z + s * problem.k + j
            value = bool(z_ref[s, j] > 0.5)
            c[col] = -1.0 if value else 1.0
            cols.append(col)
            vals.append(float(c[col]))
            constant += int(value)
    changed = dataclasses.replace(problem, c=c)
    if radius is not None:
        if int(radius) < 0:
            raise ValueError("Hamming radius must be nonnegative")
        changed = level0.append_row(
            changed, f"hamming_radius_{bundle}", cols, vals,
            -np.inf, float(int(radius) - constant))
        if not isinstance(changed, level0.Level0Problem):
            raise TypeError("append_row did not preserve Level0Problem")
    return changed, constant


def hamming_distance(problem: level0.Level0Problem, witness: CandidateWitness,
                     reference: CandidateWitness, bundle: str = "N") -> int:
    z, _ = _shape_witness(problem, witness)
    z_ref, _ = _shape_witness(problem, reference)
    slots = _bundle_slots(problem, bundle)
    return int(np.not_equal(z[:, slots] > 0.5, z_ref[:, slots] > 0.5).sum())


def _required_cover(problem: level0.Level0Problem) -> list[tuple[int, int, float]]:
    start, stop = problem.rows["cover"]
    expected = problem.n_state * len(problem.channels)
    if stop - start != expected:
        raise ValueError(f"cover has {stop - start} rows, expected {expected}")
    out = []
    for s in range(problem.n_state):
        for c in range(len(problem.channels)):
            lower = float(problem.lb[start + s * len(problem.channels) + c])
            if np.isfinite(lower) and lower > 0.0:
                out.append((s, c, lower))
    return out


def _matrix_report(problem: level0.Level0Problem, witness: CandidateWitness,
                   tolerance: float) -> tuple[dict[str, Any], np.ndarray | None, str | None]:
    try:
        x = group2_checkpoint.reconstruct_vector(
            problem, {"z": witness.z, "y": witness.y})
    except (TypeError, ValueError) as exc:
        return {"accepted": False, "message": str(exc)}, None, str(exc)
    values = np.asarray(problem.A @ x, float)
    lower = np.maximum(problem.lb - values, 0.0, where=np.isfinite(problem.lb),
                       out=np.zeros_like(values))
    upper = np.maximum(values - problem.ub, 0.0, where=np.isfinite(problem.ub),
                       out=np.zeros_like(values))
    bound = max(float(np.max(problem.var_lb - x, initial=0.0)),
                float(np.max(x - problem.var_ub, initial=0.0)))
    integer = float(np.max(np.abs(x[problem.integrality != 0]
                                  - np.rint(x[problem.integrality != 0])), initial=0.0))
    report = {
        "accepted": max(float(lower.max(initial=0.0)), float(upper.max(initial=0.0)),
                         bound, integer) <= tolerance,
        "max_lower_residual": float(lower.max(initial=0.0)),
        "max_upper_residual": float(upper.max(initial=0.0)),
        "max_bound_residual": bound,
        "max_integrality_residual": integer,
    }
    return report, x, None if report["accepted"] else "original target matrix check failed"


def validate_candidate(problem: level0.Level0Problem, witness: CandidateWitness,
                       policy: GeographyPolicy) -> ValidationReport:
    """Check raw values, all explicit policy rules, and the complete target matrix."""
    issues: list[str] = []
    metrics: dict[str, Any] = {}
    districts: list[dict[str, Any]] = []
    try:
        z_raw, y = _shape_witness(problem, witness)
    except ValueError as exc:
        return ValidationReport(False, (str(exc),), {}, (), {"accepted": False})
    if not np.isfinite(z_raw).all() or not np.isfinite(y).all():
        return ValidationReport(False, ("candidate contains non-finite contacts or shares",),
                                {}, (), {"accepted": False})
    tol = float(policy.tolerance)
    z_fraction = float(np.max(np.abs(z_raw - np.rint(z_raw)), initial=0.0))
    metrics["max_raw_contact_fractionality"] = z_fraction
    if z_fraction > tol:
        issues.append(f"contacts are fractional by {z_fraction:.6g}")
    z = np.rint(z_raw).astype(bool)
    min_y = float(y.min(initial=0.0))
    max_y = float(y.max(initial=0.0))
    metrics.update(min_share=min_y, max_share=max_y)
    if min_y < -tol or max_y > 1.0 + tol:
        issues.append("shares lie outside [0,1]")
    yz_upper = float(np.max(y - z.astype(float), initial=0.0))
    yz_lower = float(np.max(problem.eta * z.astype(float) - y, initial=0.0))
    metrics.update(max_share_above_contact=yz_upper, max_min_share_shortfall=yz_lower)
    if yz_upper > tol:
        issues.append("a positive share is assigned without a contact")
    if yz_lower > tol:
        issues.append("a selected contact is below the minimum share")

    slots = _bundle_slots(problem, policy.bundle)
    used = z[:, slots].any(axis=0)
    metrics["used_count"] = int(used.sum())
    if policy.expected_count is not None and int(used.sum()) != int(policy.expected_count):
        issues.append(f"{policy.bundle} uses {int(used.sum())} slots, expected {policy.expected_count}")
    if policy.maximum_count is not None and int(used.sum()) > int(policy.maximum_count):
        issues.append(f"{policy.bundle} uses {int(used.sum())} slots, cap {policy.maximum_count}")
    contact_counts = z[:, slots].sum(axis=0)
    if np.max(contact_counts, initial=0) > policy.contact_cap:
        issues.append(f"a district exceeds the {policy.contact_cap}-unit contact cap")

    if policy.allowed_units is not None:
        outside = sorted(problem.state_list[s] for s in range(problem.n_state)
                         if z[s, slots].any() and problem.state_list[s] not in policy.allowed_units)
        if outside:
            issues.append(f"disallowed planning units are contacted: {outside}")
    for unit, cap in policy.split_caps.items():
        if unit in problem.state_list:
            s = problem.state_list.index(unit)
            if int(z[s, slots].sum()) > int(cap):
                issues.append(f"{unit} contacts {int(z[s, slots].sum())} districts, cap {cap}")
    if policy.macro_contact_cap is not None:
        for s, unit in enumerate(problem.state_list):
            if unit in policy.unit_parent and int(z[s, slots].sum()) > policy.macro_contact_cap:
                issues.append(f"{unit} contacts {int(z[s, slots].sum())} districts, macro cap "
                              f"{policy.macro_contact_cap}")

    coverage = y @ problem.slot_has.astype(float)
    cover_excess = float(np.max(coverage - problem.cover_ub, initial=0.0))
    metrics["max_coverage_excess"] = cover_excess
    if cover_excess > tol:
        issues.append("channel coverage exceeds the available share")
    required_shortfall = 0.0
    required = _required_cover(problem)
    for s, c, target in required:
        required_shortfall = max(required_shortfall, target - float(coverage[s, c]))
    metrics.update(required_cover_rows=len(required),
                   max_required_coverage_shortfall=max(0.0, required_shortfall))
    if required_shortfall > tol:
        issues.append("explicit full-coverage rows are not satisfied")

    graph = nx.Graph()
    graph.add_nodes_from(range(problem.n_state))
    graph.add_edges_from(problem.edges)
    xy = np.asarray(problem.state_xy, float)
    has_xy = xy.shape[0] == problem.n_state and xy.ndim == 2 and xy.shape[1] >= 2
    max_distance_excess = 0.0
    max_band_residual = 0.0
    for local, j in enumerate(slots):
        selected = [int(s) for s in np.flatnonzero(z[:, j])]
        mass = float((problem.W[:, j] * y[:, j]).sum())
        upper = float(problem.U_j[j]) + sum(
            float(policy.band_allowance.get(problem.state_list[s], 0.0)) for s in selected)
        band_residual = (max(0.0, float(problem.L_j[j]) - mass, mass - upper)
                         if selected else max(0.0, mass))
        max_band_residual = max(max_band_residual, band_residual)
        connected = not selected or nx.is_connected(graph.subgraph(selected))
        forbidden: list[list[Any]] = []
        if not connected:
            issues.append(f"slot {j} is disconnected")
        if has_xy:
            for ai, a in enumerate(selected):
                for b in selected[ai + 1:]:
                    distance = float(np.linalg.norm(xy[a, :2] - xy[b, :2]))
                    limit = max(
                        policy.distance_km,
                        float(policy.distance_overrides_km.get(
                            _parent(problem.state_list[a], policy), policy.distance_km)),
                        float(policy.distance_overrides_km.get(
                            _parent(problem.state_list[b], policy), policy.distance_km)),
                    )
                    excess = distance - limit
                    max_distance_excess = max(max_distance_excess, excess)
                    if excess > tol:
                        forbidden.append([problem.state_list[a], problem.state_list[b], distance,
                                          limit])
        elif len(selected) > 1:
            issues.append(f"slot {j} has no coordinates for an independent distance check")
        if forbidden:
            issues.append(f"slot {j} contains {len(forbidden)} forbidden distance pair(s)")
        districts.append({
            "slot": j,
            "used": bool(selected),
            "units": [problem.state_list[s] for s in selected],
            "contacts": len(selected),
            "mass": mass,
            "L": float(problem.L_j[j]),
            "effective_U": upper,
            "connected": connected,
            "forbidden_pairs": forbidden,
        })
    metrics.update(max_band_residual=max_band_residual,
                   max_distance_excess=max(0.0, max_distance_excess))
    if max_band_residual > tol:
        issues.append("a district violates its effective opportunity band")

    by_parent: dict[str, list[int]] = {}
    for s, unit in enumerate(problem.state_list):
        by_parent.setdefault(_parent(unit, policy), []).append(s)
    for parent, members in by_parent.items():
        if not any(z[s, slots].any() for s in members):
            continue
        for s in members:
            share = float(y[s, slots].sum())
            if abs(share - 1.0) > tol:
                issues.append(f"parent purity requires {problem.state_list[s]} full share in "
                              f"{policy.bundle}; got {share:.6g} for parent {parent}")

    matrix, _x, matrix_issue = _matrix_report(problem, witness, tol)
    if matrix_issue is not None:
        issues.append(matrix_issue)
    return ValidationReport(not issues and bool(matrix.get("accepted")), tuple(issues), metrics,
                            tuple(districts), matrix)


def _result_number(result: Mapping[str, Any], name: str) -> float | None:
    value = result.get(name)
    if isinstance(value, (int, float)) and np.isfinite(float(value)):
        return float(value)
    return None


def solve_repair_ladder(
    problem: level0.Level0Problem,
    reference: CandidateWitness,
    validate: Callable[[CandidateWitness], ValidationReport],
    *,
    engine: str = "highs",
    threads: int = 2,
    heuristic_effort: float | None = None,
    schedule: Sequence[tuple[int | None, float]] = ((8, 10.0), (24, 10.0), (None, 70.0)),
) -> RepairOutcome:
    """Run bounded Hamming neighborhoods and stop at the first independently accepted point."""
    attempts: list[RepairAttempt] = []
    for radius, seconds in schedule:
        current, constant = hamming_problem(problem, reference, radius)
        started = time.monotonic()
        try:
            result = milp_engines.solve_problem(
                current, engine, time_limit=float(seconds), threads=threads,
                heuristic_effort=heuristic_effort)
        except state_splits.SolveFailure as exc:
            attempts.append(RepairAttempt(radius, float(seconds), exc.reason,
                                          time.monotonic() - started))
            continue
        witness = CandidateWitness.from_result(result, f"hamming-radius-{radius}")
        report = validate(witness)
        objective = hamming_distance(problem, witness, reference)
        attempts.append(RepairAttempt(
            radius, float(seconds), str(result.get("status", "returned")),
            time.monotonic() - started, float(objective), _result_number(result, "dual_bound"),
            int(result["nodes"]) if _result_number(result, "nodes") is not None else None,
            report.accepted, report.issues))
        if report.accepted:
            accepted = dict(result)
            accepted["u"] = np.asarray(result["used"], bool)
            accepted["passes"] = [{
                "name": "hamming_repair",
                "value": objective,
                "certified": result.get("status") == 0,
                "status": result.get("status"),
                "seconds": attempts[-1].seconds,
                "radius": radius,
                "objective_without_constant": _result_number(result, "objective"),
                "objective_constant": constant,
            }]
            accepted["problem"] = problem
            return RepairOutcome(accepted, tuple(attempts))
    return RepairOutcome(None, tuple(attempts))


def disconnected_components(problem: level0.Level0Problem, witness: CandidateWitness,
                            bundle: str = "N") -> list[tuple[int, tuple[int, ...]]]:
    z, _ = _shape_witness(problem, witness)
    graph = nx.Graph()
    graph.add_nodes_from(range(problem.n_state))
    graph.add_edges_from(problem.edges)
    out: list[tuple[int, tuple[int, ...]]] = []
    for j in _bundle_slots(problem, bundle):
        selected = [int(s) for s in np.flatnonzero(z[:, j] > 0.5)]
        if len(selected) > 1:
            parts = sorted((tuple(sorted(part)) for part in nx.connected_components(
                graph.subgraph(selected))), key=lambda part: (len(part), part))
            if len(parts) > 1:
                out.extend((j, part) for part in parts)
    return out


def append_connectivity_cuts(problem: level0.Level0Problem, witness: CandidateWitness,
                             start_index: int = 0, bundle: str = "N"
                             ) -> tuple[level0.Level0Problem, int]:
    """Add globally valid boundary cuts for every disconnected incumbent component."""
    z, _ = _shape_witness(problem, witness)
    graph = nx.Graph()
    graph.add_nodes_from(range(problem.n_state))
    graph.add_edges_from(problem.edges)
    rr: list[int] = []
    cc: list[int] = []
    vv: list[float] = []
    names: list[str] = []
    for j, component_tuple in disconnected_components(problem, witness, bundle):
        component = set(component_tuple)
        outside = sorted(int(s) for s in np.flatnonzero(z[:, j] > 0.5) if s not in component)
        if not outside:
            continue
        boundary = sorted(set().union(*(set(graph.neighbors(s)) for s in component)) - component)
        row = len(names)
        columns = [problem.off_z + min(component) * problem.k + j,
                   problem.off_z + outside[0] * problem.k + j]
        values = [1.0, 1.0]
        columns.extend(problem.off_z + s * problem.k + j for s in boundary)
        values.extend([-1.0] * len(boundary))
        rr.extend([row] * len(columns))
        cc.extend(columns)
        vv.extend(values)
        names.append(f"connectivity_cut_{start_index + row:04d}")
    if not names:
        return problem, 0
    block = sparse.coo_matrix((vv, (rr, cc)), shape=(len(names), problem.n_var)).tocsc()
    first = problem.A.shape[0]
    rows = dict(problem.rows)
    for offset, name in enumerate(names):
        rows[name] = (first + offset, first + offset + 1)
    changed = dataclasses.replace(
        problem,
        A=sparse.vstack((problem.A, block), format="csc"),
        lb=np.concatenate((problem.lb, np.full(len(names), -np.inf))),
        ub=np.concatenate((problem.ub, np.ones(len(names)))),
        rows=rows,
    )
    return changed, len(names)


def solve_connectivity_separation(
    target: level0.Level0Problem,
    master: level0.Level0Problem,
    reference: CandidateWitness,
    validate: Callable[[CandidateWitness], ValidationReport],
    *,
    engine: str = "highs",
    threads: int = 2,
    heuristic_effort: float | None = None,
    time_limit: float = 90.0,
    slice_seconds: float = 10.0,
) -> RepairOutcome:
    """Solve a business-and-distance master and separate disconnected integer points."""
    current, constant = hamming_problem(master, reference, None)
    attempts: list[RepairAttempt] = []
    deadline = time.monotonic() + float(time_limit)
    n_cuts = 0
    while time.monotonic() < deadline:
        seconds = min(float(slice_seconds), max(0.0, deadline - time.monotonic()))
        if seconds <= 0.0:
            break
        started = time.monotonic()
        try:
            result = milp_engines.solve_problem(
                current, engine, time_limit=seconds, threads=threads,
                heuristic_effort=heuristic_effort)
        except state_splits.SolveFailure as exc:
            attempts.append(RepairAttempt(None, seconds, exc.reason,
                                          time.monotonic() - started,
                                          issues=(f"cuts={n_cuts}",)))
            if exc.status == 2:
                break
            continue
        witness = CandidateWitness.from_result(result, f"connectivity-separation-{n_cuts}")
        components = disconnected_components(target, witness)
        if not components:
            report = validate(witness)
            objective = hamming_distance(target, witness, reference)
            attempts.append(RepairAttempt(
                None, seconds, str(result.get("status", "returned")),
                time.monotonic() - started, float(objective),
                _result_number(result, "dual_bound"),
                int(result["nodes"]) if _result_number(result, "nodes") is not None else None,
                report.accepted, report.issues + (f"cuts={n_cuts}",)))
            if report.accepted:
                accepted = dict(result)
                accepted["u"] = np.asarray(result["used"], bool)
                accepted["passes"] = [{
                    "name": "connectivity_separation",
                    "value": objective,
                    "certified": False,
                    "status": result.get("status"),
                    "seconds": attempts[-1].seconds,
                    "cuts": n_cuts,
                    "objective_without_constant": _result_number(result, "objective"),
                    "objective_constant": constant,
                }]
                accepted["problem"] = target
                return RepairOutcome(accepted, tuple(attempts))
            break
        current, added = append_connectivity_cuts(current, witness, n_cuts)
        attempts.append(RepairAttempt(
            None, seconds, "disconnected_incumbent", time.monotonic() - started,
            _result_number(result, "objective"), _result_number(result, "dual_bound"),
            int(result["nodes"]) if _result_number(result, "nodes") is not None else None,
            False, (f"components={len(components)}", f"cuts_added={added}")))
        if added == 0:
            break
        n_cuts += added
    return RepairOutcome(None, tuple(attempts))


def proves_unrestricted_infeasible(outcome: RepairOutcome) -> bool:
    """Whether an unrestricted target or valid-cut master was proved infeasible."""
    return any(attempt.radius is None and attempt.status == "infeasible"
               for attempt in outcome.attempts)


def write_reference(path: Path | str, problem: level0.Level0Problem,
                    witness: CandidateWitness, provenance: Mapping[str, Any]) -> Path:
    """Write the full-precision aggregate repair reference before optimization starts."""
    z, y = _shape_witness(problem, witness)
    if not np.isfinite(z).all() or not np.isfinite(y).all():
        raise ValueError("cannot export a non-finite repair reference")
    target = Path(path)
    record = {
        "schema": "group2-geography-reference-v1",
        "model_sha256": group2_checkpoint.model_fingerprint(problem, dict(provenance)),
        "provenance": dict(provenance),
        "source": witness.source,
        "z": z.tolist(),
        "y": y.tolist(),
    }
    encoded = json.dumps(record, indent=2, allow_nan=False) + "\n"
    record["reference_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return target


def export_research_instance(path: Path | str, problem: level0.Level0Problem,
                             policy: GeographyPolicy, provenance: Mapping[str, Any]) -> Path:
    """Write the aggregate target contract needed to reproduce and audit a research run."""
    target = Path(path)
    xy = np.asarray(problem.state_xy, float)
    conflicts = []
    if xy.shape[0] == problem.n_state:
        for a in range(problem.n_state):
            for b in range(a + 1, problem.n_state):
                distance = float(np.linalg.norm(xy[a, :2] - xy[b, :2]))
                limit = max(
                    policy.distance_km,
                    float(policy.distance_overrides_km.get(
                        _parent(problem.state_list[a], policy), policy.distance_km)),
                    float(policy.distance_overrides_km.get(
                        _parent(problem.state_list[b], policy), policy.distance_km)),
                )
                if distance > limit:
                    conflicts.append([problem.state_list[a], problem.state_list[b], distance, limit])
    record = {
        "schema": "group2-geography-research-v1",
        "model_sha256": group2_checkpoint.model_fingerprint(problem, dict(provenance)),
        "provenance": dict(provenance),
        "policy": _policy_record(policy),
        "state_list": list(problem.state_list),
        "edges": [[problem.state_list[a], problem.state_list[b]] for a, b in problem.edges],
        "coordinates_km": xy.tolist(),
        "distance_conflicts": conflicts,
        "W": np.asarray(problem.W, float).tolist(),
        "cover_ub": np.asarray(problem.cover_ub, float).tolist(),
        "required_cover": [[problem.state_list[s], problem.channels[c], target]
                           for s, c, target in _required_cover(problem)],
        "L_j": np.asarray(problem.L_j, float).tolist(),
        "U_j": np.asarray(problem.U_j, float).tolist(),
        "bundle_of": list(problem.bundle_of),
        "slots": {name: list(bounds) for name, bounds in problem.slots.items()},
        "rows": {name: list(bounds) for name, bounds in problem.rows.items()},
        "offsets": {
            "z": problem.off_z, "y": problem.off_y, "r": problem.off_r,
            "f": problem.off_f, "u": problem.off_u,
        },
        "dimensions": {"states": problem.n_state, "slots": problem.k,
                       "variables": problem.n_var, "rows": problem.A.shape[0]},
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return target


def write_certificate(path: Path | str, problem: level0.Level0Problem,
                      witness: CandidateWitness, report: ValidationReport,
                      policy: GeographyPolicy, provenance: Mapping[str, Any],
                      solver: Mapping[str, Any] | None = None) -> Path:
    """Write a full-precision accepted witness and its two validation reports."""
    if not report.accepted:
        raise ValueError("cannot certify a rejected candidate")
    x = group2_checkpoint.reconstruct_vector(problem, {"z": witness.z, "y": witness.y})
    target = Path(path)
    record = {
        "schema": "group2-geography-certificate-v1",
        "model_sha256": group2_checkpoint.model_fingerprint(problem, dict(provenance)),
        "provenance": dict(provenance),
        "policy": _policy_record(policy),
        "source": witness.source,
        "validation": report.as_dict(),
        "solver": dict(solver or {}),
        "z": np.asarray(witness.z, float).tolist(),
        "y": np.asarray(witness.y, float).tolist(),
        "u": x[problem.off_u:problem.off_u + problem.k].tolist(),
        "r": x[problem.off_r:problem.off_r + problem.n_state * problem.k].tolist(),
        "f": x[problem.off_f:problem.off_u].tolist(),
    }
    encoded = json.dumps(record, indent=2, allow_nan=False) + "\n"
    record["certificate_sha256"] = hashlib.sha256(encoded.encode()).hexdigest()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return target
