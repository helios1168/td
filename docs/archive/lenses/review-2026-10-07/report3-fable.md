# Round 3: carve-first, tested against the v2 loop

Reviewer: Claude Fable 5.1, 2026-10-07. Read-only. Sources: `CONSOLIDATED.md` (round 2 and both owner-answer sections), `METHOD-carve-first.md`, the v2 drafts, and the td checkout (`path:line`). Masses are m_rel or dollars; no sales or names. Arithmetic uses the IFA masses in `runs/exp/contig/whole127/ifa46-whole/districts.csv` and the extract rate $1.25197M per m_rel (E1).

**Verdict: ADOPT WITH CHANGES** (section 6). One finding comes first because it holds for either method: under rule C, IFA has no plan at the E2 band, and the reason is Maryland, not Connecticut (section 5). The lanes can start FI 20 and the main map; IFA waits for one owner decision.

## 1. Soundness

**The selection MILP is correct, with one scoping condition the draft lacks.** Units, not states, index the coverage rows (DC is a unit, `td/spec.py:56-58`; DC+MD in `ifa46-whole` is a two-unit support, not a merged unit). With that:

- Coverage Σ_{g∋v} x_g + Σ_{p: v∈σ(p)∪A(p)} y_p = 1 per unit, the K row Σ x_g + Σ k_p y_p = K, and x, y binary are a set partitioning. "At most one pattern per σ" is implied, as the draft says.
- Rule C is not something the generator must know. An attach unit of a selected pattern is covered by that pattern alone, so it is whole in the map. The generator only needs attach units ≠ σ and pairwise-disjoint attach sets. A joint pattern (σ a set of states) is then just a column with |σ| in the splits level; rule C becomes a library policy, and D1 (b) costs nothing.
- The lexicographic objective is representable exactly, and better than v2's: every level of the scorer's rank key is column-local or a max. Splits and cuts are sums over y; thin links and small pieces are per district (`tools/looks/score.py:226, 252`); crowded is per pattern (`:227`, it depends on k_p); extent and states-per-district are maxima, so epigraph rows; worst deviation is a max, mean deviation a sum. Solve it as sequential passes with pinning, gap 0, as A does; never as one weighted sum, because the last levels are continuous.
- The K row should be a range where the band is K-free: 46 ≤ Σ ≤ 55 for IFA solves every K at once; on the main map, one MILP with four coverage blocks and 48 ≤ Σ_c K_c ≤ 54. Capacity for IFA at E2: 48,989 / 1,148.19 = 42.7 and 48,989 / 798.74 = 61.3, so the window 46–55 is inside.

**"Every column passed the gate" does give an M1-clean map with no repair, under three conditions.** M1 is per district: one component on the polygon graph and no neck (`td/audit.py:800-925`, `district_pieces`, `district_necks`), plus every (ZCTA, fine channel) cell owned once. A column's ZIP set is the union of its units' `units.zips`, zero-opportunity ZCTAs included, which is what `wholeplan.m1_verdict` checks (`tools/exp/contig/wholeplan.py:66-85`) and what `check_m1` sees after assembly. The conditions:

1. A column passes only on `m1_verdict` status `pass`. `unresolved` (the 60 s neck limit, `audit.py:446`) is not a pass; re-run it with a longer limit offline or leave it out.
2. The column's gate ran on the same graph the final audit uses (`td.geo.polygon_graph` with connectors; R5's identity hash).
3. No ZCTA is added to a district after its gate ran (R13).

A fact the draft does not use: the M1 verdict depends on the ZIP set only. `district_necks` uses land area, and `district_pieces` uses mass only to order components. So a pattern that passes M1 passes for every channel and every band; only its mass window is channel-specific. The geometric library is shared across channels and K.

**The certificate claims are scoped correctly only if the library sits inside the master's domain.** s_lower is a bound over rule-C η-plans on the support family 𝒮_c at the band. s_drawn ≥ s_lower holds, and equality proves fewest splits over that domain, if and only if every library column is a plan the master could have chosen: (a) each column's support σ ∪ A_i (or g) is in 𝒮_c, with its size cap, distance caps and contact rule (`td/supports.py:213-256`); (b) each piece holds at least η·M_σ; (c) masses are the same dollar masses (R1). Corridor floors and Hall rows are valid for any M1 drawing, so they come free. The draft's pattern generator has no family check, so a pattern with an off-family attach set could give s_drawn < s_lower and void the equality claim. Write (a) and (b) into the generator and into MODEL §4.12. If the owner allows joint patterns for a named pair, the master that gives s_lower must relax rule C for that pair, or the bound no longer covers the library. "Minimal" stays forbidden (A3): equality proves fewest within the domain, and the domain is named in the report.

