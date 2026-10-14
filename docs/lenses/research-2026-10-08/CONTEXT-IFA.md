# IFA decision context (2026-10-08)

## Decision
Owner must choose IFA treatment for Maryland under rule C: R1 jointly carve MD+PA district, R2 use whole-county MD units, R3 exempt IFA from rule C, or R4 change IFA band; and decide whether D1, “IFA at K ≥ 50 under rule C,” survives after E2 made each district’s dollar band K-independent. No recommendation here. Assumption: “feasible” below means only arithmetic feasibility unless an actual whole-ZIP gate-passing partition is cited; arithmetic does not prove drawability/M1.

## Owner words to date
Quotes as transcribed in dated decision record `docs/lenses/REVIEW_2026-10-07.md` § Owner decisions and `review-2026-10-07/CONSOLIDATED.md` § Owner answers:

- IFA K/rule C (2026-10-07, D1): **“IFA at K ≥ 50 under rule C”.** This is explicit decision; D1 was not formally revoked in the cited record.
- Band (2026-10-07, E2): **“IFA lower edge −20%”**; districts range −20%/+15% of $1.25B. E1: **“Extract rate, as coded”** ($1.251968155812553M/m_rel). Bounds are L=798.74, U=1,148.19 m_rel, independent of K.
- Older band choice (2026-10-07, D2): **“±15% (the eligibility band)”**; D3: **“Every district vs target”, tolerance “±15% of target”**. E2 later sets IFA-specific −20% lower edge.
- Extra splits (D4/D5, 2026-10-07): **“Add splits; no policy bans”.**
- County units: PROBLEM.md row OD4 says **open**, #59; `RESULTS.md` #127 demonstrates county-piece method but does not resolve IFA OD4 policy. No explicit owner quote approving county pieces for IFA found in searched sources.
- Rule C: 2026-10-07 decision says under rule C; no owner words found authorizing an MD exception, IFA-only exemption, or fresh band change. These remain owner choices.

Session search ran all six requested topic queries. Relevant prior sessions identified: `td-review-fable` and `td-review-astra` (2026-10-07), `contiguity` (2026-10-05), and `td-research` (2026-10-08). Search results/available records confirm exact owner quotes above; separate verbatim session entries on county units or IFA-specific rule C not established. Do not treat reviewer proposals as owner words.

## Arithmetic
Source ledger: `/Users/Shared/sv-ntlee/td/runs/exp/contig/whole127/ifa46-whole/ledger.csv`, aggregated `model_channel=IFA` by state. Rate r=1.2519681558 M$/m_rel; band [L,U]=[798.74,1,148.19]. State table (m_rel; $M approximate):

| State | m_rel | $M | State | m_rel | $M |
|---|---:|---:|---|---:|---:|
| MD | 1203.64 | 1507 | DC | 13.81 | 17 |
| DE | 211.30 | 265 | WV | 121.67 | 152 |
| VA | 1120.63 | 1403 | PA | 3290.48 | 4118 |
| NJ | 2837.32 | 3552 | CT | 1333.63 | 1670 |
| RI | 342.56 | 429 | NY | 4368.97 | 5469 |
| MA | 1535.40 | 1922 | NC | 1066.28 | 1334 |
| SC | 656.63 | 822 | GA | 926.78 | 1160 |

Dollars rounded; rate conversion from ledger aggregates. Rule-C MD test: MD > U, hence MD must split. Two MD pieces need combined attach mass at least `2L−MD = 393.84`. DC+DE+WV = 346.78, short 47.06. VA has only U−VA=27.56 room for MD; PA must split (and therefore is unavailable as whole attach). Hence no rule-C MD arrangement at E2, for all K. At D3’s ±15% lower bound L=848.66, two pieces need 493.68 attachment, so also impossible. `CONSOLIDATED.md` round 3 reports verified conclusion: IFA infeasible under rule C at E2 and D3 ±15%, because MD; not a K issue.

Route tests:
- **R1 MD+PA joint district:** could alter rule-C structural restriction by allowing declared joint MD/PA pieces; PA’s pieces become potential joint attachments. No recomputed mass screen or carved joint pattern found. Arithmetic alone cannot establish feasibility; exception schema/library/master must agree and M1 gate every district.
- **R2 whole-county MD pieces:** #127 county-piece maps are precedent, but only selected states NY, CA, FL, PA, NJ, TX, MI, OH (+ IL, MA, CT) were cut; MD not included. County-piece granularity might allow valid masses, but county masses/partition not computed. Rule C “formally” satisfied only under OD4 county-unit interpretation; original-state split accounting must remain.
- **R3 no rule C:** removes obstruction identified specifically by rule C, but no fresh IFA M1 map/current band result established. Existing #127 maps do not suffice: zero M1 failures, yet all six are scorer-ineligible on ±15% band (`RESULTS.md` #127). No proof Northeast corridor risk vanishes.
- **R4 band change:** if change only U enough to hold MD whole, minimum arithmetic upper bound is U≥1,203.64, +55.45 m_rel (+4.83% over E2 U); equivalent upper dollar bound ≈$1,507M, about +$69M over $1,437.5M. This is sufficient only for MD-alone mass ceiling, not overall IFA plan. If retaining two MD pieces, reducing L to ≤775.21 makes DC+DE+WV aggregate meet the simple combined requirement, a 23.53 m_rel decrease; this ignores VA capacity / piece-level upper constraints, so not established sufficient. No smallest globally feasible band change can be derived from records; “R4 minimum” remains unproven.

