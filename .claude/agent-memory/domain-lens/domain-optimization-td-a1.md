---
name: domain-optimization-td-a1
description: Traps, rejected methods and load-bearing FOUNDATIONS entries from /domain optimization runs on the td national-channel problem (A1 track, 2026-09-03)
metadata:
  type: project
---

Running `/domain optimization` on td: what earlier runs decided, so a later run does not
re-propose retired methods or re-derive settled bounds.

**Why:** the 2026-09-02 plan was written against an unmeasured instance and proposed a
136k-binary MINLP as its centrepiece; U1-cert and U7-meas (both 2026-09-03) retired most of it.
A re-run that plans from the method menu rather than from FRAME §6's measured rows will
reproduce the same wrong centrepiece.

**How to apply:** read `docs/FRAME.md` §6's dated rows *before* `docs/DOMAIN_optimization.md`;
the §6 rows dated later than the DOMAIN file's header are what changed.

## Rejected, with the reason (2026-09-03)

- **Rep-indexed perspective MINLP (§2.1)** — retired to a contingency. Three reasons: only the
  roster is genuinely integral; the rosters worth trying are tens; and its stated
  exponential-cone/SOCP form is **not executable — there is no conic solver and no cvxpy on this
  machine** (stack: SCIP 10 via pyscipopt 6.2.1, HiGHS 1.15, scipy 1.18 `milp`/`linprog`).
- **τ-homotopy (§2.6)** — retired. Its own failure mode fires: ranging on a degenerate LP, and a
  balance-tight transportation LP is degenerate by construction.
- **ε-constraint MILP frontier in `(premium, balance)` (§2.5, Boland2015)** — wrong coordinate.
  `V` is not linear in the premium; the right frontier is `(δ, EG^bal(δ))`, one convex solve per
  point.
- **General LNS / zip-swap neighbourhoods (§2.7)** — closed by measurement: `P₀ = P*(A)` exactly
  on seed 3, so relabelling buys nothing. Only Danna2005 RINS survives, as the rounding repair.
- **Proportional response as the EG solver** — cannot take side constraints, so it cannot compute
  the band-constrained fibre. Any new run must use OA/LP or SCIP-native `log`.

## Numbers that drove it (FRAME §6, 2026-09-03)

`EG_{S₁₃} = 60.6974` vs `V = 59.9375` (gap 0.760 nats, bracket 7e-15); the EG vertex has
`M`-spread ≥ 50%, so that gap is over a feasible set the sponsor rejects. Premium ladder: match
gap 0, map gap 0.640 nats, roster gap 0.043. `g`-spread 60.65% vs `M`-spread 0.781%. 83 contested
zips among the 13 (6.12% of `M`). `corr(T_z,M_z) = 0.650`. Tier-2 floor 5e-3 nats; the Nash-tie
margin on seed 9 is 8.1e-3, only 1.6× the floor.

## FOUNDATIONS entries that turned out to matter

Load-bearing for the 2026-09-03 plan: **BoydVandenberghe2004** and **Rockafellar1970** (the
perturbation function of `EG^bal(δ)` is concave, multiplier = supergradient — this is what makes
*one* solve bound the whole frontier), **KuhnTucker1951** (agent-specific effective prices
`q_zi = p_z + ν_i M_z`), **WesterlundPettersson1995** + **DuranGrossmann1986** (LP outer
approximation: every master optimum is a *valid upper bound*, which is the whole architecture
given no conic solver), **VigerskeGleixner2018** (SCIP cross-check), **Chvatal1983**
(RHS ranging, warm starts, and the assignment stability radius for the tie question),
**Danna2005** (RINS = the band-aware rounding repair), **CodatoFischetti2006** (no-good cuts to
enumerate near-optimal rosters). Dormant and staying dormant: all of FOUNDATIONS §8 (contiguity).

## Things to check before writing anything

1. `δ` in the band is a **max deviation**, not FRAME §6's **spread** (0.781%). `LENS_GROMOV`
   M8 writes the sandwich's left endpoint as 0.0078 using the spread; that inequality may be
   false. Recompute `δ_0 = max_j |m_j − T/k|/(T/k)` first.
2. Never quote a single-vertex `M(F)` or rounding gap — the EG optimal face has many vertices and
   two independent solves returned different split sets of the same size (`MODEL_U1-cert` failure
   mode 9).
3. Trap 2 (`CLAUDE.md`): any frontier rendering must mark the MNW point, or balance minimisation
   has entered by the back door.

## The one new result the 2026-09-03 plan contributed

`EG^bal_S(δ) ≤ EG_S ≤ k·log((B_tot + w·P_S)/k)` with `B_tot = Σ_z[c2·T_z + c_free·S_free + λM_z]`
partition-invariant and `w = 0.42` — a closed-form screening bound from the premium ladder. At
`P₁₃` it bounds `max_S EG_S` over all ~10¹⁶ rosters with no solve (answers U19), and it turns
roster enumeration into branch-and-bound with a valid stop rule (U16). **Compute it before
searching for it** (§8 Q11); the illustrative arithmetic in the plan was done by hand, not run.

Related: [[td-a1-track-state]]
