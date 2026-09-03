# MODEL U7-meas — the premium ladder and the other numbers measured before formulating

**Date:** 2026-09-03 · **Unit:** `docs/units/U7-meas.md` · **Track:** A1 (`docs/APPROACHES.md`
§A1), run on `wt/A1` · **Reads:** `docs/DOMAIN_optimization.md` §2.3, §5; `docs/LENS_GROMOV.md`
Move 4 and the U-ledger (U1–U4, U8); `docs/MODEL_U2-stab.md` §"decomposition"; `docs/FRAME.md`
§6; `td/channel.py`, `td/model.py`, `td/instance.py` · **Implements:** `tools/measure/premium.py`
(written by `python-typed`, checked by `code-verify` → `docs/CODEVERIFY_U7-meas.md`)

This is the measurement stage both domain plans open with. It is also the A1 charter's kill
experiment (`APPROACHES.md` §A1, "Kill experiment") and, through U1 and U10, A0's. Nothing here
needs a new solver: two Hungarian calls, one small MILP, and arithmetic.

## 1. Premium, defined

Every zip `z` carries each wholesaler's existing book `S_i(z) ≥ 0`, total booked
`T_z = Σ_i S_i(z)`, and opportunity `M_z`. A **coverage** is a map `π = (A_1, …, A_k)` (a
partition of the zips into districts) together with a roster `σ : [k] ↪ R` (an injective
assignment of districts to wholesalers). Write `rep(z) = σ(j)` for `z ∈ A_j`.

```
P(π, σ) = Σ_z S_{rep(z)}(z)                  (premium: book that lands with its own holder)
```

Book held in `z` by anyone other than `rep(z)` contributes nothing. Every `P` in this note is
reported both in descaled book units and as a **share of total book** `Σ_z T_z`.

**Why this is the term.** Per `td/model.py`, `u_i(z) = c1·S_i + c2·(T_z − S_i) + c_free·S_free +
λ·M_z` with `c1 = 1 − λ`, `c2 = θ(1 − λ)`. Rearranging,

```
u_i(z) = [c2·T_z + c_free·S_free(z) + λ·M_z]  +  (c1 − c2)·S_i(z)
       =  common(z)                            +  w·S_i(z),        w = (1−λ)(1−θ) = 0.42
```

so a district's gain to rep `i` is `g_ij = B_j + w·b_ij` with `B_j = Σ_{z∈A_j} common(z)`
independent of `i` and `b_ij = Σ_{z∈A_j} S_i(z)` the book matrix. Summed over a roster,
`Σ_j g_{σ(j),j} = Σ_j B_j + w·P(π,σ)`: at a fixed map the **only** thing the roster changes is
the premium. (`docs/MODEL_U2-stab.md` proves the decomposition; `channel.gain_matrix` computes
`g` in exactly this separated form at `td/channel.py:281-284`; the toy instance in §4 reproduces
it to machine precision.) The stage-2 objective is `V(π,σ) = Σ_j log g_{σ(j),j}`, not the sum,
so `V` is not linear in `P` — but `P` is the term that moves.

## 2. Balance versus premium

**Balance** is on the *common* measure `M`: every district's opportunity `M(A_j)` should sit
within a band of `total/k`. It is FRAME §9's settled business constraint, and the committed
draw meets it at a 0.781% spread (FRAME §6). Stage 1 (`centers.py`) optimises it alone.

**Premium** is on the *per-agent* measures `S_i`: only the holder benefits from holding.

The two pull in different directions, and every ceiling in §3 below **ignores balance by
construction**: `P_S` lets a rep with a large national book collect a territory of any size.
Those numbers are therefore *bounds* on what a redraw could recover, not maps. To keep the
balance cost visible, the script reports `V` and the `M`-spread next to every roster it
evaluates (`P₀`'s and `P*(A)`'s); the ceilings `P_S`, `P₁₃`, `P_free` have no map and no `V`.

## 3. The ladder

For a fixed draw `π₀` (the committed map) with stage-2 roster `σ₀` and selected staff
`S₁₃ = im σ₀`:

