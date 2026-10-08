# Owner decisions, 2026-10-08 (research tab, ~01:30 owner's clock)

Structured answers in the research tab; the lander files them into PROBLEM.md and the issues.

- **F1, MD under rule C** (pick: "MD stays whole: one-state band waiver"). Maryland alone is one
  IFA district at about $1,507M, 4.8% over IFA's upper edge $1,437.5M. Rule C and the band for
  every other IFA district are unchanged. This is an OD1 waiver for MD only; it stays recorded as a
  band exception on every map that uses it. Rejected: a joint MD+PA district under rule C (MD in
  up to 4 districts, 3 cuts); raising IFA's upper edge for all districts.
- **F2, D1 revoked** (pick: "Revoke: K from the grid within 46-55"). "IFA at K >= 50 under rule C"
  (2026-10-07) no longer stands; the band is K-independent since E2, so IFA's K is chosen from
  the grid within 46-55.

Context the decision rested on: `CONTEXT-IFA.md` (scout, GPT-6 Luna) and the arithmetic in the
research tab: two MD pieces need 393.84 m_rel of whole attach mass against at most 374.34
available (DC+DE+WV plus VA's room), at every K; county grain does not change it; the
Washington-Baltimore CSA as a unit moves the obstruction to VA (DC + VA + DC-side MD counties =
1,430.6 m_rel, over U).

Tracked illustration: `runs/exp/contig/r2illustration/ifa46-md4/` (hand edit of ifa46-whole, MD in
4 county groups, M1 pass; not a candidate) awaits its shortlist entry from the lander before it is
shown again (T1).

## Later the same session (~02:20 owner's clock)

- **F1 and F2 confirmed** (owner: "for 1 yes confirm f1 and f2"). The lander files them.
- **F3, the #128 re-render is declined for good** (owner's words: "no we do not want to run
  the 58 map re-render. don't ask again, store my explicit consent to avoid that"). The 58
  shortlist entries whose renders predate the 2026-10-07 renderer change stay as they are, their
  T1 "render not current" failures are accepted, and no session asks about the re-render again.

## G1, G2: neck rule findings from the single-state draws (owner, 2026-10-08, structured answers)

**G1 (their pick "Measure width across coverage gaps").** M1's neck width counts unassigned land
between ZCTA polygons, so ZCTA coverage gaps do not read as necks. Cause: IFA TX K 3
(`runs/exp/contig/nj/ifa_tx_k3`, branch `m5-studio/explore-neck`) has one neck, El Paso + the
Trans-Pecos (44 ZIPs, $81M, 6.9% of IFA_02's land) joined to the rest of Texas by the single polygon
edge 79718-79734 at 6.14 km, because the desert ZCTA polygons do not touch (79830 Alpine has no
polygon edge to 79735 Fort Stockton) while the land passage is over 100 km wide; every neighbour is
already in the district, and repair windows up to 1,443 ZIPs proved nothing local helps. This is a
gate change (td/audit.py NeckGraph width); prototyped behind a flag, default off, until the
lander's owner-decision issue lands. Alternatives recorded and not chosen: keep the rule and give El
Paso New Mexico on the CONUS map; a one-off connector across the gap; defer.

**G2 (their pick "Dilute: Manhattan + Bronx + Westchester").** Under the 10 km / 5% land rule any
district whose land is more than 5% Manhattan fails M1: the island is under 4 km wide, so every cut
across it is a neck once the cut-off side holds 5% of the district's land (the congressional-district
NY K 5, `runs/exp/contig/nj/ifa_ny_k5_cd`, fails on a 5.5 km cut at 10024-10029 with 5.2% of the land
south of it, and adding 48 km² of Westchester only moved the cut north). Manhattan is 57 km² and
$546M, so a district holding it needs over 1,148 km² of land; Manhattan + Bronx + all of Westchester is
$1,300M on 1,277 km² (Manhattan 4.5%), inside the window. NY K 5 is re-solved with a generic land
floor: for every district, the land of units that have a neck on their own is at most NECK_SHARE of
the district's land. Alternatives recorded and not chosen: a rule exemption for water-bounded cut-off
parts; defer.
