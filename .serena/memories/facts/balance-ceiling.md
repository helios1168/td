# The valid upper bound on stage 1: the Jensen ceiling

- The valid upper bound is the Jensen ceiling `cert_draw.cert_balance_ceiling` =
  **110.883247** (v2 whole instance, k = 18).
- The contiguity-dropped local search is **not** a bound. It returns a feasible relaxed value
  below the relaxed optimum, which orders it against the contiguous optimum not at all. It is
  now named `free_search` and reported as a reference: **110.812355**, +0.022823 over the draw.
- The prototype quoted it as "the margin above the draw", understating the true 0.0937 gap by
  about fourfold.

General rule and its history: `mem:model/corrections`. Atom-route numbers on the same ceiling:
`mem:facts/state-atoms-retired`.

Source: `main:STATE.md` `## Facts` (a3924e8); host memory td-contiguity-programme (`ff63511`).
