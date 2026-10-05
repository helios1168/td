# Mandates

The register of td's hard requirements (#107). Only the owner adds, changes or waives a row;
agents propose. No step may weaken, relabel or work around a mandate without an owner-decision
issue. A row is never deleted, and a cleanup, archive or clean slate carries every row and every
return trigger forward (`docs/problem/PROBLEM.md`, 2026-10-05).

Each row is a `##` section with these fields, all required:

- **status:** `hard`, `deferred` or `waived`, nothing else.
- **owner's words:** what the owner said, with the date and the source.
- **definition:** the requirement, precise enough to check.
- **check:** the executable check that fails a map or a run on a violation. A check not yet
  written says which issue builds it.
- **latest value:** the check's value on the best map; `not measured` until a check has run.
- **waiver history:** every time the row was set aside or restored, with date and source.
- **return trigger:** `none` for a `hard` row. A `deferred` or `waived` row names a test,
  `tests/test_mandates.py::trigger_<name>`, that holds once the reason for setting the mandate
  aside is gone; the suite then fails until the owner restores the mandate or renews the waiver.

`tests/test_mandates.py` parses this file and fails on a missing field, a status outside the
three, a deferred or waived row without a trigger test, or a trigger that holds.

## M1: ZIP contiguity

- **status:** hard
- **owner's words:** owner, 2026-10-04, answers recorded in
  `runs/plan_2026-10-04/contiguity/MANDATE.md` §1 (m5, gitignored) and restated in #107.
  Graph: "the drawn 2025 TIGER ZCTA polygons. A district is connected when it looks connected
  on the map." Adjacency: rook, "a shared boundary of positive length; a single touching point
  does not count." Water: "crossings count only through a committed connector list (bridges,
  tunnels, ferries) that the owner reviews once." Coverage: "zero-opportunity ZIPs are
  territory. Every CONUS ZCTA gets a district in every channel, and the ledger, not a display
  fill, assigns it." Tolerance: "none. Any detached piece beyond the connectors fails the map."
- **definition:** in every planning channel of every map, each district's ZCTAs form one
  connected component of the graph whose vertices are all CONUS ZCTAs of the 2025 TIGER ZCTA
  polygons and whose edges are rook adjacency (a shared boundary of positive length; a shared
  corner does not count; a shared boundary shorter than the scorer's thin-link threshold counts
  as connected and stays a looks defect), plus the committed connector list across water, which
  the owner reviews once. Every CONUS ZCTA is assigned by the ledger, zero-opportunity ZIPs
  included. No tolerance: one detached piece fails the map, and listing it is not enough. The
  model plans and draws on this same polygon graph (OD2, `docs/problem/PROBLEM.md`).
  Multipart ZCTAs (owner, 2026-10-05, ruling relayed on #108; 1,429 of the 33,300 are
  MultiPolygons): one ZCTA is one vertex and its own parts always count as connected to each
  other; two ZCTAs are adjacent through a shared positive-length boundary of any of their parts.
  A separate piece on a district's drawn union that only a multipart ZCTA makes is a visual
  defect for the scorer to list, not an M1 failure.
- **check:** the polygon contiguity check `td/audit.py::check_m1` (#108), run by every td run
  on the extract, and its run-folder gate `tools/mandates/check.py::m1`, which the looks scorer's
  eligibility also applies; pinned by
  `tests/test_mandates.py::test_m1_fails_each_broken_fixture_and_passes_the_connected_one` on the
  broken fixtures in tests/fixtures/m1/.
- **latest value:** 75 of 75 drawn runs fail (2026-10-05, `tools/mandates/check.py --rescore`,
  #108). Best map, the scorer's rank 1:
  `sweep/comb_2026-10-02/stage2/ne_okks_forced_balance_na15_WH12_FI20_CB3`, M1 fail, largest
  detached piece 0.385 τ (WH/WH_07, 857 ZIPs in MI) after display fill; strictly on the ledger 2726
  detached pieces and 123242 channel ZCTAs with no owner. Smallest largest piece across runs: 0.297
  τ (WH/WH_05, 288 ZIPs in CT), `sweep/must_2026-10-01/stage2/R_na16b8_WH12_FI24_TN+NC_b10_e15`.
- **waiver history:**
  - 2026-09-01, set aside "for simplicity" (`d50bd42`) as the PROBLEM.md row "Adjacency
    contiguity is not required | settled | 2026-09-01 | user | 547 components. Reopenable only
    by the full-ZCTA-graph experiment." No trigger test.
  - 2026-09-28, the reopen condition was met (#62 built the ZIP graph over all 33,300 CONUS
    ZCTAs) and not acted on; the same day the #54 clean slate (`ce9f282`) archived the row in
    `archive/pre-support-2026-09`.
  - 2026-10-04, restored as hard by the owner, on the polygon graph.
- **return trigger:** none

## Masking: sales and names stay in the extract

- **status:** hard
- **owner's words:** owner, 2026-09-30 and 2026-10-01, `AGENTS.md` (`f98b9a3`): "sales,
  wholesaler (rep) names and firm names never enter this repo, an issue, a memory or anything
  online."
- **definition:** sales, the per-rep shares (`share`, `share_free`), the `firm` map, and rep and
  firm names never leave the extract: not into the repo, an issue, a memory or anything online.
  The exporter writes surrogate ids (`R…`, `F…`) and no currency amount, the model does not read
  the shares or the firm map, and `instance_descaled*.json.gz` is gitignored. Descaled
  opportunity, dollar opportunity and everything the model makes from them are not masked.
- **check:** `tests/test_export_instance.py::test_rep_books_stay_with_surrogate_ids_ranked_by_total_book`,
  `tests/test_export_instance.py::test_guard_refuses_an_unstripped_scale_a_currency_amount_or_a_negative_mass`
  and `.gitignore`.
- **latest value:** not measured.
- **waiver history:** none. Narrowed by the owner on 2026-09-30 from "confidential" to masking,
  and on 2026-10-01 to let dollar opportunity appear.
- **return trigger:** none
