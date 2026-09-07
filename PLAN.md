# PLAN — workflow redesign

Track `worktree-workflow`. Designed 2026-09-07 with the user; this file is the brief for the
session that executes it. Design decisions here are settled unless `## Decisions needed` says
otherwise. This file is deleted in the last commit before merge (rule D2 below).

## Goal

Cut the markdown sprawl (92 files, 25,053 lines; docs/ took 116 of 283 commits in the last 30
days against 19 for `td/`) and make session handover mechanical. After migration, `docs/` holds
only files with a named owner, state lives in `STATE.md` plus one `PLAN.md` per worktree, and a
SessionStart hook prints the resume context so no session reads more than two sections to start.

## Next step

Migration step 0 (permissions and rule 9 amendment), then step 1, on Sonnet 5. Hand over to an
Opus 5 session for step 2, then back to Sonnet for steps 3 to 6 (decision 14). One commit per
step. Stop and report before merging; the merge to `main` needs the user's approval (see
memory `ask-before-merging-to-hub`).

## Done

- 2026-09-07 design agreed (this file). Memory `td-workflow-redesign-2026-09-07` records the
  decisions in short form.
- 2026-09-07 output style cleanup done in `~/.claude`: `Caveman Clean` retired, new `Caveman`
  style is the skill verbatim at level full with normal prose for persisted text; the skill's
  override paragraph removed; anti-slop rules moved to `~/.claude/CLAUDE.md` §10; the eleven
  `caveman-proxy native-hook` entries removed from `settings.json`. Not part of step 0.

## Decisions needed

None open. All fourteen items below were decided by the user on 2026-09-07; they are settled
inputs, not questions.

1. Tracks: derived at session start by hook from `git worktree list` plus each worktree's
   `PLAN.md ## Next step` first line. No static `## Tracks` table in STATE. STATE keeps one line
   per track only for status the hook cannot see (for example "blocked on sponsor").
2. `STATE.md ## Where` is dropped; `docs/CODE_MAP.md` owns "where".
3. Unit files get a `Status:` header line with values `open`, `done`, `dropped`. Dropped units
   keep the file with a one-line reason.
4. Both `PLAN.md` (running log of one worktree) and `docs/units/<id>.md` (permanent record) are
   kept. For a unit track, PLAN `## Goal` is one line pointing at the unit file.
5. PLAN template sections: `## Goal`, `## Next step`, `## Done`, `## Decisions needed`,
   `## Files owned / forbidden`. The last section moves over from `/unit`.
6. The last commit on a track deletes `PLAN.md` and writes the unit sections. Merge is
   fast-forward when possible.
7. Verifier artifacts live at `tools/verify/<id>/` as runnable scripts, committed, never in a
   scratch directory. They are not discovered by `tests/run_all.py` and never gate the suite.
   Rationale recorded: the runner discovers only `tests/test_*.py`; existing artifacts sit in
   `docs/artifacts/<id>/` (five units), `docs/verify/` (three sets) and, for U8-band, in a
   vanished `/tmp` directory; both agent specs said "scratch scripts, never in the repo tree",
   which is what lost them.
8. Owner allowlist lives in `.claude/doc-owners.txt`, read by a PreToolUse hook (Write/Edit) and by
   `tests/test_docs_owners.py`. The hook also rejects any edit under `docs/foundations/`.
9. `literature/territory_bibliography.{md,csv,bib}` is allowlisted; the three-format gap is a
   separate task.
10. `/state`, `/unit` and the three agents are global and change globally. No other project
    depends on STATE_LOG demotion or `MODEL_<id>.md` outputs.
11. `docs/CHANNEL_NOTE.md` is dead: settled facts fold into `docs/PROBLEM.md`, then the file is
    deleted.
12. Memory `ask-before-merging-to-hub` is updated: hub branch is `main`, and `docs/tracks/<ID>/`
    (now empty) is replaced by the PLAN rule.
