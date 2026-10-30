# The analysis's model: what opportunity and sales are, and how channels and territories see them

The analysis is rebuilt from this model (owner, 2026-10-29). Every output is a measure aggregated along a map (SQL:
`GROUP BY` the map's value, `SUM`), so the model is complete when every map is defined. Status: **given** (in the
data), **settled** (rule in `DATASET_LOG.md` Settled), **open** (its question in the log's index), **parked**. A SQL
file names the symbols it implements; where a query and this file disagree, fix this file. Derivation:
`notes/2026-10-29_snowflake-conceptual-model-research.md`. `s1_opp_sales.sql:N` cites the owner's query in
`$TD_REPO/owner_sql/` at the version its `DATASET_LOG.md` entry pins.

The two source firms are analysed separately, each with its own data, on one common market metrics schema (owner,
2026-10-29 and 2026-10-30). Everything below is per source s; only Z, P, D and N are shared, and nothing adds across
sources.

## Sets and measures

| symbol | meaning | status |
|---|---|---|
| S = {1, 2} | source firms (the insurers) | given |
| Z, P | ZIPs, products | given; a source's products: all, or those it sells? Q32 |
| D | distributors, keyed as in the market metrics schema: CRD, plus broker name on a CRD a rule splits; ⊥_D for none | settled key; the split list: Q27 |
| X = Z × D × P | market cells, one period (fiscal year 2025), with projections π_Z, π_D | given |
| W_s | wholesalers of source s; *seller* and *holder* are roles, not kinds of person | given |
| C_s | source s's current channel labels | given |
| N | the new channel labels | being designed; one set for both sources? Q6 |
| M_s : X → ℝ≥0 | source s's market = its own opportunity estimate Ô_s (estimated market sales, not business anyone can necessarily win) | settled; the larger of the two estimates is parked |
| σ_s : X × W_s → ℝ | source s's sales (actual sales amount) in cell x credited to wholesaler w | given |

## The distributor key, per dataset

| source | dataset | carries | path to D | checks |
|---|---|---|---|---|
| 1 | opportunity | `cbd_id`, firm name; the raw vendor rows also carry CRD and broker name | native, if built from the raw vendor rows | |
| 1 | sales | `cbd_id`, firm name, no CRD | `mm_map`: `cbd_id` → CRD (→ broker name on a split CRD) | single-valued: 3-6 `cbd_id`s reach 2+ CRDs in the first-pass master |
| 2 | opportunity | CRD, broker name, product line, VA type | native | |
| 2 | sales | CRD, its own firm name | CRD native; on a split CRD, (CRD, sales firm name) → broker name | a CRD → broker name table cannot choose on a split CRD |

Every path, per source and dataset: **unique** (each mapping key once: rows and $ never duplicate), **total** (every
row reaches D, or ⊥_D with its reason: no CRD, company 0, CRD not in the market data; % of $ reported), **$ preserved**
(totals before = after), **cells line up** (% of sales $ on a cell with opportunity), **split list complete** (every
CRD with 2+ broker names is on it, or every rule treats its names alike).

## Maps

| map | type | meaning | status |
|---|---|---|---|
| credit | sale → W_s | who is credited with a sale (not necessarily who caused it) | given, never changes |
| κ_s | X → C_s | current channel of a cell: source s's feed channel plus its distributor rules (`s1_opp_sales.sql:459-470`) | given |
| λ_s | X × W_s → C_s | the label recorded on a sale; can depend on the seller (`s1_opp_sales.sql:418`, the IMO rule) | given; λ_s = κ_s? Q28 |
| ν_D | listed D → N | the new label of a listed distributor (`s1_opp_sales.sql:703-707`; the firm overrides) | settled (lists in the log) |
| ρ_s | C_s → N | the new label a current label carries forward (`s1_opp_sales.sql:707`, `else iwn.dist_ch`) | given for source 1 (same label); Q6 |
| ν | X → N | new channel of a cell: ν_D(d) for a listed d, else ρ_s(κ_s(x)) | I3 for every distributor? Q27 |
| H_s | C_s × Z → subsets of W_s | holders of a current channel × ZIP: 0, 1 or 2+ (coverage; may overlap) | given |
| k_s | each (c, z) → weights over H_s(c, z) summing to 1 | how a cell splits among its holders | settled: all on the lowest ID (2026-10-28) |
| τ_s | X → C_s | the current channel whose territories serve a cell in the new state (the bridge) | override-listed distributors: the channel the override states (settled 2026-10-28); otherwise κ_s(x), holder unchanged (`s1_opp_sales.sql:719`); new channels such as National: Q29 |

## States and views

A **state** is one set of channel definitions applied to the same data; nothing else differs. **Current**: labels
C_s, classification κ_s, coverage H_s(κ_s(x), z). **New**: labels N, classification ν, coverage H_s(τ_s(x), z).
Aggregating μ along f: f_*μ(b) = Σ μ(a) over all a with f(a) = b.

| view | current (per source s) | new |
|---|---|---|
| 1. channel × ZIP | (κ_s, π_Z)_* M_s | (ν, π_Z)_* M_s |
| 2a. reclassified | (κ_s, ν, π_Z)_* M_s; a cell is **reclassified** if ν(x) ≠ ρ_s(κ_s(x)) | — |
| 2b. reassigned | a cell is **reassigned** if τ_s(x) ≠ κ_s(x): its holders change | — |
| 3. coverage | holder w gets Σ_x M_s(x) · k_s(κ_s(x), π_Z(x))(w) | the same with τ_s(x) for κ_s(x) |
| 4. landing (placement) | (λ_s or κ_s, π_Z, id_W)_* σ_s | (ν, π_Z, id_W)_* σ_s |
| 5. credit | (pr_W)_* σ_s | identical: it uses no channel map |

No holder (⊥) has three causes, reported apart: unknown distributor (d = ⊥_D), no bridge (τ_s undefined), no coverage
(H_s = ∅). A share is defined only when numerator and denominator pass through the same map: a holder's territory
share = sales sent through k_s to w ÷ market sent through k_s to w. Which one ranks a wholesaler: Q31.

## Invariants

| | equation | status |
|---|---|---|
| I1 | territories fixed: H_s and k_s are the same in both states; new-state holders come only through τ_s (no new assignments) | settled, owner 2026-10-29 |
| I2 | credit fixed: view 5 uses no κ or ν | settled, owner 2026-10-29 (holds by construction) |
| I3 | in the new state the channel depends on the distributor only: ν = ν_D ∘ π_D | stakeholder, 2026-10-29; for listed distributors by construction, for all: Q27 |
| I4 | each source's market is the same in both states, so views 1-2 total Σ_x M_s(x) in each; a gap means something other than classification changed | proposed (session); the first must-be-zero check |

## Pipeline

The owner's design (2026-10-30): each source is first put on the market metrics schema, then the same rules run on
both at once.

1. **Conformance, per source:** source-internal steps (filters, ZIP and product bases, the source's own channel
   derivations) and the path to D. Different code per source, one output shape: opportunity (source, ZIP, d, product,
   feed channel, amount); sales (source, ZIP, d, product, recorded label λ_s, seller, amount).
2. **Unified facts:** both sources stacked, same columns, a `SOURCE` column; still nothing crosses sources.
3. **Rules as tables, applied by join:** κ rules (per source), ν_D (shared, keyed on d), τ_s and coverage (per
   source), display names (shared). A rule list in the owner's query becomes rows of a rule table, with a priority
   where two rows can match one key.

## Vocabulary

| instead of | say |
|---|---|
| op moves | reclassified (2a) or reassigned (2b) |
| attributed | credit (sale → person), placement (amount → channel × ZIP) or coverage (cell → holder) |
| who did it | credited seller |
| firm | source firm, or distributor |
| channel | label (of a state), feed channel (an observation on Ô_s) or team (who works which channel) |
| territory | coverage (a footprint with its channel and holders; may overlap) |
| market share | cell share (sales placed ÷ market) or territory share; a seller is ranked by contribution |

## Example

Made-up amounts, source 1. Cell x = (z, d, p) with M₁(x) = 10; κ₁(x) = IFA; H₁(IFA, z) = {w_a}; d is listed with
ν_D(d) = National. Sale σ₁(x, w_b) = 2, seller w_b an FI wholesaler (λ₁ = FI).

- View 1: IFA × z holds 10 now, National × z holds 10 after; both states total 10 (I4).
- View 2a: ρ₁(IFA) = IFA ≠ National, so x is reclassified.
- View 2b, as the owner's query does it (τ₁(x) = κ₁(x) = IFA): not reassigned; w_a keeps the 10. If d's firm override
  states FI and H₁(FI, z) = {w_c}: reassigned, the 10 goes from w_a to w_c.
- w_b keeps the 2 in both states (view 5). It is placed on National × z after; now on FI × z by λ₁ or IFA × z by
  κ₁ (Q28).
