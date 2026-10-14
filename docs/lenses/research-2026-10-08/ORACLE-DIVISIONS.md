# Oracle review: division arithmetic

## Inherited decisions

- Five fine channels require exact coverage: `national_chase`, `wells_wh`, `wells_fi`, `wh`, `fi`.
- Per state, candidate routing is binary: three pure channels, or all five fine channels consolidated into WIFI. This scope does not enumerate finer within-state routing.
- Pure-channel dollar windows remain national [$1,062.5M, $1,437.5M], WH [$850M, $1,150M], FI [$765M, $1,035M].
- WIFI uses ±15% of **global WIFI dollars / global WIFI district count**. Supervisor confirmed: independent division means require a new owner decision.
- Sealed divisions remain unapproved. M1, original-state split accounting, rule C and main-map total K constraint remain applicable.

## Diagnosis: enumerate routing, not existing layouts

Owner requests fresh routing possibilities. Previous division table instead screened one existing layout. Its negative conclusions cannot apply to all layouts.

Read supplied `state_fine_usd.csv`: all 49 CONUS state/DC rows and five fine-channel columns exist, but values are rounded to $1M. Suitable for sketches only. Regenerate full-precision dollars before any pass/fail, using approved extract rates and complete covered-cell inventory.

### 1. State decision

For each state \(s\), let \(x_s=1\) mean combined; otherwise pure.

Define full-precision state masses:

\[
N_s=D_{s,\mathrm{national\_chase}}+
D_{s,\mathrm{wells\_wh}}+D_{s,\mathrm{wells\_fi}},
\quad H_s=D_{s,\mathrm{wh}},\quad F_s=D_{s,\mathrm{fi}}.
\]

For division \(d\):

\[
M_{dc}=\sum_{s\in d}(1-x_s)D_{sc},
\qquad
M_{dW}=\sum_{s\in d}x_s(N_s+H_s+F_s).
\]

Enumerate all \(2^{|d|}\) assignments—at most 512 per division. Include all-pure and all-combined. Do not inherit current `model_channel` assignments.

Assert every required `(ZIP, fine channel)` cell routes exactly once. Zero-dollar cells still require ownership.

### 2. Pure-channel necessary checks

For positive mass and fixed window \([L_c,U_c]\):

\[
\left\lceil M_{dc}/U_c\right\rceil
\le K_{dc}\le
\left\lfloor M_{dc}/L_c\right\rfloor.
\]

Empty footprint permits K=0. Zero mass alone does not prove empty footprint.

For each assigned state/channel, report:

- Mass above U: state must split.
- At least \(\lceil D_{sc}/U_c\rceil\) districts must touch that state; corresponding cuts lower bound is this count minus one.
- Positive mass below L: cannot form a standalone district; needs same-channel territory reachable within allowed geography.

Then strengthen aggregate checks using **same-channel connected components**. Each component must independently admit a district count; sum component ranges. A combined state cannot serve as a pure-channel bridge merely because its geographic border connects two pure states.

Use adjacency that safely overapproximates permitted polygon/connector connectivity for rejection tests. Component arithmetic remains necessary, not sufficient.

### 3. WIFI: global coupling survives sealed boundaries

WIFI has no fixed dollar target. Let

\[
M_W=\sum_d M_{dW},\quad K_W=\sum_d K_{dW},
\quad [L_W,U_W]=[0.85M_W/K_W,\;1.15M_W/K_W].
\]

Once global \(M_W,K_W\) are chosen, division and connected-component masses have conditional K ranges using that common window.

Before then, local WIFI cannot receive an unconditional “feasible” verdict. Choosing local K=1 and defining a local mean would make every positive connected remainder pass balance automatically—an unauthorized policy change.

Combined footprint may have several disconnected components. They need not connect to each other, but each must receive enough separate districts and pass component arithmetic at the **same global WIFI window**.

Actual feasibility requires a partition into connected, in-band districts. A whole-state grouping check may provide a constructive witness, but its failure cannot rule out permitted ZCTA-level splits.

### 4. Across divisions

Under sealed boundaries:

- Select one routing assignment per division.
- Select compatible channel/component district counts.
- Enforce main-map total K within 48–54.
- Enforce shared WIFI mean and all remaining count restrictions.

Use small coordinator over local summaries; do not solve nine unrelated WIFI problems.

Without sealing, division deficits are not infeasibility proofs: districts can draw mass across boundaries. Keep local tables as summaries; connect channel footprints across divisions before component tests. Independent solves would require an agreed boundary/overlap scheme.

## Drift / contradiction check

1. **“WIFI cannot exist under sealing” is false.** WIFI can contain separate districts in separate divisions. Existing cross-division districts may need replacement.
2. **“Division K ranges are feasible” overstates arithmetic.** Report “passes necessary mass screen”; geometry, indivisible ZCTAs and rule C remain unresolved.
3. **Current enumeration accepts WIFI without testing it.** Its `wifi_ok` helper merely returns mass, and pure-channel survival is not whole-map feasibility.
4. **Rounded inputs can flip threshold results.** Do not publish exact assignment counts from rounded CSV.
5. **One failed drawing cannot justify an unconditional support ban.** Same support may admit another valid drawing; #127’s fixed-unit logic does not transfer automatically.
6. **Earlier national K15 impossibility claim is wrong.** Mean $1,126M lies inside its target window. A sufficiently narrow dollar-mean band can fit inside D3; existing m_rel bands require additional care for mixed fine-channel rates.
7. **MD waiver applies to MD alone**, not DC+DE+MD. For IFA arithmetic, reserve MD’s one district and remove its mass before applying ordinary bounds to South Atlantic remainder. Previous table did not implement that operation.

## Recommendation: smallest useful owner deliverable

Produce one complete machine-readable table plus short review page.

Each row contains:

- Division; combined-state subset; complementary pure states.
- Four dollar masses.
- Pure-channel aggregate and component K ranges.
- Forced split incidences and cuts lower bounds; under-L attachment obligations.
- WIFI component masses and conditional requirements.
- Status: `mass-rejected`, `component-rejected`, or `survives necessary screens`.
- Rejection reason and input/rate provenance.

Keep all rows. For readable presentation, group by combined-state count and show nondominated tradeoffs against forced splits. **Fewest combined states is not an approved optimization priority**; present it as navigation, not “best.” Settled map ranking uses actual splits, cuts, defects, shape, balance—not these arithmetic proxies.

Next, join surviving rows under global K and WIFI constraints. Only then select one small routing candidate for drawing and exact M1 evaluation.

## Risks / need from main agent

No unresolved clarification for this sketch. Supervisor confirmed global WIFI mean and full-precision requirement.

Owner still decides sealed boundaries and any new routing preference. Arithmetic cannot promise shape, M1, rule-C feasibility or runtime speedup. Do not launch another multi-scenario draw/repair batch from current tables.

## Suggested execution prompt

No implementation handoff warranted yet. Deliver sketch and corrected scope first; approved follow-up is a small reproducible arithmetic enumerator, not a new optimizer.

LEARNED: Supplied state-dollar CSV is $1M-rounded; exact enumeration needs full-precision inputs. Global WIFI mean couples divisions even when district boundaries are sealed.
DECIDED: Treat surviving arithmetic assignments as necessary-screen candidates, not feasible maps; preserve global WIFI mean as confirmed by supervisor.