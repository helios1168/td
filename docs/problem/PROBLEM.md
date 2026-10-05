# Problem ledger

What is settled and what is open about td's problem. One row per item; a revised row is struck
through and restated with a new date, never deleted. Rows below the seed line are appended by
the `triage` skill from lens, council and review output.

## The problem

**The goal** (owner, 2026-10-05). td makes the sales territory maps the owner will put in front of
stakeholders: the main map (national, WH, FI, WIFI and the combined channel) and the IFA map. In
each planning channel, K districts together cover every CONUS ZIP, and each district must be:

- **one connected piece of territory on the drawn map** (M1, hard: drawn 2025 ZCTA polygons, rook
  adjacency, a committed connector list for water, no tolerance; owner 2026-10-04);
- a sensible-looking territory (few split states, no visual defects, compact);
- balanced (drawn opportunity in the band around τ, $ per district near target).

The owner picks the final maps from a ranked shortlist (#105). The method below serves this goal,
and `WATCHDOG.md` restates it for the always-on watcher. M1 was set aside on 2026-09-01 "for
simplicity" without a return trigger and is restored here.

Since 2026-09-25 td has one problem, **the support master problem** (#52 §1). For each planning
channel c, divide its (ZIP, fine channel) opportunity into K_c districts whose drawn masses lie
in a band around τ_c. Three parts do this:

1. a support-based master MILP that plans districts on units (states, or pieces of them);
2. a ZIP realizer that turns planned unit shares into whole-ZIP borders;
3. an audited `(ZIP, fine channel) → district` ledger.

The full model is `docs/MODEL.md` (#64), pending verification in #65. Staffing is out of
scope until it returns: scenarios are district-only plans.

The previous ledger, its FRAME §9 rows (2026-08-31 to 2026-09-02) and the twelve questions for
the lenses belonged to the Nash-staffing problem. They were archived on 2026-09-28 (td#54) and
are in the tag `archive/pre-support-2026-09`.

## Settled / open

| item | status | date | owner | why |
|---|---|---|---|---|
| The support-master scope, the clean slate and decisions S1–S31 | **settled** | 2026-09-25 | user | `docs/memory/decisions/support-refactor-2026-09-25.md`; #52 revision 7 approved 2026-09-28 |
| OQ1–OQ7 of #52: where the §4 corrections land, `docs/lenses/` kept, U-number ranges, blocker cycles, C7's gate, a disconnected whole unit stops the run, the file caps | **settled** | 2026-09-28 | user | [owner's answers on #52](https://github.com/helios1168/td/issues/52#issuecomment-5866293503) |
| OD1: the final band tolerance | **open** | 2026-09-28 | user | #56; blocks D1 and E1, not implementation |
| ~~OD2: the authoritative ZIP graph~~ | ~~**open**~~ | 2026-09-28 | user | ~~#57; blocks G1~~; answered 2026-10-04, row below |
| OD3: output status and certificate tiers | **open** | 2026-09-28 | user | #58 |
| OD4: county pieces and how they are drawn | **open** | 2026-09-28 | user | #59; decided on D1's free-mode splits |
| OD5: the metro outline and the oversized-metro rule | **open** | 2026-09-28 | user | #60 |
| OD6: the catalog (channels, bundles, WIFI, K grid, support caps) | **open** | 2026-09-28 | user | #75; decided on E1's scorecards |
| F1: the new planning channels and bundles | **open** | 2026-09-28 | user | #76; after the fresh extract (#3) |

<!-- seed line: rows above were seeded 2026-09-28 (td#54) from #52; append below -->
| ~~Looks first: a plain ±15% band (as ±10%, no per-channel exception count); rank maps by channel-state splits, then visual defects (one may outrank an extra split, flagged for review), then shape, then balance; main map K 48–54 with $ per district within ±10% of each channel's target. Supersedes the council's balance-first framing; M_c(δ) with μ = 0 stays the bound and seed. District definition open (U50); OD1 (#56) still records the final band~~ | ~~**settled**~~ | 2026-10-04 | user | `docs/lenses/COUNCIL_2026-10-01.md` § Triage (the owner's 2026-10-04 answers); restated 2026-10-05 (#91), rows below |
| OD2 (#57): the authoritative ZIP graph is the 2025 TIGER ZCTA polygon rook graph: every CONUS ZCTA a vertex, an edge for a shared boundary of positive length (a shared corner does not count), water crossed only through the committed connector list. The model plans and draws on it. Supersedes the Voronoi rook graph on extract ZIPs (owner on #57, 2026-09-28) | **settled** | 2026-10-04 | user | M1 in `docs/problem/MANDATES.md` (#107) |
| M1, ZIP contiguity, is a hard mandate; the register `docs/problem/MANDATES.md` holds it and masking. Restores ~~Adjacency contiguity is not required (2026-09-01, "Reopenable only by the full-ZCTA-graph experiment")~~, a row whose condition #62 met on 2026-09-28 and which the #54 clean slate archived in `archive/pre-support-2026-09` | **settled** | 2026-10-04 | user | `docs/problem/MANDATES.md`; #107 |
| Every cleanup, archive and clean slate carries forward every mandate and every return trigger in `docs/problem/MANDATES.md`; none is archived, deleted or dropped with the rows around it. A deferred or waived mandate keeps its trigger test, and `tests/test_mandates.py` fails once the trigger holds | **settled** | 2026-10-05 | user | #107, design approved by the owner 2026-10-05 |
| Looks first (restated 2026-10-05): a plain ±15% band; rank maps by split units per channel (a district owning any ZCTA of a state has split it, zero-opportunity ZCTAs included; counted on the drawn map), then cuts (Σ over split states of districts − 1), then visual defects (one may outrank an extra split, flagged REVIEW), then shape, then balance; main map K 48–54 with $ per district within ±10% of each channel's target. M_c(δ) with μ = 0 is the seed, and a bound only over 𝒳_c(δ), the drawings that follow its family, modes, η and caps; with η > 0 it is not a floor on M1 maps (#91 finding 14). District definition: the region it covers (U50) | **settled** | 2026-10-05 | user | `docs/lenses/COUNCIL_2026-10-05.md` § Owner decisions 1–2 and finding 14; triage rows 1, 2, 5 |
| The certified split minimum ranges over all states, not a free list; the states it names are reported, and any ban is explicit with its cost | **settled** | 2026-10-05 | user | `docs/lenses/COUNCIL_2026-10-05.md` § Owner decisions 3 |
| Report s* (a certified unit-level floor) and each drawn M1 map's split count as s* + g; "minimal" only when g = 0. g is reported only against a bound that covers the map, otherwise "not covered" | **settled** | 2026-10-05 | user; second sentence #91 finding 16 | `docs/lenses/COUNCIL_2026-10-05.md` § Owner decisions 4, finding 16 |
| The state-piece contract (owner, 2026-10-05): territories are whole states except states that provably must split — "strictly build territories at whole state pieces, only splitting states that absolutely must be split"; "must split" is the certified minimum split count over all states (any ban explicit with its cost); the WH/FI quick runs use K WH 10–11 and FI 19–22; the objective optimizes balance in addition to compactness inside the settled ranking. Experiment scope is not problem scope | **settled** | 2026-10-05 | user | #117 (statement v2, the execution contract; owner's words in its body) |
| #110's answer: split and balance floors are certified by the **η-free bounding master** (U_v = min(K, cap_v, \|Z_v\|), no η lower bound); the planning master keeps η for looks; any floor from an η > 0 master is labelled "over 𝒳_c(δ) only" | **settled** | 2026-10-05 | user | #110, owner's answer 2026-10-05 (recorded on the issue); #91 findings 14–16 |
| #103's certifier scope and balance pass (owner, 2026-10-05, decisions A3 and B): s* from today's η-free master (cap_v, support-size limit, zero-mass units dropped) is labelled "over 𝒳_c(δ) only" and never backs "minimal" or "must split"; only an all-M1 bound (#119: no cap beyond K and \|Z_v\|, zero-mass units, every connected footprint) may. The balance pass is a fixed-candidate LP, reported as conditional on its plan, and #103 also hands #109 a pool of plans tied or near-tied on splits, cuts and diameter; the drawn map decides. Neither choice is on the path to a contiguous map | **settled** | 2026-10-05 | user | #103, #119; cf-luna's formulation review |
