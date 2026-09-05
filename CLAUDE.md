# National channel territory design — Claude Code setup

**Last updated:** 2026-09-05 · **Branch:** `national-channel` (the hub; `wt/runs` and `wt/A1`
merged in on 2026-09-05 with the user's approval) · **Head:** `f93f996` (the merge commit) ·
**Tests:** **222 pass, 0 fail** (run 2026-09-05 at `f93f996` in this worktree)

**Status:** **The live instance is `instance_descaled_v2.json.gz` at `k = 18`** — the sponsor's
≈$18B is confirmed and is not to be re-derived (user, 2026-09-04). The hub now carries both
2026-09-04 tracks: **runs** — the 14+1 pin-cost catalogue on v2 (`docs/RUNS.md`, artifact
https://claude.ai/code/artifact/f903ee01-eefc-40cf-bd32-8f5536b6e65f) and the HiGHS hang fix in
`td/solvers/centers.py::assign()`; **A1** — wave 1 (U8-band, U9-bandthm) verified and the v2
re-anchor done: k=18 draw (`δ₀ = 0.00997`, `V = 95.755192`), frontier and premium ladder all on
v2, and **D1′ says the premium is NOT SOFT on the live instance** (gap 0.725–0.776 nats against
the 5e-3 floor, no `δ*`, `EG_{S₁₈} = 96.532152`). The two tracks' k=18 draws are byte-identical.
**Still user-gated:** wave 2, ★11, ★8, the source-document corrections, and the sponsor's
hand-drawn-states call. **The state narrative lives in `docs/FRAME.md` §0 — read it, not this
block.**

**Resume point: `docs/FRAME.md` §0** (it supersedes `docs/CHANNEL.md` §6–7; `CHANNEL.md` §0
carries the pointer). Fast orientation: `HANDOFF.md`. A1's documents live under
`docs/tracks/A1/`; the runs track's plan and results are `docs/RUNS_PLAN.md` / `docs/RUNS.md`.

A pruned worktree. Everything from the superseded two-player merger programme is in git
history on `contiguity-harness` — recover with `git show contiguity-harness:<path>`. Nothing
was deleted, only left behind.

---

## The problem

The business is standing up a new **"national" channel**, carving the two largest firms out
of the financial-institutions and wirehouse channels. Territories are targeted at roughly
equal opportunity, **~$1B each**.

| | |
|---|---|
| zips | **3,748** on v2 (v1 had 1,229 and is a strict subset; 2,232 was an earlier double-count) |
| distinct reps | **114** on v2 (v1's 111 all retained; the 72 was an SQL error) |
| total opportunity | **≈ $18B** on v2, sponsor-confirmed 2026-09-04 (v1's "$13B" was overstated — the descaled ratio ×1.8814 puts v1 at ≈$9.6B) |
| — of which untapped | **15.7%** on v2 vs 2.9% on v1: the growth is market with no book and no rep. Contested zips only went 675 → 718 |
| footprint | national with concentration — west 33% / east 31% / TX 11.5% / FL 6.7% / ~18% spread over the rest; the "midwest uncovered" premise was wrong |
| ⇒ `k` | **18** at $1B on v2 (v1's `k = 13` followed from the overstated $13B; the consistent v1 figure was ≈ 10) |

This is **greenfield balanced districting**, not the two-player fair-division problem the
repo was built for. `docs/CHANNEL.md` is the problem; `docs/MODEL.md` is the model.

---

## The model

Per-rep book `S_i(z)`, total booked `T_z = Σ_j S_j(z)`, unowned book `S_free(z)`, opportunity
`M_z`, with `c1 = 1 − λ` and `c2 = θ(1 − λ)`:

```
u_i(z) = c1·S_i(z) + c2·(T_z − S_i(z)) + c_free·S_free(z) + λ·M_z
g_i    = Σ_{z : owner(z) = i} u_i(z)
max    Σ_i log g_i          (maximum Nash welfare, d = 0)
```

At two reps with `S = {a: A, b: B}` and `S_free = 0` this is **identically** the old
`u_a`/`u_b` — pinned by `tests/test_model.py::test_two_rep_reduction`, which is what keeps the
existing corpus of results interpretable.

**Headroom:** `M_z ≥ max_i(S_i + θ(T_z − S_i))`, unowned book included conservatively.

### Two results that make this work

**Nash welfare on a common measure *is* equal-size districting.** Every zip lands in exactly
one district, so `Σ_j M_j` is partition-invariant, and maximising `Σ_j log M_j` at fixed sum
equalises the terms. Same optimum, not an approximation — so **the $1B target needs no
constraint**: set `k = total/$1B` and balance falls out. It also sidesteps trap 2, since Nash
reaches the balance as the maximiser of a concave objective rather than by minimising a
spread. Pinned by `tests/test_channel.py::test_nash_welfare_is_equal_size_districting`.

**The objective is scale-invariant.** `u_i(z) = M_z·[c1·s_i + c2·(t_z − s_i) + λ]` with
`s_i = S_i/M_z`, so `M_z` factors out and `Σ log g_i` shifts by `n·log κ` under a global
rescale — an additive constant. The descaled instance and the real one therefore have
identical optima, gaps and certificates — **at every ρ ≥ 0, not only at ρ = 0.** Rescaling shifts `Σ log g_i` by `n·log κ`, which is the
same constant for every partition, and the perimeter is a combinatorial count, so all
objective *differences* are untouched. ρ therefore transports across the descaling unchanged.
What descaling does change is conditioning: solver feasibility tolerances are absolute in gain
units, so descaled values are better conditioned, while certificate tolerances are in nats and
are scale-free either way.

### Welfare decomposition

```
Σ_i g_i = Σ_z [λ·M_z + c2·T_z + c_free·S_free]   ← partition-invariant
        + Σ_z (c1 − c2)·S_owner(z)(z)            ← maximised by keeping zips with their incumbent
```

Balance the territories, and where there is slack leave business with the rep who already has
it. **Measured 2026-09-01 (`docs/REVIEW_GROMOV.md` R1): real aggregate saturation is 41.9%**
(median zip 46.8%) — the opportunity term is ~59% of an incumbent's `u_i`, not ~90%, the
hold-vs-not swing is ~42%, and the legacy books move the map a lot. `ceiling.py` still
hard-codes `SATURATION = 0.05` and channel_note §5.1 still carries the old arithmetic —
R1's rewrite is open. **Stale at v2 (measured 2026-09-04): saturation there is 29.6%.** It
decomposes as 41.6% → 34.5% on the shared zips (opportunity revised up ×1.226 while book stayed
flat at ×1.016) and 34.5% → 29.6% from the 1,567 untapped new zips, which carry no book at all.
Lower saturation shrinks the incumbency premium, so R1's premium arithmetic needs redoing on v2.

---

## Two stages

| stage | problem | status |
|---|---|---|
| **1 — draw** | k balanced **compact** districts on opportunity alone — contiguity was abandoned, the sold-zip graph has 547 components | **built, certified** (`solvers/centers.py`, `solvers/cert_draw.py`); the territory is a power diagram |
| **2 — match** | assign reps to districts | **built, exact** (`channel.py`) |

Stage 2 is a max-weight matching on **log** weights (`g_ij = Σ_{z∈A_j} u_i(z)`, maximise
`Σ_i log g_{i,σ(i)}`), solved exactly by the Hungarian algorithm. Nash rather than utilitarian
matters: a utilitarian match will hand one rep a district holding almost none of their book.
**Rectangular matching selects which reps staff the channel** — well-posed because k is fixed.

Known cost of the split: stage 1 cannot see relationships, so a good matching may not be
available at stage 2. Mitigation, near-free because stage 2 is milliseconds:
`channel.score_draws` ranks a portfolio of stage-1 draws by how well each staffs.

### Node classes, from `cand(z) = {i : S_i(z) > 0}`

| class | meaning |
|---|---|
| contested (≥2) | the decision problem |
| uncontested (1) | owner forced, no binary |
| **vacant** (0, filler book) | real book, no incumbent — nobody can claim it by legacy |
| untapped (0, no book) | opportunity with no book at all |

Vacant and untapped zips are **kept in the graph** — dropping them changes connectivity, and
they are exactly the "zero-value glue" of failure regime (d). Who may own them is open
(`docs/MODEL.md` §6).

---

## What is built

| file | role |
|---|---|
| `td/model.py` | N-way primitives: schema shim, per-rep utilities, gains, objective, perimeter, per-rep pieces, n-agent EF1 |
| `td/channel.py` | stage 2 (Hungarian on logs), balance report, `place_by_state`, **`allocate_districts`** (the ceiling / dual bound) |
| `td/instance.py` | loads the descaled real instance into the N-way schema |
| `td/solvers/centers.py` | **stage 1**: k-means++ seeding, transportation-LP balanced assignment, Lloyd, Nash polish, portfolio — plus `power_weights` / `power_labels`, the LP duals and the power diagram they define. `assign()`'s LP is pinned to `method="highs-ds"` with an explicit `options` dict: scipy 1.18.1's HiGHS wrapper hangs on v2 without one (`docs/RUNS.md`) |
| `td/solvers/eg_band.py` | **U8-band**: the band-constrained Eisenberg–Gale program `EG^bal_S(δ)` — `O(nk)` dual bound (no solver in the trusted path), HiGHS outer approximation, SCIP cross-check |
| `tools/measure/frontier.py` | the D1′ driver: utility-convention gate (`EG_S ≥ V`), the `δ` frontier, `δ*`, first movers, N8/N9, the plot. Background it with `python3 -u` |
| `tools/measure/instance_diff.py` | v1↔v2 comparison: recovers the descaling divisor from the unchanged zips; run on any new export before trusting a sizing figure |
| `td/solvers/cert_draw.py` | **four** post-hoc certificates: analytic balance ceiling, integer balance floor, assignment optimality at pinned centers (MILP), and `cert_power_diagram` — the duals as a solver-free `O(nk)`-checkable bound |
| `td/geo.py` + `tools/us_maps.py` | ZCTA points, LAEA projection, state basemap; six figures incl. `figure_power_regions` (the territory map) and `figure_district_regions` (the superseded zip-catchment fill, `--regions-voronoi`) |
| `tools/run_draw.py` | the reproducible pipeline: instance → (k, seed) draws on a process pool → stage 2 → `battery/results/<run-id>/k<kk>/` + `sweep.csv`; `--fix`/`--anchor NAME=ST,ST` or `--scenario file.json` for hand-drawn (partial) districts, `--k 14-22` for the v2 sweep (`--k 8-16` is the v1 regression, pinned to `sweep_20260902_s10`) |
| `tools/instance_export/export_instance.py` | work-machine exporter — stdlib only, single file, **read it before running it** |
| `td/solvers/scip_tree.py` | the two-player MILP engine; **not** what stage 1 was built on in the end |
| `td/solvers/cert_exact.py` | exact post-hoc certificate (W6c); its AM–GM OA generalises to n terms |
| `td/solvers/{base,brute}.py` | harness contract; brute-force oracle |

Tests: `.venv/bin/python3 tests/run_all.py` — **222 fast tests, 0 fail, no slow tier**
(run 2026-09-05 at `f93f996`, the merge; 222 at `82dbe98`, 218 at `fd619c7`, 208 at `ddd162d`, 184 at `74eff38`, 174 at
`8eece3f`, 151 at `7359c6e`, 131 at `f45bf89`, 65 at the prune). This worktree has no
`.venv`; use the main checkout's: `/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py`
(three levels up from this worktree, not two).
`test_engines.py` is a self-contained two-player smoke test for `scip_tree`/`cert_exact`; their
original tests were left behind because they pull `instances → synth → territory`.

---

## The open risk: stage 1 at scale

Stage 1 destroys the census decomposition — the bilateral pair structure came from overlap
between two legacy rep maps, and a greenfield channel has none.

- `scip_tree` certifies to **135 zips** (two-player). ~1,229 × 6 ≈ 7,400 binaries.
- Validi, Buchanan & Lykhovyd certify ~**1,500 units** for political districting.
  **[Stale as of 2026-09-01 recon — the frontier is now all-US instances certified at
  county level and ~175k vertices with inexact contiguity; our difficulty is the log
  objective + 547 components, not size. `docs/RESEARCH_FINDINGS.md` §0.5.]**
- **But the footprint is disconnected.** No contiguous district spans California and Florida,
  so the graph has ≥4 components and the problem *separates*: allocate integer district counts
  per component, then solve each independently at ~500 zips. Failure mechanism (a) — the thing
  that broke the legacy cut loop — arrives here as the structure that makes this tractable.
- **Symmetry** is the new hazard: k anonymous districts are interchangeable labels, which costs
  branch-and-bound its pruning. The centre-based (Hess) formulation is the standard remedy.

### Compute the balance ceiling before any solver work

`channel.allocate_districts(component_M, k)` maximises `Σ_c k_c·log(M_c/k_c)` over integer
allocations with `k_c ≥ 1`. Within a component the best conceivable outcome is `k_c` equal
districts, so this is an **upper bound on any real partition** — a free dual bound, and the
answer to whether the target is reachable at all.

**Retired 2026-09-04 (BRIEF §6.5).** This section used to say "$1B ± 10% is probably not
geometrically reachable", from illustrative splits of the superseded $6.2B sizing at k=6. The
real instance settles it the other way: the committed k=13 draw sits at **0.39 % max deviation**
(0.78 % spread), four orders inside the old worry, and `sweep_20260902_s10` balances every k from
8 to 16 within 5 %. Balance is not the binding difficulty (FRAME §9). What survives of the
paragraph is the structural point: the best `k` moves in *opposite* directions across regional
scenarios, so `k` is a balance decision and not just headcount, and four numbers — the regional
opportunity totals — settle it with no solver and no per-zip data.

---

## Traps that still apply

The full list is in git history (`git show contiguity-harness:CLAUDE.md`). These survive the
reframing because none of them was two-player:

2. **Equalisation can destroy value.** Minimising a spread can Pareto-dominate itself into a
   worse outcome. This is *why* Nash-as-balance matters — do not replace the objective with an
   explicit balance minimisation.
4. **Fairness alone is degenerate** — many allocations tie, cuts never bite, generation
   thrashes. Relevant again: every rep with no book at `z` values `z` identically.
12. `mip_rel_gap` defaults to 1e-4 in `scipy.optimize.milp`; pass `mip_rel_gap=0.0` for a real
    certificate.
13. **Separator cuts must be component-wise.** One root per component, or the dual bound is
    unsound, not merely loose. Becomes *one root per district per component* at N-way.
14. HiGHS 1.15 "Solve error" under 1e-9 tolerances; SCIP needs `misc/allow{strong,weak}dualreds`
    **off** for any lazily separated model, `ga ≤ Σu·x` not `==`, and a gain lower bound from
    the incumbent rather than 1e-9.
15. A solver abort reported as `time_limit` silently disables a retry ladder — key retries on
    the *engine's* stop reason (`extra["retryable"]`), never the harness-facing status.

**Two-tier acceptance** stands: tier 1 `CERT_TOL = 1e-8`, tier 2 `base.EPS_CERT = 5e-3` nats,
grounded on a measured data-noise floor. Re-measure the floor on the real instance.

---

## Environment

- `.venv/bin/python3` from the repo root — the system python has no numpy/scipy/networkx.
- MacTeX at `/Library/TeX/texbin`; **not** on `PATH` in non-interactive shells, so prefix
  `export PATH=/Library/TeX/texbin:$PATH` when building any note.
- Never write under `battery/figures/` (primary artifacts, and not carried into this worktree).
- **`figures/` is tracked** as of `72e5f07` — a map is a primary artifact, and a claim in the
  docs nobody can see is worse than 3 MB of PNG. Regenerate and commit together:
  `tools/us_maps.py <instance> --out figures/ --districts/--regions/--regions-voronoi <draw.csv>`.
- `data/` is empty in git, and `data/geo/` (the gazetteer cache), `instance_descaled*.json.gz`
  (v1, v2 and v2's raw export — confidential) and `battery/results/` stay ignored. The national ZCTA Rook adjacency was dropped
  2026-08-31 — nothing here reads it, and the real graph arrives with the exported instance.
  `data/README.md` is the rebuild recipe if a real-geography test instance is ever needed.
- Harness output goes to `battery/results/<run_id>/` (gitignored).

## Where to read next

1. `docs/CHANNEL.md` — the problem, the two stages, the sizing and the balance ceiling.
2. `docs/MODEL.md` — the N-way model, what the reframing broke, the engine sketch, open decisions.
3. `docs/DATA.md` — the descaled export route and why the dollar scale is not needed.
4. `docs/channel_note/` — the standalone LaTeX note: model, propositions, proofs.
5. `docs/RESULTS.md` — the empirical record of `scip_tree` at scale. Tells you
   what to expect from stage 1.
6. `docs/TEST_PLAN.md` — harness spec, tiers, gap metrics, acceptance. The tier
   definitions need re-cutting for N-way (`docs/MODEL.md` §2).
7. `tools/instance_export/README.md` — the work-machine runbook.
8. `docs/RESEARCH_FINDINGS.md` — the 2026-09-01 literature map: what our constructions are
   called, what to cite instead of prove, the absence ledger, and the prioritized roadmap
   (§9). `docs/RESEARCH_ADDITIONS.bib` holds the BibTeX candidates.
9. `docs/REVIEW_GROMOV.md` — the 2026-09-01 review of the note and formulation: the measured
   saturation correction (R1), the noise-floor resolution of cells-vs-dots (R2), the EG
   bound as certificate 5 (R3), seven note fixes (R4).

## Open decisions (`docs/MODEL.md` §6)

Empty bundles / lexicographic MNW · θ directionality (`θ_{i←j}`) · the brute-force tier
re-cut by `Π|cand(z)|` · who owns untapped and vacant zips · the filler-capture mode ·
regional opportunity totals · **book-aware stage 1 vs FINDINGS §9-G's
books-enter-at-stage-2-only invariant** (`REVIEW_GROMOV.md` R1 — live at 42% saturation).
