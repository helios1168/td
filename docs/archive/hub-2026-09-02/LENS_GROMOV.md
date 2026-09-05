# Gromov lens — the national channel territory problem

> **Hub copy, restored 2026-09-03 from `a4eb488`.** This is the neutral 2026-09-02 version every track starts from. The instance has since been measured — read `docs/FRAME.md` §6's 2026-09-03 rows and `docs/APPROACHES.md` §0's "what every track inherits" before using the numbers here. The A1 track's re-run of this file, with the measurements folded in, is at `docs/tracks/A1/LENS_GROMOV.md`.

**Date:** 2026-09-02 · **Framework:** 0.1-dev · **Reads:** `docs/FRAME.md` (and, for
non-duplication, `docs/REVIEW_GROMOV.md`, `docs/RESEARCH_FINDINGS.md` §9) ·
**Provenance:** `~/.claude/commands/gromov.md` (cited; evidence base
`~/resources/gromov/ARTIFACT_DRAFT.md`)

**Scope note.** A Gromov pass already exists at a different altitude: `REVIEW_GROMOV.md`
reviewed `channel_note.tex` and fired 14→5, 11, 8. This one is run against `FRAME.md` —
the problem, not the note — and deliberately fires three *different* moves. Where the
earlier pass measured that the incumbency premium is the large term, this one asks what
symmetry its neglect was resting on (3), bounds it (4), and audits the words that hid it (13).

Everything numeric below that is not sourced to `FRAME.md` §6 is **an unmeasured
prediction**; the instance is not in this worktree (FRAME §5) so nothing here was computed.
Each such quantity is a named unknown in the ledger.

---

## Moves that fired

### Move 3 — Find the symmetry that pays for the tool

> "*It is symmetry, not any idea of 'measure of underminancy', which makes the concept of
> probability to work so beautifully in physics.*" — `probability-paris-025`

**What the tool is.** The programme's foundational result: *Nash welfare on a common measure
is equal-size districting* — hence "the $1B target needs no constraint, balance falls out".
Every stage-1 certificate is downstream of it.

**What pays for it.** Not concavity. **Agent anonymity**: the symmetric group `S_n` acting on
wholesalers leaves the valuation profile fixed, because every agent values zip `z` at the same
`M_z`. That is what makes `Σ_i g_i` partition-invariant, which is the only property the
AM–GM/Schur-concavity argument consumes.

**The transplant check.** At the measured 41.9% saturation the agents are *not* interchangeable
— `u_i(z) = M_z·[c1·s_i + c2·(t_z − s_i) + c_free·s_free + λ]` and `s_i` is agent-specific.
`S_n` is broken by exactly the term FRAME §6 prices at ~3.7 nats. So the tool has not been
transplanted; it has been applied to a surrogate on which the symmetry still holds.

**What survives exactly** (this is FRAME §10 Q2, answered without approximation). For any
partition and matching, with `ḡ = (Σ_i g_i)/n`:

```
Σ_i log g_i  =  n·log ḡ  −  D(g),        D(g) = Σ_i log(ḡ/g_i) ≥ 0,  = 0 iff g equal
```

and, from the welfare decomposition, `Σ_i g_i = W₀ + Δ·P` with `W₀` partition-invariant,
`Δ = c1 − c2 = (1−λ)(1−θ)` and `P = Σ_z S_owner(z)(z)` the **premium**. So the objective
fibers over total welfare:

- **base** = choose (partition, roster) to maximise `P` — range ~3.7 nats, never posed;
- **fiber** = on a level set of `Σ_i g_i`, MNW ≡ equalise the `g_i` — range 1e-4–1e-2 nats.

The equal-size theorem is **true verbatim, as a fiberwise statement**. Nothing was wrong; the
base was silently assumed to be a point, which is exactly the `S_n`-symmetric case.

**Three consequences that are not in any current document.**

