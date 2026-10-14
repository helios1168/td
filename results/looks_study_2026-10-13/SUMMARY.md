# Looks study (2026-10-13)

Measurement only, no solver.  Maps ranked by (doughnut districts, max bite, min hull_fill): fewer doughnuts first, then the smaller worst bite, then the larger worst hull fill. The Census reference maps come first.  Columns are defined in `tools/looks/study.py`.

| # | map | districts | doughnuts (soft) | bite max | hull_fill min | hull_fill mean | axis max km | land/$ ratio (ch) | r90 max km | M1 | pieces | necks | splits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ref | census/regions | 16 | 0 (0) | 0.079 | 0.512 | 0.674 | 2928 | 51.51 (WIFI) | 1160 |  |  |  |  |
| ref | census/regions_ifa | 4 | 0 (0) | 0.124 | 0.562 | 0.711 | 2928 | 10.87 (IFA) | 1114 |  |  |  |  |
| ref | census/divisions_ifa | 9 | 1 (1) | 0.172 | 0.523 | 0.689 | 2167 | 25.67 (IFA) | 1100 |  |  |  |  |
| ref | census/divisions | 28 | 3 (4) | 0.214 | 0.523 | 0.664 | 2167 | 51.51 (WIFI) | 1085 |  |  |  |  |
| 1 | main/nw34-48-wide/r2 | 48 | 3 (19) | 0.559 | 0.376 | 0.709 | 1729 | 354.1 (WIFI) | 825 | fail | 1 | 3 | 17 |
| 2 | main/w8-52-filight-wide/r2 | 52 | 5 (15) | 0.516 | 0.399 | 0.686 | 2167 | 175.67 (FI) | 954 | fail | 2 | 3 | 16 |
| 3 | main/w1-50-wide/r2 | 50 | 6 (20) | 0.330 | 0.462 | 0.769 | 1542 | 6845.09 (WIFI) | 726 | fail | 2 | 2 | 11 |
| 4 | main/w8-50-bal-wide/r2 | 50 | 6 (17) | 0.355 | 0.420 | 0.691 | 2167 | 203.57 (national) | 954 | fail | 2 | 2 | 13 |
| 5 | main/ne-48-bal/r2 | 48 | 6 (18) | 0.406 | 0.454 | 0.682 | 2486 | 251.08 (national) | 1296 | fail | 0 | 1 | 12 |
| 6 | main/w8-cmp-seed-wide/r2 | 49 | 6 (19) | 0.408 | 0.433 | 0.688 | 2167 | 221.78 (national) | 954 | fail | 2 | 4 | 13 |
| 7 | main/w1-48-wide/r2 | 48 | 6 (18) | 0.465 | 0.333 | 0.754 | 1727 | 2304.34 (WIFI) | 491 | fail | 2 | 2 | 12 |
| 8 | regional/merged | 50 | 7 (17) | 0.399 | 0.470 | 0.765 | 1542 | 10901.44 (WIFI) | 726 | fail | 1 | 1 | 13 |
| 9 | main/nw34-52-wide/r2 | 52 | 7 (23) | 0.423 | 0.461 | 0.727 | 1727 | 640.43 (WIFI) | 792 | fail | 2 | 2 | 19 |
| 10 | main/w8-48-bal-wide/draw_retry | 48 | 7 (18) | 0.425 | 0.433 | 0.671 | 2167 | 280.51 (national) | 981 | fail | 2 | 4 | 17 |
| 11 | ifa/ifa49-arm1-seq-repair-fast | 49 | 7 (19) | 0.475 | 0.260 | 0.691 | 1720 | 647.38 (IFA) | 656 |  |  |  |  |
| 12 | main/ne-50-bal-wide/r2 | 50 | 8 (18) | 0.289 | 0.479 | 0.696 | 2486 | 203.42 (national) | 1296 | fail | 0 | 2 | 11 |
| 13 | main/w8-52-bal-wide/r2 | 52 | 8 (20) | 0.462 | 0.433 | 0.682 | 2167 | 212.13 (FI) | 954 | fail | 0 | 2 | 15 |
| 14 | main/ne-52-filight-wide/r2 | 52 | 9 (22) | 0.427 | 0.433 | 0.694 | 2486 | 266.57 (national) | 1296 | fail | 0 | 1 | 12 |
| 15 | main/nw34-50-wide/r2 | 50 | 9 (22) | 0.479 | 0.461 | 0.712 | 1727 | 421.54 (WIFI) | 825 | fail | 0 | 2 | 16 |
| 16 | ifa/ifa49-arm1-seq | 49 | 10 (21) | 0.608 | 0.241 | 0.673 | 1720 | 688.31 (IFA) | 656 |  |  |  |  |
| 17 | main/w1-52-wide/r2 | 52 | 12 (22) | 0.525 | 0.303 | 0.753 | 1727 | 6106.47 (WIFI) | 626 | fail | 2 | 4 | 13 |
| 18 | main/ne-52-bal-wide/r2 | 52 | 13 (21) | 0.395 | 0.433 | 0.679 | 2486 | 203.42 (national) | 1296 | fail | 0 | 2 | 14 |
| 19 | ifa/ifa_conus_v2 | 52 | 15 (24) | 0.400 | 0.456 | 0.799 | 1758 | 1969.56 (IFA) | 642 |  |  |  |  |
| 20 | ifa/ifa_conus_v1 | 52 | 15 (24) | 0.400 | 0.456 | 0.797 | 1758 | 1969.56 (IFA) | 642 |  |  |  |  |
| 21 | ifa/ifa_conus_nony | 47 | 15 (22) | 0.400 | 0.456 | 0.798 | 1758 | 642.43 (IFA) | 642 |  |  |  |  |

