# IFA K grid, K = 48..54 (2026-10-13)

The nested ladder the owner approved: K52 is `ifa_conus_v2` re-merged (all 33,300 ZCTAs hold the
same district as v2), and each step redraws one region; every other region is v2's folder unchanged.
Per-district window fixed at $1,000–1,437.5M (m_rel 798.74–1,148.19, E2). Headline M1 is the gap-width
gate (G3), as in v2; the strict gate is shown beside it. $ = m_rel × 1.2519681558.

| step | region redrawn | groups (K) |
|---|---|---|
| K53 = K52 + SA 9→10 | `regions/southatl_k10` | MD+DE (1, F1) · VA+DC+WV+NC+SC+GA+FL (9) |
| K54 = K53 + W 7→8 | `regions/west_k8` | all ten West states (8) |
| K51 = K52 + MW 14→13 | `regions/midwest_k13` | MI+IN+IL (5) · OH (2) · WI+IA (2) · MN+ND+SD+NE (2) · KS+MO+CO (2) |
| K50 = K51 + W 7→6 | `regions/west_k6` | all ten West states (6) |
| K49 = K50 + SA 9→8 | `regions/southatl_k8` | MD+DE+WV (1, F1) · VA+DC (1) · NC+SC (2) · FL+GA (4) |
| K48 = K49 + MA 12→11 | `regions/midatl_k11` | NJ (3) · PA (3) · NY (5) |

Folders are under `runs/exp/contig/ifa/kgrid/`; each has a `manifest.json`.

| K | region Ks (NE+MA+SA+SC+MW+W) | split states | M1 gap width (failing) / strict (failing) | districts in/under/over window | worst district | mean $/district | label | map |
|---|---|---|---|---|---|---|---|---|
| 48 | 4+11+8+6+13+6 | 19 | fail (IFA_12) / fail (IFA_12, IFA_28, IFA_44) | 47/0/1 | IFA_16 $1,923.8M (486.3M outside) | $1,277.8M | eligible (Manhattan neck and MD F1 excepted) | [map](K48/summary.png), [ZIP](K48/zip_IFA.png) |
| 49 | 4+12+8+6+13+6 | 19 | fail (IFA_09) / fail (IFA_09, IFA_29, IFA_45) | 48/0/1 | IFA_17 $1,923.8M (486.3M outside) | $1,251.7M | eligible (Manhattan neck and MD F1 excepted) | [map](K49/summary.png), [ZIP](K49/zip_IFA.png) |
| 50 | 4+12+9+6+13+6 | 19 | fail (IFA_09) / fail (IFA_09, IFA_30, IFA_46) | 49/0/1 | IFA_22 $1,923.8M (486.3M outside) | $1,226.7M | eligible (Manhattan neck and MD F1 excepted) | [map](K50/summary.png), [ZIP](K50/zip_IFA.png) |
| 51 | 4+12+9+6+13+7 | 17 | fail (IFA_09) / fail (IFA_09, IFA_30) | 50/0/1 | IFA_22 $1,923.8M (486.3M outside) | $1,202.6M | eligible (Manhattan neck and MD F1 excepted) | [map](K51/summary.png), [ZIP](K51/zip_IFA.png) |
| 52 | 4+12+9+6+14+7 | 16 | fail (IFA_09) / fail (IFA_09, IFA_30) | 51/0/1 | IFA_22 $1,923.8M (486.3M outside) | $1,179.5M | eligible (Manhattan neck and MD F1 excepted) | [map](K52/summary.png), [ZIP](K52/zip_IFA.png) |
| 53 | 4+12+10+6+14+7 | 19 | fail (IFA_09) / fail (IFA_09, IFA_31) | 52/0/1 | IFA_17 $1,771.5M (334.0M outside) | $1,157.2M | eligible (Manhattan neck and MD F1 excepted) | [map](K53/summary.png), [ZIP](K53/zip_IFA.png) |
| 54 | 4+12+10+6+14+8 | 22 | fail (IFA_09) / fail (IFA_09, IFA_31) | 53/0/1 | IFA_17 $1,771.5M (334.0M outside) | $1,135.8M | eligible (Manhattan neck and MD F1 excepted) | [map](K54/summary.png), [ZIP](K54/zip_IFA.png) |


"Eligible" means: every district one piece with no neck under the gap-width gate except the
Manhattan neck, and every district in the window except the MD district (F1). Both are v2's
standing exceptions, kept at every K. No K failed or errored. The worst district is the MD F1
district at every K. In K53 and K54 it is MD+DE ($1,771.5M); in the rest it is MD+DE+WV
($1,923.8M). Every other district is inside the window at every K.

Each `K<N>/` holds `summary.png`, `zip_IFA.png`, `districts.csv`, `run.json`,
`score.txt` (`tools/looks/score.py`) and `check.txt` (`tools/mandates/check.py`, strict gate).
[REVIEW.pdf](REVIEW.pdf) has one page per K, from 48 to 54.

