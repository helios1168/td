# Unit U7-meas — the measurement stage *(launched 2026-09-03 on `wt/A1`; ★6 lifted in full)*

**This is the unit both domains would have run first.** It was blocked by the plan's own
constraint ("nothing that touches `td/` code yet") and by the instance's absence; both are
lifted — the user answered ★6 in full on 2026-09-03 and the instance is at this worktree's
root. It runs as the A1 track's kill experiment; the spec is `docs/MODEL_U7-meas.md`.

## Spec (verbatim from `docs/DOMAIN_optimization.md`:§4, Stage 0)

> **Stage 0 — measure before formulating (no solver, hours).** Run §5 in full. Both lenses
> converge on this and it is the only step with no dependency on any open decision. Two of its
> outputs can *cancel the rest of this plan*: if `P₀ ≈ P*(A)` and the contested-among-the-13 count
> is small, the premium is not reachable by redrawing and the two-stage scheme was right all along.

## Files owned

- `tools/measure/__init__.py`, `tools/measure/premium.py` — read-only analysis over `td/`;
  no existing `td/` module changes
- `tests/test_measure.py`
- `docs/MODEL_U7-meas.md` (the measurement spec) · `docs/CODEVERIFY_U7-meas.md`
- `battery/results/meas_20260903/` for outputs (gitignored)

## Files forbidden

Every other unit's owned files · `docs/FRAME.md` · `docs/BRIEF.md` · `docs/LENS_*.md` ·
`docs/DOMAIN_*.md` · `docs/channel_note/**` · `CLAUDE.md` · **`battery/figures/`** (primary
artifacts, `CLAUDE.md`) · existing `td/` modules except by explicit extension agreed at launch.

## Agent → verifier

`python-typed` → `code-verify`

## Acceptance

Tests pass (the existing 151 stay green), the type checker is clean, and every number is emitted
with the run id and the instance hash that produced it. `mip_rel_gap = 0.0` on any certification
solve (trap 12); a `time_limit` abort must never be reported as a bound (trap 15). Byte-identical
re-run from the same instance.

## Numbers to compute first

`DOMAIN_optimization.md` §5 numbers 1–9 and `DOMAIN_economic-theory.md` §5 N1–N6. In the order the
lenses recommend (`LENS_GROMOV.md` §"Recommended order"): `P₀`, `P*(A)`, the `g`-spread (U1), the
contested-among-the-13 count (U4) — all four from one script — then the hand-drawn baseline (U10),
then the noise floor (U6, if a domain plan exists for it). N1–N3 do not depend on any of these.

## Inputs to read (paths and sections only)

`docs/DOMAIN_optimization.md` §5 · `docs/DOMAIN_economic-theory.md` §5 · `docs/LENS_GROMOV.md`
Move 4 and the U-ledger · `docs/FRAME.md` §5 (data defects), §6 · `docs/DATA.md` ·
`docs/TEST_PLAN.md` · `td/instance.py`, `td/channel.py`, `td/solvers/centers.py`,
`td/solvers/cert_draw.py`

## Open questions for ★0

Answered 2026-09-03: ★6 lifted in full; the instance is at this worktree's root
(`instance_descaled.json.gz`, gitignored, hand-copied) together with the two k=13 draws under
`battery/results/`. The unit runs on `wt/A1`.

## Branch

`wt/A1` (from `national-channel` at `a4eb488`)

## Stop rule

If a number cannot be computed because the instance is malformed or a defect in FRAME §5 bites
(the 6 coordinate-less zips, the headroom repairs, the 6-significant-figure rounding), report the
defect and the affected number — do not repair the data to get a number out.

**stop and report rather than improvise**
