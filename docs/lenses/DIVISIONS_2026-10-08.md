# Census divisions as sealed planning regions: mapping and arithmetic

Research tab, 2026-10-08, for owner review. Draft; nothing here is a decision.

The owner's idea: split the country into Census divisions, solve each in parallel, and run the
arithmetic screen within each. This document gives the state-to-division mapping first, then the
per-division arithmetic at the D3/E2 bands, then what the arithmetic says about the idea.

## 1. The mapping (2025 TIGER)

Source: `data/public/tl_2025_us_state.zip`, fields `REGION` and `DIVISION` (read 2026-10-08).
The Census Bureau has four regions and nine divisions. "Midwest" in the owner's list is a region
(East North Central plus West North Central), not a division, so there are nine, not ten.

| Div | Name | Region | States | Members |
|---|---|---|---|---|
| 1 | New England | Northeast | 6 | CT MA ME NH RI VT |
| 2 | Middle Atlantic | Northeast | 3 | NJ NY PA |
| 3 | East North Central | Midwest | 5 | IL IN MI OH WI |
| 4 | West North Central | Midwest | 7 | IA KS MN MO ND NE SD |
| 5 | South Atlantic | South | 9 | DC DE FL GA MD NC SC VA WV |
| 6 | East South Central | South | 4 | AL KY MS TN |
| 7 | West South Central | South | 4 | AR LA OK TX |
| 8 | Mountain | West | 8 | AZ CO ID MT NM NV UT WY |
| 9 | Pacific | West | 3 | CA OR WA |

DC is in South Atlantic (division 5) as its own unit, as td already treats it. Excluded, as
everywhere in td: AK, HI, PR, AS, GU, MP, VI (AK and HI are Pacific in the Census scheme but are
outside the CONUS map).

Note: `reference/2025/zcta_reference.csv.gz` has a `metdiv` column. That is the OMB metropolitan
division, a subdivision of large metro areas, and has nothing to do with Census divisions.

## 2. What a sealed division means

Solving each division separately makes every division boundary a hard wall: no district may hold
ZCTAs in two divisions. That is a new constraint, stronger than anything in `MANDATES.md`, and it
needs the owner's sign-off before any run. Its effects:

- It bans, for free, most of the support patterns behind the M1 failures: NJ or PA with New
  England (divisions 2 and 1), DE with NJ (5 and 2), MD with PA (5 and 2).
- It also bans attachments td has relied on: WV with OH or PA, KY with OH, OK with KS, and in the
  lead map's layout the whole "NE + plains" WIFI channel, which spans divisions 1, 4, 7 and 8.
- Under D3 the per-district band is fixed in dollars and K-independent, so a division's K is not
  apportioned; it is a range forced by the division's dollars: K_min = ceil(M_div / U),
  K_max = floor(M_div / L). The channel's K is the sum over divisions and must land in the
  channel's allowed total. A division with K_min > K_max cannot be planned alone at that band and
  must be merged with a neighbour.

## 3. Arithmetic per division and channel

Dollars from the scorer's rates (`tools/looks/score.py dollar_rates`) applied to the lead map's
ledger (`ne_plains_wh11-r2-all`) for national, WH, FI and WIFI and to `ifa46-whole` for IFA.
Bands: D3 ±15% of target, IFA −20%/+15% (E2). "Over U" states must split inside the division;
"under L" states must attach inside the division. "NO K" means no district count fits.

Main-channel caveat: in the lead map's layout New England, KS, NE, ND, SD, OK, ID, MT, NM and WY
are planned in the combined WIFI channel ($3,370M: $2,303M in New England, $590M in West North
Central, $291M Mountain, $186M West South Central), so they are absent from the national, WH and
FI rows below. WIFI itself spans four divisions and cannot exist under sealed divisions.

### national, target $1,250M, band [$1,062M, $1,438M]

| Division | States | $M | Units | K | Over U | Under L |
|---|---|---|---|---|---|---|
| Middle Atlantic | 3 | 3,307 | 2.65 | 3 | NY 1,756 | NJ PA |
| East North Central | 5 | 1,848 | 1.48 | NO K | | IL MI OH IN WI |
| West North Central | 3 | 412 | 0.33 | NO K | | MN MO IA |
| South Atlantic | 9 | 3,208 | 2.57 | 3 | | all nine |
| East South Central | 4 | 337 | 0.27 | NO K | | KY AL TN MS |
| West South Central | 3 | 2,204 | 1.76 | 2 | TX 1,971 | LA AR |
| Mountain | 4 | 1,249 | 1.00 | 1 | | AZ CO UT NV |
| Pacific | 3 | 4,329 | 3.46 | 4 | CA 4,026 | WA OR |
| CONUS (this layout) | | 16,896 | 13.52 | 12–15 | | |

### WH, target $1,000M, band [$850M, $1,150M]

