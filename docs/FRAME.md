# The national channel territory problem — problem statement

**Date:** 2026-09-02 (rev. 2, branch `national-channel`) · **Framework:** 0.1-dev · **Reads:** `docs/CHANNEL.md`, `docs/MODEL.md`,
`docs/DATA.md`, `docs/REVIEW_GROMOV.md`, `docs/RESEARCH_FINDINGS.md` (§0, §1–5, §7–9), `CLAUDE.md`,
`td/solvers/base.py`, `docs/channel_note/channel_note.tex` (§2–6, §11), `td/channel.py`,
`td/solvers/centers.py`; on `wt/workflow-dryrun`: `LENS_GROTHENDIECK.md`, `LENS_GROMOV.md`,
`BRIEF.md`, `DOMAIN_optimization.md` §2, `LIT_economic-theory.md` §0 · **Supersedes:** `CHANNEL.md` §6 (the 72-rep / $6.2B / k≈6 /
"midwest uncovered" sizing — superseded by the real export) and §7's illustrative ceiling
table (computed on the superseded $6.2B split, and on a contiguity requirement since dropped);
`CHANNEL.md` §3's "contiguous" wording in the stage-1 row. Everything else in `CHANNEL.md`,
`MODEL.md` and `DATA.md` stands.

---

## 0. Resume — read this first in a fresh session

