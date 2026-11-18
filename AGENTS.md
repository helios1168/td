# td: support-master territory design

Make the sales territory maps the owner will put in front of stakeholders: the main map and the
IFA map. In each planning channel, K_c districts cover every CONUS ZIP, and each district is **one
connected piece of territory on the drawn map** (M1, the reason the project exists), looks like a
sensible territory (few split states, no visual defects, compact) and is balanced (drawn $ in a
band around target). Method: a support-based master MILP, a ZIP realizer and an audited
`(ZIP, fine channel) → district` ledger. Staffing is out of scope. Everything before the 2026-09-28
clean slate is in the tag `archive/pre-support-2026-09`.

## Files

One file per question. Read `STATE.md` and the issue you were given first.

- `AGENTS.md` (this file): how to operate here, with the traps. Owner.
- `PROBLEM.md`: the goal, the mandates (M1, masking, T1) and every settled decision, one line each with its issue. Owner only. No step may weaken, relabel or work around a mandate without an owner-decision issue; `tests/test_mandates.py` parses its `## Mandates` section and fails an incomplete row or an expired deferral.
- `STATE.md`: five lines, written whole by the lander only.
- `docs/MODEL.md` (the method), `docs/CODE_MAP.md` (how the code works), `docs/RESULTS.md` (one dated entry per experiment, linking `results/`): implementer.
- `notes/<date>_<slug>.md`: handoffs and research, flat, write-once. `docs/archive/`: moved, never deleted, not read by default (old memory, lenses, problem briefs, rpiv artifacts).
- A decision's record is its issue's `DECIDED` comment; add its one line to `PROBLEM.md` when the owner closes it. A new doc needs no registry: say what question it answers or do not add it.
- `.okf/` is the memory store (sv-ntlee `docs/architecture/memory-store.md`). Entries change only through `okf` (stage, apply-verdict, owner-apply); the pre-commit hook enforces the gates. `/review` is the owner gate; `okf query` filters by state and kind. `docs/REFERENCES.md` stays until its citations are ACCEPTED.

## Environment

- `$TD_REPO` is the hub clone (`/Users/Shared/sv-ntlee/td`); `$TD_PY` is `$TD_REPO/.venv/bin/python3`. The system python has no numpy/scipy/networkx. A worktree has no `.venv`; use `$TD_PY` (the variables may be unset in a worktree shell: use the path).
- A worktree reads the gitignored inputs (`data/public/`, `instance_descaled*.json.gz`, `runs/`) from `$TD_REPO`; export `$TD_REPO` before running anything, or graph and map tests print SKIP lines.
- Only the `docs/figures/` that `docs/RESULTS.md` cites are tracked; regenerate a cited figure and commit it with the change.
- Background solver runs with `"$TD_PY" -u`. A script under `tools/<sub>/` that imports `td` puts the repo root on `sys.path` itself.
- One environment, `.venv`, from `requirements.txt`. Pin pyproj wherever plans are compared (3.7.2 and 3.8.0 build different ZIP graphs).

## Developer experience (the owner's work machine)

The owner runs everything on a Windows 11 work machine: PowerShell in Windows Terminal, Helix 25.07.1 (`[editor] shell = ["powershell", "-NoProfile", "-Command"]`), the repo cloned with `.venv` from `requirements.txt` plus `snowflake-cli`, the connection `[default]` in `%USERPROFILE%\.snowflake\connections.toml`.

