# Territory Division (td) — Claude Code Setup

**Last updated:** 2026-08-27  
**Project:** Fair division of ZCTA territories between two merging annuity wholesaling forces  
**Status:** Model and reference implementation settled; ready for production Python against real ZCTA data

---

## Quick Start

**Entry point:** Read `HANDOFF.md` first. It contains:
- Settled decisions (model form, fairness baseline, solution concept)
- One-page model summary with parameters and usage
- Traps already discovered during development
- Code inventory and expected graph schema

For context on what happens next, also read:
- `battery/FINDINGS.md` — synthetic case studies (C1–C9), what broke, why, and what it tells us about the three contiguity failure mechanisms
- `battery/RESEARCH_PLAN.md` — the test plan for those cases

**Minimal working example:**
```python
import networkx as nx
import territory as T
import districting as D

# Assume a networkx ZCTA graph G with per-node attributes:
# "rep_a", "rep_b", "A" (firm-A sales), "B" (firm-B sales), "M" (opportunity)
# "state" (optional)

T.validate(G)
ra, rb, _ = T.largest_pair(G)
zips = T.zips_for_pair(G, ra, rb)
exact_nash = T.solve(G, zips, "nash")  # outer approximation, 6–7 iterations
contiguous = D.solve_contiguous_nash(G, zips, rho=2e-3)  # + separator cuts
```

---

## What's Settled (Do Not Relitigate)

| Factor | Decision | Why |
|--------|----------|-----|
| **Utility model** | Linear / additive in A_z, B_z, M_z | Cobb-Douglas collapsed to one variable; had fatal zero-pathology |
| **Disagreement point** | d=(0,0) (gains are bundle utilities) | Reversed by adversarial review: neither rep can revert to legacy book after merger. At d=0, EF1 holds (Caragiannis et al. 2019); Nash restores the optimal-transport correspondence (Warren 2025) |
| **Solution concept** | Maximum Nash welfare (max g_a·g_b) | Exactly solvable via outer approximation; Pareto efficient by construction; finite algorithm with optimality certificates |
| **Fairness applies to** | All criteria (Nash, KS, egalitarian, equal-gain) | All use d=(0,0); paper's appendix tables predate this migration and need recomputing |
| **Domain** | Discrete zips, not continuum | Exact, not approximate; matches data; Rook adjacency from networkx |

**Code status:** d=(0,0) is now implemented in `territory.py` and `districting.py` (migrated 2026-08-27). The paper's `.tex` still needs updates throughout.

---

## Code Structure

### Main modules (`code/`)

| Module | Role | Key functions |
|--------|------|---|
| **territory.py** | Core solver against networkx ZCTA graph | `validate`, `census` (components), `nash_exact` (outer approximation), `solve` (exact or heuristic), `compare_criteria` (Kalai–Smorodinsky, egalitarian, etc.), `contiguity_report`, `contestability` (bootstrap robustness), `write_back` (commit assignment) |
| **districting.py** | Contiguity MILP with separator cuts | `solve_contiguous_nash` (Nash + hard contiguity), `solve_contiguous` (KS-gap variant: free Nash + welfare floor + perimeter min) |
| **synth.py** | Synthetic instance generator | Multi-rep battery: alignment, correlation, slivers, state borders, headroom, value concentration (heavy-tail dial via double Pareto-lognormal); 12 scenarios (S1–S7) backward compatible; see `TAIL_DISTRIBUTION_NOTE.md` |
| **verify_algebra.py** | 35 SymPy symbolic checks | Regression test for the model equations (standalone; does NOT exercise `territory.py`) |
| **mkfig_census.py** | Standalone plot script for the census stress test | Sole regenerator of `figures/census_stress.png`. **Not** a shared style module — nothing imports it; the battery carries its own `MAP_RC` in `battery/code/mapviz.py` |
| **territory_demo.py** | End-to-end smoke test | Synthetic lattice with misaligned territories and state bands |

### Expected graph schema

```python
G.nodes[z] = {
    "rep_a": <id>,  "rep_b": <id>,          # firm-A and -B rep IDs
    "A": <float>,   "B": <float>,   "M": <float>,  # sales, sales, opportunity
    "state": "NE",                           # optional; triggers respect_state=True path
}
# Edges = Rook adjacency (4-neighbor grid) between ZCTAs
```

### Parameters

- **theta** (transfer capture): fraction of competitor's book retained after inheritance. Not yet estimated; rests on DiD/synthetic control of prior reassignments. Reference: 0.40.
- **lam** (headroom credit): how much untapped opportunity counts vs. booked production. Compensation-philosophy choice, not estimable. Reference: 0.30.
- **rho** (compactness weight): trade-off between fairness and perimeter. Knee at 2e-3 on the battery (C8).

---