1. **Stage 1 optimises neither term.** The fiber problem is "equalise **gains** `g_i`"; stage 1
   equalises **opportunity** `M_j`. These coincide only under the common measure — i.e. only
   in the symmetric case that saturation destroys. The committed draw's headline 0.781% is a
   spread of `M` (`channel.balance_report`, `td/channel.py:68`); `stage2` computes the realized
   `g_i` per district (`td/channel.py:322`) but **the spread of `g` is never reported**. It is
   one line, and at a ~42% per-zip swing it will not be 0.781%. **U1.**
2. **The two-stage split is a perturbative expansion in saturation** around the anonymous
   problem: solve the `S_n` quotient, then break the symmetry. Exact as `t → 0`; the expansion
   parameter here is 0.42. That is the honest statement of FRAME §10 Q1 — the decomposition is
   a decomposition of the fiber.
3. **Certificates 1–4 certify the quotient.** They are exact statements about the anonymous
   surrogate `Σ_j log M_j`; their distance to the real objective is the base term, which no
   certificate touches. This is not a defect in the certificates; it is a mislabelling of what
   they certify (see Move 13).

**Generative half of the move.** The fibration says what to build: the exact fiber problem is
*re-draw to equalise `g` under the current matching*, which upgrades FINDINGS §9-F6 (Benders
feedback) from "the principled `score_draws`" to a problem with a stated objective. Iterating
draw → match → re-equalise-`g` is coordinate ascent on the decomposition above, and each
sweep is milliseconds.

### Move 4 — If you don't understand, count

> "**If you don't understand – COUNT!**" — `isoperimetry-050`

The premium is called "unexplored **and unbounded**" (`REVIEW_GROMOV` R1). It is not
unbounded; nobody has counted. Four quantities form a ladder, three of them uncomputed and
all four cheap:

| | quantity | why it is a valid bound | cost |
|---|---|---|---|
| `P₀` | premium realized by the committed draw + matching | the incumbent value | one line |
| `P*(A)` | `max_σ Σ_z S_σ(block(z))(z)` at the committed partition `A` | linear assignment — Hungarian on **premium** weights, not log-gains; exact | milliseconds |
| `P₁₃` | `max_{|R|=13} Σ_z max_{i∈R} S_i(z)` | relaxes the partition entirely, keeps the roster constraint | see below |
| `P_free` | `Σ_z max_i S_i(z)` | **the bound in use today** — relaxes everything; gives the "≤25% of welfare" | already have it |

`P₀ ≤ P*(A) ≤ P₁₃ ≤ P_free`. The one that needs a word: `f(R) = Σ_z max_{i∈R} S_i(z)` is
monotone submodular, so greedy returns a roster with `f ≥ (1−1/e)·P₁₃` (a **lower** bound plus
a concrete candidate roster), and the standard monotone-submodular certificate
`P₁₃ ≤ f(R) + Σ (top-13 marginals at R)` is a valid **upper** bound. 1,229 × 111 × 13 ≈ 1.8M
marginal evaluations — seconds. This is FRAME §10 Q3's missing upper bound, and it is
complementary to R3's EG bound: EG is conditional on the winner's 13 staff and sees geometry
through the fractional polytope; `P₁₃` is unconditional over all `C(111,13) ≈ 10^16` rosters
and ignores geometry.

**The count that decides the blocking question.** FRAME §6 reports 675 contested zips —
contested among all **111**. The premium can only be moved by the drawing at zips contested
among the **13 selected**. That number is not in any document, and neither is its share of `M`.
If it is small, the blocking decision ("may the drawing see books?") is worth close to nothing
and is settled by data instead of by principle. **U4, U9.**

**The escape clause** (the move is not complete without it — state what would overturn the
count):

- If book is concentrated in few wholesalers, `P₁₃ ≈ P_free`, the bound does not bite, and the
  pressure to make stage 1 book-aware is real.
- If the top-13 by coverage overlap geographically (books follow metros, and so does `M`),
  `P₁₃ ≪ P_free`, the 25% headline was hugely loose, and most of the "3.7 nats unexplored" was
  never reachable by any map.
- The hidden identity to hunt: **correlation between `S_i` and `M`**. Every bound above treats
  them as free; if big books sit in big-`M` zips the roster bound and the balance constraint
  interact, and `P₁₃` computed free of the balance constraint is loose in a way that is not
  small. Measurable directly.

