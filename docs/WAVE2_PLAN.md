# Wave 2 execution plan — units, corrections, re-measures, loose ends

Planned 2026-09-05 against `main` @ `352b9d7`. Covers `STATE.md ## Next` items 2–5 plus the
queued-fixes list, as parallel subagent tracks. **Item 1 (the sponsor's hand-drawn-states call,
A12) is out of scope — it is being handled separately.**

Nothing in this plan has been executed. It is the resume point for a fresh session.

## Context

The hub is clean: `main` @ `352b9d7`, no live worktrees, 222 tests green. The live instance is
`instance_descaled_v2.json.gz` at **k = 18**, one draw (seed 2, `δ₀ = 0.009970`, `V = 95.755192`,
`EG_{S₁₈} = 96.532152`).

Four discoveries during planning reshape the work into phases rather than a flat fan-out:

1. **The wave-2 briefs are v1 artifacts.** Written throughout in k=13, `P₁₃`, `S₁₃`, seed-3/seed-9,
   and v1 numbers. `U10-round` hardcodes `|F| ≤ 2k−1 ≤ 25` and "≤ 325 binaries" — at k=18 those are
   `≤ 35` and 630. Launching against a brief as written produces v1 answers.
2. **The source-doc corrections gate the units.** `DOMAIN_optimization.md` **still carries §2.12's
   refuted first-mover rule in its wrong form**, so a fresh subagent reading it today picks up
   refuted mathematics. U10 also consumes §2.10's `≤ 2k−1`; U4-disp's second candidate modulus is
   `borgwardt2019`, which the corrections downgrade.
3. **`MODEL_U8-band.md` was never re-anchored to v2, and the v2 re-run was never verified.** Its
   whole §9 is k=13; commit `82dbe98` wrote only data — a gitignored manifest, one tracked figure,
   and the headlines in `STATE.md ## Facts`. Wave 2 would consume *a verified v1 document plus an
   unverified v2 manifest*. This promotes "U8's v2 re-run not through `code-verify`" from a loose
   end to a **prerequisite**.
4. **The (★) roster-free screen has no implementation.** It was arithmetic in a docs-only commit
   (`795ea8e`); `60.8025` survives only as a display literal at
   `docs/artifacts/U9-bandthm/bandthm.py:957`, and §2.14 itself warns "recompute it before quoting;
   this plan ran no code." Its missing primitive `B_tot` is emitted by no tool. **U11's stop rule
   depends on it.**

## Decisions taken (user, 2026-09-05)

| question | answer |
|---|---|
| Concurrency | **All 4 units at once** |
| U13-base vs the A12 sponsor call | **Proceed, parameterised on A12** — greedy baseline now, bucket seed pluggable |
| Loose ends in scope | **All four groups** |
| Merge policy | **Auto-merge the verified ones** — overrides the standing "ask before merging" rule, **for this batch only**; the stored rule is unchanged |

## Corrections to the record, found while planning

Four items in `STATE.md` are themselves wrong and are fixed as part of this work:

1. **`STATE.md` `## Next`** files the `borgwardt2019` downgrade under `DOMAIN_optimization` §8. It
   is **`LIT_optimization.md` §8, lines 547–548**; `DOMAIN_optimization.md` §8 contains no
   `borgwardt2019`. Slip inherited from `VERIFY_U9-bandthm.md:419`.
2. **N7's direction.** The defect is that N7 grids on the **spread** (`0.0078`); the fix is to grid
   on **`δ₀`**, which on the live draw is **`0.009970`** (`MODEL_U8-band` §9.7 finding 1).
3. **The queued-fixes list** carries the two `MODEL_U8-band` fixes as outstanding. Both landed in
   `ddd162d` / `ed5a9a8`; only a small residue remains (P0-B step 2).
4. **`TD_SLOW=1` adds nothing.** No test module sets `SLOW = True` — the zip50 anchors were dropped
   in the `acfdbfe` prune. `CLAUDE.md` and `STATE.md` imply a live slow tier that does not exist.

---

# Phase 0 — inputs (gates Phase 1)

Three tracks in parallel.

## P0-A — `wt/w2-inputs` (docs only, no `.venv`, no data)

Runs **0a → 0b → 0d → 0c in that order**: the briefs quote the domain documents verbatim
(`## Spec (verbatim from …)`), so sources must be correct before briefs are re-anchored against
them. Steps 0a/0b/0d are transcription against a written spec — **sonnet**. Step 0c is judgement —
**opus**.

