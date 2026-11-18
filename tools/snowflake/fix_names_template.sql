use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;
--Spelling fixes in the shortlist sheet channel_contacts.  new_fix_names.ps1 copies this template to data\safe\fix_names.sql
--(gitignored): fill in the names there, never here, then F5.  Per person, one UPDATE: the sheet's spelling (exact,
--case-sensitive, as sheet_unmatched.sql shows it) to the holder's spelling (any order or case).  REPLACE also fixes the
--name inside an "A or B" cell.  The last SELECT shows each new spelling and how many slots carry it.  Undo everything:
--CREATE OR REPLACE TABLE channel_contacts CLONE channel_contacts_backup
CREATE TABLE IF NOT EXISTS channel_contacts_backup CLONE channel_contacts;

UPDATE channel_contacts SET name = REPLACE(name, 'SHEET SPELLING 1', 'HOLDER SPELLING 1') WHERE CONTAINS(name, 'SHEET SPELLING 1');
UPDATE channel_contacts SET name = REPLACE(name, 'SHEET SPELLING 2', 'HOLDER SPELLING 2') WHERE CONTAINS(name, 'SHEET SPELLING 2');

SELECT name, COUNT(*) AS slots FROM channel_contacts
WHERE CONTAINS(name, 'HOLDER SPELLING 1') OR CONTAINS(name, 'HOLDER SPELLING 2')
GROUP BY name ORDER BY name;
