# The analysis's model: what opportunity and sales are, and how channels and territories see them

The analysis is rebuilt from this model (owner, 2026-10-29). Every output is a measure aggregated along a map (SQL:
`GROUP BY` the map's value, `SUM`), so the model is complete when every map is defined. Status: **given** (in the
data), **settled** (rule in `DATASET_LOG.md` Settled), **open** (its question in the log's index), **parked**. A layer
file (`01`, `02`, ...) names the symbols it implements; where a query and this file disagree, fix this file. Derivation:
`notes/2026-10-29_snowflake-conceptual-model-research.md`. `s1_opp_sales.sql:N` cites the owner's query in
`$TD_REPO/owner_sql/` at the version its `DATASET_LOG.md` entry pins.

The two source firms are analysed separately, each with its own data, on one common market metrics schema (owner,
2026-10-29 and 2026-10-30). Everything below is per source s; only Z, P, D, N and the rules on them (ν_D, display names)
are shared, and nothing adds across sources.

## Sets and measures

| symbol | meaning | status |
|---|---|---|
| S = {1, 2} | source firms (the insurers) | given |
| Z, P | ZIPs, products | given; a source's products: all, or those it sells? Q32 |
| D | distributors, keyed as in the market metrics schema: CRD x broker name; ⊥_D for none | settled key (2026-10-30) |
| X = Z × D × P | market cells, one period (fiscal year 2025; source 2's period: Q36), with projections π_Z, π_D | given |
| W_s | wholesalers of source s; *seller* and *holder* are roles, not kinds of person | given |
| C_s | source s's current channel labels | given |
| N | the new channel labels | being designed; one set for both sources, in firm 1's channels (settled 2026-10-30, Q6) |
| M_s : X → ℝ≥0 | source s's market = its own opportunity estimate Ô_s (estimated market sales, not business anyone can necessarily win) | settled; the larger of the two estimates is parked |
| σ_s : X × W_s → ℝ | source s's sales (actual sales amount) in cell x credited to wholesaler w | given |

## The distributor key, per dataset

| source | dataset | carries | path to D | checks |
|---|---|---|---|---|
| 1 | opportunity | `FIRM_CRD`, `BROKER_NAME` on every row; company ID (missing on 26% of $) and client firm ID | native: CRD x broker name | one firm 1 channel per CRD x broker name (profile, 2026-10-30) |
| 1 | sales | `cbd_id`, firm name, no CRD | `mm_map`: `cbd_id` → CRD (→ broker name on a split CRD) | single-valued: 3-6 `cbd_id`s reach 2+ CRDs in the first-pass master |
| 2 | opportunity | CRD, broker name (the market metrics names, suffixes included), product line, VA type | native | 99.93% of $ at a CRD x broker name source 1 carries |
| 2 | sales | CRD, its own firm name | CRD native; on a split CRD, (CRD, sales firm name) → broker name | a CRD → broker name table cannot choose on a split CRD |

Every path, per source and dataset: **unique** (each mapping key once: rows and $ never duplicate), **total** (every
row reaches D, or ⊥_D with its reason: no CRD, company 0, CRD not in the market data; % of $ reported), **$ preserved**
(totals before = after), **cells line up** (% of sales $ on a cell with opportunity), **names match** (every broker
name is the market metrics name; source 2's sales reach it through its CRD map).

## Maps

| map | type | meaning | status |
|---|---|---|---|
| credit | sale → W_s | who is credited with a sale (not necessarily who caused it) | given, never changes |
| κ_s | X → C_s | current channel of a cell: source s's feed channel plus its distributor rules (`s1_opp_sales.sql:459-470`) | given |
| λ_s | X × W_s → C_s | the label recorded on a sale; can depend on the seller (`s1_opp_sales.sql:418`, the IMO rule) | given; λ_s = κ_s? Q28 |
| ν_D | listed D → N | the new label of a listed distributor (`s1_opp_sales.sql:703-707`; the firm overrides) | settled (lists in the log) |
| ρ_s | C_s → N | the new label a current label carries forward (`s1_opp_sales.sql:707`, `else iwn.dist_ch`) | source 1: the same label; source 2: not used, the route is by firm (Q6 settled) |
| ν | X → N | new channel of a cell: ν_D(d) for a listed d, else firm 1's channel of d (UNMAPPED if none), both sources | settled 2026-10-30 (Q38: per CRD x broker name; the override only fills gaps) |
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
| I3 | in the new state the channel depends on the distributor only: ν = ν_D ∘ π_D | stakeholder, 2026-10-29; for every distributor by the owner's route, per CRD x broker name (settled 2026-10-30, Q38) |
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

## Opportunity routed by firm (the first deliverable)

Owner, 2026-10-30: opportunity first, routed by firm on the market metrics schema; sales later. Per source, one row
per cell x = (z, d, p): its market, current channel and holder, new channel and holder (views 1, 2a, 2b, 3). Out of
scope for now: the firms whose firm 1 channel is EDJ or AMER, both sources and states (key decision, `DATASET_LOG.md`).

| step | source 1 | source 2 | status |
|---|---|---|---|
| M_s | `WC_MARKET_METRICS_OPPORTUNITY.GLOBAL_SALES`, fiscal year 2025 | `…_OPP_ORIGINAL.OPP` | source 2's period: Q36 |
| z | `ZIP_CODE` (text), padded to 5 | `ZIP_CODE` (a number), padded to 5 | given |
| d | `FIRM_CRD` x `BROKER_NAME` | the same columns | settled; both full; a CRD over 2+ channels splits by broker name (4 CRDs, 12 names) |
| p | `PRODUCT_LINE` × `VA_PRODUCT_TYPE`: RILA if either says RILA, VA type IOVA → IOVA, TRVA → VARIABLE, IA → INDEX, FA → FIXED | the same columns and map; RILA is a VA type here | settled (Q22); the map is the session's for both: the owner's (`s1_opp_sales.sql:453-458`) reads RILA from `PRODUCT_LINE` only, which source 2 leaves VA |
| κ_s | feed `DIST_CH`, then the rules `s1_opp_sales.sql:459-470` (company ID, broker name, feed label) | the file's `DIST_CH` (BANK, INDEPENDENT, REGIONAL, REGIONAL AGENCY, NO CHANNEL) → source 2's territory channel (BK, FP, BD, RA) | settled; source 2's pairs and NO CHANNEL kept: key decision (`DATASET_LOG.md`, Key decisions) |
| current holder | H₁(κ₁(x), z), lowest ID | H₂(κ₂(x), z), lowest ID | settled |
| ν | ν_D(d) for a listed firm (`s1_opp_sales.sql:703-707`, the firm overrides), else firm 1's channel of the firm; UNMAPPED where it has none | the same tables | settled 2026-10-30 (basis, level, the override's role, UNMAPPED) |
| new holder | H_s(τ_s(x), z) | H₂ of the source 2 channel that holds each firm 1 channel | listed firms settled; source 2's pairs (IFA → FP, FI → BK, WH → BD, PRI → RA): key decision; National: Q29 |

The firm's route (owner, 2026-10-30): firm 1's channel per market metrics firm, for both sources, so the new channels
match across sources and source 2's own channels serve only its current state. In firm 1's fiscal year 2025 rows every
CRD x broker name has at most one non-blank channel; a CRD over 2+ channels is spread through its broker names
(`DATASET_LOG.md`, 2026-10-30, profile). Settled (Q38): the route is per CRD x broker name; `crd_dist_override`
(at work) fills only an UNMAPPED, 2+ or absent route, and where it differs the route wins. A split firm stays
split through its broker names: Wells, below.

Rules keyed on a company ID (κ₁'s, ν_D's, the firm override) reach source 2 only re-keyed to CRD and broker name, read
off source 1's rows, which carry both. The company ID is the weaker key: missing on 26% of firm 1's $, and 3 company
IDs span 2+ channels.

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

Wells, a split firm (real; source 1's rules and the owner's lists, no amounts). One CRD carries two market metrics
broker names. `Wells Fargo Clearing Services, LLC` is WH by the rule `s1_opp_sales.sql:461` and company ID 1822
(`:475`); `Wells Fargo Clearing Services, LLC - BANK` is company ID 1823 (`:476`) and keeps its feed channel. On the key
d = CRD x broker name they are two distributors: d_WH and d_BANK.

- κ: each source's cells of d_WH are WH, through the name, in both sources; `crd_dist_override` had FI on d_WH, and the
  route wins (Q38).
- ν: the new-channel list breaks both out, ν_D(d_WH) = Wells WH and ν_D(d_BANK) = Wells FI (`:704`-`:705`, from company
  IDs 1822 and 14, and 1823), so ν_D is keyed on CRD x broker name; keyed on the CRD alone it could not split them.
- 2a: every cell of either name is reclassified (WH → Wells WH, the bank name's channel → Wells FI).
