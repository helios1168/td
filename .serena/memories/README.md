# td Serena memories: index

One line per memory: name, then what it holds. Read the ones a bead's `memories` metadata
names before starting. Only Claude writes here; other agents report `LEARNED:` lines.

## facts (settled numbers, with dates and conditions)
- `facts/instance-versions`: v1 against v2 table, CONUS ground set (3,713 zips, tau 471.21), v3 and pending v4, masked firm shares
- `facts/nats-headline`: one nats scale at k = 18 seed 2; balance is free, premium 0.72 to 0.78 nats, roster 0.249, premium ladder
- `facts/phase0-measurements`: B_tot, the (★) screen and its slack, D(g), premium window, measured 24 splits against the caps
- `facts/region-pin-costs`: fix and anchor cost of pinning seven regions, CALIFORNIA to CAROLINAS
- `facts/owner-sets-k18`: home states per district on the committed draw, 9.15% outside, blocks a 10% band cannot close
- `facts/state-border-snapping`: Track 1 and Track 2 grids of 2026-09-07 on the whole v2 instance
- `facts/conus-track2-grid`: the CONUS re-run at δ 5, 7, 10%; the band is always overshot after rounding
- `facts/shipped-map`: tau 470.459, state ratios over tau, "5.25% realised" not "within 5%", recomputed values
- `facts/per-state-caps`: NY at 2 refuted, CA at 4 neither refuted nor found, CA 4 at δ 10% solves
- `facts/level1-certified-splits`: certified minimum splits for k 10 to 20 at δ 10%, timings, 2025 gazetteer effect
- `facts/balance-ceiling`: the Jensen ceiling 110.883247 is the valid bound; free_search is not
- `facts/map-contiguity`: Voronoi dissolve and power-cell contiguity of the committed draw; area against mass denominators
- `facts/state-atoms-retired`: numbers of the retired state-atom route and its prototype; PYTHONHASHSEED=0

## model
- `model/reference-parameters`: the utility, θ 0.40 λ 0.30, per-zip sizing, the two saturation definitions
- `model/corrections`: ρ keeps scale invariance; a heuristic on a relaxation is not a bound; "zero by construction" is relative
- `model/u1-cert-eg-dual`: three of four certificates collapse, k-1 splits hold heterogeneously, headroom under filler modes
- `model/u2-stab`: ρ absent from stage 2, unmatched reps cannot block, ties in g are structural
- `model/u9-bandthm`: corrected MBB rule, minimised slope at δ 0, sharp k-1+t splits, OA is Kelley, Slater, gauge

## solver
- `solver/highs-and-scipy`: highs-ds pin, python3 -u, level-1 portfolio engine and sizes, level-0 sizes
- `solver/scip-modelling`: epigraph form 5 s against 400 s, getDualbound not rigorous at 1e-9
- `solver/lp-degeneracy`: vertex moves under 1e-16 perturbations; split sets and power weights are vertex-dependent

## geo
- `geo/zip-adjacency`: shattered zip graphs (v1, v2, real ZCTA), state rook graph, why proximity stays Voronoi
- `geo/zcta-geometry`: real ZCTA polygons at 250 m, 2025 gazetteer default, the 2020 pin, district_reach

## decisions (user decisions that are settled)
- `decisions/problem-scope`: what td is, early scope decisions, the two results that carry the work
- `decisions/stage1-route`: atom route abandoned, power cells plus state-line borders, CONUS only, the zip table
- `decisions/rep-split-and-app-views`: contiguous rep splits on the cell graph, rep maps, sidebar picker and named views
- `decisions/app-2026-09-08`: scenario app rules: bargaining both ways, territory = sales, release pricing, k grid
- `decisions/full-problem-2026-09-11`: multi-channel rules: sub-channels, WIFI, split caps and band break, sweep, four state patterns

## workflow
- `workflow/confidential-data`: descaled export only; shares and raw M never together; no per-record values anywhere
- `workflow/docs-and-state`: STATE is `## Now` only, facts in memories, tasks in Beads, doc owners, unit files
- `workflow/full-problem-track`: where the multi-channel grids, REVIEW.md, hot/, best/ and the contig-cut worktree live

## verify
- `verify/oracles-core`: raw instance re-read, LP for matching, SCIP, submodular B&B, gains by hand
- `verify/oracles-eg`: proportional response, certificate checking, secant squeeze, KKT residual scale
- `verify/oracles-reporting`: gate-only re-run, re-derived vectors, which upper bound, vacuous fields
- `verify/oracles-lp-labelling`: linprog interception, two-directional LP compare, rival hypotheses
- `verify/oracles-milp`: enumerate z and LP y, symbolic row read-back, stale row counts, no warm start in milp
- `verify/anchors`: byte-identity and stage-2 value anchors, and the params.json that is not provenance
- `verify/environment`: hub python in worktrees, custom test runner, battery symlink, solver stack, test counts
- `verify/eg-band-harness`: symmetric fixture trap, dual parametrisation, OA stall and vertex recovery

## domain
- `domain/lens-workflow`: read order and conventions for a /domain run; the two seeded domains
- `domain/economic-theory-conventions`: frozen section numbers and the two citation pools
- `domain/economic-theory-verdicts`: retired and ruled-out methods, the invariance split, open hand-offs
- `domain/optimization-verdicts`: rejected methods, three checks, the closed-form screening bound

## refs
- `refs/optimization-foundations`: FOUNDATIONS entries that carried the optimization plan
- `refs/econ-theory-matching`: stability and matching citations, and which ones cannot be read as support
- `refs/published-artifacts`: the four private artifact pages of 2026-09-07
