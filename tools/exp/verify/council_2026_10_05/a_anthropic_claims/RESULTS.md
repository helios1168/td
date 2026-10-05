# #91: independent verification, a_anthropic_claims

**Result:** F2 and its lexicographic objectives are exact for the stated master. F6 is exact for whole/free modes with μ=0. Hall rows are valid but insufficient. Neither the split optimum nor δ* bounds **all** polygon-connected M1 maps when η>0 excludes their contacts. Counting zero-opportunity polygon ownership does not repair that scope gap.

The supplied Opus C1 example is **not** master-infeasible at δ=0 under MODEL's C7-only rows. Its two pair supports balance exactly. Adding Hall rows changes that conclusion. A smaller, all-positive example independently proves the claimed general balance-bound failure.

## Scope and reproducible commands

Read `docs/problem/SPLITS.md` (including F1–F7, §2.1, §5), `docs/MODEL.md` (§1–5, including Claims 1–3, Proposition D, C7 and §4.8), and the relevant `td/master.py` / `td/supports.py` definitions from this managed worktree. Starting HEAD: `8875bf77c58873a5c60c2fd81eda54d87711018d`. Owner's 2026-10-05 polygon-ownership split key supersedes SPLITS's positive-opportunity key. No extract, instance_descaled file or data directory was opened for this verification. No production model was edited.

Assumptions / domains:

- One channel; toy units stand for states, one unit per state (no pieces or cross-state metros); finite, explicit ZIP vertex set, nonnegative ZIP masses, positive mass for every unit; K positive integer; τ=total mass/K. Mass units arbitrary opportunity units, not dollars. δ≥0, μ=0 except the margin counterexample. Split key is polygon ownership, including zero-mass ZIPs.
- Supports are **all** connected subsets of the induced unit graph up to the stated size cap; no distance filter. This family is closed and independent of modes. Weights are support diameter for collinear centroids p_v=v. Default modes free, η=.05, δ=.15, size cap 3, no extra contact cap.
- Corrected border, count, corridor and optional Menger rows included. Hall rows included only where marked. Corridor floors and Menger cuts computed exhaustively inside toy units, independently of td.
- Every nonnegative integer n with Σn=K enumerated; each tested by a separately assembled share LP. `check_instance` additionally compares **every** enumerated n, feasible or infeasible, with the fixed-n F2 MILP. Continuous share space tested by LP, not gridded.
- Every surjective K-colouring enumerated modulo label permutation via restricted-growth strings; exactly K! labelled colourings per enumerated partition. Non-surjective colourings cannot represent K nonempty districts. No connectivity or balance pruning before enumeration. All district connectivity checked on the full ZIP graph, not within each unit.
- scipy 1.18.1 / HiGHS; `milp`: `mip_rel_gap=0`, `mip_abs_gap=0`, `threads=1`; `linprog`: `method='highs-ds'`, explicit options, `threads=1`. SciPy forwards absolute-gap/thread options. One thread count per process. Numerical assertion tolerance 1e-7; solver feasibility defaults unchanged. These are exact formulations and exhaustive discrete searches, **not rational-arithmetic solver certificates**.
- Eight-unit path has 16 ZIPs: exhaustively checked plans, not drawings. Drawings exhaustively checked on 6-unit examples with 7–12 ZIPs and minimal witnesses. Tight 6-unit/18-ZIP/K=18 weak-duality example checks plans only.

From worktree root:

```bash
TD_PY=/Users/Shared/sv-ntlee/td/.venv/bin/python3
L=tools/exp/verify/council_2026_10_05/a_anthropic_claims
"$TD_PY" "$L/run_all.py"
# Individual groups, named O/C/D/P in the tables:
"$TD_PY" "$L/objectives.py"       # O
"$TD_PY" "$L/clusters.py"         # C
"$TD_PY" "$L/drawability.py"      # D
"$TD_PY" "$L/polygon_policy.py"   # P
set -o pipefail
"$TD_PY" tests/run_all.py 2>&1 | rg -v '^\s*PASS '
```

