# Connected-region partitions (partitions2, 2026-10-14)

Replaces `../partitions/<point>.json`: sealed corridor regions (checked connected on every channel's footprint) kept with their K/k_alt; each rest region replaced by the connected components of the channels' footprints (state graph = `geo.polygon_graph` cross-state edges incl. connectors, as `region_arith.state_graph`), each its own explicit region with its own K. K per channel sums to the point's channel K (`rest:false`, every footprint state covered). K chosen per channel to maximise the minimum `overnight.fit_delta` over the components (window `score.WINDOWS`, WIFI whole-state cap as `plan_point`); ties fewer regions. Where channels' footprints differ (nw34: national 34 inside WIFI 49) the shared blocks are refined so every channel's footprint inside a block is connected and the state sets are equal-or-disjoint; non-footprint states ride along in a block (WIFI-only plains states go with the west block). Band never widened. No point lacked an allocation; no old partition kept. A fallbacks (`.A.json`) are not regenerated.

Validated: `sealed.py run --partition F --root /tmp/td-part2/dry-<point> --host m5 --dry-run`, rc 0 for all 15, every run's final δ a number. Logs `dryrun/`. `A` = k_alt. Names `rN-xx-yy-zz` = N states, first three.

| point | channel | region (states) K → τ $M, final δ |
|---|---|---|
| ne-48-bal | national | corridor(6) 3 → 1,207.8, 0.172; r21-al-ar-fl(21) 6 → 1,282.4, 0.1209; r7-az-ca-co(7) 5 → 1,115.6, 0.1036 |
| ne-48-bal | WH | corridor(6) 3 → 966.1, 0.1201; r21-al-ar-fl(21) 5 → 1,091.7, 0.0533; r7-az-ca-co(7) 2 → 890.9, 0.0459 |
| ne-48-bal | FI | corridor(6) 5/6 → 921.6, 0.123; r21-al-ar-fl(21) 13 → 848.6, 0.0985; r7-az-ca-co(7) 3 → 954.7, 0.084 |
| ne-48-bal | WIFI | r6-ct-ma-me(6) 2 → 1,151.7, 0.2619; r9-id-ks-mt(9) 1 → 1,066.5, 0.1 |
| ne-50-bal | national | corridor(6) 3 → 1,207.8, 0.172; r21-al-ar-fl(21) 7 → 1,099.2, 0.0902; r7-az-ca-co(7) 5 → 1,115.6, 0.1036 |
| ne-50-bal | WH | corridor(6) 3 → 966.1, 0.1201; r21-al-ar-fl(21) 5 → 1,091.7, 0.0533; r7-az-ca-co(7) 2 → 890.9, 0.0459 |
| ne-50-bal | FI | corridor(6) 5/6 → 921.6, 0.123; r21-al-ar-fl(21) 14 → 788.0, 0.0291; r7-az-ca-co(7) 3 → 954.7, 0.084 |
| ne-50-bal | WIFI | r6-ct-ma-me(6) 2 → 1,151.7, 0.2619; r9-id-ks-mt(9) 1 → 1,066.5, 0.1 |
| ne-50-filight | national | corridor(7) 4 → 1,008.3, 0.0082; r20-al-ar-fl(20) 7 → 1,040.7, 0.039; r7-az-ca-co(7) 5 → 1,115.6, 0.1036 |
| ne-50-filight | WH | corridor(7) 3 → 1,048.6, 0.0967; r20-al-ar-fl(20) 6 → 868.5, 0.0213; r7-az-ca-co(7) 2 → 890.9, 0.0459 |
| ne-50-filight | FI | corridor(7) 6/5 → 849.1, 0.099; r20-al-ar-fl(20) 11 → 958.7, 0.0796; r7-az-ca-co(7) 3 → 954.7, 0.084 |
| ne-50-filight | WIFI | r6-ct-ma-me(6) 2 → 1,151.7, 0.2619; r9-id-ks-mt(9) 1 → 1,066.5, 0.1 |
| ne-52-bal | national | corridor(6) 3 → 1,207.8, 0.172; r21-al-ar-fl(21) 7 → 1,099.2, 0.0902; r7-az-ca-co(7) 5 → 1,115.6, 0.1036 |
| ne-52-bal | WH | corridor(6) 3 → 966.1, 0.1201; r21-al-ar-fl(21) 6 → 909.8, 0.0656; r7-az-ca-co(7) 2 → 890.9, 0.0459 |
| ne-52-bal | FI | corridor(6) 6 → 768.0, 0.0039; r21-al-ar-fl(21) 14 → 788.0, 0.0291; r7-az-ca-co(7) 3 → 954.7, 0.084 |
| ne-52-bal | WIFI | r6-ct-ma-me(6) 2 → 1,151.7, 0.2619; r9-id-ks-mt(9) 1 → 1,066.5, 0.1 |
| ne-52-filight | national | corridor(7) 4 → 1,008.3, 0.0082; r20-al-ar-fl(20) 7 → 1,040.7, 0.039; r7-az-ca-co(7) 5 → 1,115.6, 0.1036 |
| ne-52-filight | WH | corridor(7) 3 → 1,048.6, 0.0967; r20-al-ar-fl(20) 6 → 868.5, 0.0213; r7-az-ca-co(7) 2 → 890.9, 0.0459 |
| ne-52-filight | FI | corridor(7) 6 → 849.1, 0.099; r20-al-ar-fl(20) 13 → 811.2, 0.0569; r7-az-ca-co(7) 3 → 954.7, 0.084 |
| ne-52-filight | WIFI | r6-ct-ma-me(6) 2 → 1,151.7, 0.2619; r9-id-ks-mt(9) 1 → 1,066.5, 0.1 |
| ne-cmp-tierP | national | corridor(6) 3 → 1,207.8, 0.172; r21-al-ar-fl(21) 7 → 1,099.2, 0.0902; r7-az-ca-co(7) 5 → 1,115.6, 0.1036 |
| ne-cmp-tierP | WH | corridor(6) 3 → 966.1, 0.1201; r21-al-ar-fl(21) 6 → 909.8, 0.0656; r7-az-ca-co(7) 2 → 890.9, 0.0459 |
| ne-cmp-tierP | FI | corridor(6) 5/6 → 921.6, 0.123; r21-al-ar-fl(21) 12 → 919.3, 0.1258; r7-az-ca-co(7) 3 → 954.7, 0.084 |
| ne-cmp-tierP | WIFI | r6-ct-ma-me(6) 2 → 1,151.7, 0.2619; r9-id-ks-mt(9) 1 → 1,066.5, 0.1 |
| nw49-48 | national | ne-ny-nj(8) 3 → 1,042.4, 0.0406; pa-de-md-dc-va(5) 1 → 1,260.6, 0.1; r36-al-ar-az(36) 11 → 1,195.2, 0.1633 |
| nw49-48 | WIFI | ne-ny-nj(8) 6 → 982.4, 0.1347; pa-de-md-dc-va(5) 4/5 → 1,073.7, 0.071; r36-al-ar-az(36) 23 → 921.1, 0.0771 |
| nw49-50 | national | ne-ny-nj(8) 3 → 1,042.4, 0.0406; pa-de-md-dc-va(5) 1 → 1,260.6, 0.1; r36-al-ar-az(36) 12 → 1,095.6, 0.0872 |
| nw49-50 | WIFI | ne-ny-nj(8) 6 → 982.4, 0.1347; pa-de-md-dc-va(5) 4/5 → 1,073.7, 0.071; r36-al-ar-az(36) 24 → 882.7, 0.037 |
| nw49-52 | national | ne-ny-nj(8) 3 → 1,042.4, 0.0406; pa-de-md-dc-va(5) 1 → 1,260.6, 0.1; r36-al-ar-az(36) 13 → 1,011.3, 0.0112 |
| nw49-52 | WIFI | ne-ny-nj(8) 6 → 982.4, 0.1347; pa-de-md-dc-va(5) 5 → 859.0, 0.0104; r36-al-ar-az(36) 24 → 882.7, 0.037 |
| nw34-48 | national | ne-ny-nj(8) 2 → 1,386.3, 0.0369; pa-de-md-dc-va(5) 1 → 1,260.6, 0.1; r22-al-ar-fl(22) 6 → 1,214.1, 0.1763; r14-az-ca-co(14) 5 → 1,115.6, 0.1036 |
| nw34-48 | WIFI | ne-ny-nj(8) 6/7 → 1,041.5, 0.1042; pa-de-md-dc-va(5) 4 → 1,073.7, 0.071; r22-al-ar-fl(22) 18 → 894.3, 0.0495; r14-az-ca-co(14) 6 → 895.4, 0.0506 |
| nw34-50 | national | ne-ny-nj(8) 2 → 1,386.3, 0.0369; pa-de-md-dc-va(5) 1 → 1,260.6, 0.1; r29-al-ar-fl(29) 7 → 1,040.7, 0.039; r7-az-ca-co(7) 5 → 1,115.6, 0.1036 |
| nw34-50 | WIFI | ne-ny-nj(8) 7 → 892.7, 0.0478; pa-de-md-dc-va(5) 4/5 → 1,073.7, 0.071; r29-al-ar-fl(29) 19 → 885.4, 0.04; r7-az-ca-co(7) 5 → 929.2, 0.0852 |
| nw34-52 | national | corridor(13) 4 → 1,008.3, 0.0082; r29-al-ar-fl(29) 7 → 1,040.7, 0.039; r7-az-ca-co(7) 5 → 1,115.6, 0.1036 |
| nw34-52 | WIFI | corridor(13) 12/11 → 878.6, 0.0326; r29-al-ar-fl(29) 19 → 885.4, 0.04; r7-az-ca-co(7) 5 → 929.2, 0.0852 |
| w1-48 | WIFI | ne-ny-nj(8) 9/10 → 1,002.4, 0.1472; pa-de-md-dc-va(5) 6 → 925.9, 0.0819; r36-al-ar-az(36) 33 → 1,040.4, 0.1053 |
| w1-50 | WIFI | ne-ny-nj(8) 9/10 → 1,002.4, 0.1472; pa-de-md-dc-va(5) 6 → 925.9, 0.0819; r36-al-ar-az(36) 35 → 980.9, 0.1334 |
| w1-52 | WIFI | ne-ny-nj(8) 9/10 → 1,002.4, 0.1472; pa-de-md-dc-va(5) 6 → 925.9, 0.0819; r36-al-ar-az(36) 37 → 927.9, 0.0839 |

Region state lists are in the JSONs. Risks: all K are dollar arithmetic, no feasibility certificate; sealed.py does not move a rest-type region's K when a corridor k_alt draw is kept, so the total is off by one in that case (as in `../partitions/README.md`); the smallest final δ values are inherited corridor regions, not new components: ne-52-bal FI corridor 0.0039 (K 6), ne-50/52-filight national corridor 0.0082, nw34-52 national corridor 0.0082, nw49-52 pa-de-md-dc-va WIFI 0.0104; smallest new component: nw49-52 national r36 0.0112.
