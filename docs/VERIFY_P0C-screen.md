# VERIFY P0-C — the screen, `B_tot`, saturation, and §5.1

**Verifier:** `math-verify` (adversarial), 2026-09-05 · **Target:** track P0-C's uncommitted
changes in `.claude/worktrees/w2-phase0` (`tools/measure/premium.py`, `docs/channel_note/`).

**Artifact:** `docs/artifacts/VERIFY_P0C-screen/verify_p0c.py` (+ `verify_p0c.log`).
Re-run: `/Users/ntlee/projects/td/.venv/bin/python3
docs/artifacts/VERIFY_P0C-screen/verify_p0c.py`.
python 3.13.15 · numpy 2.5.2 · scipy 1.18.1 · sympy 1.14.0. No RNG used.

**Note added 2026-09-07.** `docs/REVIEW_GROMOV.md`, cited below by section and line, was folded
into `docs/PROBLEM.md` §2 and `docs/MODEL.md` and then deleted. Recover it with
`git show 81bd59f:docs/REVIEW_GROMOV.md`; the line references below are against that revision.

**Inputs (pinned).** `instance_descaled_v2.json.gz` (`sha256 c89f1820…`),
`battery/results/draw_k18_v2_20260904/k18` (`draw_sha256 9e091c68…`),
`battery/results/meas_v2_btot_20260905/draw_k18_v2_20260904.json`.
θ=0.40, λ=0.30, c₁=0.70, c₂=0.28, c_free=c₂, w=0.42, k=18, n_zips=3748, n_reps=114.

**Method.** Every numeric leg is recomputed from a *fresh transcription of
`channel_note.tex` eq. (util)/(Tz)/(decomp)/(split)*, reading `S`, `S_free`, `M` off the graph
directly and summing with `math.fsum` — `channel.gain_matrix` and `premium.measure` are never
the witness for their own output. The single exception is `P₁₈` (a max-k-coverage MILP), noted
below.

---

## Verdicts

| # | claim | verdict |
|---|---|---|
| 1 | `B_tot = 3268.4069219934404` = eq. (decomp)'s `W₀` | **VERIFIED** |
| 2 | `Σᵢgᵢ = B_tot + w·P₀` is P0-C's *independent oracle* | **REFUTED** (as an oracle) — the identity itself holds |
| 3 | (★)@`P_S` = 96.55406280784752, (★)@`P₁₈` = 96.79300971267465 | **VERIFIED** |
| 4 | slack 0.021911…/0.260857…; "loosening 0.064 → 0.261" | **split**: slacks VERIFIED; the 0.064 → 0.261 comparison **REFUTED** (not like-for-like) |
| 5 | `SATURATION = 29.6 %` and the six macros | **VERIFIED** (definition correctly adjudicated) |
| 6 | §5.1's 0.912 nats vs `D(g)` at 1e-4–1e-2, and the retraction | **split**: inversion + retraction VERIFIED; the `D(g)` range and the 30 % sentence **REFUTED** |

---

## C1 — `B_tot` matches the paper's `W₀`. VERIFIED

*Symbolic.* `sympy` closes eq. (util) → eq. (decomp): with `T = S_own + S_other` (eq. (Tz),
named reps only, `channel_note.tex:164-166`),

```
simplify( c1·S_own + c2·(T−S_own) + c_free·S_free + λM
          − [ c2·T + c_free·S_free + λM + (c1−c2)·S_own ] )  =  0
simplify( (c1−c2) − (1−λ)(1−θ) )                             =  0
```

so `W₀ = Σ_z[λM_z + c2·T_z + c_free·S_free(z)]` is the paper's `W₀` term-for-term.
`premium.py:255-261` codes exactly that, and `filler_capture="theta" → c_free = c2` matches
`model.utilities`' documented convention (`model.py:108-114`).

**The misread-formula failure mode was attacked specifically:**

- `T_z` over named reps only, `S_free` in its own term — the note's own footnote
  (`:180-185`) warns that `model.headroom_violations` folds `S_free` into `T_z`; `premium.py`
  does **not** make that mistake (it uses `model.free_book`, a separate attribute).
