# Full-problem mathematical and game-theoretic setup

Read-only familiarization snapshot, 2026-09-11, branch `worktree-full-problem`.
Saved at the user's explicit request, overriding the session's earlier prohibition on writing Serena memories. This is an interpretation of the documents and implementation, not a new mathematical verification. No handoff next steps were undertaken.

## Sources and precedence

Read `HANDOFF.md` and `PLAN.md` for context, `docs/MODEL_FULL.md` and `docs/FULL_PROBLEM.md` for the full formulation, and relevant sections of `docs/PROBLEM.md` and `docs/MODEL.md` for the original welfare framing. Checked the actual functions in `td/model.py`, `td/channel.py`, `td/channels.py`, `td/stage2_state.py`, `td/solvers/level0.py`, `tools/full_plan.py`, and `tools/plan_realise.py`.

Documents contain historical assumptions and stale counts. Prefer current implementation for behavior and the handoff for the latest study configuration. Study results quoted there were not rerun. This memory belongs to this worktree, not necessarily the hub or main branch.

## Objects and channel accounting

The units of allocation are zip-by-channel cells `(z,c)`, carrying opportunity `M`, each rep's book `S_i`, and unowned book `S_free`. Fine channels are `N_WH`, `N_FI`, `WH`, `FI`.

Allowed bundles are:

- N = {N_WH, N_FI}
- WH = {WH}; FI = {FI}
- WH_PLUS = {WH, N_WH}; FI_PLUS = {FI, N_FI}
- WHFI = {WH, FI}
- WHFI_PLUS = all four fine channels

A district combines a geographic set and a channel bundle. In the intended product-form formulation, it owns every bundled channel at each of its zips. A cell can be covered at most once.

`td/channels.py::fine_split` uses actual national subchannels when supplied: N_WH = Wells WH; N_FI = Chase + Wells FI. The older national-only input uses the zip WH:FI ratio, then state ratio, then 50/50. The handoff says v4 uses the exact path. Dropping national folds its two parts into WH and FI without losing mass.

## Planning and balance

Level 0 is a state-by-channel MILP. A slot has a fixed bundle. Variables include state shares `y_sj`, binary contacts `z_sj`, slot activation, roots and connectivity flows. Core rows enforce cell coverage, `eta*z <= y <= z`, opportunity bands, and connectivity on the state rook graph. Optional constraints include state-count and centroid-distance limits, split caps, forced national coverage and paired WH_PLUS/FI_PLUS shares.

The operational objective is lexicographic coverage by channel priority, then minimum contacts, and optionally geographic compactness. It is not joint maximization of rep Nash welfare. Sequential planning fixes earlier stages as prior coverage; a joint lexicographic route also exists. A timed-out pass pins its incumbent and records that it is uncertified.

The latest study uses sequential N, WH, FI stages with merged bundles, catch-all and residual sweep, bundle bands, count ceilings, split caps and geographic restrictions. These are study settings, not universal defaults. In per-bundle mode, specified counts determine targets from available bundle mass; bundles without specified counts inherit the stage's mass-weighted target, or the national target if none exists. Count ceilings need not be attained.

Band-break allowances explicitly relax upper bands. The deterministic residual sweep may break geographic caps when no admissible alternative exists and records that fact. Full coverage after a sweep does not mean every original band or cap remains satisfied.

For fixed total opportunity and fixed district count, maximizing `sum(log M_j)` favors equal opportunity; an attainable equal split reaches the AM-GM bound. This is distinct from equality of representative gains. The project explicitly treats opportunity-first drawing as a business constraint, not a consequence of the joint rep welfare objective: incumbent-book effects are not negligible.

## Valuations and Nash staffing

The additive utility is

    u_i(z,c) = (1-lambda)*S_i + theta*(1-lambda)*(T-S_i)
               + c_free*S_free + lambda*M,
    T = sum_i S_i.

