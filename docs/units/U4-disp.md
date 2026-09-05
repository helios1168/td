# Unit U4-disp — displacement as a certificate *(wave 2; the U0-lit gate has reported — launchable)*

**Status 2026-09-05.** Re-anchored to v2 / `k = 18` (`WAVE2_PLAN` §0c). The unit's **primary**
question is unchanged and still open: does a modulus `objective-gap ≥ φ(mass moved)` exist? Its
**secondary input is withdrawn** — see the premise box. Gates that used to hold it are gone: ★6 is
lifted in full (`BRIEF.md` §4 — units may read `instance_descaled.json.gz` and run code), and
U0-lit landed as `docs/LIT_optimization.md`, whose §9 (Q9) answers the gate: **no instance-specific
modulus exists in the literature**, so this stays a *proof* unit (size L), not the
citation-and-instantiation unit (size S) that ★6 held open. What the literature does supply is the
modulus's **name** — a Hölderian error bound / growth condition, `f − f* ≥ c·dist(·)^α`
(`bolte2017`), with `hoffman1952` the reason to expect the polyhedral exponent `α = 1` rather than
a generic `α = 2` (`drusvyatskiy2018`), and absence ledger row D recording the gap. Branch: from
`main`. See `docs/BRIEF.md` §4.

## ⚠ Premise change — the first-mover list this brief consumed no longer exists

The 2026-09-03 version of this brief opened: *"New inputs: the band duals `μ^±` … and the
first-mover zip list from `docs/units/U8-band.md`."* **That input is withdrawn**, on two grounds,
the second of which is not repairable by re-measuring.

1. **The v1 object dissolved.** At `k = 13` U8 reported **75 exact MBB ties carrying `2.90 %` of
   `T`** — a mass-bearing set of units genuinely indifferent between owners. On the live v2 run
   (`MODEL_U8-band` §10.6, §10.7 finding 3) `n_exact_ties = 0` and `tied_M_share = 0.0`. What
   remains is 25 ranked zips carrying `33.09` of `M` = **`0.39 %` of `T`**, all owned by just two
   reps (R0008 or R0021), with margins from `5.6e-7` to `2.5e-6` — near-ties, not ties, and an
   order of magnitude tighter than v1's while carrying a seventh of the mass. Substituting `0.39 %`
   for `2.90 %` would be enough if this were the only problem. It is not.
2. **The list is not a well-defined object.** `MODEL_U8-band` §9.7 finding 5 records degeneracy at
   **every** reported `δ`, and §10.6 confirms it on v2 (support `3773` against an expected `3781`,
   `diff = 8`). So `ν` is **one** dual optimum among many. The first-mover ranking is
   `max_i(u_i(z)/g*_i − ν_i M_z) − 2nd-max_i(…)` (`DOMAIN_optimization` §2.12): a function of `p`
   and `ν`, both of which sit on `VERIFY_U9-bandthm` §10.E's **non**-invariant list — "`g*` and `φ`
   are invariants; `p`, `ν`, the split set — and now `m` — are not" (quoted at
   `CODEVERIFY_U8-band` F1). `MODEL_U8-band` §10.6 draws the consequence itself: *"per the stop
   rule, `ν` is reported as **one** dual optimum and no first-mover ordering is named from it
   alone."* `DOMAIN_optimization` §2.12 predicted exactly this in its assumptions bullet:
   *"Multiplier uniqueness is **not met** … so `ν` is one of possibly many dual optima. The *bound*
   is unaffected (weak duality holds at any dual-feasible point); the *interpretation* is."*

