# Harness and tooling traps (AGENTS.md traps 15, 16)

The evidence behind `AGENTS.md` traps 15 and 16. Filed 2026-09-28 from td#54 ([comment](https://github.com/helios1168/td/issues/54#issuecomment-5866766796), m2 session 01a0e728 fork 01a0e738). The pre-#54 wording is `git show b7a74c9:AGENTS.md` traps 15 and 16.

- **Trap 15.** The archived solver harness (tag `archive/pre-support-2026-09`) keyed retries on the engine's own stop reason, `extra["retryable"]`, never on the status it reported to the harness. The new pipeline has no retry harness yet, and the rule carries over to the one it gets.
- **Trap 16.** Serena resolves relative paths against the hub, not the active worktree, so work in a worktree must pass absolute paths or use Read/Edit. This holds as long as Serena is started against the hub checkout.
