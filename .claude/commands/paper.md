---
description: Build the paper with the MacTeX PATH export, then check the .blg for undefined citations
allowed-tools: Bash(export PATH=/Library/TeX/texbin:$PATH && make), Bash(export PATH=/Library/TeX/texbin:$PATH && make clean), Bash(grep:*), Bash(ls:*), Bash(git status:*), Read
---

Build `nash_territory_division.pdf` the way CLAUDE.md requires — which is a build **and** a
citation check.

## Build

```
export PATH=/Library/TeX/texbin:$PATH && make
```

The export is not optional: `latexmk` and `pdflatex` live in `/Library/TeX/texbin`, which is on
`PATH` in interactive login shells but **not** in the non-interactive shell you're running in.
Without it the build fails with "make: latexmk: No such file or directory".

`make` runs BibTeX automatically and rebuilds when the `.tex`, the bibliography, or any
`figures/*.png` changed.

## Then check the log — always

```
grep -n "Citation.*undefined" nash_territory_division.blg
grep -n "Warning\|Error" nash_territory_division.blg
```

An undefined citation does **not** fail the build; it silently ships a `[?]` in the PDF. This
check is the point of the command.

Also scan the `make` output for `LaTeX Warning: Reference .* undefined` and overfull-hbox
warnings on any line you just touched.

## Report

- Build result: succeeded / failed. On failure, paste the actual error from the log, not a
  paraphrase.
- Undefined citations: list every key, or state "none".
- If I just added citations: confirm each new key exists in
  `literature/territory_bibliography.bib` (`grep "^@" ` on it) and that proper nouns in any new
  entry are **brace-protected** — `plainnat` lowercases titles otherwise.
- Don't run `make clean` unless I ask.
