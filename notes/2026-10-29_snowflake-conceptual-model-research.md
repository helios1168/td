2026-10-29 · m5-studio/snowflake-safe-dataset · 3116d2d · Agent: session (claude-opus-5-5)

# Research: the conceptual model of the opportunity and sales analysis (three gromov passes)

**Question.** Before rebuilding the analysis from scratch (owner, 2026-10-29), what are its objects, maps and
invariants, and which words hide decisions? **Result:** `tools/snowflake/DATA_MODEL.md`; its undefined symbols are
`DATASET_LOG.md` Q27-Q31. The owner's and the stakeholder's words are quoted in the log's 2026-10-29 entry.

## Method

The `gromov` agent (a reframing lens that returns objects, suspect words, named unknowns and questions, never
solutions) ran three times. Models checked in each run's meta file.

| run | model | brief |
|---|---|---|
| `4e4a955a` | `claude-bridge/claude-opus-5-5:xhigh` (agent file) | history: the session's facts, `mm_query.sql` and `DATASET_LOG.md` to read, the session's draft model to audit |
| `c1149443` | `openai-codex/gpt-6-astra:max` (owner asked for Astra) | the same brief |
| `251b277b` | `openai-codex/gpt-6-astra:max` | fresh: the situation, the stakeholder, the owner's corrections, the bare shape of the data; no files, rules or draft (the owner asked for a run free of history) |

The session checked four of run 1's line citations into the owner's query (`mm_query.sql:420`, `:691`, `:706`,
`:718`): each says what run 1 claims.

## What all three found (so not an effect of the history)

- "Channel" is several objects: a label on a sale, the vendor's classification, a split of the market, a team.
- "Firm" mixes the insurer and the distributor; the distributor's unit is undeclared, and hiding firms in reports
  does not remove firm-dependent routing.
- A territory is coverage, a relation with 0, 1 or 2+ holders, not exclusive geography.
- "Opportunity" is estimated market sales, not business anyone can necessarily win.
- Where a sale is placed is not who is credited with it.
- The central gap: a new channel × ZIP reaches no fixed territory, because the territory tables are keyed by current
  channels (run 1: "a new channel has no rows unless someone builds them"; run 2: "unproved arrow: channel change →
  holder change"; run 3: "new channel × ZIP does not determine a fixed legacy territory or wholesaler").
- Market share needs sales and market on the same cells; a seller's credit ÷ a holder's market does not have that.

## Found only without history (run 3)

- The market has to be held fixed between the states, so "op moves" measures reclassification alone (I4).
- The data name who was credited with a sale, not who caused it.
- The current state is two classifications (one per source firm); the new state is one.
- Product may change a distributor's channel.

## Found only with history (runs 1 and 2): evidence from the code

- A sale's current label can depend on its seller: an IFA sale becomes IMO when the seller sits in an IMO sales
  district (`mm_query.sql:420`).
- The source region table has territories tied to one distributor, filtered out of the owner's query
  (`mm_query.sql:691`); it bears on whether National is covered by ZIP or by distributor.
- The new-state holder lookup of the owner's query joins on the current label (`mm_query.sql:718`).
- The "larger estimate" rule sets the amount, not which estimate's channel label wins.
- "No holder" has three causes: unknown distributor, no translation, no coverage.
- The lowest-ID tie-break between 2+ holders decides rankings without anyone stating it.
- Two rankings: contribution ranks sellers, territory share ranks holders; they can name different people.

## How the model used them

Sets and measures from runs 1 and 3; the maps κ_s, λ_s, ν, H_s, k_s and τ_s from runs 1 and 2 (λ_s from run 1's
seller-dependent labels); "a state is a set of channel definitions applied to the same data" from the session's
answer to the owner; I1 and I2 from the owner, I3 from the stakeholder, I4 from run 3; the vocabulary from all three.
Not taken: run 1's "share ranks territories, contribution ranks sellers" as a rule (left open, Q31).

The questions the runs returned are in the index as Q27-Q31; run 3's "which estimate and coverage stay frozen" is I4.
The runs' full outputs were in that session's subagent artifacts only.
