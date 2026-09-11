# Phase 0 measurements (2026-09-05, all through a verifier)

v2 whole instance, the committed k = 18 draw.

- `B_tot = 3268.4069219934404` (`premium.py::measure()`, eq. `decomp`'s `W₀`).
- (★) screen: `96.554063` at `P_S`, `96.793010` at `P₁₈`.
- Slack over `EG_{S₁₈}`: **0.0219 at `P_S`** (v1 0.0641; the screen tightens 2.9x on U11's
  per-roster prune) and 0.2609 at `P₁₈` (v1 0.1051; the roster-free `P_k` rung loosens 2.5x).
  **Do not compare across rungs.**
- `D(g) = 0.148` nats on the delivered draw; `D(M) = 1.5e-4` at a 1.37% mass spread; realised
  gain spread 60.17%.
- Premium window **0.890** nats exact (0.912 is the first-order sum; the 0.022 gap is 4.5 times
  the tier-2 floor), inverting `D(g)` by **6.0x**.
- Saturation `ΣT/ΣM = 29.588%`. The other definition, `Σ(T+S_free)/ΣM`, reads 29.8107% on v2
  (`docs/units/P0C-screen.md`); state which one you quote.
- Splits at `δ₀`: a-priori cap 35, sharp `k-1+t` cap 33 (t = 16), **measured 24**. Quote the
  measured count, never the cap.
- Gate gains run 211.786 to 228.663 (16 of 18 near 211.79), clearing the 140.638 floor by 1.506x.

The screening bound behind (★): `mem:domain/optimization-verdicts`. The `k-1+t` split bound:
`mem:model/u9-bandthm`.

Source: `main:STATE.md` `## Facts` (a3924e8).
