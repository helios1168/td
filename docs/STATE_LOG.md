# State log — national channel territory design

Append-only history of `STATE.md` `## Now`, newest first. Each entry is the state narrative
as it stood when it was demoted; nothing here is edited after the fact. Entries up to
2026-09-04 were moved verbatim from `docs/foundations/FRAME.md` §0 on 2026-09-05 (the split commit);
the two 2026-09-05 entries that stood above them were folded into `STATE.md`. Serena
ignores this file; read it only when a question needs the history.

## 2026-09-06 23:30 · worktree-vbl b38c9ce — the atom route retired, the borders plan written, nothing built

**The atom route is abandoned, and the next build moves the committed map's borders onto
state lines.** Session of 2026-09-06 (evening), worktree `.claude/worktrees/vbl`, branch
`worktree-vbl`. Sponsor decisions: (1) the state-atom route is dropped outright; (2) the
borders of the committed k=18 power-cell draw (`draw_k18_v2_20260904/k18`, seed 2) are to be
moved onto state lines, sacrificing balance up to a **10% spread cap**; (3) visual map
contiguity is the bar, exact graph contiguity is not required; (4) warm start from seed 2 only,
so the result reads as the same map with its borders moved; (5) a district's home state is the
plurality of its mass.

**The plan is `docs/BORDERS_PLAN.md`, and nothing in it is built.** Owner set per state (its
home districts, else the single plurality holder); the transportation LP of `centers.assign`
with a per-zip crossing penalty `λ` and a balance band `δ` in place of the equality, which keeps
it a transportation problem (duals, at most k−1 split zips); Lloyd alternation from the
committed centres with no Nash polish; a pure-snap baseline with no LP; a δ ∈ {0, 1, 2, 5, 10%}
× λ grid overnight, one `draw.csv` and dot + Voronoi maps per cell. Measured tonight: the
committed draw already keeps **90.54% of mass inside owner sets**; a 10% cap leaves a border
inside NY/NJ against PA (NY+NJ+New England 3.19τ for three districts, PA+MD+DE 0.82τ) and AZ
split (D06 without AZ is 0.68τ). Those residual splits are the sponsor's call, not the model's.
**Track 2, added later the same evening:** the one VBL piece that fits the reframed problem,
the whole-unit minimum-splits objective (Shahmizad & Buchanan) at the *state* level, 50 units
and 18 districts with `scf` contiguity on the rook graph, solved exactly by `scipy.optimize.milp`
per δ, then realised inside each split state by the same transportation LP. It certifies the
minimum number of split states at each δ and which they are; Track 1 snaps the map you have.
Three later amendments, all in the plan: a lexicographic balance pass after the MILP (fix the
splits, minimise the maximum deviation, so δ is a cap and not a target); five Lloyd rounds
inside each split state so the CA/TX/NY cuts are compact for the shares chosen; and stage 2
measured per cell with an incumbency tie-break at level 2 behind a flag, off by default. Stage
1 stays opportunity-only by design.

**Also this session:** `docs/CHANNEL_NOTE.md` §8 (the VBL comparison and options) reviewed and
corrected, `7745ad9` and `82ef8b7`, both merged to `main` and pushed. Hess naming with the log
objective was infeasible without perspective rows; Options A–D carried no compactness term;
differences 1 and 4 compared P0 with VBL rather than the running code; "A buys a genuine dual
bound" withdrawn, since Proposition 8 already certifies the draw at 8.2e-5 nats; Option A
mis-sized at ~33,000 ZCTAs; Option D anonymous with a vacuous relaxation; certificate (iv)
lacked its dual objective. Options A–D are parked; Option B belonged to the atom route.

*What's next, and the decision it needs.* Build `td/solvers/state_borders.py` and
`tools/state_borders.py` per the plan, smoke one cell, run the grid, report the table and the
maps. The morning decision is which δ to ship, given the residual split states at each.

## 2026-09-06 20:56 · main 4e19c2b — The zero is showable, and the piece statistic had the wrong denominator

**The zero-mismatch guarantee is now showable, and the contiguity statistic that ranked the
districts was measuring the wrong denominator.** Two parallel worktrees, both merged into `main`
on 2026-09-06 at the user's instruction: `worktree-fixed-diagram` (`feaa1bc`) and
`worktree-d01` (`49b706a`), merged as `13a75c1` and `05dab7b`, followed by `3979a6b` which
corrected the records the merges left stale. Tests 275 pass, 0 fail.

**The fixed-diagram figure** (register §4a). `us_maps.py --regions-fixed <draw.csv>` builds one
power diagram — the committed draw's M-weighted centroids, one transportation LP at
exactly-equal-split targets — and draws both labellings on that single held diagram: the
committed draw at **266 of 3,704 outside**, the snapped labelling at **0 of 3,704**. Verified
end to end on merged `main`, not only by test: max dual violation 1.8e-18, the 17 split zips
ringed and named, six sliver cells stroked. The subtitle qualifies the zero with a *measured*
rebuild rather than a quoted one (15 of 3,704 at equal-split targets, 16 at own-masses), so the
figure cannot be read as a fixed-point claim. It costs **6 min 55 s** to render, because the
rebuild LP is on by default; `rebuild=False` is the switch.

**D01 is not fragmented** (register §3a). Under the snap it has two parts: a 148-ZIP NY/NJ core
holding **99.86% of its M**, and the single rural ZIP `18337` (Milford PA) at 0.14%, whose empty
catchment is **44.56% of D01's area**. The largest-piece statistic has an **area** denominator,
and area is not what stage 1 balances. On mass the snapped worst district is **D17 at 92.72%**,
not D01; on the committed draw the worst is D09 at 90.03%, not D14. The two denominators
disagree about *which* districts are the problem, on both labellings.

**Two corrections to the register, both now in it.** The committed drift is **258 at own-masses
targets and 266 at equal-split** — one number quoted for two measurements until now. And **six
cells sit under 1% of the map at k=18** (D14 0.04%, D01 0.06%, D12 0.13%, D10 0.86%, D07 0.87%,
D18 0.98%), not the three the k=13 v1 draw had.

**The review moved into the app** (`e0c7d6e`, merged 2026-09-06). `app/main.py` has a Review tab
carrying the fixed pair, verified by serving it and by `streamlit.testing`'s `AppTest`. That was
a decision, not a default: the sponsor review is a Streamlit view now, and the published
artifacts stay as the fixed record they already are. Review artifact
`893379d7-2f28-4d0f-9a5d-edb3b8f076b0` **predates all of this, so its panels still recentroid and
its D01 row still reads 55%**.

*What's next, and the decision it needs.* Whether `--regions-voronoi` should report the mass
denominator beside the area one — `tools/measure/district_pieces.py` computes all three, so this
is a reporting choice, not a measurement.

## 2026-09-06 20:13 · main 8ba1525 — The power-cell route wins on contiguity too, and the zero needs a figure

**The power-cell route now beats the state atoms on contiguity too, once you measure the
labelling it would actually ship.** Worktree `power-cell-contiguity`, branch
`worktree-power-cell-contiguity`, three commits: `a0d96fd` opened
`docs/OPTIONS_power-cell-contiguity.md` (the durable option register), `2142be8` closed its
options 1, 2-Route-A and 3, `1f6d956` qualified the zero-mismatch guarantee. Tests 269 pass.

**Option 1, largest contiguous piece per district** (`us_maps.py --regions-voronoi`). The
*committed* draw is badly fragmented — nine districts under 80% (min D14 51%), only seven at
≥95% — which is *worse* than CA5's four under 80%. The *snapped* labelling reverses it: twelve
are a single piece, seventeen of eighteen are ≥96%, and only **D01 at 55%** lags. Shared border
segments fall 1,591 → 636. Which labelling you measure decides which route wins.

**Option 2 Route A: there is no fixed point of snap → recentroid.** 20 iterations, no exact
repeat, non-monotone; it wanders spread 2.1–5.6%, gap 0.00028–0.00128. But every iterate *is* a
power diagram, so best-of-N is legitimate: **iteration 15, spread 2.1051%, gap 0.000283**, which
beats the single shot (4.0041% / 0.000724) on both axes. **Option 3:** the LP splits exactly
`k−1` = 17 zips at both target choices, carrying 17.03% of a mean district (largest `20814`,
3.699%), so the spread floor is real and nothing returns to the committed draw's 1.2902%.

**The correction that came out of review** (`1f6d956`). "Zero mismatched zips by construction"
holds only against the diagram that *produced* the snap. Rebuild the diagram from the snapped
labels and 16 of 3,704 (0.4%) fall outside again, against 258 (7.0%) committed — the same
non-self-consistency as the missing fixed point. Consequence: **every power-diagram figure
recentroids, so none of them can display the zero.**

*What's next.* Build the fixed-diagram figure (hold centres and weights, colour dots by the
labelling those weights produced) — a sponsor review needs it and it does not exist. Then
explain D01. **Merged into `main` on 2026-09-06** at the user's instruction (fast-forward, so
`main` and `worktree-power-cell-contiguity` are the same commit). Review artifact:
`893379d7-2f28-4d0f-9a5d-edb3b8f076b0`.

## 2026-09-06 18:44 · main e29e328 — CA5 map contiguity is measured, and four districts fail it

**Map contiguity for the CA5 state-atom draw is now measured, not assumed, and it fails for
four districts.** Reran `tools/run_atoms.py` (`PYTHONHASHSEED=0`, instance v2, k=18) in worktree
`ca5-map`; `draw.csv` reproduced bit-identical to the 2026-09-06 measurement (`Σ log M`
110.789532, ceiling 110.883247, gap 0.093715, spread 30.484%, one atom-graph component).
`tools/us_maps.py --regions-voronoi <draw.csv>` — each zip's Voronoi catchment dissolved by its
committed district, no LP/centers/weights, so it applies to a contiguity-search draw the same as
a center-based one (`--regions`, the power diagram, still does not) — gives the number this file
has wanted since the engine landed: **D02's largest contiguous piece holds 48% of its territory,
D11 53%, D17 55%, D06 73%**; D01/D03/D08/D09/D10/D13/D14/D16 (plus near-solid D07/D15/D18) come
out 98–100% one piece. The atom graph's single connected component certifies reachability
through `BORDER_TOL`-proximity links, not that every district is one polygon — these four are
where that gap actually bites.

