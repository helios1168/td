# The #66 sparse fixture and v3 loader (td#66)

**Context.** td#66 adds `td/data.py`, which does three things: it loads exporter v3's `td_instance_descaled/3` extract (`mem:decisions/exporter-v3-2026-09-28`), applies the CONUS rule, and builds a seeded sparse fixture. That fixture stands in for the extract until the extract arrives. The worker made seven choices on m5 on 2026-09-29 (m5 session 01a0ee38, fork 01a0ee3a). The owner explicitly approved the first two, the mass law and the acceptance bands, before landing (#66 [comment 5901932600](https://github.com/helios1168/td/issues/66#issuecomment-5901932600), 2026-09-30T00:55Z). In the same comment the owner approved extending #66's Files to `docs/CODE_MAP.md` for the two new rows. Choices 3 to 7 are the worker's implementation choices, filed as recorded and not approved by the owner as policy. #66 merged into td `main` at `2949cb0` on 2026-09-29. Acceptance there was 51 passed, 0 failed and 0 skipped, with the state polygons present. The curator checked each choice against `td/data.py` and `tests/test_data.py` at `2949cb0`. The measurements are in `mem:facts/sparse-fixture`.

**Decisions.**
1. **Lognormal masses, sigma 1.285 (owner-approved).** Each fixture cell's mass is lognormal with sigma `FIXTURE_SIGMA` = 1.285 and is independent of the ZIP's population. Masses are scaled so the median cell is 1. With this sigma, mean/median is exp(σ²/2) = 2.28, the v2 CONUS ratio (M 8,481.81 over 3,713 ZIPs with median 1, `mem:facts/instance-versions`).
2. **Acceptance bands (owner-approved).** The ZIP count must be 3,900–4,100, Gini 0.58–0.70, top-10% share 0.44–0.58 and top-1% share 0.10–0.22 (`ZIP_RANGE`, `GINI_BAND`, `TOP10_BAND`, `TOP1_BAND` in `tests/test_data.py`). `test_population_and_uniform_masses_fall_outside_the_bands` checks that population-weighted and uniform masses fail them.
3. **A vanished cell drops its ZIP (worker's choice).** A sampled ZIP whose state-clipped Voronoi cell vanishes is not a vertex. It is listed in `graph["missing"]` and removed from the fixture's extract, so the fixture's ZIPs equal the graph's explicit vertex list (trap 21). `test_fixture_drops_a_zip_whose_cell_vanishes` covers this on a small made-up map.
4. **Graph tests skip without the state polygons (worker's choice).** When `tl_2025_us_state.zip` is in neither `data/public` nor `$TD_REPO/data/public`, `tests/test_data.py` prints one SKIP line to stderr and its graph tests return early. The other tests still run.
5. **One cell per ZIP per channel, no rep book (worker's choice).** Every sampled ZIP gets a cell in every channel, with `share` `{}` and `share_free` 0.
6. **The CONUS rule has two drop reasons (worker's choice).** `conus` keeps a ZIP only if it is a row of `reference/2025/zcta_reference.csv.gz` with a state. It counts drops as "not a CONUS ZCTA" or "no state", with ZIP count, cell count and `m_rel_share` per reason, and never lists ZIPs.
7. **Channel order comes from the file (worker's choice).** The loader takes the channel order from `meta["channels"]`. If that is absent, it uses first appearance in the node table.

**Alternatives rejected.**
1. Pareto masses or population-proportional masses. The only real shape figure on file is the mean/median ratio, and the fixture must avoid population-proportional masses.
2. Wider bands. They would let population-weighted masses pass (Gini 0.545, top-10% share 0.41, `mem:facts/sparse-fixture`).
3. Keeping a vanished-cell ZIP as a massed non-vertex. The fixture's ZIPs would then differ from its explicit vertex list (trap 21).
4. A synthetic-only or network-fetching graph test. The vertex rule has to be checked on real 2025 state polygons, and tests must not need the network.
5. Sparse channel coverage or synthetic reps. The master reads only masses, and staffing is out of scope.
6. Separate AK and HI reasons. The reference holds no AK or HI rows, so telling them apart would mean guessing from ZIP prefixes.
7. Reading `channels.json`. The instance file carries the channel list itself.

**Consequences.** A graph test that skips still counts as passed in `tests/run_all.py` (`mem:facts/tooling-traps`), so the SKIP line on stderr is the only sign it did not run. Acceptance on the lander should confirm the state polygons are present, as #66's acceptance did. The fixture has no rep book, so it cannot exercise anything that reads shares. Its channels all share the same ZIP set, so it cannot exercise sparse channel coverage either. The bands and sigma are the fixture's contract: changing either changes what a fixture-based measurement means, so it goes back to the owner.

**Status.** Settled for the fixture and loader, landed in `2949cb0` (2026-09-29). Choices 1 and 2 are owner-approved. Choices 3 to 7 stand as the worker's implementation choices until an issue revisits them.
