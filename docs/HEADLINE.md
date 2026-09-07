# The headline map, end to end

The shipped path only: from the v2 instance to the committed k = 18 draw, and from that draw to
the Track 2 anchored δ = 5% map in `figures/borders_track2_anchored_d05_voronoi.png`. Every
program is written in the notation of `docs/MODEL.md` §7, every number carries its
base, and every step names its code, its verification and its run directory. Alternatives that
were built and not shipped (Track 1, the state-atom engine, the free MILP) are not described
here; `STATE.md` `## Facts` holds their grids and `docs/units/state_borders.md` the model behind
them.

| symbol | meaning | on this run |
|---|---|---|
| $Z$, $n$ | zips; $M_z \ge 0$ the opportunity at $z$; $q_z \in \mathbb{R}^2$ its internal point, equal-area projection | 3,748 zips; 3,707 with a coordinate; 3,704 of those in the lower 48 plus DC |
| $k$, $\tau$ | districts; $\tau = M(Z)/k$ the equal split | $k = 18$; $\tau = 473.513$ on the whole instance, $470.459$ on the level-1 ground set |
| $S$, $s$ | the level-1 units: the lower 48 states and DC; $M_s = \sum_{z \in s} M_z$ | $S = 49$, $\sum_s M_s = 8{,}468.3$ |
| $G_S = (S, E_S)$ | the state rook graph from the TIGER 1:20m polygons | 107 edges; Four Corners point contacts excluded |
| $c_j$ | the committed draw's centres: the $M$-weighted centroids of its 18 districts | fixed after stage 1 |
| $\mathrm{home}(j)$ | the state holding the plurality of district $j$'s mass in the committed draw | NY, CA, TX, NY, PA, CO, FL, NC, MI, CA, IL, NJ, MO, CA, FL, TX, CA, CA for D01 to D18 |
| $g_j$ | district $j$'s mass under a labelling | |
| $\delta$, $\eta$, $\varepsilon$ | the balance band; the least share a touched state must send; the compactness tie-break weight | $0.05$, $0.01$, $4.41 \times 10^{-18}$ |

Descaled units throughout, no currency scale. A "nat" is a unit of $\sum_j \log g_j$.

## 0. The instance

`instance_descaled_v2.json.gz`, the descaled export of the real channel (`docs/DATA.md`).
3,748 zips, 114 representatives, total opportunity 8,523.2. Node classes by candidacy
$\mathrm{cand}(z) = \{i : S_i(z) > 0\}$: 718 contested, 1,447 uncontested, 16 vacant (filler book
only), 1,567 untapped (no book; 15.7% of opportunity). Stage 1 sees only $(z, M_z, q_z)$; the
books enter at stage 2.

Three ground sets recur and must not be mixed. The whole instance (3,748 zips, $\tau = 473.513$)
is what the final map is measured on. The geometric set (3,707 zips with a gazetteer coordinate)
is what stage 1 solves on. The level-1 ground set (49 units, mass 8,468.3, $\tau = 470.459$) is
the lower 48 plus DC; the 3 zips in AK and HI and the 32 zips of unknown state (0.07τ together)
sit outside it and are placed at completion.

The utility model behind stage 2 (`docs/PROBLEM.md` §2, the welfare decomposition): for
representative $i$ at zip $z$,

$$u_i(z) = c_1 S_i(z) + c_2\big(T_z - S_i(z)\big) + c_{\mathrm{free}} S_{\mathrm{free}}(z) + \lambda M_z,
\qquad c_1 = 1 - \lambda,\ c_2 = \theta(1 - \lambda),$$

with transfer capture $\theta = 0.4$, headroom credit $\lambda = 0.3$, and $c_{\mathrm{free}} = c_2$
(`filler_capture = theta`). These are the weights the committed draw was staffed under, and the
headline map is staffed under the same ones so the two stage-2 values compare.

## 1. Stage 1: the committed draw

### 1.1 The objective, and why balance is the constraint

Stage 1 asks for $k$ districts maximising Nash welfare on the common measure $M$:

$$\max_{A_1, \dots, A_k} \sum_{j=1}^{k} \log M(A_j).$$

