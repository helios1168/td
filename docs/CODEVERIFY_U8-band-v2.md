# CODEVERIFY — `MODEL_U8-band.md` §10 (v2, `k = 18`)

Adversarial verification that the newly written §10 "Results — v2" (and the two residues cleared
in §5.1 and §9.1) faithfully reports what the code produced. Posture: try to break the mapping
first.

**Scope.** `docs/MODEL_U8-band.md` §5.1 (replaced constants), §5.2 (SCIP narrowing, read only),
§9.1 (residue), §10.0–§10.7. Ground truth
`battery/results/u8_band_v2_20260904/draw_k18_v2_20260904.json`. Owned code
`tools/measure/frontier.py`, `td/solvers/eg_band.py`.

**Date** 2026-09-05. **Interpreter** `/Users/ntlee/projects/td/.venv/bin/python3` (CPython
3.13.15). scipy 1.18.1, numpy 2.5.2, highspy 1.15.1, pyscipopt 6.2.1. **cwd**
`/Users/ntlee/projects/td/.claude/worktrees/w2-phase0` (worktree at `9cfcc2c` + uncommitted).

---

## Summary

| # | Row | Verdict |
|---|---|---|
| 1 | Provenance: `instance_sha256`, `draw_sha256`, θ/λ/filler, versions, `k`, `n_zips`, `T`, `T/k` | **VERIFIED** |
| 2 | §10.0 gate numbers (`EG_{S₁₈}` bracket, 30 tangents, `M`-max-dev/spread, `δ₀`, `spread₀`, `V`) | **VERIFIED** |
| 3 | §10.0 gloss "`gate.delta_upper` is `null` … no grid point records where the band would close" | **REFUTED** |
| 4 | §10.0 "`matches_reference = true`" quoted as a gate outcome | **VERIFIED (transcription) / misleading** |
| 5 | §10.0 + §10.7-1: band never fully slackens at `δ = 0.33` | **VERIFIED** |
| 6 | §10.1 frontier table (brackets, widths, tangents, `s_min`, `−V`, `t`, splits/cap) | **VERIFIED** |
| 7 | §10.1 sandwich display — last entry `96.5321517586` | **REFUTED** (1e-10 rounding slip) |
| 8 | §10.1 vertex / shape / split-cap / witness assertions | **VERIFIED** |
| 9 | §10.1 SCIP cross-check table and "unlike v1, not uniformly on one side" | **VERIFIED, field-sensitive** |
| 10 | §10.2 D1′ softness table and NOT-SOFT verdict | **VERIFIED** |
| 11 | §10.3 `δ*` ≤ `δ₀`, zero solves | **VERIFIED** |
| 12 | §10.4 N8 band-dual table — rep IDs from `staff`, not `districts` | **VERIFIED** |
| 13 | §10.4 + §10.7-2 degenerate zero-dual "tight" bands at `δ = 0.05, 0.10` | **VERIFIED** |
| 14 | §10.5 N9 proportionality (delivered 3/18, frontier 0, 30 % erosion) | **VERIFIED** |
| 15 | §10.6 + §10.7-3 first movers: `n_exact_ties = 0`, `tied_M_share = 0.0` | **VERIFIED** |
| 16 | §10.6 "margins … an order of magnitude **tighter** than v1's ties" | **REFUTED** |
| 17 | §5.1 replaced constants `140.638` / `95.176` | **VERIFIED** |
| 18 | §5.1 "all 18 gains sit at ≈ `206`" | **REFUTED** |
| 19 | §9.1 residue cleared; §9 otherwise unmutated | **VERIFIED** |
| 20 | §10.7-6 stale `instance` field; §10.7-7 stale `frontier.png` | **VERIFIED** |
| 21 | §10 vs `STATE.md` `## Facts` | **VERIFIED (no contradiction)** |
| 22 | Acceptance-5 byte-identical re-run (claimed for v1 §9, absent from §10) | **INCONCLUSIVE — not claimed** |

**Counts: 16 VERIFIED · 4 REFUTED · 1 VERIFIED-but-misleading · 1 INCONCLUSIVE.**

**Type check:** `uvx pyright 1.1.411 tools/measure/frontier.py td/solvers/eg_band.py` →
`0 errors, 0 warnings, 0 informations`.
**Tests:** `.venv/bin/python3 tests/run_all.py` → **237 passed, 0 failed, 0 skipped**. (The 13
`test_cert_draw.py` failures the brief warned about did not appear in this run.)
**Machine check:** `docs/artifacts/U8-band-v2/verify_model_s10.py` → **357 assertions pass, 3
fail**; the 3 failures are rows 7 and 18 (row 18 fires twice, once against `g_delivered` and once
against the true gate gains).

None of the four REFUTED rows changes a verdict in §10.7 items 3–5, changes D1′, `δ*`, N8, N9 or
the A1 conclusion. Rows 3, 7, 16 and 18 are defects of *statement*, not of *result*. Row 18 is
the one worth fixing on the merits: it prints a number for an object the manifest does not
contain, and the number is 3–10 % away from the truth.

---

## Mapping table (model object → code symbol → manifest field)

| Model object | Code symbol | Manifest field |
|---|---|---|
| `V(delivered)` | `frontier.build_setting` → `Setting.V = fsum(log g_i)` (`frontier.py:227`) | `V_delivered` |
| `δ₀`, `spread₀` | `frontier.py:229-230` | `delta0`, `spread0` |
| gate `EG_{S₁₈}` | `frontier.gate` (`frontier.py:234`) → `eg_band.solve_band(U, M, None)` | `gate.*` |
| `EG^bal(δ)` bracket | `frontier.evaluate` (`frontier.py:278`) → `Point.primal/.upper` | `points[i].primal/.upper` |
| reported certified bound | `Point.certified_upper = min(upper, dual_check.bound)` (`frontier.py:131-135`) | `certified_upper[i]` |
| `s_min` | `Point.slope` (`frontier.py:112`) | `points[i].slope` |
| `t`, splits, cap, degeneracy | `eg_band.VertexReport` (`eg_band.py:138-141, 345-351`) | `points[i].vertex` |
| `ν` | `nu = mu_p - mu_m` (`eg_band.py:544`) | `points[i].nu`, indexed by `staff` |
| D1′ | `frontier.softness` (`frontier.py:309`) | `softness[]` |
| `δ*` | `frontier.bisect_delta_star` (`frontier.py:325`) | `delta_star` |
| shape | `frontier.shape` (`frontier.py:355`, on `p.upper`) | `shape` |
| first movers | `frontier.movers` (`frontier.py:369`) → `eg_band.first_movers` | `first_movers` |
| §5.1 P5.3 floor | `λ(1−δ)T/k`, U9 P5.3 — no code symbol, a formula | derived from `lam`, `target` |