Observed retained suite: **ALL CLAIM CHECKS PASSED**, 4.48 seconds. Repository runner: **267 passed, 0 failed, 0 skipped**; it nevertheless prints fixture-level SKIP notices for missing public state/ZCTA archives. Those geography checks were not run. No public data fetched.

## Numerical inventory

A plan below means one integer multiset n, before feasibility filtering. Every `check_instance` row compares all these plans to fixed-n MILP, as well as checking optimum, pinned diameter and split cutoff; blend checked whenever max diameter >0.

| Instance | Units / ZIPs / K | Integer plans; feasible | (splits,diameter) optimum | Matching-policy drawings / unlabelled colourings |
|---|---:|---:|---:|---:|
| path6_K3 | 6 / 12 / 3 | 680; 1 | (2,5) | 1 / 86,526 |
| path6_K2 | 6 / 12 / 2 | 120; 1 | (0,4) | 1 / 2,047 |
| path8_K3 | 8 / 16 / 3 | 1,771; 2 | (1,6) | not enumerated |
| cycle6 | 6 / 12 / 3 | 1,140; 34 | (0,3) | 4 / 86,526 |
| border_star_six | 6 / 8 / 5 | 1,287; 1 | (1,2) | 0 / 1,050 |
| mass_star_six | 6 / 10 / 5 | 792; 1 | (1,2) | 0 / 42,525 |
| mass_path_six | 6 / 10 / 5 | 792; 1 | (1,2) | 2 / 42,525 |
| polygon_gap_six | 6 / 8 / 6 | 924; 1 | (2,2) | 0 / 266 |
| balance_gap_six at δ=.01 | 6 / 7 / 6 | 924; 1 | (1,1) | 0 / 21 |
| zero_contact_gap_six | 6 / 8 / 5 | 1,287; 1 | (2,3) | 0 / 1,050 |
| zero_matching_six | 6 / 8 / 5 | 1,287; 1 | (1,2) | 1 / 1,050 |

Path6 unit ZIP masses: (.6,.4), (.9,.5), (.5,.3), (.8,.4), (.5,.1), (.6,.4), with all 12 ZIPs forming a path. Path8: eight (.6,.4) units on a 16-ZIP path. Cycle6: six (.5,.5) units on a 12-ZIP cycle. `_six` pads the named witness with isolated whole singleton units, each mass τ, adding the same number of districts; target and original obstruction remain unchanged. Complete witness definitions follow.

## One row per pass-1 T claim and extra question