### 0a. Source-document corrections `[sonnet]`

`VERIFY_U9-bandthm.md` §9 and §10 already carry the verbatim replacement text and the verdict
citation for every item — transcription, not derivation. Each defect is restated at 2–4 sites, so
this is a **consistency sweep**:

| correction | primary site | repeats at | evidence |
|---|---|---|---|
| §2.12 first-mover REFUTED → `max_i(u_i/g*_i − ν_i M_z) − 2nd-max` | `DOMAIN_optimization.md:423-427` | `:64`, `:259` | `VERIFY_U9-bandthm` §5, verdict line 254 |
| §2.10 Slater holds at `δ = 0` too | `:261-263` | `:61` | `MODEL_U9-bandthm` §3 P0; `VERIFY` §1 row P0 |
| §2.10 `≤ 2k−1` supersedes `≤ 2k` | `:267-281` | `:65`, `:630` | `VERIFY_U9-bandthm` §4 (`−1` unconditional, 440 vertices) |
| §2.11 "**a** supergradient", quote minimised `(T/k)Σ\|ν_i\|` | `:335-336` | `:62`, `:417`, `:624` | `VERIFY_U9-bandthm` §6 |
| `borgwardt2019` → corroborating only | **`LIT_optimization.md:547-548`** | `:673`, `:781`, `:23` | `MODEL_U9-bandthm` P6-cells, §6 verdict |
| N7 grid → `δ₀` (v2: `0.009970`) | `DOMAIN_economic-theory.md:742` | `:443-444`, `:523` | `MODEL_U8-band` §9.7 finding 1 |
| §2.8 proportionality REFUTED | `:469-480` | `BRIEF.md:99-100` | `MODEL_U8-band` §9.5 |
| §2.8 EF1 row per `kawase2026balanced` | `:469-480` | `BRIEF.md:99-100` | `MODEL_U9-bandthm` P2.7 |

Plus the two `STATE.md` fixes above.

**Two items are not purely editorial.**

- **§2.11.** It cannot simply read "a supergradient". `VERIFY_U9-bandthm` §6 measured `Σ|ν_i|` as
  *itself* gauge-dependent at `δ = 0` (factor **16.4**: `5.102078` vs gauge-reduced `0.311544`),
  and a loose minimisation yields an **INVALID** supergradient. The text must say *minimised over
  the dual-optimal set, and gauge-reduced*.
- **§2.8 EF1.** `VERIFY_U9-bandthm` §9 item 4 records an over-reach: `kawase2026balanced`'s
  *positive* result is for cardinality balancedness under restricted valuations, so the existence
  half does not transfer. Only the negative half stands — the band costs **MNW's EF1 guarantee**,
  not EF1.

Quote the **v2** proportionality number: `prop_gap_delivered` min is **−12.0248** at k=18 (v1
−7.1351), so the refutation is stronger than the v1 evidence states.

### 0b. ★11 charter rewrite `[sonnet]`

`APPROACHES.md:116-119` step 3 — "rep-indexed MINLP" → "roster enumeration over band-constrained
EG programs". Keep consistent with `:44`, `:109`, `:114-115`, `:388`. Unblocked:
`collapsed-on-softness` does **not** fire (premium 0.72–0.78 nats, 146–155× the floor).

### 0d. ★8 `fotakis2014` scope correction (D6) `[sonnet]`

Six sites over-read `fotakis2014` as the reason for "books enter at stage 2 only".

> **Correction (2026-09-05, applied).** This step originally read "the invariant rests on
> Gibbard–Satterthwaite generically". That basis is **unsourced** — no G–S citation or argument
> exists in the corpus, and `LIT_economic-theory` §4 covers Green–Laffont and restricted message
> spaces instead. Correcting one over-read by asserting a second unsourced claim repeats the
> failure being fixed, so ★8 was executed as **removal only**: `fotakis2014` withdrawn at every
> site, no replacement basis asserted, the invariant recorded as a prudential design choice with an
> open citation gap, and the misreporting exposure explicitly preserved.

Sites, as they stood at `81bd59f` on 2026-09-05: `RESEARCH_FINDINGS.md:548,1087`,
`REVIEW_GROMOV.md:41`, the problem file at line 99, `APPROACHES.md:221`,
`DOMAIN_optimization.md:845`, `LENS_GROMOV.md:307`. The first three of those files were folded
away on 2026-09-07 — the ★8 statement now lives in `docs/MODEL.md` §9; recover the originals with
`git show 81bd59f:docs/<file>`. Guard rail (`LIT_economic-theory.md:1154`): must not read as "the incentive
concern goes away". ★8 lost its owning unit when U3-inv was retired, which is why it lands here.