| symbol | held fixed | varies | value | method | ledger |
|---|---|---|---|---|---|
| `P₀` | map `π₀`, roster `σ₀` | nothing | `Σ_j b_{σ₀(j),j}` | evaluation | LENS_GROMOV U2 |
| `P*(A)` | map `π₀` | roster | `max_σ Σ_j b_{σ(j),j}` | Hungarian on `−b` (rectangular, 111 × 13; Kuhn 1955), same call as `channel.match` with book weights instead of log-gains | LENS_GROMOV U3 |
| `P_S` | staff set `S₁₃` | map (no balance) | `Σ_z max_{i∈S₁₃} S_i(z)` | evaluation | **new here** |
| `P₁₃` | `k = 13` | staff set and map (no balance) | `max_{|S|=13} Σ_z max_{i∈S} S_i(z)` | max-`k`-coverage MILP, §3.1 | DOMAIN_optimization §2.3 |
| `P_free` | nothing | everything, no roster limit | `Σ_z max_{i∈R} S_i(z)` | evaluation | DOMAIN_optimization §2.3 |

```
P₀  ≤  P*(A)  ≤  P_S  ≤  P₁₃  ≤  P_free
```

Each inequality is a restriction: `σ₀` is one roster; a Hungarian roster at `π₀` is one map for
`S₁₃`; `S₁₃` is one 13-set; a 13-set is one subset of `R`. The gaps locate the unrealised
premium:

- `P*(A) − P₀` — the matching. Large means A0's stage 2 is choosing the wrong roster on this
  map, fixable in milliseconds with no redraw.
- `P_S − P₀` — the map at this roster. This is the premium a redraw could recover for the
  people already selected, and it is what the A1 charter is about.
- `P₁₃ − P_S` — the roster. Large means a different 13 would hold more book than these 13
  can under any map.
- `P_free − P₁₃` — the headcount; informational only, `k` is settled (FRAME §8 A1).

**Why `P_S` is added.** The charter's kill condition pairs `P₀ ≈ P*(A)` with "few zips
contested among the selected 13" (U4). U4 measures how much *choice* a redraw has — zips where
two of the 13 both hold book — not how much premium it recovers. A selected rep's book sitting
inside another selected rep's district is recoverable premium whether or not anyone contests
the zip, and `P_S − P₀` counts exactly that. U4 is still reported (with its `M`-share), as the
charter asks, but the verdict in §5 is on the ladder.

### 3.1 `P₁₃` as a MILP

`y_i ∈ {0,1}` (rep `i` in the staff set), `w_zi ∈ [0,1]` on the pairs with `S_i(z) > 0` only
(the `cand(z)` structure; 675 contested + 477 uncontested zips, a few thousand pairs):

```
max   Σ_{z,i} S_i(z)·w_zi
s.t.  Σ_i w_zi ≤ 1            ∀z
      w_zi ≤ y_i              ∀(z,i)
      Σ_i y_i = 13
```

`w` is integral at an optimum for fixed `y` (each zip picks its best selected rep), so the
LP-relaxed `w` loses nothing. `scipy.optimize.milp` with `mip_rel_gap = 0.0` (trap 12). The
greedy `(1 − 1/e)` solution seeds it and is reported alongside; a `time_limit` stop is
reported as *no bound* (trap 15), never as `P₁₃`.

## 4. Worked example

Three wholesalers A, B, C; four zips; `k = 2`; book table and opportunity:

| zip | `S_A` | `S_B` | `S_C` | `M` |
|---|---|---|---|---|
| z1 | 10 | 0 | 0 | 20 |
| z2 | 6 | 4 | 0 | 15 |
| z3 | 0 | 8 | 3 | 15 |
| z4 | 0 | 0 | 9 | 20 |

Total book 40. Map `π₀`: D1 = {z1, z2}, D2 = {z3, z4} (balanced: 35 / 35 in `M`). Book
matrix `b` (rows A, B, C; columns D1, D2): `[[16, 0], [4, 8], [0, 12]]`.

Take the **hand-staffed** roster D1 → A, D2 → B as the committed `σ₀`:

- `P₀ = 16 + 8 = 24` (60%).
- `P*(A)`: rosters at this map — (A, B) = 24, (A, C) = 28, (B, C) = 16 → **28** (70%), roster
  (A, C). The gap is in the matching: B on D2 forfeits z4's 9.
- `P_S` at `S = {A, C}`: z1 → A (10), z2 → A (6), z3 → C (3), z4 → C (9) → **28**. Nothing left
  for a redraw at this roster. (At `S = {A, B}` it would be 24 = `P₀`: likewise nothing.)
