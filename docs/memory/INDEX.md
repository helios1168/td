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
- `facts/tooling-traps`: evidence for AGENTS.md traps 15, 16: retries keyed on the engine's stop reason, Serena resolves against the hub
- `facts/geography-traps`: evidence for AGENTS.md traps 21, 22, 23: explicit vertex set, 2020 against 2025 vintage shifts, ZCTA against Voronoi edges (23 settled by #57)
- `facts/zcta-2025-land-and-graph`: td#62 (not landed) measurements: FACES land overlay within 9.1e-05 of ALAND on all 33,300 CONUS ZCTAs, the all-CONUS stand-in graph's 98,941 edges and one CA island

## solver
- `solver/highs-and-scipy`: highs-ds pin, python3 -u, level-1 portfolio engine and sizes, level-0 sizes

## geo
- `geo/zip-adjacency`: shattered zip graphs (v1, v2, real ZCTA), state rook graph, why proximity stays Voronoi
- `geo/zcta-geometry`: real ZCTA polygons at 250 m, 2025 gazetteer default, the 2020 pin, district_reach

## decisions (user decisions that are settled)
- `decisions/support-refactor-2026-09-25`: the td#52 decisions S1–S31 and its 26 §7 issues; scope cut, clean slate, unit modes, 2025 geography, contiguity within tolerance, ownership S25 to S28, forest rounding; STATE.md shape Now/Next/Blocked ≤ 1 KB, v2 loader test removed until #66, exact requirement pins (td#54); five memories kept beyond A3's keep list, dangling `mem:` links left (td#55)
- `decisions/open-decisions-2026-09-28`: OD1 (td#56): symmetric δ_c = 10% declared per planning channel, planning tightened by μ_S, repair and drawn audit on the final band with 1e-9 × τ_c slack, CA/TX/NY/FL band breaks retired, smallest master δ never auto-adopted; OD2 (td#57): the Voronoi rook graph of 2025 points over placed extract ZIPs, explicit vertices, DC–VA only, missing-ZIP reports; OD3 (td#58): district-only outputs, three certificate tiers (exact, bounded, feasible only), no numeric successor to CERT_TOL/EPS_CERT; OD5 (td#60): scenario-listed 2025 metro CBSAs, whole if M^c ≤ U_c else own splittable unit, S14 keeps the unit, the integer-n feasibility condition
- `decisions/exporter-v3-2026-09-28`: td#61's autonomous-queue exporter policy: channel-less extract as `national`, any channel label normalised with `channels.json`, one κ over all channels, `--rep-ids` behind `--rep-ids-channel`, no geometry exported, format 3 only with synthetic seven-channel tests
- `decisions/issue-queue-reset-2026-09-28`: 50 legacy issues closed "not planned", `archived` on the 39 only, old milestones and labels left alone (td#53)

## workflow
- `workflow/confidential-data`: descaled export only; shares and raw M never together; no per-record values anywhere; exporter v3 at `export/` writes format 3 and `channels.json`, no edges or states (td#61)