## 2. Against the v2 loop

Carve-first is faster and more likely to deliver, for one structural reason: v2 needs one plan whose every carve succeeds, while carve-first recombines carves across plans and across K. Specifics:

- **FI 20.** The existing FI map `set125/fi20_fi_nonc-r1` already satisfies rule C and, in dollars at FI's rate ($1.242M per m_rel, from $925M over 744.6 m_rel average), every district lies in [874M, 981M], inside D3's [765M, 1,035M]. Its six split states (NY, PA, CA, OH, TN, FL; 9 cuts) are 20 M1-passing columns. Seeded into the library, s_drawn ≤ 6 on day one, before any carve, and the forced-split floor at D3 is 5 (NY, PA, CA, OH, FL over U = 833 m_rel). So FI 20 is g ≤ 1 at t = 0; the question left is whether A proves 6 or finds a 5-split plan to request. v2 would redraw all of this from scratch.
- **Main map.** Under D3 the national 15 lead map fails on its lightest districts (841 m_rel ≈ $1,047M, below $1,062.5M) and WH 11 on one or two (672.6 and 683.7 m_rel ≈ $841M–$855M against $850M). The K choice moves (national 14 gives a $1,206M average with 11.9% of room below). Carve-first handles this in the selection MILP with K per channel free and 48 ≤ ΣK ≤ 54; v2 needs a grid, an owner pick, then a re-plan per K.
- **IFA.** K is a range in one MILP, so the K 46–55 sweep is free. But IFA under rule C has no plan at E2 (section 5), so neither method delivers IFA until the owner decides.

**What it loses.** (1) g is never proved: a carve that found nothing is "no pattern found in budget", so a gap between s_drawn and s_lower may be the library's fault or the geography's, and nothing distinguishes them (v2 under D4 had the same hole, since unknown was never a cut). (2) Balance is fixed at generation; the MILP picks among variants but cannot move a ZCTA. (3) A larger library than needed if columns are checked eagerly; check them lazily. (4) The master's exact per-piece targets become requests, not constraints; a plan the generator cannot realise leaves g > 0 with no proof that the plan was undrawable. (5) B's joint MILP and §4.10's proof leave the critical path; they return only if the owner wants "proved no pattern" for a small state.

**R1–R13 under carve-first.**

| R | Status | Why |
|---|---|---|
| R1 dollar adapter | keep | every column's band test and every window is in dollars |
| R2 §4.12 any-interval | keep, add the domain statement of section 1 | |
| R3 `drawable` signature | drop from the path, optional later | no per-piece proofs are needed |
| R4 conditional support exclusion | drop | there are no bans; a failing whole column is simply absent |
| R5 content identity | keep, now on every library entry | graph, rates, band, η, family caps, generator version |
| R6 search layers | replace | master pool plus exclusion rows and a request budget (change 8) |
| R7 balance LP, s_lower + g | modify | balance is a level of the selection; an optional re-gated local move after selection; the reporting rule stays |
| R8 units in audit and render | keep | |
| R9 empty-attach pieces, deadline, incumbent | keep | they describe the generator |
| R10 grid, main-map combinations | keep as stage 0, then the MILP's K range makes the combination table an output | |
| R11 staging, arithmetic screen | keep and extend to rule C (section 5) | |
| R12 replace #103's body, stub, tracking | keep | |
| R13 zero-opportunity units, `state` list, fields, checkpoint | keep; σ as a set is the natural form | |

v2 pieces that drop out: `holder_nogood` as a certificate cut (its exact encoding survives as `--exclude`, section 3), `support_ban` and its validity rules, P's feedback table, B's MILP infeasibility reporting.

## 3. Pricing and library growth

**The pricing problem, exactly.** At the splits level the LP relaxation is min Σ_p y_p subject to the coverage rows (duals π_v, free sign) and the K row (dual μ). Reduced costs: a whole column g has −Σ_{v∈g} π_v − μ; a pattern p for σ has 1 − Σ_{v∈σ∪A(p)} π_v − k_p μ. Pricing for σ is: choose k ≥ 2 and pairwise-disjoint attach sets A_1..A_k with every {σ} ∪ A_i in 𝒮_c, and a partition of σ's ZCTAs into k connected pieces with piece_i ∪ A_i in the band and M1-clean, maximising Σ_i Σ_{v∈A_i} π_v + k μ. Its feasibility oracle is the carve itself, so exact pricing is out of reach; a heuristic pricer enumerates attach tuples from the family, orders them by prize, and carves the top few. Whole columns need no pricing: the family is enumerable, so all in-band supports can be priced by a scan.