**One more count, on effort.** The roster *is* chosen optimally for a given partition
(rectangular Hungarian, `td/channel.py:288`). The partition is not: 5 seeds, ranked by a
criterion (`score_draws`) whose stage-1 component is blind to the base term. So the search is
exhaustive-and-certified on the term worth 1e-4 nats and 5-sample on the term worth ~3.7.

**And the count that should worry the programme.** The §3 baseline — group states to ~$1B,
give each bucket the wholesaler with the most book in it — is **premium-greedy and
balance-sloppy**: it crudely optimises the large term while the programme exactly optimises
the small one. It is entirely possible that the hand draw wins on `P` by more than it loses on
`D(g)`. That is the cheapest and most informative experiment in the file, and until it is run
the headline claim is not merely unevidenced (FRAME §3) but **plausibly false**. **U10.**

### Move 13 — Purge the words that think for you

> "the word 'landscape' misdirects you imagination … It takes a bit of mathematical thinking
> to see trees in the multidimensional energy and/or fitness landscapes" — `bio-dimensions-018`

FRAME already does much of this move on itself (the supersession header, the settled/open
table, the assumption ledger). Six words are still thinking for the programme; the first one
is load-bearing on the only blocking decision.

**1. "books" — one word, two objects with opposite properties.** The blocking question is
posed as *may territory-drawing see wholesaler books?* — value says yes, incentive-safety
(§9-G, fotakis2014) says no. But §9-G's objection is to reading **reports**, and R1 already
names the escape: **audited system-of-record revenue is not a report**. Split the word and the
dichotomy dissolves: the real variable is *reported vs audited*, not *stage 1 vs stage 2*. The
question to put to the user becomes answerable and much smaller: **is the audited measure
available at zip × wholesaler grain, and how far is it from the reported book?** A
report-blind, audit-aware stage 1 captures the premium and is unmanipulable by construction —
which is FRAME §10 Q5's requested formulation. Rewrite §9-G's invariant as *"reported books
enter at stage 2 only; audited revenue may enter anywhere"*.

**2. "certified".** "A certified k=13 draw exists" reads, to anyone outside the programme, as
*proved near-best*. Operationally (Move 2's test: which argument consumes it?) all five
certificates consume only the anonymous quotient. Rename to **balance-certified** and ban the
bare form in anything a sponsor reads.

**3. "opportunity" (`M_z`).** Evokes a measured quantity. It is an estimate whose regional
methodology is unaudited (A4) and on which the equal-size theorem and every certificate are
stated. Rename in the note to **the sizing estimate**, and add the sentence that follows from
Move 3: *a regional bias in `M` is invisible to all five certificates.* **U5.**

**4. "spread 0.781%".** Four significant figures of the surrogate, printed as the headline.
Worse, it is a spread of `M` while the quantity the objective wants equalised is `g`
(Move 3, consequence 1). Report both, or report `g` only.

**5. "territory map" / "power diagram".** The object is a labelling of 1,229 points; 132 of
them fall outside their own cell and the sold-zip graph has 547 components. Everyone in the
room will picture contiguous regions and reason about drive time and coverage from the
picture. This is precisely the "landscape" failure. Keep "map" for the figure, call the object
an **assignment**, and never show the fill without the dots (`937460e` already does this —
protect it).

**6. "nats".** FRAME §10 Q7. Two conversions exist and neither is hard: the near-equality rung
`Δ ≈ ½Σδ_j²` converts the fiber term to % of target (`REVIEW_GROMOV` R2), and the base term is
**already in business units** — `P` is *book landing with its incumbent*, a share, with no
logarithm anywhere. Report balance in % of target and the premium in book-share; keep nats
inside the programme.

*(Naming hazard while doing this: `Δ = c1 − c2 = 0.42` at the default `θ=0.40, λ=0.30`, and the
measured hold-vs-not swing is also ≈42%. Different quantities. They will be conflated.)*

---

## Moves that did not fire, and why

- **Move 1 (build the language).** Does not fire, and its *stability* is information: the
  earlier review found formulations shortening (contiguity → band + compactness → power
  diagram) and FRAME §10 poses seven questions that are one sentence each. The language is
  healthy; the problem is not under-formulated, it is under-measured.
- **Move 12 (soft vs hard).** Does not fire as an independent move — it **collapses into Move
  4's escape clause**. Balance was already shown soft (`REVIEW_GROMOV`: 2e-6 reachable
  geometry-free, all seeds under 1%), so no structure lives there. The unasked question,
  *is the premium soft?* — do all balance-feasible partitions land within ε of `P₁₃`? — is
  answered by the same measurement as U1/U4, so there is nothing for the move to add before
  that measurement exists.
