# Verifying reported numbers: manifests, fields and docs

Established verifying U8-band v2 §10 (2026-09-05, reporting fidelity).

- **Re-run the gate only.** `frontier.resolve_draw_dir` -> `read_draw` -> `td.channel.stage2`
  -> `frontier.build_setting` -> `eg_band.solve_band(U, M, None)` takes about 40 s at
  k = 18 / n = 3,748 and reproduces the whole `gate` block bit for bit. It is the cheapest way
  to prove a manifest is not stale and to recover quantities the manifest never stored (`sol.g`
  at the gate). Import is `from td import instance as descaled`; there is no
  `frontier.load_setting`.
- **Re-derive per-agent vectors from other stored vectors.** In a `draw_*.json` manifest,
  `g = prop_gap + u_total/k`, then `Σ log g` must equal `points[i].primal` (holds to 1.5e-14);
  `Σ m == T` exactly; counting masses on the band edge `tgt(1±δ)` at 1e-6 reproduces
  `vertex.n_tight_bands` exactly. Three cross-checks with no solver.
- **Misalignment test** (`districts` against `staff`): print what the wrong array would give at
  the same indices and show the doc contains none of those labels. Corroborate with
  `vertex.tight_agents` (indices), which is independent of `nu`.
- **Two upper bounds live in one manifest; ask which one a doc row uses.** `points[i].upper`
  (the OA master's) and `certified_upper[i] = min(upper, dual_check.bound)`
  (`frontier.py:131-135`) differ by 2 to 5e-9. `frontier.shape` uses `upper`;
  `softness.direct`, `delta_star` and the plot use `certified_upper`. Any claim at the 1e-9
  scale flips with the field. State the field.
- **Fields vacuous when a flag is absent.** `gate.matches_reference` is
  `reference is None or ...` and `gate.delta_upper` is `None` without a reference
  (`frontier.py:246, 250`); both degenerate when `--gate-reference` is omitted, as on v2.
  Quoting `matches_reference = true` as a passed check is a live failure mode in generated
  results sections.
- **Realised against pass quantities.** A level-1 `pass_max_dev` is not the realised max
  deviation (`mem:facts/shipped-map`); check which column of `grid.csv` a sentence quotes.

Source: `.claude/agent-memory/code-verify/project_td-verification-oracles.md`;
`main:STATE.md` `## Facts`.
