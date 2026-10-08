# IFA map tonight: division orchestrators and the final assembly (2026-10-08, ~05:00 owner's clock)

Goal by 08:00: one IFA map of CONUS, every district one connected piece (M1), every district inside
the IFA window [$1,000M, $1,437.5M] (E2), rule C (at most one split state per district), MD whole
(F1), sealed Census divisions where the arithmetic allows and an explicit unsealing where it does
not; plus one dataset (ZIP → district, with dollars) the owner can pull to their work machine.

## 1. What is already done (branch `m5-studio/explore-neck`, `runs/exp/contig/nj/`)

| state | K | status | districts ($M) |
|---|---|---|---|
| NJ | 3 | regional pass | 1,310 / 1,153 / 1,089 |
| PA | 4 (and 3) | regional pass | 1,042 / 1,030 / 1,030 / 1,017 |
| CT+RI | 2 | regional pass | 1,008 / 1,091 |
| IL | 2 | regional pass | 1,109 / 1,024 |
| OH | 2 | regional pass | 1,320 / 1,414 |
| FL | 4 | regional pass | 1,091 / 1,091 / 1,171 / 1,012 |
| CA | 4 (and 5) | regional pass | 4 × 1,270 |
| NY | 5 | 2 necks (Manhattan, Queens); G2 land-floor re-solve running | 1,237 / 1,088 / 1,078 / 1,035 / 1,033 |
| TX | 3 | 1 neck, a coverage-gap artefact; G1 (#131) prototype running | 3 × 1,172 |
| MI | 3 | 3 necks after 1,800 s; needs the window pass or a coarse grouping | 3 × 1,097 |

Tools in place: `run.py --states` (induced-graph draw, full-graph audit), `repair.py --states --window`
(neck and piece windows inside the dollar window), `merge.py` (single-state runs → one regional folder,
re-gated on the full graph), `coarse.py` (congressional-district grouping, `--thin-floor`, on
`m5-studio/explore-nycd`), `tools/maps/render.py`.

## 2. Division arithmetic (IFA, full extract, $M; K range from the window)

| division | states | $M | K | over U (must split) | under L (need company) |
|---|---|---|---|---|---|
| New England | CT RI MA VT NH ME | 4,835 | 4 | MA 1,922, CT 1,670 | NH RI VT ME |
| Middle Atlantic | NJ NY PA | 13,142 | 10-13 | NY, PA, NJ | |
| East North Central | OH IN IL MI WI | 10,932 | 8-10 | MI, OH, IL, WI 1,474 | |
| West North Central | MN IA MO ND SD NE KS | 4,823 | 4 | MN 1,490 | MO IA KS NE ND SD |
| South Atlantic | DE MD DC VA WV NC SC GA FL | 11,027 | 8-11 | FL, MD (F1: whole) | SC DE WV DC |
| East South Central | KY TN MS AL | 2,347 | 2 | | all four |
| West South Central | AR LA OK TX | 4,795 | 4 | TX | LA OK AR |
| Mountain | MT ID WY CO NM AZ UT NV | 3,382 | 3 | | UT NV ID NM MT WY |
| Pacific | WA OR CA | 6,049 | 5-6 | CA | WA OR (971 together: under L) |

Known knots the orchestrators must resolve first, by arithmetic at full precision, before any draw:

- **WI and MN** (each over U and under 2L): neither can split inside its own sealed division under
  rule C (a WI piece may join only a whole state; its whole neighbours are IA and MN's are IA, ND,
  SD, NE). ENC and WNC must be solved together as one Midwest region: WI-west + IA, MN pieces with
  ND/SD/NE, as the rule-C screen of 2026-10-07 found.
- **SC** ($657M): its only neighbours NC and GA are whole in band; SC + either is over U, so NC or
  GA splits, and the remainder must still clear $1,000M. NC: NC-rest ≥ 1,000 leaves ≤ 335 for SC's
  piece, SC + 335 = 992 < 1,000. Knife edge by about $8M at $1M rounding: compute at full precision;
  if it fails both ways, the escape is GA-south + SC with GA-north + a neighbour outside the division
  (AL or TN, East South Central), i.e. an explicit unsealing, which is an owner call.
- **Pacific**: WA + OR = $971M is under L, so one CA piece attaches OR + WA (rule C allows it: CA
  split, OR and WA whole). Draw CA+OR+WA together, K 5, max_size 3.
- **New England**: K 4 = CT-west, CT-east + RI (done), MA-east, MA-west + VT + NH + ME. Draw
  MA+VT+NH+ME together, K 2, max_size 4.
- **West South Central**: TX 3 (G1 pending) + LA + OK + AR = $1,280M as one connected district.
- **East South Central** (K 2) and **Mountain** (K 3): whole-state groupings only; the master
  finds connected in-band groups in seconds.

## 3. Orchestrators

Six orchestrator sessions, each a herdr tab running `pi --fork` of this session (so each carries
tonight's full context), named `td-ifa-<region>`, each owning one worktree branch
`m5-studio/ifa-<region>` cut from `m5-studio/explore-neck` (the tools live there):

| tab | region | solver slots | first action |
|---|---|---|---|
| midatl | Middle Atlantic | 2 | NY: G2 floor result → repair Queens line → merge NJ 3 + PA 4 + NY 5 |
| newengland | New England | 1 | MA+VT+NH+ME K 2 draw, then merge with CT+RI |
| midwest | ENC + WNC | 3 | arithmetic for WI/MN/IA/ND/SD/NE; MI K 3 window pass; whole-state master for MO KS NE IA ND SD IN; draws |
| southatl | South Atlantic | 2 | SC arithmetic at full precision; NC or GA split draw; whole-state groups DE+DC+WV with MD? (MD whole; DE+DC+WV = $? need company) |
| southcentral | ESC + WSC | 1 | whole-state masters; TX waits for G1 |
| west | Mountain + Pacific | 2 | CA+OR+WA K 5 draw; Mountain whole-state master |

Total 11 of the 12 solver slots; one spare for the assembly. Each orchestrator may spawn its own
workers (claude-opus-5-5 medium, deadlines stated in every brief, no review step), must keep the
mandates (T1: register every run with the lander before showing it; M1: never ship a named failure),
and reports to this session with `agent/notify` at each milestone: arithmetic done, draws done,
division merged and gated. Owner questions go through `ask_user_question` in the tab that has them.

Recipe per region: (1) arithmetic at full precision from `$TD_REPO/instance_descaled.json.gz`:
classes over-U / in-band / under-L, the whole-state groups, the attach pairs; (2) one `run.py
--states` draw per split state or attach group, band inside the window via delta, 480 s then 1,800 s
if tangled; (3) `repair.py --states --window` for necks and pieces; (4) `merge.py` into one region
folder, audited on the full graph (only out-of-region cells unowned); (5) push, send the lander the
registration list.

## 4. Assembly and export (this session)

1. `merge.py` over the six region folders → `runs/exp/contig/ifa_conus/<id>/`: every (ZCTA, fine
   channel) cell owned exactly once, `check_m1` on the full graph, the CONUS verdict, render, shortlist
   registration through the lander.
2. Export dataset in the same folder, `export/`: `ifa_zip_districts.csv` (zip, state, county,
   cbsa, district, district_name, m_rel, usd), `ifa_districts.csv` (district, name, states, zips,
   m_rel, usd, pieces, necks, band status), `ifa_map.png`, `README.md` with the rate, band, decisions
   F1/G1/G2 and the verdict. Dollars and m_rel only; no shares, reps or firms (masked-data rule).
   Pushed to GitHub on the branch; the owner pulls it from there.
3. If G1's flag is still off when the Texas district is assembled, the CONUS verdict says so and
   Texas is reported failing M1 with the gap cause (never a silent pass).

## 5. Clock

05:00 launch tabs; 05:30 arithmetic and first draws in every region; 06:30 region merges; 07:15
CONUS merge and gate; 07:45 export pushed. Anything not merged by 07:15 ships as its best regional
map, labelled.
