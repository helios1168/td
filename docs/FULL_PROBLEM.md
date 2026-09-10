# The full problem: three channels, one map, one rep pool

**Opened:** 2026-09-10 on branch `worktree-full-problem`. This file owns the formulation of the
full CWIFI problem: the business statement, the cell data, the joint problem F, the decomposition
that lets every existing solver run per bundle, the state-level plan solver (level 0), and the
routes to be timed. `docs/PROBLEM.md` and `docs/MODEL.md` keep the one-channel facts this file
builds on; `PLAN.md` on the branch carries the running log. Code anchors are `file:line` on
`main` at `7325737`.

## 0. Resume

Date 2026-09-10, branch `worktree-full-problem`, nothing solved yet.

Settled (the eleven decisions of 2026-09-10, all the user's):

1. "Other" is the residual: cells left after national, WH and FI districts are cut. A fourth
   channel exists iff the catch-all pass over the residual produces at least one district.
2. Dropped national falls back into WH and FI with no loss: national is the two largest firms,
   one WH and one FI. At most three served channels per state, never four.
3. Fallback ratio is the zip's own WH:FI mass ratio (the data carries national as one row). A zip
   with national mass and no WH or FI mass takes the state ratio, then 50/50, and is reported.
   Superseded on 2026-09-11 by decision 12 wherever the file carries the sub-channels; the ratio
   stays the rule for a file that carries national as one row.
4. Merge drivers: rep books (route R) and a geographic extent cap (route G), explored in
   parallel. The extent cap is max states per district and max centroid distance.
5. Priority reading: sequential (route S) and lexicographic joint (route J) in parallel, chosen
   by how fast J solves.
6. A channel need not cover the map; a state may be absent from a channel; districts are
   contiguous at the channel level (a state with no B cannot bridge two B districts).
7. Upper band U = 1.2τ.
8. Pass 1 of route J counts national mass in pure national slots only.
9. Catch-all pass on.
10. Data arrives in the v2 format, long by (zip, channel), `current_channel ∈ {national, wh,
    fi}`; the national rows are exactly today's data; the exporter is updated.
11. Execution optimised for wall-clock, tokens unconstrained.
12. (2026-09-11) National is the sum of three sub-channels, National (Chase), Wells (WH) and
    Wells (FI). Folding national into a merge sends Chase and Wells (FI) to FI and Wells (WH) to
    WH. The next export carries the three as `national_chase`, `national_wells_wh`,
    `national_wells_fi` (any letter case) in place of `national`; national is re-aggregated
    from them, and the fine split is exact (§2).

Open (★ items, §8): ★B WHFI⁺ bundle on or off; ★C rep pool size against 48 to 60 districts and
whether reps carry a channel tag; ★D η and the centre-free tie-break; ★E whether a state may
split geographically across plans. Route S versus J is decided from the timing table after
wave 2.

## 1. The business problem

We need to design territories on the CONUS map across several channels. So far only one channel,
national, has been drawn. The other channels are not designed yet, and we want them to come out
the same way the national map did. There are roughly three strategies, each of one to four
channels. The hardest is Combined WIFI, CWIFI: $48B of opportunity across national, WH, FI and
whatever is left, called CWIFI other.

Each channel is carved into contiguous districts of roughly equal opportunity, target about $1B
each, floor $800MM. The channels are designed in priority order: national first (the channel and
data used so far), then WH, then FI, then other. The difficulty comes from the existing
wholesalers and their current territories, and from staffing them in a weakly optimal sense:
every wholesaler serves at most one district in one channel, and every district has one
wholesaler.

Example. Arizona has $836MM of CWIFI opportunity: national $541MM, WH $152MM, FI $143MM. Three
options:

- keep three channels, each (Arizona, channel) pair grouped with other states' same-channel
  pairs to reach $800MM;
- merge WH and FI into one channel, national kept;
- keep WH and FI and drop national, its opportunity going back to the two firms' home channels.

Which is right depends on the candidate wholesalers with sales in Arizona across channels, and
on what every other state decides. **The decision that is new is the channel structure per
state.** Everything else is the one-channel problem, repeated.

## 2. Cells and data

Zips `Z` (CONUS, 3,713), state `s(z)`, the proximity graph on `Z` (`proximity_edges`, the rook
graph of the Voronoi cells, CLAUDE.md trap 23), and the state rook graph `G_S` (49 nodes, 107
edges, `td/geo.state_rook`, `td/geo.py:243-267`).

Channels in the file: `{national, wh, fi}`, where national is itself the sum of three
sub-channels the business runs, National (Chase), Wells (WH) and Wells (FI) (the user,
2026-09-11). The fine labels `C = {N_WH, N_FI, WH, FI}` are accounting only, and they are exact
when the file carries the sub-channels (`national_chase`, `national_wells_wh`,
`national_wells_fi`, matched in any letter case, `meta["channel_groups"]`):

    N_WH(z) = Wells WH(z),    N_FI(z) = Chase(z) + Wells FI(z),    N(z) = N_WH(z) + N_FI(z)

applied alike to mass, every rep book and the filler (`td/channels.py::fine_split`). A file that
carries national as one row keeps the proxy `N_WH(z) = N(z) · WH(z) / (WH(z) + FI(z))` with the
fallback of decision 3, and `params.json` says which rule fired (`meta["fine_split"]`). The
split lets "drop national" mean "give N_WH to WH and N_FI to FI" with no loss: only Wells (WH)
folds into WH; Chase and Wells (FI) fold into FI.

A cell is a pair `(z, c)`. It carries mass `M_{z,c}`, a book `S_i(z,c)` per rep `i`, filler
`S_free(z,c)`, and `T_{z,c} = Σ_i S_i(z,c)`. Every quantity the utility reads is additive over
cells; that is the fact §4 rests on.

Units. The file is descaled: `m_rel` is `M` in units of κ, one κ for the whole file, pinned to the
median positive `M` of the national data, so the national `m_rel`, the target `τ = 471.21` and
`k = 18` carry over unchanged from `instance_descaled_v2_conus.json.gz` (3,713 zips, 113 reps,
mass 8,481.8). In this file τ is $1B in descaled units; `L = 0.8τ`, `U = 1.2τ`.

Exporter and loader. Nodes keyed by `(zip, channel)` with a `channel` column, format
`td_instance_descaled/2` (`FORMAT` at `td/instance.py:50`, loader 80-127); rep surrogate ids
assigned once over the whole file and mapped to the v2 ids; both the sales and the opportunity
tables carry a channel column (assumed per zip); graph, states and geo unchanged; a format-1
file loads as the one channel `national`. Until the real file lands, a deterministic synthetic
split of the v2 CONUS instance stands in: fractions from a hash of `seed:zip` via hashlib, never
`hash()`, the same fractions applied to `M`, every `S_i` and `S_free` at a zip so per-cell
headroom holds exactly.

## 3. Districts, bundles, plans, and the joint problem F

A served channel is a bundle, a set `B ⊆ C`. The allowed family `𝔅`, each member on a switch:

    N = {N_WH, N_FI}      WH = {WH}      FI = {FI}
    WH⁺ = {WH, N_WH}      FI⁺ = {FI, N_FI}      WHFI = {WH, FI}
    WHFI⁺ = {WH, FI, N_WH, N_FI}      (off by default, ★B)

A channel plan `π(z)` is a set of pairwise disjoint bundles covering part of `C`. The three
business options of §1 are `{N, WH, FI}`, `{N, WHFI}` and `{WH⁺, FI⁺}`. Cells of channels
outside `∪π(z)` are the residual, "other".

A district is `j = (A_j, B_j)` with `B_j ∈ 𝔅`, `A_j ⊆ Z_B = {z : B ∈ π(z)}`, and `A_j` connected
in the proximity graph induced on `Z_B`. It owns the cells `A_j × B_j`: every zip in the district
carries every channel of the bundle (product form). Within a bundle the districts partition
`Z_B`: a zip that names `B` in its plan lies in exactly one B-district. Across bundles a cell
belongs to at most one district, since the bundles of `π(z)` are disjoint. So cover reads "≤ 1"
per cell and "= 1" per zip inside a bundle, the two views of one condition.

    cover:      each cell in at most one district; uncovered = other
    band:       L ≤ M_j = Σ_{z∈A_j} Σ_{c∈B_j} M_{z,c} ≤ U
    reps:       σ injective from districts to reps, every district staffed
    gain:       g_i(j) = Σ_{z∈A_j} Σ_{c∈B_j} u_i(z,c),
                u_i(z,c) = c1·S_i(z,c) + c2·(T_{z,c} − S_i(z,c)) + c_free·S_free(z,c) + λ·M_{z,c}
    objective:  max Σ_j log g_{σ(j)}(j)        (Nash over reps, stage 2 as today)

with `c1 = 1 − λ`, `c2 = θ(1 − λ)`, `c_free ∈ {c2, c1, λ}` by `filler_capture`
(`td/model.py:135,146-149`, duplicated at `td/channel.py:268-271`), θ = 0.40, λ = 0.30.

F is today's problem with `Z` replaced by `Z × C` and a bundle on each district. The two-stage
business constraint stays: the draw sees masses only, reps enter at stage 2
(`docs/PROBLEM.md`, trap 17 on the lack of a cited basis for it).

## 4. Decomposition

**Proposition (VERIFIED 2026-09-10 by math-verify, `tools/verify/U14-fullprob/REPORT.md`).** Fix a channel plan
π and, for each bundle `B` in use, a district count `k_B`. Write, for `z ∈ Z_B` (with
`M^B_z > 0`, the hypothesis of Lemma 6),

    M^B_z = Σ_{c∈B} M_{z,c},   S^B_i(z) = Σ_{c∈B} S_i(z,c),
    T^B_z = Σ_{c∈B} T_{z,c},   S^B_free(z) = Σ_{c∈B} S_free(z,c).

Then:

(a) for every `filler_capture`, `u^B_i(z) := Σ_{c∈B} u_i(z,c)` equals the single-channel utility
    of `docs/MODEL.md` §1 evaluated on `(S^B_i(z), T^B_z, S^B_free(z), M^B_z)`;
(b) the stage-1 problem, `max Σ_B Σ_{j∈J_B} log M_j` under band and contiguity, is separable by
    bundle, each summand being today's problem on `(Z_B, M^B)` with the proximity graph induced
    on `Z_B`, and Lemma 6 (`docs/MODEL.md` §8.2) holds for each summand;
(c) the only constraint coupling bundles is the rep injection σ, and stage 2 over the union of
    all districts is one linear assignment, `channel.match` (`td/channel.py:288-312`);
(d) a per-channel floor on a merged district (`L_WH ≤ Σ_{z∈A_j} M_{z,WH}` beside the band on
    `M_j`) breaks the transportation structure of Lemma 6.

*Proof.* (a) `u_i(z,c)` is linear in `(S_i(z,c), T_{z,c}, S_free(z,c), M_{z,c})` with coefficients
`(c1 − c2, c2, c_free, λ)` that depend on `(θ, λ, filler_capture)` only, never on the cell. A sum of linear forms with the same coefficients is the same linear form of the summed
arguments, so `Σ_{c∈B} u_i(z,c) = c1·S^B_i + c2·(T^B − S^B_i) + c_free·S^B_free + λ·M^B`, and
`T^B_z = Σ_i S^B_i(z)` because the sum over reps and the sum over channels commute. The three
`c_free` cases are three constants; none depends on `c`.

(b) With π fixed, `Z_B` is fixed and every constraint of F other than reps names one bundle's
variables only: the band reads `M_j` of a district of `B_j`, the cover row of a zip in `Z_B`
is `Σ_{j∈J_B} y_{zj} = 1` (§3, partition within a bundle), and contiguity is connectivity in
the graph induced on `Z_B`, which is decision 6 exactly: a zip outside `Z_B` cannot bridge two
B-districts. The objective is a sum over bundles. A maximisation of a sum of functions of
disjoint variable sets under constraints that each mention one set is the sum of the separate
maxima. Each summand is `max Σ_{j∈J_B} log M_j` on `(Z_B, M^B)` with `k_B` districts, one
scalar mass per district; that is `docs/MODEL.md` §8.1 with `Z` renamed, and Lemma 6's
substitution `η_{zj} = M^B_z y_{zj}` gives the Hitchcock structure unchanged, so at most
`k_B − 1` split zips per bundle. No field that level 1 (`td/solvers/state_splits.py`), level 2
or `channel.gain_matrix` reads names a channel, so the projected instance
`(Z_B, M^B, S^B, S^B_free)` is a format-1 instance to them and they run on it as they run on
the national instance today.

(c) σ is one injection from the set of all districts, across bundles, into the reps, and
`log g_{σ(j)}(j)` is additive over the selected pairs with `g_i(j) = Σ_{z∈A_j} u^B_i(z)` by (a).
That is Proposition 5 of `docs/MODEL.md` §9 with the district list the union over bundles:
maximum-weight bipartite matching with weights `log g_i(j)`, one Hungarian. `channel.match`
raises when some `g ≤ 0`; whether the pool is large enough (reps < districts leaves districts
unstaffed as built) is ★C.

(d) A per-channel floor adds a second mass row per merged district: `Σ_z M_{z,WH} y_{zj} ≥ L_WH`
next to the band on `Σ_z M^B_z y_{zj}`. The substitution `η_{zj} = M^B_z y_{zj}` no longer makes
the constraint matrix a node-arc incidence matrix of a bipartite network, because the second row
has coefficients `M_{z,WH} / M^B_z` that vary by zip. The acyclic-support argument and the
`k_B − 1` split count go with it; this is the Ríos-Mercado warning quoted at
`docs/MODEL.md:446-450`, two balancing attributes. ∎

Consequence. One projection tool (`td/channels.py` `project(d, B)`) and no new zip-level solver.
A merged WHFI district is balanced on its bundle mass only.

## 5. Level 0: the plan at state × channel granularity

Level 0 chooses `π` and the state-level shape of the districts at once, on cells `(s, c)`,
49 × 4 = 196. Slots `j ∈ J_B` per bundle, `K_B = ⌈M^max_B / L⌉` with `M^max_B` all mass the
bundle could ever hold; the bundle is fixed per slot, so there are no bundle binaries.
`W_{s,j} = Σ_{c∈B_j} M_{s,c}` is the mass state `s` brings to slot `j`.

    y_{s,j} ∈ [0,1]    share of s in slot j (all channels of B_j alike)
    z_{s,j} ∈ {0,1}    contact,  η z ≤ y ≤ z ≤ u_j
    u_j ∈ {0,1}        slot used
    cover:   Σ_{j : c∈B_j} y_{s,j} ≤ 1 − prior_{s,c}      ∀ (s,c)
    band:    L u_j ≤ Σ_s W_{s,j} y_{s,j} ≤ U u_j          ∀ j
    flow:    single-commodity flow per slot as level 1, root Σ_s r_{s,j} = u_j
    order:   u_j ≥ u_{j+1}, mass_j ≥ mass_{j+1} inside each J_B (symmetry)
    residual mass per (s,c) reported as other

`prior_{s,c}` is coverage fixed by an earlier pass (route S) or a prior plan. A state's share
`y_{s,j}` splits every channel of the bundle in the same proportion; level 2 decides which zips.

Mapping onto `td/solvers/state_splits.py` (each row a reuse or a replacement):

- `SplitProblem` (94-130, blocks z, y, r, f row-major in (s, j)) becomes
  `Level0Problem(SplitProblem)` with `k = K_total`, new fields `off_u`, `W (S,K)`, `bundle_of`,
  `slots {B: (start, stop)}`, `L`, `U`, `cover_ub (S,C)`, `prior`. Layout stays four blocks
  plus `u`.
- place `Σ_j y_sj = 1` (231) becomes cover per cell `Σ_{j: c∈B_j} y_sj ≤ cover_ub[s,c]`.
- `yz` (233) and `yz_lo` η (238) unchanged; add `z_sj ≤ u_j`.
- band (244) becomes two rows per slot, `Σ_s (W_sj/τ) y_sj − (L/τ) u_j ≥ 0` and
  `… − (U/τ) u_j ≤ 0`.
- root (247) becomes `Σ_s r_sj − u_j = 0`; flow rows (254-273) copied with `k → K`.
- caps (275-280) become `Σ_s z_sj ≤ n_max` per slot and `z_sj + z_s'j ≤ 1` when the centroid
  distance exceeds Δ (route G).
- anchors and `bound_z` (139-157, 285-288) kept; `forbid_bundle(problem, s, bundle)` added.
- decode (735-747, duplicated at `milp_engines.py:119-136`) moves into `SplitProblem.decode_zy`;
  `Level0Problem.decode_zy` returns slot masses `(W·y).sum(0)`, `used`, per-channel `covered`,
  `contacts`, and `splits = Σ z − n_state` so `with_cutoff`'s row reads "fewer contacts".
- `eps_lexicographic` (756-770) on `W` and `D (S,K)`, `D` zero when no centres; `balance_pass`
  (822-841) generalised to `solve_passes`: set `problem.c`, solve warm-started, pin with
  `append_row`, record `certified = (status == 0)`.

Size. At about 95 slots (`Σ_B K_B ≤ ⌈4·18/0.8⌉ + 7`) about 34k variables, 9.4k binaries, 60k
rows; at 150 slots 54k / 15k / 101k. Today at k = 18: 6,498 / 1,764 / 11,317, certified in 49 s
under the portfolio. Slot count is the lever; the driver prints it before solving.
`build_level0` raises when `U` is None: without an upper band the coverage passes build one giant
district per bundle and balance is undefined.

## 6. Routes

Two readings of "priority order", two merge drivers, four drivers over one model.

Priority reading.

- S, sequential: level 0 with slots for N only, fix the result as `prior`, then WH and WH⁺ on
  what remains, then FI, FI⁺, WHFI, WHFI⁺. Three solves of a third the size. Regression
  anchor: N alone with cover forced to 1, band 1 ± 0.05, `K_N = 18` all used, anchors from the
  committed homes and `D` from the committed centres must reproduce today's 8 splits (CA 5
  districts, NY 3, TX 2, FL 2).