At theta=0.40 and lambda=0.30, own book has coefficient 0.70, others' book 0.28, and opportunity 0.30. The filler coefficient is 0.28, 0.70 or 0.30 for theta, full or opportunity treatment. `model.coefficients` is the shared definition.

Equivalently utility is a common cell value plus `(1-theta)*(1-lambda)*S_i`. The representative-specific variation is an incumbency premium. Aggregate utility for a fixed covered set separates into a common component and retained incumbent book; its logarithmic welfare also depends on the distribution of gains.

Given fixed districts and positive gain matrix `g_ij`, `channel.match` maximizes `sum(log g_ij)` over matched pairs using linear assignment on `-log g`. One rep holds at most one district; one district has at most one rep. The rectangular match saturates the smaller side, leaving extra reps unmatched or extra districts unstaffed. The full-plan driver uses all-rep candidacy. Masked candidacy is available elsewhere.

This is centralized maximum Nash welfare matching. Nash denotes the welfare objective, not a computed strategic Nash equilibrium. There is no implemented bargaining protocol, stable-matching mechanism, transfer scheme or outside-option subtraction. Unmatched reps contribute no term to the objective. Comparing raw log sums across different numbers of staffed districts is not like for like; `_rep_moves` explicitly flags this limitation.

## Actual staffing order, a material distinction

`tools/full_plan.py` calls `state_stage2` and writes `staffing.json` before zip realization. `stage2_state._slot_sums` weights aggregate state-channel utilities by each slot's state shares. This is exact for whole-state allocations and an approximation to which books are captured when states are split.

`tools/plan_realise.py::_main` loads that staffing, cuts and repairs districts, resolves overlaps and optionally sweeps cells, while carrying the rep assignments forward. It does not rerun matching on the final realized districts. Consequently, matching is exact for the input state-share gain matrix, not established as optimal for the final repaired map.

The optional rep-driven route scores neighborhood plan changes with state-level staffing outside the MILP. It is not a joint global welfare solver, and it was not the adopted driver for the latest geographic study.

## Decomposition and realization limits

At a fixed zip-level channel plan and fixed bundle counts, linearity permits summing cell data into one projected instance per bundle. Geographic subproblems separate; the common rep pool couples staffing across all bundles. A merged district is balanced on its total opportunity, not separate channel floors.

The ordinary split-state cut is a mass-weighted transportation LP at fixed centers, with Lloyd updates. With a single scalar mass and the stated transportation assumptions, a basic optimum has at most k-1 split zips. A second independent channel balancing attribute generally removes that network structure. Rounding and repair still matter.

The implemented level-0 plan fixes state shares, not the complete zip-level channel plan assumed by the decomposition. Independent bundle cuts can claim overlapping cells. The realizer uses bundle precedence and piece transfers to resolve this; it is not an exact joint geographic realization of every state share.

State-graph connectivity does not imply zip-graph connectivity. The realizer has a power cut and an optional contiguous cut, followed by guarded repair. The handoff reports remaining disconnected districts and band violations. Contiguity uses the Voronoi cell graph, while displayed maps use real ZCTA polygons. These tessellations differ, so visual scattering alone is not a connectivity verdict.

## Game-theoretic interpretation and boundaries

Nash matching discourages sacrificing one matched rep's gain for a small increase in total utility, compared with utilitarian matching. It does not impose individual rationality against a legacy allocation or protect excluded reps through explicit outside options.

Do not transfer broad fairness or mechanism-design theorems from the literature directly to this constrained pipeline. EF1 at a single-district-per-rep matching stage is trivial when the entire district is the indivisible good, and does not establish zip-level fairness. The implementation does not establish strategyproofness or stability.

`docs/MODEL.md` section 9 explicitly withdraws the earlier cited justification for keeping books out of stage 1. The policy remains a prudential/business choice, and misreporting exposure is unresolved. Other literature claims in that section were read as context, not independently verified or adopted as guarantees of this implementation.

## Scope of this session

Familiarization only. No implementation changes, tests, solver runs, next-step work, commits or pushes were performed. The only subsequent write was this memory, explicitly requested by the user.
