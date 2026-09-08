# Track: the Headline tab must tell a refutation from a search that ran out

## Goal

`app/main.py` prints one sentence, "No map satisfies these overrides", for two outcomes that are
not the same claim. HiGHS Status 8 (scipy `status=2`) is a proof that no map satisfies the
overrides. HiGHS Status 13 with no primal solution (scipy `status=1`, `res.x is None`) says only
that the search did not reach a feasible point; CA capped at 4 at delta = 5% returns the latter
after an hour. `docs/HEADLINE.md` section 7 and `STATE.md` both insist on the distinction, and the
app is the one place a sponsor meets it. The `TODO` at `app/main.py:330` is this track.

Second, smaller item in the same commit: the tab shows the shipped cell's realised max deviation
of 5.25% beside "delta=5%" with nothing marking that it is outside the band, and a rerun's result
section shows spread but never max deviation at all.

## Next step

Committed on the branch. Ask before merging to `main`; nothing here is fast-forwarded without
the sponsor's word. After a merge, `/state` records that the tab now separates the three answers.

## Done

- Measured what scipy reports: infeasible is `status=2` with `x is None` and the message
  "The problem is infeasible. (HiGHS Status 8: model_status is Infeasible; primal_status is
  None)"; a time limit with no incumbent is `status=1` with `x is None` and "Time limit reached.
  (HiGHS Status 13: ...)". The two are distinguishable without parsing HiGHS text.
- `td/solvers/state_splits.py`: `failure_reason` names the three answers, `SolveFailure` carries
  the reason and the scipy status. It subclasses `RuntimeError`, so every existing caller and
  test still catches it.
- `tools/state_splits.py`: catches `SolveFailure` around the solve and writes
  `<out>/failure.json` (`reason`, `status`, `message`, `solve_seconds`, `delta`, `cell`) before
  re-raising, so the run still exits nonzero and `runner.status` still reads "failed".
- `app/headline.py::failure` reads that file; `app/main.py` says which of the three answers it
  got, with the elapsed search time, and falls back to the old sentence when the file is absent.
- The band wording: the shipped cell's line now names the realised numbers as realised, and the
  result section carries a four-column target-vs-realised table for both maps. It renders as
  "8 splits (CA,FL,NY,TX), realised spread 8.98%, realised max deviation 5.25%, outside its own
  5% band; balance pass 4.68%".
- Verified. 323 tests, 0 fail (321 before, plus the reason mapping and the failure record). Both
  failure paths were run end to end against the live instance from this worktree: `--cap NY=2`
  returned `reason=infeasible`, scipy status 2, HiGHS Status 8, after 40.4s; `--cap CA=4
  --unanchor CA --time-limit 10` returned `reason=no_incumbent`, status 1, HiGHS Status 13. Both
  wrote `failure.json` and re-raised, and `app/headline.py` read both back under the app venv and
  printed the matching sentence.

## Decisions needed

None. The time limit stays hard-wired at 600s; a knob for it is listed in the report, not built.

## Files owned / forbidden

Owned: `td/solvers/state_splits.py`, `tools/state_splits.py`, `app/headline.py`, `app/main.py`,
`tests/test_state_splits.py`, `docs/APP.md`, this file.

Forbidden: `STATE.md` (the hub's, updated by `/state` after merge), `docs/HEADLINE.md` (the
headline track's record; section 7 already says what this implements), everything else.
