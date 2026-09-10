# U14-fullprob: code-verify of `td/channels.py` and `td/stage2_state.py`

Date 2026-09-10. Adversarial verification of sections 2 to 4 of `docs/FULL_PROBLEM.md` against
the code, plus the two requirements `tools/verify/U14-fullprob/REPORT.md` left for wave 2.

**Verdict.** `td/channels.py` and `td/stage2_state.py` implement sections 2 to 4 as written;
nothing here refutes the model. Four of the eight attack items come back clean (3, 4, 5, 7);
items 1, 2, 6 and 8 each carry one finding: three code defects and one test gap. None of the
three is reachable from `tools/full_plan.py` as it stands, and D3 is already fixed uncommitted;
D2 must be fixed before route R is ever scored with `candidacy=True`.

107 probe checks including the confidential-instance section. Pinned snapshot: 4 fail, 2
recorded caveats. Live tree: 3 fail, 2 caveats (the channel-order probe passes against the
uncommitted loader fix). Type check clean, suite green.

## What was verified against what

Code pinned at `9956e9d` (a `git archive` snapshot run from
`/Users/ntlee/.claude/jobs/610589f0/tmp/r2/pin`). At that commit `td/channels.py` is byte
identical to `0373964` and `td/stage2_state.py`, `td/model.py`, `td/channel.py` to `260dc70`,
which are the commits the task names (`git diff 0373964 HEAD -- td/channels.py` is empty).

The worktree was dirty throughout: another agent was editing `td/channels.py`,
`td/instance.py` and three test modules while these probes ran. Every verdict below is for the
pinned snapshot; where the live tree already differs it is said so.

Artifact: `tools/verify/U14-fullprob/verify_channels.py`. Rerun from the worktree root

    /Users/ntlee/projects/td/.venv/bin/python3 tools/verify/U14-fullprob/verify_channels.py

with an optional section list (`fmt fine synth agg proj decomp req1 req2 coef mut hub`) and
`TD_VERIFY_ROOT=<dir>` to point it at a pinned snapshot. `hub` reads the confidential instance
and is off by default; it prints counts and relative deviations only, never a value.
Environment: python 3.13.15, numpy 2.5.2, scipy 1.18.1, networkx 3.6.1, pyright 1.1.413,
probe seeds 7 / 11 / 20260910, synthetic instance seed 0. Two probes fail by design and print
`[caveat]` rather than counting as failures: the zero-mass-cell book loss (a format limit) and
the surviving mutation (a test gap). The script exits non-zero while D1, D2 and the rep-order
hazard stand, so a rerun after the fixes is a clean pass.

This report is the unit's code-verify record for these two files. `docs/units/U14-fullprob.md`
was deliberately not touched: the task pins the report here and the docs hook denies writes
under `docs/`, so the orchestrator carries the counts into the `## Code verify` section.

## Mapping table

| model object (`docs/FULL_PROBLEM.md`) | code symbol | verdict |
|---|---|---|
| §2 fine labels `C`, `N_WH = N·WH/(WH+FI)` | `channels.CHANNELS`, `channels.fine_split` (`channels.py:151`) | DEFECT (degenerate input) |
| §2 decision 3 fallbacks, reported | `fine_split` state / even branch (`channels.py:179-189`) | CONFIRMED |
| §2 cell `(z,c)`: `M_{z,c}`, `S_i(z,c)`, `S_free(z,c)` | loader `_fold_cells` (`instance.py:96`), `write_v2` (`channels.py:349`), exporter `write` (`export_instance.py:736`) | DEFECT (channel order only) |
| §2 synthetic split, hashlib, per-cell headroom | `_alpha_beta`, `synthesize_channels` (`channels.py:101,114`) | CONFIRMED |
| §3 bundle family `𝔅` | `channels.BUNDLES`, `DEFAULT_BUNDLES` (`channels.py:48`) | CONFIRMED |
| §5 `W_{s,j} = Σ_{c∈B_j} M_{s,c}` | `aggregate`, `slot_weights` (`channels.py:225,267`) | CONFIRMED |
| §4 consequence: one projection tool | `project` (`channels.py:280`), `write_v1` (`channels.py:387`) | CONFIRMED |
| §4 (a) `u^B_i(z) = Σ_{c∈B} u_i(z,c)` | `project` + `channel.gain_matrix`; `state_gain_matrix` (`stage2_state.py:122`) | CONFIRMED |
| §3 gain / §4 (c) one Hungarian | `state_stage2` (`stage2_state.py:191`) | DEFECT (staffability guard) |
| requirement 1: one global rep order | `aggregate` reps, `state_gain_matrix` default | CONFIRMED, hazard named |
| requirement 2: candidacy by penalty, nothing released | `_match_masked` (`stage2_state.py:137`) | CONFIRMED |
| §3 `c1, c2, c_free` | `model.coefficients` (`model.py:124`) and both call sites | CONFIRMED |

