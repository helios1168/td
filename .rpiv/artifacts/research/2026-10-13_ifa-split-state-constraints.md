---
date: 2026-10-13
author: research sub-agent (read-only)
branch read: m5-studio/national-overnight @ 18176d5, plus origin/m5-studio/ifa-* and regional-seal
topic: How the IFA work handled split-state connection; what "constraint C" was; what to port to the main map
status: complete (no code changed, nothing committed)
---

# IFA split-state connection constraints: what "C" was, what IFA used, what to reuse

## 0. Short answer

"Constraint C" is **part C of issue #124**, "Close the loop after drawing", spec key
`replan_rounds = R` with `ban_supports`. It is not a rule about *how* a split state's share may
connect to other districts. It is a feedback loop: after draw + repair, a district left in pieces or
with a neck whose last repair window was **proved infeasible** gets its exact support banned
(`n_S = 0`), the master re-plans, and the map is redrawn, up to R rounds. A, B and C were the
owner's three-part plan on 2026-10-06/07 (#124 body, "Plan"): A = width-aware contact
(`contact_min_km`), B = drawable alone (`drawable_alone`), C = the ban loop. All three are off by
default and were a **negative result**: on the four maps measured they changed no plan (#124
closing comment: "A, B and C change no plan ... all four still fail M1").

There is a second, unrelated "rule C" in #103 (`one_split_per_district`: a support holds at most
one splittable state). It was a fewest-splits lane rule, never a drawn-map constraint; the only
IFA trace is an arithmetic enumeration script on `ifa-midwest`. Noted in §1.7 so the two are not
confused.

The IFA map that actually went to the owner (`ifa_conus_v2`, 52 districts, then the K 48–54 grid)
was **not** produced with A, B, C or pair bans. It was produced by **regional sealing**: each
state or small state group planned and drawn alone on the state-induced polygon graph
(`run.py --states`), repaired with the dollar window (`repair.py --states --window`), and the
pieces merged and re-gated on the full graph (`merge.py`). The split-state connection problem
disappears there because a district can only hold states inside its region, and most regions are
one state. What sealing did not fix is Manhattan (kept as a standing M1 exception).

## 1. The constraints and tools IFA used, one by one

Rows: name; where defined; the rule; which rounds used it; what it fixed; what it did not.

### 1.1 `forbid_pairs` (state-pair bans), #122 rounds 1–2

- **Defined:** `td/spec.py:116` (`forbid_pairs: frozenset  # frozensets {u, w}: no support holds both`),
  parsed at `td/spec.py:355-358`; applied in `td/supports.py:238`
  (`found = {s for s in found if not any(p <= s for p in cs.forbid_pairs)}`). Added to a spec copy
  by `tools/exp/contig/replan.py --forbid A-B` (`replan.py:5, 83-125`). Model text: MODEL.md §2
  (family filter) and `td/supports.py:10-13` ("a support holding both units of a pair is removed").
- **Rule:** no support (hence no district) may contain both units of the pair. It is a family filter,
  so closure under connected subsets is kept.