## Worst districts by bite (real maps)

| map | channel | district | states | bite | bite states | hull_fill |
|---|---|---|---|---|---|---|
| ifa/ifa49-arm1-seq | IFA | IFA_38 | NY | 0.608 | CT:0.326 MA:0.136 NY:0.128 | 0.241 |
| ifa/ifa49-arm1-seq | IFA | IFA_12 | CT;NY;RI;VT | 0.572 | NH:0.182 MA:0.169 CT:0.156 | 0.335 |
| main/nw34-48-wide/r2 | national | national_08 | DC;DE;MD;NJ;NY | 0.559 | PA:0.452 VA:0.032 NJ:0.029 | 0.376 |
| ifa/ifa49-arm1-seq | IFA | IFA_21 | IL;IN;MI;OH | 0.558 | IN:0.423 IL:0.067 OH:0.036 | 0.391 |
| main/w1-52-wide/r2 | WIFI | WIFI_14 | DE;NJ | 0.525 | NJ:0.439 PA:0.079 NY:0.007 | 0.366 |
| main/w8-52-filight-wide/r2 | WH | WH_05 | DC;DE;MD;NJ | 0.516 | PA:0.302 NJ:0.092 VA:0.071 | 0.399 |
| main/nw34-50-wide/r2 | WIFI | WIFI_22 | MD;PA | 0.479 | PA:0.322 WV:0.083 VA:0.038 | 0.527 |
| ifa/ifa49-arm1-seq | IFA | IFA_11 | CT;NJ;NY | 0.477 | NJ:0.267 NY:0.200 CT:0.010 | 0.430 |
| main/nw34-48-wide/r2 | WIFI | WIFI_22 | MD;PA | 0.477 | PA:0.197 VA:0.109 WV:0.076 | 0.460 |
| ifa/ifa49-arm1-seq-repair-fast | IFA | IFA_27 | MD | 0.475 | VA:0.246 WV:0.182 MD:0.041 | 0.533 |
| main/w1-48-wide/r2 | WIFI | WIFI_12 | DC;DE;NJ | 0.465 | MD:0.331 NJ:0.124 PA:0.011 | 0.333 |
| ifa/ifa49-arm1-seq-repair-fast | IFA | IFA_11 | NJ;NY | 0.463 | NJ:0.330 NY:0.133 | 0.503 |

## Doughnut districts (real maps, first 25)

