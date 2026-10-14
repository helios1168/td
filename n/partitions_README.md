# Sealed-run partitions for the main-map grid (2026-10-14)

One JSON per grid point in the schema of `tools/exp/contig/sealed.py` (`validate_partition`); `<point>.json` is the B pick, `<point>.A.json` the A fallback. Every file was run through `sealed.py run --partition F --root /tmp/td-partitions/dry --host m5 --dry-run` (log in `dryrun/<file>.log`, rc 0, nothing written).

Source: `tools/exp/region_arith.py --search` (branch `m5-studio/region-arith`, worktree read-only), its `/tmp/td-region-arith/7_partition_search.md` verdicts, recomputed in-process for the K feasibility sets (scripts in `/tmp/td-partitions/work/`, outside any repo). The recomputation reproduces the md's best B variant and chosen K for every point.

## Decisions (owner asleep, delegated)

- **B variant** = the search's best variant that passes every channel on the *win* track (its own verdict); `region=K/alt` below is the sealed region's K and k_alt; the rest region takes the point's K less the sealed regions' (`rest: true`).
- **k_alt**: one sealed region per channel gets a k_alt = K±1 that is window-feasible (win parts check) with the rest's K∓1 also feasible; the pick prefers band-feasible then the larger minimum headroom. sealed.py does not move the rest run's K when a region uses k_alt (the rest run keeps K = k_total less the primary Ks), so the merged K total is off by one if an alt draw is kept; see risks.
- **`forbid: ["DE-VA"]`** on every region holding both DE and VA (B1 corridor, B3 PA-DE-MD-DC-VA block), as in `scenarios/regions/main/sealed_example.json`; no other forbid pair.
- **A**: merged Census divisions, but one joint coarsening per point, win-feasible in every channel, ranked all-channel-band first, then most regions, then minimum headroom (sealed.py needs equal-or-disjoint state sets across a point's channels, so per-channel bests do not validate). A has `rest: false`, no k_alt (no rest to absorb it).
- **ne_plains WIFI**: not sealed; `{"regions": [], "rest": true}` with the point's K (3), whole New England 2 + plains 1.
- **nw34 explicit rest**: nw34's national footprint (34 states) is inside WIFI's (49), so the two channels' rest sets overlap without being equal; each channel lists one explicit `rest` region on the 36-state union (`rest: false`), K = point K less the sealed regions'. Same drawing unit, same K as the search's REST.

## B picks

| point | variant | K per channel (region=K/k_alt, +rest) | win-only channels | dry run |
|---|---|---|---|---|
| ne-48-bal | B7 | national:corridor=3+rest; WH:corridor=3+rest; FI:corridor=5/6+rest; WIFI:rest | WH | valid, 3 runs, 1 k_alt with final δ in window |
| ne-50-bal | B7 | national:corridor=3+rest; WH:corridor=3+rest; FI:corridor=5/6+rest; WIFI:rest | WH | valid, 3 runs, 1 k_alt with final δ in window |
| ne-50-filight | B1 | national:corridor=4+rest; WH:corridor=3+rest; FI:corridor=6/5+rest; WIFI:rest | none | valid, 3 runs, 1 k_alt with final δ in window |
| ne-52-bal | B7 | national:corridor=3+rest; WH:corridor=3+rest; FI:corridor=6+rest; WIFI:rest | FI | valid, 3 runs, 0 k_alt with final δ in window |
| ne-52-filight | B1 | national:corridor=4+rest; WH:corridor=3+rest; FI:corridor=6+rest; WIFI:rest | FI | valid, 3 runs, 0 k_alt with final δ in window |
| ne-cmp-tierP | B7 | national:corridor=3+rest; WH:corridor=3+rest; FI:corridor=5/6+rest; WIFI:rest | none | valid, 3 runs, 1 k_alt with final δ in window |
| nw49-48 | B3 | national:ne-ny-nj=3,pa-de-md-dc-va=1+rest; WIFI:ne-ny-nj=6,pa-de-md-dc-va=4/5+rest | none | valid, 3 runs, 1 k_alt with final δ in window |
| nw49-50 | B3 | national:ne-ny-nj=3,pa-de-md-dc-va=1+rest; WIFI:ne-ny-nj=6,pa-de-md-dc-va=4/5+rest | none | valid, 3 runs, 1 k_alt with final δ in window |
| nw49-52 | B3 | national:ne-ny-nj=3,pa-de-md-dc-va=1+rest; WIFI:ne-ny-nj=6,pa-de-md-dc-va=5+rest | none | valid, 3 runs, 0 k_alt with final δ in window |
| nw34-48 | B3 | national:ne-ny-nj=2,pa-de-md-dc-va=1,rest=11; WIFI:ne-ny-nj=6/7,pa-de-md-dc-va=4,rest=24 | none | valid, 3 runs, 1 k_alt with final δ in window |
| nw34-50 | B3 | national:ne-ny-nj=2,pa-de-md-dc-va=1,rest=12; WIFI:ne-ny-nj=7,pa-de-md-dc-va=4/5,rest=24 | none | valid, 3 runs, 1 k_alt with final δ in window |
| nw34-52 | B1 | national:corridor=4,rest=12; WIFI:corridor=12/11,rest=24 | none | valid, 2 runs, 1 k_alt with final δ in window |
| w1-48 | B3 | WIFI:ne-ny-nj=9/10,pa-de-md-dc-va=6+rest | none | valid, 3 runs, 1 k_alt with final δ in window |
| w1-50 | B3 | WIFI:ne-ny-nj=9/10,pa-de-md-dc-va=6+rest | none | valid, 3 runs, 1 k_alt with final δ in window |
| w1-52 | B3 | WIFI:ne-ny-nj=9/10,pa-de-md-dc-va=6+rest | none | valid, 3 runs, 1 k_alt with final δ in window |

Region state sets: B1/B7 `corridor` (B7 = NY NJ PA DE MD DC, VA to the rest; B1 adds VA, and for nw structures New England CT MA ME NH RI VT); B3 `ne-ny-nj` (New England + NY NJ) and `pa-de-md-dc-va`. Footprint-restricted to the channels that have the states.

## A fallbacks

| point | A (K per channel, region=K) | dry run |
|---|---|---|
| ne-48-bal.A | national:ma=3,mtn-pac=4,esc-sa=3,enc-wnc-wsc=4; WH:ma=2,mtn-pac=2,esc-sa=3,enc-wnc-wsc=3; FI:ma=5,mtn-pac=3,esc-sa=7,enc-wnc-wsc=6; WIFI:rest | valid, 5 runs, 0 k_alt with final δ in window |
| ne-50-bal.A | national:ma=3,mtn-pac=5,enc-wnc=2,esc-sa-wsc=5; WH:ma=2,mtn-pac=2,enc-wnc=2,esc-sa-wsc=4; FI:ma=5,mtn-pac=3,enc-wnc=5,esc-sa-wsc=9; WIFI:rest | valid, 5 runs, 0 k_alt with final δ in window |
| ne-50-filight.A | national:enc-ma=5,mtn-pac=5,esc-sa-wnc-wsc=6; WH:enc-ma=4,mtn-pac=2,esc-sa-wnc-wsc=5; FI:enc-ma=8,mtn-pac=3,esc-sa-wnc-wsc=9; WIFI:rest | valid, 4 runs, 0 k_alt with final δ in window |
| ne-52-bal.A | national:mtn-pac=5,esc-ma-sa=6,enc-wnc-wsc=4; WH:mtn-pac=2,esc-ma-sa=6,enc-wnc-wsc=3; FI:mtn-pac=3,esc-ma-sa=13,enc-wnc-wsc=7; WIFI:rest | valid, 4 runs, 0 k_alt with final δ in window |
| ne-52-filight.A | national:enc-ma=5,mtn-pac=5,esc-sa-wnc-wsc=6; WH:enc-ma=4,mtn-pac=2,esc-sa-wnc-wsc=5; FI:enc-ma=9,mtn-pac=3,esc-sa-wnc-wsc=10; WIFI:rest | valid, 4 runs, 0 k_alt with final δ in window |
| ne-cmp-tierP.A | national:ma=3,mtn-pac=5,sa=3,enc-esc-wnc-wsc=4; WH:ma=2,mtn-pac=2,sa=3,enc-esc-wnc-wsc=4; FI:ma=4,mtn-pac=3,sa=5,enc-esc-wnc-wsc=8; WIFI:rest | valid, 5 runs, 0 k_alt with final δ in window |
| nw49-48.A | national:ma-ne=3,mtn-pac=5,sa=3,enc-wnc=2,esc-wsc=2; WIFI:ma-ne=9,mtn-pac=5,sa=7,enc-wnc=7,esc-wsc=5 | valid, 5 runs, 0 k_alt with final δ in window |
| nw49-50.A | national:enc-esc=2,ma-ne=3,pac=4,sa=3,mtn-wnc-wsc=4; WIFI:enc-esc=8,ma-ne=9,pac=3,sa=8,mtn-wnc-wsc=6 | valid, 5 runs, 0 k_alt with final δ in window |
| nw49-52.A | national:sa=3,enc-ma-ne-wnc=6,esc-mtn-pac-wsc=8; WIFI:sa=8,enc-ma-ne-wnc=16,esc-mtn-pac-wsc=11 | valid, 3 runs, 0 k_alt with final δ in window |
| nw34-48.A | national:enc-esc=2,ma-ne=3,mtn-pac=4,sa=3,wnc-wsc=2; WIFI:enc-esc=7,ma-ne=9,mtn-pac=5,sa=8,wnc-wsc=5 | valid, 5 runs, 0 k_alt with final δ in window |
| nw34-50.A | national:enc-esc=2,ma-ne=3,mtn-pac=5,sa=3,wnc-wsc=2; WIFI:enc-esc=8,ma-ne=9,mtn-pac=5,sa=8,wnc-wsc=5 | valid, 5 runs, 0 k_alt with final δ in window |
| nw34-52.A | national:enc-ma-ne=5,mtn-pac=5,esc-sa-wnc-wsc=6; WIFI:enc-ma-ne=15,mtn-pac=5,esc-sa-wnc-wsc=16 | valid, 3 runs, 0 k_alt with final δ in window |
| w1-48.A | WIFI:enc=6,mtn=3,ma-ne=11,pac=8,sa=10,esc-wnc=5,wsc=5 | valid, 7 runs, 0 k_alt with final δ in window |
| w1-50.A | WIFI:enc=7,mtn=3,ma-ne=12,pac=8,sa=10,esc-wnc=5,wsc=5 | valid, 7 runs, 0 k_alt with final δ in window |
| w1-52.A | WIFI:enc=7,mtn=3,ma-ne=13,pac=8,sa=11,esc-wnc=5,wsc=5 | valid, 7 runs, 0 k_alt with final δ in window |

## Risks

- Win-only on a channel means the regional K passes the window parts check but not the final-δ band check (`ok_band`); those points: ne-48-bal (WH); ne-50-bal (WH); ne-52-bal (FI); ne-52-filight (FI). ne-48-bal's B1 passes band in every channel (h 0.43) where B7 (h 0.77) is win-only on WH.
- All K are dollar arithmetic, no feasibility certificate (the search's own notice).
- k_alt with a final δ of a hair (e.g. ne-48-bal FI k_alt 6, δ 0.0039) is a long shot; sealed.py draws it only when the primary drawing fails.
- A k_alt draw kept by sealed.py leaves the rest run at its primary K (see decisions).
