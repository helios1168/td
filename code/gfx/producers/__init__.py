"""gfx.producers -- one CLI module per figure family (PLAN.md Part D).

Every producer is invoked as `python -m gfx.producers.<name> <inputs...> --out <png>`.
None of them import a solver (`territory`, `districting`, `contig_methods`) -- they read
only JSON/JSONL/CSV files already on disk and hand them to `gfx.maps` / `gfx.charts`.
"""
from __future__ import annotations
