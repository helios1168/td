---
name: td-verification-oracles
description: Oracles, anchors and environment traps for verifying td (national channel) research code — established verifying U7-meas 2026-09-03, U8-band 2026-09-04, U8-band v2 §10 2026-09-05, Track 1 state-border snapping 2026-09-06, Track 2 state-splits MILP 2026-09-07
metadata:
  type: project
---

Verifying `tools/`-level analysis code in the **td national-channel** repo: what worked as an
independent oracle, what serves as an anchor, and what bites in this environment.

**Why:** the project's numbers are all derived from one confidential descaled instance, so the
only honest oracles are *second implementations* over the same file, plus second solvers.
**How to apply:** reach for these first on any `docs/MODEL_*.md` ↔ code verification here.

**Oracles that worked (U7-meas, all reproduced the code to ≤1e-14):**
- Re-read `instance_descaled.json.gz` with plain `gzip`+`json` and rebuild `S_i(z) =
  share·m_rel`, `M = m_rel`, `S_free = share_free·m_rel` — never `td.instance`. Format key
  `td_instance_descaled/1`; `meta` carries `zips_contested`, `n_reps`, `graph_hash`.
- Assignment/matching: `scipy.optimize.linprog` on the assignment LP instead of
  `linear_sum_assignment` (polytope is integral; check max fractionality = 0).
- MILPs: **pyscipopt 6.2.1 (SCIP) is in the venv** — a genuinely different solver from
  scipy's HiGHS. `python-mip` 2.0.0 too. Use `limits/gap` and `limits/absgap` = 0.
- Max-k-coverage: a submodular depth-first B&B (bound = f(C) + top-`left` marginals) certifies
  the real 111-rep instance in 1 375 nodes / 0.1 s. Self-test it against
  `itertools.combinations` on random matrices first.
- Gains: recompute `g = Σ_z [c2·T + c_free·S_free + λ·M] + (1−λ)(1−θ)·S_i` by hand;
  `filler_capture="theta"` ⇒ `c_free = c2`.

**Oracles that worked (U8-band, 2026-09-04 — convex/EG programs):**
- **Proportional response dynamics** (Fisher market, budgets 1: `b_zi ← u_i(z)x_zi/g_i`,
  `x = b/Σ_i b`, dual `p_z = Σ_i b_zi`, upper bound `Σp − k + Σ_i log max_z u/p`) reproduces the
  unconstrained Eisenberg–Gale value on the real 1229×13 instance to 1e-10 in ~32k iterations,
  **with no solver at all**. The single best oracle for any `EG_S` number here.
- **Certificate-checking beats re-solving.** Treat the solver as untrusted: audit its `X`
  (x ≥ 0, row sums 1, band) yourself for a *lower* bound and evaluate the Lagrangian dual
  `D = Σp + Σ_i(log max_z u_i/q_zi − 1) + (T/k)[(1+δ)Σμ⁺ − (1−δ)Σμ⁻]`, `q = p + νM`, yourself
  for an *upper* one. Needs only `μ ≥ 0` and `q > 0`; gives a bracket independent of HiGHS.
- **Secant squeeze for shadow prices.** For a concave value function, solving at `a < δ₀ < b`
  brackets the whole superdifferential between the two secants — settles "is this slope a valid
  supergradient / how far from minimal" without running a minimisation LP.
- `scipy.optimize.minimize(method="SLSQP")` multi-start is a fine oracle for concave programs on
  toys (n·k ≤ 20 vars); agrees to 1e-9.
- KKT residuals from an OA loop are **O(√bracket)**, not O(bracket) — a 3e-9 objective bracket
  buys prices good to ~1e-5. Verify by sweeping the tolerance; do not read 1e-5 as a leak.

**Anchors that exist:** `figures/u8_band/frontier.png` is byte-identical on re-run (sha256
`c9d3777…`); check `git status figures/` is clean first. Otherwise no figure sha256 anchors for
`tools/measure`. The real anchors are
(a) byte-identity re-run of `battery/results/meas_*/**.json` modulo the `"written"` field, and
(b) each draw's `metrics.json` `winner.stage2_value` — recomputing `V` and matching it to 1e-9
proves the instance file, map, roster and (θ, λ, filler) are the ones that produced the draw,
which matters because `metrics.json` records an instance path in a *different* worktree.

**Environment traps:**
- A `wt/*` worktree has **no `.venv`** — use `/Users/ntlee/projects/td/.venv/bin/python3`
  (three levels up from the worktree, not two).