## Item 1: format agreement across three writers and one reader

```
CLAIM     `share` and `share_free` are fractions of the CELL's own `m_rel` in
          channels.write_v2, the exporter's v2 write and instance.load_descaled; same key
          names, same meta["channels"] order rule.
ATTACK    Round trip through both writers into the one loader and compare per CELL, not per
          zip (the shipped round-trip test compares totals, so a channel permutation would
          pass it). Independent oracle for the exporter: raw M / kappa and raw sales / kappa
          recomputed from the CSV rows, kappa = median of the national opportunity rows.
          Then a deliberately sparse extract: the alphabetically first zip carries only the
          `fi` cell while the opportunity table names `national` first.
VERDICT   DEFECT, in the channel ORDER only; every value agrees.
BASIS     write_v2 -> load: worst relative deviation 3.49e-06 over every cell's M_c, S_c and
          S_free_c, inside the six-significant-figure write tier (5e-6). Exporter -> load:
          M_c exact (0.00e+00) against raw M / kappa; book recovers raw sales / kappa;
          totals are the cell sums to 1e-12. Both writers emit the same node columns
          (channel, m_rel, share, share_free, state, z) and the same format string. On the
          sparse extract the exporter's meta says ('national','wh','fi') and the loader's
          `Descaled.channels` says ('fi','national','wh'): the exporter orders by first
          appearance in the opportunity file, the loader by first appearance in the node
          column, and a zip missing a channel separates the two.
ARTIFACT  verify_channels.py fmt
CAVEATS   Only order diverges. `fine_split`, `aggregate` and `project` read membership, so
          nothing computed here moves; `write_v2` emits its columns in `channels_of` order,
          so a v2 -> v2 rewrite would reorder columns. The live working tree already carries
          an uncommitted fix in `td/instance.py` (honour `meta["channels"]` when it names the
          same set), and the probe passes against it.
```

## Item 2: `fine_split`

```
CLAIM     Ratios by the zip's WH:FI mass, state-ratio then 50/50 fallback, reported in meta;
          M, S, S_free conserved; a zip with wh + fi = 0 and no national mass is not reported.
ATTACK    A hand instance firing both fallbacks plus a fourth zip with no mass at all; a
          state whose ratio comes from one other zip; the 3,713-zip synthetic instance; a
          format-1 instance with no channels; a v2 file carrying only wh and fi.
VERDICT   DEFECT on the channel-less input. Everything the spec states is CONFIRMED.
BASIS     zA splits 75/25 from its own 30:10 and the same ratio hits the book and the filler
          exactly; zB takes MA's 3:1; zC takes 50/50; the report is exactly
          {zB: state, zC: even} and the zero-mass zD is absent from it. On the synthetic
          instance conservation of M, S and S_free is 2.22e-16 relative over 3,713 zips and
          no fallback fires. A file with only wh and fi splits to N_WH = N_FI = 0.
          DEFECT: `fine_split(d)` on a format-1 `Descaled` (`d.channels == ()`) passes the
          guard at channels.py:162 (`unknown = []` because there is nothing to be unknown),
          reads `M_c` as `{}` everywhere and returns an instance labelled with the four fine
          channels carrying zero mass: 21.29 units of input mass became 0.0. Downstream
          `aggregate` then returns an all-zero cell table and level 0 would plan on nothing.
          Failing input: `channels.fine_split(instance.load_descaled(<any format-1 file>))`.
          Fix, one line at channels.py:162: raise unless `have` is non-empty and contains
          "national" (`if not have or "national" not in have: raise ValueError(...)`).
          Reachability: the shipped driver is safe. `tools/full_plan.py:593` raises
          "carries one channel; pass --synthesize or give a format-2 file" before it reaches
          `fine_split` at 596-597, so no CLI path plans on zero mass. The gap is in the
          library entry point named in the interface contract (B1), which any other caller
          reaches: a notebook, the wave-3 app code, or a verify script.
ARTIFACT  verify_channels.py fine
CAVEATS   The state fallback aggregates over the whole file's zips of that state, which is
          what decision 3 says; no probe distinguishes "the state's ratio before the split"
          from "after", because the split does not move wh or fi mass.
```

