# What td is, and the user decisions that fixed its scope

**The problem** (re-scoped by the user over one session ending 2026-08-31). Fair division of
ZCTA territories between two merging wholesalers became greenfield balanced districting for a
new "national" annuity channel: the two largest firms carved out of the financial-institutions
and wirehouse channels, territories at about $1B opportunity each, solved as maximum Nash
welfare over a per-rep utility model in two stages (draw the map, then match reps). The old
two-player programme is intact on branch `contiguity-harness`. The multi-channel extension (CWIFI,
$48B across national, WH and FI) is the full-problem track (`mem:decisions/full-problem-2026-09-11`).

**Durable user decisions.**
- The real instance is the descaled export from the confidential work machine, not the
  synthetic twin (2026-08-31; `mem:workflow/confidential-data`).
- ★6 lifted: units may run code against the instance (2026-09-03).
- The sponsor's total of about $18B on v2 is correct and is not to be re-derived; v2 supersedes
  v1 and k = 18 (2026-09-04).
- U3-inv retired: books are measured from the warehouse, not self-reported, so
  strategy-proofness has no referent (2026-09-04). ★8 stays open with no cited basis.
- A1's lens, domain, brief and units were promoted to the hub (2026-09-05); they are now frozen
  under `docs/foundations/`.
- The modeled ground set is the lower 48 plus DC (2026-09-07; `mem:facts/instance-versions`).

**Two results that carry the work** (both pinned by tests).
1. Nash welfare on a common measure is equal-size districting: `Σ_j M_j` is
   partition-invariant, so maximising `Σ log M_j` equalises the terms. The $1B target needs no
   constraint, and the equalisation pathology (CLAUDE.md trap 2) is avoided.
2. The footprint is disconnected, which decomposes the problem by region and makes the balance
   ceiling (`channel.allocate_districts`) a free dual bound (`mem:facts/balance-ceiling`).

Source: host memory td-contiguity-programme (2026-09-10).
