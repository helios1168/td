---
date: 2026-10-12T23:21:17-0500
author: Nicolas Lee
commit: 617b42e
branch: m5-studio/national-overnight
repository: td-national-overnight
topic: "Main-map pipeline with joint WIFI footprint and K grid"
tags: [intent, frd, contiguity, main-map, WIFI]
status: ready
last_updated: 2026-10-12T23:21:17-0500
last_updated_by: Nicolas Lee
---

# FRD: Main-map pipeline with joint WIFI footprint and K grid

## Summary
Extend the IFA contiguity pipeline to national, WH, FI and WIFI to produce stakeholder-map candidates in a later broad overnight run. Search jointly across WIFI footprints and channel district counts rather than freezing the existing west/plains carve and three blocks. This stage captures intent only; research assesses current code and mathematics before design and run planning.

## Problem & Intent
Owner's foundational answer: **"Stakeholder maps"** (selected option: usable main-map candidates across national, WH, FI, WIFI).

Owner's correction, verbatim:
> we need to think about how we handle WIFI. that piece will also vary, i.e. we will not just fix those midwestern states to be wifi but will also run the grid across other options

IFA's state-sealed single-channel workflow is not automatically a valid four-channel workflow. Current main-map seeds, stale dollar scoring and branch-only extensions cannot be treated as stakeholder-ready.

## Goals
- Produce usable stakeholder-map candidates, not merely successful solver exits.
- Extend run/repair/merge/export behavior across all four main-map channels.
- Propose a joint whole-state WIFI footprint and K grid, including the current seed for comparison; replan national/WH/FI over each footprint's complement.
- Preserve settled dollar eligibility, full-graph M1, looks-first ranking and tracking.
- Assess latest mathematical and code changes for main-map applicability before selecting implementation or allocating solver time.

## Non-Goals
- Launch an overnight run, repair pilot or solver during discovery.
- Edit source, land branches, alter owner mandates or select a final stakeholder map.
- Freeze WIFI geography or K to the legacy configuration.
- Implicitly resolve #111/#112, claim global split minimality, or import IFA-specific waivers into main maps.
- Staffing.

## Functional Requirements
1. The pipeline SHALL support national, WH, FI and WIFI through scoped planning, drawing, repair, full-graph merge audit and exports; retain IFA compatibility.
2. Candidate construction SHALL vary whole-state WIFI footprint and channel K jointly. Research SHALL propose options including the existing eight-state/K3 seed, not assume its fixed block family is mandatory.
3. Each candidate SHALL derive consistent national/WH/FI complement domains and fine-channel routing from its WIFI footprint; audit every in-scope extract cell for exactly one owner and all required ZCTAs, including zero-opportunity territory.
4. Planning, repair and eligibility SHALL use the same per-district dollar rules: national $1,062.5M–$1,437.5M; WH $850M–$1,150M; FI $765M–$1,035M; WIFI within ±15% of its own dollar mean. Use fine-channel whole-extract rates, credit only assigned on-map dollars, and enforce total main-map K 48–54.
5. Repair SHALL account for dollar-only violations as well as detached pieces and necks; unchanged IFA m_rel windows SHALL NOT be treated as a general four-channel dollar adapter.
6. Regional/channel outputs SHALL merge without duplicate or missing ownership, preserve candidate-specific coverage/routing, and re-audit on the full 2025 polygon graph. State-keyed IFA merging alone is not sufficient evidence of four-channel correctness.
7. M1 reporting SHALL include both gap-width and legacy verdicts under G3; any gap-induced flip other than TX El Paso SHALL go to the owner. Resolve and test prototype-versus-gap-land integration before relying on it.
8. Each drawn run SHALL have a manifest under runs/exp/<lane>/<run_id>/; presented candidates SHALL have current audit/render ties in the ranked shortlist, long CSV and geographic exports.
9. Research SHALL assess dollar-triggered repair, both gap-width implementations, thin-unit land floors and #133 land-balance objectives for main-map applicability, distinguishing verified code, untested prototypes and IFA-only policy.

