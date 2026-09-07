---
name: domain-economic-theory-td
description: Traps, conventions and prior verdicts for /domain economic-theory on the td national-channel project — what was rejected, which FRAME §6 numbers drive the choices, which FOUNDATIONS entries matter
metadata:
  type: project
---

Running notes for `/domain economic-theory` on td (national channel territory design).
Latest run: **2026-09-03**, branch `wt/A1`, A1 charter (joint coverage optimisation).

**Why:** `docs/foundations/DOMAIN_economic-theory.md` gets rewritten per track charter; each rewrite must
supersede the last without breaking `docs/foundations/BRIEF.md` / `docs/units/*.md` cross-references.
**How to apply:** read this before planning; it saves re-deriving the same rejections.

## Hard conventions (violating these breaks other files)
- **Preserve section numbering.** `BRIEF.md`, `units/U1-cert|U2-stab|U3-inv|U5-crit|U6-sel.md`
  and `LIT_economic-theory.md` cite by number: §2.1 EF1/PO · §2.2 EG/CEEI · §2.3 criterion ·
  §2.4 stability · §2.5 cooperative game · §2.6 the 98 as claimants · §2.7 strategy-proofness ·
  §3's five statements · §4 steps with D1–D5 · §5 N1–N6 · §7 hand-offs · §8 Q1–Q8. Append
  new material (§2.8+, N7+, D6+, Q9+); never renumber.
- **Two citation pools, and they are different files.** `~/resources/economic-theory/FOUNDATIONS.md`
  (95 entries, cite in **bold**) and `docs/foundations/LIT_economic-theory.{md,bib}` (46 entries, cite in
  `code`). `fotakis2014` is in **neither** — it lives in `literature/RESEARCH_ADDITIONS.bib`; mark it
  ★`fotakis2014` and use it for positioning only.
- `LIT_economic-theory.md` is inherited unchanged across tracks. A new lit run must append a
  dated section, not rewrite it.

## Verdicts already reached — do not re-derive
- **Retired for good:** Monte-Carlo Shapley over 111 players (`littlechild1973` + additivity
  gives a closed form, `O(#zips·n log n)`); the Bondareva–Shapley balancedness LP as the first
  core test (`deng1999`'s integrality check replaces it); "is the EG bound decorative?"
  (answered NO by U1-cert P3, `≤ k−1` splits); "is ρ = 0?" (YES, `docs/units/U2-stab.md`
  `## Verify` row 1).
- **Ruled out on hypothesis checks, with the reason:** **Shapley & Shubik 1971** assignment game
  (needs transferable utility; FRAME §7 forbids transfers) · **Shapley & Scarf 1974** / TTC
  (needs initial endowments; greenfield) · **Kelso & Crawford 1982** gross substitutes
  (preferences are aligned/vertical, not horizontal).
- **★8 (`fotakis2014` / Gibbard–Satterthwaite, both withdrawn) is now `CLAUDE.md` trap 17.** Do
  not restate the finding here; the misreporting exposure (98-of-111 inflation incentive,
  A1-Q4's non-obvious-manipulability) remains live.

## What FRAME §6 numbers implied (numbers are in `docs/units/U1-cert.md`, `U7-meas.md`)
δ and ε are two knobs, not one; the EG−V gap's extremiser is over an infeasible set, `EG^bal`
replaces it; the premium roster gap is the whole collective claim of the 98; 83 contested zips
make `f` near-modular and maximally gameable; the Nash-tie margin means `S₁₃` is non-unique.

## The best content the 2026-09-03 run produced (reuse it)
**The invariance split.** Under `G = (ℝ_{>0})^R` acting on reported books: at fixed roster the
EG argmax, prices and band duals are invariant (value shifts by `Σ log γ_i` — **Nash 1950**
scale invariance); `max_S EG_S` is **not** invariant, so selection is manipulable. Caveat P-G3:
the programme's `u_i` is affine, not homogeneous, in `S_i` because of the `c2·T_z` coupling, so
the theorem does not apply as-is to the model as built. Check the coupling before quoting.

## Hand-offs that stay open every run
Regional bias in `M` (**A4**/U5) → econometrics — highest value, invalidates every certificate
silently. Displacement metric → optimization. Tier-2 noise floor (U6) → econometrics.
No `DOMAIN_econometrics.md` exists (★7).

See also [[domain-lens-td-workflow]].