- J, lexicographic joint: one model, passes in the `balance_pass` pattern (solve, pin the value
  with a row at `v(1+1e-9)+1e-12`, next objective): cover_N (pure national slots only, decision
  8), cover_WH (WH and WH⁺ slots), cover_FI (FI and FI⁺), cover_merged (WHFI, and WHFI⁺ when enabled: pure channels first, merged for what pure cannot serve), contacts (minimum splits, `c = 1` on
  z), then a compactness tie-break `ε·W·D` with `D` from a projected stage-1 draw when there is
  one, else contacts only. A timed-out pass pins its incumbent and records `certified = false`.
  The portfolio strategy of `tools/state_splits.py` (484-706) is reusable only for the contacts
  pass (unit cost on z); coverage passes run direct.

Merge driver. Under band and contiguity alone a sparse pure district is always feasible, so a
priority objective never merges anything on its own; something has to pay for a merge.

- R, rep books: level 0 generates; per-state moves {keep three, merge WH+FI, drop N} in priority
  order, each a `forbid_bundle` bound set, scored by the state-level stage-2 Nash value (one
  Hungarian on aggregated cells, `td/stage2_state.py`). A move changes contacts, so it cannot be
  scored with z fixed (the forbid bound collides with `η z ≤ y`); each move is a neighbourhood
  MILP, z fixed on every slot touching neither the moved state nor its rook neighbours,
  warm-started from the incumbent. The score is exact on whole states and a mass-proportional
  approximation on split ones. No rep term inside the MILP: it is bilinear, refused for the
  reason the project refused a joint draw-and-match.
