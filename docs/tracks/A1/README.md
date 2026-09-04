# Track A1 — derived documents

The A1 track (`docs/APPROACHES.md` §A1, joint coverage optimisation) re-ran stages 2–4 on
2026-09-03 with the instance measured. Its versions of the hub's stage-2/3 files live here so
the hub copies at `docs/` stay neutral for other tracks:

| here | supersedes (hub, `docs/`) | what changed |
|---|---|---|
| `LENS_GROMOV.md` | `LENS_GROMOV.md` | Moves 8/11/12/13; `EG^bal_S(δ)` replaces `EG_S`; ledger U13–U19 |
| `DOMAIN_optimization.md` | `DOMAIN_optimization.md` | §2.1 MINLP retired; §2.10–§2.15 new; D1′ replaces the τ-homotopy |
| `DOMAIN_economic-theory.md` | `DOMAIN_economic-theory.md` | §2.8–§2.10 new; D3 re-issued, D5 split, D6, D7 |
| `BRIEF.md` | `BRIEF.md` | units U8–U13, ★8–★12; U0–U7 marked landed / carried / retired |
| `units/U8-band.md` … `units/U13-base.md` | — | the six A1 units, none launched |

Paths inside these files were written when they sat at `docs/`; read `docs/BRIEF.md` as
`docs/tracks/A1/BRIEF.md`, `docs/units/U8-band.md` as `docs/tracks/A1/units/U8-band.md`, and
`docs/DOMAIN_*.md` / `docs/LENS_GROMOV.md` as the copies in this directory. Everything that
is a *fact about the instance* — `docs/MODEL_U7-meas.md`, `docs/MODEL_U1-cert.md`,
`docs/VERIFY_U1-cert.md`, `docs/CODEVERIFY_U7-meas.md`, `docs/LIT_optimization.md`, the
2026-09-03 section of `docs/LIT_economic-theory.md`, `tools/measure/`, FRAME §6's rows — stays
at the hub paths and is shared by every track.

Branch `wt/A1` (worktree `.claude/worktrees/A1`) continues from the hub head; launch U8-band
there from a session started in that directory (Serena binds to the launch directory).