### 0c. Brief re-anchor to v2 / k=18 `[opus]`

Rewrite the four wave-2 briefs plus U12-menu against the live instance. Judgement, not
substitution — several are derived quantities and two units' *premises* changed.

**U10-round** — `≤ 25` → **`≤ 35`** (manifest: `split_cap_2k_minus_1: 35`); "≤ 325 binaries, `2k`
rows" → **630 binaries, 36 rows**; the grid `{0.02, 0.05, 0.10}` omits the live `δ₀ = 0.009970`.
**Acceptance #2 is unsatisfiable as written**: it demands "both U8 vertices (OA and SCIP)", but
`CODEVERIFY_U8-band` F7 narrowed SCIP to a cross-check `certified_upper` never adopts, and the v2
run ran SCIP only at `δ ∈ {0.02, 0.33}`. Inputs point at v1 `MODEL_U1-cert` and
`battery/results/u8_band_20260904/`; live is `u8_band_v2_20260904/`.

**U11-roster** — seed-3/seed-9 → the single k=18 **seed 2** draw; the `1.37e-2` / `8.1e-3` margins
and the (★) values `60.7615` / `60.8025` all to be re-measured; `P₁₃` / `S₁₃` → `P₁₈` / `S₁₈`. The
roster-swap parenthetical "(R0009, R0012 in for R0017, R0018)" is **wrong on v2** — it is
**R0007, R0011, R0012, R0020 in for R0004, R0021, R0028, R0038**. Keep the *code* keys `P13` /
`P13_solve`: `premium.py` still emits them at k=18 (naming fossil — flag, don't chase). Add the
dependency on P0-C's `B_tot` / (★) recomputation.

**U13-base** — largest re-anchor. "≈ 1/13 of `M`" → `1/18`; band target `7.7 %` → **5.56 %**, so
the state-grain failure is strictly worse than the brief anticipates; TX's `11.5 %` was measured on
1,229 zips and must be re-measured on 3,748; delivered point `(0.0039, 59.9375)` →
**`(0.009970, 95.755192)`**. Per the A12 decision, leave the bucket seed pluggable.

**U4-disp** — the premise moved. The brief consumes U8's first-mover list, but v1's *75 exact MBB
ties carrying 2.90 % of `T`* became `n_exact_ties = 0`, `tied_M_share = 0.0`, 25 ranked zips.
Worse, `MODEL_U8-band` §9.7 finding 5 records degeneracy at **every** `δ`, so `ν` is one dual
optimum among many and **no first-mover list may be named from it alone**. Also stale: the
`4.66e-5`-nat dots-vs-cells non-decision, "Blocked on ★6" (lifted), and the header's "gated on
U0-lit — not launched" (U0-lit landed as `LIT_optimization.md`).

**U12-menu** (wave 3, re-anchored now while context is loaded) — the two-knob `77.6×` → ≈ **44.0×**
on v2; MNW point → `(δ₀, 95.755192)`, endpoint `96.532152`; `e^{Δ/k}` takes k=18.

**All five** — the "launch from `.claude/worktrees/A1`" line and the `wt/A1` branch (and U4's
`wt/workflow-dryrun`, which does not exist) are stale; tracks branch from `main`.
`BRIEF.md:118-119` is the stale sentence that produced them. Add a line to each brief noting the
`enforce-file-tools.sh` hook: `cat`/`head`/`tail`/`sed`/`awk`/`grep` on a file are blocked in
favour of Read and the Serena symbol tools (`RUNS_PLAN.md:83-89`).

## P0-B — `wt/w2-u8close` (data + `.venv`) `[opus]`

Gates all four units.

1. Add a **v2 results section** to `docs/MODEL_U8-band.md` from the live manifest, leaving the k=13
   §9 as v1 history. Follow the file's own convention of folding corrections in as
   `> **Correction (…)**` blockquotes rather than rewriting prose.
2. Clear the residue the already-landed §5.1/§5.2 fixes left behind: the **v1 constants stranded in
   §5.1** (`:257-266` — `63.113`/`42.451`, `δ = 0.0039`, "all 13 gains ≈ 90"; on v2 it is k=18,
   `δ₀ = 0.009970`, gains ≈ 206), and **§9.1's `:465-466`** "the smaller — the OA's — is the one
   reported", which still frames the choice as "take the smaller" rather than §5.2's "SCIP is never
   a source".
3. Run `code-verify` over the v2 re-run → `docs/CODEVERIFY_U8-band-v2.md`.

**Live v2 anchors** (from `battery/results/u8_band_v2_20260904/draw_k18_v2_20260904.json`):
`k=18`, `n_zips=3748`, `T=8523.2425369707`, `T/k=473.51347427615`, `δ₀=0.00997002334742`,
`V_delivered=95.75519165924108`, gate `EG_{S₁₈}=96.53215175`; grid `[δ₀, 0.02, 0.05, 0.10, 0.33]`
with `certified_upper` `96.47969860 / 96.48519087 / 96.49769027 / 96.51012323 / 96.53097802`;
slopes `s_min` `0.5856 / 0.5097 / 0.3440 / 0.1828 / 0.0549`; softness gaps `0.73038 / 0.74795 /
0.77723`, all `soft: false`; `δ* ≤ δ₀` in 0 solves; shape monotone and concave, zero violations.
Provenance `instance_sha256 c89f1820…`, `draw_sha256 9e091c68…`, θ=0.4, λ=0.3, scipy 1.18.1 /
numpy 2.5.2 / highspy 1.15.1 / pyscipopt 6.2.1.

The manifest's `instance` field still points at the retired worktree path
`.claude/worktrees/A1/instance_descaled_v2.json.gz` — fix or record.

## P0-C — `wt/w2-screen` (data + `.venv`) `[python-typed opus; math-verify opus; sonnet for the note]`

The shared measurement primitives. Owns `tools/measure/premium.py` and `docs/channel_note/`, so no
unit contends for them. **One track, not two**: `channel_note.tex` eq. `decomp` defines `W_0` = the
(★) screen's `B_tot`, so §5.1's re-measure produces exactly the number the screen is missing.

1. **Emit `B_tot` from `premium.py::measure()`** (`:302-329`) — an `O(n)` one-pass sum, currently
   computed nowhere. Cross-check against the identity `Σ_i g_i = B_tot + w·P₀`.
2. **Recompute the (★) screen on v2** — `k·log((B_tot + w·P_S)/k)` at both `P_S` and `P₁₈`. Preview
   from committed JSON (**not a result**): `B_tot ≈ 3268.40692`, (★) at `P_S` ≈ **96.554063**, at
   `P₁₈` ≈ **96.793010**, against `V = 95.755192` and `EG_{S₁₈} = 96.532152`. **The screen loosens
   on v2**: slack over `EG_{S₁₈}` goes `0.064 → 0.261`, so the v1 sentence "the screen is tight"
   does not survive — and U11 prunes less than its brief assumes.
3. **`ceiling.py:75` `SATURATION = 0.05` → the measured 29.6 %.** Six LaTeX macros depend on it
   (`chSat`, `chUown`, `chUother`, `chOppShare`, `chPremShare`, `chUswing` →
   `ceiling_numbers.tex:56-61`); blast radius is exactly `channel_note.pdf`. Nothing in `td/`,
   `tools/` or `tests/` reads it.
4. **Redo `channel_note.tex` §5.1** (`:492-522`) against 29.6 %. The 2026-09-01 Gromov review's
   R1 (`docs/REVIEW_GROMOV.md`, deleted 2026-09-07; `git show 81bd59f:docs/REVIEW_GROMOV.md`) is the
   refutation; note R1's own figure is the **v1** 41.9 %, so the redo targets 29.6 %. R1 also
   reports that eq. (split)'s ordering **inverts** on the real instance (incumbency ≈3.7 nats vs
   `D(g)` at 1e-4–1e-2), so the "derived rather than assumed" claim at `:517-519` fails — recompute
   that range too (v2 map+roster gap 0.663 + 0.249 nats). Send the arithmetic to `math-verify`
   rather than re-deriving it in place.

