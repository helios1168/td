# U14-fullprob, code verify R3: `tools/full_plan.py` against `docs/FULL_PROBLEM.md` §6

Date 2026-09-10. Verified against the **working tree**, not a commit. The tree moved twice
under this verification; every verdict below was reproduced against the last state:
`tools/full_plan.py` mtime 02:31:10 and `td/solvers/level0.py` mtime 02:31:01, over commit
`fcb4edb` ("Code verify: level0.py, one defect in the centroid-distance cap"). The uncommitted
driver diff at that point is `--move-budget` (argparse flag, `order` truncation in `_rep_moves`,
one `params.json` key) and an optional `passes` key in `_write_failure`; the uncommitted
`level0.py` diff is the `cap_dist` row-index fix and `SolveFailure.passes`.
`tests/test_full_plan_cli.py` carries the same wave: the `HAVE_LEVEL0` guard is gone and a
`--move-budget` default test is in.

Environment, measured in this session: `/Users/ntlee/projects/td/.venv/bin/python3` 3.13.15,
numpy 2.5.2, scipy 1.18.1, networkx 3.6.1, HiGHS 1.15.1 (banner from the live solve in probe 6),
run from the worktree root. Toys only, `--engine scipy --strategy direct`,
`td.geo.state_rook` monkeypatched. No CONUS solve was started.

Artifacts: `tools/verify/U14-fullprob/full_plan_probes/`, run as

    /Users/ntlee/projects/td/.venv/bin/python3 -u \
        tools/verify/U14-fullprob/full_plan_probes/probe1_route_s.py      # item 1
        ... probe2_joint_whfi.py  probe2b_catchall_crash.py               # item 2
        ... probe3_geo.py                                                 # item 3
        ... probe4_reps.py  probe4b_accept.py                             # item 4
        ... probe5_outputs.py  probe7_failure_keys.py                     # item 5
        ... probe6_threads.py                                             # item 6

`toy.py` writes a format-2 instance whose per-state channel masses are exactly what the probe
asks for, so every band argument below is checkable by hand.

## Verdicts

Counts: 17 CONFIRMED, 3 DEFECT (rows 1c, 2c, 4b), 1 UNCHECKED (`--centers` / `--incumbency`),
plus two findings that are not verdicts (3c the caps dropped under `--driver reps`, 4d the log
not separating a pin collision from an infeasible forbid). Type check 2 errors, both benign.
Tests 644 passed, 0 failed, 0 skipped (re-run on the final tree state; 639 on the previous one).

| # | claim | verdict |
|---|---|---|
| 1a | route S stage order N / WH+WH⁺ / FI+FI⁺+WHFI(+WHFI⁺), `STAGE_BUNDLES` | CONFIRMED |
| 1b | `prior` accumulates `covered`, clipped at 1 | CONFIRMED (exact, 0.0 diff) |
| 1c | a stage whose bundles have zero slots is skipped and recorded | **DEFECT** (crashes) |
| 2a | route J passes cover_N / cover_WH / cover_FI / contacts / compactness, one call | CONFIRMED |
| 2b | a WHFI slot enters no route-J coverage objective, so route J never merges | CONFIRMED |
| 2c | the catch-all rescues the merged residual, decision 1 | **DEFECT** (vacuous whenever N is served) |
| 2d | the catch-all output is labelled `WHFI_PLUS`, not WHFI and not "other" | CONFIRMED (with a `plan["bundles"]` gap) |
| 3a | `--n-max`, `--dist-max` reach `build_level0` and bite | CONFIRMED |
| 3b | `--dist-max` is km: LAEA metres / 1000 | CONFIRMED |
| 3c | both caps are silently dropped under `--driver reps` | finding, documented in code, not in `params.json` |
| 4a | moves = `forbid_bundle` copies + `_z_fix_away`, scored by `state_stage2` | CONFIRMED |
| 4b | an accepted move exists | **DEFECT** (none is reachable: every merge collides with `pin_contacts`/`pin_cover_*`) |
| 4c | a pin collision is recorded with `value: null` | CONFIRMED |
| 4d | the log distinguishes a pin collision from an infeasible forbid | **NO** (both `reason: "infeasible"`) |
| 4e | `drop_n` is not evaluable under route S | CONFIRMED (silently absent from the log) |
| 5a | `plan.json` keys; per-state shares ≤ 1 per fine channel | CONFIRMED (max excess 0.0) |
| 5b | `projections/<bundle>/instance_descaled.json.gz` loads; zips = states with positive share | CONFIRMED |
| 5c | `state_shares.csv` `target_mass = M^B_s · y_sj`, per row and per district | CONFIRMED (1e-9 rel) |
| 5d | `staffing.json` uses one global rep order (REPORT.md requirement 1) | CONFIRMED |
| 5e | `failure.json` keys equal `state_splits._write_failure`'s; `timings.json` on failure | CONFIRMED, with one additive key (`passes`) after the second integration edit |
| 6a | trap 18: one `--threads` per process, portfolio forces 2 | CONFIRMED (trap reproduced live) |
| 6b | trap 12: `certified` only from `mip_rel_gap = 0.0` solves | CONFIRMED (scipy, highs, scip) |
| 7 | tests that pass for the wrong reason | 5 named below |
| 8 | `--centers` / `--incumbency` (`_moments_from_draw`, `_anchors_from_draw`) | UNCHECKED (needs a committed draw) |

