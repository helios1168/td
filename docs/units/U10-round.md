# Unit U10-round — band-aware rounding of the `EG^bal` vertex, `γ(δ)`, and whether any integer programming is built

`DOMAIN_optimization` §2.13, §4 Stage 3, §5 row 3; `LENS_GROMOV` ledger U18; decides **D2′**.
Gated on U8-band (its vertex and value at the chosen `δ`) — **gate satisfied**: `MODEL_U8-band` §10
is the live `k = 18` v2 run, artifacts under `battery/results/u8_band_v2_20260904/`.

**Re-anchored to v2 / `k = 18` on 2026-09-05** (`WAVE2_PLAN` §0c). Every number below is the live
instance's, the quoted spec included — `DOMAIN_optimization` §2.13 was re-cut to v2 the same day
and the quote was re-synced against it. The only `k = 13` figures left are the ones §2.13 itself
labels *Historical*.

## Spec (verbatim from `docs/DOMAIN_optimization.md` §2.13)

> **The problem P3b does not solve.** `MODEL_U1-cert` P3b rounds each split unit to any buyer and
> bounds the loss by `−Σ_i log(1 − L_i/g*_i)`. Under a band that is **not enough**: rounding moves
> `M`-mass between districts and can push the rounded map out of the band. So the rounding step is
> itself a constrained problem:
>
> ```
> max  Σ_{i∈S} log( g*_i − L_i + Σ_{z∈F} u_i(z) ξ_{zi} )     ξ_{zi} ∈ {0,1},  Σ_i ξ_{zi} = 1
> s.t. the band rows on the rounded district masses
> ```
>
> **Sizing, at the live v2 instance (`k = 18`, `n = 3,748`).** `|F| ≤ 2k−1 = 35` — the v2 manifest
> records `split_cap_2k_minus_1: 35` — with `≤ k = 18` buyers each: **≤ 630 binaries, `2k = 36`
> rows, separable concave objective.** The a-priori `35` is loose: the manifest's sharp per-vertex
> cap `k−1+t` is `33` at `δ_0` (`t = 16` tight bands) and the *measured* split count there is `24`.
> **Quote the measured count and its masses, never the cap** (`MODEL_U1-cert` failure mode 9).
> *(Historical: at v1's `k = 13` these were `2k−1 = 25`, `325` binaries and `26` rows. Any bare
> `25` or `325` elsewhere in this file, or in a brief quoting it, is a v1 figure and not current.)*
>
> That is the tractable convex-MINLP class (**Kronqvist2018**), solvable by the OA
> master already written (**WesterlundPettersson1995**) or by NLP-based B&B
> (**GuptaRavindran1985**) in seconds, with `mip_rel_gap = 0.0` (trap 12). Equivalently it is one
> RINS neighbourhood around the fractional solution (**Danna2005**).
>
> **The criterion (U18, `LENS_GROMOV` M13.1).** Let `γ(δ) := EG^bal_S(δ) − V(rounded, δ)`.
> - `γ(δ_sponsor) ≤ 5e-3` nats (tier 2) ⇒ **no integer programming beyond this 630-binary repair
>   is needed**; §2.1 stays retired, and A1's deliverable is "a few convex programs plus rounding"
>   with a certified gap. This is the expected case on **v1 evidence only**: the unconstrained
>   analogue realised `5.1e-4`–`1.9e-3` nats (`MODEL_U1-cert` §4.3) — a **v1, `k = 13`**
>   measurement with **no v2 counterpart** — already inside tier 2.
> - `γ(δ_sponsor) > 5e-3` and the reduced solve is already exact ⇒ the gap is **structural**, not a
>   rounding artefact, and §2.1 fires: only a full rep-indexed integer model can close it. Record
>   which of the two solvers produced the vertex, since `F` is vertex-dependent.
> - Report `γ` at **both** §2.11 solvers' vertices, and never quote a single-vertex `M(F)`
>   (`MODEL_U1-cert` failure mode 9).
>
> **Assumptions vs FRAME §5/§6.** `|F| ≤ 2k−1` is **not** an assumption here: §2.10 now carries it
> as `[verified, unconditional; VERIFY_U9-bandthm §4 — 440 certified vertices]`. It enters only as
> a sizing input, and even that is measured rather than assumed — `F` is whatever the solve
> returns, and the numbers to quote are the sharp per-vertex cap `k−1+t = 33` at `δ_0` and the
> measured `24`, not the a-priori `35` (`MODEL_U1-cert` failure mode 9).
> Feasibility of the rounding problem is **not guaranteed** at very small `δ` (a band tight enough
> may admit no integral map at all — the integer balance floor `t*` of `cert_integer_balance_floor`
> is exactly the obstruction, and it is the one certificate that did **not** collapse into the EG
> dual, `VERIFY_U1-cert` row 4). **That is what certificate 2 is for** … if
> `t*/(T/k) > δ_sponsor` no integral band-feasible map exists and the sponsor's band is
> infeasible, which is a Farkas-style report (**Farkas1902**) the sponsor must see.

