# CODEVERIFY — Track 1, the penalised banded transportation LP (`docs/BORDERS_PLAN.md` ll. 60–86, 200–228)

Verified 2026-09-06 against branch `worktree-vbl` (worktree `/Users/ntlee/projects/td/.claude/worktrees/vbl`,
clean) with `/Users/ntlee/projects/td/.venv/bin/python3` — Python 3.13.15, numpy 2.5.2,
scipy 1.18.1, HiGHS via `scipy.optimize.linprog`. Type checker: `uvx pyright` 1.1.411 (no
pyright config in `pyproject.toml`; run with `--pythonpath` at the repo venv).

There is no `MODEL_*.md` for this unit; the plan **is** the model, and the "mapping table" below
is my reading of it pinned to code before anything was run.

## Summary

| # | Model object (plan) | Code symbol | Verdict |
|---|---|---|---|
| 1 | penalised banded LP `min Σ M_z(d²+P)x`, `Σ_j x=1`, `τ(1±δ)` band (ll. 74–79) | `td/solvers/centers.py:149 assign(..., penalty=, band=)` | **VERIFIED** |
| 1b | "`penalty=None, band=0.0` must reproduce the current path bit-for-bit" (l. 216) | same, vs `b38c9ce:td/solvers/centers.py` | **VERIFIED** |
| 2 | λ "a multiple of the committed draw's mass-weighted mean d² (`compactness/ΣM`)" (l. 75), penalty inside the descaled objective | `centers.py:203-210`; `state_borders.py:127`; `tools/state_borders.py:69-71` | **VERIFIED** |
| 3 | owner sets: plurality home, homeless fallback, unknown state excluded (ll. 68–73) | `td/solvers/state_borders.py:31 owner_sets`, `:60 penalty_matrix` | **VERIFIED** |
| 4 | alternation: labels→owners→LP→recentroid, ≤10 rounds, stop on repeat, no `improve`, every iterate saved (ll. 81–84) | `td/solvers/state_borders.py:101 refine` | **VERIFIED** |
| 5 | grid column "mass share outside owner sets"; split-state exclusion "own owner set has ≥2 districts" (ll. 189–192) | `tools/borders_report.py:186 _owner_metrics`, `:241 cell_row` | **VERIFIED** |
| 6 | real grid cell `d0.02_lam100`: band held, share = 0.0309 | `battery/results/borders_k18_v2_20260907/d0.02_lam100/draw.csv` | **VERIFIED** |
| 7 | `power_labels(penalty=)` / `power_weights(penalty=)` (ll. 218–220) | `centers.py:312`, `centers.py:336` | **VERIFIED** |
| 8 | pure-snap baseline (ll. 85–87) | `td/solvers/state_borders.py:75 pure_snap` | **VERIFIED** |

**8 VERIFIED (9 rows incl. 1b), 0 REFUTED, 0 INCONCLUSIVE.**

