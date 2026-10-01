# Planning channels, purity, fallback and scenarios (td#67, td#76)

**Context.** Exporter v3 exports base (fine) channels with one κ (`mem:decisions/exporter-v3-2026-09-28`). The planner needs planning channels built from them. On 2026-09-29 the owner settled how a unit's fine channels map to planning channels in m5 session 01a0ee3e, fork 01a0efe6, the "#3" session, recorded on td#67 and td#76. #52 S11 is the partition of (unit, fine channel) cells (`mem:decisions/support-refactor-2026-09-25`).

**Decisions.**
1. **Purity is defined per unit.** Every (unit, fine channel) cell belongs to exactly one planning channel, a per-unit case of #52 S11. A unit that has national keeps national chase, wells WH and wells FI out of WH and FI. A unit without national maps national chase and wells FI to FI, and wells WH to WH. Which units have national is declared per unit, not derived from the data (owner, td#67, td#76).
2. **Fallback only relabels a cell's planning channel.** No cell is created or merged, and the ledger keeps one row per (ZIP, fine channel). A ZIP's planning mass is the sum of M over the fine channels assigned to that planning channel there. Rep books are ignored while staffing is out of scope. This is exact because exporter v3 uses one κ across channels (owner, td#67).
3. **A scenario is one TOML spec.** It holds the unit system, the per-unit assignment of fine channels to planning channels, per-channel K, band and modes, one final tolerance, and the extract's identity. A scenario is neither a run nor the extract. Planning channels cannot overlap within a scenario, so national and a combined WIFI that share members need separate scenarios (owner, td#76).
4. **Combining channels happens downstream of the exporter**, which exports base channels only.

**Alternatives rejected.**
- Purity per state: a unit can be a carved-out piece, or a metro piece that crosses state lines.
- Creating or merging cells on fallback: unnecessary, since summing planning mass is exact under one κ.
- A fixed national aggregate inside the exporter, with κ pinned to it: the arbitrary-channel contract and the per-unit assignment make channel definitions data, not code.

**Consequences.** One open item was deferred by the owner: how to compare and propose combinations of fine channels, and what makes a combination good. It is tracked on td#76 (open) and needs X2 (td#3) first. #67's `spec.py` and `supports.py` landed on 2026-09-30 (merges 89733c2, 3778292).

**Status.** Settled by the owner, 2026-09-29. Source: m5 session 01a0ee3e, fork 01a0efe6.