## Known Challenges & Open Gates

### Contiguity MILP: Three Independent Failure Mechanisms (Trap 11)

The outer-approximation + separator-cut loop in `solve_contiguous_nash` fails to converge on certain instances. Root-cause analysis across C1–C9 identified **three independent failure modes**, not one:

1. **Pre-existing graph disconnection** (C1-seed2 A0/B0, C5-respect_state A2/B2): The free-Nash partition already splits a pair into separate components before contiguity is imposed. Both the solver and human re-assignment prefer the split. Fixer: component-quotient preprocessing — detect undisputed stray components, fix them in place, then run the MINLP on the reduced graph.

2. **Pure scale** (C7 at n=400): HiGHS hits time/iteration limits at 125+ zips regardless of topology. Fixer: lazy-callback solver (Gurobi or CBC with PuLP) or a flow-based contiguity formulation.

3. **Value concentration** (C9, heavy-tailed A_z/B_z): Switching from lognormal to double Pareto-lognormal noise, same geometry and adjacency, **moves which pairs fail**. Cost % doubles-to-quintuples even on pairs that still converge. Strikes previously-easy, small, single-component pairs. Fixer: unknown; requires stress-testing any scale/topology fix against C9.

**Impact:** A fix aimed at only one mechanism is not guaranteed to help the others. Both components preprocessing and lazy-callback/flow formulation must be validated against all three before claiming sufficiency.

### Parameter estimation

- **theta** is the single most-important lever. Everything rests on it. Needs DiD or synthetic control on prior territory reassignments (split by *why* the prior rep left: internal move, industry exit, or departure to a competitor — the third has the loss). **Not done.**

### Real data blocking

- No real ZCTA data ingested yet. Data source and procurement process undecided. This is a gate.

### Baseline and tooling inconsistencies (found 2026-08-27, flagged not fixed)

- **`districting.py:161` is still on the old baseline.** `solve_contiguous` sets
  `Sa, Sb = A.sum(), B.sum()`, so the two districting entry points run on *different*
  disagreement points: `solve_contiguous_nash` is at d=(0,0), `solve_contiguous` is not.
  Its `Amax`/`Bmax` and welfare-floor constraint inherit the old baseline too.
- **`verify_algebra.py` certifies the superseded model.** All 35 SymPy checks carry the
  `- Sa`/`- Sb` subtractions (lines 46-47, 110-114) and the old mixture-quantile `q`
  (line 48). It cannot certify d=(0,0) and did not catch the migration. The numeric
  anchor for the solver is `review/code/dzero.py`'s self-test, which needs
  `/tmp/z50.pkl` from `code/zip50.py`.
- **The battery pipeline is runnable again (fixed 2026-08-27, during the `handoff/`
  flatten).** `battery/code/run_battery.py`, `case_pipeline.py`, and `c8_rho_sweep.py`
  now resolve `code/` and `battery/figures/` relative to the repo root instead of the
  old hard-coded `/home/claude/td/...`. Still treat `battery/figures/*.png` as
  **primary artifacts, not derived outputs** — a full run is a ~17-case MINLP sweep
  that takes ~6.5 minutes and C7/C9 don't reliably converge, so don't re-run
  `run_battery.py` casually; it will overwrite them.

### Algorithmic gaps

- **Three+ wholesalers:** No threshold rule. Leximin over dense components is the natural extension; unimplemented.
- **Dense components (C2 at alpha=0):** Two-player fairness does not compose. Every pair within a dense blob gets its own bilateral solve, which looks perfect while no component-level fairness is defined. Unimplemented.
- **State borders:** Life and annuity product availability is state-scoped. If `respect_state=True`, the state constraint becomes the binding one (C5: shatters 18.6% of edges, can fragment multi-state pairs into 5+ pieces). **This question must be settled with distribution before tuning anything downstream.**
- **Capacity constraints:** Travel time and producing-advisor count per rep, not bundled into M_z. Unbuilt.

### Paper edits pending

The d=(0,0) migration and the battery results (C1–C9) need to be reflected in `nash_territory_division_20260826.tex`:
- Rewrite introduction to cite d=0 throughout
- Rename solution concept to "maximum Nash welfare" (already done in HANDOFF.md)
- §3.1: EF1 is a theorem at d=0; drop lambda* section (it was an artifact of the old baseline)
- Appendix: recompute comparison tables (KS, egalitarian, equal-gain) at d=0 instead of d=(S_a, S_b)
- §5: fold in battery findings and contiguity mechanisms
- Reference M. Warren 2025 on Nash–optimal-transport correspondence

---

## Workflows

### Generate a synthetic case

```bash
cd code
python3 synth.py --scenario S1_aligned --seed 1
# Outputs: (n_zips, S_a, S_b, M, A_z[], B_z[], M_z[], state[], rep_a[], rep_b[], adj_matrix)
```