Gates: `tests/run_all.py` 644 passed, 0 failed, 0 skipped. `uvx pyright --pythonpath
.venv/bin/python3 tools/full_plan.py` 2 errors, both benign optional narrowing
(`__doc__.splitlines()` at :97, `last['slots']` at :714 where `last` is set by the preceding
`run_stage`). No pyright/mypy config in `pyproject.toml`.

---

## Item 1: route S

```
CLAIM     §6 route S ("N, fix as prior, then WH and WH⁺, then FI, FI⁺, WHFI, WHFI⁺")
          <-> full_plan.py:68-72 STAGE_BUNDLES, :651-692 run_stage / the priority loop
ATTACK    probe1_route_s.py: three states, AA-BB adjacent, CC isolated with 0.3 national
          mass against L = 0.92, so stage N can only cover part of the map.  build_level0 and
          solve_passes are wrapped to capture every `prior` argument and every `covered`
          return.  Compared bit for bit (rtol = atol = 0), not by tolerance.
VERDICT   CONFIRMED for the order and the fold
BASIS     prior[stage n] == sum of covered[0..n-1], max abs diff 0.000e+00 at all three
          stages; accumulated prior max 0.99999999799, never above 1.  CC's residual stays
          1.0 in all four channels, so the partial-coverage case is what was folded.  Note
          the code comment at :677-678 is wrong on its own arithmetic: `residual` is
          `clip(cover_ub - covered, 0, None)`, so `1 - residual = min(1, prior + covered)`,
          identical to the fold the code performs including the clip.  It would not have
          counted the prior twice.  The behaviour is right either way; only the comment is not.
ARTIFACT  full_plan_probes/probe1_route_s.py
CAVEATS   `--prior PLAN.json` (`_prior_from_plan`) is not exercised; only the in-run fold is.
```

```
CLAIM     "a stage whose bundle has zero slots is skipped and recorded"
ATTACK    probe1_route_s.py part 2 (`--bundles N,WH,FI` with zero FI mass) and
          probe2b_catchall_crash.py (`--catch-all` after the sequential stages covered
          everything, which is the configuration decision 9 mandates).
VERDICT   REFUTED - the run dies
BASIS     `ValueError: zero-size array to reduction operation maximum which has no identity`,
          td/solvers/level0.py:211 `(M_tot * D.max(axis=1)).sum()` with K = 0.  Reached from
          full_plan.py:655 (`run_stage` -> `_build`).  Nothing skips a stage whose
          `slot_counts` are all zero.  After the crash the output directory holds
          `params.json` and `timings.json` only: no `plan.json`, no `staffing.json`, no
          `projections/`, and no `failure.json` (it is not a `SolveFailure`), so a run that
          served every channel perfectly loses its entire plan.
FIX       either guard the eps line in `build_level0` (`if K and (M_tot * D.max(axis=1))...`)
          or, in the driver, call `level0.slot_counts` before `_build` and skip the stage with
          a recorded pass entry when every count is 0.  The second is what §6 describes.
ARTIFACT  full_plan_probes/probe2b_catchall_crash.py
CAVEATS   the fault line is in level0.py (R1's file); the driver's part is not skipping.
```