- **Used:** #122 round 1 "ne5" (CT-NJ, MA-NJ, NJ-VT, CT-PA, MA-PA in every channel) and round 2
  "+DE-NJ", on nocomb_13/15, low6_cb1 and ifa_49; low6 FI also AZ-UT. RESULTS.md:781-845.
  Dropped in round 3 by the owner ("Round 2's six state-pair bans dropped", #122 round-3 comment).
- **Fixed:** the Hudson/Westchester/Long Island necks on nocomb_13/15 ("The ne5 bans remove the
  Hudson/Westchester/Long Island necks", #122 round 1 comment); DE-NJ removed the Delaware
  Memorial Bridge neck (08023) (RESULTS.md:822-826).
- **Did not:** on ifa_49, ne5 made things worse (7 pieces → 15, 10 necks → 17, band broken;
  RESULTS.md:815). DE-NJ "pushed DE into long districts that break around Philadelphia and
  Baltimore (necks 0.07-0.38 km)" so nocomb_15 and low6 were "no better than round 1"
  (RESULTS.md:822-826). Worker LEARNED: "Hand bans of state pairs ... chase the neck around the
  map" (#124 body, "Why"). The AZ-UT ban "does not touch IFA's UT neck" because no IFA district
  held AZ and UT together (RESULTS.md:1084-1090).

### 1.2 Opened units (`repair.py --open-units U`), #122 arm 2

- **Defined:** `tools/exp/contig/repair.py:1087-1089` (`--open-units`), own-window logic at
  `repair.py:585, 701`. CODE_MAP.md:66-67.
- **Rule:** inside a repair window, any district may take ZCTAs of unit U even with
  `--keep-support`: an unplanned extra split of U (one more holder allowed per unit); a neck whose
  side lies in U is repaired first, starting with the district's own ZCTAs in U.
- **Used:** #122 rounds 1–2 (`-a1ut`, `-a2ut` on ifa_49 and low6); #126 round 1 reused a2ut.
- **Fixed:** IFA_19's UT 84621 neck in one 1.8 s solve (RESULTS.md:828-830).
- **Did not:** the result fails the audit's **mode compliance** because UT was not on the free list
  (RESULTS.md:810, 1076). The main-map overnight tried "repair pass 3 with --open-units (killed:
  every window infeasible)" (handoff 2026-10-13_14-44-04, Task 3).

### 1.3 Free-list changes (`replan.py --free CHANNEL=...`), #122 round 3 and #126 round 2

- **Defined:** `replan.py:5` (`--free FI=CA,FL,NY,TX`); the channel's `free` list in the TOML.
- **Rule:** which states may be split in the channel. A scenario choice, not a constraint on
  connections.
- **Used:** #122 round 3 short lists (no map planned inside ±10%; owner widened the band;
  RESULTS.md:846-903). #126 round 2 added UT to IFA's free list (RESULTS.md:1106-1159).
- **Fixed:** "Opening UT removes the UT neck at every K" (RESULTS.md:1126-1127).
- **Did not:** DE-NJ bridge, west TX and the NYC pieces stayed (RESULTS.md:1128-1146).

### 1.4 A: width-aware contact, `contact_min_km = W` (#124 A)

- **Defined:** `td/spec.py:119`; `td/supports.py:17-24` (docstring), `supports.contact`
  `td/supports.py:104-139`, applied at `td/supports.py:218, 239-240`; MODEL.md §2 lines 100-121.
- **Rule:** two units count as touching in a support only where their shared ZIP-graph border is
  at least W km (summed `border_cm`, floored whole cm, as M1 measures width) or an approved
  connector joins them that M1's land-passage rule leaves at unlimited width; the support must be
  connected in that contact graph. A policy row (owner sets the default).
- **Used:** #124 measurement only, W = 10, on nocomb_13/15, low6_cb1, ifa_49 (RESULTS.md:978-1000).
- **Fixed:** nothing. "A removes no support: every adjacent pair of planning units shares at least
  10 km of land border. The only contacts that rest on a connector (DE-NJ, IL-KY, IN-KY) are
  connected through land anyway" (RESULTS.md:989-992). By design it "does not catch CT+NJ via NY,
  since both of those borders are wide" (#124 body, A). It reads the states of S, not where the
  drawn share lands, so it cannot see that an NYC share never touches Vermont.

### 1.5 B: drawable alone, `drawable_alone = true` (#124 B)

- **Defined:** `td/spec.py` (`drawable_alone` in the known keys, line 297);
  `tools/exp/contig/plancheck.py:118-323` (`drawable`), `plan_checked` 442-483, `checked_delta`
  485-524; MODEL.md §4.9 lines 365-449, Proposition B **[proved, Sol verifier 8b0ddc7f]**.
- **Rule:** for each multi-unit support in use, one district's MILP on S's ZIPs: held units owned
  in full, each free unit at least η, mass in the band, connected by a flow, wide-passage rows
  between held bodies, M1 necks cut lazily. Proved infeasible ⇒ `n_S = 0` is a necessary row for
  any neck-free drawing. Timeout/unknown is never a cut.
- **Used:** #124 measurement (600 s per support, 120 s on ifa_49).
- **Fixed:** nothing: "B cuts nothing" (RESULTS.md:993). Unknowns on ifa_49: FL+GA, CT+NJ+NY,
  IA+IL+WI, CT+NY+RI+VT, IL+IN+MI+OH, DC+DE+MD+NJ+PA, ID+MT+UT+WA+WY (RESULTS.md:1017).
- **Why it cannot catch the main-map failures:** B asks whether *some* single district with
  footprint S can be drawn connected. CT+NJ+NY *can* be drawn connected (through Westchester or
  across the Hudson); the failure is that the *other* districts on the map take the land the
  connection needs. MODEL.md §4.9: "B is necessary only for drawings without a neck ... It is not
  sufficient (C10)".