### Read the quote through this

`DOMAIN_optimization.md` §2.13 was itself re-cut to v2 / `k = 18` on 2026-09-05, and the quote
above is the current text, so the sizing re-anchor this section used to carry is **discharged** —
`≤ 630` binaries and `36` rows now stand in the source. Two things still belong here:

1. **The per-grid-point split counts, which §2.13 does not carry.** §2.13 quotes the `δ_0` column
   only (cap `k−1+t = 33`, measured `24`). `MODEL_U8-band` §10.1's measured counts across the five
   grid points are `24, 25, 27, 21, 16`, against caps `33, 32, 32, 24, 18` — all under the
   a-priori `35`. This is the set of numbers acceptance 2a reports; the `≤ 630`/`36` sizing and
   `5e-3` nats / `mip_rel_gap = 0.0` are unchanged.
2. **"Report `γ` at both §2.11 solvers' vertices" is still not executable and is replaced** by
   acceptance 2 below. On v2 the SCIP route never produces a vertex at all: `MODEL_U8-band` §5.2 reads
   `getDualbound()` only, never the primal incumbent, and per `CODEVERIFY_U8-band` F7
   `Point.certified_upper` never adopts SCIP's number. There is no second vertex to round.
   The *intent* of the clause — never quote a single-vertex `M(F)` as if it were an invariant — is
   preserved by acceptance 2b.

## Files owned

`td/solvers/eg_round.py` · `tests/test_eg_round.py` · `docs/MODEL_U10-round.md` (spec, first) ·
`docs/CODEVERIFY_U10-round.md` (by `code-verify`) · `battery/results/u10_round_<date>/` ·
`figures/u10_round/` (the rounded map, dots and cells, per `CLAUDE.md`).

## Files forbidden

Every other unit's owned files (`td/solvers/eg_band.py` by import only) · `docs/FRAME.md` ·
`docs/BRIEF.md` · `docs/APPROACHES.md` · `docs/LENS_*.md` · `docs/DOMAIN_*.md` · `docs/LIT_*` ·
`CLAUDE.md` · existing `td/` modules · `battery/figures/`.

## Agent → verifier

`python-typed` → `code-verify`.

## Tooling

`~/.claude/hooks/enforce-file-tools.sh` blocks `cat` / `head` / `tail` / `sed` / `awk` / `grep`
with a file operand from Bash. Use Read and the Serena symbol tools instead
(`get_symbols_overview`, `find_symbol(include_body=True)`, `replace_content`,
`replace_symbol_body`); markdown headings are symbols. `RUNS_PLAN.md` §"Working rules" has the
full table. Bash is for running things — solves, tests, git.

## Acceptance

1. `cert_integer_balance_floor`'s `t*/(T/k)` on the live v2 instance reported first; if it exceeds
   the working `δ`, the unit stops with the infeasibility report (offending districts named) and
   that *is* the deliverable.
