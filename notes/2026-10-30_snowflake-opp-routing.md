2026-10-30 · m5-studio/snowflake-v2 · c43bdd4 · Agent: session (claude-opus-5-5)

# Opportunity routed by firm: the profile, the route, what is open

Picks up from `notes/2026-10-30_snowflake-v2-start.md`. The owner set the first deliverable: opportunity, routed by firm
on the market metrics schema, both sources; sales later. Read `tools/snowflake/DATASET_LOG.md` (Conventions, Settled,
the index and every 2026-10-30 entry) and `tools/snowflake/DATA_MODEL.md` (Opportunity routed by firm) first.

## Tasks

- Done: the owner's two queries saved verbatim and hash-pinned in `$TD_REPO/owner_sql/` (`s1_sales.sql`,
  `s1_opp_sales.sql`; git-excluded), each logged with line-cited findings; `mm_query.sql` is superseded.
- Done: the schema run (18 tables) logged; the carrier-named tables are `SET` variables, real lines in
  `owner_sql/vars.sql`.
- Done: Q6 settled (one set of new channels, firm 1's, routed by firm 1's channel per market metrics firm); UNMAPPED
  settled for opportunity with no firm 1 channel; Q19 reopened with the real labels; Q40 closed by the data.
- Done: `explore/profile.sql`, first run (`data/safe/profile_2026-10-30-0324.csv`): CRD and broker name full in both
  sources; one firm 1 channel per CRD x broker name; 99.71% of source 2's $ routes at ZIP x CRD x broker name.
- Partial: `explore/profile.sql` now applies firm 1's rules (`tmp_s1_channel_rule`) and compares the firm-level route
  with `crd_dist_override`; tested in DuckDB (62 checks), not yet run at work.
- Not started: the master firm table and the opportunity cell table per source (layer `01`); views 1, 2a, 2b, 3.

## Critical references

- `tools/snowflake/DATASET_LOG.md`: Conventions (table variables, one result, masking scope), Settled, Q19-Q39.
- `tools/snowflake/DATA_MODEL.md`: Opportunity routed by firm, one row per step and source.
- `tools/snowflake/explore/profile.sql` and `explore/profile_test.sh` (`sh explore/profile_test.sh`).

## Changes

- `tools/snowflake/DATASET_LOG.md:20`: Table variables and One result conventions; Masking scoped to `tools/snowflake/`.
- `tools/snowflake/DATASET_LOG.md:100`: the open index after housekeeping (Q6, Q40 gone; Q19 back).
- `tools/snowflake/DATA_MODEL.md`: the distributor key table, the ν, ρ_s, I3 rows, and the Opportunity routed by firm
  section carry the profile's facts and the owner's route.
- `tools/snowflake/explore/profile.sql`: statements 1-8, opportunity only (the sales half is in `73774ed`).
- `tools/snowflake/README.md`: points to Conventions; lists `explore/` and `owner_sql/`.

## Learnings

- The owner's files at `/tmp` are unreadable from the sandbox; ask for `cp` (not `mv`) into `$TD_REPO/data/safe/`, whose
  inherited ACL gives read access.
- Firm 1's `DIST_CH` is the vendor's `CHANNEL` code renamed (01 IFA, 13 the one-firm label, 11 split into FI and WH,
  08 / 10 / NO CHANNEL blank); its only in-house step there is the FI / WH split.
- The one-firm channel's label comes from `s1_opp_sales.sql:468` (opportunity) and `:678`, `:692` (company 3's own
  regions); the sales query has no rule for it.
- Masking here: never a person's name, never sales $ tied to a firm name; firm names may stand in SQL; carrier names
  only through `SET`. Scoped to `tools/snowflake/` only.
- The DuckDB harness pipes `profile.sql` through `sed` (drops `use`, `SET`, `TEMPORARY`; maps `IDENTIFIER($...)` to
  fixture tables); expected values are worked out by hand, and one mutation per new rule proves the check bites.

## Next steps

1. Owner runs `explore/profile.sql` (paste the `SET` lines from `owner_sql/vars.sql`), copies the CSV into `data/safe/`.
2. Read `S1 ROUTE (CRD X NAME)`, `S2 ROUTE (CRD X NAME)`, `... VS OVERRIDE`, `OVERRIDE TABLE KEYS`; settle Q38 with the
   owner (route level; the override's role).
3. Q19 (source 2's label pairs; NO CHANNEL kept or dropped) and Q39 (source 2 territory channel per firm 1 channel).
4. Build the master firm table (CRD x broker name -> firm 1 channel, override, UNMAPPED, the new-channel list re-keyed
   from company IDs) and each source's opportunity cell table, one result set with checks; test in DuckDB.
5. Views 1, 2a, 2b, 3 for opportunity.

## Open owner decisions

- Q38: route per CRD x broker name or per ZIP x CRD x broker name; where the override differs, which wins.
- Q19, Q39: the source 2 label and territory pairs; NO CHANNEL.
- Q29: who holds new channels such as National. Q36: source 2's period. Q34: stack, do not join (kept open).