## Item 3: `synthesize_channels`

```
CLAIM     The national cell equals the input exactly; per-cell headroom holds wherever it
          held; hashlib not hash(); deterministic.
ATTACK    Float equality (not tolerance) on M, every S_i and S_free of the national cell; a
          zip constructed to sit exactly on the headroom floor, then headroom re-checked per
          channel at tol = 0; the same fingerprint computed in three subprocesses at
          PYTHONHASHSEED 0, 1 and 12345; the shipped synthetic instance re-derived from the
          confidential hub instance at the seed recorded in its own meta.
VERDICT   CONFIRMED.
BASIS     National cell bit for bit on a random fixture and on all 3,713 zips of the hub
          instance. Per-cell headroom survives the exact-floor zip at tol = 0, and the
          shipped file has 0 violations in each of national, wh, fi at the rounded-file tier
          (5e-5). Three subprocesses at different hash seeds produce one identical
          fingerprint over 100 draws; 1,000 draws all lie in [0.15, 0.55]. The shipped
          synthetic instance reproduces from the hub file at seed 0 to 4.76e-06 relative
          (the write tier) and its national cells equal the hub's M at 0.00e+00. Totals are
          the cell sums to 2.22e-16 and `instance.check_descaled` is clean.
ARTIFACT  verify_channels.py synth ; verify_channels.py hub
CAVEATS   One caveat that is a format limit, not a defect of this function: a cell with
          positive book and zero mass loses its book on `write_v2` (and on `write_v1`),
          because the share form cannot express book against M = 0. Per-cell headroom rules
          that data out, and the exporter's `validate` enforces headroom per cell, but
          nothing inside channels.py does; a hand-built instance can lose book silently.
          The hub instance was read in process; no value was printed or copied.
```

## Item 4: `aggregate`, `slot_weights`, `project`

```
CLAIM     Aggregation and slot weights are the hand sums; `project(d, B)` gives the bundle
          sums with `cand` recomputed by the loader's rule, induced edges, a `states` filter,
          and `write_v1` of a projection reloads with identical attributes.
ATTACK    A dict-based recomputation of the whole (rep, state, channel) tensor with no numpy;
          a bundle name against a bare channel tuple; a rep listed with a zero book; a zip
          with no mass in the bundle sitting between two that have mass; an empty bundle; a
          repeated channel; `channels.STATE_LIST` against `tools/borders_report._STATE_LIST`
          element by element (the list the committed anchors and centres index).
VERDICT   CONFIRMED.
BASIS     `aggregate` equals the dict sum exactly (0.00e+00); the channel axis is in CHANNELS
          order; reps are every rep in the file, sorted. `slot_weights` matches the hand sum
          for six slots including bundle names and bare tuples, refuses an absent channel and
          returns (S, 0) on no slots. `project` matches the bundle sums to 0.00e+00 for all
          seven bundles; N + WH + FI restores every zip's total; on the 3,713-zip instance
          `project("N")` keeps every zip and every edge. Node classes, node set, edges,
          `cand` and `state` survive `write_v1` -> `load_descaled` exactly, M and S at
          2.67e-06 relative (the write tier); `meta["bundle"]` survives. A rep with zero book
          is dropped from `cand` and the reloaded file agrees, so the seam is self-consistent.
          A zero-mass zip stays a vertex and the projected graph stays connected.
          `STATE_LIST` equals `borders_report._STATE_LIST` element for element (49 entries,
          no difference).
ARTIFACT  verify_channels.py agg proj
CAVEATS   `project(d, ())` returns an all-zero instance and `project(d, ("WH","WH"))` doubles
          the mass; `BUNDLES` never produces either, so these are caller contracts, recorded
          rather than filed. The tolerance on the write seam is the six-figure rounding tier,
          not bit identity; nothing in the drivers reads more than six figures.
```

