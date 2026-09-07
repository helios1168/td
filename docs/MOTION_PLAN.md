# "Borders in Motion" — overnight plan: build, verify, improve

*Written 2026-09-07 for a fresh session. The page exists and is published; it crashed on first
publish and the crash is fixed. What is missing is verification in a real browser and the
improvements below. Resume from `STATE.md` `## Now`, then this file.*

## What exists

- **Artifact** "Borders in Motion", `https://claude.ai/code/artifact/3e983b90-8f87-4dfd-aa28-4e1cd6eee497`,
  version "DC polygon crash fixed". Steps through the Track 2 anchored δ = 5% optimisation on an
  SVG map (15 steps: committed map, aggregation to 49 units, the mass bound, anchors, the MILP's
  answer, the balance pass, the transportation cut and each kept Lloyd round inside CA, FL, NY
  and TX, completion, the result) and, as a second tab, Track 1's seven Lloyd iterates at δ = 5%,
  λ = 100. A checkbox flips the dots to the committed labels.
- **Builder**, `tools/motion_page/`: `steps_data.py` (replays the anchored δ = 5% program with
  `state_splits.build_milp` / `solve` / `balance_pass` / `realise`, caches the 137 s MILP solve
  in `battery/results/motion_page/steps_milp_cache.json`, exports simplified state polygons in
  LAEA kilometres, zip coordinates, labels per step and Track 1's iterates to
  `battery/results/motion_page/steps.json`), `steps_template.html` (the page, with `__DATA__`
  where the JSON goes), `build_steps.py` (joins them into
  `battery/results/motion_page/borders_in_motion.html`), `dom_stub_run.js` (runs the page script
  under a stub DOM in node and reports any runtime error and what it drew).
- **The crash, and its fix.** DC's polygon is under the 200 km² islet filter, so its part list
  came through empty and a `reduce` over it threw at load, taking the whole script with it and
  leaving a blank map. `steps_data.py` now always keeps a state's largest part, and the template
  guards the reduce. `dom_stub_run.js` now reports "ran without error", 49 paths, 3,707
  circles, 107 edges, 26 tick buttons. **Nobody has looked at the page in a browser yet.**
- **Privacy rule for this page**, decided 2026-09-07: per-zip content is coordinates, district
  labels and a size quintile only; masses appear as state totals in τ. Keep it that way.

## The job

Verify the page renders and behaves at every step, fix what a browser shows, then make the
improvements in priority order until the morning, republishing at each stable point. Everything
below is scoped to `tools/motion_page/` and `battery/results/motion_page/`; nothing else in the
repo should change except `docs/BORDERS_RESULTS.md` and `STATE.md` at the end.

## 1. Build

```
/Users/ntlee/projects/td/.venv/bin/python3 -u tools/motion_page/steps_data.py     # ~3 min first time, then cached
/Users/ntlee/projects/td/.venv/bin/python3 tools/motion_page/build_steps.py
node tools/motion_page/dom_stub_run.js /Users/ntlee/projects/td/battery/results/motion_page/borders_in_motion.html
```

Run from the worktree with absolute paths; data is in the hub (`instance_descaled_v2.json.gz`,
`battery/results/borders_k18_v2_20260907/`, `data/geo`). The `.venv` is the hub's. `node` is at
`/opt/homebrew/bin/node`; `highspy` is importable from `.venv` (for the optional item 5 below).

## 2. Verify in a real browser

No Playwright is installed; do not install into `.venv`. Google Chrome is at
`/Applications/Google Chrome.app`, and headless screenshots need nothing else:

```
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu \
  --window-size=1400,1000 --screenshot=/Users/ntlee/projects/td/battery/results/motion_page/step.png \
  "file:///Users/ntlee/projects/td/battery/results/motion_page/borders_in_motion.html"
```

That only shows step 1. To screenshot every step, add a `?step=N` query (or `#step-N` hash)
handler to the template (item 3a below, do it first), then loop over N. Read each PNG with the
Read tool and check, per step: the map is drawn, the panel text matches the step, no label
overlaps another, the dots are visible at all five sizes, the split-state labels fit inside the
state or are placed clear of it. Also check `--enable-logging=stderr` output for console errors,
and run once with `--force-dark-mode` for the dark theme.

