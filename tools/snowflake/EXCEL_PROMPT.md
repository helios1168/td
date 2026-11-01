# Excel workbook from the run's CSV (Microsoft 365 Copilot in Excel)

Answers: how to turn `01_opportunity_sales.sql`'s one CSV into a workbook a stakeholder can decide from (checks,
summary, the manual-assignment worklist, candidates, opportunity views, and the rows to paste into statement 8).

## Before pasting

1. Data → From Text/CSV → Transform Data. Set `ITEM`, `ITEM2`, `SALES_FIRM_ID`, `MGA_AGENT_CD`, `TOP_WHOLESALER_ID`,
   `CAND_FIRM_CRD` to Text (Excel otherwise drops leading zeros and turns MGA codes into numbers; a manual assignment
   applies only when its key matches as text).
2. Load to a table named `Extract`; save the file to OneDrive or SharePoint.

## The prompt

```
The table Extract is one result set from a territory-realignment analysis. Build the workbook below so a stakeholder can review results and decide manual firm assignments. Follow the rules exactly.

STRUCTURE: LAYER and PART say what a row is. LAYER = OPPORTUNITY, SALES or REVIEW. SOURCE = S1 (firm 1) or S2 (firm 2): two separate firms, never add them together.
- OPPORTUNITY parts: V1 CHANNEL (opportunity $ by channel; NAME = CURRENT or NEW state), V2A RECLASSIFIED (ITEM = "old -> new" channel), V2B HOLDER MOVES (ITEM = what happens to the wholesaler holding the cell; ITEM2 = territory channel old -> new), V3 COVERAGE (NAME = state), CHECKS.
- SALES parts: SALES FIRM BASIS (ITEM = how a sale was matched to a market metrics firm), SALES ON CELLS, SALES CHANNEL, SALES PRODUCT, WHOLESALERS, Q35, SALES PERIOD, TIE-OUT, CHECKS.
- REVIEW parts: REVIEW (manual-assignment worklist), SUMMARY, CHECKS.

RULES:
1. AMT is dollars; show as $MM, 1 decimal. OPPORTUNITY AMT is opportunity $, SALES and REVIEW AMT is sales $: never add the two.
2. Each PART is the same dollars cut a different way: never sum across PARTs; within a part, filter NAME when it has values (e.g. CURRENT vs NEW).
3. REVIEW/REVIEW rows: one row per review key x candidate firm. Key = SOURCE, SALES_FIRM_ID, SALES_FIRM, RAW_CHANNEL, MGA_AGENT_CD. AMT is filled only on RANK_IN_KEY = 1 rows, so SUM(AMT) counts each key once. KEY_AMT repeats on every candidate row: never sum it.
4. Candidate evidence (1/0): EV_COMPANY, EV_CHANNEL, EV_MM_MAP, EV_CRD_TO_CBD, EV_NAME; ZIP_AMT = the key's $ sold where the candidate has opportunity; SCORE = match strength 0-6; RANK_IN_KEY 1 = strongest.
5. CHECKS rows whose NAME contains "MUST BE 0" must show 0 in AMT, N_FIRMS and N_ROWS (some keep their value in N_FIRMS). Other CHECKS rows are informational.
6. Ignore AMT_ALT.

BUILD THESE SHEETS:

A. "Checks": Extract rows where PART = "CHECKS" and NAME contains "MUST BE 0": LAYER, SOURCE, NAME, AMT, N_FIRMS, N_ROWS. Add STATUS = "OK" if AMT, N_FIRMS and N_ROWS are all 0 or blank, else "FAIL"; FAIL rows red. A1: a formula showing "ALL CHECKS PASS" or "n CHECKS FAIL".

B. "Decisions": an Excel table named Decisions from Extract rows where LAYER = "REVIEW", PART = "REVIEW" and RANK_IN_KEY = 1, sorted by SOURCE, then KEY_AMT descending. Columns: SOURCE, SALES_FIRM_ID, SALES_FIRM, RAW_CHANNEL, MGA_AGENT_CD, FIRM_BASIS, MATCH_CHANNEL, NEW_LIST_LABEL, TOP_WHOLESALER_ID, N_WHOLESALERS, KEY_AMT ($MM), N_CANDIDATES, CAND_FIRM_CRD, CAND_BROKER_NAME, CAND_ROUTE, SCORE. Add:
- CUM_PCT: running share of the source's KEY_AMT in this sort order (as values).
- SCORE_2: the SCORE of the same key's RANK_IN_KEY = 2 row in Extract (blank if none); TIE = "TIE" when SCORE_2 = SCORE; TIE rows yellow (rank 1 is arbitrary there).
- Editable: DECISION (dropdown: ASSIGN, LEAVE UNMAPPED, SKIP), CHOSEN_CRD and CHOSEN_NAME (prefilled as values with CAND_FIRM_CRD and CAND_BROKER_NAME, editable), ANY_CODE (dropdown Y/N, default N; Y = every MGA code of this firm and channel), COMMENT.
- SQL_ROW with exactly this formula:
=IF([@DECISION]<>"ASSIGN","","  ('"&[@SOURCE]&"', "&IF([@SALES_FIRM_ID]="","NULL","'"&[@SALES_FIRM_ID]&"'")&", "&IF([@SALES_FIRM]="","NULL","'"&SUBSTITUTE([@SALES_FIRM],"'","''")&"'")&", "&IF([@RAW_CHANNEL]="","NULL","'"&[@RAW_CHANNEL]&"'")&", "&IF(OR([@ANY_CODE]="Y",[@MGA_AGENT_CD]=""),"NULL","'"&[@MGA_AGENT_CD]&"'")&", '"&[@CHOSEN_CRD]&"', '"&SUBSTITUTE([@CHOSEN_NAME],"'","''")&"'),")
Freeze the header row and first three columns; slicers for SOURCE and FIRM_BASIS.

C. "Candidates": all Extract rows where LAYER = "REVIEW" and PART = "REVIEW": SOURCE, SALES_FIRM_ID, SALES_FIRM, RAW_CHANNEL, MGA_AGENT_CD, KEY_AMT ($MM), RANK_IN_KEY, CAND_FIRM_CRD, CAND_BROKER_NAME, CAND_ROUTE, EV_COMPANY, EV_CHANNEL, EV_MM_MAP, EV_CRD_TO_CBD, EV_NAME, ZIP_AMT ($MM), SCORE. Sort by SOURCE, KEY_AMT descending, the key, RANK_IN_KEY. EV_ cells green when 1; data bar on SCORE; a light border between keys. Slicers: SOURCE, FIRM_BASIS.

D. "Summary": pivot tables from Extract, values SUM(AMT) in $MM and % of column total, SOURCE as columns, one SOURCE slicer connected to all:
1. PART = "SALES FIRM BASIS"; rows ITEM. Add a stacked bar chart per SOURCE.
2. LAYER = "REVIEW", PART = "SUMMARY"; rows FIRM_BASIS then ITEM; also SUM(N_KEYS).
3. PART = "SALES ON CELLS", NAME = "CELL"; rows ITEM.
4. PART = "TIE-OUT"; rows NAME, columns ITEM (year); plus a cell with sales table minus dataset for 2025 (must be 0).

E. "Opportunity": pivot tables from Extract where LAYER = "OPPORTUNITY", SUM(AMT) in $MM, each with a SOURCE filter (never both sources together):
1. PART = "V1 CHANNEL": rows ITEM, columns NAME (CURRENT, NEW), plus NEW minus CURRENT.
2. PART = "V2A RECLASSIFIED": rows ITEM; % of total.
3. PART = "V2B HOLDER MOVES": rows ITEM, then ITEM2.
4. PART = "V3 COVERAGE": rows ITEM, columns NAME.

F. "Export": A1 = TEXTJOIN(CHAR(10),TRUE,Decisions[SQL_ROW]) with wrap text; A3 note: "Paste A1 into statement 8 of 01_opportunity_sales.sql, above the placeholder line, then rerun."

Put the sheets in the order Checks, Summary, Decisions, Candidates, Opportunity, Export. When done, list anything you could not build.
```

When the result's columns change, update this prompt in the same commit.