- Tests: `.venv/bin/python3 tests/run_all.py`, a custom runner (not pytest); 184 fast tests at
  `74eff38`, **237 at `9cfcc2c`** (2026-09-05). `tools/` is not a package: tests load scripts via
  `importlib.util.spec_from_file_location` and must register the module in `sys.modules` for
  `@dataclass` to resolve.
- In `.claude/worktrees/*`: `git` must be run as `/usr/bin/git -C <worktree>` (a hook refuses
  `rtk`/`caveman`-wrapped git); `grep`/`cat`/heredocs over files are blocked by
  `enforce-file-tools.sh`, so put helper scripts under `/tmp` with the **Write** tool and run
  them with the venv python. `battery/` is a **symlink** into the shared checkout, so Write
  refuses to create files there — use `docs/artifacts/<id>/` for durable artifacts.
- Type check: `uvx pyright --pythonpath /Users/ntlee/projects/td/.venv/bin/python3 <files>`
  (1.1.411 clean on the U7 files).
- `battery/results/` and `instance_descaled.json.gz` are gitignored; never write under
  `battery/figures/`. Never use Serena from a non-launch worktree.
- Known instance defects that do *not* block non-geometric numbers: 6 of 1 229 zips have no
  coordinates; 6-significant-figure export rounding makes ~69 zips miss the headroom
  inequality by a factor 1.0000006.

**Degeneracy is the recurring hazard on this instance (U8-band).** A **1e-16** perturbation of
`U` (different summation order) moves the selected LP vertex: `s_min` shifts 7e-6 relative,
split counts ±1, the tight-band count ±1 — while the value and the gains are stable to 1e-9.
Byte-identical re-runs still hold (identical input ⇒ identical output). Treat `p`, `ν`, `m`,
split sets and `t` as *one* optimum; only `φ` and `g*` are invariants.

**SCIP modelling on this problem:** the epigraph form with an auxiliary gain variable
(`g_i ≤ Σu·x`, `t_i ≤ log g_i`, `g_i` lower-bounded from the OA incumbent) solves k=13/n=1229 at
δ=0.33 in ~5 s; taking `log` of the 1229-term expression directly takes **380–430 s**. Trap 14's
recipe is load-bearing, not ceremonial. And **SCIP's `getDualbound()` is not rigorous at 1e-9**
on this program: at δ=0.05 it returned `optimal` with a bound 5.9e-9 *below* a certified-feasible
primal. Use it as a cross-check only; never let it replace an LP/weak-duality bound at tier 1.

**Oracles that worked (U8-band v2 §10, 2026-09-05 — reporting-fidelity verification):**
- **Re-run the gate only.** `frontier.resolve_draw_dir` → `read_draw` → `td.channel.stage2` →
  `frontier.build_setting` → `eg_band.solve_band(U, M, None)` takes ~40 s at k=18/n=3748 and
  reproduces the whole `gate` block **bit-for-bit**. Cheapest way to (a) prove a manifest is not
  stale and (b) recover quantities the manifest never stored (`sol.g` at the gate). Import is
  `from td import instance as descaled`; there is no `frontier.load_setting`.
- **Re-derive per-agent vectors from other stored vectors.** In a `draw_*.json` manifest,
  `g = prop_gap + u_total/k` then `Σ log g` must equal `points[i].primal` (holds to 1.5e-14);
  `Σ m == T` exactly; and counting masses on the band edge `tgt(1±δ)` at 1e-6 reproduces
  `vertex.n_tight_bands` exactly. Three cross-checks with no solver.
- **`districts` vs `staff` misalignment test.** Print what the *wrong* array would have given at
  the same indices and show the doc contains none of those labels. Corroborate with
  `vertex.tight_agents` (indices), which is independent of `nu`.

