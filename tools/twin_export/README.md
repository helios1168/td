# `twin_export` — work-machine runbook

Builds a **synthetic twin** of the confidential ZCTA instance: aggregate statistics plus a
fabricated instance on public ZCTA ids, both safe to carry back to the modelling repo.

You run this on the work machine. It never talks to the network, never writes anywhere but
the directory you give it, and never imports the territory-division repo (the handful of
functions it borrows are vendored in `_territory_vendored.py`, kept in sync by a test on
the repo side).

**Two files leave. Nothing else.**

| file | ≈ size | what is in it |
|---|---|---|
| `twin_stats.json` | 60–120 KB | aggregates only, every number k-anonymised |
| `twin_instance.json.gz` | ~1 MB per 30k ZCTAs | a synthetic instance on public ZCTA ids |

---

## 0. Install

```
python -m pip install -r requirements.txt      # numpy, scipy, networkx, pandas, pyarrow
python -c "import twin_export; print(twin_export.__version__)"
```

Python 3.9 or newer. `geopandas` is optional and only used if you pass
`--build-rook-from` or `--tiger-shapefile`.

Put the `twin_export/` directory somewhere on `PYTHONPATH` (or `cd` into its parent) and
run everything as `python -m twin_export ...`.

## Inputs

| flag | file | columns |
|---|---|---|
| `--graph` | the ZCTA Rook adjacency | see below |
| `--opportunity` | `zcta, M` | market opportunity per ZCTA |
| `--sales` | `zcta, A, B` | firm-A and firm-B sales per ZCTA |
| `--reps` | `zcta, rep_a, rep_b` | the two legacy rep maps |
| `--states` | `zcta, state` | optional, if the graph has no `state` attribute |
| `--coords` | `zcta, lon, lat` | optional; used only for the km territory radius |

**The graph.** The expected form is the **pyarrow/parquet edge table** you already cache
from your networkx build — two columns of ZCTA ids. Column names `u,v` / `src,dst` /
`zcta_a,zcta_b` are recognised automatically, otherwise the first two columns are used, or
name them with `--u-col/--v-col`. `.feather` works the same way. If reading the cache is
awkward, export it once from the session that has the graph:

```python
import pandas as pd
pd.DataFrame(list(G.edges()), columns=["u", "v"]).to_parquet("edges.parquet", index=False)
```

Also accepted, as secondary paths: a two-column `.csv` edge list, a pickled networkx graph
(`.gpickle`/`.pkl` — pickles only load under the networkx they were written with, so the
CSV route is the reliable one), `.graphml`/`.gml`, an `.npz` in the repo's
`zcta_adjacency` layout, and `--build-rook-from SHAPEFILE` (needs geopandas; never
downloads anything).

ZCTA ids are normalised with `zfill(5)` on read, so a source that dropped leading zeros
(`501` for `00501` — the classic integer cast) still joins. **Vintage:** the defaults are
`--zcta-vintage 2025 --tiger-vintage 2025`, recorded in `meta`; the repo side currently
holds a TIGER 2020 adjacency, so the vintage is what tells it whether to expect edge
differences.

Every node attribute on the graph except `state` and `lon`/`lat` is dropped the moment it
is read, so a graph carrying confidential per-ZCTA payload cannot leak through it.

---

## The runbook

### Step 1 — `validate`, on the real data, before anything else

```
python -m twin_export validate \
    --graph edges.parquet --opportunity opp.csv --sales sales.csv --reps reps.csv
```

This joins the four inputs and runs the model's own validity check. Read the join
diagnostics: it hard-fails below a 99% join, which almost always means an id-vintage or
leading-zero problem rather than missing data.

If it reports **pointwise headroom violations** (`M_z < max(A + θ·B, B + θ·A)`), stop.
That is a modelling question — the opportunity figure is smaller than the book it is
supposed to contain — and it has to be settled before a twin of it means anything.
Disconnected components and isolated ZCTAs are expected on a national graph (islands).

### Step 2 — `stats`

```
python -m twin_export stats \
    --graph edges.parquet --opportunity opp.csv --sales sales.csv --reps reps.csv \
    --states states.csv --out ./out --explain
```

Writes `out/twin_stats.json` and, with `--explain`, `out/leaving.txt` — a plain-English
inventory generated *from the stats file itself*, so it cannot drift from what was written.

If a k-anonymity guard fires the run exits **2**, names the offending key, and writes
nothing. The usual cause is a per-state block for a state with a handful of ZCTAs; raise
`--min-state` (default 100) so it is pooled into `OTHER`.

### Step 3 — `audit --sigma-sweep` (optional, recommended once)

```
python -m twin_export audit ... --stats out/twin_stats.json --sigma-sweep 0.05,0.10,0.15,0.20
```

Rebuilds the twin at each rank-jitter σ and prints the individual-level agreement beside
the neighbourhood-level agreement, so you can pick σ deliberately rather than accept the
0.10 default.

### Step 4 — `twin`

```
python -m twin_export twin \
    --graph edges.parquet --opportunity opp.csv --sales sales.csv --reps reps.csv \
    --states states.csv --stats out/twin_stats.json --out ./out
```

It builds the twin, prints the **privacy audit table**, and asks you to confirm before
writing anything. (`--yes` skips the prompt; the point of this step is that you read the
table.) On confirmation it writes `twin_instance.json.gz`, `twin_audit.json`, and an
updated `twin_stats.json` carrying the `audit` and `twin_check` blocks.

### Step 5 — `validate --twin`