| Claim | Verdict | Checked / corrected proof sketch | Instances, command, output summary |
|---|---|---|---|
| p1-opus T1: F2 exact | **holds** | Coverage + η imply r_v≤floor(1/η); count/contact rows and Σn=K give the remaining caps. Thus r_v≤U_v. s_v=0 permits exactly r_v≤1; s_v=1 always permitted. Minimum binary indicator equals 1[r_v≥2]; adding indicators does not remove any (n,t). | O: four 6–8-unit cases, 3,711 integer plans / 38 feasible; every fixed-n MILP agrees with independent share LP; minima 2,0,1,0. |
| p1-opus T2: pair row invalid | **holds** | A support multiplicity is an integer count, not a binary use variable. Feasible r_v=3 requires one split indicator, not s_v≥2. | O: E1, 2 units / 4 ZIPs; n_v=2,n_uv=1, t_v=.8/.2; proposed pair row asks binary s_v≥2. |
| p1-opus T3: lex bound and ε | **holds with stated conditions** | For every X in matching-policy 𝒳, Prop D supplies feasible read-back with equal polygon split count and w. If count>s*, lex bound immediate; otherwise count=s* and w≥d*. Nonnegative w gives εw_total<1, so one extra integer split cannot help. Not a bound for unrestricted M1; see E2/E4. | O: same four cases, pinned and blended optima (2,5),(0,4),(1,6),(0,3); P: E2 refutes unconditional extension. |
| p1-opus T4: F6 exact / monotone | **holds with stated conditions** | Whole/free, μ=0: r_v=1 forces unique n_S=1,t_vS=1, satisfying whole rows. Put exactly actual split units in F. Conversely splits⊆F. Enlarging F removes holding restrictions; newly applicable border/Hall rows hold automatically for prior unsplit ownership. With μ>0, releasing a unit can increase its margin. | O: all 448 subsets across four cases; minimum |F|=2,0,1,0, every feasible family up-closed. E5: whole feasible, free infeasible; padded 6-unit case enumerates 462 plans in each mode. |
| p1-opus T5: cluster floor | **holds** | Link copies through shared split units. Components give disjoint connected unit clusters P, with k copies, mass in [kL,kU], Σk=K. k≥2 requires a split unit; every M_v>U requires a split. Sum component lower bounds, then minimize over cluster partitions. | C: 6/6/8 units, 203/203/4,140 set partitions, floors 1/0/1 versus s*=2/0/1; tight 6-unit example floor=s*=6. |
| p1-opus T6: Hall border rows | **holds with stated conditions** | Count only supports containing v with **nonempty** N(v)∩S⊆H. Each connected copy needs a border ZIP in union(H), and copies use distinct ZIPs. Geometric ownership, not positive mass, supplies this injection. Current border star closes with Hall plus corrected corridor; other stars do not. | D: E6, 3 units / 5 ZIPs, 21 plans, s*=1; no drawing among 15 partitions; Hall rejects 2≤1. Padded 6-unit test: 1,287 plans. Wide-band E6: all 4 connected drawings pass Hall read-back. |
| p1-opus T7: graph monotonicity | **holds with stated conditions** | Same ZIP domain, edge inclusion, and all other support/mode/η/cap policies must match. Edge inclusion transfers connectivity; Prop D then applies to summaries recomputed on master graph. Inclusion sufficient, not necessary. Connectivity alone does not enforce η. | D: E8, 6 units / 6 ZIPs; full path s*=0 with drawing; removing middle edge makes master infeasible. P: η counterexamples survive identical graph. |
| p1-fable T1: F2 exact and bound | **holds with stated conditions** | Same F2 indicator proof as Opus T1. Map bound holds for 𝒳, not every connected in-band M1 map. Under polygon ownership read-back r equals owning districts, including zero-mass contacts, but η can still invalidate read-back. | O: all 3,711 plans agree; P: E2 gives polygon minimum 1 < master 2; zero_matching_six has one valid zero-ZIP-containing read-back. |
| p1-fable T2: pinned second pass | **holds** | Projection of Σs=s* has actual split count≤s*. Global minimality makes it equal s*. No phantom indicators possible at minimum cardinality. Thus pinned w optimum equals minimum w among true minimum-split plans. | O: four 6–8-unit cases; exhaustive LP minima match pinned MILP pairs (2,5),(0,4),(1,6),(0,3). |
| p1-fable T3: ε exact | **holds with stated conditions** | For w≥0 and Wmax>0, 0<ε<1/(K Wmax) bounds secondary range below integer primary gap. Within fixed primary count, ε>0 preserves exact w ordering. If Wmax=0 the displayed fraction undefined; any ε>0 works. Numerical certification still needs both gaps 0. | O: blended optima match all four enumerations. No nonzero-gap MILP retained: packet mandates gap 0 for every MILP. Arithmetic example 100001 versus 100000 has relative gap 9.9999e-6, so gap=1e-4 cannot exclude the worse value. |
| p1-fable T4: exhaustive F6 | **holds with stated conditions** | Whole/free and μ=0 required. Support family mode-independent. Whole conversion of an unsplit free unit does not change band or geometry rows; min |F| equals F2 minimum. Up-closure follows despite newly added free-only border rows because those rows already hold for whole ownership. | O: 64+64+256+64 subsets, feasible counts 16/64/192/64, minima 2/0/1/0; no monotonicity violation. |
| p1-fable T5: per-part τ differs | **holds** | Component masses must fit the parent [kL,kU] for an integer allocation summing to K. Local τ=M(P)/k erases this necessary condition. Both readings checked: each local solve for allocation (2,2), and all local counts occurring in every positive allocation. | C: E7, 6 whole units / 6 ZIPs, 1,365 joint plans, none feasible; both local (2,2) solves feasible at δ=0. Stronger free 6-unit / 12-ZIP version: both local components feasible at own τ for each k=1,2,3, but joint infeasible for every allocation. |
| p1-fable T7: master can fail to lift | **holds with stated conditions** | Stated size corrected: **3 units / 7 ZIPs**, not 3/5 (v alone has 5). With supports size≤2 and whole u,w, one district must get each end unit. A centre-free connected v-piece attached to its end is a single leaf, giving mass 4<4.675. Master continuous pieces can have masses 2 and 3. | D: E9, 63 colour partitions, no connected in-band drawing; master s*=1. Padded 6-unit / 10-ZIP star: 792 plans, one feasible; no drawing among 42,525 partitions. Hall also passes. |
| p1-fable T8: summaries cannot detect lift | **holds with stated conditions** | For size cap 2, v never a unit-graph cut vertex, so c and κ lists empty. Equal M, ZIP counts/mass multisets and distinct single-ZIP boundary sets give equal b and Hall unions. Star/path internal connectivity differs: star cannot split 2+3 attached pieces; path can. This proves insufficiency of these summaries, not impossibility of richer rows. | D: E9/E10, 3 units / 7 ZIPs, signatures identical including mass multiset and Hall; star 0/63 drawings, path 2/63. Padded six-unit checks retain identical master signatures, star 0 and path 2 drawings. |
| p1-fable T9: weak split duality | **holds with stated conditions** | Connecting K copies via each unit's r owners merges at most r−1 components, so cuts≥K−q. Resulting clusters admissible in Q, giving q≤Q and cuts≥K−Q. Since cuts≤split_units·(Umax−1), divide only when Umax>1. That Umax must also bound map contacts; η-derived Umax does **not** bound unrestricted polygon maps. | C: four 6–8-unit cases; Q=1/2/2/6 and weak floors 2/0/1/6, all respected. Tight masses 3τ≥2.55τ: 33,649 plans, one feasible, floor=forced count=s*=6. E11 refutes unrestricted M1 split inequality. |
| Extra (a): polygon split bound for every M1 | **refuted** | Matching polygon key repairs objective equality, not feasibility of read-back. η excludes small positive shares as well as zero contacts. Smallest finite strict split gap within positive-unit/matching-domain policies is 2 units / 4 ZIPs (E2). Zero-transit version E4 also violates bound. | P: E2 has 6 integer plans, only n_AB=2 feasible, s*=2; exhaustive 7 drawings give minimum 1. Padded six-unit test agrees over 924 plans. E4: polygon 1 versus master 2; six-unit check 1,287 plans. |
| Extra (b): δ* bound for every M1 / Opus C1 | **refuted** | General unrestricted claim false, but Opus's printed C1 infeasibility is itself false for C7-only master. Correct smallest finite balance gap is E3: master δ*=.01, drawn optimum 0. Hall-enhanced C1 has δ*=.05 and drawn optimum 0. | P: E3, 2 units / 3 ZIPs, all 3 drawings checked; master infeasible at 0/.00999, feasible at .01. Six-unit padding: 924 plans, none at 0, one at .01. C1 pair plan explicitly validated at δ=0; Hall variant infeasible at .04999, feasible at .05. |

