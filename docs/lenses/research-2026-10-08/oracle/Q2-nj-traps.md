# Q2 — NJ pilot traps

1. **Keep two graph variables.** `run.py:164–165` loads polygon then builds without `graph=`. Pass induced graph only to `spec.build`; retain full polygon for `write_folder` → `output.audit_run` (`run.py:429–431`). Do not monkeypatch `geo.polygon_graph`. `draw.draw` uses instance adjacency (`draw.py:270`), not a fresh global graph.

2. **Preserve graph metadata.** `spec.py:599` sets `inst.polygon` only if supplied graph contains `border`. Induce vertices, edges, borders, connectors, states and areas consistently; exclude connector edges with either endpoint outside NJ. Full audit context still retains them. Assert 598 shipped vertices, not extract-row count.

3. **Custom-graph behavior differs.** `spec.py:598` enables `stop_disconnected_whole` for caller graphs. Set NJ splittable. Trim out-of-domain mode lists; spec parsing precedes graph construction. Do not accidentally revive the earlier domain-partition error.

4. **Zero-dollar area:** `spec.py:590–592` constructs planning land only for extract-present vertices. Preserve all shipped vertices and full audit land areas; do not infer neck areas from that truncated planning dictionary.

5. **Singleton support must allow multiplicity.** `max_size=1` alone does not force three districts: verify master returns three NJ copies, NJ free, no conflicting contact cap. Inspect `solver.json` before drawing.

6. **Budget/cache/fallback:** cache key lacks regional vertex identity (`run.py:108–113`); disable cache. `--time-limit` is not necessarily whole-pipeline wall time. Undrawn output invokes fallback (`run.py:198–202`); never report fallback as successful connected optimization.

7. **Balance:** `draw.py:273–275` uses tau, not E2. NJ K3 gives approximate dollar window $1,006–1,362M at delta .15, inside E2; verify full-precision rates frozen from full extract. Do not renormalize subset rates.

LEARNED: Regional scoping must preserve metadata and bypass unscoped plan caches.
DECIDED: Prioritize assertions and reuse; no audit changes.