**Two upper bounds live in the same manifest — always ask which one a doc row uses.**
`points[i].upper` (the OA master's) and `certified_upper[i] = min(upper, dual_check.bound)`
(`frontier.py:131-135`) differ by 2–5e-9. `frontier.shape` uses `upper`; `softness.direct`,
`delta_star`, and the plot use `certified_upper`. §9/§10 tables print `upper`, §10.2 prints
`certified_upper`. Any claim at 1e-9 scale (e.g. "SCIP sits below the OA's bound") flips
depending on the field. State the field.

**Fields that are vacuous when a flag is absent.** `gate.matches_reference` is
`reference is None or …` and `gate.delta_upper` is `None if reference is None else
sol.upper - reference` (`frontier.py:246, 250`) — both degenerate when `--gate-reference` is
omitted, as on v2. Quoting `matches_reference = true` as a passed check, or reading a null
`delta_upper` as anything about the model, is a live failure mode in generated results sections.

**Oracles that worked (Track 1 state-border snapping, 2026-09-06 — LP + labelling code):**
- **Intercept `linprog` to make the solver call observable.** `centers.linprog = spy` (module
  attribute, restore in `finally`) records `(c, A_eq, b_eq, A_ub, b_ub, bounds, method,
  options)` and `res.x`. That turns "does `assign` build the model's LP" into two array
  comparisons, and it is the *only* way to check a "bit-for-bit / same matrices" claim — the
  repo's own git-head test only compares returned labels, which can agree by luck.
- **Two-directional LP comparison.** Rebuild the LP from scratch in RAW units with hand-built
  dense matrices, then check (a) the implementation's `x` is feasible for MY constraints and
  attains MY optimum, and (b) MY `x*` is feasible for the implementation's matrices. (a) alone
  misses over-constraining; (b) alone misses under-constraining. Caught nothing here but is
  cheap (n=40, k=3 solves instantly).
- **Score the rival hypothesis, not just the claim.** For "the penalty enters before the
  `/c.mean()` descale", compute both orderings and print both residuals: `0.0` vs `1.99`. A
  single residual of 0 does not show the alternative was distinguishable.
- **Ask a metric which reference it used by computing it both ways over every recorded cell.**
  `_owner_metrics` could score against the committed owner sets or the cell's own; recomputing
  both from the written `draw.csv` + instance gave `0.0e+00` vs committed for all 9 cells and
  up to `2.1e-02` vs own — so the reading is pinned, and the divergence itself is the finding.
- **Brute-force enumeration still fits.** Every balanced integer assignment of 12 zips into 3
  districts of 4 (34,650) certifies `power_weights`'s `lp_bound`; `itertools.combinations`.
- **Degenerate-input sweep is where the bugs are.** `refine` raises `ValueError: attempt to get
  argmax of an empty sequence` when every `state_idx` is `-1` (`n_states=0` ⇒ `(0,k)` argmax);
  `pure_snap` guards the same case. Unreachable on the real instance, but the sweep is 5 lines.

**Anchor note:** `battery/results/borders_k18_v2_20260907/params.json` records `"maps": false`
while every cell has a populated `figures/` — the maps came from a separate invocation, so that
`params.json` is not provenance for the directory. No byte-identity anchor exists for that run.

**Oracles that worked (Track 2 state-splits MILP, 2026-09-07 — a combinatorial MILP):**
- **Enumerate the integer part, LP the continuous part.** For a min-splits MILP with binary `z`
  and continuous shares `y`, brute force over all `2^(S·k)` z-patterns (S=6, k=2 → 4 096),
  reject with a hand-written BFS, and price each survivor with a *dense hand-built* share LP.
  Objective and split count then match `solve()` to <1e-7 on five settings in seconds.
- **Symbolic row read-back.** Densify `problem.A`, rebuild every named block from the model's
  algebra, and assert equality block by block, plus "the named blocks account for all rows" —
  that catches an *extra* undocumented row, which a feasibility oracle never does.
- **Strip the constraint blocks you want to test.** Keeping only root/rz/flow/net rows and
  pinning `z` by bounds turns a contiguity claim into 2^S HiGHS feasibility calls vs BFS.
- **Run a Lloyd/round-capped routine at every cap 0..n.** Once `rounds_used` saturates below the
  cap, labels must be byte-identical across caps — that is how you check "a rejected round is a
  no-op" without reaching inside the loop.
- **Row counts in a plan go stale before the code does.** Here the plan said 6 583 rows; the code
  builds 11 317 = 6 583 + 882 (an `η z ≤ y` block added by a later amendment) + 3 852 (capacity
  per *directed arc* instead of per arc pair). Always reconcile the gap *exactly* — an exact
  decomposition distinguishes a stale number from a construction bug.
- **Time the real-shape build even when it is not a listed claim.** A plan's "Seconds" for scf
  contiguity at k=18 did not hold on two synthetic 49-node/107-edge instances: 300 s time limit,
  10.9 % gap on the planar one. scf relaxations are weak; runtime is the risk, not row count.
  And note `solve()` *raises* on a time limit, so slowness is a hard failure downstream.

**Recurring spec-vs-code pattern here:** `scipy.optimize.milp` accepts no warm start
(options are only disp/presolve/time_limit/node_limit/mip_rel_gap), so any model text saying a
heuristic "seeds" the MILP is unimplementable — check for it.
