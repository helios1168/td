# Unit U13-base — the hand-drawn state-grouped baseline (A3) as a point on the `(δ, V)` plane

`APPROACHES` §A3 (its construction, taken verbatim); `LENS_GROMOV` M11.3 and ledger U10;
`DOMAIN_optimization` §5 row 6; FRAME §3's "the headline claim is unevidenced without it".
Construction is independent; placing the point on the frontier needs U8-band.

## Spec (verbatim from `docs/APPROACHES.md` §A3 and `docs/LENS_GROMOV.md` M11.3)

> **The map** at state grain: contiguous groups of states accumulated to ≈ 1/13 of `M`, by a
> stated greedy rule (largest remaining neighbour first) so the construction is reproducible
> rather than literally by hand. States above the band must be split; the rule for splitting
> (by metro or by zip3) is part of the charter and must be written down.
> **The roster**: for each bucket, the wholesaler with the largest book inside it; conflicts
> (one wholesaler top in two buckets) resolved by the larger share.
> **Swap which side is extremal.** Fix `V ≥ V(delivered)` and minimise the spread. That is the
> other axis of the same frontier, and it is what A3's hand-drawn baseline should be scored on
> (U10): not "does it beat the draw on `V`" but "where does it sit on the curve".

## Files owned

`tools/baseline/state_grouped.py` · `tests/test_state_grouped.py` · `docs/MODEL_U13-base.md`
(the construction rule written down *before* the code, including the split rule for TX at 11.5%
of `M` — zip3 is the only grain the instance carries) · `docs/CODEVERIFY_U13-base.md` ·
`battery/results/u13_base_<date>/` · `figures/u13_base/` (the baseline map, tracked).

## Files forbidden

Every other unit's owned files · `docs/FRAME.md` · `docs/BRIEF.md` · `docs/APPROACHES.md` ·
`docs/LENS_*.md` · `docs/DOMAIN_*.md` · `docs/LIT_*` · `CLAUDE.md` · existing `td/` modules
(`channel.stage2`, `channel.balance_report`, `tools/measure/premium.measure` by import only) ·
`battery/figures/`.

## Agent → verifier

`python-typed` → `code-verify` (launch from a session started in `.claude/worktrees/A1`).

## Acceptance

1. The greedy rule and the split rule stated in `MODEL_U13-base.md` such that a second
   implementation would produce the same buckets; state adjacency from the gazetteer
   (`td/geo.py`) or a written adjacency table under the artifacts.
2. The baseline's `to_district`, its roster by the top-book rule with the conflict rule, and the
   scores: `M`-spread and max deviation `δ_base`, `V` via `channel.stage2` **and** `V` at the
   top-book roster (they differ; report both), `P` via `tools/measure/premium.measure`, the
   realised-gain spread `D(g)`.
3. The comparison the lens asks for: the point `(δ_base, V_base)` against the delivered
   `(0.0039, 59.9375)` and, when U8 exists, against `EG^bal_{S₁₃}(δ_base)` — i.e. how far below
   the frontier the baseline sits at its own band.
4. A0's kill verdict line, filled in: does A3 tie or beat the committed draw on `V` within 5e-3
   nats? (APPROACHES §A0 "Kill experiment".)
5. Tests on a synthetic 6-state / 20-zip instance where the greedy buckets are computed by hand;
   existing tests green; provenance and byte-identity as U7-meas.

## Numbers to compute first

`δ_base` (expected to fail the ±10% band at state grain — FRAME §6: TX 11.5% vs 7.7% target —
which is why the split rule must be written) · `V_base` at both rosters · `P_base` share ·
`D(g)_base`.

## Inputs to read (paths and sections only)

`docs/APPROACHES.md` §A3, §A0 "Kill experiment" · `docs/LENS_GROMOV.md` M11.3, ledger U10 ·
`docs/FRAME.md` §3, §6 (footprint concentration row) · `docs/MODEL_U7-meas.md` §1, §5 ·
`td/channel.py::place_by_state`, `stage2`, `balance_report` · `td/geo.py` · `td/instance.py`
(the `state` node attribute) · `tools/measure/premium.py`.

## Open questions for ★0

None; A3's charter says the split rule is the track's to write down, and this unit writes it.

## Branch

`wt/A1` (or `wt/U13-base` from `wt/A1`)

## Stop rule

If no split rule at zip3 grain lands every bucket inside ±10%, report the best achievable band
and the offending states; do not move individual zips to force it — that would make it A0.

**stop and report rather than improvise**