Proposition 2 of the channel note (Jensen, or AM–GM) gives $\sum_j \log M(A_j) \le k \log(M(Z)/k)$
with equality iff every district has mass exactly $\tau$. So on a common measure the Nash
objective *is* balance, and the design follows: equal mass is the hard constraint, compactness is
the tie-break among balanced maps. Contiguity is not imposed: the v2 zip adjacency graph has 862
components over 3,748 zips (516 singletons), so a contiguity constraint on zips is vacuous.

### 1.2 The program

Centre-based balanced assignment, Hess's formulation, solved as an alternating scheme whose inner
step is a linear program (`docs/MODEL.md` §8, and §8.2 for the transportation-relaxation lemma):

$$\begin{array}{llll}
\textbf{inner, } c \text{ fixed:} & \displaystyle\min_{x} \sum_{z}\sum_{j} M_z \lVert q_z - c_j \rVert^2 x_{zj} \\[6pt]
\text{s.t.} & \displaystyle\sum_j x_{zj} = 1 & \forall z & \text{(every zip placed)}\\[4pt]
 & \displaystyle\sum_z M_z x_{zj} = \tau & \forall j & \text{(equal mass, hard)}\\[4pt]
 & x_{zj} \ge 0 & & \text{(integrality dropped)}\\[6pt]
\textbf{outer:} & c_j \leftarrow \displaystyle\sum_z M_z q_z x_{zj} \Big/ \sum_z M_z x_{zj} & \forall j & \text{(Lloyd: the } M\text{-weighted centroid)}\\[6pt]
\textbf{stop:} & \text{the labels repeat}
\end{array}
\tag{draw}$$

The inner program is a Hitchcock transportation problem (Lemma 6 of the note): substitute
$\eta_{zj} = M_z x_{zj}$ and the rows become supplies $M_z$ against demands $\tau$. Its constraint
matrix is a network matrix, so a basic optimum has forest support and splits at most $k - 1$ zips;
every other zip is assigned integrally by the relaxation itself. Its duals $(\alpha, \beta)$
satisfy $\alpha_z + M_z \beta_j \le M_z \lVert q_z - c_j \rVert^2$, so the optimal cells are the
power diagram $\mathrm{argmin}_j (\lVert q_z - c_j \rVert^2 - \beta_j)$: $k$ convex cells. The
naming of districts by their centres removes the $k!$ label symmetry an anonymous model would
carry.

### 1.3 Around the loop

Four heuristics surround (draw), and §1.5 measures them rather than trusts them.

1. **Seeding.** $M$-weighted k-means++: the first centre is a zip drawn with probability
   proportional to $M_z$, each next one proportional to $M_z\, d^2(z, \text{nearest chosen centre})$.
2. **The Lloyd loop.** Assign by the inner LP, move each centre to its district's $M$-weighted
   centroid, repeat until the labels repeat. Every round is exactly balanced before rounding, so
   the rounds buy compactness only. There is no fixed point on this instance (20 snap-and-recentroid
   iterations, no exact repeat); the loop stops on label repetition.
3. **Rounding and polish.** Each split zip goes to the district holding its largest share (at
   most $k - 1 = 17$ zips move; on this run exactly 17 were split). Then a greedy pass over
   single-zip moves that strictly raise $\sum_j \log g_j$, restricted to the three nearest centres
   so that no move crosses the country for an epsilon of balance; ties go to the more compact
   destination; a district is never emptied.
4. **Completion.** The 41 zips with no gazetteer coordinate go to the district holding the
   plurality of their state's already-placed zips, one at a time, ties and unknown states to the
   lightest district (`channel.place_by_state`).

### 1.4 The portfolio, and how seed 2 was chosen

Ten seeds (0 to 9) were drawn. Each draw was completed and then staffed by stage 2 (§4.3), and the
draw with the best staffing value was committed: seed 2 at 95.755, against 95.689 for the worst
seed and 95.749 for the runner-up (seed 7). This is `channel.score_draws`, the portfolio
mitigation of the note's §5.2: a lower bound on the joint optimum over maps and staffings, not the
joint optimum. (The channel note's §5.2 says the committed draw "is not on record as having been
selected by stage 2"; `metrics.json` in the run directory records exactly that selection, so the
note's sentence is out of date on v2. The note's markdown was folded into `docs/PROBLEM.md` and
`docs/MODEL.md` on 2026-09-07; its text is `git show 81bd59f:docs/CHANNEL_NOTE.md` and its LaTeX
source is `docs/channel_note/channel_note.tex`.)