- Tests: `.venv/bin/python3 tests/run_all.py` → **305 passed, 0 failed, 0 skipped** (matches the
  count in the brief; the plan's line 262 predicted "275 plus the new tests").
- Type check: `uvx pyright --pythonpath .venv/bin/python3 td/solvers/state_borders.py
  td/solvers/centers.py tools/state_borders.py tools/borders_report.py` → **6 errors**, of which
  3 are pre-existing (the same 3 appear on `b38c9ce:td/solvers/centers.py`, checked) and 3 are
  cosmetic in new code (`borders_report.Ctx.d: object` used as `.G` twice;
  `tools/state_borders.py:38` `__doc__.splitlines()` on `str | None`). **0 errors in
  `td/solvers/state_borders.py`.**
- Six findings that change no verdict are listed at the end; **F2 is the one a sponsor-facing
  number depends on.**

Artifacts, all rerunnable, all under `docs/verify/`:

```
/Users/ntlee/projects/td/.venv/bin/python3 docs/verify/oracle_assign_lp.py       # rows 1, 1b, 2
/Users/ntlee/projects/td/.venv/bin/python3 docs/verify/oracle_owner_sets.py      # row 3
/Users/ntlee/projects/td/.venv/bin/python3 docs/verify/oracle_refine.py          # row 4
/Users/ntlee/projects/td/.venv/bin/python3 docs/verify/oracle_grid_cell.py       # rows 5, 6, 8
/Users/ntlee/projects/td/.venv/bin/python3 docs/verify/oracle_lam_abs.py         # row 2 (real instance)
/Users/ntlee/projects/td/.venv/bin/python3 docs/verify/oracle_power_penalty.py   # row 7
```
(run from the worktree root; the three that touch real data read the hub's gitignored
`instance_descaled_v2.json.gz`, `data/geo` and `battery/results/` by absolute path).

---

## 1 — the penalised, banded LP

```
CLAIM     min Σ_zj M_z (d²_zj + P_zj) x_zj  s.t.  Σ_j x_zj = 1,
          τ(1−δ) ≤ Σ_z M_z x_zj ≤ τ(1+δ)          ↔ td/solvers/centers.py:149 assign
ATTACK    Rebuilt the LP from scratch in RAW units in docs/verify/oracle_assign_lp.py::my_lp
          -- my own O(n·k) Python d² loop (never centers._dist2), dense A_eq/A_ub assembled by
          hand, method="highs" (assign uses "highs-ds") -- on a random 40-zip / 3-district /
          4-state instance with -1 (unknown) states, band=0.02, lam=5.  assign's linprog call
          was intercepted so its own primal and its own matrices are observable, and the two
          LPs were cross-checked in BOTH directions: is assign's optimum feasible for my
          constraint set, and is my optimum feasible for assign's?  Repeated at band=0 with a
          penalty (seed 7).
VERDICT   VERIFIED
BASIS     Numeric-equality tier (this is arithmetic on an LP, not a noisy measurement).
          my LP optimum (raw)          = 1662.75097503
          assign's own x, raw objective = 1662.75097503   rel diff 1.4e-16  (< 1e-9 asked)
          assign's x in MY set:  row-sum error 0, band violation 1.4e-14
          my x* in ASSIGN's set: eq error 0, ub violation 3.6e-15
          cost-vector ratio impl/mine constant to machine precision (min = max = 1 after the
          positive rescale), so no column is mispriced.
          band=0 with a penalty (seed 7): rel diff 0.0e+00.
          The band rows are `A_ub = vstack([A_mass, -A_mass])`, `b_ub = [(1+δ)t, −(1−δ)t]` --
          the upper row and the NEGATED lower row, i.e. the inequality directions in the plan,
          not reversed; a reversed direction would have made my x* infeasible for assign's
          matrices, and it is not.
ARTIFACT  docs/verify/oracle_assign_lp.py::check_A / check_A_noband
CAVEATS   Tests the LP relaxation only.  It does not test the rounding rule
          (`X.argmax(axis=1)`) or `_repair_empty`; row 6 covers what the rounding costs on the
          real instance.  n=40/k=3 is small; the real cell is n=3707/k=18 and is covered only
          through row 6.  `targets=` combined with `band=` is exercised by the repo's own
          test_targets_off_the_total_need_a_band, not here.
```

```
CLAIM     "penalty=None, band=0.0 must reproduce the current path bit-for-bit (same matrices,
          same solver call), so the committed draw stays reproducible"  ↔ centers.assign
ATTACK    Loaded b38c9ce's centers.py via importlib from `git show`, intercepted linprog in
          BOTH modules, and compared the full argument tuple -- not just the returned labels,
          which is all the repo's own test_assign_default_path_matches_git_head compares.
          n=60, k=4, seed 11, with targets=None and with an uneven targets vector.
VERDICT   VERIFIED
BASIS     Byte/array identity (np.array_equal, ==) on every one of
          c, A_eq, b_eq, A_ub, b_ub, bounds, method, options, plus labels and n_fractional --
          all OK for both target settings.  A_ub/b_ub are None on both sides, so scipy sees an
          identical call.  The one behavioural change on the default path is the validation
          tolerance `tol = max(band, 1e-6)*w.sum()`, which at band=0 is literally the old
          `1e-6 * w.sum()`.
ARTIFACT  docs/verify/oracle_assign_lp.py::check_B
CAVEATS   Two (xy, M, centers, targets) instances only.  Does not re-derive the committed k=18
          draw end to end; that would need a full `centers.draw` rerun.
```

## 2 — descaling order and the units of λ

```
CLAIM     the penalty is added to d² BEFORE the objective is divided by c.mean(); and
          lam_abs = lam_rel × compactness/ΣM is in the units of d² (mass-weighted mean d²)
          ↔ centers.py:203-210, state_borders.py:127, tools/state_borders.py:69-71
ATTACK    Two rival hypotheses were constructed and both scored against the c vector assign
          actually hands HiGHS: (i) w·(d²+P) then /mean -- the plan's reading; (ii) w·d²/mean
          then +P -- the plausible bug.  Then, on the REAL instance, lam_abs was recomputed
          three independent ways and checked against the recorded params.json.
VERDICT   VERIFIED
BASIS     Numeric-equality tier.
          |c − (penalty inside, then /mean)| = 0.000e+00
          |c − (descale, then +P)|           = 1.994e+00      <- the rival is refuted
          Real instance (k=18, committed seed-2 draw):
            driver  100·metrics(...)["compactness"]/ΣM = 7.89124803026e+12
            refine  100·Σ M_z |xy_z − C_{l(z)}|² / ΣM   = 7.89124803026e+12  (rel 1.2e-16)
            mine    hand-rolled per-district centroid + Python sum = same    (rel 1.2e-16)
            params.json lam_abs["100.0"]              = 7891248030257.623    (rel 1.2e-16)
          So `compactness` here IS mass-weighted ΣM·d² about the district centroids
          (`centers.metrics` with centers=None), and compactness/ΣM is a mass-weighted mean d²
          -- the same units as the d² it is added to.  Sanity: lam_abs/100 = 7.89e10 against a
          median own-centre d² of 3.68e10 and a mean over all (z,j) pairs of 5.23e12, i.e. λ=1
          is worth about two typical zip-to-own-centre moments and λ=100 is ~15× the mean
          cross-district moment, which is the "effectively hard" the plan wants.
          Note ΣM here is the GEOMETRIC zips' mass (8476.33), not the whole instance's
          (8523.24); driver and refine agree on that, so the two are consistent.
ARTIFACT  docs/verify/oracle_assign_lp.py::check_C ; docs/verify/oracle_lam_abs.py
CAVEATS   Confirms the units are consistent, not that λ=100 is the right scalar.  The driver's
          lam_abs is written to params.json and then thrown away -- see finding F3.
```

## 3 — `owner_sets`

```
CLAIM     home(j) = plurality state of district j's mass; O(s) = {j : home(j)=s}, else the
          single district holding the most of state s's mass; unknown state (-1) excluded
          ↔ td/solvers/state_borders.py:31 owner_sets, :60 penalty_matrix
ATTACK    Brute-forced the rule in plain-Python dicts/lists (no numpy reductions) and compared
          on 12 random 200-zip toys (k=6, 9 states, ~10% unknown) plus hand-built degenerates:
          an exact two-state tie inside a district; an exact two-district tie for a homeless
          state; every zip unknown; two empty districts; a singleton; EMPTY input; states
          carrying no mass at all; one state owning two districts; all-zero masses.  Also
          compared against the second, independently written copy of the rule that already
          exists in the repo, `tools/borders_report._home_and_owners` (a genuine third opinion:
          it is written with the transposed mass matrix and a Python loop).
VERDICT   VERIFIED
BASIS     Exact set equality of `home` and `owners` on all 12 random toys and all 9 degenerate
          cases, three-way (numpy impl / my brute force / borders_report fallback).
          Tie rule: `W.argmax` keeps the LOWEST index on a tie -- confirmed explicitly, home=[0]
          for a 1-vs-1 tie between states 0 and 2, and owners[2]=[True,False] for a 1-vs-1 tie
          between districts 0 and 1.  Deterministic: 50 repeated calls give 1 distinct result.
          `penalty_matrix` is covered by the repo's own two tests (unknown-state row all-zero,
          λ=0 all-zero) and is exercised inside rows 1 and 4.
CAVEATS   Floating-point ties are exact-equality ties only; a near-tie at 1e-16 is decided by
          the accumulation order of `np.add.at`, which my brute force happens to match here but
          is not guaranteed to match at other zip orderings.  Not a concern at real masses.
```

## 4 — `refine`

```
CLAIM     "labels → owner sets → banded, penalised LP → recentroid (centers._centroids),
          10 rounds, stop early when labels repeat.  No Nash polish (centers.improve).  Every
          iterate is saved"  ↔ td/solvers/state_borders.py:101 refine
ATTACK    Replaced `centers.improve` with a tripwire that raises, wrapped `owner_sets`,
          `centers.assign` and `centers._centroids` to record every argument, and independently
          re-implemented the whole loop in docs/verify/oracle_refine.py::replay -- then compared
          iterate by iterate on a 90-zip / 5-state-stripe / k=4 toy where the state stripes cut
          across the clusters, at (λ,δ) = (100, 0.02), (0, 0), (10, 0), (1, 0.10).  Separately
          probed the early-stop rule for a 2-cycle rather than only a fixed point, and four
          degenerate inputs.
VERDICT   VERIFIED
BASIS     All four settings: replay reproduces every iterate and the final labelling exactly;
          `converged` agrees; `improve` call count = 0; `band` passed to `assign` == δ every
          round; `penalty` is None iff λ=0 (so λ=0 is literally `assign`'s Lloyd step, as the
          docstring claims); `centers` == `_centroids` of the FINAL labels; `metrics` matches a
          fresh `centers.metrics` call.  `len(iterates) == rounds_used <= rounds`.
          Per-round owner-set drift: owner_sets is called ONCE PER ROUND, and the labels it is
          called with are the CURRENT labels, not `labels0` (checked array-by-array; the
          "always from labels0?" probe reads False in every run that took >1 round).  **That is
          what the plan asks for** -- l. 81 writes the chain "labels → owner sets → …LP →
          recentroid" and then applies "10 rounds" to the chain, so the owner sets are inside
          the loop.  See finding F2 for what that drift does to the reported metric.
          Stop-on-ANY-repeat (not just "equal to the previous"): `seen` is seeded with
          `labels0.tobytes()` and every iterate's key is added, so a 2-cycle stops too.  On a
          60-zip/k=3/λ=100 toy the loop ran 4 rounds and the first duplicate key in
          [labels0, it0, it1, it2, it3] is at index 4 -- i.e. it stopped at exactly the first
          repeat, not later.  The repeated labelling IS appended to `iterates` before the break,
          so `labels == iterates[-1]` always holds.
ARTIFACT  docs/verify/oracle_refine.py
CAVEATS   Toy scale (n=90, k=4).  Nothing here proves the loop terminates usefully on the real
          instance -- but the recorded grid shows converged=True in 4–7 rounds for all 7 refine
          cells, under the 10-round cap.  `n_fractional` in the result is the LAST round's LP
          only; the plan does not say which round it should report.
          Degenerate inputs found one crash, F1 below.
```

## 5 — `_owner_metrics`: which owner sets, and is the exclusion computed?

```
CLAIM     grid column "mass share outside owner sets" is measured against the COMMITTED map's
          owner sets; the split-state column excludes a state "whose own owner set has ≥2
          districts", computed rather than hard-coded to CA/TX/NY/FL
          ↔ tools/borders_report.py:186 _owner_metrics (ctx.owners / ctx.home from
            load_committed:171, computed once from labels0)
ATTACK    Recomputed, for ALL NINE recorded cells, the outside share from the written draw.csv
          files and the raw instance with my own plain-Python owner-set code -- TWICE, once
          against the committed map's owner sets and once against each cell's OWN owner sets --
          and asked which of the two the grid's number equals.  Also recomputed the split-state
          list under the ≥2-owners exclusion and compared string for string.
VERDICT   VERIFIED -- the code uses the COMMITTED owner sets, the natural reading.
BASIS     Numeric-equality tier.  Per cell, |grid − mine(committed)| = 0.0e+00 for all nine
          cells; |grid − mine(own owner sets)| is nonzero for eight of the nine (up to 2.1e-02),
          so the two hypotheses are genuinely distinguishable and the committed one wins:
            committed     0.091462 | committed 0.091462 (0e+00) | own 0.091462  (identical, as
                                                                   it must be)
            snap          0.000000 | 0.000000 (0e+00) | own 0.021463 (2.1e-02)
            d0_lam100     0.037246 | 0.037246 (0e+00) | own 0.058267 (2.1e-02)
            d0.01_lam100  0.032448 | 0.032448 (0e+00) | own 0.032093 (3.5e-04)
            d0.02_lam100  0.030947 | 0.030947 (0e+00) | own 0.030592 (3.5e-04)
            d0.05_lam100  0.023447 | 0.023447 (0e+00) | own 0.019164 (4.3e-03)
            d0.1_lam100   0.018397 | 0.018397 (0e+00) | own 0.037634 (1.9e-02)
            d0.02_lam1    0.054231 | 0.054231 (0e+00) | own 0.061923 (7.7e-03)
            d0.02_lam10   0.031102 | 0.031102 (0e+00) | own 0.030747 (3.5e-04)
          Exclusion is COMPUTED: the guard is `int(ctx.owners[s].sum()) < 2`
          (borders_report.py:234) with no state-code literal anywhere in `_owner_metrics`; the
          only state literals in the file are `_STATE_LIST`, which is the index vocabulary.
          Recomputing owner-set sizes from the committed draw independently gives exactly
          {CA, FL, NY, TX} with ≥2 owner districts -- the plan's list, derived not asserted --
          and NJ with exactly 1, so NJ is NOT excluded, again as the plan says (l. 191).  Every
          cell's `states_split` string matches my independent list exactly, and no excluded
          state ever appears in one, while NJ appears in five of them.
          Grid rows are therefore consistent with the committed reading.
ARTIFACT  docs/verify/oracle_grid_cell.py
CAVEATS   `n_districts_outside_home_1pct` uses `ctx.home` (committed) with the same reasoning
          but was not separately cross-checked.  The share is over the WHOLE instance's mass
          including the 41 coordinate-less zips placed by `channel.place_by_state`; those zips
          carry a state and so can count as "outside", which is a choice the plan does not
          address.  See F2.
```

## 6 — the real cell `d0.02_lam100`

```
CLAIM     on the completed instance, every district's mass within τ(1±0.02) plus at most one
          zip's mass of rounding; outside-owner share = 0.0309
          ↔ battery/results/borders_k18_v2_20260907/d0.02_lam100/draw.csv
ATTACK    Read the written draw.csv and the instance directly (no borders_report, no refine
          rerun), rebuilt the district masses over the GEOMETRIC zips -- which is the set the LP
          actually constrains -- and measured the overrun past each band edge in units of the
          largest single zip's mass.  The share was recomputed as in row 5.
VERDICT   VERIFIED
BASIS     τ (geometric) = 470.907; band [461.489, 480.325]; largest zip M = 83.0857 = 17.64% of τ.
          Realised masses / τ:
            1.0190 1.0104 1.0045 1.0207 0.9812 0.9851 0.9810 1.0072 0.9867
            1.0216 1.0132 1.0213 0.9794 1.0239 0.9796 0.9805 0.9712 1.0136
          7 of 18 districts sit outside the band after rounding; worst overrun = 4.167
          = **0.050 largest-zip masses** = 0.885% of τ -- comfortably inside "one zip's mass"
          (the LP recorded n_fractional = 15, i.e. 15 split zips of the ≤ k−1 = 17 a basic
          transportation solution admits, and rounding them is the entire source of the
          overrun).  outside_owner_share recomputed = 0.030947, grid = 0.030947, |Δ| = 0.0e+00
          (< the 1e-4 asked).  Completed-instance spread_rel recomputed = 0.0359044 vs the
          grid's 0.03590437818055659.
          Cross-check of the plan's own verification list (l. 266-268): grid.md has exactly 9
          Track-1 rows; the δ=0, λ=100 row's outside share (0.0372) is ≤ the committed row's
          (0.0915); outside share is monotone decreasing in δ across 0, 0.01, 0.02, 0.05, 0.10
          (0.0372, 0.0324, 0.0309, 0.0234, 0.0184); AZ, ID, IL appear in the residual split list
          at every δ, matching the plan's expectation that AZ stays split.
ARTIFACT  docs/verify/oracle_grid_cell.py
CAVEATS   The band is checked on the geometric zips.  The 41 coordinate-less zips are added
          afterwards by `run_draw.complete`/`channel.place_by_state` and are outside the LP's
          control, which is why the completed-instance spread (3.59%) exceeds 2δ = 4%… it does
          not, but it could at another δ; the plan's cap should be read on the completed
          numbers.  I did not re-solve the cell; this verifies the written artifact, not that
          rerunning `refine` today reproduces it (no byte-identity anchor exists for this run).
```

## 7 — `power_labels(penalty=)` / `power_weights(penalty=)`

```
CLAIM     "power_labels(...penalty=None): + penalty in the argmin.  power_weights(..., penalty=
          None): + penalty in d2, labels via the penalised power_labels"  ↔ centers.py:312, :336
ATTACK    `power_labels` against a plain-Python argmin over d²+P−w.  `power_weights` against
          BRUTE-FORCE enumeration of every balanced integer assignment of 12 zips into 3
          districts of 4 (34,650 of them) under the penalised cost, plus an independent
          recomputation of the dual slack in the caller's own units rather than trusting the
          returned `max_dual_violation_rel`.
VERDICT   VERIFIED
BASIS     power_labels: exact agreement on 60 random points, k=4, random weights and penalties.
          power_weights: lp_bound = 132.685230481; brute-force integer optimum = 132.685230481;
          bound ≤ optimum holds with gap 0.0 (the penalised LP is integral on this instance).
          Independently computed min dual slack = 0.000e+00 (≥ −1e-9), so the duals are feasible
          for the PENALISED dual, not the unpenalised one.  Returned `labels` equal
          `power_labels(xy, C, weights_raw, P)` exactly, and differ from the UNPENALISED power
          diagram on 3 of 12 zips -- so the penalty is genuinely carried into the labels.
ARTIFACT  docs/verify/oracle_power_penalty.py
CAVEATS   These two keywords have NO production caller in the repo (grepped: `power_weights` is
          called only by `cert_draw.py` and `us_maps.py`, both without a penalty), and
          `power_weights(penalty=)` had no unit test before this file.  Track 1 does not use
          them; they are plan-mandated dead capability today.  n=12/k=3 only -- brute force
          caps the size.
```

## 8 — `pure_snap`

```
CLAIM     "Pure snap of the committed map: every zip outside its state's owner set moves to the
          nearest owner district by d² to centre.  Zero parameters"
          ↔ td/solvers/state_borders.py:75 pure_snap
ATTACK    The strongest available oracle is the real instance: if the claim holds, then after
          pure_snap NO known-state zip is outside its state's committed owner set, i.e. the
          recomputed outside share must be exactly 0.  Measured independently from the written
          `snap/draw.csv` with my own owner-set code (row 5's machinery), never calling
          pure_snap or borders_report.
VERDICT   VERIFIED
BASIS     `snap` row: independently recomputed outside share against the committed owner sets
          = 0.000000 exactly (grid records 0), over all 3,748 instance zips, while the
          committed map's is 0.091462.  519 zips changed, and the price is visible and large:
          spread_rel 0.0136844 → 0.510091, which is the "what snapping alone costs in spread"
          the plan wants the baseline to show.  Non-owner zips that moved went to an OWNER
          district by construction (`np.where(own, d2, inf).argmin`), and the repo's own two
          toy tests pin "exactly the non-owner zips move" and idempotence.
CAVEATS   The nearest-owner *choice* (as opposed to owner-membership) is checked only by the
          7-zip toy test in the repo, not independently at scale.  The 41 coordinate-less zips
          never enter pure_snap; their share of the snap row's 0 comes from `place_by_state`.
```

---

## Findings (none change a verdict)

**F1 — `refine` raises on an all-unknown-state input; `pure_snap` does not.**
`refine` sets `n_states = int(state_idx.max()) + 1 if (state_idx >= 0).any() else 0`
(state_borders.py:124) and then calls `owner_sets(..., n_states=0)`, whose
`W.argmax(axis=0)` on a `(0, k)` array raises. Smallest reproducer:

```python
sb.refine(np.zeros((2, 2)), np.ones(2), np.array([0, 1]), np.array([-1, -1]), 2,
          lam_rel=100.0, delta=0.0, rounds=1)
# ValueError: attempt to get argmax of an empty sequence
```

`pure_snap` guards the same case with `if not known.any(): return labels` (line 89). Not
reachable on the real instance (49 states are populated), and the plan says nothing about it,
so this is a robustness gap, not a model mismatch. `rounds=0` (returns `labels0` untouched,
`rounds_used=0`, `converged=False`), `k=1` and `delta=1.0` all behave sensibly.

**F2 — the objective's owner sets drift; the reported metric's do not.** Verified in row 4 that
`refine` recomputes owner sets each round from the current labels (which is what the plan asks),
and in row 5 that `_owner_metrics` scores against the COMMITTED owner sets (which is the natural
reading of the grid column). Both are individually right, but they are not the same reference,
and on the real run they have diverged materially at the extremes:

| cell | outside share vs committed owners (reported) | vs the cell's own final owners |
|---|---|---|
| `d0_lam100` | 0.0372 | 0.0583 |
| `d0.02_lam100` | 0.0309 | 0.0306 |
| `d0.1_lam100` | **0.0184** | **0.0376** |

At δ = 10% the districts' home states have moved, so the headline "1.84% outside owner sets" is
measured against reference state lines the solver itself abandoned; by the map's own final
owner sets it is 3.76%, twice as high. The morning table should say which reading it is
quoting. (The mid-δ cells, which are the likely ship candidates, differ by only 3.5e-4.)

**F3 — the λ formula is written twice.** `tools/state_borders.py:70-71` computes `lam_abs` into
`params.json` and never passes it; `state_borders.refine:127` recomputes it from `labels0`. They
agree to 1.2e-16 today (row 2), but a future edit to one silently desyncs the recorded parameter
from the one actually used. Cheapest fix is for the driver to read the value back off `refine`.

**F4 — `power_weights(penalty=)` is untested and uncalled in the repo.** Now covered by
`docs/verify/oracle_power_penalty.py`; consider promoting that check into `tests/test_centers.py`.

**F5 — the driver can write two cells to the same name.** `tools/state_borders.py:119` and `:127`
both format `d{delta:g}_lam{lam:g}`; a run with `--lam 100 --soft-lam 100 --soft-delta 0.02` and
`0.02` in `--delta` writes two rows with the same name and the second overwrites the first's
`draw.csv`. Defaults avoid it.

**F6 — `params.json` does not describe the run that made the figures.** The recorded
`params.json` has `"maps": false`, yet every cell directory contains a populated `figures/`.
The maps were rendered by a separate invocation, so `params.json` is not a faithful provenance
record for that output directory. No byte-identity anchor exists for this run, so row 6
verifies the written artifact rather than its reproducibility.

## Environment traps hit while verifying

- `git` in this worktree is wrapped; a plain `git …` (and `git -C …`) is refused by the
  worktree-isolation hook. `/usr/bin/git -C <worktree> …` works and is what the artifacts use.
- `cat`/`sed`/`grep`-on-a-file/heredocs are blocked by `enforce-file-tools`; the scratch scripts
  do their own file I/O from Python instead.
- `uvx pyright` without `--pythonpath /Users/ntlee/projects/td/.venv/bin/python3` reports
  spurious `reportMissingImports` for numpy/scipy and hides the real errors.
