# Code verify: `td/solvers/level0.py` against U14-fullprob level 0

Date 2026-09-10. Subject `td/solvers/level0.py` at `ea665cd` on `worktree-full-problem`, with
its parent edits in `td/solvers/state_splits.py` and `td/solvers/milp_engines.py` and the tests
in `tests/test_level0.py`. Spec: `docs/FULL_PROBLEM.md` §5 and §6, `PLAN.md` "Level-0 mapping
onto `state_splits.py`" and interface contract row C.

Artifact: `tools/verify/U14-fullprob/verify_level0.py`, run from the worktree root as

    PYTHONPATH=. /Users/ntlee/projects/td/.venv/bin/python3 tools/verify/U14-fullprob/verify_level0.py

45 checks, 43 pass, 2 fail (both the same defect). Python 3.13.15, numpy 2.5.2, scipy 1.18.1,
HiGHS 1.15.1, pyright 1.1.413. Every solve is deterministic (`scipy` and `highs` at
`mip_rel_gap = 0.0`, seeded `default_rng` for the two random fixtures) except the 0.35 s
time-limit probe, which accepts either outcome and returned status `time_limit` on this run.

## Counts

- VERIFIED 15 mapping rows · REFUTED 1 · INCONCLUSIVE 1 · mapping gaps (spec asks, code has no
  counterpart) 1.
- Type check: `uvx pyright --pythonpath .venv/bin/python3 td/solvers/level0.py` gives 5 errors,
  none of them a runtime fault (three are one `**kw` splat at line 497, one is `append_row`'s
  return annotation `SplitProblem` assigned back into a `Level0Problem` variable at line 505).
  The project is not pyright-clean: `td/solvers/state_splits.py` gives 7 on the same run, so
  this is not a regression gate.
- Tests: `tests/run_all.py -k level0` 18 passed, 0 failed. Full `tests/run_all.py` 634 passed,
  0 failed, 0 skipped.

## Mapping table and verdicts

| model object (§5 / §6) | code symbol | verdict |
|---|---|---|
| cover row per `(s, c)`, `ub = 1 − prior` | `level0.py:242-246` `rows["cover"]` | VERIFIED |
| `η z ≤ y ≤ z ≤ u` | `rows["yz"]`, `["yz_lo"]`, `["zu"]` (248-262) | VERIFIED |
| band `L u_j ≤ Σ_s W_sj y_sj ≤ U u_j`, τ scaling, `1 ∓ δ` rewrite | `rows["band_lo"]`, `["band_hi"]` (263-269), `delta=(U−L)/(L+U)` (358) | VERIFIED |
| root `Σ_s r_sj = u_j`, `r ≤ z` | `rows["root"]`, `["rz"]` (270-279) | VERIFIED |
| flow rows per slot, level 1's | `rows["flow_tail"]`, `["flow_head"]`, `["net"]` (281-300) | VERIFIED |
| `n_max` cap | `rows["cap_n"]` (302-305) | VERIFIED |
| `dist_max` cap `z_sj + z_s'j ≤ 1` | `rows["cap_dist"]` (306-317) | **REFUTED** |
| `u_j ≥ u_{j+1}` always | `rows["order_u"]` (319-328) | VERIFIED |
| mass ordering only without anchors and without `D` | `rows["order_mass"]` (329-339), `order_mass` default (212-213) | VERIFIED |
| anchors as `var_lb` on `z` | `level0.py:344-348` | VERIFIED |
| `forbid_bundle` zeroes both bounds on `z` and `y` | `forbid_bundle` (367-383) | VERIFIED |
| variable layout, `u` after `f`; the seam reads the subclass | `off_u` (219-222); `milp_engines._decode_x`, `fix_roots`, `with_cutoff`, `_clone`, both warm starts | VERIFIED |
| parent `SplitProblem.decode_zy` unchanged | `state_splits.py:132-151` | VERIFIED |
| `K_B = ⌈Σ M·cover_ub / L⌉` is enough slots | `slot_counts` (125-137) | VERIFIED |
| `solve_passes` pin, senses, certified, zero objective, timeout, threads | `solve_passes` (445-517) | VERIFIED |
| channel-level contiguity through a committed state | cover row + `yz_lo` | VERIFIED |
| route-S regression at `K_N = 18` | no count override in `build_level0` | mapping gap |
| a pass that times out with **no** incumbent | not handled in `solve_passes` | INCONCLUSIVE |

