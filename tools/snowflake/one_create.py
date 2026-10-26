"""Write 25_union_opp_one.sql: the whole pipeline in one CREATE of UNION_OPP (owner, 2026-10-26), made from the step
files so the two cannot drift: mm_query_f2.sql statements 1, 2 and 7 (opp_base_both, opp_f2_final, firm_key) and
24_union_opp.sql statement 1, each step's table becoming a CTE.  The checks still read the step tables.

    python3 tools/snowflake/one_create.py [--check]     # --check: exit 1 if 25_union_opp_one.sql is stale
"""
import pathlib, sys

HERE = pathlib.Path(__file__).parent
T = 'ssdb_integration.lr_strategy.'
OUT = HERE / '25_union_opp_one.sql'


def between(s, start, end):
    i = s.index(start) + len(start)
    return s[i:s.index(end, i)]


def one(s, old, new):
    assert s.count(old) == 1, old
    return s.replace(old, new)


f2 = (HERE / 'mm_query_f2.sql').read_text().replace('\r\n', '\n')
s24 = (HERE / '24_union_opp.sql').read_text()

# statement 1: opp_base_both
b1 = between(f2, f'CREATE OR REPLACE TABLE {T}opp_base_both AS (\nWITH\n', '\n);\n\n--Statement 2.')
cut = b1.index('\n\nSELECT b.* EXCLUDE (dist_ch),')
s1 = b1[:cut] + ',\n\nopp_base_both AS (' + b1[cut + 1:] + '\n),\n'
# statement 2: opp_f2_final; its firm_2 opp_base is renamed, the query's own opp_base is above
b2 = between(f2, f'CREATE OR REPLACE TABLE {T}opp_f2_final AS (\nWITH\n', '\n);\n\n--Statement 3.')
b2 = one(b2, f"opp_base AS (SELECT * FROM {T}opp_base_both WHERE src = 'firm_2'),",
         "opp_base_f2 AS (SELECT * FROM opp_base_both WHERE src = 'firm_2'),   --one query: opp_base is statement 1's")
b2 = one(b2, '    FROM opp_base\n    WHERE original_cbd_id IS NOT NULL', '    FROM opp_base_f2\n    WHERE original_cbd_id IS NOT NULL')
cut = b2.index('\n\nSELECT opp_final.*,')
s2 = b2[:cut] + ',\n\nopp_f2_final AS (' + b2[cut + 1:] + '\n),\n'
# statement 7: firm_key
b7 = between(f2, f'CREATE OR REPLACE TABLE {T}firm_key AS (\nWITH\n', '\n);\n\n--Statement 8.')
cut = b7.index("\nSELECT 'CBD_ID' AS id_type,")
s7 = (b7[:cut].rstrip('\n') + ',\n\nfirm_key AS (' + b7[cut:] + '\n),\n').replace(f'{T}opp_f2_final', 'opp_f2_final')
# 24 statement 1: UNION_OPP
b24 = between(s24, f'CREATE OR REPLACE TABLE {T}UNION_OPP AS\nWITH\n', '\n\n-- Statement 2.')
b24 = b24.replace(f'{T}opp_f2_final', 'opp_f2_final').replace(f'{T}firm_key', 'firm_key')

sql = f"""use secondary roles all;

--Made from mm_query_f2.sql (statements 1, 2, 7) and 24_union_opp.sql (statement 1): a change goes in those files, not
--here.  The whole pipeline in one CREATE (owner, 2026-10-26): firm_2's
--opportunity file through the owner's firm_1 query steps (opp_base_both, opp_f2_final), the firm key (firm_key), and
--the join onto the union (UNION_OPP).  Needs at work: union_base, opp_original, crd_cbd_mm, crd_dist_override,
--crd_cbd, territories, synthetic_key and the vendor table.  The checks (mm_query_f2.sql 3-9, 24 statements 2-5) read
--the step tables: to check, run the step files instead.

CREATE OR REPLACE TABLE {T}UNION_OPP AS
WITH
{s1}
{s2}
{s7}
{b24}
"""
sql = sql.replace('\n', '\r\n')    # CRLF, as the owner's query files
if '--check' in sys.argv:
    sys.exit(0 if OUT.exists() and OUT.read_bytes() == sql.encode() else 1)
OUT.write_bytes(sql.encode())
print(OUT.name, sql.count('\n'), 'lines')
