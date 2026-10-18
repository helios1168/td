---
type: Lesson
title: 'Landing a finished branch needs its own issue carrying the posted review verdict; landing against the milestone #105 would have closed it'
description: '"land it" stalled on the IFA-page branch: land.mjs lands an issue number with a posted review verdict, and the only related issue was #105 "Finalize the main and IFA maps" — landing against it would have closed the milestone. The approved path: scoped #144, auditor, independent reviewer, verdict posted, land (suite → fast-forward main → push → delete remote branch → close issue → regenerate STATE.md → pull on m2). Direct pushes to main are for quick config edits only, and shared branch links die at land.'
tags:
- lesson
- process
- landing
- issues
- review
- state
status: draft
generated:
  by: session-reviewer/glm-5.3
  at: 2026-10-18T08:13:36Z
state: STAGED
kind: lesson
evidence:
- pi-session:01a14bde-5509-737b-9142-90d7a3cde8f2#8e90e333
- pi-session:01a14bde-5509-737b-9142-90d7a3cde8f2#710b258d
- pi-session:01a14bde-5509-737b-9142-90d7a3cde8f2#f117c1d1
- pi-session:01a14bde-5509-737b-9142-90d7a3cde8f2#89bf29a7
uses: []
supersedes: null
history:
- {at: '2026-10-18T08:13:36Z', from: null, to: STAGED, by: session-reviewer/glm-5.3, gate: intake}
---

On 2026-10-17 the owner said "land it" for the IFA owner-page branch (`m5-studio/ifa-pages`, ~200 lines of `zip_pages.py` plus 21 render files) — and the land path would not take it as asked: `~/.pi/agent/lib/land.mjs` lands an issue number that carries a posted review verdict, and the branch had neither. The only related open issue, #105 "Finalize the main and IFA maps", is the milestone; landing against it would have closed it. The path the owner approved ("yes"): open a small scoped issue (#144, "Maps: IFA owner pages, `--title`, `--no-footer`, `--palette clean`", linked to #105), run an auditor pass then an independent reviewer pass over the diff, post the review verdict on the issue, then run the land script. It then ran the suite, fast-forwarded `main` (a066bb4), pushed, deleted the remote branch, closed #144 and set it Done on the board, regenerated `STATE.md`, and pulled on m2.

Three things worth keeping: the direct push to `main` is meant for quick config edits — a code-plus-renders change goes through its own issue and review; the reviewer model ran without `gh` access, so the parent relayed the issue body verbatim — brief reviewers accordingly; and land deletes the source branch, so GitHub links shared while the work sat on it stop resolving once it lands — re-share from main (the seven PDFs are now at `results/ifa_pages_2026-10-17/` on main).
