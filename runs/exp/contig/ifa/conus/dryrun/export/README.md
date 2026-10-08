# IFA CONUS territory export

Run folder: `runs/exp/contig/ifa/conus/dryrun` (ifa_conus_merge), written by `tools/exp/contig/merge.py` at commit `d312834f9b0acfdb4485c0e021402086b9645e1e`.

- `ifa_zip_districts.csv`: one row per ZCTA: zip_code, state, county, cbsa, district,
  district_name, m_rel, usd.
- `ifa_districts.csv`: one row per district: district, district_name, states, n_zips, m_rel,
  usd, window, pieces, necks, m1 (the full-graph M1 audit, per district).

Rate: usd = m_rel x 1.2519681558 $M per m_rel, rounded to 0.1 ($M).

Band rule (owner, 2026-10-08, E2): each district passes when its m_rel lies in the window
[798.74, 1148.19] m_rel = [$1,000.0M, $1,437.5M]; 39 of 40 districts in it.  The audit's
τ ± final_delta line (final_delta {'IFA': 0.15}: fail, 40 districts, 9 outside the final tolerance) is information only and is not tuned to agree with the window.

Decisions:
- F1: MD is kept whole, under a band waiver.
- G1 (#131): a neck's width may count the coverage gaps beside it; the gate default measures
  the shared border only. This run was audited with the gate default.
- G2: as recorded in the owner's decision record (not restated here).

Sources (merged in this order):
- `CT,MA,ME,NH,RI,VT`: `runs/exp/contig/ifa/newengland/merged` at commit `d3a98fbf473e3653618c3c47ea680c6cfdae53af`, source M1 fail
- `AL,AR,KY,LA,MS,OK,TN,TX`: `runs/exp/contig/ifa/southcentral/merged_b` at commit `ed8efa04bcdd44a39e202585f457de34ab345efd`, source M1 fail
- `DC,DE,FL,GA,MD,NC,SC,VA,WV`: `runs/exp/contig/ifa/southatl/merged` at commit `4a6cb4f06010e84573e72de6aa0395c309d74c34`, source M1 fail
- `CO,IA,IL,IN,KS,MI,MN,MO,ND,NE,OH,SD,WI`: `runs/exp/contig/ifa/midwest/ifa_mw_merge` at commit `4e223f1a8c0d02e77f218a9e502e53c1819c8644`, source M1 fail
- `AZ,CA,ID,MT,NM,NV,OR,UT,WA,WY`: `runs/exp/contig/ifa/west/merged` at commit `002ee6a25cdcd9ee3c46c8d508f9f80a2229af64`, source M1 fail

CONUS verdict: M1 fail (0 districts in pieces, 0 detached pieces (largest 0 τ), 1 necks, 0 channel ZCTAs with no owner, 4257 (ZCTA, fine channel) cells with no row, 0 owned twice, 12 mass necks listed beside M1); band (window) fail; audit fail
(its τ line information only).
