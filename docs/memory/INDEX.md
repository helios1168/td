# Memory index

One line per memory: name, then what it holds. Read the ones an issue's `## Read first` names before starting.
Memory is written only through the curator (the `memory-curator` agent, run by the lander); every other agent ends its report with `LEARNED:` lines.

td#55 pruned memory to what applies to the support master. The last version of every removed memory is at `740a985`, and all of them but `workflow/docs-and-state`'s td#54 correction are also at the tag `archive/pre-support-2026-09`; a `mem:` link to a removed memory resolves there.

## facts (settled numbers, with dates and conditions)
- `facts/instance-versions`: v1 against v2 table, CONUS ground set (3,713 zips, tau 471.21), v3 and pending v4, masked firm shares
- `facts/state-border-snapping`: Track 1 and Track 2 grids of 2026-09-07 on the whole v2 instance
- `facts/conus-track2-grid`: the CONUS re-run at δ 5, 7, 10%; the band is always overshot after rounding
- `facts/refactor-archive-and-queue`: the tag `archive/pre-support-2026-09` at 1251534 (pre-A2), milestones M0–M5 as 5–10 with the 26 plan issues, old milestones 1–4 (td#53); 77 tracked files after #54, memory to at most 37 for A3's cap of 60, 38 tracked with 15 in memory after #55
- `facts/highs-traps`: evidence for AGENTS.md traps 12, 14, 18, 19: mip_rel_gap default, Solve error and the highs-ds pin, process-global threads, keep the objective
- `facts/tooling-traps`: evidence for AGENTS.md traps 15, 16: retries keyed on the engine's stop reason, Serena resolves against the hub; `tests/run_all.py` counts an early-returning test as PASS (td#66); m5 has no `tl_2025_us_state.zip`, so its graph tests skip (td#78); `$TD_PY`/`$TD_REPO` unset in m5 worktree shells, the stale 24-test count; 2026-10-02: m5 now has the state and ZCTA zips, `TD_PY`/`TD_REPO` and the bash tool, pyproj changing the graph, Python 3.12 compatibility, the history-free bundle, presentation-map tooling; `TD_REPO` before `run_all.py` on m5 and `sys.path` in `tools/<sub>/` scripts (td#81 runs)
- `facts/portability`: 2026-10-02: Python 3.10's `tomllib`, Snowflake's Anaconda channel (GEOS 3.10.6, highspy 1.13.1), a run's footprint, Windows cp1252 and wheels, the cross-platform reference ledger
- `facts/geography-traps`: evidence for AGENTS.md traps 21, 22, 23: explicit vertex set, 2020 against 2025 vintage shifts, ZCTA against Voronoi edges (23 settled by #57)
- `facts/zcta-2025-land-and-graph`: td#62 (landed eb4b09a) measurements: FACES land overlay within 9.1e-05 of ALAND on all 33,300 CONUS ZCTAs, seven counties on the AREAWATER fallback, the all-CONUS stand-in graph's 98,941 edges and one CA island
- `facts/sparse-fixture`: td#66's seed-0 fixture: 4,000 vertices, 11,695 rook edges, none missing, 49 connected states, ~3.2 s on m5; population Gini 0.545 among the drawn ZCTAs and 0.68 over all 33,300, fixture masses Gini 0.628
- `facts/v3-extract-loading`: the real v3 extract's 5 placeholder-ZIP cells failed load at c5be768; since td#78 the loader passes any string id and CONUS counts the drop; the m2 and m5 extract copies differ; exporter v3 needs a channel column, takes the pre-v3 combined file, the first real run's counts (2026-09-29); per-channel sparsity in v3 and v4 and the retracted `has_commercial_opportunity` reading
- `facts/support-code-2026-09-30`: the landed #65–#72 code: zero-opportunity drop, master's η cap row, `ETA_MIN`, decode revalidation and gap reporting, the audit's exact allowance, realize's normalized transport, output's path guards and ledger columns, the exporter filler guard
- `facts/scenario-sweeps-2026-10`: the 51 on the fresh extract (sizes, margin on/off δ, drawing drift, real-run defects), channel shape, the owner's dollar totals and K, the 900 km cap and WIFI, the 18-split looks map, forced splits, the combined New England channel; the NE + okks 13-split map, FI's eastern shapes, the Philadelphia metro carve, the map shortlist

## solver
- `solver/highs-and-scipy`: highs-ds pin, python3 -u, level-1 portfolio engine and sizes, level-0 sizes

## geo
- `geo/zip-adjacency`: shattered zip graphs (v1, v2, real ZCTA), state rook graph, why proximity stays Voronoi
- `geo/zcta-geometry`: real ZCTA polygons at 250 m, 2025 gazetteer default, the 2020 pin, district_reach

## decisions (user decisions that are settled)
- `decisions/support-refactor-2026-09-25`: the td#52 decisions S1–S31 and its 26 §7 issues; scope cut, clean slate, unit modes, 2025 geography, contiguity within tolerance, ownership S25 to S28, forest rounding; STATE.md shape Now/Next/Blocked ≤ 1 KB, v2 loader test removed until #66, exact requirement pins (td#54); five memories kept beyond A3's keep list, dangling `mem:` links left (td#55)
- `decisions/open-decisions-2026-09-28`: OD1 (td#56): symmetric δ_c = 10% declared per planning channel, planning tightened by μ_S, repair and drawn audit on the final band with 1e-9 × τ_c slack, CA/TX/NY/FL band breaks retired, smallest master δ never auto-adopted; OD2 (td#57): the Voronoi rook graph of 2025 points over placed extract ZIPs, explicit vertices, DC–VA only, missing-ZIP reports; OD3 (td#58): district-only outputs, three certificate tiers (exact, bounded, feasible only), no numeric successor to CERT_TOL/EPS_CERT; OD5 (td#60): scenario-listed 2025 metro CBSAs, whole if M^c ≤ U_c else own splittable unit, S14 keeps the unit, the integer-n feasibility condition
- `decisions/exporter-v3-2026-09-28`: td#61's autonomous-queue exporter policy: channel-less extract as `national`, any channel label normalised with `channels.json`, one κ over all channels, `--rep-ids` behind `--rep-ids-channel`, no geometry exported, format 3 only with synthetic seven-channel tests; `/channels.json` gitignored at the hub root only (2026-09-30)
- `decisions/zcta-2025-build`: td#62's build choices: FACES land with a named AREAWATER fallback for seven counties, DC–VA kept as rook when already adjacent, county population over ZIP-covered land, CBSA/CSA/METDIV from the primary county
- `decisions/sparse-fixture-and-loader`: td#66: lognormal sigma 1.285 and the ZIP-count/Gini/top-10%/top-1% bands (owner-approved); the worker's choices: vanished cell drops its ZIP, graph tests SKIP without state polygons, one cell per ZIP per channel with no rep book, two CONUS drop reasons, channel order from `meta`
- `decisions/loader-non-zip-ids`: td#3 option (a), landed as td#78: non-ZIP string ids load and drop in the CONUS rule, counted; only the 5-digit check was relaxed, while non-string ids and the other checks are still refused; exporter-side or file-only drops rejected
- `decisions/channels-and-scenarios-2026-09-29`: owner, td#67/td#76: purity per unit, fallback only relabels cells, a scenario is one TOML spec with non-overlapping planning channels, channel combining downstream of the exporter; how to judge a combination open on td#76
- `decisions/model-md-2026-09-29`: td#64's MODEL.md choices: U36/U38 left open with form only, only `lenstra1990` cited and `verified` from the CWI report, R_c(u,v), Menger row C9 optional, repair guard on every touched unit, dated UNKNOWNS notes
- `decisions/support-code-2026-09-30`: workers' calls building #65–#72 (highspy direct, residual handling, η cap on every unit, bisection bracket, gap agreement in objective units, transport normalization, naming and path guards, filler-guard allowlist) and the reviewer findings carried into code
- `decisions/scenario-sweeps-2026-10`: local diagnostic workarounds, sweep compute across both Studios, dollar conversion, grid and stage-2 shape, the Gromov council's format, the BALANCE.md brief, the 2026-10-02 stakeholder maps; the 1.1-district strict list, east-shape ranking, the Philadelphia-only carve, shortlist tiers, the council triage close-out
- `decisions/work-environment-2026-10`: running td at work: ML Jobs, then a stored procedure on the PyPI mirror over Anaconda, then `PYTHONUTF8=1` on Windows with the bundle unchanged
- `decisions/issue-queue-reset-2026-09-28`: 50 legacy issues closed "not planned", `archived` on the 39 only, old milestones and labels left alone (td#53)

## workflow
- `workflow/confidential-data`: descaled export only; shares and raw M never together; no per-record values anywhere; exporter v3 at `export/` writes format 3 and `channels.json`, no edges or states (td#61); 2026-10-01: masking only, dollar opportunity allowed in the public repo
