# Unit U8-band — `EG^bal_{S₁₃}(δ)`: the band-constrained fibre, its duals, the softness certificate and the frontier

**The A1 track's kill test for the band-constrained problem** (`LENS_GROMOV` M8/M12, ledger
U13/U14/U7; `DOMAIN_optimization` §2.10–§2.12, §4 Stages 1–2, §5 rows 1, 2, 4;
`DOMAIN_economic-theory` N7–N9). Stage 0 is done: `B_tot = 1145.81`, (★) at `P₁₃` = 60.8025,
`δ₀` = 0.39% (seed 3) / 0.62% (seed 9) — FRAME §6.

## Spec (verbatim from `docs/DOMAIN_optimization.md` §2.10, §2.11)

> ```
> EG^bal_S(δ) = max_X  Σ_{i∈S} log g_i(X),        g_i(X) = Σ_z u_i(z) x_{zi}
>      s.t.   Σ_{i∈S} x_{zi} = 1                  ∀z          [duals p_z, free]
>             Σ_z M_z x_{zi} ≤ (1+δ)·T/k          ∀i∈S        [duals μ_i^+ ≥ 0]
>             Σ_z M_z x_{zi} ≥ (1−δ)·T/k          ∀i∈S        [duals μ_i^- ≥ 0]
>             x ≥ 0
> ```
> **One solve bounds the whole curve.** From any `δ` with slope `s(δ)`, concavity gives
> `EG^bal(δ') ≤ EG^bal(δ) + s(δ)·(δ' − δ)` for every `δ' > δ`. So a single solve at `δ_0` plus
> its duals can *prove* softness at the sponsor's `δ` if
> `EG^bal(δ_0) + s(δ_0)(δ_sponsor − δ_0) − V(delivered) ≤ 5e-3`.
> **Primary — LP outer approximation, warm-started across `δ`.** Epigraph variables `t_i`,
> master `max Σ_i t_i  s.t.  t_i ≤ log ĝ_i^{(r)} + (g_i − ĝ_i^{(r)})/ĝ_i^{(r)}` plus the band and
> supply rows. Each tangent is a global overestimator of `log`, so every master optimum is a
> valid upper bound on `EG^bal(δ)` and hence on `V`.
> **Cross-check — SCIP with native `log`.** Set the gap to `0.0` (trap 12), read the *dual*
> bound; a `time_limit` stop is not a bound (trap 15). Run it at two or three `δ` only.
> **Marking the MNW point (trap 2).** Plot the delivered draw at `(δ_0, 59.9375)` and the
> unconstrained endpoint `(0.33, 60.6974)` with its ≥ 50% spread annotated, every time the
> curve is rendered.

## Files owned

- `td/solvers/eg_band.py` (the solver: OA master on HiGHS via `scipy.optimize.linprog` /
  `highspy`, SCIP cross-check via `pyscipopt`, dual extraction, solver-free `O(nk)` dual check)
- `tools/measure/frontier.py` (the CLI: grid, bisection for `δ*`, D1′ certificate, first-mover
  list, N8/N9, the plot with the MNW point)
- `tests/test_eg_band.py`
- `docs/MODEL_U8-band.md` (spec; write it first, from the two DOMAIN sections above),
  `docs/CODEVERIFY_U8-band.md` (by `code-verify`)
- `battery/results/u8_band_<date>/` (gitignored), `figures/u8_band/` (tracked — a curve nobody
  can see is worse than a PNG)

## Files forbidden

Every other unit's owned files · `docs/FRAME.md` · `docs/BRIEF.md` · `docs/APPROACHES.md` ·
`docs/LENS_*.md` · `docs/DOMAIN_*.md` · `docs/LIT_*` · `docs/channel_note/**` · `CLAUDE.md` ·
existing `td/` modules (`channel.py`, `model.py`, `instance.py`, `solvers/*`) except by import ·
`tools/measure/premium.py` · `battery/figures/`.

## Agent → verifier

`python-typed` → `code-verify`. Serena binds to the session's launch directory — launch only
from a session started in `.claude/worktrees/A1` and confirm the active project path first.

## Acceptance

