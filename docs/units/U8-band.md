# Unit U8-band — `EG^bal_{S₁₃}(δ)`: the band-constrained fibre, its duals, the softness certificate and the frontier

Status: done

**The A1 track's kill test for the band-constrained problem** (`LENS_GROMOV` M8/M12, ledger
U13/U14/U7; `DOMAIN_optimization` §2.10–§2.12, §4 Stages 1–2, §5 rows 1, 2, 4;
`DOMAIN_economic-theory` N7–N9). Stage 0 is done: `B_tot = 1145.81`, (★) at `P₁₃` = 60.8025,
`δ₀` = 0.39% (seed 3) / 0.62% (seed 9) — FRAME §6.

## Spec (verbatim from `docs/foundations/DOMAIN_optimization.md` §2.10, §2.11)

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

Every other unit's owned files · `docs/foundations/FRAME.md` · `docs/foundations/BRIEF.md` · `docs/foundations/APPROACHES.md` ·
`docs/foundations/LENS_*.md` · `docs/foundations/DOMAIN_*.md` · `docs/foundations/LIT_*` · `docs/channel_note/**` · `CLAUDE.md` ·
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

`docs/foundations/DOMAIN_optimization.md` §2.10–§2.12, §3, §4 · `docs/foundations/DOMAIN_economic-theory.md` §2.8–§2.9,
N7–N9 · `docs/foundations/LENS_GROMOV.md` M8, M11, M12 · `docs/MODEL_U1-cert.md` §1, §3 P1, §4.1, §5 ·
`tools/verify/U1-cert/instance_numbers.py` (the unconstrained EG solve and its dual check — the
value to reproduce at `δ = 0.33`) · `docs/MODEL_U7-meas.md` §1, §6 · `docs/foundations/LIT_optimization.md`
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

## Model

From `docs/MODEL_U8-band.md` (2026-09-04, v1 at `k=13`; extended 2026-09-05 with §10, v2 at
`k=18` on the live instance). Defines the band-constrained fibre

```
EG^bal_S(δ) = max_X  Σ_{i∈S} log g_i(X),   s.t.  Σ_i x_{zi}=1,  (1−δ)T/k ≤ Σ_z M_z x_{zi} ≤ (1+δ)T/k
```

which upper-bounds `V(π,σ)` for every integral coverage with roster `S` whose districts respect
the band at `δ` (`MODEL_U1-cert` P1 plus one feasibility check). The **hard gate**: the
unconstrained `EG_{S₁₃}` must reproduce `60.6974156139` to `1e-6` before any frontier point is
computed, using the **unmasked** utility convention (`channel.gain_matrix`, not
`model.utilities`).

**Corrections applied in place, each superseding an earlier draft or a published claim.**
1. The good-side selection rule (U9 P2.5): `supp(X*) ⊆ argmax_i(u_i(z)/g*_i − ν_i M_z)`, not the
   published ratio form `argmax_i u_i(z)/q_{zi}` (`DOMAIN_optimization` §2.12), which is false
   already at `ν ≡ 0`.
2. The reported supergradient is `s_min(δ) = (T/k)Σ_i|ν_i|` minimised over the dual-optimal set,
   never the raw `Σ_i(μ_i^+ + μ_i^-)`, which is unbounded at `δ = 0`.
3. D1′'s certificate is witnessed, not assumed: every sponsor `δ` is also a solved grid point, so
   the tangent bound is checked against the direct solve (`bound ≥ direct`) rather than trusted.
4. SCIP is a cross-check only; `Point.certified_upper` never adopts SCIP's dual bound (an earlier
   draft's "take the smaller" is unsafe at tier-1 scale, per `CODEVERIFY_U8-band.md` F7).
5. Split counting requires cleaning the vertex first (below `1e-6`, renormalised, re-certified as
   a vertex) — an uncleaned support threshold manufactures phantom splits.

**Numbers computed — v1 (`k=13`, §9), delivered seed-3 draw, `V(delivered) = 59.9374697984`.**

