# Morning package, sealed overnight 2026-10-14

*Final, 2026-10-14 07:00 CDT; all runs stopped (both drivers and every solver process, 06:55 CDT). Main-map table reflects the SEALED.json files as last written: m5 `main/`, `main2/` and `main2_m5/` (11:55 UTC), m2 `main2/` (11:55 UTC).*

## Summary

1. **IFA map: all seven K = 48..54 pass** (7/7). Every district is inside the $1,000-1,437.5M window; M1 (one connected piece per district) fails only on the Manhattan district, the one exception you allowed.
2. **Main map: 1 of 15 points has a passing map, `ne-48-bal`** (the 2026-10-13 unsealed draw, re-judged tonight as `ne-48-bal-r2`): it passes M1 under tonight's water/empty-land rule, with 48/48 districts in window and 8 split states. It is not sealed. The other 14 points have no passing sealed map, and nothing more will finish tonight.
3. **w1-48, w1-50, w1-52:** the big rest region (36 states, WIFI, band about ±2%) was planned for w1-48 and w1-50, but the exact draw left 14,859-16,571 ZCTAs undrawn within its time (no connected drawing). w1-52 was never planned on m2 (25-min cap); on m5 it was planned (K = 37) and the draw ended the same way (16,001 undrawn). The small NY/NJ and PA/DC regions of these points also ended in a drawing error.
4. **nw49-48/50/52 and nw34-48/50/52:** a rest region has no plan in band (nw49: the 36-state rest, national channel; nw34: a western or southern rest region, WIFI or national), and the DC/DE/MD/PA/VA region has no national plan at K = 1.
5. **ne_plains (all six points except the unsealed `ne-48-bal` deliverable):** the east block (20-21 states) has no plan in band, in the national channel (K = 6-7) or WH (K = 5-6). Sealing removes the corridor states the unsealed plan used as fillers.
6. Why: each point is solved as separate regions, each with one symmetric $ band; a region whose blocks differ in dollar density cannot fit one band (details below).
7. Round 1 (first partition) also timed out drawing the coupled New York group of the corridor (about 337 s per channel); round 2 split the regions into connected components and gave the draw 6,000 s.
8. Shape check (eye review only, not a gate): 22 districts flagged across the 8 passing maps by the provisional rule; list in [shape/FLAGS.md](shape/FLAGS.md).
9. Nothing was merged to main for the sealed driver (`m5-studio/sealed`, review ended at max rounds with concerns); tonight's runs use snapshot 43ca971.
10. Everything below links into `maps/` (renders), `shape/` (shape measures) and the run folders.

## IFA, K = 48..54

Window $1,000-1,437.5M per district. Source: [ifa/IFA_INDEX.md](ifa/IFA_INDEX.md). "Flags" = districts flagged for eye review in [shape/FLAGS.md](shape/FLAGS.md).

| K | verdict | M1 detail | in / under / over | split states | mean $/district | flags | maps |
|---|---|---|---|---|---|---|---|
| 48 | passes | Manhattan only | 48/0/0 | 21 (AZ CA CT FL IL IN KS MA MD MI MN NC NJ NV NY OH PA TN TX VA WI) | $1,277.8M | 4 | [summary](maps/IFA_K48_summary.png), [pages](maps/IFA_K48_pages.pdf), [IFA map](maps/IFA_K48_IFA.png) |
| 49 | passes | Manhattan only | 49/0/0 | 21 (AZ CA CT FL IL IN KS MA MD MI MN NC NJ NV NY OH PA TN TX VA WI) | $1,251.7M | 3 | [summary](maps/IFA_K49_summary.png), [pages](maps/IFA_K49_pages.pdf), [IFA map](maps/IFA_K49_IFA.png) |
| 50 | passes | Manhattan only | 50/0/0 | 21 (AZ CA CT FL IL IN KS MA MD MI MN NC NJ NV NY OH PA TN TX VA WI) | $1,226.7M | 3 | [summary](maps/IFA_K50_summary.png), [pages](maps/IFA_K50_pages.pdf), [IFA map](maps/IFA_K50_IFA.png) |
| 51 | passes | Manhattan only | 51/0/0 | 19 (CA CT FL IL IN KS MA MD MI MN NC NJ NY OH PA TN TX VA WI) | $1,202.6M | 3 | [summary](maps/IFA_K51_summary.png), [pages](maps/IFA_K51_pages.pdf), [IFA map](maps/IFA_K51_IFA.png) |
| 52 | passes | Manhattan only | 52/0/0 | 18 (CA CT FL IL KS MA MD MI MN NC NJ NY OH PA TN TX VA WI) | $1,179.5M | 2 | [summary](maps/IFA_K52_summary.png), [pages](maps/IFA_K52_pages.pdf), [IFA map](maps/IFA_K52_IFA.png) |
| 53 | passes | Manhattan only | 53/0/0 | 18 (CA CT FL IL KS MA MD MI MN NC NJ NY OH PA TN TX VA WI) | $1,157.2M | 2 | [summary](maps/IFA_K53_summary.png), [pages](maps/IFA_K53_pages.pdf), [IFA map](maps/IFA_K53_IFA.png) |
| 54 | passes | Manhattan only | 54/0/0 | 21 (AZ CA CT FL IL KS MA MD MI MN NC NJ NV NY OH OR PA TN TX VA WI) | $1,135.8M | 3 | [summary](maps/IFA_K54_summary.png), [pages](maps/IFA_K54_pages.pdf), [IFA map](maps/IFA_K54_IFA.png) |