## REFUTED

```
CLAIM     §5 / §6 route G: "z_{s,j} + z_{s',j} <= 1 when the state centroid distance exceeds
          Delta", one row per (far pair, slot)  <->  level0.py:306-317, rows["cap_dist"]
ATTACK    Two oracles. (1) Symbolic read-back: the assembled block's rows were compared with
          rows written by hand from the spec. (2) A hand-built instance with a known answer:
          three states on a path at x = 0, 1, 2, mass 1.0 each, one channel, L = 0.8,
          U = 1.2, dist_max = 1.5.  Every state alone is a legal slot, so the maximum cover
          is 3.0 and no slot ever needs two far states.
VERDICT   REFUTED
BASIS     The row index is the pair index, not the (pair, slot) index:

              pk = np.repeat(np.arange(P), K)      # [0]*K, [1]*K, ...
              add("cap_dist", _block(np.concatenate([pk, pk]), <cols over all (p, j)>,
                                     np.ones(2 * P * K), P * K, n_var), -inf, 1)

          `_block` sums duplicates, so row p becomes  sum_j z_{a_p,j} + sum_j z_{b_p,j} <= 1:
          two states further apart than Delta may not be contacted **anywhere on the map**,
          at most one of them may appear in one single slot.  Rows P .. P*K-1 of the block are
          empty (36 of 42 empty in the 6-pair, 7-slot fixture).  On the three-state probe the
          model returns cover 2.0 where 3.0 is correct, and state 2 is left uncovered.  Rows
          should be `np.arange(P * K)` repeated twice, the way `cap_n` uses `j_of`; `order_mass`
          is the row block where a pair index *is* correct, because that row sums over all s.
FIX       In build_level0, replace

              pk = np.repeat(np.arange(P), K)
          by
              pk = np.arange(P * K)

          (the column expressions already enumerate (pair, slot) in that order).  Confirmed by
          the artifact's check "the per (pair, slot) cap covers 3.0 and still keeps far states
          out of one slot": the same cap appended one row at a time with `append_row` gives
          cover 3.0 with states 0 and 2 in different slots.
ARTIFACT  tools/verify/U14-fullprob/verify_level0.py, checks "cap_dist is one row per (far
          pair, slot)" and "dist_max forbids one slot holding two far states, not the whole
          map".
BLAST     Route G is the only consumer.  `tools/full_plan.py:123` gives `--dist-max` the
RADIUS    default `None` and line 403 passes it only under `--driver geo`, and the one run
          on disk, `battery/results/full_problem/seq_regression/params.json`, records
          `"driver": "geo"` with `"dist_max": null` and `"n_max": null`.  So no committed
          result is affected, and `--n-max` alone is sound.  Any route-G run that sets
          `--dist-max` before the fix solves a much more constrained problem and
          under-reports coverage without saying so.
```

## INCONCLUSIVE

```
CLAIM     §6: "A timed-out pass pins its incumbent and records certified = false."
ATTACK    12 states, three bundles, engine=highs, threads=2, time_limit=0.35 s.
VERDICT   VERIFIED for the incumbent case (status "time_limit", certified False,
          "pin_cover_A+AB+B" present in rows, the next pass then solved).
          INCONCLUSIVE for the no-incumbent case: `solve_problem` raises `SolveFailure` and
          `solve_passes` neither catches it nor records it, so the whole call dies rather than
          logging a pass with certified = false.  No probe can make that outcome
          deterministic at a chosen time limit, so this is named rather than tested.
BASIS     level0.py:491-499 has no try/except around the two solve calls.  The propagation
          itself is known and covered: `tests/test_level0.py::test_append_row_pins_a_value`
          exercises the same path deterministically for reason `infeasible`.  What is
          untested is the one reason string `no_incumbent` at a time limit.
ARTIFACT  verify_level0.py, `timed_out_pass_pins_its_incumbent`.
CAVEATS   The docstring only promises the incumbent case, so this is a gap between §6 and the
          code, not a contradiction inside the code.
```

