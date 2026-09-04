# Unit U10-round — band-aware rounding of the `EG^bal` vertex, `γ(δ)`, and whether any integer programming is built

`DOMAIN_optimization` §2.13, §4 Stage 3, §5 row 3; `LENS_GROMOV` ledger U18; decides **D2′**.
Gated on U8-band (its vertex and value at the chosen `δ`).

## Spec (verbatim from `docs/DOMAIN_optimization.md` §2.13)

> ```
> max  Σ_{i∈S} log( g*_i − L_i + Σ_{z∈F} u_i(z) ξ_{zi} )     ξ_{zi} ∈ {0,1},  Σ_i ξ_{zi} = 1
> s.t. the band rows on the rounded district masses
> ```
> with `|F| ≤ 2k−1 ≤ 25` and `≤ k` buyers each: **≤ 325 binaries, `2k` rows, separable concave
> objective.** … solvable by the OA master already written or by NLP-based B&B in seconds, with
> `mip_rel_gap = 0.0` (trap 12).
> **The criterion (U18).** Let `γ(δ) := EG^bal_S(δ) − V(rounded, δ)`. `γ(δ_sponsor) ≤ 5e-3` nats
> ⇒ no integer programming beyond this 325-binary repair is needed; §2.1 stays retired.
> `γ(δ_sponsor) > 5e-3` and the reduced solve is already exact ⇒ the gap is structural and §2.1
> fires. Report `γ` at **both** §2.11 solvers' vertices, and never quote a single-vertex `M(F)`.
> Feasibility … is **not guaranteed** at very small `δ` — the integer balance floor `t*` of
> `cert_integer_balance_floor` is exactly the obstruction … if `t*/(T/k) > δ_sponsor` no integral
> band-feasible map exists.

## Files owned

`td/solvers/eg_round.py` · `tests/test_eg_round.py` · `docs/MODEL_U10-round.md` (spec, first) ·
`docs/CODEVERIFY_U10-round.md` (by `code-verify`) · `battery/results/u10_round_<date>/` ·
`figures/u10_round/` (the rounded map, dots and cells, per `CLAUDE.md`).

## Files forbidden

Every other unit's owned files (`td/solvers/eg_band.py` by import only) · `docs/FRAME.md` ·
`docs/BRIEF.md` · `docs/APPROACHES.md` · `docs/LENS_*.md` · `docs/DOMAIN_*.md` · `docs/LIT_*` ·
`CLAUDE.md` · existing `td/` modules · `battery/figures/`.

## Agent → verifier

`python-typed` → `code-verify` (launch from a session started in `.claude/worktrees/A1`).

## Acceptance

1. `cert_integer_balance_floor`'s `t*/(T/k)` on the instance reported first; if it exceeds the
   working `δ`, the unit stops with the infeasibility report (offending districts named) and
   that *is* the deliverable.
2. For `δ ∈ {0.02, 0.05, 0.10}` (★9 unknown — report all three) and for **both** U8 vertices
   (OA and SCIP): the rounded integral map, its `V`, `M`-max-deviation (inside the band), and
   `γ(δ)`; `mip_rel_gap = 0.0`; no `time_limit` reported as a bound.
3. D2′ stated: "no MINLP needed" iff `γ ≤ 5e-3` at both vertices; otherwise "structural gap" with
   the number.
4. Tests: on the `MODEL_U7-meas` §4 toy, the rounding MIP reproduces brute force over all
   `2^|F|` roundings; a band tight enough to be infeasible is detected and reported; existing
   tests green.
5. Provenance fields as U7-meas; byte-identical re-run.

## Numbers to compute first

`t*/(T/k)` (the integer balance floor, geometry-free) · `|F|` and `M(F)` at each U8 vertex (report
both, never one) · `γ(δ)` at the three `δ` · the rounded map's `P` (premium share) beside its `V`.

## Inputs to read (paths and sections only)

`docs/DOMAIN_optimization.md` §2.13, §4 Stage 3 · `docs/MODEL_U1-cert.md` §3 P3b, §4.3, §5.9 ·
`docs/VERIFY_U1-cert.md` §5 (P3c's vertex-dependence finding) · `docs/LIT_optimization.md` §0,
§4 (`budish2013` — why no rounding theorem applies; `akbarpour2020`, `gandhi2006` fallbacks) ·
`td/solvers/cert_draw.py::cert_integer_balance_floor` · U8's outputs under `battery/results/`.

## Open questions for ★0

★9 (the sponsor's `δ`): this unit reports at three candidate values rather than waiting.

## Branch

`wt/A1` (or `wt/U10-round` from `wt/A1`)

## Stop rule

If the reduced MIP is infeasible at a `δ` the integer balance floor says is feasible, report the
contradiction — it means `F` was mis-identified or the band rows were mis-stated — and do not
enlarge `F` to force feasibility. If `|F| > 2k − 1`, report the count as a refutation of U9's
P3-split and continue with the measured `F`.

**stop and report rather than improvise**