## Item 2: route J and the catch-all

```
CLAIM     §6 route J: cover_N (pure N, decision 8), cover_WH (WH, WH⁺), cover_FI (FI, FI⁺),
          contacts, compactness, in one `solve_passes` call
          <-> full_plan.py:78-82 JOINT_COVER, :340-359 _pass_list, :362-383 _run_passes
ATTACK    probe2_joint_whfi.py, variant joint_withN.  AA carries WH 0.5 and FI 0.5, each
          below L = 0.84 alone, 1.0 together and inside the band; BB carries national only.
          So the one and only district that can serve AA's WH and FI is a merged slot.
VERDICT   CONFIRMED (the pass list) and CONFIRMED (route J never opens a merged district)
BASIS     pass log = cover_N 2.1, cover_WH 0.0, cover_FI 0.0, contacts 3.0, all certified,
          one `solve_passes` call per stage.  11 slots were built including 2 WHFI slots;
          none is used.  cover_WH's objective is zero on WHFI columns (`cover_pass` only
          names the bundles it is given) and the contacts pass minimises sum z, so opening a
          WHFI slot is strictly worse.  AA's WH and FI end up entirely in the residual
          (residual AA = {WH: 1.0, FI: 1.0}).  Route S does reach WHFI on the same instance:
          probe2_joint_whfi.py variant seq_withN covers AA's 1.0 with a WHFI slot at the
          seq_FI stage, which is the asymmetry the TODO at full_plan.py:75-77 records.
ARTIFACT  full_plan_probes/probe2_joint_whfi.py
CAVEATS   toy scale; a CONUS run may open WHFI only if some other pass pays for it, and none does.
```

```
CLAIM     decision 1 / §6 catch-all: "one bundle over the residual cells ... a fourth channel
          exists iff the catch-all used a slot" <-> full_plan.py:92 CATCH_ALL_BUNDLE,
          :701-705
ATTACK    the discriminating pair in probe2_joint_whfi.py.  Same WH/FI residual at AA in
          both runs; the only difference is whether AA has any national mass.
VERDICT   REFUTED as a residual pass; CONFIRMED as an implementation of "one four-channel
          bundle"
BASIS     joint_withN (AA national 0.1): catch-all builds 2 WHFI_PLUS slots, cover_other = 0,
          0 slots used, AA's WH and FI stay unserved.  joint_noN (AA national 0.0, everything
          else identical): cover_other = 1.0, 1 slot used, mass 1.0, y = {AA: 1.0}.  The
          mechanism is the product form: a WHFI_PLUS slot appears in all four cover rows, so
          `y_sj <= min_c cover_ub[s,c]`, and once cover_N has served AA's national mass
          `cover_ub[AA, N_WH] = 0` forces `y = 0`.  On any instance where national mass sits
          in every state (the synthetic CONUS instance does), the catch-all can never use a
          slot, and "a fourth channel exists iff the catch-all used a slot" always answers no.
FIX       the catch-all bundle has to be per-cell, not a product bundle: run it over
          `{WH, FI}` and `{N_WH, N_FI}` (or per residual channel) rather than
          `CATCH_ALL_BUNDLE = "WHFI_PLUS"`, or weight `W` by `cover_ub` so a slot prices only
          the residual it can actually take.  One line at full_plan.py:92 selects the bundle.
ARTIFACT  full_plan_probes/probe2_joint_whfi.py
CAVEATS   the choice of a four-channel bundle follows §6's own wording; this is the design
          degenerating under product form, not the driver deviating from the doc.
```

