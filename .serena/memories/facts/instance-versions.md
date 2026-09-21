# Instance versions and the CONUS ground set

All instances are descaled exports (see `mem:workflow/confidential-data`). They are gitignored
and live in the hub root.

| | v1 `instance_descaled.json.gz` (regression only) | v2 `instance_descaled_v2.json.gz` |
|---|---|---|
| zips | 1,229 | 3,748 (strict superset; raw had 3,749, `BLANK` dropped) |
| reps | 111 | 114 (all 111 retained) |
| contested / uncontested / vacant / untapped | 675 / 477 / 2 / 75 | 718 / 1,447 / 16 / 1,567 |
| untapped share of opportunity | 2.9% | 15.7% |
| aggregate saturation | 41.6% | 29.6% |
| total | 2,745.6 (v1 units) | 5,165.6 v1 units, x1.8814 (8,523.2 in v2 units) |
| k at $1B | 13 (overstated; consistent about 10) | 18 |

v1's "$13B" was about $9.6B. v2's growth is untapped market: x1.6333 over worked zips, while
contested zips only went from 675 to 718.

**CONUS ground set, decided 2026-09-07** (`docs/PROBLEM.md` §6): the 32 blank-state, 2 AK and
1 HI zips (0.49% of M) are handled separately and enter no modeling, optimization or
districting work. Live single-channel instance: `instance_descaled_v2_conus.json.gz`, 3,713
zips, 113 reps, M 8,481.81, tau = 471.21 at k = 18. Whole-instance figures (3,748 zips,
tau = 473.51) predate the decision; never mix the two bases.

**Multi-channel files.** The full-problem track works on `instance_descaled_v3_conus.json.gz`,
derived from the user's three-channel v3 export by the v2 CONUS rule; since 2026-09-10 v3 is
the source of truth and v2 is retired for that track. Reported totals: national $17.6B, all
three channels $48B. The v4 file (`instance_descaled_v4.json.gz`, hub root) is pending from the
user and carries the national sub-channels; see `mem:decisions/full-problem-2026-09-11`.

Firms are masked `F0` / `F1`: A = `F0`, 53 reps, 41.1% of book; B = `F1`, 61 reps, 58.9%. Both
hold book in 671 zips carrying 48.8% of mapped opportunity; 3,704 of 3,748 v2 zips are mappable
(41 lack a gazetteer point, 3 sit outside the lower 48).

Source: `main:STATE.md` `## Facts` (a3924e8, 2026-09-10); host memory
td-full-problem-overnight-2026-09-10; `worktree-full-problem:PLAN.md` decision 12.
