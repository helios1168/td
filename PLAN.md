# PLAN — branch `worktree-ca5-map`

## Goal

Add Voronoi district-boundary and CA5 state-atom map figures for the k=18 draw
(`atoms_k18_v2_20260906`), on top of the state-atoms engine's stage-1 output.

## Next step

Unknown, read the diff. Both commits (`ce1ef67`, `9363c14`) only add PNG figures under
`figures/atoms_k18_v2_20260906/`; no code or docs changed since the fork point. The branch is
2 commits ahead of `main` and not merged; check whether the figures are still wanted before
folding them in.

## Done

- 2026-09-06 CA5 state-atom map figures added (k=18, `atoms_k18_v2_20260906`): contestability,
  district_regions_voronoi, districts, firm_a, firm_b, opportunity.
- 2026-09-06 Voronoi district-boundary map added for the CA5 draw.

## Decisions needed

None recorded on this branch.

## Files owned / forbidden

Owned by this track: `figures/atoms_k18_v2_20260906/`.

Forbidden: `td/`, `app/`, `tools/` except what this track itself touches, `battery/`, `data/`,
any `instance_descaled*`, any other worktree's files, push, force-push, merge to `main`.