*What it means.* Not a new draw and not a new cost — the 0.093715-nat gap stands. It is the
first hard evidence for the "atom-graph contiguity is not verified map contiguity" worry this
file has carried since 2026-09-06: roughly a fifth of the districts are visibly fragmented on
the ground.

*What's next.* Decide whether D02/D11/D17/D06's fragmentation is tolerable as delivered, or
forces a change to the cut/merge rules (tighter `BORDER_TOL`, a different NY+NJ/CA cut, or a
rule against a district straddling a proximity link at all). Work is on branch
`worktree-ca5-map` (`ce1ef67` the map figures, `9363c14` the boundary map), not merged into
`main` — ask before merging.

## 2026-09-06 15:24 · main bb0ff52 — push and merge already done before this session touched them

**Push and merge, both already done before this session touched them.** `git push origin main`
returned "Everything up-to-date": `origin/main` already sits at `bb0ff52`. `worktree-state-atoms`
and `main` are the same commit, `bb0ff52` — the branch was already merged (or `main` was built
directly on top of it). The prior entry's claims — "8 commits ahead" and worktree "ask before
merging" — were stale; whatever merged and pushed this did so outside this session's record. No
new code; the 269-pass count is a fresh run confirming the number the prior entry already
carried.

*What's next.* The real open item is the state-atom engine's **stage-2 cost**, still unmeasured
and possibly exceeding the 0.094-nat stage-1 gap: run `channel.score_draws` on
`battery/results/atoms_k18_v2_20260906/k18/draw.csv`, no new code needed. `.claude/settings.local.json`
carries an uncommitted local edit (permissions + `outputStyle: "Caveman Clean"`) unrelated to
this session's task and left uncommitted.

## 2026-09-06 14:19 · main bb0ff52 — state-atom stage-1 engine landed and reproduces the measurement

**The state-atom stage-1 engine is in the package** (`ff63511`), and it reproduces the
2026-09-05 exploration exactly. Scope stayed **stage 1 only** — nothing here reads rep books or
the staffed objective. `td/atoms.py` builds the atoms, `td/solvers/atom_draw.py` draws on them,
`tools/run_atoms.py` runs the pipeline, and `td/geo.py` gained `state_rook`. The prototype
`tools/state_atoms/district4.py` is deleted; the rest of that directory is exploratory or builds
the artifact and stays.

*The user's decision.* Cut counts are **CA 5 / TX 2 / NY+NJ 3 / FL 2**, the cheapest measured
setting. Measured on v2 at k=18: 56 atoms in one component, `Σ log M` **110.789532** against the
balanced ceiling **110.883247**, a gap of **0.093715 nats** at a **30.5 %** mass spread, all 18
districts connected, `draw.csv` covering all 3,748 zips.

*Two corrections the engine carries.* `STATE.md` said a stage-1 engine "would sit under the
`base.py` harness contract" — wrong: `base.py` plus `REGISTRY` is the **two-player** harness
(`Result.to_a`, `filter_pair`, `root_a`/`root_b`) and only `brute` and `scip_tree` are
registered. Stage 1 is `centers.py`, unregistered, and the new engine is its sibling. And the
prototype's `free_bound` **was not a bound**: a local search over the relaxation returns a
feasible relaxed value `F ≤ U*`, while the contiguous optimum also satisfies `C* ≤ U*`, which
orders the two not at all. It is renamed `free_search` and reported as a reference; the valid
bound is `cert_draw.cert_balance_ceiling`. Measured, `free_search` = 110.812355, so quoting it
as "the margin above the draw" understated the real gap **fourfold**.

*Two behaviours preserved on the user's call*, so the numbers reproduce: the search tie-breaks
on set iteration over atom names, so a run **requires `PYTHONHASHSEED=0`** and `run_atoms.py`
refuses to start without it; and the stateless bucket goes into the lightest district as one
block rather than being spread by `channel.place_by_state`.

*What's next.* The engine's stage-2 cost is unmeasured, and `wt/w2-phase0` turns out to have
been merged into `main` already — what is actually outstanding is the **push**.

## 2026-09-05 18:54 · worktree-state-atoms d1fdba8 — state-atom stage-1 model explored and measured, no repo code changed

**A state-atom stage-1 model was explored and measured end-to-end. No repo code changed.** The
question, from the user: replace the zip as stage 1's atomic unit with whole states, cutting the
oversized ones into pieces. Scope is **stage 1 only** — rep-to-district assignment stays a
stage-2 problem to be developed later, so nothing here touches rep books or the staffed
objective. Everything below is measured on v2 at k=18 and lives in the artifact
`7902dfb3-afc6-431e-ac2c-ceb109662780`; the scripts are in the job scratch dir, not the repo.

*The atom inventory.* 52 state codes. Only **5 states exceed the 473.5 target** — CA 4.126×,
TX 2.020×, NY 1.794×, FL 1.398×, NJ 1.037×. Largest atom needing no cut is IL at 0.677×. The
user grouped **NY+NJ as one atom** (1,340.4, 2.831×); the delivered draw already fuses them, D01
being NY 373.6 + NJ 96.7 of 471.8 and D12 NJ 340.9 + NY 128.6 of 471.8. NY+NJ+CT would be
3.014×, a near-exact three-district block, left open.

*Granularity alone is not the obstacle.* With contiguity dropped, an equal-mass cut of the four
oversized groups reaches `Σ log M` **110.883135** against the balanced ceiling **110.883247** —
a gap of 0.000112 nats, and above the zip-level draw's own 110.883101. Leaving every state whole
instead costs **3.871 nats**. Splitting the big groups is the whole mechanism.

*Contiguity is where the cost appears.* Drawn for real on the true TIGER state rook graph
(49 nodes, 107 edges — the instance's own zip graph contracts to 42 components and cannot supply
it), pieces cut by `centers.draw`: **CA 3 / TX 2 / NY+NJ 2 costs 0.864 nats**, more than the
0.72–0.78 incumbency premium. CA 3 / TX 2 / NY+NJ 3 costs 0.456; CA 4 / TX 2 / NY+NJ 3 costs
0.123; **CA 5 / TX 2 / NY+NJ 3 / FL 2 costs 0.094**, spread 30.5 %. A piece above target can
never combine with anything, so it strands as an oversized district — that is the whole effect.
TX at 2 is right at any setting (1.013× and 1.007×).

*Structural finding.* Cutting NY+NJ into 2 **severs New England**: `CT MA ME NH RI VT` reach the
network only through NY, so both NY pieces being oversized leaves them a 0.434× district. A
third NY+NJ piece at 0.944× repairs it and the atom graph returns to one component.

*What's next.* Two decisions, below. The wave-2 merge question is **untouched and still open**.

## 2026-09-05 18:54 · main 9980732 — wave 2 Phase 0 and Phase 2 executed on `wt/w2-phase0`, unmerged

**Wave 2 Phase 0 and Phase 2 are executed and committed on `wt/w2-phase0`** — five commits on
`9cfcc2c`, 237 tests pass (222 baseline + 15 new from P2-B), branch **unmerged and unpushed**.
Phase 1's four units are not launched; Phase 0 no longer blocks them.

*What landed.* `3b968de` **P0-A**: 0a's eight source corrections; 0b rewrote A1's charter to
roster enumeration over band-constrained EG programs, touching **12 sites** because `:44`,
`:109`, `:388` all claimed "one solve"; 0d withdrew `fotakis2014`; 0c re-anchored five briefs.
`2d472de` **P0-B**: `MODEL_U8-band` §10 for v2, §9 kept byte-identical as v1 history, plus
`CODEVERIFY_U8-band-v2.md`. `8b7123b` **P0-C**: `B_tot` emitted from `premium.py::measure()`,
(★) recomputed, `SATURATION` → 29.6 %, `channel_note` §5.1 retracted; `VERIFY_P0C-screen.md`.
`4a724d6` **P2-A**, `3e59445` **P2-B**.

*What the verifiers refuted* — seven claims, two of which would have shipped wrong numbers:

- **The (★) screen direction was backwards.** The plan's `0.064 → 0.261` pairs v1's `P_S` slack
  against v2's `P₁₈`. On `P_S` — U11's actual per-roster prune — slack goes `0.0641 → 0.0219`:
  it **TIGHTENS 2.9×**. The loosening is real but lives on `P_k`, the roster-free bound.
- **`Σᵢgᵢ = B_tot + w·P₀` is NOT an independent oracle** (`WAVE2_PLAN.md:320` overstates it). It
  is one sum rearranged: doubling `free_book` in both paths leaves it passing while `B_tot`
  moves. `B_tot` is verified instead by independent transcription (Δ = 0.0e+00).
- **`MODEL_U8-band` §5.1's gate gains.** Not ≈206 (that is `mean(g_delivered)`); measured
  211.786–228.663. Conclusion survives: min clears the 140.638 floor by 1.506×.
- `channel_note` §5.1 had inherited v1's `D(g)`; true value **0.148 nats**, and the 1e-4–1e-2
  range is `D(M)`. The 30 % threshold is **not** crossed at 29.588 %, so the passage now rests
  on the measured 0.890-nat window. Inversion holds at **6.0×**, not orders of magnitude.

*What it means.* ★8 was executed **removal only**: `fotakis2014` withdrawn at all seven sites,
Gibbard–Satterthwaite withdrawn too (no citation exists anywhere in the corpus), **nothing put
in its place** — the invariant has no cited basis and stands as a prudential design choice, with
the misreporting exposure explicitly preserved. P2-B **established** cert 1's residual-targets
equivalence by KKT proof plus 4,000-case numeric check, and **refused** `WAVE2_PLAN`'s literal
cert-2 instruction after measuring that both inherited symmetry breaks cut off the optimum.

