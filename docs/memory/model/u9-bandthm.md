# U9-bandthm: the theory behind EG^bal_S(δ)

Unit U9-bandthm (2026-09-04) proved the five claims U8-band consumes and corrected A1's plan
documents. Check these before restating the EG^bal price or frontier story.

1. **DOMAIN_optimization §2.12's good-side MBB rule is false as written.**
   `supp(X) ⊆ argmax_i u_i(z)/q_zi` omits the `1/g_i`. The correct O(nk) rule is
   `z -> argmax_i (u_i(z)/g_i - ν_i·M_z)`, whose max value is `p_z`. U14's first-mover ranking
   must use the corrected margin.
2. **`(T/k)·Σ_i(μ_i⁺ + μ_i⁻)` is unbounded at δ = 0**: both band rows are tight for every agent,
   so a constant can be added to both multipliers. The quotable slope is the minimised one,
   `s_min = (T/k)·Σ_i |ν_i|` over the dual-optimal set (one extra small LP).
3. **The -1 in `≤ 2k-1` is unconditional.** Sharp form `#splits ≤ k-1+t` (t = band-tight
   agents), attained. Proof: the dependency `Σ_z p_z·(supply) + Σ_{i in B} ν_i·(band) -
   Σ_i (budget) = 0`, whose right side vanishes by `Σ_z p_z = k - Σ_i ν_i m_i`.
4. **Finite convergence of the OA loop is refuted as stated.** DuranGrossmann1986 finiteness is
   about convex MINLP; EG^bal is continuous and the loop is Kelley's method (in k dimensions).
   What holds: validity at every iteration, monotone masters, a certified bracket at every
   iteration, and exactness from a single tangent at the optimal `g*`, whose LP duals are the
   program's own `(p, μ±)`.
5. **Slater holds at every δ ≥ 0**, including 0 (affine constraints; `x = 1/k` is in the
   relative interior). §2.10's "multipliers exist only for δ > 0" is weaker than the truth.
6. **Multiplier gauge** `(p, ν) -> (p - cM, ν + c·1)` leaves `q_zi` and every identity
   invariant. It is pinned to c = 0 iff some agent's band is slack. Quote `p_z` and `ν_i` only
   with the tight set beside them.
7. **`δ₀` = 0.0039 (seed 3, v1) is a max deviation; N7's 0.0078 is a spread.** LENS_GROMOV M8's
   inequality is true by monotonicity; only the label was wrong. Grid from the max deviation.

Harness traps: `mem:verify/eg-band-harness`. Related: `mem:model/u1-cert-eg-dual`.

Source: `.claude/agent-memory/modeler/project_u9-bandthm.md` (2026-09-04).