| Division | States | $M | Units | K | Over U | Under L |
|---|---|---|---|---|---|---|
| Middle Atlantic | 3 | 2,174 | 2.17 | 2 | | PA NJ NY |
| East North Central | 5 | 1,536 | 1.54 | NO K | | all five |
| West North Central | 3 | 458 | 0.46 | NO K | | MN MO IA |
| South Atlantic | 9 | 2,764 | 2.76 | 3 | | all nine |
| East South Central | 4 | 477 | 0.48 | NO K | | all four |
| West South Central | 3 | 948 | 0.95 | 1 | | TX LA AR |
| Mountain | 4 | 470 | 0.47 | NO K | | all four |
| Pacific | 3 | 1,311 | 1.31 | NO K | CA 1,177 | WA OR |
| CONUS (this layout) | | 10,139 | 10.14 | 9–11 | | |

### FI, target $900M, band [$765M, $1,035M]

| Division | States | $M | Units | K | Over U | Under L |
|---|---|---|---|---|---|---|
| Middle Atlantic | 3 | 4,060 | 4.51 | 4–5 | NY 1,874, PA 1,528 | NJ |
| East North Central | 5 | 3,106 | 3.45 | 4 | OH 1,076 | IL MI IN WI |
| West North Central | 3 | 981 | 1.09 | 1 | | MN MO IA |
| South Atlantic | 9 | 4,341 | 4.82 | 5 | FL 1,489 | GA VA MD SC WV DE DC |
| East South Central | 4 | 1,733 | 1.93 | 2 | | AL KY MS |
| West South Central | 3 | 1,419 | 1.58 | NO K | | LA AR |
| Mountain | 4 | 799 | 0.89 | 1 | | CO UT AZ NV |
| Pacific | 3 | 2,065 | 2.29 | 2 | CA 1,624 | WA OR |
| CONUS (this layout) | | 18,504 | 20.56 | 18–24 | | |

### IFA, target $1,250M, band [$1,000M, $1,438M], MD whole by F1

| Division | States | $M | Units | K | Over U | Under L |
|---|---|---|---|---|---|---|
| New England | 6 | 4,835 | 3.87 | 4 | MA 1,922, CT 1,670 | NH RI VT ME |
| Middle Atlantic | 3 | 13,142 | 10.51 | 10–13 | NY 5,470, PA 4,120, NJ 3,552 | |
| East North Central | 5 | 10,932 | 8.75 | 8–10 | MI 3,292, OH 2,734, IL 2,133, WI 1,474 | |
| West North Central | 7 | 4,823 | 3.86 | 4 | MN 1,490 | MO IA KS NE ND SD |
| South Atlantic | 9 | 11,027 | 8.82 | 8–11 | FL 4,366, MD 1,507 (F1 waiver) | SC DE WV DC |
| East South Central | 4 | 2,347 | 1.88 | 2 | | TN KY AL MS |
| West South Central | 4 | 4,795 | 3.84 | 4 | TX 3,515 | LA OK AR |
| Mountain | 8 | 3,382 | 2.71 | 3 | | UT NV ID NM MT WY |
| Pacific | 3 | 6,049 | 4.84 | 5–6 | CA 5,078 | WA OR |
| CONUS | | 61,333 | 49.07 | 43–61 | | |

Sum of division K ranges for IFA: 48 to 57. With sealed divisions IFA has no plan at K 46 or 47.

## 4. What the arithmetic says

1. **For IFA, sealed divisions work arithmetically.** Every division has a feasible K range on its
   own, the ranges sum to 48–57, which overlaps the owner's 46–55, and the walls remove the NJ,
   DE and MD cross-division patterns that caused the M1 failures. The remaining questions are
   inside divisions: CT must split with RI as its only attach (CT+RI = $2,099M against two
   floors of $2,000M, so a $99M window, as found before), MA must split with NH, VT and ME as
   attach states, and MN must split inside West North Central.
2. **For the main map, sealed divisions do not work.** At national and WH, four and five of the
   eight divisions have no feasible K at all, because their dollars are a fraction of one
   district (East South Central is 0.27 of a national district; West North Central 0.33). They
   must merge with neighbours, which is what the "NE + plains" layout does by hand. Division
   groups (for example Midwest = 3+4, or South = 5+6+7) would be the unit instead, and that is a
   layout choice, not a Census geography.
3. **The WIFI channel cannot exist under sealed divisions** in its current form; it spans four.
4. **Parallelism gain.** IFA's nine divisions solve independently, the largest (Middle Atlantic,
   13 units, 3 states) being far smaller than the CONUS IFA problem; the state-level master is
   already fast, so the gain is in drawing and gating, which run per division on a tenth of the
   ZCTAs. The plan-time check-and-ban loop then runs on the Middle Atlantic alone, where every
   past failure was.

## 5. Questions for the owner

- Accept sealed division boundaries as a hard constraint for IFA? (Changes the eligible set;
  excludes K 46–47.)
- For the main map, choose division groups by hand (the current layout is one), or drop the idea
  for the main map and use divisions for IFA only?
- Does WIFI stay as the four-division combined channel it is, which rules out sealing for the
  main map, or is it redefined?

LEARNED: Census divisions are nine (the owner's "Midwest" is a region = divisions 3+4); the 2025
TIGER state file carries REGION and DIVISION, and `zcta_reference.csv.gz`'s `metdiv` is the OMB
metropolitan division, unrelated.
LEARNED: Sealed Census divisions are arithmetically feasible for IFA at E2 (every division has a
K range; they sum to 48–57) and infeasible for national and WH (four to five divisions hold a
fraction of one district), while WIFI spans four divisions.
