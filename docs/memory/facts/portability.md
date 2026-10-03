# td on other Pythons and platforms

Checks made on 2026-10-02 in td session 01a0fd88 (measured on m2), when the owner asked how to run td scenarios in a work Snowflake environment and then on a Windows work machine. Each holds for td at commit 9583135 and the package versions named. Python 3.12 and the history-free bundle: `facts/tooling-traps`. Snowflake runtimes: sv-ntlee `kb/snowflake-notebooks.md`. Recommendations: `decisions/work-environment-2026-10`.

- **Python 3.10:** td compiles except for `import tomllib` in `td/spec.py`, its only 3.11-only feature; a `tomli` fallback would make it 3.10-compatible. Compile check only; tests were not run on 3.10.
- **Snowflake's Anaconda channel cannot run td as is.** Every shapely there links GEOS 3.10.6, so `geo.voronoi_cells` (ordered Voronoi, GEOS ≥ 3.12) fails. Its highspy 1.13.1 also changes the plan against 1.15.1: WH 565 against 563 pieces at δ=0.25 on the comb ne6_clean scenario, both passing the audit.
- **Footprint:** one td run (4 channels, δ=0.25, no maps) peaks at about 450 MB resident memory and 6.6 s on m2.
- **Windows text encoding:** td's only run-path text open without an explicit encoding is `td/spec.py:229` (`areas.csv.gz`, used by `check_metros`), plus `td/geo.py:598` on the geo-build path. Under Windows' cp1252 default, decoding `areas.csv.gz` fails at byte 0x8d. `PYTHONUTF8=1` avoids it until the code is fixed.
- **Windows wheels:** the win_amd64 cp313 wheels of pyproj 3.7.2 and shapely 2.1.2 bundle PROJ 9.5.1 (EPSG v11.022) and GEOS 3.13.1, the same as the macOS wheels, so Windows shares the libraries that set the ZIP graph.
- **Cross-platform reference run:** `scenarios/50_ifa.toml` with `delta = 0.40` and `--fixture 0 --no-maps` gives ledger SHA-256 8310ebd1…2be18009 and an audit pass on m2, the same over two runs. A port can be checked against it.
