# National under the regional recipe: plan (2026-10-08)

Drafted in the td-research tab after the IFA CONUS map (`ifa_conus_v2`, 38bcd2d) shipped.
Status: draft, revised twice after the owner's answers of 2026-10-08 (G5 in
`research-2026-10-08/DECISIONS-2026-10-08.md`): a fresh main-map run from scratch on a new grid
with the WIFI region and every channel's K on the axes, sealed regions per channel in place of
the distance, support-size and free-list knobs, dollar-scaled masses, national K 14 allowed.
Nothing here is a run or a registration.

## 1. The recipe the IFA map was built with

What changed between the 2026-10-07 pipeline and the IFA night, in the order a run uses it:

1. **A fixed dollar window per district, not a τ band.** Every district is judged against the
   channel's window (D3: target ±15%; IFA's E2 edge −20%). The planner still takes a τ ± δ band,
   so δ is chosen so that τ(1 ± δ) sits inside the window, and `merge.py --window` reports
   in/under/over per district. The audit's τ line is information only and `final_delta` is never
   tuned to make it agree (owner, E2 pick).
2. **Arithmetic first.** Per-state dollars at full precision from the extract, states over U
   marked "must split", states under L marked "must attach", K bounded by total/U and total/L,
   and whole-state groupings enumerated under rule C (a district holds whole states, or a piece
   of one split state plus whole states) before any solver runs. The screen is a necessary
   condition only: geometry, M1 and shape are not settled by it.