### 1.5 What the committed draw certifies, and what it does not

The Jensen ceiling holds for every partition of these zips into 18 districts, whatever its
geometry. Over the 3,704 plotted zips (mass 8,468.3) it is $k \log(M/k) = 110.766768$ and the
draw scores 110.766686: a gap of **0.000082 nats** at a mass spread of 1.29% (1.37% on the whole
instance after completion, max deviation 1.00%). Not certified: that the 18 centres are the right
ones (the joint problem over centres and assignment is untouched); the integer balance floor and
the pinned-centres MILP of `docs/MODEL.md` §10, never run on v2; and the labelling as a
power diagram, since after the polish 258 zips (7.0% of count, 1.66% of mass) sit outside their
own cell at own-masses targets.

### 1.6 What the next step inherits

Three things, and only these: the centres $c_j$ (recomputed as the $M$-weighted centroids of the
committed districts), each district's home state $\mathrm{home}(j)$ (the plurality state of its
mass), and the district numbers D01 to D18. The committed shapes are not inherited. The
committed map's own state composition is not connected on the rook graph (D09 holds crumbs in ND,
NY and TN; D18's CA piece is cut off from ID and MT), so it was never a feasible point of the
level-1 program and could not serve as a warm start.

Committed composition by home state: NY (D01, D04), CA (D02, D10, D14, D17, D18), TX (D03, D16),
PA (D05), CO (D06), FL (D07, D15), NC (D08), MI (D09), IL (D11), NJ (D12), MO (D13). 41 states
have no home district.

| committed draw | value | base |
|---|---|---|
| seeds run / kept | 10 / seed 2 | `tools/run_draw.py --k 18 --seeds 0-9` |
| $\sum_j \log g_j$ / ceiling / gap | 110.766686 / 110.766768 / 0.000082 | 3,704 plotted zips |
| mass spread / max deviation | 1.37% / 1.00% | whole instance |
| split zips at the final LP | 17 = $k - 1$ | geometric set |
| zips outside their own power cell | 258 (7.0%, 1.66% of mass) | own-masses targets |
| stage 2 value / unmatched reps | 95.755 / 96 | whole instance, $\theta = 0.4$, $\lambda = 0.3$ |

Run: `battery/results/draw_k18_v2_20260904/k18/` (`draw.csv`, `metrics.json` with all ten seeds
and the winner). Code: `td/solvers/centers.py` (`draw`, `assign`, `improve`, `power_weights`),
`td/channel.py` (`score_draws`, `place_by_state`), `td/solvers/cert_draw.py`. Verification:
`docs/units/U1-cert.md` and `docs/units/U7-meas.md` (`## Model`, `## Verify`, `## Code verify`),
with their runnable artifacts under `tools/verify/U1-cert/` and `tools/verify/U7-meas/`;
`tests/test_cert_draw.py` against brute force at small $k$.

## 2. Level 1: which states split, and how their mass is shared

The border build asks how the committed draw's borders must move to lie on state lines under a
balance band. Level 1 answers on 49 units: it chooses which states are split, among how many
districts, and what share of each split state's mass goes where. It is a mixed-integer program on
the state graph; zips do not appear.

### 2.1 Data

$M_s$ is the state's mass over its zips with a coordinate. $D_{sj} = \sum_{z \in s} M_z \lVert q_z
- c_j \rVert^2 / M_s$ is the moment of state $s$ about committed centre $j$, a 49 × 18 table. The
rook graph $G_S$ comes from the TIGER state polygons, not from the instance's zip adjacency (which
contracted to states gives 10 edges over 42 components).

### 2.2 The minimum-splits program

A state touching $m$ districts is split $m - 1$ times, so $\sum_s (\sum_j z_{sj} - 1)$ counts the
splits. Variables: $y_{sj} \in [0, 1]$ the share of state $s$ sent to district $j$; $z_{sj} \in
\{0,1\}$ contact; $r_{sj} \in \{0,1\}$ the root of district $j$'s state set; $f_{aj} \ge 0$ a unit
flow on directed arc $a$ of $G_S$ carried by district $j$. $N = S = 49$.