**Caveat to record, not fix:** `ceiling.py` is otherwise entirely v1 (1,229 zips, 111 reps, K=13,
seed-3 masses frozen as literals at `:57-98`). Bumping `SATURATION` fixes §5.1 and leaves the rest
describing the retired instance. `STATE.md` already parks that as v1 history — do not widen.

---

# Phase 1 — the four wave-2 units (parallel, after Phase 0)

| unit | route | worktree | data/venv | model |
|---|---|---|---|---|
| U4-disp | `modeler` → `math-verify` | `wt/w2-u4disp` | no | **opus / opus** |
| U10-round | `python-typed` → `code-verify` | `wt/w2-u10round` | yes | **opus / opus** |
| U11-roster | `python-typed` → `code-verify` | `wt/w2-u11roster` | yes | **opus / opus** |
| U13-base | `python-typed` → `code-verify` | `wt/w2-u13base` | yes | **sonnet / opus** |

Branch names deliberately avoid `wt/u4`, `wt/u10`, `wt/u11` — those already exist as **v1-era
branches with unrelated content** (e.g. `wt/u10` is "reconcile harness output with gfx producers"),
all merged into `main`.

**Model rationale.** Every research agent pins `model: opus` in frontmatter, so this is about where
to override *down*. U4-disp stays opus and is the one to protect: `LIT_optimization` §9 Q9 found no
instance-specific modulus, so it is a genuine proof unit — prove a KŁ exponent for `Σ log g_i` on
the assignment polytope, expect `α ∈ [1,2]` with Hoffman suggesting `α = 1` on a polyhedron — and
`DOMAIN_optimization` §8 Q3 calls it "the single highest-leverage unknown in the plan". U10 and U11
stay opus for solver correctness (`mip_rel_gap = 0.0` certificates; a branch-and-bound whose bound
must be *valid*). U13-base drops to **sonnet** for implementation — greedy adjacency bucketing plus
scoring through existing `channel.stage2` / `premium.measure` is the most mechanical of the three —
while its `code-verify` stays opus. Every verifier stays opus; that is the layer that must stay
adversarial.