**Orphan noted.** §5.1's "all 18 gains sit at ≈ 206" names the gains of the `delta=None` (gate)
solve. **The manifest stores no such field.** That orphan is row 18.

---

## Rows

```
CLAIM     §10 provenance block ↔ manifest header + frontier.sha256 (frontier.py:388)
ATTACK    Recomputed both digests from the files on disk rather than trusting the manifest;
          the manifest's `instance` path is a retired worktree, so the digest is the only
          thing that ties §10 to a live file. Also checked T == sum(m_delivered) and
          target == T/k as arithmetic identities the manifest could have gotten wrong.
VERDICT   VERIFIED
BASIS     Numeric equality (exact). shasum -a 256 /Users/ntlee/projects/td/instance_descaled_v2.json.gz
          = c89f182003aeec326228b6d7c14536b9ece0482b5f2d0ed2c8edea4e1be95286 == manifest
          instance_sha256. shasum -a 256 battery/results/draw_k18_v2_20260904/k18/draw.csv
          = 9e091c68f7fb9a24e44c03b87004091378227f378817ff5a53fd5908e2f0b87b == manifest
          draw_sha256. k=18, n_zips=3748, T=8523.2425369707 == fsum(m_delivered) to 0.0,
          target=473.51347427614996 == T/18 to 1e-9. θ=0.4, λ=0.3, filler_capture="theta",
          scipy 1.18.1 / numpy 2.5.2 / highspy 1.15.1 / pyscipopt 6.2.1 all exact.
ARTIFACT  docs/artifacts/U8-band-v2/verify_model_s10.py, section "0. PROVENANCE / ANCHORS"
          and "ORACLE A"; /usr/bin/shasum -a 256.
CAVEATS   Does not verify that instance_descaled_v2.json.gz is the *intended* instance, only
          that the file on disk today has the digest §10 records. The doc says the manifest is
          "gitignored"; `battery/results/` is indeed in .gitignore, though the `battery/results`
          symlink itself shows as untracked in this worktree — immaterial.
```

```
CLAIM     §10.0 gate numbers ↔ frontier.gate → eg_band.solve_band(U, M, None)
ATTACK    Did not read the manifest. Rebuilt the Setting from the instance + draw.csv +
          a re-run stage-2 roster and re-solved the unconstrained fibre from scratch,
          then compared every §10.0 digit. Also cross-checked V against the draw's own
          metrics.json winner.stage2_value, a file the frontier run only reads.
VERDICT   VERIFIED
BASIS     Numeric equality (exact, tolerance 0.0 — not the domain noise floor).
          Independent re-solve gives EG_S primal 96.53215175255613, upper 96.53215175853765,
          bracket 5.981519279885106e-09, n_cuts 30, M_max_dev_rel 0.3659737340801589,
          M_spread_rel 0.5737969902729481, V 95.75519165924108, delta0 0.00997002334741755,
          spread0 0.013684389361687034 — bit-identical to the manifest at every field, and to
          §10.0's printed digits (5.98e-9, 30 tangents, 0.36597373, 0.57379699,
          0.00997002334742, 0.01368438936169). spread0/delta0 = 1.3725533918 (doc) vs
          1.3725533917... recomputed, agrees to 5e-11. gap_to_V 0.7769600992965735 → 0.77696010.
          V - metrics.json winner.stage2_value = 1.42e-14.
ARTIFACT  docs/artifacts/U8-band-v2/oracle_gate.py
          `/Users/ntlee/projects/td/.venv/bin/python3 -u docs/artifacts/U8-band-v2/oracle_gate.py`
          (~40 s), output cached at /tmp/u8v2/oracle_gate_out.json.
CAVEATS   The re-solve uses the same eg_band code path, so it is a determinism/transcription
          oracle, not an independent solver. The SCIP cross-checks in the manifest were not
          re-run (row 9 uses the recorded values).
```

```
CLAIM     §10.0 "(`gate.delta_upper` is `null` in the manifest — no grid point records where
          the band would close.)" ↔ frontier.py:250
ATTACK    Read the field's definition instead of its value.
VERDICT   REFUTED
BASIS     frontier.py:250 is
              delta_upper=None if reference is None else sol.upper - reference
          `delta_upper` is the *signed gap between the unconstrained EG_S and a published
          reference value* passed with `--gate-reference`. It has no relation whatsoever to
          band closure, and it is not indexed by grid point. It is `null` here for exactly one
          reason: the v2 run was invoked without `--gate-reference` (`gate.reference = null`,
          `gate_reference = null`). The v1 manifest is the control: it carries
          `reference = 60.6974156139` and `delta_upper = 6.1139289186940005e-09`, which §9.0
          correctly reports as "6.11e-9 from the published 60.6974156139".
          Concrete failing input: pass `--gate-reference 96.53215175853765` to the same v2 run
          and `delta_upper` becomes `0.0` while the band still does not close at δ = 0.33.
VERDICT-IMPACT  None. The substantive claim the sentence supports (row 5) is established
          independently and correctly in the same paragraph by the certified numeric gap.
ARTIFACT  tools/measure/frontier.py:234-259 (read); verify_model_s10.py section "10.0 GATE",
          "info gate.reference / gate.delta_upper" and the V1 CROSS-CHECKS block.
CAVEATS   The parenthetical is the only place §10 misreads a field; every other field name it
          cites resolves to the value it quotes.
```