$$\begin{array}{llll}
\min\limits_{y,\,z,\,r,\,f} & \displaystyle\sum_{s}\Big(\sum_{j} z_{sj} - 1\Big) \;+\; \varepsilon \sum_{s}\sum_{j} M_s D_{sj}\, y_{sj} \\[8pt]
\text{s.t.} & \displaystyle\sum_{j} y_{sj} = 1 & \forall s & \text{(all of } s \text{ placed)}\\[4pt]
 & \eta\, z_{sj} \le y_{sj} \le z_{sj} & \forall s, j & \text{(contact carries mass; no mass without contact)}\\[4pt]
 & (1-\delta)\,\tau \le \displaystyle\sum_{s} M_s\, y_{sj} \le (1+\delta)\,\tau & \forall j & \text{(the band, hard)}\\[4pt]
 & z_{\mathrm{home}(j),\,j} = 1 & \forall j & \text{(anchor: } j \text{ keeps its home state)}\\[4pt]
 & \displaystyle\sum_{s} r_{sj} = 1,\quad r_{sj} \le z_{sj} & \forall j & \text{(one root per district, inside it)}\\[4pt]
 & f_{aj} \le (N-1)\, z_{\mathrm{tail}(a),\,j},\quad f_{aj} \le (N-1)\, z_{\mathrm{head}(a),\,j} & \forall a, j & \text{(flow only on arcs inside the district)}\\[4pt]
 & \displaystyle\sum_{a \to s} f_{aj} - \sum_{a \leftarrow s} f_{aj} \ge z_{sj} - N\, r_{sj} & \forall s, j & \text{(every touched state absorbs one unit)}\\[4pt]
 & y \ge 0,\quad z, r \in \{0,1\},\quad 0 \le f \le N-1
\end{array}
\tag{splits}$$

The last three rows are the single-commodity-flow contiguity of Validi, Buchanan and Lykhovyd,
written on the state graph.

**Claim 1 (contiguity is exact).** With $r$ binary, the flow rows admit a set $\{s : z_{sj} = 1\}$
iff it is non-empty and connected in $G_S$. If connected, root it anywhere and send one unit along
a spanning tree to every other node. If disconnected, the component without the root has net
inflow zero and demands at least one unit. With $r$ continuous the argument fails (a fractional
root in each component pays for it), which is why $r$ stays integral.

**Claim 2 (the tie-break never buys a split).** With $\varepsilon = \tfrac{1}{2} \big/ \sum_s M_s
\max_j D_{sj}$, the compactness term lies in $[0, \tfrac12)$ for every feasible $y$, so two
solutions differing in split count differ by at least $\tfrac12$ in the objective in the same
direction, and the optimum has the least split count among feasible solutions. The first draft
scaled $\varepsilon$ at the committed map's own composition and a four-state counterexample
returned two splits where zero was optimal; the bound must hold over every feasible $y$.

**Claim 3 (what the anchors do).** Without the anchor row the districts are anonymous and the
program carries the full $k!$ relabelling symmetry; HiGHS held a one-split gap open for 600 s.
Fixing $z_{\mathrm{home}(j), j} = 1$ names district $j$ by its committed home state. It is a
restriction, so the anchored optimum is an upper bound on the free minimum. Six of the eight
splits are forced by mass alone: CA at 4.153τ needs four districts under a 5% band (three cuts),
and TX (2.026τ), NY (1.805τ) and FL (1.392τ) each need two (one cut each). The two anchored cuts
beyond that are NY's third district and CA's fifth.

These four ratios are $M_s/\tau$ on the **level-1 ground set**, $\tau = 470.459$, as
`--dump-state-shares` writes them straight from the arrays `build_milp` is handed (NJ, the fifth
state over $\tau$, is 1.043). `STATE.md` `## Facts` quotes CA 4.126, TX 2.020, NY 1.794, FL 1.398
and NJ 1.037 in its state-atom block, and those are a different base: the atom route keeps every
zip, including the ones with no gazetteer point, so it divides by the whole-instance
$\tau = 473.513$. Rescaling the level-1 masses to that $\tau$ reproduces CA 4.126, NY 1.794 and
NJ 1.037 exactly, and falls short at TX 2.013 and FL 1.383 — the gap is the mass of the
coordinate-less zips in those two states, which level 1 drops and the atom route keeps. Neither
number is wrong; they must not be compared. The floor
$\lceil M_s / ((1+\delta)\tau) \rceil$ is 4, 2, 2, 2 on either base.

