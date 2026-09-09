# Root fix on the level-1 state-split MILP

Claim. With every district anchored to its home state (`build_milp(..., anchors=[(home(j), j)
for every j])`), fixing the flow roots `r[home(j), j] = 1` and `r[s, j] = 0` for the other
states (`td/solvers/milp_engines.py fix_roots`) leaves the optimal objective value and the set
of optimal `(z, y)` unchanged. Only the `r` and `f` blocks may differ.

Verdict: VERIFIED, 2026-09-08, by the `math-verify` agent, under the hypothesis that every
anchor handed to `fix_roots` is one `build_milp` applied (`var_lb` of that `z` is 1 at solve
time).

Basis.

1. `r` and `f` carry zero objective coefficients and appear only in the `root`, `rz`,
   `flow_tail`, `flow_head` and `net` row blocks; `place`, `yz`, `yz_lo`, `band` and `cap`
   never touch a root. Each flow row's support lies inside one district's columns, so the
   flow block separates over districts.
2. For a fixed `z` column and root, a district's flow rows are feasible exactly when its state
   set is nonempty, connected, and contains the root. Checked against a BFS oracle over every
   subset and every root on the assembled matrix: 1,824 pairs, no disagreement. The big-M is
   sound: `rz` puts the root inside the set, the arc caps `(N-1) z_end` confine flow to the
   set, every selected non-root node absorbs at least one unit, and a spanning tree on at
   most `N` nodes moves at most `N-1` units per arc, so the cap never binds.
3. An anchor forces the home state into the set for every feasible `z`, so the feasible
   `(z, y)` projections of the two models coincide and the objective depends on `(z, y)`
   alone.

Numbers. 320 paired solves at `mip_rel_gap = 0` (S from 4 to 9, k from 2 to 3, delta 0.1,
eta 0.01, random masses, some with caps and shared homes, 317 with the home a leaf of its
district, 26 with a district equal to its home alone). Max objective difference 3.3e-12, `z`
identical in every pair, max `y` difference 5.7e-12.

The gap the adoption step must guard. Fixing a root re-imposes the anchor through the `rz` row
(`r <= z`). When an anchor has been released, by a `bounds` entry that sets `z[home(j), j]` to
0 or by `--unanchor`, the root-fixed model is infeasible (one case, plain optimum 6.216) or
strictly worse (35 of 60 unanchored instances). `build_milp(fix_roots=True)` must therefore
root only the anchors that survive `_release_anchors` and `_release_bound_anchors` in
`tools/state_splits.py`. The bench's single call site passes one anchor list to both and uses
no caps, bounds or unanchor, so it is safe as written.

Caveats. The scipy engine only; k = 18, S = 49 not run here (the bench covers those sizes).

Reproduce:

```
/Users/ntlee/projects/td/.venv/bin/python3 tools/verify/milp_root_fix/check_root_fix.py
```
