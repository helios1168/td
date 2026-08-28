# Objection 2 revisited: does a concave capacity response move the allocation?

**Read `HANDOFF_REVIEW.md` first.** This supplements it. Retirement condition set there
(§5, objection 2): *"fit a crude concave response and check whether the allocation
moves."* Run below, two different concave shapes, deliberately different in kind. All
numbers under the **settled** `d=(0,0)` baseline, recomputed from the code, not read off
a prior run. Scope caveat is unchanged from the rest of `review/`: everything here is the
`zip50.py` synthetic instance (corr(A_z,B_z)=+0.68); see §7.

**Verdict up front: confirmed, not retired** — and the reason is sharper than "capacity
matters." A capacity assumption that is even mildly correlated with legacy book size
reproduces, almost exactly, the pre-merger-baseline allocation that objection 1 got
retired for. Objection 2 is not an independent, later concern. Left unexamined, it is a
side door back into objection 1.

---

## 1. Two response shapes, tested for different reasons

The linear model scores territory size with no diminishing returns: a rep winning 40
zips is serviced at the same per-zip effectiveness as one winning 4. `u_a(z)` composes
with a concave transform `f` of the *pooled raw gain*, `G_a(S) = f(raw_a(S))`, and the
solver re-maximises `log G_a + log G_b`. `f = identity` recovers the plain model exactly.
Both shapes below still compose with the outer-approximation solver used everywhere else
in `review/` — `log(f(y))` is concave whenever `f` is concave increasing and `y` is
linear in `x`, so the tangent-cut machinery in `dzero.py` generalises by swapping in
`log f` and its derivative (`code/capacity.py::nash_exact_capacity`, validated against
brute force on 100/100 instances at n=12, power and saturating, symmetric and
asymmetric parameters).

**POWER**, `f(y)=y**kappa` — homogeneous. Run first because it is cheap to check and,
it turns out, degenerate: see §2.

**SATURATING**, `f(y)=K(1-e^{-y/K})` — a capacity ceiling `K` in raw-utility units, not
homogeneous. This is the substantive case: §3.

---

## 2. Power-law track: exactly the same instability the review already found

**Symmetric `kappa` is provably a no-op, for every `kappa`, not approximately.**
`log(raw_a**kappa) + log(raw_b**kappa) = kappa*(log raw_a + log raw_b)` — verified
symbolically (`code/obj2_power.py`, sympy simplifies the difference to exactly `0`). A
positive scalar multiple of an objective never changes its argmax, allocation by
allocation, so no search is needed to know the result: swept `kappa` in
`{0.15, 0.30, 0.50, 0.70, 0.90, 1.00}` on the 50-zip instance and the allocation does not
move once, at any value *(verified)*.

**Asymmetric `kappa` is not a new phenomenon — it is `omega.py`'s asymmetric-Nash weight
by another name.** `kappa_a != kappa_b` maximises `kappa_a*log(g_a) + kappa_b*log(g_b)`,
which has the same argmax as `omega*log(g_a) + (1-omega)*log(g_b)` for
`omega = kappa_a/(kappa_a+kappa_b)`. Checked directly against `asym_nash` for six
`(kappa_a,kappa_b)` pairs: identical allocation in 5/6 *(verified)*; the sixth
(`kappa_a=.55, kappa_b=.45`, i.e. `omega=.55` exactly) differs by 5 zips only because
that omega sits on a genuine near-tie in the data (objective values differ by `8e-7` out
of `~2.0`, i.e. two independent solver runs landing on opposite sides of a knife-edge —
not a violation of the identity). Sweeping the ratio `kappa_a/kappa_b` from 1.00 to 2.00
reproduces the *same* shape as the review's own omega sweep — 0 zips at parity, growing
roughly monotonically with the ratio, 11 zips moved by `kappa_a/kappa_b=2` — because it
*is* that sweep, computed a second way.

**Conclusion: the power-law framing of "capacity elasticity" contributes nothing new.**
It is either a no-op (symmetric) or a restatement of the omega-instability finding
objection 1 already produced (asymmetric). No separate mitigation is needed; the
guidance in `HANDOFF_REVIEW.md` §6 ("any material tilt forfeits EF1") already covers it.

---

## 3. Saturating-ceiling track: the real content of objection 2