## VERIFIED, one line each (full attacks in the artifact)

- **Cover rows.** Read back symbolically on a three-bundle, three-channel, six-state model
  where two bundles share channel `c0`: row `(s, c)` carries coefficient 1 on `y_sj` for
  exactly the slots whose bundle lists `c`, and its upper bound is `1 − prior_sc` to the last
  bit; the lower bound is `−inf`. A channel in no bundle gets an empty row, which is
  vacuously true, and that is the right reading of "other".
- **Band and the `1 ∓ δ` rewrite.** `(1 − delta) * tau == L` and `(1 + delta) * tau == U` hold
  as exact float equalities at `tau = (L+U)/2`, not just to tolerance, so the level-1
  conditioning trick carries over unchanged. Each band row is `Σ_s (W_sj/τ) y_sj − (L or
  U)/τ · u_j` with the right sense.
- **`η z ≤ y ≤ z ≤ u`, root, `rz`.** One row per `(s, j)` or per slot, coefficients exact.
  `u_j = 1` with no contact is impossible (`band_lo` forces mass ≥ L > 0, so some `y > 0`, so
  some `z = 1`), and `z = 1` with `u = 0` is blocked by `zu`; that is why `decode_zy` may read
  `used` off `z` and why `_objective` may fill the `u` block from `used`.
- **Flow block identity.** `A[rows["flow_tail" | "flow_head" | "net" | "yz" | "yz_lo" | "rz"],
  :off_u]` is byte-identical (dense array equality, plus row bounds) to `build_milp`'s own
  blocks at `k = K` on the same edge list and `eta`. `root` and `band` differ by design (`u`
  on the right-hand side).
- **`K_B` is enough slots.** A used slot carries at least `L`, so a plan covering total mass
  `T` uses at most `⌊T/L⌋` slots, and `T ≤ avail`; `K_B = ⌈avail/L − 1e−9⌉ ≥ ⌊avail/L⌋`, so
  the count never binds. Checked as arithmetic over 2,000 random `(avail, L)` pairs and by
  solving two instances (a plain bundle, 4 slots to 7; a merged bundle under a partial prior,
  7 slots to 10) with three extra slots each: the padding states that raise the count carry
  exactly `L` and are then closed with `forbid_bundle`, which runs after `slot_counts`, so the
  slots exist and no new mass is reachable, and the covered mass does not move. Note `slot_counts` sums `M_sc · cover_ub_sc`
  over `c ∈ B`, while the mass state `s` can actually put into bundle `B` is
  `M^B_s · min_{c∈B} cover_ub_sc` (every cover row of the bundle bounds the same
  `Σ_{j∈J_B} y_sj`). The code therefore over-estimates for merged bundles under a partial
  prior: safe direction, larger MILP. In the probe it counted 5.0 available where 4.0 was
  reachable and still gave 7 slots against the 5 that could be used.
- **Channel-level contiguity.** Three-state path, masses `[0.5, 0, 0.5]`: free, the zero-mass
  middle state bridges and the cover is 1.0; with `prior[1, c0] = 1` the cover falls to 0.0 and
  `z[1]` is off everywhere, exactly decision 6. On a merged bundle `{c0, c1}` committing
  **one** channel of the pair is already enough to refuse the bridge (cover 1.0 → 0.0), because
  any single cover row of the bundle bounds `y_1j`. The module docstring says "all cells of B
  prior-committed"; the mechanism is "any cell", which is stricter and worth stating that way.