```
python -m twin_export validate --twin out/twin_instance.json.gz --stats out/twin_stats.json
```

Re-runs the model's validity check on the twin and refreshes the `twin_check` block.
Exit **3** means the twin does not reproduce the real instance closely enough — report it,
do not export.

---

## Read these three things before you export

1. **The audit contrast.** The table has two halves.

   *Individual level* — Pearson on log, Spearman, share of ZCTAs within 1%/5% of their real
   rank or value, exact-rank matches against a Monte-Carlo band, exact-value matches,
   activity-flag agreement against its chance baseline, local rank agreement within 3 hops.
   **These should be weak.** Exact-value matches must be `0`; the tool refuses to build a
   twin where they are not. A Spearman near 1 would mean the twin is a relabelling.

   *Neighbourhood level* — correlation of 3-hop neighbourhood means, Moran's I real vs twin,
   rank correlation by hop, decile share curves. **These should be strong** for `M`: that
   structure is the whole reason the twin is worth carrying back. `A` and `B` are redrawn
   from the aggregates conditional on `M`, so their neighbourhood correlation is low by
   design, not by defect.

   The verdict line reports `individual_max_spearman`, the 3-hop correlation of `M`, and
   `sigma_effective` — σ recovered from the *measured* attenuation, so you can confirm the
   jitter you asked for is the jitter that happened.

2. **Every `twin_check` row with `ok = false`.** Each row is
   `{key, real, predicted, twin, tol, ok}`. `predicted` is what the twin *should* show given
   the privacy transformation — spatial statistics are attenuated by
   ρ² = 1/(1 + 12σ²) = 0.893 at σ = 0.10, because that is what rank jitter does. A spatial
   row that came back exactly equal to the real one would mean the jitter had not worked.

3. **`leaving.txt`.** The inventory of what is in `twin_stats.json`, generated from the file.

---

## What leaves this machine

**`twin_stats.json` — aggregates only.** No per-ZCTA number appears in it.

- every value passes `Agg.put(key, value, n_support)`; a value backed by fewer than
  `--min-support` (default 20) ZCTAs raises and the run exits 2
- every quantile is the **mean of a window of order statistics** around the rank, never a
  single ZCTA's value; **no minimum and no maximum is ever reported**
- the coarse CDF's top bin is merged downward until no single ZCTA supplies half its mass
- per-state blocks only for states with at least `--min-state` (default 100) ZCTAs;
  everything else is pooled into `OTHER`, and per-state blocks carry medians and IQRs only
- per-rep statistics are p25/50/75/90 windowed over ±3 reps, and their k-anonymity support
  is counted in ZCTAs, not reps
- rep names are replaced by integers at load; the name map never leaves the tool
- every number is rounded to 6 significant figures
- the writer refuses outright to emit any five-digit-shaped string, so a ZCTA id cannot
  appear even by accident
- with `--strip-scale` (on by default) M, A and B are divided by one common number, the
  median positive M, so no dollar amount appears anywhere; ratios are untouched

The blocks: `scale` (saturation = (ΣA + ΣB)/ΣM, book ratio, active/glue shares, Gini
coefficient of M over positive-M ZCTAs),
`marginals` (distribution shape of M, A, B, A/M, B/M: lognormal and dPlN fits, windowed
quantiles, a coarse CDF of bin means), `conditional` (share curves by M-decile and how A
and B co-move), `headroom` (slack over `max(A + θB, B + θA)` at θ ∈ {0.2, 0.4, 0.6}),
`spatial` (Moran's I, hop correlations), `graph` (adjacency structure — derivable from
public TIGER geometry anyway), `territories` (rep counts, territory size and fragmentation,
misalignment, census at `min_share` ∈ {0.01, 0.02, 0.05}), `per_state`, `radius` (how far a
rep's ZCTAs sit from the rep's own centre, in hops and km — the travel-cost calibration;
`--no-radius-km` drops the km half), `twin_check`, `audit`, `meta`, `inputs`.

Two things in there are ratios you have explicitly approved: `scale.saturation` (combined
market penetration) and `scale.book_ratio`. `--strip-penetration` rounds the saturation to
the nearest 0.05 if you would rather it were coarser.

**`twin_instance.json.gz` — a synthetic instance.**

- `nodes{z, state, A, B, M, rep_a, rep_b}` and `edges{u, v}`, columnar, ZCTA ids as strings
- **real and public:** the ZCTA ids, the Rook edge list, state membership — all three are
  derivable from public TIGER data, which the repo rebuilds independently and cross-checks
- **synthetic:** M, A, B and both rep maps. M's *ranks* are jittered by σ (default 0.10) and
  the values redrawn from the aggregates; A and B are drawn conditional on the new M; the
  rep maps are BFS-Voronoi territories calibrated to the measured misalignment
- **absent:** geometry of any kind, rep names, dollar scale
- `meta` carries the seed, σ, θ, λ, the rep counts, `graph_hash` (sha256 over the sorted
  edge list, so the repo can confirm it rebuilt the same graph), and the vintages

## Runtime

Under ten minutes end to end on a national instance (~33k ZCTAs, ~180 reps): `stats` about
a minute, `twin` about seven, `validate --twin` seconds.

## Exit codes

| code | meaning |
|---|---|
| 0 | success |
| 2 | a privacy guard fired (k-anonymity, or the JSON leak guard). Nothing was written. |
| 3 | a validation or `twin_check` failure |
| 4 | an input could not be read, joined, or made sense of |