## Needs your eye

- **M1 failures other than Manhattan:** none under the gap-width gate. These necks fail only the
  strict gate, and the gap width (G3) clears them:
  - El Paso (TX) at every K. This is v2's own flip.
  - The West K6 district Phoenix + NM + UT (K48, K49, K50; IFA_44/45/46): a 5.5 km neck in Utah.
    The repair could not remove it under the strict gate.
- **Out-of-window districts:** only the MD F1 district (see above).
- **Regroupings.** Every redrawn region except MA11 is regrouped, because no v2 group could take or
  give one district and keep its τ inside the window:
  - **SA10:** WV moved out of the MD district, so that district is now MD+DE (MD still whole, still
    over the window under F1, and $152M less over than in v2). VA+DC, NC+SC, GA and FL were merged
    with WV into one K9 group.
  - **SA8:** FL and GA were merged into one K4 group.
  - **W8:** Mountain K2 and Pacific K6 were dissolved into one West K8 group.
  - **W6:** West K6, one group.
  - **MW13:** MI, IL and IN were merged into one K5 group.
- **Looks** (M1 passes, but the shapes are worth a look):
  - **W8:** the Salt Lake City district spans six states (UT, MT, WY, NM, NV and a piece of AZ) and
    sits at $1,002M, on the window floor. An LA/Riverside district runs up eastern CA with slivers
    of NV and OR.
  - **W6:** San Diego + western AZ + southern NV. Seattle + OR + ID + MT + WY + northern NV.
  - **SA10:** the Charlotte district is southern VA + western NC + upstate SC. The Charleston
    district is coastal SC + GA + north FL.
  - **MW13:** Indianapolis + southwest Michigan form one district (IN 536, MI 542 m_rel).

## Judgement calls

1. **Which group changes.** Within a region I took the group whose new τ stays in the window and
   closest to its centre. Where no single v2 group could, I merged the fewest adjacent groups that
   could:
   - SA10: adding a district to any SA group drops its τ under $1,000M. Only all the non-MD groups
     together clear the floor (τ 807.9 m_rel).
   - SA8: FL K3 would be $1,455M, so FL+GA K4 (τ 1,103.5).
   - W6: Mountain K1 and Pacific K4 are both over the window, so West K6 (τ 1,115.0). I chose this
     over AZ+NM alone + the rest at K5 (τ 1,142.6, 5.6 m_rel of headroom).
   - MW13: the one two-group merge that fits is MI+WI+IA K4 (τ 1,109.2).
2. **SA10 retry.** VA..FL K9 at τ 807.9 (δ 0.011) still had a VA district in pieces (0.39 τ) after
   the window repair. I moved WV from the MD district into the rest: MD+DE K1, rest K9 at τ 821.4
   (δ 0.027). This drew and repaired to 0 pieces and 0 necks, 9/9 in the window. It shrinks the F1
   district and does not widen any waiver.
3. **W8 retry.** Pacific K6 at τ 805.3 is inside the window, so I kept v2's groups first. At δ 0.008
   the repair still left 12 pieces. I switched to whole West K8 (τ 836.2), which repaired to 0
   pieces and 0 necks.
4. **MW13 retry.** MI+WI+IA K4 left a 0.42 τ piece: a lower-Michigan district reached WI through
   the UP. I switched to MI+IN+IL K5 (τ 1,074.1, three groups). Its first draw (1,800 s) kept a
   0.81 km neck in SW Indiana through:
   - three repairs, the longest with `--flow` and 1,500 s windows;
   - a hand move of 14 ZCTAs. That made a new neck, and that folder is not used.

   A redraw of the same spec with a 3,600 s limit came out with 0 pieces and 0 necks. That is
   `mw_k13_miinil_b`, which K48–K51 use. An alternative IL+WI+IA+MN+ND+SD+NE K5 drawn beside it
   also came out clean (`mw_k13_ilwiiamn`); it is not used.
5. **MA11.** I took PA K3 (τ 1,096.8) over NY K4 (τ 1,092.2), which are 0.4% apart. Reasons:
   - PA K3 reuses the existing `ifa_pa_k3` draw (0 pieces, 0 necks, $1,373M each).
   - NY K5 and its Manhattan exception stay exactly as in v2.
   - The NY K4 drafts had Long Island necks (d08bf30, 5f2df8e).
6. **Rendering and export.** Maps were rendered with `TD_REPO=<worktree>` (the merge records its
   spec relative to the repo) and the untracked inputs from the hub, as v2 was. Grid points have no
   `export/` (long CSV and GeoJSON); only v2 has one.
7. **Driver and bundle code.** `tools/exp/contig/kgrid.sh <K>` builds one point (merge, render,
   score, gate). `tools/exp/contig/kgrid_review.py` builds this bundle.
