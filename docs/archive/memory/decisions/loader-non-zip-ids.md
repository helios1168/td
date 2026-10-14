# Non-ZIP ids reach the CONUS rule (td#3, td#78)

**Context.** The real v3 extract failed `td.data.load` at `c5be768` (`mem:facts/v3-extract-loading`). A few cells had 5-character alphabetic ZIP ids, which look like the blank-ZIP placeholder that the pre-v3 exporter dropped. `load()` refused any id that was not five digits, so these cells never reached the CONUS rule. That contradicted the `td/data.py` docstring, which says blank ids drop under that rule. On 2026-09-29 the owner chose among three options in m5 session 01a0ee3e (fork 01a0efe6). The choice was recorded on td#3 and implemented by td#78, which merged at `42aef54`. Lander acceptance on m2 on 2026-09-30 was 53 passed, 0 failed and 0 skipped, with the state polygons present.

**Decisions.**
1. **The loader passes non-ZIP ids through and the CONUS rule counts the drop (owner, td#3, option (a)).** `from_payload` accepts any string ZIP id. `conus` drops ids that are not ZCTAs as "not a CONUS ZCTA", with ZIP count, cell count and `m_rel_share`, and never lists them (`mem:decisions/sparse-fixture-and-loader` choice 6).
2. **#78 relaxes only the 5-digit rule (m5 session, when #78 was filed).** The loader still refuses non-string ZIP ids by count, and every other malformed-extract check stays: channels not in the list, bad `m_rel`, shares outside [0, 1], and duplicate cells. Option (a) covers the blank-ZIP placeholder and nothing wider.

**Alternatives rejected.**
1. (b) Have the exporter drop non-ZIP ids with a count and re-run the extract. This moves the rule off the one place that already counts CONUS drops, and it needs a new export from the work machine.
2. Keep the loader strict and drop the cells only in the file. That is a manual edit the loader never sees, and it has no count.
3. Relax more than the 5-digit rule, such as accepting non-string ids. That is wider than the placeholder needs.

**Consequences.** Any string id in an extract loads. Garbage ids therefore surface only as a "not a CONUS ZCTA" count in `dropped`, never as a load error, so a large count there is worth reading. The m5 hub copy of the real extract was hand-edited before #78 landed, so the two Studios' copies differ (`mem:facts/v3-extract-loading`).

**Status.** Settled. Landed in `42aef54` (2026-09-30).
