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
