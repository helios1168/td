"""Validated, atomic warm-start checkpoints for the Group 2 planner.

Checkpoints are deliberately feasibility artifacts, not solve results: restoring one only
supplies a warm start to a new solve.  It cannot certify a pass or cause optimization to be
skipped.  The JSON records a complete level-0 vector so it can be checked against the current
model before use.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
from typing import Any

import numpy as np

from td.solvers import level0


SCHEMA = 1
_PART = re.compile(r"^[A-Za-z0-9_.-]+$")


def _canonical(value: Any) -> bytes:
    """Stable JSON bytes, refusing non-finite values rather than hiding them."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _digest_array(hasher: "hashlib._Hash", value: Any) -> None:
    array = np.asarray(value)
    hasher.update(str(array.shape).encode("ascii"))
    hasher.update(array.dtype.str.encode("ascii"))
    hasher.update(np.ascontiguousarray(array).tobytes())


def model_fingerprint(problem: level0.Level0Problem, provenance: dict[str, Any]) -> str:
    """Hash all feasibility-defining model data plus reviewed input provenance.

    The objective is intentionally absent: a checkpoint stays a valid warm start when the
    next lexicographic pass changes the objective, but any constraint/bound/geography change
    invalidates it.
    """
    h = hashlib.sha256(b"group2-checkpoint-model-v1\0")
    matrix = problem.A.tocsc()
    for value in (matrix.shape, matrix.indptr, matrix.indices, matrix.data, problem.lb,
                  problem.ub, problem.integrality, problem.var_lb, problem.var_ub,
                  problem.W, problem.cover_ub, problem.L_j, problem.U_j, problem.slot_has,
                  problem.state_xy, problem.slot_root):
        _digest_array(h, value)
    h.update(_canonical(dict(
        n_state=problem.n_state, k=problem.k, n_var=problem.n_var,
        offsets=[problem.off_z, problem.off_y, problem.off_r, problem.off_f, problem.off_u],
        edges=[list(edge) for edge in problem.edges], state_list=list(problem.state_list),
        bundle_of=list(problem.bundle_of), slots=problem.slots, rows=problem.rows,
        eta=problem.eta, radius_max=problem.radius_max, provenance=provenance,
    )))
    return h.hexdigest()


def _part(value: str) -> str:
    if not _PART.fullmatch(value):
        raise ValueError("checkpoint stage and pass names may contain only letters, digits, . _ -")
    return value


def reconstruct_vector(problem: level0.Level0Problem, result: dict[str, Any]) -> np.ndarray:
    """Return a fully feasible vector from a solver result's ``z``/``y`` blocks.

    Engine results intentionally omit SCF roots and flows.  For every connected selected
    district this builds a rooted spanning tree: each arc carries its child's subtree size.
    The construction is exact for this model's SCF formulation and is then checked by the
    public full-model validator below.
    """
    if "x" in result:
        x = np.asarray(result["x"], dtype=float).copy()
        level0.check_point(problem, x)
        return x
    if "z" not in result or "y" not in result:
        raise ValueError("checkpoint result needs full x or z and y")
    S, K = problem.n_state, problem.k
    z = np.asarray(result["z"], dtype=float).reshape(S, K) > 0.5
    y = np.asarray(result["y"], dtype=float).reshape(S, K)
    if not np.isfinite(y).all():
        raise ValueError("checkpoint y contains a non-finite value")
    x = np.zeros(problem.n_var, dtype=float)
    x[problem.off_z:problem.off_z + S * K] = z.ravel()
    x[problem.off_y:problem.off_y + S * K] = y.ravel()
    x[problem.off_u:problem.off_u + K] = z.any(axis=0)

    adjacent: list[list[tuple[int, int]]] = [[] for _ in range(S)]
    for edge, (a, b) in enumerate(problem.edges):
        adjacent[a].append((b, 2 * edge))
        adjacent[b].append((a, 2 * edge + 1))
    for j in range(K):
        chosen = np.flatnonzero(z[:, j])
        if not chosen.size:
            continue
        chosen_set = set(int(s) for s in chosen)
        forced = [s for s in chosen if problem.var_lb[problem.off_r + s * K + j] > 0.5]
        candidates = forced or [s for s in chosen
                                if problem.var_ub[problem.off_r + s * K + j] > 0.5]
        if len(forced) > 1 or not candidates:
            raise ValueError(f"slot {j} has no unique permitted flow root")
        root = int(candidates[0])
        parent: dict[int, tuple[int, int]] = {root: (-1, -1)}
        stack = [root]
        while stack:
            here = stack.pop()
            for nxt, arc in adjacent[here]:
                if nxt in chosen_set and nxt not in parent:
                    parent[nxt] = (here, arc)
                    stack.append(nxt)
        if len(parent) != len(chosen_set):
            raise ValueError(f"slot {j} contacts are disconnected")
        x[problem.off_r + root * K + j] = 1.0
        children: dict[int, list[int]] = {s: [] for s in parent}
        for child, (par, _) in parent.items():
            if par >= 0:
                children[par].append(child)
        def subtree(node: int) -> int:
            total = 1
            for child in children[node]:
                total += subtree(child)
            if node != root:
                _, arc = parent[node]
                x[problem.off_f + arc * K + j] = total
            return total
        subtree(root)
    level0.check_point(problem, x)
    return x