Size and solve: 6,498 variables, 1,764 of them binary, 11,317 rows. HiGHS through
`scipy.optimize.milp` with `mip_rel_gap = 0` closed it in 168 s. Objective $57.0048 = 49 + 8 +
0.0048$, the constant being $\sum_s 1$. Result: 8 splits; CA in five districts, NY in three, TX and
FL in two; 45 states whole.

### 2.3 The balance pass

(splits) spends the whole band wherever that saves a split, so its $y$ sits at the band's edge
somewhere even when the chosen splits allow a tighter balance. With $z$ fixed at $z^\star$, $y$ is
re-solved by two LPs in sequence, both keeping $\eta z^\star \le y \le z^\star$ so no bridge state
is emptied:

$$\begin{array}{llll}
\text{(pass 1)} & \min\limits_{y,\,t} \; t & \text{s.t.} & \sum_j y_{sj} = 1,\ \ \eta z^\star_{sj} \le y_{sj} \le z^\star_{sj},\ \ \big\lvert \sum_s M_s y_{sj} - \tau \big\rvert \le t \quad \forall s, j \\[6pt]
\text{(pass 2)} & \min\limits_{y,\,u,\,l} \; u - l & \text{s.t.} & \text{the rows of (pass 1) with } t = t^\star,\ \ l \le \sum_s M_s y_{sj} \le u \quad \forall j
\end{array}$$

Deviations sum to zero, so $\max_j |g_j - \tau| \le \text{spread} \le 2 \max_j |g_j - \tau|$, and a
single pass can return a wider spread at equal maximum deviation. On this run the MILP's $y$ had
spread 10.00%; the pass returned 9.30% with maximum deviation 4.68%. The level-1 shares after the
pass:

| state | mass (level-1 τ) | shares $y^\star$ |
|---|---|---|
| CA | 4.153τ | D02 18.8%, D10 25.3%, D14 24.9%, D17 8.2%, D18 22.9% |
| FL | 1.392τ | D07 71.8%, D15 28.2% |
| NY | 1.805τ | D01 58.2%, D04 37.0%, D05 4.9% |
| TX | 2.026τ | D03 51.4%, D16 48.6% |

Code: `td/solvers/state_splits.py` (`build_milp`, `solve`, `eps_lexicographic`, `balance_pass`,
`connected`). Verification: `docs/units/state_splits.md` `## Verify` refuted three parts of the
first formulation before the build ($\varepsilon$ bounded over every feasible $y$; $y \ge \eta z$
so a bridge state carries mass; the two-LP pass) and refuted the plan's "seconds" for the free
program; its `## Code verify` verified five model-to-code mappings and the row count 11,317.
Artifacts: `tools/verify/state_splits/`.

## 3. Level 2: realising the shares at zip level

Every unsplit state goes whole to its district. For each split state $s$, its zips are assigned
by the same transportation LP as (draw), restricted to $s$, against the full centre set, with
per-district targets $y^\star_{sj} M_s$ in place of $\tau$ (a district with $z_{sj} = 0$ gets
target 0 and receives nothing):

$$\begin{array}{llll}
\min\limits_{x} & \displaystyle\sum_{z \in s}\sum_{j} M_z \lVert q_z - c_j \rVert^2 x_{zj} \\[6pt]
\text{s.t.} & \displaystyle\sum_j x_{zj} = 1 & \forall z \in s \\[4pt]
 & \displaystyle\sum_{z \in s} M_z x_{zj} = y^\star_{sj}\, M_s & \forall j \\[4pt]
 & x_{zj} \ge 0
\end{array}
\tag{targets}$$

A basic optimum splits at most one zip fewer than the number of districts with a positive target,
and the split zips are rounded to their largest share. Then up to five Lloyd rounds inside the
state: every district touching $s$ is re-centred at the $M$-weighted centroid of its full
membership (whole states included), (targets) is re-solved, and the round is kept only if it does
not raise $\sum_{z \in s} M_z \lVert q_z - c_j \rVert^2$ for the state; the loop stops when the
state's labels repeat or a round is rejected. The committed centres were placed for the old
shares and can sit in the wrong place for the piece a district now owns; the rounds make the cut
compact for the shares actually chosen. On this run three rounds were kept in total and eight
zips were rounded.