*What's next.* **Decide whether `wt/w2-phase0` merges to `main`** — the wave-2 decision said
verified tracks auto-merge *this batch only*, but nothing has merged and the push was refused by
the auto-mode classifier. Then launch Phase 1's four units.

## 2026-09-05 02:35 · main 9cfcc2c — wave 2 planned but not executed

**Wave 2 is planned but not executed.** `docs/WAVE2_PLAN.md` (this commit) is the execution
plan — 9 tracks in 3 phases, with per-track model assignments, worktree names and merge order.
Nothing in it has run: no unit launched, no correction applied, no re-measure taken. The tree is
otherwise unchanged from `352b9d7` — 222 tests, live instance at k=18.

*What the planning found.* Three things filed as cleanup actually **gate** the units, which is
why the plan is phased rather than a flat fan-out:

- **`MODEL_U8-band.md` was never re-anchored to v2, and its v2 re-run was never verified.** Its
  whole §9 is k=13; `82dbe98` wrote only data — the gitignored manifest, one tracked figure, and
  the headlines in `## Facts`. Wave 2 would consume a verified v1 document beside an unverified
  v2 manifest, so U8's v2 `code-verify` is a prerequisite (P0-B), not a loose end.
- **The wave-2 briefs are v1 artifacts, and two units' premises moved.** U4-disp's first-mover
  tie set went from 75 exact ties (2.90 % of `T`) to `n_exact_ties = 0`; U10-round's acceptance
  #2 is unsatisfiable as written, demanding a SCIP vertex that `CODEVERIFY_U8-band` F7 narrowed
  to a cross-check `certified_upper` never adopts.
- **The (★) roster-free screen has no implementation.** It was arithmetic in a docs-only commit
  (`795ea8e`); `60.8025` survives only as a display literal at
  `docs/artifacts/U9-bandthm/bandthm.py:957`. Its primitive `B_tot` is emitted by no tool, and
  U11's branch-and-bound stop rule depends on it.

*Four corrections to this file's own record*, all folded into the plan: the `borgwardt2019`
downgrade belongs to `LIT_optimization.md` §8, **not** `DOMAIN_optimization` §8 (slip inherited
from `VERIFY_U9-bandthm.md:419`); N7's defect is that it grids on the **spread**, and the fix is
to grid on `δ₀`; the two `MODEL_U8-band` §5.1/§5.2 fixes already landed in `ddd162d` / `ed5a9a8`,
leaving only a small residue; and `TD_SLOW=1` adds nothing — no test module has set `SLOW = True`
since the `acfdbfe` prune, so the slow tier `CLAUDE.md` advertises does not exist.

*What it means.* A fresh session can execute wave 2 from `docs/WAVE2_PLAN.md` without
reconstructing any of the above. The user's four planning decisions are recorded there
(all 4 units concurrent · U13 parameterised on A12 · all loose-end groups in scope · verified
tracks auto-merge, **this batch only**).

*What's next.* Execute **Phase 0** — it gates everything else. The one decision still
outstanding is the sponsor's hand-drawn-states call (A12), being taken in a separate session.

## 2026-09-05 01:21 · main 352b9d7 — the hub consolidated: one resume point on the live v2 instance

**The live instance is `instance_descaled_v2.json.gz` at `k = 18`** (≈$18B, sponsor-confirmed
2026-09-04, not to be re-derived). `main` became the hub on 2026-09-05: fast-forwarded to
`national-channel` (a strict descendant, 198 commits), that worktree retired, the gitignored
inputs moved to the repo root, `docs/math_note/` restored from `contiguity-harness`. The same
day `wt/runs` and `wt/A1` were merged with the user's approval (three state-file conflicts,
zero code conflicts): the hub carries the 14+1 pin-cost catalogue (`docs/RUNS.md`), the HiGHS
hang fix in `td/solvers/centers.py::assign()`, A1's wave 1 (U8-band, U9-bandthm) and the v2
re-anchor. The merge review established: **the two tracks' k=18 draws are byte-identical**
(`cmp`, not inferred) — A1 drew with the unpatched LP and runs with the patched one, so the
solver fix did not move the draw and every A1 v2 number is directly comparable with the
catalogue's baseline; one nats scale for every lever (see `## Facts`); no contradictions
between the tracks. Verified after the merge: 222 tests; a fresh k=18 seed-2 draw with the
merged solver is byte-identical to A1's `draw_k18_v2_20260904/k18/draw.csv`.

*Later on 2026-09-05 — the tree was restructured for a cheap start-up (this commit):* state
consolidated into this file (CLAUDE.md carries invariants only, `HANDOFF.md` deleted, FRAME §0
back to framing revisions, history in `docs/STATE_LOG.md`); A1's lens / domain plans / brief /
units promoted to the hub paths (neutral copies in `docs/foundations/archive/hub-2026-09-02/`, user
decision); `TEST_PLAN`, `RESULTS`, `RESEARCH_GUIDE` archived; `docs/CODE_MAP.md` holds the
file map and run recipes; Serena indexes markdown (marksman) and its memories collapsed to
one; `/state` rewritten around this file; headroom removed, `rtk` installed; pycache-only
fossils deleted. No `td/`, `tools/` or `tests/` behaviour changed (docstring paths only).

*What it means.* One resume point, on the live instance. The k=13 seed-3-vs-seed-9 decision,
the atlas, and `REVIEW_GROMOV` R1's 41.9 %-saturation premium arithmetic are v1 history.
*What's next, all user-gated:* the sponsor's hand-drawn-states call, then wave 2 (see `## Next`).

## 2026-09-04 23:03 · wt/runs d7c4503 — the 14+1 pin-cost catalogue ran; HiGHS hang fixed; artifact published

**Earlier — state on 2026-09-04, 23:03 (branch `wt/runs`, worktree `.claude/worktrees/runs`, head
`d7c4503`, branched from `national-channel` at `e3cc5d2`; tests 184 pass, 0 fail): the runs
track ran the 14+1 pin-cost catalogue to completion, found and fixed a solver hang along the
way, and published the artifact.** *What landed* (`d7c4503`): 14 scenario specs
(`docs/artifacts/runs/scenarios/*.json`, 7 regions × {`fix`,`anchor`}), the driver
(`run_all.sh`), the map script (`make_maps.sh`) and the generator (`build_artifact.py`) — all
new under `docs/artifacts/runs/`; 15 power-diagram maps plus one `opportunity.png` under
`figures/runs_20260904/` (tracked); results and the region table in `docs/RUNS.md`. Every one
of the 15 runs (`instance_descaled_v2.json.gz`, `--k 14-22 --seeds 0-9`) staffed all districts
(0 unstaffed) with masses summing to the instance total. Artifact:
https://claude.ai/code/artifact/f903ee01-eefc-40cf-bd32-8f5536b6e65f — headline table,
7-region pin-cost catalogue, three charts (bar at k=18, cost-vs-k, deviation-vs-k), 15 scenario
sections with maps and per-district tables.