def _safe_metadata(result: dict[str, Any]) -> dict[str, Any]:
    """Keep only small, non-certifying solve facts in a checkpoint."""
    allowed = ("name", "status", "seconds", "engine", "objective", "mip_gap", "nodes")
    meta: dict[str, Any] = {}
    for key in allowed:
        value = result.get(key)
        if isinstance(value, np.generic):
            value = value.item()
        if isinstance(value, (str, bool, int)):
            meta[key] = value
        elif isinstance(value, float) and math.isfinite(value):
            meta[key] = value
    return meta


class CheckpointStore:
    """A directory of independently recoverable Group 2 warm starts."""
    def __init__(self, root: Path | str, provenance: dict[str, Any]) -> None:
        self.root = Path(root)
        self.provenance = json.loads(_canonical(provenance))

    def path(self, stage: str, pass_name: str) -> Path:
        return self.root / f"{_part(stage)}--{_part(pass_name)}.json"

    def save(self, stage: str, pass_name: str, result: dict[str, Any],
             problem: level0.Level0Problem) -> Path:
        """Atomically save a validated warm vector; never write an invalid checkpoint."""
        target = self.path(stage, pass_name)
        x = reconstruct_vector(problem, result)
        record = dict(schema=SCHEMA, stage=stage, pass_name=pass_name,
                      saved_at=time.time(), fingerprint=model_fingerprint(problem, self.provenance),
                      provenance=self.provenance, warm_start=x.tolist(), metadata=_safe_metadata(result))
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        try:
            with temporary.open("wb") as fh:
                fh.write(_canonical(record) + b"\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(temporary, target)
            try:
                directory = os.open(self.root, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            except OSError:
                pass
        finally:
            if temporary.exists():
                temporary.unlink()
        return target

    def load(self, stage: str, pass_name: str, problem: level0.Level0Problem) -> dict[str, Any] | None:
        """Return a validated vector, or ``None`` for absent, stale, corrupt, or bad files."""
        try:
            record = json.loads(self.path(stage, pass_name).read_text(encoding="utf-8"))
            if (record.get("schema") != SCHEMA or record.get("stage") != stage
                    or record.get("pass_name") != pass_name
                    or record.get("provenance") != self.provenance
                    or record.get("fingerprint") != model_fingerprint(problem, self.provenance)):
                return None
            x = np.asarray(record["warm_start"], dtype=float)
            if not np.isfinite(x).all():
                return None
            level0.check_point(problem, x)
            return dict(x=x, stage=stage, pass_name=pass_name,
                        metadata=dict(record.get("metadata") or {}))
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def latest(self, stage: str, problem: level0.Level0Problem) -> dict[str, Any] | None:
        """Newest valid checkpoint for one stage, independent of pass ordering."""
        _part(stage)
        candidates: list[tuple[float, dict[str, Any]]] = []
        for path in self.root.glob(f"{stage}--*.json") if self.root.exists() else ():
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                pass_name = record["pass_name"]
                loaded = self.load(stage, pass_name, problem)
                if loaded is not None:
                    candidates.append((float(record.get("saved_at", 0.0)), loaded))
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
                continue
        return max(candidates, key=lambda item: item[0])[1] if candidates else None

