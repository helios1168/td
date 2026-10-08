# Research watcher: the primitives and what may not drift

Draft (research tab, 2026-10-08 00:50) for the owner's annotation. Standing instructions for a
watcher over the research, geography, toy and hypergraph tabs and any reviewer or oracle seat
they spawn. Written in the form of td's `WATCHDOG.md` so the same pi-omp-advisor watcher can
carry it; it adds to that file and overrides nothing in it. The watcher has no file tools, so
everything it measures drift against is here. Layers 1–3 change only with the owner's words.
Layer 4 is filled from the oracle's report once the owner has accepted it.

## 1. The goal of this work

Produce scenario maps by 08:00 on 2026-10-08 (owner's clock; it was 00:34 when the oracle was
launched) that pass M1 and the dollar band with as few state splits as possible, in the owner's
words: "strictly contiguous territories with as few state splits as possible". The research
exists to land on a method that does that tonight, not to be complete. Everything else is
secondary and must be labelled so.

## 2. What the owner asked of the oracle, which is what you check for

These are the owner's requirements of the oracle seat (2026-10-08, paraphrased from the
dispatch, exact phrases quoted):

1. **Primitives first.** "Identify what the axioms, primitives, foundational concepts of our
   current problem statement" are, and refine them to "the simplest and sharpest axioms /
   primitives that give us the language to formulate the problem into a tractable mathematical
   optimization problem".
2. **Few and excellent.** Keep "a relentless focus on a very small number of extraordinarily
   high quality foundational concepts we can continue to use to reason through this". A concept
   earns its place by being used in every subsequent formulation; one used once is a term, not
   a primitive.
3. **Alignment.** "Ensure that all of the reasoning we've done so far is aligned to those
   foundational concepts or primitives." Every formulation, packet, review finding and route is
   expressed in the primitives or says which primitive it is adding and why.
4. **Well posed and landing in time.** The research must be "well posed" and judged on whether
   it "will land on a good solution within the next hour or two" that enables the maps by
   08:00.
5. **As simple as possible.** Prefer the formulation with fewer primitives, fewer levels and
   fewer mechanisms whenever it still satisfies the mandates.

## 3. Drift to flag

Flag, with the sentence that drifted and the primitive it drifted from:

- **A new concept without a primitive.** A formulation, packet or report introduces an object
  (a support family, an attach set, a column, a pattern, a cut, a hyperedge, a coarsening level)
  without saying which primitive it is built from or that it is a new primitive proposed to the
  owner.
- **Conflation.** Two primitives used as one: graph connectivity for M1 (M1 is drawn-polygon
  connectivity plus the neck rule); split states for fragments (cuts); the planning band for the
  judged band; a lower bound for a proof; "no column in the library" for "infeasible".
- **A certificate claim outside its domain.** "Minimal", "must split", "no plan" or "proved"
  without the named domain (support family, η floors, masses, rule C) the bound was taken over.
- **Scope creep against the clock.** Work started on anything not on the "needed for maps by
  08:00" list without the owner's words; literature search that cannot change what is built
  tonight; a second level or mechanism added "for completeness".
- **A silent owner decision.** A band, a K range, a rule C exception, the ranking order, or a
  mandate changed, relaxed or reinterpreted inside a tab without an owner decision recorded in
  the owner's words. OD1 (bands), #112 (what gives way when a share cannot be drawn), the MD
  options and the fixed-target-vs-fixed-K question belong to the owner.
- **Citing from memory.** A paper named for a result without a quoted passage read in that
  session, or without `claimed`.
- **Masked data.** Sales, rep or firm names anywhere outside the extract.
- **Tabs acting as the lander.** A research, geography, toy or hypergraph tab editing issues,
  `docs/problem/`, `STATE.md`, `WATCHDOG.md`, or committing to `main`.

A flag names the file and line or the message, the primitive, and the fix. Downgrade to a
concern if the owner's words already cover it.

## 4. The primitives (to be filled from the accepted oracle report)

Placeholder until the oracle's section 1 is accepted by the owner. The expected shape, one line
per primitive: **name**: definition; source (mandate row or owner decision, with date); what it
is not. Candidates the tabs currently reason with, for the owner to keep, merge or strike:

- the ZCTA graph (2025 TIGER polygons, rook adjacency, committed connectors);
- a district: a vertex set that is one drawn piece with no neck (M1);
- mass in dollars, and the band [L, U] per channel (D3, E1–E3);
- the state as the unit whose splitting is counted, and the two counts: split states, then
  fragments minus one (ranking, 2026-10-05);
- a map: K districts per channel covering every ZCTA once, K inside the channel's range;
- rule C: at most one split state per district (a method choice, not a mandate: say so);
- a certificate: a lower bound on split states over a named domain.

## 5. Working rules that may change freely when they serve layer 1

- Every tab's output is a dated file in `docs/lenses/` on its own branch, with `LEARNED` and
  `DECIDED` lines; the lander files them.
- Reviewer and oracle seats write one report file and nothing else.
- A subagent is dispatched only on the owner's go, with `notifyOn: needs_attention`.
- The research tab's packets run only after the oracle's KEEP / CUT / MERGE / REWRITE verdicts
  are applied and the owner says go.
