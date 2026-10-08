# Covering a division with the channel structure: the sketch and the arithmetic

Research tab, 2026-10-08. Draft for owner review; an Astra oracle review of the same question is
in progress and will be filed beside this.

## 1. The question

Without assuming the lead map's layout, how can each Census division be covered 100% by the
current channel structure, and which coverings pass the arithmetic? The structure is:

- Five fine channels: `national_chase`, `wells_wh`, `wells_fi` (together the **national** model
  channel), `wh` (**WH**), `fi` (**FI**).
- Each state is either **pure** (its national, WH and FI cells planned as three separate
  channels) or **combined** (all five fine channels of the state merged into **WIFI**).
- Bands (D3, E3): national, WH and FI within ±15% of a fixed dollar target ($1,250M, $1,000M,
  $900M); WIFI within ±15% of the **global** dollar-weighted mean over all WIFI districts, so
  WIFI's band is not fixed and couples every division that has combined states.

## 2. How to think about it

The decision variable is one bit per state: pure or combined. A division with n states has 2^n
assignments (at most 512 for South Atlantic). Each assignment is checked channel by channel:

1. **Pure channels, K range.** For channel c, the pure states' dollars M_c must admit a district
   count: ceil(M_c / U_c) ≤ floor(M_c / L_c). Under D3 this range depends only on dollars, not on
   a chosen K. An empty range means the assignment is infeasible when sealed.
2. **Forced splits and forced company.** Within the pure states, a state over U_c must split in
   channel c; a state under L_c must attach to a same-channel pure neighbour inside the division.
   Counted, not yet checked for connectivity.
3. **WIFI.** Each connected component of the combined states must be partitionable into
   districts within ±15% of the global WIFI mean. That is a partition check conditional on the
   global (M_WIFI, K_WIFI), which couples the divisions: it can only be finished once every
   division's combined set is chosen. The enumeration reports each assignment's WIFI dollars and
   leaves this check for the coupled step.
4. **Sealing.** If divisions are sealed (no district crosses a division line, not an approved
   constraint), each division's check is independent except through WIFI's global mean. If not,
   the K range and the attach check are taken over the merged region instead.

What arithmetic does not decide: M1, shape, rule C, the look. It only prunes.

## 3. The result, sealed divisions, pure channels only

Dollars from the scorer's rates on the lead map's ledger, per state and fine channel, rounded to
$1M (sketch precision; pass/fail at the margin needs the full-precision regeneration). Script
output in `research-2026-10-08/combos.csv`.

| Division | States | Assignments | Feasible for the pure channels | Options |
|---|---|---|---|---|
| New England | 6 | 64 | 1 | all six combined (WIFI $2,302M) |
| Middle Atlantic | 3 | 8 | 2 | all pure (nat 3, WH 2, FI 4–5; 3 forced splits) or all combined ($9,540M) |
| East North Central | 5 | 32 | 5 | IL combined; IN+OH; OH+WI; IN+MI+WI; all five |
| West North Central | 7 | 128 | 1 | all seven combined ($2,443M) |
| South Atlantic | 9 | 512 | 144 | all pure (nat 3, WH 3, FI 5) and 143 partial combinations |
| East South Central | 4 | 16 | 1 | all four combined ($2,547M) |
| West South Central | 4 | 16 | 1 | all four combined ($4,754M) |
| Mountain | 8 | 256 | 1 | all eight combined ($2,812M) |
| Pacific | 3 | 8 | 1 | all three combined ($7,705M) |

The finding: **under sealed divisions, pure channels can exist only in the Middle Atlantic, East
North Central and South Atlantic.** Everywhere else, every pure channel's dollars within the
division are a fraction of one district (the Pacific has $4,329M national but only $1,311M WH;
WH's K range is empty), so the only covering is all-WIFI. That would put about $22.5B of the
$48.9B main-map dollars into WIFI, including Texas and California.

So sealing at the Census division is incompatible with the main map's pure-channel structure as
it stands. Two ways out, both owner choices:

- **Seal at division groups, not divisions.** The lead map's layout is one such grouping by
  hand (Northeast plus plains as WIFI, the rest pure, no walls). The check above re-run on a
  chosen grouping tells whether it is feasible.
- **Do not seal the main map; seal IFA only**, where every division is feasible on its own
  (`DIVISIONS_2026-10-08.md`, section 4).

## 4. What is still unchecked

- The WIFI partition check against the global mean (step 3 above).
- Connectivity of forced attachments inside a division (an under-L state needs a same-channel
  pure neighbour that is also inside the division).
- Full precision. Entries near a band edge can flip at $1M rounding.

## 5. Questions for the owner

- Is sealing meant for IFA only, or for the main map too? For the main map it needs a grouping
  coarser than the Census division.
- If division groups: which grouping should be checked first? The current layout is the obvious
  candidate; a four-region grouping (Northeast, Midwest, South, West) is the other natural one.

LEARNED: Under sealed Census divisions and D3, the main map's pure channels (national, WH, FI)
are arithmetically feasible only in the Middle Atlantic, East North Central and South Atlantic;
the other six divisions can be covered only by all-WIFI, because each pure channel's dollars there
are a fraction of one district.

## 6. Oracle corrections accepted (GPT-6 Astra medium, `research-2026-10-08/ORACLE-DIVISIONS.md`)

- "WIFI cannot exist under sealing" (DIVISIONS doc, section 4) is wrong. WIFI can hold separate
  districts in separate divisions; only the lead map's cross-division WIFI districts would need
  replacing. Corrected reading: the lead map's WIFI layout cannot survive sealing.
- Surviving assignments "pass the necessary mass screen"; they are not feasible maps. Geometry,
  indivisible ZCTAs, M1 and rule C are unresolved by arithmetic.
- Add a same-channel connected-component check: an under-L pure state needs a pure same-channel
  neighbour, and a combined state is not a bridge between pure states.
- The IFA South Atlantic row must reserve MD's one district under F1 and remove its mass before
  the K range: remainder $9,520M gives 7–9, so 8–10 in all, not 8–11.
- National K 15 is not impossible under D3: its mean $1,126M lies inside the target window, so a
  τ-band with δ ≤ 0.056 implies D3 (the earlier "no δ works" claim was wrong; δ is merely tight).
- Full-precision dollars before any published pass/fail count.
- Fewest combined states is navigation, not an approved ranking.
