# Handoff — national channel territory design / framework 0.1 dry run (`wt/workflow-dryrun`)

**Updated:** 2026-09-02 · **Branch:** `wt/workflow-dryrun` · **Head:** `ab15133`

## Start here
- **Resume point:** `docs/FRAME.md` §0 — supersedes `docs/CHANNEL.md` §6–7; `CHANNEL.md` §0
  holds a pointer plus the pre-dry-run narrative.
- **Status header:** `CLAUDE.md`
- **Memory:** `~/.claude/projects/-Users-ntlee-projects-td/memory/td-contiguity-programme.md`
- **Key docs:** `docs/BRIEF.md` (the plan, units, ★ decisions) · `docs/units/*.md` (8 briefs) ·
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
- [ ] **★7** — run `/domain econometrics`? Only route to U5/A4 (regional bias in `M`) and U6
      (the tier-2 noise floor); neither has a domain file or a seeded `FOUNDATIONS.md`.
- [ ] Two doc fixes from `VERIFY_U2-stab.md`: `MODEL_U2-stab.md` §4 row 6's counts
      (2,187 / 3,672) are tie-break dependent and unlabelled; P2.2's raw threshold of 5 holds
      only under the distinctness hypothesis (4 suffices without it).
- [ ] Carried from `docs/REVIEW_GROMOV.md`, untouched by this branch: **R1** (`ceiling.py`'s
      `SATURATION = 0.05`, channel_note §5.1, FINDINGS §4C/C6's stale "α ≈ 0.9"), then C4 →
      stage-2 rescore of the cells → the cells-vs-dots call; the EG bound as certificate 5;
      R4's seven note fixes. `BRIEF.md` §6 adds a free rename pass: *certified* → *balance-certified*.
- [ ] Open from before, unchanged: the `docs/MODEL.md` §6 list, and book-aware stage 1 vs
      `RESEARCH_FINDINGS` §9-G's books-at-stage-2-only invariant.
