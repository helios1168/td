# Handoff — national channel territory design / framework 0.1 dry run (`national-channel`)

**Updated:** 2026-09-02 · **Branch:** `national-channel` · **Head:** `ec8e727` (pushed) · **Tests:** 151 pass, 0 fail (re-run 2026-09-02)

## Start here
- **Resume point:** `docs/FRAME.md` §0 — supersedes `docs/CHANNEL.md` §6–7; `CHANNEL.md` §0
  holds a pointer plus the pre-dry-run narrative.
- **Status header:** `CLAUDE.md`
- **Caution:** the repository-root checkout (`~/projects/td`) is on `contiguity-harness` and
  describes the superseded programme. Work in this worktree. It has no `.venv`; run tests with
  `/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py` (three levels up).
- **Memory:** `~/.claude/projects/-Users-ntlee-projects-td/memory/td-contiguity-programme.md`
- **Key docs:** `docs/FRAME.md` (§8 A1–A13 sponsor asks, §10 Q1–Q12 lens questions) · `docs/BRIEF.md` (the plan, units, ★ decisions) · `docs/units/*.md` (8 briefs) ·
  `docs/MODEL_U2-stab.md` + `docs/VERIFY_U2-stab.md` (the one finished unit) ·
  `docs/DOMAIN_optimization.md`, `docs/DOMAIN_economic-theory.md`, `docs/LIT_economic-theory.md`
  (46 DOIs) · `docs/LENS_GROMOV.md`, `docs/LENS_GROTHENDIECK.md` · `docs/CHANNEL.md`,
  `docs/MODEL.md`, `docs/DATA.md` · `docs/RESEARCH_FINDINGS.md`, `docs/REVIEW_GROMOV.md`

## Next actions
- [ ] **★6 (blocking) — may a unit run code against `instance_descaled.json.gz`?** It is absent
      from this worktree and `BRIEF.md` §4's constraint forbids it, so every wave-1 result is
      conditional and **U7-meas** (the measurement stage both domains wanted first) is unlaunched.
      `BRIEF.md` §7: two of those numbers could cancel the rest of the plan.
- [ ] **★3 — should roster stability be a sixth acceptance criterion?** `BRIEF.md` §5 said to ask
      after U2-stab reports; it has (question is live, non-vacuous, decidable in 169 comparisons).
- [ ] Launch the rest of wave 1 — **U0-lit**, **U1-cert**, **U3-inv**; independent, no instance
      needed. U0-lit gates wave 2 (U4-disp, U5-crit, U6-sel).
- [ ] **Sponsor questions, one sentence each** (FRAME §8): A1 ($1B target or constraint), A2 (are
      the 98 released), A6 (any operational coverage rule), **A11** (home-office / national-accounts
      share of `M` — changes `k`), **A12** (what grain the signed territory is described in),
      **A13** (any team-staffed territory — changes the matching's shape).
- [ ] **FRAME §10 Q8** is the cheapest new experiment: premium-max *balanced* draw at fixed roster
      = `centers.py`'s transportation LP with cost `−u_i(z)`; gated on ★6 (needs the instance).
- [ ] **★7** — run `/domain econometrics`? Only route to U5/A4 (regional bias in `M`) and U6
      (the tier-2 noise floor); neither has a domain file or a seeded `FOUNDATIONS.md`.
- [ ] Two doc fixes from `VERIFY_U2-stab.md`: `MODEL_U2-stab.md` §4 row 6's counts
      (2,187 / 3,672) are tie-break dependent and unlabelled; P2.2's raw threshold of 5 holds
      only under the distinctness hypothesis (4 suffices without it).
- [ ] Carried from `docs/REVIEW_GROMOV.md`, untouched by this branch: **R1** (`ceiling.py`'s
      `SATURATION = 0.05`, channel_note §5.1, FINDINGS §4C/C6's stale "α ≈ 0.9"), then C4 →
      stage-2 rescore of the cells → the cells-vs-dots call; the EG bound as certificate 5;
      R4's seven note fixes plus an eighth queued 2026-09-02 (stage 2 is unit-demand, so EF1 is
      vacuous there; `channel_note` §3's "EF1 survives" holds for the joint problem only). `BRIEF.md` §6 adds a free rename pass: *certified* → *balance-certified*.
- [ ] Open from before, unchanged: the `docs/MODEL.md` §6 list, and book-aware stage 1 vs
      `RESEARCH_FINDINGS` §9-G's books-at-stage-2-only invariant.
- [x] `td/solvers/greedy_balanced.py` deleted 2026-09-02 (was untracked, unreferenced, untested).
