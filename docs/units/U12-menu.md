# Unit U12-menu — the sponsor menu: `(δ, V, book share, μ, fairness verdicts)`, the a-priori softness bound, and the tie-break text

`DOMAIN_economic-theory` §2.3, §2.8–§2.10, §4 steps 2–3 and 7; `LENS_GROMOV` M11.2–M11.3;
absorbs [pred]'s U5-crit. Gated on U8-band (the curve and duals) and U11-roster (the intervals);
U13-base supplies the baseline point when it exists.

## Spec (verbatim from `docs/DOMAIN_economic-theory.md` §2.9)

> **How to put it to the sponsor.** As a **menu, not an elicitation**. Compute
> `EG^bal_{S₁₃}(δ)` on the grid … plot `(δ, V)` with the delivered MNW point marked … and hand
> over three columns per row: the band, the continuity value in book share, and the fairness
> verdicts of §2.8's table.
> **The second knob, and it must be on the same page.** `δ` is on `M`; `ε` is on `g`. The
> measurement says they came apart by 77.6×. A sponsor asked only for `δ` has answered a
> question about territory size and not about what any wholesaler receives.
> [§2.9, the distinction] Computing `μ` therefore does not elicit the sponsor's rate, and it
> must not be presented as though it did.

## Files owned

`docs/MODEL_U12-menu.md` (the menu, its derivation and the sponsor-facing page as an appendix) ·
`docs/VERIFY_U12-menu.md` · `docs/artifacts/U12-menu/**` (the arithmetic that fills the table,
reading U8/U11/U13 outputs; no solves of its own).

## Files forbidden

Every other unit's owned files · `docs/FRAME.md` · `docs/BRIEF.md` · `docs/APPROACHES.md` ·
`docs/LENS_*.md` · `docs/DOMAIN_*.md` · `docs/LIT_*` · `docs/channel_note/**` · `CLAUDE.md` ·
all of `td/`, `tests/`, `tools/` (read-only).

## Agent → verifier

`modeler` → `math-verify` (the verifier checks every number in the table against the U8/U11/U13
artifacts and the `breugem2022` bound's hypotheses).

## Acceptance

1. A table with one row per `δ ∈ {δ₀, 0.02, 0.05, 0.10, 0.33}`: `EG^bal` (nats), the gap to the
   delivered draw in nats **and as a geometric-mean-gain percentage** (`e^{Δ/k} − 1`), premium in
   book share, the aggregate band dual (the MRT, labelled as such, with left/right derivatives at
   any kink), N8 (how many bands bind, sign of `ν`), N9 (proportionality verdict), the FEFx/EF1
   verdict per `kawase2026balanced`, and the U11 interval where the row depends on `S₁₃`.
2. The MNW point `(δ₀, 59.9375)` and the unconstrained endpoint marked on every rendering
   (trap 2); the A3 baseline point from U13 if available.
3. `breugem2022vertical`'s a-priori bound on the utility lost to per-player constraints
   evaluated from FRAME §6's high-level parameters, placed beside U8's computed curve, with the
   hypotheses checked and the verdict "bound is / is not informative at 5e-3".
4. The `(δ, ε)` two-knob statement with the 77.6× number, `haimes1979tradeoffs`'s MRT/MRS
   procedure as the framing, and the explicit sentence (from U9 P2-price) that the prices are
   multipliers, not competitive prices.
5. The tie-break disclosure paragraph (★10 / D7): the named tie-break, the margin, the
   near-optimal roster set from U11.
6. `math-verify` VERIFIED on the arithmetic and on the `breugem2022` application; PLAUSIBLE or
   better on the fairness-verdict mapping.

## Numbers to compute first

None of its own; it consumes U8 (`EG^bal`, `μ`, N8, N9), U11 (intervals), U13 (the baseline
point), and computes `e^{Δ/k} − 1` and the `breugem2022` bound from FRAME §6.

## Inputs to read (paths and sections only)

`docs/DOMAIN_economic-theory.md` §2.3, §2.8–§2.10, §4 steps 2, 3, 7, §5 N4, N7–N9, N11 · the
2026-09-03 section of `docs/LIT_economic-theory.md` (`echenique2021constrained`,
`kawase2026balanced`, `breugem2022vertical`, `haimes1979tradeoffs`, `acland2023weighting`) ·
`docs/LENS_GROMOV.md` M11–M13 · `docs/FRAME.md` §3 (Tolerance), §6, §8 A1/A5/A6 ·
`docs/units/U5-crit.md` (what it absorbs) · `docs/MODEL_U8-band.md`, `docs/MODEL_U11-roster.md`
and their `battery/results/` outputs · `docs/MODEL_U13-base.md` if present.

## Open questions for ★0

★9 (the sponsor's `δ`) and ★4 (now `ε`) are *answered by choosing a row of this menu*; ★10 is
served by item 5. The unit must not pick the row.

## Branch

`wt/A1` (or `wt/U12-menu` from `wt/A1`)

## Stop rule

If U8 reports softness across the plausible band (D1′), the menu is one line — "every row
staffs the same within 5e-3 nats" — and the unit stops there; do not pad it. If U11's
near-optimal set is large, lead with that and report the rows as intervals; do not collapse
them to points.

**stop and report rather than improvise**