```
CLAIM     the catch-all output's label
ATTACK    read the slot record written by the joint_noN run
VERDICT   CONFIRMED: labelled `WHFI_PLUS`
BASIS     `{"id": "P012", "bundle": "WHFI_PLUS", "used": true, "mass": 1.0, "y": {"AA": 1.0}}`
          and `projections/WHFI_PLUS/`.  Not "WHFI", not "other".  Gap: `plan["bundles"]` is
          `list(enabled)` = the six default bundles, so it omits `WHFI_PLUS` even when a slot
          carries it.  `_prior_from_plan` survives that (it looks names up in
          `channels.BUNDLES`), but a reader of `plan["bundles"]` is told the wrong thing.
ARTIFACT  full_plan_probes/probe2_joint_whfi.py
CAVEATS   none.
```

## Item 3: driver G

```
CLAIM     §6 route G: `sum_s z_sj <= n_max`, `z_sj + z_s'j <= 1` beyond Δ km on state
          centroids <-> full_plan.py:184-191 _state_xy, :386-401 _build
ATTACK    probe3_geo.py monkeypatches `state_rook` with real shapely boxes at LAEA metre
          offsets 0, 500 km, 2,000 km on a chain AA-BB-CC.  Each state has 0.4 national mass
          and k = 1, so L = 0.96 and a slot must hold all three states to be usable: a cap
          that forbids any pair drops covered mass from 1.2 to 0.  Five runs: no cap,
          --dist-max 3000, --dist-max 1000, --n-max 2, and --dist-max 1000 --driver reps.
VERDICT   CONFIRMED
BASIS     `_state_xy` returns [[0, 0], [500, 0], [2000, 0]], i.e. km, and `td.geo.LAEA` is
          `+proj=laea ... +ellps=sphere`, metres, so the /1000 is right.  --dist-max 3000
          adds a `cap_dist` block of 0 rows (no pair beyond 3,000 km) and covers 1.2;
          --dist-max 1000 adds 4 rows = 2 far pairs x 2 slots (AA-CC 2,000 km, BB-CC 1,500
          km) and covers 0.0.  --n-max 2 adds a `cap_n` block of 2 rows and covers 0.0.
ARTIFACT  full_plan_probes/probe3_geo.py
CAVEATS   the cap is checked as a row block and by its effect on the optimum, not by reading
          the real TIGER centroids; the tests in `tests/test_full_plan_cli.py` pass `{}` for
          the polygons, so `_state_xy` had never executed before this probe.  The row *content*
          of `cap_dist` belongs to `td/solvers/level0.py` and is R1's verdict, not this one:
          R1 found a `_block` row-index defect there (`np.repeat(np.arange(P), K)` collapsing
          the slots of a pair into one row, which forbids the pair anywhere on the map) and
          fixed it in the same working tree.  This probe's discriminator, covered mass falling
          from 1.2 to 0.0, fires under both readings, so read row 3a as "the flags reach the
          builder and the cap binds", not as a check on the row algebra.
```

Finding 3c: under `--driver reps`, `_build` passes `n_max=None, dist_max=None` (full_plan.py:398-399),
so `--dist-max 1000 --driver reps` produced no `cap_dist` rows and covered 1.2, while
`params.json` still records `dist_max: 1000.0`. The drop is deliberate and commented, but a
reader of `params.json` cannot tell the cap was ignored.

## Item 4: driver R

```
CLAIM     §6 route R: per-state moves {keep, merge WH+FI, drop N}, each a `forbid_bundle` copy
          with z fixed away from the state and its rook neighbours, scored by `state_stage2`,
          the accepted move's problem becoming the incumbent
          <-> full_plan.py:85-89 MOVES, :413-426 _z_fix_away, :428-513 _rep_moves
ATTACK    probe4_reps.py: four states in a path, each 0.5/0.5/0.5, driver reps on both routes;
          plus an independent oracle that rebuilds the joint model by hand, runs the same
          passes, and then solves the *same* `forbid_bundle` twice, once on the pinned problem
          the driver hands the move and once on the unpinned problem.  probe4b_accept.py then
          tries to construct an acceptance: a state with no WH or FI mass at all (so the
          forbid is a no-op) and a degenerate national split (many contact-optimal maps).
