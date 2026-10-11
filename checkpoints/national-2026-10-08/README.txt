WIP checkpoint: national / main-map reconnaissance, 2026-10-08
Saved for Pi setup replacement, 2026-10-11. Related issue: td#105.

This is an artifact-only checkpoint, NOT a landable implementation. Do not
merge this old branch wholesale into main: source HEAD f11faed is the Oct 8
scout snapshot and includes superseded policy text and an inert G1 prototype.
No repair code, solver jobs, geometry gates, new maps or presentation package
were produced. main, STATE.md, mandates, issue bodies and memory were not edited.

artifacts.tar.gz preserves 9 original drafts/audit files and 8 scout reports:
- scout plan, historical intake, corrected findings, repair proposal;
- dollar-audit script, v1 and authoritative v2 JSON/CSV;
- scouts/{history-decisions,national,wh,fi,wifi-combined,map-inventory,
  live-state,presentation}.md.
DONOR_STDOUT.txt preserves the final approved measurement's original stdout.

Primary readout: td-main-map-scout-findings-2026-10-08.md.
Authoritative dollars: td-main-map-dollar-audit-2026-10-08-v2.{json,csv}.
The v1 FI upper-edge float representation is superseded; flags/dollars did
not change. Source/audit-script hashes are recorded in v2. The archived
script has absolute historical paths and refuses to overwrite output;
do not execute it blindly on today's source/data.

Important supersession: WIFI IS the combined channel and E3 applies at
+/-15% of its global dollar mean (main 1293d41). Older archived scouts/intake
contain an erroneous exemption. They are untrusted historical evidence,
not current policy. The findings and proposal carry the correction.

Historical pause point: both audited seeds have national 13/15, WH 10/11,
FI 20/20, WIFI 3/3 in dollar band. The same three districts fail:
national_01 deficit about $48.415M; national_09 $39.659M; WH_09 $9.230M.
Full M1/shape eligibility was not freshly checked or claimed. Originals
were fingerprinted unchanged. No map was promoted or chosen as final.

Proposed (NOT authorized) next work: fixed-K WH whole-state regroup across
WH_08/09/11 and national donor regroup plus Florida rebalance across
national_01/09/12. Need current design reconciliation, owner execution
approval, solver allocation and bounded budget. No automatic expansion,
K/band/cap change or IFA prototype flag. Main solver allocation was zero
at the Oct 8 pause; do not treat that as current machine staffing.

Private extract and ignored original run/renderer assets are intentionally
not included. No sales/share/firm data is archived. The original run paths
and input hashes are in the readout/audit. Restore required inputs only
through approved paths; never refresh the 58 owner-accepted old renders.

Checkpoint validation: archive byte identity/member inventory; JSON/CSV
structure and recorded script hash; script AST parse; git diff --check.
No solver, map gate, rendering or application audit rerun is part of saving.
