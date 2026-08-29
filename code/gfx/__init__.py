"""
gfx -- the contiguity-programme graphics library (PLAN.md Part D, unit U7).

Replaces (does not extend) `battery/code/mapviz.py` and the per-script styling in
`case_pipeline.py` / `mkfig_zip50.py` / `mkfig_census.py` / `c8_rho_sweep.py`, which stay
frozen as the byte-identity anchor. Every new figure goes through this package.

Dependency policy: matplotlib + numpy + scipy only, everywhere, except
`geom.polys_from_shapes` which imports shapely lazily inside the function body. In
particular nothing here imports networkx or any solver module (`territory`, `districting`,
`contig_methods`) -- producers read only JSON/JSONL files on disk.

Submodules:
    style      palette, rcParams, figure-size presets, save(), lint_text_overlap()
    geom       polygon/segment geometry (Voronoi cells, TIGER shapes, adjacency segments)
    maps       axes-level map primitives (choropleth, heatmap, boundary, adjacency, seeds)
    charts     axes-level chart primitives (bars, tables, curves, ECDFs, matrices)
    schemas    the instance-JSON schema producers consume + a synthetic fixture builder
    producers  one CLI module per figure family; see Part D's "Common figure set" table
"""
from __future__ import annotations

__all__ = ["style", "geom", "maps", "charts", "schemas"]