13. Branch triage: `git branch --merged main` over the 19 `wt/*` and 5 orphan `worktree-*`
    branches. Merged ones are deleted in step 5. Unmerged ones are listed for the user; never
    deleted by the executing session.
14. Executor: background jobs inside this worktree, run sequentially, one commit per step.
    Model split decided 2026-09-07: Sonnet 5 (effort xhigh) runs steps 0, 1, 3, 4, 5 and 6;
    Opus 5 runs step 2 alone, because folding RESEARCH_FINDINGS, OPTIONS_*, REVIEW_GROMOV and
    CHANNEL_NOTE into PROBLEM and MODEL is the only step that needs judgment about what is
    settled versus superseded. Order: Sonnet steps 0 and 1, then Opus step 2, then Sonnet
    steps 3 to 6. Each session starts by reading this file and `## Next step`, and ends by
    updating `## Next step` and `## Done`. Merge asks first.

## Design

### D1. Living files and their owners

One topic, one file. A session that cannot name the owner in one breath has found a sprawl bug.

| File | Owns | Cap |
|---|---|---|
| `STATE.md` (hub only) | `## Now`, `## Next`, `## Facts` | Now 1 KB; Next 7 rows |
| `docs/PROBLEM.md` (renamed from `CHANNEL.md`) | settled facts about the business problem | none |
| `docs/MODEL.md` | settled facts about the model | none |
| `docs/CODE_MAP.md` | how to run anything; absorbs `RUNS.md` and `DATA.md` | none |
| `docs/APP.md` | the Streamlit scenario app | none |
| `docs/units/<id>.md` | brief, `## Model`, `## Verify`, `## Code verify`, `Status:` line | verifier sections hold verdict, artifact path, refutations only |
| `docs/foundations/` | FRAME, APPROACHES, LENS_*, DOMAIN_*, LIT_*, BRIEF, former `archive/` | read-only, never edited |
| `<worktree>/PLAN.md` | the one active plan of that track | committed on the branch; deleted at merge |
| `tools/verify/<id>/` | runnable verifier artifacts for unit `<id>` (scripts, oracles) | not test-discovered; cited from the unit file |
| `literature/territory_bibliography.{md,csv,bib}` | citations (bibliography skill) | none |
| `CLAUDE.md` | invariants, traps, environment | never stamped |

Deleted after folding: `docs/STATE_LOG.md`, all `MODEL_*`, `VERIFY_*`, `CODEVERIFY_*`,
`RESEARCH_FINDINGS.md`, `OPTIONS_*.md`, `REVIEW_GROMOV.md`, `CHANNEL_NOTE.md`, every
`*_PLAN.md` and `*_RESULTS.md`, `RUNS.md`, `DATA.md`, `.serena/memories/core.md`. Moved, not
deleted: `docs/artifacts/<id>/` and `docs/verify/` to `tools/verify/<id>/`, so `docs/` holds
markdown only.

Bugs and small todos live in code: an `xfail` test or a `TODO` comment at the site, found by
`pytest -rx` and `grep TODO`. `## Next` holds decisions plus the next unit only.

### D2. Handover protocol

Start of any session (hub or track):
1. The SessionStart hook prints `STATE.md ## Now`, the derived track list, the current worktree
   path, and the local `PLAN.md ## Next step` if present. Nothing else is required.
2. Pick a track. Work in its worktree. Activate Serena by absolute worktree path. Never read
   `docs/` from a sibling checkout.

End of a track session: update `PLAN.md ## Done` and `## Next step`; commit on the branch. Do
not touch hub `STATE.md`.

End of a hub session or after a merge: `/state` rewrites `## Now` (what landed, what it means,
next decision), prunes `## Next`, stamps, makes one `State:` commit, pushes. No demotion step.

Merge (hub session; ask first): the last track commit writes the unit sections and numbers into
`## Facts`, then deletes `PLAN.md`. After merge: unlock and remove the worktree, delete the
branch.

