# Handoff — national channel territory design / stage-1 scenarios (`stage1-scenarios`)

**Updated:** 2026-09-02 · **Branch:** `stage1-scenarios` · **Head:** `8eece3f` (pushed as `origin/stage1-scenarios`; off `national-channel` at `544504e`) · **Tests:** 174 pass, 0 fail (run 2026-09-02)

## Start here
- **Resume point:** `docs/FRAME.md` §0 — supersedes `docs/CHANNEL.md` §6–7; `CHANNEL.md` §0
  holds a pointer plus the pre-dry-run narrative.
- **Status header:** `CLAUDE.md`
- **Caution:** the repository-root checkout (`~/projects/td`) is on `contiguity-harness` and
  describes the superseded programme. Work in this worktree. It has no `.venv`; run tests with
  `/Users/ntlee/projects/td/.venv/bin/python3 tests/run_all.py` (three levels up). The instance
  (`instance_descaled.json.gz`) and the gazetteer cache (`data/geo/`) are gitignored and were
  copied into this worktree by hand — a fresh worktree needs the same two copies.
- **Do not use Serena in this worktree:** the MCP server binds to the session's launch
  directory and edits the wrong tree (it did, once, on 2026-09-02 — reverted).
- **Memory:** `~/.claude/projects/-Users-ntlee-projects-td/memory/td-contiguity-programme.md`
- **Key docs:** `docs/FRAME.md` (§0 resume, §8 A1–A13 sponsor asks, §10 Q1–Q12 lens questions) · `docs/BRIEF.md` (the plan, units, ★ decisions) · `docs/units/*.md` (8 briefs) ·
  `docs/MODEL_U2-stab.md` + `docs/VERIFY_U2-stab.md` (the one finished unit) ·
  `docs/DOMAIN_optimization.md`, `docs/DOMAIN_economic-theory.md`, `docs/LIT_economic-theory.md`
  (46 DOIs) · `docs/LENS_GROMOV.md`, `docs/LENS_GROTHENDIECK.md` · `docs/CHANNEL.md`,
  `docs/MODEL.md`, `docs/DATA.md` · `docs/RESEARCH_FINDINGS.md`, `docs/REVIEW_GROMOV.md`
- **The scenario runner:** `tools/run_draw.py instance_descaled.json.gz --k 8-16 --seeds 0-4
  --fix SOUTHWEST=TX,OK --anchor FLORIDA=FL --workers 8 --out battery/results/<run>/`
  (module docstring has the layout; `--scenario file.json` takes the same `fix`/`anchor` keys).
  Latest runs: `battery/results/sweep_20260902/` (unpinned) and `sweep_20260902_south/`.

## Next actions
- [ ] **Sponsor: which states, if any, are hand-drawn?** The pin is by state, so FRAME §8
      A12 (decision grain) is live; the `--fix` cost shows as the other districts' uniform
      shortfall in `sweep.csv` (`vs_target` is against `total / k` on purpose).
- [ ] **Certificates 1–4 are not adapted to anchored draws** — certificate 4 needs the locked
      zips excluded from the free-cell check (`centers.py` module docstring, "Anchored districts").
- [ ] Review and merge `stage1-scenarios` into `national-channel`; push.
- [ ] `us_maps.py`'s 12-colour palette repeats hues at k ≥ 13 (SOUTHWEST and D07 at k=13).
- [ ] **★6** — answered in practice on this branch (the user asked for real-instance runs);
      whether framework *units* may read `instance_descaled.json.gz` is still formally open,
      and **U7-meas** stays unlaunched behind it.
- [ ] **★3 — should roster stability be a sixth acceptance criterion?** `BRIEF.md` §5 said to ask
      after U2-stab reports; it has (question is live, non-vacuous, decidable in 169 comparisons).
- [ ] Launch the rest of wave 1 — **U0-lit**, **U1-cert**, **U3-inv**; independent, no instance
      needed. U0-lit gates wave 2 (U4-disp, U5-crit, U6-sel).
- [ ] **Sponsor questions, one sentence each** (FRAME §8): A1 ($1B target or constraint), A2 (are
      the 98 released), A6 (any operational coverage rule), **A11** (home-office / national-accounts
      share of `M` — changes `k`), **A12** (what grain the signed territory is described in),
      **A13** (any team-staffed territory — changes the matching's shape).
- [ ] **FRAME §10 Q8** is the cheapest new experiment: premium-max *balanced* draw at fixed roster
      = `centers.py`'s transportation LP with cost `−u_i(z)`; `assign(targets=)` now exists, the
      cost-matrix change is what is left.
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
