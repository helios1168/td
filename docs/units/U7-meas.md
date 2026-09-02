# Unit U7-meas — the measurement stage *(blocked on ★6 and on the instance — not launched)*

**This is the unit both domains would have run first.** It is blocked by this plan's own
constraint ("nothing that touches `td/` code yet") *and* by the instance's absence from this
worktree. It is written down so that lifting ★6 launches it without re-planning.

## Spec (verbatim from `docs/DOMAIN_optimization.md`:§4, Stage 0)

> **Stage 0 — measure before formulating (no solver, hours).** Run §5 in full. Both lenses
> converge on this and it is the only step with no dependency on any open decision. Two of its
> outputs can *cancel the rest of this plan*: if `P₀ ≈ P*(A)` and the contested-among-the-13 count
> is small, the premium is not reachable by redrawing and the two-stage scheme was right all along.

## Files owned

- `td/` — **a new module and its tests only**; the exact paths to be fixed when the unit is
  launched, since ★6's answer may scope them narrowly (e.g. read-only analysis under
  `tools/measure/` rather than anything under `td/`)
- `docs/MODEL_U7-meas.md` (the measurement spec) · `docs/CODEVERIFY_U7-meas.md`
- `battery/results/<run-id>/` for outputs (gitignored)

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

**★6 — may a unit run code against the instance?** And, practically: the instance is at the main
checkout root, gitignored, not in this worktree (FRAME §5). Launching this unit requires deciding
where it runs. Both must be answered before launch.

## Branch

`wt/U7-meas` (from `wt/workflow-dryrun`)

## Stop rule

If a number cannot be computed because the instance is malformed or a defect in FRAME §5 bites
(the 6 coordinate-less zips, the headroom repairs, the 6-significant-figure rounding), report the
defect and the affected number — do not repair the data to get a number out.

**stop and report rather than improvise**
