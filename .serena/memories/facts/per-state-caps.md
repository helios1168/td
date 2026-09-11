# Per-state split caps on the single-channel map (measured 2026-09-07)

Three different answers, never to be merged into one: refused by the floor, refuted by the
solver, and searched without success.

- **NY at 2 is refuted.** HiGHS Status 8 in seconds: two anchored districts need 1.90 tau, the
  state supplies 1.805 tau.
- **CA at 4 is neither refuted nor found.** Legal at δ = 5%, exactly on the floor (4.200 tau of
  band against 4.153 tau, a window 4.7% of a district); an hour of branch and bound ended with
  no incumbent at all (Status 13, `primal_status is None`). This refutes nothing.
- TX and FL are already at their floor of 2, so the map is tight and the band is the lever.
- **CA capped at 4 at δ = 10% solves**: 7 splits, CA in 4, NY falls to 2, NJ splits, spread
  16.70%, stage 2 95.7458, time-limited incumbent at a 1.79% gap (`figures/overrides/ca4_d10/`).

The multi-channel track uses its own caps (CA 3, TX 2, NY 3 with the band broken for CA and
TX): `mem:decisions/full-problem-2026-09-11`.

Source: `main:STATE.md` `## Facts` and `## Next` row 1 (a3924e8).
