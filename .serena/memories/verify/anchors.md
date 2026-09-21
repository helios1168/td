# Reproducibility anchors that exist, and ones that do not

- `figures/u8_band/frontier.png` is byte-identical on re-run (sha256 `c9d3777...`); check
  `git status figures/` is clean first. There are no other figure sha256 anchors for
  `tools/measure`.
- Byte-identity re-run of `battery/results/meas_*/**.json`, modulo the `"written"` field.
- Each draw's `metrics.json` `winner.stage2_value`: recomputing `V` and matching it to 1e-9
  proves the instance file, map, roster and (θ, λ, filler) are the ones that produced the draw.
  This matters because `metrics.json` records an instance path in a different worktree.
- The shipped map: a rerun through the override code with no caps gives a byte-identical
  `draw.csv` (`mem:facts/shipped-map`).
- The full-problem track's stakeholder figure: `battery/results/full_problem/best/` carries
  `PROVENANCE.md` (instance sha256, code tag `stakeholder-best-1` = `26142e0`) and
  `reproduce.sh` (`mem:workflow/full-problem-track`).
- **Not an anchor:** `battery/results/borders_k18_v2_20260907/params.json` records
  `"maps": false` while every cell has a populated `figures/`; the maps came from a separate
  invocation, so that `params.json` is not provenance for the directory. No byte-identity
  anchor exists for that run.
- Before 2026-09-09 every draw used the 2020 gazetteer; reproduce those with
  `TD_GAZ_VINTAGE=2020` (`mem:geo/zcta-geometry`). The atom search needs `PYTHONHASHSEED=0`
  (`mem:facts/state-atoms-retired`).

Source: `.claude/agent-memory/code-verify/project_td-verification-oracles.md`;
`main:STATE.md` `## Facts`; host memory td-full-problem-overnight-2026-09-10.
