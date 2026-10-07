# Results

Measured results on `main`. Each section names the command that regenerates it. Per
`docs/memory/workflow/confidential-data.md`, this file carries aggregates only.

## The tagged catalog's scorecard (#70, 2026-09-30)

The pre-support catalog was scored once with the #52 §4 audit (`docs/MODEL.md` §9, S22). Its
exports stay in the tag `archive/pre-support-2026-09`:

- [`scenarios.csv`](https://github.com/helios1168/td/blob/archive/pre-support-2026-09/scenarios.csv): one row per (scenario, ZIP, source channel). This is the input scored here.
- [`exports/database/`](https://github.com/helios1168/td/tree/archive/pre-support-2026-09/exports/database): the ZIP and nationwide ZCTA tables, long and wide.
- [`exports/tableau/`](https://github.com/helios1168/td/tree/archive/pre-support-2026-09/exports/tableau): the Tableau extracts, state structure and district-reach GeoJSON.
- [`MATH_REVIEW.md`](https://github.com/helios1168/td/blob/archive/pre-support-2026-09/MATH_REVIEW.md) §3.6: the earlier read-only audit of the same exports.

**Reading the scorecard.**

- **Bands are unverified.** `scenarios.csv` has no opportunity column, and the catalog declared
  no final tolerance (OD1). The tag also records no plan, modes, solver report, names or
  geography manifest, so those checks are unverified too.
- **Rep labels fail in every scenario.** 235 (scenario, district) pairs carry more than one
  rep label, spread over all 36 scenarios. This matches the count in `MATH_REVIEW.md` §3.6,
  which neither council seat had verified. Staffing is out of scope (OD3, #58), so new runs
  leave the rep column blank.
- **There are unguarded fragments.** 27 (scenario, district) pairs are in pieces, with 29
  pieces between them, in 22 of the 36 scenarios. The catalog's summaries claimed "100%
  Contiguous". MATH_REVIEW §3.5 found that label written even when the separate check failed,
  after fragment healing and national routing that ran with no band or support guard.
- **What holds.** Every cell has exactly one owner, with no `other` or blank owner. The
  district count in every layer matches the K in the scenario's name.

The tag does not ship the graph the catalog was drawn on. Contiguity is therefore measured on
the 2025 Voronoi rook graph over the catalog's own ZIPs (OD2, `geo.zip_graph`). These fragment
counts are not comparable with older ones, such as those in `facts/fi21-cover-grid`. A
district's territory is every ZIP where it owns at least one cell. Pieces are counted as
components beyond the largest, by ZIP count, since the catalog carries no mass.

Regenerate with `"$TD_PY" -m td.audit catalog --public "$TD_REPO/data/public"`, which reads
the tag through git and needs `tl_2025_us_state.zip`.

Scored with `td/audit.py` on the tag's [`scenarios.csv`](https://github.com/helios1168/td/blob/archive/pre-support-2026-09/scenarios.csv): 36 scenarios, 6478 ZIPs, 1166040 cells.

Contiguity is on the 2025 Voronoi rook graph over the catalog's ZIPs (OD2, built by `geo.zip_graph`: 6478 vertices, 19029 edges). 0 catalog ZIPs have no 2025 gazetteer point and are left out; 0 lose their cell. The tag does not ship the graph it was drawn on, so these counts are not comparable with older ones.

| check | pass | fail | listed | unverified |
|---|---|---|---|---|
| one owner per cell | 36 | 0 | 0 | 0 |
| district count per channel | 36 | 0 | 0 | 0 |
| dropped for zero opportunity | 36 | 0 | 0 | 0 |
| final bands on drawn mass | 0 | 0 | 0 | 36 |
| phantom shares | 36 | 0 | 0 | 0 |
| planned against drawn owners | 0 | 0 | 0 | 36 |
| mode compliance | 0 | 0 | 0 | 36 |
| ZIP contiguity | 14 | 0 | 22 | 0 |
| geography manifest is 2025 | 0 | 0 | 0 | 36 |
| solver status, bound and gap | 0 | 0 | 0 | 36 |
| certificate tier | 0 | 0 | 0 | 36 |
| one name per district | 0 | 0 | 0 | 36 |
| rep labels | 0 | 36 | 0 | 0 |

| scenario | verdict | one owner per cell | district count | districts with conflicting rep labels | districts in pieces | pieces |
|---|---|---|---|---|---|---|
| 46_total_14n_11wh_21fi_0wifi | fail | pass | pass | 7 | 1 | 1 |
| 47_total_14n_11wh_21fi_1wifi | fail | pass | pass | 7 | 2 | 2 |
| 48_total_12n_11wh_21fi_4wifi | fail | pass | pass | 7 | 0 | 0 |
| 48_total_12n_11wh_24fi_1wifi | fail | pass | pass | 8 | 1 | 1 |
| 48_total_13n_11wh_21fi_3wifi | fail | pass | pass | 7 | 0 | 0 |
| 48_total_13n_11wh_23fi_1wifi | fail | pass | pass | 6 | 2 | 2 |
| 48_total_14n_11wh_21fi_2wifi | fail | pass | pass | 7 | 1 | 1 |
| 48_total_14n_11wh_22fi_1wifi | fail | pass | pass | 5 | 1 | 1 |
| 49_total_12n_11wh_21fi_5wifi | fail | pass | pass | 7 | 0 | 0 |
| 49_total_12n_11wh_25fi_1wifi | fail | pass | pass | 6 | 0 | 0 |
| 49_total_13n_11wh_21fi_4wifi | fail | pass | pass | 7 | 0 | 0 |
| 49_total_13n_11wh_24fi_1wifi | fail | pass | pass | 8 | 1 | 1 |
| 49_total_14n_11wh_21fi_3wifi | fail | pass | pass | 7 | 1 | 1 |
| 49_total_14n_11wh_23fi_1wifi | fail | pass | pass | 6 | 3 | 3 |
| 50_total_12n_11wh_21fi_6wifi | fail | pass | pass | 7 | 0 | 0 |
| 50_total_12n_11wh_26fi_1wifi | fail | pass | pass | 8 | 1 | 2 |
| 50_total_13n_11wh_21fi_5wifi | fail | pass | pass | 7 | 0 | 0 |
| 50_total_13n_11wh_25fi_1wifi | fail | pass | pass | 6 | 0 | 0 |
| 50_total_14n_11wh_21fi_4wifi | fail | pass | pass | 7 | 1 | 1 |
| 50_total_14n_11wh_24fi_1wifi | fail | pass | pass | 8 | 2 | 2 |
| 51_total_12n_13wh_24fi_2wifi | fail | pass | pass | 6 | 1 | 1 |
| 51_total_12n_13wh_25fi_1wifi | fail | pass | pass | 6 | 0 | 0 |
| 51_total_13n_11wh_23fi_4wifi | fail | pass | pass | 7 | 1 | 2 |
| 51_total_13n_11wh_24fi_3wifi | fail | pass | pass | 6 | 1 | 1 |
| 51_total_13n_13wh_24fi_1wifi | fail | pass | pass | 6 | 1 | 1 |
| 52_total_12n_10wh_25fi_5wifi | fail | pass | pass | 5 | 1 | 1 |
| 52_total_12n_11wh_25fi_4wifi | fail | pass | pass | 7 | 0 | 0 |
| 52_total_12n_13wh_25fi_2wifi | fail | pass | pass | 6 | 0 | 0 |
| 52_total_12n_14wh_25fi_1wifi | fail | pass | pass | 6 | 0 | 0 |
| 52_total_13n_13wh_24fi_2wifi | fail | pass | pass | 6 | 1 | 1 |
| 52_total_13n_14wh_24fi_1wifi | fail | pass | pass | 6 | 1 | 1 |
| 52_total_14n_13wh_24fi_1wifi | fail | pass | pass | 6 | 1 | 1 |
| 53_total_12n_14wh_25fi_2wifi | fail | pass | pass | 6 | 0 | 0 |
| 53_total_13n_14wh_24fi_2wifi | fail | pass | pass | 6 | 1 | 1 |
| 53_total_13n_14wh_25fi_1wifi | fail | pass | pass | 6 | 0 | 0 |
| 53_total_14n_14wh_24fi_1wifi | fail | pass | pass | 6 | 1 | 1 |
| **total** | | | | 235 | 27 | 29 |

## Stakeholder territory options (2026-10-02)

Drawn, audited, margin-off runs from the comparative-statics grid (`runs/sweep/grid_2026-10-01/`,
local), rendered with the archived stakeholder figure (`tools/plan_summary.py` in
`archive/pre-support-2026-09`, unchanged look; only the strip and footer text drop the archived
staffing model). Deck: [`territory_options_2026-10-02.pdf`](https://github.com/helios1168/td/blob/main/docs/figures/stakeholder_2026-10-02/territory_options_2026-10-02.pdf).

| option | districts | within ±10% | worst |
|---|---|---|---|
| [A](https://github.com/helios1168/td/blob/main/docs/figures/stakeholder_2026-10-02/A_48_total_13n_12wh_23fi_0wifi.png): no WIFI region, 1,600 km mountain/plains cap, national 13 / WH 12 / FI 23 | 48 | 48/48 | 4.5% |
| [B](https://github.com/helios1168/td/blob/main/docs/figures/stakeholder_2026-10-02/B_50_total_13n_12wh_24fi_1wifi.png): WIFI = ID MT ND NE SD WY, 1,600 km cap, 13 / 12 / 24 + 1 | 50 | 50/50 | 9.2% |
| [C](https://github.com/helios1168/td/blob/main/docs/figures/stakeholder_2026-10-02/C_51_total_16n_12wh_21fi_2wifi.png): same WIFI, 900 km cap, 16 / 12 / 21 + 2 | 51 | 50/51 | 11.2% |
| [Reference](https://github.com/helios1168/td/blob/main/docs/figures/stakeholder_2026-10-02/REF_51_total_13n_11wh_24fi_3wifi.png): today's 51, 8-state WIFI, 13 / 11 / 24 / 3 | 51 | 41/51 | 88% |
| [IFA](https://github.com/helios1168/td/blob/main/docs/figures/stakeholder_2026-10-02/IFA_49_total.png), separate channel, K = 49 | 49 | 49/49 | 9.6% |

Deviation is drawn mass over the channel's mean (the audit's measure); dollars convert `m_rel` at
each channel's own factor from the owner's channel totals. ZIP 13027's FI cell is unassigned in
every run (triage item I3). The 1,600 km cap is a policy change, not a model fix. Regenerate
(local, gitignored): `runs/sweep/grid_2026-10-01/present/legacy/adapt.py` then `wrap.py` over the
archived `tools/`.

## #81 Hess-style ZIP compactness against support diameter

Measured 2026-10-02 on m5 (#81). Scenario: the 2026-10-01 "18-split" stakeholder candidate
(`A_fi1600_v1_na16_WH12_FI24`, committed as `scenarios/experiments/16n_12wh_24fi_nowifi_mtn1600.toml`:
no WIFI, national 16 / WH 12 / FI 24, all 49 units on the national list, 1,600 km mountain/plains
cap, CA contact cap 4) on `instance_descaled.json.gz`. Both arms replicate the looks driver's
caveats: the rounding margin is off (in memory), ZIP 13027's FI cell (m_rel 1.6e-8) is zeroed at
load (#73's workaround), and deviations are in m_rel, the audit's measure.

**Arms.**
1. *Support diameter*: the support master (`docs/MODEL.md` §3, objective Σ_S w_S n_S, w_S the
   largest unit-centroid distance in S) and the ZIP realizer (§7). Reference run
   `runs/sweep/looks_2026-10-01/stage2/A_fi1600_v1_na16_WH12_FI24/` (m5, local); a re-run on
   2026-10-02 at `9583135` reproduced its ledger, `districts.csv` and scorecard byte for byte.
2. *Hess*: `tools/exp81/hess.py`, a separate planner at ZIP grain, min Σ_z Σ_j M_z ‖p_z − c_j‖² x_zj
   with each district held to the planning band (δ 0.0725 / 0.05 / 0.08). It cannot sit inside the
   support master, which decides (n_S, t_{v,S}) per unit and never sees a ZIP. A whole unit is one
   item and a free unit's positive ZIPs are items. Each district's unit set obeys the support
   family's rules: K, max_size, the dist_km caps, G[S] connected, η, ⌊1/η⌋ and the CA contact cap.
   The corridor floor, border cap, count cap and margin are left out; they exist to make a
   unit-grain plan drawable, and this plan is drawn already. Neither arm enforces ZIP contiguity.
   The centres come from location–allocation (the archived MODEL §8 loop): LP-relaxed rounds from
   the `realize.kmeans` seed, a restricted first assignment, then fixed-centre MILPs
   (`mip_rel_gap` 0, warm-started) alternating with centroid moves until the assignment repeats,
   which it did on all three channels. From the bare k-means seed the MILP found no FI incumbent in
   300 s; the LP-relaxed rounds fixed that. The result is a local optimum with no bound over all
   centres, audit tier "feasible only". Of the realizer, the Hess arm needs zero-mass placement
   (`realize.place_zero`), the one repair pass (S23, final band, mode guard), the piece causes, and
   `td.output`'s ledger, names, audit and maps, all reused unchanged (`tools/exp81/run_hess.py
   assemble`). It does not need the realizer's centres, transport LP or tree rounding: its plan
   is already a ZIP assignment.

**Measures** (`tools/exp81/measure.py`). Every measure is read from the drawn ledger, so both
objectives are scored on each final map. Each score stays in its own unit and is never normalised
against the other. Per channel c, with drawn mass m_j the ledger's m_rel over district j's cells
and τ = (c's ledger total) / K_c:
- *Balance*: deviation m_j / τ − 1; compliance is the audit's final band τ(1 ± final_delta),
  final_delta = 0.10.
- *Support diameter* Σ_j w(S_j), S_j the units where j holds positive m_rel, w the master's
  diameter (km). On arm 1 it equals the master's objective: the drawn supports are the planned ones.
- *Hess* Σ_j Σ_{z∈j} M_z ‖p_z − c_j‖², p_z the ZIP's 2025 gazetteer point in EPSG:5070 (km),
  M_z its m_rel in c, c_j the M-weighted centroid of j's ZIPs; m_rel·km², shown in 10⁶. Per
  district, rms = √(Hess_j / m_j), km. The Hess arm's own objective uses the same points, masses
  and centroids: on its drawn map `run_hess.py` and `measure.py` agree to floating-point rounding.
- *Extent*: the largest distance between two ZIP points a district holds, any mass, km.
- *Contacts* Σ_j |S_j|, and *split units*, units with two or more districts of positive mass.
- *Pieces*: the audit's ZIP contiguity on the declared graph (components beyond the heaviest).
  "Bridged" is a lower bound: the pieces left if every graph vertex with no cell in c could link
  any district, which removes the pieces the run labels "connector ZIP not in ledger".
- *Solver*: `solver.json` and the Hess arm's `hess_solver.json`. The support master's size is
  rebuilt from the spec (`master.build`, before presolve); the Hess size is its last MILP's,
  lazy connectivity cuts included.

| measure | national: diameter | national: Hess | WH: diameter | WH: Hess | FI: diameter | FI: Hess |
|---|---|---|---|---|---|---|
| final audit verdict | pass | pass | pass | pass | pass | pass |
| within ±10% | 16/16 | 16/16 | 12/12 | 12/12 | 24/24 | 24/24 |
| worst deviation | 9.56% | 7.36% | 8.30% | 9.75% | 9.54% | 8.31% |
| support diameter, km | **10,246** | 10,364 | **8,758** | 9,146 | **11,882** | 14,540 (planned 14,116) |
| Hess, 10⁶ m_rel·km² | 1,109 | **1,062** | 1,008 | **968** | 1,303 | **1,196** |
| mean / max district rms, km | 249 / 488 | 236 / 487 | 293 / 552 | 289 / 565 | 244 / 558 | 233 / 533 |
| mean / max extent, km | 941 / 1,790 | 898 / 1,790 | 1,029 / 1,694 | 1,047 / 1,694 | 869 / 2,023 | 855 / 2,023 |
| max support diameter, km | 1,498 | 1,498 | 1,360 | 1,360 | 1,399 | 1,360 |
| contacts | 56 | 57 | 54 | 56 | 61 | 67 |
| max units per district | 5 | 5 | 6 | 6 | 4 | 4 |
| split units (owners in them) | 5 (12) | 5 (13) | 5 (10) | 7 (14) | 8 (20) | 9 (27) |
| districts in pieces | 16 | 14 | 12 | 12 | 10 | 14 |
| pieces (bridged) | 292 (1) | 284 (0) | 600 (0) | 598 (0) | 38 (2) | 41 (0) |
| repair moves | 3 | 14 | 0 | 3 | 0 | 27 |
| solver status, gap | optimal, 0 | local optimum, no bound | optimal, 0 | local optimum, no bound | optimal, 0 | local optimum, no bound |
| solve time, s (Hess: the whole loop) | 0.45 | 580 | 7.55 | 21 | 0.05 | 4,970 |
| model: columns (integer) / rows / nonzeros | 12,724 (2,421) / 38,865 / 124,018 | 28,544 (28,544) / 51,625 / 229,984 | 24,841 (4,152) / 70,280 / 234,838 | 11,940 (11,940) / 28,944 / 124,248 | 5,056 (1,143) / 14,747 / 47,785 | 59,832 (59,832) / 94,414 / 429,936 |

Bold marks each arm's own objective. Each arm is also scored under the other's objective, and
the comparison stays inside one unit: on Hess, arm 1 is 4.4%, 4.1% and 9.0% above the Hess arm
(national, WH, FI); on support diameter, the Hess arm is 1.2%, 4.4% and 22.4% above arm 1. A km
of diameter and an m_rel·km² of Hess are never traded against each other here. Arm 1's split
units are national CA FL NJ NY TX, WH CA NJ NY OH PA and FI CA FL NC NJ NY OH PA TX. The Hess
arm's are national the same five (NY three ways), WH those five plus KY and VA, and FI those
eight plus TN. Pieces by cause: arm 1 has 26 / 13 / 3 corridor pieces, and the rest are
"connector ZIP not in ledger". The Hess arm has 8 corridor pieces on national and 2 shape pieces on
WH, and the rest are connectors. The support arm's solve times are the reference run's; its
re-run took 11.5 s to build and solve all three masters with their support families, and 0.11 s
for the three realizers.

**Audits.** Both runs pass. Beyond the solver lines, the Hess arm's scorecard differs from arm
1's in three checks:
- *Planned against drawn owners* lists one item: repair made FI_08 an extra owner of TN, a free
  unit. That raises FI's drawn diameter above its planned 14,116 km.
- *Certificate tier* is "feasible only" against arm 1's "exact".
- *ZIP contiguity* lists 40 districts in pieces with 923 pieces, against arm 1's 38 and 930.

A support-family check on the drawn unit sets (`run_hess.policy_check`, applied to both ledgers)
finds nothing in arm 1. In the Hess arm it finds five drawn shares below η, all left by the
repair pass, since the MILP holds η: national_16's NY, and FI_08's TN, FI_13's TN, FI_18's NC and
FI_20's NY. Size, distance caps, G[S] connectivity, ⌊1/η⌋ and the CA cap hold in both arms.

**Maps.** [national](https://github.com/helios1168/td/blob/main/docs/figures/exp81_national.png),
[WH](https://github.com/helios1168/td/blob/main/docs/figures/exp81_WH.png),
[FI](https://github.com/helios1168/td/blob/main/docs/figures/exp81_FI.png): support diameter on
the left and Hess on the right, drawn from each ledger as `python -m td maps` draws them. Colours
follow sorted district ids, so the same colour in both panels is not the same territory. Each
legend line gives the states the district holds opportunity in.

**Stakeholder summaries.** The same three plans in the stakeholder map look (state-level
districts per channel, $ from the channel totals, the legacy `plan_summary` figure the
2026-10-02 deck uses):
[support diameter](https://github.com/helios1168/td/blob/main/docs/figures/exp81_summary_support.png),
[Hess](https://github.com/helios1168/td/blob/main/docs/figures/exp81_summary_hess.png) and
[hess from support](https://github.com/helios1168/td/blob/main/docs/figures/exp81_summary_fromsupport.png).
States split between districts in any channel: 8 under support diameter and 11 under Hess.

| summary strip | national | WH | FI |
|---|---|---|---|
| support diameter: worst deviation, split states | 9.6%, 5 | 8.3%, 5 | 9.5%, 8 |
| Hess: worst deviation, split states | 7.4%, 5 | 9.8%, 7 | 8.3%, 9 |

**Why the maps differ.**
- *Where units are whole, the maps mostly agree.* 13 of 16 national districts (12 distinct unit
  sets, since both arms have two CA-only districts), 5 of 12 WH and 9 of 24 FI have the same
  drawn unit set in both arms. The largest extents are set by sparse whole
  states and are the same in both arms on all three channels (national_14 KS NE OK SD TX,
  1,790 km; WH_02, 1,694 km; FI_04 CA ID MT NV, 2,023 km), so neither objective moves them.
- *Inside a free unit, diameter is blind and Hess is not.* A copy of {CA} or {NY} costs 0 however
  its ZIPs spread, and which ZIPs it gets is the realizer's call, made from border-aware or
  k-means centres. The Hess arm puts each such district on a metro, at the price of crossing
  state lines, which diameter charges.
- *Hess is nearly blind to light whole units and to state lines.* A whole unit's Hess cost is
  M_v‖p̄_v − c_j‖² plus a fixed inertia, so a light unit costs almost nothing wherever it goes. Its
  district is then chosen by the size, distance-cap and connectivity rows more than by geography.
  RI (17 m_rel) and VT (3) join the New York City district national_15, a 432 km support. A
  state line costs Hess nothing either, so the FI districts around New York, Pennsylvania, Ohio
  and Tennessee cross one to reach a metro (the first case below). Diameter charges each such
  crossing in full.
- *Repair does more work after Hess.* The Hess plan assigns free ZIPs one by one with no
  contiguity row, and repair moved 14 / 3 / 27 detached pieces, against arm 1's 3 / 0 / 0. That
  is where the extra FI owner and the five η shortfalls come from.

**Where the objectives disagree.**
- *A district wholly inside a split unit, diameter 0, with different spread.* Observed. Arm 1's
  national_04 is CA alone and spans the Bay Area and Los Angeles (San Jose 35%, San Francisco
  22%, Los Angeles 12% of its mass): rms 197 km, extent 571 km, diameter 0. The Hess arm's two
  CA-only districts both sit in Southern California (Los Angeles, Riverside, San Diego), with rms
  57 and 27 km and extents 224 and 107 km. It gives the Bay Area to the CA+NV district
  national_07, whose rms rises from 154 to 225 km. FI shows the same pattern. Arm 1 has six
  single-state FI districts, all scored 0; FI_21 (upstate NY) has rms 192 km and extent 556 km.
  The Hess arm keeps only FI_10 (FL). In place of the other five it draws six cross-border
  districts: OH+WV 241 km, NJ+NY 255, NJ+NY+PA 261, NY+PA 261, OH+PA 449 and NC+TN 577.
  Together they carry 2,044 km of FI's 2,659 km rise in diameter.
- *A long support whose opportunity is concentrated near its centre.* Observed. The Hess arm's
  national_15 (NJ NY RI VT) has a diameter of 432 km and an rms of 42 km: 98% of its mass is in
  the New York CBSA, and RI and VT are light whole units. Its FI_23 (OH+PA) has a diameter of
  449 km and an rms of 83 km, with 57% of its mass in Pittsburgh, near the OH–PA border. Arm 1's
  candidates are national_15 (MA ME NH NY RI: 566 km, rms 109) and WH_07 and FI_09 (DE NJ PA:
  261 km, rms 59 and 61).
- *A compact ZIP-level result with more administrative fragmentation.* Observed on FI and WH,
  and slightly on national.
  - FI: contacts rise from 61 to 67, split units from 8 to 9, and owners in split units from 20
    to 27. NY and PA each go four ways. TN, a single district in arm 1, goes three ways (615 /
    59 / 49 m_rel), and two of those shares fall below η after repair.
  - WH: KY and VA split (66 / 79 and 106 / 92 m_rel).
  - national: NY goes three ways instead of two.
  #80's piece charge prices exactly this.
- *A support-level improvement the realizer cannot turn into a comparably compact map.*
  Observed. Arm 1's FI_08 is DC+MD+PA, at 210 km one of its smallest multi-unit diameters, but
  94% of its drawn PA share lies in the Pittsburgh CBSA. The district runs from Washington to
  Pittsburgh: rms 151 km, extent 516 km. WH_06 is the same support (PA share 70% Pittsburgh,
  rms 133 km, extent 597 km). In the Hess arm, MD goes with DE and eastern PA (FI_09 DE MD PA,
  rms 88 km, extent 386 km), DC with VA and NC (FI_08), and Pittsburgh with eastern Ohio
  (FI_23).

**Runtime and model size.** The support arm built and solved all three masters in 11.5 s, each
to proven optimality (gap 0). Its largest master, WH, has 24,841 columns, of which 4,152 are
integer.
- *Hess wall time.* The Hess arm took 580, 21 and 4,970 s (national, WH, FI): 5,571 s in total,
  about 480 times as long.
- *Hess model size.* Every column is binary, from 11,940 (WH) to 59,832 (FI), and the rows carry
  586 up-front separator-cut families plus 6–16 lazy ones per channel.
- *MILP solves.* national and WH needed 8 MILPs each, the full-model ones taking 1–69 s;
  national's restricted first assignment took four 120 s rounds. FI needed 13. Its seven full
  MILPs took 590, 882, 900, 900, 560, 248 and 308 s. Iterations 2 and 3 stopped at the 900 s
  limit with gaps of 1.3e-5 and 2.6e-6; the other five ended optimal.
- *Certificates.* Each full MILP is certified only at its own centres. Nothing bounds the Hess
  objective over all centres, so the Hess arm's 4–9% gain is measured against a local optimum
  from one seed.

**Verdict.** Inconclusive (`docs/problem/UNKNOWNS.md` U38). At ZIP grain, Hess removes two real
failure modes of support diameter:
- diameter-0 single-state districts that spread across a large state;
- small-diameter supports that the realizer draws long.

It pays for that in several ways:
- support diameter rises 1–22%, and administrative fragmentation rises on FI and WH;
- repair leaves five η shortfalls and one extra owner;
- it runs about 480 times as long;
- it gives no global certificate.

Its gain in its own unit is 4–9%, and in mean district rms 1–5%. Neither arm dominates. The
"hess from support" variant below separates the objective from the seed. Still open: the owner's
reading of the side-by-side maps.

### Variant: hess from support

Measured 2026-10-02 on m5 (#81). The variant runs the Hess arm's location–allocation loop
unchanged except for its start (`tools/exp81/run_variant.py`, `seed_support.py`):
- *Seed.* District j starts at the M-weighted centroid of the support arm's j-th drawn district.
  The LP-relaxed rounds are skipped, so the first assignment is made at the support map's own
  geometry.
- *First assignment.* It is still the restricted one (each item limited to its nearest 3, then 5
  centres), because the support map lies outside the planning band and is not a feasible start.
  On FI, nearest-3 was infeasible and nearest-5 stopped at its 120 s limit with a gap of 2.1e-6.
- *Everything else* is the Hess arm's: the rows, the fixed-centre MILPs (`mip_rel_gap` 0), the
  centroid moves, the stop when the assignment repeats, and `run_hess.py assemble`.

The seed objective is the support map's Hess score at its own centroids, which is arm 1's Hess
measure above. Objectives are the planned ones, in 10⁶ m_rel·km².

| | national | WH | FI |
|---|---|---|---|
| seed objective | 1,109.09 | 1,008.37 | 1,303.35 |
| converged objective | 1,062.04 | 970.40 | 1,216.47 |
| change from the seed | −4.24% | −3.76% | −6.67% |
| centre iterations; full MILPs, all optimal at gap 0 | 6; 6 | 4; 4 | 7; 8 |
| wall time, s (box under load) | 205 | 9 | 794 |
| Hess arm's objective (k-means seed) | 1,062.04 | 970.40 | 1,201.94 |
| variant against the Hess arm | identical | identical | +1.21% |
| drawn ZIPs (m_rel > 0) assigned differently from the Hess arm | 0 of 3,713 | 0 of 1,390 | 570 of 5,122 (13.4% of m_rel) |
| whole units assigned differently from the Hess arm | 0 of 44 | 0 of 33 | 4 of 40: DC MS VT WV |
| planned ZIPs moved from the support map (matched by largest shared mass) | 427 (11.4% of m_rel) | 145 (9.1%) | 616 (13.0%) |
| whole units the plan moved from the support map | CT NV RI | CT NM NV VT WY | CT DE KS VT WY |

On national and WH the variant's drawn ledger equals the Hess arm's ZIP for ZIP, district labels
included, so every drawn measure in the main table holds for the variant and no new map is
drawn. Only the run differs: national took 205 s against 580 s and WH 9 s against 21 s, without
the LP-relaxed rounds and on a loaded box, so this is no clean benchmark. On FI
the variant's labels drift from their seeds and from the Hess arm's, so the FI counts match
districts by largest shared mass. The FI rows of the drawn measures:

| measure | FI: diameter | FI: Hess | FI: Hess from support |
|---|---|---|---|
| final audit verdict | pass | pass | pass |
| within ±10% | 24/24 | 24/24 | 24/24 |
| worst deviation | 9.54% | 8.31% | 8.48% |
| support diameter, km | **11,882** | 14,540 (planned 14,116) | 12,526 (planned the same) |
| Hess, 10⁶ m_rel·km² | 1,303 | **1,196** | **1,216** |
| mean / max district rms, km | 244 / 558 | 233 / 533 | 233 / 533 |
| mean / max extent, km | 869 / 2,023 | 855 / 2,023 | 852 / 2,023 |
| max support diameter, km | 1,399 | 1,360 | 1,360 |
| contacts | 61 | 67 | 61 |
| max units per district | 4 | 4 | 4 |
| split units (owners in them) | 8 (20) | 9 (27) | 8 (20) |
| districts in pieces | 10 | 14 | 12 |
| pieces (bridged) | 38 (2) | 41 (0) | 38 (2) |
| repair moves | 0 | 27 | 14 |
| η shortfalls after repair | 0 | 4 | 1 |
| solver status, gap | optimal, 0 | local optimum, no bound | local optimum, no bound |
| solve time, s (Hess: the whole loop) | 0.05 | 4,970 | 794 |
| model: columns (integer) / rows / nonzeros | 5,056 (1,143) / 14,747 / 47,785 | 59,832 (59,832) / 94,414 / 429,936 | 59,832 (59,832) / 94,078 / 427,488 |

The variant's audit passes on all three channels, with the scorecard's "feasible only" tier. The
support-family check (`run_hess.policy_check` on the drawn ledger) finds the Hess arm's
national_16 NY shortfall again, since that plan is the same. On FI it finds one shortfall,
FI_08's PA (DC DE MD PA), in place of the Hess arm's four. FI's split units are arm 1's eight:
CA FL NC NJ NY OH PA TX, with TN in one district again. 16 of the variant's 24 FI unit sets are
arm 1's, against 9 for the Hess arm. It keeps four single-state districts (FL, OH, PA and TN), where arm 1
has six and the Hess arm one. Its upstate New York district, FI_21 (NY VT), has rms 198 km and
extent 649 km.
[FI map](https://github.com/helios1168/td/blob/main/docs/figures/exp81_fromsupport_FI.png):
the Hess arm on the left and the variant on the right. As in the main maps, the same colour in
both panels is not the same territory.

**What it says.**
- *Seed dependence.* The Hess local optimum depends on the seed on FI and not, from these two
  seeds, on national or WH. On FI the support seed's plan is 1.2% above the k-means seed's and
  assigns 13% of the m_rel differently. Two seeds bound nothing: the spread over other
  seeds is unmeasured, and so is the gap to the global optimum.
- *Distance from a Hess local optimum.* Under the Hess arm's rules, the local optimum the support
  map descends to is 4.2%, 3.8% and 6.7% below it (national, WH, FI). On national and WH that
  optimum is the Hess arm's plan.
- *The FI tradeoff.* On Hess, arm 1 is 7.1% above the FI optimum near the support map, against
  9.0% above the Hess arm. On support diameter, that optimum is 5.4% above arm 1, against 22.4%
  for the Hess arm. It keeps arm 1's contacts, split units and piece count, and leaves one η
  shortfall, not four. So on FI the extra fragmentation is not the price of Hess compactness: a
  Hess local optimum within 1.2% of the Hess arm's has none of it. The lower of the two optima
  found is still the fragmented one. On WH the fragmentation is in the only optimum found: KY
  and VA split from both seeds.

Regenerate (m5, local inputs, `runs/exp81/`):

```
"$TD_PY" -u tools/exp81/run_hess.py solve <channel>          # one process per channel
"$TD_PY" -u tools/exp81/run_hess.py assemble --out runs/exp81/hess
"$TD_PY" tools/exp81/measure.py <run_dir> --spec scenarios/experiments/16n_12wh_24fi_nowifi_mtn1600.toml --out runs/exp81/<arm>_measures.json
"$TD_PY" tools/exp81/sidebyside.py <arm1_run_dir> runs/exp81/hess --out docs/figures --prefix exp81_ --labels "support diameter" "Hess (ZIP, location–allocation)"
"$TD_PY" -u tools/exp81/run_variant.py solve <channel>       # one process per channel
"$TD_PY" -u tools/exp81/run_hess.py assemble --out runs/exp81/hess_from_support
"$TD_PY" -u tools/exp81/run_variant.py compare
"$TD_PY" tools/exp81/sidebyside.py runs/exp81/hess runs/exp81/hess_from_support --out <dir> --prefix exp81_fromsupport_ --labels "Hess (k-means seed)" "Hess (seeded from the support map)"   # FI's PNG only
# stakeholder summaries: the gitignored sweep adapter and legacy plan_summary on m5, unchanged;
# adapt.py reads <run_dir>.toml, a link to the 18-split spec
export TD_ZCTA_SHP=runs/sweep/grid_2026-10-01/present/legacy/archive/data/tiger/2025/tl_2025_us_zcta520.shp
"$TD_PY" runs/sweep/caps_2026-10-02/adapt.py <run_dir> runs/exp81/summary/<name> "900 (1600 mtn/plains, WA, CA)"
"$TD_PY" runs/sweep/caps_2026-10-02/wrap.py runs/exp81/summary/<name> --geo-cache runs/sweep/grid_2026-10-01/present/legacy/archive/geo
```

## #109 A contiguity-aware realizer on today's plans (2026-10-05)

Measured 2026-10-05 on m5 with `tools/exp/contig/` (#109) on the polygon graph and its 163
approved connectors, after #114 and #116, before the owner approved #114's 16 proposed connectors
the same day; those runs are in `runs/exp/contig/pre_connectors/`, and s13, deck A and grid
na15/WH12/FI23 are being redrawn on the approved list. Each scenario was re-planned on today's `main` with
`margin = false` in every channel (μ = 0), and drawn by the realizer instead of the power diagram;
the run folders are `runs/exp/contig/<map>-<arm>/` (gitignored; full ledger, scorecard, districts,
run.json, contig.json). M1 is `td.audit.check_m1` on the written ledger, footprint coverage (D3).

**The realizer.** Per channel, every ZCTA of a split unit, of an exclave (D2) and of a dropped unit
is free, zero-opportunity ZCTAs included; the rest is fixed to its unit's one holder. Free ZCTAs go
to districts by a MILP per coupled group (free components that share a district): each ZCTA one
owner, each district's drawn mass in the internal band, holders per unit first and geodesic shape
second in the objective. Connectivity is exact on the polygon graph: highspy 1.15.1 exposes
`cbMipDefineLazyConstraints` but HiGHS never calls it (tested: the other MIP callbacks fire), so
the realizer runs a solve-check-cut loop of separator rows (U59), each ZCTA demanding one unit, so
zero-opportunity ZCTAs are held to it. A geodesic-DAG restriction (each ZCTA needs a neighbour of
its district nearer the district's border, CONTIGUITY.md §4 rank 2) runs first and its drawing
starts the complete loop. "optimal" is a connected optimum of the complete model at
`mip_rel_gap = 0`; "connected" is connected and feasible; "infeasible" is a proof under the
group's rules; "unknown" is a time limit or a restricted model, never infeasible. No archived
engine was reused (U64): the pair-era SCIP engine (`td/solvers/scip_tree.py` at the tag, C03) is a
two-label log-objective SCIP model; only its separator idea carried over.

**Sequential.** Coupled groups are large (below), so the arms were also run one split unit at a
time (`--sequential`): each unit drawn against what its districts already own next to it, the rest
at planned shares. That is neither a restriction nor a relaxation of the joint model; its drawings
are real maps judged by the audit, and its failures prove nothing.

**What was run.** Deck A (`none_stay_0_m1600_na13_WH12_FI23`, national 13 / WH 12 / FI 23, every
channel optimal at δ = 0.02 on the polygon graph), IFA K 49 (optimal at δ = 0.02), layout-`none`
grid maps, and s13 (`ne_okks_s13_na15_WH12_FI20_CB3`, FI δ = 0.08), for comparison only while
#114's proposed connectors were unruled (D14). Decks B and C are combined
layouts blocked the same way and were not drawn. Arms: `arm1` (the master's support, shares
recomputed in the plan's band), `arm1` with fixed targets (each (unit, district) mass within the
unit's heaviest ZCTA of the plan, the triage's row 15), and arm 2's remedies as separate runs, never
one chosen (#112): `band` (a group retried at δ = 0.05, 0.10, 0.15), `split` (a unit's neighbouring
districts may also hold it, each a split) and `move` (as `split`, no more holders than the plan).
No no-good cut was issued: no plan's whole read-back fibre was proved empty (#91 finding 10).

**Coupled groups (U59).** Joint groups at ZIP scale, from the joint `arm1` runs:

| map | channel | groups: districts / free ZCTAs (columns) | joint status at 300 s + 300 s |
|---|---|---|---|
| deck A | national | 7 / 7,421 (14,853); 6 / 3,822 (11,246) | unknown, unknown |
| deck A | WH | 4 / 4,257 NY+NJ+PA (8,519); 2 / 1,833 CA (3,641); 2 / 1,397 IL; 2 / 1,013 FL; 1 / 1 | unknown; connected; three not reached in the channel's 900 s |
| deck A | FI | 22 / 16,192 (37,864) | unknown |
| IFA 49 | IFA | 49 / 21,182 (70,512; 170k rows) | unknown |

No joint group above 1,833 free ZCTAs reached a connected drawing or a proof in the time given,
so the joint maps keep the power diagram's owners there and fail M1 as before; no infeasibility
certificate was produced for any real map, at fixed targets or recomputed shares. The toy
certificate (#7's thin share, `tests/test_contig_realize.py`) is the only proof. The fixed-target
runs were equally unknown on every large group.

**Results** on the pre-approval connector list (runs ended by 08:45; per map, channels summed;
`runs/exp/contig/pre_connectors/TABLE.md` on m5 has the per-channel table, from
`tools/exp/contig/report.py`):

| run | M1 (D3) | pieces | largest piece | groups or units drawn connected | worst / mean dev | split units | cuts | δ needed | share-only (U61) | exclave splits |
|---|---|---|---|---|---|---|---|---|---|---|
| deckA-arm1 (joint) | fail | 9 | 0.448 τ | 1 of 8 | 2.4% / 1.0% | 36 | 42 | – | 16 | 9 |
| deckA-arm1-fixed (joint, fixed targets) | fail | 9 | 0.448 τ | 1 of 8 | 2.4% / 1.0% | 36 | 42 | – | 16 | 9 |
| deckA-arm1-seq | fail | 7 | 0.448 τ | 15 of 28 | 3.8% / 1.3% | 36 | 42 | – | 16 | 9 |
| deckA-band-seq | fail | 3 | 0.46 τ | 28 of 28 | 5.0% / 2.0% | 36 | 42 | 0.05 | 16 | 9 |
| deckA-split-seq | fail | 5 | 0.448 τ | 14 of 28 | 2.4% / 1.2% | 36 | 42 | – | 16 | 9 |
| deckA-move-seq | fail | 7 | 0.448 τ | 12 of 28 | 3.8% / 1.3% | 36 | 42 | – | 16 | 9 |
| grid na13/WH12/FI24 arm1-seq | fail | 9 | 0.464 τ | 12 of 28 | 6.1% / 1.6% | 37 | 45 | – | 20 | 11 |
| grid na13/WH11/FI24 arm1-seq | fail | 10 | 0.464 τ | 12 of 26 | 7.5% / 3.0% | 36 | 44 | – | 17 | 12 |
| grid na15/WH12/FI23 arm1-seq | fail | 3 | 0.448 τ | 17 of 29 | 3.6% / 1.4% | 38 | 43 | – | 19 | 9 |
| ifa49-arm1 (joint) | fail | 13 | 0.367 τ | 0 of 1 | 7.0% / 1.7% | 24 | 50 | – | 36 | 5 |
| ifa49-arm1-fixed (joint, fixed targets) | fail | 13 | 0.367 τ | 0 of 1 | 7.0% / 1.7% | 24 | 50 | – | 36 | 5 |
| ifa49-arm1-seq | fail | 6 | 0.367 τ | 20 of 22 | 16.4% / 2.5% | 24 | 49 | – | 36 | 5 |
| ifa49-band-seq | fail | 6 | 0.367 τ | 21 of 22 | 16.4% / 2.9% | 24 | 49 | – | 36 | 5 |
| ifa49-split-seq | fail | 11 | 0.367 τ | 15 of 22 | 16.4% / 2.5% | 24 | 51 | – | 36 | 5 |
| ifa49-move-seq | fail | 13 | 0.367 τ | 12 of 22 | 16.4% / 2.4% | 24 | 50 | – | 36 | 5 |
| s13-arm1-seq (comparison) | fail | 14 | 0.0882 τ | 14 of 15 | 9.4% / 6.0% | 24 | 32 | – | 12 | 9 |
| s13-band-seq (comparison) | fail | 14 | 0.0882 τ | 14 of 15 | 9.4% / 6.0% | 24 | 32 | – | 12 | 9 |

Pieces and the largest piece are M1's on the ledger. Deviation is drawn mass over the channel mean.
A group or unit the realizer did not draw keeps `td.realize` and `td.territory`'s owners, so a
failing map mixes the two realizers and its balance is not the realizer's (IFA's 16.4% is NY#3,
from NY's fallback beside NJ drawn by the realizer). Split units and cuts are counted on the drawn
map by polygon ownership; against a covering bound every map is **not covered** (U56): no all-M1
bound exists yet (#119), and #103's s* is labelled "over 𝒳_c(δ) only". U63 (districts resting on
one connector) is defined on M1-passing drawings, and there are none.

**What the runs show.**
- **No map drawn by the realizer alone passes M1** (footprint coverage, D3), in any arm; the window
  repair below makes s13, deck A, grid na15/WH12/FI23 and IFA 49 pass.
- **Every layout-`none` map fails on the same district shape**: a district whose units join only
  through split units, above all one per channel holding CT and a share of NY (deck A national_07,
  WH_05 and FI_07 = CT + NJ + NY; grid na15 national_08, WH_05, FI_07). CT reaches its other units
  only through NY, and no NY drawing that routes the share from CT to them was found at the plan's
  δ: the NY unit is `unknown` in every arm-1 run (the DAG restriction infeasible, the complete loop
  out of time), so CT's 289 ZCTAs stay detached at 0.13–0.46 τ. Grid na15/WH12/FI23 is down to
  exactly these three pieces. With a wider band (`band`), every unit of deck A drew connected at
  δ ≤ 0.05 one at a time and national_07 joined, yet three pieces remain as gaps between units drawn
  separately: WH_05 and FI_07 (CT with its NY share, apart from the NJ share) and national_08
  (DC + NC + NJ + PA + VA + WV, its PA share apart). This is #112's case; it is unproved either way,
  and no certificate exists for it.
- **Elsewhere the sequential realizer draws most split units connected at the plan's δ**: IFA 20 of
  22 units (FL and NY unknown), deck A 15 of 28 at δ = 0.02 and all 28 at δ ≤ 0.05.
- **s13** gets down to a largest piece of 0.088 τ, against 0.455 τ for the power diagram, but on
  the pre-approval list it fails on the cross-channel exclaves D14 names (06390, 89826, 89832,
  82933–82944), which the approved connectors now join, and on five small NYC pieces.
- **s13 on the approved connector list** (`runs/exp/contig/s13-arm1-seq/`, sequential arm 1, after
  the owner's 2026-10-05 ruling): M1 fail with 3 detached pieces, all in national's NY share
  (11214..., 8 ZCTAs, 0.136 τ; 10302..., 8 ZCTAs, 0.0225 τ; 11701..., 5 ZCTAs, 0.0119 τ), where the
  NY unit was not drawn (`unknown`) and kept the power diagram's owners. WH, FI and WIFI have no
  detached piece; FI's OH and PA units were not drawn either and happen to be whole there. Worst
  deviation 9.4% (national), split units 14, cuts 22, no exclave splits.
- **Arm 2** (`split`, `move`) did not beat arm 1: allowing a unit's neighbouring districts makes the
  per-unit models larger and slower, and no remedy produced an M1 map.

**Window repair** (`tools/exp/contig/repair.py`, 2026-10-05, m5). A large-neighbourhood search
on a drawn run folder that fails M1: per channel, each district's detached pieces in turn, every
ZCTA outside a window W keeps its owner and one exact MILP (`draw._solve_group`) redraws W. W is
first a ball, the free ZCTAs (split units, exclaves, dropped units) within h hops of the pieces
plus the pieces (a piece over 750 ZCTAs only to h hops inside its border), h = 3, 6, 12, ... while
proved infeasible, up to 1,500 ZCTAs; then a corridor, the free ZCTAs on a path from the piece to
the rest of its district at most `slack` hops longer than the shortest. Rows: each ZCTA one owner,
each district's drawn mass in the channel's final band (±10%, the band the audit judges; a
district whose mass outside W is already above it makes W infeasible), the
window units' split units and cuts not above the drawn map's; objective split units, then cuts,
then geodesic shape. Connectivity is exact: separator rows per BFS layer in the cut loop, and
with `--flow` a single-commodity flow per district from its root body, which proves an infeasible
window in seconds where the cut loop ran for minutes. `--keep-support` (arm 1) lets a ZCTA go only
to a district whose plan holds its unit; without it a unit may change holders (arm 2), which the
audit lists. "optimal" is optimal on W with the rest fixed (`mip_rel_gap = 0`), never an optimum
of the map; "infeasible" proves only that W at that size has no drawing, never a certificate for
the map, and no no-good cut was issued. The runs read their source's ledger back to plan copies
and write a full run folder; a pre-connector drawing is repaired with the plan that drew it
(`--plans-file`) and audited on the approved graph.

| repaired run (`runs/exp/contig/`) | source drawing | channel: pieces before (largest) → windows (shape size \|W\| status s) | M1 / audit | worst dev before → after | split states / cuts |
|---|---|---|---|---|---|
| `s13-arm1-seq-repair` | s13 arm1-seq, approved list | national: 3 (0.136 τ) → ball 3 117 optimal <1 | **pass / pass** | national 9.4% → 10.0% | 4 / 7 unchanged |
| `s13-band-seq-repair` (arm 1, flow) | s13 band-seq, approved list | national: same 3 → ball 3 117 optimal 0.1 | **pass / pass** | national 9.4% → 10.0% | 4 / 7 unchanged |
| `g_na15_WH12_FI23-arm1-seq-pre-repair-ks` (arm 1, flow) | grid na15/WH12/FI23 arm1-seq, pre-connector | each channel CT (289 ZCTAs; 0.152 / 0.298 / 0.448 τ) → ball 3 372, ball 6 528 infeasible; ball 12 1002 optimal (national 21.5, WH 30.2, FI 2.5) | **pass / pass** | national 3.6% → 9.5%, WH 2.0% → 2.4%, FI 2.0% → 8.7% | 13/15, 8/8, 17/20 unchanged |
| `deckA-band-seq-pre-repair` (flow) | deck A band-seq, pre-connector | national DC+NC+NJ+PA+VA+WV's PA/VA/WV piece (2,202 ZCTAs, 0.184 τ) → ball 1 1208, corridor 0 14 infeasible; corridor 1 47 optimal 0.5. WH CT+NY piece (572, 0.46 τ) → ball 2 1267, corridor 0 15, corridor 1 71 infeasible; corridor 2 191 connected (gap 3.8e-4, 600). FI CT (328, 0.45 τ) → ball 3 457 optimal 9.5 | **pass / pass** | national 5.0%, WH 4.9%, FI 4.9% → 7.6% | 11/14, 8/8, 17/20 unchanged |
| `deckA-band-seq-pre-repair-ks` (arm 1, flow, b589d15) | the same | the same windows and statuses (WH corridor 2 connected, gap 2.3e-3) | **pass / pass** | the same | unchanged |
| `deckA-band-seq-repair` (arm 1, flow) | deck A band-seq, approved list | national piece (2,019, 0.154 τ) → corridor 1 47 optimal 0.6; FI CT + 07844 (0.448 τ) → ball 3 409 infeasible, ball 6 767 unknown (600), corridor 2 164 optimal 5.9 | **pass** / fail (WH bands, from the source) | unchanged: national 10.0%, WH 15.0%, FI 5.0% | 8/10, 6/6, 14/17 unchanged |
| `g_na15_WH12_FI23-band-seq-repair` (arm 1, flow) | grid band-seq, approved list | FI as deck A's | **pass** / fail (WH bands, from the source) | unchanged: national 2.6%, WH 15.0%, FI 5.0% | 9/11, 6/6, 14/17 unchanged |
| `ifa49-arm1-seq-repair-fast` (arm 1, flow, 90 s and 1,000 ZCTAs per window) | IFA 49 arm1-seq, redrawn 2026-10-05 on the approved list (16 pieces, largest 0.366 τ) | IFA, one district at a time: 06901 ball 3 18, MI#2 ball 3 37, NY#2 ball 3 59, NJ#2 ball 3 88 optimal; NY#4's Manhattan piece (69, 0.366 τ) ball 3 192 unknown, corridor 2 57 optimal; NY#3's four (78 ZCTAs from 06390, 0.338 τ, and three upstate) corridor 8 675 connected; IL+IN+MI+OH#1's two ball 3 714 optimal; DC+DE+MD+NJ+PA#1's two ball 3 670 connected; CT+NY+RI+VT#1's last ball 16 933 connected; every other window proved infeasible | **pass / pass** | 9.5% → 9.9% | 22 / 42 → 22 / 40 |

- **s13, deck A, grid na15/WH12/FI23 and IFA 49 each have an M1-passing map whose audit passes**:
  `s13-arm1-seq-repair` and `s13-band-seq-repair`, `deckA-band-seq-pre-repair` and its arm-1 rerun,
  `g_na15_WH12_FI23-arm1-seq-pre-repair-ks` and `ifa49-arm1-seq-repair-fast`. No split or cut
  rises (IFA's cuts fall by two); the cost is balance inside the final band, not the plan's δ
  (deck A's internal δ was 0.05 already, the `band` remedy). In s13, deck A and the grid no planned
  share vanishes; in IFA two do (IFA_11's 0.086 of CT, IFA_21's 0.126 of IL; C8, listed by the
  audit, not failed), which arm 1 allows since no district gains a unit. Deck A's and
  the grid's are repairs of drawings made before the owner approved #114's connectors, judged on
  the approved graph with the plans that drew them. The approved-list band-seq drawings of the
  same two maps also pass M1 after repair, but their WH channel was drawn at δ = 0.15 by the `band`
  remedy and fails the final band (WH_07 +15%, WH_11 −14.5%) before and after.
- **The CT + NJ + NY district** joins CT to NJ through NY once W holds about 1,000 ZCTAs of
  Westchester, the Bronx, Manhattan and the Hudson shore (ball 12), or a corridor of 164–191; the
  balls of 372–528 are proved infeasible. Without `--keep-support` grid national instead moved CT
  whole to national_15 and 32 NY ZCTAs back (`g_na15_WH12_FI23-arm1-seq-pre-repair`, an arm-2
  move the audit lists), so the arm-1 run is the one to read.
- Every window that drew took under 100 s except deck A's WH corridor (600 s, connected, not
  proved optimal); the infeasible ones were proved in under 30 s each. IFA needed one fix: a
  neighbouring district's own piece away from the window is left as it is (its mass still in the
  band row) instead of having to join through W, which had made every IFA window infeasible.
  The runs are from commits 28847d7 (`s13-arm1-seq-repair`), 7d4df99 (`deckA-band-seq-pre-repair`),
  0a04329 (the `-ks` grid run and the approved-list band-seq repairs) and b589d15 (IFA); the
  later commits change how pieces are grouped and which components of a neighbouring district
  must join; the earlier runs were not repeated with them. U63, the districts whose
  connectivity rests on one connector edge (contig.json lists the edges): s13 national 11, WH 10,
  FI 11, WIFI 3 (`s13-arm1-seq-repair`); grid and deck A national 11, WH 9, FI 13; IFA 17 of 49.

**Per channel** (`tools/exp/contig/report.py` on the repaired folders, regenerated 2026-10-05
after the review fixes; the folders were read, not rewritten). A channel the repair redrew shows
the repair's final band δ in "δ needed", marked "(repair)", with the worst deviation it reached;
before the fix the column copied the source drawing's δ (grid FI 0.02 at 8.7%). A channel with no
window keeps its source drawing's δ.

| run | arm | channel | K | plan δ | M1 (map, D3) | pieces | largest piece | drawn | groups | s | worst gap | δ needed | worst / mean dev | split units | cuts | share-only (U61) | exclave splits | one-connector districts (U63) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| s13-arm1-seq-repair | arm1+repair seq | FI | 20 | 0.08 | pass | 0 | 0 τ | not all (unknown) | connected 5, unknown 2 | 254.2 | 2.1e-16 |  | 8.0% / 5.1% | 7 | 11 | 5 | 0 | 11 |
| s13-arm1-seq-repair | arm1+repair seq | WH | 12 | 0.0595 | pass | 0 | 0 τ | all (connected) | connected 3 | 216.2 | 0.012 | 0.0595 | 5.9% / 4.2% | 3 | 4 | 0 | 0 | 10 |
| s13-arm1-seq-repair | arm1+repair seq | WIFI | 3 | 0.1 | pass | 0 | 0 τ | all (connected) |  | 0 |  | 0.1 | 9.3% / 6.2% | 0 | 0 | 0 | 0 | 3 |
| s13-arm1-seq-repair | arm1+repair seq | national | 15 | 0.0938 | pass | 0 | 0 τ | all (connected) | connected 3, optimal 1, unknown 1 | 213.3 | 0 | 0.1 (repair) | 10.0% / 7.4% | 4 | 7 | 6 | 0 | 11 |
| s13-band-seq-repair | band+repair seq | FI | 20 | 0.08 | pass | 0 | 0 τ | all (connected) | connected 7 | 288.9 | 2.1e-16 | 0.1 | 10.0% / 6.4% | 7 | 11 | 5 | 0 | 10 |
| s13-band-seq-repair | band+repair seq | WH | 12 | 0.0595 | pass | 0 | 0 τ | all (connected) | connected 3 | 216 | 0.012 | 0.0595 | 5.9% / 4.2% | 3 | 4 | 0 | 0 | 10 |
| s13-band-seq-repair | band+repair seq | WIFI | 3 | 0.1 | pass | 0 | 0 τ | all (connected) |  | 0 |  | 0.1 | 9.3% / 6.2% | 0 | 0 | 0 | 0 | 3 |
| s13-band-seq-repair | band+repair seq | national | 15 | 0.0938 | pass | 0 | 0 τ | all (connected) | connected 3, optimal 1, unknown 1 | 573.6 | 0 | 0.1 (repair) | 10.0% / 7.4% | 4 | 7 | 6 | 0 | 11 |
| g_na15_WH12_FI23-arm1-seq-pre-repair-ks | arm1+repair seq | FI | 23 | 0.02 | pass | 0 | 0 τ | all (connected) | connected 7, infeasible 2, optimal 1, unknown 7 | 408.7 | 0.0039 | 0.1 (repair) | 8.7% / 1.7% | 17 | 20 | 10 | 0 | 13 |
| g_na15_WH12_FI23-arm1-seq-pre-repair-ks | arm1+repair seq | WH | 12 | 0.02 | pass | 0 | 0 τ | all (connected) | connected 4, infeasible 2, optimal 1, unknown 2 | 260.8 | 0.0095 | 0.1 (repair) | 2.4% / 1.4% | 8 | 8 | 3 | 0 | 9 |
| g_na15_WH12_FI23-arm1-seq-pre-repair-ks | arm1+repair seq | national | 15 | 0.025 | pass | 0 | 0 τ | all (connected) | connected 6, infeasible 2, optimal 1, unknown 3 | 365.3 | 0.042 | 0.1 (repair) | 9.5% / 2.7% | 13 | 15 | 6 | 0 | 11 |
| deckA-band-seq-pre-repair | band+repair seq | FI | 23 | 0.02 | pass | 0 | 0 τ | all (connected) | connected 14, optimal 1 | 895.1 | 0.013 | 0.1 (repair) | 7.6% / 2.1% | 17 | 20 | 10 | 0 | 13 |
| deckA-band-seq-pre-repair | band+repair seq | WH | 12 | 0.02 | pass | 0 | 0 τ | all (connected) | connected 7, infeasible 3 | 949.9 | 0.0095 | 0.1 (repair) | 4.9% / 1.6% | 8 | 8 | 3 | 0 | 9 |
| deckA-band-seq-pre-repair | band+repair seq | national | 13 | 0.02 | pass | 0 | 0 τ | all (connected) | connected 8, infeasible 2, optimal 1 | 921.7 | 0.0035 | 0.1 (repair) | 5.0% / 2.6% | 11 | 14 | 3 | 0 | 11 |
| deckA-band-seq-pre-repair-ks | band+repair seq | FI | 23 | 0.02 | pass | 0 | 0 τ | all (connected) | connected 14, optimal 1 | 894.1 | 0.013 | 0.1 (repair) | 7.6% / 2.1% | 17 | 20 | 10 | 0 | 13 |
| deckA-band-seq-pre-repair-ks | band+repair seq | WH | 12 | 0.02 | pass | 0 | 0 τ | all (connected) | connected 7, infeasible 3 | 951.6 | 0.0095 | 0.1 (repair) | 4.9% / 1.6% | 8 | 8 | 3 | 0 | 9 |
| deckA-band-seq-pre-repair-ks | band+repair seq | national | 13 | 0.02 | pass | 0 | 0 τ | all (connected) | connected 8, infeasible 2, optimal 1 | 921.2 | 0.0035 | 0.1 (repair) | 5.0% / 2.6% | 11 | 14 | 3 | 0 | 11 |
| deckA-band-seq-repair | band+repair seq | FI | 23 | 0.02 | pass | 0 | 0 τ | all (connected) | connected 10, infeasible 3, optimal 1, unknown 2 | 2267.8 | 0.28 | 0.1 (repair) | 5.0% / 2.3% | 14 | 17 | 9 | 0 | 13 |
| deckA-band-seq-repair | band+repair seq | WH | 12 | 0.02 | pass | 0 | 0 τ | all (connected) | connected 5 | 421.2 | 2.1e-16 | 0.15 | 15.0% / 3.6% | 6 | 6 | 2 | 0 | 9 |
| deckA-band-seq-repair | band+repair seq | national | 13 | 0.02 | pass | 0 | 0 τ | all (connected) | connected 7, infeasible 2, optimal 1 | 1018.8 | 0.009 | 0.1 (repair) | 10.0% / 3.7% | 8 | 10 | 4 | 0 | 11 |
| g_na15_WH12_FI23-band-seq-repair | band+repair seq | FI | 23 | 0.02 | pass | 0 | 0 τ | all (connected) | connected 10, infeasible 3, optimal 1, unknown 2 | 2273.6 | 0.28 | 0.1 (repair) | 5.0% / 2.3% | 14 | 17 | 9 | 0 | 13 |
| g_na15_WH12_FI23-band-seq-repair | band+repair seq | WH | 12 | 0.02 | pass | 0 | 0 τ | all (connected) | connected 5 | 423 | 2.1e-16 | 0.15 | 15.0% / 3.6% | 6 | 6 | 2 | 0 | 9 |
| g_na15_WH12_FI23-band-seq-repair | band+repair seq | national | 15 | 0.025 | pass | 0 | 0 τ | all (connected) | connected 8 | 419.2 | 0.015 | 0.05 | 2.6% / 2.0% | 9 | 11 | 5 | 0 | 11 |
| ifa49-arm1-seq-repair-fast | arm1+repair seq | IFA | 49 | 0.02 | pass | 0 | 0 τ | all (connected) | connected 16, infeasible 12, optimal 6, unknown 4 | 1286.3 | 0.012 | 0.1 (repair) | 9.9% / 3.2% | 22 | 40 | 33 | 0 | 17 |
| s13_WH11-repair | arm1+repair seq | FI | 20 | 0.08 | pass | 0 | 0 τ | not all (unknown) | connected 5, unknown 2 | 258.3 | 2.1e-16 |  | 8.0% / 5.1% | 7 | 11 | 5 | 0 | 11 |
| s13_WH11-repair | arm1+repair seq | WH | 11 | 0.09 | pass | 0 | 0 τ | all (connected) | connected 3 | 9.6 | 0 | 0.09 | 8.9% / 5.1% | 3 | 3 | 0 | 0 | 8 |
| s13_WH11-repair | arm1+repair seq | WIFI | 3 | 0.1 | pass | 0 | 0 τ | all (connected) |  | 0 |  | 0.1 | 9.3% / 6.2% | 0 | 0 | 0 | 0 | 3 |
| s13_WH11-repair | arm1+repair seq | national | 15 | 0.0938 | pass | 0 | 0 τ | all (connected) | connected 3, optimal 1, unknown 1 | 216.2 | 0 | 0.1 (repair) | 10.0% / 7.4% | 4 | 7 | 6 | 0 | 11 |

**Review fixes** (Sol review 35e038f8). The window's band row had borrowed the sequential
realizer's clamp, under which a district already above the band takes nothing more instead of
making the window infeasible (a toy window next to a district fixed at 1.2 τ came back "optimal");
it now keeps the negative upper residual, and each attempt lists the districts outside the band
before and after. None of the runs above met that case: a window that used the clamp leaves its
district above the band, and every repaired channel ends at or inside ±10%. Before repairing,
`repair.py` now checks that the source's districts.csv lists the plan's copies under the ids, names
and supports its ledger was written with; the four candidate maps' sources pass with the plan files
they were repaired with (deck A and grid from `--plans-file`, s13 WH 11 from
`wh_dollar/_plans_11`, IFA 49 from `_plans`). The joint `band` remedy no longer stops at an
infeasible narrower band; the sequential runs above did not use that loop.

Regenerate (m5, local): `runs/exp/contig/launch.sh deckA ifa49` (joint and fixed-target arms),
`runs/exp/contig/launch_seq.sh <map> ...` (sequential arms), then `"$TD_PY"
tools/exp/contig/report.py runs/exp/contig/*/`. Specs are the stored TOMLs with `margin = false`
added per channel, in `runs/exp/contig/_specs/`; plans cache in `runs/exp/contig/_plans/`. Window
repair: `"$TD_PY" -u tools/exp/contig/repair.py runs/exp/contig/<run> --out
runs/exp/contig/<run>-repair --plans runs/exp/contig/_plans --flow --keep-support` (IFA with
`--time-limit 90 --max-zctas 1000`; a pre-connector drawing with `--plans-file
runs/exp/contig/_plans/<spec>_<extract>.pkl`, the cache entry without the connector key).

## #121 Border-length shape term and M1's necks (2026-10-05)

Measured 2026-10-05 on m5 with `tools/exp/contig/` at m5-studio/121 (border term 71517c8, final
neck rule 848e482). M1 is `td.audit.check_m1` under the owner's final neck rule (MANDATES.md M1,
"Area only", "One connected piece", "Land must be a real passage"): a district fails when one
connected part holding ≥ 5% of its land area reaches the rest only through < 10 km of shared ZCTA
border; an approved connector is width 0 only where land within the district's states would join
its sides through a passage itself ≥ 10 km wide (max flow on the polygon graph without
connectors, `NeckGraph.land_would_do`, exact to the millimetre and erring towards a neck), else
unlimited. Necks by mass are listed beside M1 and fail nothing.

The five tier-1 maps were redrawn by the arm-1 sequential realizer with the border term (the shared
ZCTA border between districts, the moment kept as a 1% tie-break), window repaired with
`--keep-support --flow` (pieces, then necks), and given a second repair pass of at most ~45 min per
map (`runs/exp/contig/border/repair2.sh`, one channel at a time). "Old" is the shortlist's current
tier-1 drawing; "border map" the best border folder. Scorer is `tools/looks/score.py` with the
current M1 (the folders' scorecard M1 rows predate the final rule).

| rank | id | old: pieces, necks | border map (`runs/exp/contig/border/`) | pieces (largest τ) | necks | mass necks | worst / mean dev | splits / cuts old → border | cut border km old → border | M1 | scorer |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ne_plains_wh11 | 0, 4 | `ne_plains_wh11-r2-all` | 0 | 0 | 13 | 9.3% / 5.2% | 14 / 21 → 14 / 21 | 47,930 → 37,557 | pass | ELIGIBLE |
| 2 | low6_cb1 | 0, 10 | `low6_cb1-r2-FI` | 0 | 6 | 19 | 10.0% / 2.8% | 29 / 34 → 29 / 34 | 88,553 → 53,322 | fail | M1 only |
| 3 | nocomb_13_12_23 | 0, 7 | `nocomb_13_12_23` | 3 (0.398) | 3 | 16 | 9.2% / 1.6% | 36 / 42 → 28 / 34 | 130,220 → 69,649 | fail | M1 only |
| 4 | nocomb_15_12_23 | 0, 5 | `nocomb_15_12_23-r2-national` | 0 | 3 | 11 | 9.8% / 2.3% | 38 / 43 → 29 / 34 | 102,270 → 66,362 | fail | M1 only |
| 5 | ifa_49 | 0, 18 | `ifa_49` | 7 (0.338) | 5 | 16 | 9.8% / 3.4% | 22 / 40 → 22 / 40 | 75,444 → 45,663 | fail | M1 only |

- Every old drawing fails M1 under the final rule, by necks alone (4 to 18 per map).
- The border term cuts the shared border between districts by 22% to 47% and never raises splits
  or cuts; on the two no-combined-channel maps it lowers them (36 → 28 and 38 → 29 splits).
- `ne_plains_wh11` passes M1 and is ELIGIBLE. Its last neck under the area rule, WH_09 (IN+KY)
  across the Ohio River bridges, cleared under "Land must be a real passage": the land route at
  Evansville is 4.4 km wide, so the bridges keep full width. `ne_plains_wh11-r2-all` is a re-audit
  of `ne_plains_wh11` (same ledger byte for byte) whose scorecard and manifest carry the final rule.
- The other four still fail inside the final band after the second pass. The neck windows'
  model carries no neck term, so most neck windows came back optimal or connected with the neck
  still there; the CT pieces of nocomb_15_12_23 were joined only through a thin Westchester strip
  (WH_05 1.24 km) and Long Island (national_08 8.82 km). Remaining pieces and necks, and the
  windows tried, are in `runs/autonomous_2026-10-05/batch_border/BATCH.md`; whether to relax
  anything is #112, the owner's decision.

Regenerate (m5, local): redraw `"$TD_PY" -u tools/exp/contig/run.py <spec> --arm arm1
--sequential --plans <cache> --out runs/exp/contig/border/<id>-draw`; repair `"$TD_PY" -u
tools/exp/contig/repair.py runs/exp/contig/border/<id>-draw --out runs/exp/contig/border/<id>
--keep-support --flow --h0 3 --max-zctas 1500 --time-limit 600 --neck-time-limit 120` (IFA:
`--max-zctas 1000 --time-limit 90 --neck-time-limit 90`); second pass `runs/exp/contig/border/repair2.sh`;
rescore `runs/exp/contig/border/rescore_final/rescore.py` (writes `TABLE.md`, `rescore.json`).
Each run folder's `manifest.json` holds its exact command and plan cache.

### Third pass: neck-aware window repair (2026-10-06)

Measured 2026-10-06 on m5 with `tools/exp/contig/repair.py` at m5-studio/121 (neck cuts ef03fc1,
`--budget` 0380ee5, `--diag-final-delta` ee6b68e). Every repair window now runs M1's exact neck
check on each drawing its solve-check-cut loop would keep; a neck whose side meets the window, in
a district the window is held to, adds a `draw.NeckCut`: the border across the side, counted where
both ends stay the district's, at least 10 km while two connected anchor sets (one in the side, one
in the rest) stay the district's and its land stays small enough for each to hold the 5% share.
The cut holds for every drawing in which the district has no neck (proof in `draw.NeckCut`;
checked by enumeration on a toy), so "optimal" is an optimum of the cut-augmented model and
"infeasible" proves that no drawing of the window, the rest fixed, is connected, inside the
scenario's declared ±10% final band and without a neck in the districts cut. The single-anchor
row x_j(a) + x_j(r) − 1 is not valid (a drawing keeping a tiny part of the side is not a neck),
hence the anchor sets and the area row. Districts with a neck on the map that the window is not
repairing are exempt. Runs: `runs/exp/contig/border/repair3.sh`, about 50 min per map, one channel
after another (`--h0 8 --max-zctas 2000 --time-limit 300 --neck-time-limit 240 --budget 1000`;
IFA `--h0 6 --time-limit 240 --neck-time-limit 180 --budget 3000`). Scorer as above, with its
thin links and small pieces (`rescore_final/rescore_r3.py`).

| rank | id | map (`runs/exp/contig/border/`) | pieces (largest τ) | necks | mass necks | worst / mean dev | splits / cuts | cut border km | thin / small | M1 | scorer |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ne_plains_wh11 | `ne_plains_wh11-r2-all` (unchanged) | 0 | 0 | 13 | 9.3% / 5.2% | 14 / 21 | 37,557 | 0 / 3 | pass | ELIGIBLE |
| 2 | low6_cb1 | `low6_cb1-r2-FI` → `low6_cb1-r3-national` | 0 | 6 → 4 | 19 → 17 | 10.0% / 2.9% | 29 / 34 | 53,322 → 53,001 | 3 / 19 → 2 / 19 | fail | M1 only |
| 3 | nocomb_13_12_23 | `nocomb_13_12_23-r3-FI` (drawing unchanged) | 3 (0.398) | 3 | 16 | 9.2% / 1.6% | 28 / 34 | 69,649 | 3 / 15 | fail | M1 only |
| 4 | nocomb_15_12_23 | `nocomb_15_12_23-r3-FI` (drawing unchanged) | 0 | 3 | 11 | 9.8% / 2.3% | 29 / 34 | 66,362 | 1 / 14 | fail | M1 only |
| 5 | ifa_49 | `ifa_49-r3-IFA` (drawing unchanged) | 7 (0.338) | 5 | 16 | 9.8% / 3.4% | 22 / 40 | 45,663 | 6 / 7 | fail | M1 only |

- The neck cuts removed two necks the border term had kept, low6_cb1's FI_08 (the NJ side of the
  Delaware Memorial Bridge) and FI_11 (GA+TN), each in its first window (ball h 8, |W| 494 and
  756, connected).
- Every other window that touched a remaining neck or piece was either proved infeasible inside
  the declared ±10% band for that window (corridors up to |W| ≈ 600, balls at h 5-8, the largest
  nocomb_13_12_23's national_08 ball of 1962 ZCTAs) or unknown at its 240-300 s limit (every other
  window of about 1000-2000 ZCTAs): unfinished, not shown infeasible for the map. Two necks, low6_cb1 FI_03 and ifa_49 IFA_19 (both UT 84621), lie in whole units of
  one holder, out of every arm-1 window's reach.
- ±15% diagnostic (never a deliverable; `<id>-r3-<channel>-diag15`, `--diag-final-delta 0.15`):
  no map draws neck-free; of the 44 windows infeasible at ±10%, 35 stay infeasible, 2 are unknown
  and 7 were not reached. Per-item windows, cuts and statuses, and the #112 list:
  `runs/autonomous_2026-10-05/batch_border/BATCH.md`.

Regenerate (m5, local): `runs/exp/contig/border/repair3.sh <id> <source folder> "<plans args>"
"<repair args>" <channel> ...` and `diag15.sh` (same arguments); rescore
`runs/exp/contig/border/rescore_final/rescore_r3.py` (writes `TABLE_r3.md`, `TABLE_diag15.md`).

### The cut-off part is the smaller side: rescore (2026-10-06)

Measured 2026-10-06 on m5 with `td.audit.district_necks` at m5-studio/121 c26ed48. Sol's review
of the neck check found that requiring the rest to be one connected piece holding ≥ 5% let a hub
of 6% of a district's land, with 24 lobes of 94/24 % each on 100 m threads, pass. The owner ruled
("Cut-off part = smaller side", MANDATES.md M1): a neck is one connected part with ≥ 5% of the
district's land and no more land than the rest, behind < 10 km of border; the rest may lie in
pieces of any size, and small fringes off a larger body never add together. The check now finds
the narrowest such part (the hub plus 11 lobes, 1.3 km, on the counterexample). Widths are
counted in whole centimetres, each border floored, so every cut is an integer and a neck is at
most 999,999 cm: 9.999999995 km is a neck, exactly 10 km is not. Flooring errs only towards a
neck (three borders of 3.333334 km, 10.000002 km in all, floor to 999,999 cm and are listed), and
on the shipped borders, rounded to the centimetre, the check is exact; only a time-out is listed
unresolved. A `--diag-final-delta` folder, or any folder derived from one, is marked
`"diagnostic": true`, INELIGIBLE and failed by M1's gate.

All 51 folders under `runs/exp/contig/border/` and `runs/exp/contig/replan/` were rescored
(`runs/exp/contig/border/rescore_0606/`, `TABLE.md`, `rescore.json`), "old" being the reviewed
neck rule (28706a9) in the same check:

- **No M1 verdict changed.** `ne_plains_wh11-r2-all` (and its source `ne_plains_wh11`) still
  passes M1 with 0 necks and stays ELIGIBLE, rank 1; every other folder failed and still fails.
- Neck counts rose in 30 of 51 folders, for example `ifa_49-r3-IFA` 5 → 10,
  `nocomb_13_12_23-r3-*` 3 → 5, `nocomb_15_12_23` 1 → 3, `low6_cb1-replan-ne5ut` 3 → 5; no
  search was unresolved, and the slowest whole-map M1 check took 36 s with scoring (6 s before).
- The ten `*-diag15` folders are backfilled `"diagnostic": true` ("backfilled") and score
  INELIGIBLE, reason "diagnostic band".

Regenerate (m5, local): `TD_REPO=... "$TD_PY" runs/exp/contig/border/rescore_0606/rescore.py`.

## #122 Re-plan the four failing maps: bans and opened units (2026-10-06)

Measured 2026-10-06 on m5 with `tools/exp/contig/` at m5-studio/122 (round 1 8fc44b7, round 2
74b98a3). Every row is judged with the landed M1 check (`tools/mandates/check.py`, #121's final
neck rule: the smaller side, widths in floored whole cm) and the looks scorer, inside each
scenario's declared ±10% final band; round 1's maps are rescored under it here.
`tools/exp/contig/replan.py` re-solves a scenario's master with `forbid_pairs` (unit pairs no
district may hold together) added to a copy of its TOML, at the declared δ. Every re-solve below
found a plan at its declared δ in every channel. `repair.py --open-units U` lets any window
district take ZCTAs of U even with `--keep-support`: an arm-2 split, one more allowed per unit. A
neck whose side lies in an opened unit is repaired first, and its first window is the district's
own ZCTAs in that unit (`own_window`, round 2).

"ne5" bans CT-NJ, MA-NJ, NJ-VT, CT-PA and MA-PA in every channel. The six-pair set with PA-VT
has no plan within final_delta 0.1 on nocomb_15_12_23. Round 2 (owner, "Add DE-NJ, rerun after
the #121 fix") adds DE-NJ, against the NJ end of the Delaware Memorial Bridge (08023, 5.67 km).
low6_cb1 FI also bans AZ-UT, so UT does not need its 84621 neck. Splits/cuts: the scorer's splits
and the state splits, from the #121 border map to the variant. $ is the scorer's per-channel $ per
district (M).

| id | variant | round | changes | pieces (τ) / necks | splits/cuts vs #121 border map | worst / mean | $ per district (M) | M1 | scorer |
|---|---|---|---|---|---|---|---|---|---|
| nocomb_15_12_23 | `-r3-FI` (#121 border map) | - | - | 0 (0) / 3 | 29/34 | 9.8% / 2.3% | FI 880, WH 928, national 1,169 | fail | M1 only |
| nocomb_15_12_23 | `-replan-a1` | 1 | arm-2 repair | 0 (0) / 3 | → 29/34 | 9.8% / 2.3% | same | fail | M1 only |
| nocomb_15_12_23 | `-replan-ne5-r2` | 1 | ne5, 2 repair passes | 2 (0.199) / 2 | → 28/34 | 9.9% / 1.8% | same | fail | M1 only |
| nocomb_15_12_23 | `-replan-ne5dn-r2` | 2 | ne5 + DE-NJ, 2 passes | 3 (0.375) / 4 | → 27/33 | 9.5% / 1.9% | same | fail | M1 only |
| nocomb_13_12_23 | `-r3-FI` (#121 border map) | - | - | 3 (0.398) / 5 | 28/34 | 9.2% / 1.6% | FI 880, WH 928, national 1,349 | fail | M1 only |
| nocomb_13_12_23 | `-replan-a1` | 1 | arm-2 repair | 3 (0.398) / 5 | → 28/34 | 9.2% / 1.6% | same | fail | M1 only |
| nocomb_13_12_23 | `-replan-ne5-r2` | 1 | ne5, 2 passes | 3 (0.176) / 3 | → 27/33 | 9.9% / 2.0% | same | fail | M1 only |
| nocomb_13_12_23 | `-replan-ne5dn-r2` | 2 | ne5 + DE-NJ, 2 passes | 2 (0.0868) / 1 | → 27/32 | 10.0% / 2.2% | same | fail | M1 only |
| low6_cb1 | `-r3-national` (#121 border map) | - | - | 0 (0) / 4 | 29/34 | 10.0% / 2.9% | FI 833, WH 916, WIFI 576, national 1,334 | fail | M1 only |
| low6_cb1 | `-replan-a1ut` | 1 | arm 1 + open UT (FI) | 0 (0) / 4 | → 29/34 | 10.0% / 2.9% | same | fail | M1 only |
| low6_cb1 | `-replan-ne5ut-r2` | 1 | ne5, FI AZ-UT, 2 passes | 2 (0.434) / 5 | → 26/32 | 8.1% / 2.0% | same | fail | M1 only |
| low6_cb1 | `-replan-ne5dnut-r2` | 2 | ne5 + DE-NJ, FI AZ-UT, 2 passes | 3 (0.397) / 5 | → 27/33 | 8.5% / 2.1% | same | fail | M1 only |
| ifa_49 | `-r3-IFA` (#121 border map) | - | - | 7 (0.338) / 10 | 22/40 | 9.8% / 3.4% | IFA 1,268 | fail | M1 only |
| ifa_49 | `-replan-a1ut` | 1 | arm 1 + open UT | 7 (0.338) / 10 | → 22/40 | 9.8% / 3.4% | same | fail | M1 only |
| ifa_49 | `-replan-ne5` | 1 | ne5 | 15 (0.355) / 17 | → 22/42 | 13.6% / 1.7% | same | fail (band too) | M1 only |
| ifa_49 | `-replan-a2ut` | 2 | arm 1 + open UT, IFA_19's own window first | 5 (0.267) / 6 | → 23/41 | 9.9% / 3.6% | same | fail | M1, mode compliance (the UT split) |

- **No map passes M1**, so the round-2 worker rendered no deck or ZIP pages; #120's renderer
  (`tools/maps/render.py`, 2026-10-06) later rendered and shortlisted four of them (the three
  `-ne5dn(ut)-r2` maps and `ifa_49-replan-a2ut`). The best by pieces and necks is
  `nocomb_13_12_23-replan-ne5dn-r2`. Everything it fails is in one district, national_08
  (DC+NC+NJ+PA+VA+WV): a DC piece of 85 ZIPs (0.0868 τ) and a WV piece of 738 ZIPs (0.0224 τ),
  both cut off by other districts, and a 0.17 km neck inside PA that cuts off the NJ side. None of
  these is a narrow state-pair crossing like the DE-NJ bridge, so no seventh pair is named; what to
  do about it is the owner's call.
- DE-NJ removed the Delaware Memorial Bridge neck, but on nocomb_15 and low6 DE moved into long
  districts (WH_07 DE+ME+NH+NY+PA+VT, national_10 DE+MD+NY+PA+VT, national_13). Those are cut off
  around Philadelphia and Baltimore (necks of 0.07-0.38 km, pieces up to 0.375 τ), so both maps
  are no better than round 1's ne5.
- ifa_49: the own UT window removed IFA_19's 84621 neck in its first try (299 ZCTAs, optimal,
  1.8 s), and neck windows also cleared three New York necks. 5 pieces and 6 necks remain in New
  York, New England, Maryland and west Texas.
- Round 1's maps keep their M1 failures under the landed rule. Their neck counts change: for
  example `ifa_49-r3-IFA` goes from 5 to 10 and `low6_cb1-replan-ne5ut` from 3 to 5.

Regenerate (m5, local): `runs/exp/contig/replan/chain.sh <id> <variant> <source spec> <pairs...>`
(`PARENT=`, `BUDGET=1500`), second pass `tools/exp/contig/repair.py <folder> --out <folder>-r2
--keep-support --flow --channels <failing> --h0 8 --max-zctas 2000 --time-limit 300
--neck-time-limit 300 --budget 1500`; ifa_49 `repair.py runs/exp/contig/border/ifa_49-r3-IFA
--keep-support --open-units UT --flow --h0 6 --max-zctas 2000 --time-limit 240 --neck-time-limit
180 --budget 7200`; table `TD_REPO=... "$TD_PY" runs/exp/contig/replan/rescore_r2.py` (writes
`TABLE_r2.md`, `rescore_r2.json`). Remaining items per map: `runs/autonomous_2026-10-05/batch_replan/BATCH.md`.

### Round 3: short split lists, round 2's bans dropped, then a widened planning band (2026-10-06)

Owner's picks: national, WH and low6's WIFI split only CA FL NY TX, FI also PA OH, and ifa_49's
IFA its 15 forced states (NY CA FL PA NJ TX MI OH IL MA CT MD MN WI VA). Every other state stays
whole, and round 2's six bans are dropped. low6 FI keeps AZ-UT (an orchestrator default). WIFI's
domain (ID MT ND NE SD WY) holds none of CA FL NY TX, so it stays all whole as before.
`replan.py --free CHANNEL=U1,...` replaces a channel's `free` in the copy; `run.py`'s and
`repair.py`'s manifest `plan` lists each channel's δ, final_delta, bans and `free`, and `run.json`
each channel's final_delta.

**Step 1, at the declared band: every map stops at the re-plan.** In each map some channel has no
master plan within final_delta 0.1 (margin = false). Smallest feasible δ (`td.master
.smallest_delta`, converged, rounded up to 1e-4 as `replan.py` does):

| id | binding channel(s): smallest δ | other channels: δ used |
|---|---|---|
| nocomb_13_12_23 | FI 0.1273 | national 0.0899, WH 0.0474 |
| nocomb_15_12_23 | FI 0.1273 | national 0.0774, WH 0.0474 |
| low6_cb1 | national 0.1071, FI 0.1174 (also 0.1174 without AZ-UT) | WH 0.0821, WIFI at its declared 0.02 |
| ifa_49 | IFA 0.3433 | - |

No whole state alone exceeds 1.1 τ (the largest are IFA NC 1.067 and low6 FI TN 1.079), so no
single oversized state causes this. Rounds 1 and 2 re-solved every channel at its declared δ
(0.02-0.033) with the longer lists.

**Step 2, the owner widened the planning band (2026-10-06): no map passes M1.** ifa_49 is out
(0.3433). `replan.py --widen C` sets C's final_delta to 0.15 (the owner's ±15% eligibility frame)
in the copy, so C plans at its smallest δ: nocomb FI, low6 national and FI. Every other channel
keeps final_delta 0.10 at its smallest δ within it. The folders are not diagnostic: M1's gate and
the scorer (its ±15% band and $ rule unchanged) judge them, and each run's own band check passes
(every district inside its channel's band). Pipeline as round 2: draw (arm 1, sequential, border
term), then `repair.py --flow --keep-support` at 1200 s per channel (`-w15`) and a second pass at
2400 s per channel (`-w15-r2`, the result; the `-w15` folder is its parent).

| id | variant | δ used (final band) | pieces (largest τ) / necks | splits / state splits / cut km vs #121 border map | worst / mean dev | $ per district (M), $ rule | M1 |
|---|---|---|---|---|---|---|---|
| nocomb_13_12_23 | `-replan-short-w15-r2` | national 0.0899, WH 0.0474 (±10%); FI 0.1273 (±15%) | 5 (0.416) / 4 | 28/34/69,649 → 11/18/67,168 | 12.7% / 5.1% | FI 880 (-2.3%), WH 928 (-7.2%), national 1,349 (+7.9%): all pass | fail |
| nocomb_15_12_23 | `-replan-short-w15-r2` | national 0.0774, WH 0.0474 (±10%); FI 0.1273 (±15%) | 3 (0.416) / 4 | 29/34/66,362 → 12/19/65,628 | 12.7% / 5.3% | FI 880 (-2.3%), WH 928 (-7.2%), national 1,169 (-6.5%): all pass | fail |
| low6_cb1 | `-replan-shortut-w15-r2` | WH 0.0821, WIFI 0.02 (±10%); national 0.1071, FI 0.1174 (±15%) | 4 (0.426) / 4 | 29/34/53,001 → 11/18/51,991 | 14.6% / 6.6% | FI 833 (-7.4%), WH 916 (-8.4%), national 1,334 (+6.7%): pass; WIFI 576 (no target) | fail |

- The short lists cut the splits by more than half (scorer splits 28-29 → 11-12) and the cut border
  by 1-4%. Mean deviation rises from 1.6-2.9% to 5.1-6.6%.
- Every failure is in the Northeast corridor. The largest piece is FI_06 (CT+DE+NY+PA) on both
  nocomb maps: 209 ZIPs from 17501, 0.416 τ. On low6 it is national_06
  (CT+DE+NY+PA+RI): 1,901 ZIPs from 15001, 0.426 τ. Necks include WH_11 0.08 km at 10036-10173
  (Manhattan) and FI_06 0.96 km at 17507-17517/17555.
- Of the 12 pieces left (5 + 3 + 4), 11 are left because their last window hit its time limit
  (unknown) and 1 (low6 national_06) because the budget ran out. The second pass removed one
  neck each on nocomb_13 and low6 and changed nothing on nocomb_15.
- The $ rule passes on every targeted channel of all three maps. $ per district is the channel total
  over K, so it equals the earlier runs' figures.
- Rendered with `tools/maps/render.py` and shortlisted at tier 3, FAILS M1. The legacy summary
  page's subtitle still reads "drawn band ±10%" for every channel, including the widened ones.

Regenerate (m5, local): `runs/exp/contig/replan/chain_r3.sh`, `repair_r3.sh`, `repair_r3b.sh`;
table `TD_REPO=... "$TD_PY" runs/exp/contig/replan/rescore_r3.py` → `rescore_r3.json`,
`TABLE_r3.md` (per-piece reasons, necks, split states per channel).

## #125 Overnight main-map set: the ne_plains layout at every $-eligible K (2026-10-07)

Measured 2026-10-07 on m5 with `tools/exp/contig/set125.sh` at m5-studio/125, autonomously (the
owner was away; the orchestrator steered). The layout, split lists, eta, max_size and distance caps
are `runs/exp/contig/wh_dollar/s13_WH11.toml`'s (ne_plains_wh11). Only K and, later, the split lists
vary. Every channel plans at the master's smallest δ (`replan.py`; each copy is declared at δ 0.02
and rounded up to 1e-4) within its final_delta 0.10. No channel is widened: on the orchestrator's
steer, WH 10 (planned at ±12.5%) is dropped, and a K with no plan at ±10% is recorded and skipped.
Pipeline: draw (`run.py --arm arm1 --sequential`, border term), then `repair.py --keep-support --flow
--h0 3 --max-zctas 1500 --time-limit 600 --neck-time-limit 120 --budget 1800` (`-r1`). Where M1
still fails, a second pass runs with `--h0 8 --max-zctas 2000 --time-limit 300 --neck-time-limit
240` (`-r2`), plus, on FI 19 only, a third FI pass with `--max-zctas 2500 --time-limit 900` (`-r3`).
Each final folder is gated (`tools/mandates/check.py`), scored (`tools/looks/score.py`) and rendered
(`tools/maps/render.py`).

**Which K plan at ±10%.** Smallest master δ per channel (`td.master.smallest_delta`, converged).
National, WH and FI are judged against their $ rule, WIFI has no target, and the main map's
total K must lie in 48-54.

| layout | channel | K: smallest δ | plans at ±10% |
|---|---|---|---|
| ne_plains | national | 13: 0.1054, 14: 0.1201, 15: 0.0888 | 15 only |
| ne_plains | WH | 11: 0.0879 | 11 |
| ne_plains | FI | 19: 0.0355, 20: 0.0494, 21: 0.1008, 22: 0.1352 | 19, 20 |
| ne_plains | WIFI | 2: 0.3657, 3: 0.0931, 4: 0.4574 | 3 only |
| ne6 (item 7: New England alone in WIFI, the plains in national, WH and FI; plains caps 1600 km) | WH | 11: 0.6470 at s13's max_size 4, 0.1353 at max_size 5 | none |

So issue items 1-5 have no plan at ±10% (national 13 or 14, FI 21 or 22), and item 7 has none at
WH 11 (national 14: 0.0934 and 15: 0.0518 do plan there). Two K sets remain:
na15/WH11/FI20/WIFI3 (the lead map's K at the smaller δ) and na15/WH11/FI19/WIFI3. On the
orchestrator's second steer, variety then came from shorter split lists on na15/WH11/FI20.
`tools/exp/split_floor.py` (±10%) forces splits in national CA TX NY FL, WH CA, and FI NY CA PA FL
OH, so the candidates are WH without NJ and FI without TN, NC or both. FI without both NC and TN
has no plan (smallest δ 0.1702).

| variant | K nat/WH/FI/WIFI | split lists | δ used nat/WH/FI/WIFI | $ per district (M) vs target | splits / state splits | cut km | defects (thin, small, crowded) | worst / mean dev | pieces (largest τ) / necks | M1 | scorer | tier |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ne_plains_wh11 (lead map, #121)` | 15/11/20/3 | s13_WH11 lists | 0.0938/0.09/0.08/0.1 | FI 925 (+2.8%), WH 922 (-7.8%), WIFI 1,123, national 1,126 (-9.9%) | 14 / 21 | 37,557 | 4 (0, 3, 1) | 9.3% / 5.2% | 0 (0) / 0 | pass | ELIGIBLE | tier 1 (owner) |
| `na15_wh11_fi20-r1` | 15/11/20/3 | s13_WH11 lists | 0.0888/0.0879/0.0494/0.0931 | FI 925 (+2.8%), WH 922 (-7.8%), WIFI 1,123, national 1,126 (-9.9%) | 13 / 20 | 39,189 | 1 (0, 1, 0) | 9.3% / 4.2% | 0 (0) / 0 | pass | ELIGIBLE | P 4 |
| `fi20_wh_nonj-r1` | 15/11/20/3 | WH without NJ | 0.0888/0.0879/0.0494/0.0931 | FI 925 (+2.8%), WH 922 (-7.8%), WIFI 1,123, national 1,126 (-9.9%) | 12 / 20 | 38,992 | 2 (0, 1, 1) | 9.3% / 4.2% | 0 (0) / 0 | pass | ELIGIBLE | P 1 |
| `fi20_fi_notn-r1` | 15/11/20/3 | FI without TN | 0.0888/0.0879/0.0494/0.0931 | FI 925 (+2.8%), WH 922 (-7.8%), WIFI 1,123, national 1,126 (-9.9%) | 13 / 20 | 38,049 | 1 (0, 1, 0) | 9.3% / 4.4% | 0 (0) / 0 | pass | ELIGIBLE | P 5 |
| `fi20_fi_nonc-r1` | 15/11/20/3 | FI without NC | 0.0888/0.0879/0.0494/0.0931 | FI 925 (+2.8%), WH 922 (-7.8%), WIFI 1,123, national 1,126 (-9.9%) | 13 / 19 | 37,780 | 2 (0, 2, 0) | 9.3% / 4.3% | 0 (0) / 0 | pass | ELIGIBLE | P 6 |
| `fi20_fi_notn_wh_nonj-r1` | 15/11/20/3 | FI without TN, WH without NJ | 0.0888/0.0879/0.0494/0.0931 | FI 925 (+2.8%), WH 922 (-7.8%), WIFI 1,123, national 1,126 (-9.9%) | 12 / 20 | 37,852 | 3 (0, 2, 1) | 9.3% / 4.4% | 0 (0) / 0 | pass | ELIGIBLE | P 2 |
| `fi20_fi_nonc_wh_nonj-r1` | 15/11/20/3 | FI without NC, WH without NJ | 0.0888/0.0879/0.0494/0.0931 | FI 925 (+2.8%), WH 922 (-7.8%), WIFI 1,123, national 1,126 (-9.9%) | 12 / 19 | 37,582 | 4 (0, 3, 1) | 9.3% / 4.3% | 0 (0) / 0 | pass | ELIGIBLE | P 3 |
| `na15_wh11_fi19-r3` | 15/11/19/3 | s13_WH11 lists | 0.0888/0.0879/0.0355/0.0931 | FI 974 (+8.2%), WH 922 (-7.8%), WIFI 1,123, national 1,126 (-9.9%) | 15 / 23 | 41,064 | 6.1042 (1, 3, 1) | 9.3% / 4.1% | 1 (0.104) / 0 | fail | INELIGIBLE (M1) | 3 |

- Every map that plans and is drawn at FI 20 passes M1 after one repair pass and is ELIGIBLE.
  These maps go in at tier P (pending owner review), not tier 1: tiers are the owner's call (OD3).
  Against the lead map (14 splits / 21 state splits, 4 defects, mean 5.2%), each has fewer splits,
  no more defects (1-4) and a lower mean deviation. Each has the same worst deviation, 9.3%, and a
  longer cut border (37,557 km → 37,582-39,189 km). Dropping NJ from WH's list
  takes off one split; dropping TN or NC from FI's takes off none (13 alone, 12 with WH without NJ).
- Tier P's ranks are the scorer's order over the six (`tools/looks/score.py` `rank`: splits, then
  defects, extent, states per district, worst and mean deviation): the three 12-split maps first
  (WH without NJ 2 defects, plus FI without TN 3, plus FI without NC 4), then the three 13-split
  maps (the s13_WH11 lists 1 defect and mean 4.2%, FI without TN 1 and 4.4%, FI without NC 2). The
  scorer flags the two 13-split, 1-defect maps REVIEW (+1 split for -1 defect).
- $ per district is the channel's total over K, so it is the same on every FI 20 map: national
  1,126M (-9.9%), WH 922M (-7.8%), FI 925M (+2.8%). FI 19 gives FI 974M (+8.2%). National 15 sits
  at the edge of the $ rule on every map.
- na15/WH11/FI19 fails M1 after three passes, on one piece: FI_07 (DE+NY+PA)'s DE, 68 ZIPs from
  19701, 0.104 τ. DE is whole, so the district must reach it through PA's Philadelphia ZIPs; every
  window was infeasible or hit its time limit (up to 900 s, 2,158 ZCTAs). It is at tier 3.
- The national drawing is the same in every variant (the same plan at δ 0.0888). Its NY unit hits
  its time limit with no incumbent (730 s), and repair joins the pieces.

Files (gitignored, m5): `runs/exp/contig/set125/`: `_specs/<id>{-base.toml,.toml,.json}` (the K
copy, the planned copy, the re-plan report), `<id>-{draw,r1,r2,r3}/`, `<id>-*.log`, `TABLE.md`,
`rescore.json`. Regenerate: `[FREE_WH=… FREE_FI=… LAYOUT=ne6|ne6m5] tools/exp/contig/set125.sh <id>
<K nat> <K WH> <K FI> <K WIFI> [--jobs N]`, `FROM=repair` to resume after a draw; the FI 19 third
pass is `repair.py <id>-r2 --out <id>-r3 --channels FI --keep-support --flow --h0 8 --max-zctas
2500 --time-limit 900 --neck-time-limit 240 --budget 2400 --jobs 3`; table `TD_REPO=… "$TD_PY"
runs/exp/contig/set125/rescore.py`.

## #124 Plan check: width-aware contact (A), drawable alone (B), close the loop (C) (2026-10-07)

Each map plans with A alone, then A+B, then A+B+C, using spec copies of #122 round 3's
(`replan/_specs/<id>-replan-short(ut)-w15.toml`: short split lists, the owner's widened bands,
low6 FI AZ-UT). ifa_49 had no round-3 run, so its copy is of round 2's spec (`_specs/ifa49.toml`,
the `ifa_49-replan-a2ut` lineage, 27 free states, δ 0.02). A is `contact_min_km = 10` (M1's W),
B is `drawable_alone` (a 600 s test per support, 120 s on ifa_49), and C is `replan_rounds = 3`.
Each map is drawn (arm 1, sequential, border term) and repaired (`repair.py --flow
--keep-support`, 1200 s per channel, 3600 s on ifa_49's one channel), once.
M1's constants and the bands are unchanged.

**No part changes any map.**
- A removes no support: every adjacent pair of planning units shares at least 10 km of
  land border. The only contacts that rest on a connector (DE-NJ, IL-KY, IN-KY) are connected
  through land anyway. Support families are unchanged: 3,903 per channel on the nocomb maps;
  1,991 / 1,991 / 1,975 / 47 on low6; 1,963 on ifa_49.
- B cuts nothing, so A+B's plans equal A's, and A+B reuses A's folder (`reuse.json`).
- C bans nothing, because no piece or neck the repair leaves has a last window proved infeasible:
  each one is "window unknown at its time limit" or "budget spent". So A+B+C stops at round 0
  on A's folder, and the C loop past round 0 has not run on a map.
- C's gate was off in these A+B+C runs: reusing A's folder as round 0 read A's `replan_rounds`
  of 0, not the copy's 3 (Sol's review, fixed after the runs). The outcome cannot change, since
  the cause table shows 0 proved-infeasible windows on every map, so nothing was there to ban;
  the maps were not rerun.
- C past round 0 is covered on toys only: bookkeeping tests, and one end-to-end test from round 0
  to round 1 (`test_c_bans_a_proved_infeasible_support_and_redraws_it_in_round_1`). In that
  test a real repair window proves a support infeasible, and C bans it, re-plans, redraws,
  repairs and records the ban's cost. Its plan, draw and repair steps run in process on the toy,
  not as the replan.py, run.py and repair.py CLIs.

The table is the same for A, A+B and A+B+C: one folder per map, `plancheck/<id>-pc-A`.

| map | supports cut (B tested / cut / unknown) | δ before → after | pieces (largest τ) | necks (district width) | splits / cuts / cut km | worst / mean dev | M1 | scorer |
|---|---|---|---|---|---|---|---|---|
| nocomb_13_12_23 | none; national 10/0/0, WH 11/0/0, FI 14/0/1 (CT+DE+NY+PA, no incumbent in 600 s) | national 0.0899, WH 0.0474, FI 0.1273 → same | 5 (0.398) | 5: FI_06 0.96 km, WH_11 0.64 and 0.08 km, national_04 8.81 km, national_08 1.11 km | 11 / 18 / 67,298 | 14.2% / 5.2% | fail | ineligible: M1 |
| nocomb_15_12_23 | none; national 10/0/0, WH 11/0/0, FI 14/0/1 (CT+DE+NY+PA, as above) | national 0.0774, WH 0.0474, FI 0.1273 → same | 3 (0.434) | 6: FI_06 0.78 km, WH_11 0.64 and 0.08 km, national_05 8.12 km, national_14 7.75 and 1.00 km | 12 / 19 / 65,800 | 12.7% / 5.2% | fail | ineligible: M1 |
| low6_cb1 | none; national 9/0/0, WH 11/0/0, FI 15/0/0, WIFI 1/0/0 | national 0.1071, WH 0.0821, FI 0.1174, WIFI 0.02 → same | 4 (0.426) | 5: FI_06 0.00 km, FI_08 5.67 km, WH_12 0.29 km, national_06 0.74 km, national_12 1.00 km | 11 / 18 / 52,036 | 12.9% / 6.6% | fail | ineligible: M1 |
| ifa_49 | none; IFA 19/0/7 (FL+GA, CT+NJ+NY, IA+IL+WI, CT+NY+RI+VT, IL+IN+MI+OH, DC+DE+MD+NJ+PA, ID+MT+UT+WA+WY at 120 s) | IFA 0.02 → same | 7 (0.338) | 14: IFA_38 four (0.00-3.45 km), IFA_11 0.05 km, IFA_07 0.61 km and eight more of 2.36-8.00 km | 21 / 40 / 45,550 | 9.9% / 3.1% | fail | ineligible: M1 |

Splits are the scorer's count of split states, and cuts are the extra district holders per state.
Every map's deviations are inside its own bands (the widened ±15% on nocomb FI and low6
national and FI, ±10% elsewhere).

What each piece and neck left traces to (`plancheck.causes`). "Budget spent" means the repair's
log shows a window on that district that was never tried. Otherwise the cause is the last window's
status.

| map | pieces: unknown / budget / infeasible | necks: unknown / budget / infeasible | where |
|---|---|---|---|
| nocomb_13_12_23 | 2 / 3 / 0 | 1 / 4 / 0 | FI CT+DE+NY+PA (205 ZIPs from 17039, 0.398 τ: unknown after 5 infeasible windows); WH NJ+NY+VT; national CT+NJ+NY, DE+MD+NY+OH+PA, CA |
| nocomb_15_12_23 | 2 / 1 / 0 | 1 / 5 / 0 | FI CT+DE+NY+PA (250 ZIPs, 0.434 τ); WH NJ+NY+VT; national MA+NJ+NY, CA |
| low6_cb1 | 2 / 2 / 0 | 0 / 5 / 0 | national CT+DE+NY+PA+RI (1,901 ZIPs, 0.426 τ, budget), MA+ME+NH+NJ+NY+VT, NY; WH NJ+NY+VT; FI CT+NY, DE+NJ+PA |
| ifa_49 | 0 / 7 / 0 | 0 / 14 / 0 | NY#3 (9 infeasible and 5 unknown windows, then budget), CT+NY+RI+VT, and necks across NY, NJ, DC-PA, NC-VA, UT, MI, TX, CA |

- Against #122's `-w15` folders (same plans, same 1200 s budget, before #122's review fixes to
  repair.py), the redrawn maps differ only in the repair. Pieces are 5 / 3 / 4 (unchanged).
  Necks are 5 / 6 / 5, against 5 / 4 / 5.
- ifa_49 is worse than `ifa_49-replan-a2ut` (5 pieces, 6 necks), whose repair opened UT and ran
  7200 s. This run opens no unit and spends its 3600 s before reaching most necks.
- Every failure but the CA, UT, MI, TX and NC necks is in the Northeast corridor. These are the
  districts #124's Goal names (CT+DE+NY+PA#1, CT+NJ+NY#1). B finds them drawable or unknown,
  so it cannot cut them, and C cannot ban them, since no window was proved infeasible.
- Rendered with `tools/maps/render.py` (ifa_49 `--corridor`) and shortlisted at tier 3, FAILS M1
  (`<id>_pc_a`). `tools/mandates/check.py --tracking`: 147 run folders, 32 entries, 0 failures.
- MODEL §4.9's Proposition B is proved (Sol verifier 8b0ddc7f, 2026-10-07).

Regenerate (m5, local, `runs/exp/contig/plancheck/`): copies `plan.sh <id> <base> <A|AB>`; draw,
repair and C `loop.sh <id>-pc-<A|ABC> _specs/<id>-pc-<A|ABC>.toml <parent> <budget> [--planned
_specs/<id>-pc-A.json | --round0 <id>-pc-A --check-time 600]`; table `TD_REPO=... "$TD_PY"
rescore_pc.py --code <checkout>` → `rescore_pc.json`; per-round records `<id>-pc-<v>-plancheck.json`.

## #126 An IFA map that passes M1 and the $ rule (2026-10-07)

Measured 2026-10-07 on m5 with `tools/exp/contig/` at m5-studio/126 (main 5b4a2fb; the two
`-azut` K 46 and K 52 repairs after merging #123, ee800d8, with `--jobs 3`). Drawn and judged
autonomously under the owner's overnight grant; M1 constants, the ±10% final band and the
$ target ($1.25B ±10% per district) are unchanged. Every row is judged with the landed M1 gate
(`tools/mandates/check.py`) and the looks scorer. All re-plans use `ifa49.toml`'s own free list
(27 states) in copies under `runs/exp/contig/ifa126/_specs/`, and every one found a plan at the
declared δ 0.02. Approaches: (1) a longer window repair (2 h) of the #121 border map and of
#122's a2ut, no opened unit; (2) re-plan at K 46, 47 and 52, border draw, 1.5 h repair;
(3) ban AZ-UT, at K 49 and, after (2), at K 46 and 52 (45 min repair, `--jobs 3`). Splits / cuts:
the scorer's split states / each state's districts beyond its first. Causes left: per remaining
piece and neck, "budget" when a window of it was not tried for lack of budget, else its last
window's status ("infeasible" proves no drawing of that window, the rest fixed, inside the band;
"unknown" hit its time limit).

| approach | folder | change | K | $ per district (M) | splits / cuts | cut border km | thin / small | worst / mean dev | pieces (largest τ) / necks | causes left | M1 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| - | `border/ifa_49` | #121 border map | 49 | 1,268 | 22 / 40 | 45,663 | 6 / 7 | 9.8% / 3.4% | 7 (0.338) / 10 | - | fail | M1: fail |
| - | `replan/ifa_49-replan-a2ut` | #122 a2ut (open UT) | 49 | 1,268 | 23 / 41 | 44,583 | 4 / 9 | 9.9% / 3.6% | 5 (0.267) / 6 | - | fail | audit: mode compliance fails; M1: fail |
| 1 | `ifa126/ifa_49-long` | repair border/ifa_49, 2 h, no opened unit | 49 | 1,268 | 22 / 40 | 45,220 | 6 / 7 | 9.8% / 3.4% | 4 (0.338) / 7 | 7 neck budget, 4 piece unknown | fail | M1: fail |
| 1 | `ifa126/ifa_49-a2ut-long` | repair a2ut, 2 h, no opened unit | 49 | 1,268 | 23 / 41 | 43,941 | 4 / 9 | 9.7% / 3.6% | 3 (0.267) / 4 | 4 neck budget, 3 piece unknown | fail | audit: mode compliance fails; M1: fail |
| 2 | `ifa126/ifa_46-replan` | K 46, ifa49 free list | 46 | 1,351 | 21 / 38 | 44,685 | 3 / 10 | 10.0% / 2.6% | 2 (0.285) / 4 | 2 neck infeasible, 2 neck unknown, 2 piece infeasible | fail | M1: fail |
| 2 | `ifa126/ifa_47-replan` | K 47, ifa49 free list | 47 | 1,322 | 23 / 44 | 45,153 | 6 / 14 | 9.5% / 2.7% | 8 (0.459) / 13 | 13 neck budget, 5 piece budget, 3 piece unknown | fail | M1: fail |
| 2 | `ifa126/ifa_52-replan` | K 52, ifa49 free list | 52 | 1,195 | 23 / 47 | 51,960 | 5 / 15 | 9.2% / 2.9% | 3 (0.179) / 9 | 9 neck budget, 3 piece unknown | fail | M1: fail |
| 3 | `ifa126/ifa_49-azut` | K 49, AZ-UT banned | 49 | 1,268 | 21 / 43 | 46,796 | 8 / 9 | 9.4% / 2.4% | 17 (0.479) / 17 | 17 neck budget, 5 piece budget, 11 piece infeasible, 1 piece unknown | fail | M1: fail |
| 2+3 | `ifa126/ifa_46-azut` | K 46, AZ-UT banned, repair --jobs 3, 45 min | 46 | 1,351 | 22 / 40 | 42,811 | 5 / 13 | 11.4% / 2.9% | 3 (0.37) / 5 | 4 neck budget, 1 neck infeasible, 3 piece infeasible | fail | M1: fail |
| 2+3 | `ifa126/ifa_52-azut` | K 52, AZ-UT banned, repair --jobs 3, 45 min | 52 | 1,195 | 23 / 45 | 51,880 | 5 / 12 | 10.0% / 3.1% | 3 (0.474) / 8 | 8 neck budget, 3 piece unknown | fail | M1: fail |

- **No IFA map passes M1**, so none goes in at tier P; all eight attempts are rendered and
  shortlisted at tier 3 (`ifa_*_126*`, ranks 30-37). The fewest failures is `ifa_46_126`
  (`ifa126/ifa_46-replan`): 2 pieces and 4 necks, $1.351B per district (+8.1%), 21 splits,
  worst / mean 10.0% / 2.6%. Its pieces are a Bronx piece of IFA_10 (30 ZIPs from 10464) and a
  PA piece of IFA_39 (367 ZIPs from 16901), both with windows proved infeasible; its necks are
  CT (06069, 5.26 km), the Delaware Memorial Bridge (08023, 5.67 km), UT (84621, 5.48 km) and
  west TX (79734, 6.14 km).
- **The AZ-UT ban does not touch IFA's UT neck.** In every IFA plan here, with or without the
  ban, all of UT sits whole in ID+MT+UT+WA+WY (no IFA district holds AZ and UT together), so the
  ban only reshuffles other supports, and the neck stays: southeast UT (96 ZIPs from 84511)
  reaches the rest of the state only through 84621's 5.48 km of border (84621-84652 4.19 km,
  84621-84654 1.29 km). Only an opened UT (a2ut) removed it, and that split is not on the free
  list, so the audit's mode compliance fails. At K 49 the ban made the drawing worse (17 pieces,
  17 necks).
- Necks that recur on most attempts: UT 84621, west TX 79718-79734 (6.14 km, IFA's west TX
  district), the NJ end of the Delaware Memorial Bridge (08023), and Long Island / Fishers Island
  (06390, 11947). Most causes left on the longer runs are budget (necks not reached) or unknown;
  infeasible windows are the minority.
- `ifa_46-azut` leaves one district at 11.4%, outside the declared ±10% final band (scorecard
  "final bands on drawn mass" fails); the scorer's ±15% band does not flag it.
- The longer repair moved the K 49 maps a little (border map 7 pieces / 10 necks → 4 / 7; a2ut
  5 / 6 → 3 / 4) and nothing more within 2 h.

Regenerate (m5, local): `runs/exp/contig/ifa126/chain.sh <variant> <spec> <parent> <budget>
<replan args>` (`REPAIR_EXTRA="--jobs 3"` for the `-azut` K 46 and 52), `repair_long.sh <variant>
<source run> 7200`; table `TD_REPO=... "$TD_PY" runs/exp/contig/ifa126/rescore.py` →
`rescore.json`, `TABLE.md`. Each folder's `manifest.json` holds its exact command and parent.

### Round 2: UT on IFA's free list (2026-10-07)

Measured 2026-10-07 on m5 at m5-studio/126 (main 15c8550 merged after the runs). The orchestrator,
under the owner's overnight grant, added UT to IFA's free list: a labelled scenario change that
allows one more split state, not a threshold change; the M1 constants, the ±10% final band and the
$ target are unchanged. Approach 2b: `replan.py --free IFA=<ifa49's 27 states>,UT` at K 46, 49 and
52 (each found a plan at the declared δ 0.02, and each splits UT: 3, 2 and 3 districts), border draw
(`run.py --sequential --jobs 1`), a 1 h repair with `--jobs 4`, then a second 1 h repair of each
(every first pass left budget or unknown causes). Columns as above; round 1's best map is the first
row for comparison.

| approach | folder | change | K | $ per district (M) | splits / cuts | cut border km | thin / small | worst / mean dev | pieces (largest τ) / necks | causes left | M1 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2b | `ifa126/ifa_46-ut` | K 46, ifa49 free list + UT (+1 split state), repair 1 h --jobs 4 | 46 | 1,351 | 22 / 39 | 46,431 | 4 / 10 | 9.9% / 3.2% | 1 (0.214) / 3 | 2 neck budget, 1 neck unknown, 1 piece unknown | fail | ineligible: M1: fail |
| 2b | `ifa126/ifa_46-ut-r2` | K 46, ifa49 free list + UT (+1 split state), second 1 h repair | 46 | 1,351 | 22 / 39 | 46,431 | 4 / 10 | 9.9% / 3.2% | 1 (0.214) / 3 | 1 neck infeasible, 2 neck unknown, 1 piece unknown | fail | ineligible: M1: fail |
| 2b | `ifa126/ifa_49-ut` | K 49, ifa49 free list + UT (+1 split state), repair 1 h --jobs 4 | 49 | 1,268 | 21 / 41 | 45,583 | 7 / 9 | 9.9% / 2.4% | 9 (0.338) / 11 | 11 neck budget, 5 piece budget, 4 piece unknown | fail | ineligible: M1: fail |
| 2b | `ifa126/ifa_49-ut-r2` | K 49, ifa49 free list + UT (+1 split state), second 1 h repair | 49 | 1,268 | 21 / 41 | 44,713 | 7 / 10 | 9.9% / 2.7% | 6 (0.338) / 7 | 7 neck budget, 6 piece unknown | fail | ineligible: M1: fail |
| 2b | `ifa126/ifa_52-ut` | K 52, ifa49 free list + UT (+1 split state), repair 1 h --jobs 4 | 52 | 1,195 | 20 / 45 | 49,881 | 4 / 14 | 7.4% / 2.0% | 4 (0.262) / 11 | 11 neck budget, 4 piece unknown | fail | ineligible: M1: fail |
| 2b | `ifa126/ifa_52-ut-r2` | K 52, ifa49 free list + UT (+1 split state), second 1 h repair | 52 | 1,195 | 20 / 44 | 47,980 | 4 / 13 | 9.4% / 2.4% | 3 (0.118) / 5 | 2 neck budget, 3 neck unknown, 3 piece unknown | fail | ineligible: M1: fail |

- **No round-2 map passes M1**, so none goes in at tier P; the three final maps (`-r2`) are rendered
  and shortlisted at tier 3 (`ifa_46_126_ut`, `ifa_49_126_ut`, `ifa_52_126_ut`, ranks 38-40).
- **Opening UT removes the UT neck at every K.** No round-2 map has a neck or piece in UT. The cost
  is one more split state (K 46: 21 → 22 splits against `ifa_46-replan`).
- **The closest map is `ifa_46_126_ut`** (`ifa126/ifa_46-ut-r2`): 1 piece and 3 necks, against
  round 1's 2 and 4. $1.351B per district (+8.1%), 22 splits, worst / mean 9.9% / 3.2%. Left: a
  PA piece of IFA_39 (NY+PA#1, 208 ZIPs from 16925, 0.214 τ, window unknown), CT (IFA_10,
  06069, 1.90 km, unknown), the Delaware Memorial Bridge (IFA_12, 08023, infeasible in every
  window) and west TX (IFA_44, 79734, unknown). The second pass changed nothing on this map.
- **Delaware Memorial Bridge (08023).** K 46: IFA_12 has support DE+MD+NJ#1 and no PA; its NJ part
  (229 ZIPs from 07751, Monmouth / Ocean, 63% of its mass) meets DE only across the bridge
  (08023-08069 3.34 km, 08023-08070 2.33 km) and otherwise borders NJ#2 (191 km), PA#1 (106 km)
  and NJ#1 (68 km); the second pass proved every window around it infeasible. K 52: IFA_14 has
  support DE+NJ#1; the hanging part is DE (68 ZIPs and 08023), which borders MD#1 (190 km) and
  DC+MD+PA+VA+WV#1 (39 km). The plan change that avoids it: no support that holds DE and NJ without
  PA (DE goes with MD or PA, and NJ's districts hold NJ, or NJ with PA); a support containing DE,
  NJ and PA can join them through Philadelphia. K 49's IFA_13 (DC+DE+MD+NJ+PA#1) holds PA and has
  no bridge neck, but a different one: its 116 ZIPs from 08002 (64 PA, 52 NJ) hang on
  19013-19022 (2.24 km).
- **West TX (79718-79734).** At every K the district is TX#2 (San Antonio; IFA_44, 47, 49): its 44
  Trans-Pecos ZIPs from 79734 reach the rest of the district only through 79718-79734 (6.14 km),
  and their one other neighbour district is the NM district (AZ+CO+NM#1 at K 46 and 49, CO+NM#1 at
  K 52), across 228 km of border. The plan change that avoids it: give the NM district a support
  that includes TX (TX is already free, so no new split state), so these ZIPs can join it; within
  TX#2 alone the windows ended unknown or unreached.
- K 49 and 52 keep more failures (6 pieces / 7 necks and 3 / 5), mostly in the NY-CT-NJ and
  Great Lakes supports, with causes unknown or budget.

Regenerate (m5, local): `runs/exp/contig/ifa126/chain2.sh <variant> <spec> runs/exp/contig/border/ifa_49
3600 --free IFA=AZ,CA,CO,CT,FL,GA,IA,IL,IN,KS,LA,MA,MD,MI,MN,MO,NC,NJ,NY,OH,PA,SC,TN,TX,UT,VA,WA,WI`
(specs `ifa126/_specs/ifa_46.toml`, `_specs/ifa49.toml`, `ifa126/_specs/ifa_52.toml`), then
`repair2.sh <variant> 3600`; table `TD_REPO=... "$TD_PY" runs/exp/contig/ifa126/rescore.py --round 2`
→ `rescore2.json`, `TABLE2.md`.

### Round 3: exact support bans at K 46 (2026-10-07)

Measured 2026-10-07 on m5 at m5-studio/126 (main 99220a8, nothing new on main since). The
orchestrator, under the owner's overnight grant, had round 2's two plan changes tested at K 46 from
`ifa_46-ut`'s spec copy (UT free). Both are scenario choices made with #124's `ban_supports` (exact
supports, n_S = 0), not state-pair bans; the M1 constants, the ±10% final band and the $ target are
unchanged. The bans are enumerated from the family the master builds for that copy (1,963 supports):

- **3a `ifa_46-ut-dnj`**, "support ban: DE+NJ without PA (round-2 windows proved infeasible)": the 65
  supports holding DE and NJ but not PA (from DE+NJ and DE+MD+NJ to CT+DC+DE+MD+NJ+NY; the list is
  in `ifa126/_specs/ifa_46-ut-dnj.bans.json` and the copy's `ban_supports`).
- **3b `ifa_46-ut-dnj-tx`**: the same 65 plus the 16 supports holding NM but not TX (81 in all), so
  the NM district must hold TX. Banning only the NM district's own support (AZ+CO+NM) is not enough:
  the master moves NM to AZ+CO+NM+UT, still without TX. The family has 7 supports with NM and TX
  (NM+TX, NM+OK+TX, CO+NM+TX, ...); no code change was needed.

Both plans are optimal at the declared δ 0.02 (objective 10,434 km in round 2; 10,462 for 3a;
10,696 for 3b). 3a puts DE in DC+DE+MD+NJ+PA#1 and keeps the NM district at AZ+CO+NM#1; 3b puts DE
in DE+MD+NJ+PA#1 and NM in NM+OK+TX#1. Each was drawn (`run.py --sequential --jobs 1`) and repaired
twice for 1 h with `--jobs 4` (every first pass left unknown or budget causes). Columns as above;
round 2's best map is the first row for comparison.

| approach | folder | change | K | $ per district (M) | splits / cuts | cut border km | thin / small | worst / mean dev | pieces (largest τ) / necks | causes left | M1 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2b | `ifa126/ifa_46-ut-r2` | round 2 best: K 46, ifa49 free list + UT (+1 split state) | 46 | 1,351 | 22 / 39 | 46,431 | 4 / 10 | 9.9% / 3.2% | 1 (0.214) / 3 | 1 neck infeasible, 2 neck unknown, 1 piece unknown | fail | ineligible: M1: fail |
| 3a | `ifa126/ifa_46-ut-dnj` | K 46, UT free, support ban: DE+NJ without PA (round-2 windows proved infeasible), 65 supports, repair 1 h --jobs 4 | 46 | 1,351 | 22 / 40 | 45,952 | 2 / 12 | 9.9% / 3.3% | 3 (0.311) / 5 | 5 neck budget, 3 piece unknown | fail | ineligible: M1: fail |
| 3a | `ifa126/ifa_46-ut-dnj-r2` | K 46, UT free, support ban: DE+NJ without PA (round-2 windows proved infeasible), 65 supports, second 1 h repair | 46 | 1,351 | 22 / 40 | 46,016 | 2 / 12 | 10.0% / 3.7% | 2 (0.311) / 4 | 1 neck infeasible, 3 neck unknown, 2 piece unknown | fail | ineligible: M1: fail |
| 3b | `ifa126/ifa_46-ut-dnj-tx` | K 46, UT free, support ban: DE+NJ without PA (round-2 windows proved infeasible), 65 supports + support ban: NM without TX (NM district must hold TX), 16 supports, repair 1 h --jobs 4 | 46 | 1,351 | 21 / 41 | 47,876 | 4 / 14 | 8.9% / 3.0% | 2 (0.29) / 1 | 1 neck unknown, 2 piece unknown | fail | ineligible: M1: fail |
| 3b | `ifa126/ifa_46-ut-dnj-tx-r2` | K 46, UT free, support ban: DE+NJ without PA (round-2 windows proved infeasible), 65 supports + support ban: NM without TX (NM district must hold TX), 16 supports, second 1 h repair | 46 | 1,351 | 21 / 41 | 47,876 | 4 / 14 | 8.9% / 3.0% | 2 (0.29) / 1 | 1 neck unknown, 2 piece unknown | fail | ineligible: M1: fail |

- **No round-3 map passes M1**, so none goes in at tier P; the two final maps (`-r2`) are rendered
  (`--corridor`) and shortlisted at tier 3 (`ifa_46_126_dnj` rank 41, `ifa_46_126_dnjtx` rank 42).
- **The Delaware Memorial Bridge neck is gone in both.** With DE and NJ held only together with PA,
  neither map has a piece or neck at 08023; round 2's PA piece of IFA_39 (NY+PA#1) is gone too.
- **Giving the NM district TX removes the west TX neck.** 3b's IFA_36 (NM+OK+TX#1) takes the
  Trans-Pecos ZIPs; 3a, which keeps AZ+CO+NM#1, still has round 2's neck in TX#2 (IFA_44, 79734,
  cut 79718-79734 6.14 km, unknown).
- **The closest map is `ifa_46_126_dnjtx`** (`ifa126/ifa_46-ut-dnj-tx-r2`): 2 pieces and 1 neck, all
  in the New York metro, against round 2's 1 and 3. $1.351B per district, 21 splits (one fewer
  than round 2), worst / mean 8.9% / 3.0%. Left, all with windows ended unknown (the second pass
  changed nothing):
  - IFA_10 (CT+MA+NJ+NY+RI#1): a piece of 21 ZIPs from 07421 (north NJ, 0.29 τ) and a piece of 25
    ZIPs from 10001 (Manhattan, 0.242 τ), both cut off by other districts;
  - IFA_11 (CT+NY#1): a neck 0.90 km wide (11361-11362, Queens) that cuts off 110 ZIPs from 10017,
    35.1% of its mass.
- **`ifa_46_126_dnj`** (`ifa126/ifa_46-ut-dnj-r2`): 2 pieces and 4 necks. Left: IFA_26
  (MA+NJ+NY+RI#1) pieces from 10001 (37 ZIPs, 0.311 τ) and 07430 (15 ZIPs, 0.29 τ), unknown;
  IFA_10 (CT+NY#1) neck at 11547-11579 (1.65 km, 86 ZIPs from 06320), unknown; IFA_11
  (DC+DE+MD+NJ+PA#1) neck at 21402-21403 (1.10 km, 158 ZIPs from 20001), unknown; IFA_36 (NY#1)
  neck at 11702-11706 / 11702-11795 (6.17 km, 34 ZIPs from 11705), infeasible; IFA_44 (TX#2) west
  TX, unknown. Its worst district is 10.0%.
- What remains at K 46 is the New York metro: supports that join NJ, NYC and New England
  (CT+MA+NJ+NY+RI, MA+NJ+NY+RI) leave Manhattan and north-NJ pieces cut off by the NY and CT+NY
  districts.

Regenerate (m5, local; run from a checkout, scripts in `$TD_REPO/runs/exp/contig/ifa126/`):
`"$TD_PY" mkspec3.py ifa_46-ut-dnj` (and `mkspec3.py ifa_46-ut-dnj-tx "$("$TD_PY"
nm_without_tx.py)" "<label>"`) writes `_specs/<variant>.in.toml`, a copy of `_specs/ifa_46-ut.toml`
with the `ban_supports` line enumerated from the family; then `chain3.sh <variant> <that copy>
runs/exp/contig/border/ifa_49 3600 --keep` and `repair2.sh <variant> 3600`; table `TD_REPO=...
"$TD_PY" rescore.py --round 3` → `rescore3.json`, `TABLE3.md`.