## Item 5: the decomposition's clause (a) with the real projection

```
CLAIM     `channel.gain_matrix` on `project(d, B)` equals `state_gain_matrix` on an integral
          whole-state plan at 1e-9, and the sum over bundles of projected gain matrices
          equals the cell-level gain, for all three filler_capture values.
ATTACK    The math-verify artifact's (a) block re-run with `channels.project` substituted for
          its private `_projected_graph`, over the three business plans of section 1
          ({N, WH, FI}, {N, WHFI}, {WH+, FI+}) plus {WHFI+}, each with 12 parameter settings
          (3 filler_capture x 4 (theta, lam) including the degenerate (0, 0) and (1, 0.99));
          one global rep order on every call, including a rep that holds book nowhere. Then
          the state-grain identity over all seven bundles and three filler_capture values,
          and once at full size (3,713 zips, 113 reps).
VERDICT   CONFIRMED.
BASIS     Cell-level gain equals the sum of `channels.project` gains at worst 3.96e-16
          relative over the four plans x 12 settings. `state_gain_matrix` equals
          `channel.gain_matrix` on the projection at worst 2.13e-14 absolute over 7 bundles
          x 3 filler_capture, and 3.11e-15 relative on the full-size instance (WHFI over
          every state). A half state share is exactly half that state's contribution, which
          is the mass-proportional approximation the doc claims for split states.
ARTIFACT  verify_channels.py decomp
CAVEATS   The sum-over-bundles identity is checked on plans that partition C, which is what
          section 3 requires of pi(z); overlapping bundles are the level-0 cover row's job
          and were shown load bearing by math-verify, not re-checked here. Clauses (b), (c)
          and (d) are math-verify's, not re-run.
```

## Item 6: the two requirements from math-verify

