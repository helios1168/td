# Confidential data: what may exist here and what never leaves

The user's real territory data lives on a separate confidential work machine and never enters
this environment raw. What arrives is the **real instance, descaled** (route since 2026-08-31):
per-(zip, rep) shares `s_i = S_i/M_z` in [0, 1], `m_rel = M/median(M)`, surrogate rep ids,
public ZCTA ids and edges, and no currency amount. PII and firm identity are masked upstream
(firms appear as `F0` / `F1`). The exporter is `tools/instance_export/export_instance.py`
(stdlib only, one file, meant to be read before it is run); the loader is `td/instance.py`.

**Why descaling loses nothing.** `u_i(z) = M_z·[c1·s_i + c2·(t_z - s_i) + λ]`, so `M_z` factors
out, and `Σ_i log g_i` shifts by `n·log κ` under a global rescale. The descaled and real
instances have identical optima, gaps and certificates at every ρ ≥ 0
(`mem:model/corrections`).

**Rules.**
- Never ask for raw sales or raw `M`. Never let shares and raw `M` leave together:
  `share x M` is the book.
- The exporter refuses to write on a join below 0.99, a share outside [0, 1], a headroom
  violation, a median `m_rel` away from 1, or the divisor appearing in `meta`.
- A vacancy filler key marks territories with no incumbent (real sales, real firm, never a
  candidate owner); pass it as `--filler-key`; its own name does not leave.
- Geometry never leaves either way; TIGER ZCTA5 is public and rebuilt here (`data/README.md`).
  `tools/twin_export/` (on `contiguity-harness`) is superseded.
- `data/`, `battery/results/` and `instance_descaled*.json.gz` are gitignored. Never commit
  them, and never copy per-record values (data rows, individual rep or zip values) into
  commits, docs, memories or beads. Aggregates and settled numbers are fine.
- Per-zip values may be shown in the scenario app only because it runs on a private tailnet
  (`mem:decisions/app-2026-09-08`).

Source: host memory td-work-machine-constraints (2026-08-31, updated 2026-09-08).

**Correction, 2026-09-28 (td#61, merged 9beed30).** Exporter v3 lives at
`export/export_instance.py` (runbook `export/README.md`), not `tools/instance_export/`. It
writes `td_instance_descaled/3`, long by (zip, channel) cell, plus `channels.json` (per
channel: raw spellings, row, cell and zip counts, opportunity share; never κ or a currency
amount). One divisor κ, the median positive cell M over all channels, serves every channel.
Any channel value is accepted and normalised; an extract with no channel column is one
channel, `national`. No edges or states leave any more: the ZIP graph and states are built
in the repo from public 2025 data (td#62). `--rep-ids` now requires `--rep-ids-channel`, the
channel an earlier single-channel export is checked against. Decisions:
`mem:decisions/exporter-v3-2026-09-28`. Source: m5-studio session 01a0e75a (m5-61), td#61.

**Update, 2026-10-01 (owner; AGENTS.md since f98b9a3 and 2026-10-01).** Confidentiality is now masking: sales, rep names and firm names stay out of the repo, issues, memory and anything online. Descaled opportunity and everything the model makes from it, and since 2026-10-01 dollar opportunity (channel totals and dollars per district), may appear in the public repo. The privacy boundary of an export includes the raw spellings in `channels.json`, not only the gzipped instance (td#61 review, session 01a0f177).