| map | district | core without ring | ring without core |
|---|---|---|---|
| main/ne-48-bal/r2 | FI_04 |  | Los Angeles-Long Beach-Anaheim, CA Metro Area (land 55%, m 21%); San Jose-Sunnyvale-Santa Clara, CA Metro Area (land 65%, m 1%) |
| main/ne-48-bal/r2 | FI_09 |  | St. Louis, MO-IL Metro Area (land 51%, m 20%) |
| main/ne-48-bal/r2 | FI_16 | New York-Newark-Jersey City, NY-NJ Metro Area (m 61%, land 24%) |  |
| main/ne-48-bal/r2 | WH_08 |  | St. Louis, MO-IL Metro Area (land 51%, m 12%) |
| main/ne-48-bal/r2 | national_08 |  | Philadelphia-Camden-Wilmington, PA-NJ-DE-MD Metro Area (land 51%, m 27%) |
| main/ne-48-bal/r2 | national_12 | New York-Newark-Jersey City, NY-NJ Metro Area (m 59%, land 24%) |  |
| main/ne-50-bal-wide/r2 | FI_04 |  | Los Angeles-Long Beach-Anaheim, CA Metro Area (land 58%, m 21%); San Jose-Sunnyvale-Santa Clara, CA Metro Area (land 88%, m 29%) |
| main/ne-50-bal-wide/r2 | FI_05 | San Jose-Sunnyvale-Santa Clara, CA Metro Area (m 71%, land 12%) |  |
| main/ne-50-bal-wide/r2 | FI_11 |  | St. Louis, MO-IL Metro Area (land 51%, m 20%) |
| main/ne-50-bal-wide/r2 | FI_16 | New York-Newark-Jersey City, NY-NJ Metro Area (m 57%, land 23%) |  |
| main/ne-50-bal-wide/r2 | WH_08 |  | St. Louis, MO-IL Metro Area (land 51%, m 12%) |
| main/ne-50-bal-wide/r2 | national_04 | San Francisco-Oakland-Fremont, CA Metro Area (m 56%, land 26%) |  |
| main/ne-50-bal-wide/r2 | national_11 |  | St. Louis, MO-IL Metro Area (land 51%, m 2%) |
| main/ne-50-bal-wide/r2 | national_14 | New York-Newark-Jersey City, NY-NJ Metro Area (m 51%, land 23%) |  |
| main/ne-52-bal-wide/r2 | FI_05 |  | Los Angeles-Long Beach-Anaheim, CA Metro Area (land 65%, m 27%) |
| main/ne-52-bal-wide/r2 | FI_07 |  | Lancaster, PA Metro Area (land 57%, m 26%) |
| main/ne-52-bal-wide/r2 | FI_12 |  | St. Louis, MO-IL Metro Area (land 51%, m 20%) |
| main/ne-52-bal-wide/r2 | FI_18 | New York-Newark-Jersey City, NY-NJ Metro Area (m 55%, land 23%) |  |
| main/ne-52-bal-wide/r2 | FI_21 |  | Cleveland, OH Metro Area (land 51%, m 12%) |
| main/ne-52-bal-wide/r2 | FI_22 |  | Knoxville, TN Metro Area (land 67%, m 18%) |
| main/ne-52-bal-wide/r2 | WH_02 |  | Memphis, TN-MS-AR Metro Area (land 63%, m 0%) |
| main/ne-52-bal-wide/r2 | WH_04 |  | Los Angeles-Long Beach-Anaheim, CA Metro Area (land 59%, m 28%) |
| main/ne-52-bal-wide/r2 | WH_09 |  | Cincinnati, OH-KY-IN Metro Area (land 50%, m 4%) |
| main/ne-52-bal-wide/r2 | WH_11 |  | Washington-Arlington-Alexandria, DC-VA-MD-WV Metro Area (land 64%, m 24%) |
| main/ne-52-bal-wide/r2 | national_04 | San Francisco-Oakland-Fremont, CA Metro Area (m 56%, land 26%) |  |

## Soft doughnut districts missing the hard test (real maps, first 25)