2. **The frontier grid, at the OA vertex, with vertex-dependence probed rather than asserted.**
   - **2a — the numbers.** For all five live grid points `δ ∈ {δ₀ = 0.00997002334742, 0.02, 0.05,
     0.10, 0.33}` (★9 unknown — report all five; `δ₀` is the live max-deviation, `MODEL_U8-band`
     §10.0), from the **OA vertex** — the only vertex the v2 run produced: `F` and `|F|`, `M(F)`,
     the rounded integral map, its `V`, its `M`-max-deviation (and whether it is inside the band),
     and `γ(δ)`. `mip_rel_gap = 0.0`; a `time_limit` stop is reported as **no bound**, never as a
     bound (trap 15).
   - **2b — vertex-dependence, measured on the route that exists.** `F` is not an invariant: it is
     a property of the reported vertex, not of the optimal face (`MODEL_U1-cert` failure mode 9;
     `CODEVERIFY_U8-band` F1 and F2 — on v1, a `U` perturbed in 37 of 15,977 entries at `1.1e-16`
     moved the split count by ±1, and `m` itself is not an invariant). So at `δ₀` **and** at one
     interior `δ`, obtain at least one *second*
     optimal vertex by the F2 recipe (re-solve the OA with a `1e-16`-scale perturbation of `U`, or
     from a different warm start / tolerance rung, confirming the value still agrees to tier 1) and
     report `|F|`, `M(F)` and `γ` at **each vertex found**, plus the spread across them. If no
     second distinct vertex can be produced, say so explicitly and label every `F`, `M(F)` and `γ`
     "one vertex, not an invariant". **No `M(F)` or `γ` may be stated as an invariant anywhere in
     the deliverable.**
   - **2c — SCIP, where it exists, as a value cross-check only.** The v2 run ran SCIP at
     `δ ∈ {0.02, 0.33}` only (`MODEL_U8-band` §10.1: dual bounds `96.4851908684` and
     `96.5309780292`, both within `2.31e-9` / `2.27e-9` of the OA). At those two `δ` quote the SCIP
     dual bound beside the OA bracket as a cross-check on `EG^bal(δ)`. It is **not** a vertex, it
     supplies **no** `F`, and it is **never** a source of the reported bound (`MODEL_U8-band` §5.2
     as narrowed by `CODEVERIFY_U8-band` F7). At the other three `δ` there is no SCIP number and
     none is to be manufactured.
3. D2′ stated: "no MINLP needed" iff `γ ≤ 5e-3` at the **largest** `γ` over the vertices examined
   in 2b; otherwise "structural gap", with that number and with the vertex it came from named.
   If 2b found only one vertex, D2′ is stated as conditional on that vertex and says so.
4. Tests: on the `MODEL_U7-meas` §4 toy, the rounding MIP reproduces brute force over all
   `2^|F|` roundings; a band tight enough to be infeasible is detected and reported; existing
   tests green.
5. Provenance fields as U7-meas; byte-identical re-run.

## Numbers to compute first

`t*/(T/k)` (the integer balance floor, geometry-free) · `|F|` and `M(F)` at the OA vertex at each of
the five `δ`, and at every additional vertex 2b produces (never a single `M(F)` presented as the
value) · `γ(δ)` at the five `δ` · the rounded map's `P` (premium share) beside its `V`.

## Inputs to read (paths and sections only)

`docs/DOMAIN_optimization.md` §2.13 (re-cut to v2; quoted in full above), §4 Stage 3 — whose
"`γ(δ) ≤ 5e-3` at **both** vertices" is the clause superseded by point 2 above · **`docs/MODEL_U8-band.md` §10 — the live v2 run** (§10.0 `δ₀` and the gate,
§10.1 the frontier, split counts and the SCIP cross-check), and §5.2 for why SCIP is a cross-check
only · `docs/CODEVERIFY_U8-band.md` F1, F2, F7 · `docs/MODEL_U1-cert.md` §3 P3b, §4.3, §5.9 ·
`docs/VERIFY_U1-cert.md` §5 (P3c's vertex-dependence finding) · `docs/LIT_optimization.md` §0, §4
(`budish2013` — why no rounding theorem applies; `akbarpour2020`, `gandhi2006` fallbacks) ·
`td/solvers/cert_draw.py::cert_integer_balance_floor` · U8's v2 outputs under
**`battery/results/u8_band_v2_20260904/`** (`draw_k18_v2_20260904.json`; gitignored, reached
through a symlink — its `instance` field is a stale `.claude/worktrees/A1/` path, `MODEL_U8-band`
§10 note, and `instance_sha256` is the field to trust).

## Open questions for ★0

★9 (the sponsor's `δ`): this unit reports at all five live grid values rather than waiting.
`δ₀ = 0.009970` is now *in* the grid — v1's `{0.02, 0.05, 0.10}` omitted it, and `δ₀` is the
tightest band anyone would ask for and the one D1′ and `δ*` were both decided at.

## Branch

From `main` (e.g. `wt/U10-round`). The old "launch from `.claude/worktrees/A1`" instruction and the
`wt/A1` branch are dead — `A1` was retired in `3c8a643`; `BRIEF.md:118-119` is the stale sentence
that produced them.

## Stop rule

If the reduced MIP is infeasible at a `δ` the integer balance floor says is feasible, report the
contradiction — it means `F` was mis-identified or the band rows were mis-stated — and do not
enlarge `F` to force feasibility. If `|F| > 2k − 1 = 35`, report the count as a refutation of U9's
P3-split and continue with the measured `F`.

**stop and report rather than improvise**
