# Verification oracles: instance, assignment, MILP, coverage, gains

Every td number derives from one confidential descaled instance, so the only honest oracles are
second implementations over the same file, plus second solvers. Reach for these first on any
`docs/units/<id>.md` `## Model` against code check. Established verifying U7-meas (2026-09-03).

- **Re-read the instance yourself.** Plain `gzip` + `json`, then rebuild `S_i(z) =
  share·m_rel`, `M = m_rel`, `S_free = share_free·m_rel`; never go through `td.instance`. Format
  key `td_instance_descaled/1` (the multi-channel files are `/2`); `meta` carries
  `zips_contested`, `n_reps`, `graph_hash`.
- **Assignment and matching**: `scipy.optimize.linprog` on the assignment LP instead of
  `linear_sum_assignment` (the polytope is integral; check max fractionality = 0).
- **MILPs**: pyscipopt 6.2.1 (SCIP) is in the venv, a different solver from scipy's HiGHS;
  `python-mip` 2.0.0 too. Set `limits/gap` and `limits/absgap` to 0. See
  `mem:solver/scip-modelling`.
- **Max-k-coverage**: a submodular depth-first branch and bound (bound = f(C) + top-`left`
  marginals) certifies the 111-rep instance in 1,375 nodes / 0.1 s. Self-test it against
  `itertools.combinations` on random matrices first.
- **Gains**: recompute `g = Σ_z [c2·T + c_free·S_free + λ·M] + (1-λ)(1-θ)·S_i` by hand;
  `filler_capture="theta"` means `c_free = c2` (`mem:model/reference-parameters`).
- **Brute-force enumeration still fits small cases.** Every balanced integer assignment of 12
  zips into 3 districts of 4 (34,650) certifies `power_weights`' `lp_bound`.

Related oracles: `mem:verify/oracles-eg` (convex programs), `mem:verify/oracles-reporting`
(manifests and docs), `mem:verify/oracles-lp-labelling`, `mem:verify/oracles-milp`. Anchors:
`mem:verify/anchors`.

Source: `.claude/agent-memory/code-verify/project_td-verification-oracles.md` (U7-meas
2026-09-03, Track 1 2026-09-06).