No-capacity baseline for reference: `k=22, y_a*=7.3715, y_b*=7.2318` (matches
`HANDOFF_REVIEW.md` §2's `d=(0,0)` row exactly).

### 3a. Symmetric ceiling `K_a=K_b=K`: cosmetic down to a severe constraint

| K | K / y_a* | K / y_b* | zips moved | objective gained by re-solving |
|---|---|---|---|---|
| 10 – 4 (six values) | 1.36 – 0.54 | 1.38 – 0.55 | **0** | 0 |
| 3.0 | 0.41 | 0.41 | 2 | 8.6e-6 |
| 2.0 | 0.27 | 0.28 | 2 | 1.3e-5 |

*(verified, `code/obj2_capacity.py` Test A, `code/mkfig_obj2.py` panel a)* Even where it
moves 2 zips, they are a knife-edge tie: at very loose `K` those two zips sit at utility
ratio `1.024742` vs `1.025190` — 0.04% apart — and the objective gain from moving is
`~1e-5`, four to five orders of magnitude below the gains seen once the ceiling is
asymmetric (§3b). **A capacity ceiling that is genuinely the same number for both reps
does not, on its own, materially move the allocation, unless it is pushed below roughly
half of what each rep would otherwise be given** — a considerably more severe
constraint than "capacity exists."

### 3b. Book-proportional ceiling `K_a=m*S_a, K_b=m*S_b`: real, not cosmetic

Own book is the only capacity signal present in this data, so it is the natural (not the
only defensible) crude proxy. Both directions tested, because §4 of `HANDOFF_REVIEW.md`
already recorded what happens when only one direction of an asymmetry gets checked.

| m | zips moved, a-favored (`K_a{=}mS_a,K_b{=}mS_b`) | zips moved, b-favored (swapped) |
|---|---|---|
| 10 | 2 | 2 |
| 6 | 4 | 3 |
| 5 | 2 | 3 |
| 4 | 3 | 2 |
| 3 | 4 | 3 |
| 2 | 4 | 5 |
| 1.5 | 5 | 6 |
| 1.0 | 7 | 6 |

*(verified, Test B/B', `code/mkfig_obj2.py` panel b)* Unlike the symmetric case, the
objective gain from re-solving is real and grows monotonically as `m` shrinks: `1.4e-3`
at `m=10` (the loosest value tested — capacity ten times the pre-merger book) up to
`1.4e-2` at `m=1`, two to three orders of magnitude above the symmetric-ceiling noise
floor in §3a. The effect reverses direction when the proxy is inverted (b-favored column)
— confirming a real mechanism tied to which side's ceiling binds first, not an artefact
of one arbitrary sign choice.

### 3c. The headline: this can silently reproduce the rejected map

| m | zips vs. **rejected** `d=(S_a,S_b)` map | zips vs. **settled** `d=(0,0)` map |
|---|---|---|
| 10 | 3 | 2 |
| 6 | 3 | 4 |
| 5 | 1 | 2 |
| 4.5 | 3 | 4 |
| 4 | 2 | 3 |
| **3.5** | **0** | 3 |
| 3 | 1 | 4 |
| 2.5 | 2 | 5 |

*(verified, `code/mkfig_obj2.py` panel c — same run also spot-checked at m=3.5..5.0 in
`code/obj2_capacity.py`, identical figures)* At `m=3.5` — capacity set to 3.5 times each
rep's pre-merger book, not an extreme assumption given the realised post-merger books are
themselves 2.5–4x the pre-merger ones — the book-proportional-capacity allocation is
**bit-identical to the rejected pre-merger-baseline map**: 0 zips differ. At `m=5` only 1
zip differs. Across this whole range it differs from the currently-settled `d=(0,0)` map
by 2–5 zips, i.e. by *more* than it differs from the map objection 1 spent a full review
retiring.

Concretely, at `m=4` (comfortably above the survival threshold for a's book, `y_a*/S_a =
2.46`, and close to it for b's, `y_b*/S_b = 4.02`):

| allocation | k | a's book | b's book | a's opp. share | a vs pre-merger | b vs pre-merger |
|---|---|---|---|---|---|---|
| no capacity, `d=0` (settled) | 22 | 7.372 | 7.232 | 48.9% | +145.7% | +301.8% |
| pre-merger baseline, rejected | 25 | 7.979 | 6.639 | 53.4% | +166.0% | +268.8% |
| **book-capacity, `m=4`, `d=0`** | **25** | **7.936** | **6.681** | **53.1%** | **+164.5%** | **+271.1%** |

The last row and the middle row are not identical, but they are close enough (0.5 points
of book each, 0.3 points of opportunity share) that a reader could not tell them apart in
a committee room. **Setting `d=0` does not, by itself, prevent a legacy-book-size
asymmetry from re-entering the allocation.** It just relocates the channel from an
explicit, auditable disagreement point to an implicit, easy-to-miss capacity assumption
that looks purely operational.

---

## 4. Verdict

| # | Objection | Status | Retirement condition |
|---|---|---|---|
| 2 (power-law framing) | Capacity as elasticity in territory size | **Retired as a distinct concern** — provably a no-op when symmetric, and identical to the already-covered omega-instability finding when not | none needed; `HANDOFF_REVIEW.md` §6 governs |
| 2 (capacity-ceiling framing) | Capacity as a hard-ish servicing limit | **Confirmed, not retired.** Symmetric ceilings are cosmetic; ceilings correlated with legacy book size are not, and at plausible multiples reproduce the rejected `d=(S_a,S_b)` map almost exactly | **New condition, unresolved:** get a capacity signal that is *not* a proxy for legacy book size (see §5), or explicitly own the reintroduced tilt the way `HANDOFF_REVIEW.md` §6 asks any seniority weight to be owned |

Objection 2's other sub-claim — theta constant across zips though transfer capture
plausibly depends on relationship depth — is **not addressed here**; no real
relationship-depth signal exists in the synthetic instance to test it against, and
inventing one would be exactly the kind of undefended proxy this note just warns against
for capacity. Left open.

---

## 5. What this means operationally

**Do not use legacy book size as a capacity proxy without saying so out loud.** Book size
is the only capacity-shaped signal sitting in this data, which makes it tempting to reach
for — and §3c shows reaching for it, even informally ("bigger book, more infrastructure,
more capacity"), quietly reopens the entitlement question the disagreement-point decision
was supposed to close. If distribution wants a capacity constraint, the analogous demand
`HANDOFF_REVIEW.md` §6 makes of an explicit seniority weight applies here too: name the
capacity number, defend where it came from, and state plainly that it is expected to move
the allocation toward whichever rep it favors.

**A genuinely symmetric capacity ceiling is comparatively safe.** §3a shows the same
numeric ceiling for both reps barely moves anything until pushed to roughly half of what
the model already wants to give each side — well past where a real staffing constraint
would plausibly sit for two reps managing a comparable book. If a capacity mechanism is
wanted mainly to be defensible against an "unlimited attention" critique rather than to
change the split, a shared ceiling well above each rep's `d=0`-optimal raw gain does that
job at negligible cost.

**If capacity is to bind for real, it needs its own data.** Producer-appointment counts,
scheduled hours, or an explicit staffing number per rep would be a legitimate, non-book
capacity signal. None of those exist in this dataset; this is a gap to close with real
data, not to paper over with a book-size proxy.

---

## 6. Scope of these findings

Same caveat as the rest of `review/`: every number here comes from `zip50.py`'s synthetic
50-zip mixture (corr(A_z,B_z)=+0.68). The *structural* findings should generalise: that
symmetric power-law capacity is exactly neutral; that asymmetric power-law capacity
collapses into the omega-instability already found; that a symmetric capacity ceiling is
close to neutral; and that a book-size-correlated ceiling is not, and can reproduce the
rejected baseline. The *specific* multiples — `m~3.5` for exact reproduction, the
particular zip counts — are instance-specific and should be recomputed on real data
before being quoted.

---

## 7. Files

```
review/
  objection2_capacity.md         this file
  figures/
    capacity_ceiling_test.png    3 panels: symmetric ceiling is cosmetic (a), book-
                                 proportional ceiling is not (b), and it converges to
                                 the rejected pre-merger-baseline map (c)
  code/
    capacity.py                  nash_exact_capacity -- outer approximation generalised
                                 to any concave response (f, log f, (log f)'); power_
                                 response and saturating_response factories; validated
                                 against brute force, 100/100 at n=12
    obj2_power.py                the power-law track: symbolic no-op proof, numeric
                                 confirmation, and the kappa<->omega equivalence check
    obj2_capacity.py             the saturating-ceiling track: symmetric sweep (3a),
                                 book-proportional sweep both directions (3b), and the
                                 comparison against both baselines (3c)
    mkfig_obj2.py                figure generation for capacity_ceiling_test.png
```

**Running the code.** Same environment as the rest of `review/` (numpy, scipy>=1.9,
sympy, matplotlib, networkx). Expects `/tmp/z50.pkl` from `../code/zip50.py`, and
`obj2_power.py`/`mkfig_obj2.py` additionally import `omega.py`/`dzero.py` from this
directory (both already `sys.path.insert` themselves).
