# `instance_export` — work-machine runbook

Exports the **real** ZCTA instance with the dollar scale removed. One file leaves:
`instance_descaled.json.gz`.

This supersedes `tools/twin_export/` for the N-way problem. The twin exists because the
2026-08-28 decision was "nothing real per-ZCTA leaves"; that was revised on 2026-08-31 once
PII and firm were masked upstream, and once it became clear the dollar level is not
information the model uses.

## Why removing the scale costs nothing

With `s_i(z) = S_i(z)/M_z` and `t_z = T_z/M_z`:

```
u_i(z) = c1·S_i + c2·(T_z − S_i) + λ·M_z  =  M_z · [ c1·s_i + c2·(t_z − s_i) + λ ]
```

`M_z` factors out, and the objective `Σ_i log g_i` shifts by `n·log κ` under a global
rescale — an additive constant that cannot move the argmax. **The optimal allocation, the gaps and the certificates are exactly identical** on the descaled
instance and the real one — **at every ρ ≥ 0.** Rescaling shifts `Σ log g_i` by `n·log κ`,
the same constant for every partition, and the perimeter is a combinatorial count, so every
objective *difference* is untouched and ρ transports unchanged.

So this is not a lossy privacy compromise. It is dropping a constant the solver never reads.

## Install

Nothing to install beyond the standard library, unless your edge table is parquet or
feather — then `pip install pyarrow`. Python 3.9+.

It is one file. **Read it before you run it** — that is the point of it being one file.

## Inputs

| flag | columns | notes |
|---|---|---|
| `--sales` | `zip_code, rep_id, firm, sales` | long: one row per (zip, rep). Zips repeat. |
| `--opportunity` | `zip_code, M` | one row per zip |
| `--graph` | edge table | parquet / feather / csv; `u,v` or `src,dst` or first two columns |
| `--states` | `zip_code, state` | optional |
| `--filler-key KEY` | — | repeatable; a `rep_id` that marks a **vacancy**, not a person |
| `--rep-ids PATH` | — | optional; an earlier export to check the surrogate ids against |

Both `--sales` and `--opportunity` may carry one more column, `current_channel`. See
"More than one channel" below: with it the tables go long by (zip, channel) and the export
changes format; without it nothing changes at all.

Column names are matched case- and underscape-insensitively, with the usual synonyms
(`zcta`/`zip`/`postal_code`, `rep`/`wholesaler_id`, `amount`/`production`/`premium`).
ZCTA ids are `zfill(5)`-normalised on read, so a source that dropped leading zeros
(`501` for `00501`) still joins.

`firm` is optional and kept only as a masked group label — it is the natural grouping for
the merger structure, and masking it costs nothing.

## No adjacency graph? Build it from TIGER

If the work machine has no edge table but does have the TIGER shapefiles,
`build_adjacency.py` produces both side inputs from them (needs `pip install geopandas`):

```bash
python3 build_adjacency.py --zcta tl_2020_us_zcta520.zip \
                           --state tl_2020_us_state.zip --out ./adj
# -> ./adj/edges.csv (--graph) and ./adj/states.csv (--states)
```

Rook rule: **shared boundary of positive length**, not corner-touching — the corner pairs
are ~2% of candidates and including them silently changes every contiguity answer. The
script self-checks against the verified national build (33,791 ZCTAs, 90,429 edges, 190
components; TIGER 2020 and 2025 give identical edge sets) and says so either way. State
membership is by the ZCTA's internal point, which is all the region labelling needs.
Everything derives from public TIGER data — the outputs are not confidential.

## Run

```bash
# 1. look before you leap -- prints the report, validates, writes nothing
python3 export_instance.py validate \
    --sales sales.csv --opportunity opp.csv --graph edges.parquet

# 2. export
python3 export_instance.py export \
    --sales sales.csv --opportunity opp.csv --graph edges.parquet \
    --states states.csv --out ./out
```

Step 2 prints the same report and asks for confirmation before writing (`--yes` skips).

## More than one channel

The business runs national, WH and FI over the same map, and the extract that carries all
three has one more column, `current_channel`, with values `national`, `wh` and `fi`. Both
tables must carry it, or neither: a channelled sales table joined to a per-zip opportunity
table would price every channel against the whole zip's opportunity. The header may be
spelled `current_channel`, `current channel` or `channel`, in any case; the values are
stripped and lower-cased.

| flag | columns |
|---|---|
| `--sales` | `zip_code, rep_id, firm, current_channel, sales` — one row per (zip, rep, channel) |
| `--opportunity` | `zip_code, current_channel, M` — one row per (zip, channel) |

A cell is a (zip, channel) pair, and the export is the same file with its node table long by
cell instead of by zip:

- `format` becomes `td_instance_descaled/2`.
- Node columns are `z, channel, m_rel, share, share_free, state`, one row per cell. `z`
  repeats, once per channel that zip has. A zip need not carry every channel; a cell that
  appears in neither table simply does not exist.
