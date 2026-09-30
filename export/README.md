# `export/` — work-machine runbook

Exports the **real** ZCTA instance with the dollar scale removed. Two files leave:
`instance_descaled.json.gz` (format `td_instance_descaled/3`) and `channels.json`.

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

Nothing to install: standard library only, Python 3.9+. Inputs are delimited text (comma,
tab, semicolon or pipe); export parquet to CSV first.

It is one file. **Read it before you run it** — that is the point of it being one file.

## Inputs

| flag | columns | notes |
|---|---|---|
| `--sales` | `zip_code, rep_id, firm, current_channel, sales` | long: one row per (zip, rep, channel) |
| `--opportunity` | `zip_code, current_channel, M` | one row per (zip, channel), or several that sum |
| `--filler-key KEY` | — | repeatable; a `rep_id` that marks a **vacancy**, not a person |
| `--rep-ids-channel NAME` | — | optional; rank the reps with book in this channel first (see below) |
| `--rep-ids PATH` | — | optional; an earlier single-channel export to check the surrogate ids against; needs `--rep-ids-channel` |
| `--rep-map PATH` | — | optional; write the raw rep id to surrogate map here (`rep_surrogate, rep_id, firm_surrogate, firm`). Confidential: it stays on this machine |

Column names are matched case- and underscore-insensitively, with the usual synonyms
(`zcta`/`zip`/`postal_code`, `rep`/`wholesaler_id`, `amount`/`production`/`premium`).
ZCTA ids are `zfill(5)`-normalised on read, so a source that dropped leading zeros
(`501` for `00501`) still joins.

`firm` is optional and kept only as a masked group label — it is the natural grouping for
the merger structure, and masking it costs nothing.

## No graph, no states