- **Move 9 (bound by the stupidity of the generator).** Fires **inverted**, which is a clean
  diagnostic. Its premise is a dumb generator, licensing a search among simple mechanisms. The
  only hidden mechanism here is wholesaler misreporting, whose generator is a self-interested
  optimiser — the assumption must be maximal cleverness, not stupidity. Move 9 is not merely
  silent; it points the wrong way, which is why the governance answer has to be structural
  (Move 13.1) rather than a bound on how devious anyone will be.
- **Move 7 (space of kin).** Already the plan, not a finding: the portfolio, `score_draws` and
  §9-D's frontier sweep *are* the passage from the draw to the space of draws. The lens adds
  only the cap — the frontier is worth sweeping in `(balance, compactness, premium)`, not the
  first two alone, and no further altitude is needed.
- **Move 10 (dissect the proof).** Subsumed by Move 3: the dissection of the equal-size proof —
  it consumes nothing but the invariance of `Σ_i g_i` — *is* the symmetry audit, and reporting
  it twice would double-count one observation.
- **Move 2 (definitions), partial, and it fails its own test cleanly.** The tier-2 floor
  (`base.EPS_CERT = 5e-3`, `td/solvers/base.py:81`) looks like a candidate: it renders the main
  open decision undecidable (FRAME §10 Q4). But it *is* consumed by a live argument
  (R2's dots-vs-cells indistinguishability), so it passes the operational test. Its defect is
  **calibration, not pedigree** — the comment at `base.py:73-80` records it as measured on a
  197-zip two-player instance. The fix is a measurement (**U6**), not a purge, so the move
  does not fire. Worth stating: FRAME Q4's suspicion is right about the symptom and wrong
  about the cause.
- **Move 5 (numerical bounds), discharged rather than fired.** FRAME §6 is this move already
  done. Two numbers remain unpinned and both are business-side: the balance↔continuity
  exchange rate (§3, never elicited) and U6. Named in the ledger.
- **Move 6 (the improbable).** The one improbable fact — a 5-seed heuristic landing 4.5e-5
  nats under the ceiling — already has its explanation (second-order flatness at balance plus
  softness), as does the 8.22%/8.53% agreement. Explained, so no signal.
- **Move 11 (the ladder).** The near-equality rung was already run in R2; the rest of the
  ladder needs quantitative results on the base term, which do not exist yet. Re-run it after
  Move 4's numbers land.

---

## Named unknowns (Move 14 ledger)

> "What is really depressing is the difficulty of specifically articulating what you don't
> understand." — `bio-dimensions-066`

Grades: **[E]** empirically settleable now (needs only the instance) · **[B]** needs a business
answer · **[T]** needs a theorem. All **[E]** items are hours, not days.

| # | unknown | grade | why it matters | where a counterexample lives |
|---|---|---|---|---|
| U1 | Spread of realized gains `g_i` on the committed draw (vs 0.781% in `M`) | E | the fiber objective is equal `g`, not equal `M`; the headline may be measuring the wrong thing | if `w_i` is near-constant across the 13 matched reps, `g`-spread ≈ `M`-spread and the distinction is decorative |
| U2 | `P₀` — premium realized by the committed draw, as a share of total book | E | there is no number today for the term worth ~3.7 nats | — |
| U3 | `P*(A)` — premium-maximising matching at the committed partition | E | separates "the map is wrong" from "the matching is wrong"; if `P₀ ≈ P*(A)` the drawing is the whole gap | — |
| U4 | zips contested **among the selected 13** (vs 675 among 111), and their share of `M` | E | decides whether the blocking book-awareness question is worth anything | if the 13 are book-disjoint the count is ~0 and the decision is moot |
| U5 | regional bias in the sizing estimate `M` (A4) | B | the single unknown that would invalidate all five certificates at once, silently | methodology differing by region or by firm |
| U6 | data-noise floor **on this instance** (tier-2 = 5e-3 imported from a 197-zip two-player instance) | E | decides dots-vs-cells; a floor calibrated elsewhere is deciding it now | re-bootstrap under the contestability noise model at `n=1,229, k=13` |
| U7 | is the premium **soft**? do all balance-feasible partitions reach within ε of `P₁₃`? | E | if soft, stage-1 book-awareness is worthless and §9-G's invariant costs nothing | same measurement as U1/U4 |
| U8 | correlation between `S_i` and `M` | E | the hidden identity that would overturn Move 4's ladder | books following metros, as `M` does |
| U9 | saturation robustness to the headroom repairs (A8) | E | R1's 41.9% is the load-bearing number for this entire lens | instance absent from this worktree |
| U10 | the hand-drawn baseline's `(P, D(g))` against the committed draw's | E | the baseline is premium-greedy; it may **win** on the term that matters | — |
| U11 | is audited system-of-record revenue available at zip × wholesaler grain, and how far from reported book? | B | dissolves or confirms the only blocking decision (Move 13.1) | — |
| U12 | the balance↔continuity exchange rate | B | §3 says it is a binding tolerance and it has never been elicited | — |

Not on this ledger because they are already on FRAME §9's: the vacant/untapped ownership rule,
`filler_capture`, θ directionality, A2, A6.

---

## Open questions this lens raises (inputs to `/domain` and `/research-plan`)

1. **[optimization]** Is the roster bound `P₁₃` — monotone-submodular max-coverage with a
   cardinality constraint — a *certificate* the literature already packages (LP/greedy duality,
   `max-k-coverage`, facility-location selection)? If so this is a citation, not a
   construction. Pairs with FINDINGS C3/R3, which bounds a different relaxation.
2. **[economic theory / fair division]** The decomposition `Σ log g = n log ḡ − D(g)` with a
   partition-dependent base is elementary; the question is whether the *fiberwise* reading of
   the equal-split theorem (equal-size districting is exactly optimal on level sets of total
   welfare, and only there) is stated anywhere, and what replaces it globally when measures are
   agent-specific but **correlated** through a common `M`. Nash-welfare-with-heterogeneous-but-
   proportional valuations is the search.
3. **[optimization]** The joint base problem — choose (partition, roster) to maximise premium
   subject to a balance band — is FINDINGS §9-I.4 ("Nash-optimal territory design and salesforce
   selection") with the objective now written down. Is it a known joint districting +
   selection formulation, and does the fiber/base split give a natural Benders decomposition
   (§9-F6)?
4. **[mechanism design]** Formalise the audited/reported split (Move 13.1): a mechanism whose
   drawing reads only non-manipulable statistics and whose matching reads reports only within
   the retained set. What does fotakis2014's impossibility actually forbid once the drawing's
   input is not a report? This is the paper-shaped question in the file, and it is the one the
   business will ask.
5. **[optimization / statistics]** What noise model is the right one for U6 at this scale, and
   is a tolerance that renders the programme's own open decision undecidable evidence that
   the *decision* is mis-posed (R2 already says the tie-break should be staffing value, not
   stage-1 Nash) rather than the tolerance mis-set?
6. **[geometry]** FRAME §10 Q6 — "the glue is the worthless part". Untouched by this lens; it
   is §9-H's one experiment, and Move 12 would fire on it properly once the full-ZCTA graph
   exists (is contiguity soft on the full graph and rigid on the sold-zip graph?).

**Recommended order.** U2, U3, U1, U4 (one session, one script, all four from the existing
instance) → U10, the hand-drawn baseline → U6 → then the Move 13 rename pass, which is free
and blocks nothing. U11 is the single question to put to the user, and it is smaller than the
blocking question FRAME §9 currently records.
