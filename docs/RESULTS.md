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

Draft (lane B of #81, 2026-10-02): the support-diameter arm is measured; the Hess arm, the
comparison and the verdict are filled in when the arms join. Scenario: the 2026-10-01 "18-split"
stakeholder candidate (`A_fi1600_v1_na16_WH12_FI24`: no WIFI, national 16 / WH 12 / FI 24, all
49 units on the national list, 1,600 km mountain/plains cap, CA contact cap 4) on
`instance_descaled.json.gz`. Both arms replicate the looks driver's caveats: the rounding margin
is off (in memory), ZIP 13027's FI cell (m_rel 1.6e-8) is zeroed at load (#73's workaround), and
deviations are in m_rel, the audit's measure.

**Arms.**
1. Support diameter: the support master (`docs/MODEL.md` §3, objective Σ_S w_S n_S, w_S the
   largest unit-centroid distance in S) and the ZIP realizer (§7). Reference run
   `runs/sweep/looks_2026-10-01/stage2/A_fi1600_v1_na16_WH12_FI24/` (m5, local); a re-run on
   2026-10-02 at `9583135` reproduced its ledger, `districts.csv` and scorecard byte for byte.
2. Hess: TBD.

**Measures** (`tools/exp81/measure.py`; every one is read from the drawn ledger, so both
objectives are scored on the same final map, each in its own unit and never normalised against
the other). Per channel c, with drawn mass m_j the ledger's m_rel over district j's cells and
τ = (c's ledger total) / K_c:
- *Balance*: deviation m_j / τ − 1; compliance is the audit's final band τ(1 ± final_delta),
  final_delta = 0.10.
- *Support diameter* Σ_j w(S_j), S_j the units where j holds positive m_rel, w the master's
  diameter (km). On arm 1 it equals the master's objective: the drawn supports are the planned ones.
- *Hess* Σ_j Σ_{z∈j} M_z ‖p_z − c_j‖², p_z the ZIP's 2025 gazetteer point in EPSG:5070 (km),
  M_z its m_rel in c, c_j the M-weighted centroid of j's ZIPs; m_rel·km², shown in 10⁶. Per
  district, rms = √(Hess_j / m_j), km.
- *Extent*: the largest distance between two ZIP points a district holds, any mass, km.
- *Contacts* Σ_j |S_j|, and *split units*, units with two or more districts of positive mass.
- *Pieces*: the audit's ZIP contiguity on the declared graph (components beyond the heaviest).
  "Bridged" is a lower bound: the pieces left if every graph vertex with no cell in c could link
  any district, which removes the pieces the run labels "connector ZIP not in ledger".
- *Solver*: `solver.json` (and the Hess arm's `hess_solver.json`); the support master's size is
  rebuilt from the spec (`master.build`, before presolve).

| measure | national: diameter | national: Hess | WH: diameter | WH: Hess | FI: diameter | FI: Hess |
|---|---|---|---|---|---|---|
| final audit verdict | pass | TBD | pass | TBD | pass | TBD |
| within ±10% | 16/16 | TBD | 12/12 | TBD | 24/24 | TBD |
| worst deviation | 9.56% | TBD | 8.30% | TBD | 9.54% | TBD |
| support diameter, km | 10,246 | TBD | 8,758 | TBD | 11,882 | TBD |
| Hess, 10⁶ m_rel·km² | 1,109 | TBD | 1,008 | TBD | 1,303 | TBD |
| max district rms, km | 488 | TBD | 552 | TBD | 558 | TBD |
| max extent, km | 1,790 | TBD | 1,694 | TBD | 2,023 | TBD |
| max support diameter, km | 1,498 | TBD | 1,360 | TBD | 1,399 | TBD |
| contacts | 56 | TBD | 54 | TBD | 61 | TBD |
| max units per district | 5 | TBD | 6 | TBD | 4 | TBD |
| split units | 5 | TBD | 5 | TBD | 8 | TBD |
| districts in pieces | 16 | TBD | 12 | TBD | 10 | TBD |
| pieces (bridged) | 292 (1) | TBD | 600 (0) | TBD | 38 (2) | TBD |
| solver status, gap | optimal, 0 | TBD | optimal, 0 | TBD | optimal, 0 | TBD |
| master time, s | 0.45 | TBD | 7.55 | TBD | 0.05 | TBD |
| model: supports / columns (integer) / rows / nonzeros | 2,421 / 12,724 (2,421) / 38,865 / 124,018 | TBD | 4,152 / 24,841 (4,152) / 70,280 / 234,838 | TBD | 1,143 / 5,056 (1,143) / 14,747 / 47,785 | TBD |

Arm 1's split units: national CA FL NJ NY TX, WH CA NJ NY OH PA, FI CA FL NC NJ NY OH PA TX. Master
times are the reference run's; the re-run took 0.53, 9.86 and 0.07 s, 11.5 s for all three
masters with their support families, 0.11 s for the three realizers and 60 s end to end with the
audit and maps.

**Why the maps differ.** TBD at the join.

**Where the objectives disagree.** TBD at the join; arm 1's candidates:
- *Wholly inside a split unit* (diameter 0): national_04 and national_05 are both CA-only, with
  rms 197 and 57 km; national_11 FL, WH_08 FL, and FI_10 FL, FI_20 and FI_21 NY, FI_22 OH,
  FI_23 PA, FI_24 TN.
- *Long support, opportunity near its centre* (lowest rms per km of diameter): national_15
  MA+ME+NH+NY+RI (566 km, rms 109), WH_07 DE+NJ+PA (261, 59), FI_09 DE+NJ+PA (261, 61).
- *Compact ZIP-level result with more administrative fragmentation*: TBD.
- *Support-level gain the realizer cannot turn into a compact map*: TBD.

**Runtime and model size.** TBD at the join, against the arm-1 rows above.

Side-by-side maps: TBD (`docs/figures/`). Regenerate (m5, local inputs):

```
"$TD_PY" tools/exp81/measure.py <run_dir> --out runs/exp81/<arm>_measures.json
"$TD_PY" tools/exp81/sidebyside.py <arm1_run_dir> <hess_run_dir> --out <dir> --labels "support diameter" "Hess"
```