`build_adjacency.py`, which built the old `--graph` and `--states` inputs from TIGER 2020
shapefiles, was removed on 2026-09-28 (td#54); it is in the tag `archive/pre-support-2026-09`.
Exporter v3 (td#61) drops `--graph` and `--states`: the ZIP graph and each ZIP's state are
built in the repo from public 2025 data (td#62). No edges or states leave this machine.

## Run

```bash
# 1. look before you leap -- prints the report and the channel table, writes nothing
python3 export_instance.py validate --sales sales.csv --opportunity opp.csv \
    --filler-key '<sentinel>' --impute-missing-m --repair-headroom

# 2. export
python3 export_instance.py export --sales sales.csv --opportunity opp.csv \
    --filler-key '<sentinel>' --impute-missing-m --repair-headroom --out ./out
```

Step 2 prints the same report and asks for confirmation before writing (`--yes` skips).
`--impute-missing-m` and `--repair-headroom` are the data repairs the last export used; their
counts are reported and ride into `meta`. `--theta 0.40` and `--lam 0.30` are the defaults.

Before step 2, check in the step 1 report that the channel table lists the channels you
expect, spelled the ways you expect, and that it says `validation: clean`.

## Channels

The channel column may be spelled `current_channel`, `current channel` or `channel`, in any
case, and both tables must carry it, or neither: a channelled sales table joined to a per-zip
opportunity table would price every channel against the whole zip's opportunity. With neither,
the whole extract is one channel, `national`.

**Any channel value is accepted.** Each is normalised: stripped, lower-cased, then any run of
spaces, hyphens, slashes, parentheses or dots becomes one underscore, and a leading or
trailing underscore is dropped. So `Wells (WH)`, `WELLS-WH` and `wells wh` are one channel,
`wells_wh`. A value that normalises to nothing is refused. The channel list is the order in
which the opportunity table first names each channel. A channel that only `--impute-missing-m`
brings in, from sales rows alone, follows those, in sales-table order.

A cell is a (zip, channel) pair:

- `share[cell][rep]` is that rep's book as a fraction of **that cell's** opportunity, and
  `share_free` likewise.
- A zip need not carry every channel; a cell that appears in neither table does not exist.
- With a channel column, a cell's opportunity is the **sum** of its rows: the extract carries
  a cell's M once across its rows (one row holds it and duplicates hold 0, or several rows
  hold parts). Without one, M repeats on every row of a zip, and two different positive
  values there are refused as a bad merge.

**One divisor for every channel.** `m_rel = M / κ`, where κ is the median positive cell M
over all channels. So masses are comparable across channels and no channel is special.

**`channels.json`** is written next to the instance, for the owner to review before anything
is modelled. Per channel, in file order, it holds the raw values that normalised to its name
(`spellings`; empty for a channel-less extract), its `sales_rows`, `cells` and `zips`, and its
`opportunity_share` of the total. It holds counts and one ratio, never a currency amount and
never κ.

### Surrogate rep ids

Surrogate ids are handed out in descending total book across channels. With
`--rep-ids-channel NAME`, the reps with book in that channel are ranked first, on that
channel's book alone, and the rest follow. So they keep the ids an earlier single-channel
export of that channel gave them. Firm labels are numbered the same way. Nothing is carried
over from a file and there is no map to keep: the order reproduces because the rows are the
same data, and the flags must be the same too.

`--rep-ids PATH` checks exactly that, against an earlier single-channel export still on this
machine. It compares each surrogate id's book, zip by zip, over `--rep-ids-channel`, and stops
the export if any of them moved. Only the zips that file kept are compared, so a filtered copy
of it works too. Skip the flag if the channel's rows are not meant to be identical.

To tie a scenario's surrogate rep ids back to people, run the same export again with
`--rep-map rep_map.csv`: the ids are a deterministic ranking of the same inputs, so the map
holds for the file already in use. The map is confidential and never enters the clone.

## What the report tells you

```
candidate structure (cand(z) = real reps with positive sales)
  untapped   (0 reps)         412   no sales at all
  vacant     (0 reps)         792   sales, but only under a filler key
  uncontested(1 rep )       8,110   owner forced, no decision
  contested  (2+ reps)     23,900   the actual problem
  max candidates                5
  zips with filler book     1,340   (1,655 rows)
```

Every count in it is per **cell**, not per zip: a zip is contested in one channel and
untapped in another, and the cell is what gets a decision.

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
  into that rep's gain and still occupies space on the map, but there is no
  decision to make. If this class is very large, most of the map is already settled.
- **untapped** — opportunity with nobody's book on it. **No candidate can own it.** These are
  kept in the export because deleting them would punch holes in the map. How they should be
  allocated is an open modelling question, not something this tool decides.

A large untapped class is worth raising before modelling continues.

## What leaves

`instance_descaled.json.gz`, format `td_instance_descaled/3`, and `channels.json`:

- **real and public** — ZCTA ids.
- **real and descaled** — per cell, `share[cell][rep]` in [0,1] and `m_rel[cell] = M / κ`.
  Node columns are `z, channel, m_rel, share, share_free`, one row per cell.
- **surrogate** — rep ids become `R0000…` in descending book; firms become `F0, F1, …`.
  The map is built in memory and written only by `--rep-map`. This is a second pass on top
  of your upstream masking, so no upstream label rides along even if one looks innocuous.
- **channel names**, normalised, and in `channels.json` their raw spellings and counts.
- **absent** — every currency amount, the divisor κ, geometry, edges, states, real rep or
  firm names, and the filler sentinel's name.

Shares and `m_rel` are both dimensionless. **`share × M` would be the book, so `M` never
leaves in dollars** — only as a ratio to its own median. Do not export the raw opportunity
file alongside this one.

Every float is rounded to 6 significant figures.

## Guards

Checked before anything is written; any failure writes nothing.

| guard | exit |
|---|---|
| a channel column on one table only, or a blank channel value | 4 |
| two different M values for one zip in a channel-less extract | 4 — a bad merge |
| an opportunity value that is NaN or infinite | 4 — bad data; a blank M reads as no value |
| a cell whose opportunity totals below 0, after `--impute-missing-m` | 4 — a cell cannot hold negative opportunity |
| join rate below 0.99 | 4 — almost always an id-vintage or leading-zero problem, not missing data |
| any share outside [0,1] | 3 — sales exceed opportunity in that cell |
| pointwise headroom `1 ≥ maxᵢ(sᵢ + θ(t − sᵢ))` violated | 3 — the opportunity figure is smaller than the book it should contain. A modelling question; settle it first. |
| median positive `m_rel` outside [0.5, 2.0] | 2 — the descaling did not happen |
| any `m_rel` above 1e4 | 2 — looks like a currency amount |
| any `m_rel` below 0 | 2 — a cell cannot hold negative opportunity |
| a field named `kappa` in `meta` or `channels.json` | 2 — the divisor must not leave (a channel may still be called kappa) |
| the filler sentinel's name anywhere in the payload or `channels.json`, in any value or key, raw channel spellings included, in any case or Unicode form (compared NFKC-normalised and case-folded); only the exporter's own field names, each listed in the code, are exempt | 2 — only its count leaves |
| `--rep-ids` without `--rep-ids-channel`, or naming no channel of the extract | 4 |
| a surrogate id's book moved in `--rep-ids-channel`, under `--rep-ids` | 2 — the ids no longer mean what they meant |

Every share guard runs per cell. The median guard runs over every positive cell, the set κ
is the median of, so it is 1.0 by construction up to imputed and repaired cells.

Exit codes: `0` ok · `2` guard fired · `3` validation failed · `4` unreadable input.

## On the repo side

The extract goes to the hub root on m2 and is gitignored. `td/data.py` (td#66) loads it,
multiplying `share × m_rel` back into `S`: the real instance divided throughout by κ, exact
to the 6-sig-fig rounding.
