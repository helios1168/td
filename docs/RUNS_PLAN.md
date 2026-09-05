# Stage-1 pin-cost catalogue on the new instance — the `runs` worktree and its artifact

> **Pick this up in a fresh session.** This file is self-contained: it assumes no memory of the
> conversation that produced it. Start at §0 and work down. Everything the plan depends on was
> read out of the repo and is restated here, so nothing needs re-deriving from chat history.
>
> **This file lives at** `~/.claude/plans/lets-work-in-projects-td-claude-worktree-stateless-balloon.md`.
> §0 step 5 copies it into the worktree as `docs/RUNS_PLAN.md` so it is version-controlled too.

---

## 0. Kickoff — do these in order, before anything else

> **Already done on 2026-09-04, do not redo:** steps 1–5, then §1 and §2's validation. The
> worktree exists, Serena is bound to it, the gitignored inputs are copied, `tests/run_all.py`
> passed 184/0, this plan is committed as `docs/RUNS_PLAN.md`, the old-instance regression (§1)
> came back byte-identical to `sweep_20260902_s10`, and `instance_descaled_v2.json.gz` arrived,
> validated clean, and had its one data-quality finding fixed (below).
>
> **Resolved: the real-dollar total.** The sponsor confirmed the new instance's real total is
> **≈ $18B**, replacing the old ≈$13B/k≈13 assumption with **k≈18**. Every k-anchor and the
> k-sweep range in this file (§3–§7) have been updated accordingly; §1's regression keeps its
> original `--k 8-16` because it is pinned to the historical `sweep_20260902_s10` artifact and
> must never move.
>
> **Resolved: the `BLANK` pseudo-zip.** The raw export carried one vacant node literally named
> `"BLANK"` (no state, `share_free=1.0`, no candidates) — a data-quality artifact, not a real
> ZIP. It has been dropped: the untouched export is kept as `instance_descaled_v2.raw.json.gz`
> and `instance_descaled_v2.json.gz` (used everywhere below) is the cleaned 3,748-zip version.
> `check_descaled` is clean on the cleaned file; gazetteer-missing count is 41 (was 42).
>
> **Still to do: §4 onward** — scenario specs, the 14+1 run catalogue (~14 min of solver time),
> maps, the generator, and the artifact. None of that has run yet.

**1. ~~Create the worktree.~~ Done.** For the record, it was created explicitly rather than with
`EnterWorktree(name:)`, because `worktree.baseRef` defaults to `fresh` and would have branched
from `origin/<default-branch>` instead of `national-channel`:

```bash
git -C /Users/ntlee/projects/td worktree add \
  /Users/ntlee/projects/td/.claude/worktrees/runs -b wt/runs national-channel
```

A fresh session enters it by path: `EnterWorktree(path: "/Users/ntlee/projects/td/.claude/worktrees/runs")`.
Better still, **launch `claude` from that directory** — Serena binds to the session's launch
directory, and starting there removes the whole class of wrong-worktree failures described in
step 2.