History recipe, replacing STATE_LOG:

```
git log --grep '^State:' -p -- STATE.md
```

`claude --resume` is for a same-day interrupt only. Anything crossing a day goes through `/state`
and the hook.

### D3. Memory stores: one per audience

| Store | Audience | Holds | Never holds |
|---|---|---|---|
| `CLAUDE.md` | every session, every agent | invariants, traps, environment | state, dates, narrative |
| auto-memory (`~/.claude/projects/<p>/memory/`) | the user across projects | preferences, corrections with the why, decisions git cannot show | anything a repo file records |
| `STATE.md`, `PLAN.md` | the next session | work state | preferences |
| `.claude/agent-memory/<agent>/` | one subagent type | lessons that agent keeps hitting; one file, 60 lines | project facts |
| `.serena/memories/` | nobody | dropped | |

Memory hygiene: entries that become `CLAUDE.md` invariants are deleted from memory
("Serena binds to hub", "★8 uncited" move to CLAUDE.md traps). Index under 12 lines.

### D4. Machinery changes

- `/state` (`~/.claude/commands/state.md`): drop the STATE_LOG demotion; enforce the two caps;
  refuse when `## Now` exceeds 1 KB; drop `## Where`.
- `/unit` (`~/.claude/commands/unit.md`): scaffold `docs/units/<id>.md` with `Status: open` and
  the three empty verifier sections, plus a `PLAN.md` from the template in decision 5.
- `modeler`, `math-verify`, `code-verify` (`~/.claude/agents/`): write into the unit file's
  section, not a new `docs/*_<id>.md`. The runnable artifact is committed under
  `tools/verify/<id>/`; the current "scratch scripts, never in the repo tree" instruction in
  both verifier specs is replaced, since it is what lost the U8-band evidence. Full reasoning
  goes into the artifact and git.
- Stages 1 to 4 (`/frame` … `/research-plan`) are unchanged and unused on td.
- Subagents for noisy work (inventory, grep sweeps, verifier runs) become a `CLAUDE.md` rule;
  only the verdict returns to the main context.

### D5. Hooks (project `.claude/settings.json`, scripts under `~/.claude/hooks/` in the existing
shell style with a test script)

| Hook | Matcher | Action |
|---|---|---|
| SessionStart | startup, resume, compact, clear | print `STATE.md ## Now`, derived track list, `$PWD`, local `PLAN.md ## Next step` |
| PreCompact | manual, auto | write a scratch snapshot (branch, `git status --short`, last test line) that SessionStart re-injects |
| PreToolUse Write/Edit | path under `docs/` | reject a new `docs/*.md` not in `.claude/doc-owners.txt`; reject any edit under `docs/foundations/`; reject `## Now` over 1 KB |
| Stop | — | if `docs/` or `td/` changed and neither `STATE.md` nor `PLAN.md` did, print a reminder (no block) |

Verify matcher names against current docs before writing (see `## Permissions and control`).

## Migration steps

One commit per step. Each step names its check. The executing session runs
`.venv/bin/python3 tests/run_all.py` from the repo root venv after steps 3, 4 and 6 (a worktree
has no `.venv`).

0. Permissions and rule 9 amendment (see `## Permissions and control`). Check: a fresh session
   in this worktree can run `git worktree add`, Write, Edit and `mcp__serena__*` without a prompt.
1. `git mv` FRAME, APPROACHES, LENS_*, DOMAIN_*, LIT_*, BRIEF and `docs/archive/` into
   `docs/foundations/`; fix citations in `docs/units/*.md`. Check: `grep -rn 'docs/\(FRAME\|APPROACHES\|LENS_\|DOMAIN_\|LIT_\|BRIEF\|archive\)' --include=*.md` returns only `foundations/` paths.
