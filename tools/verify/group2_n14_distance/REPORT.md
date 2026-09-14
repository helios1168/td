# Group 2 N14 distance-floor verification

CLAIM: The exported `seq_N` model for the fixed 14 National district, full-coverage target is
infeasible.

MODE: Numeric exhaustive enumeration.

ATTACK: The verifier removes connectivity, split caps, the exact district count, Hamming repair,
and every cross-district constraint. It retains only full coverage of one required unit, the
six-unit contact cap, pair-distance compatibility, `y <= 1`, and the district opportunity floor.
This relaxation should make a false infeasibility claim easier to break.

VERDICT: VERIFIED

BASIS: Every distance-valid district support is a clique in the compatibility graph and every
clique is contained in a maximal clique. With nonnegative opportunity, the largest support of at
most six units containing a chosen required unit consists of that unit and the five largest
compatible members of some maximal clique. Exhaustive enumeration finds seven required units
whose best possible support is below 553.724691:

| Unit | Maximum opportunity | Shortfall |
|---|---:|---:|
| CO | 548.754666 | 4.970024 |
| ID | 341.321233 | 212.403458 |
| MT | 263.275277 | 290.449413 |
| ND | 238.881152 | 314.843539 |
| NE | 282.167471 | 271.557220 |
| SD | 238.881152 | 314.843539 |
| WY | 341.321233 | 212.403458 |

ARTIFACT:

~~~bash
/Users/Shared/sv-ntlee/repos/td/.venv/bin/python3 \
  tools/verify/group2_n14_distance/check_distance_floor.py \
  battery/results/group2_national_states_n14w11f21_20260914_repair1/research/seq_N_instance.json
~~~

CAVEATS: This verdict covers the frozen full nationwide National coverage target exported by the
run. It does not cover the broader staged planner with partial National coverage or a target that
requires full coverage only in the 19 Group 2 states. The verifier checks the exported conflict
list against the coordinates and distance policy before using it.

LEARNED: 2026-09-14, the 900 km diameter rule and lower band already contradict full nationwide
coverage locally; flow tuning and longer repair solves cannot resolve this target.
