# National under the regional recipe: plan (2026-10-08)

Drafted in the td-research tab after the IFA CONUS map (`ifa_conus_v2`, 38bcd2d) shipped.
Status: draft for the owner. Nothing here is a run, a registration or a decision; the open
questions in §5 go to the owner before step 1 starts.

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

Window [L, U] = [$1,062.5M, $1,437.5M], target $1,250M. Pure-state total $16,980.6M, so K is
12–15 (16,980.6/1,437.5 = 11.8; /1,062.5 = 16.0). Means: K 15 $1,132M (slack above L $70M per
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

## 4. Steps

Hub `main` lacks `run.py --states`, `repair.py --window`, `merge.py` and `coarse.py`; they live
on `m5-studio/explore-neck` (d312834) and `m5-studio/ifa-conus`. Step 0 brings them onto one
branch; td/audit.py's G1 prototype stays as the env-flag prototype until #131 lands.

0. **Branch and freeze** (30 min). Cut `m5-studio/national` from `m5-studio/ifa-conus` (which has
   the reconciled merge.py and export tools); carry nothing onto main. Freeze the lead ledger
   `runs/exp/contig/set125/fi20_fi_nonc_wh_nonj-r1` as the base: every WH, FI, WIFI cell and the
   national cells of the kept regions are copied, never re-solved.
1. **Arithmetic screen** (1 h, one Sol worker). Enumerate whole-state groupings for the east pool
   under rule C, `max_size 5`, polygon adjacency and the window, at K 5 and K 6, with and without
   the two borrows (IN+MI+OH; MS to the TX group), at full precision. Output: every feasible
   layout with its split states and cut count, ranked by the settled order (splits, cuts). If no
   layout closes at K 15 without a third split, the K 14 question goes to the owner with the
   layouts attached (Q1).
2. **Regional spec and plan** (30 min). One TOML per east variant: `channels.national` only, the
   east units, the chosen K, `free` = the split states the screen needs (NY always; FL only if a
   layout needs it), the lead spec's `max_size`, `max_dist_km`, `contact_caps`, `fallback`, and δ
   sized to the window. Plan with the master on the induced graph; a plan that needs more splits
   than the screen said is a bug, stop and look.
3. **Draw** (1–2 h wall, up to 6 solver processes). Split states on their own induced graph
   (`run.py --states NY`, NY K 2–3 with the whole-state partners declared), whole-state districts
   need no draw. NY first by congressional units (`coarse.py`, seconds), the ZIP draw only if the
   coarse grouping leaves a neck the repair cannot close. The known NY trap stands: Manhattan
   cannot be an in-band district's neck-free member below 1,148 km² of land; a national NY
   district that holds Manhattan needs the Bronx and Westchester with it (G2 logic, not G2
   itself, which was decided for IFA).
4. **Repair** (30 min). `repair.py --states --window 1062.5,1437.5` in dollars (see Q2) on every
   neck and piece; two "unknown" windows on one neck end the attempt and the district is reported
   failing M1 with cause and mass.
5. **Merge and gate** (30 min). `merge.py` with a channel filter: sources are the east national
   run(s) plus the lead ledger restricted to everything else. Full-graph audit, both M1 gates,
   D3 in dollars for all 15 (or 14) national districts, E3 unchanged for WIFI by construction,
   `--window` column, render from the hub with `TD_NECK_GAP_WIDTH` matching the headline gate.
6. **Register and show** (lander). Shortlist entry first (T1), then the map to the owner. Shape is
   their call; a second east variant from step 1 is the fallback if the first looks wrong.
7. **WH_09 afterwards** by the same recipe on the WH channel: a whole-state regroup screen for
   IN+KY+MI+WI ($9.2M short) before any draw.

Time, serial: about 5 h with one orchestrator and three workers; the screen and the spec are the
only parts that cannot overlap.

## 5. Open questions for the owner

- **Q1, K.** If the east does not close at K 15 without a third split, is national K 14 (main map
  total 48, still in 48–54) acceptable? Changes a reported number.
- **Q2, dollars in the solver.** National's three rates spread 5%. Options: (a) scale each cell's
  mass by its fine channel's rate so the planner's band is a dollar band (the extract is
  transformed and the manifest records it; every mass in the run folder is then $M); (b) keep
  m_rel and shrink the band 2.5% each side so dollars cannot leave the window; (c) keep m_rel and
  check dollars only after the draw, redrawing on a miss. (a) is cleanest and (b) is cheapest;
  both change numbers that get reported, so it is the owner's pick.
- **Q3, scope.** Redraw the east only and keep the lead map's west, south centre and Midwest
  national districts exactly as drawn (they pass dollars and cached M1)? The alternative is a full
  national re-plan, which risks districts the owner has already accepted.
- **Q4, borrows.** May the east pool take IN+MI+OH or send MS to AR+LA+TX if the screen needs it?
  Both are inside national and inside rule C; they only widen the east's search.

## 6. What this plan does not promise

The screen is arithmetic, not feasibility. NY's necks are real geometry and the IFA night closed
NY only at the cost of one reported neck. Cached M1 evidence for the kept regions is from the
2026-10-07 gate and is re-gated in step 5, not trusted. No scenario id exists until the merged
ledger is committed (G4).
