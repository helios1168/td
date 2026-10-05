"""Opus T1-T4; Fable T1-T4: F2, lex objectives, F6, pair-row counterexample."""
from dataclasses import replace
from toy import Toy, check_instance, enumerate_plans, pad, path_toy, share_lp, solve, subsets


def main():
    cycle = Toy("cycle6", tuple(v for v in range(6) for _ in range(2)), (.5,) * 12,
                tuple((z, (z + 1) % 12) for z in range(12)), 3)
    cases = [path_toy(6, 3), path_toy(6, 2), path_toy(8, 3), cycle]
    for toy in cases:
        plans, optimum, ds = check_instance(toy, draw=len(toy.units) <= 12)
        # Exhaustive free-set search; support family unchanged by mode.
        feasible = set()
        for f in ((), *subsets(toy.V)):
            restricted = replace(toy, modes=tuple("free" if v in f else "whole" for v in toy.V))
            result = solve(restricted)
            if result is not None:
                feasible.add(frozenset(f))
                assert result[0][0] <= len(f)
        assert min(map(len, feasible)) == optimum[0]
        assert all(f | {v} in feasible for f in feasible for v in toy.V)
        forced = {v for v in toy.V if toy.M[v] > toy.U}
        assert all(forced <= f for f in feasible)
        cutoff_layer = [f for f in feasible if len(f) == optimum[0] - 1 and forced <= f]
        assert not cutoff_layer
        print(f"F6 {toy.name}: subsets={2 ** len(toy.V)} feasible={len(feasible)} "
              f"minimum={optimum[0]} up_closed=True forced={sorted(forced)}")

    # T2's unit v needs >=3 ZIPs to obey the count cap; explicit masses/edges.
    pair = Toy("pair_row", (0, 1, 1, 1), (.5, 1., 1., .5), ((0, 1), (1, 2), (2, 3)),
               3, delta=0, eta=.05, size_cap=2)
    n = {(1,): 2, (0, 1): 1}
    t = share_lp(pair, n)
    assert t is not None and abs(t[1, (1,)] - .8) < 1e-7
    assert solve(pair, fixed_n=n)[0][0] == 1
    assert n[(1,)] + n[(0, 1)] - 1 == 2
    print("pair_row: feasible n_v=2,n_uv=1,t_v_v=.8,t_v_uv=.2; binary s_v>=2 invalid")

    whole = Toy("mu_mode", (0, 0), (.5, .5), ((0, 1),), 1,
                delta=.1, modes=("whole",), margin=True)
    assert solve(whole) is not None
    assert solve(replace(whole, modes=("free",))) is None
    print("mu_mode: whole feasible; free mu=.5 band=[1.4,.6] infeasible; up_closure fails")
    padded_whole = pad(whole)
    padded_free = replace(padded_whole, modes=("free",) + ("whole",) * 5)
    whole_plans, whole_count = enumerate_plans(padded_whole)
    free_plans, free_count = enumerate_plans(padded_free)
    assert whole_plans and not free_plans
    assert solve(padded_whole) is not None and solve(padded_free) is None
    print(f"mu_mode_six: units=6 ZIPs=7 integer_plans={whole_count}/{free_count} "
          "whole feasible=1 free feasible=0")

    # Positive gap permits nonoptimal secondary objectives: exact arithmetic, no solver claim.
    # Gap=(second-best-best)/second-best can be <1e-4 at arbitrarily large diameter scale.
    best, worse = 100000, 100001
    assert (worse - best) / worse < 1e-4
    print("gap_arithmetic: diameter 100001 vs 100000 relative gap=0.0000099999 < 1e-4")


if __name__ == "__main__":
    main()
