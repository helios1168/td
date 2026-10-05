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
  repair below makes s13, deck A and grid na15/WH12/FI23 pass.
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
each district's drawn mass in the channel's final band (±10%, the band the audit judges), the
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
| `deckA-band-seq-repair` (arm 1, flow) | deck A band-seq, approved list | national piece (2,019, 0.154 τ) → corridor 1 47 optimal 0.6; FI CT + 07844 (0.448 τ) → ball 3 409 infeasible, ball 6 767 unknown (600), corridor 2 164 optimal 5.9 | **pass** / fail (WH bands, from the source) | unchanged: national 10.0%, WH 15.0%, FI 5.0% | 8/10, 6/6, 14/17 unchanged |
| `g_na15_WH12_FI23-band-seq-repair` (arm 1, flow) | grid band-seq, approved list | FI as deck A's | **pass** / fail (WH bands, from the source) | unchanged: national 2.6%, WH 15.0%, FI 5.0% | 9/11, 6/6, 14/17 unchanged |
IFA_ROW

- **s13, deck A and grid na15/WH12/FI23 each have an M1-passing map whose audit passes**:
  `s13-arm1-seq-repair` and `s13-band-seq-repair`, `deckA-band-seq-pre-repair` and
  `g_na15_WH12_FI23-arm1-seq-pre-repair-ks`. In none does a planned share vanish ("planned
  against drawn owners" lists nothing new) or a split or cut rise; the cost is balance inside the final
  band, not the plan's δ (deck A's internal δ was 0.05 already, the `band` remedy). Deck A's and
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
  proved optimal); the infeasible ones were proved in under 30 s each. U63 (districts resting on one connector) is in each passing folder's contig.json.

Regenerate (m5, local): `runs/exp/contig/launch.sh deckA ifa49` (joint and fixed-target arms),
`runs/exp/contig/launch_seq.sh <map> ...` (sequential arms), then `"$TD_PY"
tools/exp/contig/report.py runs/exp/contig/*/`. Specs are the stored TOMLs with `margin = false`
added per channel, in `runs/exp/contig/_specs/`; plans cache in `runs/exp/contig/_plans/`.
