# Tracks — results ledger across approaches

**Charters:** `docs/APPROACHES.md` (one `## <ID>` section per approach). **This file:** one
row per approach, written by `/track-report` on the track's branch and imported by
`helios sync <id>`, which also copies the track's changed docs into `docs/tracks/<id>/`.
Rows are compared on `FRAME.md` §3's six acceptance criteria; those are method-independent,
so a row is comparable whatever the approach did internally.

**State:** `planned` (charter only) · `running` · `ready` (stage 5b/6b reached, verdicts in) ·
`merged` (adopted into the hub) · `abandoned` (killed — say why in the notes column).

**Criteria (FRAME §3):** C1 count and size · C2 coverage · C3 roster · C4 continuity per
person · C5 distance-to-best in business units · C6 reproducible and auditable. Cell values:
`met` / `unmet` / `n/a` / `?`, with the headline number where one exists.

| ID | state | stage | head | C1 | C2 | C3 | C4 | C5 | C6 | headline | notes / pointer |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A0 | running | 5b | ec8e727 | met 0.78% | met 1229/1229 | met 13/13 | unmet | unmet (nats) | met | balance-certified k=13 draw; saturation 41.9% | incumbent draw-then-match; `docs/FRAME.md` §0, `docs/VERIFY_U2-stab.md` |
