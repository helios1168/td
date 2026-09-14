#!/usr/bin/env python3
"""Verify a local distance and band obstruction in a Group 2 research instance."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
from typing import Any

import networkx as nx
import numpy as np


def _parent(unit: str, policy: dict[str, Any]) -> str:
    return str(policy.get("unit_parent", {}).get(unit, unit))


def _recomputed_conflicts(instance: dict[str, Any]) -> set[frozenset[str]]:
    states = [str(value) for value in instance["state_list"]]
    xy = np.asarray(instance["coordinates_km"], dtype=float)
    policy = instance["policy"]
    base = float(policy["distance_km"])
    overrides = {str(key): float(value)
                 for key, value in policy.get("distance_overrides_km", {}).items()}
    tolerance = float(policy.get("tolerance", 0.0))
    conflicts: set[frozenset[str]] = set()
    for a, b in itertools.combinations(range(len(states)), 2):
        limit = max(
            base,
            overrides.get(_parent(states[a], policy), base),
            overrides.get(_parent(states[b], policy), base),
        )
        if float(np.linalg.norm(xy[a, :2] - xy[b, :2])) > limit + tolerance:
            conflicts.add(frozenset((states[a], states[b])))
    return conflicts


def verify(path: Path) -> tuple[bool, list[dict[str, Any]], dict[str, Any]]:
    raw = path.read_bytes()
    instance = json.loads(raw)
    states = [str(value) for value in instance["state_list"]]
    state_index = {state: index for index, state in enumerate(states)}
    policy = instance["policy"]
    weights = np.asarray(instance["W"], dtype=float)
    floors = np.asarray(instance["L_j"], dtype=float)
    contact_cap = int(policy["contact_cap"])
    tolerance = float(policy.get("tolerance", 0.0))

    if set(instance["bundle_of"]) != {"N"}:
        raise ValueError("the verifier expects a pure National stage")
    if instance["slots"].get("N") != [0, len(floors)]:
        raise ValueError("the National slot range does not cover the exported stage")
    if weights.shape != (len(states), len(floors)):
        raise ValueError(f"W has shape {weights.shape}, expected {(len(states), len(floors))}")
    if np.any(weights < -tolerance):
        raise ValueError("the nonnegative opportunity upper-bound argument does not apply")
    if not np.allclose(weights, weights[:, [0]], atol=1e-10, rtol=0.0):
        raise ValueError("National opportunity differs by slot")
    if not np.allclose(floors, floors[0], atol=1e-10, rtol=0.0):
        raise ValueError("district floors differ by slot")
    if contact_cap < 1:
        raise ValueError("contact_cap must be positive")

    exported_conflicts = {
        frozenset((str(row[0]), str(row[1])))
        for row in instance["distance_conflicts"]
    }
    recomputed_conflicts = _recomputed_conflicts(instance)
    if exported_conflicts != recomputed_conflicts:
        raise ValueError("exported distance conflicts do not match coordinates and policy")

    required = {
        str(state)
        for state, _channel, target in instance["required_cover"]
        if float(target) > tolerance
    }
    unknown = required.difference(state_index)
    if unknown:
        raise ValueError(f"required_cover names unknown states: {sorted(unknown)}")

    compatibility = nx.Graph()
    compatibility.add_nodes_from(states)
    compatibility.add_edges_from(
        (a, b)
        for a, b in itertools.combinations(states, 2)
        if frozenset((a, b)) not in recomputed_conflicts
    )
    maximal_cliques = list(nx.find_cliques(compatibility))
    opportunity = weights[:, 0]
    floor = float(floors[0])
    failures: list[dict[str, Any]] = []
    for state in sorted(required):
        best_mass = -np.inf
        best_support: tuple[str, ...] = ()
        for clique in maximal_cliques:
            if state not in clique:
                continue
            others = sorted(
                (candidate for candidate in clique if candidate != state),
                key=lambda candidate: (-opportunity[state_index[candidate]], candidate),
            )[:contact_cap - 1]
            support = (state, *others)
            mass = float(sum(opportunity[state_index[candidate]] for candidate in support))
            if mass > best_mass:
                best_mass = mass
                best_support = support
        if best_mass < floor - tolerance:
            failures.append({
                "state": state,
                "maximum_compatible_opportunity": best_mass,
                "district_floor": floor,
                "shortfall": floor - best_mass,
                "maximizing_support": list(best_support),
            })

    metadata = {
        "instance_sha256": hashlib.sha256(raw).hexdigest(),
        "model_sha256": instance.get("model_sha256"),
        "required_units": len(required),
        "contact_cap": contact_cap,
        "district_floor": floor,
        "maximal_compatibility_cliques": len(maximal_cliques),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "networkx": nx.__version__,
    }
    return bool(failures), failures, metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("instance", type=Path)
    args = parser.parse_args()
    proved, failures, metadata = verify(args.instance)
    print("CLAIM: the exported frozen full-coverage National target is infeasible")
    print("MODE: numeric exhaustive support enumeration")
    print("ATTACK: drop connectivity, split caps, exact district count, and all nonlocal coupling")
    print(f"INSTANCE: {json.dumps(metadata, sort_keys=True)}")
    for failure in failures:
        print("OBSTRUCTION:", json.dumps(failure, sort_keys=True))
    print("VERDICT:", "VERIFIED" if proved else "INCONCLUSIVE")
    if proved:
        print("BASIS: a required unit cannot occur in any distance-valid support of at most "
              "contact_cap units with enough total available opportunity to reach the floor")
    else:
        print("BASIS: no local obstruction was found; this does not establish feasibility")
    return 0 if proved else 1


if __name__ == "__main__":
    raise SystemExit(main())