- All three `c_free` branches (`theta`/`full`/`opportunity`) are transcribed identically to
  `channel.gain_matrix:271` and `model.utilities:122`.
- **Candidacy trap checked and cleared.** `model.utilities` zeroes non-candidates, which would
  break eq. (decomp) on the 1,567 untapped + 16 vacant zips. `channel.gain_matrix` does *not*
  call `model.utilities` (its docstring says it does — a stale docstring, harmless here); it
  evaluates every rep on every zip (`channel.py:267,275-284`), which is what eq. (decomp)'s
  "for any allocation own of all of Z" requires. Had it used `model.utilities`, `Σᵢgᵢ` would
  have been short by the untapped/vacant mass.

*Numeric.* Fresh transcription `B_tot = 3268.4069219934404`, **|Δ| = 0.0e+00** against
`premium.py` (tier 1, `CERT_TOL = 1e-8`). `P₀`: |Δ| = 2.3e-13.

## C2 — the identity is **not** an independent oracle. REFUTED (as an oracle)

The identity is arithmetically true and holds on the live instance:

```
fresh Σᵢgᵢ        = 3708.248805673527
fresh B_tot + w·P₀ = 3708.248805673527      (18 × JSON mean gain: 3708.2488056735265)
```

> ⚠ **The task brief's "both sides = 3712.6435…" is a misquote.** The correct value is
> **3708.2488056735**, off by **+4.3947**. Anyone carrying 3712.6435 forward is carrying a
> wrong number; it appears nowhere in the code, the JSON or the note.

**Why it is not an oracle.** `channel.gain_matrix` accumulates `common(z) + (c1−c2)·s` zip by
zip; `premium.py`'s `B_tot` re-sums the *same* `common(z)` and `book_matrix` re-sums the *same*
`s`. The assertion is therefore a rearrangement of one sum, not two independent computations.
Mutation test (in the artifact):

| mutation | assertion |
|---|---|
| **M1** shared upstream misreading — `model.free_book` returns 2× in **both** paths | **PASSES**, while `B_tot` silently moves 3268.4069 → 3273.7194 |
| **M2** divergence — λ perturbed by 1e-6 in `gain_matrix` only | **RAISES** (Δ 2.1e-3) |

So its real discriminating power is: (i) the two code paths agree; (ii) every zip lands in
exactly one district and σ staffs all 18 districts injectively; (iii) `w = (1−λ)(1−θ)` agrees
with `c₁−c₂` (two different expressions — a genuine, if tiny, cross-check). It **cannot** see a
shared misreading of eq. (util) — which is precisely the failure mode C1 was asked about.

Keep the assertion (it is cheap and it does catch drift), but `WAVE2_PLAN.md:320`'s
"the `B_tot` identity … is the independent oracle for the (★) recomputation" **overstates it**.
The independent oracle is the fresh eq.-(util) transcription in this artifact; it agrees to
0.0e+00, so `B_tot` is verified — by the artifact, not by the assertion.

## C3 — the (★) arithmetic. VERIFIED

```
(B_tot + 0.42·1372.4513766943758)/18 = 213.60202778917102 → 18·ln = 96.55406280784752  |Δ|=0.0e+00
(B_tot + 0.42·1494.784276729282)/18  = 216.45646212331883 → 18·ln = 96.79300971267465  |Δ|=0.0e+00
```

Natural log confirmed by falsification: base-10 would give 41.932897, not 96.554063. Units are
nats. `P_S = Σ_z max_{i∈S₁₈} S_i(z)` reproduced independently (|Δ| = 2.3e-13). Direction of the
bound checked: (★)@`P_S` = 96.554 ≥ `EG_{S₁₈}` = 96.532 ≥ `V` = 95.755, and (★)@`P₁₈` ≥
(★)@`P_S` since `P₁₈ ≥ P_S`. Monotone and in the claimed direction.

