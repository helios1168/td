# Synthetic case-study plan — pre-merger → Nash → contiguous MINLP

**Date:** 2026-08-27. **Scope:** `synth.py` battery, executed in parallel (one subagent
per case). Every case produces a three-stage figure — pre-merger territory maps and book
distributions, the exact per-pair Nash division, the contiguous MINLP solution — plus a
metrics JSON with the optimality certificate (bound gap), fragmentation before→after,
perimeter, and the product cost of contiguity.

**Pipeline:** `code/case_pipeline.py` — instance → `validate` → `census` (split=True,
d=(0,0) per the review) → `nash_exact` per overlap pair → `solve_contiguous_nash` per
pair. Dense components are solved pair-by-pair over each pair's own overlap zips as an
*illustration only* (two-player fairness does not compose there; figures carry the
caveat and the pairs are starred).

**Acceptance per case:** `validate()` clean; every Nash solve `optimal` with
|bound gap| < 1e-8; both gains positive; contiguous solve reaches 1/1 components;
figure renders with all three rows populated.

| # | Case | Instance(s) | Question it answers |
|---|------|-------------|---------------------|
| C1 | Baseline aligned | S1_aligned, seeds 1 & 2 | Sanity + seed stability: clean 1-1 pairs, small contiguity cost, certificates hold across seeds |
| C2 | Entangled | S2_entangled (alpha=0) + alpha=0.5 variant | Kill criterion 1 territory: what per-pair solves look like inside a dense blob, and how the picture degrades between alpha=0.5 and 0 |
| C3 | Slivers | S3_slivers, census at min_share ∈ {0.5%, 2%, 8%} | Does the division itself (not just the census verdict) move with the trim threshold; orphan share alongside |
| C4 | Book correlation | S4_separate (rho=−0.5, corr≈−0.1) vs rho=+1.0 (corr≈+0.9) | Separate vs heavily contested books: gains symmetry, interpenetration of the Nash map, contiguity cost at the two extremes |
| C5 | State borders | S5_states, respect_state False vs True | Kill criterion 3: what the state constraint costs on top of contiguity, and whether it fragments the feasible set |
| C6 | Tight headroom | S6_tight (sat=0.55) vs default sat=0.12 | Headroom stress: how the split and gains change when the market is nearly saturated; confirms bargaining set nonempty under d=0 |
| C7 | Scale | S1-style, n=400 | Solver behaviour at 2× size: iterations, wall time, whether certificates still close |
| C8 | Compactness frontier | S1 largest pair, rho sweep {0, 1e-4, 5e-4, 2e-3, 8e-3, 3e-2} | Trap 7 quantified on the battery: product vs perimeter frontier, where the knee sits |
| C9 | Heavy sales tail (added post-hoc) | S7_heavytail, seeds 1 & 2 (same geometry as C1) | Does commercially-concentrated (dPlN heavy-tailed) A_z/B_z, vs. population-like lognormal, change contiguity convergence independent of graph topology? See FINDINGS.md addendum + code/TAIL_DISTRIBUTION_NOTE.md |

**Not in scope this round:** capacity fields (`cap_a/cap_b` are generated and ready but
objection 2's operational use needs a non-book-size capacity signal first);
theta-heterogeneity (open half of objection 2); leximin over dense components (unbuilt).

**Deliverables:** `figures/C*.png`, `figures/C*.json`, findings summary; committed to
`Work/td/battery/` alongside this plan.

**Post-hoc addendum (same day):** C9 added after `synth.py` gained a dPlN tail dial for A_z/B_z (`code/TAIL_DISTRIBUTION_NOTE.md`); run through the same case_pipeline.py pipeline as C1-C8, not a separate script.
