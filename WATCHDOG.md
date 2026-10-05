# td watcher: mandates

Standing instructions for the pi-omp-advisor watcher (owner, 2026-10-05). The model and cadence are in
sv-ntlee `agent/pi/WATCHDOG.yml`, and the workflow rules in its `WATCHDOG.md`.

## What td is for

td draws sales districts for each planning channel: K districts per channel, each holding a
balanced share of the channel's opportunity, **and each one connected piece of territory**.
Contiguity is the reason the project exists. The owner calls it a mandate to be strictly kept
(2026-10-04). On 2026-09-01 it was set aside "for simplicity" with no return trigger, and for five
weeks every map shipped with detached pieces while the reports said "pieces are listed". Your job is
to catch the next drift like that while it is still one sentence or one edit.

## The mandates (owner decisions 2026-10-04; the register `docs/problem/MANDATES.md` is still to be filed)

**M1, ZIP contiguity (hard).** Every district in every channel is one connected piece:
- on the drawn 2025 TIGER ZCTA polygons, rook adjacency (a shared boundary of positive length;
  a shared corner point does not count);
- across water only through the committed connector list;
- every CONUS ZCTA belongs to a district, zero-opportunity ZIPs included, assigned by the ledger;
- no tolerance: a detached piece fails the map. Listing the piece is not enough.

The model plans and draws on that same polygon graph.

**Statuses.** Only the owner sets a status: `hard`, `deferred` (with an executable return trigger),
or `waived` (dated, with its condition).

## Raise a `blocker` when

1. Wording makes M1 weaker. Examples: "listed", "reported", "measured", "tracked", "flagged",
   "defect rank", "best effort", "for simplicity", "moot", "dead", "not required", "out of scope",
   "follow-up", "later", a tolerance, a piece-size threshold, or "connected at unit level" offered
   as if it settled the ZIP level. A deferral counts here unless the owner made it and it names a
   test that fires.
2. An edit or write changes what M1 is or how it is checked, and the owner has not approved that
   change in this session or on the issue. Paths: `docs/problem/MANDATES.md`,
   `docs/problem/PROBLEM.md`, `docs/MODEL.md`, `td/audit.py`, `td/realize.py`, `td/master.py`,
   `td/output.py`, `td/swap.py`, `tools/looks/`, `tools/mandates/`, `tests/test_mandates.py`,
   `AGENTS.md`. Examples: a check turned into a warning or listing, a fixture deleted or weakened,
   a failing test skipped or xfail'd, a threshold loosened, the graph swapped.
3. A map, run or shortlist entry is called eligible, final, passing or shippable while it has a
   detached piece.

## Raise a `concern` when

4. An owner decision about td is stated without the owner's words. A quote, issue comment or
   PROBLEM.md row is enough; "the owner wants" alone is not.
5. A contiguity result is given as a count without severity, such as "5 pieces" with no mass or
   tau share, or "17 real of 872".
6. The agent settles a question that `## Asking` says to raise, or the gate and review stop
   checking M1.
7. An archive, clean-slate or cleanup step drops a mandate row or a return trigger.

## Not drift (stay quiet)

- Reporting honestly that maps fail M1, or measuring how badly they fail.
- Planning, research and experiments that do not change the requirement.
- The audit listing pieces with cause and mass, provided the map also fails.
- Unit-level facts (split sets, split floors, $ per district) used as lower bounds.
- Experiments on a contiguity-aware realizer that relax balance or splits rather than M1.
- The owner changing a mandate in this session's user messages. The owner is the authority:
  your job then is to check the change lands in MANDATES.md with their words.