```
CLAIM     §10.0 "`above_V = true`, `matches_reference = true`, status `optimal`"
          ↔ frontier.py:246, 258
ATTACK    Checked whether `matches_reference` can be false on this run.
VERDICT   VERIFIED as transcription; the presentation is misleading.
BASIS     frontier.py:246: `matches = reference is None or bool(...)`. With
          `gate.reference = null`, `matches_reference` is **vacuously true** and carries no
          information. §10.0 lists it beside `above_V` and `status` as though it were a check
          that passed. v1 §9.0 was in a genuinely different position — it had a reference and
          reported the 6.11e-9 delta. `above_V = true` and `status = optimal` are real and
          independently reproduced (row 2).
ARTIFACT  tools/measure/frontier.py:246; verify_model_s10.py "10.0 GATE" NOTE lines.
CAVEATS   Not a false statement; a true statement quoted out of its guard. Grouped with row 3
          as the pair of gate-provenance defects.
```

```
CLAIM     §10.0 / §10.7-1 "the band never fully slackens on this grid": 0.33 < the
          unconstrained M-max-deviation 0.36597373, and EG^bal(0.33) sits 0.00117373 nats
          below EG_{S₁₈}
ATTACK    Tried to make the strict inequality an artifact of bracket noise, and tried to
          break the stated *reason* (a max-deviation argument is only sound if the
          unconstrained optimal m is unique).
VERDICT   VERIFIED
BASIS     Numeric equality plus a certified separation. From the independent gate re-solve,
          M_max_dev_rel = 0.3659737340801589 > 0.33 (exact match to the doc's 0.36597373).
          The separation is *certified*, not noise: EG_S_primal (a valid LOWER bound on EG_S)
          96.53215175255613 minus points[4].upper (a valid UPPER bound on EG^bal(0.33))
          96.53097802696875 = 0.0011737255873... → 0.00117373 as printed. That is 1.4e5 times
          the widest bracket in the run (8.44e-9) and 1.2e5 times tier-1 CERT_TOL. The
          conclusion therefore does not depend on m being unique at the unconstrained optimum,
          even though the sentence's *reason* would. v1 control: M_max_dev_rel = 0.3224108705
          < 0.33 and EG_S13_upper - points[4].upper = +2.95e-9, i.e. within bracket — which is
          what "closes the sandwich" meant at v1. The v1/v2 contrast is real.
ARTIFACT  oracle_gate.py (M_max_dev_rel); verify_model_s10.py "10.0 GATE" and the V1 block.
CAVEATS   §10 does not state the uniqueness caveat; it does not need to, because it also
          states the numeric gap. A reader who took only the max-deviation sentence would be
          relying on an unproved uniqueness.
```

```
CLAIM     §10.1 frontier table ↔ manifest points[i] (delta, primal, upper, bracket, n_cuts,
          slope, vertex.n_tight_bands, vertex.n_split, vertex.split_cap)
ATTACK    Transcribed all 50 table cells into the checker at the doc's own printed precision
          and demanded exact agreement after rounding — no tolerance. Then attacked the
          *field choice*: the manifest carries two valid upper bounds per point and §5.2 names
          `certified_upper` as the reported one.
VERDICT   VERIFIED
BASIS     Numeric equality at the printed precision (tolerance 0.0 after rounding).
          All five rows: primal to 10 dp, upper to 10 dp, width to 3 s.f., tangents (n_cuts)
          16/24/35/49/64, s_min to 4 dp 0.5856/0.5097/0.3440/0.1828/0.0549, `−V` to 6 dp
          0.724507/0.729999/0.742499/0.754932/0.775786, t 16/15/15/7/1, splits (cap)
          24(33)/25(32)/27(32)/21(24)/16(18). `split_cap == k-1+t` holds at all five.
          Every bracket ≤ 1e-8 (tier 1): 7.07/6.67/4.38/8.44/4.33 e-9. `slope == slope_raw`
          to the last bit at all five (the doc's "s_min matches slope_raw at every δ").
          FIELD CHOICE: the doc's column is labelled "[primal, upper]" and it is
          `points[i].upper` throughout, which is **the same convention §9.1 used for v1**, and
          the same field `frontier.shape` (frontier.py:358) consumes. It is a valid upper bound
          and it is the *looser* of the two, hence conservative. It differs from
          `certified_upper` by 0.0 / 5.27e-9 / 3.35e-9 / 5.01e-9 / 2.33e-9. At 8 dp the two
          agree at four of five points and differ only at δ = 0.33 (…802 vs …803).
ARTIFACT  verify_model_s10.py sections "10.1 FRONTIER TABLE" and "10.1 CROSS-FIELD".
CAVEATS   §10 never says which of the two fields its table reports, and §10.2's "direct"
          column silently switches to `certified_upper` (row 10). The mixture is inherited
          from the code, not introduced by §10.
```

```
CLAIM     §10.1 sandwich display, last entry `96.5321517586` for EG_{S₁₈}
ATTACK    Rounded every displayed digit of the seven-term chain from the manifest.
VERDICT   REFUTED
BASIS     Numeric equality at 10 dp. Six of seven entries are exact. The seventh:
          gate.EG_S_upper = 96.53215175853765, whose correct 10-dp rounding is
          **96.5321517585**; §10.1 prints **96.5321517586**. Error +1e-10.
          Concrete failing input: `round(96.53215175853765, 10)` → 96.5321517585.
VERDICT-IMPACT  None. The slip is in the conservative direction (it overstates an upper bound
          by 1e-10, two orders below tier-1 CERT_TOL 1e-8 and below every bracket in the run),
          and the chain's ordering is unaffected: the strict inequality against
          96.5309780270 survives with 1.17e-3 to spare.
ARTIFACT  verify_model_s10.py, "doc sandwich digits" assertion.
CAVEATS   Purely a display digit; the same number is written correctly as
          96.53215175853765 in §10.0.
```

