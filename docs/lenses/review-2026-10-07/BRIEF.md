# Brief: what the A+C+B pipeline is for, and what has already failed (td, 2026-10-07)

## The goal, in the owner's words
- 2026-10-07: "now lets get back to the core problem. strictly contiguous territories with as few
  state splits as possble."
- The standing goal and its mandates are in `WATCHDOG.md`, layers 1–4. In short: in each channel,
  K_c districts cover every CONUS ZIP, and every district passes **M1**. M1 means one connected
  piece on the 2025 TIGER ZCTA polygons (rook adjacency, water only through listed connectors)
  with **no neck**: no part holding at least 5% of the district's land that reaches the rest only
  through a passage under 10 km of shared border.
- Eligibility:
  - drawn mass within ±15% of τ_c;
  - $ per district within ±10% of target;
  - main-map K between 48 and 54, IFA K between 46 and 55.
- Ranking, looks first: (1) split units per channel; (2) cuts, meaning Σ over split states of
  (districts − 1); (3) visual defects; (4) shape; (5) balance.

## Channels and sizes in play
- **Main map** (ne_plains layout): national K 15, WH K 11, FI K 20, WIFI K 3. WIFI is a combined
  channel of New England plus the plains states, all held whole.
- **IFA:** K 46–49.
- The best main maps so far pass M1 with 12–14 split states. They come from hand-chosen free lists;
  the split count has never been minimised.
- **No IFA map** both passes M1 and comes near balance.

## Evidence so far (details in `docs/RESULTS.md` and the issues)
1. **Plan, then draw, then repair (#121, #122, #124, #126) fails on IFA and the old Northeast
   layouts.**
   - The master fixes each state's share per district, and the drawing must realise those shares
     at ZIP level.
   - M1 failures show up only after drawing. Repair windows of up to about 2,000 ZCTAs mostly end
     "unknown" at their time limit.
   - The failures cluster in a few places:
     - districts holding pieces of two split states, such as NJ or PA joined to CT, MA or NYC
       pieces;
     - the Delaware Memorial Bridge (ZCTA 08023), which breaks a district holding DE and NJ
       without PA;
     - Utah: ZCTA 84621 breaks a district holding Utah with ID, MT or WY but without NV or CO,
       and the ZCTA pair 84740–84750 necks any district holding all of Utah;
     - west Texas: 79718–79734.
2. **#124's per-support drawability MILP** (`tools/exp/contig/plancheck.py`, `drawable`; proof in
   `docs/MODEL.md` §4.9) never once proved a support infeasible. Every hard case came back
   "unknown" (for example FI CT+DE+NY+PA at 600 s). The MILP needed wide-passage flow rows,
   because lazy NeckCut rows alone kept cycling.
3. **#127's whole-unit plans pass M1 by construction.**
   - The method: every unit is held whole, each district's exact ZIP union is checked with the M1
     gate, and a failing exact unit set is banned before the master re-plans (`wholeplan.py`).
   - The result: six IFA maps, all M1-clean, in about a minute each.
   - The catch: whole states and county pieces are too coarse for balance. Worst deviation was
     43–310%, because NY cannot be cut evenly by county: Queens has to sit with Nassau.
4. **The master** (`docs/MODEL.md` §3; `docs/problem/SPLITS.md` §3):
   - n_S ∈ ℤ≥0 copies of support S, shares t_{v,S}, and mass rows aggregated over the copies.
   - η_c > 0 makes a copy's footprint exactly S. With μ ≡ 0, its optimum bounds every connected
     drawing (Proposition D).
   - The objective is diameter, which is blind to splits.
   - #103's F2 adds a binary s_v per splittable unit.

## The pipeline under review (approved by the owner 2026-10-07: "yes i like your recommendation")
- **A, #103:** minimise split states in the master with a certificate (F2, lexicographic). It adds
  **rule C**, a switch under which each district holds at most one split state; everything else in
  it is whole states. A exports `plan.json`.
- **B, #129:** for each split state, an exact k-piece MILP carves the state's ZCTAs into the
  planned pieces. Each piece joined to its whole "attach" states must pass M1 inside its mass
  window. The result is ok, infeasible (proved) or unknown.
- **P, #130:** runs plan → carve every split state → assemble the ledger → exact M1 gate on every
  district. A proved-infeasible carve becomes a no-good cut, and the master re-plans. A district
  that fails the gate after an ok carve gets an exact support ban.
- **Lane models (owner):**
  - A and P: Sonnet 5.5 high. B: Opus 5.5 high.
  - Sol advises every lane through `ask_advisor` and reviews every lane.
  - The three lanes run in parallel against `CONTRACT.md`.

## Owner decisions still open (`WATCHDOG.md` §4); the pipeline must not settle them silently
- OD1, the final band.
- OD4, county pieces.
- #102, how M1 is achieved.
- #112, what gives way when a share cannot be drawn connected.
- #111, the smallest share that counts.
- #110, which master certifies floors.
