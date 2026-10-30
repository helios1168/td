# The analysis's model: what opportunity and sales are, and how channels and territories see them

The analysis is rebuilt from this model (owner, 2026-10-29). Every output is a measure aggregated along a map (SQL:
`GROUP BY` the map's value, `SUM`), so the model is complete when every map is defined. Status: **given** (in the
data), **settled** (rule in `DATASET_LOG.md` Settled), **open** (its question in the log's index). A SQL file names
the symbols it implements; where a query and this file disagree, fix this file. Derivation:
`notes/2026-10-29_snowflake-conceptual-model-research.md`.

## Sets and measures

| symbol | meaning | status |
|---|---|---|
| S = {1, 2} | source firms (the insurers) | given |
| Z, P | ZIPs, products | given |
| D | distributors (broker-dealers), plus ⊥_D for an unknown distributor | open: the unit, Q27 |
| X = Z × D × P | market cells, one period (fiscal year 2025), with projections π_Z, π_D | given once D is |
| W_s | wholesalers of source firm s; *seller* and *holder* are roles, not kinds of person | given |
| C_s | firm s's current channel labels | given |
| N | the new channel labels, shared by both firms | being designed; shared labels: Q6 |
| Ô_s : X → ℝ≥0 | firm s's opportunity estimate (estimated market sales, not business anyone can necessarily win) | given |
| M : X → ℝ≥0 | the market, M = max(Ô₁, Ô₂): sets the amount only, not a channel | settled 2026-10-24; same measure? Q23 |
| σ_s : X × W_s → ℝ | firm s's sales in cell x credited to wholesaler w | given |

## Maps

| map | type | meaning | status |
|---|---|---|---|
| credit | sale → W_s | who is credited with a sale (not necessarily who caused it) | given, never changes |
| κ_s | X → C_s | current channel of a cell in firm s's labels (vendor channel plus your query's firm rules) | given; must cover every cell with M > 0: label source Q30 |
| λ_s | X × W_s → C_s | the label recorded on a sale; can depend on the seller (`mm_query.sql:420`, the IMO rule) | given; λ_s = κ_s? Q28 |
| ν | X → N | new channel of a cell | being designed; ν = ν_D ∘ π_D (I3)? Q27 |
| H_s | C_s × Z → subsets of W_s | holders of a channel × ZIP: 0, 1 or 2+ (coverage; may overlap) | given |
| k_s | each (c, z) → weights over H_s(c, z) summing to 1 | how a cell splits among its holders | today all on the lowest ID; Q29 |
| τ_s | N → C_s, partial | which of firm s's current channels serves a new channel's ZIPs (the bridge) | missing, Q29 |

## States and views

A **state** is one set of channel definitions applied to the same data; nothing else differs. **Current**: per source
firm, labels C_s, classification κ_s, coverage H_s directly. **New**: labels N, classification ν, coverage through τ_s
then H_s. Aggregating μ along f: f_*μ(b) = Σ μ(a) over all a with f(a) = b.

| view | current (per firm s) | new |
|---|---|---|
| 1. channel × ZIP | (κ_s, π_Z)_* M | (ν, π_Z)_* M |
| 2. reclassification | (κ_s, ν, π_Z)_* M; a cell **stays** if κ_s(x) = τ_s(ν(x)), else it **moves** | — |
| 3. coverage | holder w gets Σ_x M(x) · k_s(κ_s(x), π_Z(x))(w) | the same with τ_s(ν(x)) for κ_s(x) |
| 4. landing (placement) | (λ_s or κ_s, π_Z, id_W)_* σ_s | (ν, π_Z, id_W)_* σ_s |
| 5. credit | (pr_W)_* σ_s | identical: it uses no channel map |

No holder (⊥) has three causes, reported apart: unknown distributor (d = ⊥_D), no translation (τ_s undefined), no
coverage (H_s = ∅). A share is defined only when numerator and denominator pass through the same map: a holder's
territory share = sales sent through k_s to w ÷ market sent through k_s to w. Which one ranks a wholesaler: Q31.

## Invariants

| | equation | status |
|---|---|---|
| I1 | territories fixed: H_s and k_s are the same in both states; new-state holders come only through τ_s (no new assignments) | settled, owner 2026-10-29 |
| I2 | credit fixed: view 5 uses no κ or ν | settled, owner 2026-10-29 (holds by construction) |
| I3 | in the new state the channel depends on the distributor only: ν = ν_D ∘ π_D | stakeholder, 2026-10-29; unit and product: Q27 |
| I4 | the market is the same in both states, so views 1-2 total Σ_x M(x) in each; a gap means something other than classification changed | proposed (session); the first must-be-zero check |

## Vocabulary

| instead of | say |
|---|---|
| op moves | reclassified (off the diagonal of view 2) |
| attributed | credit (sale → person), placement (amount → channel × ZIP) or coverage (cell → holder) |
| who did it | credited seller |
| firm | source firm, or distributor |
| channel | label (of a state), vendor channel (an observation on Ô_s) or team (who works which channel) |
| territory | coverage (a footprint with its channel and holders; may overlap) |
| market share | cell share (sales placed ÷ market) or territory share; a seller is ranked by contribution |

## Example

Made-up amounts. Cell x = (z, d, p) with M(x) = 10; κ₁(x) = IFA; H₁(IFA, z) = {w_a}; ν_D(d) = National. Sale
σ₁(x, w_b) = 2, seller w_b an FI wholesaler (λ₁ = FI).

- View 1: IFA × z holds 10 now, National × z holds 10 after; both states total 10 (I4).
- τ₁(National) undefined: view 2 counts x as moved; view 3 takes 10 from w_a to ⊥ (no translation).
- τ₁(National) = FI with H₁(FI, z) = {w_c}: x moves (IFA ≠ FI) and its 10 goes from w_a to w_c.
- w_b keeps the 2 in both states (view 5). It is placed on National × z after; now on FI × z by λ₁ or IFA × z by
  κ₁ (Q28).
