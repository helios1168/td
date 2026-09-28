# The support-master refactor: owner decisions of 2026-09-25

**Status:** the owner's choices in m5 sessions 01a0d8f6 and 01a0d98f, 2026-09-25. The plan that carries them, revision 6, is td#52 (`type:decide`, `owner-decision`), filed verbatim at 41,403 characters; it is accepted by the owner's review comment plus all 26 of its §7 issues filed across milestones M0 to M5, and it authorises no deletion itself (A1 and A2 gate that). td#52 was still open on 2026-09-26. Codes such as OD1, C4 and S25 refer to that plan; its decisions are numbered S1–S31 below. The pipeline as it stood: `mem:facts/support-pipeline`.
  - Correction, 2026-09-28 (council C18, td#55): this record first said 21 §7 issues. Revision 7 of td#52 §7 lists 18 work issues plus X2, F1 and OD1–OD6, 26 in all, and all 26 were filed that day (#3 and #53–#77 except #52; [filing comment](https://github.com/helios1168/td/issues/52#issuecomment-5866385436)).

**Context.** td had grown a Nash staffing track, an app and legacy docs around the support master, and its 36-scenario catalog can't be reproduced (`mem:facts/support-pipeline`). The master MILP is about 100 lines inside a 38-file import closure.

**Decision.**
- **Scope** (S1, S5, S6). td is cut down to the support master, the ZIP realizer and channel routing. Nash staffing, the app and the legacy docs are archived in the git tag `archive/pre-support-2026-09`.
- **Clean slate** (S8, S20, S21). The old support pipeline is deleted in M0 and ported from the tag. The realizer is minimal, about 300 lines. The code becomes a flat package of about 9 modules with a `python -m td` command line, channels as TOML files and an optional `hooks.py`.
- **Baselines** (S22). First the 36-scenario catalog was to be frozen as the regression baseline. Once it proved irreproducible, the new pipeline is accepted on an audit scorecard instead, no baselines live on `main`, and the catalog is scored once from the tag.
- **"State-clipped"** (S9) means one whole/splittable flag per planning unit and channel in a single master: all-whole gives the clipped map, all-splittable the ZIP-border optimum.
- **Unit modes** (S9, S10, S11) are whole, clipped and free, plus optional pre-drawn pieces. When clipped mode is infeasible, the answer is the smallest feasible δ. Channel domains partition the (unit, fine channel) cells, and fallback opportunity is planned inside the bands.
- **Geography** (S13–S16). Pieces are built from counties; metros stay whole (in clipped mode a metro wins over a state line, logged as an exception); caps are rurality-aware. All three are optional per scenario. A district is named after its largest metro. The public ZCTA reference table is committed with a manifest.
  - Correction, 2026-09-28 (OD5, td#60): only a metro with M^c ≤ U_c in a channel stays whole. An oversized metro, including one that crosses a state line, keeps its own unit and is split under the channel's clipped or free mode. See `decisions/open-decisions-2026-09-28`.
- **Every Census and geography input is 2025 vintage** (S17–S19). ACS, RUCA and the 2020 relationship files are dropped; rurality comes from 2025 urban areas; HUD is pinned to 2025 Q4; the test fixture uses `co-est2025` county populations. Which files exist: `kb/census-geography.md` in sv-ntlee.
  - Correction, same day: the earlier geography decision had the owner sign up for a Census API key as well as a HUD token, kept in `user/.zshenv`; with 2025-only inputs the Census key is not needed.
- **Contiguity wins within the declared final tolerance** (S23, S24): repair may reconnect a piece only if both districts stay within OD1's tolerance. C4 builds border-aware centres and labels each piece's cause. Porting `contiguous_cut` waits for a trigger of more than 2 pieces per map in free mode.
- **Ownership.** Ownership is per channel layer (S25). A share exists only as a set of ZIPs, and the ledger is the only ownership record (S26). Drawability is settled in the master through a corridor floor, a border cap, a count cap and a per-support rounding margin (S27). A remaining draw failure stops the run and names the unit and district (S28).
- **Realizer rounding** (S27). The realizer rounds along the transport LP's forest of split ZIPs (Claim 3), not by argmax. The margin μ_S of a support is the sum, over its splittable units, of each unit's heaviest ZIP. Metro binding is dropped from the realizer, because whole metros are their own units (plan revision 5). Background: `kb/assignment-lp-rounding.md` in sv-ntlee.

**Alternatives rejected.**
- Rounding each ZIP to its largest share (`td/solvers/centers.py:244`): it bounds nothing about a district's mass error.
- Keeping the catalog as a regression baseline: no Studio holds the inputs to rerun it.
- Porting `contiguous_cut` now: deferred until free mode shows more than 2 pieces per map.

**Consequences.** The legacy modules can't simply be dropped from the current tree, since the support master imports their helpers (`mem:facts/support-pipeline`); the clean slate ports from the tag instead. The 2020 gazetteer pin for the committed-map smoke test (`mem:geo/zcta-geometry`) does not carry into the new pipeline. The exporter needs v3 before a fresh extract with new channels (`mem:facts/support-pipeline`). td's papers migrate only as the support model cites them (`mem:refs/literature`).

## The numbered decisions, S1–S31

**Status:** td#52 revision 7 §2, "Decisions settled with the owner (2026-09-25)", as approved by the owner on 2026-09-28 ([owner answers](https://github.com/helios1168/td/issues/52#issuecomment-5866293503)); numbered here by td#55 (A3). The wording is the table's; the council notes in brackets are revision 7's, shortened, with the owner's answer added to S24 and S27, and S29 drops its pointer to `drafts/literature-handling.md`. S3, S4 and S7 are carried out by td#53 (`mem:facts/refactor-archive-and-queue`, `decisions/issue-queue-reset-2026-09-28`) and the OD issues; S14 is qualified by OD5 (`decisions/open-decisions-2026-09-28`).

- **S1.** The core is master → ZIP realizer → ledger. Nash staffing, the app and the legacy docs are archived. Scenarios are district-only plans until staffing returns.
- **S2.** One new master replaces the three current implementations. It allows repeated supports, with each whole unit owned by one district instance (OPTIONS D1 option 2).
- **S3.** Archiving means tagging `archive/pre-support-2026-09` and then deleting from `main`. The remote-only branches stay as they are.
- **S4.** Legacy issues are closed with the `archived` label; survivors are re-filed; the 4 old milestones are replaced.
- **S5.** The app is archived; rebuilding it goes to the backlog.
- **S6.** The core docs are rewritten and the rest archived. Memory is pruned to what still applies.
- **S7.** D1–D5 from OPTIONS become owner-decision issues. The new code can switch between policies.
- **S8.** Each channel is declarative, with optional code hooks for its own features.
- **S9.** Units are states or pre-drawn pieces. Each unit has a mode per channel: `whole`, `clipped` or `free`.
- **S10.** When clipped mode is infeasible, the run reports the smallest feasible δ, which gives the price of clipping. [Council C4: this δ is a property of the master; it says nothing about whether the plan can be drawn on ZIPs.]
- **S11.** Channel domains partition the (unit, fine channel) cells. Fallback opportunity is assigned before solving, so it counts in bands. There is no routing code after solving.
- **S12.** The work is built on a fresh extract that includes the new channels. The exporter reads its channel list from a file.
- **S13.** Optional geography features: county-built pieces, whole metros and rurality-aware caps. All are off by default.
- **S14.** In clipped mode a metro that crosses a state line stays whole, and each such crossing is logged in the audit.
- **S15.** Districts are named after their largest metro. Maps label principal cities. Exports carry county, CBSA and place columns.
- **S16.** The public ZCTA reference table is committed with a manifest.
- **S17.** All Census and geography inputs are 2025 vintage. ACS, RUCA and the 2020 relationship files are dropped, and no Census API key is used.
- **S18.** ZIPs with no ZCTA are placed with the HUD-USPS crosswalk pinned to 2025 Q4, using a HUD token the owner creates.
- **S19.** Rurality comes from the 2025 urban-area share and the county's metro status. The fixture uses `co-est2025` populations.
- **S20.** Clean slate. The old support pipeline is deleted in M0, and new code ports algorithms by reading them from the tag.
- **S21.** Minimal realizer of about 300 lines, rewritten with the old code only as reference.
- **S22.** No baselines on main. The catalog is scored once from the tag. `RESULTS.md` holds the scorecard and links to the tagged exports.
- **S23.** Contiguity wins within the final tolerance. Repair may move a piece only if both districts stay inside OD1's declared final tolerance. Otherwise the piece stays and is reported with its cause. [Council C16: under the current clipped model the target must also be admissible in the piece's unit.]
- **S24.** Border-aware centres now, graph cut on a trigger. C4 builds border-aware centres and labels each piece's cause. If free mode leaves more pieces per map than the old cut did, a follow-up issue ports `contiguous_cut` with the #1 fix. [Council C17: the old rate counts districts in pieces, not pieces; the owner sets the trigger on C4's numbers.]
- **S25.** Ownership is per channel layer. A district owns 100% of its channel's opportunity in its ZIPs. Another channel's district can cover the same ZIPs, on its own map layer.
- **S26.** A share exists only as a set of ZIPs. The ledger is the only ownership record. The master's shares are targets for the realizer. Reported shares, masses and bands come from the ledger, and maps are drawn only from it.
- **S27.** Drawability is settled in planning. The master carries a corridor floor, a border cap and a count cap, all computed from ZIP data, plus a rounding margin per support. [Council C6–C8: as printed, two of these rows exclude drawable plans and one is conditional; B1 corrects them (OQ1).]
- **S28.** A draw failure stops the run. If a share still can't be drawn and the drawn map breaks the final tolerance, the run fails and names the unit and district. Each such case is filed as a missing planning rule.
- **S29.** Literature lives in the global kb. `kb/references.bib` is the one registry of papers, fetched by DOI, and kb topic pages quote what papers say. td keeps only `docs/REFERENCES.md`, which says what td relies on each paper for.
- **S30.** Only what the support model cites is migrated. Each paper is re-read before it enters the registry. td's 6 `.bib` files and the LIT notes stay in the tag.
- **S31.** A citation needs a quoted result, or it stays `claimed`. It names a result for a named claim. `verified` means the passage was read, quoted in kb and checked for retraction. Withdrawn citations stay listed with the reason. The rule replaces td's trap 17 and becomes global.

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