```
CLAIM     §10.1 vertex / shape / split assertions: rank = n_support at all five; cleaning at
          1e-6 moved g by 0.0 relative, max band violation ≤ 5.95e-16; cleaned and raw split
          counts identical; every count under k−1+t and under 2k−1 = 35;
          integral_witness_in_band true at all five; monotone and concave, zero violations
ATTACK    Rather than reading `shape`, recomputed the secant slopes by hand from the grid;
          rather than reading `n_tight_bands`, recounted how many of the 18 reported masses
          sit on a band edge; rather than trusting `prop_gap`, reconstructed g from
          prop_gap + u_total/k and re-evaluated Σ log g against the reported primal.
VERDICT   VERIFIED
BASIS     Numeric equality / exact integer equality.
          rank == n_support: 3773/3773, 3773/3773, 3775/3775, 3769/3769, 3765/3765.
          clean_max_g_rel == 0.0 at all five; max clean_max_band_violation = 5.943e-16 ≤ 5.95e-16.
          n_split == n_split_raw at all five. n_split < split_cap and < 35 at all five.
          integral_witness_in_band true at all five. shape.monotone = shape.concave = true and
          both violation fields exactly 0.0.
          ORACLE (hand-recomputed secants on the grid, on certified_upper AND on points.upper —
          the two give the same four slopes to 6 dp): 0.547585, 0.416647, 0.248659, 0.090673 —
          strictly positive and strictly decreasing, so monotone and concave independently.
          ORACLE (masses): Σ m = 8523.2425369707 = T exactly at all five; max band violation of
          the reported m against tgt(1±δ) is ≤ 2.84e-13 at all five; the count of masses on a
          band edge (1e-6) is 16/15/15/7/1 — reproducing `t` exactly, from m alone.
          ORACLE (gains): Σ log(prop_gap + u_total/k) reproduces points[i].primal to ≤ 1.5e-14
          at all five, so prop_gap, u_total and primal are mutually consistent.
ARTIFACT  verify_model_s10.py sections "10.1 SANDWICH AND SHAPE" and the ORACLE blocks in
          "10.5 N9 PROPORTIONALITY".
CAVEATS   `is_vertex`, `gauge_pinned` and `degenerate` are taken from the manifest; the
          rank computation itself was not redone (it needs the full X, which the manifest
          does not store).
```

```
CLAIM     §10.1 SCIP cross-check table, and "Unlike v1, SCIP does not sit uniformly on one
          side here — 2.31e-9 *below* the OA's upper at δ = 0.02 … 2.27e-9 *above* it at 0.33"
ATTACK    Recomputed the differences against BOTH upper bounds the manifest carries, and ran
          the same comparison on the v1 manifest to test whether the "unlike v1" contrast is
          a property of the run or of the field chosen.
VERDICT   VERIFIED as stated; the "unlike v1" contrast is field-sensitive and noise-scale.
BASIS     Numeric equality. SCIP dual bounds 96.48519086840737 and 96.53097802923818, both
          `status = optimal`, both with limits/gap = limits/absgap = 0.0, dual reductions off,
          numerics/feastol 1e-9; walls 31.75760817527771 s and 32.24733304977417 s → 31.8 / 32.2.
          |OA.upper − SCIP| = 2.308937e-9 and 2.269431e-9 → 2.31e-9 and 2.27e-9. Both ≥ the OA
          primal (so the §5.2 unsafe case does not arise), and both inside 1e-6.
          FIELD SENSITIVITY: against `certified_upper` — which §5.2 names as the bound
          `Point.certified_upper` reports — SCIP is +2.956e-9 and +4.596e-9, i.e. ABOVE at both
          δ, exactly as at v1 (+3.248e-9, +3.860e-9 against v1's certified_upper; +1.579e-9,
          +1.102e-9 against v1's upper). So "does not sit uniformly on one side" is true of
          `points.upper` and false of `certified_upper`.
          The doc says "below the OA's **upper**", which names the right field, so the sentence
          is accurate. All four magnitudes are ≤ 5e-9, below tier-1 CERT_TOL 1e-8; nothing
          qualitative turns on the sign. This observation is not promoted to §10.7's findings.
ARTIFACT  verify_model_s10.py "10.1 SCIP CROSS-CHECK" and "V1 CROSS-CHECKS".
CAVEATS   SCIP was not re-run (a ~30 s solve each, but pyscipopt 6.2.1 on a 3748×18 native-log
          model was out of budget here). The recorded bounds are taken as given; only the
          arithmetic and the side-of-the-bound reasoning were attacked.
```

```
CLAIM     §10.2 D1′ table and NOT-SOFT verdict ↔ frontier.softness (frontier.py:309)
ATTACK    Recomputed the one-solve tangent bound from scratch as
          certified_upper[δ₀] + s_min·(δ − δ₀) rather than reading `softness[].bound`, and
          re-derived gap and slack from their definitions.
VERDICT   VERIFIED
BASIS     Numeric equality (exact to 1e-9, well inside tier 1).
          ORACLE tangent bound: 96.4796986046 + 0.5855858097256728·(δ − 0.0099700233) gives
          96.48557201658716 / 96.50313959087893 / 96.53241888136522 — bit-identical to
          softness[].bound and to the doc's 96.48557202 / 96.50313959 / 96.53241888.
          gap = bound − V reproduces 0.7303803573 / 0.7479479316 / 0.7772272221 → the doc's
          0.73038036 / 0.74794793 / 0.77722722 exactly.
          slack = bound − direct reproduces 3.8115e-4 / 5.4493e-3 / 2.2296e-2 → 3.81e-4 /
          5.45e-3 / 2.23e-2 at 3 s.f.; all positive, tangent_valid true at all three, so §10.A's
          guard genuinely passes.
          `direct` = certified_upper[1..3] exactly, i.e. §10.2 reports the *certified* bound
          while §10.1 reports the master's — both are in the manifest, the switch is the code's.
          Floor multiples: 0.7303803573/5e-3 = 146.076 → "146×" ✓; 0.7772272221/5e-3 = 155.445,
          matching STATE.md's "146–155×".
          Intercept claim: EG^bal(δ₀) − V = 0.72450694532 → "0.724507" ✓; /5e-3 = 144.90,
          printed as "145×" (rounded up, where the 146× above is a floor) — a 0.07 %
          presentational inconsistency, not a defect.
          soft = false at all three; softness_verdict string matches.
ARTIFACT  verify_model_s10.py "10.2 SOFTNESS (D1-prime)".
CAVEATS   The tangent's *validity* as a supergradient is witnessed only at the three grid
          points the manifest solves; nothing here re-derives U9 P4.3.
```