- `share[cell][rep]` is that rep's book as a fraction of **that cell's** opportunity, not of
  the zip's, and `share_free` likewise.
- `meta` gains `channels` (in the order the opportunity file first mentions them) and
  `kappa_channel`, plus `n_cells`.
- Edges, `state`, `firm`, `graph_hash`, the rounding and every other `meta` key are what
  they were. The graph is over zips, unchanged: contiguity does not know about channels.

Two things are pinned so that nothing already computed moves.

The divisor comes first. `m_rel` is `M / median(positive M)` as before, but the median is
taken over the `national` rows alone. Those rows are the extract the current instance was built from, so
every national cell's `m_rel` is the number it already has, and so is the district target that
was derived from it. A WH or FI cell is a ratio to the same national median, which is what
makes masses comparable across channels. Run without any national rows and the export refuses.

The rep ids come second. Surrogate ids are still handed out in descending book, but the reps with
national book are ranked among themselves first and the rest are numbered after them. So every
rep in the existing instance keeps the id it has there, and reps who appear only under WH or FI
take the numbers above. Firm labels are numbered the same way. Nothing is carried over from a
file and there is no map to keep: the order reproduces because the national rows are the same
data. **This only holds if that is true.** If the national rows in the expanded extract are not
byte for byte the rows the last export used, say so before anyone builds on the result.

`--rep-ids PATH` checks exactly that, against an earlier export you still have on this machine
(`instance_descaled.json.gz` from the previous run). It compares each surrogate id's book, zip
by zip, over the national channel, and stops the export if any of them moved. Only the zips
that file kept are compared, so a filtered copy of it works too. Skip the flag if you no longer
have the file.

One thing to read differently: with channels present, the candidate structure in the report
counts cells rather than zips. A zip is contested in national and untapped in FI, and it is
the cell that gets a decision. The report says so above the counts; the zip and cell totals
are both printed.

The footprint components and the balance-ceiling table below them still run on zips, summing
a zip's mass over all its channels. So the `k` column is the ceiling for districting the
whole opportunity at once, not the ceiling for any one channel. Read a per-channel ceiling
off a per-channel export, or off the projection tool on the repo side.

### Opportunity is summed per cell in the channelled extract

The single-channel extract repeats a zip's M on every one of its rows, and the exporter takes
it once (two different positive values in one zip are refused as a bad merge). The
three-channel extract carries a cell's opportunity once across its rows: one row holds it and
the duplicate rows hold 0, or several rows hold parts of it. With a channel column present the
exporter therefore sums the opportunity column within each (zip, channel) cell and never
compares rows. Summing the column over national rows gives the national total and over all
rows the whole opportunity, with no double counting.

### The command to run on the three-channel extract

These flags are the ones the last export used, and this run needs the same set or the national
numbers will not come out the same. From the current instance's own `meta`: 129 zips had their
opportunity lifted to the headroom floor, 90 had it imputed from their book, and one filler key
was in play. Use the same sentinel string as last time; it does not leave the machine, only the
count does.

```bash
# 1. read the report, validate, write nothing
python3 export_instance.py validate \
    --sales sales.csv --opportunity opp.csv --graph edges.parquet \
    --states states.csv \
    --filler-key '<the same sentinel as last time>' \
    --impute-missing-m --repair-headroom

# 2. export
python3 export_instance.py export \
    --sales sales.csv --opportunity opp.csv --graph edges.parquet \
    --states states.csv \
    --filler-key '<the same sentinel as last time>' \
    --impute-missing-m --repair-headroom \
    --out ./out
```

The three-channel extract is the source of truth from 2026-09-10 on and the single-channel
instance is retired, so its national opportunity values may differ from the old ones. Do not
pass `--rep-ids ./out-previous/instance_descaled.json.gz`: that flag checks the national share
vectors against the previous export and refuses to write when any moved, which is the right
check only when the national rows are meant to be identical. Rep surrogate ids are still
assigned to national reps first, by total sales, so they coincide with the old ids wherever the
national sales are unchanged.
`--theta 0.40` and `--lam 0.30` are the defaults and were what the last run used, so they are
not repeated here. The join rate was 1.0 last time, so `--join-floor` is not needed; if the
report shows it has fallen, read the failure message before touching that flag.

Before step 2, check three lines of the step 1 report:

- `channels  national wh fi` and `kappa from national`.
- `cells (zip, channel)` against what you expect from the extract.
- `validation: clean`. If headroom fails on a WH or FI cell, that cell's opportunity is
  smaller than the book in it, which is a data question and not one this tool should paper
  over with `--repair-headroom` unless the same call was already made for national.

## What the report tells you

