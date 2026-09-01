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
rescale — an additive constant that cannot move the argmax. **At ρ = 0 (the model) the
optimal allocation, the gaps and the certificates are exactly identical** on the descaled
instance and the real one. Only ρ > 0 mixes a log-scale term with a raw perimeter count and
therefore notices the scale.

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

Column names are matched case- and underscape-insensitively, with the usual synonyms
(`zcta`/`zip`/`postal_code`, `rep`/`wholesaler_id`, `amount`/`production`/`premium`).
ZCTA ids are `zfill(5)`-normalised on read, so a source that dropped leading zeros
(`501` for `00501`) still joins.

`firm` is optional and kept only as a masked group label — it is the natural grouping for
the merger structure, and masking it costs nothing.

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
- **surrogate** — rep ids become `R0000…` in descending total share; firms become `F0, F1, …`.
  The map is built in memory and never written. This is a second pass on top of your
  upstream masking, so no upstream label rides along even if one looks innocuous.
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
| any share outside [0,1] | 3 — sales exceed opportunity in that zip |
| pointwise headroom `1 ≥ maxᵢ(sᵢ + θ(t − sᵢ))` violated | 3 — the opportunity figure is smaller than the book it should contain. A modelling question; settle it first. |
| median `m_rel` outside [0.5, 2.0] | 2 — the descaling did not happen |
| any `m_rel` above 1e4 | 2 — looks like a currency amount |
| `kappa` present in `meta` | 2 — the divisor must not leave |

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
