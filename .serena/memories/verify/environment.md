# Environment facts for verifiers and implementers

- A worktree has no `.venv`; use the hub's python (`$TD_PY`, the hub root's
  `.venv/bin/python3`). From `.claude/worktrees/<id>` that is three levels up, not two.
- Tests: `tests/run_all.py`, a custom runner (not pytest). `tools/` is not a package: tests
  load scripts via `importlib.util.spec_from_file_location` and must register the module in
  `sys.modules` for `@dataclass` to resolve.
- Test counts over time: 184 at `74eff38`, 237 at `9cfcc2c` (2026-09-05), 546 on `main`
  (2026-09-10), 801 on `worktree-full-problem` at `3e9d002` (2026-09-11).
- `battery/` in a worktree is a symlink into the shared checkout, so the Write tool refuses to
  create files there. Durable verifier artifacts go to `tools/verify/<id>/`, committed.
- Type check: `uvx pyright --pythonpath "$TD_PY" <files>` (1.1.411 was clean on the U7 files).
- Put helper scripts in a scratch directory outside the repo and run them with the venv python;
  never name one `numbers.py` (it shadows stdlib `numbers`).
- Solver stack: SCIP 10 via pyscipopt 6.2.1, HiGHS 1.15 (highspy), scipy 1.18 `milp` and
  `linprog`, python-mip 2.0.0. There is no conic solver and no cvxpy.
- Known v1 instance defects that do not block non-geometric numbers: 6 of 1,229 zips have no
  coordinates; the 6-significant-figure export rounding makes about 69 zips miss the headroom
  inequality by a factor of 1.0000006. Use a relative tolerance of at least 1e-6 in equality
  and tie checks.

Related: `mem:verify/oracles-core`, `mem:solver/highs-and-scipy`.

Source: `.claude/agent-memory/code-verify/project_td-verification-oracles.md`;
`.claude/agent-memory/domain-lens/domain-optimization-td-a1.md`; `main:STATE.md` header.
