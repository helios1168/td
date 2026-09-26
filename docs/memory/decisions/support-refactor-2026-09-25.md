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