- `P₁₃` (= `P₂` here): {A, C} = 28, {A, B} = 24, {B, C} = 21 → **28**.
- `P_free`: every zip to its top rep → 10 + 6 + 8 + 9 = **33** (82.5%), unreachable with two.

Ladder `24 ≤ 28 ≤ 28 ≤ 28 ≤ 33`. Reading: the whole reachable gap is the matching; a redraw
buys nothing; A1 would be killed on this instance.

Two checks the test fixture pins. (i) `channel.gain_matrix` on this instance at θ = 0.40,
λ = 0.30 gives `g = [[22.82, 16.10], [17.78, 19.46], [16.10, 21.14]]`, and `g − 0.42·b` has
identical rows (the rep-independent `B_j`), confirming §1. (ii) `channel.stage2` (Nash) picks
D1 → A, D2 → C on its own, `V = 6.1788`, so under the *model's* stage 2 `P₀ = 28 = P*(A)` and
the matching gap vanishes; the 24 is what a hand-drawn roster leaves behind. The script
therefore takes `σ₀` from the draw's recorded `metrics.json` winner and recomputes it through
`channel.stage2` as an assertion, and accepts an explicit roster override for baselines (U10).

## 5. The other numbers

| # | quantity | definition | ledger |
|---|---|---|---|
| U1 | realised-gain spread | `min_j g_{σ₀(j),j}`, `max_j`, `(max − min)/mean`, beside the same three on `M(A_j)` | LENS_GROMOV U1; A0's second kill |
| U4 | contested among the 13 | `#{z : |cand(z) ∩ S₁₃| ≥ 2}` and `Σ M_z` over them as a share of `Σ_z M_z` | LENS_GROMOV U4 |
| U8 | book–opportunity correlation | Pearson `corr(T_z, M_z)` pooled over zips, and `corr(S_i(z), M_z)` for each `i ∈ S₁₃` over the zips where `S_i(z) > 0` | DOMAIN_optimization §5 row 4 |
| — | `V` at `σ₀` and at the `P*(A)` roster | `channel.stage2` value; `V` rescored with the premium-optimal roster fixed | shows the balance cost of the relabel |

Read-only probe before the unit (2026-09-03, seed-3 draw): U4 = **83 of 675** contested zips,
**6.12%** of `M`. The script must reproduce it.

## 6. Verdict rule for the A1 kill experiment

Convert a premium gap `ΔP` (book units) to nats through the stage-2 objective: a relabel or
redraw that adds `ΔP` of premium adds `w·ΔP` of gain spread across districts, and
`Σ_j log g_j` moves by about `w·ΔP / ḡ` where `ḡ` is the mean realised gain at `σ₀`. Call a
gap **small** if `w·ΔP / ḡ ≤ 5e-3` (the tier-2 floor, `td/solvers/base.py`, FRAME §6). This is
a first-order conversion, reported next to the raw gap, not a certificate.

- All three of `P*(A) − P₀`, `P_S − P₀`, `P₁₃ − P_S` small → **A1 collapses to A0 plus a
  relabel**; record `abandoned` in `APPROACHES.md` §0 with the three numbers.
- Otherwise A1 stays `running`, and the largest gap names what it can win: matching (A0's
  stage 2 is wrong), map (A1's redraw), or roster (A1's `Σ y = k` selection).
- Independently, U1: if the `g`-spread is far from the 0.781% `M`-spread, A0's headline
  balance number measures the wrong thing (A0's soft kill).

## 7. Inputs, outputs, provenance

Inputs: `instance_descaled.json.gz` (via `td.instance.load_descaled`), a draw directory in
either layout (`<dir>/draw.csv` + `metrics.json`, or `<dir>/k13/…`), and `θ`, `λ`,
`filler_capture` at `channel.gain_matrix`'s defaults. Runs on both k=13 draws:
`battery/results/draw_k13_20260901` (seed 3, balance-certified, FRAME §6's committed draw) and
`battery/results/sweep_20260902_s10/k13` (seed 9, +0.103 nats of staffing, FRAME §0).

Output: one JSON per draw under `battery/results/meas_20260903/`, carrying run id, instance
sha256, draw-file sha256, the parameters, every number above in both units, the `P*(A)` roster,
and the verdict-rule conversions. Byte-identical on re-run apart from a timestamp field.

**Stop rule** (from the unit brief): if a number cannot be computed because of a FRAME §5 data
defect, report the defect and the affected number; do not repair the data.