VERDICT   CONFIRMED for the mechanism; REFUTED for "an accepted move"
BASIS     Structure: `forbid_bundle` copies `var_lb`/`var_ub`, so `_z_fix_away`'s `bound_z`
          calls hit the copy and the incumbent survives; the score is
          `state_stage2(cells, prefix + trial_slots)`, i.e. the whole plan, not the stage.
          Every non-keep move on probe4's toy is `{"value": null, "reason": "infeasible"}` on
          both routes.  The oracle isolates the cause: the same forbid is feasible on the
          unpinned problem and infeasible on the pinned one, for merge_whfi and drop_n and
          for two different states.  The pinned problem carries `pin_cover_N`, `pin_cover_WH`,
          `pin_cover_FI` and `pin_contacts` (solve_passes returns it as `result["problem"]`,
          full_plan.py:672).  The argument generalises whenever the cover pass reached that
          state's mass, which every toy here and the synthetic CONUS instance satisfy: a move
          that changes which bundles a state is served by removes that mass from a pinned
          cover objective
          (cover_WH counts WH and WH⁺, both forbidden by merge_whfi; cover_N counts pure N,
          forbidden by drop_n), so the cover pin is unreachable; a move that does not change
          them is a no-op whose trial optimum equals the incumbent's.  probe4b confirms the
          second half: merge_whfi at a state with no WH/FI mass solves and scores
          -1.2473006366857216, exactly the keep value, and `accepted = value > best_value`
          keeps it out.  So route R as built cannot accept the merge it exists to explore;
          the only acceptance it could ever record would be an alternative optimum of the
          contacts objective picked up by the solver, which is a tie, not the move.
FIX       hand the moves the pre-pin problem (keep `problem` from before `_run_passes` and
          re-impose only the cover rows the move is meant to preserve), or re-solve the move
          with the full pass list instead of `contacts` alone and compare coverage explicitly.
ARTIFACT  full_plan_probes/probe4_reps.py, full_plan_probes/probe4b_accept.py
CAVEATS   because no move is ever accepted, the incumbent hand-off at :509-511 is untested by
          execution.  Read: an accepted trial carries `_z_fix_away`'s z bounds into the
          incumbent, so every later state is re-solved over a progressively frozen z, and
          those bounds are never released.
```

```
CLAIM     "a forbid that lowers achievable cover collides with the cover pin and is recorded
          with `value: null`", and the log tells the two failures apart
VERDICT   CONFIRMED for the record; NO for distinguishability
BASIS     the failed entry is `{state, move, value: null, reason, accepted: false}` and a
          successful one has no `reason` key, so `value: null` does mark a failure.  But
          `reason` comes from `getattr(exc, "reason", type(exc).__name__)` and both a pin
          collision and a forbid with no feasible map raise `SolveFailure` with
          `reason = "infeasible"`; only the third failure mode, a slot the move leaves
          unstaffable, differs (it is a `ValueError`, logged as `"ValueError"`).  A reader of
          `plan.json` cannot tell a pin collision from an infeasible forbid.  The
          oracle in probe4_reps.py is what separates them, by re-solving without the pins.
ARTIFACT  full_plan_probes/probe4_reps.py
```

```
CLAIM     `drop_n` is not evaluable under route S (the N slots live in an earlier model)
VERDICT   CONFIRMED
BASIS     route joint logs `drop_n` for every state (infeasible); route sequential logs only
          `keep` and `merge_whfi`, because `forbidden = [b for b in forbidden if b in enabled]`
          empties for `drop_n` at the seq_FI stage and the move is skipped with no log entry.
          Its absence is silent: nothing in `plan.json` says the move was not offered.
          Second-order: under route S `merge_whfi` reduces to forbidding FI and FI⁺, since WH
          and WH⁺ are not in the last model, and the state's WH is already committed by the
          earlier stage, which sets `cover_ub[s, WH] = 0` and makes WHFI unusable there.  So
          route S + driver R cannot merge either, for a second and independent reason.
ARTIFACT  full_plan_probes/probe4_reps.py
```

## Item 5: outputs

```
CLAIM     plan.json / projections / state_shares.csv / staffing.json / failure.json /
          timings.json <-> full_plan.py:289-316, :517-556, :707-733, :320-336, :738-746