`realise` processes the split states in alphabetical order (CA, FL, NY, TX) and moves the shared
centre array as it goes, so in general a later state's cut can depend on an earlier state's
rounds. On this cell it cannot: the four split states' district sets (CA: D02, D10, D14, D17, D18;
FL: D07, D15; NY: D01, D04, D05; TX: D03, D16) are pairwise disjoint, and a state's rounds move
only the centres of districts touching that state, so no centre used for one split state is moved
by another. The order dependence STATE.md flags as unjudged is real for the code and inert for
the shipped map.

Code: `td/solvers/state_splits.py::realise`, `td/solvers/centers.py::assign` (with `targets=`).
The per-round iterates are recorded per split state for the "Borders in Motion" replay.

## 4. Completion, measurement, and stage 2

### 4.1 Completion

The 41 zips without a coordinate, and the AK, HI and unknown-state zips outside the level-1 ground
set, are placed last by the same rule the committed draw uses (`channel.place_by_state`): to the
district holding the plurality of their state, else the nearest, ties to the lightest district.
This adds 0.6% of mass unevenly, which with the eight rounded zips is why the realised maximum
deviation (5.25%) exceeds the band (5%) that level 1 enforced on its own ground set.

### 4.2 Measurement

On the whole instance: spread $(\max_j g_j - \min_j g_j) / \bar g$, maximum deviation $\max_j
|g_j / \tau - 1|$, and the Nash value $\sum_j \log g_j$ against its whole-instance ceiling
$18 \log(8{,}523.2 / 18) = 110.883247$.

| headline map | value | committed draw |
|---|---|---|
| state splits | 8 (certified minimum under the anchors) | 24 |
| states not whole | CA (5 districts), NY (3), TX (2), FL (2) | |
| spread / max deviation | 8.98% / 5.25% | 1.37% / 1.00% |
| $\sum_j \log g_j$ / gap to 110.883247 | 110.874 / 0.0096 nats | 110.883 / 0.00015 nats |
| zips relabelled against the committed draw | 776 of 3,748 | |
| stage 2 value / unmatched reps | 95.788 / 96 | 95.755 / 96 |

### 4.3 Stage 2: staffing the map

Given the map $A_1, \dots, A_k$, let $g_{ij} = \sum_{z \in A_j} u_i(z)$ be what district $j$ is
worth to representative $i$, evaluated for every representative on every district (§0 gives
$u_i$). Nash-optimal staffing is the linear assignment problem on logs (Proposition 5 of the note):

$$\begin{array}{llll}
\max\limits_{\sigma} & \displaystyle\sum_i \sum_j \big(\log g_{ij}\big)\, \sigma_{ij} \\[6pt]
\text{s.t.} & \displaystyle\sum_j \sigma_{ij} \le 1 & \forall i & \text{(each rep staffs at most one district)}\\[4pt]
 & \displaystyle\sum_i \sigma_{ij} = 1 & \forall j & \text{(each district staffed)}\\[4pt]
 & \sigma_{ij} \ge 0
\end{array}
\tag{P2}$$

The constraint matrix is totally unimodular, so the LP is integral and the Hungarian algorithm
solves it exactly. With 114 representatives against 18 districts the matching is rectangular:
96 representatives go unmatched, and the matching is the retention decision. The headline map
staffs at 95.788 against the committed draw's 95.755, with 96 unmatched in both. Stage 2 is
unchanged by the border move to within 0.03 nats.

Code: `td/channel.py`, `td/model.py` (`utilities`). Weights $\theta = 0.4$, $\lambda = 0.3$,
`filler_capture = theta`, as in the committed run's `metrics.json`.

## 5. The map

`tools/us_maps.py` renders each cell twice from its `draw.csv`: `districts.png` (one dot per
zip, area proportional to $M_z$, colour by district) and `district_regions_voronoi.png` (each
zip's Voronoi catchment clipped to its own state and coloured by district, so a state that lies
whole in one district shows as one whole state, and inside a split state the line between two
zips of different districts is their perpendicular bisector). The committed figures
`figures/borders_track2_anchored_d05_districts.png` and
`figures/borders_track2_anchored_d05_voronoi.png` are byte-identical copies of the cell's two
renderings.

### 5.1 Composition of the headline map, whole instance