*Not independently certified:* `P₁₈ = 1494.784276729282` is `premium.py`'s own max-18-coverage
MILP. I verified `status = "optimal"`, that the reported staff set attains the reported value,
and that the `(1−1/e)` greedy set attains the *same* value (greedy = MILP here, a strong
corroboration but not a proof of optimality). Re-deriving the MILP optimum over C(114,18) was
out of scope.

## C4 — the slacks, and "0.064 → 0.261". Slacks VERIFIED; the comparison REFUTED

Slacks over `EG_{S₁₈} = 96.53215175` reproduce to 1.2e-16 / 0.0e+00.

**But the two rungs are different objects and the plan crosses them.** From
`LENS_GROMOV.md:70-71` (v1, `EG_{S₁₃} = 60.6974156139`):

| rung | v1 slack | v2 slack | direction |
|---|---|---|---|
| **`P_S`** — the per-roster screen | 60.7615 − 60.6974 = **0.0641** | **0.0219** | **TIGHTENS 2.9×** |
| **`P_k`** (`P₁₃`/`P₁₈`) — the roster-*free* bound | 60.8025 − 60.6974 = **0.1051** | **0.2609** | loosens 2.5× |

`WAVE2_PLAN.md:195` ("slack over `EG_{S₁₈}` goes 0.064 → 0.261") pairs the **v1 `P_S` rung**
with the **v2 `P₁₈` rung**. It is not like-for-like.

**Which is operative for U11?** `docs/units/U11-roster.md:10` states the screen as
`EG^bal_S(δ) ≤ EG_S ≤ k·log((B_tot + w·P_S)/k)` — a **per-roster** bound evaluated at each
candidate `S`'s own coverage premium. That is the enumeration prune, and the v1 sentence "the
screen is tight" (`LENS_GROMOV.md:70`) was about exactly that rung. The `P_k` rung is the
roster-free global bound (`LENS_GROMOV.md:280`, "U19"), used to bound `max_S EG_S`, not to
prune.

⇒ **On the only rung that can be measured, U11's prune gets *tighter* on v2, not weaker.**
Telling U11 "your prune weakens 0.064 → 0.261" is unsupported by a like-for-like comparison.
What *is* true: the roster-free bound `max_S EG_S ≤ 96.793` sits 0.261 above `EG_{S₁₈}` (v1:
0.105), so the roster-free bracket widened. Both facts should be reported, separately labelled.

*Caveat.* Slack measured at one roster (`S₁₈`) is evidence about the screen's tightness at that
roster only; the prune's real power is slack relative to the *spread of `EG_S` across rosters*,
which nobody has measured at either version.

## C5 — `SATURATION = 29.6 %`. VERIFIED; the agent chose correctly

Measured on the live instance: `ΣT = 2521.8632860237576`, `ΣS_free = 18.9730029127805`,
`ΣM = 8523.2425369707`.

| definition | value |
|---|---|
| (a) `ΣT/ΣM` — the note's own `t_z = T_z/M_z` | **29.5881 %** |
| (b) `Σ(T+S_free)/ΣM` — `REVIEW_GROMOV` R1's | 29.8107 % |
| (c) `ΣS_free/ΣM` — as *worded* in the task | 0.2226 % |

> The task's second candidate is mis-worded: the 29.81 % the agent weighed and rejected is
> **(b)**, not (c). (c) is 0.22 %.

**(a) is required**, on two independent grounds:
1. `channel_note.tex:495` defines saturation as `t_z = T_z/M_z`, and `:164-166` + `:180-181`
   fix `T_z` to named representatives only, with `S_free` in its own term.
2. `ceiling.py:260-261` codes the archetype as `u_own = c1·t + λ`, `u_other = c2·t + λ` — **no
   `S_free` term at all**, i.e. "a zip whose whole book sits with one incumbent, `S_free = 0`"
   (`:497-501`). Feeding (b) into a formula that has no `S_free` slot would double-count the
   filler as the incumbent's book.

