# Triage: docs/problem/CONTIGUITY.md (#106, landed c603d46)

Approved by the owner 2026-10-05 ("Approve as drafted") and applied the same day. The brief is a
problem doc, not a lens file, so its triage table lives here.

Applied: U59–U65 and the U56 restatement in `docs/problem/UNKNOWNS.md`; #109 amendments (rows 1,
4, 6, 8, 15, 16, 18); #116 amendment (row 5); comment on #112 (row 14); new issue #118 (row 11,
"new issue F" below).

## Table

| # | finding (brief §) | bin | destination | why |
|---|---|---|---|---|
| 1 | CU1: is joint Detail tractable at ZIP scale in HiGHS; does highspy expose a lazy-constraint callback (§3.7, §5) | Unknown + Issue | **U59** (E); #109 amendment A | #109 runs option 1 already; it should report the size and time per coupled group and settle the callback question first |
| 2 | CU2: which of today's plans have an M1 drawing at their support (§5) | Drop | — | duplicate of U55 (liftability) with U54 (internal band); #109 measures both |
| 3 | CU3: what infeasibility proof licenses a master cut when shares are continuous (§5, §3.7) | Unknown | **U60** (T) | a theorem; #109 arm 2 already cuts only on a proved-infeasible whole fibre, so no new issue until a proof is wanted |
| 4 | CU4: districts with no fixed body touching a split state they share ("ports") (§5, option 2 risk) | Unknown + Issue | **U61** (E); #109 amendment B | decides whether rooted models work; cheap to count on #109's maps |
| 5 | CU5: one piece count; the three conventions disagree (s13 4 or 5; WH_07 33 or 1; IFA 49 7 or 12) (§2.5, §5) | Unknown + Issue | **U62** (E); #116 amendment C | #108 makes the audit the M1 verdict; once #116 owns every ZCTA, display fill retires and the audit's list is the one count |
| 6 | CU6 residual: how many districts' connectivity depends on a single connector (§5) | Unknown + Issue | **U63** (E); #109 amendment D | the approved list makes the graph one component; a district held together by one ferry is fragile and worth knowing |
| 7 | CU7: telling multipart-ZCTA pieces from M1 failures (§5) | Drop | — | answered by #108 at 27dfa6e: part-level graph, 110–230 listed per run, out of the ranking (owner 2026-10-05) |
| 8 | CU8: can the archived separator/flow engines (C03, C05, C06, C13, C21) be revived on HiGHS (§4, §5) | Unknown + Issue | **U64** (E); #109 amendment E | the brief says they may shorten option 1; #109's worker should check before writing new code |
| 9 | CU9: prove or refute R3's port extension of brieden2017 Thm 10 (§3.4, §5) | Unknown | **U65** (T/E) | option 5 ranks last and is a warm start only; no issue now |
| 10 | CU10: the price of M1 in splits and balance (§5) | Unknown (restate) | **U56** restated | U56 has the split gap g; add balance points so CU10 has no second home |
| 11 | AGENTS.md trap 23 and `BALANCE.md:41-42` still say contiguity is judged on the Voronoi graph (§2.5) | Issue | **new issue F** | both contradict M1 once #108 lands; trap 23 is in AGENTS.md, so the owner approves the wording |
| 12 | `MODEL.md:651-652` lists pieces (§2.5) | Drop | — | #108's diff rewrites MODEL.md §9 |
| 13 | Three piece-count conventions (§2.5) | Drop | — | the same finding as row 5 |
| 14 | Options ranked 1–6 (§4) | Issue (comment) | comment on **#112** | a recommendation; how M1 is achieved stays the owner's (#112, WATCHDOG layer 4) |
| 15 | Treat the master's support as the districts *allowed* in a split state, not fixed shares; Detail recomputes shares (§3.7) | Issue | #109 amendment G | #109 says arm 1 "keeps the master's plan fixed", which can be read as fixed shares; finding 9 says a failure at fixed targets excludes nothing |
| 16 | Flow demand is one unit per ZIP, not its opportunity, so zero-opportunity ZIPs cannot escape connectivity (§3.7) | Issue | #109 amendment H | a formulation trap; with mass-weighted demand an empty ZIP could be left off a district's tree |
| 17 | Build the master's adjacency from the polygon graph and connectors (§3.7) | Drop | — | #114 |
| 18 | Report "connected and feasible" apart from "proved optimal" (§3.7) | Issue | #109 amendment I | #109 asks for solve time and gap but not this split |
| 19 | Post-repair heuristics guarantee nothing and every result must pass #108's gate (§3.7, option 6) | Drop | — | already M1 under tolerance none; every map passes the gate or fails |
| 20 | Decisions the brief points to: #112, #110, connectors, trap 23 (§6) | Drop | — | #112 open; #110 answered pending your confirmation; connectors done; trap 23 is row 11 |