ATTACK    probe5_outputs.py on a four-state path with asymmetric channel masses.  Every
          number is recomputed from `channels.aggregate` (and, for the projection, from the
          projected instance's own node masses), never from the file being checked.
          target_mass is compared per row and per district group, not only in total, so a
          permutation of masses across slots cannot pass.  The failure path is forced by
          patching `level0.solve_passes` to raise `SolveFailure(2, ...)`.
VERDICT   CONFIRMED
BASIS     keys `{state_list, bundles, slots, per_state, passes, moves}`, slot record keys
          `{id, bundle, used, mass, contacts, y}`.  Max (per-channel coverage - 1) over all
          cells = 0.0, and `residual_by_channel` equals 1 - coverage to 1e-6 everywhere.
          Each `projections/<bundle>/instance_descaled.json.gz` loads through
          `td.instance.load_descaled` (which does not call `check_descaled`, so the low median
          `m_rel` of a projection is not rejected) and its zip set is exactly the zips of the
          states with positive share in that bundle; the projection's summed node mass equals
          the aggregated `M^B_s` to better than 1e-5 relative (`write_v1` rounds to 6
          significant figures, which is the noise floor here).  `state_shares.csv`: 0 bad rows
          at 1e-9 relative against `M^B_s * share` recomputed from the cells, and each
          district group sums to that slot's own `mass` (D01 1.100000000 vs 1.100000000, D02
          0.900000000 vs 0.900000000, and the same for N and WH).  `staffing.json` `reps` is
          `cells.reps`, one sorted global order over the whole instance, used in one
          `state_stage2` call over the union of slots, which is REPORT.md requirement 1; the
          assignment is injective and no district is unstaffed.  `failure.json` keys equal
          `tools/state_splits.py::_write_failure`'s exactly (`cell, delta, message, reason,
          solve_seconds, status`) with `delta: null` and `reason: "infeasible"`, and both
          `timings.json` and `params.json` are on disk after the re-raise.  One qualification
          from the second integration edit (probe7_failure_keys.py): `_write_failure` now
          copies `exc.passes` into the record when the exception carries it, and
          `solve_passes` now attaches that log to every `SolveFailure` it raises.  So the key
          sets are equal for a failure raised anywhere else, and a real level-0 failure writes
          a seventh key, `passes`.  `reason` and `solve_seconds`, the two fields
          `app/headline.py::failure` reads, are untouched, so the extra key is additive; the
          shipped test cannot see it, because it constructs a bare `SolveFailure`.
ARTIFACT  full_plan_probes/probe5_outputs.py
CAVEATS   the 1e-9 tier is a toy artefact: this instance's shares are exact (1.0, 0.6, 0.4), so
          `_slot_records`' `round(y, 6)` was a no-op.  On real data the CSV's `share` is rounded
          while `slot["mass"]` uses the unrounded `y`, so the per-district sum can differ by up
          to about 1e-6 times the contact count relative; the shipped test's 1e-6 is the right
          tier for CONUS.  Level 2 is not run on a projection here, only the load; the CSV's
          `district` column
          renumbers per bundle (`run_draw.district_id(j)` over that bundle's used slots), so
          the mapping back to the plan's slot ids exists only through the row order.
          Downstream risk not covered: two bundles that share a fine channel (N and WH⁺, say)
          both project the full `M^B` of the same zips, so nothing at zip level yet enforces
          the state-grain cover row.
```

## Item 6: the traps

