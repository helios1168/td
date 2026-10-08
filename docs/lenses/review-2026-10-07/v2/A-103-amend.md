## Amendment v2 (owner, 2026-10-07): part A of the fewest-splits pipeline

This amendment **supersedes** the original B2 Goal, Files and Acceptance above. The original
context and the certificate protocol still apply where they are restated here.

## Goal
The master minimises split states under rule C with a certificate, and serves plans and re-plans
to #130 through contract v2.

## Plan
0. **Band around the target, in dollars** (owner 2026-10-07, D3: every district within ±15% of
   its channel's $ target; D2: plan at ±15%). Add a spec switch: masses are dollars (cells weighted
   by `score.py`'s rates), and the band is target·[0.85, 1.15] instead of τ_c·[1 ± δ]. WIFI keeps
   τ_c, since it has no target. K is then feasible only where total/K can sit in the band; the
   grid reports which K are.
1. **Rule C as a row, switch `one_split_per_district`.** Every state stays a candidate. For every
   support with |S| ≥ 2:

   Σ_{v∈S} s_v + |S|·n_S ≤ |S| + 1

   A used multi-unit support then holds at most one state that actually splits. A state with
   s_v = 0 has one holder by coverage. Do not filter the family by free lists. This is not the
   banned pair row s_v ≥ n_S + n_T − 1.
2. **First deliverable, in the first hour:** the pass-1 grid with the switch on, posted on #103
   and #130.
   - IFA at every K from 46 to 55;
   - FI 20, national 15 and WH 11;
   - each at the target band ±15% (the plan band) and, for information, ±10% and ±20%, giving
     (channel, K, band) → s*, infeasible or unknown.

   The ±20% column is information only (owner 2026-10-07); a band other than the scenario's is
   never adopted here (OD1). IFA plans at the smallest K ≥ 50 (inside 46–55) that the grid shows feasible at ±15% (owner 2026-10-07, D1: "IFA at K ≥ 50 under rule C"). The grid still reports K 46–49: under a target band the CT bound no longer depends on K and is marginal (about 1,328 needed of CT's 1,334 m_rel), so the owner may revisit D1.
3. **Lexicographic passes,** all at gap 0 (`mip_rel_gap = mip_abs_gap = 0`):
   1. minimise Σ s_v;
   2. pin Σ s_v = s* (the count, not the set) and minimise cuts, Σ_v (r_v − 1);
   3. pin both and minimise diameter.
4. **Certificate,** as in B2: μ ≡ 0, both gaps 0, and a fresh master with Σ s ≤ s* − 1 proved
   infeasible.
   - A timeout is unknown.
   - Report s_incumbent, s_lower, lower_status and the domain "over C-rule supports at the target band".
   - Never write "minimal" or "must split" (A3).
   - With rule C off, report the bound s* only, for comparison, and no plan.
5. **Contract v2:** `plan.json` and the pool (same splits and cuts, at most 5, ordered by
   diameter), plus `tools/expb2/plan.py` with `--cuts`.
   - `holder_nogood` must be encoded exactly; `support_ban` sets n_S = 0.
   - **The first commit is the stub CLI** (`"stub": true`), so #130 can build against it.
6. **docs/MODEL.md §4.12:**
   - prove that s_v counts split states exactly under rule C (integer n, η > 0, coverage, caps);
   - prove that the holder_nogood encoding excludes exactly one multiplicity vector.

   The Sol reviewer verifies it and tags it [proved] or [claimed].

Lane: `worker-advised` on `claude-bridge/claude-sonnet-5-5:high`. The Sol advisor uses Anthropic's
advisor timing. Sol reviews and verifies.

## Files
- `tools/expb2/`
- `scenarios/experiments/`
- `tests/test_expb2_split.py`
- `docs/MODEL.md` (§4.12 only)
- `docs/RESULTS.md` (its own #103 section only)
- `docs/CODE_MAP.md` (its own rows only)

## Acceptance
- `python3 tests/run_all.py` passes, including `tests/test_expb2_split.py`, whose toys cover:
  - rule C changing s*;
  - a support with several candidate states of which only one splits;
  - a holder_nogood excluding exactly its vector, while a changed multiplicity and an added
    holder stay feasible;
  - cuts minimised over two split sets of equal size;
  - a timeout reported as unknown.
- The grid comment (Plan 2) is on #103 and #130, with root gap, node counts and pass times per
  channel (U53).
- An FI 20 `plan.json` and pool validate against contract v2, and `plan.py` re-plans FI with a
  sample cuts.json.
- §4.12 is tagged by the Sol verifier.
- An F6 cross-check where the cutoff layer is small; optional.

## Read first
- `docs/problem/SPLITS.md`
- `docs/MODEL.md`
- `td/master.py`
- `docs/memory/facts/highs-traps.md`
- `docs/memory/facts/scenario-sweeps-2026-10.md`
- `docs/lenses/COUNCIL_2026-10-05.md`

## Blocked by
None.
