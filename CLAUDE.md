# National channel territory design — Claude Code setup

**Last updated:** 2026-09-01 · **Branch:** `national-channel` · **Head:** `0d3b556`

**Status:** the 2026-08-31 pivot is landed and the tree matches it. Stage 2 (staffing) is
built and exact; **stage 1 (drawing the districts) is the open work**, and the next step is
not code — it is one read-only run of `export_instance.py validate` on the work machine:
since `1272c72` its report prints the **regional opportunity shares and the balance ceiling
table** itself (all shares and counts, nothing written); `build_adjacency.py` rebuilds the
graph from TIGER if none exists. 38 tracked files, **66 tests pass, 0 fail**. **Resume point: `docs/CHANNEL.md` §0.**

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
| zips carrying sales | **~1,229** (2,232 was a double-count; corrected 2026-09-01) |
| distinct reps | **72**, including an "open" (vacancy) key → 71 real |
| total opportunity | **≈ $6.2B** — from the same 2026-08-31 sizing; re-confirm on the corrected extract |
| footprint | west coast, east coast, Texas, Florida — **midwest uncovered** |
| ⇒ `k` | **≈ 6** at $1B, pending that re-confirmation |

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
it. At ~5% saturation with λ=0.3 the opportunity term is ~90% of `u_i`. **Check that ratio
against real saturation** — it decides how much the legacy books move the map at all.

---

## Two stages

| stage | problem | status |
|---|---|---|
| **1 — draw** | k balanced contiguous districts on opportunity alone | **open — the hard part** |
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
| `td/channel.py` | stage 2 (Hungarian on logs), balance report, **`allocate_districts`** (the ceiling / dual bound) |
| `td/instance.py` | loads the descaled real instance into the N-way schema |
| `tools/instance_export/export_instance.py` | work-machine exporter — stdlib only, single file, **read it before running it** |
| `td/solvers/scip_tree.py` | the finalist MILP engine; stage 1 will be built on it |
| `td/solvers/cert_exact.py` | exact post-hoc certificate (W6c); its AM–GM OA generalises to n terms |
| `td/solvers/{base,brute}.py` | harness contract; brute-force oracle |

Tests: `.venv/bin/python3 tests/run_all.py` — **65 fast tests, no slow tier.**
`test_engines.py` is a self-contained two-player smoke test for `scip_tree`/`cert_exact`; their
original tests were left behind because they pull `instances → synth → territory`.

---

## The open risk: stage 1 at scale

Stage 1 destroys the census decomposition — the bilateral pair structure came from overlap
between two legacy rep maps, and a greenfield channel has none.

- `scip_tree` certifies to **135 zips** (two-player). ~1,229 × 6 ≈ 7,400 binaries.
- Validi, Buchanan & Lykhovyd certify ~**1,500 units** for political districting — the
  published state of the art for exactly this problem.
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

On illustrative splits of $6.2B the ceiling spread at k=6 ranges 19.4%–87.1%, so **$1B ± 10%
is probably not geometrically reachable**: a ~$0.9B region gets exactly one district and
cannot be subdivided. The best `k` moves in *opposite* directions across scenarios, so k is a
balance decision, not just headcount. **Four numbers — regional opportunity totals — settle
this with no solver and no per-zip data.**

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
- `data/` is empty in git. The national ZCTA Rook adjacency was dropped 2026-08-31 — nothing
  here reads it, and the real graph arrives with the exported instance. `data/README.md` is
  the rebuild recipe if a real-geography test instance is ever needed.
- Harness output goes to `battery/results/<run_id>/`.

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

## Open decisions (`docs/MODEL.md` §6)

Empty bundles / lexicographic MNW · θ directionality (`θ_{i←j}`) · the brute-force tier
re-cut by `Π|cand(z)|` · who owns untapped and vacant zips · the filler-capture mode ·
regional opportunity totals.