**Mid-run finding, fixed with the user's sign-off at each step (full detail in `docs/RUNS.md`):
`td/solvers/centers.py::assign()`'s `scipy.optimize.linprog(method="highs")` hangs
indefinitely on the new instance** — 0.08s on the old instance, up to 214s (and, at k=18 with
no `options` dict at all, confirmed via `faulthandler` to never return) on the new one for the
same shape of LP. Not the Alaska/Hawaii zips' extreme LAEA coordinates (ruled out by testing
without them — no change). Fixed: `method="highs-ds"` pinned with an explicit
`options={"time_limit": 60.0}` — scipy 1.18.1's HiGHS wrapper appears to need *any* options
dict present to avoid the hang; root cause not chased further than confirming the fix is
narrow and correct. Verified before resuming the catalogue: 184/184 tests unchanged; the
old-instance regression (`--k 8-16 --seeds 0-9` vs. `sweep_20260902_s10`) is byte-identical at
8 of 9 k-values — **k=9 differs only at the tie-noise floor** (all ten seeds land within
~6e-6 nats of each other; the new LP method flips which tied seed wins, moving nash by ~3e-6,
about 1,000× under `CLAUDE.md`'s 5e-3 nat tolerance) — accepted as expected tie noise, not a
defect, with the user's explicit approval before resuming.

**Region table (recomputed from the actual catalogue, not the earlier illustrative one):**
cost tracks distance from natural k as designed — CALIFORNIA (natural k 4.36) costs ~2.04 nats
against baseline at k=18, CAROLINAS (natural k 15.92, inside the 14–22 sweep) costs ~0.008, a
~250× spread. `nash Δ` (balance cost) is identical between `fix` and `anchor` for every region
(expected — both pin the same mass); `stage-2 Δ` (the staffed objective) diverges and isn't
always negative: **FLORIDA `fix` staffs +0.029 nats *better* than the unpinned baseline**, and
CAROLINAS `anchor` +0.012 better — stage 2 sees rep books stage 1 doesn't, so a hand-drawn
district can occasionally out-staff a balance-only split even though it can never win on
balance alone. Full table in `docs/RUNS.md`.

*What's next:* the sponsor still needs to pick which states (if any) are hand-drawn — this
catalogue is the price list `CHANNEL.md`'s open item asked for, not the decision itself. No
merge to `national-channel` has happened or is proposed by this entry (ask-before-merging-to-hub
stands).


## 2026-09-04 22:41 · wt/A1 82dbe98 — v2 re-anchor done: D1′ NOT SOFT on the live instance at k = 18

**Earlier — state on 2026-09-04, night, 22:41 (branch `wt/A1`, worktree `.claude/worktrees/A1`, head
`82dbe98`, 2 commits over `9854fea`; tests **222 pass, 0 fail** — 218 + 4 from `test_frontier`):
the v2 re-anchor is done. `D1′ is NOT SOFT on the live instance — v2 at k = 18, roster S₁₈.`
Wave 1's verdict survives the instance change, and wave 2 is unblocked against real v2 numbers.**

*What landed.* The gating step from the previous entry, in order. **(1)** `.gitignore` widened to
`instance_descaled*.json.gz`, matching `wt/runs` — the literal rule left the confidential v2 export
untracked *but committable*; then v2 copied in and re-validated (`check_descaled` → `[]`;
3,748 / 718 / 1,447 / 16 / 1,567 / 114 exactly as `wt/runs` reported). **(2) The v2 draw at
k = 18**, `battery/results/draw_k18_v2_20260904/k18/` (gitignored), `--seeds 0-9 --workers 8` —
seeds 0–9 rather than v1's 0–4 so it agrees with the baseline `wt/runs`'s catalogue will produce.
Winner **seed 2**, 0 unstaffed, masses sum to 8,523.21, spread **1.368%**, **`δ₀ = 0.009970`**
(max deviation), **`V = 95.755191659241`**. Each `(k, seed)` draw is independent
(`centers.draw(XY, M, k, seed=seed, locked=...)`), so this is bit-identical to the `k18` slice of
`wt/runs`'s `--k 14-22` baseline — no duplication conflict. **(3) `frontier.py`'s gate re-pointed**
(`82dbe98`, the session's only code change). **(4) The frontier on v2**,
`battery/results/u8_band_v2_20260904/` + `figures/u8_band_v2/frontier.png`. **(5) The premium
ladder on v2**, `battery/results/meas_v2_20260904/`.

*The gate change, and why it is not a weakening.* `EG_S13_REFERENCE = 60.6974156139` was a hard
constant that **raised** on any instance but v1 at k = 13, so it blocked the v2 run outright. It
was standing in for a structural fact: `EG_S` maximises `Σ_i log g_i` over every coverage and the
delivered map *is* a coverage, so **`EG_S ≥ V` is a theorem** that holds on any instance and fails
exactly when `U` and `V` were built in different utility conventions — the `model.utilities`
(masked) against `channel.gain_matrix` (unmasked) mistake `CODEVERIFY_U8-band` row 2 records. The
gate now asserts that always; `--gate-reference VALUE` keeps the exact pin as an opt-in. **The v1
draw with `--gate-reference 60.6974156139` reproduces wave 1 unchanged** —
`[60.69741561132058, 60.69741562001393]`, delta `6.11e-9` — so the refactor is behaviour-preserving
on the certified artifact. Four new tests in `tests/test_frontier.py`; `EG_S13_*` result keys and
plot labels are now parametrised on `setting.k` (v1's manifest keeps the old key names).

*The number that scopes the track.* Gate: `EG_{S₁₈} = [96.532151752556, 96.532151758538]`, bracket
`5.98e-9`, **`+0.776960` above `V`**. Then the frontier — every bracket tier-1
(`4.33e-9`–`8.44e-9`), 16–64 cuts, **monotone and concave with zero violations**:

| `δ` | 0.009970 (`δ₀`) | 0.02 | 0.05 | 0.10 | 0.33 |
|---|---|---|---|---|---|
| `EG^bal_{S₁₈}(δ)` | 96.479699 | 96.485191 | 96.497690 | 96.510123 | 96.530978 |
| gap to `V` = 95.755192 | **0.724507** | 0.729999 | 0.742499 | 0.754932 | 0.775786 |

**D1′: NOT SOFT at every `δ`** — the one-solve bounds are 0.730 / 0.748 / 0.777 nats at
`δ = 0.02 / 0.05 / 0.10`, **146–155× the 5e-3 tier-2 floor**, with tangent slack `+3.81e-4` to
`+2.23e-2`. **`δ*` does not exist on `[δ₀, 0.33]`**: the gap is already 0.724507 nats at the left
endpoint, so zero bisection solves were needed and the verdict does not rest on the slope at all.
`s_min(δ₀) = 0.585586`. SCIP cross-checked at `δ = 0.02` and `0.33`, both status `optimal` (never
`time_limit`, 31.8 s and 32.2 s), agreeing to `2.31e-9` and `2.27e-9`.

*What it means.* **A1's charter survives its kill test a second time, now on the live instance**,
and `APPROACHES.md` §0's `collapsed-on-softness` branch does **not** fire. **The band is still not
what binds:** v2's whole frontier rises **0.0513 nats across a 33-fold widening** of `δ` (v1: 0.077
across 84-fold), so ★9 remains a governance choice rather than a value trade-off. Note the premium
is *slightly larger* on v2 in absolute nats (0.7245 vs 0.6830 at `δ₀`) even though saturation fell
41.6% → 29.6% — it is not simply proportional to saturation, and `k` moved 13 → 18 as well.

*Structure at `δ₀`, and one thing that changed character.* **N8:** 16 of 18 bands tight, 2 agents
slack, `+8/−8` binding — **not CEEI**, the same shape as v1; from `δ = 0.05` outward only lower
bands bind (`+0/−6`, `+0/−4`, `+0/−1`), and at 0.33 one tight / 17 slack. **Splits 24**, under the
cap `k−1+t = 33` and the unconditional `2k−1 = 35`; rank 3773/3773, band residual `5.9e-16`,
integral witness in band at every `δ`. **First movers are no longer tie-degenerate:** v1 had **75
exact MBB ties carrying 2.90% of `T`; v2 has zero**. The list is still flagged DEGENERATE for a
*different* reason — vertex support 3773 against an expected 3781, so `ν` is one dual optimum among
several — but the named zips now carry strictly positive margins (`5.6e-7`–`2.5e-6`) and the top 25
hold 0.39% of `T`, concentrated on R0008 / R0021 / R0014 / R0009. Quote the list only with that
caveat.

*The premium ladder moved in one place that matters.* Shares of total book (v1/k=13 → v2/k=18):
`P₀` 37.82 → **41.53%**, `P_S` 51.43 → **54.42%**, `P₁₃` 52.34 → **59.27%**, `P_free` 79.44 →
**84.17%**. The **match gap is exactly 0 on both** — the Hungarian matching is already optimal at
the `P*(A)` roster. The map gap barely moves (0.640 → 0.663 nats). But the **roster gap grows
0.0430 → 0.2494 nats, 5.8×**: on v1 the roster was nearly free, on v2 *which reps staff the channel*
is worth a quarter nat. **That is the one downstream priority this re-anchor changes — it is
U11-roster's subject.**

*What's next, in order.* (1) **Wave 2** — U10-round, U11-roster, U4-disp, and U13-base; briefs at
`docs/tracks/A1/units/`, **written against v1 assumptions, so re-read them before launching** (U11
reuses `eg_band.py` as its solver, and its priority is now higher than the brief assumes). (2)
`REVIEW_GROMOV` R1's premium arithmetic can now be redone on v2 — saturation 29.6% and the measured
ladder above are both in hand. (3) **Still user-gated:** the merge of `wt/A1` into
`national-channel`, ★11's charter rewrite, ★8, and the source-document corrections wave 1 implies.

*Process note worth not re-learning.* `frontier.py` backgrounded writes **block-buffered** stdout to
its log, so 34 minutes passed with an empty output file and no way to tell which stage was running;
`sample <pid>` on the process showed it inside `SCIPsolve → heurExecMultistart`, which located it
past the gate and past the `δ₀` point. **Run it with `python3 -u` when backgrounding.** Also: SCIP
was only 64 s of that 34 minutes — the OA master solves dominate at `n·k = 67,464`.


## 2026-09-04 end of day · wt/A1 fd619c7 — hold lifted: ≈$18B confirmed, k = 18, v2 supersedes v1

**Earlier the same day — state on 2026-09-04, end of day (branch `wt/A1`, worktree
`.claude/worktrees/A1`,
head `fd619c7`; tests **218 pass, 0 fail** at `fd619c7` — 184 + 24 from U8-band + 10 from
`instance_diff`): the hold is lifted. `The sponsor's ≈$18B is confirmed, k = 18, and v2 supersedes v1.` A1's wave-1 results
stand as certified facts about **v1 at k = 13** and must be re-run before they mean anything
about the live problem.**

*User decisions (2026-09-04, end of day).* The ≈$18B total **is correct and is not to be
re-derived**. Work continues on `instance_descaled_v2.json.gz` at **k = 18**. This resolves the
instance-and-`k` question the earlier hold was waiting on.

*Consequence, recorded not acted on.* The two descaled exports pin the real growth ratio
`D_v2 / D_v1 = ×1.8814` — robust, because the descaling divisor is recoverable (below). With
`D_v2 = $18B` that puts **`D_v1` at ≈$9.6B, not the ≈$13B** §6 records. v1's `k = 13` therefore
came from an overstated total; the consistent v1 sizing would have been `k ≈ 10`. **§6's
"total opportunity ≈ $13B" and "⇒ territories k 13" rows, and §9's settled item "k = 13 at a
$1B target", are superseded** — marked in place. Nothing downstream of them is re-derived here.

*The instance review that produced this (2026-09-04, no code changed).* Both exports carry
exactly one `m_rel` per zip (`nodes.z` / `nodes.m_rel`, column-oriented), so nothing double-counts,
even though the *source* has one row per zip × rep with the zip's opportunity repeated on each.
- **The descaling divisor changed.** `m_rel = M / median(positive M)`, and 440 of the 1,229 shared
  zips land on one constant ratio `K = divisor_v1/divisor_v2 = 1.650015380` — they are the zips
  **unchanged in dollars**, holding 37.9% of v1's opportunity. `f = ratio / K` is the real
  per-zip change. Of the rest, **787 grew and exactly 2 shrank** (`92505` ×0.70, `11228` ×0.85);
  median mover ×1.41, p95 ×5.04, max ×21.1 (`19801`, Wilmington DE). `K` is a uniform rescale and
  therefore a **no-op for the objective** — it cannot move an optimum, a gap or a certificate.
- **The growth is untapped market, not bigger territories.** Zips with no candidate rep go
  77 → 1,584; `zips_untapped` 75 → **1,567**; uncontested 477 → 1,447; **contested barely moves,
  675 → 718**. Untapped is 2.9% of v1's opportunity and **15.7% of v2's**. Growth is ×1.8814 over
  all opportunity but only **×1.6333 over worked zips**. So the contested decision problem A1
  actually optimises grew by ~6%, not by 3×.
- **Saturation falls 41.6% → 29.6%, and it decomposes.** On the shared zips alone 41.6% → 34.5%,
  because real opportunity was revised up ×1.2257 while book stayed flat at ×1.0162; the rest,
  34.5% → 29.6%, is the new zips, 1,567 of which are untapped and carry no book at all. This is
  the number `REVIEW_GROMOV` R1 measured at 41.9%, so **R1's premium arithmetic is now stale too**.
- v2 also adds Alaska and Hawaii (3 zips, 0.095% of opportunity); v1 was CONUS-only. Other meta
  moves: `zips_m_imputed` 5 → 90, `zips_headroom_repaired` 289 → 129, `repair_added_share`
  0.0573 → 0.0095, `n_reps` 111 → 114 (all 111 retained), `n_sales_rows` 2,637 → 5,324.
- Visual check published as the **Opportunity Map Diff** artifact,
  `https://claude.ai/code/artifact/68eecbb9-3ce2-45d9-8161-5db7fe212957` (both instances on one
  projection and one circle-area scale; views for coverage and for real change).
- **Every number above is reproducible:** `tools/measure/instance_diff.py <old> <new>` recovers
  `K` from the unchanged zips and emits the whole comparison (10 tests, `test_instance_diff.py`;
  218 total). Run it on any future export before trusting a sizing figure — it also reports the
  row-inflation factor a dollar total should be checked against.

*What this does to wave 1.* Nothing is retracted. U8's manifest pins
`instance_sha256 = cf7d66c0…` and `draw_sha256`, so **"NOT SOFT" is a certified fact about v1 at
k = 13, roster `S₁₃`** and is scoped as such. It is not yet a fact about v2 at k = 18. The
mechanism is plausibly scale-free — the verdict came from the *level* at `δ₀`, not the slope —
and the contested set barely grew, so the structure is likely intact; that is a hypothesis, not a
result. `td/solvers/eg_band.py` and `tools/measure/frontier.py` are instance-agnostic and need no
change.

*What's next, in order.* (1) **A v2 draw at k = 18.** `battery/results/draw_k13_20260901` is a
*v1* draw; every A1 unit consumes a draw plus its stage-2 roster, so stage 1 has to run on v2
first (`tools/run_draw.py`, and `wt/runs`'s `RUNS_PLAN.md` catalogue covers this ground with
`--k 14-22`). (2) **Re-run `tools/measure/frontier.py` on the v2 draw at k = 18** — one solve
re-tests D1′ and re-anchors `δ₀`, `V`, `EG_S` and the roster before any wave-2 unit is spent.
(3) Then wave 2 (U10-round, U11-roster, U4-disp) and U13-base. (4) **Still user-gated:** the merge
of `wt/A1` into `national-channel` (analysed and safe — three state-file conflicts, zero code
conflicts, additions only, `td-runs` has no objection), ★11's charter rewrite, ★8, and the
source-document corrections wave 1 implies.


## 2026-09-04 · wt/runs 2f83d48 — v2 validated, BLANK pseudo-zip dropped, k-target reframed 13 → 18

**Earlier — state on 2026-09-04, branch `wt/runs`, head `2f83d48`: the runs track validated the
new instance, fixed one data-quality defect, and reframed its k-target from 13 to 18 on the
sponsor's real total.** *What landed* (`2f83d48`, docs + gitignored data,
no `td/`/`tools/` change; preceded by Serena onboarding `205a507` and this plan's commit
`a2c102c`): the old-instance regression (`instance_descaled.json.gz`, `--k 8-16 --seeds 0-9`)
reproduced `sweep_20260902_s10` byte-identical across `sweep.csv` and all nine `k*/draw.csv`,
certifying the solver and seeding haven't moved. The new instance
`instance_descaled_v2.json.gz` arrived and validated clean (`check_descaled` empty list; raw
export 3,749 zips / 4,712 edges / 114 reps / total M 8,524.5 — 3.1× the old instance's 2,745.6;
8 new states AK/HI/IA/ID/MS/MT/NE/NM, none dropped). One data-quality artifact found and fixed:
a vacant pseudo-zip literally named `"BLANK"` carries no `state` field, so `place_by_state`
can't place it the way the other 41 uncoordinated real zips can — dropped, leaving
`instance_descaled_v2.json.gz` at 3,748 zips / total M 8,523.2 (`instance_descaled_v2.raw.json.gz`
keeps the untouched export for provenance). The sponsor then confirmed the new instance's real
total is **≈ $18B** (was ≈$13B on the old instance), moving the working target from k≈13 to
**k≈18**; `docs/RUNS_PLAN.md` was reframed accordingly — the new-instance k-sweep (§4–§7) moves
from `--k 8-16` to **`--k 14-22`** (same 9-value width, same `--seeds 0-9`), the map/table
anchor moves from k=13 to k=18, and §3's region table was recomputed at the new target
(k=18 → 473.5): CALIFORNIA 1,953.8 (4.13×), TEXAS 972.1 (2.05×), NEWYORK 849.6 (1.79×), MIDWEST
876.5 (1.85×), CAROLINAS 535.2 (1.13×), SOUTHWEST 606.8 (1.28×), FLORIDA 661.9 (1.40×). *What it
means:* **every one of the seven candidate regions is now oversized as a single district**, not
just CALIFORNIA as on the old instance — CAROLINAS and SOUTHWEST are the closest fits. Region
definitions stay fixed per the plan's own rule (re-tuning would curve-fit the thing being
measured); this is a finding for §7's generator, not something resolved by regrouping. §1's
old-instance regression keeps its original `--k 8-16` (pinned to `sweep_20260902_s10`, must
never move). *What's next:* §4 onward — 14 committed scenario JSON specs (7 regions ×
{`fix`,`anchor`}), the 14+1 run catalogue at `--k 14-22 --seeds 0-9` (~14 min), 15 power-diagram
maps at k=18, the generator, and a new published artifact (must not touch `c007d61d`) — none of
it has run yet, all gated on a go-ahead. Cross-branch note: `wt/A1` is separately proposing to
merge into `national-channel`; confirmed by cross-session message that its merge touches none of
the three files this entry updates in a way that conflicts with this branch, and its retirement
of `CLAUDE.md`'s old "$1B ± 10% not geometrically reachable" paragraph is consistent with (not
contradicted by) this entry's own region-oversized finding on the new numbers.


