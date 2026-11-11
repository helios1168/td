"""Every SQL file under tools/snowflake/ starts with the session header (owner, 2026-10-31,
tools/snowflake/DATASET_LOG.md Key decisions "Session header"); files older than the rule are listed."""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "tools" / "snowflake"
HEADER = ["use role rl_ssdb_Integration_Lr_Strategy_Rw;", "use database ssdb_Integration;", "use schema lr_strategy;"]
OLDER = {"amer_holder.sql", "lpl_checks.sql", "override_review.sql", "profile.sql", "sales_crosswalk.sql",
         "schema.sql", "transfers.sql"}  # ponytail: these start with `use secondary roles all;`, before the rule


def test_every_sql_file_starts_with_the_session_header():
    bad = [str(p.relative_to(ROOT)) for p in sorted(ROOT.rglob("*.sql")) if p.name not in OLDER
           and [l.strip() for l in p.read_text().splitlines()[:3]] != HEADER]
    assert not bad, f"missing the session header: {bad}"