- G, geographic: `Σ_s z_{s,j} ≤ n_max` per slot and/or `z_{s,j} + z_{s',j} ≤ 1` when the state
  centroid distance exceeds Δ. Linear and centre-free. R selects among the `(n_max, Δ)` grid.

Catch-all pass, both routes, last: one bundle over the residual cells, districted where the band
allows; what it cannot cover stays unserved. "Four channels" then has a definition: the
catch-all pass used at least one slot.

Zip-level realisation runs once for the chosen plan: project per bundle, level 2 with a residual
pseudo-column for uncovered mass (so `realise` does not raise on a state touching no district,
`state_splits.py:945-946`, and `centers.assign`'s target sum stays exact), then one global
stage 2.

## 7. What exists, what is new

Reused unchanged or by subclass: `SplitProblem`, `_block` (133-136), the flow rows, the η rows,
`bound_z`, anchors, `with_cutoff`, `fix_roots`, `_clone` (152-196), the engine seam (`_highs_lp`
358-378, `_scip_solve` 468-506), the `balance_pass` pattern, `eps_lexicographic`, the
`channel.gain_matrix` formula (`td/channel.py:252-285`), `channel.match`, `ss.realise`, the
driver shell of `tools/state_splits.py` (`_main`, `Timings`, `params.json` 581-600,
`_write_failure` 447-464 with the key contract at `tests/test_state_splits_cli.py:78-96`).

New: the v2 loader (`td/instance.py`, `FORMAT_V2 = "td_instance_descaled/2"`, node attrs `M_c`,
`S_c`, `S_free_c` beside today's totals, `Descaled.channels`) and exporter
(`tools/instance_export/export_instance.py`, `channel` beside the columns at 167-172, sales join
keyed on `(z, rep, channel)`, κ pinned to the national median, `--rep-ids` map); `td/channels.py`
(`CHANNELS`, `BUNDLES`, `fine_split`, `CellTable`, `aggregate`, `slot_weights`, `project`,
`synthesize_channels`, `write_v1`, `write_v2`); `td/stage2_state.py` (`Slot`, `Plan`,
`state_utilities`, `state_gain_matrix`, `state_stage2` in the shape of `channel.stage2`);
`td/solvers/level0.py` (`Level0Problem`, `build_level0`, `Pass`, `append_row`, `solve_passes`,
`forbid_bundle`); `tools/full_plan.py` (`--route {sequential,joint}`, `--driver {reps,geo}`,
`--catch-all`, `--k`, `--band-lo 0.8 --band-hi 1.2`, `--bundles`, `--priority N,WH,FI`,
`--eta`, `--n-max`, `--dist-max`, `--prior`, `--centers`, `--incumbency`, model and engine
flags, `--synthesize`, `--out`; writes `params.json`, `plan.json`, `staffing.json`,
`timings.json`, `failure.json` on `SolveFailure`, and `projections/<bundle>/`); six test modules.

One small refactor: `model.coefficients(theta, lam, filler_capture) -> (c1, c2, c_free)` replaces
the duplicated block in `td/model.py:146-149` and `td/channel.py:268-271`.

The app (`app/`) is untouched until solve times are known; it never imports `td` and nothing in
it keys on a channel today (`app/store.py:41-45`).

## 8. Assumptions and ★ decisions

Settled: `U = 1.2τ`; route G is an extent cap (states per district, centroid distance); cover_N
counts pure national slots only; catch-all on; the fine split exact from the three national
sub-channels (decision 12), the ratio `N_WH : N_FI = WH : FI` at the zip only for a file without
them (decision 3); product form (a district carries every channel of its bundle
on every zip); the draw sees masses only and reps enter at stage 2; a merged district is balanced
on bundle mass alone (§4 (d)).

Assumed until the real file lands: the synthetic channel split of the v2 CONUS instance stands in
for the data, with per-cell headroom exact by construction; the sales and opportunity channel
columns are per zip.

Open:

- ★B WHFI⁺ off by default; `{N, WH}` is not a bundle.
- ★C rep pool size against 48 to 60 districts, and whether reps carry a channel tag. Stage 2 as
  built leaves districts unstaffed when reps < districts (`channel.match` is rectangular the
  other way).
- ★D η (the smallest share a contact may carry) and the centre-free tie-break when no stage-1
  draw exists for a bundle.
- ★E a state may split geographically across plans: level 0 allows it; per-state purity is one
  binary per state if refused.
- Route S versus J, from the timing table (§9).

## 9. Numbers to compute first

1. `K_B` per bundle and the total slot count on the synthetic instance; the driver prints it
   before solving.
2. One level-0 solve time per route on the synthetic CONUS instance (joint route, geo driver,
   600 s per pass, threads 2, portfolio on the contacts pass only), logs under
   `tools/verify/U14-fullprob/`.
3. The route-S regression against today's 8 splits under today's four settings (band ±5%,
   `K_N = 18`, committed anchors and centres).
4. Residual mass per `(s, c)` under each route, and whether the catch-all pass uses a slot.
5. The `math-verify` verdict on §4 (`tools/verify/U14-fullprob/`), which updates the
   proposition's status line.