## 2026-09-04 · wt/A1 ed5a9a8 — wave 1 (U8-band, U9-bandthm) landed and verified; then HELD on the new instance

**Earlier the same day — state on 2026-09-04 (branch `wt/A1`, worktree `.claude/worktrees/A1`,
head `ed5a9a8`, 5 commits over `629e3da`; tests 208 pass, 0 fail — 184 pre-existing + 24 new, run
at `ddd162d`; `ed5a9a8` is docs-only): wave 1 launched,
landed and was verified. `D1′ says the premium is NOT SOFT: A1 continues and wave 2 is live.**

*What landed.* **U9-bandthm** (`954d9eb` MODEL, `f199e92` VERIFY; `modeler` → `math-verify`) and
**U8-band** (`69997ac` code+MODEL+figures, `ddd162d` CODEVERIFY + both refuted rows fixed;
`python-typed` → `code-verify`), launched in parallel from this worktree after activating Serena
to it *by path* (six registered projects are named `td`).

*The number that decides the track.* The hard gate passed first: `EG_{S₁₃}` reproduced as
`[60.69741561132, 60.69741562001]` — `6.11e-9` from the published `60.6974156139`, confirming the
**unmasked** utility convention (`channel.gain_matrix`, not `model.utilities`). Then the frontier,
every bracket tier-1 (`2.8e-9`–`8.2e-9`), 15–57 tangents, monotone and concave with **zero**
violations:

| `δ` | 0.0039 (`δ₀`) | 0.02 | 0.05 | 0.10 | 0.33 |
|---|---|---|---|---|---|
| `EG^bal_{S₁₃}(δ)` | 60.620441 | 60.628865 | 60.641601 | 60.657725 | 60.697416 |
| gap to `V` = 59.9375 | **0.682971** | 0.691975 | 0.708802 | 0.736845 | 0.759946 |

**D1′: NOT SOFT at every `δ`** — 137–147× the 5e-3 tier-2 floor. **`δ*` does not exist on
`[δ₀, 0.33]`**: the gap is already 0.683 nats at the left endpoint, so zero bisection solves were
needed, and the verdict does not rest on the slope at all. `s_min(δ₀) = 0.5608759` nats per unit
`δ`, a *verified* supergradient (tangent slack `+5.8e-4` to `+1.7e-2`). SCIP cross-checked at
`δ = 0.02` and `0.33`, status `optimal` (never `time_limit`), agreeing to `1.58e-9` and `1.10e-9`.
`EG^bal(0.33) = EG_{S₁₃}` exactly, because the band goes slack there (the EG vertex's max
deviation is 0.3224 < 0.33) — the sandwich closes at its right endpoint.

*What it means.* **The band was never what was binding.** The whole frontier rises `0.077` nats
while `δ` widens 84-fold, so relaxing balance from 0.39 % to 33 % buys back almost nothing of the
0.760-nat premium. A1's charter survives its own kill test a second time, and the `collapsed-on-
softness` branch in `APPROACHES.md` §0 does **not** fire. ★9 changes character: the sponsor's `δ`
is nearly free on value grounds, so it is a governance choice, not a trade-off.

*Structure measured at `δ₀`.* **N8:** 12 of 13 bands tight, six `ν_i > 0` and six `ν_i < 0` — **not
CEEI**; from `δ = 0.02` outward only lower bands bind, and at `0.33` all `ν = 0` and anonymity is
restored. The single band-slack agent pins the multiplier gauge, so `p` and `ν` are quotable here
(U9 P2b). **Splits:** 19, under the cap `k−1+t = 24` and the unconditional `2k−1 = 25`; rank
1248/1248, cleaned at 1e-6 with **zero** phantom splits. **First movers:** degenerate — 75 exact
MBB ties carrying 2.90 % of `T`, so `ν` is one dual optimum and no first-mover list is named from
it alone (the unit's stop rule fired as written).

*Four published claims were refuted, all deliberately, none contradicting a settled result.*
(1) `DOMAIN_optimization` §2.12's first-mover rule `argmax_i u_i(z)/(p_z + ν_i M_z)` omits `1/g*_i`
and is false even at `ν ≡ 0` — `math-verify` reproduced it at **one zip, `k = 2`, integer data**.
The corrected additive margin `max_i(u_i/g*_i − ν_i M_z) − 2nd-max` **selects a different set of
zips entirely**, so U14 and U4-disp would have inherited a wrong list. (2) The slope
`Σ(μ⁺+μ⁻)` is not unique and is unbounded at `δ = 0`; only `s_min = (T/k)Σ|ν_i|` is quotable.
(3) The brief's own "finite convergence under `ĝ > 0`" fails for a purely continuous master
(Duran–Grossmann / Fletcher–Leyffer are MINLP theorems); only `ε`-termination holds — validity is
untouched, since every master optimum bounds `EG^bal` at every iteration. (4) **`DOMAIN_economic-
theory` §2.8's "proportionality is the first casualty" is refuted: no rep is below proportionality
at any `δ`.** Four reps are below it in the *delivered draw* (R0010 −7.14, R0013 −4.70, R0017
−2.33, R0018 −1.73) — **the starvation is the map's, not the band's**, though the minimum gap does
fall 32 % (+13.36 → +9.09) as the band tightens.

*Verification.* `VERIFY_U9-bandthm.md`: all five brief-mandated propositions VERIFIED against
rigorous brackets (`6.3e-10`–`3.2e-7`) from two independent SCIP solves with exact-rational
endpoint repair; `P6-cells` VERIFIED for the direct half, PLAUSIBLE for the `[conjectured]`
`borgwardt2019` half. `CODEVERIFY_U8-band.md`: **20 rows, 18 VERIFIED / 2 REFUTED / 0
INCONCLUSIVE**, acceptance 1–6 all PASS, `frontier.png` regenerated **byte-identical** by two
fresh full runs, manifest byte-identical modulo `{written, wall_seconds}`. Both refuted rows were
fixed in `ddd162d`: a real hole in the `ĝ > 0` guarantee on the `delta=None` path (P5.3's floor
comes from the band's *lower* row, so it does not hold there; a per-iterate check now raises, and
the gate re-runs bit-identically in the same 23 cuts), and a wrong "≈ 27 nats" figure for the
masked convention — measured `EG = 55.9763` masked and `51.9343` at the masked delivered map, so
the conclusion (masked lands below `V` and mimics a P1-band refutation) stands but the number was
off by ~29 nats. Two declined instructions were adjudicated in the unit's favour: the exact
`s_min` LP could have tightened D1′ by at most `1.6e-5` nats against a 5e-3 floor (the whole
superdifferential at `δ₀` sits inside `[0.560711, 0.560995]`), and the Slater-point tangent seed
`u_i(Z)/k ≈ 89–93` is exact and 1.4–2.2× tighter than P5.3's constant.

*Two extensions to settled results, neither a contradiction.* The district mass vector `m` is not
an invariant of the unconstrained optimum (add it to `VERIFY_U9-bandthm` §10.E's non-invariant
list), and the *primal* vertex is as fragile as the dual under a last-bit input change.

*⚠ Everything is HELD (user, 2026-09-04) — **LIFTED the same day; see the entry above**, which
settles the instance-and-`k` question this hold was waiting on ($18B confirmed, k = 18, v2
supersedes v1). Kept for provenance.* **A new instance landed in
`.claude/worktrees/runs/` at 18:26 the same day, while wave 1 was running**, and it is not a minor
revision. Measured directly: **3,748 zips against v1's 1,229** (3.05×), 114 reps against 111, and
total descaled `M` **8,523.2 against 2,745.6** (3.10×). The `runs` session reports it as
sponsor-confirmed, replacing the $13B / k ≈ 13 sizing with **k ≈ 18** (the dollar figures are not
checkable from here — descaling removes the scale by design). **§9's "k = 13 at a $1B target —
settled" and §8's assumption A1 are therefore reopened**, and the user's instruction is to hold:
**no merge, no wave-2 launch** until the instance-and-`k` question is settled with the sponsor.

This does **not** invalidate anything above. U8's manifest pins `instance_sha256 = cf7d66c0…` and
`draw_sha256` precisely so the scope is unambiguous: **NOT SOFT is a certified fact about v1 at
k = 13, roster `S₁₃`.** Whether it survives v2 at k ≈ 18 is open. The mechanism is plausibly
scale-free — the verdict came from the **level** at `δ₀` (0.683 nats before any extrapolation),
not from the slope — but that is a hypothesis. Scale is not the obstacle: `n·k` goes 15,977 →
~67,000 while the OA converged in 15–57 tangents at 1e-9 brackets. What changes is every *number*
— `δ₀`, `V`, `EG_S`, and the roster itself (13 of 111 → ~18 of 114). **The cheapest first move
when the hold lifts is one re-run of `tools/measure/frontier.py` on v2 at the new `k`:** a single
solve re-tests the verdict and re-anchors every downstream number before a wave-2 unit is spent.

*What's next, in order.* (1) **HELD — wave 2:** U10-round, U11-roster, U4-disp are unblocked by
the D1′ verdict but deliberately not launched (three units against a possibly-superseded instance
is waste); U12-menu follows U8+U11+U13; U13-base likewise held. (2) **User-gated, reported not
done:** the merge into `national-channel` — analysed and **safe** (6 ahead / 3 behind `629e3da`;
`git merge-tree` gives exactly three conflicts, all state-stamp files, zero code conflicts; every
`wt/A1` code change is an *add*, and `td-runs` confirmed no objection from the runs side) but not
authorised; ★11 rewrite
A1's charter step 3 in `APPROACHES.md`; the merge of `wt/A1` into `national-channel`; ★8's
`fotakis2014` correction; and the three source documents this wave contradicts —
`DOMAIN_optimization` §2.12 (refuted rule), §2.10 (`δ > 0` multiplier restriction too weak; the
coarse `≤ 2k` superseded), §2.11 (supergradient wording), §8 (`borgwardt2019` is corroborating,
not load-bearing), and `DOMAIN_economic-theory` N7 (grids on the spread 0.0078 rather than
`δ₀ = 0.0039`) and §2.8 (the proportionality and EF1 rows). (3) **U3-inv is retired** (user,
2026-09-04): books are measured from the data warehouse, not self-reported, so the
strategy-proofness question has no referent; ★2 shrinks to a data-quality question.

*Assumption recorded:* the session ran unattended through launch, verification, commit and this
`/state` pass, stopping at the two gates BRIEF §7 sets (no merge, no hub edits on the D1′ outcome).


## 2026-09-04 · national-channel b3931fa — the ten-seed sweep mapped at all nine k; k-Sweep artifact republished

**Earlier — state on 2026-09-04 (branch `national-channel`, worktree
`.claude/worktrees/national-channel`, head `b3931fa`, recorded by state commit `2ce052e` and
pushed to origin the same day; tests 184 pass, 0 fail at `b3931fa`):
the stage-1 ten-seed sweep is now visible at every k it was run for — the k-Sweep artifact
carries a map section for all nine k instead of three.** *What landed* (`b3931fa`, hub work,
no `td/` or `tools/` change): the six unrendered k values of `sweep_20260902_s10` — k = 8, 9,
11, 12, 14, 15 — drawn from that run's existing `draw.csv` via
`tools/us_maps.py --districts --regions` (no re-solve; the sweep already held every k), so
`figures/sweep_20260902_s10/` now has all nine k with `districts.png` + `district_regions.png`
each, matching `k10`/`k13`/`k16`. The artifact at
`https://claude.ai/code/artifact/c007d61d-c753-4151-9026-2288b9d5eb38` was republished in
place with one section per k, each section's numbers generated from that k's `metrics.json`
rather than typed; the generator reproduces the already-published k=10 and k=16 sections
byte-for-byte, which is what certifies the six new ones. Images are **lossless WebP** —
9 sections at 5.0 MB against 3.6 MB for the previous 3. Lossy was tested and rejected: at
q90 the power-diagram borders and labels reach max channel error 110 (PSNR 40.2 dB hides it,
because the error concentrates on hard edges, not texture). The `assets` capability is not
available on this account, so images remain data URIs. *Measured in passing:* at **k = 8 all
ten seeds land on the same draw** — stage-2 spread exactly 0.00e+00, so the portfolio buys
nothing there — while k = 9…16 spread 3.7e-2 to 2.1e-1 nats; this corroborates the sweep
table's `gain 0.000` rows at k ≤ 10. *What it means:* the k decision can now be read off maps
across the whole 8–16 range rather than three points; nothing in the model, the solver or the
certificates moved. *What's next, unchanged by this entry:* the A1 track's **U8-band** is
still the gating unit and still launches from `.claude/worktrees/A1` (a session was running
U8-band and U9-bandthm there on 2026-09-04); the seed-3-vs-seed-9 k=13 decision below is
still open; `--regions-voronoi` was deliberately not added to the artifact — it is the
superseded zip-catchment rendering, and `district_regions.png` already *is* the power diagram.