| map | district | core dense | ring sparse |
|---|---|---|---|
| main/ne-48-bal/r2 | FI_01 |  | Memphis, TN-MS-AR Metro Area (land 49%, m 11%) |
| main/ne-48-bal/r2 | FI_08 |  | Chattanooga, TN-GA Metro Area (land 35%, m 0%) |
| main/ne-48-bal/r2 | FI_10 |  | Toledo, OH Metro Area (land 31%, m 0%) |
| main/ne-48-bal/r2 | FI_14 |  | Wilmington, NC Metro Area (land 41%, m 0%) |
| main/ne-48-bal/r2 | FI_15 |  | Allentown-Bethlehem-Easton, PA-NJ Metro Area (land 32%, m 4%) |
| main/ne-48-bal/r2 | WH_01 |  | Memphis, TN-MS-AR Metro Area (land 49%, m 0%) |
| main/ne-48-bal/r2 | WH_06 |  | New York-Newark-Jersey City, NY-NJ Metro Area (land 36%, m 4%) |
| main/ne-48-bal/r2 | WH_09 |  | Chicago-Naperville-Elgin, IL-IN Metro Area (land 27%, m 3%) |
| main/ne-48-bal/r2 | national_01 |  | Virginia Beach-Chesapeake-Norfolk, VA-NC Metro Area (land 27%, m 0%) |
| main/ne-48-bal/r2 | national_04 |  | Los Angeles-Long Beach-Anaheim, CA Metro Area (land 46%, m 4%) |
| main/ne-48-bal/r2 | national_11 |  | Chicago-Naperville-Elgin, IL-IN Metro Area (land 27%, m 6%) |
| main/ne-48-bal/r2 | national_14 |  | Houston-Pasadena-The Woodlands, TX Metro Area (land 21%, m 1%) |
| main/ne-50-bal-wide/r2 | FI_01 |  | Memphis, TN-MS-AR Metro Area (land 49%, m 11%) |
| main/ne-50-bal-wide/r2 | FI_07 |  | Allentown-Bethlehem-Easton, PA-NJ Metro Area (land 25%, m 1%) |
| main/ne-50-bal-wide/r2 | FI_10 |  | Chattanooga, TN-GA Metro Area (land 35%, m 0%) |
| main/ne-50-bal-wide/r2 | FI_15 |  | Virginia Beach-Chesapeake-Norfolk, VA-NC Metro Area (land 27%, m 0%) |
| main/ne-50-bal-wide/r2 | FI_18 |  | Cincinnati, OH-KY-IN Metro Area (land 20%, m 1%) |
| main/ne-50-bal-wide/r2 | WH_01 |  | Memphis, TN-MS-AR Metro Area (land 49%, m 0%) |
| main/ne-50-bal-wide/r2 | WH_06 |  | New York-Newark-Jersey City, NY-NJ Metro Area (land 36%, m 4%) |
| main/ne-50-bal-wide/r2 | WH_09 |  | Chicago-Naperville-Elgin, IL-IN Metro Area (land 27%, m 3%) |
| main/ne-50-bal-wide/r2 | national_09 |  | Allentown-Bethlehem-Easton, PA-NJ Metro Area (land 25%, m 2%) |
| main/ne-50-bal-wide/r2 | national_12 |  | Chicago-Naperville-Elgin, IL-IN Metro Area (land 27%, m 6%) |
| main/ne-52-bal-wide/r2 | FI_01 |  | Columbus, GA-AL Metro Area (land 23%, m 3%); Memphis, TN-MS-AR Metro Area (land 49%, m 11%) |
| main/ne-52-bal-wide/r2 | FI_08 |  | Allentown-Bethlehem-Easton, PA-NJ Metro Area (land 25%, m 1%) |
| main/ne-52-bal-wide/r2 | FI_11 |  | Chattanooga, TN-GA Metro Area (land 36%, m 0%) |

## Sanity checks and notes

- Census divisions: hull_fill East North Central 0.75/bite 0.085, East South Central 0.80/bite 0.172, Middle Atlantic 0.76/bite 0.041, Mountain 0.56/bite 0.021, Pacific 0.52/bite 0.088, South Atlantic 0.55/bite 0.102, West North Central 0.70/bite 0.214, West South Central 0.57/bite 0.046
- main/ne-52-filight-wide/r2 national_11 (IA;MI;MN;MO;WI): bite 0.184 (IL:0.120 IN:0.050 AR:0.008), hull_fill 0.681
- w1-50-wide/r2 WIFI_29 (ME;NH;NY;VT): doughnut 0, soft 0: dense [] sparse []
- w1-50-wide/r2 WIFI_36 (NY): doughnut 0, soft 0: dense [] sparse []
- w1-50-wide/r2 WIFI_37 (NY): doughnut 0, soft 1: dense [] sparse [Kiryas Joel-Poughkeepsie-Newburgh, NY Metro Area (land 15%, m 3%)]
- w1-50-wide/r2 WIFI_38 (NY): doughnut 0, soft 1: dense [New York-Newark-Jersey City, NY-NJ Metro Area (m 20%, land 1%)] sparse []
- w1-50-wide/r2 WIFI_39 (NY): doughnut 0, soft 1: dense [] sparse [Syracuse, NY Metro Area (land 20%, m 1%)]
- no folder under runs/exp/contig carries `ifa_kgrid`; the IFA set is the three `ifa_conus_*` folders and two full 49-district `ifa49-arm1-seq*` maps.
- hull_fill is capped at 1; `hull_fill_raw` in districts.csv is not.
- doughnut tests use CBSAs of at least 5% of the channel's mean district m_rel.
