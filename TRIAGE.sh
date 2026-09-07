#!/bin/sh
# Step 5 triage: commands the worktree-isolation guard refused in this session. Run these by
# hand from the hub (/Users/ntlee/projects/td) or as noted. Deleted at merge, like PLAN.md.
set -e

# Group 1: worktree status checks refused ("-C <path>" redirects git outside this worktree).
# All nine live sibling worktrees have unknown dirty status; the six whose branch is merged
# were left in place rather than removed, since a worktree with unknown status is never
# removed. Run each; a clean status on a merged one clears it for
# `git worktree unlock <path> && git worktree remove <path> && git branch -d <branch>`.
git -C /Users/ntlee/projects/td/.claude/worktrees/app-review status --short          # branch worktree-app-review, merged
git -C /Users/ntlee/projects/td/.claude/worktrees/ca5-map status --short             # branch worktree-ca5-map, UNMERGED (2 ahead) -- never remove
git -C /Users/ntlee/projects/td/.claude/worktrees/channel-note-md status --short     # branch worktree-channel-note-md, merged
git -C /Users/ntlee/projects/td/.claude/worktrees/headline status --short            # branch worktree-headline, UNMERGED (4 ahead) -- never remove
git -C /Users/ntlee/projects/td/.claude/worktrees/motion status --short              # branch worktree-motion, merged
git -C /Users/ntlee/projects/td/.claude/worktrees/power-cell-contiguity status --short  # branch worktree-power-cell-contiguity, merged
git -C /Users/ntlee/projects/td/.claude/worktrees/state-atoms status --short         # branch worktree-state-atoms, merged
git -C /Users/ntlee/projects/td/.claude/worktrees/state-table-align status --short   # branch worktree-state-table-align, UNMERGED (1 ahead) -- never remove
git -C /Users/ntlee/projects/td/.claude/worktrees/vbl status --short                 # branch worktree-vbl, merged

# Group 2: PLAN.md writes into sibling worktrees, refused (Write/Edit outside this worktree).
# The finished files were written to the fallback path below instead; copy each into place.
# ca5-map and state-table-align had no PLAN.md and were untouched by any other session during
# this triage -- safe to apply as drafted.
cp /Users/ntlee/.claude/jobs/b313fd3c/tmp/plans/ca5-map.PLAN.md /Users/ntlee/projects/td/.claude/worktrees/ca5-map/PLAN.md
cp /Users/ntlee/.claude/jobs/b313fd3c/tmp/plans/state-table-align.PLAN.md /Users/ntlee/projects/td/.claude/worktrees/state-table-align/PLAN.md

# headline/PLAN.md is NOT included here: while this triage ran, worktree-headline picked up
# three new commits from a concurrent session (89b44e9 -> 5ec4872, "Plan: what the override
# work found, and where it stands"), which rewrote PLAN.md with live content. The draft this
# session prepared (/Users/ntlee/.claude/jobs/b313fd3c/tmp/plans/headline.PLAN.md, built from
# the stale 89b44e9 tree) would clobber that work and is deliberately NOT copied. Current
# headline/PLAN.md has `## Status`, `## What the override does`, `## Findings`, `## Open`,
# `## Constraints that still bind` -- not the decision-5 template (`## Goal`, `## Next step`,
# `## Done`, `## Decisions needed`, `## Files owned / forbidden`). If the template headers are
# still wanted, add only the missing ones by hand once that session is done; do not overwrite.