**2. ~~Initialize serena in the new worktree.~~ Done** — bound correctly on session launch (no
`activate_project` call needed; the working directory was already the `runs` worktree). For
the record, Serena binds to a project root, and the wrong root
silently edits the wrong worktree — this exact failure happened on 2026-09-02 (FRAME §0's process
note: `python-typed` edited `centers.py` in the hub worktree because its Serena binding pointed at
the session's launch directory). So:

- Serena's tools are **deferred**. Load them first:
  `ToolSearch("select:mcp__serena__initial_instructions,mcp__serena__activate_project,mcp__serena__get_symbols_overview,mcp__serena__find_symbol,mcp__serena__find_referencing_symbols,mcp__serena__replace_symbol_body,mcp__serena__insert_after_symbol,mcp__serena__insert_before_symbol,mcp__serena__replace_content,mcp__serena__get_diagnostics_for_file")`
- Call `mcp__serena__initial_instructions` (required before any coding work).
- Call `mcp__serena__activate_project("/Users/ntlee/projects/td/.claude/worktrees/runs")`.
- **Confirm the returned active-project path is the `runs` worktree** before any edit. If it names
  `national-channel` or the main checkout, stop and re-activate.

**3. ~~Copy the gitignored inputs.~~ Done.** From `national-channel` (HANDOFF's "Starting a track" step 2 —
these are not in git and do not arrive with the branch):

```bash
cd /Users/ntlee/projects/td/.claude/worktrees/runs
cp ../national-channel/instance_descaled.json.gz .
cp -R ../national-channel/data/geo data/
mkdir -p battery/results && cp -R ../national-channel/battery/results/sweep_20260902_s10 battery/results/
```

**4. ~~Sanity-check the environment.~~ Done — 184 pass, 0 fail.** This worktree has no `.venv`;
use the main checkout's, three levels up: `/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py`.

**5. ~~Copy this plan into the repo~~ Done.** Committed as `docs/RUNS_PLAN.md`, so the plan is
version-controlled alongside the work it describes.

---

## Working rules for this task

**Lean on serena for everything it covers.** These are not preferences; the hook
`~/.claude/hooks/enforce-file-tools.sh` blocks the Bash alternatives outright.

| operation | use | never |
|---|---|---|
| understand a code file | `get_symbols_overview`, then `find_symbol(include_body=True)` on what you need | `Read` for discovery; `cat`/`head`/`tail`/`less`/`sed -n`/`awk <file>` |
| find who calls something | `find_referencing_symbols` | grep-then-guess |
| edit a whole symbol | `replace_symbol_body` | `Edit`, `sed -i`, `perl -i`, `patch` |
| edit a few lines inside one | `replace_content` (regex mode; a tight `start.*?end` wildcard is cheaper and just as safe) | rewriting the file |
| the same edit across files | `replace_in_files` (`dry_run` first) | a loop of edits |
| add at file top/bottom | `insert_before_symbol` / `insert_after_symbol` on the first/last top-level symbol | append via shell |
| write a file | `Write` | `>`, `>>`, heredocs, `tee` |

Notes learned the hard way in the session that wrote this plan:

- `mcp__serena__list_dir`, `find_file` and `search_for_pattern` are **not available in this build**.
  Use `Glob` (by name) and `Grep` (by content) for *discovery only*; every follow-up read or
  reference search goes back through serena.
- Serena executes calls one at a time internally but they cannot race, so **batch independent
  calls into one message** — every round-trip re-sends the growing context.
- `Read` is fine for Markdown/JSON/CSV. The symbolic tools are for code.
- After `replace_symbol_body` or `rename_symbol` returns success, the edit is applied and
  references are updated — do not re-read the file to confirm.
- Bash is for *running* things: git, tests, `tools/run_draw.py`, `tools/us_maps.py`, pipelines with
  no file operand.

**Never `cd` into `~/iCloud` / `~/Library/Mobile Documents`** — EINTR hangs brew, tmux and hooks,
and Claude Code keeps the cwd across Bash calls, so one `cd` poisons the session. Enforced by
`~/.claude/hooks/no-icloud-cwd.sh`.

---

## Context — why this task exists

`tools/run_draw.py` has been able to pin hand-drawn districts by state since `8eece3f`
(2026-09-02):

- `--fix NAME=ST,ST` — a **closed** district: exactly those states, removed before the solver, and
  `k` reduced by one (`solver_k(k, sc) = k - len(sc.fix)`).
- `--anchor NAME=ST,ST` — an **open** district: those states locked in, `k` unchanged, and the
  solver fills the rest toward the common target through the `residual_targets` water-fill. An
  anchor already past its share is *saturated* and receives nothing.
- `--scenario file.json` — the same thing from a committed JSON file (`{"fix": {...},
  "anchor": {...}}`), merged with the flags by `load_scenario`.

Exactly one scenario has ever been run through it (`sweep_20260902_south`,
`--fix SOUTHWEST=TX,OK --anchor FLORIDA=FL`), it was not preserved, and FRAME §0's "what is next"
item (i) is still open: *ask the sponsor which states, if any, are hand-drawn.*

That question needs a price list. This builds one: for each candidate region, what pinning it
costs, closed versus open, at every `k` from 14 to 22, in nats against the unpinned baseline.

**A new instance arrives with this work** — same descaled format, higher-quality opportunity data.
It supersedes `instance_descaled.json.gz` for every catalogue number. The existing instance is
kept for exactly one purpose: a byte-identical regression that proves the solver has not moved.

**The finding this is designed to expose:** each region has a natural `k` at which its opportunity
mass matches `total / k`, so pin cost is a V in `k` — which makes "which states are hand-drawn?"
and "what is `k`?" one joint decision rather than two sequential ones.

### Decisions already taken (do not relitigate)

| | |
|---|---|
| scenario set | pin-cost catalogue: 7 regions × {`fix`, `anchor`} = 14 runs, + unpinned baseline. Sponsor-map and deliberately-infeasible variants were considered and declined. |
| real total | sponsor-confirmed **≈ $18B** on the new instance (was ≈$13B on the old) ⇒ working target moves from k≈13 to **k≈18**. |
| `k` coverage | **`--k 14-22`** for every new-instance scenario, `--seeds 0-9` — same 9-value width and seed set as the old sweep, recentered on 18 instead of 12/13. §1's old-instance regression keeps `--k 8-16` unchanged (pinned to `sweep_20260902_s10`). |
| visualization | one power-diagram map per scenario at **k=18** (`--regions`), plus tables and cross-scenario charts. |
| old instance | regression check only. The catalogue is **new-instance only** — no dual catalogue, no old-vs-new comparison table. |
| file handling | the new instance arrives under a **new filename alongside** the old one, so the regression stays possible. |
| data cleaning | the raw export's `BLANK` pseudo-zip (vacant, no state) is dropped before use — see §2. |

---

## 1. Pipeline regression on the **old** instance — run before anything else

```bash
/Users/ntlee/projects/td/.venv/bin/python3 tools/run_draw.py instance_descaled.json.gz \
  --k 8-16 --seeds 0-9 --workers 8 --out battery/results/runs_<date>/_regress_old
```

→ **verify (load-bearing):** `sweep.csv` and all nine `k*/draw.csv` byte-identical to
`battery/results/sweep_20260902_s10`. If they are, solver and seeding are unchanged and every
new-instance number below is trustworthy. If not, **stop and report** — nothing downstream is
interpretable and the cause is out of this branch's scope. ~56 s. Then set aside; the old instance
plays no further part.

*Why this is worth 56 seconds:* a new dataset and an unverified pipeline are two unknowns, and you
cannot debug a surprising pin cost with both in play. This collapses one to zero.

## 2. ~~Accept and validate the new instance~~ Done

`instance_descaled_v2.json.gz` arrived alongside `instance_descaled.json.gz`. What was found and
done, for the record (re-derivable, but stated here so a fresh session doesn't redo it):

- `td.instance.load_descaled` → `td.instance.check_descaled` returned an **empty list** on the raw
  export. It gates four independent things: pointwise headroom `M_z ≥ max_i(S_i + θ(T_z − S_i))` at
  θ=0.40 (tol 5e-5, for the export's 6-significant-figure rounding); no negative `S` or `M`;
  `cand`/`S` agreement on contested zips; and **median `M` ≈ 1.0**, which is what catches a file
  exported without descaling — that would sail through everything else while silently wrecking
  solver conditioning.
- `d.summary()` on the raw export: 3,749 zips / 4,712 edges; 718 contested, 1,447 uncontested, 17
  vacant, 1,567 untapped; 114 reps (three new: `R0111`–`R0113`); total descaled `M` 8,524.5 — a
  3.1× increase over the old instance's 2,745.6. Eight states appear that the old instance did not
  (`AK, HI, IA, ID, MS, MT, NE, NM`); none were dropped, so no region definition loses a state.
- Gazetteer coverage on the raw export: 3,707 of 3,749 placed by coordinate (42 missing, up from 6
  on the old instance) — the rest are placed by state via `channel.place_by_state`.

**Finding, fixed rather than just flagged: the `BLANK` pseudo-zip.** One node in the raw export is
literally named `"BLANK"` — vacant (`M=1.248`, `S_free=1.248`, no candidates) and, unlike every
real zip, carries **no `state` field at all**, so it can't be placed by `place_by_state` the way
the other 41 uncoordinated zips can. It is a data-quality artifact, not a real ZIP, and was
**dropped**: the untouched export is kept as `instance_descaled_v2.raw.json.gz` for provenance,
and `instance_descaled_v2.json.gz` (used by every command below) is the cleaned file — 3,748 zips,
4,712 edges (no edges touched `BLANK`), 16 vacant, 41 gazetteer-missing, total `M` 8,523.2.
`check_descaled` is clean on the cleaned file too. This was a targeted data edit to the instance
file, not a change to `td/instance.py` or any loader — the "no change to `td/` or `tools/`" rule
below still holds.

**If `check_descaled` reports problems, stop and report** rather than cataloguing an invalid
instance — it did not, but this still gates any future re-export.

**Resolved (was "flag, not resolve"): the real dollar total.** A descaled instance carries no
currency scale, so this needed the sponsor's number rather than a computation. The sponsor
confirmed the new instance's real total is **≈ $18B**, so the working target is **k≈18**
(was k≈13 on the old $13B instance). The k-sweep for the new-instance catalogue is recentered to
`--k 14-22` (§3–§7) — still a range, not a single asserted k, for the same robustness reason the
original 8–16 sweep was wide.

## 3. Regions — recomputed, not redefined

| region | states |
|---|---|
| CALIFORNIA | CA |
| TEXAS | TX, OK |
| NEWYORK | NY |
| MIDWEST | IL, MO, MN, WI, IN, MI |
| CAROLINAS | NC, SC, VA |
| SOUTHWEST | AZ, NV, UT, CO |
| FLORIDA | FL |

**Recomputed on the cleaned new instance** (total M 8,523.2; k=18 target 473.5) — these are the
numbers the artifact reports, not the old-instance table this section used to carry:

| region | M | k-equivalents (k=18) | natural k |
|---|---|---|---|
| CALIFORNIA | 1,953.8 | 4.13 | 4.4 |
| TEXAS | 972.1 | 2.05 | 8.8 |
| NEWYORK | 849.6 | 1.79 | 10.0 |
| MIDWEST | 876.5 | 1.85 | 9.7 |
| CAROLINAS | 535.2 | 1.13 | 15.9 |
| SOUTHWEST | 606.8 | 1.28 | 14.0 |
| FLORIDA | 661.9 | 1.40 | 12.9 |

**Finding: at k=18, every region is oversized as a single district**, not just CALIFORNIA as on
the old instance — every k-equivalent above is >1. CALIFORNIA remains the tightest constraint
(natural k 4.4, far below the 14–22 sweep), but CAROLINAS and SOUTHWEST are now the closest to
fitting (k-equivalents 1.13 and 1.28), a different ranking than the old table's. This is reported
as a finding, not resolved by regrouping — see below.

**Definitions stay fixed.** Re-tuning a grouping so it lands on target would be curve-fitting the
very thing the catalogue measures. If the new data pushes a region's k-equivalent outside what
k ∈ [14,22] can reach, report it as a finding — as CALIFORNIA already is: at natural k 4.4 it
cannot be one district at any `k` in range, and pins are state-grain only (FRAME §8's A12 grain
question). Pricing that limit explicitly is why it stays in.

Any state present in one instance and not the other is called out before the run; `_check_states`
rejects an unknown state outright.

## 4. Scenario specs — `docs/artifacts/runs/scenarios/*.json`

One JSON per run in `load_scenario`'s format, named `<region>_fix.json` / `<region>_anchor.json` —
14 files. Committed specs, not shell history. Names are uppercase and must not match
`_SOLVER_NAME_RE` (`D07`-style); all seven are safe. `load_scenario` also rejects a name defined
twice and a state pinned to two districts.

## 5. Run the catalogue — `docs/artifacts/runs/run_all.sh`

The unpinned baseline plus each spec:

```bash
/Users/ntlee/projects/td/.venv/bin/python3 tools/run_draw.py instance_descaled_v2.json.gz \
  --scenario docs/artifacts/runs/scenarios/<s>.json \
  --k 14-22 --seeds 0-9 --workers 8 --out battery/results/runs_<date>/<s>
```

Same `k` range and seeds throughout — that is what makes Σ log M comparable across scenarios at
fixed `k`. ~56 s per run measured, ~14 min for 15. Output is gitignored (`battery/results/`).

→ verify: every run reports 0 unstaffed districts, and district masses summing to the instance
total. A scenario leaving a district unstaffed is a finding to surface, not a row to bury.

*The metric, and why it is exact:* Σ log M is not comparable across `k` (more districts, more
terms), but at fixed `k` every scenario partitions the same total into the same number of parts,
so the difference against the unpinned baseline is a pure additive cost in nats. This is the
scale-invariance argument in `CLAUDE.md`: a global rescale shifts `Σ log g_i` by `n·log κ`, the
same constant for every partition, so differences survive descaling untouched.

## 6. Maps — one per scenario at k = 18

```bash
/Users/ntlee/projects/td/.venv/bin/python3 tools/us_maps.py instance_descaled_v2.json.gz \
  --out figures/runs_<date>/<s>/ --regions battery/results/runs_<date>/<s>/k18/draw.csv
```

`--regions` is the power diagram (`district_regions.png`); `--regions-voronoi` is the superseded
zip-catchment fill and is deliberately not used. `us_maps.py` also writes four base figures into
`--out` — delete them (`figures/` is tracked as of `72e5f07`; don't commit 15 copies of
`opportunity.png`). Keep the new instance's `opportunity.png` **once**, at `figures/runs_<date>/`,
as the visual record of what changed in the data. ~3 s per map with the gazetteer cached.

Known cosmetic risk: `us_maps.color_districts` is a greedy colouring over a 12-colour palette
(`QUAL`), so two adjacent districts can share a hue at any `k` — the `SOUTHWEST`/`D07` collision
at k=13 already noted in HANDOFF's open items is one instance; k=18 has one more district and is
no less exposed. Report it if it makes a map unreadable; do not widen scope to fix the palette.
Both district figures share `draw_palette`, so the two renderings cannot drift.

**Never write under `battery/figures/`** — primary artifacts of the superseded battery, and not
carried into these worktrees.

## 7. Generator — `docs/artifacts/runs/build_artifact.py`

Reads every `metrics.json` and `sweep.json`, embeds each map as **lossless WebP**, writes one
self-contained HTML file. Nothing typed by hand.

*Why lossless:* the k-Sweep tested lossy and rejected it — at q90 the power-diagram borders and
labels reach max channel error 110. PSNR 40.2 dB hides this because the error concentrates on hard
edges, not texture. The `assets` capability is not available on this account, so images are data
URIs; budget accordingly (16 MB rendered cap, ~275 KB per map, 15 maps ≈ 4 MB).

Reuse the National Channel k-Sweep's stylesheet verbatim so the two artifacts read as one family:
IBM Plex Sans/Mono, the token set with three theme blocks (`:root`, then
`@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`, then
`:root[data-theme="dark"]`), `table.num` with `font-variant-numeric: tabular-nums`, hand-emitted
SVG charts with `<title>` tooltips. Read the published source first:
`Artifact(action:"read", url:"https://claude.ai/code/artifact/c007d61d-c753-4151-9026-2288b9d5eb38")`
— it saves the full HTML to a local file. Load the `artifact-design` and `dataviz` skills before
writing the page.

Structure:

- **Instance header** — what the new data is: zips, reps, total M, node classes, gazetteer
  coverage, per-state geometry, and how it differs from the 2026-09-01 export. A reader must know
  which dataset produced every number below.
- **Headline table, k = 18** — per scenario: region, mode, states, pinned M, pinned vs target,
  spread of the *unpinned* districts, Σ log M, Δ nats vs baseline, stage-2 value, Δ.
- **Chart A** — pin cost at k=18, grouped bars, `fix` against `anchor` per region.
- **Chart B** — pin cost (Δ nats vs baseline) against `k`, one line per region. This is the V, and
  the chart the artifact exists for.
- **Chart C** — the pinned district's deviation from target against `k`, one line per region; each
  crosses zero at that region's natural `k`. The sponsor-facing reading of B.
- **15 sections**, one per scenario: the k=18 power diagram, a nine-row `k` table, and the k=18
  per-district table from `summary_rows` (district, mode, zips, M, vs target, top state +share,
  n_states, `max_zip_share`, `median_zip_M`, rep, stage-2 gain) with `mode` marking the pinned row.
- **Reproduce** — the exact commands, naming the instance file.

Assertions the generator enforces, failing loudly: district masses sum to the instance total in
every run; `n_unstaffed == 0` everywhere; `n_fixed`/`n_anchor` in each `sweep.json` match its spec
file; every section's `instance` path is the new instance.

→ verify: open locally, check both themes, then publish with `Artifact` — a **new** artifact with
its own URL; it must not touch `c007d61d`. Give it a favicon on first publish and keep the title
stable across redeploys.

## 8. Record and commit

- `docs/RUNS.md` — the new instance's provenance and validation result, the region table with
  recomputed k-equivalents, what `fix` and `anchor` mean operationally, the measured cost per
  region, the natural-`k` reading, and the artifact URL.
- Commit on `wt/runs` and push. **Do not merge to `national-channel`** — the standing rule is
  ask-before-merging-to-hub, and hub restamping (`/state`: FRAME §0, `CLAUDE.md`, `HANDOFF.md`,
  memory) belongs to that approved merge, not to this branch. The new instance is gitignored and
  does not travel with the branch; `docs/RUNS.md` records where it came from.

---

## Critical files

| file | role |
|---|---|
| `tools/run_draw.py` | **unchanged** — `Scenario`, `load_scenario`, `parse_pin`, `expand_states`, `solver_k`, `run_sweep`, `complete`, `summary_rows`, `sweep_row`, `write_sweep` already do all of it |
| `tools/us_maps.py` | **unchanged** — `--regions` per scenario; `draw_palette` / `color_districts` own the colouring |
| `td/instance.py` | **unchanged** — `load_descaled` / `check_descaled` gate the new file |
| `td/solvers/centers.py` | **changed in `d7c4503`, with the user's sign-off** — `assign()`'s LP pinned to `method="highs-ds"` + an explicit `options` dict after the HiGHS hang (`docs/RUNS.md`); `draw(locked=)`, `residual_targets`, `seed_centers(initial=)`, `improve(movable=)` are what make pins work |
| `docs/artifacts/runs/scenarios/*.json` | new — 14 specs |
| `docs/artifacts/runs/run_all.sh` | new — the driver |
| `docs/artifacts/runs/build_artifact.py` | new — the generator |
| `docs/RUNS.md`, `docs/RUNS_PLAN.md` | new — the catalogue, and this plan |
| `figures/runs_<date>/**` | new, tracked — 15 power diagrams + the instance's opportunity map |

**No change to `td/` or `tools/`** *(as planned; in the event the HiGHS hang forced the one
`centers.py` change above, reported and signed off before it was made — `docs/RUNS.md`)*. The
scenario machinery is built, tested (16 tests in
`tests/test_run_draw.py`, 7 in `test_centers.py`) and regression-pinned by
`test_draw_without_locks_is_unchanged`; this task exercises it, it does not extend it. If the new
instance turns out to need loader or solver changes, that is a finding to report before writing
code, not a licence to edit the solver on this branch.

## Verification, end to end

1. ~~`.venv/bin/python3 tests/run_all.py` → 184 pass, 0 fail.~~ Done.
2. ~~Old-instance no-pin run byte-identical to `sweep_20260902_s10`~~ Done — the check that makes
   every other number meaningful.
3. ~~`check_descaled` clean on the new instance; summary and per-state diff reported.~~ Done
   (§2) — including the `BLANK` pseudo-zip fix.
4. All 15 runs (`--k 14-22`): 0 unstaffed, masses sum to total; generator assertions pass.
5. Artifact published, renders in light and dark, under 16 MB.
6. `wt/runs` clean and pushed; hub untouched.

## Reference — where to read more

- `docs/FRAME.md` §0 — the resume point and the state narrative. §6 carries measured rows.
- `HANDOFF.md` — fast orientation, the "Starting a track" checklist, published artifact IDs.
- `CLAUDE.md` (worktree) — the model on one page, the two stages, the trap list, code inventory.
- `docs/CHANNEL.md`, `docs/MODEL.md` — the problem and the N-way model.
- k-Sweep artifact `c007d61d-c753-4151-9026-2288b9d5eb38` — the design to match.
- Atlas artifact `1f2cddd9-b98b-4213-83ea-784566147c6a` — the certified k=13 draw.
