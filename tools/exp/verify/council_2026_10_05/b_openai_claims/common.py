"""Shared fixtures for the b_openai_claims checks: the fixed random suites and small helpers."""
from model import random_inst

# Suite A: 6-8 units, 1-3 ZIPs each, 2-4 free/clipped units, K 2-4. Seeds 0..399, kept when the
# master has a feasible plan. Suite B: more splittable units and districts, for split variety.
SUITE_A = dict(n_free=(2, 4), deltas=(0.15, 0.25, 0.35), K=(2, 4), zips_per=(1, 3))
SUITE_B = dict(n_free=(3, 5), deltas=(0.15, 0.25), K=(3, 5), zips_per=(1, 3), clipped=False)


# The seeds of 0..399 (A) and 0..149 (B) whose master has a feasible plan, found by
# `suite(SUITE_A, range(400))` and `suite(SUITE_B, range(150))`; listed so each check skips the scan.
SEEDS_A = [3, 4, 9, 15, 18, 21, 23, 29, 30, 45, 46, 54, 55, 57, 59, 66, 67, 68, 78, 79, 86, 92, 96,
           98, 102, 114, 139, 144, 163, 164, 166, 170, 175, 176, 183, 192, 208, 209, 214, 216, 224,
           227, 238, 239, 243, 245, 248, 259, 269, 274, 275, 283, 285, 292, 293, 296, 298, 300, 302,
           313, 319, 327, 329, 330, 334, 339, 360, 363, 366, 373, 378, 387, 392, 394]
SEEDS_B = [1, 4, 11, 25, 26, 30, 37, 39, 41, 45, 47, 52, 57, 60, 66, 73, 78, 86, 87, 92, 96, 97, 98,
           100, 102, 107, 110, 111, 113, 114, 127, 131, 135, 145, 146, 147]


def suites():
    """Suite A + suite B: 110 instances with 6-8 units, each with at least one feasible plan."""
    out = suite(SUITE_A, SEEDS_A) + suite(SUITE_B, SEEDS_B)
    assert len(out) == 110
    return out


def suite(cfg, seeds, need_plan=True):
    out = []
    for seed in seeds:
        I = random_inst(seed, **cfg)
        ps = I.plans()
        if ps or not need_plan:
            out.append((I, ps))
    return out


def fmt(I, nvec):
    return {"+".join(sorted(I.F[s])): c for s, c in sorted(nvec.items())}


def report(tag, ok, detail=""):
    ok = bool(ok)
    print(f"[{'ok' if ok else 'MISMATCH'}] {tag}" + (f": {detail}" if detail else ""))
    return bool(ok)
