---
name: td-verification-oracles
description: Oracles, anchors and environment traps for verifying td (national channel) research code — established verifying U7-meas 2026-09-03 and U8-band 2026-09-04 on wt/A1
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
  `74eff38`. `tools/` is not a package: tests load scripts via `importlib.util.spec_from_file_location`
  and must register the module in `sys.modules` for `@dataclass` to resolve.
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

**Recurring spec-vs-code pattern here:** `scipy.optimize.milp` accepts no warm start
(options are only disp/presolve/time_limit/node_limit/mip_rel_gap), so any model text saying a
heuristic "seeds" the MILP is unimplementable — check for it.