- **Nothing is pasted from the agent's screen** (owner, 2026-11-18: "I cannot paste from here to my work computer, anything you need me to run needs to be a script which I got pull and run"). Every command, query or edit the owner runs is a committed file: tell them the one line to type, e.g. `:sh git pull` then `:sh .\tools\snowflake\<script>.ps1`, or "open `<file>.sql`, F5". No SQL, PowerShell or config snippets to copy.
- **SQL runs with F5 in Helix**: `F5 = [':write', ':sh .\.venv\Scripts\python.exe tools\snowflake\run_sql.py %{buffer_name}']`. `tools/snowflake/run_sql.py` runs the whole file in one session (Snowsight's Run All), shows the last result's first 50 rows in a popup and all of it in `data\safe\last.csv`, opens its Snowsight page if `data\safe\snowsight_url.txt` holds a query URL, and runs a `--then <path>` file after. The account's `ALLOW_ID_TOKEN` is false (no SSO token cache): `.\tools\snowflake\sql_session.ps1`, left open in its own pane, logs in once and F5 runs in that session; without it every F5 is a browser login. F6 (`:pipe … run_sql.py --stdin`) runs the selection in any buffer, a scratch one too, and puts the output under it as `--` comments, with no browser tab; a scratch line `--then data/safe/fix_names.sql` runs that file (and its own `--then`) with the output in the scratch buffer. It writes only stdout and exits 0: Helix shows stderr instead of stdout when there is any and hides a failing command's output.
- **The owner's work clone cannot push** (owner, 2026-11-18: "remember that I'm unable to push to the repo so there is no data leakage concern"): names in files or buffers on that machine leak nowhere. Masking still applies to everything that reaches the agent and to everything the agent commits.
- **The owner's own files go in the gitignored `data\safe\`**, which a clone does not have, so `git pull` never conflicts with them: a script creates the folder and copies a template there (`new_fix_names.ps1`). `.helix/ignore` shows it in Helix's picker and search.
- **What the owner sends back** is a masked result (`R<n>` keys, counts, fixed labels), uploaded as `data\safe\last.csv` right after the F5 that made it. A result with names stays on their screen: say which, every time.
- **PowerShell, not bash**: `New-Item -ItemType Directory -Force`, `Copy-Item`, `$env:VAR`; Windows Terminal splits with Alt+Shift+D. PowerShell treats `%` as `ForEach-Object`. Scripts cannot be run here: say what was and was not tested.

## Tests

`"$TD_PY" tests/run_all.py 2>&1 | rg -v '^\s*PASS '` from the repo or worktree root prints only the failures, SKIP lines and the summary. `run_all.py` has no per-test skip: a test that returns early counts as PASS, so read the SKIP lines. Do not wrap it in `rtk test`: rtk keeps only the last 5 lines, which can hide a FAIL.

## Git

- `gh` is for issues and labels. Git goes over SSH. Work on a topic branch; leave it committed and pushed.
- Share artifacts as GitHub web links (`https://github.com/helios1168/td/blob/<branch>/<path>`), not `file://` paths.

## Masking

- Sales and wholesaler (rep) names never enter this repo, an issue, a note or anything online. Firm and source names may (owner, 2026-11-09: "Firm/source names are fine. It's wholesaler names we must mask"). Wholesalers leave Snowflake only as the stable surrogates `R<n>` of `td_holder_key` (`tools/snowflake/02_model_extract.sql`), a table that never leaves Snowflake; the exporter's surrogates (`R…`, `F…`) are unchanged. The per-rep shares (`share`, `share_free`) and the `firm` map are sales data: the model does not use them and they never leave the extract.
- Not confidential (owner, 2026-09-30 and 2026-10-01): descaled opportunity (`m_rel`), opportunity in dollars, and everything the model makes from them (run output, ledgers, maps, per-ZIP values).

## Never weaken a mandate

Raise it with the owner instead of writing any of these about M1 or the settled frame: "listed", "reported", "tracked", "best effort", "for simplicity", "moot", "not required", "follow-up", a tolerance or threshold, or unit-level connectivity offered as settling the ZIP level. M1 was set aside that way on 2026-09-01 and every map shipped with detached pieces for five weeks.

- A check, test, fixture or scorer key may not start measuring something easier than the goal: no failure turned into a warning, no skipped or xfail'd test, no weakened fixture. Paths that need the owner's words: `PROBLEM.md`, `docs/MODEL.md`, `td/audit.py`, `td/realize.py`, `td/master.py`, `td/output.py`, `td/swap.py`, `tools/looks/`, `tools/mandates/`, `tests/`, `AGENTS.md`.
- A map is eligible, final, shippable or "the answer" only if it passes M1 and the settled frame. Report a piece with its τ share, never a bare count; a lower bound is not a feasibility claim ("13 splits is the minimum"); unit-level results are not ZIP-level.
- "M1" means only the contiguity mandate. Name a map by its shortlist id and label, never "M2" or "deck B". Cite an owner decision with the owner's words and the issue.
- A deferral needs an executable return trigger (a `tests/test_mandates.py::trigger_*`), and a cleanup or archive carries every mandate and settled row forward.

## Traps that still apply

Numbers are kept because code comments cite them (`trap 12`, `trap 18`); retired numbers are not reused.

12. `scipy.optimize.milp` defaults `mip_rel_gap` to 1e-4; pass `mip_rel_gap=0.0` for a certificate.
14. HiGHS 1.15 fails with "Solve error" under 1e-9 tolerances, and scipy 1.18.1's `linprog(method="highs")` can hang; pin `highs-ds` with an explicit `options` dict.
15. Key solver retries on the engine's own stop reason, never on a harness-facing status.
16. Serena resolves relative paths against the hub, not the active worktree; pass absolute paths, or use Read/Edit.
18. HiGHS's thread pool is process-global, sized by the first `threads` value a process uses; use one thread count per process.
19. A zero-objective feasibility solve is slower, not faster; never drop the objective to "just find a feasible point".
21. The ZIP graph's vertex set ships explicitly; never infer it from which ZIPs have a polygon or a cell.
22. All geography is 2025 vintage; never mix vintages or compare a number across them.
23. (Rewritten, [#118](https://github.com/helios1168/td/issues/118); the old wording called the Voronoi rook graph the contiguity model.) Contiguity is judged on the drawn 2025 ZCTA polygon rook graph plus the committed connectors (M1, [#57](https://github.com/helios1168/td/issues/57)); a district that looks scattered on the map is a failure, not an artifact. The display fill hides pieces: the ledger assigns every ZCTA.
24. Unit-level floors (split count, δ*) from a master with η > 0 do not bound M1 maps; label them "over 𝒳_c(δ) only".
