# Proposed PROBLEM.md text: M1's neck rule, water and empty land (owner, 2026-10-14)

Written by worker (claude-bridge/claude-sonnet-5-5) for the supervisor to show the owner. `PROBLEM.md` is
not edited. The code is on the branch of this commit (`td/audit.py`: `NeckGraph`, `district_necks`,
`check_m1`); the rescore of the grids under it is in `/tmp/td-m1-rescore/TABLE.md` (summarised in the
worker's report).

The owner's words (2026-10-14, answering "which water rule"): picked "(a) Any water crossing. A neck
or detached piece passes if its narrow passage is an approved water connector (bridge, tunnel or
ferry)... Narrow land necks (Cincinnati, El Paso, Utah) would still fail", amended: "(a) except we
should treat necks that are surrounded by empty or zero-opportunity zips the same way we treat water,
which i believe is what happened to el paso". Also: "keep the manhattan exception and in general those
water split cases are ok".

## 1. Replace, in the M1 row's **definition**, from "An approved connector is a passage of unlimited width, except ..." to "... leaves the connector at full width."

Old text (PROBLEM.md lines ~95-102):

> An approved connector is a passage of unlimited width, except where the district could have reached
> the far side by land; there it has width 0. W = 10 km and 5% are the values of the option the owner
> picked; only the owner changes them. "By land" means joined in the polygon graph without connectors,
> within the states the district owns ZCTAs in, through a land passage that is itself at least 10 km
> wide (owner, 2026-10-05, structured pick "Land must be a real passage", #121, after WH_09's IN+KY
> bridges were judged against a 4.4 km strip at Evansville); a narrower land route leaves the
> connector at full width.

Proposed text:

> An approved connector (a bridge, tunnel or ferry, a road across land in no ZCTA, an island's
> `nearest` row) is a passage of unlimited width, always (owner, 2026-10-14, "(a) Any water
> crossing. A neck or detached piece passes if its narrow passage is an approved water connector
> (bridge, tunnel or ferry)"; "keep the manhattan exception and in general those water split cases
> are ok"). This replaces the 2026-10-05 rule "No, unless land would do" and its refinement "Land
> must be a real passage" (#121): a connector no longer has width 0 where the district could have
> reached the far side by land. W = 10 km and 5% are the values of the option the owner picked; only
> the owner changes them. A neck through populated land still fails (Cincinnati, El Paso without the
> rules below, Utah).

## 2. Replace the **Coverage gaps** paragraph (from "Coverage gaps (owner, 2026-10-08 ...") with

> Empty land counts towards a passage (owner, 2026-10-08, structured pick "Measure width across
> coverage gaps", G1, #131, after IFA TX K 3's El Paso + Trans-Pecos part met the rest of Texas by
> one 6.14 km polygon edge, 79718-79734, across desert over 100 km wide; extended 2026-10-14, "(a)
> except we should treat necks that are surrounded by empty or zero-opportunity zips the same way we
> treat water, which i believe is what happened to el paso"). A passage's width also counts (R2)
> land in no ZCTA between the district's polygons, and (R3) ZCTAs of zero opportunity in the
> district's planning channel, whichever district owns them or none: all of a ZCTA's rows in that
> channel have m = 0. Such a ZCTA is a relay in the width graph: the passage through it is as wide
> as its narrowest link, and it holds no land area or mass for the 5% share. A ZCTA of positive
> opportunity that another district owns is never a relay, so a narrow neck through populated land
> fails as before. R2 is the default (G3's `TD_NECK_GAP_WIDTH=1` flag is retired: `=0` opts out for
> comparison); #131 lands the width on main. R3 changes widths only: a district whose parts touch
> only through empty land is still in pieces, and a detached piece still fails (no change to the
> piece rule). The Manhattan neck of the IFA map is an owner exception (2026-10-14), kept whether or
> not the rule above clears it; it is named at the map, not coded.

### 2b. R5, add to the same paragraph (owner, 2026-10-14, recorded on #140, "yes")

> In the pieces check too, two ZCTAs of one state that face each other across land in no ZCTA are
> adjacent (R5): a district whose parts are separated only by such land is one piece. The edges are
> the land-only gap land of `reference/2025/zcta_gap_land.csv.gz` (`geo.polygon_graph`'s `gaps`), never
> across water and never across a state line; a pair across water, or one only the Voronoi rows
> give, joins nothing. The switch is the same as G1's (default on, `TD_NECK_GAP_WIDTH=0` opts out).
> Reassigning zero-opportunity glue ZCTAs is a repair-step change and is not part of this rule.

**R5 is coded but inactive on every real map today.** `zcta_gap_land.csv.gz` is not in
`reference/2025/` (the repo ships only the Voronoi rows, `zcta_polygon_vs_voronoi.csv.gz`, columns
`a,b,change,border_m`, which carry no land/water marker, so they cannot be made land-only). Building the
file needs `python -m td geo --gap-land --public $TD_REPO/data/public` with the gazetteer, county and
FACES/AREAWATER downloads that `data/public/` does not hold, and writes into `reference/2025/` and
its `MANIFEST.json`, outside this task's files. `geo.polygon_graph()["gaps"]` is empty (0 pairs), so
`check_m1` says "R5 inactive" in its summary and `counts["gap_edges"]` is 0. Fixtures in
`tests/test_neck_water_empty.py` cover the rule on toy graphs (one piece across land; two pieces across
water, across a state line, or with the switch off). R2 (neck width) falls back on the Voronoi rows
when `gaps` is empty, as the G1 prototype did, and those rows can cross water.

## 3. Waiver history: add after the 2026-10-04 line

> - 2026-10-14, the neck rule was loosened by the owner, not waived: approved connectors are
>   unlimited width always (the "land would do" width 0 is retired); empty land (no ZCTA) and
>   zero-opportunity ZCTAs of the channel count towards a passage's width; land-only gap edges join a
>   district's pieces (R5, coded, inactive until the gap file ships). The detached-piece rule otherwise,
>   the 5% share, the 10 km width and "narrow land necks still fail" are unchanged
>   (`td/audit.py`, `tests/test_neck_water_empty.py`, `tests/test_neck_gapwidth.py`; the old rule is
>   the opt-in `TD_NECK_PRE_2026_10_14_LAND_RULE=1`).

## 4. Other lines that would change when the owner closes this

- "Necks and gap width" block: the G3 line ("until #131 lands it is in effect with
  `TD_NECK_GAP_WIDTH=1`, both verdicts reported, any flip other than TX El Paso goes to the owner")
  becomes: "G1 and R3 are the default (owner, 2026-10-14); the opt-outs are for comparison".
- `latest value` of M1: rewrite by `tools/mandates/check.py --rescore ... --write-register` once the
  owner accepts the rule; the worker did not run `--write-register`.
- The pinned test row: `tests/test_mandates.py::test_m1_fails_each_broken_fixture_and_passes_the_connected_one`
  moved the fixture `connector_land_would_do` from the broken set to the passing set (it fails only
  under the opt-in old rule); no other fixture changed.

## 5. Not changed by the worker (follow-ups)

- `td/supports.py` (`Contact.connects`, `contact`), `tools/exp/contig/repair.py:230` (`neck_cuts`
  widths) and `tools/exp/contig/plancheck.py` still read `NeckGraph.land_would_do` directly: the
  master and the repair treat a connector as 0 km where land would do, so they are stricter than the
  new M1 on connectors (MODEL.md §9 says so). They need the owner's word on following the new rule.
- `NeckGraph` now defaults to `gap_width=True`, so repair/replan/plancheck widths follow G1 too.