**U13 can start during Phase 0** if wanted: construction needs nothing from U8 (U8 only places its
point on the frontier). It still needs its re-anchored brief from 0c.

### Concurrency hazard

Four tracks plus P0-C on one machine. U10's acceptance #2 forbids reporting a `time_limit` as a
bound, and three units require byte-identical re-runs. Pin each track's worker count rather than
inheriting `--workers 8`, and **re-run serially any solve that hits a time limit before quoting its
number**. Each `python-typed` track must launch in its own worktree — it calls
`mcp__serena__initial_instructions` and Serena binds to the session's launch directory, which is
exactly what the briefs' stale "launch from `.claude/worktrees/A1`" line was protecting.

---

# Phase 2 — loose ends (parallel, independent of Phases 0–1)

## P2-A — `wt/w2-fixes` (docs + light code, no data) `[sonnet]`

**B4 — `math_note/toy_{grid,path}.py`.** *Two* breakages, not one: `code/gfx` was deleted in
`acfdbfe`, **and** `REPO = HERE.parent.parent.parent` resolves one level above the repo (correct
when the note lived at `research/contiguity/`). Only four symbols are used — `style.use_rc()`,
`style.PALETTE`, `style.tight_layout()`, `style.lint_text_overlap()`. `ceiling.py:46-54` already
solved this exact problem by inlining, with a comment explaining why; copy that. Recover the
original from `git show contiguity-harness:code/gfx/style.py` if needed. Note `make` is currently a
**no-op** (committed outputs are newer than the scripts), so the breakage is latent until
`make clean`; also `math_note/Makefile:6` has no worktree venv fallback, unlike `channel_note`'s.