| district | $g_j / \tau$ | zips | mass relabelled vs committed | states (share of district mass) |
|---|---|---|---|---|
| D01 | 0.969 | 123 | 26% | NY 98 |
| D02 | 0.997 | 198 | 30% | CA 83, NV 17 |
| D03 | 1.039 | 132 | 7% | TX 100 |
| D04 | 1.038 | 271 | 8% | NY 65, CT 18, MA 10, NH 5, RI 2 |
| D05 | 1.028 | 238 | 12% | PA 52, MD 24, NY 17, DC 4, DE 3 |
| D06 | 0.966 | 216 | 35% | AZ 57, CO 35, NM 3, SD 3 |
| D07 | 1.000 | 239 | 1% | FL 100 |
| D08 | 0.998 | 226 | 9% | NC 55, VA 42, WV 3 |
| D09 | 0.995 | 305 | 18% | MI 47, OH 41, WI 12 |
| D10 | 0.963 | 174 | 21% | CA 99 |
| D11 | 1.017 | 261 | 18% | IL 67, MN 20, IA 5, NE 5, ND 3 |
| D12 | 1.037 | 182 | 31% | NJ 100 |
| D13 | 0.963 | 249 | 13% | IN 22, LA 20, MO 18, KY 14, AL 12, TN 8, AR 4, MS 2 |
| D14 | 0.963 | 84 | 24% | CA 100 |
| D15 | 0.964 | 246 | 9% | FL 41, GA 40, SC 17 |
| D16 | 1.047 | 204 | 12% | TX 94, OK 3, KS 3 |
| D17 | 1.052 | 283 | 25% | CA 42, WA 24, UT 21, ID 6, OR 6 |
| D18 | 0.964 | 117 | 19% | CA 97, HI 1 |

Shares under 0.5% of a district are not listed; the 32 unknown-state zips (0.07τ) land in D01,
D06, D18, D15 and D10.

### 5.2 The four split states, level-1 shares against realised

| state | mass (level-1 τ) | level-1 $y^\star$ | realised (share of state mass) |
|---|---|---|---|
| CA | 4.153τ | D02 18.8, D10 25.3, D14 24.9, D17 8.2, D18 22.9 | D14 23.4, D10 23.1, D18 22.6, D02 20.1, D17 10.8 |
| FL | 1.392τ | D07 71.8, D15 28.2 | D07 71.6, D15 28.4 |
| NY | 1.805τ | D01 58.2, D04 37.0, D05 4.9 | D01 52.8, D04 37.6, D05 9.5 |
| TX | 2.026τ | D03 51.4, D16 48.6 | D03 51.4, D16 48.6 |

The Lloyd rounds keep the targets fixed, so the drift between the two columns comes from rounding
the split zips (eight on this run) and from completion. NY's is the largest: its zips are large
(the heaviest zip in the instance carries 0.18τ), so one rounded zip moves a state share by
several points.

## 6. What is certified

| statement | kind | holds for |
|---|---|---|
| No partition of the plotted zips into 18 districts scores above 110.766768 | closed-form bound (Jensen) | every partition, any geometry |
| The committed draw's gap to it is 0.000082 nats | measurement | the committed labelling |
| Among all assignments of the 49 units to 18 districts that place every unit, keep every district within 5% of τ on that ground set, keep each district's state set connected on the rook graph, send at least 1% of a touched state's mass, and keep each district in its committed home state, none has fewer than 8 splits | solver certificate, zero gap | the anchored feasible set and no larger one |
| The solution's contiguity and band rows hold | independent re-check | the returned $z$, $y$ |
| The level-2 cut is compact for the chosen shares | heuristic | no optimality claim; the transportation LP is exact for the shares it is given, the Lloyd rounds are descent |
| Map contiguity inside CA, NY, TX and FL | visual | not graph-certified; the sponsor's stated bar |

Not certified, and open: the free minimum without the anchor row lies between 6 and 8 (HiGHS
left it open at 600 s); the committed draw's centres as the right ones; the integer balance floor
and pinned-centres MILP on v2; and whether California can be held to four districts at δ = 5%
(§7).

## 7. Per-state caps, and what an hour of search proves

`--cap ST=N` adds a row holding state `ST` to at most `N` districts; `--unanchor ST` drops that
state's home anchors, and the app releases only the surplus a cap forces, keeping the cap-many
anchors that hold the most of the state's committed opportunity. The Headline tab drives both.