1. `EG^bal_{S₁₃}(δ₀)` on seed 3 with a primal–dual bracket ≤ 1e-8 nats (tier 1) from the OA
   route, and SCIP's dual bound within 1e-6 of it at two grid points; the `O(nk)` dual check
   passes at every reported point with no solver in the trusted path.
2. The sandwich holds numerically: `59.9375 ≤ EG^bal(δ₀) ≤ … ≤ EG^bal(0.33) = 60.6974 ± 1e-6`;
   monotone and concave on the grid (report any violation as a finding, not a fix).
3. **D1′ stated as a certificate**: the one-solve bound at `δ = 0.10` (and at 0.02, 0.05), with
   the verdict *soft* / *not soft* against 5e-3 nats.
4. `δ*` to three digits by bisection, or "none in `[δ₀, 0.33]`".
5. Outputs carry run id, instance sha256, draw sha256, θ/λ/filler_capture, solver versions;
   byte-identical re-run modulo timestamp; `mip_rel_gap = 0.0` on every SCIP call; no
   `time_limit` reported as a bound.
6. Tests: a toy (the `MODEL_U7-meas` §4 instance with `M = [20,15,15,20]`) where `EG^bal` at
   `δ = 0` and at `δ` large are computed by brute force over fractional splits on a grid and by
   the unconstrained EG (equal to `MODEL_U1-cert`'s value on the same toy); the OA bound is
   never below the true value at any iteration; existing 184 tests stay green.

## Numbers to compute first

| # | number | flips what |
|---|---|---|
| 1 | `EG^bal_{S₁₃}(δ₀)`, its `p`, `μ^±`, support size vs `n + k − 1 + #tight` | D1′; whether `ν` may be read as "the" exchange rate (degeneracy) |
| 2 | the one-solve concavity bound at `δ ∈ {0.02, 0.05, 0.10}` | **A1 lives or collapses-on-softness** |
| 3 | the grid `{δ₀, 0.02, 0.05, 0.10, 0.33}` and `δ*` | U13; the shape (concave-rising vs flat-then-jump) |
| 4 | first-mover zips at `δ*` and their `M`-mass | U14; U4-disp's input |
| 5 | N8: reps with a binding band and the sign of `ν_i` at each `δ` | whether §2.8 collapses to CEEI (all `ν_i = 0`) |
| 6 | N9: proportionality gap `u_i(A_i) − u_i(Z)/k` per selected rep at each `δ` | whether balance and "do not starve anybody" conflict |

## Inputs to read (paths and sections only)

`docs/DOMAIN_optimization.md` §2.10–§2.12, §3, §4 · `docs/DOMAIN_economic-theory.md` §2.8–§2.9,
N7–N9 · `docs/LENS_GROMOV.md` M8, M11, M12 · `docs/MODEL_U1-cert.md` §1, §3 P1, §4.1, §5 ·
`docs/artifacts/U1-cert/instance_numbers.py` (the unconstrained EG solve and its dual check — the
value to reproduce at `δ = 0.33`) · `docs/MODEL_U7-meas.md` §1, §6 · `docs/LIT_optimization.md`
§0, §1, §6 (`jalota2023` caveat; `lundell2022` SHOT; `chaudhury2024eg` Frank–Wolfe) ·
`td/channel.py::gain_matrix`, `td/solvers/centers.py::power_weights` (the existing dual-check
pattern) · `battery/results/draw_k13_20260901/`, `battery/results/meas_20260903/`.

## Open questions for ★0

★9 (the sponsor's `δ`) is what this unit is built to survive not knowing; it reports the whole
curve. ★11 (rewrite the charter's step 3) waits for this unit's report.

## Branch

`wt/A1` (or `wt/U8-band` from `wt/A1` if run in its own worktree; copy the instance and
`battery/results/` in by hand — both gitignored)

## Stop rule

If the OA loop does not converge to tier 1 within 200 cuts at some `δ`, report the best valid
upper bound reached and the iterate, do not tune. If SCIP and OA disagree beyond 1e-6, report
both and the smaller valid bound. If the dual support size shows degeneracy, report `ν` as one
dual optimum and do not name a first-mover list from it alone. If the instance's `u_i(z)/M_z`
rounding (69 zips at `> 1` by ≤ 4.2e-7) affects a bound, say by how much and do not repair it.

**stop and report rather than improvise**
