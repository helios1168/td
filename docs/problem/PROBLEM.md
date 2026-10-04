# Problem ledger

What is settled and what is open about td's problem. One row per item; a revised row is struck
through and restated with a new date, never deleted. Rows below the seed line are appended by
the `triage` skill from lens, council and review output.

## The problem

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
| OD2: the authoritative ZIP graph | **open** | 2026-09-28 | user | #57; blocks G1 |
| OD3: output status and certificate tiers | **open** | 2026-09-28 | user | #58 |
| OD4: county pieces and how they are drawn | **open** | 2026-09-28 | user | #59; decided on D1's free-mode splits |
| OD5: the metro outline and the oversized-metro rule | **open** | 2026-09-28 | user | #60 |
| OD6: the catalog (channels, bundles, WIFI, K grid, support caps) | **open** | 2026-09-28 | user | #75; decided on E1's scorecards |
| F1: the new planning channels and bundles | **open** | 2026-09-28 | user | #76; after the fresh extract (#3) |

<!-- seed line: rows above were seeded 2026-09-28 (td#54) from #52; append below -->
| Looks first: a plain ±15% band (as ±10%, no per-channel exception count); rank maps by channel-state splits, then visual defects (one may outrank an extra split, flagged for review), then shape, then balance; main map K 48–54 with $ per district within ±10% of each channel's target. Supersedes the council's balance-first framing; M_c(δ) with μ = 0 stays the bound and seed. District definition open (U50); OD1 (#56) still records the final band | **settled** | 2026-10-04 | user | `docs/lenses/COUNCIL_2026-10-01.md` § Triage (the owner's 2026-10-04 answers) |
