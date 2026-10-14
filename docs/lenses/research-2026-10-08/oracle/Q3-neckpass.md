# Q3 — shortest neck-aware pass

**Reuse `repair.solve_window`, not a fresh `run.py` draw.** Load the existing plan and ledger; translate district IDs back to plan-copy names with `repair.owners_from_ledger` (`repair.py:147–160`). Preserve identical plan ordering.

For NJ, choose a local window spanning the neck and neighboring donor territory; outside ownership stays fixed. Reuse existing neck-window construction rather than inventing a radius. NY/PA: repair only after their district audits identify failures; leave passing drawings untouched.

`repair.py:360–382` builds:

```python
def cutter(own):
    return neck_cuts(c, owner, W, m, ng, own, check)
```

and passes `_solve_group(..., necks=cutter, neck_seed={z: owner[z] for z in zs})`. `ng` must be full authoritative `NeckGraph`. `neck_cuts` (`253–309`) overlays proposed window ownership onto the ledger, audits districts, and builds area/anchor-aware `NeckCut` rows. Include every currently failing affected district in `repairing`; otherwise `solve_window` deliberately exempts existing necks outside that set (`360–368`). Re-audit all affected districts afterward.

**Seed distinction:** `neck_seed` generates initial rejection cuts; it is not a solver warm start. `_solve_group(start=...)` considers an existing drawing (`draw.py:1114–1117`), but an invalid necked seed cannot become its accepted incumbent. `solve_window` currently receives seeds from `_attempt`, not directly from the ledger. Local fixed ownership supplies the substantive fix-up restriction without changing that API.

**Budget:** propose one 120–240-second local solve attempt, within a 480-second repair budget; unmeasured, not a completion promise. Neck checks add time outside some solver budgets. Use background notification and retain unknown honestly.

**State verdict:** audit each exact district set via `district_pieces`/`district_necks` on full graph, plus state-footprint coverage/routing/bands. Merging three states still leaves CONUS missing cells: it does not fix national coverage. Label verdict regional, not CONUS.

LEARNED: `neck_seed` cuts the old drawing; it is not a warm start.
DECIDED: Prefer existing local repair window over fresh state-wide draw.
