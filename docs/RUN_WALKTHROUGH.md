# How a run works, and why the 51 stopped at ±10%

A plain-English walkthrough of `python -m td run`, using the first real run of
`scenarios/51_total_13n_11wh_24fi_3wifi.toml` on the fresh extract (2026-09-30, `main` at 25b6256).
It is a mental model and simplifies in places; `docs/MODEL.md` is the specification. τ is a
channel's average district size: its total opportunity divided by K.

## The steps

**Preparing the data**

1. **Load the extract**: 10 fine channels, about 29,000 (ZIP, fine channel) cells.
2. **Clean the ground set**: drop every ZIP that is not a 2025 ZCTA in the 48 contiguous states
   or DC (`data.conus`). PO box, unique and military ZIPs have no ZCTA and are excluded, never
   placed (owner decision on #63). 486 ZIPs were dropped.
3. **Keep the scenario's own channels** (`spec.scope`, #79): national chase, wells WH, wells FI,
   WH and FI. The new fine channels are planned in their own scenarios (#76). That leaves 11,721
   cells on 6,623 ZIPs.
4. **Build the ZIP map**: which ZIPs touch, over the ZIPs with opportunity in this scenario.
5. **Group ZIPs into states**: 49 units. Two states are neighbours if any of their ZIPs touch.

**Setting up each planning channel.** From here on, each channel is solved on its own.

6. **Assign cells to planning channels**:
   - national: the 41 non-western states × {national chase, wells WH, wells FI};
   - WH: the 41 states × WH;
   - FI: the 41 states × FI;
   - WIFI: the 8 western states × all five fine channels.
7. **Set the targets**: K districts, a target size τ, and an allowed band of τ ± δ. δ is 10%,
   and 100% for WIFI's three fixed blocks.
8. **Decide which states may be divided.** A *whole* state goes entirely into one district; a
   *free* state may be shared among several. A state bigger than the top of the band *must* be
   divided:
   - national: CA (3.1τ), TX (1.5τ), NY (1.3τ);
   - WH: CA (1.2τ);
   - FI: NY (2.3τ), CA (2.0τ), PA (1.9τ), FL (1.8τ), OH (1.3τ).
9. **List candidate district shapes (supports).** A support is any connected group of up to 6
   states within the distance limits, minus the national rules (New England only with itself and
   NY, FL alone, MS not with the southeast). national has 1,472 candidates, WH and FI 1,931 each,
   WIFI 16 (its three blocks and their pieces).

**Solving**

10. **The master**, an optimization run per channel. It decides how many districts use each
    shape, and how each divided state's opportunity is shared among them. Every plan must satisfy
    all of these:
    - exactly K districts;
    - each whole state in exactly one district, and every divided state's opportunity fully
      handed out;
    - **every district's size inside the band, shrunk by the rounding margin μ_S**
      (`MODEL.md` §4.6). At each end of the band, a district reserves the heaviest single ZIP of
      every divided state it touches;
    - feasibility rules for drawing: a district may enter a divided state from a given neighbour
      only as often as the border allows, and no district may take a sliver smaller than η.

    Among plans that satisfy all of that, it prefers compact districts, with the smallest total
    diameter. Compactness only ranks plans; it played no part in the failure.
11. **Result**: the solver *proved* that no plan exists at ±10% for national, WH or FI. WIFI fits
    its ±100%.
12. **Find the smallest band that works**, by bisection on δ: national ±16.5%, WH ±30.2%,
    FI ±13.0%.
13. **Stop.** Under OD1 the model never loosens a declared band on its own. It writes the
    smallest bands to `solver.json` and stops: no ledger, no maps.

**What runs next when a plan exists**

14. **Drawing** (`MODEL.md` §7):
    - inside each divided state, place a centre for each district sharing it;
    - hand each ZIP's opportunity to nearby centres, matching each district's planned share
      (a transport LP);
    - round so that every ZIP goes whole to one district;
    - make one repair pass to reattach stray pieces, provided both districts stay in band.

    Then come the ledger ((ZIP, fine channel) → district), the audit scorecard and the maps.

## Why ±10% failed

Think of each district as a box from (1 − δ)τ to (1 + δ)τ. The margin shrinks a district's box,
at both ends, by the heaviest ZIP of every divided state the district touches.

- **The margin.** In national, WH and FI, at least one state that must be divided contains a ZIP
  heavy enough that the margin alone uses up the ±10% band, or all but a sliver of it. A district
  holding part of that state is left with an empty box, and adding a neighbour adds the
  neighbour's margin too. With the margin set to 0 (a diagnostic, not a committed mode):
  national ±6.7%, FI ±2.9%, WH ±19.3%.
- **WH's geography.** With the WIFI states removed, the west coast (AZ, CA, NV, OR, UT, WA) is an
  island holding 1.615 districts' worth of WH at K = 11. One district there is 60% too heavy, and
  two are each 19% too light, whatever the free list. At K = 13 the island holds 1.909 and the
  rest 11.09, which fit. national (4.027 + 8.973) and FI (3.086 + 20.914) happen to fit.
- **Why the margin exists.** When ZIPs are finally assigned whole, a district can gain or lose up
  to one heavy ZIP per divided state it touches (`MODEL.md` Claim 3). The margin guarantees that
  the final map still meets the band.
- **Where it is conservative.** It reserves the heaviest ZIP anywhere in the divided state, not
  the ZIP actually on that district's edge. #73 measures the middle option: the margin only where
  a state is actually divided.

IFA 50 (`scenarios/50_ifa.toml`) stopped the same way, at ±45.4%. Its smallest band does not move
with the free list, the support size, the distance cap or η, and with the margin set to 0 it fits
at 0%.

## How the legacy pipeline got a map

The tagged catalog's 51 always produced a map because it never checked the final map against a
band (`MATH_REVIEW.md` at `archive/pre-support-2026-09`):

- its national and FI solves used a ±10% state-level band with no rounding margin, at
  mip_rel_gap 0.01–0.05;
- the ZIP stage widened the band by 0.1τ (`--band-slack 0.1`) and then ran unguarded fragment
  healing and national routing;
- WH11 was loaded from a nationwide run whose τ counted the western states, so the WIFI carve-out
  was never part of WH's solve;
- it ran on `instance_descaled_v4_conus.json.gz`, not today's extract.

Scored on today's extract, its 51 map has national at −16% to +12% (8 of 13 districts within
±10%), WH at −27% to +22% (5 of 11), FI at −26% to +26% (16 of 24) and WIFI at −60% to +86%
(0 of 3). In all, 22 of its 51 districts are outside ±10%. The figures are on #74.

## Sources

- #73: the smallest bands with and without the margin, and the levers tried on IFA.
- #74: the legacy 51 scored on today's extract.
- #76 and #79: the scenario scope and the IFA scenario.
- `runs/<scenario>/solver.json` (local, gitignored): each run's smallest-δ report.
