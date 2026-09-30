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
