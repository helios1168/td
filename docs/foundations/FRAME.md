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

## 0. Revisions

- rev. 2, 2026-09-02 — second framing pass (§8 A11–A13, §9 EF1 vacuity, §10 Q8–Q12).
- rev. 1, 2026-09-02 — first framing pass, written after the work.

**Project state is not in this file.** Resume from `STATE.md` (`## Now`, `## Next`); the
history of every earlier state entry, including the ones that used to sit here, is
`docs/STATE_LOG.md`. This section records framing revisions only.

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
| zips | v1 **1,229** → **v2 3,748** | export; v2 2026-09-04 | v1 is a strict subset of v2 |
| — contested / uncontested / vacant / untapped | v1 675 / 477 / 2 / 75 → **v2 718 / 1,447 / 17 / 1,567** | export meta `cand_histogram` | **the contested set barely grew (675 → 718); v2's gain is untapped market.** Untapped is 2.9% of v1's opportunity and **15.7% of v2's** |
| distinct wholesalers | v1 **111** → **v2 114** (all 111 retained) | export | 114 → ~18 is a 6.3:1 selection ratio |
| ~~total opportunity~~ | ~~**≈ $13B**~~ → **superseded 2026-09-04: ≈$9.6B for v1** | export | The sponsor confirmed **≈$18B for v2**, and the two descaled exports pin `D_v2/D_v1 = ×1.8814`, so v1's true total was ≈$9.6B and the $13B was overstated by ≈×1.36. **v2 ≈$18B is the live figure.** |
| ~~⇒ territories `k`~~ | ~~**13** at $1B~~ → **`k = 18`** on v2 | arithmetic | v1's `k = 13` followed from the overstated $13B; the consistent v1 sizing was `k ≈ 10`. Every wave-1 result is scoped to v1 at k = 13. |
| footprint concentration | west 33.2% · east 31.0% · TX 11.5% · FL 6.7% · ~18% elsewhere | export | national, not four islands — the earlier premise was wrong |
| components of the sold-zip graph | **547**; largest 5.1% of M; 68% of M in sub-1% crumbs | export | why contiguity was dropped |
| largest single zip | 10017 at **1.07%** of total M ≈ 14% of one territory | export | granularity is benign; near-perfect balance is reachable |
| **aggregate saturation** Σ(booked)/Σ(opportunity) | v1 **41.9%** (median zip 46.8%, p90 110%) → **v2 29.6%** | `REVIEW_GROMOV` R1 measured on v1; v2 measured 2026-09-04 | the load-bearing correction — existing books move the map a lot. **On v2 it decomposes: 41.6% → 34.5% on the shared zips (opportunity revised up ×1.226, book flat at ×1.016), then → 29.6% from the 1,567 untapped new zips. R1's premium arithmetic is stale at v2.** |
| hold-vs-not swing in a wholesaler's valuation of a zip | **≈ 42%** (assumed 6.7%) | ibid. | continuity is a first-order term, not a tilt |
| incumbency premium as a share of total welfare | **≤ ≈ 25%** (assumed ~6%) | ibid. | ~3.7 nats of swing, unexplored |
| achieved balance spread | v1/k=13 0.642% drawn / **0.781%** placed → **v2/k=18 0.060% drawn / 1.368% placed**, max deviation `δ₀ = 0.9970%` | `battery/results/draw_k13_20260901`; `draw_k18_v2_20260904` (seeds 0–9, winner seed 2) | balance is solved on both; v2's `δ₀` is 2.5× v1's 0.39%, expected at 3× the zips and k=18 |
| distance to the analytic balance ceiling | **4.51e-5 nats** (portfolio best: 2e-6) | `cert_draw` | four orders below the premium term |
| portfolio staffing spread across 5 seeds | 7.1e-2 nats | `score_draws` | the effort ledger's middle term |
| compactness headroom | a **8.53%** more compact assignment exists in the same balance band (152 relabels); power-diagram bound independently gives 8.22%, with **132 of 1,223** zips outside their own cell | pinned-centers MILP; `cert_power_diagram` | open question 1, in one number |
| acceptance floors | tier 1 `1e-8` nats · tier 2 `5e-3` nats | `td/solvers/base.py:72,81` | the cells-vs-dots gap (4.66e-5) sits **below** tier 2 |
| **premium ladder** on the committed draw, share of total book | v1/k=13 `P₀` 37.82% · `P*(A)` 37.82% · `P_S` **51.43%** · `P₁₃` 52.34% · `P_free` 79.44% → **v2/k=18 41.53% · 41.53% · 54.42% · 59.27% · 84.17%** | `MODEL_U7-meas` §6, `battery/results/meas_20260903`; **v2 `meas_v2_20260904`** (2026-09-04) | matching gap **0 on both** (stage 2 is already right); map gap v1 13.6% ≈ 0.640 nats → **v2 12.9% ≈ 0.663 nats**; **roster gap v1 0.9% ≈ 0.043 nats → v2 4.85% ≈ 0.249 nats, 5.8×** — on v2, *which reps staff the channel* is worth a quarter nat, which raises U11-roster's priority |
| **EG bound at the delivered roster** | v1 `EG_{S₁₃}` **60.6974** vs `V` 59.9375 → **0.760 nats**, bracket 7e-15 → **v2 `EG_{S₁₈}` 96.532152 vs `V` 95.755192 → 0.776960 nats**, bracket 5.98e-9 | `MODEL_U1-cert` P4, `VERIFY_U1-cert`; **v2 `u8_band_v2_20260904` gate** | the first bound ever on the term the business signs; the gain is bought with balance — the EG vertex's `M`-spread is ≥ 50% on v1 and **57.4%** on v2 |
| **band frontier / D1′** — is the premium soft under a balance band? | v1/k=13 gap **0.683 → 0.760 nats** over `δ ∈ [0.0039, 0.33]` → **v2/k=18 gap 0.724507 → 0.775786 over `δ ∈ [0.00997, 0.33]`** | `MODEL_U8-band`, `battery/results/u8_band_20260904`; **v2 `u8_band_v2_20260904`**, `figures/u8_band_v2/frontier.png` | **NOT SOFT on both**, 137–147× the 5e-3 floor on v1 and **146–155× on v2**; **no `δ*` exists** on either — the gap is already large at `δ₀`, so the slope never decides it. The band was never what binds: v2's whole curve buys back **0.0513 nats across a 33-fold widening** (v1: 0.077 across 84-fold) |
| **roster-free premium screen** `max_S EG_S ≤ k·log((B_tot + w·P₁₃)/k)` | **60.8025** → no coverage by *any* 13 of 111 beats the delivered draw by more than **0.865 nats**; the screen is 0.064 above `EG_{S₁₃}`, so it is tight | `DOMAIN_optimization` §2.14 (★), computed 2026-09-03 (`B_tot` 1145.81, `w` 0.42) | replaces the 9.65-nat ceiling as the unconditional bound; the delivered draw's own max deviation is 0.39% (seed 9: 0.62%) |
| certificate collapse into the EG dual | **3 of 4** (ceiling, pinned-centers MILP, power diagram); the integer balance floor is primal-only | `VERIFY_U1-cert` P2 | partial refutation of `DOMAIN_optimization` §3 / `LENS_GROTHENDIECK` descent 3 |
| split units at an EG vertex | `≤ k − 1` heterogeneously (the MBB face); measured 10, `M(F)` 2.4–3.2% of `T`, vertex-dependent | `VERIFY_U1-cert` P3 | the a-priori value bound is vacuous; quote only with the split masses |
| **realised-gain spread** across the selected | v1 **60.65%** (seed 9: 59.47%) against a 0.781% `M`-spread → **v2 60.17%** against 1.368% | `MODEL_U7-meas` U1; v2 `meas_v2_20260904` | A0's soft kill (LENS_GROMOV U1) fires on both, and the ratio is **stable across a 3× instance change**: the headline balance number measures territory size, not what each rep gets |
| zips contested among the selected | v1 **83** of 675, **6.12%** of `M` → **v2 124** of 718, **7.82%** | `MODEL_U7-meas` U4; v2 `meas_v2_20260904` | the redraw has little *choice*; its premium comes from moving uncontested book, not from adjudicating overlaps |
| `corr(T_z, M_z)` | v1 0.650 pooled (per rep 0.23–0.93) → **v2 0.745** (per rep 0.11–0.95) | `MODEL_U7-meas` U8; v2 `meas_v2_20260904` | the premium ladder bites moderately (DOMAIN_optimization §2.3's escape clause does not fire) |
| tests | **222** pass, 0 fail | `tests/run_all.py` at `82dbe98` (`wt/A1`; 218 at `fd619c7`, 184 at `74eff38`) | the regression surface |
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
| ~~`k = 13` at a $1B target~~ → **`k = 18` on v2** | **re-settled** | 2026-09-04 | user | The sponsor confirmed ≈$18B (not to be re-derived). The old $13B/k=13 came from an overstated total — the descaled ratio ×1.8814 puts v1 at ≈$9.6B, i.e. `k ≈ 10`. Assumption A1 still attached, now against $18B. |
| ~~Instance sizing: 1,229 zips / 111 wholesalers / ~$13B~~ → **3,748 zips / 114 wholesalers / ≈$18B** (v2) | **re-settled** | 2026-09-04 | user | `instance_descaled_v2.json.gz` supersedes v1. v1 is a strict subset; the growth is overwhelmingly **untapped** market (untapped zips 75 → 1,567; contested only 675 → 718). Supersedes `CHANNEL.md` §6 and the 2026-09-01 row. |
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
