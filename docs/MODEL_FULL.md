# The full optimisation model, line by line

Status: drafted 2026-09-11 from the code as it runs on the track `full-problem`
(`td/solvers/level0.py`, `tools/full_plan.py`, `td/solvers/centers.py`,
`td/solvers/state_splits.py`, `tools/plan_realise.py`, `td/channel.py`). `docs/FULL_PROBLEM.md`
carries the derivation and the decisions; this file carries the mathematics only, one line
per relation with what it says. Every model here is a MILP or an LP; the only nonlinearity is
the logarithm in the staffing objective, which the assignment solver handles exactly, and the
one place a bilinear term would appear (a rep term inside the plan MILP) was refused and is
listed at the end.

The problem is solved in three levels, the output of each fixing the input of the next:

1. Level 0, the plan: which channels each state serves in which kind of district, at
   state times channel grain (a MILP, solved lexicographically pass by pass).
2. Level 2, the realisation: which zips belong to which district (a transportation LP per
   split state, then a contiguity repair on the cell graph).
3. Stage 2, the staffing: which wholesaler runs which district (a maximum-weight assignment
   on log gains).

## 1. Sets and indices

```
s ∈ S                 states (49 on CONUS); the rook graph G_S = (S, E_S), E_S the pairs sharing a border
c ∈ C                 fine channels, C = {N_WH, N_FI, WH, FI}; national = N_WH + N_FI
B ∈ 𝔅                 bundles, each a set of fine channels a single district may hold:
                        N = {N_WH, N_FI}, WH = {WH}, FI = {FI}, WH_PLUS = {WH, N_WH},
                        FI_PLUS = {FI, N_FI}, WHFI = {WH, FI}, WHFI_PLUS = C
j ∈ J_B, J = ∪_B J_B  slots: candidate districts, K_B per bundle, bundle B_j fixed per slot
a ∈ A_S               arcs: both directions of every edge of E_S
z ∈ Z                 zips (6,459 on the v3 CONUS file); s(z) its state
i ∈ R                 wholesalers (reps)
```

## 2. Data

```
M_{s,c}   ≥ 0        opportunity mass of state s in fine channel c (from the per-zip cells, summed)
M_{z,c}   ≥ 0        opportunity mass of zip z in fine channel c
W_{s,j}   = Σ_{c∈B_j} M_{s,c}      the mass slot j would take from state s at full share
τ_B                   target mass per district of bundle B: the bundle's total mass over its count K_B
L_B, U_B              band floor and ceiling per bundle, L_B = (1 − δ) τ_B, U_B = (1 + δ) τ_B, δ = 0.10
η        = 0.05       the smallest share of a state a district may hold (a contact is at least η)
n_max    = 6          the most states one district may touch
d_max    = 900 km     the farthest two state centroids in one district may sit
x_s                   state centroid coordinates; d(s,s') their distance
p_{s,c}  ∈ [0,1]      prior: the share of cell (s,c) already committed by an earlier stage (route S)
cap_s                 split cap: the most slots of one stage that may touch state s (CA 3, TX 2, NY 3)
a_s      ≥ 0          band-break allowance for a capped state, a_s = max(0, W_s / cap_s − τ_B)
S_i(z,c) ≥ 0          rep i's book (sales) in cell (z,c);  T_{z,c} = Σ_i S_i(z,c)
S_free(z,c)           unowned book in the cell (a vacancy's sales, no rep)
θ = 0.40, λ = 0.30    capture rate of another rep's book, and weight on opportunity
c1 = 1 − λ, c2 = θ (1 − λ), c_free ∈ {c2, c1, λ}   utility coefficients (filler_capture theta | full | opportunity)
N = |S|               the big-M for the flow rows (a tree over at most N states)
```

## 3. Level 0: the plan MILP

### 3.1 Variables

```
y_{s,j} ∈ [0,1]       share of state s held by slot j, the same share on every channel of B_j (product form)
z_{s,j} ∈ {0,1}       contact: slot j holds a positive share of state s
u_j     ∈ {0,1}       slot j is used (a district exists)
r_{s,j} ∈ {0,1}       state s is the root of slot j's contiguity tree
f_{a,j} ∈ [0, N−1]    flow on arc a for slot j (one commodity per slot, tree-shaped)
```

### 3.2 Rows (every row named as in `problem.rows`)

