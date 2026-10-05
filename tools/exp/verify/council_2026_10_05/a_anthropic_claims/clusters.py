"""Opus T5; Fable T5/T9; pass-2 F7, forced-set and enumeration refinements."""
from dataclasses import replace
from itertools import product
from math import comb, inf
import networkx as nx
from toy import Toy, enumerate_plans, path_toy, solve, subsets


def partitions(items):
    if not items:
        yield ()
        return
    first, *rest = items
    for p in partitions(rest):
        yield ((first,),) + p
        for i, block in enumerate(p):
            yield p[:i] + (tuple(sorted((first,) + block)),) + p[i + 1:]


def floors(toy):
    allowed = {}
    for p in subsets(toy.V):
        if nx.is_connected(toy.graph.subgraph(p)):
            mass = sum(toy.M[v] for v in p)
            allowed[p] = tuple(k for k in range(1, toy.K + 1)
                               if k * toy.L - 1e-7 <= mass <= k * toy.U + 1e-7)
    cluster_floor, Q, tested = inf, 0, 0
    for partition in partitions(list(toy.V)):
        tested += 1
        if not all(allowed.get(p) for p in partition):
            continue
        Q = max(Q, len(partition))
        for ks in product(*(allowed[p] for p in partition)):
            if sum(ks) != toy.K:
                continue
            cost = sum(max(int(k >= 2), sum(toy.M[v] > toy.U for v in p))
                       for p, k in zip(partition, ks))
            cluster_floor = min(cluster_floor, cost)
    return cluster_floor, Q, tested


def main():
    for toy in (path_toy(6, 3), path_toy(6, 2), path_toy(8, 3)):
        plans, tested = enumerate_plans(toy)
        a, Q, partitions_tested = floors(toy)
        optimum = min(p[0][0] for p in plans)
        cap = max(toy.contact_cap(v) for v in toy.V)
        weak = (toy.K - Q) / (cap - 1) if cap > 1 else 0
        assert a <= optimum and weak <= optimum
        for key, n, t in plans:
            cuts = sum(toy.counts(n).values()) - len(toy.V)
            assert cuts >= toy.K - Q
            assert key[0] >= weak
        print(f"clusters {toy.name}: partitions={partitions_tested} plans={tested} "
              f"cluster_floor={a} Q={Q} weak={weak:g} s*={optimum}")

    # Every unit mass >=2.55 tau; disconnected singletons give tight forced floor.
    tight = Toy("tight_2.55", tuple(v for v in range(6) for _ in range(3)), (1.,) * 18,
                tuple((3*v+i, 3*v+i+1) for v in range(6) for i in range(2)), 18,
                eta=.2, size_cap=1)
    plans, tested = enumerate_plans(tight)
    a, Q, count = floors(tight)
    assert solve(tight)[0][0] == 6 == a == (tight.K - Q) / 2
    assert len(plans) == 1
    print(f"tight_2.55: units=6 ZIPs=18 plans={tested} feasible=1 Q={Q} "
          "Umax=3 weak=6 forced=6 s*=6")

    # Six whole units in two disconnected three-unit paths, masses 2.4 and 1.6.
    regions = Toy("per_part_tau", tuple(range(6)), (.6, .6, 1.2, .4, .4, .8),
                  ((0, 1), (1, 2), (3, 4), (4, 5)), 4, modes=("whole",) * 6)
    plans, tested = enumerate_plans(regions)
    assert not plans and solve(regions) is None
    first = Toy("part_2.4", (0, 1, 2), (.6, .6, 1.2), ((0, 1), (1, 2)), 2,
                delta=0, modes=("whole",) * 3)
    second = replace(first, name="part_1.6", masses=(.4, .4, .8))
    assert solve(first) is not None and solve(second) is not None
    assert all(not all(k*.85 <= m <= k*1.15 for k, m in zip(ks, (2.4, 1.6)))
               for ks in ((1, 3), (2, 2), (3, 1)))
    print(f"per_part_tau: joint plans={tested} feasible=0; local tau=1.2/.8 feasible at delta=0")

    # Stronger reading: all positive local K allocations have feasible own-tau solves.
    free_regions = Toy("all_local_allocations", tuple(v for v in range(6) for _ in range(2)),
                       (.4,) * 6 + (4/15,) * 6,
                       tuple((z, z+1) for z in range(11) if z != 5), 4)
    assert not enumerate_plans(free_regions)[0] and solve(free_regions) is None
    for k in (1, 2, 3):
        local = Toy(f"local_K{k}", (0, 0, 1, 1, 2, 2), (.4,) * 6,
                    tuple((z, z+1) for z in range(5)), k, delta=0)
        assert solve(local) is not None
        assert solve(replace(local, masses=(4/15,) * 6)) is not None
    print("all_local_allocations: 6 units/12 ZIPs, both components feasible at own tau for K=1,2,3; "
          "joint K=4 +/-15% infeasible for (1,3),(2,2),(3,1)")

    carve = Toy("fixed_carving", tuple(range(6)), (1.,) * 6,
                tuple((v, v+1) for v in range(5)), 3, modes=("whole",) * 6, size_cap=2)
    plans, tested = enumerate_plans(carve)
    assert solve(carve)[0][0] == 0
    bad_regions = ({0, 1, 2}, {3, 4, 5})
    good_regions = ({0, 1}, {2, 3}, {4, 5})
    respects = lambda n, rs: all(any(set(s) <= r for r in rs) for s in n)
    assert not any(respects(n, bad_regions) for _, n, _ in plans)
    assert any(respects(n, good_regions) for _, n, _ in plans)
    assert any(not any(set(s) <= r for r in good_regions) for s in carve.family)
    print("fixed_carving: parent s*=0; 3+3 carving infeasible at parent tau=2; "
          "2+2+2 carving exact despite unused crossing supports (Opus iff too strong)")

    # T9's polygon-map split bound still requires its asserted contact cap.
    eta_map = Toy("weak_eta_failure", (0, 0, 0), (1., 1., 1.), ((0, 1), (1, 2)),
                  3, eta=.5)
    a, Q, count = floors(eta_map)
    assert Q == 1 and eta_map.contact_cap(0) == 2
    assert (eta_map.K - Q) / (eta_map.contact_cap(0) - 1) == 2
    assert solve(eta_map) is None
    print("weak_eta_failure: 1 unit/3 ZIPs, K=3 eta=.5; polygon split=1, "
          "claimed split floor=2; cuts=2 remains valid")

    # Counting formula, with no implication of solver independence.
    pool, forced, target = 6, 2, 4
    sets = [set(f) for f in subsets(range(pool)) if len(f) == target - 1 and {0, 1} <= set(f)]
    assert len(sets) == comb(pool - forced, target - 1 - forced) == 4
    print("cutoff_layer: m=6 f=2 s*=4 candidates=C(4,1)=4; same-HiGHS cross-check not solver independent")


if __name__ == "__main__":
    main()
