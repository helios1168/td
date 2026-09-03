#!/usr/bin/env bash
# Per-track worktree setup, run by `helios new <id>`: tools/track-setup.sh <id> <charter.md> <worktree>
# Writes the git-ignored CLAUDE.local.md charter and links the shared .venv. Idempotent.
set -euo pipefail
id=$1; charter=$2; wt=$3
root=$(git -C "$wt" rev-parse --path-format=absolute --git-common-dir | sed 's#/\.git$##')

[ -e "$wt/.venv" ] || ln -s "$root/.venv" "$wt/.venv"

cat > "$wt/CLAUDE.local.md" <<EOF
# Track \`$id\` — charter (git-ignored, written by helios; edit the source in the hub's docs/APPROACHES.md)

This worktree is **one research track**: one methodology family applied to the problem in
\`docs/FRAME.md\`. Several tracks run in parallel from the hub branch \`national-channel\`; the
hub compares them in \`docs/TRACKS.md\` on FRAME §3's six acceptance criteria.

## Rules for this track
- **Frozen, read-only:** \`docs/FRAME.md\` §1–§9, \`docs/CHANNEL.md\`, \`docs/MODEL.md\`,
  \`docs/DATA.md\`. If the approach needs the frame changed, stop and say so in
  \`docs/TRACK_REPORT.md\` — do not edit those files here.
- **Start at stage 2.** Run \`/grothendieck\` and \`/gromov\` with the charter below as the
  argument (they read FRAME.md for the problem), then \`/domain\`, \`/research-plan\`, and the
  unit agents as usual. Existing \`LENS_*.md\`, \`DOMAIN_*.md\`, \`BRIEF.md\`, \`units/\`,
  \`MODEL_*.md\`, \`VERIFY_*.md\` in this worktree describe the **incumbent** approach (A0);
  overwrite them for this track — the hub keeps the originals.
- **Instance data (★6):** \`instance_descaled.json.gz\` is absent here and BRIEF §4's rule
  stands: no unit reads it unless the hub says ★6 is settled.
- **Python:** \`.venv/bin/python3\` (linked to the root checkout's venv). Tests:
  \`.venv/bin/python3 tests/run_all.py\`.
- **After every stage** run \`/track-report\` so the hub can \`helios sync $id\`.
- Commit on this branch (\`alt/$id\`) freely; never push, never touch \`national-channel\`.

## Charter

$(cat "$charter")
EOF
echo "track-setup: $wt/CLAUDE.local.md written, .venv linked"