### 1.6 C: support bans after drawing, `replan_rounds = R` + `ban_supports` (#124 C)

- **Defined:** `td/spec.py:121-122` (`replan_rounds`, `ban_supports`), parsed `td/spec.py:376-385`;
  master row `td/master.py:19, 126-128` (`n_S = 0`); the loop `tools/exp/contig/plancheck.py`
  (docstring lines 28-48; `causes` 530-581, `new_bans` 584-600, `close_round` 603-628, the CLI
  loop 777-882); MODEL.md §3 line 141 ("support ban (§4.9, #124): n_S = 0") and §4.9 lines 451-460.
- **Rule (exact):** round 0 plans, draws (arm 1, sequential, border term) and repairs
  (`repair.py --keep-support --flow`). For every detached piece and neck left, `causes` reads the
  repair record: "budget spent" if the log says a window of that district was never tried; else
  the status of the **last** window tried on it. Only the cause `"window infeasible (outside fixed)"`
  (`plancheck.py:89`) creates a ban (`new_bans`, line 592: `if f["cause"] != INFEASIBLE ... continue`).
  The ban is the district's **exact support** (its unit set), added to `ban_supports` of the next
  round's spec copy; the input spec's own `ban_supports` stay banned in every round. Repeat up to
  R rounds, or stop when nothing qualifies. Each ban records window evidence and cost (δ,
  objective, splits, cuts) before and after. MODEL.md §4.9: "A window's infeasibility is conditional
  on everything outside the window being fixed, so it does not prove that S cannot be drawn ...
  the master with C bans bounds nothing." It is a **policy**, never a proof.
- **Used:** #124 measurement (R = 3) on all four maps; #126 round 3 used the `ban_supports` key by
  hand (see 1.6a); the main-map overnight (2026-10-13) ran the CLI loop (`~/overnight/plancheck_c.sh`,
  folders `<point>/pc/`, `<point>/pcb/`, gitignored) per the handoff.
- **Fixed:** nothing in #124: "C bans nothing: no piece or neck the repair leaves has a last window
  proved infeasible. Each is unknown or budget spent" (#124 measurement comment; RESULTS.md:994-997).
  Also "C's gate was off in these A+B+C runs" because the reused round 0 read A's `replan_rounds`
  of 0 (fixed afterwards, RESULTS.md:998-1001); the fix could not change the outcome.
- **Did not (main map, last night):** handoff Task 3: "the #124 C support-ban loop (`plancheck.py`,
  IFA round-3 DE+NJ-without-PA bans + proved-infeasible supports): completed, failed: bans moved
  pieces, never cleared them (w1-50-wide got worse: 4 pieces/8 necks). Abandoned." The run folders
  are gitignored, so I could not verify the numbers; this is the handoff's record.
- **Why bans move pieces instead of clearing them (from the code and the IFA record):**
  1. A C ban removes one exact unit set. The master picks the nearest alternative that still pairs
     the split state's share with a far-away whole state (e.g. ban CT+NJ+NY and it plans
     CT+NY+RI or MA+NJ+NY+RI). #126 round 3 saw exactly this when banning only AZ+CO+NM: "the
     master moves NM to AZ+CO+NM+UT, still without TX", so the worker had to ban all 16
     NM-without-TX supports by hand (RESULTS.md:1176-1178). The loop bans one support per round.
  2. The underlying cause is not in the support. Handoff "Learnings": "the unsealed support master
     pairs states whose drawn shares never touch (it doesn't know where in a split state the share
     lands; the draw puts it at the metro)". The master has no row that ties a share's location to
     the support's other units, so any re-plan reproduces the pattern somewhere else.
  3. C fires only on proved-infeasible windows, which were a minority everywhere (#124 cause
     tables: 0 infeasible on every map; #126: "infeasible windows are the minority",
     RESULTS.md:1094). Unknown and budget-spent pieces are listed, never banned.

### 1.6a Hand-enumerated `ban_supports` ("exact support bans"), #126 round 3

- **Defined:** same key as 1.6; enumerated by `runs/exp/contig/ifa126/mkspec3.py` and
  `nm_without_tx.py` (gitignored, named in RESULTS.md:1213-1221).
