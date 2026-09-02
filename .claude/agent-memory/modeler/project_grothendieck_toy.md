---
name: grothendieck-toy-unit-traps
description: Traps and findings from unit T1-cut of the grothendieck-toy scratch project (two-wholesaler zip split) — spec/lens mismatch, no FOUNDATIONS, exact-arithmetic convention
metadata:
  type: project
---

Scratch project `/Users/ntlee/tmp/framework-scratch/grothendieck-toy` (framework stamp 0.1-dev) is a dry-run toy for the modeler→math-verify→python-typed→code-verify workflow.

**2026-09-02 — unit T1-cut (spectrum / deficiency / price of connectivity), findings:**

- **Trap: the brief's "verbatim" spec is not in the section it names.** `docs/units/T1-cut.md` quotes `Σ`, `δ`, `δ_free`, `π` as verbatim from `docs/LENS_GROTHENDIECK.md` "Concepts introduced". That table actually introduces `𝒫(G)`, cut parameter, `σ`, `D(k)`, straddling bound, wall/chamber — none of `Σ/δ/π`. The brief is self-contained so I proceeded and recorded the discrepancy in MODEL §8 rather than blocking. Expect the same drift in sibling briefs; check the cited section before assuming the quote is real.
- **No FOUNDATIONS and no `docs/LIT_*.md` exist in this repo.** Cite nothing; label every proposition [proved]/[sketch]/[conjectured].
- **Python is `/usr/bin/python3` (3.9.6, stdlib only) — there is no `.venv`.** Scratch scripts go under `toy/scratch/`.
- **Headline result:** `π = 0` for the toy instance (`δ = δ_free = 1/2`). Connectivity, which FRAME §4 marks as the hard/expensive constraint, is free; the obstruction is parity (`W = 15` odd, integer weights). Any downstream unit that assumes connectivity is what makes the frame's fairness notion empty is wrong.
- **FRAME numbers all checked out** (n=6, W=15, fair share 7.5); nothing in §5–6 was wrong.
- **Convention I had to fix, not inherit:** `Σ` reads values of *both* parts of each unordered cut. Harmless here (`Σ = W − Σ`) but load-bearing if a later unit introduces two valuations `w_1 ≠ w_2`.

**Why:** these are workflow-level traps, not derivable from reading the current files quickly.
**How to apply:** on any further unit in this repo, verify the brief's quoted spec against its named source section before modelling, and use exact `Fraction`/integer arithmetic (never float) so the enumeration doubles as the proof.