Then two data checks, in Python against the run: the final step's labels equal
`battery/results/borders_k18_v2_20260907/track2_anchored/d0.05/d0.05/draw.csv` on every
geometric zip; and the MILP step's shares equal that cell's `splits.json` `y_shares` to two
decimals (the replay is deterministic and this held on 2026-09-07; recheck after any change to
`steps_data.py`).

Publish only when both the screenshots and the data checks pass. From a new session the update
must pass the URL: `Artifact(file_path=..., url="https://claude.ai/code/artifact/3e983b90-8f87-4dfd-aa28-4e1cd6eee497", label="...")`,
after `Artifact(action="read", url=...)` once. Publishing without `url` from a new conversation
creates a second artifact; do not.

## 3. Improve, in this order

Stop at any point; each item is independent and the page must be publishable after each.

a. **Deep links.** `?step=N&mode=t1|t2` on load, and the hash updated as the user steps, so a
   step can be linked from the results doc and screenshotted in a loop. Small.
b. **Colours that match the figures.** The page assigns its own 18 nominal colours; the rendered
   PNGs use `tools/us_maps.py::draw_palette`, which picks hues so adjacent districts never
   share one. Export that palette from `steps_data.py` (call `draw_palette` on the final
   labelling the same way `figure_districts` does, and once on the committed labelling) and use
   it in the template, so the page and "The Five Percent Map" agree hue for hue.
c. **Split-state fill.** A split state is currently filled with its largest holder's colour and
   labelled with all shares. Fill it with stripes in the touching districts' colours,
   proportional to share, using SVG `<pattern>` elements built per state. Also stack the
   anchor labels (CA has five districts homed there) instead of joining them on one line.
d. **Inside a split state, show the cut.** At each level-2 step draw the power-cell boundaries
   between the touching districts for that round: `centers.power_weights(xy_s, M_s, C, targets)`
   gives the duals β; the boundary between districts i and j is the line
   `‖q − c_i‖² − β_i = ‖q − c_j‖² − β_j`, clipped to the state polygon (`shapely` in
   `steps_data.py`, exported as line strings). This is the one addition that makes the level-2
   steps explain themselves: the viewer sees the cut move as the centres move.
e. **Transitions.** CSS transition on circle `fill` (150 ms) so a step change reads as
   movement; respect `prefers-reduced-motion`. Optional autoplay button with a 2 s cadence.
f. **Hover.** A tooltip per dot: state, size quintile, district at this step, district in the
   committed map. No mass values.
g. **Track 1 overlay.** On the Track 1 tab, outline each round's owner sets (states coloured by
   owner district, hatched where a state has several) so the viewer sees why zips cross where
   they do. `state_borders.owner_sets` on each iterate gives the data.
h. **The MILP's search.** Optional. `scipy.optimize.milp` exposes no callback, but `highspy` is
   in `.venv`: build the same model through `highspy.Highs` from `SplitProblem`'s `c, A, lb, ub,
   integrality, var_lb, var_ub`, set `output_flag` and parse the log's incumbent lines
   (objective and time) to plot the incumbent and bound trajectory, 17 → 8 splits over 137 s,
   as a small chart on the MILP step. Only if a to c are done and time remains.

## 4. Acceptance

- `dom_stub_run.js` reports no error, and a headless screenshot of every step (both tabs) has
  been looked at, light and dark.
- Final-step labels equal the run's `draw.csv`; MILP-step shares equal its `splits.json`.
- The artifact is updated in place at the URL above, with a version label naming what changed.
- `docs/BORDERS_RESULTS.md`'s paragraph on the page and `STATE.md` `## Now` say what the page now
  shows and which items above are done and not done. Commit on `worktree-vbl`, push, and ask
  before merging to `main`.

## Constraints

- Never write per-zip mass values into the page. Never write under `battery/figures/`. Never
  install into `.venv`. Hand-made worktree, absolute paths, Serena by absolute path.
- The page's fonts and MathJax come from allowed CDNs; if a screenshot shows raw `$…$` or a
  fallback font, that load was blocked and the fix is to inline, not to change hosts.
- Do not widen scope into the other three artifacts.