- **Rule:** ban every family support matching a predicate: "DE and NJ without PA" (65 supports) and
  "NM without TX" (16 supports). This is the predicate form the C loop lacks.
- **Used:** #126 round 3, K 46, UT free (RESULTS.md:1160-1221).
- **Fixed:** "The Delaware Memorial Bridge neck is gone in both" and "Giving the NM district TX
  removes the west TX neck" (RESULTS.md:1189-1194). #126 closing comment lists the three things
  that worked: UT free, DE+NJ-without-PA bans, NM-without-TX bans.
- **Did not:** the NY metro: IFA_10 (CT+MA+NJ+NY+RI#1) left a north-NJ piece (0.29 τ) and a
  Manhattan piece (0.242 τ); IFA_11 (CT+NY#1) a 0.90 km Queens neck (RESULTS.md:1195-1211).
  "Supports that join NJ, NYC and New England ... leave Manhattan and north-NJ pieces cut off."

### 1.7 "Rule C" of #103 (`one_split_per_district`) — not a drawn-map constraint

- **Defined:** only as an issue amendment (#103, "Rule C as a switch, `one_split_per_district`")
  and the review lenses (`docs/lenses/review-2026-10-07/report3-fable.md:12-21, 102-110`). Not in
  `td/spec.py` (known keys at line 294-297 do not include it). Not in any IFA spec.
- **Rule:** a support holds at most one splittable state; the rest are whole. The reviewers showed
  IFA has **no** rule-C plan at the E2 band because of MD (report3-fable.md:102-110).
- **IFA trace:** `tools/exp/contig/rulec_enum.py` on `origin/m5-studio/ifa-midwest` (a state-grain
  arithmetic enumerator for the Midwest region, lines 1-5), used to pick region groupings. Nothing
  else. **Not found** as code in `td/` or in any spec on any branch.

### 1.8 Whole-unit plan check at plan time (#127 `wholeplan.py`)

- **Defined:** `tools/exp/contig/wholeplan.py`, `pieces.py` (CODE_MAP.md:76); RESULTS.md:1222-1300.
- **Rule:** every unit whole (optionally pre-cut county pieces), M1 checked exactly on each
  district's ZIP union at plan time, failing districts banned as exact unit sets, loop to
  convergence. No draw, no repair.
- **Fixed:** six maps pass M1 by the gate; found 84621 and 08023 by itself.
- **Did not:** bands of ±43% to ±310%; none eligible. Dead end for balance.

### 1.9 Regional sealing (`run.py --states`, `repair.py --states --window`, `merge.py`) — what made the IFA map

- **Defined (ifa-conus branch):** `tools/exp/contig/run.py:149-152, 569-582` (`--states`: plan and
  draw on the polygon graph induced on the listed states; M1 on the full graph);
  `repair.py:1095-1100` (`--window LO,HI` clips the band to the dollar window; `--states`);
  `merge.py:1-33` (docstring: merges `STATES=<folder>` sources into one folder, every state split
  between merged districts becomes `free`, `--window`, `--gap-width`, merge invariant). Ported to
  `origin/m5-studio/regional-seal` at `cd180a5`. Specs: `runs/exp/contig/_specs/ifa_*.toml` on
  `ifa-kgrid` (37 files). **None of those specs uses `forbid_pairs`, `ban_supports`,
  `contact_min_km` or `confine`** (grep over all of them: empty). The only sealing-era pair ban is
  the main-map test `reg_w1_mdva2.toml` on `regional-seal` (`forbid_pairs = [["DE","VA"]]`,
  "DE and Tidewater VA never share a district").
- **Rule:** the planning channel is restricted to a region (one state, or a few whole states plus
  the split one), with `max_size` 1–6 and `margin = false`; K per region is chosen so τ lies in the
  dollar window; each region is drawn and repaired alone; the merge re-gates the whole map. A
  district can only hold units of its region, so the master can no longer pair an NYC share with
  Vermont.
- **Regions (ifa_conus_v2 README, "Sources"):** New England CT+RI K2 and MA+VT+NH+ME K2; Middle
  Atlantic NJ 3 + PA 4 + NY 5 (each state alone); South Atlantic (MD+DE+WV K1 under the F1 waiver,
  VA+DC, NC, NC-piece+SC, GA, FL 4); South Central (TX 3, AR+LA+OK, KY/TN-north, MS/AL/TN-south);
  Midwest 14; West (Mountain K2 + Pacific K5). The K 48–54 grid regroups a few
  (`results/ifa_kgrid_2026-10-13/REVIEW.md` on `ifa-kgrid`).
- **Fixed:** 0 pieces at CONUS; DE bridge, DC, New England, UT, west TX (El Paso via gap width G3)
  all gone (`ifa_conus_v2/run.json`: "0 detached pieces ... 1 necks" with gap width; 2 strict).
- **Did not:** Manhattan. NY K5 was drawn by coarsening to congressional districts
  (`coarse.py`, `explore-nycd` a61ad59: "0 pieces, 2 necks (Manhattan, Queens/Nassau)"), a no-good
  pass forbidding the necked groups (`coarse.py --nogood`, line 190: `sum_{u in S} x[u,h] -
  sum_{u not in S} x[u,h] <= |S| - 1`) changed nothing (6a6867e "same two necks"), the
  Queens/Nassau neck was closed by a 109-ZIP window repair (`ifa_ny_k5_cd-qn/repair_report.md`:
  "ball h=3, 109 ZIPs, optimal, 2.6 s"), and Manhattan stayed: "Manhattan only remaining M1 neck
  under both gates" (5.50 km, 5.2% of land). Owner G2 (#132, "Dilute: Manhattan + Bronx +
  Westchester") was tried (`ifa_ny_k5_cd_dilute*` folders) and aborted (commit 1ff8b90 "record
  aborted dilution repair"). The K grid labels every K "eligible (Manhattan neck and MD F1 excepted)".

### 1.10 Gap-width M1 (G1/G3, `TD_NECK_GAP_WIDTH=1`), #131

- **Defined:** `td/audit.py` `NeckGraph(gap_width)` (ported in phase 3 `4afed4d` on this branch);
  MANDATES.md:84-87.
- **Rule:** a neck that exists only because ZCTA polygons do not touch across land in no ZCTA is
  not a neck. Owner G3 2026-10-08.
- **Fixed:** El Paso 79718-79734 (the only flip on ifa_conus_v2). Not a split-state device.

## 2. Which of these the main-map grid already uses

Checked on `m5-studio/national-overnight` @ 18176d5 (`scenarios/main_*.toml`, `overnight.py`).

| device | in code on this branch | used by main_*.toml / overnight.py |
|---|---|---|
| `forbid_pairs` | yes (`td/spec.py:116`, `supports.py:238`) | only `main_west8.toml` legacy MS pairs (MS-AL, MS-FL, MS-GA, MS-SC) and `confine`/`extra_supports` for New England; **not** for NYC, DC, DE-NJ |
| `contact_caps` | yes (`td/master.py:170, 473-474`) | `CA = 4` in ne_plains, nw34, west8 (national/WH/FI). Caps holders per unit; unrelated to where shares land |
| `contact_min_km` (A) | yes (`supports.py:104-139`) | no (0 everywhere) |
| `drawable_alone` (B) | yes (`plancheck.py`) | no |
| `replan_rounds` / `ban_supports` (C) | yes (`plancheck.py`, `master.py:126`) | not in specs; run by hand last night via `plancheck_c.sh`, failed (handoff) |
| predicate-enumerated `ban_supports` (#126 3a/3b) | key yes; enumerator scripts gitignored on m5 (`ifa126/mkspec3.py`) | last night's `mk_ban_spec.py` (m5 `~/overnight/`, not in repo) applied "DE+NJ without PA"; result failed per handoff |
| `--open-units` | yes (`repair.py:1087`) | tried as repair pass 3, killed (handoff) |
| `--land-ratio` (#133 land term) | yes (`run.py:36-39`, `overnight.py:167`) | yes, R = 10 on every draw |
| `run.py --states`, `repair.py --states --window`, `merge.py` | **no** on this branch; on `regional-seal` @ `cd180a5` | regional test on w1-50-wide only (`reg_w1_*.toml`): 2 pieces/2 necks → 1/1 (NYC), sealed districts all in window |
| gap-width gate | yes (phase 3) | yes, headline M1 across gaps |
| `one_split_per_district` (rule C, #103) | **not found** anywhere | no |

## 3. Assessment: what to port, and the gaps left

### 3.1 Port (in this order)

1. **Regional sealing** (`run.py --states`, `repair.py --states --window`, `merge.py` from
   `regional-seal`/`ifa-conus`). It is the only device that cleared the detached pieces the owner
   listed (DC inside MD, NYC share in New England, DE+NJ over the bridge) on both IFA and the
   w1-50-wide test. The owner already chose it (handoff, 2026-10-13 ~14:40). Conventions that IFA
   found necessary: `margin = false` in region specs (else NY's master is infeasible), per-region K
   so τ sits in the channel's dollar window, a hard wall-clock kill per draw (NY+NJ K7 hung HiGHS
   ~2 h), judge only on the merged full-graph gate (region scorecards show τ ~10× too small).
2. **Predicate-enumerated `ban_supports`** as the regional sealer's complement, for regions that
   must hold several states: "DE and NJ only together with PA" (#126 3a, proved useful) and
   "no district holds NM without TX" (3b). Write a small enumerator in the repo (the #126 scripts
   are gitignored); the key and the master row already exist. Use them as **scenario choices**
   recorded in the spec copy, as #126 did, not as the C loop.
3. **`forbid_pairs` for a few bridge-only contacts inside a region**: DE-VA (regional-seal
   `reg_w1_mdva2.toml`, needed for DC+DE+MD+VA K3). Keep the list short; #122 showed long pair
   lists "chase the neck around the map".

### 3.2 Do not port as the fix

- **A** (`contact_min_km`): proved inert at W = 10 on every map; by construction blind to the
  "share lands at the metro" failure.
- **B** (`drawable_alone`): necessary-only; every failing NYC support is drawable alone.
- **C loop** (`replan_rounds`): fires only on proved-infeasible windows (rare), bans one exact
  support per round, and the master re-pairs the share with the next far-away whole state. Both
  #124 and last night's run confirm "bans moved pieces". If kept at all, keep it as the recorder
  of causes (`plancheck.causes`), which is useful diagnostics.
- **`--open-units`**: breaks mode compliance unless the unit is also made free; every window
  infeasible on the main map last night.
- **#127 whole-unit loop**: passes M1 but with bands no owner would accept.

### 3.3 Gaps that sealing does not close

1. **NYC / Manhattan.** Sealing NY alone still leaves a Manhattan neck (5.5 km, 5.2% land) in IFA
   and 1 piece + 1 neck in the w1-50-wide test. IFA's state of the art is: NY K5 by congressional
   coarsening (`coarse.py`), Queens/Nassau closed by a 109-ZIP window repair
   (`ifa_ny_k5_cd-qn`, port its window: `--states NY --window 798.74,1148.19 --time-limit 240`), and
   Manhattan carried as an **owner-accepted exception** at every K. The owner's G2 dilution
   (Manhattan + Bronx + Westchester, #132) was tried and aborted; `--land-ratio` (#133, on this
   branch) is the generic form of that land floor and is the lever to try first for the main
   map's NY region. The handoff's item 2 (a rule that no upstate NY district takes a Manhattan
   piece) has no implementation anywhere; the nearest existing mechanism is a `--nogood`-style row
   in `coarse.py` (line 190), which on IFA NY "still 0 pieces, 2 necks".
2. **Within-state necks** sealing cannot touch (handoff "Learnings"): Cincinnati/KY 41011-45202,
   Utah 84621 (fixed in IFA by freeing UT or by a UT-with-NV/CO support), El Paso 79718-79734
   (gap width clears it), LA/SF, NJ 08505-08611. These need the window repair
   (`repair.py --flow`), free-list changes, or neck-specific windows, not master rows.
3. **Cost of sealing**: +2 split states (MD, VA), +2 multi-state districts, worse land ratios
   (NY 753, VA 278, MD 64) on the w1 test; IFA paid with MD over the window (F1 waiver). Expect
   an owner decision on the equivalents for the main map.

## 4. Not found / not verifiable here

- No issue, spec key or code named "constraint C" other than #124 C and #103 rule C.
- Last night's C-loop folders (`<point>/pc/`, `<point>/pcb/`) and `~/overnight/mk_ban_spec.py`
  are on m5, gitignored; the "4 pieces/8 necks" figure is quoted from the handoff only.
- #126's `mkspec3.py` / `nm_without_tx.py` enumerators are gitignored on m5; only RESULTS.md
  describes them.
- The IFA regional rounds have no RESULTS.md section on any branch (RESULTS.md ends at #128); the
  record is commit messages, run.json/README in the run folders, and `REVIEW.md` on `ifa-kgrid`.
