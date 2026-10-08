# Carve-first: plan from a library of districts that pass M1 (draft for round 3)

The orchestrator's proposal, 2026-10-07, answering the owner's E4 request: "whatever methodology
we're using here should be investigated for a better and faster solution". Nothing here is
decided. It would replace the v2 loop (plan, carve, cut, re-plan, and "search layers" for added
splits).

## Why now
Under D3 and E2 every district's band is a fixed dollar interval:
- target × [0.85, 1.15], and [0.80, 1.15] for IFA;
- WIFI uses ±15% of its dollar average, which depends on K_WIFI.

The band does not depend on K. Under rule C each split state carves independently. So whether a
piece of σ attached to whole states A can be drawn is a fact about (σ, piece, A, band), not about
the plan. That allows carving **before** planning.

## Method
1. **Whole-state columns.**
   - Every connected set g of whole states with dollar mass in [L, U] (the master's support
     family restricted to all-whole) is checked once with the exact M1 gate on its ZIP union,
     as #127 did.
   - Columns that pass go into the library. A failure is a fact about g, never a ban on anything
     else.
2. **Carving patterns.**
   - A pattern p for a state σ is a partition of σ's ZCTAs into k_p pieces, each with an attach
     set A_i of whole states.
   - Each district piece_i ∪ A_i passes the gate and lies in [L, U].
   - The attach sets are disjoint, and none contains σ or another split state, which is rule C
     built in.
   - B's carver generates many varied patterns per (σ, k, attach choice): heuristic-first,
     judged by the gate, in parallel across states.
   - Each pattern records its states (σ plus every A_i), k_p, its districts' dollars, border_km
     and visual defects.
3. **Selection MILP** (set partitioning). The variables are x_g for whole columns and y_p for
   patterns.
   - Each state v is covered exactly once: Σ_{g∋v} x_g + Σ_{p: v∈σ(p)∪A(p)} y_p = 1.
   - At most one pattern per state σ: Σ_{p:σ(p)=σ} y_p ≤ 1. This is already implied by the
     coverage row.
   - Districts: Σ x_g + Σ k_p y_p = K.
   - Objective, lexicographic: splits Σ y_p, then cuts Σ (k_p − 1) y_p, then defects and shape,
     then balance (the worst column deviation, by an epigraph row).
4. **Certificate.**
   - #103's master gives s_lower, a lower bound over every C-rule plan.
   - The library MILP gives s_drawn, the best over the library.
   - If s_drawn = s_lower, the map is proved fewest-splits (in the stated domain). Otherwise it
     is reported as s_lower + g with g = s_drawn − s_lower.
5. **Growing the library (pricing).**
   - The LP relaxation's duals on the coverage rows price a new pattern for σ. The pricing
     problem is a carve with prizes on the attach states.
   - A heuristic pricing call per state adds patterns where they would improve the objective.
   - A master plan from #103 that reaches s_lower with a state σ split in a way the library
     lacks becomes a direct carve request for that σ.
   - Unknown carves leave the library unchanged: no ban, no cut. Every pattern in the library
     has passed the gate.
6. **Drawing.** The ledger is the union of the chosen columns. The gate re-runs on the assembled
   map as an integration check; a failure there is a bug, not a ban.

## What changes from v2
- **A:** unchanged (s_lower, grid, dollar adapter R1).
- **B:** becomes a pattern generator over (σ, k, attach choices), plus pricing calls.
- **P:** becomes the library builder plus the selection MILP and assembly.
- **The v2 cut machinery** (holder_nogood, support_ban, re-plan CLI with cuts, search layers)
  drops out of the main path. It could stay as a fallback.

## Known risks
- **Library completeness:** the answer is only as good as the library. g measures the loss, and
  pricing reduces it.
- **Size:** IFA's whole-state family was about 2,000 supports at K 46, and CA or NY in 4 pieces
  with attach choices could give hundreds of patterns. Measure on FI first.
- **The WIFI band depends on K_WIFI** (E3), so WIFI columns need a band per K, or WIFI is solved
  as whole states only at each K.
- **Balance:** each column's mass is fixed when it is generated, so balance can only be improved
  by more patterns, not by moving ZIPs after selection.
