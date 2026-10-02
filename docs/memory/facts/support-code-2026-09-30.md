# The support-master code as landed (td#65–#72)

Facts about td's modules from the 2026-09-30 m5 wave (td orchestrator session 01a0f177 and its worker and reviewer forks). Each holds for the code at the merges of #67–#72 on `main` (2026-09-30) until the named function changes. The choices behind them are in `decisions/support-code-2026-09-30`.

## Scope (td#65, MODEL.md)
- **Zero-opportunity units and channels are out of scope** (#65 F1). They are dropped from V_c before solving, and their cells stay in the ledger with no owner, marked `dropped: zero opportunity`. Drawn shares, Proposition D and Claim 2's divided formulas assume M_v > 0 and τ_c > 0. The audit lists ownerless rows without failing and restricts ownership and count checks to retained cells and solved channels.
- OD2 excludes globally zero ZIPs from optimization. That is a different thing from channel-relative zero masses inside retained units (MODEL.md §1), so omitting a wholly zero ZIP is not an exporter defect.

## master.py (td#68)
- The master is solved with highspy directly. The solver report writes `gap` as 0 whenever |objective − bound| ≤ `audit.allowance(objective)`, and sets `mip_abs_gap` = 0 alongside `mip_rel_gap` = 0 for a certificate; HiGHS's default `mip_abs_gap` of 1e-6 would stop small-objective solves short of the exact tier.
- **The η cap is an explicit row.** Σ_{S∋v} n_S ≤ ⌊1/η_c⌋ is built as `eta_cap` for every unit. Without it, HiGHS's 1e-7 feasibility tolerance admitted copies a hair below η_c (η = 1/3 + 1e-8 gave three copies) that the exact δ-MILP's k-range excludes, so bisection and exact disagreed. Strict η-derived integer caps and tolerance-based η rows can otherwise give different verdicts.
- **`ETA_MIN` = 1e-4** (literal, tied to 100 × `FEAS_TOL` by a test). `build` and `exact_delta` refuse η_c below it, because under `FEAS_TOL` the η rows are vacuous in the incumbent check and a support member could be planned at share 0. `100 * 1e-6` is 9.999999999999999e-05 in Python floats, so thresholds that must compare exactly are written as literals.
- **`decode` rebuilds (n, t) and rechecks every master row at `FEAS_TOL` = 1e-6** (τ-normalized). A share-sum residual of at most 1e-6 goes onto the unit's largest t_{v,S}, and a larger miss raises. Holding a whole unit at t = n can move a band row by the residual × M_v/τ (2.5× in the reviewer's toy), so decoded rows need revalidation. After every row passes, zero decoded support shares stop the run, preserving Claim 1 footprints.
- The Menger row (MODEL.md §4.5 C9) is not built. `final_delta` defaults to `delta` (`td/spec.py`), so a scenario's final tolerance equals its planning band unless set.
- `exact_delta` returns the solver's lower bound in `Delta.lower` for an unknown result; that endpoint need not be infeasible.
- With `time_limit` = 0, highspy 1.15 returns kTimeLimit with `primal_solution_status` 0, objective inf and dual bound −inf: a genuine "no incumbent" result usable in tests (#68).

## audit.py (td#70)
- **Exact-tier allowance** is EXACT_ALLOWANCE × max(1, |objective|) with EXACT_ALLOWANCE = 1e-9, in objective units; the #70 round 2 supervisor approved it and the code cites the decision. A reported gap agrees when its implied bound, objective − gap·|objective|, lies within that allowance of the solver bound; at a zero objective only 0 or the actual gap agrees.

## realize.py (td#69)
- **The transport LP is normalized by the mean positive ZIP mass.** HiGHS's absolute feasibility tolerance (1e-7) let an LP with right-hand sides around 1e-9 return success with every flow at 0. After the solve, row residuals (FLOW_TOL = 1e-6) and positive-ZIP coverage are checked, and a positive ZIP left without flow raises `RealizeError` (#72 B1).
- `realize.py` sits at the 400-line cap `test_the_module_is_at_most_about_400_lines` enforces.
- Drawn-minus-planned mass sums to zero over each group of districts sharing split states, before repair; repair is the only leak (council 2026-10-01: 101.65 m_rel moved from FI's GA group to FI_17 in `runs/51_nomargin_wh20`).
- Mixed free/clipped repair must preserve the recipient's clipped footprint. The realizer and the audit share main-component ordering for cause reporting, and the expected-cell inventory comes from the retained input domain, not from drawing. Corridor-floor cache keys keep component-border multiplicity.

## output.py and spec (td#71)
- The ledger adds `county`, `cbsa` and `place` as 2025 GEOIDs, then `district_name`, `m_rel` and `reason`. District ids are `<channel>_<nn>`, and `audit.check_names` requires names unique across the run.
- `output.py` refuses a scenario name that isn't a plain file name when it names the default run directory: `os.path.join(geo.ROOT, "runs", name)` drops `runs/` for an absolute name. `td.spec.parse` accepts path-containing channel keys, so output filenames validate them separately.
- `reference/2025/areas.csv.gz` has 2025 CBSA titles but no population; summing `zcta_reference.pop2025` over a CBSA's ZCTAs gives it. CBSA titles use "--" between principal cities only when a city's own name has a hyphen. The committed suffixes classify all 393 metropolitan and 542 micropolitan records; CBSA membership alone doesn't.
- A sparse extract's Voronoi rook graph differs from the induced all-CONUS graph; on the seed-0 fixture the default induced graph falsely reported AL as 46 components. Sparse channels can leave realizer-owned zero-mass connector ZIPs absent from the ledger, so contiguity diagnostics use ledger-retained ZIPs.

## Exporter v3 filler guard (td#61, #72 A1)
- The guard matches the filler key case- and Unicode-insensitively and checks every string value and data-derived key. It exempts only the exporter's own field names in `META_FIELDS`, `NODE_FIELDS` and `CHANNEL_FIELDS`, and a test holds each list equal to the emitted keys. A literal walk had matched the exporter's own `zips_with_filler`, `n_filler_rows` and `n_filler_keys`. Keys nested under an exempt field are still checked; whole-level exemptions skip unknown keys.
- The export privacy boundary includes the raw spellings in `channels.json`, not only the gzipped instance. A raw substring search of serialized JSON misses quote, backslash and non-ASCII spellings; compare decoded strings.
- ZIP download validation keeps the target file type when validating `.part` files. NaN slips past comparison-only phantom-share checks.