```
CLAIM     (i) `state_gain_matrix` and any per-bundle `gain_matrix` call use one global rep
          order so blocks stack. (ii) candidacy goes through a penalty assignment, never
          `channel.match` with zeroed gains, and nothing is ever released.
ATTACK    (i) compare `aggregate`'s rep list, `state_gain_matrix`'s default and
          `model.reps(project(d, B).G, ...)`; ask for a permuted order and check the rows
          permute and nothing else; build a rep whose book lives in one channel only.
          (ii) brute force over every injection restricted to the mask, maximum cardinality
          first then maximum sum log g, on 300 random masks with gains on both sides of 1,
          plus 200 under the utilitarian criterion; compare the penalty formula term for term
          with `tools/staff.py:128`; check the cell table's arrays and every rep's utility
          before and after a `candidacy=True` run; then a plan that fails Hall's condition,
          two used slots whose only book-holding rep is the same one.
VERDICT   (i) CONFIRMED for the code under test, with a hazard for future callers.
          (ii) CONFIRMED for the mechanism, DEFECT in the staffability guard.
BASIS     (i) `aggregate`'s reps are every rep in the file, sorted, and that is
          `state_gain_matrix`'s default, so the state side is globally ordered by
          construction; a permuted request permutes rows and only rows; `state_utilities`
          keeps T over every rep under a rep subset (a rep left out still holds its book).
          Hazard: nothing in the owned files calls `channel.gain_matrix`, and a caller that
          leaves it on its default gets `model.reps`, which returns NODE order, not sorted
          order: on the probe fixture the projection's own list is ['R2','R0','R1'] against
          the global ['R0','R1','R2'], with the same rep set, so stacked blocks would be
          silently mis-rowed. The rep SET also differs per bundle ({'N': ('R0',),
          'FI': ('R9',)}). Scanned at the pinned commit: `tools/full_plan.py` (which landed
          mid-verification, at `9956e9d`) and `td/solvers/level0.py` contain no `gain_matrix`
          call at all; the driver uses `channels.project` only, to write the per-bundle
          instances. The requirement lands on whoever writes the global stage 2 in wave 3.
          (ii) `stage2_state.py` never mentions `release_reps`; the penalty is
          `pen = hi + (min(g.shape) + 1) * (hi - lo + 1.0)`, term for term `tools/staff.py`'s
          `assign`; `_match_masked` equals the brute-force optimum on all 500 random masks
          (0 mismatches, worst value gap 0.00e+00); `candidacy=True` mutates no array of the
          cell table and leaves every gain and utility bit identical, so `S_free` is untouched
          and trap 20 is respected; the restriction never raises the Nash value.
          DEFECT: `_check_staffable` (stage2_state.py:164) tests each column separately, so a
          plan failing Hall's condition passes it. Failing input: two used slots, one over
          (AZ, WH) and one over (CA, FI), where R0 is the only rep with book in either.
          `state_stage2(..., candidacy=True)` returns without raising, `assignment` is
          {1: 'R0'}, `unstaffed_districts` is [0] and `value` is 1.1314, the sum of logs over
          one of the two slots. Section 3's `reps` row says every district is staffed, and
          route R compares plans by this `value`, so a plan that cannot be staffed scores as
          if it had fewer slots. Fix: after the match, when `candidacy` is on, raise (or
          report a `staffed` flag) when `len(pairs) < len(slot_ids)`; the per-column guard
          alone cannot detect it.
ARTIFACT  verify_channels.py req1 req2
CAVEATS   The unstaffed slot IS reported in `unstaffed_districts`, so a caller that reads
          more than `value` can see it; the same silence exists with `candidacy=False`
          whenever reps < slots, which is open item C, not this code's doing. Reachability:
          all three `state_stage2` call sites in the driver pass `candidacy=False`
          (`full_plan.py:474, 481, 745`), so D2 is latent today and fires the first time
          route R is scored with candidacy on, which is what the requirement-2 mechanism
          exists for.
```

## Item 7: `model.coefficients`

```
CLAIM     Identical values to the pre-refactor block for every filler_capture; validation
          message unchanged.
ATTACK    Transcribe the block from `git show main:td/model.py` (146-149), which is the same
          text as `main:td/channel.py` (268-271), and compare floats bit for bit over 15
          parameter settings; compare the ValueError strings; recompute `model.utilities` and
          `channel.gain_matrix` from the hand formula on a random instance.
VERDICT   CONFIRMED.
BASIS     Bit-identical `(c1, c2, c_free)` on 5 (theta, lam) pairs x 3 filler_capture values.
          The message is `filler_capture 'nonsense' not in ('theta', 'full', 'opportunity')`
          from both. `model.utilities` matches the hand formula with `np.array_equal` and
          `channel.gain_matrix` to 1e-12 for all three filler_capture values. The diff
          against `main` touches nothing but the two extractions.
ARTIFACT  verify_channels.py coef
CAVEATS   Bit identity is asserted for the coefficients, not for downstream sums, where the
          accumulation order is unchanged anyway (the diff moved no arithmetic).
```

## Item 8: tests that pass for the wrong reason

