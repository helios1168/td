# State-atom exploration (2026-09-05)

**The engine is in the package now.** The algorithm this directory prototyped lives in
`td/atoms.py` (the atoms) and `td/solvers/atom_draw.py` (the draw), and is run by
`tools/run_atoms.py`. `district4.py` was deleted when they landed: two copies of a search whose
exact numbers matter would drift.

What is left here is exploratory, still outside the pipeline, still uncovered by tests, and
still needs `sys.path` and instance paths edited before it runs.

Run from the repo root with the root `.venv`, and set `PYTHONHASHSEED=0` — set iteration order
otherwise moves results by roughly 0.015 nats.

| file | what it does |
|---|---|
| `partition2.py` | granularity alone, contiguity dropped: three split rules (inherit / equal / whole) against the balanced ceiling. The source of `110.883135` and `107.011866` |
| `atoms.py` | per-state opportunity, zip-graph component health, how the delivered zip draw fragments states |
| `nynj.py` | whether the delivered draw already fuses NY and NJ, and the NY+NJ+CT arithmetic |
| `firms.py` | masked firm labels, book split, per-zip firm dominance |
| `build_map.py` + `state-atoms.tpl.html` | generates artifact `7902dfb3-afc6-431e-ac2c-ceb109662780`, splicing the firm-territory SVG into the template |

`build_map.py` writes to a path under a job scratch directory that no longer exists; point
`TPL`/`OUT` at this directory before running it.

## One correction the engine carries and this directory does not

`partition2.py` and the deleted `district4.py` both described their contiguity-dropped local
search as an upper bound on the contiguous draw. **It is not one.** A local search over the
relaxation returns some feasible relaxed value `F` at or below the relaxed optimum `U*`, and
the contiguous optimum `C*` is also at or below `U*`; that orders `F` against `C*` not at all.
The valid bound is the Jensen ceiling, `cert_draw.cert_balance_ceiling`. In the package the
local search is called `free_search` and is reported as a reference. Measured on v2 at k=18 it
comes in at `110.812355` against a ceiling of `110.883247`, so quoting it as the bound
understated the draw's gap by about four times.
