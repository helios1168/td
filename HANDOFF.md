# Handoff — national channel (branch `national-channel`)

**Updated:** 2026-09-02 · **Branch:** `national-channel` · **Head:** `01e1e84` · **Tests:** 151 pass, 0 fail

## Start here
- **Resume point:** `docs/CHANNEL.md` §0 — the canonical, chained state narrative (read first).
- **Status header:** `CLAUDE.md` (branch/head/tests + pointer to §0).
- **Memory:** `~/.claude/projects/-Users-ntlee/memory/td-national-channel.md`.
- **Key docs:** `docs/CHANNEL.md` (the problem), `docs/MODEL.md` (the model), `docs/DATA.md`
  (the export route), `docs/RESEARCH_FINDINGS.md`, `docs/REVIEW_GROMOV.md`, `docs/channel_note/`.
- **Caution:** the repository-root checkout (`~/projects/td`) is on `contiguity-harness` and
  describes the superseded programme. Work in this worktree. It has no `.venv`; run tests with
  `../../.venv/bin/python3 tests/run_all.py`.

## Next actions
- [ ] **Decision (needs user's call):** at measured 41.9% saturation, does stage 1 get to see
      books? Value on the table says yes (~3.7 nats); FINDINGS §9-G's invariant ("books enter at
      stage 2 only") says no, and `score_draws` already breaches it mildly. Audited
      system-of-record books are the likely escape.
- [ ] **132-dots vs power-diagram cells** (lexicographic compactness-vs-Nash): gated on the
      stage-2 rescore of the cells — order C4 → rescore → adopt unless staffing drops by more
      than the portfolio spread. See `docs/RESEARCH_FINDINGS.md` §9-C4/D.
- [ ] **R1 fixes still open:** `ceiling.py`'s `SATURATION = 0.05` constant and the
      `channel_note` §5.1 rewrite. (CHANNEL.md §0 and CLAUDE.md's ~5%/90% lines already corrected
      at `01e1e84`.)
- [ ] **Stale number:** FINDINGS §4C/C6's "α ≈ 0.9 expected" — measured α ≈ 0.6.
- [ ] **R4:** seven local note fixes to fold into the §9-B citation pass (see
      `docs/REVIEW_GROMOV.md`), plus an eighth queued 2026-09-02: stage 2 is unit-demand, so
      EF1 is vacuous there; `channel_note` §3's "EF1 survives" holds for the joint problem only.
- [ ] **Dispose of `td/solvers/greedy_balanced.py`** (untracked, unreferenced, untested, written
      2026-09-01 20:39): commit with a test and a build-table line, or delete.