3. **Regions that seal.** Each region is a set of states whose districts stay inside it, so
   regions solve in parallel and merge without re-routing. A region is chosen so that it closes
   under rule C and the window; where it cannot (IFA's Midwest needed Colorado), one borrow is an
   owner decision.
4. **Draw on the induced graph.** `run.py --states A,B,...` plans and draws on the polygon graph
   restricted to the region (keeping only connectors with both ends inside) while the audit runs
   on the full graph. Single-state runs for split states; multi-state runs where a piece rides
   with whole states (`ifa_pac_k5`: OR+WA + a CA piece).
5. **Coarse units when the ZIP draw fails on necks.** Congressional districts (`coarse.py`) tile
   a state with contiguous units and solve in seconds; the only clean NY K 5 and MI K 3 came
   from them. Senate districts did not help.
6. **Local repair windows for necks and pieces.** `repair.py --states --window LO,HI` frees the
   ZCTAs around a neck and re-solves inside the window; most windows close in under 5 s, and a
   window that returns "unknown" twice is abandoned, not retried.
7. **Gates with both verdicts.** `td.audit` M1 on the full graph (pieces, necks, every cell owned
   once); the G1 gap-width prototype (`TD_NECK_GAP_WIDTH=1`) beside the default gate, with G3
   exempting coverage-gap necks only; any district whose verdict the flag flips is reported.
8. **Merge by cell, re-gate, export.** `merge.py` assembles source runs into one ledger keyed by
   (ZCTA, fine channel), hard-errors on a cell claimed twice, re-audits the merged ledger on the
   full graph, writes the window column, and `export_long.py` / `export_geojson.py` produce the
   deliverables under the G4 scenario id.
9. **Orchestration.** One orchestrator tab per region, workers with explicit deadlines, no review
   step, a 12-process solver cap, and a clock with a hard stop where the merge runs on whatever
   arrived. Shape is the owner's gate: a passing map they call atrocious is not done.

What the recipe does not do: no balance-only repair exists (`repair.py` triggers on pieces and
necks), so a connected district with low dollars needs a redraw; and the planner's own neck graph
ignores the G1 flag.

## 2. What is different about national

National is one channel of the joint main map, not a map of its own.

- **Three fine channels, three rates.** National plans `national_chase`, `wells_wh` and
  `wells_fi` together (rates $1.234M, $1.240M and $1.178M per m_rel). A τ band in m_rel is not a
  dollar band: the rates spread 5%, so a district's dollars can leave the window while its mass
  is inside. IFA had one rate and never met this. See Q2.
- **Fifteen states are combined.** ME NH VT MA RI CT ID MT ND NE SD WY NM OK KS route all five fine
  channels into WIFI (3 districts, E3 passes). Their national dollars ($639M) are not national's
  to plan. The 34 pure states plus DC hold $16,980.6M.
- **Other channels are fixed.** FI passes D3 in both lead candidates (20/20) and WIFI passes E3
  (3/3); WH fails only on WH_09 ($840.8M, IN+KY+MI+WI, $9.2M short). A national redraw must leave
  every WH, FI and WIFI cell exactly where it is. `merge.py` keys cells by (ZCTA, fine channel)
  already, but it treats a source as owning whole ZCTAs; it needs a per-source channel filter so
  a national-only run can be merged over the lead ledger's other channels.
- **Planner knobs the IFA runs did not use.** `max_size 5`, `max_dist_km 900` with per-state
  overrides, `contact_caps CA = 4`, `eta 0.05` and the `fallback` table for states where national
  is absent. Regional specs must carry them unchanged.
- **The main map's total K is 48–54.** National 15 / WH 11 / FI 20 / WIFI 3 = 49 today. K 14
  keeps the total at 48.

## 3. Arithmetic (full precision, E1 rates, `instance_descaled.json.gz`)

Window [L, U] = [$1,062.5M, $1,437.5M], target $1,250M. Pure-state total $16,980.6M, of which $16,895.7M
sits on ledger vertices, so K is 12–15 (16,895.7/1,437.5 = 11.8; /1,062.5 = 15.9). Means: K 15 $1,132M (slack above L $70M per
district on average), K 14 $1,213M, K 13 $1,306M.

| state | $M | | state | $M | | state | $M |
|---|---:|---|---|---:|---|---|---:|
| CA | 4,025.8 over U, ≥3 districts | | PA | 534.8 | | MN | 198.8 |
| TX | 1,970.7 over U, 2 | | MI | 458.1 | | LA | 191.2 |
| NY | 1,756.0 over U, 2–3 | | VA | 409.6 | | NV | 164.5 |
| FL | 1,370.4 **in band alone** | | OH | 402.7 | | MO | 162.4 |
| NJ | 1,016.6 | | GA | 374.6 | | SC | 161.9 |
| IL | 664.1 | | CO | 333.4 | | KY | 130.7 |
| NC | 545.2 | | MD | 248.4 | | WI | 116.1 |
| AZ | 535.3 | | WA | 245.1 | | AL | 111.2 |
| | | | UT | 216.1 | | TN 76.5, OR 57.6, IA 51.1, AR 42.5, DC 39.6, WV 30.6, DE 28.1, MS 18.8 | |

35 extract ZIPs ($84.9M) are not ledger vertices and are not credited (E1 as coded).

The lead map (`fi20_fi_nonc_wh_nonj-r1`, national K 15) in dollars:

| district | states | $M | window |
|---|---|---:|---|
| 01 | AL+FL+GA+MS+SC | 1,014.1 | **under** by 48.4 |
| 02 | AR+LA+TX | 1,088.1 | in |
| 03 | AZ+CO+UT | 1,084.8 | in |
| 04, 05, 06 | CA ×3 | 1,098 / 1,100 / 1,109 | in |
| 07 | CA+NV+OR+WA | 1,185.7 | in |
| 08 | DC+DE+MD+NY+PA | 1,178.0 | in |
| 09 | FL | 1,022.8 | **under** by 39.7 |
| 10 | IA+IL+MN+MO+WI | 1,192.5 | in |
| 11 | IN+MI+OH | 1,067.8 | in, $5.3M slack |
| 12 | KY+NC+TN+VA+WV | 1,192.7 | in |
| 13 | NJ+NY | 1,216.3 | in |
| 14 | NY | 1,229.1 | in |
| 15 | TX | 1,116.3 | in |

Reading: the west (03–07), the south centre (02, 15) and the Midwest (10, 11) pass and are
whole-state layouts the owner has seen; nothing in the recipe improves them. The failure is the
east at K 6 (01, 08, 09, 12, 13, 14: $6,853M, mean $1,142M, total slack above L $478M). Hand
checks show why it is tight: FL whole is in band, but AL+GA+MS+SC ($666M) then needs NC, which
strands KY+TN+VA+WV ($647M); MD+DC+DE cannot fund both the VA group and the NY+PA district.
The east at K 5 (mean $1,371M, slack below U $334M) is the other side of the same squeeze.
Whether K 5, K 6 or a wider east pool (borrowing IN+MI+OH or the TX group's slack, e.g. MS with
AR+LA+TX at $1,107M) closes is exactly what step 1 computes; it is not settled here.

## 4. Owner answers (G5, 2026-10-08)

- **K.** K 14 is allowed if K 15 needs a third split state.
- **Dollars.** Each cell's mass is scaled by its fine channel's E1 rate, so the planner's band is
  a dollar band. The transformed extract is recorded in the manifest.
- **Scope.** Full national re-plan, not an east-only redraw.
- **Borrows.** Not answered as asked; the owner's words: "lets first plan out a fresh run from
  scratch with a whole new grid". Asked what the grid covers, the owner chose the whole main map:
  the WIFI region and every channel's K on the axes. Borrows are moot; nothing is frozen.
- **Regions, not caps** (owner, later the same session: "lets also take the same division level
  approach, so that we can drop the distance caps, support size caps, and the pinning freeing
  like we did for IFA"). Each channel is planned inside sealed regions, as IFA was; `max_dist_km`,
  `max_size`, `contact_caps` and hand-written `free` lists go. A region bounds a district's
  spread, the window bounds its size, and the screen says which states split.

## 5. The new grid: the whole main map in sealed regions

The 2026-10-01 grid (`runs/sweep/grid_2026-10-01`) was comparative statics on τ ± δ with the
planner's caps as axes. Under D3 the band is fixed in dollars and, by the owner's directive, the
caps are gone: a channel is planned inside sealed regions, each region closes on its own under
rule C and the window, and the regions merge without re-routing. A cell is feasible or not; it is
ranked by the settled order: splits, cuts, defects, shape, balance.

**Fixed by decision, not swept.** D3 windows (national [1,062.5, 1,437.5], WH [850, 1,150],
FI [765, 1,035] $M), E3 for WIFI, rule C, E1 rates, the `fallback` table, masses in $M (G5),
main-map total K 48–54, every pure state on every pure channel's list. Routing of national cells
in WIFI states is "stay" (fall back only mattered under the 900 km cap, which no longer exists;
it can return as an owner choice).

**Regions are per channel and come from arithmetic.** A region is a union of Census divisions
(the IFA night's six: New England, Middle Atlantic, South Atlantic, South Central = ESC+WSC,
Midwest = ENC+WNC, West = Mountain+Pacific, or merges of neighbours). For each channel and WIFI
region the screen's first table is each candidate region's total against the window, K and the
slack of the mean from the nearer edge. Computed today at full precision (ledger vertices):

| channel, WIFI today's 15 | Middle Atlantic | South Atlantic | SA + ESC | South Central (ESC+WSC) | WSC alone | Midwest | West |
|---|---|---|---|---|---|---|---|
| national | $3,307M K 3, slack 40 | $3,208M K 3, slack **7** | $3,546M K 3, slack 119 | $2,542M K 2, slack 167 | $2,204M K 2, slack 40 | $2,260M K 2, slack 68 | $5,578M K 4 (43) or K 5 (53) |
| WH | $2,174M K 2, slack 63 | $2,764M K 3, slack 71 | $3,241M K 3, slack 70 | $1,425M **no K** | $948M K 1, slack 98 | $1,995M K 2, slack 147 | $1,782M K 2, slack 41 |
| FI | $4,060M K 4 (20) or K 5 (47) | $4,341M K 5, slack 103 | $6,074M K 6 (23) or K 7 (103) | $3,152M K 4, slack 23 | $1,419M **no K** | $4,087M K 4 (13) or K 5 (52) | $2,864M K 3, slack 80 |

Reading: no single partition serves all three channels. National needs the South as SA+ESC (SA
alone sits $7M above the floor, which is why the lead map's southeast failed); WH needs
ESC with SA and WSC alone; FI needs WSC with ESC. With no WIFI region at all, New England has no
K in any channel, so "none" forces NE into the Middle Atlantic region (NE+MA: national K 3 slack
158, WH K 3 slack 101, FI K 6 slack 123) and the four Census regions become natural. The full
table for the five WIFI regions and three partitions is in the stage-1 output; the point is that
the region partition is a screened choice per channel, not an input.

**Axes.**

| axis | values | why |
|---|---:|---|
| WIFI region | none, 6 low, plains 9, New England 6, today's 15 | the coupling axis |
| region partition per channel | IFA six, South = SA+ESC, four Census, and the one-merge neighbours of each | chosen by the slack table; a region with no K or slack under $25M is dropped |
| K per region | each value the window admits | the table above; total K 48–54 across channels |
| WIFI K | 1–3 | E3 passes by construction when balanced; a looks choice |

No support size, no distance cap, no free list. A region of n states with K districts has few
whole-state partitions under rule C; the screen enumerates them all.

**Stage 1, the screen** (one Sol worker, 2 h to build, minutes to run). A `regionplan.py`:
for a channel, a region, a K and the window, enumerate every partition of the region's states
into K connected groups (state adjacency from `reference/2025`) where each group is whole states,
or whole states plus a piece of one split state (rule C), a split state's pieces summing to its
dollars, each group's dollars in the window. A state splits only when the enumeration finds no
whole-state partition without it, largest-first. Output per (region, K): every feasible layout
with split count, cut count, worst and mean deviation from target, tightest district; and
"infeasible" with the binding states when none exists. This is the IFA night's hand arithmetic
made a tool, and it replaces `wholeplan.py`'s master for stage 1 (the master stays for pieces'
targets in stage 2). Necessary condition only: pieces are masses, not geometry.

**Stage 2, the draw** (3–6 frontier combinations, the IFA recipe per channel and region,
1–3 h wall each under the 12-process cap). For each combination:

1. Whole-state districts need no draw.
2. Each channel's split states draw on their own induced graphs (`run.py --states`), the layout's
   piece sizes as targets: NY by congressional units first (`coarse.py`), the ZIP draw only when
   the coarse grouping leaves a neck; TX, CA, FL, PA, OH by the ZIP draw as in the IFA runs; a
   piece that rides with whole states draws on the multi-state induced graph with the whole
   states declared. Channels and regions draw in parallel; a state split in two channels is two
   independent draws.
3. Repair windows in the channel's dollar window (`repair.py --states --window`), two unknowns
   end an attempt.
4. Merge by (ZCTA, fine channel) across regions and channels (`merge.py` with a per-source
   channel filter), full-graph audit, both M1 gates, D3 in dollars per channel, E3 for WIFI,
   `--window` column, render from the hub with `TD_NECK_GAP_WIDTH` matching the headline gate.
5. Shortlist entry by the lander (T1), then the map to the owner. Shape is their gate; the next
   frontier combination is the fallback.

**Build items before stage 1.**

- Dollar-scaled extract: `Extract` masses multiplied by the fine channel's E1 rate at load
  (`td/data.py`), recorded in the manifest as `mass_unit = "usdM"` with the rates. The ledger's
  `m_rel` column then holds $M, so `export_long.py` divides by the rate per fine channel to
  restore m_rel for the G4 schema; a test asserts the round trip. Masks are untouched.
- `regionplan.py`, the stage-1 enumerator above, with a test on a hand-checkable region
  (Middle Atlantic national K 3: NJ+NY-piece, NY, NY-piece+PA style layouts).
- `merge.py --source-channels`: restrict a source to named model channels so single-channel
  regional runs merge into one multi-channel ledger.
- Regional spec writer: from a layout, the single-channel TOML for a split state's draw (its K,
  the whole-state partners declared, δ sized to the window, no caps).
- `tests/`: the extract round trip, the enumerator, the merge channel filter, the induced-graph
  draw on a two-state fixture (exists for NJ).

**Time.** Build 4 h, stage 1 under 1 h, stage 2 about 3 h wall per combination with three drawn
in parallel under the cap, lander registration after. One orchestrator tab per combination with
a worker per region, deadlines, no review step, as on the IFA night. First map in about 9 h from
go.

## 6. Settled by the owner, 2026-10-08

Q1–Q4 in G5; Q5 (grid scope) answered "whole main map"; the division-level directive drops the
caps and free lists. No question is open; the plan waits only for the go and the issue the
lander files for it.

## 7. What this plan does not promise

The screen is arithmetic, not feasibility. NY's necks are real geometry and the IFA night closed
NY only at the cost of one reported neck. No cached evidence from the lead map is carried; every
district is re-gated in stage 2 step 4. No scenario id exists until the merged ledger is
committed (G4). Sealing is a constraint stronger than any mandate, adopted by the owner for the
main map with this directive; a region that cannot close is reported, and its borrow is an owner
decision as on the IFA night.