**A heuristic pricer is enough, because the bound does not come from the LP.** A heuristic pricer cannot certify LP optimality, so the restricted master's LP value is never a valid lower bound and must not be reported as one. That is fine here: s_lower is A's, and pricing only lowers s_drawn. Two cautions: the LP of a set partitioning with 49 rows and thousands of columns is degenerate, so duals jump between iterations; and the duals say nothing about which piece shapes are drawable. Treat dual pricing as the second source of requests.

**The master is the pricer of record.** A's master is the relaxation of the full-pattern selection problem that drops drawability, so its plan is the best possible request: for each split σ it names k, the attach sets and target shares, and every whole support. The loop is: A's plan → one request per split state (σ, k, A_i, windows from the band and the attach masses) → generator → library → selection. If the plan's whole supports pass and every request is filled, the plan itself is a feasible selection and s_drawn = s_lower. If not, P asks A for the next plan with `--exclude` carrying the tried multiplicity vectors. The `holder_nogood` encoding is exactly the right device for this enumeration, and here its validity no longer matters for the certificate: an over-exclusion costs search, not correctness, because s_lower was fixed by the first clean solve. Keep the exact encoding anyway; it is cheap and it keeps the enumeration honest.

**A plan the library cannot match** is used three ways and never as a cut: as requests with the plan's windows; as the seed of the next exclusion; and as a diagnostic row (which request failed, after how many attempts, nearest miss in mass and in M1), which is the first measurement of U55 the project will have.

**Seed the library before pricing anything.** Every M1-passing district of every tier 1, P and E map in `tools/shortlist/shortlist.json` is a column once re-weighted in dollars and re-checked against the band. This is free, and for FI 20 it is already s_drawn ≤ 6.

Published analogues, named as the brief asks and not read this session: set partitioning for districting (Garfinkel and Nemhauser, 1970, claimed) and column generation for districting with a heuristic pricer (Mehrotra, Johnson and Nemhauser, 1998, claimed). Neither is in `kb/references.bib`; nothing above depends on them.

## 4. Scale