```
cover     Σ_{j : c ∈ B_j} y_{s,j} ≤ 1 − p_{s,c}                       ∀ s, c     a cell is held at most once, less what an earlier stage took; the gap is residual
yz        y_{s,j} ≤ z_{s,j}                                          ∀ s, j     no share without a contact
yz_lo     η z_{s,j} ≤ y_{s,j}                                        ∀ s, j     a contact is at least η of the state
zu        z_{s,j} ≤ u_j                                              ∀ s, j     an unused slot touches nothing
band_lo   Σ_s W_{s,j} y_{s,j} ≥ L_{B_j} u_j                          ∀ j        a used district holds at least its bundle's floor
band_hi   Σ_s W_{s,j} y_{s,j} ≤ U_{B_j} u_j + Σ_{s capped} a_s z_{s,j}   ∀ j    ... and at most its ceiling, raised by a_s for each capped state it touches (band break; a_s = 0 without --band-break)
root      Σ_s r_{s,j} = u_j                                          ∀ j        a used slot has exactly one root
rz        r_{s,j} ≤ z_{s,j}                                          ∀ s, j     the root is a contact
flow_tail f_{a,j} ≤ (N−1) z_{tail(a),j}                              ∀ a, j     flow leaves only a contacted state
flow_head f_{a,j} ≤ (N−1) z_{head(a),j}                              ∀ a, j     flow enters only a contacted state
net       z_{s,j} − N r_{s,j} ≤ Σ_{a into s} f_{a,j} − Σ_{a out of s} f_{a,j}   ∀ s, j   every non-root contact absorbs one unit of flow: the contacts of a slot form one connected piece of G_S
cap_n     Σ_s z_{s,j} ≤ n_max                                        ∀ j        at most n_max states per district
cap_dist  z_{s,j} + z_{s',j} ≤ 1                       ∀ j, ∀ (s,s') with d(s,s') > d_max   two far states never share a district
serve     Σ_j z_{s,j} ≥ 1                               ∀ s named by --serve-all-states    a named state is in some district
max_splits  Σ_j z_{s,j} ≤ cap_s                         ∀ s named by --max-splits          a capped state is cut between at most cap_s districts of this stage
plus_pair   Σ_{j∈J_WH_PLUS} y_{s,j} = Σ_{j∈J_FI_PLUS} y_{s,j}   ∀ s   national is dropped on both halves equally (route S: the FI stage takes the WH stage's fold as a constant target)
order_u   u_{j+1} ≤ u_j                                 ∀ consecutive j in one J_B          symmetry: slots of a bundle are used in index order
order_mass  Σ_s W_{s,j+1} y_{s,j+1} ≤ Σ_s W_{s,j} y_{s,j}   ∀ consecutive j in one J_B   symmetry: and in descending mass (off when anchors or per-slot moments name the slots)
```

Bounds that stand in for rows:

```
z_{s,j} = 1                    anchors: a contact committed before the solve (the greedy warm start's seeds, or a committed map)
z_{s,j} = y_{s,j} = 0          a state farther than the radius cap from a rooted slot's root, or every state of a closed slot
u_j = 1  /  u_j = 0            fixed_used: the first K_B^fixed slots of a bundle must be used; max_used: the rest may not be
```

### 3.3 Objectives, solved lexicographically

Each pass optimises one linear objective, then pins its value with one appended row
(`pin_<pass>`: objective ≤ v + |v| (slack + 10⁻⁹) + 10⁻¹²) before the next pass runs. In
order:

```
cover_B     max Σ_{j ∈ J_B} Σ_s W_{s,j} y_{s,j}     for the stage's pure bundle B          most mass served by pure districts of the priority channel (N, then WH, then FI)
cover_merged  max Σ_{j ∈ J_WHFI ∪ J_WHFI_PLUS} Σ_s W_{s,j} y_{s,j}                        then most mass served by merged districts, only where the pure ones could not
contacts    min Σ_{s,j} z_{s,j}                                                             fewest state contacts: fewest split states and smallest districts
compactness min Σ_{s,j} ε W_{s,j} D_{s,j} y_{s,j}                                          tie-break: mass-weighted second moment about each slot's seed, ε small enough never to trade a contact
```

A pass that hits the time limit pins its incumbent and is recorded as uncertified. Route S
runs the model three times, once per stage (N; WH and WH_PLUS; FI, FI_PLUS, WHFI,
WHFI_PLUS), each stage's cover passing to the next as the prior p. Route J runs one model
over all seven bundles with the four cover passes in the order above.

### 3.4 Passes around the stages