Pick from S1–S7 in `SCENARIOS`. New in C9: `S7_heavytail` (dPlN tail dial for A_z, B_z) — see `TAIL_DISTRIBUTION_NOTE.md`.

### Run the full battery (C1–C9)

```bash
cd battery/code
python3 run_battery.py
# Generates figures/C*.png + figures/C*.json + figures/battery_run_log.json
# ~6.5 min on one machine (case_pipeline.py runs each instance through validate → census → exact Nash → contiguous MINLP)
```

Each case produces:
- Three-panel figure: pre-merger territories, exact Nash, contiguous MINLP (all zip-level Voronoi choro­pleths)
- Metrics JSON: bound gaps, fragmentation, perimeter, product cost of contiguity

### Verify the algebra

```bash
cd code
python3 verify_algebra.py
# 35 SymPy checks; exits nonzero on failure. Standalone symbolic — does NOT exercise territory.py
```

The numeric anchor is `review/code/dzero.py` (self-test validates d=0 migration).

### Stress-test the census

```bash
cd code
python3 census_stress.py
# Exercises census(min_share) sweep, corr dial check, state binding
# Outputs: figures/census_stress.png
```

### Build the paper PDF

MacTeX (full TeX Live, installed 2026-08-27 via `brew install --cask mactex`) provides
`pdflatex`/`latexmk` at `/Library/TeX/texbin`, on `PATH` for every new shell.

```bash
cd papers
make            # latexmk -pdf nash_territory_division_20260826.tex
make clean      # remove latexmk-generated aux/log/etc.
```

---

## Next Steps (Priority Order)

### 1. Paper edits (Publish & communicate)

Update `nash_territory_division_20260826.tex` to reflect d=(0,0) migration and battery findings:
- d=(0,0) throughout (reversed from pre-merger baseline)
- Rename solution concept to "maximum Nash welfare" (not "Nash bargaining")
- §3.1: EF1 is a theorem at d=0; drop lambda* section (artifact of old baseline)
- Recompute appendix tables (KS, egalitarian, equal-gain) at d=0 instead of d=(S_a, S_b)
- §5: fold in C1–C9 battery findings and the three contiguity failure mechanisms
- Cite M. Warren 2025 on Nash–optimal-transport correspondence at d=0

Outcome: paper ready for circulation and publication; sets the record straight on settled decisions.

### 2. Fix contiguity convergence (Unblock real data at scale)

Test one or both candidate fixes on the synthetic battery (C1–C9):
- **Component-quotient preprocessing:** Detect and pre-fix undisputed small/stray components before MINLP; recompute results for C1-seed2 A0/B0, C5 A2/B2
- **Lazy-callback or flow formulation:** Replace scipy.optimize.milp (re-solves from scratch) with Gurobi or CBC/PuLP; test on C7 (n=400) and C9 (heavy tail)

**Validation must cover all three failure mechanisms** (pre-existing disconnection, pure scale, value concentration) before declaring sufficiency.

Acceptance: all C1–C9 pairs converge without iteration/time limits, gaps < 1e-8.

### 3. Leximin over dense components (Future architecture)

For instances where the census reveals dense (3A-vs-5B) overlap:
- Decompose bilevel subproblems: (a) compute the maximin welfare floor over dense pairs using Choquet or other cooperative solution, (b) enforce that floor and maximize total welfare subject to it
- OR: adopt a lexicographic rule (first maximize min pair gain, then second-maximize, etc.)
- Test on C2 at alpha=0

---

## Prerequisites (Parallel / Blocking)

These are necessary before going live but can proceed in parallel with 1–3 above:

### Real ZCTA data ingestion (GATE)

- Decide data source (USPS, Census Bureau, commercial vendor)
- Build graph loader: nodes = ZCTAs, edges = Rook adjacency, attributes per schema
- Validate: headroom pointwise, no islands, rep-territory assignments are correct
- Run `T.census(G, split=True)` at a min_share sweep; report component count and orphan share

### Estimate theta (Parameter identification)

- Literature: DiD or synthetic control on historical territory reassignments
- Source: internal reassignment records, split by reason (internal move / exit / competitor)
- Outcome: point estimate + confidence interval for the merger scenario
- Impact: every zip's utility hinges on theta

### Settle state-scope question (Decision gate)

- Consult distribution on whether territories must respect state lines
- If yes: `respect_state=True` in all downstream calls; flag that state constraint is the binding one (C5 shows 18.6% of edges cross state, multi-state pairs shatter into 5+ pieces)
- If no: proceed without state constraint but document that assumption

---

## Key Files & Documents

### Theory & review

