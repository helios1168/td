# Degeneracy: the recurring hazard on this instance

- **A 1e-16 perturbation of `U`** (a different summation order) moves the selected LP vertex:
  `s_min` shifts 7e-6 relative, split counts move by one, the tight-band count by one, while the
  value and the gains are stable to 1e-9 (U8-band). Byte-identical re-runs still hold (identical
  input gives identical output). Treat `p`, `ν`, `m`, split sets and `t` as one optimum among
  many; only `φ` and `g*` are invariants.
- **Split sets are vertex-dependent, not instance invariants.** Two solves at the same `g*`
  returned different split sets of the same size (`M(F)` 66.17 against 87.66; realised gap
  5.1e-4 against 1.9e-3). Quote `|F| ≤ k-1` (or the sharp `k-1+t`), `M(F) < g_min`, and the
  direction of the bound chain; never a bare single-vertex `M(F)` or rounding gap.
- **A balance-tight transportation LP is degenerate by construction.**
  `centers.power_weights`' `beta` (`weights_raw`) equals `dF/dm_j` and is the EG multiplier only
  when the LP is nondegenerate (support = n + k - 1). On the real instance do not read HiGHS's
  beta as "the EG prices"; the bound is unaffected, the interpretation is not.
- **Multiplier gauge.** `(p, ν) -> (p - cM, ν + c·1)` leaves every identity invariant and is
  pinned only when some agent's band is slack. Quote `p_z` or `ν_i` with the tight set beside
  them (`mem:model/u9-bandthm`).
- Ranging and homotopy methods fail here for the same reason; τ-homotopy was retired on it
  (`mem:domain/optimization-verdicts`).

Source: `.claude/agent-memory/code-verify/project_td-verification-oracles.md`;
`.claude/agent-memory/modeler/project_u1-cert-eg-dual.md`;
`.claude/agent-memory/domain-lens/domain-optimization-td-a1.md`.
