# The headline map, district by district

The shipped map: Track 2, anchored, δ = 5%. Eight state splits, certified minimal under the
anchors. California is cut into five districts, New York three, Texas two, Florida two, and
every other state sits whole inside one district.

One close-up per district, zoomed to its own territory. The subject district carries its colour
from the overview maps, every other district is muted grey, and the dots are ZIP codes sized by
opportunity. Full write-up in [`docs/HEADLINE.md`](../../docs/HEADLINE.md); the two overview
renderings are [`borders_track2_anchored_d05_voronoi.png`](../borders_track2_anchored_d05_voronoi.png)
and [`borders_track2_anchored_d05_districts.png`](../borders_track2_anchored_d05_districts.png).

## How to read the numbers

An equal share is 5.56% of national opportunity, since there are 18 districts. The **deviation**
column is the gap from that equal share in percentage points. The whole map spans 8.98% from
the largest district to the smallest, and D17 at +0.29 points is the only district outside the
nominal 5% band once the map is realised into whole ZIP codes.

A state is listed under a district when that district holds at least 1% of the district's own
opportunity, so incidental slivers are left out.

| district | share | deviation | ZIPs | states |
|---|---|---|---|---|
| D01 | 5.38% | −0.17 | 123 | NY |
| D02 | 5.54% | −0.01 | 198 | CA, NV |
| D03 | 5.77% | +0.22 | 132 | TX |
| D04 | 5.77% | +0.21 | 271 | NY, CT, MA, NH, RI |
| D05 | 5.71% | +0.15 | 238 | PA, MD, NY, DC, DE |
| D06 | 5.36% | −0.19 | 216 | AZ, CO, NM, SD |
| D07 | 5.56% | +0.00 | 239 | FL |
| D08 | 5.54% | −0.01 | 226 | NC, VA, WV |
| D09 | 5.53% | −0.03 | 305 | MI, OH, WI |
| D10 | 5.35% | −0.21 | 174 | CA |
| D11 | 5.65% | +0.09 | 261 | IL, MN, IA, NE, ND |
| D12 | 5.76% | +0.20 | 182 | NJ |
| D13 | 5.35% | −0.21 | 249 | IN, LA, MO, KY, AL, TN, AR, MS |
| D14 | 5.35% | −0.20 | 84 | CA |
| D15 | 5.36% | −0.20 | 246 | FL, GA, SC |
| D16 | 5.81% | +0.26 | 204 | TX, OK, KS |
| D17 | 5.85% | +0.29 | 283 | CA, WA, UT, ID, OR |
| D18 | 5.36% | −0.20 | 117 | CA, HI |

D07 lands within 0.005 points of an equal share. D14 is the smallest by ZIP count at 84, and
D09 the largest at 305, which shows how far ZIP count and opportunity come apart.

Hawaii appears under D18 because it has no place in the state adjacency graph and is assigned
after the fact, alongside Alaska and the ZIP codes with no gazetteer coordinate.

## The districts

### D01 — 5.38%, New York
![D01](district_D01.png)

### D02 — 5.54%, California and Nevada
![D02](district_D02.png)

### D03 — 5.77%, Texas
![D03](district_D03.png)

### D04 — 5.77%, New York and New England
![D04](district_D04.png)

### D05 — 5.71%, Pennsylvania, Maryland, New York, DC, Delaware
![D05](district_D05.png)

### D06 — 5.36%, Arizona, Colorado, New Mexico, South Dakota
![D06](district_D06.png)

### D07 — 5.56%, Florida
![D07](district_D07.png)

### D08 — 5.54%, North Carolina, Virginia, West Virginia
![D08](district_D08.png)

### D09 — 5.53%, Michigan, Ohio, Wisconsin
![D09](district_D09.png)

### D10 — 5.35%, California
![D10](district_D10.png)

### D11 — 5.65%, Illinois, Minnesota, Iowa, Nebraska, North Dakota
![D11](district_D11.png)

### D12 — 5.76%, New Jersey
![D12](district_D12.png)

### D13 — 5.35%, the mid-South
![D13](district_D13.png)

### D14 — 5.35%, California
![D14](district_D14.png)

### D15 — 5.36%, Florida, Georgia, South Carolina
![D15](district_D15.png)

### D16 — 5.81%, Texas, Oklahoma, Kansas
![D16](district_D16.png)

### D17 — 5.85%, California and the Northwest
![D17](district_D17.png)

### D18 — 5.36%, California and Hawaii
![D18](district_D18.png)