**B7 — `docs/RUNS.md` absolute baseline.** The region table (`:52-83`) reports only deltas, so a
reader cannot convert to a level. The baseline is already on disk in
`battery/results/runs_20260904/baseline/sweep.csv` at k=18: `nash = 110.88310108262327`,
`stage2_value = 95.75519165924106`, `winner_seed = 2`. A table edit, not a re-run. (Cross-check:
`CAROLINAS_fix` `nash 110.87467895743872` → Δ −0.00842, matching the table's −0.008.)

**B8 — `build_artifact.py` assertions.** The file has **zero** `assert`/`raise` — all four
`RUNS_PLAN` §7 assertions (`:339-341`) are missing: district masses sum to the instance total in
every run; `n_unstaffed == 0` everywhere; `n_fixed`/`n_anchor` match each spec file; every
section's `instance` path is the new instance. All inputs are present in `sweep.json` and
`scenarios/*.json`. B7 and B8 are the same artifact — do them together.

**B10 — palette check, not fix.** `RUNS_PLAN.md:294-298` records the decision: "Report it if it
makes a map unreadable; **do not widen scope to fix the palette**." Be precise about what is
actually broken: `color_districts` guarantees *neighbour*-distinctness, which holds at any k while
the adjacency stays 12-colourable (measured degrees 2–5). What degrades past 12 is *global*
uniqueness — ≥6 non-adjacent repeats at k=18 vs 2 at k=13, which is by design. **But** the recorded
`SOUTHWEST`/`D07` collision is described as *adjacent*, which would be a real colouring failure.
Scope: verify that one case against the 15 maps in `figures/runs_20260904/` and report. Only widen
if it is genuinely adjacent.

## P2-B — `wt/w2-cert` (data + `.venv`) `[python-typed opus → math-verify opus]`

**B9 — certificates 1–4 for anchored draws.** Soundness-bearing: the pin-cost catalogue in
`docs/RUNS.md` is built on anchored draws. `centers.py:45-53` names the gap explicitly and declares
it out of scope for that module. Per certificate:

- **1 `cert_balance_ceiling`** — still *true* for any partition, but the honest anchored ceiling is
  over the **free** mass at **residual** targets. Quoted as-is on a pinned scenario it is a valid
  but vacuous bound.
- **2 `cert_integer_balance_floor`** — must solve `t*` on free zips against `residual_targets`
  (`centers.py:244-273`); today it searches over partitions that move locked zips, so its "floor"
  is unreachable and **understates** the true floor.
- **3 `cert_assignment_at_centers`** — must fix `x_{zj}` for locked zips (a `movable` mask,
  analogue of `improve(movable=)` at `centers.py:414`), else it "improves" the draw by relabelling
  anchored zips.
- **4 `cert_power_diagram`** — cheapest, and the fix is named in the docstring: `targets` = realised
  masses (already the default) and exclude locked zips from the free-cell check, since a locked zip
  need not sit in its own power cell and would be reported as a dual-feasibility violation.

Existing machinery: `centers.draw(locked=)` `:528`, `:540-573`; `residual_targets` `:244`;
`improve(movable=)` `:414`. Tests: `tests/test_cert_draw.py` (21), `tests/test_centers.py` (28).

---

# Verification

- `.venv/bin/python3 tests/run_all.py` from the **repo root** (a `wt/*` worktree has no `.venv`) —
  222 tests, 0 fail, on every track before it counts as green. ~7 s (208 ran in 6.3 s).
  **Do not rely on `TD_SLOW=1`** — it currently adds nothing.
- Each `code-verify` / `math-verify` returns VERIFIED / REFUTED / INCONCLUSIVE with a runnable
  artifact. **Only VERIFIED tracks auto-merge**; anything else stops and reports.
- P0-A has no test signal — its check is that every site in the 0a table changed and no other line
  did, verified by reading the diff.
- P0-C: `math-verify` clears the §5.1 arithmetic before any number reaches `channel_note.pdf`; the
  `B_tot` identity `Σ_i g_i = B_tot + w·P₀` is the independent oracle for the (★) recomputation.
- Re-measured numbers replace the v1 ones in `STATE.md ## Facts` only after their verifier clears.
- Byte-identity anchors are invalid if `figures/` is dirty — check before quoting one.
- Close with `/state`.

# Risks

- **Auto-merge across 9 tracks** touching overlapping docs. Ownership is disjoint by construction
  (P0-A owns domain/lens/brief docs, P0-B owns `MODEL_U8-band`, P0-C owns `premium.py` and
  `channel_note/`, each unit owns its own files per its brief's "files owned"), but merge order
  matters: **P0-A → P0-B → P0-C → units → P2**. Report conflicts rather than resolve them silently.
- **The (★) screen loosening** may weaken U11's stop rule enough to change its plan. Its brief's
  stop rule already covers the case (report cardinality if the near-optimal set exceeds 100).
- **U4-disp may return REFUTED**, which is a real deliverable — it closes D4. Not a failure.
- **`figures/` is tracked**; U10 and U13 both emit figures and must regenerate and commit them.

# Out of scope

Item 1, the sponsor's hand-drawn-states call (A12) — separate session. U12-menu (needs U8 + U11 +
U13); its brief is re-anchored here but the unit is not launched. The HiGHS root cause (scipy
1.18.1 option merging) — deferred unless it recurs. `ceiling.py`'s remaining v1 content beyond
`SATURATION`.

# Bibliography gap (surfaced, not scoped)

`kawase2026balanced`, `borgwardt2019` and `fotakis2014` all have resolved DOIs but live only in the
per-domain `.bib` files. **None is in `docs/math_note/territory_bibliography.bib`** (78 entries), so
`math_note.tex` cannot cite them, and there is no `.md`/`.csv` sibling — the `bibliography` skill's
three-format sync is unsatisfied for this project. 0a cites all three, so the corrections walk
straight into this.