**A reader may push back here, and should know where.** `MODEL_U8-band` §10.6 goes on to say the
near-tie *set* — R0008/R0021's 25 closest zips — "is the defensible object". That sentence is an
assertion about one `ν`; nothing in the record proves the set is invariant over the dual-optimal
face, and the LP that could have checked it (§10.A's minimisation over the exact dual-optimal set)
**was not run** (`MODEL_U8-band` §9.7 finding 6). This unit therefore treats the 25-zip set as
"computed at one dual optimum" and may cite it as an illustration, never as the object a bound is
proved about.

### The disposition chosen: **re-scope, do not block**

The unit is **not** blocked, and the reason is that the withdrawn input was never load-bearing for
the deliverable. U4's question is whether a modulus `φ` exists — a property of the value function
and the feasible set, settled by proof or by a clean absence, not by any zip list.
`DOMAIN_optimization` §2.4 calls the first-mover list a **"better input"**, an object to measure
against rather than a price vector to interpret. Losing a better *illustration* is not losing the
*premise*. Blocking U4 would stall what `DOMAIN_optimization` §8 Q3 still calls *"the plan's
highest-leverage unknown for FRAME §3.5"* on an auxiliary — the wrong trade.

The collapse lands exactly on the seam this unit already draws. U4 was always required to separate
the **descriptive** metric (free) from the **bound** (in question). Degeneracy destroys
*interpretive* dual content — which zip flips first — and leaves *bound-producing* dual content
intact, because weak duality holds at any dual-feasible point. So the re-scope is: **U4 keeps the
bound side and drops the interpretive side.**

**What U4 may consume, and why each survives degeneracy**

| object | source | status under degeneracy |
|---|---|---|
| displacement between **two named maps** (zips moved and `M`-mass) | a transportation solve, `Hitchcock1941`, TU-integral | well defined *given the two maps*; this is the descriptive metric, and it was always free |
| `g*` and `φ` | `VERIFY_U9-bandthm` §10.E | the only quantities on the **invariant** list |
| the frontier slope `s_min` as **a valid supergradient** | `DOMAIN_optimization` §2.11 (the doctrine); `MODEL_U8-band` §10.2 (the measurement) | usable, **with the guard**. §2.11: "`(T/k)·Σ_{i∈S} (μ_i^+ + μ_i^-)` is **a** supergradient at `δ`, for any optimal dual; the quotable value is the **minimised**, **gauge-reduced** `(T/k)Σ_i\|ν_i\|` — at `δ = 0` the unminimised form is unbounded, and a loose minimisation yields an **invalid** supergradient." On v2 the minimisation *was* loose (§9.7 finding 6: §10.A's exact dual-optimal-set LP was not run; a proportionate substitute was used), so validity rests entirely on §10.2's tangent-slack guard, which passes at all three sponsor widths (`+3.81e-4` to `+2.23e-2` nats, `tangent_valid = true`). Say "a supergradient", never "the slope"; and never quote `s_min` without the guard that makes it valid. |
| the band duals `ν_i` (nats per unit of `M`) | `MODEL_U8-band` §10.4 | admissible **only** in bound-shaped statements valid at any dual-feasible point. `gauge_pinned = true` at every `δ`, so `ν` is not free to slide by gauge — but the residual non-uniqueness is combinatorial (§9.7 finding 5) and per-rep `ν_i` values are not invariant. |

**What is now out of scope for U4** — any zip-level "which zips move first" claim, any bound proved
about a named tie set, and any statement that a particular `M`-mass is *the* first-mover mass.
Producing a defensible version of that would require the §10.A dual-optimal-face LP that U8 did not
run (`MODEL_U8-band` §9.7 finding 6). **That is a separate unit and it is not this one.** Recorded
here as a named follow-on so the gap is visible rather than absorbed.

## Spec (verbatim from `docs/DOMAIN_optimization.md` §2.4)

*Re-synced 2026-09-05 — the source was rewritten and the block this brief previously quoted (an
"**Assumptions.** That a *lower* bound on displacement-to-any-better-coverage can be read from the
§2.2 duals …" paragraph) is no longer in §2.4. Current text:*

> ### 2.4 Displacement as the acceptance unit — **kept, unchanged, still the unproved step**
>
> *(Rests on **Hitchcock1941**, **Kuhn1955**, **Ahuja1993** / **Orlin1993**, **Schrijver1986**,
> **Chvatal1983**, **GaleKuhnTucker1951**.)*
>
> Unchanged in substance. What the new work adds is a **better input**: the band duals of §2.12 are
> denominated in nats per unit of `M` and the set of first-moving zips (§2.12) is a displacement by
> construction, so U4-disp has a concrete object to measure rather than a price vector to interpret.
> The modulus `objective-gap ≥ φ(mass moved)` is still neither cited nor proved
> (`MODEL_U1-cert` §8.5). **Failure mode unchanged:** without the modulus, displacement is
> descriptive and acceptance stays in nats.

**Falsified by v2:** the middle sentence's "the set of first-moving zips (§2.12) is a displacement
by construction" — see the premise box. `DOMAIN_optimization.md` is owned by another track and
still carries the claim, here and in §8 Q3 ("a first-mover list that *is* a displacement") and in
§5 row 4. Read those three through this brief, not the other way round.

`DOMAIN_optimization.md` §8 Q3 calls this question *"unchanged, and still the plan's
highest-leverage unknown for FRAME §3.5"*: everything about acceptance in business units
(FRAME §3.5, §10.7, and both lenses' units complaint) rests on it.

## Files owned

`docs/MODEL_U4-disp.md` · `docs/VERIFY_U4-disp.md` · `docs/artifacts/U4-disp/**`

## Files forbidden

Every other unit's owned files · `docs/FRAME.md` · `docs/BRIEF.md` · `docs/LENS_*.md` ·
`docs/DOMAIN_*.md` · `docs/channel_note/**` · `CLAUDE.md` · all of `td/`, `tests/`, `tools/`,
`figures/`, `battery/`.

## Agent → verifier

`modeler` → `math-verify`

## Tooling

`~/.claude/hooks/enforce-file-tools.sh` blocks `cat` / `head` / `tail` / `sed` / `awk` / `grep`
with a file operand from Bash. Use Read and the Serena symbol tools instead
(`get_symbols_overview`, `find_symbol(include_body=True)`, `replace_content`); markdown headings
are symbols. `RUNS_PLAN.md` §"Working rules" has the full table. Bash is for running things.

## Acceptance

VERIFIED or REFUTED on: a modulus `objective-gap ≥ φ(mass moved)` for the coverage problem, with
`φ` explicit and its hypotheses stated — **or** a clean impossibility/absence statement, in which
case acceptance stays in nats and FRAME §3.5 is answered instead by translating a branch-and-bound
gap through the near-equality rung `Δ ≈ ½Σδ_j²` (`REVIEW_GROMOV` R2). A REFUTED verdict here is a
real deliverable: it closes D4. Per `LIT_optimization` §9, the attack to try first is a **KŁ
exponent / Hölderian error bound** for `Σ log g_i` on the assignment polytope (`bolte2017`,
`drusvyatskiy2018`), with `hoffman1952` as the prior for `α = 1`; the honest expected range is
`α ∈ [1, 2]` and the exponent is the thing to pin down — do **not** invent a bespoke argument
before trying that route.

Second required statement: displacement *between two given maps* is a transportation problem
(`Hitchcock1941`, TU-integral) and is always available — separate the **descriptive** metric,
which is free, from the **bound**, which is what is in question. `LENS_GROTHENDIECK.md` §5a's
diagnosis — that a nat-tolerance on a second-order-flat functional is self-defeating *by
construction* — must be stated as the motivation and checked, not assumed.

**Third required statement (new, 2026-09-05 — the degeneracy discipline).** Every dual quantity the
model leans on must be labelled by whether it survives non-uniqueness of `ν`. Concretely: `φ` and
its hypotheses must be stated in terms of dual-optimal-set-invariant objects (`g*`, `φ`, the
displacement between two named maps), **or** the hypotheses must name the specific dual optimum
they condition on and say what would change at another. A modulus that silently depends on one
`ν` is REFUTED-by-construction for this programme's purposes and must be reported as such rather
than published.

## Numbers to compute first

1. **The displacement scale on the live instance.** Between two *named* maps — the delivered v2
   draw (`V = 95.75519165924108`) and the `EG^bal(δ₀)` vertex (`δ₀ = 0.00997002334742`,
   `EG^bal = 96.4796985975`, gap `0.724507` nats) — the zips moved and the `M`-mass moved, by a
   transportation solve. This is the first-order quantity `φ` would have to relate to a nat gap,
   and both endpoints are named maps, so it is well defined despite degeneracy. Record that the
   `EG^bal` vertex is **one** vertex of a degenerate optimal face (`CODEVERIFY_U8-band` F1, F2 —
   on v1, `m` and the split set moved under a `1.1e-16` perturbation of `U`), so the number is conditional
   on that vertex and must be reported as such.
2. **The threshold at which two maps become distinguishable in displacement**, given the tier-2
   floor of `5e-3` nats — i.e. invert whatever `φ` the unit gets, or state that it cannot be
   inverted.

**Removed 2026-09-05: the dots-versus-cells displacement.** The old first line here was
`DOMAIN_optimization` §5 row 8 — displacement between the dots map and the cells map, "which
converts the `4.66e-5`-nat non-decision into a first-order quantity", marked "**Blocked on ★6**".
Three things are now wrong with it. (a) **The ★6 block is lifted**, so the label is stale.
(b) **`4.66e-5` is a v1 number and has no v2 counterpart.** It was measured on the `k = 13` seed-3
draw (`docs/CHANNEL.md`, 2026-09-01: the pinned-centers MILP proved an `8.53 %` more compact
assignment in the same band, 152 relabels, `−4.66e-5` nats); no v2 pinned-centers or power-diagram
run exists under `battery/results/`, and `WAVE2_PLAN` declines to widen `ceiling.py`'s v1 content.
Carrying the number into a v2 unit would import a retired instance's arithmetic. (c) **Displacement
is not the deciding number anyway.** FRAME's decision ledger still carries "the 132 dots: adopt the
power cells or keep the drawn map" as **open**, with "the deciding number is the staffing value of
the cells map, not yet computed" (`REVIEW_GROMOV` sharpens it to the *stage-2* staffing value;
`CHANNEL.md` gives the ordering
"C4 → stage-2 rescore of the cells → adopt unless staffing drops by more than the portfolio
spread") — not a displacement. `DOMAIN_optimization` §5 row 8 still lists it as "predecessor row 8,
unchanged"; that row is stale and is another track's to fix, not this unit's. **U4 does not own the
dots-versus-cells decision and does not compute it.**

## Inputs to read (paths and sections only)

`docs/DOMAIN_optimization.md` §2.4, **§2.11's "shape facts" bullet** (corrected 2026-09-05: "a"
supergradient for any optimal dual, minimised and gauge-reduced, and a loose minimisation is
*invalid* — this is the governing statement for anything this unit does with `s_min` or `ν`),
§2.12 (both the "which zips move first" bullet and its assumptions bullet — the second contradicts
the first under degeneracy), §8 Q3, §4 D4 ·
**`docs/MODEL_U8-band.md` §9.7 findings 5 and 6, §10.2, §10.4, §10.6, §10.7 finding 3 — the live
v2 evidence for the premise box** · `docs/CODEVERIFY_U8-band.md` F1, F2 (the invariance list, and
how fragile the reported vertex is) · **`docs/LIT_optimization.md` §9 (Q9) and absence ledger row D
— the gate, and it has reported**; §7 (Q7, stability radius) for the second candidate framing ·
`docs/LENS_GROTHENDIECK.md` §5a, descent 4 and 7 · `docs/FRAME.md` §3 (acceptance criterion 5),
§6 (the tier floors), §10 Q4 and Q7 · `docs/REVIEW_GROMOV.md` R2 ·
`~/resources/optimization/FOUNDATIONS.md` (`Hitchcock1941`, `Schrijver1986`, `Chvatal1983`,
`GaleKuhnTucker1951`)

## Open questions for ★0

**★6 is lifted and the U0-lit gate has reported** — both former holds are gone; the unit is
launchable. `LIT_optimization` §9's verdict ("no instance-specific modulus for partitioning or
assignment") settles the size question the old ★6 note left open: this is a proof unit (L), not a
citation unit (S).

**New, for ★0.** Should a follow-on unit run `MODEL_U8-band` §10.A's dual-optimal-face LP, to make
*some* first-mover statement defensible? It would restore an object the programme has now referred
to in three documents and can no longer name. U4 flags the need; U4 does not do it.

## Branch

From `main` (e.g. `wt/U4-disp`). The old `wt/U4-disp` "from `wt/workflow-dryrun`" instruction is
dead — that branch does not exist — as is "launch from `.claude/worktrees/A1`"; `A1` was retired in
`3c8a643`, and `BRIEF.md:118-119` is the stale sentence that produced both.

## Stop rule

If no modulus exists and none can be proved, **stop and report the absence** — do not invent a
weaker metric to have something to deliver. The absence is what D4 needs. Likewise, if the only way
to get a modulus is to condition on one dual optimum, **report that as the finding**; do not name a
first-mover set to make the unit look complete.

**stop and report rather than improvise**
