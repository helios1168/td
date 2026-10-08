## Contract v2 (shared by #103 A, #129 B, #130 P)

The three lanes build against this contract at the same time. Each lane's first commit is a stub
that reads and writes these files, so the others can build against it. Every file carries
`"contract": 2`; a reader rejects any other version, and any identity that doesn't match.

### Identity
- `instance`: the spec path plus the sha256 of the spec text, the extract name and the graph
  version, i.e. `td.geo.polygon_graph` with its connector list.
- `plan_id`: a stable hash of (instance, channel, K, band, rule, the sorted cuts applied,
  and the multiplicity vector).
- `parent_id`: the plan this one was re-planned from, or null.

### plan.json (A writes it; P reads it). One file per plan; a pool is several files.
```json
{"contract": 2, "plan_id": "...", "parent_id": null, "instance": {...},
 "channel": "FI", "K": 20, "units": "usd", "target": 900e6, "band": [765e6, 1035e6], "eta": 0.02,
 "rule": {"one_split_per_district": true},
 "objective": {"splits": 5, "cuts": 9, "diameter": 1234.5},
 "certificate": {"s_incumbent": 5, "s_lower": 5, "lower_status": "proved|unknown",
                 "domain": "C-rule supports at the target band", "cuts_applied": ["<cut_id>", "..."]},
 "split_states": ["CA", "NY"],
 "supports": [{"support_id": "CA", "units": ["CA"], "n": 2},
              {"support_id": "CA+NV", "units": ["CA", "NV"], "n": 1}],
 "districts": [{"id": "FI_04", "support_id": "CA+NV", "copy": 1, "whole": ["NV"], "split": "CA",
                "target_share": 812.3, "mass_lo": 0.0, "mass_hi": 0.0}],
 "pool_index": 0}
```
- `support_id` is the sorted unit names joined by `+`. `copy` numbers the copies of a support,
  from 1 to n.
- `target_share` is the decoder's equal split, M_σ·t_{σ,S}/n_S (`td/master.py:336-382`). It is a
  target only; B may realise unequal masses inside the windows.
- **Masses are dollars** (owner 2026-10-07, D3: "Every district vs target", tolerance "±15% of
  target"). Every cell's m_rel is weighted by its fine channel's rate (`tools/looks/score.py`
  `dollar_rates`; IFA uses the whole-extract IFA total), and `band` = target·[0.85, 1.15]. The
  band no longer depends on K; WIFI has no target and keeps τ_c·[0.85, 1.15].
- **Window:** mass_lo = max(η·M_σ, band_lo − M(whole)); mass_hi = min(M_σ, band_hi − M(whole)). The carve's partition conserves M_σ, and no other clipping is applied. The η floor
  keeps every piece non-empty, so the drawn split set equals the planned one.
- Plans exist only with rule C on. With rule C off, A reports the bound (s*) only, never a
  plan.json.
- **Pool:** every plan with the same splits and cuts as the best, ordered by diameter, at most 5,
  is written as `pool_index` 0..4.

### replan CLI (A provides it; P calls it)
```
python3 tools/expb2/plan.py --spec <toml> --channel C --k K --band-from-target 0.15 \
  --rule one_split_per_district --cuts cuts.json --pool 5 --out <dir>
```
- It writes `plan_<pool_index>.json` and `status.json`, where `status.json` is
  `{"status": "feasible|infeasible|unknown", "stop": "<engine stop reason>",
  "passes": [{"pass": 1, "objective": 5, "gap": 0.0, "seconds": 1.2}, ...]}`.
- Every call reruns the full lexicographic objective: splits, then cuts, then diameter. It never
  substitutes `td.master`'s diameter plan or smallest-δ search, and never changes δ.
- A's first commit is a stub that returns a rule-C-filtered diameter plan, ignores the cuts and
  sets `"stub": true`. P refuses `stub: true` outside its own tests.

### cuts.json (P writes it; A reads it)
Every cut has `cut_id`, `kind`, `scope` (instance, channel, K, band, rule) and `proof`
(job_id, engine, stop, model_version, and `"verified": true` only when the proof behind it is
tagged [proved] in docs/MODEL.md).
- `holder_nogood`: `{"state": "CT", "holders": {"<support_id>": <n>, ...}}`. It lists the
  multiplicity of **every** support containing the state, zero for absent ones, which also covers
  supports the master could add. It excludes exactly that vector: any change in any multiplicity,
  including a new holder, stays admissible. A encodes it exactly, with indicator rows on the
  bounded integers.
- `support_ban`: `{"support_id": "..."}`. Valid only (i) for a district with no split state whose
  fixed ZIP union fails the exact M1 gate (#127's rule), or (ii) for a support that
  `plancheck.drawable` proved undrawable alone (MODEL §4.9, Proposition B).
- A cut whose `proof.verified` is false is never written; P keeps it as a search note, not a cut.
- There is no `policy` kind: a carve still unknown after the pool ends its channel as "no map found" (owner 2026-10-07, D4).

### carve job (P writes one per split state of a plan; B reads it)
```json
{"contract": 2, "job_id": "<hash>", "plan_id": "...", "instance": {...}, "channel": "FI",
 "state": "CA", "units": "usd", "band": [765e6, 1035e6], "time_limit": 900,
 "pieces": [{"district": "FI_04", "support_id": "CA+NV", "copy": 1, "target_share": 812.3,
             "mass_lo": 0.0, "mass_hi": 0.0, "attach": ["NV"]}]}
```
`attach` lists the whole states the piece joins; an empty list means the piece is the whole
district.

### carve result (B writes it; P reads it)
```json
{"contract": 2, "job_id": "...", "state": "CA", "status": "ok|infeasible|unknown",
 "found_by": "heuristic|milp", "stop": "<engine stop reason>",
 "proof": {"kind": "joint_milp|drawable_alone", "verified": true, "piece": null},
 "assign": {"<zcta>": "FI_04"},
 "gate": [{"district": "FI_04", "pieces": 1, "necks": 0, "status": "pass"}],
 "border_km": 0.0, "seconds_first_ok": 0.0, "seconds": 0.0}
```
- `ok` means every ZCTA of the state is assigned, every piece is inside its window, and every
  piece ∪ attach passes `td.audit.district_pieces` and `district_necks` (no neck proved or
  unresolved). `assign` is present only for `ok`.
- `infeasible` comes only from a solver proof of the joint relaxation, or from `drawable` on one
  piece (set `proof.piece`). It is reported only when that proof's MODEL section is tagged
  [proved]; until then, report `unknown` with stop `milp_infeasible_claimed`.
- A timeout is `unknown`, which never becomes a cut.
