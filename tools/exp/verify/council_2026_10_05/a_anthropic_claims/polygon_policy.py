"""Owner's polygon split key: unconditional split/balance bounds and zero contacts."""
from dataclasses import replace
from toy import Toy, check_instance, drawings, enumerate_plans, pad, share_lp, solve


def main():
    # Smallest FINITE strict split gap: two units, four ZIPs, all opportunity positive.
    gap = Toy("polygon_gap", (0, 0, 1, 1), (.45, .45, .1, 1.),
              ((0, 1), (1, 3), (3, 2), (2, 0)), 2, delta=0, eta=.1, size_cap=2)
    plans, tested = enumerate_plans(gap)
    ds, colours = drawings(gap, policy=False)
    assert min(d[0][0] for d in ds) == 1 and solve(gap)[0][0] == 2
    assert not drawings(gap)[0]
    relaxed = replace(gap, eta=0)
    assert solve(relaxed)[0][0] == 1
    assert all(share_lp(relaxed, d[2]) is not None for d in ds)
    print(f"polygon_gap: units=2 ZIPs=4 plans={tested} feasible={len(plans)} "
          f"drawings={len(ds)}/{colours}; unrestricted polygon minimum=1 master s*=2; eta=0 s*=1")
    check_instance(pad(gap))

    # Smallest finite balance gap: A=.9; B=.1+1. K=2, tau=1.
    balance = Toy("balance_gap", (0, 1, 1), (.9, .1, 1.), ((0, 1), (1, 2)),
                  2, delta=0, eta=.1, size_cap=2)
    ds, colours = drawings(balance, policy=False)
    assert ds and min(d[3] for d in ds) == 0
    assert solve(balance) is None
    assert solve(replace(balance, delta=.00999)) is None
    assert solve(replace(balance, delta=.01)) is not None
    assert solve(replace(balance, eta=0)) is not None
    print(f"balance_gap: units=2 ZIPs=3 drawings={len(ds)}/{colours}; drawn delta*=0 "
          "master delta*=.01 (eta*.M_B+M_A=1.01); eta=0 delta*=0")

    padded_balance = pad(balance)
    assert not enumerate_plans(padded_balance)[0] and solve(padded_balance) is None
    assert len(drawings(padded_balance, policy=False)[0]) == 1
    check_instance(pad(replace(balance, delta=.01)))

    # Opus C1 as printed: actually feasible at delta=0 without Hall strengthening.
    original = Toy("opus_C1", (0, 1, 1, 2), (.5, 0., 1., .5),
                   ((0, 1), (1, 2), (1, 3)), 2, delta=0, eta=.05,
                   modes=("whole", "free", "whole"))
    n = {(0, 1): 1, (1, 2): 1}
    assert share_lp(original, n) is not None and solve(original)[0][0] == 1
    assert solve(replace(original, hall=True)) is None
    assert solve(replace(original, hall=True, delta=.04999)) is None
    assert solve(replace(original, hall=True, delta=.05)) is not None
    assert drawings(original, policy=False)[0]
    print("opus_C1: C7-only master feasible at delta=0 with {a,v}/{v,b}, v shares=.5/.5; "
          "claimed infeasibility refuted; Hall variant delta*=.05, drawn delta*=0")

    # Zero transit alone can still force extra split even under polygon ownership.
    zero = Toy("zero_contact_gap", (0, 0, 1, 1, 2), (.45, .45, 0., 1., .1),
               ((0, 1), (0, 2), (1, 2), (2, 3), (2, 4)), 2, delta=0, eta=.2,
               size_cap=3)
    ds, colours = drawings(zero, policy=False)
    assert min(d[0][0] for d in ds) == 1
    assert solve(zero)[0][0] == 2
    witness_n = {(0, 1, 2): 1, (0, 1): 1}
    assert share_lp(zero, witness_n) is not None
    relaxed = replace(zero, eta=0)
    assert solve(relaxed)[0][0] == 1
    assert all(share_lp(relaxed, d[2]) is not None for d in ds)
    print(f"zero_contact_gap: units=3 ZIPs=5 drawings={len(ds)}/{colours}; "
          "{A,z0,B}|{z1} polygon split=1, master s*=2; feasible shares A=.7/.2,v=.2/.8,B=.1/0")
    check_instance(pad(zero))

    # Six-unit matching-policy floor remains valid with zero-mass ZIPs.
    zero_matching = Toy("zero_matching", (0, 1, 1, 1, 2), (.5, 0., .5, .5, .5),
                        ((0, 1), (1, 2), (2, 3), (3, 4)), 2,
                        modes=("whole", "free", "whole"), hall=True)
    compatible = replace(pad(zero_matching), name="zero_matching_six")
    check_instance(compatible)


if __name__ == "__main__":
    main()