Cross-check against `STATE.md ## Facts`: v2 aggregate saturation **29.6 %** — agrees with (a)
(29.588 %), not (b) (29.811 %). (The v1 row 41.6 % is likewise (a); R1's 41.9 % is (b). The two
documents have always used different definitions — worth a one-line footnote somewhere, but the
v2 numbers are consistent.)

All six dependent macros reproduce **exactly** at the committed `SATURATION = 0.296`:
`chSat 29.6 · chUown 0.507 · chUother 0.383 · chOppShare 59.1 · chPremShare 24.5 ·
chUswing 32.5`.

> **One rounding-order finding (cosmetic, flagged not blocking).** `ceiling.py:75` stores the
> *rounded* 0.296. At the unrounded 0.2958807 the macro `chOppShare` prints **59.2**, not 59.1
> (59.1580 vs 59.1483). The other five are unchanged. Storing 0.296 is defensible (it is what
> `chSat` must print), but the note is then quoting a derived percentage computed from a
> 3-s.f. input.

## C6 — §5.1's range. Inversion + retraction VERIFIED; `D(g)` range and the 30 % sentence REFUTED

**eq. (split) closes exactly on the live draw** (tier 1):

```
first term  18·log((W₀ + w·P₀)/18) = 95.90297879222464
Σᵢ log gᵢ                          = 95.75519165924108   (metrics V: |Δ| = 1.4e-14)
D(g)                               = 0.1477871329835665  residual 0.0e+00
```

### 6a. The quoted `D(g)` range is wrong by 1–3 orders of magnitude. REFUTED

`channel_note.tex:520-521` says `D(g)` "at solver-realistic imbalances (≲ a few percent) stays
at 10⁻⁴–10⁻² nats". On the delivered v2 draw:

- **`D(g)` = 0.1478 nats** — 15× the *top* of the quoted range, 1478× the bottom.
- The realised **gain** spread is **60.17 %**, not "a few percent". The 1.37 % figure is the
  **mass** spread; `D(M) = 1.46e-4` nats — *that* is the quantity living in 1e-4–1e-2.

eq. (split) is written on `g`, not `M`. The sentence conflates the two, and the "≲ a few
percent" parenthetical is false for `g` on this instance. The range is inherited **verbatim**
from `REVIEW_GROMOV` R1's v1 bullet (`REVIEW_GROMOV.md:30-31`) — so the answer to "does the v2
redo inherit a v1 number?" is **yes, for `D(g)`**. (`0.663`/`0.249`/`29.6 %` are correctly v2;
`3.7 nats` was correctly dropped.)

### 6b. The inversion, and the retraction, still stand. VERIFIED

Even with the corrected `D(g)`:

```
premium window (P₀ → P₁₈), exact  0.8900 nats   >   D(g) 0.1478 nats     ratio 6.0×
```

The ordering **does** invert on the live instance, so the retraction of "derived rather than
assumed" at `:515-524` follows. The margin is **6×**, not the 90×–9000× the quoted numbers
imply — the conclusion survives the correction, the rhetorical force does not.

### 6c. `0.663 + 0.249 = 0.912` overstates the window by 0.022 nats

`premium.py::gap()` reports `w·ΔP/ḡ`, the **first-order** linearisation of eq. (split)'s first
term. Exactly:

| | exact `18·log(a₂/a₁)` | quoted (1st order) |
|---|---|---|
| map gap | 0.651084 | 0.663003 |
| roster gap | 0.238947 | 0.249400 |
| **combined** | **0.890031** | 0.912402 ("≈ 0.91") |

The linearisation error is **0.0224 nats = 4.5× the tier-2 floor `EPS_CERT = 5e-3`**, so it is
not covered by the project's own tolerance. It does not change any conclusion (0.890 vs 0.148
still inverts), but the note should quote **0.890** (or say "first-order").

### 6d. The 30 % threshold sentence does not follow from 29.6 %. REFUTED

`channel_note.tex:526-529` (new): "The live instance measures 29.6 % — against the 30 %
threshold this note set for a 'modest continuity tilt,' the map is **no longer** drawn by
opportunity alone."