2. (Opus 5 session.) Rename `docs/CHANNEL.md` to `docs/PROBLEM.md`. Fold RESEARCH_FINDINGS,
   OPTIONS_*, REVIEW_GROMOV and CHANNEL_NOTE into PROBLEM, MODEL and `## Facts`; delete them.
   Fix references in CLAUDE.md, CODE_MAP, APP. The commit body carries a disposition table:
   every H2 of the four source files, with "kept in PROBLEM §x", "kept in MODEL §y",
   "number moved to Facts", or "dropped: <reason>". Check: no remaining `CHANNEL` reference;
   every H2 of the four deleted files appears in the disposition table.
3. Collapse `MODEL_*`, `VERIFY_*`, `CODEVERIFY_*` into `docs/units/<id>.md` sections; add
   `Status:` lines; `git mv docs/artifacts/<id>/` and `docs/verify/*` to `tools/verify/<id>/`
   and repoint every artifact path in the unit files. For U8-band, the unit file states that
   the `/tmp` artifacts are unrecoverable. Delete the source reports. Check: every former
   report's verdict line appears in its unit file; every cited artifact path exists; tests pass.
4. Delete `docs/STATE_LOG.md`. Rewrite `/state`, `/unit`, and the three agents. Rewrite `STATE.md`
   into the new shape; move each bug row of `## Next` to an `xfail` test or a `TODO` at the site.
   Fold `RUNS.md` and `DATA.md` into CODE_MAP. Check: `## Now` under 1 KB; `## Next` at most 7
   rows; tests pass.
5. Worktree and branch triage: unlock and remove merged or dead worktrees; delete merged
   branches; each live worktree gets a `PLAN.md`. List unmerged branches for the user. Check:
   `git worktree list` shows only live tracks plus the hub.
6. Hooks and allowlist: `.claude/doc-owners.txt`, the four hooks, `tests/test_docs_owners.py`.
   Refresh CLAUDE.md invariants (traps from memory, subagent rule, rule 9 amendment) and
   CODE_MAP. Retire `.serena/memories/core.md`. Update memory per D3 and decision 12. Check:
   zero orphans (every `docs/*.md` outside `foundations/` is named in `doc-owners.txt`);
   tests pass; a fresh session start prints the resume block.

Then: report, and ask before merging to `main`.

## Permissions and control

Three different things blocked the design session on 2026-09-07, and only the first is a
permissions prompt. Fix all three in step 0. Doc URLs are from a check on 2026-09-07; re-verify
exact syntax against the live page before writing settings.