```
other_first   before the N stage: WHFI_PLUS slots over the named states (MT, WA, WY) with floor L = 0.5 τ   a state no channel can serve alone gets one all-channel district first
catch-all     after the FI stage: one slot per fine channel over the residual, floor 0.5 τ      what is left and reaches half a book becomes a district
sweep         after the catch-all: every residual cell (s, c) joins an adjacent used slot whose bundle's channels are all residual in s, the slot ending least over U_B; caps kept when any candidate allows, else broken and recorded   all opportunity covered
```

The sweep is a deterministic post-pass, not a solve: for state s with residual channel set
R_s, candidates are used slots j with B_j ⊆ R_s and either y_{s,j} > 0 or a contact on a
rook neighbour of s; the share added is min_{c ∈ B_j} r_{s,c}; the winner minimises
(mass_j after) − U_{B_j}; states are processed by descending residual mass and the pass
repeats until nothing moves.

## 4. Level 2: zips into districts

Level 0 hands each bundle a projected instance (its zips, its channels' masses summed per
zip) and the plan's shares. An unsplit state goes whole to its one district. A split state
s (two or more slots with y_{s,j} > 0, plus the pseudo-district `other` carrying the
residual share) is cut by the transportation LP below, with the district centres
c_j initialised from the slot's seed states and moved by up to five Lloyd rounds (a round is
kept only if the state's compactness cost does not rise).

```
variables   x_{z,j} ∈ [0,1]                              fraction of zip z in district j (integral at every vertex but the k − 1 split zips)
objective   min Σ_{z ∈ s} Σ_j M_z (‖p_z − c_j‖² + π_{z,j}) x_{z,j}      mass-weighted squared distance to the centre: the cut is a power diagram of the centres
place       Σ_j x_{z,j} = 1                              ∀ z ∈ s        every zip is placed once
mass        Σ_{z ∈ s} M_z x_{z,j} = y_{s,j} M_s          ∀ j            each district takes exactly the share the plan gave it of the state (a band of ± b around it under --band)
```

Then, per bundle, on the cell graph G_cell (the rook graph of the per-state Voronoi cells of
the zip points, clipped to land), the repair: free every zip a district holds outside the
states the plan admits it in, and every piece but the heaviest of a district in several
pieces; grow each freed zip back onto the neighbouring admissible district with the most
cell edges into it, refusing a move that raises either district's distance outside
[L_B − σ, U_B + σ] (σ = 0.02 τ_B); then bridge a whole remaining piece to a neighbour and pay
the mass back with zips next to the piece's own body. Before the repair, a losing bundle's
detached pieces in a state it lost the overlap on go to the winning bundle's district there.
After all bundles, `--sweep-zips` gives every still-unclaimed cell (z, c) to a district
serving c in s(z) that is adjacent to z on that district's cell graph, else to the one holding
the most cells of (s(z), c).

The repair and the sweeps are heuristics with a stated guard, not optimisations; the
realiser records every move and every district still in pieces with its reason.

## 5. Stage 2: staffing

```
g_{i,j}   = Σ_{z ∈ A_j} Σ_{c ∈ B_j} [ c1 S_i(z,c) + c2 (T_{z,c} − S_i(z,c)) + c_free S_free(z,c) + λ M_{z,c} ]    rep i's gain from running district j: its own book kept at c1, others' book captured at c2, vacancies at c_free, opportunity at λ
variables   w_{i,j} ∈ {0,1}                              rep i runs district j
objective   max Σ_{i,j} log(g_{i,j}) w_{i,j}             Nash welfare over the staffed districts (utilitarian: Σ g w)
one_rep     Σ_i w_{i,j} ≤ 1                              ∀ j            one wholesaler per district
one_dist    Σ_j w_{i,j} ≤ 1                              ∀ i            one district per wholesaler
staffed     Σ_j Σ_i w_{i,j} = min(|R|, |J_used|)                        every district is staffed while reps last
```

A rectangular assignment problem, solved exactly by the Hungarian method on the matrix
log g. Reps are candidates for every district (no legacy candidacy); reps left over are
idle, districts left over are unstaffed.

## 6. What is not in the model, and why

- A rep term inside level 0 (score a plan by its staffing while planning) is bilinear
  (y_{s,j} times w_{i,j}) and was refused for the same reason the single-channel work refused
  a joint draw-and-match; route R scores per-state moves by re-solving stage 2 outside the
  MILP instead.
- Per-channel floors inside a merged district would be a second balancing attribute and
  break the transportation structure of level 2; a merged district is banded on its total.
- Contiguity at level 2 is enforced by repair on the cell graph, not by rows in the LP; the
  power diagram is not contiguity-aware, which is what the contiguous split-state cut on the
  branch `worktree-contig-cut` is testing.
