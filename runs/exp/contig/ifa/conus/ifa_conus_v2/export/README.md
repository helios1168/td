# IFA CONUS territory export

Run folder: `runs/exp/contig/ifa/conus/ifa_conus_v2` (ifa_conus_merge), written by `tools/exp/contig/merge.py` at commit `4572e81cc81e7b94f2233e5c3969407e4f502e7d`.

- `ifa_zip_districts.csv`: one row per ZCTA: zip_code, state, county, cbsa, district,
  district_name, m_rel, usd.
- `ifa_districts.csv`: one row per district: district, district_name, states, n_zips, m_rel,
  usd, window, pieces, necks, m1 (the full-graph M1 audit, per district); m1_default (the same audit with the gate default).

Rate: usd = m_rel x 1.2519681558 $M per m_rel, rounded to 0.1 ($M).

Band rule (owner, 2026-10-08, E2): each district passes when its m_rel lies in the window
[798.74, 1148.19] m_rel = [$1,000.0M, $1,437.5M]; 51 of 52 districts in it.  The audit's
τ ± final_delta line (final_delta {'IFA': 0.15}: fail, 52 districts, 5 outside the final tolerance) is information only and is not tuned to agree with the window.

Decisions:
- F1: MD is kept whole, under a band waiver.
- G1 (#131): a neck's width may count the coverage gaps beside it; the gate default measures
  the shared border only. This run was audited twice: with the gate default and with TD_NECK_GAP_WIDTH=1 (gap width counted).
- G2: IFA NY K 5 is re-solved with a generic land floor so a unit with a neck on its own stays
  under 5% of its district's land (owner 2026-10-08, pick 'Dilute: Manhattan + Bronx +
  Westchester', issue #132).
- G3 (owner, 2026-10-08 05:35): a neck that exists only because ZCTA polygons do not touch across
  land in no ZCTA (a coverage gap) does not fail M1.  The owner's words: "looks great! lets pass
  it or make an exception. necks caused by empty zips should trigger a fail, that is a GREAT
  looking map" (read as: should not fail).  This run's headline M1 is the gap-width audit; the gate-default verdict is shown beside it, and the districts whose verdict differs are: IFA/IFA_30.

Sources (merged in this order):
- `CT,MA,ME,NH,RI,VT`: `runs/exp/contig/ifa/newengland/merged` at commit `d3a98fbf473e3653618c3c47ea680c6cfdae53af`, source M1 fail
- `NJ,NY,PA`: `runs/exp/contig/ifa/midatl/merged_v2` at commit `63c4f22df0cd97f1239c232dec40d0c05d7413a5`, source M1 fail
- `DC,DE,FL,GA,MD,NC,SC,VA,WV`: `runs/exp/contig/ifa/southatl/merged` at commit `4a6cb4f06010e84573e72de6aa0395c309d74c34`, source M1 fail
- `AL,AR,KY,LA,MS,OK,TN,TX`: `runs/exp/contig/ifa/southcentral/merged_b` at commit `5b5da2621f01d6c01e6b7f8f1d945f0741d8cf59`, source M1 fail
- `CO,IA,IL,IN,KS,MI,MN,MO,ND,NE,OH,SD,WI`: `runs/exp/contig/ifa/midwest/ifa_mw_merge` at commit `4e223f1a8c0d02e77f218a9e502e53c1819c8644`, source M1 fail
- `AZ,CA,ID,MT,NM,NV,OR,UT,WA,WY`: `runs/exp/contig/ifa/west/merged` at commit `002ee6a25cdcd9ee3c46c8d508f9f80a2229af64`, source M1 fail

CONUS verdict: M1 fail (0 districts in pieces, 0 detached pieces (largest 0 τ), 1 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 11 mass necks listed beside M1); with the gate default, M1 fail (0 districts in pieces, 0 detached pieces (largest 0 τ), 2 necks, 0 channel ZCTAs with no owner, 0 (ZCTA, fine channel) cells with no row, 0 owned twice, 15 mass necks listed beside M1); band (window) fail; audit fail
(its τ line information only).