## Non-Functional Requirements
- **Performance**: Broad overnight search is the later target; exact wall-clock, parallelism, allocation and stop/retry policy are deferred to planning. No solver work authorized now.
- **Security**: Sales, per-rep shares and rep/firm names never leave the extract. Only permitted opportunity and masked outputs enter artifacts or exports.
- **UX / Accessibility**: Maps must look sensible to stakeholders; few splits, no visual defects, compactness and balance matter. No new UI requested; owner chooses final maps.
- **Reliability**: Record scenario, code/math provenance, geography vintage, rates and candidate footprint/K with each run; validate merged ledgers and reproducible exports. Failed or unverified candidates cannot be labeled eligible.

## Constraints & Assumptions
- Use support master MILP and ZIP realizer as starting framework; investigate carve-first changes rather than declaring issue titles implemented.
- Current branch is 617b42e; orientation references separate scouts, IFA and #131 branches. “Latest” means assess and reconcile those sources, not blindly run one branch.
- All geography is 2025 vintage. Full-graph M1 remains authoritative even when drawing on an induced graph.
- Settled ranking: channel-state splits, cuts, visual defects, shape, balance. Restricted master floors remain labeled “over 𝒳_c(δ) only”; no “minimal” claim without a covering bound.
- Whole-state WIFI footprint search was accepted; precise geographic alternatives remain to be proposed. Do not silently equate owner's “midwestern states” with a newly fixed region.
- #130 and #131 remain open; local scorer uses obsolete mean-based rules and local audit lacks gap-width implementation. #133 exists and concerns land balance, contrary to the brief's missing-reference note.
- #132's Manhattan/Bronx/Westchester decision is IFA-specific; main-map applicability requires assessment, not automatic adoption.
- Use $TD_PY, hub extract/public geography, tracked branch and filesystem run manifests. Code moves between Studios via GitHub.

## Acceptance Criteria
These govern later implementation/run verification, not execution in this discovery session.
- [ ] Research artifact contains proposed WIFI footprint/K grid including current seed, corresponding complement/routing rules, and explicit evidence for main-map applicability of each assessed enhancement.
- [ ] A later candidate grid contains at least two distinct whole-state WIFI footprints and records channel K and total K in each snapshotted scenario/manifest.
- [ ] Scoped run.py / repair.py / merge.py invocations are documented and executable for four-channel candidates; merge audit reports no missing/duplicate cells or required ZCTAs on the full graph.
- [ ] Dollar audit output lists every district's dollars and bounds for all four channels; a fixture with passing channel average but an under-floor district fails eligibility, and a dollar-only violation is identified as repair work.
- [ ] tools/mandates/check.py output and M1 audit report zero detached pieces/violating necks for any candidate labeled eligible, both gap verdicts, and required owner review for new flips.
- [ ] tools/looks/score.py rejects per-district dollar failures, WIFI mean-band failures and total K outside 48–54; preserves settled ranking.
- [ ] Long CSV/scenarios.csv and geographic exports agree with the audited ledger; presented candidates have manifest, shortlist entry and current render/check ties, with runs/shortlist/INDEX.md rebuilt.
- [ ] "$TD_PY" tests/run_all.py exits successfully after later implementation, including checks covering varying footprints, routing/merge coverage, dollar-only failures and selected gap-width implementation.
- [ ] This discovery writes only a new FRD; no source changes or solver launches occur.

## Recommended Approach
Reuse the existing support-master → draw.py → repair → merge → export pipeline, extending candidate-specific channel domains and per-district dollar handling rather than duplicating IFA scripts. Research should ground a joint whole-state WIFI footprint/K grid and full-graph audit seam, then assess gap-width, thin-unit and land-balance additions before design and bounded overnight planning.

## Decisions

### Stakeholder intent
**Question**: For main-map overnight work, what counts as success for you and stakeholders?
**Recommended**: n/a — intent question.
**Chosen**: "Stakeholder maps".
**Rationale**: Usable stakeholder candidates are the goal, not run readiness or evidence alone.

