# Unit U13-base — the hand-drawn state-grouped baseline (A3) as a point on the `(δ, V)` plane

Status: open

`APPROACHES` §A3 (its construction, taken verbatim); `LENS_GROMOV` M11.3 and ledger U10;
`DOMAIN_optimization` §5 row 6; FRAME §3's "the headline claim is unevidenced without it".
Construction is independent; placing the point on the frontier needs U8-band.

## Spec (verbatim from `docs/foundations/APPROACHES.md` §A3 and `docs/foundations/LENS_GROMOV.md` M11.3)

> **The map** at state grain: contiguous groups of states accumulated to ≈ 1/18 of `M`, by a
> stated greedy rule (largest remaining neighbour first) so the construction is reproducible
> rather than literally by hand. States above the band must be split; the rule for splitting
> (by metro or by zip3) is part of the charter and must be written down.
> **The roster**: for each bucket, the wholesaler with the largest book inside it; conflicts
> (one wholesaler top in two buckets) resolved by the larger share.
> **Swap which side is extremal.** Fix `V ≥ V(delivered)` and minimise the spread. That is the
> other axis of the same frontier, and it is what A3's hand-drawn baseline should be scored on
> (U10): not "does it beat the draw on `V`" but "where does it sit on the curve".

## Files owned

`tools/baseline/state_grouped.py` · `tests/test_state_grouped.py` · this file's `## Model`
(the construction rule written down *before* the code, including the split rule for TX — v1
measured TX at 11.5% of `M` on the 1,229-zip instance; that number must be **re-measured on the
live 3,748-zip instance**, do not assume it carries over — zip3 is the only grain the instance
carries) · `## Code verify` · `battery/results/u13_base_<date>/` ·
`figures/u13_base/` (the baseline map, tracked).

## Files forbidden

Every other unit's owned files · `docs/foundations/FRAME.md` · `docs/foundations/BRIEF.md` · `docs/foundations/APPROACHES.md` ·
`docs/foundations/LENS_*.md` · `docs/foundations/DOMAIN_*.md` · `docs/foundations/LIT_*` · `CLAUDE.md` · existing `td/` modules
(`channel.stage2`, `channel.balance_report`, `tools/measure/premium.measure` by import only) ·
`battery/figures/`.

**Tooling.** `cat`/`head`/`tail`/`sed`/`awk`/`grep` on a file are blocked by the
`enforce-file-tools.sh` hook — use `Read`/`Edit` and the Serena symbol tools instead
(`git show ae2b18d:docs/RUNS_PLAN.md:83-89`).

## Agent → verifier

`python-typed` → `code-verify` (launch from a session started on `main`).

## Acceptance

1. The greedy rule and the split rule stated in `MODEL_U13-base.md` such that a second
   implementation would produce the same buckets; the greedy rule's starting seed (which state
   the accumulation begins from) stays **pluggable** — per the A12 decision (2026-09-05), the
   sponsor's hand-drawn-states call is being taken in a separate session and this unit must not
   hard-code its outcome; state adjacency from the gazetteer (`td/geo.py`) or a written adjacency
   table under the artifacts.
2. The baseline's `to_district`, its roster by the top-book rule with the conflict rule, and the
   scores: `M`-spread and max deviation `δ_base`, `V` via `channel.stage2` **and** `V` at the
   top-book roster (they differ; report both), `P` via `tools/measure/premium.measure`, the
   realised-gain spread `D(g)`.
3. The comparison the lens asks for: the point `(δ_base, V_base)` against the delivered
   `(0.009970, 95.755192)` and, when U8 exists, against `EG^bal_{S₁₈}(δ_base)` — i.e. how far
   below the frontier the baseline sits at its own band.
4. A0's kill verdict line, filled in: does A3 tie or beat the committed draw on `V` within 5e-3
   nats? (APPROACHES §A0 "Kill experiment".)
5. Tests on a synthetic 6-state / 20-zip instance where the greedy buckets are computed by hand;
   existing tests green; provenance and byte-identity as U7-meas.

## Numbers to compute first

`δ_base` (expected to fail the ±10% band at state grain — FRAME §6 (v1): TX 11.5% vs a 7.7%
target; on v2 the target tightens to **5.56%** (1/18 of `M`), so the state-grain failure is
**strictly worse** than v1 anticipated. TX's 11.5% was measured on v1's 1,229-zip instance and
must be **re-measured on the live 3,748-zip instance** before it can be quoted on v2 — no v2 TX
number exists yet, do not invent one — which is why the split rule must be written) · `V_base`
at both rosters · `P_base` share · `D(g)_base`.

## Inputs to read (paths and sections only)

`docs/foundations/APPROACHES.md` §A3, §A0 "Kill experiment" · `docs/foundations/LENS_GROMOV.md` M11.3, ledger U10 ·
`docs/foundations/FRAME.md` §3, §6 (footprint concentration row) · `docs/MODEL_U7-meas.md` §1, §5 ·
`td/channel.py::place_by_state`, `stage2`, `balance_report` · `td/geo.py` · `td/instance.py`
(the `state` node attribute) · `tools/measure/premium.py`.

## Open questions for ★0

None; A3's charter says the split rule is the track's to write down, and this unit writes it.

## Branch

`main` (or `wt/U13-base` from `main`)

## Stop rule

If no split rule at zip3 grain lands every bucket inside ±10%, report the best achievable band
and the offending states; do not move individual zips to force it — that would make it A0.

**stop and report rather than improvise**

## Model

none yet

## Verify

none yet

## Code verify

none yet
