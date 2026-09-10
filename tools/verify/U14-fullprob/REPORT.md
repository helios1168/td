# U14-fullprob: decomposition proposition, math-verify report

Date 2026-09-10. Artifact `verify_decomposition.py` in this directory. Re-run from the worktree root:

    /Users/ntlee/projects/td/.venv/bin/python3 tools/verify/U14-fullprob/verify_decomposition.py

Environment printed by the script: python 3.13.15, numpy 2.5.2, scipy 1.18.1, sympy 1.14.0,
networkx 3.6.1, seed 20260910, tolerance 1e-12 inside `CERT_TOL = 1e-8`. 60 checks, 0 failures.

```
CLAIM:    U14-fullprob decomposition proposition, docs/FULL_PROBLEM.md §4 (PLAN.md:210-219).
          Code under test: td/model.py:124-162, td/channel.py:252-312, tools/staff.py:114-131.
          Structure cited: docs/MODEL.md:375-406 (Lemma 6), docs/MODEL.md:446-450.
MODE:     both (sympy identity plus numeric cross-check against independent oracles)
VERDICT:  (a) VERIFIED  (b) VERIFIED  (c) VERIFIED  (d) VERIFIED
```

| clause | basis |
|---|---|
| (a) u additive over cells | sympy identity closes with `c_free` symbolic, then each of the three `filler_capture` values; `channel.gain_matrix` on a cell-level graph equals the sum of per-bundle projected gain matrices to 2.9e-16 relative over 12 parameter settings |
| (b) stage 1 separates by bundle at fixed π and k_B | brute-force enumeration with the cover row re-imposed at cell level: joint max equals the sum of per-bundle maxima, argmax is the tuple of argmaxima |
| (c) injectivity is the only coupling | `channel.match` equals the exhaustive max over injections on 200 random instances and on a stacked two-bundle matrix; per-bundle matchings reuse a rep, so the coupling is real |
| (d) per-channel floors break Lemma 6 | exact sympy solve: the feasible set is the single point y = 1/2, both zips split against k − 1 = 1, four positive entries against n + k − 1 = 3, no integral point; `linprog` agrees |

Hypotheses shown load bearing by attack: one coefficient vector per bundle (per-channel λ leaves a
residual); k_B fixed (with only Σ k_B fixed the split (3,1) beats (2,2) by 0.17 nats, which is
what level 0 decides); bundles inside π(z) disjoint (a shared fine label empties the joint
feasible set; the level-0 cover row is that condition); the catch-all pass is sequential, since
tied optima of a WH pass leave residuals of different value.

Requirements for wave 2:

1. One global `reps_order` on every `gain_matrix` call; the default is the projection's own rep
   list, so per-bundle blocks would not stack.
2. `channel.match` cannot express a forbidden pair (raises on g ≤ 0). Any candidacy restriction
   goes through the penalty assignment of `tools/staff.py`; a held rep is a row removal.

Caveats: (c) is for unrestricted staffing; positivity of g is checked on constructed instances
only; reps < districts leaves districts unstaffed (★C); the artifact carries its own projection,
so code-verify should swap in `td.channels.project` for the (a) block; instances are small enough
to enumerate, nothing runs on the live instance.