## Routes, cost, constraints, reviewer/oracle evidence
No route is built as an IFA solution. Checkpoint says no wave launched / implementation absent (`REVIEW_2026-10-07.md` Status). Thus tonight implementation time is unknown; route requires design + pattern/map generation + complete audit, not a known turnkey operation. No responsible hour estimate evidenced.

| Route | Requirement / costs / decisions touched | Evidence |
|---|---|---|
| R1 | Joint MD+PA carve exception in both master and pattern library; changes rule-C scope; potential split/cut costs unknown; joint carving and M1 verification needed. | Review open-route row explicitly says proposed row is unreviewed and stage-0 screen must be rerun. Fable says MD/PA joint district mirrors Philadelphia–Wilmington drawn maps. Oracle: joint patterns require corresponding relaxation in lower-bound master; otherwise certificate domain mismatch. |
| R2 | Partition MD into whole counties; county-level units / generation and audit; OD4 remains open. Could increase split-state pieces/cuts; count and band impact unmeasured. | #127 `RESULTS.md` details county method and success elsewhere (1–3 min per whole-unit run, not this route); states county pieces are starting point. No MD-specific test. |
| R3 | Remove rule C for IFA only; direct policy/method change, retain M1 hard. Split count/cuts may change, unmeasured. | Review calls this separate track. Oracle says rule C is a separate restriction, not M1; absent rule C does not remove corridor M1 risk. Existing K49 sequential realizer report has unresolved pieces prior repair, and repaired map passes M1 but historical band differs; not current proof. |
| R4 | Owner-approved OD1 band change; potentially relaxes upper and/or lower bound; dollar eligibility changes and recheck all districts. No global minimum established. | E2 is already owner-set band; only owner may further change. Review says other band change is open route. Oracle insists arithmetic pass is not carve certificate. |

Shared constraints: M1 is hard (MANDATES.md §M1); no agent may weaken/work around mandate; OD1 and OD4 are owner decisions (PROBLEM.md). Rule C is a modeling choice in REVIEW, not M1 itself. Results #127: six whole/county-piece IFA map variants all gate-pass M1 but fail old ±15% scorer band; do not call them current eligible dollar maps.

## D1 status
D1 says “IFA at K ≥ 50 under rule C” (2026-10-07). Its original rationale involved CT thresholds depending on K under mean-centered bands. E2 switched IFA to fixed-dollar bounds; CT’s old K threshold no longer applies. But checkpoint later finds stronger obstruction: MD infeasible under rule C at every K under E2 (and D3 ±15%). Therefore D1’s combination has no feasible IFA map under current conditions. `REVIEW_2026-10-07.md` labels D1 **“Overtaken”** and says K no longer matters; CONSOLIDATED says “D1’s K≥50 no longer has a reason; IFA’s K is set by grid within 46–55.” Oracle cautions changed rationale is not formal revocation: because owner explicitly said D1, present K46–49 as requiring owner confirmation, not as already authorized. Confirming D1 keeps K floor 50 if a route solves MD; revoking/overriding it permits 46–49 search but cannot by itself cure MD. Under any route, K choice still affects global allocation / result; local dollar band does not depend on K.

## Unestablished facts / assumptions
- No current route-specific IFA plan, MD county aggregate test, R1 amended screen, R3 M1 result, or full R4 band-search result.
- No new IFA dollar-per-district audit on #127 ledgers at E1 rate. Their published scorecards use historical checks; treat as M1 evidence only.
- “R4 minimum” table gives two local arithmetic thresholds, not a sufficient global solution. Assumed modifying one band edge at a time; exact policy meaning of “smallest” (one edge vs max percentage change) was not specified.
- Neighbour/attachment analysis follows reviewed whole127 state masses and stated constraints; it is a necessary screen, not an exhaustive county/ZCTA carve search.

LEARNED: Under E2 and rule C, Maryland arithmetic obstruction is K-independent; existing #127 M1-passing IFA maps fail their recorded balance eligibility and do not answer current E1 dollar-band question.
LEARNED: County-piece OD4 remains open; #127 county-piece implementation covers named states but does not establish Maryland county feasibility.
DECIDED: none