| `δ` | `EG^bal` bracket `[primal, upper]` | `s_min` | `−V` (gap) | splits (cap) |
|---|---|---|---|---|
| `0.0039460106` (`δ₀`) | `[60.6204408013, 60.6204408042]` | `0.5609` | `0.682971` | 19 (24) |
| `0.02` | `[60.6288653530, 60.6288653560]` | `0.4942` | `0.691396` | 20 (23) |
| `0.05` | `[60.6416012810, 60.6416012849]` | `0.3710` | `0.704131` | 16 (22) |
| `0.10` | `[60.6577253430, 60.6577253509]` | `0.2663` | `0.720256` | 16 (20) |
| `0.33` | `[60.6974156089, 60.6974156171]` | `0.0000` | `0.759946` | 10 (12) |

D1′ verdict: **NOT SOFT** at `δ ∈ {0.02, 0.05, 0.10}` — the intercept `EG^bal(δ₀) − V = 0.682971`
nats already exceeds the `5e-3` floor by 137×, so no slope can rescue it. `δ* ≤ δ₀`, bisection runs
zero solves. N8: at `δ₀` twelve of thirteen bands are tight, six-and-six split. N9: no rep falls
below proportionality anywhere on the frontier; the **delivered integral draw** starves 4 of 13
reps, not the band.

**Numbers computed — v2 (`k=18`, §10), live instance, delivered draw, `V(delivered) =
95.75519165924108`.**

| `δ` | `EG^bal` bracket `[primal, upper]` | `s_min` | `−V` (gap) | splits (cap) |
|---|---|---|---|---|
| `0.00997002334742` (`δ₀`) | `[96.4796985975, 96.4796986046]` | `0.5856` | `0.724507` | 24 (33) |
| `0.02` | `[96.4851908640, 96.4851908707]` | `0.5097` | `0.729999` | 25 (32) |
| `0.05` | `[96.4976902647, 96.4976902691]` | `0.3440` | `0.742499` | 27 (32) |
| `0.10` | `[96.5101232221, 96.5101232306]` | `0.1828` | `0.754932` | 21 (24) |
| `0.33` | `[96.5309780226, 96.5309780270]` | `0.0549` | `0.775786` | 16 (18) |