**The mass floor is necessary and not sufficient.** $\lceil M_s/((1+\delta)\tau) \rceil$ rules a
cap out; it never promises one is reachable. California at 4 is legal at δ = 5% and sits exactly
on the floor: four districts at the top of the band hold 4.200τ against California's 4.153τ,
leaving 0.047τ of slack to cover every other state that reaches into those four, a window 4.7% of
a district wide. HiGHS found no feasible integer point in 10 minutes, nor 20, nor 60; the hour
run ended `model_status is Time limit reached; primal_status is None`, so it never held an
incumbent at all.

**A search failure is not a refutation.** New York at 2 returns HiGHS Status 8, Infeasible, in
seconds: two districts are anchored in New York and need at least 1.90τ while the state supplies
1.805τ, and Pennsylvania and New Jersey are anchored elsewhere. That is a proof. California at 4
returns Status 13 with no primal solution, which says only that branch and bound did not reach a
feasible point in the time given. A map may exist. Three outcomes have to be told apart wherever
this is reported: refused by the mass floor, refuted by the solver, and searched without success.
The Headline tab still collapses the last two into one sentence; there is a `TODO` at
`app/main.py` where it does.

**Caps have almost no legal move at δ = 5%.** Only four states are split, TX and FL are already at
their floor of 2 so a cap there is a no-op, NY at 2 is refuted, and CA at 4 is the knife-edge
above. The map is not merely optimal on this feasible set, it is tight.

**The band is the lever, not the cap.** California capped at 4 at δ = 10% solves: 7 splits, CA in
4, NY falling to 2 on its own, NJ splitting for the first time, spread 16.70% against 8.98%,
stage 2 95.7458, a time-limited incumbent at a 1.79% gap. Gallery and numbers:
`figures/overrides/ca4_d10/`.

## 8. Reproducing it

From the repo root, with the hub's `.venv` and the gitignored inputs in place
(`docs/CODE_MAP.md`):

```
.venv/bin/python3 tools/run_draw.py instance_descaled_v2.json.gz --k 18 --seeds 0-9 --workers 8 \
  --out battery/results/draw_k18_v2_20260904

.venv/bin/python3 -u tools/state_splits.py instance_descaled_v2.json.gz \
  --draw battery/results/draw_k18_v2_20260904/k18/draw.csv --geo-cache data/geo \
  --delta 0.05 --anchor-homes --time-limit 600 --rounds 5 --eta 0.01 \
  --out battery/results/borders_k18_v2_20260907/track2_anchored/d0.05 --maps
```

The second command's parameters are recorded in the cell's `params.json`; the level-1 solution
($z$, $y$, shares, status, gap) in `splits.json`; the map in `draw.csv`; the grid row in
`grid.csv`. Stage 1 is seeded, so the first command reproduces the committed draw only with the
same seeds; the second is deterministic given the draw.

## 9. Sources

- Model and proofs: `docs/PROBLEM.md` §2 (the welfare decomposition, the utility model) and §3
  (the two stages); `docs/MODEL.md` §7 (the two propositions and the notation), §8 (stage 1 as
  centre-based balanced assignment, §8.2 the transportation-relaxation lemma), §9 (stage 2),
  §10 (certificates). These absorbed `docs/CHANNEL_NOTE.md` on 2026-09-07; its text is
  `git show 81bd59f:docs/CHANNEL_NOTE.md`, its LaTeX source `docs/channel_note/channel_note.tex`.
- The border build: `docs/units/state_borders.md` and `docs/units/state_splits.md` (brief,
  `## Model`, `## Verify`, `## Code verify`), the Track 1 and Track 2 grids in `STATE.md`
  `## Facts`, and the artifacts under `tools/verify/state_splits/`. The plan and results files
  they replaced are `git show ae2b18d:docs/BORDERS_PLAN.md` and
  `git show ae2b18d:docs/BORDERS_RESULTS.md`.
- Runs: `battery/results/draw_k18_v2_20260904/k18/` and
  `battery/results/borders_k18_v2_20260907/track2_anchored/d0.05/d0.05/` (hub, gitignored).
- Artifacts: "The Five Percent Map" `322e6a55-a576-4adf-8dc5-8fd2f4ca6c5a` (this map, its tables,
  the three-level model); "Borders in Motion" `3e983b90-8f87-4dfd-aa28-4e1cd6eee497` (every
  optimisation step replayed on the map); "Districting from Duality"
  `d87b53b0-f394-417e-aab5-0fba8d3c6cb0` (the study guide).
