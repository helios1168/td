# Problem

What td is solving and what is settled. Owner-owned: agents propose, the owner changes. A settled
decision is one line with the issue that decided it (the record is that issue's `DECIDED` comment).
A revised line is struck through and restated with a new date, never deleted. Detail behind a line
is in the issue or in `docs/archive/` (not read by default). Method: `docs/MODEL.md`.

## Goal

td makes the sales territory maps the owner will put in front of stakeholders: the main map
(national, WH, FI, WIFI and the combined channel) and the IFA map. In each planning channel c,
K_c districts together cover every CONUS ZIP, and each district is:

- **one connected piece of territory on the drawn map** (M1, hard, the reason the project exists);
- **a sensible-looking territory:** few split states, no visual defects, compact;
- **balanced:** drawn opportunity within the band, and $ per district near target.

The output is an audited `(ZIP, fine channel) → district` ledger with maps. The owner picks the
final main and IFA maps from a ranked shortlist ([#105](https://github.com/helios1168/td/issues/105)). Staffing is out of scope. The method (the
support-master problem, [#52](https://github.com/helios1168/td/issues/52)) is a support-based master MILP, a ZIP realizer and that ledger;
anything that serves the goal may change, anything that changes what this file says needs the owner.

## Mandates

Hard requirements; only the owner adds, changes or waives a row, and agents propose. No step may
weaken, relabel or work around a mandate without an owner-decision issue. A row is never deleted,
and a cleanup, archive or clean slate carries every row and every return trigger forward
([#107](https://github.com/helios1168/td/issues/107), owner 2026-10-05). M1 was set aside "for simplicity" on 2026-09-01 with no return
trigger, and for five weeks every map shipped with detached pieces while reports said "pieces are
listed"; that pattern is what this register exists to stop.

Each mandate is a `###` section of this `## Mandates` section with these fields, all required:

- **status:** `hard`, `deferred` or `waived`, nothing else.
- **owner's words:** what the owner said, with the date and the source.
- **definition:** the requirement, precise enough to check.
- **check:** the executable check that fails a map or a run on a violation. A check not yet
  written says which issue builds it.
- **latest value:** the check's value on the best map; `not measured` until a check has run.
- **waiver history:** every time the row was set aside or restored, with date and source.
- **return trigger:** `none` for a `hard` row. A `deferred` or `waived` row names a test,
  `tests/test_mandates.py::trigger_<name>`, that holds once the reason for setting the mandate
  aside is gone; the suite then fails until the owner restores the mandate or renews the waiver.

`tests/test_mandates.py` parses this section and fails on a missing field, a status outside the
three, a deferred or waived row without a trigger test, or a trigger that holds.


### M1: ZIP contiguity

- **status:** hard
- **owner's words:** owner, 2026-10-04, answers recorded in
  `runs/plan_2026-10-04/contiguity/MANDATE.md` §1 (m5, gitignored) and restated in #107.
  Graph: "the drawn 2025 TIGER ZCTA polygons. A district is connected when it looks connected
  on the map." Adjacency: rook, "a shared boundary of positive length; a single touching point
  does not count." Water: "crossings count only through a committed connector list (bridges,
  tunnels, ferries) that the owner reviews once." Coverage: "zero-opportunity ZIPs are
  territory. Every CONUS ZCTA gets a district in every channel, and the ledger, not a display
  fill, assigns it." Tolerance: "none. Any detached piece beyond the connectors fails the map."
- **definition:** in every planning channel of every map, each district's ZCTAs form one
  connected component of the graph whose vertices are all CONUS ZCTAs of the 2025 TIGER ZCTA
  polygons and whose edges are rook adjacency (a shared boundary of positive length; a shared
  corner does not count; a shared boundary shorter than the scorer's thin-link threshold counts
  as connected and stays a looks defect), plus the committed connector list across water, which
  the owner reviews once. Every CONUS ZCTA is assigned by the ledger, zero-opportunity ZIPs
  included. No tolerance: one detached piece fails the map, and listing it is not enough. The
  model plans and draws on this same polygon graph (OD2, `PROBLEM.md`).
  Multipart ZCTAs (owner, 2026-10-05, ruling relayed on #108; 1,429 of the 33,300 are
  MultiPolygons): one ZCTA is one vertex and its own parts always count as connected to each
  other; two ZCTAs are adjacent through a shared positive-length boundary of any of their parts.
  A separate piece on a district's drawn union that only a multipart ZCTA makes is a visual
  defect for the scorer to list, not an M1 failure.
  Connector review (owner, 2026-10-05, #108): every row of `reference/2025/connectors.csv` is
  approved: 52 bridges, 8 tunnels and 22 ferries as listed, and 77 roads across land in no
  ZCTA ("land gaps count when crossed by a named road"); the four islands with no road or
  scheduled ferry (43436, 98281, 98297, 98353) each join their nearest ZCTA by an owner row of
  kind `nearest`. With them the polygon graph is one component.
  Second connector review (owner, 2026-10-05, structured pick "Approve all 16", #114): the 16
  rows #114 proposed are approved: 11 in-state rows, one per group of ZCTAs that reach their
  own state only through another (NY 06390 and VA 23440 by kind `nearest`; roads for TN 37851,
  CA 96134, WY, southeast UT and NV), and 5 state-line roads TIGER names only by route (the
  Delaware Memorial Bridge DE-NJ, I-295/US-40; four Ohio River crossings IL-KY). With them
  every state is connected on its own ZCTAs. No KY-MO crossing is listed.
  Coverage (owner, 2026-10-05, structured pick "Yes, footprint coverage"): a planning channel
  covers every CONUS ZCTA of its own footprint, the units its domains carve, and every
  (ZCTA, fine channel) cell is owned exactly once across the planning channels. Under the
  WIFI partition a carved channel does not cover all of CONUS; the goal's "every CONUS ZIP" is
  met by the channels together.
  Necks (owner, 2026-10-05, in session: "a neck should fail m1"; structured picks "Narrow
  passage on the map" and "No, unless land would do"; then, once #121 showed that a mass clause
  makes single dense downtown ZCTAs necks and no map passable, "Area only" and "One connected
  piece"): a district fails M1 when one connected part of it holding at least 5% of its land
  area reaches the rest only through a passage narrower than 10 km, the passage's width being
  the total shared ZCTA border across the cut. Mass is reported for each neck but does not
  decide it. An approved connector is a passage of unlimited width, except where the district
  could have reached the far side by land; there it has width 0. W = 10 km and 5% are the values
  of the option the owner picked; only the owner changes them. "By land" means joined in the
  polygon graph without connectors, within the states the district owns ZCTAs in, through a
  land passage that is itself at least 10 km wide (owner, 2026-10-05, structured pick "Land
  must be a real passage", #121, after WH_09's IN+KY bridges were judged against a 4.4 km
  strip at Evansville); a narrower land route leaves the connector at full width. The part cut
  off is the smaller side (owner, 2026-10-06, structured pick "Cut-off part = smaller side",
  #121, after Sol's review found a 6% hub with 24 lobes under 5% each, on 100 m threads,
  passing): one connected part with at least 5% of the land and no more land than the rest,
  which may lie in pieces; small fringes off a larger body are never added together.
  Coverage gaps (owner, 2026-10-08, structured pick "Measure width across coverage gaps", G1,
  #131, after IFA TX K 3's El Paso + Trans-Pecos part met the rest of Texas by one 6.14 km
  polygon edge, 79718-79734, across desert over 100 km wide): a passage's width also counts land
  in no ZCTA between the district's polygons, so a coverage gap is not a neck. In effect now (owner,
  2026-10-08, G3: "lets pass it or make an exception ... that is a GREAT looking map", confirmed
  in the orchestrator as "use 1 now"): maps are gated with the G1 prototype on
  (`TD_NECK_GAP_WIDTH=1`, branch `m5-studio/explore-neck` d312834) and report both verdicts;
  any verdict other than TX El Paso that the flag flips goes to the owner. #131 lands the width on
  main as the default.
- **check:** the polygon contiguity check `td/audit.py::check_m1` (#108), run by every td run
  on the extract, and its run-folder gate `tools/mandates/check.py::m1`, which the looks scorer's
  eligibility also applies; pinned by
  `tests/test_mandates.py::test_m1_fails_each_broken_fixture_and_passes_the_connected_one` on the
  broken fixtures in tests/fixtures/m1/.
- **latest value:** necks: not measured until #121's check runs. 75 of 75 drawn runs fail (2026-10-05, `tools/mandates/check.py --rescore`,
  #108). Best map, the scorer's rank 1: `sweep/must_2026-10-01/stage2/A_fi1600_v1_na16_WH13_FI24`,
  M1 fail, largest detached piece 0.272 τ (national/national_08, 908 ZIPs in CT+MA+RI) after display
  fill; strictly on the ledger 2924 detached pieces and 89675 channel ZCTAs with no owner. Smallest
  largest piece across runs: 0.252 τ (national/national_10, 545 ZIPs in DE+MD), `exp81/hess`.
- **waiver history:**
  - 2026-09-01, set aside "for simplicity" (`d50bd42`) as the PROBLEM.md row "Adjacency
    contiguity is not required | settled | 2026-09-01 | user | 547 components. Reopenable only
    by the full-ZCTA-graph experiment." No trigger test.
  - 2026-09-28, the reopen condition was met (#62 built the ZIP graph over all 33,300 CONUS
    ZCTAs) and not acted on; the same day the #54 clean slate (`ce9f282`) archived the row in
    `archive/pre-support-2026-09`.
  - 2026-10-04, restored as hard by the owner, on the polygon graph.
- **return trigger:** none

### Masking: sales and names stay in the extract

- **status:** hard
- **owner's words:** owner, 2026-09-30 and 2026-10-01, `AGENTS.md` (`f98b9a3`): "sales,
  wholesaler (rep) names and firm names never enter this repo, an issue, a memory or anything
  online."
- **definition:** sales, the per-rep shares (`share`, `share_free`), the `firm` map, and rep and
  firm names never leave the extract: not into the repo, an issue, a memory or anything online.
  The exporter writes surrogate ids (`R…`, `F…`) and no currency amount, the model does not read
  the shares or the firm map, and `instance_descaled*.json.gz` is gitignored. Descaled
  opportunity, dollar opportunity and everything the model makes from them are not masked.
- **check:** `tests/test_export_instance.py::test_rep_books_stay_with_surrogate_ids_ranked_by_total_book`,
  `tests/test_export_instance.py::test_guard_refuses_an_unstripped_scale_a_currency_amount_or_a_negative_mass`
  and `.gitignore`.
- **latest value:** not measured.
- **waiver history:** none. Narrowed by the owner on 2026-09-30 from "confidential" to masking,
  and on 2026-10-01 to let dollar opportunity appear.
- **return trigger:** none

### T1: Tracking: every map run is tracked, every map shown is on the shortlist

- **status:** hard
- **owner's words:** owner, 2026-10-05, in session: "I'm having trouble easily keeping track what
  m1, deck b, m2, m3 means, where the maps are, etc.", then on the proposed fix (shortlist the
  eligible maps under descriptive ids, retire ad-hoc labels, track contig runs in the #92
  tracker): "yes do the shortlist fix, file the issue, and add this to mandate.md so that the
  advisor can monitor for deviation against this going forward" (#120).
- **definition:** (1) every run that draws a map, whether `td run`, a sweep or a `tools/exp/*`
  drawing or repair, writes its folder under `runs/exp/<lane>/<run_id>/` with a `manifest.json`
  in #92's format (code commit and dirty flag, command, scenario, instance, status, and the
  parent run of a repair or any run derived from another), so `tools/exp/index.py` indexes it; no
  hand-written launcher writes a map run that the tracker cannot see. (2) Every map put in
  front of the owner or stakeholders is an entry in the shortlist registry (`shortlist.json`:
  id, tier, rank, label, run path, image paths, notes) and the generated
  `runs/shortlist/INDEX.md` is rebuilt; a map that drops out moves to a superseded tier and is
  never deleted. (3) Reports, issues, decks and conversation name a map by its shortlist id
  and label (layout and K per channel) and give its image path; ad-hoc labels that are on no
  shortlist ("M1", "M2", "deck B") are not used, and "M1" means only the contiguity mandate.
- **check:** the tracking check, `tools/mandates/check.py::tracking` (CLI: --tracking, #120): it
  fails a run folder under runs/exp/ with a ledger and no manifest; a shortlist entry of
  `tools/shortlist/shortlist.json` whose run folder, manifest or image is missing, whose image is
  not the output of `tools/maps/render.py` in its run folder (no render.json, or a stale one), or
  whose recorded M1 differs from a fresh run of the gate; and an id used by more than one entry.
  Part (3) is checked by the mandate advisor reading the session.
- **latest value:** pass (2026-10-06, `tools/mandates/check.py --tracking` on m5-studio's runs/,
  #120): 121 run folders with a ledger under runs/exp, 25 shortlist entries, 0 failures.
- **waiver history:** none.
- **return trigger:** none

## Settled

One line each. The deciding issue is linked; where it carries no `DECIDED` comment the record is
the file named.

**Scope and frame**

- The support-master scope, the clean slate and decisions S1-S31 (owner, 2026-09-25; plan approved 2026-09-28): [#52](https://github.com/helios1168/td/issues/52).
- OQ1-OQ7 of [#52](https://github.com/helios1168/td/issues/52) (where the corrections land, U-number ranges, a disconnected whole unit stops the run, file caps): the owner's answers on [#52](https://github.com/helios1168/td/issues/52). OQ6: a district's part of a unit need not itself be connected.
- Outputs are district-only plans with no staffing claim; master-solve tiers are exact, bounded or feasible only, and a certificate is earned, never claimed (owner, 2026-09-28; OD3): [#58](https://github.com/helios1168/td/issues/58).
- Metros: scenario-listed 2025 metropolitan CBSAs (county unions), off by default; a fitting metro is whole, an oversized one is its own splittable unit, a cross-state metro keeps its unit (OD5): [#60](https://github.com/helios1168/td/issues/60).
- The ground set is the 2025 ZCTAs in the 48 states and DC; ZIPs with no ZCTA are excluded (owner): [#63](https://github.com/helios1168/td/issues/63).
- The authoritative ZIP graph is the 2025 TIGER ZCTA polygon rook graph with a committed connector list; the model plans and draws on it (OD2, owner 2026-10-04, supersedes the Voronoi graph): [#57](https://github.com/helios1168/td/issues/57) and M1 ([#107](https://github.com/helios1168/td/issues/107)).
- CA/TX/NY/FL band breaks are retired and a reported smallest master δ is never adopted by default (OD1, 2026-09-28); the band itself is the row under Band below: [#56](https://github.com/helios1168/td/issues/56).
- Zero-opportunity ZIPs are territory; a district is the region it covers (owner, 2026-10-04/05): [#82](https://github.com/helios1168/td/issues/82) and [#91](https://github.com/helios1168/td/issues/91).
- A band the model did not meet is reported, never silently loosened; runs are deterministic and reproducible from git (owner, 2026-10-01 brief): [#56](https://github.com/helios1168/td/issues/56).
- Every (ZCTA, fine channel) cell is owned exactly once by the ledger, zero-opportunity cells included: [#116](https://github.com/helios1168/td/issues/116).

**Looks first (owner, 2026-10-05)**

- Eligible maps are ranked: split units per channel, then cuts, then visual defects (one may outrank an extra split, flagged REVIEW), then shape, then balance; never balance first: [#91](https://github.com/helios1168/td/issues/91).
- Split units = Σ over channels of the units v with r_v ≥ 2 districts holding positive opportunity in v (a state split in WH and in FI counts 2; CA in 5 districts counts 1); cuts = Σ (r_v − 1); a district owning any ZCTA of a state has split it: [#90](https://github.com/helios1168/td/issues/90) and [#91](https://github.com/helios1168/td/issues/91).
- The certified split minimum ranges over all states, not a free list; any ban is explicit with its cost: [#91](https://github.com/helios1168/td/issues/91).
- Report s* (a certified unit-level floor) and each M1 map's splits as s* + g; "minimal" only when g = 0 against a bound that covers the map: [#91](https://github.com/helios1168/td/issues/91).
- A floor from a master with η > 0 bounds only the drawings that follow its family, modes, η and caps; it is no floor on M1 maps and is labelled "over 𝒳_c(δ) only": [#91](https://github.com/helios1168/td/issues/91).
- Floors are certified by the η-free bounding master; only an all-M1 bound ([#119](https://github.com/helios1168/td/issues/119)) may back "minimal" or "must split"; the balance pass is a fixed-candidate LP reported as conditional on its plan: [#110](https://github.com/helios1168/td/issues/110) and [#103](https://github.com/helios1168/td/issues/103).
- The state-piece contract: whole states except where a split is provably needed ("must split" = the certified minimum over all states); the WH/FI quick runs use K WH 10-11 and FI 19-22: [#117](https://github.com/helios1168/td/issues/117).

**Band and K (owner, 2026-10-07/08; supersedes the plain ±15% and ±10% rows)**

- Every district's drawn $ is within ±15% of its channel's target (national $1.25B, WH $1.0B, FI $900M), planned and judged the same way; WIFI, with no target, within ±15% of its dollar mean: [#130](https://github.com/helios1168/td/issues/130) (record: `docs/archive/lenses/review-2026-10-07/`, `docs/archive/lenses/research-2026-10-08/DECISIONS-2026-10-08.md`).
- $ is m_rel times each fine channel's whole-extract rate (IFA $1.25197M per m_rel); off-map $ is not credited: [#130](https://github.com/helios1168/td/issues/130).
- IFA is judged in the window −20%/+15% of $1.25B ($1,000M-$1,437.5M); the audit's τ ±15% line is information only: [#130](https://github.com/helios1168/td/issues/130).
- IFA has one waiver district, MD+DE+WV whole (about $1,924M, 54% over target), recorded on every map that uses it; no other district is exempt (F1 widened, owner 2026-10-08): [#130](https://github.com/helios1168/td/issues/130).
- Main-map total K is 48-54 and IFA K is 46-55 from the grid; "IFA K ≥ 50" is revoked (F2): [#130](https://github.com/helios1168/td/issues/130).
- IFA Midwest borrows Colorado (KS splits into KS-east + MO and KS-west + CO; CO leaves Mountain for the Midwest), owner 2026-10-08, branch `m5-studio/ifa-midwest` a234f5d: [#130](https://github.com/helios1168/td/issues/130).

**Necks and gap width (owner, 2026-10-05/08)**

- M1's rulings (multipart ZCTAs, the 159 + 16 approved connectors, footprint coverage, necks at 5% of land and 10 km, smaller side, gap width) are in the M1 row above: [#108](https://github.com/helios1168/td/issues/108), [#114](https://github.com/helios1168/td/issues/114), [#121](https://github.com/helios1168/td/issues/121), [#131](https://github.com/helios1168/td/issues/131).
- G1: a neck's width also counts land in no ZCTA between a district's polygons; G3: until [#131](https://github.com/helios1168/td/issues/131) lands it is in effect with `TD_NECK_GAP_WIDTH=1`, both verdicts reported, any flip other than TX El Paso goes to the owner: [#131](https://github.com/helios1168/td/issues/131).
- G2: an IFA district holding Manhattan also holds the Bronx and Westchester, and NY is planned with a land floor for thin units: [#132](https://github.com/helios1168/td/issues/132).
- The 58 shortlist renders made before [#128](https://github.com/helios1168/td/issues/128) stay as they are and their T1 "render not current" failures are accepted; do not ask again (owner, 2026-10-08): [#128](https://github.com/helios1168/td/issues/128).

**Tracking**

- Every map run is tracked under `runs/exp/<lane>/<run_id>/` with a `manifest.json` and every map shown is a shortlist entry named by id and label (mandate T1, owner 2026-10-05): [#120](https://github.com/helios1168/td/issues/120).

## Open (tracked as issues)

Never settle these by default, in code or in prose.

- Output catalog and bundles: county pieces ([#59](https://github.com/helios1168/td/issues/59), OD4); the catalog of channels, bundles, WIFI, K grid and caps ([#75](https://github.com/helios1168/td/issues/75), OD6); new channels ([#76](https://github.com/helios1168/td/issues/76)); the fresh v3 extract ([#3](https://github.com/helios1168/td/issues/3)); heavy ZIPs, territory or booking addresses ([#83](https://github.com/helios1168/td/issues/83), U52).
- How M1 is achieved and what gives way when a share cannot be drawn connected ([#112](https://github.com/helios1168/td/issues/112)); the smallest share that counts beyond a split ([#111](https://github.com/helios1168/td/issues/111)); the ZIP-grain planner ([#102](https://github.com/helios1168/td/issues/102)); charging for state pieces ([#80](https://github.com/helios1168/td/issues/80)).
- The within-state IFA land balance ([#133](https://github.com/helios1168/td/issues/133), R = 10 taken as an assumption overnight); the NE + plains split floor ([#115](https://github.com/helios1168/td/issues/115), U58); the all-M1 bounding master ([#119](https://github.com/helios1168/td/issues/119)); the final main and IFA maps ([#105](https://github.com/helios1168/td/issues/105)).
- The dollar windows the overnight grid scores with (national floor $1,000M, WIFI $850-1,150M, a whole-state WIFI district up to $1.6B) are in the scorer but not filed here as owner decisions: confirm on [#130](https://github.com/helios1168/td/issues/130) before relying on them.
- Open unknowns with no open issue (file one before working on one): the swap rule (A is an interim default, B open; [#85](https://github.com/helios1168/td/issues/85) closed), metros beyond NYC (OD5 stays open there), the Hess side-by-side reading (U38), and U40-U48, U55-U57 and U59-U65 in `docs/archive/problem/UNKNOWNS.md`.