- **The `eps` tie-break stays lexicographic at level 0.** At level 1 the guarantee rests on
  `Σ_j y_sj = 1`, which level 0 does not have: a state may appear in slots of several bundles.
  The `W` weighting restores it, `Σ_j W_sj y_sj = Σ_c M_sc Σ_{j: c∈B_j} y_sj ≤ Σ_c M_sc
  cover_ub_sc ≤ M_tot_s`, so `eps_lexicographic(M_tot, D)` still keeps the whole term under
  half a contact. Confirmed by maximising `eps · Σ W D y` over the LP relaxation with
  `linprog` (an oracle independent of the formula): 0.3121 < 0.5 on a random three-bundle
  model.
- **Pins.** The pin row is `≤` on the minimised objective at `v + |v|·1e−9 + 1e−12`, read back
  from the matrix: at cover mass 14,400 the bound is −14399.999986, a relaxation of the true
  −14400, where `v(1+1e−9)` would have been −14400.0000144, tighter than the optimum by more
  than HiGHS's absolute feasibility tolerance. `v = max(solver objective, decoded objective)`
  keeps the pin loose in both senses. A three-pass run (cover, contacts, cover again) recovers
  14,400 under both pins, so the min-sense pin at `v = 7` cuts nothing either.
- **Certified semantics.** `scipy` and `highs`/`scip` report `certified = (status == 0)`; the
  portfolio branch reads `certified_splits`, which is the certificate that no map with fewer
  contacts exists, which is the contacts objective exactly. Verified on the six-state
  contiguity fixture: the portfolio returns 7 contacts, certified, in 0.6 s, matching the
  direct scipy answer.
- **Zero-objective pass.** Recorded at `value = 0, certified = True, status = 0, seconds = 0.0`,
  not solved, and adds no `pin_` row, so the next pass keeps its whole feasible set (trap 19).
- **Threads.** `strategy="portfolio"` with `threads=4` raises; `threads=None` is read as 2 so a
  direct HiGHS pass cannot size the process pool first (trap 18). `engine="cpsat"` is refused.
- **Layout and the engine seam.** `off_u = off_f + 2|E|·K`, `n_var = off_u + K`, `var_ub` is
  `N−1` on the flow block only and 1 on `u`, `integrality` is set on `z`, `r` and `u` and not
  on `y`. `_decode_x`, `fix_roots`, `with_cutoff` and `_clone` all return or read the subclass
  correctly; `with_cutoff(p, s*)` bounds `Σ z ≤ n_state + s* − 1`, which on `Level0Problem`
  reads "fewer contacts" because `decode_zy` defines `splits = contacts − n_state`.
- **Parent decode regression.** `SplitProblem.decode_zy` reproduces the pre-refactor
  `_solve_scipy` body (`git show main:td/solvers/state_splits.py`, 735-747) field by field on a
  level-1 solve. The one behaviour change, `y / np.where(row > 0, row, 1.0)` for the old bare
  division, is unreachable at level 1: the `place` row forces `Σ_j y_sj = 1` (bounds checked at
  `[1, 1]`), so no row of `np.where(z, y, 0)` sums to zero.

## Mapping gap

`docs/FULL_PROBLEM.md` §6 names the route-S regression as "`K_N = 18` all used", but
`build_level0` derives every `K_B` from `slot_counts` and takes no count override. At band ±5 %
with `X = 18τ` the derived count is `⌈18/0.95⌉ = 19`; the ordering rows and a cover pin at `X`
leave exactly 18 used, so the regression is reachable, just not expressible as written. Worth
either a `counts=` argument or a sentence in §6.

## Tests that pass for the wrong reason

1. `test_n_max_and_dist_max_caps_bind` (`tests/test_level0.py:268`) cannot see the `cap_dist`
   defect. Its fixture is six states of 0.2 at `x = 0..5` with `dist_max = 2.5`: under the
   correct rows a slot may hold at most three consecutive states, 0.6 < L, so the cover is 0;
   under the broken rows it is 0 as well. Its structural assertion,
   `far.rows["cap_dist"][1] - far.rows["cap_dist"][0] == 6 * far.k`, counts rows including the
   36 empty ones, so it holds either way. A discriminating fixture needs states that are
   individually in band, as in the artifact's three-state probe.
