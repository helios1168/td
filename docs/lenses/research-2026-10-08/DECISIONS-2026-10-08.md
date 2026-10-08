# Owner decisions, 2026-10-08 (research tab, ~01:30 owner's clock)

Structured answers in the research tab; the lander files them into PROBLEM.md and the issues.

- **F1, MD under rule C** (pick: "MD stays whole: one-state band waiver"). Maryland alone is one
  IFA district at about $1,507M, 4.8% over IFA's upper edge $1,437.5M. Rule C and the band for
  every other IFA district are unchanged. This is an OD1 waiver for MD only; it stays recorded as a
  band exception on every map that uses it. Rejected: a joint MD+PA district under rule C (MD in
  up to 4 districts, 3 cuts); raising IFA's upper edge for all districts.
- **F2, D1 revoked** (pick: "Revoke: K from the grid within 46-55"). "IFA at K >= 50 under rule C"
  (2026-10-07) no longer stands; the band is K-independent since E2, so IFA's K is chosen from
  the grid within 46-55.

Context the decision rested on: `CONTEXT-IFA.md` (scout, GPT-6 Luna) and the arithmetic in the
research tab: two MD pieces need 393.84 m_rel of whole attach mass against at most 374.34
available (DC+DE+WV plus VA's room), at every K; county grain does not change it; the
Washington-Baltimore CSA as a unit moves the obstruction to VA (DC + VA + DC-side MD counties =
1,430.6 m_rel, over U).

Tracked illustration: `runs/exp/contig/r2illustration/ifa46-md4/` (hand edit of ifa46-whole, MD in
4 county groups, M1 pass; not a candidate) awaits its shortlist entry from the lander before it is
shown again (T1).

## Later the same session (~02:20 owner's clock)

- **F1 and F2 confirmed** (owner: "for 1 yes confirm f1 and f2"). The lander files them.
- **F3, the #128 re-render is declined for good** (owner's words: "no we do not want to run
  the 58 map re-render. don't ask again, store my explicit consent to avoid that"). The 58
  shortlist entries whose renders predate the 2026-10-07 renderer change stay as they are, their
  T1 "render not current" failures are accepted, and no session asks about the re-render again.

## G1, G2: neck rule findings from the single-state draws (owner, 2026-10-08, structured answers)

**G1 (their pick "Measure width across coverage gaps").** M1's neck width counts unassigned land
between ZCTA polygons, so ZCTA coverage gaps do not read as necks. Cause: IFA TX K 3
(`runs/exp/contig/nj/ifa_tx_k3`, branch `m5-studio/explore-neck`) has one neck, El Paso + the
Trans-Pecos (44 ZIPs, $81M, 6.9% of IFA_02's land) joined to the rest of Texas by the single polygon
edge 79718-79734 at 6.14 km, because the desert ZCTA polygons do not touch (79830 Alpine has no
polygon edge to 79735 Fort Stockton) while the land passage is over 100 km wide; every neighbour is
already in the district, and repair windows up to 1,443 ZIPs proved nothing local helps. This is a
gate change (td/audit.py NeckGraph width); prototyped behind a flag, default off, until the
lander's owner-decision issue lands. Alternatives recorded and not chosen: keep the rule and give El
Paso New Mexico on the CONUS map; a one-off connector across the gap; defer.

**G2 (their pick "Dilute: Manhattan + Bronx + Westchester").** Under the 10 km / 5% land rule any
district whose land is more than 5% Manhattan fails M1: the island is under 4 km wide, so every cut
across it is a neck once the cut-off side holds 5% of the district's land (the congressional-district
NY K 5, `runs/exp/contig/nj/ifa_ny_k5_cd`, fails on a 5.5 km cut at 10024-10029 with 5.2% of the land
south of it, and adding 48 km² of Westchester only moved the cut north). Manhattan is 57 km² and
$546M, so a district holding it needs over 1,148 km² of land; Manhattan + Bronx + all of Westchester is
$1,300M on 1,277 km² (Manhattan 4.5%), inside the window. NY K 5 is re-solved with a generic land
floor: for every district, the land of units that have a neck on their own is at most NECK_SHARE of
the district's land. Alternatives recorded and not chosen: a rule exemption for water-bounded cut-off
parts; defer.

**Solver process cap 4 → 12 (owner, 2026-10-08 ~04:10, structured answer "Raise to 12").** Asked
in the td-research session (01a119b6, around entries #4494-#4496) after the machine check (18 cores,
64 GB, about 500 MB per solver process); the launch that followed ran 11 solver processes at 4.3 GB.
Tonight's IFA tabs hold 11 of the 12 with one spare for the assembly; main-map slots are the owner's
allocation.

**IFA band verdict is the E2 window (owner, 2026-10-08 ~05:15, southatl tab, their pick "E2 window
$1,000M-$1,437.5M").** Every IFA region merge and the CONUS gate report band pass/fail per district
against [798.74, 1148.19] m_rel; the audit's τ ±15% final-band line is information only and
final_delta is never changed to make it agree (the mandate advisor blocked southatl's 0.1733; it was
reverted to the default 0.15). MD+DE+WV ($1,924M) passes only under the widened F1 waiver (owner,
same tab: "Both join MD's waiver district"). Filing with the lander is southatl's relay.

**G3: El Paso coverage-gap neck passes (owner, 2026-10-08 ~05:35, td-research tab, after seeing
docs/lenses/research-2026-10-08/elpaso_neck.png and texas_ifa_k3.png).** Owner's words: "looks
great! lets pass it or make an exception. necks caused by empty zips should trigger a fail, that is a
GREAT looking map". Reading applied (the sentence contradicts itself; "pass it", "make an exception"
and "GREAT looking map" carry the intent): a neck that exists only because ZCTA polygons do not
touch across land in no ZCTA (a coverage gap) does NOT fail M1. Applied tonight as: the South Central
merge and the CONUS IFA merge are gated with the G1 prototype on (TD_NECK_GAP_WIDTH=1, measuring
width across coverage gaps, #131) and both verdicts are reported; any verdict other than El Paso
that the flag flips is reported to the owner, not decided. ifa_sc_merge_b moves to tier E with the
note. Filing in PROBLEM.md / MANDATES.md is the lander's.

**Open (06:40): Queens/Nassau under the gap-width gate.** In ifa_conus_v1 (4572e81) the NY
Queens/Nassau neck (7.48 km, 41 ZIPs, 46% land, 69% mass) passes only under the G1 prototype, and the
gap edges the prototype adds inside that district are water crossings (11024-11050 Manhasset Bay
4.80 km, 11024-11359 Little Neck Bay 3.04 km, 10306-11224 and 10301-11209 across the Narrows,
11356-11371 Flushing Bay), the prototype's documented no-land-test caveat (td/audit.py:487-488).
G3 covers necks caused by empty ZIPs (land in no ZCTA), not water, so the flip is reported to the
owner, not adopted: ifa_conus_v1 fails M1 on Manhattan and Queens/Nassau, El Paso excepted.

**G4: export schema and scenario id (owner, 2026-10-08, 14:20).** Every data export for the owner's
work machine is the database's nationwide long schema, column for column, no additions:
`scenario, zip_code, current_channel, canonical_channel, state, model_channel, bundle, district,
district_channels, rep, m_rel, has_commercial_opportunity` (archive
`tools/export_all_scenarios_nationwide_long.py`, 2026-09-14; owner: "match the same exact schema we
uploaded previously"). No dollars (usd is derived downstream from m_rel and the rate), `rep` blank,
`has_commercial_opportunity` = m_rel > 0, one row per (scenario, ZCTA, source channel) over every
CONUS ZCTA. The scenario id is `<K>_<channels>_<commit>`: K the district count, the channels in
lower case sorted alphabetically and joined by `_`, and the short hash of the commit that first
committed the run folder's ledger.csv on its branch (owner: "just use 52_ifa_ and the relevant
commit hash at the end"); e.g. `52_ifa_38bcd2d` for ifa_conus_v2, and a main map would read
`51_fi_n_wh_wifi_<hash>`. The file is `<scenario>_nationwide_zcta_long.csv` (+ `.gz`) under the run
folder's `export/`, with `scenarios.csv` beside it mapping the id to run_id, branch, commit,
ledger_commit, code_commit, spec and instance sha256, source runs, m1 and shortlist rank.
Writer: `tools/exp/contig/export_long.py` (m5-studio/ifa-conus ef5d761), which refuses an
uncommitted run folder. Tonight's earlier two-file export (ifa_zip_districts.csv, ifa_districts.csv)
is withdrawn. Files to: docs/memory (decision + fact), CODE_MAP row for export_long.py, and a line
in td's AGENTS.md if the owner wants it as an invariant (lander).

**G5: national under the regional recipe (owner, 2026-10-08, td-research tab).** Four answers to
`docs/lenses/NATIONAL_PLAN_2026-10-08.md` §5: (1) national may drop to K 14 (main-map total 48)
if K 15 cannot close without a third split state; (2) the solver sees dollars: each cell's mass is
scaled by its fine channel's E1 rate so the planner's band is a dollar band, the transformed
extract recorded in the manifest (alternatives rejected: shrinking the m_rel band 2.5% a side;
checking dollars only after the draw); (3) scope is a full national re-plan, not an east-only
redraw keeping the lead map's west, south centre and Midwest; (4) to the borrow question the owner
answered "lets first plan out a fresh run from scratch with a whole new grid", so borrows are moot
and the plan is a new grid (axes in the plan's §5). Q5 answered in the same tab: the grid is the whole main map, "WIFI region and every K on the
axes" (over national only with WH, FI and WIFI held, and over national first then the whole
map). Files to: PROBLEM.md settled table (lander).

**G5 addendum: regions, not caps (owner, 2026-10-08, td-research tab).** Owner's words: "lets also
take the same division level approach, so that we can drop the distance caps, support size caps,
and the pinning freeing like we did for IFA." The main-map grid plans every channel inside sealed
regions (unions of Census divisions, chosen per channel by the window-slack table), with no
`max_dist_km`, `max_size`, `contact_caps` or hand `free` lists; the screen decides which states
split. Sealing is a constraint stronger than any mandate and is adopted for the main map by this
directive. Routing of national cells in WIFI states stays "stay" (DECIDED by td-research: fall
back only mattered under the 900 km cap). Plan: `docs/lenses/NATIONAL_PLAN_2026-10-08.md` §5.
