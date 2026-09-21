# U2-stab: roster stability findings

Unit U2-stab (2026-09-02, v1, k = 13 of 111 reps).

1. **ρ does not enter stage 2.** `td/channel.py::gain_matrix` builds `g_ij` with no ρ term, so
   the induced-preference alignment (DOMAIN_economic-theory §2.4) is exact at every ρ. N2
   ("is ρ = 0") gates the EF1 claim (§2.1), not the stability claim.
2. **"Generically unstable" is a square-market intuition.** Holding k = 13 and growing n,
   greedy-versus-Hungarian agreement rises from 0.011 (n = 13) to 0.700 (n = 111) on iid values.
   At the real shape a small blocking-pair count, possibly zero, is the right prediction.
3. **A max-weight matching cannot be blocked by an unmatched agent** (swapping it in raises the
   objective). The 13 x 111 sweep is really 13 x 13; the unselected reps are outside
   stability's reach, which is why the envy-free-matching axiom (aignerhorev2022) is the only
   thing that speaks to the selection margin.
4. **Exact ties in `g` are structural.** `g_ij = B_j + (1-λ)(1-θ)·b_ij`, so every rep with no
   book in district j ties at `B_j`. State uniqueness as "per-round argmax unique", never "all
   values distinct"; the 6-significant-figure export needs a relative tolerance of at least
   1e-6 for that check.

`(1-λ)(1-θ) = 0.42` at the reference parameters reproduces the measured hold-versus-not swing
of about 42% to 0.0017 (`mem:model/reference-parameters`).

Citations that carried weight: `mem:refs/econ-theory-matching`.

Source: `.claude/agent-memory/modeler/project_u2-stab-traps.md` (2026-09-02).
