# PLAN — branch `worktree-headline`

Branch-local record. Updated 2026-09-07 after the override work landed.

## Status

Built and committed. Not merged to the hub.

| commit | what |
|---|---|
| `d7493f8` | the per-state cap in the solver, the driver flags, and the Streamlit Headline tab |
| `0455cb2` | figure galleries with descriptions, and the California-capped override |
| `89b44e9` | leader lines for small districts, 18 per-district close-ups |
| `83a9db0` | district shares to two decimals on both overview maps |
| `9f761a2` | `docs/HEADLINE.md`, the end-to-end write-up |

313 tests pass. Re-running the headline through the new code with no caps reproduces it exactly:
objective 57.00483235477814, 8 splits, CA/FL/NY/TX, gap 0, byte-identical `draw.csv`.

## What the override does

`--cap ST=N` on `tools/state_splits.py` holds a state to at most N districts, through a new
`"cap"` row block in `build_milp`. `--unanchor ST` releases anchors, and releases only the
surplus a cap forces, keeping the cap-many anchors that hold the most of that state's committed
opportunity. `--dump-state-shares PATH` writes each state's $M_s/\tau$ ratio and anchored count
and exits before solving; it writes ratios only, never $\tau$ and never a mass, because the app
reads it.

The app's Headline tab refuses a cap below the arithmetic floor, warns without blocking when a
cap releases anchors, and diffs the rerun against the headline. `app/` still never imports `td`.

## Findings, and corrections to earlier numbers

**The CA ratio is 4.1529, not the 4.126 this file used to record.** The floor is still 4. The
band that would admit California in 3 is about 38.4%, not the 37.5% quoted earlier.

**The mass floor is necessary, not sufficient.** $\lceil M_s/((1+\delta)\tau)\rceil$ rules a cap
out; it does not promise one is reachable. California in 4 is legal at δ = 5% and sits exactly
on the floor: four districts at the cap hold 4.200τ against California's 4.153τ, leaving 0.047τ
of slack for every other state across those four and a window 4.7% of a district wide. HiGHS
found no feasible integer point in 10 minutes, nor in 20.

**Per-state caps have almost no legal move on this map at δ = 5%.** Only four states are split.
TX and FL are already at their floor of 2, so a cap there is a no-op. NY at 2 is *proven*
infeasible in seconds: two districts are anchored in New York and need at least 1.90τ, but the
state supplies only 1.805τ, and Pennsylvania and New Jersey are anchored elsewhere. CA at 4 is
the knife-edge above. The map is not merely optimal, it is tight.

**The band is the lever, not the cap.** California capped at 4 at δ = 10% solves: 7 splits, CA in
4, NY falls 3 to 2 on its own, NJ splits for the first time, spread 16.70% against 8.98%, stage 2
95.7458. Time-limited incumbent, 1.79% gap. Written up in `figures/overrides/ca4_d10/`.

**The shipped map's measured max deviation is 5.25%, outside its own nominal 5% band.** The
4.68% figure that satisfies the band is `pass_max_dev`, a state-level quantity computed on
continuous shares before `realise` makes whole ZIP codes of them and before AK, HI and the
coordinate-less ZIPs are placed. `grid.csv` carries three different measurement objects side by
side with nothing marking which is authoritative. Anywhere the map is called "within 5%", this
distinction belongs in the sentence.

**Opportunity capture reproduces exactly.** Recomputed independently from the instance and the
shipped draw: stage 2 95.78785, spread 0.089824, Nash 110.873686, 776 ZIPs changed, every ZIP
assigned once, mass conserved to floating precision.

## Open

- The hour-long California-at-4, δ = 5% run may still be in flight; if it found nothing, that
  cap is out of reach at the tighter band and the app should say so rather than appear to hang.
- Per-state figures for CA, NY, TX and FL, showing each state carved by district plus the states
  connected to it through a shared district.
- `docs/APP.md` has no section for the Headline tab yet.
- Nothing downstream of a real `runner.launch` has been exercised: Streamlit cannot be driven
  headlessly, so the tab's run, cancel and render flow is unverified by test.
- The per-district close-ups reuse the landscape overview canvas, so a portrait state wastes
  width.
- `STATE.md` and `docs/CODE_MAP.md` do not point at `docs/HEADLINE.md` yet. That belongs with
  `/state` at merge time.

## Constraints that still bind

`app/` never imports `td` and never receives a raw mass. Never write under `battery/figures/`.
Use `\git`; the hook blocks heredocs and `cat`/`grep` on files. Serena resolves relative paths
against the hub, so pass absolute worktree paths. Run tests and drivers with the hub interpreter
`/Users/ntlee/projects/td/.venv/bin/python3`; this worktree has no `.venv`, and its `.venv-app`
was built by hand. Ask before merging to the hub.
