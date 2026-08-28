# Battery findings — pre-merger → Nash → contiguous MINLP (C1–C8)

**Date:** 2026-08-27. Companion to `RESEARCH_PLAN.md`. Fifteen runs across eight cases,
drafted in parallel by subagents, then **re-run as one batch under the final code** so
every number below is on a single convention. Full metrics in `figures/C*.json`; run log
in `figures/battery_run_log.json`.

---

## 0. Code changes made this session (read first)

1. **`territory.py` / `districting.py` migrated to `d=(0,0)`.** The handoff code still
   subtracted pre-merger books (`Sa, Sb = A.sum(), B.sum()`) in `prefix_table`,
   `nash_exact`, and `solve_contiguous_nash` — the baseline the review reversed. Caught
   when C6_tight produced an *empty bargaining set* (best product −243) under the old
   baseline: the exact lambda* pathology the review says d=0 removes. Migration is three
   one-line changes (commented in place); validated against brute force (40/40 exact at
   n=12) and against `review/code/dzero.py` with `da=db=0`. Gains are now bundle
   utilities, positive by construction.
2. **HiGHS tolerance fix in `nash_exact`.** Default MIP integrality tolerance (1e-6)
   lets binaries sit ~1e-7 off {0,1}; the rounded incumbent then appears to violate its
   own tangent cut by more than `tol=1e-9` and the outer approximation stalls re-adding
   an identical cut forever (first hit on C4's A3/B3). Fix: pass
   `mip_feasibility_tolerance=1e-9, primal_feasibility_tolerance=1e-9`.
3. **`case_pipeline.py`** (new): instance → validate → census(split=True) → exact Nash
   per overlap pair → `solve_contiguous_nash` per pair → 3-row figure + metrics JSON.
   Prefix-fallback results are labelled `exact=false` rather than dropped.

## 1. Verification summary (final batch)

All 15 runs: `validate()` clean; **every exact Nash certificate at machine precision
(max |bound gap| 7.5e-14 across ~70 pair solves)**; all gains positive (d=0); contiguous
product ≤ free product everywhere. Contiguity MINLP solved 73/77 pair instances; the 4
failures are themselves findings (below): C1-seed2 A0/B0 (69 zips, iteration limit),
C5-respect_state A2/B2 (61 zips, 5 in-state pieces), C7 A3/B3 + A0/B0 + A1/B1
(205/125/44 zips, time/iteration limits at n=400).

| case | corr(A,B) | census comps | 1-1 opp share | pairs | cont OK | cont cost % range |
|---|---|---|---|---|---|---|
| C1 seed1 | +0.58 | 4 | 100% | 4 | 4/4 | 0.31–1.08 |
| C1 seed2 | +0.88 | 4 | 100% | 4 | 3/4 | 0.42–1.45 |
| C2 alpha=0 | +0.69 | 1 | 0% | 10 | 10/10 | 0.11–0.43 |
| C2 alpha=0.5 | +0.69 | 2 | 31% | 9 | 9/9 | 0.00–1.17 |
| C3 (3 thresholds) | +0.55 | 3–4 | 42–98% | 4 | 4/4 | 0.14–2.20 |
| C4 separate | −0.10 | 4 | 100% | 4 | 4/4 | 0.42–1.10 |
| C4 contested | +0.90 | 4 | 100% | 4 | 4/4 | 0.44–1.32 |
| C5 free | +0.58 | 1 | 0% | 8 | 8/8 | 0.00–1.18 |
| C5 respect_state | +0.58 | 1 | 0% | 8 | 7/8 | 0.00–2.37 |
| C6 tight (sat .55) | +0.58 | 4 | 100% | 4 | 4/4 | 0.00–2.67 |
| C7 n=400 | +0.74 | 4 | 100% | 4 | 1/4 | 1.03 (solved pair) |
| C9 heavytail seed1 | -0.02 | 4 | 100% | 4 | 4/4 | 1.58-2.88 |
| C9 heavytail seed2 | +0.10 | 4 | 100% | 4 | 3/4 | 1.50-4.83 |

**Addendum, same day, later session.** `synth.py` gained a double Pareto-lognormal (dPlN) tail dial for `A_z`/`B_z` -- plain lognormal by default, bit-for-bit backward compatible (verified against all 12 existing seeded scenarios) -- with a new `S7_heavytail` scenario (`sales_tail_alpha=1.0, sales_tail_beta=3.5`: Zipf-like upper tail, steeper lower tail, per Eeckhout 2004 AER / Reed 2001-2004 / Giesen, Zimmermann & Suedekum 2010 JUE -- see `code/TAIL_DISTRIBUTION_NOTE.md`). Added as **C9**, same geometry as C1's two seeds (alpha=1, 4x4 reps), to isolate whether commercially-concentrated sales values (vs. population-like lognormal) change contiguity convergence independent of graph topology. See §2b.

## 2. Case findings

**C1 — baseline & seed stability.** Structure reproduces across seeds: 4 clean 1-1
pairs, 100% opportunity, near-symmetric gains (g_a/g_b typically within 2–4%),
contiguity cheap. One honest failure: seed-2 A0/B0 (69 zips, the most fragmented
free-Nash pair under the higher corr 0.88) hits the contiguity iteration limit even at
4× budget — the outer approximation + separator-cut loop is not guaranteed to converge
within budget on larger contested pairs.

**C2 — entanglement (kill criterion 1 territory).** At alpha=0.5 the census still
isolates one clean 1-1 component with 31% of opportunity; at alpha=0 the entire market
is one dense 4A×5B component — 1-1 share 0%, every one of 10 pair solves an
illustration only. Certificates stay pristine, which is exactly the trap: each bilateral
solve looks perfect while no component-level fairness is defined. This is the concrete
case for leximin-over-components; at alpha=0 that regime swallows 100% of opportunity.

**C3 — sliver threshold.** The division is **not** threshold-sensitive; only the census
bookkeeping is. Across min_share 0.5%/2%/8% the four solved pairs' zip assignments are
set-identical (verified), products identical to 6 decimals; what moves is the headline
verdict (1-1 share 42% at 0.5% vs 98% at 2–8%) because two sub-1%-of-opportunity sliver
edges glue components at the low threshold. On real data: report the census at a
threshold sweep and treat pair-level assignments, not component counts, as the robust
quantity; a "dense" verdict that appears only below ~1% via sub-1% edges is sliver noise.

**C4 — book correlation (kill criterion 4).** At corr≈−0.10 the map leans toward legacy
books and contiguity is nearly free; at corr≈+0.90 gains become strikingly symmetric
(near-proportional books mean many near-equal splits) while fragmentation and perimeter
rise and contiguity costs a bit more. Near-zero correlation does *not* make the
machinery trivial — with S_a/S_b ≈ 5/3 plus the theta and lambda terms, a substantial
minority of zips still cross against their larger raw book.

**C5 — state borders (kill criterion 3).** 18.6% of adjacency edges cross state lines;
the largest pairs span 4–5 states and shatter into up to 5 in-state pieces. Small pairs
pay ≈0 extra; the biggest pair (A2/B2, 61 zips, 5 pieces under the cut) fails to certify
even at triple budget. Verdict: not a hard kill (piece-wholesale assignments keep the
problem feasible) but the state constraint, not fairness, determines what is achievable
for multi-state overlaps — and the current cut formulation cannot certify those.
Settle the state-scope question with distribution before tuning anything downstream.

**C6 — tight headroom.** With sat=0.55 and M_z forced near the pointwise bound (min
slack 1.8% vs 314% loose), the division itself barely moves (k shifts ≤1 zip per pair);
products scale up ~2.6–2.8× and gains tilt mildly toward the larger book. Feasibility
never degrades — under the old baseline this same instance was *infeasible* (empty
bargaining set on A1/B1), confirming lambda* was an artifact of the baseline, not of
tight markets. Solver behaviour unchanged (4–7 iterations, machine-precision gaps).

**C7 — scale (n=400).** `nash_exact` scales exactly as claimed: 5–10 cut rounds
regardless of size, ~2.5 s on a 205-zip pair, machine-precision certificates. The
**contiguity MINLP is the scale bottleneck**: 3 of 4 pairs fail (HiGHS 20 s/round time
limit at 205/125 zips; cut-loop thrash at 44). The prefix heuristic's shortfall on the
205-zip pair is 0.007% at ~5,600× speedup — right screening tool at scale, with exact
solve reserved for final certification. National scale needs the lazy-callback solver
already flagged in HANDOFF §6.

**C8 — compactness frontier (trap 7 quantified).** Frontier on the largest S1 pair
(62 zips): rho=0 gives perimeter 31 at 0.08% below the unconstrained product; the knee
is the rho∈[2e-3, 8e-3] shelf — perimeter 14 (vs 31) for 0.60% of product — and
rho=3e-2 buys one more edge at ~5× that cost. rho=2e-3 confirmed as a sound default:
sits on the knee, and pricing the perimeter also kills degenerate near-ties (fastest
solves). Solver-reported perimeter is meaningless at rho=0 (unpriced y-variables) —
recompute from the assignment.

**C9 -- heavy sales tail (independent risk factor, not just topology or scale).** Same geometry as C1 (identical positions, adjacency, and rep territories at each seed, confirmed by identical pair sizes) -- only `A_z`/`B_z`'s noise changed from plain lognormal to dPlN. Effect is not just "contiguity got a bit more expensive": cost% roughly doubles-to-quintuples across every pair that still solves (e.g. seed1 A0/B0: 0.88% -> 2.69%; seed2 A1/B1: 0.53% -> 2.44%), iteration counts rise even where convergence holds (seed1 A1/B1: 4 -> 17 iters), and -- the striking part -- **the point of failure moves**. Seed2's A0/B0 (69 zips, the pre-disconnected 67+2-zip pair that hit the iteration limit under C1) now converges cleanly in 16 iterations under the heavy tail; meanwhile seed2's A2/B2 (31 zips, a single connected component that solved trivially in 2 iterations under C1) now hits the iteration limit. Verdict: value concentration is a third, independent contiguity-convergence risk mechanism, distinct from the pre-existing-graph-disconnection and pure-scale mechanisms already found (C1-seed2/C5/C7) -- it strikes previously-easy, small, single-component pairs and does not track pair size or topology. A fix aimed only at topology (component-quotient preprocessing) or only at scale (lazy-callback solver / flow formulation) is not guaranteed to help here; both should be stress-tested against S7_heavytail before being called sufficient. Whether real annuity-wholesaler sales are actually this concentrated is unresolved -- see `code/TAIL_DISTRIBUTION_NOTE.md`'s caveat that ZCTA-level population itself looks near-lognormal (USPS boundary redrawing smooths it), while commercial/advisor-office activity plausibly does not.

## 3. What this changes upstream

- The d=0 migration is now **in the code**, not just the review: `territory.py` and
  `districting.py` match the settled decision. The paper edits (HANDOFF_REVIEW §2) are
  still pending in the .tex.
- Contiguity convergence is the weakest link (C1s2/C5/C7): worth a flow-formulation or
  lazy-callback variant before real data, since real pairs will be larger than 62 zips.
- The census instrumentation is trustworthy (C3), the dense regime is real and big
  (C2), and the state constraint is the binding one to settle with distribution (C5).
- Everything here is synthetic: structural claims should transfer; magnitudes will not.
- C9 shows contiguity-convergence risk has (at least) three independent causes -- graph topology, pure scale, and value concentration -- not one. A convergence fix should be validated against all three, not just the size/topology cases already run.

## 4. Files

```
battery/
  RESEARCH_PLAN.md          the case plan
  FINDINGS.md               this file
  code/case_pipeline.py     the per-case pipeline (figure + metrics)
  code/run_battery.py       batch runner (final consistent run)
  code/c8_rho_sweep.py      the rho frontier
  figures/C*.png, C*.json   15 figures + metrics, battery_run_log.json
../code/territory.py        MODIFIED: d=(0,0) + HiGHS tolerances
../code/districting.py      MODIFIED: d=(0,0)
../code/synth.py            MODIFIED: dPlN tail dial (m_tail_*, sales_tail_*), S7_heavytail scenario -- backward compatible, see TAIL_DISTRIBUTION_NOTE.md
../code/TAIL_DISTRIBUTION_NOTE.md   what changed in synth.py and why (cites
                             Eeckhout 2004; Reed 2001/2002/2004; Giesen et al. 2010)
```