- **papers/nash_territory_division_20260826.{pdf,tex}** — the paper (pending d=0 edits)
- **review/HANDOFF_REVIEW.md** — adversarial review finding the d=0 reversal, objections 1–4, and fixes
- **HANDOFF.md** — settled decisions, model, traps, code inventory, where to start (read first)

### Synthetic battery & findings

- **battery/RESEARCH_PLAN.md** — the test plan (C1–C9 cases and acceptance criteria)
- **battery/FINDINGS.md** — results, verified numbers, root causes of failures, structural insights
- **battery/code/case_pipeline.py** — per-case runner (instance → census → exact Nash → contiguous MINLP → 3-row figure + JSON)
- **battery/code/run_battery.py** — batch runner for all C1–C9
- **battery/figures/C*.{png,json}** — 15 outputs; run_log.json has wall times and iteration counts

### Documentation & references

- **SYNTH.md** — the synthetic battery scenarios (S1–S7): what each kills, how to use them, census min_share sensitivity
- **code/TAIL_DISTRIBUTION_NOTE.md** — heavy-tail dial in synth.py (dPlN, citations, backward-compatibility verification)
- **literature/territory_bibliography.{md,csv,bib}** — full citation set with annotations
- **reference/** — two reference papers on fair division (2-D continuum, and the earlier all-criteria discrete draft; the 1-D continuum note was deleted 2026-08-27 as superseded). `reference/fair_division_2d_20260825.pdf` §10 is the **only local source** for the M. Warren 2025 optimal-transport reference, which has no entry in `territory_bibliography.bib`

---

## Code Conventions

### Naming

- **g_a, g_b**: gains at the disagreement point (d=0); bundle utilities
- **u_a(z), u_b(z)**: per-zip utility to each rep
- **rep_a, rep_b**: wholesaler IDs (nodes in the census overlap graph)
- **z**: a ZCTA node; **S** or **assignment**: a subset of zips (allocated to rep A)
- **theta**: transfer capture (0–1)
- **lam**: headroom credit (0–1)
- **rho**: compactness weight (nonnegative; 0 means fairness only, 2e-3 is the knee)

### Solver

- **outer approximation** (in `nash_exact`): log-concave objective → convex MINLP → supporting hyperplanes → optimality certificate
- **separator cuts** (in `solve_contiguous_nash`): hard contiguity constraint via Gomory cuts and lazy generation
- **Both are inside one MINLP loop,** not the same convergence theory — worth knowing before assuming one argument covers both

---

## Quick Reference: What Each Module Produces

| Module | Input | Output | Use case |
|--------|-------|--------|----------|
| `synth.py` | scenario name, seed, n_reps, n_zips | networkx graph G with attributes | Stress test, battery case studies, example instances |
| `territory.py::nash_exact` | graph G, zip list | assignment S, gains g_a/g_b, bound gap | Exact fair division (6–7 iterations regardless of n; machine-precision certificates) |
| `territory.py::solve` | graph G, zip list, criterion="nash" | assignment S, gains, metrics | Plug-and-play solver; use exact by default |
| `districting.py::solve_contiguous_nash` | graph G, zip list, rho | assignment S, gains, perimeter, contiguity cost % | Fairness + geographic compactness |
| `territory.py::census` | graph G | list of components + per-pair metadata | Decompose national problem into bilaterals |
| `territory.py::contestability` | graph G, assignment, bootstrap n | per-zip objection probability | Robustness under measurement error |

---

## Contacts & Attribution

**Theory:** Foundations in Nash bargaining (Rubinstein & Wolinsky 1985; Binmore, Rubinstein & Wolinsky 1986), discrete fair division (Caragiannis et al. 2019 on EF1), and optimal transport (Warren 2025).

**Code:** Python 3.10+; dependencies: `networkx`, `numpy`, `scipy`, `pandas`, `matplotlib`, `pyomo`, `gurobipy` or `highs` (solver). HiGHS is open-source and included in `scipy>=1.11`.

**Project memory:** `Work/td` on the user's machine; `project_memory_*` tools keep decisions and learnings across sessions.

---

## For Claude Code CLI

When starting a task on this project:

1. **Load HANDOFF.md** to understand model and decisions
2. **Check the most recent session memory** (`project_memory_read`) for any decisions or obstacles
3. **Run `verify_algebra.py`** if the *symbolic* model changed — but note it is written against the superseded d=(S_a,S_b) baseline and cannot certify d=(0,0). The solver's numeric anchor is `review/code/dzero.py`
4. **Run relevant battery cases** (e.g., C9 for heavy tails, C5 for state borders) to validate structural changes
5. **Test on the smallest instance that exhibits the failure mode** before running the full battery
6. **Commit findings to project memory** after discovering a new trap or pattern

The codebase is mature and tested; most changes will be algorithmic (contiguity fixes) or operational (real data loading) rather than model changes.
