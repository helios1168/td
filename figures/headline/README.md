# The headline map, up close

The shipped map: Track 2, anchored, δ = 5%. Eight state splits, certified minimal under the
anchors. California is cut into five districts, New York three, Texas two, Florida two, and
every other state sits whole inside one district.

One close-up per split state, plus the share and coverage table for all 18 districts. Full
write-up in [`docs/HEADLINE.md`](../../docs/HEADLINE.md); the two overview renderings are
[`borders_track2_anchored_d05_voronoi.png`](../borders_track2_anchored_d05_voronoi.png)
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

## The four split states

One figure per state that more than one district holds. Each shows the state carved by district
colour, together with every state those districts also reach into, since that is the other half
of the story: a district that takes a slice of California has to get the rest of its opportunity
somewhere. States outside that set are drawn in the muted context grey.

A district is named in a subtitle when it holds at least 1% of that state's opportunity, the same
1% threshold the model itself uses to decide that a state is present in a district. A district
can therefore show as a thin colour on the map without being named, though that does not happen
for these four.

Where a district's territory inside the frame is too small to sit under its own label, the label
moves to open ground and keeps a thin line back to the district. On these close-ups a label has
to leave room around the district: a district keeps its label on top only if its territory in
frame is at least four times the label box, so the label hides at most a quarter of it. D14 and
D18 in California and D01 in New York are the three that need the leader line. The overview maps
use the looser test, since there the alternative to a covered district is a label with nowhere
to go.

| state | share of national opportunity | districts | reaches into |
|---|---|---|---|
| California | 22.92% | D02 20.1%, D10 23.1%, D14 23.4%, D17 10.8%, D18 22.6% | AK, HI, ID, MT, NV, OR, UT, WA |
| Texas | 11.22% | D03 51.4%, D16 48.6% | KS, OK |
| New York | 9.97% | D01 52.8%, D04 37.6%, D05 9.5% | CT, DC, DE, MA, MD, ME, NH, PA, RI, VT |
| Florida | 7.77% | D07 71.6%, D15 28.4% | GA, SC |

The percentages after each district are shares of that state's own opportunity, not of the
nation. They sum to 100% per state.

California and New York are the two states whose districts spill furthest. California's five
districts collectively cover eight other states, which is why holding it to fewer districts
reorganises the whole west. Texas and Florida are nearly self-contained, reaching only into two
neighbours each, which is why capping them changes little.

### California, in five districts
![California](state_CA.png)

### Texas, in two districts
![Texas](state_TX.png)

### New York, in three districts
![New York](state_NY.png)

### Florida, in two districts
![Florida](state_FL.png)

## Regenerating these

```
tools/us_maps.py <instance> --state-figures <draw.csv> --out <dir>
```

`--state-figures` defaults to whichever states the draw splits. The companion flag
`--district-figures` renders one close-up per district in the same style; those were reviewed
and are not kept here, since the state figures and the table above carry the same information
in four pages instead of eighteen.