```
CLAIM     trap 18 (one thread count per process; the portfolio parent uses 2) and trap 12
          (`mip_rel_gap = 0.0` for a certificate)
ATTACK    probe6_threads.py: `solve_passes(strategy="portfolio", threads=...)` for None, 2, 4;
          then the exact sequence the driver produces under `--strategy portfolio --driver
          reps`, live against HiGHS 1.15.1 in one process: threads 2, then None (which is what
          `_rep_moves` passes), then 2, then 4 as a control.
VERDICT   CONFIRMED
BASIS     `solve_passes` accepts threads None and 2 under portfolio and refuses 4 with the
          trap-18 message.  Live: 2 -> status 0, None -> status 0, 2 -> status 0, and 4 ->
          `SolveFailure ... HiGHS stopped (Not Set) with no incumbent`, trap 18 reproduced
          exactly.  So `_rep_moves`' `threads=args.threads` (None under portfolio) is safe
          because an unset option does not re-size the pool; it would not be safe if a future
          edit forwarded a different integer.  Trap 12: every engine the driver offers pins
          the gap at zero before `certified` is read (`scipy` `options={"mip_rel_gap": 0.0}`,
          `highs` `setOptionValue("mip_rel_gap", 0.0)` at milp_engines.py:376, `scip`
          `setParam("limits/gap", 0.0)` at :484), `certified = res["status"] == 0` for a
          direct pass, and a scipy time-out returns the string status `"time_limit"`, which is
          not 0, so it records `certified = false`.  That path is live: `solve_problem`'s scipy
          branch calls `ss.solve(problem, time_limit=..., strict=False)` (milp_engines.py:92),
          which is exactly the `strict=False` softening `_solve_scipy` needs to return a
          timed-out incumbent instead of raising, so §6's "a timed-out pass pins its incumbent
          and records certified = false" holds on the engine the tests pin.  The portfolio
          contacts pass reads
          `certified_splits`, the portfolio's own cutoff-round certificate, and its objective
          is exactly the unit cost on z that certificate is about.
ARTIFACT  full_plan_probes/probe6_threads.py
CAVEATS   the live sequence was run on a small model; the SCIP path was not executed.
```

## Item 7: tests that pass for the wrong reason

`tests/test_full_plan_cli.py` (working tree, mtime 02:26:20):

1. `test_driver_reps_logs_every_move_and_the_catch_all_pass_runs` asserts `plan["moves"]` is
   non-empty and `"keep" in {m["move"]}`. Both hold when every non-keep move failed with
   `value: null`, which is what happens on the toy. It should assert that at least one
   non-keep move carries a numeric `value`, which would have failed and surfaced item 4b.
2. The same test asserts `"catch_all" in stages`. A catch-all that used zero slots still logs
   its passes at value 0, so the assertion holds in exactly the degenerate case of item 2c.
   It should assert `cover_other > 0` on an instance built to have a residual, or assert the
   documented negative ("no slot used") explicitly.
3. `_check_plan`'s per-channel `covered <= 1 + 1e-6` restates the model's own cover row on the
   solver's own output; no plan the MILP can produce fails it. The check with teeth is the one
   this probe ran: `residual_by_channel == 1 - covered` recomputed from the cells.
4. `test_end_to_end_sequential_writes_a_plan_and_projections` compares `sum(target_mass)` over
   all rows of a bundle with `sum(mass)` over that bundle's slots. Any permutation of masses
   across districts, and any error that cancels between rows, passes. Per row and per district
   is the check (probe5).
5. No test passes `--n-max`, `--dist-max`, `--prior`, `--centers` or `--incumbency`; the toys
   monkeypatch `state_rook` to return `{}` for the polygons, so `_state_xy`,
   `_anchors_from_draw` and `_moments_from_draw` are dead to the suite. `--dist-max` had never
   been executed before probe3.

(The `HAVE_LEVEL0` early-return guard, which made four end-to-end tests pass trivially whenever
an import failed, has already been removed by the integration agent.)

## Not covered

`--centers` / `--incumbency` (`_anchors_from_draw`, `_moments_from_draw`, the compactness
pass) need a committed draw and the real instance: UNCHECKED. `--prior PLAN.json`
(`_prior_from_plan`) is read but not executed. Nothing here ran on CONUS, so the §9 numbers
(slot counts, solve times, the route-S 8-split regression) are untouched by this report.

**Verdict.** `tools/full_plan.py` drives the level-0 model as §6 writes it, but two of §6's own
constructions are inert as built (the product-form catch-all bundle covers nothing wherever
national is served, and route R's moves are re-solved on the pinned problem, so no merge is ever
feasible) and a stage with zero slots crashes the run outright, losing the plan on exactly the
`--catch-all` configuration decision 9 mandates.