2. `test_fix_roots_keeps_the_subclass_and_the_r_bounds` (`:229`) builds with no anchors and no
   `D`, so mass ordering is **on**, and then names slot 0 through `fix_roots`: the combination
   `build_level0`'s own docstring says needs `order_mass=False`. It passes because on the
   `CONTIG` fixture the two feasible slots both carry 0.9, so the ordering row is slack. The
   test does not exercise the hazard it sits next to.
3. `test_coverage_leaves_a_residual_when_it_cannot` (`:83`) turns the residual into mass with
   `out["residual"][:, 0] @ prob.M_s`, and `M_s` is the state total over **all** channels. It
   agrees with the answer only because channel B is empty in that fixture. `residual` is a
   share per cell, so the driver must multiply by `M[:, c]`, not `M_s`.

## Caveats

- Only `solve_passes` refuses `cpsat`. A direct `milp_engines.solve_problem(level0_problem,
  "cpsat")` rebuilds a level-1 model from `M_s`, `delta` and `eta` and would return an answer to
  a different problem; `lp_heuristic` and `balance_pass` likewise assume `Σ_j y_sj = 1` and the
  level-1 band, and neither raises on a `Level0Problem`.
- `solve_passes` dispatches to the portfolio on `p.name == "contacts"`, not by inspecting `c`.
  A `Pass` named `"contacts"` carrying another cost vector would be portfolio-solved and its
  `certified` would then mean "the contact count is minimal", not "this objective is optimal".
- Nothing here checks the level-0 model on the real or synthetic CONUS instance: no timing, no
  route-S regression against today's 8 splits, no `td/channels.CellTable` round trip. The
  duck-typed inputs (`cells.M`, `cells.channels`) were supplied by a `SimpleNamespace`, the same
  way `tests/test_level0.py` does.
- Solver-tolerance claims (the pin at dollar scale) were checked at cover mass 14,400, one
  order below the instance's 8,481.8 × the descaled band; the numeric-equality tier is used for
  row read-backs and 1e-6 relative for solved values.

## The orchestrator's six items

1. **Row by row against §5** - CONFIRMED for cover, band and the `τ = (L+U)/2` rewrite,
   `η z ≤ y ≤ z ≤ u`, root, the flow rows, `n_max`, both ordering rows and their default,
   anchors and `forbid_bundle`. **DEFECT** for `dist_max`: `cap_dist` is one row per far pair,
   not per (far pair, slot). Fix and probe above.
2. **Variable layout** - CONFIRMED. `u` sits after `f`, every slice in `_decode_x`,
   `fix_roots`, `with_cutoff`, `_clone` and both warm starts reads the subclass, and the
   parent's `decode_zy` reproduces the pre-refactor body on a level-1 problem field by field.
3. **`solve_passes`** - CONFIRMED for the pin in both senses at cover mass 14,400, the
   `certified` semantics per engine and under the portfolio, a timed-out pass pinning its
   incumbent, the skipped zero-objective pass and the thread rule. UNCHECKED: a pass that times
   out with no incumbent at all, which raises out of `solve_passes` instead of being recorded.
4. **`K_B` is enough slots** - CONFIRMED, by arithmetic and by two solves with three extra
   slots. `slot_counts` over-counts for merged bundles under a partial prior, in the safe
   direction.
5. **Contiguity at the channel level** - CONFIRMED on a three-state path, and on a merged
   bundle where committing one channel of the pair is already enough to refuse the bridge.
6. **Tests that pass for the wrong reason** - three named above:
   `test_n_max_and_dist_max_caps_bind` (blind to the `cap_dist` defect),
   `test_fix_roots_keeps_the_subclass_and_the_r_bounds` (mass ordering on beside a per-slot
   root fix), `test_coverage_leaves_a_residual_when_it_cannot` (residual is a share, weighted
   by `M_s` rather than `M[:, c]`).

**Verdict: the level-0 model implements §5 and §6 correctly except the `dist_max` extent cap,
whose rows collapse to one per far pair and forbid the two states from being contacted anywhere
(one-line fix, no committed result affected).**