### Correct fixed-WIFI framing
**Question**: Probe confirms D3/E3 per-district dollars, full-graph M1 with both gap verdicts, looks-first ranking, K total 48–54, tracked shortlist/exports (docs/problem/PROBLEM.md:62–67; WATCHDOG.md:44–72). Keep these gates, with this stage limited to framing—no solver launch or source edits?
**Recommended**: Keep all.
**Chosen**: "Change frame", followed by the verbatim WIFI correction in Problem & Intent after the clarification question: "Which part needs changing: map gates, search scope, or stage boundary? Describe correction in custom answer."
**Rationale**: WIFI geography itself must vary; an inherited fixed carve would miss the requested search.

### Joint grid and unchanged gates
**Question**: WIFI varies, agreed. Current seed fixes eight west/plains states and three blocks (scenarios/51_total_13n_11wh_24fi_3wifi.toml:17,74–83). Should research propose whole-state WIFI footprint and K options—including current seed—with national/WH/FI replanned over each complement, leaving exact grid and budget for planning?
**Recommended**: Propose joint grid; preserve D3/E3, M1, ranking, total K 48–54, tracking; no launch now.
**Chosen**: "Propose joint grid (Recommended)".
**Rationale**: Broader stakeholder alternatives justify later solver cost; evidence: scenario :27–32,52,64,78 domain seam plus confirmed unchanged gates. Exact grid and budget explicitly deferred.

### Assess latest enhancements, defer knobs
**Question**: Brief missed #133: land-balance objective for city-versus-rural splits (https://github.com/helios1168/td/issues/133). For 'latest code and math', should research assess dollar-triggered repair, both gap-width implementations, thin-unit floors and #133 for main-map use, while deferring implementation choices, land-ratio bound, exact grid and solver budget to later design/planning?
**Recommended**: Assess all, defer knobs.
**Chosen**: "Assess all, defer knobs (Recommended)".
**Rationale**: Cover known map-quality risks without accepting untested branch code or transferring IFA policy automatically.

## Open Questions
- Exact whole-state WIFI footprint alternatives and channel K grid: research proposes; planning fixes launch grid.
- Which dollar-repair architecture/pilots, gap-width implementation and thin-unit/land-balance mechanisms apply to main maps: research/design decides with evidence.
- #133 land-ratio bound or replacement balance measure: owner decision deferred; placeholder R=10 is not approval.
- Solver budget, jobs, overnight duration, pilot authorization and launch timing: deferred to planning.

## Suggested Follow-ups
- #111 small-share defect/floor policy and #112 unattached-share tradeoffs remain owner decisions; no default adopted here (WATCHDOG.md:77–90; live issues read this session).
- #119 all-M1 bound remains optional unless stakeholder claims require global “minimal”; restricted floors cannot support that claim (docs/problem/PROBLEM.md:60–61; live #119).
- Orientation's #133 missing-reference claim is stale; live issue supplies land-balance goal and owner-bound blocker.

## References
- .rpiv/artifacts/orientation/2026-10-13-ifa-to-national.md (read fully).
- STATE.md; WATCHDOG.md; docs/problem/PROBLEM.md (read fully).
- scenarios/51_total_13n_11wh_24fi_3wifi.toml (read fully).
- tools/looks/score.py (first 150 lines read directly; scorer seam probed by agent).
- Latest IFA run ifa_conus_v2; scouts dollar audit and unexecuted repair proposal: orientation context only, not independently rerun or verified.
- Live GitHub issues read this session: [#105](https://github.com/helios1168/td/issues/105), [#130](https://github.com/helios1168/td/issues/130), [#131](https://github.com/helios1168/td/issues/131), [#132](https://github.com/helios1168/td/issues/132), [#133](https://github.com/helios1168/td/issues/133), [#112](https://github.com/helios1168/td/issues/112), [#111](https://github.com/helios1168/td/issues/111), [#119](https://github.com/helios1168/td/issues/119).
