# Three corrections that must not be repeated

**1. ρ > 0 does not break scale invariance** (`ecbbf84`). Rescaling shifts `Σ log g_i` by
`n·log κ`, the same constant for every partition, so the argmax is unchanged at every ρ ≥ 0.
This is also what justifies the descaled export (`mem:workflow/confidential-data`). Separately,
ρ does not enter stage 2 at all (`mem:model/u2-stab`).

**2. A local search over a relaxation is not an upper bound** (2026-09-06, `ff63511`). The
state-atom prototype reported its contiguity-dropped search as a bound on the contiguous draw.
The search returns a feasible relaxed value at or below the relaxed optimum; the contiguous
optimum is also at or below that optimum; nothing orders the two. Measured, the wrong quantity
understated the gap fourfold (`mem:facts/balance-ceiling`). Rule: a bound comes from a
relaxation solved to optimality or from an analytic argument, never from a heuristic run on a
relaxed problem. The tell was in the prototype's own docstring, which recorded the "bound"
being beaten by a feasible solution.

**3. "Zero by construction" names a relation, not a property** (2026-09-06, `1f6d956`). The
power-cell snapped labelling has zero zips outside their own cell with respect to the diagram
that produced it. Rebuild the diagram from the snapped labels and 16 of 3,704 fall outside
again. The user caught this in a published figure: every power-diagram rendering recomputes
centroids from the draw it is handed, so it shows the next iterate's mismatch. Rules: quote such
a guarantee with the object it is relative to; when a figure is the evidence for a claim, check
the figure is drawn from the labelling the claim is about (`mem:facts/map-contiguity`).

Also from 2026-09-07: a figure must be drawn from the dataset the claim is about, never
re-joined from several sources at render time, and every figure is looked at before it is
published (`mem:decisions/stage1-route`).

Source: host memory td-contiguity-programme (2026-09-10).
