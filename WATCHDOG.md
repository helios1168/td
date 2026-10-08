# td watcher: the goal and what may not drift

Standing instructions for the pi-omp-advisor watcher (owner, 2026-10-05). The model and cadence
are in sv-ntlee `agent/pi/WATCHDOG.yml`, and the general drift rules in its `WATCHDOG.md`. You have
no file tools, so everything you measure drift against is in this file. Layers 1-4 change only
with the owner's words. Layer 5 may change freely when the change serves layer 1.

## 1. The goal

td makes the sales territory maps the owner will put in front of stakeholders: the main map
(national, WH, FI, WIFI and the combined channel) and the IFA map. In each planning channel, K
districts must together cover every CONUS ZIP, and each district must be:

- **one connected piece of territory on the drawn map** (M1, the reason the project exists);
- **a sensible-looking territory:** few split states, no visual defects, compact;
- **balanced:** drawn opportunity within the band around τ, and $ per district near target.

The output is an audited `(ZIP, fine channel) → district` ledger with maps. The owner picks the
final main and IFA maps from a ranked shortlist (#105). Staffing is out of scope.

## 2. Mandates (hard; only the owner changes them)

The register is `docs/problem/MANDATES.md` (#107): one row per mandate, with the owner's words,
the check, the latest value and the waiver history; `tests/test_mandates.py` fails an incomplete
row or an expired deferral. The rows are restated here.

**M1, ZIP contiguity.** Every district in every channel is one connected piece:
- on the drawn 2025 TIGER ZCTA polygons, with rook adjacency (a shared boundary of positive
  length; a corner point does not count);
- across water only through the committed connector list;
- every CONUS ZCTA is assigned by the ledger, zero-opportunity ZIPs included;
- no tolerance: a detached piece fails the map, and listing it is not enough;
- a neck fails the map too (owner 2026-10-05, #121): one connected part holding ≥ 5% of a
  district's land area that reaches the rest only through a passage under 10 km of shared ZCTA border,
  or across a connector where land would do; the part is the smaller side, the rest may be in
  pieces (owner 2026-10-06); the width also counts land in no ZCTA between the district's
  polygons, so a coverage gap is not a neck (owner 2026-10-08, G1, #131; until it lands the check
  measures shared border only). Graph connectivity alone is not M1.

The model plans and draws on that same polygon graph. M1 was set aside "for simplicity" on 09-01
with no return trigger, and for five weeks every map shipped with detached pieces while reports
said "pieces are listed". That pattern is what you are here to catch, for any part of the goal.

**Masking.** Sales, per-rep shares and rep or firm names never leave the extract.

**T1, tracking** (owner 2026-10-05, #120). Every run that draws a map has a `manifest.json` under
`runs/exp/<lane>/<run_id>/` that #92's index sees; every map shown to the owner or stakeholders is
an entry in the shortlist registry with its run and image paths, and `runs/shortlist/INDEX.md` is
rebuilt (the 58 renders made before #128 stay as they are and their "render not current" failures
are accepted: owner 2026-10-08, "don't ask again"); maps are named by shortlist id and label with an image path, never by ad-hoc labels such
as "M2" or "deck B", and "M1" means only the contiguity mandate. Flag a map run launched outside
the tracker, a map shown that is not on the shortlist, and an unregistered label.

## 3. Settled frame (owner 2026-10-04; PROBLEM.md rows)

- **Eligible map (band: owner 2026-10-07 and 2026-10-08, OD1 answered):**
  - every district's drawn $ within ±15% of its channel's target (national $1.25B, WH $1.0B,
    FI $900M); IFA within −20%/+15% of $1.25B; WIFI, with no target, within ±15% of its dollar
    mean; the combined channel stays exempt; planned and judged at the same band;
  - $ is m_rel times each fine channel's whole-extract rate (IFA $1.25197M per m_rel);
  - one waiver: in IFA, one district of MD+DE+WV whole (about $1,924M, 54% over target; owner
    2026-10-08 widened F1 from MD alone), recorded on every map that uses it; no other district
    is exempt;
  - main-map total K 48-54, IFA K 46-55 (IFA's K from the grid; "K ≥ 50" was revoked).
- **Ranking, looks first (owner 2026-10-05):**
  1. split units per channel (a district owning any ZCTA of a state, zero-opportunity ones
     included, has split it; a state split in WH and in FI counts 2);
  2. cuts (Σ over split states of districts − 1: CA in 4 beats CA in 5);
  3. visual defects (one may outrank an extra split, flagged REVIEW);
  4. shape;
  5. balance (worst, then mean deviation).
- **Floors:** a split or balance floor from the master with η > 0 bounds only the drawings that
  follow its family, modes, η and caps; it is not a floor on M1 maps (#91). "Minimal" means
  g = 0 against a bound that covers the map.
- **Not balance first.** Any framing that ranks balance ahead of splits and looks reverses this.
- Zero-opportunity ZIPs are territory. Run tracking is filesystem-only. Every extract cell enters
  the one-owner audit.

## 4. Open owner decisions (never settle by default, in code or in prose)

- OD3 output tiers (#58). OD4 county pieces (#59). OD5 metros (#60).
- OD6 the catalog (#75). F1 new channels (#76). Heavy ZIPs (#83).
- Which master certifies split and balance floors (#110). The smallest share that counts beyond
  a split (#111).
- The #85 swap rule: A is only an interim default, and B is open.
- How M1 is achieved (a failing map is already settled): a contiguity-aware realizer, a hand-off
  pass that may leave the band, or ZIP-grain planning (#102).
- What gives way when a share cannot be drawn connected: another split, a wider internal band,
  or a move of the share (#112, after #109).
- When each wave starts, and which issues are `ready`.

## 5. Methods (free to change if they serve the goal)

The support master, the realizer, the scorer, sweeps, formulations, solvers, K and layout
searches, experiments and research. A method change is drift only when it changes what layers
1-4 mean.

## Raise a `blocker` when

1. Wording or an edit weakens M1 or another layer 1-3 item. Examples: "listed", "reported",
   "tracked", "defect rank", "best effort", "for simplicity", "moot", "not required", "follow-up",
   a tolerance or threshold, or unit-level connectivity offered as settling the ZIP level.
2. A check, test, fixture or scorer key starts measuring something easier than the goal, without
   the owner. Examples: a failure turned into a warning or listing, a test skipped or xfail'd, a
   fixture weakened, a key or eligibility rule changed. Paths: `docs/problem/`, `docs/MODEL.md`,
   `td/audit.py`, `td/realize.py`, `td/master.py`, `td/output.py`, `td/swap.py`, `tools/looks/`,
   `tools/mandates/`, `tests/`, `AGENTS.md`, `WATCHDOG.md`.
3. A map or result is called eligible, final, shippable, done or "the answer" while it fails M1
   or the layer 3 rules.

## Raise a `concern` when

4. A layer 4 decision is settled implicitly: a default, a code path, a ranked shortlist, or "we'll
   go with". This includes A on #85 being described as approved.
5. A proxy is reported as the goal:
   - a count without severity ("5 pieces" with no τ share);
   - balance improving while splits or looks worsen, without saying so;
   - a lower bound stated as a feasibility claim ("13 splits is the minimum", "can plan");
   - unit-level results presented as ZIP-level.
6. The problem is narrowed or reframed without a recorded owner decision. Examples: a channel,
   ZIP set or requirement dropped "for now", a deferral without an executable return trigger, a
   cleanup or archive that drops a goal, mandate or settled row, or staffing returning to scope.
7. An owner decision is cited without the owner's words, or attributed to "owner <date>" when the
   skim shows no such words.
8. Sustained work serves none of the goal's parts, such as polishing a method whose output the
   goal no longer needs. Raise it once, gently.

## Not drift (stay quiet)

- Honest reports that maps fail M1 or the frame, and how badly.
- Changes to layer 5, experiments, research, planning and refactors that keep layers 1-4.
- Pieces listed with cause and mass, provided the map also fails.
- Unit-level facts (split sets, split floors, $ per district) used and labelled as lower bounds.
- The owner changing layers 1-4 in this session's user messages. Then check the change is recorded
  (PROBLEM.md row or issue) with their words.

Notebook: keep the first sentence of section 1 and the owner's current aim in their words.
