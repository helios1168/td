---
name: u1-cert-eg-dual
description: Findings and traps from unit U1-cert (Eisenberg-Gale dual vs the four certificates) on the national-channel territory project, 2026-09-03
metadata:
  type: project
---

Unit U1-cert (2026-09-03, worktree `.claude/worktrees/A1`) produced results later units should
not re-derive, and hit three traps.

**Why:** two of these contradict a lens/domain premise; the numbers are expensive to re-earn.
**How to apply:** check these before restating the EG/certificate story or the `k-1` claim.

1. **The four certificates do NOT all collapse — three of four do.**
   `cert_integer_balance_floor`'s LP relaxation has optimum `t = 0` (split every zip
   fractionally), so it carries no dual at all; it is the *primal/achievability* half of the
   same sandwich, not a degeneration of the EG dual. The honest organisation is "one duality
   gap with two sides", not "five certificates" and not "one".
2. **RETRACTED 2026-09-03 by `docs/VERIFY_U1-cert.md` §5 — do not repeat.** I claimed the
   lens's `[standard] <= |S| - 1` split-unit bound was a tau = 0 privilege and that the honest
   heterogeneous bound is `<= k`. **False.** `<= k - 1` holds heterogeneously: a vertex of the
   optimal face is a Fisher equilibrium, so it lies in the MBB-restricted face `P'` whose supply
   and budget rows are linearly dependent (`sum_z p_z*supply_z - sum_i budget_i = k - sum_z p_z
   = 0`), giving rank `<= n+k-1`. `brieden2017 Lem. 4` as cited in `LENS_GROTHENDIECK.md` §2
   needs no replacement.
   **The trap, generalised:** I took the *obvious* description of the optimal face
   (`sum_i x_zi = 1`, `sum_z u_iz x_zi = g*_i`) and computed its rank. That description is not
   minimal. Before quoting "rank => split count", ask whether an equilibrium/KKT restriction
   cuts the face further. The rank-`n+k` result about that matrix is true but non-minimal, and
   it also needed an unstated `u_i != 0` hypothesis for its "iff".
3. **The `<= k-1` *count* is worthless without the split masses on this instance.** Top-12 zip
   mass `249.39` vs EG `g_min = 103.62`, ratio `2.41`, so the a-priori value bound is `+inf`.
   Realised `M(F) = 66.17` (10 splits) gives `1.018` nats; per-agent `0.245`; actual gap
   `5.1e-4`.
4. **Headline numbers (real instance, delivered k=13 seed-3 draw, theta=0.40 lam=0.30):**
   `EG_{S13} = 60.697416` certified to `1.3e-13` by its own Lagrangian dual;
   `V(delivered) = 59.937470` (bracket 7.1e-15 by fsum on a good iterate; the width is a
   property of the iterate, not the instance); gap **`0.760` nats** vs the analytic ceiling's `9.649`
   (12.70x tighter). Realised `g`-spread `60.65%` vs published `M`-spread `0.781%` (77.6x).
   The EG optimum's map has a **54.2% M-spread** — the 0.76 nats is bought by abandoning
   balance, so quote it with the spread beside it.
5. **`u_i(z) <= M_z` (headroom) holds only under `filler_capture="theta"`** (max ratio
   `1.00000042`, the 6-sig-fig export rounding). At `"full"` — `MODEL.md` §6.7's own
   recommendation — it is `1.2949`. The correction to the ceiling is `sum_{i in S} log nu_i`
   = **`+0.2584` nats** at S13 (and the same maximised over all staff sets), *not* the
   `k*log(nu_max) = 3.360` I first quoted. **Trap:** when a bound reads `sum_i log nu_i`, do not
   report `k*log(max_i nu_i)` and call it the correction — here that is 13x loose and it turned
   a 0.26-nat footnote into a false "same order as the 3.7-nat premium" claim.

**Traps.**
- Do not name a scratch script `numbers.py`: it shadows stdlib `numbers` and numpy's import
  dies with a confusing circular-import AttributeError.
- `centers.power_weights`'s `beta`/`weights_raw` equals `dF/dm_j` and IS the EG multiplier only
  when the transportation LP is **nondegenerate** (support `= n + k - 1`). A balance-tight LP is
  degenerate by construction, so on the real instance HiGHS's beta should not be read as "the EG
  prices". The bound is unaffected; the interpretation is. `omega_j = 1/(rho m*_j)` is always a
  dual optimum.
- **Split sets are vertex-dependent, not instance invariants.** Two solves at the same `g*`
  return different `F` of the same size (`M(F)` 66.17 vs 87.66; realised gap 5.1e-4 vs 1.9e-3).
  Quote `|F| <= k-1`, `M(F) < g_min`, and the *direction* of the bound chain — never a bare
  `M(F) = 66.168`.
- Two `u` conventions coexist: `model.utilities` masks non-candidates to 0, `channel.gain_matrix`
  does not. Everything comparing against `stage2` must use the unmasked one.

Reusable: `docs/artifacts/U1-cert/eg.py` — proportional response + the Lagrangian dual
`D(p) = sum p_z - k + sum_i log max_z(u_iz/p_z)`, which bounds EG for **any** `p > 0`, so the
reported number never trusts the solver. 60k iterations close 1229x13 to 1e-13 in ~1 s.
See [[u2-stab-traps]].