**P1. Permission prompts.** Set `permissions.defaultMode` to `"bypassPermissions"` in
`~/.claude/settings.json` (user scope, so every project inherits it). Values documented at
https://code.claude.com/docs/en/permission-modes.md are `auto`, `default`, `acceptEdits`,
`bypassPermissions`, `plan`, `dontAsk`. `auto` is the current default on Max and routes actions
through a classifier, which is what produced the prompts. `bypassPermissions` skips checks;
managed settings can disable it via `permissions.disableBypassPermissionsMode`, which does not
apply to a personal machine. Keep a short `permissions.deny` list as the safety floor, since deny
outranks allow and ask: `rm -rf` outside the repo, `git push --force`, `git branch -D`, anything
under `~/Library/Mobile Documents`. The existing hooks (`enforce-file-tools.sh`,
`no-icloud-cwd.sh`) run in every mode and stay as guardrails. Precedence of settings files
(https://code.claude.com/docs/en/settings-reference.md): managed, then
`.claude/settings.local.json`, then `.claude/settings.json`, then `~/.claude/settings.json`.
CLI flags (`--permission-mode`, `--dangerously-skip-permissions`, `--allowedTools`) are
per-invocation and do not persist; do not rely on them.

Alternative if bypass feels too broad: stay in `auto` and add a `PermissionRequest` hook that
returns `{"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {"behavior":
"allow"}}}` for everything except a deny pattern. More moving parts; recommend P1 as written.

**P2. Rule 9 in `~/.claude/CLAUDE.md` forbade Claude from creating worktrees.** The reason was
data loss: worktrees created by `EnterWorktree` carry a marker in `.git/worktrees/<name>/` and
the periodic sweep removes them with their branch. The docs
(https://code.claude.com/docs/en/worktrees.md) confirm that worktrees created by plain
`git worktree add` are never auto-deleted. Amend rule 9 to: Claude creates every worktree with
`git worktree add .claude/worktrees/<name> -b worktree-<name>` followed by
`git worktree lock --reason "keep"`, never with `EnterWorktree(name)`, and enters it with
`EnterWorktree(path)`. This is exactly how `worktree-workflow` was created. Add
`"Bash(git worktree *)"` to `permissions.allow` if not running under bypass.

**P3. Background jobs reject edits in the hub checkout until the session is isolated.** This is
harness behaviour, not a setting. P2 resolves it: the session isolates itself.

**P4. The `rtk hook claude` PreToolUse hook rewrites `git` to `rtk git` and defeats the
worktree isolation guard.** The rewrite is a hook in `~/.claude/settings.json` (PreToolUse,
matcher Bash), not a shell alias. In a worktree-isolated background job the harness refuses any
Bash command whose git operand it cannot see through a launcher, so a plain `git commit` fails
with "runs rtk with a git command among its operands". Calling `/usr/bin/git` or `\git` to skip
the rewrite is then blocked by the `auto` mode classifier as evasion. Observed 2026-09-07 while
committing this file; the user committed by hand.

Measured from rtk's own `history.db` (2026-09-05 to 2026-09-07, 627 rewritten commands):
git accounted for 286 runs and saved 1,836 tokens in total, 16.2% of raw git output and 2.8% of
everything rtk saved; 192 of the 286 git runs saved nothing, 244 saved under 20 tokens, and
`git add` came out negative (34 raw, 446 shown). Two `rtk diff` runs alone saved 39.7K, so the
value of rtk is in `diff`, `ls` and `find`, not in git. The hook also logged 125 `ask` decisions
in three days (11 on git), and the rewrite turns an allowlisted `git status` into `rtk git status`,
which the `Bash(git status:*)` rule no longer matches; verify both in step 0.

Decided 2026-09-07 by the user: exclude git from rtk, keep rtk for the rest.
Fix: configure rtk to leave `git` alone (rtk `filters.toml` or the hook's exclusion list; check
`rtk hook --help`), keep it for `diff`, `ls`, `find`, `grep`. Then `"Bash(git *)"` in
`permissions.allow` matches again. Check: a background job in a worktree can run `git add`
and `git commit` without a prompt. Pushing stays with the user per the autoMode environment note.

**Hook facts confirmed** (https://code.claude.com/docs/en/hooks.md): `SessionStart` matchers are
`startup`, `resume`, `clear`, `compact`, `fork`; stdout on exit 0 is injected into context.
`PreCompact` matchers are `manual`, `auto`. `PreToolUse` can return
`"permissionDecision": "allow" | "deny" | "ask"` under `hookSpecificOutput`. Background
subagents and `-p` runs deny anything not allowed by rules or a `PermissionRequest` hook, so P1
also unblocks unattended jobs.

## Files owned / forbidden

Owned by this track: everything under `docs/`, `STATE.md`, `CLAUDE.md`, `.claude/settings.json`,
`.claude/doc-owners.txt`, `tests/test_docs_owners.py`, `tools/verify/`,
`~/.claude/commands/{state,unit}.md`, `~/.claude/agents/{modeler,math-verify,code-verify}.md`,
`~/.claude/hooks/*`, `~/.claude/CLAUDE.md` (rule 9 amendment only), the auto-memory directory.

Forbidden: `td/`, `app/`, `tools/` except `tools/verify/`, `battery/`, `figures/`, `data/`, any
`instance_descaled*`, any other worktree's files, push, force-push, merge to `main`.