**State on 2026-09-02 (latest, branch `national-channel`, head `0d0ea96`, pushed — `cf4170b` was
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
k ≤ 10. Maps for k = 10, 13, 16 are tracked under `figures/sweep_20260902_s10/k<kk>/`
(`districts.png`, `district_regions.png`). Artifact, sweep table + charts + maps:
https://claude.ai/code/artifact/c007d61d-c753-4151-9026-2288b9d5eb38 (the 2026-09-01 atlas
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

## 1. The business problem, in the owner's words

The business is standing up a **new "national" channel**. The two largest firms are being
carved out of the existing financial-institutions and wirehouse channels and given their own
dedicated coverage. Somebody has to say, before the channel launches, **which parts of the
country each new territory covers, and who covers it** — with territories of roughly equal
opportunity, about **$1B each**, so that no wholesaler is handed a territory they cannot
work and none is handed one they cannot lose money in.

Nothing exists yet. There is no incumbent national-channel alignment to adjust; this is a
first draw over a national footprint, from the two firms' business as it sits today plus
market sizing for where it could go.

## 2. Actors and the decision

| | |
|---|---|
| **Decides** | National sales leadership (the channel sponsor). Nicolas Lee delivers the recommendation and the evidence; leadership signs the map and the roster. |
| **Affected** | The **111** wholesalers holding book at the two firms — around **13** are selected into the channel and the rest keep covering the remaining firms in the existing FI/wirehouse channels; the two carved-out firms' branch relationships, which move with the coverage; the FI/wirehouse channel leaders losing those accounts. |
| **What is actually chosen** | (a) the **number of territories**, (b) a **partition of the footprint** — every zip carrying sales lands in exactly one territory, (c) the **roster**: which wholesalers staff the channel and which territory each one gets. |
| **How often** | Once at stand-up (the decision now), then re-examined when the opportunity sizing refreshes — assumed annual, see §8. Between refreshes the map is expected to hold; churn in the roster is handled by replacement, not redraw. |
| **Reversibility** | Low. A territory map that is redrawn a quarter after launch costs relationships at the two firms and credibility with the 98 wholesalers not selected. This is a one-shot decision that must be defensible line by line. |

## 3. Objective, and what "solved" means

**In words.** Cut the national footprint into a small number of territories carrying roughly
the same amount of opportunity; put a wholesaler on each who already has relationships inside
it; and do not starve anybody. Equal opportunity is the stated goal, but it is not the only
one — a perfectly balanced map that hands a wholesaler a territory containing almost none of
their existing business is worse than a slightly uneven map that does not.

**The acceptance test — what a business owner signs.** All six, or it is not done:

1. **Count and size.** Exactly `k` territories, each within a stated band of `$total/k`.
   *Achieved:* 0.78% spread at k=13, comfortably inside any plausible band.
2. **Coverage.** Every zip carrying sales is in exactly one territory; no zip is orphaned and
   none is in two. *Achieved:* 1,229 of 1,229, including the 6 without coordinates.
3. **Roster.** Every territory has exactly one named wholesaler; no wholesaler has two;
   the unselected are named as *not selected for this channel*, not as released.
   *Achieved:* 13 of 13 staffed, 13 of 111 selected.
4. **Continuity, reported per person.** For each selected wholesaler, the share of their
   existing book that falls inside the territory they are given, and the share that does not.
   **Not yet produced at the individual level** — this is the largest gap between what has
   been computed and what would be signed. At 41.9% saturation it is the number the room
   will ask for first.
5. **A distance-to-best in business units.** A stated bound of the form "no achievable map
   beats this one by more than X% of a territory's opportunity / more than $Y of misplaced
   book". Four certificates exist and a fifth is specified, but they are denominated in
   **nats**; nobody signs a nat. Translation is outstanding.
6. **Reproducible and auditable.** The map regenerates from the export by one command, with
   the certificates recomputed, on a machine that never sees a dollar amount.

**Baseline to beat.** The honest comparison is a **hand-drawn state-grouped alignment** — the
way sales ops would do it without this work: group states until each bucket looks like $1B,
then assign the wholesaler with the most book in each. That baseline has never been
constructed, so the headline claim ("this is better than what we would otherwise have done")
is currently unevidenced. Constructing it is cheap.

**Tolerance.** Balance: a spread band of ±10% would be generous and is already beaten by an
order of magnitude, so balance is *not* the binding tolerance — it is solved. The binding
tolerances are (i) how much continuity loss the business will accept in exchange for balance,
which has never been elicited, and (ii) the programme's own acceptance floor for certified
claims: tier 1 `1e-8` nats, tier 2 `5e-3` nats (`td/solvers/base.py:72,81`).

## 4. Constraints

**Hard**

| constraint | source |
|---|---|
| Every zip carrying sales is assigned to exactly one territory. | Partition requirement — a zip cannot be covered twice. `docs/CHANNEL.md` §1 |
| One wholesaler per territory, at most one territory per wholesaler. | Coverage rule; `docs/CHANNEL.md` §3 |
| More wholesalers than territories (111 vs ~13), so staffing *selects*. | Real instance, 2026-09-01 export |
| No dollar amount, no PII and no firm identity leaves the work machine. | `docs/DATA.md`; confidentiality regime |
| The vacancy ("filler") key holds real book but is **not** a person and can never be given a territory. | `docs/DATA.md` §"Vacancies" |

**Soft**

| constraint | source |
|---|---|
| Roughly equal opportunity per territory (~$1B). | The business ask, `docs/CHANNEL.md` |
| Where there is slack, leave business with the wholesaler who already has it. | Welfare decomposition, `docs/CHANNEL.md` §2 |
| Territories should be geographically coherent enough to be worked by one person. | Coverage practicality; the compactness term |

**Dropped, with reason**

| dropped | reason |
|---|---|
| **Adjacency contiguity** — territories need not be connected regions. | The zips carrying sales form **547 components**; the largest is 5.1% of total opportunity and 68% of opportunity sits in sub-1% crumbs. Contiguity over sold zips is not a meaningful requirement. (Caveat: on the *full* ZCTA graph including unsold zips it may be recoverable — `RESEARCH_FINDINGS` §9-H.) |
| A hard $1B ± band as an explicit constraint. | Balance is already the objective's own consequence on a common measure; imposing it as a band risks the equalisation pathology (trap 2). |

**Policy / governance**

- Selection must not be gameable by a wholesaler inflating reported book. The 98 not selected
  have maximal incentive to inflate; audited system-of-record revenue is the intended
  defence (`RESEARCH_FINDINGS` §9-G). **Not yet a written invariant.**
- The recommendation must be explainable to the affected wholesalers, not just correct.

## 5. Data actually available

| source | grain | refresh | confidentiality | real / synthetic |
|---|---|---|---|---|
| Internal sales system of record — booked production by wholesaler × zip | ZCTA × rep | assumed annual (§8) | PII and firm masked upstream; exported as **shares in [0,1]**, never dollars | **real**, descaled |
| Opportunity / market sizing by zip (`M_z`) | ZCTA | assumed annual (§8) | exported as `m_rel = M/median(M)`; the divisor never leaves | **real**, descaled |
| Vacancy ("filler") book — territories with no official wholesaler | ZCTA | with the above | same | **real**; 2 zips |
| Census Gazetteer ZCTA centroids | ZCTA | public, static | none — public | **real**, public |
| ZCTA adjacency (TIGER) | ZCTA pairs | public, static | none | **real**; built, currently unused |

**Route.** `tools/instance_export/export_instance.py` runs read-only on the work machine and
emits shares plus `m_rel`; guards refuse to write a currency amount or the divisor.
`td/instance.py` reads it back. Everything downstream is scale-free — rescaling shifts the
objective by the same constant for every partition, so the descaled instance and the real one
have identical optima, gaps and certificates.

**Known defects in the data as it stands**

- The 2026-08-31 sizing (2,232 zips, 72 reps, $6.2B) was a **double-count in the source
  pull**, corrected by the user 2026-09-01. Anything quoting those figures is stale.
- **6 of 1,229 zips have no coordinates**; they are placed by state after the draw, which is
  what moves the spread from 0.642% to 0.781%.
- Export rounds to **6 significant figures**; the loader carries a matching tolerance.
- The exporter has a `--repair-headroom` path, i.e. some zips arrived with booked production
  exceeding their sized opportunity. The repaired count is not carried in this statement.
- `instance_descaled.json.gz` is **not present in this worktree** (gitignored; it lives at the
  main checkout root). Nothing here can be re-measured without it.

## 6. Numbers that bound the problem

| quantity | value | source | why it matters |
|---|---|---|---|
| zips carrying sales | **1,229** | export, 2026-09-01 | the decision's size |
| — contested / uncontested / vacant / untapped | 675 / 477 / 2 / 75 | export | only 675 are genuinely contested |
| distinct wholesalers | **111** | export | 111 → ~13 is an 8.5:1 selection ratio |
| total opportunity | **≈ $13B** | export | sets `k` |
| ⇒ territories `k` | **13** at $1B | arithmetic | the count is not itself in question |
| footprint concentration | west 33.2% · east 31.0% · TX 11.5% · FL 6.7% · ~18% elsewhere | export | national, not four islands — the earlier premise was wrong |
| components of the sold-zip graph | **547**; largest 5.1% of M; 68% of M in sub-1% crumbs | export | why contiguity was dropped |
| largest single zip | 10017 at **1.07%** of total M ≈ 14% of one territory | export | granularity is benign; near-perfect balance is reachable |
| **aggregate saturation** Σ(booked)/Σ(opportunity) | **41.9%** (median zip 46.8%, p90 110%; 48% of opportunity sits above 30%) | `REVIEW_GROMOV` R1, measured | the load-bearing correction — existing books move the map a lot |
| hold-vs-not swing in a wholesaler's valuation of a zip | **≈ 42%** (assumed 6.7%) | ibid. | continuity is a first-order term, not a tilt |
| incumbency premium as a share of total welfare | **≤ ≈ 25%** (assumed ~6%) | ibid. | ~3.7 nats of swing, unexplored |
| achieved balance spread | 0.642% drawn / **0.781%** placed | `battery/results/draw_k13_20260901` | balance is solved |
| distance to the analytic balance ceiling | **4.51e-5 nats** (portfolio best: 2e-6) | `cert_draw` | four orders below the premium term |
| portfolio staffing spread across 5 seeds | 7.1e-2 nats | `score_draws` | the effort ledger's middle term |
| compactness headroom | a **8.53%** more compact assignment exists in the same balance band (152 relabels); power-diagram bound independently gives 8.22%, with **132 of 1,223** zips outside their own cell | pinned-centers MILP; `cert_power_diagram` | open question 1, in one number |
| acceptance floors | tier 1 `1e-8` nats · tier 2 `5e-3` nats | `td/solvers/base.py:72,81` | the cells-vs-dots gap (4.66e-5) sits **below** tier 2 |
| tests | **151** pass, 0 fail | `tests/run_all.py` at `937460e` | the regression surface |
| decision horizon | one stand-up; re-examined on data refresh | §8 assumption | rules out anything needing quarterly re-solve |

**What these bound.** At 1,229 units and k=13 the instance is *small* by the current
districting literature (all-US instances are certified at county level; 175k vertices with
inexact contiguity). Size is not the constraint. The constraints are the log objective, the
shattered graph, and — newly — that the largest term in the objective has never been
optimised or bounded.

## 7. Out of scope

| out | why |
|---|---|
| **Compensation, quota and comp-plan design** for the new channel | A separate business decision with its own owner; the territory map is an input to it, not a substitute. |
| **Transition packages** for the ~98 not selected | Same — an HR/comp decision. Noted because the map creates the need. |
| **Restoring adjacency contiguity** | Dropped on evidence (§4). One experiment on the full ZCTA graph could reopen it; until then, out. |
| **Any dollar-denominated artifact** | Confidentiality. Everything here is share-space and scale-free by construction. |
| **The two-player merger programme** (harness, S0/S1/S2, `scip_tree` at 135 zips) | Different problem; preserved intact on branch `contiguity-harness`. Its engines are borrowed, its framing is not. |
| **Non-equal territory entitlements** (senior wholesalers sized larger) | Not asked for. Would change the objective, not just the parameters. |
| **Forecasting** what each territory will actually produce | The decision is an allocation of opportunity, not a revenue projection. |
| **Coverage design for the residual FI/wirehouse channels** | The carve-out's other half; a different owner's problem. |
| **Launch sequencing and communications** | Downstream of the signed map. |

## 8. Assumptions made here

Recorded rather than asked, per the unattended instruction.

| # | assumption | how to check it | owner |
|---|---|---|---|
| A1 | `k = 13` is settled arithmetic ($13B / $1B) and leadership will not move the $1B target. | Ask the sponsor whether $1B is a target or a constraint, and whether 12 or 14 territories are acceptable. One question. | user → sponsor |
| A2 | The ~98 unselected wholesalers are **not released** — they keep covering the remaining firms in the existing channels. Stage-2's "unmatched" output means *not selected for this channel*. | Confirm with the sponsor. If wrong, the objective gains a retention term and the framing of selection changes. Flagged as open since 2026-08-31 and still unconfirmed. | user → sponsor |
| A3 | The decision recurs roughly **annually**, on the opportunity-sizing refresh; nothing needs to re-solve quarterly. | Ask how often market sizing refreshes and whether territories are expected to move with it. | user → sponsor |
| A4 | Opportunity `M_z` is a trustworthy common measure — the same quantity, comparably estimated, in every zip. All balance claims rest on this. | Ask the source of the sizing and whether its methodology varies by region or firm. A regional bias in `M` biases every territory. | user |
| A5 | "Roughly equal" means equal **opportunity**, not equal existing book, equal account count or equal travel burden. | One sentence to the sponsor. Equal-book would be a different problem entirely. | user → sponsor |
| A6 | Geographic coherence matters for coverability but has **no stated threshold** — no maximum drive time, no state-splitting rule, no airport constraint. | Ask whether any operational rule exists (e.g. "don't split a state", "must be within one time zone"). If one does, it is a hard constraint currently missing from §4. | user → sponsor |
| A7 | Books are reported honestly for the purpose of the current draw; incentive-gaming is a governance risk to close before wholesalers see the mechanism, not a defect in the present data. | Compare reported book against audited system-of-record revenue for the 111. | user |
| A8 | The measured 41.9% saturation is representative and not an artifact of the headroom repairs or of the double-count correction. | Recompute saturation excluding repaired zips and report both. Requires the instance, absent from this worktree. | programme |
| A9 | Territory-drawing may continue to be evaluated by how well it staffs (`score_draws`), pending the book-awareness decision — i.e. the mild existing breach of the "books enter at staffing only" invariant is tolerated for now. | The decision itself (§9, open). Until it lands, every published draw carries the breach. | user |
| A10 | 6 coordinate-less zips placed by state is acceptable; they carry no structural weight. | Report their share of total opportunity. If it exceeds ~0.5%, fix the coordinates instead. | programme |
| A11 | Every dollar of `M` is geographically attributable to a zip. The two carved-out firms are national firms with home offices; if part of their business is home-office / national-accounts (not worked from a geography), it belongs in a non-geographic bucket carved out *before* the draw, and the $13B / k=13 arithmetic changes. | Ask the sponsor whether the channel will have a home-office or national-accounts role, and what share of sized opportunity is HQ-driven. | user → sponsor |
| A12 | The zip is the grain the sponsor manages territories by. Sales ops may communicate and police territories by state, metro (CBSA) or firm branch; if so, the 132-dots question and much of the tie-breaking dissolve at the coarser grain and the zip map is derived, not signed. | Ask what unit a territory is described in on the signed document. | user → sponsor |
| A13 | One wholesaler per territory is a rule, not a default. The largest zip alone is ~14% of a territory; a dense metro could be team-covered (two reps, one territory) under a different rule, which changes the matching from an injection to a b-matching. | Ask whether any territory is expected to be staffed by more than one person. | user → sponsor |

## 9. Settled / open

| item | status | date | owner | why |
|---|---|---|---|---|
| The problem is greenfield balanced territory design, not the two-player merger problem | **settled** | 2026-08-31 | user | The carve-out has no bilateral overlap structure; the pair census does not apply. |
| `k = 13` at a $1B target | **settled** | 2026-09-01 | user | $13B total, from the corrected export. Assumption A1 attached. |
| Instance sizing: 1,229 zips / 111 wholesalers / ~$13B / national footprint | **settled** | 2026-09-01 | user | The real descaled export, after three user corrections to the source pull. Supersedes `CHANNEL.md` §6. |
| Adjacency contiguity is not required | **settled** | 2026-09-01 | user | 547 components. Reopenable only by the full-ZCTA-graph experiment. |
| Territories are drawn on opportunity, then staffed — two stages | **settled as a business constraint** | 2026-09-01 | user | Survives as "territories shall be opportunity-balanced"; the claim that it was *derived* was retracted at 41.9% saturation. |
| Staffing is exact and selects the roster | **settled** | 2026-09-01 | programme | Exact, milliseconds, 13 of 111. |
| A certified k=13 draw exists (0.781% spread, 13/13 staffed, 4.5e-5 nats under ceiling) | **settled** | 2026-09-01 | programme | Four certificates; 151 tests. |
| The territory map is a power diagram of its centers, with the duals as a solver-free certificate | **settled** | 2026-09-01 | programme | `937460e`; independently reproduces the MILP's 8.53% as 8.22%. |
| Real saturation is 41.9%, not the 5% assumed | **settled (measured)** | 2026-09-01 | programme | `REVIEW_GROMOV` R1, computed against the export. Invalidates the sizing paragraph that assumed it. |
| Balance is not the binding difficulty | **settled** | 2026-09-02 | programme | Solved to 4.5e-5 nats against a ~3.7-nat premium term. Effort is on the smallest term. |
| **Does territory-drawing get to see wholesaler books?** | **open — blocking** | 2026-09-02 | **user** | ~3.7 nats of value says yes; the incentive-safety invariant says no; audited system-of-record book is the likely escape. Everything about the premium term waits on this. |
| **The acceptance test in business units** (§3.5) — nats → dollars/book-share | **open** | 2026-09-02 | programme | Five certificates nobody outside the programme can read. Blocks presentation, not computation. |
| **Per-wholesaler continuity report** (§3.4) | **open** | 2026-09-02 | programme | The first question the room will ask; never produced. |
| **The hand-drawn baseline** (§3) | **open** | 2026-09-02 | programme | The "better than what we'd have done anyway" claim is currently unevidenced. |
| The 132 dots: adopt the power cells or keep the drawn map | **open** | 2026-09-01 | user, on programme's evidence | Nash-indistinguishable by the programme's own tier-2 floor; the deciding number is the staffing value of the cells map, not yet computed. |
| Who owns vacant (2) and untapped (75) zips | **open** | 2026-08-31 | user | They carry opportunity but no incumbent; the allocation rule is a business call. |
| How vacancy book is capitalised (`filler_capture`) | **open** | 2026-08-31 | user | The default is the no-change case, and is probably not the right answer. |
| Whether capture depends on *which* wholesaler is displaced (θ directionality) | **open** | 2026-08-31 | user | Currently one scalar. Directionality multiplies the identification problem. |
| Empty bundles / lexicographic tie-breaking | **open, but answerable from the literature** | 2026-09-01 | programme | The programme's own anchor citation already defines it; one paragraph and one test. |
| A2 — that the unselected are not released | **open** | 2026-08-31 | user → sponsor | Unconfirmed for two days; changes what staffing means if wrong. |
| Whether any operational coverage rule exists (A6) | **open** | 2026-09-02 | user → sponsor | If one does, §4 is missing a hard constraint. |
| The note's fairness claim at stage 2 (EF1 "survives the move") | **open** | 2026-09-02 | programme | Stage 2 is unit-demand — removing a wholesaler's only territory empties the bundle — so EF1 is vacuous there. `channel_note` §3 must restate the claim for the joint allocation only, or in swap-based form (`RESEARCH_FINDINGS` §9-G). Recorded in `CHANNEL.md` §0 on `national-channel`; not yet in the note. |
| Two `FRAME.md` copies on two branches | **settled** | 2026-09-02 | user | `wt/workflow-dryrun` merged into `national-channel`; one `FRAME.md`. |
| A11–A13 (home-office carve-out, decision grain, team territories) | **open** | 2026-09-02 | user → sponsor | Each is a one-question ask that changes the problem statement, not a parameter: A11 changes `k`, A12 changes the unit, A13 changes the matching's shape. |

## 10. Notes for the lenses (questions only)

1. The objective decomposes into a partition-invariant part, a balance part and an incumbency
   part. At 41.9% saturation the incumbency part is ~3.7 nats of swing against 1e-4–1e-2 nats
   of balance. **Is the two-stage separation still the right decomposition of this problem, or
   is it a decomposition of the small term?**
2. Balance was proved to be a consequence of the objective on a common measure. Saturation
   means the measure is *not* common — each wholesaler values the same zip differently, by up
   to ~42%. **What survives of the equal-size result when the measure stops being common, and
   is there a weighted or per-agent statement that replaces it exactly rather than
   approximately?**
3. Certificates exist for balance (analytic ceiling), for compactness at fixed centers
   (duals), and a lower bound for the joint map-plus-staffing value. **What is the natural
   upper bound for the incumbency premium, and is there a reason none has appeared?**
4. The programme's tier-2 acceptance floor (5e-3 nats) is two orders *above* the gap between
   the two candidate maps. **Is a tolerance that renders the main open decision undecidable a
   correctly calibrated tolerance, or is the floor measuring the wrong noise?**
5. Territory-drawing that reads reported books is unfixable against misreporting; territory-
   drawing that ignores them leaves ~25% of total welfare on the table. **Is there a
   formulation in which the drawing depends only on quantities a wholesaler cannot inflate,
   without discarding the continuity value?**
6. The footprint has 547 components on sold zips but is plausibly connected on the full ZCTA
   graph, where the connecting zips are exactly the ones carrying no book. **Is "the glue is
   the worthless part" a structural feature of this problem or an artifact of restricting
   attention to sold zips?**
7. Certificates are denominated in nats — a unit derived from the objective's own functional
   form. **Is there an invariant statement of distance-to-optimal in the problem's own units
   (opportunity, misplaced book) that does not pass through the logarithm?**
8. Fix the roster `S` (13 wholesalers). Maximising the utilitarian value `Σ_z u_{σ(z)}(z)`
   subject to equal-`M` territory masses is a **transportation LP** — the same LP `centers.py`
   already solves, with cost `−u_i(z)` (plus, optionally, the same `M_z d²` compactness term)
   in place of `M_z d²` — integral up to `k−1` split zips. It optimises the premium term
   *exactly* under the balance the business asked for, with no logarithm. **Is its value a
   new rung `P*_bal(S)` in the premium ladder between `P*(A)` and `P₁₃`, and is alternating
   it with the Hungarian step a coordinate ascent whose fixed points are what the joint
   formulation would find?**
9. The stages could run in the other order: select the 13 first (max-coverage / audited
   book, `P₁₃`), then draw the map around the selected wholesalers' book centroids as sites,
   reading only their normalised geographic profiles. **Does roster-first lose anything that
   draw-first keeps, and does it satisfy the inflation-invariance the incentive argument
   demands, by construction?**
10. Books and sizing both follow metros. **At the grain of metro areas (or of the two firms'
    branches), does the tie-breaking degeneracy that produces the 132 dots and the
    second-order-flat objective exist at all — and is the zip map then a derived artifact
    rather than the decision?** (A12.)
11. If some share of the sized opportunity is home-office business with no geography (A11),
    the common-measure argument is being applied to a quantity that is not partitionable.
    **What is the right treatment of non-geographic opportunity — a `k+1`-th territory, a
    pre-draw carve-out, or a per-territory credit — and how does each change `k`?**
12. With one wholesaler per territory the matching is an injection and the solver is
    Hungarian; with team coverage of a dense metro it becomes a capacitated `b`-matching,
    where Nash-welfare matching is NP-hard already at capacity 2 (`RESEARCH_FINDINGS` §4B).
    **Is exactness at stage 2 an artifact of a rule the sponsor has not actually stated?**
    (A13.)