D1′ verdict: **NOT SOFT** at all three sponsor widths, `146×`–`155×` the floor; `δ* ≤ δ₀`, zero
solves. Unlike v1, the band never fully slackens on this grid (unconstrained `M`-max-deviation
`0.36597 > 0.33`). N8: sixteen of eighteen bands tight at `δ₀`, eight-and-eight split, easing to
one rep (R0000) still binding at `δ = 0.33`. N9: 3 of 18 reps starved on the delivered draw, none
on the frontier. First movers: `n_exact_ties = 0` (unlike v1's 75-zip tie block); the top-25
near-tie zips carry `0.39 %` of `T`, all owned by R0008 or R0021; the dual is degenerate (support
`3773` vs expected `3781`), so no ordering is named from `ν` alone.

**What this unit cannot say (§8).** Anything about a different roster; anything about
misreporting; anything about error in the common measure `M` — every `p_z` and `ν_i` is a
functional of `M`. `ν` is a marginal rate of *transformation*, not the sponsor's marginal rate of
*substitution*, which has never been elicited.

**Open / findings not yet closed.** The v1 `/tmp` artifacts referenced by the earlier
`CODEVERIFY_U8-band.md` (rows citing `/tmp/u8verify/*.py`) were never committed to the repo and
are unrecoverable (see Code verify below). The mass vector and the split *set* at the
unconstrained optimum are not invariants (only `g*` and `φ` are) — extends `VERIFY_U9-bandthm`
§10.E's list. `figures/u8_band/frontier.png` was not regenerated for v2 and still shows the `k=13`
curve.

Full report: `git show 8b14eee:docs/MODEL_U8-band.md`.

## Verify

none yet

## Code verify

**v1** (`docs/CODEVERIFY_U8-band.md`, 2026-09-04, `code-verify`, against `td/solvers/eg_band.py`
and `tools/measure/frontier.py` at `k=13`). **20 rows: 18 VERIFIED, 2 REFUTED, 0 INCONCLUSIVE.**
Type check clean; `tests/run_all.py` → 208 passed, 0 failed; `figures/u8_band/frontier.png`
re-generated byte-identically. **D1′ "NOT SOFT" stands, and stands on a certified lower bound, not
on the slope.**

| # | row | verdict |
|---|---|---|
| 1–12, 14–19 | program, gate, duality, cleaning, supergradient, D1′, witness, OA safety, stall floor, SCIP, grid, first movers, N8/N9, `δ*` | VERIFIED |
| 13 | §5.1 "`ĝ > 0` guaranteed by U9 P5.3" | **REFUTED** — `solve_band(delta=None)` drops the lower band row P5.3's floor comes from; a constructed instance zeroes an agent and crashes the loop. No published number is affected: every `delta=None` solve on the real instance clears the floor by ≥1.3×. |
| 20 | §1 "the masked bound lands ≈27 nats [below V]" | **REFUTED** (the number) — measured masked EG is `55.9763` nats, not `≈27`; the load-bearing claim (masked lands below `V = 59.9375`) survives. |

**v1 artifacts are unrecoverable.** All v1 scratch scripts lived at `/tmp/u8verify/*.py` per the
report's own artifact table; `/tmp` is not committed and the directory no longer exists in this
worktree. Nothing under `tools/verify/U8-band/` is v1 material — that directory holds only the v2
artifacts (below). The v1 verdicts above stand as recorded prose; they cannot be re-run.

**v2** (`docs/CODEVERIFY_U8-band-v2.md`, 2026-09-05, `code-verify`, against `MODEL_U8-band.md` §10
at `k=18`, **current**). **16 VERIFIED · 4 REFUTED · 1 VERIFIED-but-misleading · 1 INCONCLUSIVE.**
Type check clean; `tests/run_all.py` → 237 passed, 0 failed; `verify_model_s10.py` → 357
assertions pass, 3 fail (the three REFUTED display/wording rows below; row counts differ from the
headline 4 REFUTED because one row fires twice). **None of the REFUTED rows changes D1′, `δ*`, N8,
N9 or the A1 conclusion** — all four are defects of statement, not of result.

| # | row | verdict |
|---|---|---|
| 3 | §10.0 gloss on `gate.delta_upper` being `null` | **REFUTED** — the field is the gap to a `--gate-reference` value, unrelated to band closure; it is `null` only because no reference was passed. No impact: the substantive claim (band never closes) is established independently by a certified numeric gap. |
| 7 | §10.1 sandwich display, last entry `96.5321517586` | **REFUTED** — correct 10-dp rounding is `96.5321517585`; a `+1e-10` display slip, two orders below tier-1 tolerance. |
| 16 | §10.6 "margins … an order of magnitude tighter than v1's ties" | **REFUTED as written** — nothing is tighter than v1's exact `0.0` ties; the supportable reading is the tie block's *mass* (v1 `2.90 %` vs v2 `0.39 %`, a 7.47× ratio), not "tighter margins". |
| 18 | §5.1 "all 18 gains sit at ≈206" | **REFUTED** — independent re-solve gives 16 of 18 gains at `≈212` and two outliers at `223.6`/`228.7`; `206` was `mean(g_delivered)`, a different quantity. The conclusion survives: the minimum gate gain (`211.786`) still clears the `140.638` floor by 1.5×. |
| 22 | Acceptance-5 byte-identical re-run, claimed for v1 §9 | **INCONCLUSIVE** — §10 makes no such claim for v2, so there is nothing to verify or refute; a gap worth closing, not a defect. |

**Artifacts**, moved to `tools/verify/U8-band/` — the v2 artifact set; there is no v1 set to move:
`verify_model_s10.py`, `oracle_gate.py`, `oracle_gate_v1.py`.

Full reports: `git show 8b14eee:docs/CODEVERIFY_U8-band.md` (v1);
`git show 8b14eee:docs/CODEVERIFY_U8-band-v2.md` (v2, current).
