---
type: Lesson
title: 'Gitignored `runs/` does not mean unpublished: overnight map packages live on the `night` branch, so search remote branches and past sessions before telling the owner an artifact is not on GitHub'
description: 'Asked for the latest IFA K48–54 maps and a GitHub link, the first two answers — "only on m5, in the gitignored run folder" and "they aren''t on GitHub" — were wrong: the owner had already viewed them at `night/n/maps/IFA_K<NN>_pages.pdf`, byte-identical to `runs/exp/sealed_2026-10-14/ifa/K<NN>/zip_pages.pdf`. Check the night branch and the session history first.'
tags:
- lesson
- artifacts
- github
- publishing
- night-branch
- runs
status: draft
generated:
  by: session-reviewer/glm-5.3
  at: 2026-10-18T08:13:36Z
state: STAGED
kind: lesson
evidence:
- pi-session:01a14bde-5509-737b-9142-90d7a3cde8f2#1a0627d5
- pi-session:01a14bde-5509-737b-9142-90d7a3cde8f2#ae3d6150
- pi-session:01a14bde-5509-737b-9142-90d7a3cde8f2#72ad5ab3
- pi-session:01a14bde-5509-737b-9142-90d7a3cde8f2#8e3b638a
uses: []
supersedes: null
history:
- {at: '2026-10-18T08:13:36Z', from: null, to: STAGED, by: session-reviewer/glm-5.3, gate: intake}
---

`runs/` is gitignored, so a render that lives there is invisible to a fresh checkout — but invisible to git is not the same as unpublished. The 2026-10-14 overnight published its packages on the `night` branch: the sealed night's IFA K48–54 set as `n/maps/IFA_K<NN>_pages.pdf` with `n/MORNING.md` and `n/ifa/IFA_INDEX.md`, and the national package under `d/` (`d/INDEX.md`, `d/maps/`). When the owner asked on 2026-10-17 for the latest IFA K48–54 maps and a GitHub link, the first two answers — "only on m5, in the gitignored run folder" and "they aren't on GitHub; the only `zip_pages.pdf` files on GitHub are the two main-map renders" — were both wrong: `night/n/maps/IFA_K48_pages.pdf` and `.../IFA_K52_pages.pdf` match `runs/exp/sealed_2026-10-14/ifa/K<NN>/zip_pages.pdf` byte for byte, and the owner had viewed those links before.

What recovered the answer was process, not memory: searching past sessions for github.com URLs (ripgrep over the sessions directory surfaced a `night/n/maps` link) and listing remote branches (`git ls-remote | rg night`). Before telling the owner an artifact is not on GitHub, do both; a path under `runs/` being gitignored says nothing about whether an overnight driver published it. Orientation while the question is live: after #144 landed (2026-10-18) the restyled owner set is on main under `results/ifa_pages_2026-10-17/` (same districts — split counts 21, 21, 21, 19, 18, 18, 21 verified against the 10-14 table), while `results/ifa_kgrid_2026-10-13/` is the older 10-13 ladder — pre South-Atlantic-redraw, still carrying the over-window MD district — not the current one.
