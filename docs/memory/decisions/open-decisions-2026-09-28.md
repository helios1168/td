# Answers to the plan's open decisions, 2026-09-28

The owner's answers to td#52's open decisions (OD codes), one section each. The plan as a whole: `decisions/support-refactor-2026-09-25`. `OPTIONS.md` is read from the tag `archive/pre-support-2026-09`.

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
