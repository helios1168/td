# Optimization FOUNDATIONS entries that carried weight on td

From `~/resources/optimization/FOUNDATIONS.md`, as used by the 2026-09-03 optimization plan:

- **BoydVandenberghe2004** and **Rockafellar1970**: the perturbation function of `EG^bal(δ)` is
  concave and the multiplier is a supergradient, which is what lets one solve bound the whole
  frontier.
- **KuhnTucker1951**: agent-specific effective prices `q_zi = p_z + ν_i M_z`.
- **WesterlundPettersson1995** and **DuranGrossmann1986**: LP outer approximation; every master
  optimum is a valid upper bound, which is the whole architecture given no conic solver.
  DuranGrossmann1986's finite-convergence result is about convex MINLP and does not transfer to
  the continuous EG^bal loop (`mem:model/u9-bandthm`).
- **VigerskeGleixner2018**: the SCIP cross-check.
- **Chvatal1983**: RHS ranging, warm starts, and the assignment stability radius for the tie
  question.
- **Danna2005**: RINS as the band-aware rounding repair.
- **CodatoFischetti2006**: no-good cuts to enumerate near-optimal rosters.
- **Boland2015**: the ε-constraint frontier, rejected for the wrong coordinate.
- Dormant and staying dormant: all of FOUNDATIONS §8 (contiguity).

Other citation facts: `brieden2017 Lem. 4` supports the `≤ k-1` split bound as cited in
`LENS_GROTHENDIECK.md` §2 (`mem:model/u1-cert-eg-dual`); the k-means SDP ladder
(`iguchi2017`, `piccialli2022`, `croella2026`) is the proposed stage-1 certificate route (open
question C7).

Related: `mem:domain/optimization-verdicts`, `mem:refs/econ-theory-matching`.

Source: `.claude/agent-memory/domain-lens/domain-optimization-td-a1.md`;
`git show a16c304:PLAN.md` `## Decisions needed`.
