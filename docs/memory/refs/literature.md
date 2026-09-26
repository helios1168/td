# td's literature before the support refactor, and what migrates

Counted on m5 in session 01a0d98f, 2026-09-25. The rule for papers across projects: sv-ntlee `docs/memory/decisions/literature.md`.

- **Inventory:** 6 `.bib` files with 344 entries, 262 distinct papers, 256 of them with DOIs. 78 entries are copied between files, and the copies agree. 4 papers are filed under two keys each: `jain2010egmarkets`/`jainvazirani2010`, `jalota2023`/`jalota2023fisher`, `echenique2021`/`echenique2021constrained`, `he2018`/`he2018pseudomarket`. There are also 2,250 lines of `LIT_*.md` notes.
- **What migrates:** all of it stays in the tag `archive/pre-support-2026-09`, and only papers the support model cites move to the global registry, `/Users/Shared/sv-ntlee/kb/references.bib`. td had no `docs/REFERENCES.md` as of 2026-09-26.
- **Shmoys–Tardos and Lenstra–Shmoys–Tardos:** `docs/foundations/LIT_optimization.md` §0 already cites `lenstra1990` and `shmoystardos1993`, but only for the `≤ k−1` fractional-count lemma on the archived Nash track (`mem:model/u9-bandthm` P3-split; MATH_REVIEW §3.3's split bound). Their rounding theorem was unused: the realizer rounds by argmax (`mem:facts/support-pipeline`). The support refactor uses it; the quoted result is in sv-ntlee `kb/assignment-lp-rounding.md`.