```
CLAIM     The shipped tests catch the properties they name.
ATTACK    Five targeted mutations of the modules under test, each imported in place of the
          real module, with the shipped test module run against it in process.
VERDICT   DEFECT, one mutation survives; three weak tests named.
BASIS     Caught: `write_v2` pricing share against the ZIP's m_rel instead of the CELL's
          (test_write_v2_payload, test_write_v2_round_trip); `project` keeping every rep in
          `cand` (test_project_recomputes_cand_and_the_node_classes); `fine_split` using the
          FI:WH ratio (test_fine_split_uses_the_zips_own_ratio); `state_gain_matrix` pricing
          unused slots (three tests). NOT caught: replacing the candidacy penalty with
          `pen = hi + 1e-9`, small enough that a swap of allowed cells can outbid a forbidden
          one. `tests/test_stage2_state.py` passes in full, because
          test_candidacy_masks_the_rep_with_no_book has a forced assignment where any penalty
          works. Weak tests, all passing for a weaker reason than they read:
          test_write_v2_round_trip compares totals only, so a permutation of the channel
          labels inside a zip would pass (the live working tree adds
          test_write_v2_round_trips_into_the_same_cells, which closes this);
          test_fine_split_conserves_totals asserts `b["M"] == a["M"]`, which holds because
          the attribute dict is copied, not because anything was conserved (its `M_c` sum
          line is the real check); test_state_gain_matches_channel_gain_matrix covers
          filler_capture "theta" only (this report covers all three); and two tests return
          silently instead of failing when an import is missing
          (test_write_v2_round_trip's `hasattr(instance, "FORMAT_V2")` guard and
          test_state_gain_matches_channel_gain_matrix's `try: from td import channels`),
          which the runner reports as a pass. Both guards are stale now that A1 and B1 have
          landed and should go.
ARTIFACT  verify_channels.py mut
CAVEATS   Five mutations is not a mutation score; they were chosen at the claims this report
          verifies. The mutation runner imports the test module in process, so a test relying
          on runner state would behave differently there (none does: both modules pass
          unmutated under it).
```

## Mechanical gates

- `.venv/bin/python3 tests/run_all.py` in the live worktree: **636 passed, 0 failed, 0 skipped**
  (tree dirty with another agent's uncommitted edits). On the pinned `9956e9d` snapshot: 633
  passed, 1 failed, and that failure is
  `test_centers.py::test_assign_default_path_matches_git_head`, which shells out to `git show`
  and cannot work in a snapshot that is not a git repository. Not a code failure.
- `uvx pyright --pythonpath /Users/ntlee/projects/td/.venv/bin/python3 td/channels.py
  td/stage2_state.py`: **0 errors, 0 warnings** on both the live tree and the pinned snapshot
  (pyright 1.1.413). Without `--pythonpath` it reports three unresolved-import errors for
  numpy, networkx and scipy; that is the interpreter, not the code.
- The unit's own acceptance command is the suite; there is no separate one in the brief.

## Defects, in one line each

- **D1** (item 2, `channels.py:162`). `fine_split` accepts a format-1 instance
  (`channels == ()`) and returns a silently zeroed fine-label instance; guard on a non-empty
  `have` containing `national`. Not reachable from the CLI (`full_plan.py:593` refuses first);
  reachable from every other caller of the contract's entry point.
- **D2** (item 6, `stage2_state.py:164`). `_check_staffable` is per column, so a plan failing
  Hall's condition returns unstaffed slots and a `value` summed over fewer slots without
  raising; check `len(pairs) < len(slot_ids)` after the match under `candidacy`. Latent today,
  since the driver passes `candidacy=False` everywhere; fix before route R uses candidacy.
- **D3** (item 1, exporter and loader). `meta["channels"]` (opportunity-file order) and
  `Descaled.channels` (node-column order) disagree when a zip is missing a channel; values are
  unaffected. Already fixed, uncommitted, in the live `td/instance.py`.
- **T1** (item 8, test gap). Shrinking the candidacy penalty to `hi + 1e-9` leaves
  `tests/test_stage2_state.py` green; the mask test's assignment is forced. Add a case where a
  forbidden cell would win on cost.

Two caveats worth keeping: a zero-mass cell with positive book loses that book on `write_v2`
and `write_v1` (the share form cannot express it, and only the exporter's per-cell `validate`
rules it out), and `project` carries no rep order, so any future per-bundle
`channel.gain_matrix` call must be passed `aggregate(d).reps` or its rows will not stack.