```
CLAIM     §10.3 "δ* ≤ δ₀ = 0.00997002334742 … the bisection runs zero solves"
ATTACK    Read bisect_delta_star's early-return branch to confirm zero solves is the
          lo_gap > 5e-3 branch and not a bisection that silently failed.
VERDICT   VERIFIED
BASIS     Exact equality. delta_star.n_solves = 0, value = lo = hi = 0.0099700233, verdict
          "delta* <= delta_0 = 0.0100: the gap is already 0.724507 nats at the left endpoint,
          so no band on [delta_0, 0.33] makes the premium soft". frontier.py:329-333 shows this
          is the `lo_gap > SMALL_NATS` early return, i.e. the strongest of the three cases, as
          §10.3 says. lo_gap is computed from certified_upper (frontier.py:627) = 0.724507 ✓.
ARTIFACT  verify_model_s10.py "10.3 DELTA*"; tools/measure/frontier.py:325-352 (read).
CAVEATS   None material.
```

```
CLAIM     §10.4 N8 table takes rep IDs from the manifest's `staff` array; the IDs are aligned
          with their ν values
ATTACK    This is the row most likely to be silently wrong, so it got three attacks:
          (i) rebuilt the ν>0 / ν<0 / ν=0 name lists from `nu` + `staff` and demanded
          set-and-order equality with all 25 names §10.4 prints; (ii) printed what the
          `districts` array would have given at the same indices, to show the two are not
          interchangeable; (iii) cross-checked the list *lengths* against the independently
          computed n_binding_upper / n_binding_lower, which come from mu_plus/mu_minus > 1e-9,
          a different code path from `nu = mu_p - mu_m`.
VERDICT   VERIFIED
BASIS     Exact list equality. `staff` is the correct array: it is
          `tuple(sigma[d] for d in districts)` (frontier.py:215), i.e. the rep staffing the
          district at that index, and every per-agent vector (`nu`, `m`, `prop_gap`,
          `u_total`, `g_delivered`) is built on the same index. My independent re-run of
          build_setting reproduces `staff` in the same order, element for element.
          δ₀: ν>0 = [R0018, R0013, R0021, R0038, R0028, R0014, R0017, R0015];
              ν<0 = [R0004, R0001, R0000, R0006, R0009, R0003, R0005, R0002];
              ν=0 = [R0010, R0008] — all three lists match §10.4 exactly, in order.
          0.02: ν<0 loses R0009 → 7 names, ν=0 gains it → [R0010, R0009, R0008]. Matches.
          0.05 / 0.10 / 0.33: ν>0 empty ("—" in the doc); ν<0 = [R0004,R0001,R0000,R0003,
              R0005,R0002] / [R0001,R0000,R0003,R0005] / [R0000]. Matches.
          Cross-check: |ν>0| == n_binding_upper and |ν<0| == n_binding_lower at all five
          (8/8, 8/7, 0/6, 0/4, 0/1) — so no multiplier hides in (0, 1e-9].
          MISALIGNMENT TEST: the same indices in `districts` give
          [D07, D15, D08, D13, D09, D06, D02, D10] — the doc prints none of these, so it did
          not read the wrong array.
          Corroboration: at δ = 0.33 `vertex.tight_agents = [2]` and `staff[2] = 'R0000'`,
          the single rep §10.4 names. Independent of `nu` entirely.
          q ranges: [3.33e-8, 0.2553] / [3.35e-8, 0.2551] / [3.41e-8, 0.2557] /
          [3.49e-8, 0.2569] / [3.73e-8, 0.2649] — exact at the printed precision.
          gauge_pinned true at all five. §10.4's narrative counts (16 of 18 tight, split
          eight-and-eight; only lower bands bind from 0.05 outward; force-fed group 6 → 4 → 1)
          all reproduce.
ARTIFACT  verify_model_s10.py "10.4 N8 BAND DUALS"; oracle_gate.py (staff order).
CAVEATS   ν itself is taken from the manifest; the LP duals were not re-solved per grid point.
```

```
CLAIM     §10.4 footnote + §10.7-2: degenerate zero-dual "tight" bands appear at δ = 0.05
          (9 of 12) and δ = 0.10 (3 of 14), and only there
ATTACK    Recomputed t − |signed ν| and (zero-dual count) − n_agents_band_slack independently
          and checked they agree — they are different quantities and only coincide if the
          degeneracy story is right. Then checked the "confined to the two interior points"
          half by running the same arithmetic at δ₀, 0.02 and 0.33.
VERDICT   VERIFIED
BASIS     Exact integer equality. Per grid point (t, |signed ν|, zero-dual, n_agents_band_slack):
            δ₀   (16, 16, 2, 2)   → t − signed = 0, zero − slack = 0
            0.02 (15, 15, 3, 3)   → 0, 0
            0.05 (15,  6, 12, 3)  → 9, 9      ← the doc's "9 of the 12"
            0.10 ( 7,  4, 14, 11) → 3, 3      ← the doc's "3 of the 14"
            0.33 ( 1,  1, 17, 17) → 0, 0
          The two independently computed excesses agree at every point, and
          n_agents_band_slack + t = 18 at every point, which is the consistency identity the
          degeneracy story requires. The doc's specific numbers (n_agents_band_slack = 3 at
          0.05, = 11 at 0.10; t equal to the signed-ν count exactly at 16/15/1 with slack
          2/3/17) are all exact. The claim that this is a v2-only wrinkle is not tested here
          beyond the v2 grid.
ARTIFACT  verify_model_s10.py "10.4 DEGENERATE ZERO-DUAL CLAIM (finding b)".
CAVEATS   "v2-only" is asserted relative to v1's §9.4, which was not re-derived; only the v2
          side of the contrast is checked.
```

