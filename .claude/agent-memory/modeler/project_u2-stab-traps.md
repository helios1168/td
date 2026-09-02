---
name: u2-stab-traps
description: Traps and corrections found while modelling unit U2-stab (roster stability) on the national-channel territory project, 2026-09-02
metadata:
  type: project
---

Unit U2-stab (2026-09-02) hit four things worth carrying into later economic-theory units on
this project.

**Why:** each one either contradicts a brief/plan premise or saves a later unit a wrong turn.
**How to apply:** check these before restating the corresponding premise.

1. **`ρ` does not enter stage 2.** `td/channel.py::gain_matrix` builds `g_ij` with no `ρ`
   term, so the induced-preference alignment (DOMAIN §2.4) is exact at every `ρ`. DOMAIN §5's
   N2 ("is ρ = 0") gates the EF1 claim (§2.1), **not** the stability claim. The U2-stab brief
   assumed otherwise.
2. **`LIT_economic-theory.md` §0.4's "generically unstable" is a square-market intuition.**
   Holding k=13 and growing n, greedy-vs-Hungarian agreement rises 0.011 (n=13) → 0.700
   (n=111) on iid values. At the real 111-of-13 shape a *small* blocking-pair count, quite
   possibly zero, is the right prediction — not "will find pairs".
3. **A max-weight matching can never be blocked by an unmatched agent** (swap it in and the
   objective strictly rises). So DOMAIN §3 item 4's `13 × 111` sweep is really `13 × 13`; the
   98 unselected are structurally outside stability's reach, which is why the envy-free-matching
   axiom (aignerhorev2022, absence A3) is the only thing that speaks to the selection margin.
4. **Exact ties in `g` are structural, not measure-zero.** `g_ij = B_j + (1−λ)(1−θ)·b_ij`, so
   every rep with no book in district `j` ties at `B_j`. Uniqueness hypotheses must be stated
   as "per-round argmax unique", never "all values distinct". The 6-significant-figure export
   rounding (FRAME §5) means that check needs a relative tolerance ≥ 1e-6.

Also: `(1−λ)(1−θ) = 0.42` at the reference parameters reproduces FRAME §6's measured
"hold-vs-not swing ≈ 42%" to 0.0017 — a free consistency check on any reading of the model.
See [[foundations-econ-theory-matching]].
