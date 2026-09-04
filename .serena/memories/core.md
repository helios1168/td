# Project Core

Territory design for a new "national" annuity wholesaling channel: carve two largest firms
out of financial-institutions/wirehouse channels, split ~1,229 zips / 111 reps / ~$13B
opportunity into k≈13 territories of ~$1B each. Greenfield balanced districting (not the
two-player fair-division problem the repo predates), solved as maximum Nash welfare over a
per-rep utility model.

Two stages:
- **Stage 1 (draw)**: k balanced compact districts on opportunity alone (no contiguity --
  sold-zip graph has 547 components; treated as a power diagram).
  `td/solvers/centers.py` (k-means++ seed, transportation-LP balance, Lloyd, Nash polish,
  power diagram/duals), `td/solvers/cert_draw.py` (four post-hoc certificates).
- **Stage 2 (match)**: assign reps to districts, exact max-weight matching on log gains
  (Hungarian). `td/channel.py` (stage 2, balance report, `place_by_state`,
  `allocate_districts` ceiling/dual bound).

Other core files: `td/model.py` (N-way primitives: utilities, gains, objective, perimeter,
n-agent EF1), `td/instance.py` (loads the descaled real instance), `td/geo.py` +
`tools/us_maps.py` (ZCTA points/projection/figures), `tools/run_draw.py` (the reproducible
instance -> draws -> stage 2 -> results pipeline), `td/solvers/scip_tree.py` +
`td/solvers/cert_exact.py` (two-player MILP engine + exact certificate, not what stage 1 is
built on), `td/solvers/{base,brute}.py` (harness contract, brute-force oracle).

This is a git worktree of `/Users/ntlee/projects/td` (current branch a `wt/*` track branch).
The fast-moving state narrative (what's built, what's launched, resume point) lives in
`docs/FRAME.md` §0 and the root `CLAUDE.md`, not here -- these memories cover durable
structure/conventions only and should not be updated to track it.

See `mem:tech_stack`, `mem:suggested_commands`, `mem:conventions`, `mem:task_completion`.
