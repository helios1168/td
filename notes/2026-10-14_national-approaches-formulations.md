2026-10-14 · m5-studio/national-approaches · 457ff8f · Agent: worker (claude-sonnet-5-5)

# National (main) map: every approach tried so far, with its formulation, for an independent mathematical review

Purpose: the owner wants a new approach for the main map. Before one is proposed, this note states what has been tried and the exact mathematics of each attempt, so a mathematician can check soundness against the code. It recommends nothing.

## Reading guide

- **Code wins.** Every load-bearing claim carries a repo-root-relative `path:line` and a contiguous fragment of that line in backticks (long lines are quoted by a fragment). Where the prose in `PROBLEM.md`, `docs/MODEL.md` or `docs/RESULTS.md` disagrees with the code, I follow the code and list the disagreement in §17. A path alone means I read the file but am unsure of the line.
- **Code state read.** `main` @ 457ff8f for everything not named otherwise. Branch-only code is cited as `<branch>:<path>:<line>` and read with `git show`: `m5-studio/window-band` @ 8a22136 (window band), `m5-studio/sealed` @ 4963113 (`sealed.py`, `glue.py`), `m5-studio/warm-start` @ 53dac30 (`warm.py`), `m5-studio/carve-first` @ b1e047b, and the tag `archive/pre-support-2026-09`. Gitignored run outputs are cited by their path under the hub clone (`runs/exp/...`, `$TD_REPO` = `/Users/Shared/sv-ntlee/td`); those were read, not regenerated.
- **Tags.** `(inferred)` marks anything I derived rather than read. `(verified by me)` marks a number I computed from the repository's data in this session (read-only).
- **Not found.** The brief names a `balance.py` on the warm-start branch. It does not exist there: `git ls-tree` on `m5-studio/warm-start` lists `tools/exp/contig/warm.py` and no `balance.py`; the only balance document is `docs/archive/problem/BALANCE.md`. `m5-studio/carve-first` carries no code either (§12).
- **Masking.** Dollars, ZCTA/state ids and district ids appear. No per-rep shares, sales, rep or firm names were read into this note.

## Approaches at a glance