## Pruning memory: td#55, 2026-09-28

**Status:** two judgement calls made without asking while executing td#55 (A3, S6's memory pruning) on m2-studio, 2026-09-28, m2 session 01a0e76f fork 01a0e771 ([DECIDED comment](https://github.com/helios1168/td/issues/55#issuecomment-5867688957)); merged in `764c5c9`.

**Context.** A3's keep list named the memories to keep from before the refactor. Five records written for the support master were not on it, and several kept memories carry `mem:` links to memories #55 deleted.

**Decision.**
- Five memories beyond A3's literal keep list stay: `decisions/support-refactor-2026-09-25`, `decisions/open-decisions-2026-09-28`, `decisions/issue-queue-reset-2026-09-28`, `facts/refactor-archive-and-queue` and `facts/tooling-traps`. Memory is 14 files plus `INDEX.md`, inside the 60-file cap.
- `mem:` links in kept memories that point at deleted memories are left as they are. `INDEX.md` says where they resolve: `740a985` for all, and `archive/pre-support-2026-09` for all but `workflow/docs-and-state`.

**Alternatives rejected.**
- Deleting the five: it would lose the settled S1–S31 and OD records and break the `AGENTS.md` trap pointers to `facts/tooling-traps`.
- Rewriting the dangling links: it would edit more of the kept memories than #55 asked for.

**Consequences.** `STATE.md` may carry Next and Blocked under the 1 KB cap. The repo has no instance-loader test until #66 lands. A version change goes through an explicit `requirements.txt` edit.
