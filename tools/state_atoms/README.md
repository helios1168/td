# State-atom stage-1 exploration (2026-09-05)

Exploratory scripts behind artifact `7902dfb3-afc6-431e-ac2c-ceb109662780` and the `STATE.md`
entry of the same date. **Nothing here is part of the production pipeline**, nothing imports it,
and no test covers it. It is committed so the work survives the session; drop the directory if
the approach is not taken up.

Scope is stage 1 only. Rep-to-district assignment stays a stage-2 problem, so none of this reads
rep books or the staffed objective.

Run from the repo root with the root `.venv`, and set `PYTHONHASHSEED=0` — set iteration order
otherwise moves results by roughly 0.015 nats.

| file | what it does |
|---|---|
| `district4.py` | the answer: cuts each oversized group with `centers.draw`, builds the true TIGER state rook graph, draws 18 contiguous districts by seeded growth plus connectivity-checked local search, and reports each draw against a contiguity-free upper bound |
| `partition2.py` | granularity alone, contiguity dropped: three split rules against the balanced ceiling |
| `atoms.py` | per-state opportunity, zip-graph component health, how the delivered draw fragments states |
| `nynj.py` | whether the delivered draw already fuses NY and NJ, and the NY+NJ+CT arithmetic |
| `firms.py` | masked firm labels, book split, per-zip firm dominance |
| `build_map.py` + `state-atoms.tpl.html` | generates the artifact, splicing the firm-territory SVG into the template |

`build_map.py` writes to a path under the job scratch directory that no longer exists; point
`TPL`/`OUT` at this directory before running it.

## Two things to know before trusting a number

The draws are **not certified optimal**. Exact set-partition was tried and abandoned on
measurement: enumerating connected subsets of the 47- and 54-atom components passes 250,000
columns, and at 177,000 columns HiGHS found no feasible cover in 180 s. The reported bound is the
same atom set partitioned with contiguity dropped, which can only do better.

Adjacency **cannot** come from the instance. Contracted to states, the instance's zip graph has
10 edges and 42 components. These scripts import the state rook graph from the cached TIGER
shapefile via `geo.states_outline()`.