| Quantity | Estimate | Source |
|---|---|---|
| Family 𝒮_c per channel | IFA 1,963; national 1,472; WH 1,931; FI 1,931; WIFI 16 | `docs/RESULTS.md:1166`, `docs/memory/facts/scenario-sweeps-2026-10.md:6` |
| In-band whole columns | a fraction of the family; measure | unknown |
| Gate cost per column | about 0.1 s typical; 60 s worst (neck limit) | `whole127/ifa46-whole`: 3 rounds of 46 districts plus 3 master solves in 8.3 s |
| Whole-column pass over a family | minutes typical | 2,000 × 0.1 s |
| Split states under rule C | FI 20: 5–6; IFA: 15 or more (section 5) | arithmetic |
| Requests (σ, k, attach tuple) | FI 50–150; IFA 300–600 | tens of family supports contain each σ; disjoint tuples after the window filter |
| Cost per request | 20 seeded attempts × 1–5 s gate = 20–100 s; ×3 variants | B plan 1.1; CT has 289 ZCTAs (`RESULTS.md:523`), NY about 1,800 |
| Exhaustive library, 6 processes | FI about 0.3–1.5 h; IFA 1–4 h | above |
| Master-guided library | FI: minutes (the pool's 5 plans × 5–6 requests) | |
| Selection MILP | about 50 rows (200 on the main map), 10³–10⁴ columns: seconds per pass | set partitioning with few rows |

**Measure first, in this order:** (1) the rule-C arithmetic screen at D3 and E2 (section 5), minutes; (2) A's master verdicts per channel, s_lower or infeasible; (3) the seeded library plus the selection MILP on FI 20, which gives g at t = 0; (4) the whole-column pass rate and its time distribution on FI's family; (5) B on the three tight requests, CT with RI (window 78.7 m_rel), MN with SD, NE and ND, and NC with SC, which decide whether 80–150 m_rel windows are reachable at ZCTA grain; (6) g on FI 20 after the pool's requests.

**Stop rules.** The MILP needs none below about 10⁵ columns; above that, drop dominated patterns (same σ, k and attach tuple, no better at any level). The library needs a budget, which is the E4 question in its new form: per channel, a request budget (6 processes × 2 h) and an enumeration budget (10 master plans per split count, two counts above s_lower). At the budget, report s_lower, s_drawn, g and the unfilled requests.

## 5. E2 check, verified and extended

**CT at the extract rate, confirmed.** Target 1.25e9 / 1.25197e6 = 998.43 m_rel; L = 798.74, U = 1,148.19. CT 1,333.63, RI 342.56.

| CT in | condition | result |
|---|---|---|
| 1 piece | CT ≤ U | over by 185.4 |
| 2 pieces, one with RI | piece_RI ∈ [456.18, 805.63] and [185.44, 534.89] | window [456.18, 534.89], width 78.71 |
| 2 pieces, neither with RI | 2L ≤ CT | short 263.9, so RI must sit with CT, not MA |
| 3 pieces | 3L − RI ≤ CT | short 720.0 |

MA 1,535.39 is over U and splits; with NH and ME (483.69) on one piece and VT (166.73) on the other, the first piece has window [553.9, 664.5], width 110.6. New England is feasible on paper. The CONSOLIDATED arithmetic is right.

**The screen stops at CT too early. MD makes IFA infeasible under rule C at E2, at any η.** DC is its own unit with 13.81 m_rel (the 14 non-zero DC rows of `whole127/ifa49-pieces/ledger.csv:6173-6194`), so MD is 1,203.64, over U. Under rule C an MD piece's district holds only whole neighbours of MD: DC 13.81, DE 211.30, WV 121.67, VA 1,120.63 (PA splits). Two districts holding MD pieces need 2L = 1,597.48, so attach mass ≥ 393.84, and DC + DE + WV = 346.78 falls short. With VA, VA's district can hold at most 27.56 of MD, which leaves ≥ 1,176.08 of MD for the others: one district is over U, and two districts have at most 1,176.08 + 346.78 = 1,522.86 < 2L. More pieces only add L each. So MD has no rule-C plan at E2, at D3 ±15% (attach needed 493.7), and at the old τ-bands at K 50. My round-1 hand check that claimed a 14-split rule-C allocation at K 50 was wrong on MD and on SC; this is why the screen must run in code, not by hand.

Other findings of the same screen, all at E2:

- **SC forces one more split.** SC 656.63 is under L; SC+NC = 1,722.91 and SC+GA = 1,583.41 are over U; SC's only neighbours are NC and GA. So NC or GA splits: NC with SC has window [142.1, 267.5]; GA with SC needs AL on the other piece, window [247.7, 491.6].
- **The Upper Midwest is pinned, not infeasible.** MN 1,190.40 and WI 1,177.14 are both over U. WI's only whole neighbour with enough mass is IA (needs ≥ 420.3; IA 630.23), so IA goes to WI. MN then needs ≥ 407.1 without IA: ND+SD = 308.9 fails, SD+NE = 556.6 works; MN piece with ND, SD and NE has window [59.5, 366.3]. That pins NE, SD and ND to MN, after which KS+OK = 785.4 is 13.3 under L and MO, LA, TN (796.50, 2.2 under L), AR, MS, OK and NM form a chain with more claimants than small states; the master settles it, probably with TX in four pieces or IL in three.
- **Forced splits:** CA, FL (4 pieces: 3U = 3,444.6 < 3,486.95), TX, NY, NJ, PA, OH, MI, IL, MN, WI, MD, MA, CT, plus NC or GA: s_lower ≥ 15 under rule C at E2, against 21–22 on today's IFA maps, and infeasible because of MD.

**Owner decision, before any IFA lane work:** (a) a joint pattern for MD with a PA piece (what every drawn map has done, the "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD" districts), carved jointly; (b) county pieces of MD as whole units (OD4), which satisfies rule C formally; (c) rule C off for IFA; or (d) a different band. None may be chosen by a lane. The same screen should run for the main map at D3 before its K is argued.

## 6. Verdict and lanes

**ADOPT WITH CHANGES.**

1. **Stage 0 before everything, under A, in the first hour.** Freeze the rates (R1). Extend `tools/exp/split_floor.py` to rule C: for each unit over U, the attach-capacity test of section 5; for each unit under L, the company test (some whole neighbour set, or a split neighbour, brings it into the band). Run it at D3 for national 13–16, WH 10–12, FI 19–21, WIFI 3 and at E2 for IFA, then A's master for s_lower or infeasible. Post the table on #103 and #130, with the MD decision put to the owner.
2. **Scope the certificate** (section 1): the generator admits only family supports and η-floored pieces; §4.12 states the domain and the equality rule; a joint pattern needs a master with the matching rule-C exception.
3. **Seed the library** from the shortlist's M1-passing districts, re-weighted in dollars, re-checked against the band. FI 20 starts at s_drawn ≤ 6.
4. **The master is the pricer of record**; dual pricing is the second source. `plan.py` keeps the exact `holder_nogood` encoding as `--exclude`; `cuts.json`, `support_ban` and the proof fields go. Requests are memoised by content identity; a request's terminal state is "no pattern found in budget", never infeasible.
5. **Selection MILP as sequential passes** on the scorer's rank key, gap 0, K as a range (IFA 46–55; main map 48 ≤ ΣK ≤ 54 with K per channel free unless the owner pins it). Joint patterns only from the owner's list.
6. **Gate semantics** as section 1's three conditions; the final `check_m1` on the ledger is an integration check, and a failure there is a bug.
7. **Balance**: 3 variants per request with different seeds; an optional post-selection local move inside one split state, both districts re-gated, accepted only if the drawn rank improves (R7's rule).
8. **Budget** (E4 in its new form): per channel, 6 processes × 2 h of requests and 10 master plans per split count for two counts above s_lower; at the budget, report s_lower, s_drawn, g and the unfilled requests.
9. **Lanes.**
   - **A (#103):** stage 0; the dollar adapter; the rule-C master with s_lower and the pool; `--exclude`; no cuts, no bans. Sonnet 5.5, advised.
   - **B (#129):** the pattern generator: one request in, up to 3 gate-passed variants out, with the attributes the rank key needs (dollars, cuts, thin links, small pieces, extent, states); the whole-column checker is `wholeplan.m1_verdict` reused. No MILP on the path; §4.10 becomes optional. Measure CT with RI, MN with SD+NE+ND, NC with SC, then NY 4 and CA 4. Opus 5.5, advised.
   - **P (#130):** the library store with identity hashes, seeding from the shortlist, the request manager (pool first, duals second), the selection MILP, assembly, run folder, audit, scorer (cuts key, per-district $ band), the report with s_lower, s_drawn, g and unfilled requests. Round 1 against a canned library and A's stub; round 2: FI 20, then the main map with K chosen by the MILP and confirmed by the owner, IFA only after the MD decision. Sonnet 5.5, advised.
   - Landing order A, B, P; each lane owns its doc sections; the checkpoint line in every lane (R13).

## LEARNED lines

LEARNED: Under rule C at the E2 band (IFA, −20%/+15% of $1.25B, extract rate), MD (1,203.64 m_rel; DC is a separate unit of 13.81) has no plan at any η: its whole neighbours DC+DE+WV total 346.78 against the 393.84 two pieces need, and VA (1,120.63) can take at most 27.56 of MD; so IFA under rule C is infeasible at E2, at D3 ±15% and at the K 50 τ-bands, and only a joint MD+PA carve, county pieces of MD (OD4), rule C off, or another band can rescue it.
LEARNED: Under rule C at the E2 band, SC (656.63) forces NC or GA to split (SC+NC 1,722.91 and SC+GA 1,583.41 are over U 1,148.19), and WI's only sufficient whole neighbour is IA, which pins MN to SD+NE(+ND); the rule-C forced-split floor for IFA at E2 is 15, against 21–22 on today's IFA maps.
LEARNED: The round-1 hand check of a 14-split rule-C IFA allocation at K 50 was wrong on MD and SC; the rule-C arithmetic screen (attach capacity for units over U, company for units under L) must run in code, as an extension of `tools/exp/split_floor.py`.
LEARNED: An M1 verdict depends on the ZIP set only (`district_necks` uses land area, `district_pieces` uses mass only to order), so a gate-passed district is a valid column for every channel and band; only the mass window is channel-specific.
LEARNED: `set125/fi20_fi_nonc-r1`'s FI 20 districts already satisfy rule C with 6 split states and 9 cuts, and in dollars at FI's rate ($1.242M per m_rel) every district lies in [$874M, $981M], inside D3's [$765M, $1,035M]; seeding a column library from it gives s_drawn ≤ 6 before any carve.
LEARNED: Under D3 the national 15 lead map's two lightest districts (841 m_rel, about $1,047M) fall below $1,062.5M and WH 11's lightest (672.6 m_rel, about $841M) falls below $850M, so the main map's K per channel must be re-chosen at the target band.
DECIDED: none
