Task: A1 repair turn 1, fix the concrete runtime defect in the FEFx audit core.
Directory: /Users/Shared/sv-ntlee/repos/td/.claude/worktrees/agy-math-review
Branch: worktree-agy-math-review
Mode: implementation
Read: agy-job/prompts/A1.md; agy-job/contract.md sections 1, 2, 9, 12, and 14; tools/measure/fefx.py; agy-job/reports/A1.json.
Owned files: tools/measure/fefx.py, agy-job/reports/A1.json. Do not edit any other source, test, documentation, model, ledger, or prompt file.
Dependencies: A1 initial implementation is reported complete but failed Luna validation.
Defect: In compute_envy_matrix, applicable pairs construct PairVerdict(..., reason=None, ...), then execute reason_counts[reason] += 1. This raises KeyError(None) on every normal applicable pair. Fix the accounting so applicable pairs do not index the not-applicable reason map, while preserving all reported counts and the PairVerdict reason contract.
Review adjacent edge cases while repairing: keep non-applicable reason counts exact; avoid division by zero when the retained roster is empty; preserve the explicit gain_matrix/masked semantics and legacy fairness anchor. Do not redesign APIs or change unrelated behavior.
Acceptance: run /Users/Shared/sv-ntlee/repos/td/.venv/bin/python3 -m py_compile tools/measure/fefx.py; directly execute a minimal applicable-pair call and the C0/Q0 toy cases; rerun the focused anchor checks if available. Update agy-job/reports/A1.json with the repair summary and exact tests. No confidential data rows.
Scope: This is an ad hoc TD job. No Beads, Helios, STATE.md, PLAN.md, or memories. Do not delegate further, commit, push, install dependencies, or change scope. Use apply_patch for edits, Serena for code reading/callers if available, and rtk for shell commands. Return the structured report as the final response.
