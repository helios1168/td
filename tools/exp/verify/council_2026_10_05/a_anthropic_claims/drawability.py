"""Opus T6/T7; Fable T7/T8; Hall, same-summary lift failures, graph inclusion."""
from dataclasses import replace
from toy import Toy, check_instance, drawings, enumerate_plans, pad, share_lp, solve


def star_path(path=False):
    # v's five unit-mass ZIPs; whole u,w attach to distinct leaves/endpoints.
    interior = tuple((z, z+1) for z in range(5)) if path else ((0, 1), (1, 2), (1, 3), (1, 4), (1, 5))
    if path:
        edges = interior + ((5, 6),)
    else:
        edges = interior + ((6, 2),)
    return Toy("mass_path" if path else "mass_star", (0, 1, 1, 1, 1, 1, 2),
               (3., 1., 1., 1., 1., 1., 3.), edges, 2, modes=("whole", "free", "whole"),
               size_cap=2, hall=True)


def signature(toy, multiset=True):
    return (toy.M, {v: len(zs) for v, zs in toy.Z.items()},
            {v: tuple(sorted(toy.masses[z] for z in zs)) for v, zs in toy.Z.items()} if multiset else None,
            {key: len(zs) for key, zs in toy.border.items()}, toy.corridor, toy.kappa,
            tuple(toy.nrows))


def main():
    border_star = Toy("border_star", (0, 1, 1, 1, 2), (.5, 1/3, 1/3, 1/3, .5),
                      ((0, 1), (1, 2), (1, 3), (1, 4)), 2, delta=.1,
                      modes=("whole", "free", "whole"))
    plans, tested = enumerate_plans(border_star)
    assert solve(border_star)[0][0] == 1
    n = {(0, 1): 1, (1, 2): 1}
    assert share_lp(border_star, n) is not None
    stronger = replace(border_star, hall=True)
    assert share_lp(stronger, n) is None and solve(stronger) is None
    ds, colours = drawings(border_star)
    assert not ds
    assert border_star.corridor[(0, 1, 2), 1] == 1/3
    print(f"border_star: units=3 ZIPs=5 plans={tested} feasible={len(plans)} s*=1 "
          f"drawings=0/{colours}; Hall 2<=1 fails; triple corridor mass=4/3>1.1")
    check_instance(pad(border_star))
    wide = replace(border_star, delta=.75, hall=True)
    valid, colour_count = drawings(wide)
    assert valid and all(share_lp(wide, d[2]) is not None for d in valid)
    print(f"Hall_validity: border-star wide band, connected drawings={len(valid)}/{colour_count}; all read-backs pass")

    star, path = star_path(), star_path(True)
    assert signature(star) == signature(path)
    assert solve(star)[0][0] == solve(path)[0][0] == 1
    sd, sc = drawings(star)
    pd, pc = drawings(path)
    assert not sd and pd
    assert any(abs(d[3] - 1/11) < 1e-7 for d in pd)
    print(f"same_summaries: units=3 ZIPs=7 star drawings=0/{sc} path drawings={len(pd)}/{pc}; "
          "M,ZIP counts,mass multisets,b,c,kappa,Hall equal; s*=1 both; path masses=5,6")
    check_instance(pad(star))
    check_instance(pad(path))

    # Hall still misses indivisible mass along a path; this contrast has DIFFERENT mass multisets.
    lumpy = Toy("lumpy_path", (0, 1, 1, 1, 2), (.5, .1, .8, .1, .5),
                ((0, 1), (1, 2), (2, 3), (3, 4)), 2, delta=.2, hall=True,
                size_cap=2, modes=("whole", "free", "whole"))
    uniform = replace(lumpy, masses=(.5, 1/3, 1/3, 1/3, .5))
    assert solve(lumpy)[0][0] == 1
    assert not drawings(lumpy)[0] and drawings(uniform)[0]
    assert signature(lumpy, multiset=False) == signature(uniform, multiset=False)
    assert signature(lumpy) != signature(uniform)
    print("lumpy_path: Hall-feasible s*=1; no drawing at +/-20%; uniform path lifts; "
          "full T8 mass-multiset summary differs (not T8 counterexample)")

    graph = Toy("graph_inclusion", tuple(range(6)), (1.,) * 6,
                tuple((v, v+1) for v in range(5)), 3, size_cap=2, modes=("whole",) * 6)
    assert solve(graph)[0][0] == 0 and drawings(graph)[0]
    deleted = replace(graph, edges=tuple(e for e in graph.edges if e != (2, 3)))
    assert solve(deleted) is None and not drawings(deleted)[0]
    print("graph_inclusion: path6 s*=0; delete middle edge -> two odd components, infeasible; "
          "original M1 drawing lacks read-back on smaller master graph")

    equal_targets = Toy("unequal_targets", (0, 0), (.9, 1.1), ((0, 1),), 2)
    assert drawings(equal_targets)[0]
    assert all(abs(sum(equal_targets.masses[z] for z in range(2) if d[1][z] == 0) - 1) > .01
               for d in drawings(equal_targets)[0])
    print("no_good_scope: .9/1.1 ZIPs, K=2 +/-15%; targets 1/1 impossible, unequal drawing valid")

    disconnected_part = Toy("per_unit_pieces", (0, 0, 0, 0, 0, 1), (1.,) * 6,
                            ((0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (4, 5)),
                            2, delta=0, modes=("free", "whole"))
    ds, colours = drawings(disconnected_part)
    witness = (0, 1, 1, 1, 0, 0)
    assert any(d[1] == witness for d in ds)
    assert share_lp(disconnected_part, {(0, 1): 1, (0,): 1}) is not None
    print("per_unit_pieces: connected mass3/3 drawing {z1,z5,C}|{z2,z3,z4}; "
          "first district's v-intersection disconnected; per-unit connectivity is invalid necessity")


if __name__ == "__main__":
    main()