**29.588 % < 30 %.** Under R1's definition 29.811 % < 30 % too. The note's own threshold is
**not crossed** on v2. R1's v1 41.9 % *did* cross it, which is what licensed R1's language; the
v2 redo keeps the conclusion while the number moved to the other side of the line. As written
the inference is invalid.

The *conclusion* ("incumbency book carries real weight") is independently supported by the
0.890-nat premium window measured in 6b — but it must be argued from that, not from a
threshold the instance sits below. Suggested honest reading: "the live instance measures
29.6 %, essentially at the 30 % line the note drew, and the directly measured premium window
(0.89 nats against `D(g)` ≈ 0.15) confirms incumbency is the larger term."

*Aside, not in scope but in the same paragraph:* `:516` calls the first term "bounded within a
`\chPremShare`% (=24.5 %)-scale window". 24.5 % is the *per-zip archetype* premium share of one
incumbent's utility. The **aggregate** premium share of realised welfare is **11.9 %** at `P₀`
(21.4 % at the unreachable `P_free` ceiling). Reusing the archetype number as an aggregate
window is a mild over-read.

---

## Required before the PDF is rebuilt

1. **`channel_note.tex:520-521`** — replace "`D(g)` … stays at 10⁻⁴–10⁻² nats" with the
   measured `D(g) = 0.148` nats on the delivered k=18 draw (and, if the 10⁻⁴–10⁻² range is
   kept, attribute it to `D(M)`, the mass imbalance, explicitly). **Blocking** — it is a wrong
   measured number in a sponsor-facing document.
2. **`channel_note.tex:526-529`** — the 30 % sentence. 29.6 % is *below* the threshold;
   re-argue from the 0.89-nat premium window. **Blocking.**
3. **`channel_note.tex:519`** — "≈0.91 nats" → **0.890** (exact), or label as first-order.
4. **`WAVE2_PLAN.md:195` / anything told to U11** — "slack 0.064 → 0.261" is not like-for-like.
   Like-for-like: `P_S` 0.064 → **0.022 (tightens)**; roster-free `P_k` 0.105 → 0.261.
5. **`WAVE2_PLAN.md:320`** — "the `B_tot` identity … is the independent oracle" → it is a
   duplicate-computation cross-check; the oracle of record is
   `docs/artifacts/VERIFY_P0C-screen/verify_p0c.py`.
6. **Anywhere carrying `Σᵢgᵢ = 3712.6435`** — the value is **3708.2488056735**.

Optional: `chOppShare` 59.1 vs 59.2 (rounding order, §C5); `channel.gain_matrix`'s docstring
claims it calls `model.utilities` and it does not (harmless, but the candidacy difference is
load-bearing for eq. (decomp) and deserves a correct comment).

## What was checked against an oracle vs. only for internal consistency

| checked against an **independent** oracle | checked only for **internal consistency** |
|---|---|
| `B_tot`, `Σᵢgᵢ`, `P₀`, `P_S` (fresh eq.-(util) transcription, `math.fsum`) | `P₁₈` (own MILP; `status=optimal`, staff attains value, greedy ties it) |
| eq. (decomp), eq. (split) (sympy, symbolic) | `EG_{S₁₈} = 96.53215175` (taken from U8's manifest as given) |
| `D(g)`, `D(M)`, the premium window (recomputed from gains, not from `gaps`) | the v1 anchors 60.7615 / 60.8025 / 60.6974156139 (read from `LENS_GROMOV`/`MODEL_U1-cert`, not re-solved) |
| saturation (a)/(b)/(c) and all six macros (recomputed from `ceiling.py`'s own formulas) | |

**Tolerance tiers.** Tier 1 (`CERT_TOL = 1e-8`) applies to C1/C2/C3 and eq. (split)'s residual —
all clear it, most at exactly 0.0. Tier 2 (`EPS_CERT = 5e-3` nats) is the relevant floor for
C6's 0.0224-nat linearisation error, which it **fails** (4.5×).