```
CLAIM     §10.5 N9 proportionality: delivered min gap −12.0248 with 3 of 18 below (R0038,
          R0013, R0028); frontier minima +18.5526 … +26.6363 with 0 below; u_i(Z)/k ≈ 181.9–187.1;
          erosion ≈ 30 %
ATTACK    Recomputed prop_gap from its definition g − u_total/k rather than reading it, and
          re-derived the reps' identities through `staff` (row 12's alignment question again).
VERDICT   VERIFIED
BASIS     Numeric equality at the printed precision. ORACLE: g_delivered − u_total/18
          reproduces prop_gap_delivered to ≤ 1e-10 at all 18 entries. min = −12.024837703 →
          −12.0248 ✓. Exactly three entries are negative, at staff indices 8, 5, 9 =
          R0038 (−12.02), R0013 (−7.79), R0028 (−6.69) — the doc's list and order.
          Per-point minima: 18.5526 / 20.0169 / 22.2690 / 24.6734 / 26.6363, all exact at 4 dp;
          zero negative entries at all five. u_total/18 spans 181.90060605833045 to
          187.08298901026893 → "181.9–187.1" ✓. Erosion (26.6363−18.5526)/26.6363 = 30.35 %
          → "about 30 %" ✓. v1 control: 4 of 13 below, erosion 32.0 % — the doc's "4 of 13"
          and "32 %" both check out against the v1 manifest.
ARTIFACT  verify_model_s10.py "10.5 N9 PROPORTIONALITY" and "V1 CROSS-CHECKS".
CAVEATS   The interpretive claim that "the two business goals conflict at the delivered map,
          not at the fractional optimum" is an economic reading, not a number.
```

```
CLAIM     §10.6 / §10.7-3: "No exact MBB ties (n_exact_ties = 0, tied_M_share = 0.0) — unlike
          v1's 75-zip tie block"; top 25 carry 33.09 of M = 0.39 % of T, owned by R0008 or
          R0021, margins 5.6e-7 to 2.5e-6; support 3773 vs expected 3781, diff 8, degenerate
ATTACK    This row is load-bearing for U4-disp, so it was attacked hardest. Checked the field
          semantics (is n_exact_ties over all zips or only the reported 25?), recomputed the
          tie count from the reported margins, recomputed the M-share two ways, recomputed
          `expected` from its formula, and pulled v1's 75 from the v1 manifest rather than
          from §9.
VERDICT   VERIFIED
BASIS     Exact equality. n_exact_ties = 0, tied_M_share = 0.0 in the manifest.
          Semantics: frontier.py:685-686 computes n_exact_ties from `n_tied` and
          tied_M_share = M[fm.margin <= 1e-12].sum()/T over the **full** margin array, not the
          reported top-25 — so a zero here is a statement about all 3748 zips, which is what
          U4-disp needs.
          Corroboration from the reported set: the 25 margins are sorted ascending with
          min 5.643275375683861e-07 (→ 5.6e-7) and max 2.4815965231477377e-06 (→ 2.5e-6);
          none is ≤ 1e-12, consistent with a zero tie count.
          Owner counts: R0021 × 22, R0008 × 3 — "just two reps" ✓, and no third rep appears.
          Σ M over the 25 = 33.093461 → 33.09 ✓; /T = 0.0038827313 → 0.39 % ✓; Σ M_share
          reproduces the same figure to 1e-15.
          Support: n_support 3773, expected 3781 = n + k − 1 + t = 3748 + 17 + 16 (the code's
          own formula, eg_band.py:347), diff 8, degenerate = (n_support != expected) = True
          (eg_band.py:351) — so §10.6's inference is the code's own criterion, not a gloss.
          first_movers.vertex is field-for-field identical to points[0].vertex, so the δ₀
          attribution is right.
          v1 control, read from the v1 manifest: n_exact_ties = 75, and its 25 reported
          margins are all exactly 0.0. So "unlike v1's 75-zip tie block" is correct.
CONSEQUENCE  U4-disp's premise — that a first-mover list *can* be named on v2 — is NOT
          supported by this manifest, and §10.6 says so correctly: the dual is degenerate
          (diff 8), so ν is one dual optimum among many and no ordering is named from it alone.
          §10.6's fallback object (the 25-zip near-tie set on R0008/R0021, 0.39 % of T) is
          reproduced exactly.
ARTIFACT  verify_model_s10.py "10.6 FIRST MOVERS" and "V1 CROSS-CHECKS";
          tools/measure/frontier.py:369-384, 679-686; td/solvers/eg_band.py:347-351, 362-374.
CAVEATS   `fm.margin` itself was not recomputed (it needs the full U and duals at δ₀). A
          fabricated `n_exact_ties = 0` with a genuinely tied margin array would survive this
          row — but the 25 smallest margins being 5.6e-7 and up makes that implausible.
```

```
CLAIM     §10.6 "margins from 5.6e-7 to 2.5e-6 — an order of magnitude tighter than v1's ties
          but not exact"
ATTACK    Asked what "tighter" can mean when the comparison object is an exact tie.
VERDICT   REFUTED (as written)
BASIS     v1's tie block has margin **exactly 0.0** at all 25 reported zips (v1 manifest,
          first_movers.zips). A margin of 5.6e-7 is looser than 0.0, not "an order of magnitude
          tighter" — nothing is tighter than an exact tie. The sentence attaches "tighter" to
          "margins", where it is unsatisfiable.
          The reading that IS supported is about the tie block's *mass*: v1 tied_M_share
          0.02901053148638934 vs v2's top-25 share 0.0038827313497712523, a ratio of 7.47× —
          "an order of magnitude" as a round figure. Alternatively the block *size*, 25 vs 75
          zips (3×), which is weaker.
          Concrete failing input: min(v1 margins) = 0.0 < 5.643e-7 = min(v2 margins).
VERDICT-IMPACT  None on any number; §10.7-3, which is the finding that carries downstream,
          states only "n_exact_ties = 0; the near-tie set is small (25 zips, 0.39 % of T) and
          concentrated on two reps" — all of which is verified in row 15.
ARTIFACT  verify_model_s10.py "V1 CROSS-CHECKS" and the first-movers block.
CAVEATS   A wording defect. If the intended meaning is the mass ratio, the sentence needs to
          say so and to name 2.90 % → 0.39 %.
```

