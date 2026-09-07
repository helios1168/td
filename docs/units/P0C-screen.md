# Unit P0C-screen — the (★) roster-free screen, `B_tot`, saturation, and channel_note.tex §5.1

Status: open

Adversarial verification (`math-verify`, 2026-09-05) of track P0-C's uncommitted changes in
`.claude/worktrees/w2-phase0` (`tools/measure/premium.py`, `docs/channel_note/`): `B_tot`, the
(★) roster-free bound at `P_S` and `P₁₈`, the screen's slack against `EG_{S₁₈}`, saturation, and
`channel_note.tex` §5.1's claims about `D(g)` and the 30% continuity threshold. There is no
`MODEL_*.md` for this unit; `git show ae2b18d:docs/BORDERS_PLAN.md` and `channel_note.tex` are
the model.

## Model

none yet

## Verify

From `docs/VERIFY_P0C-screen.md` (2026-09-05, `math-verify`). Every numeric leg is recomputed
from a fresh transcription of `channel_note.tex`'s own equations, reading `S`, `S_free`, `M` off
the graph directly (`channel.gain_matrix` and `premium.measure` are never the witness for their
own output); the sole exception is `P₁₈` (an MILP, checked for optimality but not re-derived).

| # | claim | verdict |
|---|---|---|
| 1 | `B_tot = 3268.4069219934404` = eq. (decomp)'s `W₀` | **VERIFIED** |
| 2 | `Σᵢgᵢ = B_tot + w·P₀` is P0-C's *independent oracle* | **REFUTED** (as an oracle) — the identity itself holds, but it is a rearrangement of one sum, not two independent computations, and cannot see a shared misreading of eq. (util) |
| 3 | (★)@`P_S` = 96.55406280784752, (★)@`P₁₈` = 96.79300971267465 | **VERIFIED** |
| 4 | slack `0.021911…`/`0.260857…`; "loosening 0.064 → 0.261" | **split**: the two slacks VERIFIED; the "0.064 → 0.261" comparison **REFUTED** — it pairs v1's `P_S` rung with v2's `P₁₈` rung, which are different objects. Like-for-like, `P_S` tightens `0.064 → 0.022` (2.9×) and the roster-free `P_k` loosens `0.105 → 0.261` (2.5×); U11's prune (which uses `P_S`) gets tighter on v2, not weaker |
| 5 | `SATURATION = 29.6 %` and the six dependent macros | **VERIFIED** — definition `ΣT/ΣM` correctly adjudicated over the two candidate readings |
| 6 | §5.1's `0.912` nats vs `D(g)` quoted at `1e-4`–`1e-2`, and the retraction | **split**: the inversion (premium window `0.890` nats `>` `D(g) = 0.148` nats) and the retraction of "derived rather than assumed" VERIFIED; the quoted `D(g)` range and the "30% threshold crossed" sentence **REFUTED** — `D(g) = 0.148` is 15× the top of the quoted range (the range describes `D(M)`, the mass imbalance, not `D(g)`), and `29.588 % < 30 %`, so the note's own threshold is not crossed on v2 |

**Artifact**, moved out of the deleted per-unit artifacts directory to `tools/verify/P0C-screen/`:
`verify_p0c.py`.

**Required before the PDF is rebuilt** (blocking, not yet applied as of this report):
`channel_note.tex:520-521`'s `D(g)` range, `:526-529`'s 30% sentence, `:519`'s "≈0.91 nats", and
`git show ae2b18d:docs/WAVE2_PLAN.md:195`/`:320`'s stale slack comparison and oracle claim.

Full report: `git show 8b14eee:docs/VERIFY_P0C-screen.md`.

## Code verify

none yet