The Manhattan district (the same 40-ZIP neck, 8.53 km wide, in every K) is the only M1 failure; detail per K in the index.

## Main map, 15 grid points

Each point is solved as several regions (a "corridor" of DC/DE/MD/NJ/NY/PA, a New England block, a western block, a big east/south block ...) and the pieces are merged. A point yields a sealed map only if every region does. Times are CDT. Sources: `main/`, `main2/`, `main2_m5/` (m5) and `main2/` (m2) SEALED.json, and [main_unsealed/INDEX.md](main_unsealed/INDEX.md).

| point | final outcome | decisive reason |
|---|---|---|
| ne-48-bal | **deliverable: unsealed map `ne-48-bal-r2` passes M1** (0 pieces, 0 necks, 48/48 districts in window, 8 split states: CA FL NC NJ NY OH PA TX). Sealed version: no map | east block `r21-al-ar-fl` (21 states), national K = 6: no plan inside its ±12.1% band (converged) [maps](maps/MAIN_ne-48-bal_summary.png), [pages](maps/MAIN_ne-48-bal_pages.pdf) |
| ne-50-bal | no sealed map | east block `r21-al-ar-fl`, WH K = 5: no plan inside its ±5.3% band (infeasible) |
| ne-50-filight | no sealed map | corridor, national K = 4: no plan inside its ±0.8% band (converged); east block `r20-al-ar-fl`, national K = 7: none inside ±3.9% (converged) |
| ne-52-bal | no sealed map | east block `r21-al-ar-fl`, WH K = 6: no plan inside its ±6.6% band (converged) |
| ne-52-filight | no sealed map | east block `r20-al-ar-fl`, national K = 7: no plan inside its ±3.9% band (converged); corridor, national K = 4: none inside ±0.8% in round 1 (converged) |
| ne-cmp-tierP | no sealed map | east block `r21-al-ar-fl`, WH K = 6: no plan inside its ±6.6% band (converged) |
| nw49-48 | no sealed map | rest region `r36-al-ar-az` (36 states), national K = 11: no plan inside its ±16.3% band (converged); also `pa-de-md-dc-va` national K = 1 infeasible; `ne-ny-nj` drawing error |
| nw49-50 | no sealed map | rest region `r36-al-ar-az`, national K = 12: no plan inside its ±8.7% band (converged); also `pa-de-md-dc-va` national K = 1 infeasible; `ne-ny-nj` drawing error |
| nw49-52 | no sealed map | rest region `r36-al-ar-az`, national K = 13: no plan inside its ±1.1% band (converged); also `pa-de-md-dc-va` national K = 1 infeasible; `ne-ny-nj` drawing error |
| nw34-48 | no sealed map | rest region `r14-az-ca-co`, WIFI K = 6: no plan inside its ±5.1% band (converged); `pa-de-md-dc-va` national K = 1 infeasible; `ne-ny-nj` and `r22-al-ar-fl` ended with no ledger written |
| nw34-50 | no sealed map | rest region `r29-al-ar-fl`, national K = 7: no plan inside its ±3.9% band (converged); `r7-az-ca-co` WIFI K = 5: none inside ±8.5% (converged); `pa-de-md-dc-va` national K = 1 infeasible |
| nw34-52 | no sealed map | rest region `r29-al-ar-fl`, national K = 7: no plan inside its ±3.9% band (converged); `r7-az-ca-co` WIFI K = 5: none inside ±8.5% (converged); the corridor plan (WIFI K = 12) was drawn but the drawing broke a band row, so no ledger |
| w1-48 | no sealed map | rest region `r36-al-ar-az` (36 states, WIFI K = 33, band ±2%): planned, no connected drawing, 14,859 ZCTAs undrawn; `ne-ny-nj`: 2,712 undrawn, retry also failed; `pa-de-md-dc-va`: no constructed drawing (PA#2 at $950.1M against window $907.4-944.4M) |
| w1-50 | no sealed map | rest region `r36-al-ar-az` (WIFI K = 35, band ±2%): planned, no connected drawing, 15,691 ZCTAs undrawn on m5 and 16,571 on m2 (drawing status unknown at the time limit); `ne-ny-nj` and `pa-de-md-dc-va`: no constructed drawing |
| w1-52 | no sealed map | rest region `r36-al-ar-az` (WIFI K = 37, band ±2%): planned on m5 only (m2's replan hit its 25-min cap), no connected drawing, 16,001 undrawn (status unknown); `ne-ny-nj` and `pa-de-md-dc-va`: no constructed drawing |

For each point the table takes the most advanced attempt across the four SEALED.json files (m5 `main/` round 1, `main2/`, `main2_m5/`, m2 `main2/`). "±X%" is the band's own tolerance from the dollar window, not an opened-up band: "no plan inside its ±X% band" means the planner found no plan at any tolerance up to the window's limit. nw34 and w1 ran on both m5 and m2; w1-52 is the only point where the two hosts differ in how far they got. Regions that were still running at the 06:55 stop never completed.

## Why the main map is mostly infeasible tonight

- **One symmetric $ band per region.** Every region is solved with a single band around its target. The northeast-plains "rest" is several separate blocks (for example a western block near $900M per district against a band of $918-1,150M), so no single band fits them all.
- **Not the cause (tested):** the split lists (allowing more splits is still infeasible), the maximum district size (6, still infeasible), the drawable-alone switch (off, still infeasible).
- **Fix tried:** partitions2 makes every region connected per channel, each with its own K ([partitions2/README.md](partitions2/README.md)). It cleared the New England and plains regions, but the east block (21 states) has no plan inside its band at every northeast point, and the nw49 and nw34 rest regions stay without a plan (national band converged at 0.01-0.16).
- **Corridor and big-WIFI draws run out of time.** The DC/DE/MD/NJ/NY/PA corridor's New York group is a coupled problem (337 s per channel in round 1); the 36-state WIFI rest region of w1 ran out its draw time with 14,859-16,571 ZCTAs undrawn.
- **The one main map that works** is `ne-48-bal` from the 2026-10-13 unsealed grid, because that plan used the corridor states as fillers, which sealing forbids.

## What we learned and what next

- **The binding limit is one symmetric band per region.** A region whose blocks differ in dollar density cannot fit one band, even when every district could sit inside the dollar window on its own.
- **Sealing removes filler states.** The unsealed `ne-48-bal` passes because corridor states absorbed the imbalance; sealed, the east block has to fit alone and has no plan inside its band.
- **The NY corridor and the big WIFI draws need far more time at tight bands.** At ±2% the exact draw of a 36-state region did not connect (about 15,000 ZCTAs undrawn) and the New York group did not finish in 337 s per channel.
- **IFA is solved; the main map is not.** IFA K = 48..54 pass (Manhattan the one allowed exception); main has one passing map and it is unsealed.
- **Next, option 1:** plan against the absolute dollar window (an asymmetric band) instead of a symmetric band around the regional target.
- **Next, option 2:** carve first, filtering columns by the window; this is the parallel track, see `notes/2026-10-14_carve-first-lite-handoff.md`.
- **Deferred items** (including the unlanded sealed driver and the PDF explainer wording) are in `notes/2026-10-14_overnight-deferred.md`.

## Links

- [STATUS.md](STATUS.md): the supervisor's running log
- [partitions/README.md](partitions/README.md): first region split
- [partitions2/README.md](partitions2/README.md): connected-region split
- [shape/FLAGS.md](shape/FLAGS.md), [shape/districts.csv](shape/districts.csv)
- [maps/INDEX.md](maps/INDEX.md): all renders
