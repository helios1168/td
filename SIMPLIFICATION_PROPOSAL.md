# Repo inventory and cleanup record

**Revised:** 2026-08-27. This file replaces an earlier proposal of the same name that
recommended several deletions which would have broken the paper. Those recommendations
were checked file by file and are corrected below.

**Historical record, paths as of 2026-08-27.** Later the same day the repo was baselined
into git (commit `5b1bf4c`) and `handoff/` was flattened into the repo root — every
`handoff/...` path below should be read with that prefix dropped. Left unrewritten so
this stays an accurate record of what was found and why, not a live reference.

---

## Standing constraints (void as of the 2026-08-27 baseline commit)

1. ~~Only `README.md` is tracked in git (one commit, `01f88ea`). Every other file is
   untracked, so deletion is permanent — `git checkout` restores nothing.~~ Everything is
   now tracked (`git ls-files` = 97 files as of the baseline commit); deletions are
   git-recoverable.
2. ~~Nothing here can be regenerated on this machine. No `numpy`/`scipy`/`networkx`/
   `matplotlib`, system Python 3.9.6 only, no venv, and no LaTeX toolchain.~~ A `.venv`
   with the full scientific stack (see `requirements.txt`) exists and has been verified
   to import cleanly.

A future reader should not inherit these as live gates — they applied only to the
pre-baseline state.

---

## Executed 2026-08-27 (verified zero-loss)

| Path | Evidence |
|---|---|
| `.DS_Store` ×4 | OS metadata |
| `handoff/code/__pycache__/`, `handoff/review/code/__pycache__/` | cpython-310/312 artifacts from another machine |
| `handoff/review/code/_to_delete/capacity_ceiling_test.png` | md5 `96ac56fe…` — byte-identical to `handoff/review/figures/capacity_ceiling_test.png` |
| root `nash_territory_division_20260826.pdf` | md5 `ac6f61eb…` — byte-identical to `handoff/papers/` copy |
| `handoff/review/code/implicit_parameter_audit_kernel.py` | nothing imports it; `HANDOFF_REVIEW.md:272` records it as published separately as a skill |
| `handoff/archive_HANDOFF_2026-08-27.md` | diffed against `HANDOFF.md`: **zero unique content**, a strict subset |
| `handoff/reference/fair_division_line_20260825.pdf` | `HANDOFF.md` itself called it "superseded operationally"; the analytics it holds are not referenced by the current pass |

Added `.gitignore` so caches and OS files do not return.

---

## Where the previous proposal was wrong

Ranked by damage, all verified against the files:

1. **Deleting `handoff/figures/` would have made the paper unbuildable.** The four paper
   PNGs exist in exactly one place, are referenced by bare filename at
   `papers/…tex:318,336,424,464`, and **no script in the repo generates them** — the only
   `savefig` calls write the census, review, and C-series figures. The stated reason
   ("in the paper; don't need to be stored twice") inverts the situation: they are in the
   *compiled PDF*, which is the artifact you would lose the ability to rebuild. The
   directory also holds **5** files, not 4, so the proposed `rm -rf` would have taken
   `census_stress.png` — which the same document said to keep.
2. **Deleting `zip50.py` would have broken the one review file the proposal kept.** It is
   the sole generator of the paper's §5 instance and of `/tmp/z50.pkl`, which **16** files
   read — including `review/code/dzero.py:61`, the project's only numeric solver anchor
   per `HANDOFF.md:200`.
3. **Deleting 17 of 18 files in `review/code/` overshoots badly.** `HANDOFF_REVIEW.md:266`
   names `dzero.py` *and* `omega.py` as keepers. `figdec.py` is the sole source of the ω
   knife-edge table (`HANDOFF_REVIEW.md:88-93`) on which the entire d=0 decision rests;
   `probe4.py` holds the objection-3 numbers; `capacity.py`/`obj2_*.py`/`mkfig_obj2.py`
   are the whole evidence base for objection 2, which the review calls the one a referee
   will press hardest. Exactly **one** file was genuinely disposable.
4. **Deleting `handoff/reference/` removes the only handle on the Warren 2025 citation.**
   `fair_division_2d_20260825.pdf` §10 is the sole local source, and the `.bib` has no
   warren/transport/kantorovich entry — so the fallback of "keep URLs in the bibliography"
   fails: there is no entry, no URL, and no DOI anywhere in the repo.
5. `method.md` was misidentified as a superseded methodology sketch. It is a Claude skill
   file (`name: problem-framing`); the adversarial review's §2 and §5 are literally its
   Grothendieck and Gromov passes. It is provenance for the d=0 reversal.
6. `github_setup/` does not exist. An entire decision branch concerned a phantom.
7. `LITERATURE_WORKFLOW.md` was listed twice, at two different paths, with opposite
   verdicts. It lives in `handoff/literature/`.
8. Counts were wrong in two places: `reference/` holds 3 PDFs (not 4), `figures/` holds
   5 PNGs (not 4). `README.md` — the only tracked file — got no verdict at all.

---

## Open decisions

| Path | Size | Question |
|---|---|---|
| `handoff/battery/figures/*.png` — **RESOLVED: keep** | 13 MB | **Not regenerable.** Hard-coded `/home/claude/td` paths *and* a split module layout *and* no scientific stack *and* a ~17-case MINLP run. Deleting is data loss, not cleanup. The `C*.json` metrics (~100 KB) must be kept regardless. |
| `handoff/reference/discrete_territory_division_20260826.pdf` — **RESOLVED: keep** | ~0.6 MB | `HANDOFF.md:304` keeps it as the fallback if the Nash choice is challenged; holds the `210.253` Appendix-B figure that deferred objection 4 concerns. |
| `handoff/HANDOFF_2026-08-27.pdf` | 103 KB | Renders one of the two HANDOFF markdowns; could not determine which without `pdftotext`. Kept rather than deleted on a guess. |
| `handoff/review/code/coupling4.py` | 30 lines | Superseded by `coupling5.py`. Cheap to keep. |
| `handoff/code/territory_demo.py` | — | Marginal smoke test, documented at `HANDOFF.md:194`. |

---

## Deferred to the paper pass

- Adversarial-review objections 3 and 4: deferred, logged as known-open.
- M. Warren 2025 to be cited as corroboration for d=(0,0) plus an N>2 remark
  (semi-discrete transport → Laguerre cells → contiguity by construction). Needs a new
  `.bib` entry: *Continuum Nash bargaining solutions*, Nonlinear Differ. Equ. Appl.
  **32**:109 (2025), doi 10.1007/s00030-025-01118-7.
