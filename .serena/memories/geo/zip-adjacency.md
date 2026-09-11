# Zip and state adjacency

The sold-zip graph is shattered, which is why stage 1 is center-based (Hess) compact assignment
on distances, chosen by the user over adjacency contiguity on 2026-09-01.

- v1: 547 components over 1,229 zips. `centers.py` still quotes these; `docs/PROBLEM.md` §5 is
  corrected.
- **v2 instance graph: 862 components over 3,748 zips, 516 singletons**; the largest carries
  13.5% of M, and **47.6%** of M sits in components under 1% each.
- Contracted to states, the instance graph gives only 10 edges and 42 components. A state model
  must import the TIGER state rook graph (49 nodes, 107 edges), which `td/geo.py::state_rook`
  builds.
- Real ZCTA polygon adjacency over the 3,704 placed zips gives about 816 components with 474
  singletons (CLAUDE.md trap 23; the 2026-09-09 memory said 817). Nearest-polygon bridging
  would need edges of median 8 km up to 169 km, and contracting through all 33,300 CONUS ZCTAs
  gives 3.46M edges. So the reachability graph stays the Voronoi rook graph of the zip points,
  shipped as `proximity_edges` / `proximity_zips` in `geom.json`.
- The two tessellations share 4,462 edges of 10,483 and 4,843 (Jaccard 0.411). A district that
  looks scattered on screen is not evidence of a contiguity failure.
- Known gap: there is no DC to VA cell edge (queued on the full-problem track).

Related: `mem:geo/zcta-geometry`, `mem:decisions/rep-split-and-app-views`.

Source: `main:STATE.md` `## Facts` (a3924e8); host memory td-contiguity-programme; CLAUDE.md
traps 21 and 23.