```
CLAIM     §5.1 replaced constants: λ(1−δ)T/k = `140.638` at δ = δ₀ = 0.0099700233 and
          `95.176` at δ = 0.33, with λ = 0.3, T/k = 473.51347427615
ATTACK    Recomputed from the formula with both the full-precision δ₀ and the doc's printed
          10-digit δ₀, to see whether the printed constant is stable under that truncation.
VERDICT   VERIFIED
BASIS     Numeric equality at 3 dp.
            0.3·(1 − 0.00997002334741755)·473.51347427614996 = 140.63776016468998 → 140.638 ✓
            0.3·(1 − 0.0099700233)·473.51347427614996        = 140.63776017142584 → 140.638 ✓
            0.3·(1 − 0.33)·473.51347427614996                =  95.17620832950614 →  95.176 ✓
          δ₀ is printed in §5.1 as 0.0099700233, which is round(delta0, 10) ✓.
          The companion sentence "the seed clears that floor by a factor of ~1.3
          (u_i(Z)/k ≈ 182–187)" also checks: u_total/18 spans 181.90–187.08 (→ 182–187 rounded)
          and min/floor = 181.90060605833045 / 140.63776016468998 = 1.2934 → ~1.3 ✓.
          The two v1 constants (63.113, 42.451) are gone from §5.1 — the residue is cleared.
          For the record they were also correct at v1: 0.3(1−δ₀^v1)T₁₃/k = 63.11023791923079
          and 0.3(1−0.33)T₁₃/k = 42.45137297364231.
ARTIFACT  verify_model_s10.py "5.1 REPLACED CONSTANTS"; oracle_gate.py / oracle_gate_v1.py.
CAVEATS   U9 P5.3 itself is not re-derived; only its instantiation is arithmetic-checked.
```

```
CLAIM     §5.1 "every `delta=None` solve is the gate on the real instance, where all 18 gains
          sit at ≈ `206` against a floor of `140.638`, so no published number depends on the
          distinction"
ATTACK    The manifest has no field for the gate solve's gains — this is the one §10/§5.1
          number with no manifest counterpart, so the only way to test it was to re-run the
          gate and read `sol.g`. Also tested the sentence as a *range* claim, since it says
          "all 18 gains sit at".
VERDICT   REFUTED
BASIS     Independent re-solve of `eg_band.solve_band(U, M, None)` on the same instance and
          draw. The 18 gains at the unconstrained optimum are, sorted:
            211.786, 211.792, 211.792, 211.794, 211.795, 211.796, 211.796, 211.796, 211.796,
            211.797, 211.797, 211.797, 211.798, 211.799, 211.801, 211.802, 223.615, 228.663
          min 211.78636234207835, max 228.6634264451535, mean 213.3896676979576.
          **They do not sit at ≈ 206.** The nearest single figure is ≈ 212 (16 of 18), with two
          outliers at 223.6 and 228.7. `206` is instead `mean(g_delivered) = 206.01382253741815`
          — the mean of the *delivered draw's* gains, a different object, whose own spread is
          169.88 to 293.83, so "all 18 … at ≈ 206" is false of that object too (−18 % to +43 %).
          Concrete failing inputs: gate gain 211.78636234207835 (2.8 % above 206) and
          228.6634264451535 (11.0 % above 206); delivered gain 169.8757683552205 (17.5 % below)
          and 293.8256217219448 (42.6 % above).
          The same re-solve reproduces every other §10.0 gate number bit-for-bit (row 2), so
          this is not a stale-artifact problem — the number was never in the artifact.
VERDICT-IMPACT  The *conclusion* survives: min gate gain 211.786 > the 140.638 floor by a
          factor 1.506, so "no published number depends on the distinction" holds, and ĝ > 0
          is never at risk on the v2 gate. Only the quoted magnitude and the named object are
          wrong.
NOTE      The v1 sentence this replaced ("all 13 gains sit at ≈ 90") was wrong in the same
          shape but a different way: the v1 gate gains are 103.6–136.8 (mean 106.9), and 90 was
          the *seed* value u_i(Z)/k ≈ 88.7–92.7 that the same sentence already quotes. So the
          v2 rewrite did not inherit the v1 number's meaning; it substituted a third quantity.
ARTIFACT  docs/artifacts/U8-band-v2/oracle_gate.py and oracle_gate_v1.py
          `/Users/ntlee/projects/td/.venv/bin/python3 -u docs/artifacts/U8-band-v2/oracle_gate.py`
          `/Users/ntlee/projects/td/.venv/bin/python3 -u docs/artifacts/U8-band-v2/oracle_gate_v1.py`
CAVEATS   The claim is about "every delta=None solve"; only the final iterate's gains were
          recovered, not the intermediate OA iterates. The floor argument is unaffected —
          the seed is u_i(Z)/k ≥ 181.90, also above 140.638, so both ends of the loop clear it.
```

```
CLAIM     §9.1 residue cleared ("take the smaller" → "SCIP is a cross-check … never adopts
          SCIP's number"); §9 otherwise still v1 and not silently mutated
ATTACK    Read the full working-tree diff of docs/MODEL_U8-band.md rather than the rendered
          file, so that any edit anywhere in §9 would show.
VERDICT   VERIFIED
BASIS     `git diff -U3 docs/MODEL_U8-band.md` = 198 insertions, 7 deletions, in exactly three
          hunks: (a) §5.1 lines ~257-266, the constants and the "13 gains ≈ 90" sentence;
          (b) §9.1 lines ~462-467, the two-line residue; (c) the §10 append at EOF.
          No other line of §9 changed: §9.0, the §9.1 table, §9.2–§9.7 are byte-identical to
          the committed v1 text.
          The replacement reads "Per §5.2, SCIP is a cross-check on the reported bound, not a
          source of it: `Point.certified_upper` never adopts SCIP's number, so the OA's value
          stands regardless of which cross-check happens to come out smaller." That matches
          §5.2 at :309-318 ("`Point.certified_upper` … takes the minimum of the master's value
          and the solver-free `O(nk)` dual **only**, and never adopts SCIP's number") and it
          matches the code: frontier.py:131-135 is
              return float(min(self.upper, self.dual_check.bound))
          with no SCIP term anywhere in Point.certified_upper. The phrase "take the smaller"
          appears nowhere in the file. §10.1 repeats the same framing consistently.
ARTIFACT  /usr/bin/git -C <worktree> diff -U3 docs/MODEL_U8-band.md;
          tools/measure/frontier.py:130-135 (read); docs/MODEL_U8-band.md:297-318 (read).
CAVEATS   §5.2 cites "frontier.py:126-131" for Point.certified_upper; the property is actually
          at 130-135 in the current file (the dataclass field block starts at 104). A stale
          line reference, pre-existing, not part of this change.
```