## Pass-2 refinements affecting these claims

| Refinement | Verdict | Proof / numerical evidence |
|---|---|---|
| All C1: objective-preserving feasible read-back, graph/domain/policy conditions | **holds with stated conditions** | Polygon counting alone insufficient; E2/E4 retain η failures. Zero ZIPs with positive unit contact can be harmless (`zero_matching_six`: 1 valid drawing). Entire zero-mass units dropped by MODEL remain a domain mismatch for an all-ZIP/all-state M1 claim; toys keep M_v>0. Original zero-transit map now splits v, so its old positive-opportunity split count 0 cannot be used under owner's new key. |
| All C2: Hall valid, stars differ, summaries insufficient | **holds with stated conditions** | E6 shared hub rejects 2≤1; E9 distinct attachments passes Hall but cannot lift; E10 same summaries lifts. Opus's lumpy .1/.8/.1 versus uniform thirds contrast correctly demonstrates Hall insufficiency, but **does not have equal ZIP-mass multisets**, so it cannot support the original full T8 signature claim. The star/path all-unit-mass pair can. |
| All C3: no-good scope | **holds with stated conditions** | Empty fixed-target search is not empty n-fibre. E12: adjacent .9/1.1 ZIPs cannot meet 1/1 targets but do give connected in-band drawing. E13: a district's disconnected unit intersection reconnects through another unit. Failure with a per-unit connectedness restriction therefore invalid as universal no-good. Excluding n requires all admissible t and all joint unequal copy allocations; excluding split set requires all plans under that set. Timeout is unknown. An invalid cut can corrupt a subsequently claimed floor; only the **unchanged original** master floor survives. |
| All C4: forced-only infeasibility implies extra split / 13 | **holds with stated conditions** | Mandatory set Φ={v:M_v>U}. By F6, infeasibility with only Φ free proves s*≥|Φ|+1. If historical F0 is larger than current Φ, up-closure transfers infeasibility to Φ, not the old cardinality. Conditional 4+3+6=13 needs matching forced sets, fixed-δ infeasibility and an incumbent. **Historical masses, cutoff statuses, bisection brackets, δ,η and the claimed 13 certificate not verified here**; no extract access permitted. O checks mandatory containment on all 448 free sets, but does not certify historical production counts. |
| All C5: F7 fixed regions | **holds with stated conditions** | Parent τ and K allocation enumeration necessary, insufficient (E8's 3+3 carving). Restriction exact iff **some parent optimum respects regions**. Opus's “iff no family support crosses” is too strong: no crossing supports is sufficient, not necessary. E8's 2+2+2 carving attains s*=0 despite unused crossing supports. Arbitrary carving cannot certify the unrestricted minimum. |
| All C6: cutoff layer / independence | **holds with stated conditions** | With all m eligible units and f mandatory ones, monotonicity reduces the cutoff to size s*−1 supersets of Φ: C(m−f,s*−1−f). Fixed old free-list constants 2^17 or 924 do not bound owner's all-state search. C checks m=6,f=2,s*=4 gives 4 candidates. F6 using same HiGHS is a formulation/control-flow cross-check, not vendor-independent infeasibility evidence. Independent share-LP assembly still uses HiGHS, so retained checks make no solver-independence claim. |

No unread NP-hardness citation, certificate-size assertion or VIPR assertion used or verified. No conclusion that no richer computable row can help. Claim 3's rounding correctness taken from the named document; these tests concern split/read-back/lift scope, not a new transport rounding implementation.

## Complete counterexamples / witnesses

All unlisted caps absent; family includes all connected unit subsets up to indicated size; distances unbounded. Menger included. μ=0 except E5.

### E1. Invalid pair row

Units u={a}, v={b,c,d}; masses (.5,1,1,.5); ZIP path a–b–c–d. Both free; K=3, τ=1, δ=0, η=.05, size cap 2. Plan n_{v}=2,n_{uv}=1; t_{u,uv}=1,t_{v,v}=.8,t_{v,uv}=.2. Singleton-v copies each mass 2.5·.4=1; uv copy mass .5+2.5·.2=1. Count cap r_v=3≤3, corrected border one crossing≤1. s_v=1 exact, but proposed pair row asks s_v≥2.

### E2. Smallest finite strict polygon split gap

Units A={a1,a2}, B={b0,b1}; masses a1=a2=.45,b0=.1,b1=1. ZIP cycle edges a1–a2, a2–b1, b1–b0, b0–a1. Both free; K=2, τ=1, δ=0, η=.1, size cap 2.

Draw districts {a1,a2,b0} | {b1}: each mass 1, each connected, A unsplit, B split; polygon count 1. B contact on first district is .1/1.1=1/11<η.

Master with one split cannot work: B mass 1.1>U forces B split. A must be whole. Its district must use AB, so mass at least .9+.1·1.1=1.01>1. Thus master needs A and B split. Feasible n_AB=2,t_A,AB=t_B,AB=1: each decoded copy mass (.9+1.1)/2=1; both corrected border counts 2≤2, both ZIP count caps 2≤2. Hence s*=2 > drawn minimum 1.

Minimality, **finite feasible-master gap**, ordered by unit count then total ZIP count: one unit's split count fixed by K. With at most three ZIPs and at least two positive-mass units, at most one unit can have two owners (ZIP count cap); feasible master s*≤1. A zero-split matching-policy-domain drawing has shares exactly 1 and always supplies a feasible unsplit read-back, so cannot be below that value. Thus 2 units / 4 ZIPs is minimum. This is not a claim about dropped zero-mass units or mismatched policies.

### E3. Smallest finite balance gap

Units A={a}, B={b0,b1}; masses (.9,.1,1); ZIP path a–b0–b1. Both free; K=2, τ=1, η=.1, size cap 2. Draw {a,b0}|{b1}, masses 1/1, connected; drawn δ*=0.

Only potentially best master plan is n_AB=n_B=1 (A cannot split: one ZIP). AB requires B share≥.1 and therefore mass≥.9+.1·1.1=1.01. At that share, B-only mass=.99. Alternative A|B whole masses .9/1.1 needs δ=.1. Thus master δ*=.01 exactly. δ=0/.00999 infeasible, .01 feasible. One positive unit, if master feasible at any δ with μ=0, balances its identical support copies exactly at δ=0. Two singleton-ZIP units supply whole read-back. Hence 2 units / 3 ZIPs minimum finite balance gap under matching domain policies.

Opus C1 as printed: whole A={a},B={b}, free v={z0,z1}; masses (.5,.5,0,1), edges a–z0,b–z0,z0–z1, K=2, τ=1, η=.05, size cap3. Drawing {a,z0,b}|{z1} balances exactly and now counts one polygon split. Under C7-only master, n_Av=n_vB=1 with v shares .5/.5 and A,B whole balances 1/1, passes each border cap 1≤1, count cap2≤2, and has no cut vertex in either active support. Thus printed δ=0 infeasibility false. Hall union row rejects these two pair supports (2≤1). Then only triple AvB plus singleton v can work; c_v(AvB)=0 but η requires masses at least1.05 and at most.95, so Hall-enhanced δ*=.05. Triple/singleton plan at v shares .05/.95 attains it.

### E4. Polygon key still fails on zero transit

Units A={a1,a2}, v={z0,z1}, B={b}; masses (.45,.45,0,1,.1). Edges a1–a2, a1–z0, a2–z0, z0–z1, z0–b. All free; K=2, τ=1, δ=0, η=.2, size cap 3.

Draw {a1,a2,z0,b}|{z1}: connected, masses 1/1, only v split (including zero contact). Master one-split candidates: A-only or B-only split leaves v whole mass1 alone, so A+B must share another district but disconnected. Splitting only v: triple AvB with v contact has mass>1; pair Av/vB needs v shares .1/.9, first below η=.2. Thus s*≥2. Feasible supports AvB and Av, each once: opportunity allocations A=.7/.2, v=.2/.8, B=.1/0, giving masses 1/1 and legal shares (A:7/9,2/9; v:.2,.8; B:1). Count/border/corridor/Menger rows pass. Hence s*=2, polygon count=1.

### E5. μ breaks F6 up-closure

One unit v, two adjacent ZIPs (.5,.5); K=1, τ=1, δ=.1, η=.05. Whole mode: μ=0, feasible mass1 in [.9,1.1]. Free mode: μ=.5, tightened band [1.4,.6], empty. F=∅ feasible, F={v} infeasible. Adding five isolated whole singleton units of mass1 and five districts yields the retained six-unit witness without changing τ or failure.

### E6. Hall closes shared-border star

Whole A={a}, B={b}, each mass .5. Free v={h,l1,l2}, each mass1/3. Edges h–a,h–b,h–l1,h–l2. K=2, τ=1, δ=.1, η=.05, size cap 3. Supports Av and vB, one each, v shares .5/.5, masses1/1; C7 each 1≤1, r_v=2≤3. Hall H={A,B}: two copies≤|{h}|=1, false. Remaining triple AvB+singleton v has corridor c_v=1/3, triple mass≥1+1/3>1.1. Therefore adding Hall makes master infeasible. Connected district without h is one leaf with mass≤.5<.9, so no M1 drawing. At δ=.75, all four connected drawings obeying the same policies pass Hall and share-LP read-back.

### E7. Per-part τ hides parent infeasibility

Six whole singleton units on disconnected paths 0–1–2 and 3–4–5; masses (.6,.6,1.2,.4,.4,.8), K=4, τ=1, δ=.15, η=.05, size cap 3. Components mass 2.4 and 1.6. Allocations (1,3),(2,2),(3,1) all violate at least one parent's component-total band: 2.4 fits neither 1,2 nor3 districts; 1.6 fits neither 1,2 nor3. At own τ and (2,2), first component districts {0,1}|{2}, masses1.2/1.2; second {3,4}|{5}, masses.8/.8. Each local solve feasible at δ=0.

Stronger universal-local reading: same six-unit graph, each unit two ZIPs, masses .4 per ZIP in first component and 4/15 per ZIP in second, with each component's six ZIPs forming a path. All free, size cap 3, μ=0. Each component admits k=1,2,3 at its own τ and δ=0: full component; overlapping two-unit supports sharing middle unit equally; three singleton units, respectively. Thus every local solve arising in positive allocations of global K=4 succeeds, but no parent allocation succeeds.

### E8. Fixed carving and graph mismatch

Six whole singleton units, mass1 each, ZIP/unit path 0–1–2–3–4–5; K=3, τ=2, δ=.15, η=.05, size cap 2. Parent pairs {0,1},{2,3},{4,5} give s*=0, mass2 each.

Fixed regions {0,1,2}/{3,4,5} each mass3: k=1 upper2.3<3; k=2 lower3.4>3; every allocation fails. Parent τ and allocation enumeration therefore insufficient. Regions {0,1}/{2,3}/{4,5} attain optimum despite family supports {1,2},{3,4} crossing their borders: no-crossing-family is not necessary.

Delete edge 2–3 from master graph: two odd three-unit components cannot form 3 in-band whole districts. Original connected drawing exists only on richer graph. This is absence-of-guarantee example, not proof that edge inclusion necessary.

### E9/E10. Equal summaries, different lifts

Whole u={a},w={b}, masses3 each. Free v has five ZIPs of mass1. Unit path u–v–w; K=2, τ=5.5, δ=.15 (band [4.675,6.325]), η=.05, size cap 2; Hall included.

E9 star: v centre c with leaves l1,l2,l3,l4, edges c–li, plus a–l1,b–l2. E10 path: v p1–p2–p3–p4–p5, plus a–p1,p5–b. Both have M_v=5, |Z_v|=5, mass multiset {1,1,1,1,1}, b_{uv}=b_{wv}=1, boundary union size2, no cut-vertex support hence empty corridor/Menger lists, identical modes/caps/family/weights. Master {uv},{vw}, each once, can allocate v opportunity 2 and3; s*=1.

Star: u,w cannot share district (size cap2). Centre belongs to one; other connected district can take only its attached leaf, mass4<4.675. No lift. Path: {a,p1,p2}|{p3,p4,p5,b}, masses5/6, connected and in band. Exhaustive path gives two valid cut locations.

Additional Hall-insufficiency witness, **not equal-multiset T8 witness**: path a–p1–p2–p3–b, endpoint units whole mass.5 each, free v masses (.1,.8,.1), K=2, τ=1, δ=.2, η=.05, size cap2, Hall included. Master pair supports feasible at v shares .5/.5. Connected cut prefix masses .5,.6,1.4,1.5, none in [.8,1.2]. Replacing v masses with thirds permits cuts .8333/1.1667; border/corridor/Menger/Hall match but ZIP-mass multiset does not.

### E11. Weak split bound needs map contact cap

One free unit, three unit-mass ZIPs on a path; K=3, τ=1, δ=.15, η=.5, no external neighbours. Draw one ZIP per district: all connected/in-band, cuts=2, polygon split units=1. Q=1. Master's η-derived Umax=min(K,floor(1/η),|Z|)=2, yielding claimed split floor (3−1)/(2−1)=2>1. Map violates η; master infeasible. Cuts≥K−Q remains correct. Split form valid only if chosen Umax also bounds map ownership counts; denominator undefined at Umax=1, requiring separate zero-cut treatment.

Tight six-unit witness: six disconnected units, each a 3-ZIP unit-mass path, all free; K=18, τ=1, δ=.15, η=.2, size cap1. Every unit mass3τ≥2.55τ. Q=6, Umax=3, weak bound=(18−6)/2=6. Every unit forced split; one feasible plan n_{v}=3 for every unit, s*=6.

### E12/E13. Invalid no-good restrictions

E12: one free unit, adjacent ZIPs (.9,1.1); K=2, τ=1, δ=.15, η=.05. Equal copy targets1/1 cannot be drawn by indivisible ZIPs; connected .9/1.1 drawing valid. Aggregated n_v=2,t_vv=1 same for both. Equal-target failure cannot exclude n.

E13: v has unit-mass ZIP path z1–z2–z3–z4–z5; whole C={c} mass1, edges c–z1,c–z5. K=2, τ=3, δ=0, η=.05, size cap3. Drawing {z1,z5,c}|{z2,z3,z4} connected with masses3/3, v shares2/5 and3/5. First district's intersection with v disconnected. Master read-back supports vC,v feasible. Per-unit connectivity is not an M1 necessity.

## What restores a bound (identification only; no redesign implemented)

To bound **all** matching-domain geometric M1 maps, support contact must represent polygon ownership independently of mass. Allow zero or arbitrarily small t on owned contacts, retain geometric n and s, remove the η lower bound and η-derived contact cap from the bounding relaxation, and use U_v=min(K,cap_v,|Z_v|), **not floor(1/η)**. Read-back then satisfies coverage, band (μ=0), geometric modes/caps, count/border/Hall/corridor/Menger rows, with identical split count. That supplies both split and δ lower bounds, subject still to matching domain, graph, support family and geometric policies.

For literally every M1 map defined only by ownership/connectivity/band, the other restrictions must also be relaxed: all states eligible/free, every connected geometric footprint allowed, and no contact cap beyond K and ZIP count. Include all geometric-domain units, not silently dropped zero-mass connectors. For a reinstated zero-mass unit, a feasible bookkeeping read-back can use owned ZIP count / unit ZIP count in place of undefined opportunity share; its mass coefficients remain zero. Every ZIP belongs to one district, so this share convention covers the unit and obeys t≤n. Geometric necessity proofs for border/count/corridor/Menger do not require positive mass. This identifies a sufficient bounding relaxation, not a production implementation; retained Toy deliberately enforces MODEL's M_v>0 domain.

Merely exempting **zero-share** contacts from η repairs their read-back but not E2/E3, whose bad contacts are strictly positive. Applying η only to positive-opportunity contacts likewise does not cover all M1 maps. Alternatively retain η and report the floor explicitly over η-compatible 𝒳 only. An ownership-aware relaxation is a lower-bound model, not a guarantee that its decoded continuous shares lift.

Consequently, owner's `s*+g` comparison has g≥0 only for maps covered by that bound. In E2, unrestricted drawn split count minus current master s* is −1. Do not call this negative difference an optimality gap or claim global drawn minimality from that master.

## Residual risks / limits

- Both LP and MILP use HiGHS floating point; not vendor-independent infeasibility certificates. Closed-form witness arguments and exhaustive drawings independently check the decisive counterexamples.
- No historical production counts or 13-split certification re-run; no source data permitted. Owner's all-state minimum cannot inherit an old restricted free-list certificate.
- Public-geography fixture tests printed SKIP notices despite runner summary's `0 skipped`; no polygon-source validation performed by this lane.
- Gap=1e-4 danger demonstrated arithmetically, not by a nonzero-gap MILP in retained suite; hard packet rule requires every MILP gap 0.
- Exact split/diameter two-pass checks do not implement owner's full split/cuts/defects/shape/balance ranking. They verify stated T claims; cuts can be a separate pinned per-support objective via double counting.

DECIDED: fixed exhaustive path/cycle/star toys instead of random sampling; closed-form counterexamples and independent fixed-n comparison make seed choice unnecessary.
DECIDED: “smallest” means finite feasible-master counterexample within positive-unit matching-domain policies, ordered by units then ZIPs; infeasible or mismatched-policy examples do not establish a finite split gap.

DECIDED: retained MILPs always use both gaps 0; author's proposed 1e-4 demonstration replaced by exact gap arithmetic to obey packet's hard solver rule.
