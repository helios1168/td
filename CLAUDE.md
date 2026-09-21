@AGENTS.md

# Claude only

The main Claude session is the orchestrator: it plans, dispatches, reviews, verifies, merges and
keeps memory. Codex implements.

## Orchestration

1. Plan the change.
2. Write one bead per step with the `files`, `test` and `memories` metadata (plus `unit`,
   `accept`, `author` and the labels in `AGENTS.md`).
3. Dispatch implementation with `bd-codex <ids>`, in waves; the beads of one wave own disjoint
   file sets.
4. Run `verify math <unit>` or `verify code <unit>`; by default the verifier is the agent that
   did not author the work.
5. Review each diff: `git diff --stat` first, then file by file.
6. Merge the branch into `main` once its verify bead closes; then unlock and remove the worktree
   and delete the branch.
7. Curate Serena memories from each run's `LEARNED:` lines.
8. Keep `STATE.md` `## Now` current.

## Subagents

Noisy work (inventories, grep sweeps, verifier runs) goes to a subagent; only the verdict returns
to the main context.

## Plans

Every plan ends with an `## Execution` section: the model per step, the waves with their disjoint
file sets, and the long pole, started first.