## 2026-09-03 end of overnight run · wt/A1 d82a0fa — A1 stages 2–4 re-run with measurements; units U8–U13 cut

**Earlier — state on 2026-09-03, end of the overnight run (branch `wt/A1`, worktree
`.claude/worktrees/A1`, head `d82a0fa`, 13 commits over `national-channel` at `a4eb488`;
tests 184 pass, 0 fail at `74eff38`): the A1 track has run the charter's stages 2–4 with the
measurements in hand, and stops before launching units.** *What landed* (all on `wt/A1`, hub
untouched): U7-meas (`74eff38`, `f7b9917`) and U1-cert (`2f965d1`, `dcc2a69`, `a253b1a`) —
numbers in §6; the (★) roster-free screen (`795ea8e`: `max_S EG_S ≤ 60.8025`, 0.865 nats over
the delivered draw, no solve; `δ₀` is the 0.39% max deviation, not the 0.78% spread);
`LENS_GROMOV.md` re-run under the charter (`67adc92`: Moves 8/11/12/13 — `EG^bal_S(δ)`, the
band-constrained EG program, replaces `EG_S` as the certificate; the frontier `δ ↦ EG^bal(δ)`;
band duals as the un-elicited exchange rate; "MINLP"/"jointly" purged; ledger U13–U19);
`DOMAIN_optimization.md` (`30c1fae`: §2.1 retired to a contingency, §2.10–§2.15 new, D1′ the
one-solve softness certificate replaces the τ-homotopy) and `DOMAIN_economic-theory.md`
(`173089b`: §2.8 `EG^bal` as CEEI with quantity bands, §2.9 MRT-vs-MRS, §2.10 the roster
market; D5 split, D6 `fotakis2014` scope correction, D7 tie-break policy) re-run;
`LIT_optimization.md` new (`8a63445`, 46 entries: `EG^bal_S` is an Eisenberg–Gale market,
`jainvazirani2010`, but its price reading breaks at stated budgets, `jalota2023`; `≤ k−1` is
`lenstra1990`; `budish2013` closes rounding-by-citation; `borgwardt2019` keeps the
power-diagram certificate at `δ > 0`) and a 2026-09-03 section in `LIT_economic-theory.md`
(`913a7f0`, 38 entries: `echenique2021constrained` prices constraints and proves envy is lost
under per-agent bands; `kawase2026balanced`; `breugem2022vertical`); `BRIEF.md` superseded on
this branch (`d82a0fa`) with units **U8-band, U9-bandthm, U10-round, U11-roster, U12-menu,
U13-base** and ★8–★12. *What it means:* A1's kill test passed (matching gap 0, map 0.64 nats,
roster 0.04), but everything it can win is ≤ 0.865 nats over all rosters and ≤ 0.760 at the
delivered one, all of it above 33% max deviation; the live question is what survives a band,
and it is one concave solve per roster (U8-band), not a MINLP. A0's soft kill fired
(`g`-spread 60.65% vs 0.78%). *What's next, in order:* (1) **★12 — done: `national-channel` was
fast-forwarded to `wt/A1` at `8546de6` on 2026-09-03 with the user's approval and pushed;**
the two branches share a head and `wt/A1`'s worktree continues from it. *Reorganised the same
day:* A1's lens, domain plans, brief and units U8–U13 moved to `docs/tracks/A1/`; the hub's
`docs/foundations/LENS_GROMOV.md`, `DOMAIN_*.md`, `BRIEF.md` restored to their neutral `a4eb488` versions
with a header; `APPROACHES.md` §0 gained the "what every track inherits" block and each
charter's kill line was updated; `HANDOFF.md` gained the track-start checklist. (2) Launch **U8-band** from a session
started in `.claude/worktrees/A1` (Serena binds to the launch directory) — its D1′ certificate
can end the track in one solve; U9-bandthm, U13-base, U6-sel, U3-inv run alongside. (3) After
U8: ★11 rewrite the charter's step 3; ★9 the sponsor's `δ` as a menu (U12), ★10 the tie-break
policy (U11's evidence), ★8 the `fotakis2014` correction. Assumption recorded: the user asked
for the overnight run to continue without stopping; the track went one stage past the
approved plan (lens, domains, literature, research plan) and launched nothing.


## 2026-09-03 · wt/A1 (from a4eb488) — A1 track opened; ★6 lifted; U7-meas and U1-cert launched and landed

**Earlier on 2026-09-03 (branch `wt/A1`, worktree `.claude/worktrees/A1`, branched from
`national-channel` at `a4eb488`): the A1 track (`docs/foundations/APPROACHES.md` §A1, joint coverage
optimisation) is open. ★6 is lifted in full — units may run code against
`instance_descaled.json.gz` for any purpose (user decision, 2026-09-03). The instance, the
gazetteer cache and the two k=13 draws (`draw_k13_20260901` seed 3, `sweep_20260902_s10/k13`
seed 9) were copied into this worktree by hand (all gitignored).** Launched here: **U7-meas**
(the measurement stage, `docs/MODEL_U7-meas.md`) as A1's kill experiment — the premium ladder
`P₀ ≤ P*(A) ≤ P_S ≤ P₁₃ ≤ P_free`, the realised-gain spread (U1), contested-among-the-13 (U4)
and `corr(S_i, M)` (U8) — and **U1-cert** (`units/U1-cert.md`, EG dual vs the four
certificates) in parallel. The lens and domain re-runs under the A1 charter wait for the
numbers. Hub files edited here (this file, `BRIEF.md`, `APPROACHES.md`, the two unit briefs)
reach `national-channel` only by a merge the user approves. Everything below this entry is
the hub's state at `a4eb488`.

*Later the same day — both units landed.* **U1-cert** (`MODEL_U1-cert.md`, `VERIFY_U1-cert.md`,
`docs/artifacts/U1-cert/`): P1 VERIFIED at every `ρ ≥ 0` under a named extension hypothesis;
P2 three-of-four (the integer balance floor is not an EG-dual degeneration); the modeler's
"`≤ k` splits heterogeneously" REFUTED and retracted (`≤ k − 1` holds via the MBB face);
`EG_{S₁₃} = 60.6974` vs `V = 59.9375`. **U7-meas** (`MODEL_U7-meas.md`, `tools/measure/`,
`CODEVERIFY_U7-meas.md` 15/17 VERIFIED, the two refuted rows being spec text since fixed;
184 tests): the premium ladder and the other numbers are in §6. **A1's kill test passed** —
the matching is already right, the map holds 0.64 nats of premium, the roster 0.04 — but
U1-cert caps the whole thing at 0.76 nats at this roster and shows it is bought with balance.
A0's soft kill (U1) fires: `g`-spread 60.65% vs `M`-spread 0.78%. *Assumption recorded:* the
user asked for the run to continue overnight without stopping, so the track proceeds past the
approved plan into the charter's next stage — `/gromov`, `/domain optimization`,
`/domain economic-theory` and `/research-plan` under the A1 charter with these numbers — and
stops before launching new units. Still no merge into `national-channel` without asking.


## 2026-09-02 · national-channel 0d0ea96 — stage-1 scenarios, the k sweep, the ten-seed sweep and its artifact

**State on 2026-09-02 (branch `national-channel`, head `0d0ea96`, pushed — `cf4170b` was
the fast-forward of `stage1-scenarios`, `0d0ea96` adds the ten-seed sweep, its maps and the
artifact link, see "Later the same day" below; the work was done in worktree
`.claude/worktrees/stage1-scenarios`, branched at `544504e`, code commit `8eece3f`, and the
174 tests were re-run in this worktree after the fast-forward): stage 1
now runs *scenarios* on the real instance — hand-drawn districts by state, a k sweep, and
per-district opportunity statistics — and the unpinned k=13 draw reproduces
`draw_k13_20260901` bit-for-bit; 174 tests pass, 0 fail (151 + 23 new).**

*What landed* (`8eece3f`, code + tests, one commit). `td/solvers/centers.py`: `draw(locked=)`
anchors zips to districts before the LP — locked zips leave the LP, their mass comes off the
district's target through the new `residual_targets` water-fill (an anchor already past its
share is *saturated* and receives nothing), the anchors' centroids seed the free centers
(`seed_centers(initial=)`), and `improve(movable=)` never moves them; `assign(targets=)` takes
per-district masses. `locked=None` is the old path literally (`targets=None`, `initial=None`,
`movable=None`), pinned by `test_draw_without_locks_is_unchanged` and by the real-instance
regression. `tools/run_draw.py`: `--fix NAME=ST,ST` (closed: exactly those states, removed
before the solver, k reduced by one) and `--anchor NAME=ST,ST` (open: locked in, filled to the
common target), or both in `--scenario file.json`; `--k 8-16` / `--seeds 0-4` ranges; every
(k, seed) draw on a `ProcessPoolExecutor` (`--workers`, default 8); per-k `k<kk>/draw.csv` +
`metrics.json` plus `sweep.csv` / `sweep.json`; per district `mode`, `vs_target`, `n_states`,
largest-zip share, median zip, stage-2 gain. Tests: 7 new in `test_centers.py`, 16 in the new
`test_run_draw.py` (parsers, scenario validation, `complete` with pins, serial-vs-pool
determinism).