```
candidate structure (cand(z) = real reps with positive sales)
  untapped   (0 reps)         412   no sales at all; adjacency only
  vacant     (0 reps)         792   sales, but only under a filler key
  uncontested(1 rep )       8,110   owner forced, no decision
  contested  (2+ reps)     23,900   the actual problem
  max candidates                5
  zips with filler book     1,340   (1,655 rows)
```

Below the candidate structure, the report prints the **footprint components and the balance
ceiling** — the numbers stage 1 is blocked on:

```
footprint components (a contiguous district cannot span two)
  share of M      zips   states
      46.8%        612   NY NJ MA
      30.6%        870   CA WA OR
      ...

balance ceiling (k_c equal districts per component; crumbs excluded)
  k   districts/component     ceiling spread   best possible spread
  6   2/2/1/1                      91.9%          91.9%  (same split)
  ...
```

Everything in it is a **share or a count** — no currency amount — so the `validate` run
(which writes nothing) is enough: read the share column and the ceiling table off the
console and carry them back by eye. Components below 1% of total opportunity are reported
as crumbs and excluded from the ceiling; since every disconnected component must host a
whole district, any crumb is a decision to surface, not to size.

Pass `--filler-key` for every sentinel your extract uses for a vacant territory. Its sales
stay in the instance as **unowned book** (`S_free`) that any inheriting rep partly captures,
but it never becomes a candidate owner — an objective term for a vacancy would have the
solver bargaining on behalf of an empty chair. The sentinel's own name does not leave: only
the counts do.

Under the rule agreed 2026-08-31, **a rep is a candidate for a zip only where it has
positive sales there.** That produces three classes and you should look at their sizes:

- **contested** — two or more claimants. The actual optimisation problem.
- **vacant** — sales exist but only under a filler key. Real book, real firm, no incumbent
  person. Nobody can claim these by legacy, which makes them the zips most genuinely up for
  grabs — and, under the candidacy rule, ownable by nobody until an allocation rule is set.
- **uncontested** — exactly one claimant. The owner is forced; the zip still carries utility
  into that rep's gain and still occupies space in the adjacency graph, but there is no
  decision to make. If this class is very large, most of the map is already settled.
- **untapped** — opportunity with nobody's book on it. **No candidate can own it.** These are
  kept in the export because deleting them would change the graph's connectivity — they are
  exactly the "zero-value glue" of failure regime (d). How they should be allocated is an
  open modelling question, not something this tool decides.

A large untapped class is worth raising before modelling continues.

## What leaves

`instance_descaled.json.gz`:

- **real and public** — ZCTA ids, the Rook edge list, state membership. All derivable from
  public TIGER data, which the repo rebuilds and cross-checks via `graph_hash`.
- **real and descaled** — `share[z][rep]` in [0,1], and `m_rel[z] = M_z / median(positive M)`.
  With channels, both are per cell and the median is the national one.
- **surrogate** — rep ids become `R0000…` in descending total share, national book first;
  firms become `F0, F1, …`. The map is built in memory and never written. This is a second
  pass on top of your upstream masking, so no upstream label rides along even if one looks
  innocuous.
- **absent** — every currency amount, the divisor κ, geometry, real rep or firm names.

Shares and `m_rel` are both dimensionless. **`share × M` would be the book, so `M` never
leaves in dollars** — only as a ratio to its own median. Do not export the raw opportunity
file alongside this one.

Every float is rounded to 6 significant figures.

## Guards

Checked before anything is written; any failure writes nothing.

| guard | exit |
|---|---|
| join rate below 0.99 | 4 — almost always an id-vintage or leading-zero problem, not missing data |
| any share outside [0,1] | 3 — sales exceed opportunity in that cell |
| pointwise headroom `1 ≥ maxᵢ(sᵢ + θ(t − sᵢ))` violated | 3 — the opportunity figure is smaller than the book it should contain. A modelling question; settle it first. |
| median `m_rel` outside [0.5, 2.0] | 2 — the descaling did not happen |
| any `m_rel` above 1e4 | 2 — looks like a currency amount |
| any `m_rel` below 0 | 2 — a cell cannot hold negative opportunity |
| `kappa` present in `meta` | 2 — the divisor must not leave |
| a surrogate id's national book moved, under `--rep-ids` | 2 — the ids no longer mean what they meant |

Every share guard runs per cell. The median is taken over the `national` cells alone: a
channel a third the size of national has `m_rel` around a third, and over every cell the
median would be measuring the channel mix rather than the descaling.

Exit codes: `0` ok · `2` guard fired · `3` validation failed · `4` unreadable input.

## On the repo side

```python
from descaled import load_descaled, check_descaled
d = load_descaled("instance_descaled.json.gz")
print(d.summary())
assert check_descaled(d) == []
# d.G carries cand/S/M per node; d.contested / d.uncontested / d.untapped
```

The loader multiplies `share × m_rel` back into `S`, so the graph it builds is the real
instance divided throughout by κ — exact to the 6-sig-fig rounding.
