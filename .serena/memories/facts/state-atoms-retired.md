# State atoms: the retired stage-1 route, numbers kept for the record

Engine measured 2026-09-06 (`ff63511`, stage 1 only, run `battery/results/atoms_k18_v2_20260906`);
the route was retired the same day (`mem:decisions/stage1-route`). Target 473.5 at k = 18.

- Cut plan **CA 5 / TX 2 / NY+NJ 3 / FL 2**: 56 atoms, 126 edges, one component. Pieces CA1
  0.838x, CA2 to CA5 0.825 to 0.826x, TX1 1.013x, TX2 1.007x, NYNJ1 to 3 0.943 to 0.944x, FL1
  0.706x, FL2 0.691x.
- `Σ log M` **110.789532**, ceiling **110.883247**, gap **0.093715** nats, spread **30.484%**
  (max 1.130x, min 0.826x), all 18 districts connected.
- Of 52 state codes only 5 exceed target: CA 4.126x, TX 2.020x, NY 1.794x, FL 1.398x, NJ 1.037x
  (whole-instance tau = 473.5, every zip kept; the level-1 ground set reads higher, see
  `mem:facts/shipped-map`). Largest atom needing no cut: IL 0.677x. NY+NJ 2.831x, +CT 3.014x.
- The atom graph's one component certifies `BORDER_TOL`-proximity reachability, not that every
  district is a single polygon.

Prototype-only numbers (2026-09-05, not re-measured). Contiguity dropped, equal-mass cuts reach
110.883135 (gap 0.000112); every state whole reaches 107.011866 (gap 3.871); zip baseline
110.883101. Contiguity enforced: CA 3 / TX 2 / NY+NJ 2 gives 110.019580 (gap 0.864, spread
98.2%, and it severs New England: CT MA ME NH RI VT reach the network only through NY, leaving
them a 0.434x district); CA 3 / TX 2 / NY+NJ 3 gives 110.427114 (0.456); CA 4 / TX 2 / NY+NJ 3
gives 110.759967 (0.123). These draws are local search against a relaxation, not certified
optimal. Exact set partition was tried and abandoned (over 250k columns; HiGHS found no feasible
cover in 180 s at 177k).

**`PYTHONHASHSEED=0` is required** for the atom search, by decision: it tie-breaks on set
iteration over atom names, and without it results move about 0.015 nats.

Source: `main:STATE.md` `## Facts` (a3924e8).