*Measured on the real instance* (all under `battery/results/`, gitignored):
`draw_k13_regress/` — identical `draw.csv` to the 2026-09-01 run, winner seed 3, 59.9375, 1.2 s
for 5 seeds on the pool (the earlier 4-minute wall time was the gazetteer download, not
compute). `sweep_20260902/` — k = 8..16 unpinned, spread 0.47%–1.31%, every district staffed
at every k, 31 s. `sweep_20260902_south/` — `--fix SOUTHWEST=TX,OK --anchor FLORIDA=FL`, 10 s:
SOUTHWEST is 317.6 at every k (7.5% *under* target at k=8, 50% *over* at k=13, 85% at k=16),
and its excess lands on the other districts — at k=13 all twelve sit 4% under the $1B-scale
target; FLORIDA grew across eight south-eastern states at k=8 to reach 346.7, held FL + LA at
k=13, and at k=16 saturated at Florida's own 183.6 against a 171.6 target. No TX/OK zip leaks
out of SOUTHWEST at any k. The k=13 map renders; SOUTHWEST and D07 share a hue (the 12-colour
palette).

*Later the same day — the ten-seed sweep and its artifact.* `battery/results/sweep_20260902_s10/`
(`--k 8-16 --seeds 0-9 --workers 8`, 56 s, no pins): every k lands every district within 5% of
target and staffs all of them; spread 0.47%–1.31%. **At k=13 seed 9 staffs at 60.0401 nats,
+0.103 over the certified seed-3 draw (59.9375)** — the five extra seeds changed the k=13 map,
and the portfolio's gain (winner minus stage-1-best) is 0.03–0.11 nats at k ≥ 11 and zero at
k ≤ 10. Maps for **all nine k** are tracked under `figures/sweep_20260902_s10/k<kk>/`
(`districts.png`, `district_regions.png`; k = 8, 9, 11, 12, 14, 15 rendered 2026-09-04 from
the same run's `draw.csv`, no re-solve). Artifact, sweep table + charts + a map section per k:
https://claude.ai/code/artifact/c007d61d-c753-4151-9026-2288b9d5eb38 (nine sections as of
2026-09-04; images embedded as lossless WebP, 4.97 MB — the `assets` capability is not
available on this account, so they are data URIs; the 2026-09-01 atlas
at `1f2cddd9…` still shows the certified k=13 draw). Decision this raises: adopt the seed-9
k=13 map, or keep the certified seed-3 one? The two are Nash-indistinguishable (0.84% vs
0.78% spread, both far under the 5e-3-nat tier-2 floor); staffing is the only difference, and
the certificates were run on seed 3.

