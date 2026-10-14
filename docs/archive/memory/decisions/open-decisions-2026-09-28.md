# Answers to the plan's open decisions, 2026-09-28

The owner's answers to td#52's open decisions (OD codes), one section each, in OD order. The plan as a whole: `decisions/support-refactor-2026-09-25`. `OPTIONS.md` is read from the tag `archive/pre-support-2026-09`.

## OD1: the final band tolerance (td#56)

**Status:** the owner's answer to four structured questions in m5 session 01a0e73e (alias `m5-56`), 2026-09-28, recorded in [td#56's decision comment](https://github.com/helios1168/td/issues/56#issuecomment-5867757782) with its DECIDED line (oracle run f705d6cc). Decision-only: the empty marker commit 7f4ac7f was merged as f292304.

**Context.**
- #52 left the final band open as OD1 and made it block D1 (#73) and E1 (#74). S23 lets repair move a piece only inside OD1's tolerance, and OD5's whole-or-splittable metro test reads the band's upper bound U_c.
- OD1 and D1 formed a soft cycle. D1 measures the smallest feasible δ, which would inform OD1, but D1 was blocked on OD1. The owner therefore declared an initial δ before D1 runs (m5 session 01a0e73e, td#56, 2026-09-28).
- The archived `tools/group2_run.py` `planner_args` (tag `archive/pre-support-2026-09`) ran δ = 0.1 per-bundle with `--band-break` on the split-capped states CA 3, TX 2, NY 2 and FL 2. This was the 2026-09-11 FI 21 rule in the removed memory `decisions/full-problem-2026-09-11`, also at the tag (td#56, 2026-09-28).
- #52 did not retire that band-break decision. OD1 now supersedes it (td#56, 2026-09-28).

**Decision.**
- The default final band is symmetric, δ_c = 10%, and each scenario declares it separately for each planning channel. A channel may take a different value only when the scenario says so explicitly.
- The planning constraints sit inside each channel's final band, tightened by the per-support margin μ_S (S27).
- The archived CA, TX, NY and FL band breaks are retired, and the band is never widened silently.
- When a declared band is infeasible, the run reports the smallest master δ where one is available. That δ is never adopted automatically; only a rerun that declares it explicitly may use it.
- Repair is allowed only when both drawn district masses stay inside their declared final bands and the target is admissible in the piece's unit mode.
- The audit uses drawn ledger masses. It allows at most 1e-9 × τ_c of numerical slack at each band boundary, lists every larger breach, and applies the S28 failures.
- The initial 10% is not claimed feasible on the fresh extract. Earlier measurements, including the old band-break run and `facts/conus-track2-grid`, are not evidence of feasibility here.
- This δ also sets OD5's metro whole-or-splittable threshold U_c.

**Alternatives rejected.**
- One shared scenario δ: it would rule out explicit channel-specific targets.
- A looser or a tighter default: rejected until there is evidence from the fresh extract.
- Looser audit slack: it could mask breaches.

**Consequences.** D1 and E1 run against a declared δ_c = 10% per channel. A smallest-δ result is a report, not a new band. Any wider band must be declared in the scenario as a separate run.

## OD2: the authoritative ZIP graph (td#57)

**Status:** the owner's answer to two structured questions in m5 session 01a0e73e (alias `m5-57`), 2026-09-28, recorded in [td#57's decision comment](https://github.com/helios1168/td/issues/57#issuecomment-5867271658) with its DECIDED line. Decision-only: the empty marker commit 829e8f0 was merged as 463290b.

**Context.** `OPTIONS.md` §D4 asks every result to pin six things: the graph-construction method and version, the gazetteer vintage, the authoritative planning adjacency, the permitted support overrides, what happens to assigned ZIPs missing from the graph, and whether zero-opportunity ZIPs are in the optimization domain. #52 §9's OD2 recommendation pinned only the method and the vintage. The vertex set, the clip region, the missing-ZIP policy and the zero-opportunity domain were left open until G1 (m5 session 01a0e73e fork 01a0e759, td#57 handoff). The pre-refactor graph is described in `geo/zip-adjacency`.

**Decision.**
- The authoritative adjacency is the Voronoi rook graph of 2025 gazetteer points over the extract's placed ZIPs only.
- Its vertices are the extract ZIPs that have a 2025 point and a Voronoi cell that survives state clipping, shipped as an explicit list and never inferred.
- An edge needs a shared border of positive length. DC–VA is the only manual override, and islands are not bridged.
- Zero-opportunity ZCTAs are for display only and are not optimization vertices.
- ZIPs with no point, or whose cell does not survive clipping, are listed in a report. Placing HUD-only ZIPs is G2's job (td#63).
- G1 (td#62) checks all CONUS ZCTAs as a stand-in before the real extract exists. C2 and E1 must rerun the state-component check on the real graph.
- `AGENTS.md` trap 23 is no longer provisional. No source or number from the earlier vintage counts as a current measurement.

**Alternatives rejected.**
- Real-ZCTA rook adjacency: it fragments heavily (`geo/zip-adjacency`).
- All CONUS ZCTAs as vertices: zero-opportunity ZIPs would change contiguity.
- Island bridges: td#45 never adopted them.

**Consequences.** G1 builds the graph under these pins and reports the missing ZIPs. Contiguity checks run on the listed vertex set, never on the drawn ZCTA polygons.

## OD3: output status and certificate tiers (td#58)

**Status:** the owner's answer to a structured question in m5 session 01a0e73f (alias `m5-58`), 2026-09-28, recorded in td#58's decision comment with its DECIDED line (oracle run f379a4f0). #58 was still labelled `doing` on m5-studio when this was filed on 2026-09-28.

**Context.** `OPTIONS.md` §D5 defines the exact tier as a solve at `mip_rel_gap=0.0` with a valid certificate. It requires master optimality, drawn-ledger feasibility and staffing validity to be reported separately (m5 session 01a0e73f fork 01a0e75c). The Nash-era two-tier numeric acceptance, `CERT_TOL = 1e-8` and `EPS_CERT = 5e-3` nats in `td/solvers/base.py` at the tag, was deleted in #54 and left to OD3.

**Decision.**
- Run outputs are district-only plans. The ledger CSV's rep column stays blank, and there is no staffing claim until staffing returns.
- The scorecard gives each master solve one of three certificate tiers:
  - **exact:** a proven optimum at `mip_rel_gap=0` (D5, `AGENTS.md` trap 12);
  - **bounded:** an incumbent with a valid bound and the actual gap;
  - **feasible only:** a validated plan with no optimality claim.
- The tier certifies the master only. Drawn-ledger checks are reported separately.

**Alternatives rejected.**
- Rep labels now: there is no verified roster.
- Two tiers, or a single status: fewer tiers hide the bounded case, where a bound exists with a gap.

**Consequences.** OD3 defines what each tier means and sets no numbers. The Nash-era tolerances `CERT_TOL` and `EPS_CERT` therefore have no successor in the support-master scope (td#58 comment, 2026-09-28). As of 2026-09-28, #70 (audit.py), which builds the tier row, does not link #58; only #71 does.

## OD5: metro outlines and oversized metros (td#60)

**Status:** answered by an oracle run (b7b1af8d) in m5 session 01a0e75a (alias `m5-60`) under the autonomous queue and recorded in [td#60's OD5 comment](https://github.com/helios1168/td/issues/60#issuecomment-5867324973) with four DECIDED lines. The owner adopted it as their own answer during `/land 60` ([comment](https://github.com/helios1168/td/issues/60#issuecomment-5867395304)), 2026-09-28. Decision-only: the empty marker commit 5785a33 was merged as 6b4560f.

**Context.** #52 §4 gives a whole metro its own unit, and S13 makes the metro feature optional. For a cross-state metro in clipped mode, #52's S14 row says the metro "stays whole" while §4 says it "keeps its own unit". The two readings differ for a metro whose mass is above the band's upper bound, which cannot fit in one district (m5 session 01a0e75a, td#60, 2026-09-28). The owner's 2026-09-25 geography choice, that the metro wins over a state line in clipped mode and is logged as an exception, is in `decisions/support-refactor-2026-09-25`.

**Decision.**
- Metro outlines are the 2025 metropolitan CBSAs the scenario lists by code. Each is the union of the ZIPs assigned to its 2025 TIGER/Line CBSA counties: a ZIP's membership follows its G1 county and that county's 2025 CBSAFP.
- The feature is off by default (S13). CSAs, metropolitan divisions and micropolitan CBSAs are not metro units.
- Each planning channel classifies every metro once, against the scenario's declared band upper bound U_c. A metro with M^c ≤ U_c is whole and never split. One with M^c > U_c keeps its own unit and is split under the scenario's clipped or free mode by the master's shares and the ZIP realizer.
- The classification stays fixed through a smallest-δ search.
- S14 means that a cross-state metro keeps its own unit, not that it is forced whole. The audit logs the crossing.
- There is no metro-binding step. A disconnected whole unit stops the run under OQ6.

**Alternatives rejected.**
- Carving all CBSAs, or using CSA or division outlines: adds units nobody asked for and conflicts with #52's CBSA recommendation.
- A separate ZIP→CBSA polygon overlay: could break the county-union outline.
- Always-free or always-clipped overrides, or reclassifying mid-search: changes the scenario's semantics or breaks C4's fixed-mode premise.
- Forcing an oversized cross-state metro whole: a mass above U_c cannot fit in one district.

**Consequences.** Under #52 §4's master rows, a clipped metro split only among its own singleton copies is feasible only if some integer n satisfies M^c/U_c ≤ n ≤ M^c/L_c. Without such an n, that mode can be infeasible (td#60, 2026-09-28; first proposed for #64's `MODEL.md`).
