# Optimization verdicts on td: rejected methods, checks, the screening bound

The 2026-09-02 plan was written against an unmeasured instance and proposed a 136k-binary MINLP
as its centrepiece; U1-cert and U7-meas (2026-09-03) retired most of it. Plan from the measured
rows (now the `facts/*` memories), not from the method menu.

**Rejected, with the reason (2026-09-03).**
- Rep-indexed perspective MINLP (§2.1): a contingency only. Only the roster is integral, the
  rosters worth trying are tens, and its exponential-cone / SOCP form is not executable: there
  is no conic solver and no cvxpy (`mem:verify/environment`).
- τ-homotopy (§2.6): ranging on a degenerate LP, and a balance-tight transportation LP is
  degenerate by construction (`mem:solver/lp-degeneracy`).
- ε-constraint MILP frontier in (premium, balance) (§2.5, Boland2015): wrong coordinate. `V` is
  not linear in the premium; the right frontier is `(δ, EG^bal(δ))`, one convex solve per point.
- General LNS / zip-swap neighbourhoods (§2.7): closed by measurement (`P₀ = P*(A)` exactly on
  seed 3). Only Danna2005 RINS survives, as the rounding repair.
- Proportional response as the EG solver: it cannot take side constraints, so it cannot compute
  the band-constrained program; use OA / LP or SCIP-native `log` (`mem:solver/scip-modelling`).
- §2.12's MBB rule is false as written (`mem:model/u9-bandthm`).

**Check before writing anything.**
1. δ in the band is a max deviation, not a spread. Recompute `δ₀ = max_j |m_j - T/k|/(T/k)`.
2. Never quote a single-vertex `M(F)` or rounding gap; the EG optimal face has many vertices.
3. Any frontier rendering must mark the MNW point, or balance minimisation has entered by the
   back door (trap 2).

**The screening bound (2026-09-03).**
`EG^bal_S(δ) ≤ EG_S ≤ k·log((B_tot + w·P_S)/k)`, with
`B_tot = Σ_z[c2·T_z + c_free·S_free + λM_z]` partition-invariant and `w = 0.42`. At the top
premium rung it bounds `max_S EG_S` over all rosters with no solve (U19) and turns roster
enumeration into branch and bound with a valid stop rule (U16, now U11-roster's (★) prune).
Measured values: `mem:facts/phase0-measurements`.

FOUNDATIONS entries that carried the plan: `mem:refs/optimization-foundations`.

Source: `.claude/agent-memory/domain-lens/domain-optimization-td-a1.md` (2026-09-03).