*Process note.* The first implementation attempt used the `python-typed` agent, whose Serena
binding pointed at the session's launch worktree (`national-channel`) and edited
`centers.py` there; the residue was reverted by file copy and verified by `diff`. Both the
implementation and the tests were then written by Sonnet `general-purpose` agents barred from
Serena, against the plan's Section D body spec.

*What it means, and what is next.* A fixed hand-drawn district is not free: the sweep table
makes its cost visible as the other districts' uniform shortfall, and k is a decision the
table now supports directly. Next: (i) ask the sponsor which states, if any, are hand-drawn —
FRAME §8 A12's grain question is live here, since the pin is by state; (ii) certificates 1–4
are **not** adapted to anchored draws (certificate 4 needs the locked zips excluded from the
free-cell check — noted in the `centers.py` docstring); (iii) `vs_target` is measured against
`total / k`, the $1B-scale target, deliberately, so a fixed district's cost shows on its
neighbours; (iv) ~~review and merge `stage1-scenarios` into `national-channel`~~ — done, a
fast-forward, same day. ★6 is answered
in practice for *this* branch — the user asked for runs on the real instance and they were
made — but whether framework *units* may read it is still formally open. The earlier entry's
decision order (★3, U0-lit / U1-cert / U3-inv, A11–A13) stands.


## 2026-09-02 · national-channel ec8e727 — second framing pass; wt/workflow-dryrun merged

**Earlier — 2026-09-02 (branch `national-channel`, head `ec8e727`, pushed; content head `7359c6e`): a
second framing pass — a catch-up walk of the two-stage method plus an alternatives ledger —
with no code touched; 151 tests pass, 0 fail, re-run 2026-09-02 after the merge.**
`7359c6e` **merges `wt/workflow-dryrun`** (head `750a7cc`) **into `national-channel`** together
with this revision, so the dry run's companions — `LENS_*.md`, `DOMAIN_*.md`, `BRIEF.md`,
`units/`, `MODEL_U2-stab.md`, `VERIFY_U2-stab.md` — now live here, alongside the two state
commits the dry run lacked (`96d2ee8` HANDOFF.md tracked, `f0f045a` `greedy_balanced.py`
deleted). Conflicts were docs-only (`CLAUDE.md`, `HANDOFF.md`, `CHANNEL.md` §0).

*What this pass added.* (i) §8 A11–A13: three sponsor-side assumptions the earlier pass did
not state — that every dollar of `M` is geographically attributable (no home-office /
national-accounts carve-out), that the zip is the decision grain the sponsor manages by, and
that one wholesaler per territory is a rule rather than a default. (ii) §9: the stage-2 EF1
vacuity gap (from `CHANNEL.md` §0 on this branch — a unit-demand matching cannot be EF1
non-trivially) and the branch merge, recorded as settled. (iii) §10 Q8–Q12: five alternative approaches
to the original ask, phrased as questions for the lenses — a premium-maximising *balanced*
draw as a transportation LP at fixed roster (one cost-matrix change to `centers.py`), a
roster-first ordering of the stages, a coarser decision grain (metro / branch), the
home-office carve-out, and team territories for dense metros. Nothing in §1–§7 changed
except the header.

*What is next, and the decision it needs.* The earlier entry's order stands: ★6 (may a
unit read the instance), ★3 (stability as a sixth acceptance criterion), then launch
U0-lit / U1-cert / U3-inv. The three sponsor questions behind A11–A13 are one sentence each
and change the statement, not a parameter — ask them alongside A1/A2/A6.


## 2026-09-02 · wt/workflow-dryrun ab15133 — framework 0.1 dry run reached stage 5; U2-stab 13/13 VERIFIED

**Earlier — 2026-09-02: the framework 0.1 dry run reached stage 5 on branch
`wt/workflow-dryrun` — stages 1–5 all ran, and the first verified unit came back 13/13
VERIFIED with nothing refuted.** Head `ab15133`; **docs-only — no file under `td/`, `tests/`,
`tools/` or `figures/` was touched**, so the 151-test result recorded at `937460e` stands
unchanged (not re-run on this branch). This file's §0 is the resume point for this branch and
supersedes `docs/CHANNEL.md` §6–7 (see the header above); `CHANNEL.md` §0 now carries a
pointer here rather than a second narrative.

*What landed*, five commits:

- **`0ca54e6` — stages 1–3.** `FRAME.md` (this file), `LENS_GROTHENDIECK.md` (uncited) and
  `LENS_GROMOV.md` (cited), then `DOMAIN_optimization.md` and `DOMAIN_economic-theory.md`, and
  the economic-theory literature run `LIT_economic-theory.md` + `.bib` — **46 entries, every
  one carrying a DOI**, with an absence ledger.
- **`bef533d` — stage 4.** `BRIEF.md` and eight unit briefs under `docs/units/`
  (`U0-lit`, `U1-cert`, `U2-stab`, `U3-inv`, `U4-disp`, `U5-crit`, `U6-sel`, `U7-meas`); four
  launchable in wave 1, four specified but not launched under the stated budget.
- **`4d0dbab` — stage 5a.** `MODEL_U2-stab.md` (the roster-stability unit) with runnable
  artifacts under `docs/artifacts/U2-stab/`.
- **`fb72bdc` — stage 5b.** `VERIFY_U2-stab.md`: `math-verify` attacked all 13 rows of the
  §7 handoff table and returned **13 VERIFIED, 0 REFUTED**, each backed by a standalone
  script that recomputes every matching independently of `stab.py`.
- **`ab15133`** — agent memory harvested from the run under `.claude/agent-memory/`.

*What it means.* Two things, one about the framework and one about the problem. **The
framework:** a unit brief cut from FRAME/LENS/DOMAIN/LIT was executable end to end by
`modeler` → `math-verify` with no chat-history dependency, and the verifier did real work
rather than rubber-stamping — it raised **two documentation caveats** that stand as open doc
fixes: §4 row 6's auxiliary counts (2,187 / 3,672 rosters with a blocking pair) are
**tie-break dependent** and are not labelled as such, and **P2.2's raw-Hungarian threshold of
5 depends on the distinctness hypothesis** — without distinctness a max entry of 4 suffices.
Neither touches a proposition. **The problem:** U2-stab establishes that the roster-stability
question is live, non-vacuous *because* saturation is 41.9% (the rep-dependent term is a 42%
modulation of `g`, its row 13 recovering FRAME §6's 0.42 to 0.0017), and decidable in **169
comparisons rather than 1,443** — no unselected wholesaler among the 98 can ever block a
max-weight roster (P3.3), so only the 13×13 selected sub-matrix matters. It also predicts,
against `LIT_economic-theory.md` §0.4's expectation, that at the real 111-of-13 shape the
delivered Hungarian roster coincides with the unique stable roster **~70% of the time** (0.011
at 13×13, rising with slack) — a prediction, not a measurement.

*What is next, and the decision it needs.* The blocking one is **★6 — may a unit run code
against `instance_descaled.json.gz`?** The instance is not in this worktree and the plan's own
constraint forbids it, which is why every wave-1 result is conditional and why U7-meas (the
measurement stage both domains wanted to run *first*) is unlaunched. `BRIEF.md` §7 records the
risk plainly: two measured numbers could *cancel* the rest of the plan. Second, **★3 — should
roster stability become a sixth acceptance criterion?** `BRIEF.md` §5 says to ask this only
after U2-stab reports, and it now has: the question is cheap, so the ask is warranted.
Then: launch the remaining wave-1 units (**U0-lit**, **U1-cert**, **U3-inv** — all independent
and none needing the instance), and consider **★7**, `/domain econometrics`, which is the only
route to U5/A4 and U6.


## 2026-09-02 — the framing pass itself

**Earlier — 2026-09-02: the framing pass itself.** This is the first framing pass, written *after* the work rather than
before it, so most of §9 is already settled by evidence: the real descaled instance is in
(1,229 zips / 111 reps / ~$13B ⇒ k=13), a certified k=13 draw exists (0.78% opportunity
spread, all 13 territories staffed, 4.5e-5 nats under the analytic ceiling), the territory map
is a power diagram with a solver-free certificate, and 151 tests pass. What framing exposes is
that **the acceptance test the business would actually sign has never been written down**, and
the two open items are both about the term nobody optimised: the 2026-09-01 review measured
real saturation at **41.9%** (not the 5% assumed), which makes the incumbency premium
(~3.7 nats of swing) roughly four orders of magnitude larger than the balance residual that
received all the effort. **Next, and the decision it needs:** state the acceptance test in
business units (not nats), then resolve whether territory-drawing may see rep books at all —
the value says yes, the incentive-safety argument (`RESEARCH_FINDINGS` §9-G) says no. That is
the user's call, and it is the only genuinely blocking one.

---
