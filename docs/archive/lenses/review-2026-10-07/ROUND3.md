# Round 3: test the carve-first method

Read `/tmp/iss/acb/review/CONSOLIDATED.md`, its round-2 section and both owner-answer sections
(E1–E3 decided, E4 open), then `/tmp/iss/acb/review/METHOD-carve-first.md`. The owner asked for
this: "whatever methodology we're using here should be investigated for a better and faster
solution". It is read-only as before; the only file you write is your round-3 report.

1. **Soundness.**
   - Is the selection MILP correct as written: coverage, K, rule C built into patterns, and the
     lexicographic objective?
   - Does "every column passed the gate" give an M1-clean map with no repair?
   - Are the certificate claims (s_lower from #103, s_drawn from the library, "proved
     fewest-splits" only when equal) correctly scoped?
2. **Against the v2 loop.** Is carve-first faster and more likely to deliver a clean map for FI
   20, IFA (−20%/+15%, K 46–55) and the main map? What does it lose? Which of R1–R13 does it make
   unnecessary, and which still apply?
3. **Pricing and library growth.** Is dual-priced pattern generation workable here? What is the
   pricing problem exactly, and is a heuristic pricer enough? How should a #103 plan that the
   library cannot match be used?
4. **Scale.** Estimate the size of the whole-column family and the pattern counts for FI 20 and
   IFA. What should be measured first, and what is the stop rule if the library MILP is too
   large?
5. **E2 check.** Verify CT at the extract rate with IFA at −20%/+15%: two pieces, one with RI,
   slack +78.7 m_rel (CONSOLIDATED, owner answers round 2).
6. **Verdict:** `ADOPT`, `ADOPT WITH CHANGES` (list each change), or `KEEP v2` (with the reason),
   and the lane structure you would file.

Do not cite a paper from memory. If you rely on a published method, name it and mark it
`claimed`.

Write it to `/tmp/iss/acb/review/report3-<fable|astra>.md` and show it in the chat.