```
CLAIM     §10.7-6 the manifest's `instance` field is stale; §10.7-7 figures/u8_band/frontier.png
          has not been regenerated and still shows k = 13
ATTACK    Checked the git history of the PNG rather than its content, and checked that the
          stale path's *content* is nonetheless the live one via the digest.
VERDICT   VERIFIED
BASIS     Exact. manifest.instance =
          '/Users/ntlee/projects/td/.claude/worktrees/A1/instance_descaled_v2.json.gz' — a
          retired worktree, as §10's note says. (manifest.draw_dir is stale in the same way;
          §10 mentions only `instance`.) The digest at that path equals the digest of the live
          /Users/ntlee/projects/td/instance_descaled_v2.json.gz (row 1), so the note's "unaffected"
          is right.
          figures/u8_band/frontier.png: last touched by commit 69997ac "U8-band: eg_band.py +
          frontier.py + tests + MODEL + figures/u8_band" (the v1 commit) and clean in the
          working tree (`git status --short figures/` is empty). It has not been regenerated
          for v2, exactly as §10 states, and §10 references no figure. `figures/` was clean
          before this verification run and remains clean.
ARTIFACT  /usr/bin/git log --oneline -2 -- figures/u8_band/frontier.png;
          /usr/bin/git status --short figures/; /usr/bin/shasum -a 256.
CAVEATS   The PNG's pixel content was not inspected; the git history is the evidence.
```

```
CLAIM     §10 does not contradict STATE.md ## Facts for v2
ATTACK    Took each of STATE.md's six v2 numbers and tried to derive a conflicting value from
          the manifest.
VERDICT   VERIFIED (no contradiction)
BASIS     Numeric equality at STATE.md's precision.
            k = 18 ✓; δ₀ = 0.009970 ✓ (0.00997002334742);
            V = 95.755192 ✓ (95.75519165924108); EG_{S₁₈} = 96.532152 ✓ (96.53215175255613);
            premium 0.72–0.78 nats ✓ (0.724507 at δ₀ … 0.775786 at 0.33; gate gap 0.77696);
            NOT SOFT ✓; D1′ 146–155× ✓ (146.08 … 155.44); no δ* ✓ (n_solves = 0, δ* ≤ δ₀);
            balance free, 33-fold widening buys 0.051 nats ✓ (0.33/δ₀ = 33.1;
            certified_upper[4] − certified_upper[0] = 0.05127942 and the same on points.upper).
          Roster 0.249 nats, match gap 0, map gap 0.663 are U7 numbers; §10 makes no claim
          about them, so there is nothing to contradict.
          Minor omission (not a contradiction): STATE.md identifies the draw as "k=18 seed 2";
          §10 says only "the live v2 instance's committed draw" and never names the seed, where
          §9 named "the committed seed-3 draw".
ARTIFACT  verify_model_s10.py "STATE.md FACTS CONSISTENCY"; STATE.md:76-100 (read).
CAVEATS   Only the ## Facts block was compared; ## Now / ## Next were not.
```

```
CLAIM     Acceptance 5 (two full re-runs byte-identical apart from `written` and
          `wall_seconds`) for the v2 run
ATTACK    Looked for the claim in §10 and for evidence in the manifest.
VERDICT   INCONCLUSIVE — the claim is not made
BASIS     §9 records acceptance 5 explicitly for v1 ("Two full re-runs are byte-identical apart
          from `written` and `wall_seconds`"). §10 makes no such statement, and the manifest
          carries no re-run marker. What is missing is the claim itself, so there is nothing to
          verify or refute. Partial positive evidence: the gate portion re-ran bit-identically
          (row 2), which is consistent with the determinism acceptance 5 asserts, but it
          exercises one of six solves and none of the SCIP or first-mover paths.
ARTIFACT  Would need `python3 -m tools.measure.frontier <instance> <draw> --out …` twice and a
          json diff excluding `written`/`wall_seconds`; not run (two SCIP solves at ~32 s each
          plus five band solves, out of budget here).
CAVEATS   If §10 is meant to mirror §9's template completely, the absence of an acceptance-5
          line is itself a gap worth closing.
```

---

## What the attack did not cover

* The SCIP cross-check bounds were not regenerated; §10.1's two SCIP rows are checked only for
  arithmetic and side-of-the-bound consistency.
* `rank`, `is_vertex` and `fm.margin` are taken from the manifest — they need the full `X` and
  duals, which the manifest does not store. `t`, `expected`, `split_cap` and the gains WERE
  re-derived from stored vectors and all agreed.
* No proposition of U9 (P2.5, P4.3, P5.3, P5.4) is re-proved; only their instantiations are
  arithmetic-checked. That is `VERIFY_U9-bandthm`'s job.
* v1 §9 was used as a control (its manifest was read) but was not itself re-verified.

## Artifacts

| Path | What it does | Command |
|---|---|---|
| `docs/artifacts/U8-band-v2/verify_model_s10.py` | 360 assertions transcribing every §10 and §5.1 number against the manifest, plus six independent oracles (V, δ₀, spread₀, prop_gap, Σ log g, band feasibility of m, secant concavity) | `.venv/bin/python3 docs/artifacts/U8-band-v2/verify_model_s10.py` |
| `docs/artifacts/U8-band-v2/oracle_gate.py` | Re-solves the v2 gate from instance + draw; reproduces §10.0 and recovers the gate gains §5.1 quotes | `.venv/bin/python3 -u docs/artifacts/U8-band-v2/oracle_gate.py` (~40 s) |
| `docs/artifacts/U8-band-v2/oracle_gate_v1.py` | Same on v1/k=13, as the control for rows 5, 9, 16, 18 | `.venv/bin/python3 -u docs/artifacts/U8-band-v2/oracle_gate_v1.py` |

Run all three with cwd `/Users/ntlee/projects/td/.claude/worktrees/w2-phase0` and the repo-root
venv. `verify_model_s10.py` reads `/tmp/u8v2/oracle_gate_out.json` for the gate-gains row; run
`oracle_gate.py` first or that one row is skipped.