| § | approach | dates | contiguity enforced at | outcome for the main map |
|---|---|---|---|---|
| 1 | legacy flow-tree + support master + power-diagram realizer + healing | to 2026-09-28 | state/unit level; ZIP level never | pieces; M1 not required until 2026-10-04 |
| 2 | support master MILP + transport-LP realizer + territory pass (`td/`) | from 2026-09-28 | unit graph G[S] only | 75 of 75 drawn runs fail M1 (2026-10-05) |
| 3 | Hess-style ZIP-grain planner (#81) | 2026-10-02 | unit-level separator cuts | inconclusive; not a contiguity method |
| 4 | contiguity-aware draw (`draw.py`) + exact window repair (`repair.py`), border term, neck cuts | 2026-10-05..06 | exact (P) on free ZCTAs; (N) by NeckCut in repair windows | repaired maps pass M1 on old rules; under the final neck rule only `ne_plains_wh11` |
| 5 | plan feedback: pair bans, free lists, A/B/C, whole-unit loop (#122, #124, #127) | 2026-10-06..07 | plan-side, unit level | no main map passes; IFA whole-unit maps pass M1 but not the band |
| 6 | `ne_plains` layout at every $-eligible K (#125) | 2026-10-07 | as 4 | 6 maps pass M1 then; later dollar audit fails them |
| 7 | 21-point joint WIFI × K grid, symmetric dollar band | 2026-10-13 | as 4 | 20 of 21 no plan in window; best map 1 neck |
| 8 | regional-seal quick test + IFA pipeline | 2026-10-13 | sealing + as 4 | w1-50-wide: 1 piece/1 neck (NYC) |
| 9 | sealed driver, 15 points, strict drawing, drawable-alone | 2026-10-14 night | sealing + as 4 | no sealed map |
| 10 | unsealed grid with the window band [L, U] | 2026-10-14 day | as 4 | all 15 plan; exact draw does not finish |
| 11 | warm start: repair the first drawing, glue, merge, gate | 2026-10-14 | repair windows + gate | 3 passing maps (3,629–5,618 heuristic-placed ZCTAs each) |
| 12 | carve-first (set partitioning over gated columns) | in progress, other session | per-column gate | not built |
| 13 | IFA-origin tools (`coarse.py`, `rulec_enum.py`, `merge.py`) | 2026-10-08..13 | unit-level flow (coarse) | IFA K48–54 pass, Manhattan excepted |

## 0. The problem, formally

### 0.1 Geography: the graph M1 is judged on

- **Vertices.** V = every CONUS ZCTA of the 2025 TIGER ZCTA polygons: |V| = 33,300 (verified by me with `geo.polygon_graph()`; PROBLEM.md:61 `connected component of the graph whose vertices are all CONUS ZCTAs of the 2025 TIGER ZCTA`). A multipart ZCTA is one vertex whose parts are always mutually connected (PROBLEM.md:68 `Multipart ZCTAs (owner, 2026-10-05, ruling relayed on #108; 1,429 of the 33,300 are`). Vertex set ships explicitly; never inferred from polygons (AGENTS.md trap 21).
- **Edges.** E = E_poly ∪ E_conn. E_poly: two ZCTAs whose polygons share a boundary of positive length in EPSG:5070; a corner touch is no edge (`reference/2025/POLYGON_GRAPH.json` `"adjacency": "rook: boundaries share a length > 0 m in EPSG:5070; a corner touch (length 0) is not an edge"`). E_conn: the committed connector list `reference/2025/connectors.csv`, which I counted: 179 rows, all `approved`, kinds 52 bridge, 8 tunnel, 22 ferry, 91 road, 6 nearest (verified by me). |E| = 89,900 = 89,721 bordered polygon edges + 179 connectors (verified by me). The graph is one connected component (PROBLEM.md:77 `With them the polygon graph is one component.`). 49 state codes (48 + DC) label the vertices.
- **Unit graph** used by the master: units are states (and carved pieces, none in the main-map specs); two units are adjacent iff some ZIP of one has an edge of E to some ZIP of the other, so on the same ZIPs E(M1) ⊆ E(G) (docs/MODEL.md:39-43 `every M1 graph edge between units is an edge of G: on the same ZIPs, E(M1) ⊆`).
- **Gap land.** `geo.polygon_graph()["gaps"]` has 0 pairs (verified by me), so rule R5 (land-only gap edges joining pieces) is inactive on the real graph (docs/MODEL.md:880-883 `is not shipped yet, so R5 is inactive on the real graph and`).

### 0.2 Channels, fine channels, masses, dollars

- **Fine channels** F = {n₁, n₂, n₃, wh, fi}: three national fine channels (their names are on line 10 of `scenarios/main_ne_plains.toml`, not repeated here) plus `wh` and `fi`; five more are planned elsewhere (`scenarios/main_ne_plains.toml:12` `planned_elsewhere = ["career", "edj", "ifa", "imo", "priafs"]`).
- **Planning channels** c with domains D_c ⊆ V_unit × F that partition all (unit, fine) cells (td/spec.py:408 `raise SpecError("the domains do not partition V × F: " + "; ".join(msg))`). Per grid structure (`overnight.STRUCTURES`, tools/exp/contig/overnight.py:127 `STRUCTURES = {                  # structure -> (base spec, split lists: the base's or the #76 rule)`):
  - `ne_plains`: WIFI = 15 whole-state units (ME NH VT MA RI CT; ID MT ND NE SD WY NM OK KS) holding all five fine channels; national = {n₁, n₂, n₃}, WH = {wh}, FI = {fi}, each over the other 34 units (`scenarios/main_ne_plains.toml`).
  - `west8`: WIFI = 8 west states, `nw49`/`nw34`: national + WIFI over 49/34 units; `w1`: one channel WIFI over all 49 units (`scenarios/main_west8.toml`, `main_nw49.toml`, `main_nw34.toml`, `main_w1.toml`). The national channel keeps national fine channels of units that have national; units without it send them to their fallback channel (td/spec.py:411 `def check_national(spec: Spec) -> None:`).
- **Cell mass.** After `tools/exp/contig/dollarize.py` the extract is in $M: m_{z,f} = m_rel_{z,f} · r_f, r_f = (owner's whole-extract dollar total of f) / (extract's m_rel total of f) (tools/looks/score.py:289 `return {f: DOLLARS[f] / total[f] for f in DOLLARS if total[f] > 0}`; PROBLEM.md:215 `off-map $ is not credited`). The channel mass of a ZIP is m_z^c = Σ_{f: (u(z),f) ∈ D_c} m_{z,f}; unit mass M_v = Σ_{z∈Z_v} m_z^c. Dollar values are not masked (PROBLEM.md, Masking row).
- **K and τ.** K_c ∈ ℤ≥1, τ_c = Σ_v M_v / K_c (td/spec.py:660 `tau = sum(M[u] for u in keep) / c.k`).
- **On-map $M by structure** `ne_plains` (notes/2026-10-12_main-map-joint-wifi-grid-research.md:102 `| `ne_plains` (15 states) | 3,370 (NE 2,303 + plains 1,067) | 16,896 | 10,139 | 18,504 |`): WIFI 3,370; national 16,896; WH 10,139; FI 18,504.

### 0.3 Dollar windows [L_c, U_c] (the hard balance condition)

Values from the scorer (the code), $ per district:

| channel | window `score.WINDOWS` | note |
|---|---|---|
| national | [1,000, 1,437.5] | tools/looks/score.py:109 `WINDOWS = {"national": (1.0e9, 1.4375e9), "WH": (0.85e9, 1.15e9),` |
| WH | [850, 1,150] | same line |
| FI | [765, 1,035] | tools/looks/score.py:110 `"FI": (0.765e9, 1.035e9), "WIFI": (0.85e9, 1.15e9)}` |
| WIFI | [850, 1,150]; up to 1,600 for a district that alone owns, in its channel, every state it holds a ZCTA in | tools/looks/score.py:111 `WHOLE_STATE_CAP = {"WIFI": 1.6e9}` |
| IFA (one-channel map) | [1,000, 1,437.5] | PROBLEM.md:216 `IFA is judged in the window −20%/+15% of $1.25B ($1,000M-$1,437.5M)` |

The gate compares in whole dollars, edges included (tools/looks/score.py:337 `inside = lo is not None and round(lo) <= round(x) <= round(hi)`), and a WIFI district may reach the cap only if it is a "whole-state" district (tools/looks/score.py:334 `whole = bool(st) and all(owners[ch, s] == {d} for s in st)`). Main-map total K ∈ [48, 54] (tools/looks/score.py:103 `MAIN_K = (48, 54)`); the 2026-10-13/14 grids used totals 48, 49 (comparison), 50, 52. District $ is the sum of its drawn cells' $M in its own channel.

A channel's K can be feasible only if L_c ≤ τ_c ≤ U_c (the masses of K districts in [L_c, U_c] sum to K τ_c); the planners (`overnight.fit_delta`, `plan_point`) require the strict inequality. For `ne_plains` this gives national K ∈ 12..16, WH K ∈ 9..11, FI K ∈ 18..24 (verified by me: 16,896/12 = 1,408 ≤ 1,437.5 and 16,896/17 = 993.9 < 1,000; 10,139/9 = 1,126.6 ≤ 1,150 and /12 = 845 < 850; 18,504/18 = 1,028 ≤ 1,035 and /25 = 740 < 765; the research note reaches the same ranges, notes/2026-10-12_main-map-joint-wifi-grid-research.md:108 `Under the final windows: `ne_plains` N 12–16, WH 9–11, FI 18–24, WIFI fixed 3`).

### 0.4 The ledger

A map is the ledger λ: V × F → districts ∪ {∅}, one owner per (ZCTA, fine channel) cell, zero-opportunity cells included, every ZCTA of a channel's footprint owned in that channel (docs/MODEL.md:789-796 `The ledger has one row per (ZIP, fine channel) cell of the extract and one per cell of the`; PROBLEM.md:84 `Coverage (owner, 2026-10-05, structured pick "Yes, footprint coverage"): a planning`). All reported shares, masses and bands come from the ledger. The master's planned shares are targets and are never read as masses (docs/MODEL.md:803).

### 0.5 M1, exactly as the gate computes it

`td.audit.check_m1` (called by `tools/mandates/check.py::m1` through `score.m1_check`) is the gate; PROBLEM.md names it as the check (PROBLEM.md:115 `the polygon contiguity check `td/audit.py::check_m1` (#108), run by every td run`). Let X ⊆ V be one district's ZCTA set in channel c, Z⁰_c the ZCTAs all of whose rows in c have m = 0 (td/audit.py:1016 `zero = {z for z, m in chm[ch].items() if not m > 0}     # R3: no opportunity in ch`). The district passes iff all three hold:

**(P) One piece.** G_adj[X] is connected, where G_adj = (V, E_poly ∪ E_conn) (td/audit.py:941 `adj = adjacency(run.polygon, gaps=gap_width)    # R5: land-only gap edges join pieces too`; td/audit.py:1021 `if len(comps) < 2:`). A district with ≥ 2 components has detached pieces and the map fails; "listing" is not enough (PROBLEM.md:66 `included. No tolerance: one detached piece fails the map, and listing it is not enough. The`).

**(N) No neck.** Write a(·) for land area (`aland`). A *neck* is a set A ⊆ X, connected on E_poly ∪ E_conn ∪ (land-only gap edges), with
  0.05 · a(X) ≤ a(A) ≤ a(X ∖ A) (the cut-off part is the *smaller side*; the rest may lie in pieces), and
  w(A) < 10 km,
where w(A) is the minimum, over placements of relays on either side, of the total width of the edges leaving A in the *width graph* H_X (td/audit.py:461 `NECK_W_KM = 10.0        # owner, 2026-10-05 (#121): a passage narrower than this is a neck; never tuned`, td/audit.py:462 `NECK_SHARE = 0.05       # owner: a part holding this share of the district's land area`). H_X has vertex set X ∪ R(X). Edge widths, in whole centimetres, each floored (`border_cm`, td/audit.py:485 `def border_cm(metres: float) -> int:`; a neck has width ≤ NECK_W_CM − 1, td/audit.py:466 `NECK_W_CM = round(NECK_W_KM * 1e5)`):
  - polygon edge: its shared border length;
  - approved connector: ∞ (R1; the old rule "0 where land would do" survives only as an opt-in, td/audit.py:938 `land_rule = os.environ.get(LAND_RULE_ENV) == "1"`);
  - land in no ZCTA between two ZCTAs of one state (R2, `gap_width`): the shared Voronoi border of the `dropped` rows, because the land-only file is absent (td/audit.py:562 `and b not in self.connector.get(a, ()) and self.state.get(a) == self.state.get(b)):`);
  - relays R(X) (R3): the ZCTAs of Z⁰_c reachable from X through chains of Z⁰_c ZCTAs (td/audit.py:698 `for y in (*g.border_cm.get(z, ()), *g.connector.get(z, ())):`), whoever owns them, with the same edge widths and no land or mass; a ZCTA of positive opportunity owned by another district is never a relay.
  The search is a MILP (narrowest cut with a side in the share range, `mip_rel_gap` 0) with a single-commodity flow for own-connectedness; a stop on its time limit is listed as an `unresolved` neck, which fails.

**(C) Coverage.** Every (ZCTA, fine channel) cell has exactly one owned row, in the planning channel the scenario routes it to (td/audit.py:917 `and every (ZCTA, fine channel) cell of the scenario owned exactly once, in`); two districts of one channel owning one ZCTA fail. Any item fails the district/map (td/audit.py:1055 `status = "fail" if items else "pass" if ng is not None else "unverified"`).

Consequences, each a checkable claim (§16):
  - **M1 is district-local.** (P) and (N) for district j read only j's ZCTA set X_j, the static graph, and the static set Z⁰_c (`zero` is built from all rows of the channel regardless of owner, td/audit.py:1016). Only (C) couples districts. (inferred from the code above.)
  - **Strict vs gap-width.** "Strict" is `TD_NECK_GAP_WIDTH=0`; the default gate is gap-width on (td/audit.py:396 `return os.environ.get(GAP_WIDTH_ENV) != "0"`). Gap width only adds same-state edges to the width graph and (R5, inactive) to the pieces graph, so every neck/piece found with it on is also found with it off (inferred; the research note states the same, notes/2026-10-12_main-map-joint-wifi-grid-research.md:70 `Gap width can only relax M1, never make a pass fail.`). R1 and R3 apply in both.
  - **No code implements the Manhattan exception.** `grep -ni manhattan td/ tools/mandates tools/looks/score.py` finds only two docstring mentions (td/audit.py:533, td/audit.py:923). The owner's words are "keep manhattan excepted" (notes/2026-10-14_m1-water-empty-land-proposal.md:14 `"keep manhattan excepted" (2026-10-14, #140): Manhattan is the single`); the IFA maps "pass" only by hand-labelling (docs/RESULTS.md:1345 `M1 fails only on the Manhattan district (8.53 km neck, 5.4% of its land; the owner's one exception)`). No main-map candidate needs it (runs/exp/national_2026-10-14/INDEX.md:90 `Manhattan is the only allowed M1 exception (owner, 2026-10-14); none of the three candidates needs it`).

### 0.6 Split states, shape, priorities; what is hard, what is optimised, what is only reported

- **Split state (scorer).** Σ_c |{s : ≥ 2 districts of c own a ZCTA of s, zero-opportunity ones included}| (tools/looks/score.py docstring, rank key 1 `channel-state splits, Σ_c the states where two or more of c's districts own a ZCTA`); cuts = Σ (holders − 1). PROBLEM.md counts only districts "holding positive opportunity" (PROBLEM.md:205); see §17.
- **Shape** is not a constraint anywhere in the pipeline. The scorer has defect counts (thin links, small pieces, crowded states, polygon pieces) and `tools/looks/study.py` reports hull fill, bite, cut-edge counts; `sealed.py` has an optional hard shape-limit file, off by default (m5-studio/sealed:tools/exp/contig/sealed.py:76 `parameters, not decisions: with no file, or`). An 80-verdict calibration found no rule that generalises (docs/RESULTS.md:1349 `no metric rule generalises (best 8/74 errors, 6-9 on the held-out sheet)`).
- **Priority order.** PROBLEM.md:204 (2026-10-05) `then visual defects (one may outrank an extra split, flagged REVIEW), then shape, then balance; never balance first` puts splits first. The owner's 2026-10-14 #134 decision, as recorded in the handoff, is "order: contiguity, shape, balance, splits" (notes/2026-10-14_carve-first-lite-handoff.md:19 `#134 (order: contiguity, shape, balance, splits)`), and #112's "the ±15% band is hard; K moves, the band does not" (same line). PROBLEM.md is not updated (owner-only file). The scorer's `rank_key` is (splits, defects, extent, states/district, worst dev, mean dev) (tools/looks/score.py:549 `def rank_key(s: dict) -> tuple:`).

| item | hard constraint | in an objective | only reported |
|---|---|---|---|
| M1 (P, N, C) | yes, final gate | master: unit-level contiguity and drawability rows only; draw/repair: exact for (P) on the free ZCTAs, (N) by `NeckCut` rows in repair windows | per-piece τ shares |
| dollar window [L_c, U_c] | yes (master band rows, draw/repair band rows, scorer gate) | not optimised; draw: tools/exp/contig/draw.py:50 `Balance is held by the band, not optimised.` | worst-$ position, mean deviation |
| K_c, total K ∈ [48, 54] | yes (fixed per grid point) | – | – |
| split states / cuts | derived from the master's supports (arm 1 keeps the plan's holders) | draw: weight 1000 per extra holder; repair: split units first, holders second | scorer rank keys |
| shape / compactness | no | master: Σ support diameters; draw: border-km term (≤ 900) + moment tie-break (≤ 9) + land term (≤ 900) | defects, study.py measures |
| land ratio in split states (#133, R = 10) | no | soft term in the draw | `land.csv` |

### 0.7 Structure worth stating before the approaches (all (inferred) from §0.2–0.5)

Given the channel domains, the K_c and the windows, the main-map problem separates by channel: channel c asks for a partition of its footprint's ZCTAs into K_c blocks, each (i) M1-local-feasible and (ii) of mass in [L_c, U_c]; the coverage rule (C) is exactly the partition requirement within each channel. Channels interact only through (a) the domain partition (which cells belong to which channel), (b) the total K ∈ [48, 54], and (c) the sum in the split-state count. Every approach below plans or draws per channel.

## 1. Legacy pipeline (to 2026-09-28; tag `archive/pre-support-2026-09`)

Read from the tag's `MATH_REVIEW.md` and from `docs/RESULTS.md`; the legacy code itself I did not read.

**(a) Variables and sets.**
  - Level 0: a state-level single-commodity flow-tree MILP with r_{s,j} ≤ z_{s,j} and flow conservation (archive/pre-support-2026-09:MATH_REVIEW.md:35 `**Level 0 MILP:** Employed a single-commodity flow-tree formulation to enforce state contiguity`).
  - Support master per channel/bundle B: n_S ∈ {0..K}, t_{v,S} ∈ [0,1] over S_0 = {S ⊆ V : G[S] connected, |S| ≤ s̄, ‖c_u−c_v‖ ≤ D_uv} (archive/pre-support-2026-09:MATH_REVIEW.md:56 `$$\mathcal{S}_0=\{S\subseteq V:G[S]\text{ connected},\ |S|\le\bar{s},`).
  - Realizer: transport LP over a split unit's ZIPs, rounded by `centers.assign` argmax (archive/pre-support-2026-09:MATH_REVIEW.md:104 `uses `X.argmax(axis=1)` and repairs empty required districts`).

**(b) Constraints.** Σ_S n_S = K (line 68); Σ_{S∋v} t_{v,S} = 1; η_{v,S} n_S ≤ t_{v,S} ≤ 1 with η = 0.10 (K ≤ 14) or 0.05 at articulation vertices in the generic grid solver and 0.25 in the group-2 solver (archive/pre-support-2026-09:MATH_REVIEW.md:75 `The generic grid solver uses $\eta_{v,S}=0.10$ at articulation vertices when $K\le14$, and $0.05$ otherwise.`); L_K n_S ≤ Σ_v M_v t_{v,S} ≤ U_K n_S (archive/pre-support-2026-09:MATH_REVIEW.md:71 `$$L_K n_S\le\sum_{v\in S}M_vt_{v,S}\le U_K n_S,$$`); contact caps for capped macro units. Band slack 0.1 τ was added in the realizer's guard for the 48/49/50 grids (archive/pre-support-2026-09:MATH_REVIEW.md:148 `**`--band-slack 0.1`**`).

**(c) Objective.** min 0.001 Σ_S Diam(S) n_S (archive/pre-support-2026-09:MATH_REVIEW.md:80 `$$\min\ 0.001\sum_S\operatorname{Diam}(S)n_S.$$`).

**(d) Contiguity.** Unit-level only (G[S] connected). Inside split units: power cells, a `contiguous_cut` heuristic, and `heal_assignment_contiguity`, which moves pieces of ≤ 250 ZIPs "with no capacity or master-support guard" (archive/pre-support-2026-09:MATH_REVIEW.md:129 `moves non-heaviest pieces of at most 250 ZIPs into neighboring districts`). ZIP-level contiguity was never a constraint: PROBLEM.md records M1 set aside "for simplicity" on 2026-09-01 (PROBLEM.md:28).

**(e) Solver.** `mip_rel_gap` 0.05 default; 0.01 or 0.05 for new national solves (archive/pre-support-2026-09:MATH_REVIEW.md:150 `The generic solver defaults to `mip_rel_gap=0.05``).

**(f) Output.** The 2026-10-02 stakeholder options A/B/C/Reference and IFA 49 (docs/RESULTS.md:108-114). Scored later with the audit on the 2025 Voronoi rook graph: 27 (scenario, district) pairs in pieces with 29 pieces, in 22 of 36 catalog scenarios (docs/RESULTS.md:25 `27 (scenario, district) pairs are in pieces, with 29`). After the polygon graph and M1 were adopted: "75 of 75 drawn runs fail" M1 (PROBLEM.md:120 `75 of 75 drawn runs fail (2026-10-05, `tools/mandates/check.py --rescore``).

**(g) Why it stopped.** No ZIP-level connectivity row; slack and unguarded healing mean "the final map does not inherit a zero-slack band certificate" (archive/pre-support-2026-09:MATH_REVIEW.md:148). Replaced at the 2026-09-28 clean slate (#52).

**(h) Soundness questions.** Not asked of this stage (superseded): the tag's own review lists the unproved guarantees (archive/pre-support-2026-09:MATH_REVIEW.md:136 `### 3.5 Which Guarantees Survive to the Final Map?`).

## 2. Support master + ZIP realizer + territory pass (current `td/`, #52)

This is the base layer every later approach reuses (`td/master.py`, `td/supports.py`, `td/realize.py`, `td/territory.py`). Specification: docs/MODEL.md.

**(a) Sets, parameters, variables (per channel c).**
  - Units V_c (states), unit masses M_v, τ_c, ZIP masses m_z, modes mode(v) ∈ {whole, clipped, free}. In the main-map specs `mode = "whole"` with a per-channel `free` list (`scenarios/main_ne_plains.toml`: national free {CA, FL, NY, TX}; WH {CA, FL, NJ, NY, PA, TX}; FI {CA, FL, NC, NY, OH, PA, TN, TX}; WIFI none) and `margin = false`, so μ_S ≡ 0 in those specs. **Not every base spec sets it:** `main_ne_plains.toml` (all four channels) and `main_nw34.toml`'s national channel do (`scenarios/main_ne_plains.toml:15` `margin = false`; `scenarios/main_nw34.toml:26` `margin = false`), while `main_nw49.toml`, `main_w1.toml`, `main_west8.toml` and nw34's WIFI channel do not, so the default `margin: bool = True` applies to them unless a launcher writes the key (td/spec.py:118 `margin: bool = True         # μ_S in the band rows; false sets μ ≡ 0 (MODEL §4.6, #84)`). `sealed.py` writes `margin = false` into every channel of every spec it makes (m5-studio/sealed:tools/exp/contig/sealed.py:409 `keys = {c: {"k": str(v["k"]), "margin": "false", **({"max_size": str(max_size)} if max_size else {})}`), which the 2026-10-14 runs used; the 2026-10-13 grid launcher does not (§7 h.4).
  - Support family 𝒮_c: S ⊆ V_c with G[S] connected, |S| ≤ s̄_c (`max_size`: 5/4/6/9 for national/WH/FI/WIFI), pairwise centroid distance ≤ R_c(u,v) = max(max_dist_km, dist_km[u], dist_km[v]) (900 km base, per-state overrides), plus spec extras, minus `forbid_pairs`; closed under connected subsets (td/supports.py:227 `found = set() if cs.listed_only else set(connected_sets(ch.units, touch, cap, ok))`; td/supports.py:225 `return inst.units.distance_km(u, v) <= cs.dist_cap(u, v)`; td/supports.py:238 `found = {s for s in found if not any(p <= s for p in cs.forbid_pairs)}`).
  - Variables: n_S ∈ ℤ≥0 (copies of support S; n_S ≤ 1 when S holds a whole unit), t_{v,S} ∈ [0,1] (their total share of v).

**(b) Constraints** (lo, hi = 1−δ, 1+δ; τ-normalised masses):
```
count        Σ_S n_S = K_c                                      td/master.py:151
cover        Σ_{S∋v} t_{v,S} = 1                    v ∈ V_c     td/master.py:153
eta          η_c n_S ≤ t_{v,S}                      v ∈ S       td/master.py:160
share        t_{v,S} ≤ n_S                          v ∈ S       td/master.py:161
hold         t_{v,S} = n_S  (v whole, or clipped with |S|>1)    td/master.py:163
band_lo      (lo + μ_S) n_S ≤ Σ_{v∈S} (M_v/τ) t_{v,S}           td/master.py:165
band_hi      Σ_{v∈S} (M_v/τ) t_{v,S} ≤ (hi − μ_S) n_S           td/master.py:166
eta_cap      Σ_{S∋v} n_S ≤ ⌊1/η_c⌋                              td/master.py:168
contact      Σ_{S∋v} n_S ≤ cap_v                                td/master.py:172
corridor     (M_v/τ) t_{v,S} ≥ (c_v(S)/τ) n_S, v a cut vertex of G[S]   td/master.py:179
border       Σ_{S∋v, N(v)∩S={u}} n_S ≤ b_{uv}, v free          td/master.py:183
count_cap    Σ_{S∋v} n_S ≤ |Z_v|                                td/master.py:186
ban          n_S = 0, S ∈ ban_supports                          td/master.py:189
```
`c_v(S)` is the component-versus-rest corridor floor (td/supports.py:337 `floor = max(floor, lightest_path(zs, inst.units.zip_adj, ch.m, side, rest))`), `b_{uv}` the number of v's ZIPs with an edge into u (docs/MODEL.md:248-257).

**(c) Objective.** min Σ_S w_S n_S, w_S = max pairwise unit-centroid distance of S in km (td/master.py:146 `model.n_col[s] = _add_col(model, supports.diameter(inst, s), 0.0,`; td/supports.py:374 `return max((inst.units.distance_km(u, v) for u in s for v in s), default=0.0)`). Balance is not in the objective.

**(d) Contiguity.** Unit level only: a copy's footprint is its support (η > 0), connected in the unit graph G. Whole-unit districts are ZIP-connected whenever every unit is ZIP-connected (docs/MODEL.md:656-658 `Whole units need no realizer. If every unit is connected on the ZIP graph, a district made only of`). For a split unit the district's part "need not itself be connected" (docs/MODEL.md:667 `A district's part of a unit`). The corridor floor, border cap, count cap and Menger row are *necessary* conditions on the read-back of a connected drawing (Proposition D, docs/MODEL.md:300), not sufficient (docs/MODEL.md:335 `No set of rows here is`). Neck rules (N) are not in the master at all; `contact_min_km` (A) adds a width-aware unit-contact rule, off by default (§5).

**(e) Solver.** HiGHS through `highspy`, `mip_rel_gap` 0.0 for plans, with every incumbent re-checked against the rows at FEAS_TOL = 1e-6 (td/master.py:66 `FEAS_TOL = 1e-6`; td/master.py:294 `def solve(model: Model, mip_rel_gap: float = 0.0, time_limit: float | None = None) -> Solution:`). Smallest δ: `exact_delta` (whole/clipped units only; Claim 2) or `bisect_delta` with free units (td/master.py:437, 514). Day-run master solves took 0.4 s or less per channel (runs/exp/national_2026-10-14/main/ne-48-bal/rest-FI-WH-national/draw/solver.json: FI 0.423 s, WH 0.015 s, national 0.02 s, all `optimal`, gap 0).

**Decoding and realizer.**
  - Each S with n_S ≥ 1 becomes n_S copies with the *same* planned share t_{v,S}/n_S of each v ∈ S (td/master.py:379 `share = {v: t[v, s] / n[s] for v in sorted(s)}`). (Claim 1(iii): nothing is lost for plans obeying the same rows, because averaging the copies of one support preserves every row — docs/MODEL.md:493-496.)
  - Per split unit v with copies J_v: centres c_j (k-means for copies of {v}; mass-weighted border centroid for multi-unit copies), then the transport LP min Σ_{z,j} ‖p_z − c_j‖² x_{zj} over mass flows x_{zj} ≥ 0 with Σ_j x_{zj} = m_z (z ∈ Z_v, m_z > 0) and Σ_z x_{zj} = a_{v,j} (j ∈ J_v), solved by dual simplex so the solution is basic (td/realize.py:164 `cost = np.array([_d2(p[z], c[j]) for z in zs for j in js])`; td/realize.py:169 `res = linprog(cost, A_eq=a_eq[:-1], b_eq=b_eq[:-1], bounds=(0.0, None), method="highs-ds",`). At a vertex the positive-flow graph is a forest, ≤ |J_v|−1 ZIPs are split (Lemma 3a, docs/MODEL.md:545-548), and tree rounding keeps each district's error in unit v below its heaviest split ZIP (Claim 3, docs/MODEL.md:570-573).
  - Then one mode-guarded repair pass and one swap pass (td/realize.py:314 `def repair(inst, channel: str, owner: dict, support: dict, comp: dict | None = None) -> list:`; td/swap.py:96 `def swap(inst, channel: str, owner: dict, planned: dict) -> list:`), then the territory pass gives every zero-opportunity ZCTA an owner by breadth-first growth and a shortest-path join of pieces, never moving a ZIP of positive mass (td/territory.py:40 `def grow(owner: dict, free: set, adj: dict, same: dict | None = None) -> dict:`; td/territory.py:82 `def join(owner: dict, zero: set, adj: dict, unit_of: dict, holds: dict, m: dict) -> list:`).

**(f) Output.** 75 of 75 drawn maps failed M1 on 2026-10-05 (PROBLEM.md:120). In the #81 comparison, the support-master arm left 16/12/10 districts in pieces (national/WH/FI) and 292/600/38 pieces ("bridged" 1/0/2) (docs/RESULTS.md:188 `| districts in pieces | 16 | 14 | 12 | 12 | 10 | 14 |`; docs/RESULTS.md:189 `| pieces (bridged) | 292 (1) | 284 (0) | 600 (0) | 598 (0) | 38 (2) | 41 (0) |`), counted on the declared ZIP graph of that date (inferred: the polygon graph replaced the Voronoi graph on 2026-10-04, after this measurement, PROBLEM.md:196 `The authoritative ZIP graph is the 2025 TIGER ZCTA polygon rook graph with a committed connector list`).

**(g) Why it failed.** The realizer cuts non-convex units with a convex power diagram and the master pairs units whose *drawn* shares need not touch (docs/MODEL.md:690-693 `convex cut across a non-convex unit leaves *shape* pieces`; notes/2026-10-13_overnight-grid-to-regional-sealing.md:37 `the unsealed support master pairs states whose drawn shares never touch`).

**(h) Soundness questions I notice.**
  1. Proposition D and its Corollary (the master as a bound) are proved only for μ ≡ 0 and only over 𝒳_c(δ) — drawings with the same support family, modes, η, caps (docs/MODEL.md:300-304, 349-353). D applies to the specs that set `margin = false` (ne_plains, and every 2026-10-14 spec copy); with μ_S > 0 the master is a restriction that bounds nothing (docs/MODEL.md:331-334 `So the master with μ_S > 0 is a restriction of the master with μ ≡ 0, whose feasible set it shrinks, and neither its optimum nor`). Any "no plan" or "smallest δ" statement bounds only that family. The family itself is cut by hand-chosen policy parameters (`max_size`, `max_dist_km`, `free` lists, `forbid_pairs`, η): e.g. nw49 national needed `max_dist_km` raised from 1200 to 1500 km before any plan existed (runs/exp/national_2026-10-14/probes/nw49_dist.md:16 `K17 infeasible at 1200 (proved), feasible at 1500, so the binding K17 requirement lies`).
  2. The objective is indifferent to balance and drawability. Probe plans sit on the window edges: every ne_plains FI plan spans exactly $765.0M..$1,035.0M (runs/exp/national_2026-10-14/probes/split_rules.md:10 `| ne-48-bal | FI | 21 | 881.2 | 765-1035 | R0 | CA FL NC NY OH PA TN TX | optimal | 765.0..1035.0 |`). The planned masses are therefore extreme points of the band rows (inferred), leaving the ZIP-level draw no planned slack.
  3. Closure under connected subsets is proved for the family (docs/MODEL.md:86-89) — the check that `forbid_pairs` removes only supersets keeps it (td/supports.py:238).
  4. The corridor row's validity for a *third* component needs the component-versus-rest floor, not the pairwise one (C6, docs/MODEL.md:228-239); the code takes `max` over the sides of "lightest path from side i to the union of the others" (td/supports.py:337). I read, not re-proved, the counterexample.

## 3. Hess-style ZIP-grain planner (#81, 2026-10-02) — comparison arm, never a production planner

**(a)** Items i: a whole unit is one item (all its ZIPs), a free unit's ZIPs with m>0 are items; districts j; binaries x_{ij}, y_{vj} (district j touches free unit v); centres c_j.

**(b)** At fixed centres (tools/exp81/hess.py:25-33):
```
assign   Σ_j x_ij = 1;  band  L ≤ Σ_i m_i x_ij ≤ U;  link  x_ij ≤ y_vj;
eta      Σ_{i∈v} m_i x_ij ≥ η_c M_v y_vj;  size  Σ_v u_vj ≤ s̄_c;  dist  u_aj + u_bj ≤ 1 (d(a,b) > R_c);
eta_cap  Σ_j y_vj ≤ ⌊1/η_c⌋;  contact  Σ_j u_vj ≤ cap_v;
connect  u_aj + u_bj − 1 ≤ Σ_{w∈N(C)} u_wj   (separator cuts on the unit graph)
```
**(c)** min Σ_z Σ_j M_z ‖p_z − c_j‖² x_zj (tools/exp81/hess.py:5 `min Σ_z Σ_j M_z ‖p_z − c_j‖² x_zj`), alternating with centroid moves (location–allocation) until the assignment repeats.

**(d) Contiguity.** Unit level by separator cuts; ZIP contiguity is not a row in this arm or in the support arm (tools/exp81/hess.py:44-45). A single-commodity flow version of the unit-level rule "was tried and found no incumbent on FI in 300 s" (tools/exp81/hess.py:42 `flow formulation of the same rule was tried and found no incumbent on FI in 300 s.  The master's`).

**(e) Solver.** HiGHS, `mip_rel_gap` 0 and `mip_abs_gap` 0, 900 s per MILP, ≤ 30 iterations, 3 h per channel, 4 threads (tools/exp81/hess.py:77 `TIME_LIMIT = 900.0          # seconds for one assignment MILP`; tools/exp81/hess.py:79 `TOTAL_LIMIT = 3 * 3600.0    # seconds for the whole loop of one channel`).

**(f) Output.** On the Hess measure the support arm is 4.4%, 4.1%, 9.0% above the Hess arm (national, WH, FI); on support diameter the Hess arm is 1.2%, 4.4%, 22.4% above (docs/RESULTS.md:196 `the comparison stays inside one unit: on Hess, arm 1 is 4.4%, 4.1% and 9.0% above the Hess arm`); wall time 580, 21, 4,970 s (national, WH, FI) (docs/RESULTS.md:296 `*Hess wall time.* The Hess arm took 580, 21 and 4,970 s (national, WH, FI): 5,571 s in total,`); pieces 284/598/41 vs 292/600/38 (docs/RESULTS.md:189).

**(g)** Verdict "Inconclusive" (docs/RESULTS.md:308 `**Verdict.** Inconclusive (`docs/archive/problem/UNKNOWNS.md` U38). At ZIP grain, Hess removes two real`): compactness gains were small, runtime ~480×, no global certificate (only a local optimum per centre set).

**(h)** The centre-fixed MILP is certified only at its centres; the loop is a local optimum with no bound over all centres (tools/exp81/hess.py:55). Not a contiguity approach.

## 4. Contiguity-aware realizer `draw.py` (#109, 2026-10-05) and exact window repair `repair.py`, with the border term (#121) and neck cuts

These are the engines of every later map. The master plan is *fixed*; only the ZIP ownership of split units, exclaves and dropped units is optimised.

### 4.1 `draw.py`: one MILP per coupled group

**(a) Sets and variables.**
  - For a plan, `split_fixed`: a unit with exactly one holder is that district's (its largest ZIP-component fixed; other components "exclaves" are free); a unit with ≠ 1 holders and all dropped units are *free* (tools/exp/contig/draw.py:262 `if len(js) != 1:`). Fixed ZCTAs of district j fall into *bodies* (components on G_adj); the first body is the root. In `draw.draw` the order is by ZCTA count, not mass, although the comment says "heaviest" (tools/exp/contig/draw.py:813 `root = {j: bnode[j, 0] for j in js if bodies.get(j)}     # the heaviest body: largest first`; tools/exp/contig/draw.py:240 `return sorted(out, key=lambda c: (-len(c), min(c)))`); `repair.py` orders its bodies by mass (tools/exp/contig/repair.py:347 `comps = sorted(draw.components(zs_j, adj),`). Any body is a valid root for the separator and flow rows, so this affects efficiency, not validity (inferred).
  - Free components that share an allowed district form a *coupled group* g with ZCTA set Z_g, districts J_g; `allowed(z)` = the districts whose plan holds z's unit (arm 1: tools/exp/contig/draw.py:331 `if len(hold.get(v, [])) > 1 and arm == "arm1" and z not in exclave:`). `prune` removes pairs no connected in-band drawing can use (path mass from the root body exceeds hi − F_j) (tools/exp/contig/draw.py:547 `def prune(zs, allowed, js, root, gadj, vert_of, m, fixed_mass, lo, hi) -> dict:`).
  - Binaries x_{z,j} (z to district j), y_{v,j} (j owns a ZCTA of unit v); continuous c_{zw} ∈ [0,1] (border cut indicator), optionally s_v, e_{v,j,k} (land excess), flows f^j_{a→b} ∈ [0, cap_j].

**(b) Constraints** for group g, with F_j the fixed mass of j (bodies + `extra`), lo/hi the band:
```
(1) Σ_{j∈allowed(z)} x_{z,j} = 1                              ∀ z ∈ Z_g         draw.py:942
(2) x_{z,j} ≤ y_{v(z),j}                                                         draw.py:944
(3) lo − F_j ≤ Σ_{z∈Z_g, m_z>0} m_z x_{z,j} ≤ hi − F_j         ∀ j ∈ J_g         draw.py:956
(4) x_{z,j} ≤ Σ_{y∈N_Γ(z)} x_{y,j}   (omitted if z touches a body of j, or if j has no body and one ZCTA already reaches lo)   draw.py:1043
(5) c_{zw} ≥ x_{z,j} − x_{w,j}                                 ∀ adjacent free z,w, ∀ j∈allowed(z)   draw.py:948
(6) separator rows, added lazily (below)
(7) optional: single-commodity flow rows; land rows; fixed-target rows; count/cap rows (repair); NeckCut rows (repair)
    land (#133, R = 10):  e_{v,j,k} ≥ (L_j − R·L_k)/A_v − (1 − y_{v,k}),  e ≥ 0, for ordered pairs (j,k) of holders planned ≥ 0.20 τ in unit v;
        L_j = j's land in v, A_v = v's land (draw.py:957); cost LAND_WEIGHT/((|holders|−1)·#units) per e
```
(lo, hi) = (τ(1−δ), τ(1+δ)) with δ the plan's (main), or the window [τ·band_lo, τ·band_hi] under the window band (m5-studio/window-band:tools/exp/contig/draw.py:296 `lo, hi = (ch.tau * x for x in ch.spec.rel_band(delta))`). In `sequential` mode both sides of (3) are clamped at max(0, ·): "a district already past the band takes nothing more instead of being forced back" (tools/exp/contig/draw.py:954 `if sequential:          # a district already past the band is not forced back`).

**(c) Objective** (min): `W_split Σ y_{v,j}` over pairs (v,j) where j holds no fixed ZCTA of v, W_split = 1000 (tools/exp/contig/draw.py:81 `SPLIT_WEIGHT = 1000.0       # one more holder of a unit outweighs any shape difference`; tools/exp/contig/draw.py:878 `cost.append(0.0 if held else SPLIT_WEIGHT)`), plus the border term b·Σ_{z<w} km_{zw} c_{zw} (b so that the whole term ≤ SHAPE_SCALE = 900, with a credit for borders against the district's own bodies), plus a moment tie-break scaled to ≤ 0.01·900 = 9 (tools/exp/contig/draw.py:870 `cost.append(b_scale * x)`; tools/exp/contig/draw.py:82 `SHAPE_SCALE = 0.9 * SPLIT_WEIGHT`), plus the land term of #133 (≤ LAND_WEIGHT = 900 per group; R = 10, holders planned ≥ 0.20 τ in the unit) (tools/exp/contig/draw.py:86 `LAND_MIN_SHARE = 0.20       # #133: a holder counts when it plans this share of τ in the unit`).

**(d) Contiguity, exactly how.** HiGHS 1.15's lazy-constraint callback is never invoked, so the model is solved, checked and cut in a loop (tools/exp/contig/draw.py:1115-1300):
  1. Up front: row (4), "every ZCTA of j needs a neighbour of j".
  2. After each solve, for each district j with components, let `main` = the component containing the root body (or the heaviest component if j has no body). For each other component C and each z ∈ C add the separator rows
     x_{z,j} ≤ Σ_{s∈Sep} x_{s,j} (Sep = the ring N(C)∖C, and Sep = (ring around `main`) ∩ (vertices reachable from C without entering `main`)), and, if z is a body vertex, Σ_{s∈Sep} x_{s,j} ≥ 1; for a district without a body, x_{z,j} + x_{b,j} − Σ_{s∈Sep} x_{s,j} ≤ 1 with b the heaviest ZCTA of `main` (tools/exp/contig/draw.py:1264 `row(-inf, 0.0, [col[z, j]] + sidx, [1.0] + [-1.0] * len(sidx))`; tools/exp/contig/draw.py:1262 `row(1.0, inf, sidx, [1.0] * len(sidx))`; tools/exp/contig/draw.py:1269 `row(-inf, 1.0, [col[z, j], col[b, j]] + sidx, [1.0, 1.0] + [-1.0] * len(sidx))`).
  3. Re-solve (warm-started by `setSolution`) until a solution has no detached component. Each row is valid for every connected drawing (any path from z to the root, or to b, leaves C through Sep, and enters `main` through the second ring), so an infeasible step *proves* that no connected drawing exists in the group under the group's rules, and a connected optimum is optimal for the complete model (tools/exp/contig/draw.py:24-31 `**Connectivity, exactly.**`). Each added row cuts off the current solution (all of Sep is unowned by j at that solution), so the loop terminates (inferred), but the number of rounds is not bounded polynomially.
  4. `repair.py --flow` (and `plancheck.drawable`) additionally impose a single-commodity flow per district from its root: arc flows f ≤ cap_j x_{b,j} into b, inflow − outflow = x_{v,j} at ZCTAs and = 1 at non-root body vertices (tools/exp/contig/draw.py:973 `row(-inf, 0.0, [k, col[b, j]], [1.0, -float(cap_of[j])])`; tools/exp/contig/draw.py:980 `row(1.0, 1.0, idx, val)`; tools/exp/contig/draw.py:982 `row(0.0, 0.0, idx + [col[v, j]], val + [-1.0])`). This is an exact compact formulation of (P) on the free ZCTAs; `draw.draw` itself (the first drawing) does not pass `flow` (tools/exp/contig/draw.py:378 `r = _solve_group(c, zs, allowed, bodies, body_of, fixed, adj, m, p, unit_of, hold,` — no `flow=`).
  5. Level: ZIP/ZCTA, exact for (P) on the *free* ZCTAs; the fixed whole-unit ZCTAs are not re-assigned. (N) is **not** in `draw.draw`. Only the window repair adds `NeckCut` rows.

**(e) Solver.** HiGHS directly; `mip_rel_gap = 0`; absolute gap 0.05 until a connected solution exists, then 1e-6 (tools/exp/contig/draw.py:88 `PHASE1_GAP = 0.05           # the cut loop's absolute gap until a connected drawing exists`; tools/exp/contig/draw.py:89 `FINAL_ABS_GAP = 1e-6        # then mip_rel_gap = 0 and this absolute gap (trap 12)`); time limit per group = min(channel time left, `group_limit`). A first start comes from the "geodesic-DAG" restriction (every ZCTA of j needs a neighbour nearer j's bodies along geodesic; its drawing seeds the complete model) and from the heuristic `construct`; neither proves anything (tools/exp/contig/draw.py:409 `for dag in (True, False):`).

**Status semantics.** `optimal` = connected optimum of the complete group model; `connected` = connected and feasible; `infeasible` = proved by HiGHS under the group's rules; `unknown` = time limit or a restricted model, never read as infeasible (tools/exp/contig/draw.py:61-63 `- **Status per group**: `optimal``).

### 4.2 `--sequential`

One split unit (or adjacent split units entered through one another) at a time; each district's part is attached to the *union* of what it already owns next to the unit, taken as one body; units not yet drawn count at their *planned* masses in the band row (`extra`). The docstring says it is "neither a restriction nor a relaxation of the joint model", so its failures prove nothing (tools/exp/contig/draw.py:425 `def _sequential(inst, plan, c, owner, free, exclave, allowed, hold, planned, support, p, delta,`; tools/exp/contig/draw.py:64-66 `- **Sequential** (`sequential=True`, `_sequential`): one split unit at a time, for groups too`). The overnight and day grids run `run.py --arm arm1 --sequential` (tools/exp/contig/overnight.py module docstring).

### 4.3 `repair.py`: exact window repair (large-neighbourhood search)

**(a)** Input: a drawn folder failing M1. For each channel and each detached piece (then each neck), a window W ⊆ free ZCTAs: a *ball* (free ZCTAs within h hops of the piece, h = h₀, 2h₀, … while proved infeasible and |W| ≤ `--max-zctas`) and then *corridors* (free ZCTAs on a path from the piece to the rest of its district at most `slack` hops longer than the shortest) (tools/exp/contig/repair.py:399 `def ball(pieces: list, free: set, adj: dict, h: int, whole: int = 750) -> set:`; tools/exp/contig/repair.py:418 `def corridor(pieces: list, owner: dict, free: set, adj: dict, slack: int) -> set:`).
**(b)–(c)** The model is `draw._solve_group` on W with everything outside fixed, the channel's **final band** as (lo, hi) (tools/exp/contig/repair.py:356 `lo, hi = ch.final_band`), arm 1 with `--keep-support`, `--flow`, objective "split units first, then holders (cuts), then border", and the cap rows "window units' split units and cuts may not rise above the drawn map's" (tools/exp/contig/repair.py:378 `g = draw._solve_group(c, zs, allowed, bodies, body_of, outside, adj, m, p, unit_of,`; tools/exp/contig/repair.py:381 `start=seed, count=count, layers=True, flow=flow, border=border,`).
**(d)** (P) exact inside W via flow plus separator rows per BFS layer; districts with pieces outside W that the window is not repairing are left as they are (mass counted).
**Neck cuts.** For each neck of a district meeting W, a `NeckCut` row pair with binary t: Σ_{e∈δ(A)} w_e·[both ends of e are j's] ≥ need·t and share·area(j) − a_min ≥ −big·(t + Σ_{anchors}(1 − x_{z,j})); valid "for every drawing in which j has no neck and its anchors lie in one component of j" (tools/exp/contig/draw.py:133 `class NeckCut:`; tools/exp/contig/draw.py:1079 `row(-cut.const, inf, list(single) + [t], list(single.values()) + [-cut.need])`). Connector widths in these rows still use the **pre-2026-10-14** land rule (tools/exp/contig/repair.py:230 `km += 0.0 if ng.land_would_do(u, v, states) else NECK_KM`), so a repair row can cut a drawing the current gate accepts (docs/MODEL.md:884-889 `The master side (`td.supports.contact`, `repair.neck_cuts`, `plancheck`) still reads the`).
**(e)** Per window `--time-limit` (300–1,800 s) and a channel `--budget`; `--jobs N` races windows in processes (HiGHS pinned to one thread each, trap 18).
**Status semantics.** "optimal" is optimal on W with the rest fixed (never an optimum of the map); "infeasible" proves only that W at that size has no drawing, "never a certificate for the map" (docs/RESULTS.md:557-559 `"optimal" is optimal on W with the rest fixed (`mip_rel_gap = 0`), never an optimum`).

### 4.4 Results of this layer (m5, 2026-10-05..07)

  - **Realizer alone** (no repair): no map passes M1 (docs/RESULTS.md:516 `- **No map drawn by the realizer alone passes M1** (footprint coverage, D3), in any arm; the window`). Coupled-group sizes at ZIP scale: deck A national two groups, 7 districts on 7,421 free ZCTAs (14,853 columns) and 6 districts on 3,822 (11,246 columns), both "unknown" at 300 s + 300 s; FI one group of 22 districts on 16,192 free ZCTAs (37,864 columns), unknown; IFA 49: 49 districts / 21,182 free ZCTAs / 70,512 columns / 170k rows, unknown (docs/RESULTS.md:471-475). "No joint group above 1,833 free ZCTAs reached a connected drawing or a proof in the time given" (docs/RESULTS.md:477).
  - **Repair** made s13, deck A, grid na15/WH12/FI23 and IFA 49 pass M1 (docs/RESULTS.md:574-576), at the cost of balance inside the final band (national 3.6% → 9.5% worst deviation), no new splits.
  - **Border term + final neck rule (#121)**: the border term cut the shared border between districts 22–47% (docs/RESULTS.md:686); under the final neck rule every old drawing failed M1 by necks alone, and only `ne_plains_wh11` passed (docs/RESULTS.md:685-689). The neck-aware third pass proved most remaining windows infeasible at ±10% or left them unknown (docs/RESULTS.md:735-741).

### 4.5 Soundness questions at this layer

  1. **Arm-1 restriction.** Whole units and the plan's holder lists are fixed. "Infeasible" proves nothing about the map, only about the group under the plan's support (draw docstring; docs/RESULTS.md:557-559). The CT + NJ via NY district is the recurring example: drawn infeasible/unknown at every δ, repaired only with ≈1,000-ZCTA windows (docs/RESULTS.md:585-588).
  2. **Objective ordering is not strictly lexicographic.** The border term is scaled to ≤ 900, the land term to ≤ 900 per group, the moment term ≤ 9, each "below one split" (1,000), but they add: the total shape/land cost can reach ≈ 1,809 > 1,000 (inferred from draw.py:82, 85 and the term construction), so a solution with one more holder can be preferred.
  3. **Sequential mode** clamps the band row for districts already past the band, so a sequential drawing can leave districts out of the window; only the later repair/gate catches it (tools/exp/contig/draw.py:954; docs/RESULTS.md:638-642 `**Review fixes** (Sol review 35e038f8). The window's band row had borrowed the`).
  4. **`prune`** discards (z, j) pairs whose cheapest root-body path already exceeds hi − F_j; valid when j has a root body (path mass counts only free ZCTAs, bodies at 0) (tools/exp/contig/draw.py:547). I checked the logic, not a proof.
  5. **NeckCut validity** is argued in the docstring and "checked by enumeration on a toy" (docs/RESULTS.md:716 `checked by enumeration on a toy), so "optimal" is an optimum of the cut-augmented model and`); I did not re-derive it.
  6. **Group decomposition is exact in the joint mode** (inferred): groups share no free ZCTA and no district, and F_j is constant, so the band rows and the objective separate; `--sequential` is not exact (4.2).
  7. **Tolerances are in the extract's units.** On the dollar extract (masses in $M) the draw accepts a given or constructed start with a band slack `tol = 1e-7·max(1, hi)` 1e-7 × 1,035 $M ≈ $103 at the FI top (tools/exp/contig/draw.py:1119 `tol = 1e-7 * max(1.0, hi)`), and the master certifies planned masses only to `FEAS_TOL` = 1e-6 of τ (≈ $1,000–1,400 on τ ≈ $1,000–1,400M, td/master.py:66). The final whole-dollar gate (tools/looks/score.py:337) is the arbiter, so these slacks matter only for edge cases (inferred).
  8. **Connector widths**: draw/repair/plancheck/master-contact still use the pre-2026-10-14 connector rule while the gate uses R1 (docs/MODEL.md:884-889), so the rows can be stricter than the gate on connectors (follow-up the repo already lists).

## 5. Plan-side feedback devices: #122 bans, #124 A/B/C, #127 whole-unit loop (2026-10-06/07)

All were tried on pre-window maps (ne_plains, nocomb, low6, ifa_49) under ±10%/±15% symmetric bands. None changed the master's *family* by a principled rule; each edits it by hand or by a drawing's failure.

### 5.1 #122: unit-pair bans, free-list changes, opened units, widened band

**(a)** `replan.py`: `forbid_pairs` F ⊆ pairs of units; 𝒮_c ← {S ∈ 𝒮_c : no {u,w} ∈ F with {u,w} ⊆ S} (closure preserved: only supersets are removed; td/supports.py:238). `--free C=U₁,…` replaces channel C's `free` list; `--widen C` sets final_delta(C) = 0.15 (ruled by the owner 2026-10-06); `repair.py --open-units U` lets any window district take ZCTAs of U even with `--keep-support` (an arm-2 split, one more allowed per unit).
**(b)–(c)** As §2/§4; only the family or the repair cap changes.
**(d)** Contiguity as §4.
**(f)** Round 1 "ne5" bans (CT-NJ, MA-NJ, NJ-VT, CT-PA, MA-PA) and round 2 "+DE-NJ": no map passes M1; best `nocomb_13_12_23-replan-ne5dn-r2` has 2 pieces and 1 neck, all in national_08 (DC+NC+NJ+PA+VA+WV) (docs/RESULTS.md:820 `- **No map passes M1**, so the round-2 worker rendered no deck or ZIP pages; #120's renderer`; docs/RESULTS.md:822-826). DE-NJ removed the Delaware Memorial Bridge neck but pushed DE into long districts cut off around Philadelphia and Baltimore (docs/RESULTS.md:828-830). Round 3: owner's short split lists (national/WH/WIFI split only CA FL NY TX, FI also PA OH) cut splits by more than half (scorer 28–29 → 11–12), but "every map stops at the re-plan" at the declared band; smallest feasible δ FI 0.1273 (nocomb) (docs/RESULTS.md:856 `**Step 1, at the declared band: every map stops at the re-plan.** In each map some channel has no`); after the owner widened to ±15%: still no M1 pass, every failure in the Northeast corridor (docs/RESULTS.md:871, 888).
**(g)** Bans "chase the neck around the map" (notes/2026-10-13_ifa-split-state-constraints.md:58-59 `"Hand bans of state pairs ... chase the neck around the`) — ne5 made ifa_49 worse (7 → 15 pieces, 10 → 17 necks) (notes/2026-10-13_ifa-split-state-constraints.md:55 `on ifa_49, ne5 made things worse (7 pieces → 15, 10 necks → 17, band broken;`).
**(h)** A pair ban is a family *restriction*: a "no plan" after bans bounds nothing; there is no certificate that the removed supports are undrawable.

### 5.2 #124 A (width-aware contact), B (drawable alone), C (close the loop)

**A.** Replace "G[S] connected" by "S connected in its contact graph C(S)": u,v ∈ S touch iff the summed floored-cm border between their ZIP-edges ≥ W = 10 km (= 1,000,000 cm) or an approved connector joins them that the *pre-2026-10-14* land rule leaves unlimited within states(S) (td/supports.py:117 `need = round(ch.spec.contact_min_km * 1e5)`; td/supports.py:128 `if b in ng.connector.get(a, ()) and not ng.land_would_do(a, b, states[u] | states[v]):`). The family stays closed under subsets connected in their own contact graph (docs/MODEL.md:112-116). **Result: removes no support on any measured map** — every adjacent pair of planning units shares ≥ 10 km of land border (docs/RESULTS.md:989-992 `- A removes no support: every adjacent pair of planning units shares at least 10 km of`).

**B.** For a support S with |S| ≥ 2 define D_c(S, δ) = the ZIP sets X ⊆ ∪_{v∈S} Z_v with (a) Z_v ⊆ X for held v, (b) Σ_{X∩Z_v} m_z ≥ η M_v for free v, (c) mass(X) ∈ [L_c, U_c], (d) X connected, (e) X has no M1 neck. **Proposition B** (docs/MODEL.md:387-390, "proved, Sol verifier"): D_c(S,δ) = ∅ ⇒ n̂_S = 0 for the read-back of every drawing in 𝒳^N_c(δ); so n_S = 0 is a valid row. `plancheck.drawable` decides D = ∅ by one MILP on S's ZIPs (x_z for free units, held components contracted, single-commodity flow from the heaviest body or a chosen root, wide-passage flows between held bodies, lazy `NeckCut` rows), "infeasible" only on a HiGHS proof, a timeout/unknown never adds the row (docs/MODEL.md:404-444). **Result: cuts nothing**; every support tested was found drawable or unknown (docs/RESULTS.md:994 `- B cuts nothing, so A+B's plans equal A's, and A+B reuses A's folder (`reuse.json`).`; docs/RESULTS.md:1038 `B finds them drawable or unknown,`) — B asks whether *some* single district with footprint S exists, not whether the other districts leave it the land it needs (notes/2026-10-13_ifa-split-state-constraints.md:112-116).

**C.** After a drawing and repair, a district left in pieces/necked whose *last* repair window was proved infeasible gets its exact support banned (n_S = 0), re-plan, redraw, up to R rounds (docs/MODEL.md:452-461). The ban is a *policy*: a window's infeasibility is conditional on everything outside it being fixed. **Result: bans nothing** — no remaining piece or neck had a last window proved infeasible (docs/RESULTS.md:995-997); on the 2026-10-13 main grid the loop "bans moved pieces, never cleared them (w1-50-wide got worse: 4 pieces/8 necks)" (notes/2026-10-13_overnight-grid-to-regional-sealing.md:20 `bans moved pieces, never cleared them (w1-50-wide got worse: 4 pieces/8 necks). Abandoned.`).

**(h) soundness, A/B/C.** (i) A, plancheck and `repair.neck_cuts` read the *old* connector rule (docs/MODEL.md:884-889), so they are stricter than the gate. (ii) B is necessary-only (C10, docs/MODEL.md:617-626). (iii) C's bans are not necessary conditions, so the master "with C bans bounds nothing" (docs/MODEL.md:459-460 `with C bans bounds nothing. Each ban names the exact unit set, the channel, the window (attempt,`).

### 5.3 #127 whole-unit plans checked against M1 at plan time (IFA only)

**(a)–(c)** Drop `free` so every unit is whole; each round: δ* = `master.exact_delta` with the bans so far, *no cap on δ*; plan at δ*; for each support in use run `district_pieces` + `district_necks` on its ZIP union; ban every failing support as its exact unit set; repeat until all pass (tools/exp/contig/wholeplan.py docstring). Optional `pieces.py` cuts a state into round(m/τ) connected county groups, each passing M1, by seeded growth and border moves over 100 attempts.
**(d)** M1 exact by construction (district = union of whole units/pieces; the gate is the check).
**(f)** All six IFA maps pass the gate; none is eligible: the master's δ* is 0.43–3.10 (band ±43% … ±310%) because whole states and county pieces cannot be balanced (docs/RESULTS.md:1236-1240, 1244-1249).
**(h)** Exactness of "ban the failing support" is sound as a *column filter* (an M1 failure of a whole-unit district is a fact about its ZIP set, not about the rest of the map) — consistent with the district-locality claim (§16 C1); the cost is the band.

## 6. #125: the `ne_plains` layout at every $-eligible K (2026-10-07)

**(a)–(c)** The §2 master per channel at its smallest δ ≤ final δ = 0.10; `set125.sh`: replan → `run.py --arm arm1 --sequential` → `repair.py --keep-support --flow` (pass r1, r2, and for FI 19 a third). Variants differ by split list (WH without NJ, FI without TN/NC).
**(d)** As §4 (arm 1, sequential draw; repair with flow and neck cuts). **(e)** Master "converged" smallest δ per K; repair windows 600 s / 300 s.
**(f)** Plans at ±10%: national 15 only (13: 0.1054, 14: 0.1201, 15: 0.0888), WH 11 only, FI 19 and 20 (21: 0.1008, 22: 0.1352 > 0.10), WIFI 3 only (docs/RESULTS.md:925-928). Six FI-20 variants and the lead map pass M1 after one repair pass; FI 19 fails M1 on one 68-ZIP DE piece (docs/RESULTS.md:950, 964-966).
**(g)** These "ELIGIBLE" verdicts were judged under the old averaged dollar rule and the pre-2026-10-14 neck rule: the later dollar audit puts them outside the new windows — national 13/15, WH 10/11 in window, FI 20/20, WIFI 3/3 (notes/2026-10-13_ifa-to-national-orientation.md:31 `both tier-P seeds (`ne_plains_wh11_fi20_finonc_whnonj`, `…_whnonj`) fail D3 dollars identically`), and the owner's national floor was later lowered from $1,062.5M to $1,000M to make K 16 reachable (notes/2026-10-12_main-map-joint-wifi-grid-research.md:108 `With national's old $1,062.5M floor, national stopped at 15 and every district above it had to come from FI`).
**(h)** "Plans at ±10%" is the symmetric-band feasibility of §2 (h.1).

## 7. Joint WIFI-footprint × K grid, 21 points, per-channel dollar windows (2026-10-13, `m5-studio/national-overnight`)

**(a) What varied.** A grid point = (structure s, K vector k): s ∈ {ne_plains, west8, nw49, nw34, w1} (§0.2), total Σ k_c ∈ {48, 49 (comparison), 50, 52}, WH K ≥ 8, "balanced" vs "FI-light" pairs (notes/2026-10-12_main-map-joint-wifi-grid-research.md:111 `Settings for every point: dollar-scaled masses and per-channel dollar windows (B1); land balance in the draw at R = 10`; tools/exp/contig/overnight.py:143-161 `_point("ne-48-bal", "ne_plains", national=14, WH=10, FI=21, WIFI=3),`). K_c is window-feasible iff L_c < $_c/K_c < U_c (§0.3).

**(b) The planning band (the restriction that later proved binding).** For each channel the final δ is the largest δ (to 1e-4 below) with τ(1−δ) ≥ L and τ(1+δ) ≤ U:
```
δ_fin = ⌊ 10⁴ · min(τ − L, U − τ) / τ ⌋ / 10⁴      (K_c = 1: 0.10 if L ≤ τ ≤ U)
band  = [τ(1 − δ_fin), τ(1 + δ_fin)]  ⊆ [L, U], symmetric about τ
```
(tools/exp/contig/overnight.py:264 `d = math.floor(min(tau - lo, hi - tau) / tau * 1e4 + 1e-9) / 1e4`). `U` is the $1.6B whole-state cap for a channel with no split unit and a cap (WIFI) (tools/exp/contig/overnight.py:290 `lo, hi = window[0] / 1e6, (score.WHOLE_STATE_CAP[c] if whole else window[1]) / 1e6`). Declared δ = min(0.02, δ_fin); `replan.py` plans at the declared δ, else at the master's smallest feasible δ if ≤ δ_fin, else stops (tools/exp/contig/overnight.py:168 `DECLARED_DELTA = 0.02           # set125's declared δ: replan.py takes the smallest up to the final δ`). The split list is the base spec's (ne_plains, west8) or the #76 rule: units with $ > τ/2 (tools/exp/contig/overnight.py:283 `free = sorted(u for u, m in mass[c].items() if m > tau / 2)`).

**(c)–(e)** Chain per point: replan (10 min per channel), `run.py --arm arm1 --sequential --land-ratio 10` (75 min per channel, one retry at plan δ + 0.05 on `infeasible`/`unknown`), `repair.py` pass 1 (30 min/channel) and pass 2 only if M1 fails, then gate + scorer dollar windows; a dollar-gate failure re-runs once at K ∓ 1 (tools/exp/contig/overnight.py:171 `DRAW_S = 4500.0                 # run.py --time-limit: 75 min per channel`; tools/exp/contig/overnight.py:174 `REPAIR_S = 1800.0               # repair.py --budget: 30 min per channel per pass`). The `-wide` siblings floor δ at the master's smallest feasible δ, up to 0.35 (tools/exp/contig/overnight.py:304 `WIDE_MAX = 0.35                 # a -wide point's floor stops here: a wider band is no territory`), so their planned districts need not lie in the window.

**(f) Output.** 20 of 21 points have no plan inside their windows; the 17 `-wide` siblings all fail M1 with 13–22 districts outside the windows; the one in-window point `ne-48-bal` gave `r2` with 0 pieces, 1 neck (Delaware Memorial Bridge, 5.67 km under the *old* connector rule), 48/48 in window (docs/RESULTS.md:1320-1322).

**(g) Why it failed.** (1) Planning inside a symmetric sub-window failed for 20 of 21 points (docs/RESULTS.md:1320); widening the band (the `-wide` points) moved districts out of the window; (2) the unsealed master pairs states whose drawn shares never touch, giving recurrent pieces at NYC, DC, New England and the Delaware bridge (notes/2026-10-13_overnight-grid-to-regional-sealing.md:37 `**Root cause of the main-map pieces**: the unsealed support master pairs states whose drawn shares never touch`).

**(h) Soundness questions.**
  1. The symmetric band is a strict subset of the window unless τ is the window's midpoint, so "no plan inside the band" is a statement about a *restriction* of the owner's constraint (td/master.py rows with lo=1−δ, hi=1+δ). The next stage (§10) removed the restriction and every point planned.
  2. The final-δ rounding is downward to 1e-4, so the band is slightly smaller than the largest symmetric band: harmless but it means the "no plan" verdicts are at ≤ δ_fin, not at the window.
  3. The `-wide` points' dollar failures are by construction (band wider than the window).
  4. **A second restriction on 15 of the 21 points.** The 2026-10-13 launcher writes K and δ into the base spec but not `margin`, and the base specs of west8, nw49, w1 and nw34's WIFI channel have no `margin` key, so their band rows carry the rounding margin μ_S > 0 (td/master.py:165 `rows.append(Row("band_lo", (s,), {**mass, n: -(lo_band + mu)}, 0.0, math.inf))`); I checked the spec copies `runs/exp/main_overnight_2026-10-13/w1-48/spec.toml` and `.../nw49-48/spec.toml`: no `margin` line (runs/exp/main_overnight_2026-10-13/nw34-48/spec.toml:31 `margin = false` is the national channel only; runs/exp/main_overnight_2026-10-13/ne-48-bal/spec.toml:21 `margin = false` is one of four, one per channel). μ_S is a policy that "removes plans that could be drawn" (docs/MODEL.md:293 `- **A policy.** It removes plans that could be drawn, and it can make lumpy units infeasible at`). So "no plan inside the window" for those 15 points confounds the symmetric band with μ_S > 0; I did not quantify μ_S.

## 8. Regional-seal quick test (2026-10-13, `m5-studio/regional-seal`) and the IFA pipeline it copies

**(a) What sealing is.** A partition 𝒫 of the footprint states of a channel into regions r with K_r districts each, Σ_r K_r = K_c; region r is planned and drawn on the polygon graph *induced on its states* (`run.py --states`; docs/CODE_MAP.md:77 `the polygon graph induced on NJ keeps NJ's shipped vertices and no edge, border or connector leaves it`) with `margin = false`, and the merged map is re-gated on the full graph (tools/exp/contig/merge.py:3 `merged into one run folder and audited as one map, so a`; tools/exp/contig/merge.py:27 `The merge invariant: every district keeps its exact ZCTA set; every (ZCTA, fine channel) cell has`). No district can hold a state outside its region.
**(d)** As §4 inside each region (region-induced graph), then the full-graph gate. **(b)–(e)** Per region the §2 master with `max_size` 1–6, K_r chosen so τ_r is in the window, drawn (§4.1) and repaired (§4.3) with `--window` clipping the final band to the absolute dollar window; one HiGHS thread per process.
**(f) w1-50-wide test.** Regions CT+RI K1, MA+ME+NH+VT K1, NY K5, NJ+PA K5, DC+DE+MD+VA K3 (DE–VA forbidden), rest unsealed: gap-width M1 2 pieces/2 necks → 1 piece/1 neck (both NYC); sealed districts outside the $ window 6/15 → 0/15; whole map 16 → 10 outside, all in the unsealed part; cost: split states 11 → 13, multi-state districts 16 → 18, worse land ratios (docs/RESULTS.md:1323). The owner chose regional sealing for the main map (notes/2026-10-13_overnight-grid-to-regional-sealing.md:22 `**Owner decision (2026-10-13 ~14:40): go with regional sealing for the main map.**`).
**(g) Limits found:** NJ alone has no K with τ in window → NJ+PA; DC+DE+MD+VA needs a DE–VA forbid; `margin = false` or NY's master is infeasible; NY+NJ K 7 hung HiGHS ~2 h past its limit (notes/2026-10-13_overnight-grid-to-regional-sealing.md:39 `NJ alone has no K with τ in window → NJ+PA (K 5); DC+DE+MD+VA needs a DE–VA forbid pair; `margin = false``). Within-state necks sealing does not touch: Cincinnati/KY, Utah 84621, El Paso, LA/SF, NJ 08505-08611 (notes/2026-10-13_overnight-grid-to-regional-sealing.md:40).
**(h)** (i) Sealing is a restriction of the unsealed model, so any sealed feasibility result is a lower-feasibility statement; the unsealed 10-14 day run (§10) found all 15 points plannable in the window, so the sealed regions' failures are not failures of the problem. (ii) The merge keeps each source's exact ZCTA set and cannot create a piece (inferred from the invariant); necks can change because relays (R3) come from other regions' zero-opportunity ZCTAs.

**The IFA pipeline (reference, `m5-studio/ifa-conus`, not on main):** per state/region `run.py --states <ST> --delta 0.15` (spec copies with K per region, `margin = false`, δ = final δ = 0.15, `max_size = 1`), `coarse.py` (NY by congressional/state-senate units), `repair.py --states --window LO,HI` clipping every channel's final band to the absolute window, `merge.py --window --gap-width --export` (notes/2026-10-13_ifa-to-national-orientation.md:9 `Spec copies per state have `k` per state, `margin = false`, `delta/final_delta = 0.15`, `max_size = 1`.`; notes/2026-10-13_ifa-to-national-orientation.md:11 `**`tools/exp/contig/repair.py <run> --states <ST> --window LO,HI`). Note what IFA's per-region band was: ±15% planning, then the *absolute* window in repair — not a symmetric fit inside the window (inferred from those two lines).

## 9. Sealed driver, 15 grid points (2026-10-14 night; `m5-studio/sealed` 4963113, run on snapshot 43ca971)

**(a) Sets.** Per channel an explicit partition of its footprint into *connected* regions (State graph = polygon cross-state edges incl. connectors), each with its own K_r (Σ_r K_r = K_c) chosen to maximise min_r `fit_delta` over regions, and the corridor regions (NY NJ PA DE MD DC [+VA, +New England]) kept; channels' state sets must be equal-or-disjoint (runs/exp/sealed_2026-10-14/partitions2/README.md `K chosen per channel to maximise the minimum `overnight.fit_delta` over the components`).
**(b) Per region** (m5-studio/sealed:tools/exp/contig/sealed.py module docstring): spec copy with K_r, `margin = false`, final δ = `fit_delta(τ_r, K_r, L, U)` (the symmetric fit of §7(b); m5-studio/sealed:tools/exp/contig/sealed.py:33 `gives the region's τ (region $ over`) with τ_r = region $/K_r; **`--drawable-alone` on by default** (m5-studio/sealed:tools/exp/contig/sealed.py:43 `(#124 B) is on by default (`; the master plans only supports `plancheck.drawable` accepts); drawing `run.py --states` arm 1 sequential, land R = 10; **strict**: a channel with undrawn ZCTAs or a group status other than optimal/connected is a failure and "a failed drawing is never repaired or merged" (m5-studio/sealed:tools/exp/contig/sealed.py:50 `failure, and a failed drawing is never repaired or merged`); then `repair.py --states` r1/r2, `glue.py`, `merge.py`, gate, scorer.
**(c) Objective/solver.** As §2/§4. Caps: replan 600 s, draw 2,700 s (0.85 per channel), repair 1,800 s (m5-studio/sealed:tools/exp/contig/sealed.py:135 `DRAW_FRAC = 0.85                # run.py's per-channel time limit, of the draw's wall cap`; m5-studio/sealed:tools/exp/contig/sealed.py:133 `CAPS = {"replan": 600.0, "draw": 2700.0, "repair": 1800.0, "glue": 600.0, "combine": 600.0, "merge": 3600.0,`).
**(d) Contiguity.** As §4 within a region; cross-region contiguity is moot (no district crosses a region); merge re-gates on the full graph.
**(f) Output.** IFA K48–54: all seven pass (§13). Main map: 1 of 15 points has a passing map — `ne-48-bal`, the *unsealed* 10-13 r2 re-judged — and the 14 other points no sealed map: the east block (20–21 states) "has no plan inside its band" in national (K 6–7) or WH (K 5–6); nw49 36-state rest and nw34 rests "no plan inside its band"; w1 36-state rest planned at ±2% "no connected drawing", 14,859–16,571 ZCTAs undrawn; the corridor's coupled NY group timed out at about 337 s per channel in round 1 (runs/exp/sealed_2026-10-14/MORNING.md:13 `Round 1 (first partition) also timed out drawing the coupled New York group of the corridor`; runs/exp/sealed_2026-10-14/MORNING.md:9 `**w1-48, w1-50, w1-52:** the big rest region (36 states, WIFI, band about`; docs/RESULTS.md:1347).
**(g) What bound it.** "One symmetric band per region ... is the binding limit; regions whose blocks differ in $ density cannot fit even when each district could sit in the window" (docs/RESULTS.md:1348). Tested and *not* the cause: split lists (more splits still infeasible), `max_size` 6, `--drawable-alone` off (runs/exp/sealed_2026-10-14/MORNING.md:61 `- **Not the cause (tested):** the split lists (allowing more splits is still infeasible), the maximum district size (6, still infeasible), the drawable-alone`). Sealing also removes the corridor states the unsealed plan used as fillers (runs/exp/sealed_2026-10-14/MORNING.md:64).
**(h) Soundness questions.**
  1. The "binding limit" is inferred from the later unsealed window-band result, not tested on the sealed partitions: I find no run that combines sealed partitions with the window band (STATUS.md of the day run lists only unsealed launches, runs/exp/national_2026-10-14/STATUS.md:2).
  2. K_r are allocated by *arithmetic* (region_arith), "no feasibility certificate" (tools/exp/region_arith.py:2 `no feasibility certificate: no MILP over ZIPs, no run).`); the "forced splits" in it are valid lower bounds only against the window top (`forced_top`) (tools/exp/region_arith.py docstring, three tracks).
  3. Sealing forbids cross-region supports, so Σ_r K_r = K_c and every region's blocks must each tile into districts of mass in the window: a *necessary* feasibility condition per connected block is τ_block ∈ [L, U]-compatible allocation (the "parts floor", tools/exp/split_floor.py docstring `each connected component of the channel's units ... takes a whole number k_i ≥ 1 of districts`). That is a sound necessary condition (a district cannot cross components) but not sufficient.
  4. `drawing_failures` makes any non-optimal/non-connected group a *run failure*: a time-limit "unknown" is treated as a failure of the point, so the label "no connected drawing" does not distinguish infeasible from slow (m5-studio/sealed:tools/exp/contig/sealed.py:140 `DRAWN_OK = ("optimal", "connected")        # a group or channel drawing the owner accepts (2026-10-14: contiguity at the solver)`).

## 10. Unsealed national grid with the window band (2026-10-14 day; `m5-studio/window-band` 8a22136)

**(a) What changed vs §2/§7.** For channel c with `band_lo` = L_c/τ_c, `band_hi` = U_c/τ_c, 0 < band_lo < 1 < band_hi (WIFI: U := $1.6B when no split unit):
```
master    band_lo · n_S ≤ Σ_{v∈S} (M_v/τ) t_{v,S} ≤ band_hi · n_S        (μ_S = 0, margin = false)
draw      F_j + Σ m_z x_{z,j} ∈ [τ·band_lo, τ·band_hi] = [L_c, U_c]
repair    final band [τ·band_lo, τ·band_hi];  audit's final band the same
δ         only a report: δ_equiv = max(1 − band_lo, band_hi − 1); no wider retry
```
(m5-studio/window-band:td/master.py:152 `lo_band, hi_band = cs.rel_band(delta)`; m5-studio/window-band:td/spec.py:149 `return self.window or (1.0 - delta, 1.0 + delta)`; m5-studio/window-band:td/spec.py:144 `return None if self.band_lo is None else max(1.0 - self.band_lo, self.band_hi - 1.0)`; m5-studio/window-band:tools/exp/contig/draw.py:295 `delta, wider = ch.spec.window_delta, ()`.) `master.window_feasibility` solves the window once and reports (method `window`); `exact_delta`/`bisect_delta`/`smallest_delta` all route to it (m5-studio/window-band:td/master.py:451 `def window_feasibility(inst, channel: str, fam=None, time_limit: float | None = None,`). Each spec key is written with `repr` so the window is exact (m5-studio/window-band:tools/exp/contig/overnight.py via `window_keys`).
**Unsealed**, `--drawable-alone` off, strict drawing, glue, 2026-10-14 gate, split rule R1 (the structure's own list R0 ∪ {units with $ > τ/2}; runs/exp/national_2026-10-14/probes/split_rules.md:4 `Rules in order: R0 the structure's own list`) on ne-50/52-filight national and ne-52-bal FI, nw49 national `max_dist_km` 1500 (runs/exp/national_2026-10-14/STATUS.md:2 `LAUNCHED from m5-studio/window-band 8a22136`; docs/RESULTS.md:1355-1357; runs/exp/national_2026-10-14/probes/split_rules.md).
**(c)–(d)** Objective and solver as §2/§4; contiguity as §4 on the full graph (unsealed). **(b)** The per-channel master for ne-48-bal: bands national [0.8286, 1.1911]τ, WH [0.8384, 1.1343]τ, FI [0.8682, 1.1746]τ (runs/exp/national_2026-10-14/main/ne-48-bal/rest-FI-WH-national/spec.toml: `band_lo = 0.828612424521089`, `band_hi = 1.1911303602490653`, …); WIFI (K 3, no split unit) band [850, 1,600]/τ (spec `final_delta = 0.424341` in rest-WIFI).
**(e)** Master per channel: ≤ 0.43 s, optimal, gap 0 (§2). Draw time limit per channel 0.85 × 6,000 = 5,100 s at launch (runs/exp/national_2026-10-14/STATUS.md:2 `caps replan 1500 s / draw 6000 s, --hours 10`), then 0.85 × 36,000 s with repair 3,600 s in the relaunch (runs/exp/national_2026-10-14/STATUS.md:4 `Relaunched those 5 into main_r2/ with draw cap 36000 s`).
**(f) Output.** *Planning*: all 15 points plan inside the window (docs/RESULTS.md:1357). *Drawing*: the exact drawing of large coupled groups does not finish. First-attempt group sizes in the ne_plains points (free ZCTAs, districts, columns, rows, seconds, status; runs/exp/national_2026-10-14/main/<point>/rest-FI-WH-national/draw/contig.json):

| point / channel | group (unit) | free ZCTAs | districts | columns | rows | s | status |
|---|---|---|---|---|---|---|---|
| ne-48-bal FI | PA | 1,833 | 4 | 12,115 | 35,484 | 4,341 | unknown, no incumbent |
| ne-48-bal FI | CA | 1,803 | 2 | 8,075 | 17,939 | 139 | connected |
| ne-48-bal national | CA | 1,803 | 4 | 11,693 | 34,070 | 4,578 | connected |
| ne-48-bal national | NY | 1,826 | 2 | 8,340 | 18,474 | 358 | connected |
| ne-cmp-tierP FI | PA | 1,833 | 3 | 10,275 | 27,056 | 4,941 | connected: "time limit: the constructed drawing stands" |
| ne-cmp-tierP national | NY | 1,826 | 2 | 8,340 | 18,455 | 5,070 | connected: "time limit: the constructed drawing stands" |
| ne-50-bal FI | FL | 1,013 | 3 | 5,619 | 14,772 | 4,615 | unknown, no incumbent |

The undrawn ZCTAs then carry the non-contiguous fallback owners (td.realize + td.territory). The undrawn counts reported per point are exact sums of whole free-unit groups (verified by me against the group sizes in the same `contig.json` files: PA 1,833, NY 1,826, CA 1,803, TX 1,989, FL 1,013, OH 1,233, TN 638, NC 853, NJ 598): ne-48-bal FI 3,659 = PA + NY; ne-50-bal FI 7,708 = FL + NY + PA + OH + CA; ne-cmp-tierP and ne-50-filight FI 1,826 = NY; ne-cmp-tierP national 3,792 = CA + TX; ne-50-filight national 1,803 = CA (counts: runs/exp/national_2026-10-14/INDEX.md:27 `FI 3,659 (PA group DC+PA+VA+WV, DE+MD+PA, NJ+PA, PA)`, :28 `FI 1,826 + national 1,803 = 3,629`, :29 `FI 1,826 + national 3,792 = 5,618`, :72 `7,708 FI + 3,792 national ZCTAs heuristic-placed`; the INDEX labels the 3,659 as the PA group only, while 3,659 = 1,833 + 1,826 includes NY — my arithmetic, inferred). The groups are drawn one after another inside a channel's time limit, so a group that consumes the limit leaves the later groups, easy ones included, undrawn (inferred from the group lists above: ne-50-bal FI lists only TN, NC, FL). Every first attempt ended "no connected drawing"; the long retries were stopped by hand with those draws unsolved (runs/exp/national_2026-10-14/INDEX.md:14 `The exact drawing did not finish for large coupled groups`).
**(g)** Binding: exact drawing of coupled groups with 2–4 districts on 1,000–1,850 free ZCTAs (columns 5.6–12k, rows 15–35k). The master does not bind.
**(h)** (1) The window-band master's *infeasibility* would still be a statement about the §2 family only (R1, `max_dist_km` and `max_size` were relaxed per point to get plans). (2) Proposition D's proof is for the symmetric band; the window version replaces lo/hi by the owner's constants and uses nowhere a symmetry of the band (inferred; docs/MODEL.md has the §4.6a policy text but no restated proof, m5-studio/window-band:docs/MODEL.md §4.6a).

## 11. Warm start (2026-10-14 evening; `m5-studio/warm-start` 53dac30)

**(a) Procedure** (m5-studio/warm-start:tools/exp/contig/warm.py module docstring). Input D⁰: the first attempt's full ledger, in which every group `draw.py` left undrawn is filled by the non-contiguous fallback (td.realize + td.territory). Then
  1. `repair.py` pass r1 (`--keep-support --flow`, windows around detached pieces and necks, final band = the channel's dollar window), r2 if a channel still has pieces/necks;
  2. `glue.py`: for a district with a detached piece, the shortest path from the piece to its other ZCTAs through ZCTAs of *zero mass in the channel* held by other districts; applied only if no donor gains or enlarges a piece or neck; never moves a ZCTA of positive mass (m5-studio/window-band:tools/exp/contig/glue.py:10 `and is held by another district of the run; the path goes to the district.  It is applied only if`; m5-studio/window-band:tools/exp/contig/glue.py:17 `channel is never moved, and the check at the end of `glue_channel` stops the run if one was.`);
  3. merge, gate (gap-width and strict), dollar windows scored on the *full* dollar extract (the merged extract overstates FI by ~2%: runs/exp/national_2026-10-14/INDEX.md:89 `Dollar scoring:`)
**(b)–(e)** Repair model and objective as §4.3 (contiguity (P) exact inside windows, (N) by NeckCut; HiGHS, 1,500 s windows); glue is a BFS, no optimisation. The deliverable rule: "the final exact gate shows every district contiguous ... and in its window" (m5-studio/warm-start:tools/exp/contig/warm.py:24 `(owner's rule, relayed 2026-10-14: the final exact gate shows every district contiguous, Manhattan the only`).
**(f) Output.** 3 passing main maps, each with 3,629–5,618 ZCTAs placed by the realizer heuristic and verified only by the gate: ne-48-bal (K 48; M1 pass/pass; 48/48 in window; 8 split states), ne-50-filight (K 50; gap-width pass, strict fails on 2 necks; 50/50; 9 states), ne-cmp-tierP (K 49; pass/pass; 49/49; 8 states) (runs/exp/national_2026-10-14/INDEX.md:92 `Passing maps contain heuristic-placed ZCTAs (3,629 to 5,618): gate-verified, not drawn by the exact`; docs/RESULTS.md:1359 `**3 passing main maps**: ne-48-bal (pass/pass, 48/48 in window, 8 split states), ne-50-filight (gap-width pass, strict fails on 2 necks; 50/50; 9 states), ne-cmp-tierP (pass/pass, 49/49; 8 states).`). Fails: ne-50-bal and ne-52-filight (FI_19 NY in 4 pieces, 104/29/3/1 ZIPs, largest 0.263 τ), ne-52-bal (FI_18 NY 21 ZIPs, FI_07 NJ 7 ZIPs), nw49-48/52 (a 9-ZIP NY piece), nw34 ×3 (national never drew), w1 ×3 (never drew) (docs/RESULTS.md:1360 `**Fails:** ne-50-bal and ne-52-filight (FI_19 NY in 4 pieces), ne-52-bal (FI_18 NY, FI_07 NJ), nw49-48/52 (a 9-ZIP NY piece in WIFI); nw34 x3 national never drew; w1 x3 never drew before the stop.`).
**(g)** NY windows ended `unknown` at their time limit (up to 1,500 s) in r1–r3; the pieces are inside the group the exact draw never solved.
**(h) Soundness questions.**
  1. The passing maps are certified only by the gate; the heuristic-placed zones carry no optimality or split-minimality statement; their shape is the power-diagram's (FI_06, FI_07 flagged by the shape study sit in the heuristic PA group, runs/exp/national_2026-10-14/INDEX.md:92-94, "no link is claimed" for the other two maps).
  2. Gate-pass depends on the 2026-10-14 neck rule (R1, R3). ne-48-bal/r2 had 1 neck under the 10-13 rule (docs/RESULTS.md:1322) and 0 under the 10-14 rule (docs/RESULTS.md:1346); `ne-50-filight` still fails strict.
  3. Because each district's M1 status is local (§0.5), a passing ledger can be judged district by district; the glue step's "no donor failure grows" test relies on that locality (m5-studio/window-band:tools/exp/contig/glue.py docstring).

## 12. Carve-first (parallel track; in progress, other session — only what is committed)

**Status.** Nothing is built. `m5-studio/carve-first` @ b1e047b holds the 2026-10-07 method draft and two notes; there is no `tools/exp/carve/` (checked on the branch tree and the worktree `td-carve-first`, clean). The method was "adopt with changes" in round 3 and "never built" (notes/2026-10-14_carve-first-lite-handoff.md:13 `Reviewers voted "adopt with changes" in round 3 on 2026-10-07; it was never built.`). The lite design is "drafted in chat 2026-10-14, **not planned or started**" (notes/2026-10-14_carve-first-lite-handoff.md:8).

**(a) Sets and variables** (docs/archive/lenses/review-2026-10-07/METHOD-carve-first.md): a *column* g = a connected set of whole states whose dollar mass is in [L, U] and whose ZIP union passes the exact M1 gate (library, "A failure is a fact about g, never a ban on anything else"); a *pattern* p for a state σ = a partition of σ's ZCTAs into k_p pieces, piece i with an attach set A_i of whole states, each piece ∪ A_i passing the gate and in [L, U], the attach sets disjoint and containing neither σ nor another split state (rule C built in) (docs/archive/lenses/review-2026-10-07/METHOD-carve-first.md:28 `The attach sets are disjoint, and none contains σ or another split state, which is rule C`). Binaries x_g, y_p.

**(b) Selection MILP (set partitioning).**
```
Σ_{g∋v} x_g + Σ_{p: v ∈ σ(p) ∪ A(p)} y_p = 1      ∀ state v          (each state covered once)
Σ_g x_g + Σ_p k_p y_p = K
```
(docs/archive/lenses/review-2026-10-07/METHOD-carve-first.md:36 `Each state v is covered exactly once: Σ_{g∋v} x_g + Σ_{p: v∈σ(p)∪A(p)} y_p = 1.`; docs/archive/lenses/review-2026-10-07/METHOD-carve-first.md:39 `Districts: Σ x_g + Σ k_p y_p = K.`).

**(c) Objective.** Lexicographic: splits Σ y_p, cuts Σ (k_p − 1) y_p, defects and shape, then balance (worst column deviation by an epigraph row) (docs/archive/lenses/review-2026-10-07/METHOD-carve-first.md:40 `Objective, lexicographic: splits Σ y_p, then cuts Σ (k_p − 1) y_p, then defects and shape,`). Shape limits and the band act as *column filters* at selection time (notes/2026-10-14_carve-first-lite-handoff.md:26).

**(d) Contiguity/M1.** Per column, by the exact gate at generation; "Keep only passing columns"; the assembled map is gated again and "a gate failure here is a bug, not a ban" (notes/2026-10-14_carve-first-lite-handoff.md:27). The carver for split states is to generalise `coarse.py`'s flow MILP to the state-senate grain with attach sets contracted to roots (notes/2026-10-14_carve-first-lite-handoff.md:24 `Generate them at the state-senate (sldu) grain by generalising`).

**(e) Sizing / certificate / growth.** `tools/exp/region_arith.py` (landed) gives per channel and K the feasible K, forced splits, the whole-state library size at caps 4/6/none, carving jobs and rule-C orphans (notes/2026-10-14_carve-first-lite-handoff.md:51). Certificate: if the library MILP's s_drawn equals the master's s_lower the map is "proved fewest-splits (in the stated domain)" (METHOD-carve-first.md:45). Growth: duals of the coverage rows price new patterns; unknown carves leave the library unchanged (METHOD-carve-first.md:47-54).

**(h) Soundness questions I notice.**
  1. *Locality.* The scheme is sound only because M1 and the dollar window are district-local (C1 in §16). Then a set of columns/patterns that exactly covers the footprint is M1-feasible iff every column passes.
  2. *Certificate domain.* s_lower is the §2 master's bound, valid only "over 𝒳_c(δ)" (PROBLEM.md:208 `A floor from a master with η > 0 bounds only the drawings that follow its family, modes, η and caps;`); under rule C the library's domain is further restricted, so "proved fewest-splits" needs the η-free, all-M1 bound (#119), which is not built.
  3. *Rule C* excludes any district with two split states; the drawn passing maps do contain such districts in two of three cases (§16 C22), so rule C is a restriction of what has been drawn, and `region_arith` counts "rule C orphans" (states no column or attach set can take) (tools/exp/region_arith.py docstring, whole-state groups paragraph). Whether orphans exist for the main-map footprints at K 48–52 is exactly its Phase 0 question (not run for this note).
  4. *WIFI window.* The METHOD file says the WIFI band depends on K_WIFI (E3) (METHOD-carve-first.md:70); the scorer's WIFI window is fixed at [850, 1,150] with the $1.6B whole-state allowance (tools/looks/score.py:109-111). Code wins.
  5. *Library completeness* is an open size/coverage question (METHOD-carve-first.md:65-67).

## 13. IFA-origin tools (not used on the main map; included because they are the only ZIP-contiguity machinery that worked for IFA)

  - **`coarse.py`** (single-state channel): ZCTA → the TIGER state-senate/congressional district holding most of its land; coarse units = components; the partition MILP groups units into K connected groups of mass in [lo, hi] with minimum total border. Variables x_{u,h}, r_{u,h} (root), f_{a,h} (flow ≤ (n−1) on owned arcs), y_e (cut adjacency); rows Σ_h x_{u,h} = 1; lo ≤ Σ_u mass_u x_{u,h} ≤ hi; Σ_u r_{u,h} = 1; r ≤ x; f_{a,h} ≤ (n−1)x_{s,h}, ≤ (n−1)x_{t,h}; inflow − outflow ≥ x_{u,h} − n r_{u,h}; y_e ≥ |x_{a,h} − x_{b,h}|; min Σ_e (border_km_e + 1e-3) y_e (tools/exp/contig/coarse.py:172 `add([(X(u, h), mass[u]) for u in range(n)], lo, hi)`; tools/exp/contig/coarse.py:181 `add([(F(a, h), 1), (X(s, h), -(n - 1))], -np.inf, 0)`; tools/exp/contig/coarse.py:184 `add([(F(a, h), 1) for a in in_arcs[u]] + [(F(a, h), -1) for a in out_arcs[u]]`; tools/exp/contig/coarse.py:206 `c[Y(e)] = g["edges"][a, b] + 1e-3      # tie-break: fewer cut adjacencies`). Contiguity at the unit level is exact (a node set with no root-reachable path receives no flow: summing inflow − outflow ≥ 1 over a root-less component gives 0 ≥ |component|, inferred); ZCTA-level contiguity follows because each unit is a connected set of ZCTAs by construction. `mip_rel_gap = 0` (tools/exp/contig/coarse.py:213 `options={"time_limit": time_limit, "mip_rel_gap": 0.0, "disp": False})`). Opt-in `--thin-floor` row Σ_u x_{u,h}(thin_u − 0.05 land_u) ≤ 0 (the G2 land floor).
  - **`rulec_enum.py`**: arithmetic, not a model: for a state set it enumerates districts that are a whole attached cluster in [L, U], or one split state σ with n pieces each joined to a union of whole components of the rest, feasible iff Σ_d max(L − w_d, 1e-6) ≤ M_σ ≤ Σ_d (U − w_d) and no w_d ≥ U (tools/exp/contig/rulec_enum.py:43 `lo = sum(max(L - w, 1e-6) for w in W); hi = sum(U - w for w in W)`; tools/exp/contig/rulec_enum.py:44 `if lo <= Ms <= hi:`), at the IFA window 798.74–1,148.19 m_rel (tools/exp/contig/rulec_enum.py:4 `L, U, F = 798.74, 1148.19, 1.2519681558`). It treats σ's mass as perfectly divisible and ignores contiguity of the pieces within σ. "Untested" (docs/CODE_MAP.md row).
  - **`land.py`** (#133): `land.csv`, per split group the in-state land ratio, largest over smallest, over the pieces holding ≥ 20% of their district's mass, against R (docs/CODE_MAP.md:64 `the in-state land ratio (largest over smallest, over the pieces holding 20% or more of their district's mass,`). **`backfill.py`** writes T1 manifests for runs drawn before tracking; no formulation (docs/CODE_MAP.md:45). **`plancheck.py`, `replan.py`, `wholeplan.py`, `pieces.py`** are §5.
  - **`merge.py`** (§8) and the IFA K ladder: each K step redraws one region, every other region is the previous folder unchanged (docs/RESULTS.md:1330 `A nested ladder from `ifa_conus_v2` (K52): each step redraws one region and every other region is v2's folder unchanged.`).

## 14. Why IFA works and national does not (evidence in the record, not a diagnosis)

| | IFA (all seven K = 48..54 pass) | main map (3 maps pass, via warm start) |
|---|---|---|
| planning channels | one, over 49 units, one fine channel, one $ rate | four (national, WH, FI, WIFI) or two/one in other structures, five fine channels, five $ rates; cells (ZIP, fine) in up to three channels |
| sealing | ZIP-disjoint state regions merge cleanly because "IFA has one cell per ZIP" (notes/2026-10-12_main-map-joint-wifi-grid-research.md:56) | "the main map is four channels over the same 41 non-west states, so state-keyed region merges do not transfer as-is" (notes/2026-10-13_ifa-to-national-orientation.md:27); the sealed driver needs equal-or-disjoint state sets across channels |
| window | one: [1,000, 1,437.5]; the repair clips the final band to the *absolute* window (notes/2026-10-13_ifa-to-national-orientation.md:11) | four windows; the symmetric fit-inside band was used until 2026-10-14 (§7); WIFI cap 1.6B |
| districts | regions of 1–14 districts; mostly single-state regions or a split state with whole attachments (ifa note §1.9, IFA regions list) | plans with supports of up to 6 units across 8 free states; the PA/FL/TN/NY groups combine a split state with whole-state bodies |
| exact coupled groups | per region small (NY K5 by coarsening; Queens/Nassau closed by a 109-ZIP window) | PA/NY/FL groups of 1,000–1,850 free ZCTAs with 2–4 districts, 5.6–12k columns (§10) do not finish in the first attempt, nor in 4–5 h retries; a TN group (AR+MO+TN, KY+TN) also did not in ne-52-bal (runs/exp/national_2026-10-14/INDEX.md:74 `the TN group (AR+MO+TN, KY+TN) did not finish`) |
| residual failures | Manhattan only (8.53 km, owner exception) | none for the 3 passing maps; others fail on NY pieces |
| iterations | about a week of per-state/region iterations with hand-chosen supports (UT free, DE+NJ-without-PA bans, NM-with-TX bans, §5; RESULTS dates 2026-10-07..14) | one grid pass per day |

Facts behind the rows: IFA's result list (docs/RESULTS.md:1330-1335, 1345); IFA's regions (notes/2026-10-13_ifa-split-state-constraints.md:211-215 `**Regions (ifa_conus_v2 README, "Sources"):** New England CT+RI K2 and MA+VT+NH+ME K2; Middle`); the IFA fixes that worked were regional sealing + UT free + DE+NJ-without-PA and NM-with-TX bans (notes/2026-10-13_ifa-split-state-constraints.md:216-217). Differences I can read but not weigh: (i) the IFA master is planned at ±15% and the *window* is imposed at repair, not a symmetric band inside it; (ii) rule C (one split state per district) holds on IFA maps "It is still undecided (#141)" (notes/2026-10-14_carve-first-lite-handoff.md:33), while the unsealed main-map master does not enforce it; (iii) in IFA every district's $ is judged against one window, in the main map against channel-specific windows whose headroom is smaller at some K (§15 B3).

## 15. Bottlenecks, as precisely as the record allows

**B1. Exact drawing of coupled groups (the binding computational limit).** Free ZCTAs 1,000–1,850 per group, 2–4 districts, 5.6–12k columns, 15–35k rows; first attempts stopped at the per-channel limit (≈ 4,300–5,100 s) without an incumbent or on "the constructed drawing stands" (§10 table), and the long retries ran 4–5 h without finishing (runs/exp/national_2026-10-14/STATUS.md:9 `Stopped m5 main_r2 (5 ne_plains draws stuck 4-5 h in exact solves of large coupled groups).`). Named groups: FI: Pennsylvania/Mid-Atlantic (DC+PA+VA+WV, DE+MD+PA, NJ+PA, PA), Florida (AL+FL, FL, FL+GA), Tennessee (AR+MO+TN, KY+TN), and New York (INDEX.md rows); WIFI (structures nw49/nw34/w1): the Maryland group DC+MD+DE+NJ+PA+WV with MD split, "unknown at its time limit" on every first attempt on m2 (runs/exp/national_2026-10-14/INDEX.md:14 `(the Pennsylvania/Mid-Atlantic, Florida and Tennessee groups in FI; the Maryland group DC+MD+DE+NJ+PA+WV in WIFI)`; runs/exp/national_2026-10-14/STATUS.md:6 `m2 first attempt: every WIFI channel (nw34 x3, nw49 x3) stalled on the same Mid-Atlantic group`). The undrawn ZCTA counts show that the whole NY unit (1,826 ZCTAs) is among the heuristic-placed ZCTAs of FI in all three passing maps, although the INDEX names only the PA group (§10, my arithmetic, inferred); NY is also the unit the warm start fails on in the other FI points (B2). RESULTS.md names the coupled groups as "NY/NJ/PA, AL/FL, KY/TN in FI" (docs/RESULTS.md:1358); the two lists differ in whether NY is in the FI exact-draw failures at the first attempt (§17).

**B2. NY after warm start.** `ne-50-bal` / `ne-52-filight`: FI_19 (NY) in 4 detached pieces (104, 29, 3, 1 ZIPs; 0.263 τ); `ne-52-bal`: FI_18 (NY, 21 ZIPs, 0.061 τ) and FI_07 (NJ, 7 ZIPs); exact NY windows ended `unknown` at 1,500 s (runs/exp/national_2026-10-14/INDEX.md:72 `**Fails M1 after the warm start: FI_19 (NY) in 4 pieces**`; runs/exp/national_2026-10-14/INDEX.md:74 `**Fails M1: FI_18 (NY, 21 ZIPs, 0.061 τ) and FI_07 (NJ, 7 ZIPs, 0.0006 τ) detached**`). `nw49-48/52`: a 9-ZIP NY piece in a WIFI district (runs/exp/national_2026-10-14/INDEX.md:75 `**Fails M1: WIFI_27 (NY) has a detached 9-ZIP piece, 0.085 τ**`).

**B3. Dollar arithmetic is tight at specific blocks** (verified by me from the passing maps' `dollars.csv`, `runs/exp/national_2026-10-14/warm/<pt>/merged/dollars.csv`):
  - *FI sitting at the upper edge U = 1,035.* In all three passing maps the two West FI districts are FI_04 = CA alone ($1,030.8M) and FI_05 = CA+OR+WA ($1,034.6M, 0.44M under U). The FI mass of CA+OR+WA is $2,065.4M (CA 1,624.0 + OR 121.0 + WA 320.4). If these two districts hold only CA/OR/WA ZCTAs and cover them, each has mass in [2,065.4 − 1,035, 1,035] = [1,030.4, 1,035.0], a 4.6M-wide interval; three districts would average $688M < 765, one would be $2,065M > 1,035. So the upper-edge sit is forced by the block, not by the draw (the closed-block premise is read off the ledgers; the master chose it).
  - *Lower edge.* NC alone (FI) $767.8M (L = 765) in all three; FL alone (national) $1,004.1M in ne-cmp-tierP (L = 1,000); WH_04 CA+NV+OR+WA $854.8M (L = 850); national_07 CA+NV+OR+WA $1,001.4M in ne-48-bal; FI_12 IN+KY $768.9M.
  - *WIFI.* WIFI_03 = MA+ME+NH+VT at $1,230.7M exceeds the 1,150 top and relies on the whole-state allowance (cap 1,600) in all three.
  - Window arithmetic fixes the K ranges (§0.3). The grid's *headroom* is 2·min(avg − L, U − avg)/(U − L), minimum over channels (notes/2026-10-12_main-map-joint-wifi-grid-research.md:108 `headroom = 2·min(avg−L, U−avg)/(U−L), minimum over channels`), 0.14–0.87 over the grid points; the two designed points that pass have 0.86 (`ne-48-bal`, notes/2026-10-12_main-map-joint-wifi-grid-research.md:115 `| 14 | 10 | 21 | 3 | 48 | 1,207 / 1,014 / 881 / — | 0.86 |`) and 0.26 (`ne-50-filight`, notes/2026-10-12_main-map-joint-wifi-grid-research.md:117 `| 16 | 11 | 20 | 3 | 50 | 1,056 / 922 / 925 | 0.26 |`).

**B4. The master does not know where shares land.** It pairs units whose drawn shares need not touch; drawability rows are necessary only; A, B, C bans moved pieces without clearing them (§5; notes/2026-10-13_overnight-grid-to-regional-sealing.md:37).

**B5. Policy parameters that bind plans:** `max_dist_km` (nw49 national: 1,200 → 1,500), split lists (R1 needed on ne-50/52-filight national and ne-52-bal FI), `max_size`, η, contact caps (docs/RESULTS.md:1357; probes in runs/exp/national_2026-10-14/probes/).

**B6. Four-channel structure blocks state sealing** (§14).

**B7. Gate dependence.** The one fully exact passing map (ne-48-bal/r2) passes only under the 2026-10-14 neck rule (docs/RESULTS.md:1322 vs 1346); `ne-50-filight` fails the strict gate on two necks (national_15 NY 5.99 km, national_16 79734 6.14 km) (runs/exp/national_2026-10-14/INDEX.md:28 `pass / **fail** (strict: 2 necks`).

**B8. Compute.** m5 12 and m2 8 single-thread slots (tools/exp/contig/overnight.py:135 `SLOTS = {"m5": 12, "m2": 8}     # one thread per process; m2 lower after the smoke if memory is tight`); HiGHS 1.15 callbacks unusable, so the cut loop re-solves from scratch (tools/exp/contig/draw.py:24 `- **Connectivity, exactly.**  highspy 1.15.1 never invokes its lazy-constraint callback, so the`).

## 16. Claims the reviewer should check (each single and falsifiable)

*M1 and structure*
  - **C1.** For a fixed channel, polygon graph and static zero-opportunity set Z⁰_c, whether district X passes (P) and (N) depends on X alone (td/audit.py:1013-1017 as read).
  - **C2.** With `polygon["gaps"]` empty, every neck found with `gap_width=True` is also found with `gap_width=False`, and the piece sets are equal.
  - **C3.** Every one of the 49 state ZCTA sets is connected in G_adj (verified by me), so every district that is a union of whole states connected in the unit graph is (P)-connected (MODEL §7, docs/MODEL.md:656-658).
  - **C4.** No code path special-cases Manhattan; `check_m1` fails the IFA Manhattan district.

*Master*
  - **C5.** With μ ≡ 0 and band [band_lo, band_hi]τ, every row of §2(b) holds for the read-back of any connected drawing whose districts' footprints are in 𝒮_c, whose masses are in [L, U] and whose shares obey η, modes and caps (Proposition D carries over verbatim from ±δ; proof not restated in MODEL.md for the window).
  - **C6.** Averaging the copies of one support preserves all rows (so the aggregate (n_S, t_{v,S}) plan loses nothing relative to explicit copies).
  - **C7.** The symmetric band τ(1 ± δ_fin) is contained in [L, U] and equals it only when τ = (L+U)/2; `fit_delta`'s rounding makes it slightly smaller.
  - **C8.** For ne_plains, window-feasible K are national 12–16, WH 9–11, FI 18–24 (arithmetic in §0.3).
  - **C9.** The diameter objective is not constrained to prefer balanced plans: probe plans reach both window edges (probes/split_rules.md:10).

*Draw / repair*
  - **C10.** Every separator row of §4.1(d) holds for every connected drawing, including the second ring (near-`main` ∩ reachable) and the no-body form; every added row is violated by the solution that produced it, so the loop terminates.
  - **C11.** The flow rows are feasible for every connected district (root = the first body, largest by ZCTA count in `draw.draw`; each ZCTA and each other body consuming one unit).
  - **C12.** `prune` never removes a pair some connected in-band drawing uses.
  - **C13.** The objective of `_solve_group` is *not* lexicographic in (holders, shape) when the land term is on: border ≤ 900, land ≤ 900 per group, moment ≤ 9, split 1,000 (tools/exp/contig/draw.py:85 `LAND_WEIGHT = SHAPE_SCALE   # the land term's (#133) most per group, below one split`).
  - **C14.** `NeckCut` rows hold for every drawing in which district j has no neck and its anchors lie in one component of j (draw.py:133-161).
  - **C15.** Proposition B (docs/MODEL.md:387-402): D_c(S,δ) = ∅ ⇒ n_S = 0 for every neck-free connected drawing.
  - **C16.** A window repair never raises the window units' split units or cuts above the drawn map's when the cap is on.

*Sealing, arithmetic*
  - **C17.** Any plan feasible for a sealed partition (no support crossing a region, same band) is feasible for the unsealed model with the same band.
  - **C18.** For a connected block of the footprint, any district lies in one block, so a necessary condition is the existence of integers k_i ≥ 1, Σ k_i = K with τ-compatible block masses (parts floor, tools/exp/split_floor.py).
  - **C19.** FI West block (verified numbers): if exactly two FI districts cover CA+OR+WA and hold no other ZCTA, both masses lie in [1,030.4, 1,035.0]; with 1 or 3 districts the window is violated.
  - **C20.** Whole-state masses at the edges (NC FI $767.8M ≥ 765; FL national $1,004.1M ≥ 1,000) are exact consequences of the extract, not of any plan.

*Facts about the maps*
  - **C21.** In the three passing maps every district is in its window; the M1 gate (gap-width) passes with 0 pieces and 0 necks in ne-48-bal and ne-cmp-tierP, and strict fails on two necks in ne-50-filight (INDEX.md:27-29).
  - **C22.** District-level rule-C violations (a district holding ≥ 2 split states, split taken as ≥ 2 districts owning a ZCTA): ne-48-bal none; ne-50-filight national_09 (NY, PA), WH_06 (NJ, PA), FI_18 (OH, PA); ne-cmp-tierP WH_06 (NJ, PA), FI_18 (OH, PA) (verified by me from `merged/ledger.csv`).
  - **C23.** Master solve times in the window run are ≤ 0.43 s per channel (draw/solver.json, ne-48-bal).
  - **C25.** In joint mode the coupled-group decomposition of `draw.draw` is exact (groups share no free ZCTA and no district; F_j is constant outside a group).
  - **C26.** On the dollar extract the acceptance slack `tol = 1e-7·max(1, hi)` of `accept` is ≈ $103 at hi = $1,035M, so a given/constructed start can be accepted up to that far outside the band; the whole-dollar gate still decides.
  - **C24.** `glue.py` never moves a ZCTA of positive mass in the channel and never accepts a move that creates or enlarges a piece or neck in a donor.
  - **C27.** The 2026-10-13 grid's spec copies for w1 and nw49 (read) and, by their base specs, west8 and nw34's WIFI channel (not read: m2) carry the default `margin = true` (rounding margin μ_S > 0), unlike ne_plains and every 2026-10-14 spec.

## 17. Disagreements between prose and code, follow-ups, and what I did not do

**Expected / Found / Why it matters** (code wins; none edited, since `PROBLEM.md`, `docs/MODEL.md`, `td/audit.py` are owner paths):
  1. *National window.* Expected (PROBLEM.md:214 `Every district's drawn $ is within ±15% of its channel's target`): national [$1,062.5M, $1,437.5M]. Found (tools/looks/score.py:109): floor $1,000M; PROBLEM.md:239 admits the floor is "in the scorer but not filed here as owner decisions". Matters: K 16 and the window-band feasibility depend on the $1,000M floor.
  2. *Neck connector rule.* Expected (PROBLEM.md:95 `An approved connector is a passage of unlimited width, except where the district`): width 0 where land would do. Found: unlimited always (R1) (td/audit.py:938, docs/MODEL.md:861). The M1 row in PROBLEM.md awaits the owner (notes/2026-10-14_m1-water-empty-land-proposal.md:19).
  3. *Split definition.* Expected (PROBLEM.md:205): districts "holding positive opportunity" in a unit. Found (tools/looks/score.py docstring): "own a ZCTA ... zero-opportunity ones included".
  4. *Priority order.* PROBLEM.md:204 splits first; #134 (2026-10-14, per the handoff) puts splits last (notes/2026-10-14_carve-first-lite-handoff.md:19).
  5. *WIFI window.* METHOD-carve-first.md:70 and PROBLEM.md:214 describe a K-dependent ±15% of the WIFI dollar mean; the scorer fixes [850, 1,150] with a 1.6B whole-state allowance (tools/looks/score.py:109-111).
  6. *Which ZCTAs are heuristic-placed.* Expected (runs/exp/national_2026-10-14/INDEX.md:27 `FI 3,659 (PA group DC+PA+VA+WV, DE+MD+PA, NJ+PA, PA)`): the 3,659 FI ZCTAs of ne-48-bal are the PA group. Found: 3,659 = 1,833 (PA) + 1,826 (NY); the first-attempt `contig.json` lists PA as the unknown group and no NY group at all for FI (never started). Matters: the NY unit is heuristic-placed in all three passing maps, and NY is where the other FI points fail (§15 B2).
  7. *Connector count.* PROBLEM.md:223 `159 + 16` vs docs/RESULTS.md:429 "163 approved connectors" before the 16 vs the file's 179 rows (52 bridge, 8 tunnel, 22 ferry, 91 road, 6 nearest) (verified by me).
  8. *merge.py docstring* still calls the strict run "m1_default" and `TD_NECK_GAP_WIDTH=0`; the default is now gap-width on (tools/exp/contig/merge.py docstring; the handoff already lists it, notes/2026-10-14_overnight-deferred.md:13).
  9. *Brief vs branch:* no `balance.py` on warm-start; no committed carve-first code.

**Follow-ups (not done, outside this note):** (a) a restated Proposition D for the window band (§16 C5); (b) repair/plancheck/contact rows still on the old connector rule; (c) `sealed.py` + window band combination was never run (§9 h.1); (d) the FI West block arithmetic (B3) deserves a master-level check of alternatives that mix CA/OR/WA with NV/AZ/ID; (e) rule-C incidence in unsealed plans.

**Not done / not read:** I did not re-derive proofs (Proposition D, B, NeckCut, Claim 3); I read the legacy code only through `MATH_REVIEW.md`; I did not read `tools/exp/contig/set125.sh`, the `plancheck.py` MILP body, or `kgrid*.sh`; hub outputs were read, not regenerated; no solver was run. Numbers marked "verified by me" come from read-only Python on the committed graph and on the hub's `ledger.csv` / `dollars.csv`.
