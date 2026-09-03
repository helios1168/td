# Gromov lens — the A1 track: joint coverage optimisation, after measurement

**Date:** 2026-09-03 (branch `wt/A1`; supersedes the hub's 2026-09-02 lens *on this branch only*)
· **Framework:** 0.1 · **Reads:** `docs/APPROACHES.md` §A1 (the charter, taken verbatim),
`docs/FRAME.md` §6 (as extended 2026-09-03), `docs/MODEL_U7-meas.md` §6,
`docs/MODEL_U1-cert.md` §5–§6, `docs/VERIFY_U1-cert.md` §0, §6–§7,
`docs/CODEVERIFY_U7-meas.md`, `docs/DOMAIN_optimization.md` §2.1, §2.5, §2.6 ·
**Predecessor:** the hub's `docs/LENS_GROMOV.md` of 2026-09-02 (fired 3, 4, 13; ledger U1–U12).
Its Move 3 fibration and Move 13 rename pass stand and are not repeated; its ledger numbering
is kept, with U1–U4 and U8 now *measured* and U13–U19 added ·
**Provenance:** `~/.claude/commands/gromov.md` (cited; evidence base
`~/resources/gromov/ARTIFACT_DRAFT.md`)

**Scope note.** The predecessor ran against an unmeasured problem and its three moves were
all of the form *go and count*. The counts are in (FRAME §6, 2026-09-03 rows). This pass runs
against the A1 charter with those numbers as givens, and the moves that fire are different:
the ones that operate on sharp inequalities once they exist (8, 11, 12), and the one that
purges the two words the charter is built on (13: "MINLP", "jointly"). Everything numeric
below is sourced to FRAME §6 or the two unit models unless marked **[prediction]**.

**The charter, in one line.** Choose `(π, σ)` together to maximise
`V(π,σ) = Σ_j log u_{σ(j)}(A_j)` by a rep-indexed MINLP with balance as a band; certify by the
fixed-roster Eisenberg–Gale relaxation. **What is now known:** at the delivered roster `S₁₃`,
`EG_{S₁₃} − V = 0.760` nats and the EG vertex realising it has `M`-spread ≥ 50% (U1-cert P4);
the premium ladder puts 0 nats on the matching, 0.64 on the map, 0.04 on the roster (U7-meas
§6); the realised-gain spread is 60.65% against the 0.78% `M`-spread; 83 zips (6.12% of `M`)
are contested among the 13. **Where A1 is stuck:** all of its upside at this roster is ≤ 0.76
nats and appears to be bought with balance; nobody knows what survives a band.

---

## Moves that fired

### Move 8 — Step down to a surrogate, then audit the step

The charter's honest problem is the band-constrained joint program. Its stated certificate is
the *unconstrained* fixed-roster EG relaxation `EG_S`. That is a surrogate, and the charter
never audited the step. Run both audits.

**Audit 1 — is the surrogate easy?** Yes, and that is the finding: it is too easy, because it
drops the one constraint the sponsor wrote down. `EG_S` ignores balance (U1-cert §5.3), so the
0.760 nats it prices is a gap over a feasible set the business would reject. The number a
decision needs is the **band-constrained fibre value**

```
EG^bal_S(δ) = max { Σ_{i∈S} log Σ_z u_i(z) x_zi  :  Σ_i x_zi = 1,  x ≥ 0,
                    (1−δ)·T/k ≤ Σ_z M_z x_zi ≤ (1+δ)·T/k  ∀ i∈S }
```

and this is **still one concave program** — the band is `2k` linear rows added to a
polyhedron, the objective is unchanged. Concavity is not touched, weak duality is not
touched, and P1's proof (U1-cert §3, `[proved]`) goes through verbatim with the band added to
both the integral coverage and the relaxation, because the band is a constraint on `x` and
the proof only needs `X_π` feasible. So the surrogate the charter should have named costs
exactly one more solve than the one it did name, and it is sandwiched today:

```
59.9375 = V(delivered)  ≤  EG^bal_{S₁₃}(0.0078)  ≤  EG^bal_{S₁₃}(δ)  ≤  EG^bal_{S₁₃}(0.33) = EG_{S₁₃} = 60.6974
```

(the right end because the unconstrained vertex has max deviation 33.00% on both independent
solves, U1-cert §4.3). **U13.** This is the cheapest decisive experiment in the file and it
replaces `DOMAIN_optimization.md` §2.6's τ-homotopy as the first thing to run: the homotopy
asks whether the *map* moves as books switch on; `EG^bal(δ)` asks directly how much *value*
the band leaves on the table, and it is convex where the homotopy is an empirical claim about
an MINLP.

**Audit 2 — price the retreat.** If `EG^bal_{S₁₃}(δ)` were computed exactly for the sponsor's
δ, what fraction of the charter's question would be answered?

- The *map* half (0.64 nats on the ladder) — **fully**, at that roster: the gap
  `EG^bal − V` is an upper bound on any band-feasible redraw, and rounding its vertex
  (≤ `k−1` splits, VERIFY P3a — and see U15 for whether the band changes that) gives a
  constructive integral map within a computable distance of it.
- The *roster* half (0.04 nats on the ladder, 8× the floor) — **not by one solve**, but by
  a handful: the ladder says only rosters within 0.043 nats of `S₁₃` in premium can matter,
  and `P₁₃`'s optimum differs from `S₁₃` by a two-rep swap (R0017, R0018 → R0009, R0012).
  `EG^bal` at that roster is a second solve. **U16.** The selection non-convexity
  (`LENS_GROTHENDIECK` OQ3, `Σ y_i = k`) is bypassed by enumeration, not solved.
- The *certificate in business units* (C5) — **not at all**; still nats (U1-cert §6, FRAME
  §10 Q7). But the band duals are new equipment for it — Move 11 below.

So the retreat from "MINLP" to "a few convex programs plus rounding" prices at
**most of the charter**, which is the audit's verdict on how much rigour the MINLP deserves:
little, until `EG^bal` says the rounding gap or the roster gap exceeds the floor.

**The word the audit exposes.** The charter's certificate was named before the problem's
constraint was in it. That is the surrogate silently becoming the problem — the failure Move
8 exists to catch — and U1-cert §5.3 caught it as a *failure mode* rather than as the *first
thing to fix*.

### Move 11 — Treat statements as raw material: run the ladder

> This move "needs a field with quantitative results to operate on." The predecessor declined
> it for that reason. As of 2026-09-03 there are two sharp inequalities and one equality case
> on this instance, so it fires.

**Rough → sharp → equality → near-equality**, on the term the business signs:

| rung | statement | status |
|---|---|---|
| rough | `V ≤ k·log(T/k) = 69.5865` (the analytic ceiling; U1-cert P1c) | 9.65 nats loose |
| sharp | `V ≤ EG_{S₁₃} = 60.6974` at the delivered roster | 0.760 nats loose, certified to 7e-15 |
| equality | `EG_S = k·log(λT/k)` for every `S` iff `u_i ≡ λM` (τ = 0; U1-cert P2.1) | the programme as built lives here |
| near-equality | at τ = 0.42 the gap opens to 0.760 nats, and the extremiser leaves the balance band by 33% max deviation | **the structure is in how the gap depends on the band** |

**Operate on the statements.** Three of the move's operations produce something the charter
does not have:

1. **Vary the constraint set as a family** — `δ ↦ EG^bal_{S₁₃}(δ)` on `[0.0078, 0.33]`. This
   *is* `DOMAIN_optimization.md` §2.5's `(premium, balance)` frontier, but in `V` rather than
   in `P`, and computable by convex parametric programming rather than by a sequence of
   ε-constraint MILPs. Its shape answers Move 12 below. Mark the MNW point (δ = 0.0078,
   the delivered draw) on it, as §2.5 insists (trap 2). **U13.**
2. **Read the inequality backwards.** The band duals `μ_i^±` of `EG^bal` are shadow prices in
   **nats per unit of `M`** on each district's balance constraint. That is the
   **balance↔continuity exchange rate** — LENS_GROMOV U12, the tolerance FRAME §3 calls binding
   and "never elicited". It has never been elicited because it was never *computed*. A computed
   shadow price is not a business decision, but it converts the question the sponsor is asked
   from "how much continuity would you trade for balance?" (unanswerable) into "at δ = 5% the
   marginal territory-dollar of balance costs X nats of continuity; is that the right δ?"
   (answerable). **U14.**
3. **Swap which side is extremal.** Fix `V ≥ V(delivered)` and minimise the spread. That is the
   other axis of the same frontier, and it is what A3's hand-drawn baseline should be scored
   on (U10): not "does it beat the draw on `V`" but "where does it sit on the curve". One
   frontier, both baselines plotted.

**Couple under products — declined.** The move's product/fibration/foliation operations need
a second instance or a second objective to couple with; the only candidate is the τ-homotopy,
and Move 8 has just argued `EG^bal(δ)` supersedes it. Noted, not run.

### Move 12 — Chart soft against hard and work the borderline

The predecessor said this move collapses into Move 4's escape clause until U1/U4 are
measured. They are. It now fires on the question the ledger called **U7**: *is the premium
soft inside the balance band?*

**The softness test, made precise.** The premium is soft at band δ if every band-feasible
coverage at `S₁₃` has `V` within the tier-2 floor (5e-3 nats) of the delivered draw — i.e. if
`EG^bal_{S₁₃}(δ) − V(delivered) ≤ 5e-3`. If so, there is no structure to find inside the band:
every legal map staffs the same, A1's redraw is decorative, and the honest response is A5's
(sample the band, pick by staffing value, report a percentile). If not, the borderline
`δ* = min { δ : EG^bal(δ) − V > 5e-3 }` is where the structure starts, and A1's whole case is
the interval `[δ*, δ_sponsor]`.

**What the measured numbers already say about the answer [prediction].** The gap is 0.760 at
δ = 0.33 and 0 at δ = 0.0078; `EG^bal(δ)` is concave in δ (the value function of a concave
program with the constraint right-hand side as parameter). Concavity in δ means the curve
rises *fastest* near δ = 0, so the premium is **not expected to be soft**: the borderline δ*
should be close to the delivered spread, well inside any band the sponsor would name. The
opposite reading — a flat curve until some δ where a single large zip becomes movable — would
be a rigidity signal worth its own investigation (FRAME §6: zip 10017 alone is 14% of a
territory). Either way it is one parametric solve, and it is the A1 kill experiment restated
for the band-constrained problem: **the ladder said the map holds 0.64 nats; the band decides
how much of that is real.**

**Working the borderline.** If δ* is small, the interesting object is not the optimum at the
sponsor's δ but the *set of zips whose assignment changes* as δ crosses δ* — the first zips
to move are the ones where the premium-per-dollar-of-imbalance is highest, and that list is
readable from the band duals (Move 11.2) without a second solve. It is also the natural
input to U4-disp (displacement as the acceptance unit).

### Move 13 — Purge the words that think for you

The predecessor purged six words in FRAME. Two more are in the A1 charter itself, and both
are load-bearing on what the track builds next.

**1. "MINLP."** The charter's step 3 is a rep-indexed mixed-integer *nonlinear* program with
`y_i` selection binaries, `x_{zi}` assignment binaries, and a perspective-log objective —
1,229 × ~30 ≈ 37k binaries after roster pruning, `DOMAIN_optimization.md` §2.1's "centrepiece".
After measurement, the object is not that. Fix the roster and the problem is a concave
program with a polyhedral feasible set (`EG^bal_S`), whose vertex solution splits at most
`k − 1` units (P3a as verified; U15 asks whether the band raises it to `2k − 1`). The
nonlinearity is in the objective only, and it is *concave* — there is nothing for
branch-and-bound to branch on except the `≤ k − 1` split units, which rounding handles with a
bound (P3b). The selection binaries are the only genuine integrality, and the ladder says the
rosters worth trying are a handful. **"MINLP" was imagining a hard problem where the
measurements show a short enumeration of easy ones.** Rename the track's step 3 to *roster
enumeration over band-constrained EG programs*, and keep "MINLP" for the day the rounding gap
or the roster count exceeds what enumeration handles.

**2. "jointly."** The charter's distinctness claim against A0 (`APPROACHES.md` "A0 / A1") is
that A1 decides partition and roster *in one solve*. It does not need to, and it should not
say it does: the roster enters through `S` in `EG^bal_S`, the map through `x`, and the two
are coupled only by the enumeration loop. What A1 actually adds over A0 is not jointness; it
is **(a) the map is drawn on `u_i` under a band instead of on `M` alone, and (b) the value is
certified against the term the business signs.** Say that. It also makes A1's cost — the draw
reads books, FRAME §9's blocking decision — exact rather than implicit: the *only* place books
enter the draw is the objective of `EG^bal_S`, and `LENS_GROTHENDIECK` §5b's `G`-invariance
question is asked of one concave program, not of a MINLP.

**3. "the ~3.7-nat premium swing" (FRAME §6, repeated in the charter's "Why it might beat
A0").** It is the size of the *term*, not of what any redraw can win. At the delivered
roster the reachable amount is ≤ 0.760 nats unconstrained and `EG^bal − V` constrained; over
all rosters the ladder adds ≤ 0.043 nats first-order. The 3.7 should be retired from every
sentence that argues for building something, and replaced by the bracket
`[EG^bal_{S₁₃}(δ) − V, 0.803]`. U7-meas §6 and U1-cert §6 already say this; the charter's
motivation paragraph does not yet.

---

## Moves that did not fire, and why

- **Move 1 (build the language).** Still does not fire, and the trend is the diagnostic Move 1
  asks for: the A1 problem statement went from a paragraph of MINLP (`DOMAIN_optimization`
  §2.1) to three lines of convex program (Move 8 above) *because* the numbers landed.
  Formulations are getting shorter. The line is alive.
- **Move 3 (symmetry).** Done by the predecessor and now measured: the `S_n`-broken term is
  0.76 nats at the delivered roster, not 3.7. The fibration (base = premium, fibre = equalise
  `g`) stands; the fibre's realised spread is 60.65%. Nothing to add without repeating it.
- **Move 4 (count).** Discharged — the counts are the inputs to this pass. One residual count
  is worth stating because it bounds A1's roster search: the rosters that can beat `S₁₃` in
  premium by more than the floor are those within `P₁₃ − P_S = 10.46` book of the optimum;
  greedy and the exact MILP agree on the optimum and it is a two-rep swap away. **[prediction]**
  the near-optimal set is tens, not thousands; U16 measures it.
- **Move 5 (numerical bounds).** Discharged by U1-cert and U7-meas. The one conversion worth
  writing down: 0.760 nats of `Σ log g` across 13 reps is a **6.0% rise in the geometric mean
  gain** (`e^{0.760/13} − 1`), against a 13.6%-of-book map gap. Both are small next to what
  the words "unexplored premium" evoked.
- **Move 6 (the improbable).** Two coincidences, both explained on inspection. `P₀ = P*(A)`
  *exactly* on seed 3 (the Nash roster is premium-optimal): `g_ij = B_j + w·b_ij` and the
  `B_j` are nearly equal because the draw is balanced, so the log-gain ordering is the book
  ordering — expected, not improbable. Greedy attains the `P₁₃` MILP optimum: the selected
  books are nearly disjoint (83 contested zips among 13), and greedy is exact on disjoint
  coverage. Neither licenses attention.
- **Move 7 (space of kin).** A5's charter, not A1's. The one place A1 touches it is Move 12's
  softness verdict: if the premium is soft in the band, A1 should hand the problem to A5.
- **Move 9.** Inverted, as before; nothing new.
- **Move 10 (dissect the proof).** Already done, by U1-cert: P2 dissected the four certificates
  down to the property each consumes and found three consume the EG dual and one does not.
  The move's residual instruction — *note what the proof does not see* — is U1-cert §5's
  "what the bound does not cover" (misreporting, error in `M`), verified. Repeating it here
  would double-count.
- **Move 2 (definitions).** Fires weakly and is folded into Move 8: the working formula that
  proves things is `EG^bal_S`, not `EG_S`, so promote it to the definition of "the
  certificate" in the charter. No other definition fails the operational test.

---

## Named unknowns (Move 14 ledger)

> "What is really depressing is the difficulty of specifically articulating what you don't
> understand." — `bio-dimensions-066`

Grades as before: **[E]** empirically settleable now · **[B]** needs a business answer ·
**[T]** needs a theorem. Numbering continues the predecessor's; settled items keep their
number and carry the value.

| # | unknown | grade | status 2026-09-03 |
|---|---|---|---|
| U1 | spread of realised `g_i` vs `M`-spread | E | **measured: 60.65% vs 0.781%** (seed 9: 59.47% vs 0.836%). A0's soft kill fires. |
| U2 | `P₀` | E | **measured: 37.82% of book** |
| U3 | `P*(A)` | E | **measured: 37.82%** — the matching is already premium-optimal; seed 9's relabel buys 0.14% of book and loses 0.008 nats of `V` |
| U4 | contested among the 13, and `M`-share | E | **measured: 83 zips, 6.12% of `M`** |
| U5 | regional bias in `M` | B | open; invisible to the EG dual too (U1-cert §5.6) |
| U6 | data-noise floor on this instance | E | open; not touched by either unit |
| U7 | is the premium soft inside the balance band? | E | **restated as U13**: soft iff `EG^bal_{S₁₃}(δ) − V ≤ 5e-3` |
| U8 | `corr(S_i, M)` | E | **measured: 0.650 pooled**, 0.23–0.93 per selected rep; the ladder bites moderately |
| U9 | saturation robustness to headroom repairs | E | open; 69 zips at `u/M > 1` by ≤ 4.2e-7 (U1-cert §5.2) |
| U10 | the hand-drawn baseline's position | E | open; now to be scored as a point on the `(δ, V)` frontier, not as a `V` comparison alone |
| U11 | audited book at zip × wholesaler grain | B | open; unchanged |
| U12 | the balance↔continuity exchange rate | B → **E+B** | the band duals of `EG^bal` compute it as a shadow price (U14); the business answer becomes "is this the right δ" |
| **U13** | `EG^bal_{S₁₃}(δ)` for δ ∈ {0.0078, 0.02, 0.05, 0.10, 0.33} — the frontier in `V` | E | one parametric concave solve; **the first thing A1 should run**. Counterexample to "not soft": a flat curve until a large-zip threshold |
| **U14** | the band duals `μ_i^±` at each δ, and which zips move first as δ crosses δ* | E | readable from U13's solves; the input to U4-disp and to the sponsor question |
| **U15** | does the band change the split-unit count? `≤ k−1` was proved on the MBB face with `k` budget rows; the band adds `2k` rows, of which at most `k` are tight at a vertex | T | expected `≤ 2k−1` by the same rank argument **[prediction]**; matters because P3b's value bound scales with `M(F)` |
| **U16** | `EG^bal` at the `P₁₃` roster (R0009, R0012 in for R0017, R0018) and at every roster within the floor of it | E | two to tens of solves; bypasses OQ3's selection non-convexity by enumeration |
| **U17** | fragility of `S₁₃` to Nash ties: the best alternative Nash optimum is 1.37e-2 nats away on seed 3 and **8.1e-3 on seed 9** (1.6× the floor) | E | `P_S`, U4, U8 are functions of the set `S₁₃`; nothing detects a tie (CODEVERIFY U7-meas). Report the margin with every `S₁₃`-conditional number |
| **U18** | the rounding gap of the `EG^bal` vertex at the sponsor's δ, in nats and in moved `M` | E | decides whether any integer programming is needed at all (Move 13.1) |
| **U19** | `max_S EG^bal_S` — the roster-free bound | T | only the ceiling (69.59) bounds it today; enumeration (U16) gives a lower bound, the ladder's `P₁₃` a heuristic upper one. Whether `S ↦ EG^bal_S` has any submodular-like structure is the theorem-shaped question |

---

## Open questions this lens raises (inputs to `/domain` and `/research-plan`)

1. **[optimization]** `EG^bal_S` — the Eisenberg–Gale program with per-agent quantity bands. Is
   it in the literature as a named object (Fisher market with capacity constraints; EG with
   side constraints), do its duals retain the price reading, and does the `≤ k−1` split bound
   survive the extra rows (U15)? If the answers are yes, A1's certificate is a citation plus
   one solve, and `DOMAIN_optimization.md` §2.1's MINLP is not needed unless U18 says so.
2. **[optimization]** The frontier `δ ↦ EG^bal_{S₁₃}(δ)` as a parametric concave program:
   what is the cleanest way to trace it with SCIP-native `log` or with HiGHS on a
   log-tangent outer approximation (no conic solver on the machine), and how is the MNW point
   marked so trap 2 is not walked into by the back door (§2.5)?
3. **[economic theory]** The band duals as the exchange rate: in a CEEI with quantity
   constraints, is the multiplier on an agent's quantity bound interpretable as a price the
   *sponsor* pays for balance, and is there a known welfare-theoretic reading of "the first
   zips to move as the band loosens"? This is U12 turned into an economics question.
4. **[economic theory / optimization]** Roster selection after the ladder: with premium
   nearly determined by book disjointness (83 contested among 13), is `S ↦ EG^bal_S` close to
   modular over near-optimal rosters, so that enumeration within the `P₁₃` slack is provably
   enough (U16, U19)? `LENS_GROTHENDIECK` OQ3 in its measured form.
5. **[optimization / statistics]** Nash-tie fragility (U17): the 8.1e-3-nat margin on seed 9
   means every `S₁₃`-conditional number is one data refresh from changing. What is the right
   report — the margin, a tie-aware `P_S` over all near-optimal rosters, or both?
6. **[mechanism design]** Unchanged from the predecessor's Q4: now that books enter the draw
   only through the objective of one concave program, what exactly does `fotakis2014` forbid,
   and does `G`-invariance of the *duals* (rather than of the map) give the audited/reported
   split a formal handle? A2's question, sharpened by A1's formulation.

**Recommended order.** U13 (one parametric solve; it is the A1 kill test for the
band-constrained problem and it answers U7, and its duals give U14 for free) → U18 (round the
δ-sponsor vertex; decides whether any integer programming is needed) → U16 (the roster
enumeration) → U10 on the frontier. U15 and U19 are the theorem-shaped items and go to
`/domain optimization`. The charter's step 3 should be rewritten after U13, not before.

**Stopping review (constructed, not Gromov's — see `gromov.md`).** Question yield: six new
unknowns (U13–U19) that could not be stated before the two units landed, all shorter than the
questions they replace. Marginal value: Move 8's audit says the current form answers most of
the charter, up from "unknown" — not shrinking. Language health: the A1 problem statement is
three lines where it was a section. All three tests pass; the line is alive.
