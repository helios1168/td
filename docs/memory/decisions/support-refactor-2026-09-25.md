# The support-master refactor: owner decisions of 2026-09-25

**Status:** the owner's choices in m5 sessions 01a0d8f6 and 01a0d98f, 2026-09-25. The plan that carries them, revision 6, is td#52 (`type:decide`, `owner-decision`), filed verbatim at 41,403 characters; it is accepted by the owner's review comment plus all 21 of its §7 issues filed across milestones M0 to M5, and it authorises no deletion itself (A1 and A2 gate that). td#52 was still open on 2026-09-26. Codes such as OD1, C4 and S25 refer to that plan. The pipeline as it stood: `mem:facts/support-pipeline`.

**Context.** td had grown a Nash staffing track, an app and legacy docs around the support master, and its 36-scenario catalog can't be reproduced (`mem:facts/support-pipeline`). The master MILP is about 100 lines inside a 38-file import closure.

**Decision.**
- **Scope.** td is cut down to the support master, the ZIP realizer and channel routing. Nash staffing, the app and the legacy docs are archived in the git tag `archive/pre-support-2026-09`.
- **Clean slate.** The old support pipeline is deleted in M0 and ported from the tag. The realizer is minimal, about 300 lines. The code becomes a flat package of about 9 modules with a `python -m td` command line, channels as TOML files and an optional `hooks.py`.
- **Baselines.** First the 36-scenario catalog was to be frozen as the regression baseline. Once it proved irreproducible, the new pipeline is accepted on an audit scorecard instead, no baselines live on `main`, and the catalog is scored once from the tag.
- **"State-clipped"** means one whole/splittable flag per planning unit and channel in a single master: all-whole gives the clipped map, all-splittable the ZIP-border optimum.
- **Unit modes** are whole, clipped and free, plus optional pre-drawn pieces. When clipped mode is infeasible, the answer is the smallest feasible δ. Channel domains partition the (unit, fine channel) cells, and fallback opportunity is planned inside the bands.
- **Geography.** Pieces are built from counties; metros stay whole (in clipped mode a metro wins over a state line, logged as an exception); caps are rurality-aware. All three are optional per scenario. A district is named after its largest metro. The public ZCTA reference table is committed with a manifest.
  - Correction, 2026-09-28 (OD5, td#60): only a metro with M^c ≤ U_c in a channel stays whole. An oversized metro, including one that crosses a state line, keeps its own unit and is split under the channel's clipped or free mode. See `decisions/open-decisions-2026-09-28`.
- **Every Census and geography input is 2025 vintage.** ACS, RUCA and the 2020 relationship files are dropped; rurality comes from 2025 urban areas; HUD is pinned to 2025 Q4; the test fixture uses `co-est2025` county populations. Which files exist: `kb/census-geography.md` in sv-ntlee.
  - Correction, same day: the earlier geography decision had the owner sign up for a Census API key as well as a HUD token, kept in `user/.zshenv`; with 2025-only inputs the Census key is not needed.
- **Contiguity wins within the declared final tolerance:** repair may reconnect a piece only if both districts stay within OD1's tolerance. C4 builds border-aware centres and labels each piece's cause. Porting `contiguous_cut` waits for a trigger of more than 2 pieces per map in free mode.
- **Ownership.** Ownership is per channel layer (S25). A share exists only as a set of ZIPs, and the ledger is the only ownership record (S26). Drawability is settled in the master through a corridor floor, a border cap, a count cap and a per-support rounding margin (S27). A remaining draw failure stops the run and names the unit and district (S28).
- **Realizer rounding.** The realizer rounds along the transport LP's forest of split ZIPs (Claim 3), not by argmax. The margin μ_S of a support is the sum, over its splittable units, of each unit's heaviest ZIP. Metro binding is dropped from the realizer, because whole metros are their own units (plan revision 5). Background: `kb/assignment-lp-rounding.md` in sv-ntlee.

**Alternatives rejected.**
- Rounding each ZIP to its largest share (`td/solvers/centers.py:244`): it bounds nothing about a district's mass error.
- Keeping the catalog as a regression baseline: no Studio holds the inputs to rerun it.
- Porting `contiguous_cut` now: deferred until free mode shows more than 2 pieces per map.

**Consequences.** The legacy modules can't simply be dropped from the current tree, since the support master imports their helpers (`mem:facts/support-pipeline`); the clean slate ports from the tag instead. The 2020 gazetteer pin for the committed-map smoke test (`mem:geo/zcta-geometry`) does not carry into the new pipeline. The exporter needs v3 before a fresh extract with new channels (`mem:facts/support-pipeline`). td's papers migrate only as the support model cites them (`mem:refs/literature`).

## Carrying out the clean slate: td#54, 2026-09-28

**Status:** three choices made while executing td#54 (A2, the M0 clean slate) on m2-studio, 2026-09-28, m2 session 01a0e728 fork 01a0e738 ([handoff comment](https://github.com/helios1168/td/issues/54#issuecomment-5866766796)). They landed in `ce9f282` and were merged in `a7335d5`. The owner approved the first; the other two were judgement calls made without asking.

**Context.** The clean slate deleted the legacy code, including `td/instance.py` and its tests, and reset the core docs. `tests/test_docs_owners.py` had required a `STATE.md` holding only `## Now` (`mem:workflow/docs-and-state`), but the global `/land` skill writes Now, Next and Blocked.

**Decision.**
- `tests/test_docs_owners.py` accepts the global land skill's `STATE.md` shape: `## Now` first, then optionally `## Next` and `## Blocked` in that order, with the whole file at most 1 KB. The owner approved this.
- The v2 loader round-trip test is removed, not stubbed, because `td/instance.py` is deleted. A loader comes back in C1 (#66, "Implement data.py and the sparse fixture").
- `requirements.txt` keeps exact pins at the versions installed in the hub `.venv` on 2026-09-28 (for example scipy 1.18.1, highspy 1.15.1), without the old frozen-pin rule. Its header says to bump versions deliberately.

**Alternatives rejected.**
- Keeping the `## Now`-only check: it would fail after every lander rewrite of `STATE.md`.
- Stubbing the loader test: there is no loader left to test until #66.
- Unpinned requirements: a `.venv` rebuild would not be reproducible.

**Consequences.** `STATE.md` may carry Next and Blocked under the 1 KB cap. The repo has no instance-loader test until #66 lands. A version change goes through an explicit `requirements.txt` edit.
