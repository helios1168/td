# Verifying a combinatorial MILP (Track 2 state-splits, 2026-09-07)

- **Enumerate the integer part, LP the continuous part.** For a min-splits MILP with binary `z`
  and continuous shares `y`, brute force every `2^(S·k)` z-pattern (S = 6, k = 2 gives 4,096),
  reject with a hand-written BFS, and price each survivor with a dense hand-built share LP.
  Objective and split count then match `solve()` to under 1e-7 on five settings in seconds.
- **Symbolic row read-back.** Densify `problem.A`, rebuild every named block from the model's
  algebra, and assert equality block by block, plus "the named blocks account for all rows".
  That catches an extra undocumented row, which a feasibility oracle never does.
- **Strip the constraint blocks you want to test.** Keeping only root/rz/flow/net rows and
  pinning `z` by bounds turns a contiguity claim into 2^S HiGHS feasibility calls against BFS.
- **Run a round-capped routine at every cap 0..n.** Once `rounds_used` saturates below the cap,
  labels must be byte-identical across caps; that checks "a rejected round is a no-op" without
  reaching inside the loop.
- **Row counts in a plan go stale before the code does.** The plan said 6,583 rows; the code
  builds 11,317 = 6,583 + 882 (an `η z ≤ y` block from a later amendment) + 3,852 (capacity per
  directed arc instead of per arc pair). Reconcile the gap exactly; an exact decomposition
  distinguishes a stale number from a construction bug.
- **Time the real-shape build even when it is not a listed claim.** A plan's "seconds" for scf
  contiguity at k = 18 did not hold on two synthetic 49-node / 107-edge instances: 300 s time
  limit, 10.9% gap on the planar one. scf relaxations are weak; runtime is the risk, not row
  count. `solve()` raises on a time limit, so slowness is a hard failure downstream.
- **`scipy.optimize.milp` accepts no warm start** (options are only disp, presolve,
  time_limit, node_limit, mip_rel_gap). Any model text saying a heuristic "seeds" that MILP is
  unimplementable; check for it.

Related: `mem:solver/highs-and-scipy`, `mem:verify/oracles-lp-labelling`.

Source: `.claude/agent-memory/code-verify/project_td-verification-oracles.md`.
