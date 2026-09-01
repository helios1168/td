# Data route — the descaled real instance

**Opened:** 2026-08-31 · **Split out of `NWAY.md` on 2026-08-31.** Companion files: `CHANNEL.md` (the problem), `MODEL.md` (the model), `DATA.md` (the export route).


**The synthetic twin is superseded for this problem.** With PII and firm masked upstream, and
the dollar scale removed, the *real* instance can be exported: real ZCTAs, real adjacency,
real territory structure, real share patterns. That is strictly better than a twin calibrated
to aggregates, and it skips the rank-jitter and fidelity-audit apparatus entirely.

The justification is algebraic, not statistical. `u_i(z) = M_z · [c1·s_i + c2·(t_z − s_i) + λ]`
with `s_i = S_i/M_z`, so `M_z` factors out; and `Σ_i log g_i` shifts by `n·log κ` under a
global rescale. At ρ = 0 the descaled instance and the real one have the **same** optimal
allocation, gaps and certificates. Removing the scale drops a constant the solver never reads.

- `tools/instance_export/export_instance.py` — work-machine exporter, single file, auditable.
  Emits shares in [0,1] plus `m_rel = M/median(M)`; surrogate rep ids; guards that refuse to
  write a currency amount or the divisor.
- `td/instance.py` — repo-side loader; `S_i = share_i · m_rel` reconstructs the
  instance to within the exporter's 6-sig-fig rounding.

Two consequences to carry forward:

1. **Correction, 2026-08-31: ρ > 0 *is* scale-invariant too.** An earlier version of this
   file claimed `Σ log g_i − ρ·perimeter` broke the invariance by mixing a log-scale term with
   a raw count. **It does not.** Rescaling shifts the log sum by `n·log κ` — the same constant
   for every partition — and the perimeter is combinatorial, so every objective *difference* is
   untouched and the argmax is unchanged at **every ρ ≥ 0**. ρ transports across the descaling
   unchanged, and this strengthens the descaled-export justification rather than qualifying it.
   The genuinely scale-dependent object is the *other* districting entry point,
   `solve_contiguous` (KS gap in raw gain units plus ρ·perimeter), which is not carried into
   this worktree. What descaling does change is **conditioning**: solver feasibility tolerances
   are absolute in gain units, so descaled values are better conditioned, while certificate
   tolerances are in nats and scale-free either way.
2. **Tail fits move to share space.** The dPlN/lognormal calibration and `S7_heavytail` were
   fitted to sales *values*; shares are bounded in [0,1] with different tail behaviour. The
   generator's tail knobs need recalibrating, not re-pointing.

`cand(z) = {i : S_i(z) > 0}` — a rep is a candidate only where it has sales (settled
2026-08-31). This makes `cand` derivable from the sales table alone, with no coverage source.

### Vacancies: the filler key (2026-08-31)

Some territories have no official rep and their sales are booked under a **filler key** — a
rep-shaped sentinel that is not a person. It carries real sales, real opportunity and a real
firm. It must **never** become a candidate: an objective term for a vacancy has the solver
bargaining on behalf of an empty chair, and `Σ log g_i` would trade real reps' welfare away
to feed it.

The schema already separates the two roles, which is what makes this cheap: `utilities`
computes `T_z` from *all* books but loops over `cand` only. So filler book arrives as a
separate node attribute `S_free`, is excluded from `cand`, and every candidate capitalises it:

```
u_i(z) = c1·S_i + c2·(T_z − S_i) + c_free·S_free + λ·M_z
```

That gives **four** node classes:

| class | `cand` | book | meaning |
|---|---|---|---|
| contested | ≥ 2 | real | the decision problem |
| uncontested | 1 | real | owner forced, no binary |
| **vacant** | 0 | filler only | real book, no incumbent — nobody can claim it by legacy |
| untapped | 0 | none | opportunity with no book at all |

Vacant zips are commercially the most interesting: they are genuinely up for grabs, with no
legacy claim on either side. They are also, under the candidacy rule, ownable by nobody — so
they need an allocation rule, same as untapped. See §6.6.
