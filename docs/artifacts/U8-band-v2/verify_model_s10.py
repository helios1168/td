"""Adversarial verification of docs/MODEL_U8-band.md section 10 (v2, k=18) against the
manifest battery/results/u8_band_v2_20260904/draw_k18_v2_20260904.json.

Every check is stated as (claim-in-doc, value-recomputed-from-manifest-or-oracle).
Run:  /Users/ntlee/projects/td/.venv/bin/python3 /tmp/u8v2/verify_model_s10.py
from cwd /Users/ntlee/projects/td/.claude/worktrees/w2-phase0
"""
from __future__ import annotations

import json
import math
import pathlib

ROOT = pathlib.Path('/Users/ntlee/projects/td/.claude/worktrees/w2-phase0')
V2 = ROOT / 'battery/results/u8_band_v2_20260904/draw_k18_v2_20260904.json'
V1 = ROOT / 'battery/results/u8_band_20260904/draw_k13_20260901.json'

M = json.loads(V2.read_text())
M1 = json.loads(V1.read_text()) if V1.exists() else None

PASS, FAIL = [], []


def chk(name, doc, got, tol=0.0, mode='num'):
    if mode == 'num':
        ok = abs(float(doc) - float(got)) <= tol
    elif mode == 'eq':
        ok = doc == got
    else:
        raise ValueError(mode)
    (PASS if ok else FAIL).append((name, doc, got))
    print(('  ok  ' if ok else 'FAIL  ') + f'{name}: doc={doc!r} got={got!r}')
    return ok


def sec(t):
    print('\n' + '=' * 78 + f'\n{t}\n' + '=' * 78)


k = M['k']
T = M['T']
Vd = M['V_delivered']
tgt = M['target']
pts = M['points']
cu = M['certified_upper']
staff = M['staff']

# --------------------------------------------------------------- 0. provenance
sec('0. PROVENANCE / ANCHORS')
chk('k', 18, k, mode='eq')
chk('n_zips', 3748, M['n_zips'], mode='eq')
chk('T', 8523.2425369707, T)
chk('T/k == target', T / k, tgt, tol=1e-9)
chk('target 473.51347427615', 473.51347427615, tgt, tol=5e-12)
chk('delta0 0.00997002334742', 0.00997002334742, M['delta0'], tol=5e-15)
chk('V_delivered', 95.75519165924108, Vd)
chk('theta', 0.4, M['theta'])
chk('lam', 0.3, M['lam'])
chk('filler_capture', 'theta', M['filler_capture'], mode='eq')
for lib, v in [('scipy', '1.18.1'), ('numpy', '2.5.2'), ('highspy', '1.15.1'),
               ('pyscipopt', '6.2.1')]:
    chk(f'version {lib}', v, M['solver_versions'][lib], mode='eq')
chk('instance_sha256 prefix', 'c89f182003aeec32', M['instance_sha256'][:16], mode='eq')
chk('draw_sha256 prefix', '9e091c68f7fb9a24', M['draw_sha256'][:16], mode='eq')
print(f"  info  manifest instance field = {M['instance']}")
print(f"  info  manifest draw_dir field = {M['draw_dir']}")

# ---------------------------------------- ORACLE: recompute V, delta0, spread0
sec('ORACLE A: recompute V, delta0, spread0, prop_gap from the manifest raw vectors')
g = M['g_delivered']
m = M['m_delivered']
u = M['u_total']
V_re = math.fsum(math.log(x) for x in g)
chk('V = sum log g_delivered (oracle)', Vd, V_re, tol=1e-12)
d0_re = max(abs(x - tgt) for x in m) / tgt
chk('delta0 = max|m-T/k|/(T/k) (oracle)', M['delta0'], d0_re, tol=1e-14)
sp_re = (max(m) - min(m)) / (sum(m) / len(m))
chk('spread0 = (max-min)/mean(m) (oracle)', M['spread0'], sp_re, tol=1e-14)
chk('T = sum(m_delivered) (oracle)', T, math.fsum(m), tol=1e-8)
pg_re = [gi - ui / k for gi, ui in zip(g, u)]
chk('prop_gap_delivered = g - u_total/k (oracle) max|diff|', 0.0,
    max(abs(a - b) for a, b in zip(pg_re, M['prop_gap_delivered'])), tol=1e-10)

# ------------------------------------------------------------------ 1. sec 10.0
sec('10.0 GATE AND delta_0')
G = M['gate']
chk('EG_S primal', 96.53215175255613, G['EG_S_primal'])
chk('EG_S upper', 96.53215175853765, G['EG_S_upper'])
chk('bracket 5.98e-9', 5.98e-9, G['bracket'], tol=5e-12)
chk('n_cuts 30', 30, G['n_cuts'], mode='eq')
chk('gap_to_V 0.77696010', 0.77696010, G['gap_to_V'], tol=5e-9)
chk('above_V', True, G['above_V'], mode='eq')
chk('matches_reference', True, G['matches_reference'], mode='eq')
chk('status optimal', 'optimal', G['status'], mode='eq')
chk('spread0 0.01368438936169', 0.01368438936169, M['spread0'], tol=5e-15)
chk('spread0/delta0 = 1.3725533918', 1.3725533918, M['spread0'] / M['delta0'], tol=5e-11)
chk('M_max_dev 0.36597373', 0.36597373, G['M_max_dev_rel'], tol=5e-9)
chk('M_spread 0.57379699', 0.57379699, G['M_spread_rel'], tol=5e-9)
print(f"  info  gate.reference = {G['reference']!r}  gate.delta_upper = {G['delta_upper']!r}"
      f"  gate_reference = {M['gate_reference']!r}")
print('  NOTE  matches_reference is `reference is None or ...` (frontier.py:246) -> '
      'VACUOUSLY TRUE when reference is None')
print('  NOTE  delta_upper = None if reference is None else sol.upper - reference '
      '(frontier.py:250) -> null because no --gate-reference was passed; it has NO '
      'relation to "where the band would close"')
chk('doc EG^bal(0.33)=96.53097802696875 == points[4].upper', 96.53097802696875,
    pts[4]['upper'], tol=0.0)
chk('gap EG_S - EG^bal(0.33) = 0.00117373', 0.00117373,
    G['EG_S_primal'] - pts[4]['upper'], tol=5e-9)
chk('0.33 < M_max_dev', True, 0.33 < G['M_max_dev_rel'], mode='eq')

# ------------------------------------------------------------------ 2. sec 10.1
sec('10.1 FRONTIER TABLE')
doc_rows = [
    # delta, primal, upper, width, tangents, s_min, minusV, t, split, cap
    (0.0099700233, 96.4796985975, 96.4796986046, 7.07e-9, 16, 0.5856, 0.724507, 16, 24, 33),
    (0.02, 96.4851908640, 96.4851908707, 6.67e-9, 24, 0.5097, 0.729999, 15, 25, 32),
    (0.05, 96.4976902647, 96.4976902691, 4.38e-9, 35, 0.3440, 0.742499, 15, 27, 32),
    (0.10, 96.5101232221, 96.5101232306, 8.44e-9, 49, 0.1828, 0.754932, 7, 21, 24),
    (0.33, 96.5309780226, 96.5309780270, 4.33e-9, 64, 0.0549, 0.775786, 1, 16, 18),
]
for r, p in zip(doc_rows, pts):
    d = r[0]
    print(f'-- delta {d}')
    chk(' delta', d, p['delta'], tol=1e-12)
    chk(' primal(10dp)', r[1], round(p['primal'], 10), tol=0.0)
    chk(' upper(10dp)  [doc col "upper" == points.upper]', r[2], round(p['upper'], 10), tol=0.0)
    chk(' width', r[3], p['bracket'], tol=5e-12)
    chk(' tangents', r[4], p['n_cuts'], mode='eq')
    chk(' s_min(4dp)', r[5], round(p['slope'], 4), tol=0.0)
    chk(' -V(6dp) from upper', r[6], round(p['upper'] - Vd, 6), tol=0.0)
    chk(' t', r[7], p['vertex']['n_tight_bands'], mode='eq')
    chk(' splits', r[8], p['vertex']['n_split'], mode='eq')
    chk(' cap', r[9], p['vertex']['split_cap'], mode='eq')
    chk(' cap == k-1+t', k - 1 + p['vertex']['n_tight_bands'], p['vertex']['split_cap'], mode='eq')
    chk(' bracket <= tier1 1e-8', True, p['bracket'] <= 1e-8, mode='eq')
    chk(' slope == slope_raw', p['slope'], p['slope_raw'], tol=1e-12)
    chk(' rank == n_support', p['vertex']['rank'], p['vertex']['n_support'], mode='eq')
    chk(' n_split == n_split_raw', p['vertex']['n_split'], p['vertex']['n_split_raw'], mode='eq')
    chk(' clean_max_g_rel == 0.0', 0.0, p['vertex']['clean_max_g_rel'], tol=0.0)
    chk(' clean_max_band_violation <= 5.95e-16', True,
        p['vertex']['clean_max_band_violation'] <= 5.95e-16, mode='eq')
    chk(' n_split < cap', True, p['vertex']['n_split'] < p['vertex']['split_cap'], mode='eq')
    chk(' n_split < 2k-1=35', True, p['vertex']['n_split'] < 35, mode='eq')
    chk(' integral_witness_in_band', True, p['integral_witness_in_band'], mode='eq')
    chk(' is_vertex', True, p['vertex']['is_vertex'], mode='eq')
    chk(' status optimal', 'optimal', p['status'], mode='eq')

sec('10.1 CROSS-FIELD: doc table "upper" vs manifest certified_upper')
for i, p in enumerate(pts):
    print(f"  delta={p['delta']:<12} points.upper={p['upper']!r}  "
          f"certified_upper={cu[i]!r}  diff={p['upper'] - cu[i]:.3e}  "
          f"dual_bound={p['dual_check']['bound']!r}")
print('  NOTE  Point.certified_upper = min(upper, dual_check.bound)  (frontier.py:131-135);'
      '\n        softness.direct, delta*, and shape all use certified_upper (frontier.py:606,'
      ' 627-628, 470).')
print('  NOTE  doc 10.1 column is labelled "[primal, upper]" and matches points.upper exactly '
      '(same convention as v1 section 9.1).')
print('  8dp round of certified_upper (the plan anchors): '
      + ', '.join(f'{v:.8f}' for v in cu))
print('  8dp round of points.upper (what section 10 tabulates): '
      + ', '.join(f"{p['upper']:.8f}" for p in pts))

sec('10.1 SANDWICH AND SHAPE')
chain = [Vd] + [p['upper'] for p in pts] + [G['EG_S_primal']]
chk('sandwich strictly increasing on points.upper', True,
    all(a < b for a, b in zip(chain, chain[1:])), mode='eq')
chk('sandwich strictly increasing on certified_upper', True,
    all(a < b for a, b in zip([Vd] + cu + [G['EG_S_primal']],
                              ([Vd] + cu + [G['EG_S_primal']])[1:])), mode='eq')
doc_chain = [95.7551916592, 96.4796986046, 96.4851908707, 96.4976902691,
             96.5101232306, 96.5309780270, 96.5321517586]
real_chain = [round(Vd, 10)] + [round(p['upper'], 10) for p in pts] + [round(G['EG_S_upper'], 10)]
chk('doc sandwich digits', doc_chain, real_chain, mode='eq')
S = M['shape']
chk('shape.monotone', True, S['monotone'], mode='eq')
chk('shape.concave', True, S['concave'], mode='eq')
chk('max_monotonicity_violation 0.0', 0.0, S['max_monotonicity_violation'], tol=0.0)
chk('max_concavity_violation 0.0', 0.0, S['max_concavity_violation'], tol=0.0)
# independent concavity oracle on certified_upper
grid = M['grid']
slopes = [(cu[i + 1] - cu[i]) / (grid[i + 1] - grid[i]) for i in range(4)]
print('  oracle secant slopes on certified_upper:', [f'{s:.6f}' for s in slopes])
chk('oracle: secants non-increasing (concave)', True,
    all(slopes[i] >= slopes[i + 1] for i in range(3)), mode='eq')
chk('oracle: secants positive (monotone)', True, all(s > 0 for s in slopes), mode='eq')
slopes_u = [(pts[i + 1]['upper'] - pts[i]['upper']) / (grid[i + 1] - grid[i]) for i in range(4)]
print('  oracle secant slopes on points.upper:', [f'{s:.6f}' for s in slopes_u])
chk('oracle: secants concave on points.upper too', True,
    all(slopes_u[i] >= slopes_u[i + 1] for i in range(3)), mode='eq')

sec('10.1 SCIP CROSS-CHECK')
for i, (dd, doc_b, doc_diff, doc_wall) in enumerate(
        [(0.02, 96.4851908684, 2.31e-9, 31.8), (0.33, 96.5309780292, 2.27e-9, 32.2)]):
    p = next(p for p in pts if abs(p['delta'] - dd) < 1e-12)
    s = p['scip']
    chk(f' scip@{dd} dual bound (10dp)', doc_b, round(s['dual_bound'], 10), tol=0.0)
    chk(f' scip@{dd} status', 'optimal', s['status'], mode='eq')
    chk(f' scip@{dd} |OA.upper - SCIP|', doc_diff, abs(p['upper'] - s['dual_bound']), tol=5e-12)
    chk(f' scip@{dd} wall', doc_wall, round(M['wall_seconds'][f'scip@{dd}'], 1), tol=0.0)
    chk(f' scip@{dd} >= OA primal', True, s['dual_bound'] >= p['primal'], mode='eq')
    print(f'   SCIP - points.upper     = {s["dual_bound"] - p["upper"]:+.3e}')
    print(f'   SCIP - certified_upper  = {s["dual_bound"] - cu[i and 4 or 1]:+.3e}'
          if False else
          f'   SCIP - certified_upper  = '
          f'{s["dual_bound"] - cu[pts.index(p)]:+.3e}')
    print(f'   settings: {s["settings"]}')
print('  NOTE  doc says "Unlike v1, SCIP does not sit uniformly on one side here".'
      '  That holds only against points.upper; against certified_upper (the bound '
      '\n        section 5.2 names as reported) SCIP is ABOVE at both deltas, exactly as in v1.')

# ------------------------------------------------------------------ 3. sec 10.2
sec('10.2 SOFTNESS (D1-prime)')
doc_soft = [(0.02, 96.48557202, 0.73038036, 96.48519087, 3.81e-4),
            (0.05, 96.50313959, 0.74794793, 96.49769027, 5.45e-3),
            (0.10, 96.53241888, 0.77722722, 96.51012323, 2.23e-2)]
for (dd, b, gp, di, sl), s in zip(doc_soft, M['softness']):
    chk(f' soft@{dd} delta', dd, s['delta'], tol=1e-12)
    chk(f' soft@{dd} bound', b, s['bound'], tol=5e-9)
    chk(f' soft@{dd} gap', gp, s['gap'], tol=5e-9)
    chk(f' soft@{dd} direct', di, s['direct'], tol=5e-9)
    chk(f' soft@{dd} slack (3 s.f.)', sl, float(f"{s['slack']:.3g}"), tol=0.0)
    chk(f' soft@{dd} soft==False', False, s['soft'], mode='eq')
    chk(f' soft@{dd} tangent_valid', True, s['tangent_valid'], mode='eq')
    chk(f' soft@{dd} direct == certified_upper', s['direct'],
        cu[M['grid'].index(dd)], tol=0.0)
    chk(f' soft@{dd} slack == bound-direct (oracle)', s['slack'],
        s['bound'] - s['direct'], tol=1e-15)
    chk(f' soft@{dd} gap == bound - V (oracle)', s['gap'], s['bound'] - Vd, tol=1e-13)
# tangent bound oracle: EG(d0) + s_min*(d - d0), with EG(d0) = certified_upper[0]
for (dd, b, *_), s in zip(doc_soft, M['softness']):
    orc = cu[0] + pts[0]['slope'] * (dd - M['grid'][0])
    chk(f' ORACLE tangent bound @{dd}', s['bound'], orc, tol=1e-9)
chk('smallest gap / 5e-3 = 146x', 146, math.floor(M['softness'][0]['gap'] / 0.005), mode='eq')
chk('largest gap / 5e-3 (STATE says 155x)', 155,
    math.floor(M['softness'][2]['gap'] / 0.005), mode='eq')
chk('EG^bal(d0)-V = 0.724507 (doc 10.2/10.3)', 0.724507, round(cu[0] - Vd, 6), tol=0.0)
print(f'  info (EG^bal(d0)-V)/5e-3 = {(cu[0] - Vd) / 0.005!r}  '
      f'doc says "145x" (round), floor is 144 -- doc rounds UP here but uses floor '
      f'(146) for the softness gaps')
chk('(EG^bal(d0)-V)/5e-3 rounds to 145x', 145, round((cu[0] - Vd) / 0.005), mode='eq')
chk('doc 10.2 "EG^bal(d0) = 96.4796985975" == primal not certified_upper',
    96.4796985975, round(pts[0]['primal'], 10), tol=0.0)
chk('doc 10.2 s_min = 0.5855858097', 0.5855858097, round(pts[0]['slope'], 10), tol=0.0)
chk('softness_verdict not soft', 'not soft: the premium survives the band and A1 continues',
    M['softness_verdict'], mode='eq')

# ------------------------------------------------------------------ 4. sec 10.3
sec('10.3 DELTA*')
D = M['delta_star']
chk('n_solves 0', 0, D['n_solves'], mode='eq')
chk('delta*.value == delta0(10dp)', 0.0099700233, D['value'], tol=0.0)
chk('delta* verdict mentions <= delta_0', True,
    D['verdict'].startswith('delta* <= delta_0'), mode='eq')
print(f"  info verdict: {D['verdict']}")

# ------------------------------------------------------------------ 5. sec 10.4
sec('10.4 N8 BAND DUALS -- staff vs districts alignment')
doc_upper = [
    ['R0018', 'R0013', 'R0021', 'R0038', 'R0028', 'R0014', 'R0017', 'R0015'],
    ['R0018', 'R0013', 'R0021', 'R0038', 'R0028', 'R0014', 'R0017', 'R0015'],
    [], [], []]
doc_lower = [
    ['R0004', 'R0001', 'R0000', 'R0006', 'R0009', 'R0003', 'R0005', 'R0002'],
    ['R0004', 'R0001', 'R0000', 'R0006', 'R0003', 'R0005', 'R0002'],
    ['R0004', 'R0001', 'R0000', 'R0003', 'R0005', 'R0002'],
    ['R0001', 'R0000', 'R0003', 'R0005'],
    ['R0000']]
doc_zero = [['R0010', 'R0008'], ['R0010', 'R0009', 'R0008'], None, None, None]
doc_q = [(3.33e-8, 0.2553), (3.35e-8, 0.2551), (3.41e-8, 0.2557),
         (3.49e-8, 0.2569), (3.73e-8, 0.2649)]
for i, p in enumerate(pts):
    nu = p['nu']
    up = [staff[j] for j in range(k) if nu[j] > 0]
    lo = [staff[j] for j in range(k) if nu[j] < 0]
    ze = [staff[j] for j in range(k) if nu[j] == 0]
    print(f"-- delta {p['delta']}  nu>0 {up}  nu<0 {lo}  nu==0 {ze}")
    chk(f' [{p["delta"]}] nu>0 list (staff order)', doc_upper[i], up, mode='eq')
    chk(f' [{p["delta"]}] nu<0 list (staff order)', doc_lower[i], lo, mode='eq')
    if doc_zero[i] is not None:
        chk(f' [{p["delta"]}] nu==0 list', doc_zero[i], ze, mode='eq')
    chk(f' [{p["delta"]}] n_binding_upper == |nu>0|', p['n_binding_upper'], len(up), mode='eq')
    chk(f' [{p["delta"]}] n_binding_lower == |nu<0|', p['n_binding_lower'], len(lo), mode='eq')
    chk(f' [{p["delta"]}] q_min(3sf)', doc_q[i][0], float(f"{p['q_min']:.3g}"), tol=0.0)
    chk(f' [{p["delta"]}] q_max(4dp)', doc_q[i][1], round(p['q_max'], 4), tol=0.0)
    chk(f' [{p["delta"]}] gauge_pinned', True, p['vertex']['gauge_pinned'], mode='eq')
    # cross-array trap: would `districts` give the same labels?
    dup = [M['districts'][j] for j in range(k) if nu[j] > 0]
    print(f"   (districts array at same indices, nu>0: {dup})")

sec('10.4 DEGENERATE ZERO-DUAL CLAIM (finding b)')
for i, p in enumerate(pts):
    nu = p['nu']
    signed = sum(1 for x in nu if x != 0)
    zero = k - signed
    t = p['vertex']['n_tight_bands']
    slack = p['vertex']['n_agents_band_slack']
    print(f"  delta {p['delta']:<12} t={t:<3} |signed nu|={signed:<3} zero={zero:<3} "
          f"n_agents_band_slack={slack:<3} t-signed={t - signed:<3} zero-slack={zero - slack}")
    chk(f' [{p["delta"]}] zero-dual count == 18 - signed', zero, k - signed, mode='eq')
    chk(f' [{p["delta"]}] slack + t == 18 ?', k, slack + t, mode='eq') if t + slack == k else None
chk('doc: at 0.05, t exceeds signed by 9', 9,
    pts[2]['vertex']['n_tight_bands'] - sum(1 for x in pts[2]['nu'] if x != 0), mode='eq')
chk('doc: at 0.05, 9 of the 12 zero-dual reps are tight-but-degenerate', 9,
    (k - sum(1 for x in pts[2]['nu'] if x != 0)) - pts[2]['vertex']['n_agents_band_slack'],
    mode='eq')
chk('doc: at 0.05, n_agents_band_slack = 3', 3, pts[2]['vertex']['n_agents_band_slack'], mode='eq')
chk('doc: at 0.10, t exceeds signed by 3', 3,
    pts[3]['vertex']['n_tight_bands'] - sum(1 for x in pts[3]['nu'] if x != 0), mode='eq')
chk('doc: at 0.10, 3 of the 14 tight-but-degenerate', 3,
    (k - sum(1 for x in pts[3]['nu'] if x != 0)) - pts[3]['vertex']['n_agents_band_slack'],
    mode='eq')
chk('doc: at 0.10, n_agents_band_slack = 11', 11,
    pts[3]['vertex']['n_agents_band_slack'], mode='eq')
for i, exp_t, exp_slack in [(0, 16, 2), (1, 15, 3), (4, 1, 17)]:
    chk(f' doc: at grid[{i}] t == |signed nu| == {exp_t}', exp_t,
        pts[i]['vertex']['n_tight_bands'], mode='eq')
    chk(f' doc: at grid[{i}] |signed nu| == {exp_t}', exp_t,
        sum(1 for x in pts[i]['nu'] if x != 0), mode='eq')
    chk(f' doc: at grid[{i}] n_agents_band_slack == {exp_slack}', exp_slack,
        pts[i]['vertex']['n_agents_band_slack'], mode='eq')
chk('doc 10.4: at d0, 16 of 18 tight, split 8 and 8', (16, 8, 8),
    (pts[0]['vertex']['n_tight_bands'], pts[0]['n_binding_upper'], pts[0]['n_binding_lower']),
    mode='eq')
chk('doc 10.4: from 0.05 outward only lower bands bind', True,
    all(p['n_binding_upper'] == 0 for p in pts[2:]), mode='eq')
chk('doc 10.4: force-fed group 6 -> 4 -> 1', [6, 4, 1],
    [p['n_binding_lower'] for p in pts[2:]], mode='eq')
chk('doc 10.4: at 0.33 exactly one rep (R0000) binds', ['R0000'],
    [staff[j] for j in range(k) if pts[4]['nu'][j] < 0], mode='eq')
chk('doc 10.4: tight_agents at 0.33 == [2] and staff[2] == R0000', ('R0000', [2]),
    (staff[2], pts[4]['vertex']['tight_agents']), mode='eq')

# ------------------------------------------------------------------ 6. sec 10.5
sec('10.5 N9 PROPORTIONALITY')
chk('u_total/k min (doc 181.9)', 181.9, round(min(u) / k, 1), tol=0.0)
chk('u_total/k max (doc 187.1)', 187.1, round(max(u) / k, 1), tol=0.0)
chk('delivered min gap -12.0248', -12.0248, round(min(M['prop_gap_delivered']), 4), tol=0.0)
below = [(staff[j], M['prop_gap_delivered'][j])
         for j in range(k) if M['prop_gap_delivered'][j] < 0]
below.sort(key=lambda t: t[1])
chk('delivered: 3 of 18 below proportionality', 3, len(below), mode='eq')
chk('delivered below list', [('R0038', -12.02), ('R0013', -7.79), ('R0028', -6.69)],
    [(n, round(v, 2)) for n, v in below], mode='eq')
doc_min = [18.5526, 20.0169, 22.2690, 24.6734, 26.6363]
for dm, p in zip(doc_min, pts):
    chk(f' [{p["delta"]}] min prop_gap', dm, round(min(p['prop_gap']), 4), tol=0.0)
    chk(f' [{p["delta"]}] reps below proportionality == 0', 0,
        sum(1 for x in p['prop_gap'] if x < 0), mode='eq')
    # oracle: prop_gap == g - u_total/k, and g must satisfy sum log g = certified value
chk('erosion 26.64 -> 18.55 is about 30%', 30,
    round(100 * (doc_min[4] - doc_min[0]) / doc_min[4]), mode='eq')
# ORACLE: recover g at each point from prop_gap, and check sum log g brackets the primal
for i, p in enumerate(pts):
    gg = [x + ui / k for x, ui in zip(p['prop_gap'], u)]
    s = math.fsum(math.log(x) for x in gg)
    print(f"   ORACLE delta={p['delta']:<12} sum log(prop_gap + u/k) = {s!r} "
          f" primal={p['primal']!r}  diff={s - p['primal']:+.3e}")
    chk(f' ORACLE [{p["delta"]}] sum log g reproduces primal', p['primal'], s, tol=1e-9)
# ORACLE: band feasibility of the reported masses m
for p in pts:
    d = p['delta']
    lo_b, hi_b = tgt * (1 - d), tgt * (1 + d)
    viol = max(max(lo_b - x for x in p['m']), max(x - hi_b for x in p['m']))
    print(f"   ORACLE delta={d:<12} max band violation of reported m = {viol:+.3e}"
          f"   sum m = {math.fsum(p['m'])!r} (T = {T!r})")
    chk(f' ORACLE [{d}] m within band', True, viol <= 1e-6, mode='eq')
    chk(f' ORACLE [{d}] sum m == T', T, math.fsum(p['m']), tol=1e-6)
    chk(f' ORACLE [{d}] t == count of m on a band edge', p['vertex']['n_tight_bands'],
        sum(1 for x in p['m'] if abs(x - lo_b) <= 1e-6 or abs(x - hi_b) <= 1e-6), mode='eq')

# ------------------------------------------------------------------ 7. sec 10.6
sec('10.6 FIRST MOVERS')
FM = M['first_movers']
chk('n_exact_ties 0', 0, FM['n_exact_ties'], mode='eq')
chk('tied_M_share 0.0', 0.0, FM['tied_M_share'], tol=0.0)
chk('first_movers delta == delta0', 0.0099700233, FM['delta'], tol=0.0)
z = FM['zips']
chk('25 zips', 25, len(z), mode='eq')
chk('top-25 M sum = 33.09', 33.09, round(math.fsum(x['M'] for x in z), 2), tol=0.0)
chk('top-25 M share = 0.39% of T', 0.39,
    round(100 * math.fsum(x['M'] for x in z) / T, 2), tol=0.0)
chk('ORACLE M_share sums to same', math.fsum(x['M'] for x in z) / T,
    math.fsum(x['M_share'] for x in z), tol=1e-12)
owners = sorted({x['owner'] for x in z})
chk('owners are exactly R0008/R0021', ['R0008', 'R0021'], owners, mode='eq')
mg = [x['margin'] for x in z]
chk('margin min 5.6e-7', 5.6e-7, float(f'{min(mg):.2g}'), tol=0.0)
chk('margin max 2.5e-6', 2.5e-6, float(f'{max(mg):.2g}'), tol=0.0)
chk('no exact tie: all margins > 0', True, min(mg) > 0, mode='eq')
chk('ORACLE n_exact_ties = #(margin <= 1e-12) over these 25', 0,
    sum(1 for x in mg if x <= 1e-12), mode='eq')
chk('n_support 3773', 3773, FM['vertex']['n_support'], mode='eq')
chk('expected 3781', 3781, FM['vertex']['expected'], mode='eq')
chk('diff 8', 8, FM['vertex']['expected'] - FM['vertex']['n_support'], mode='eq')
chk('degenerate True', True, FM['vertex']['degenerate'], mode='eq')
chk('ORACLE expected == n + k - 1 + t', M['n_zips'] + k - 1 + FM['vertex']['n_tight_bands'],
    FM['vertex']['expected'], mode='eq')
chk('first_movers.vertex == points[0].vertex', pts[0]['vertex'], FM['vertex'], mode='eq')

# ------------------------------------------------------------------ 8. sec 5.1
sec('5.1 REPLACED CONSTANTS  lam*(1-delta)*T/k')
lam = M['lam']
f0 = lam * (1 - M['delta0']) * tgt
f0_rounded_delta = lam * (1 - 0.0099700233) * tgt
f33 = lam * (1 - 0.33) * tgt
print(f'  lam(1-delta0)T/k  = {f0!r}   (delta0 full precision)')
print(f'  lam(1-0.0099700233)T/k = {f0_rounded_delta!r}')
print(f'  lam(1-0.33)T/k    = {f33!r}')
chk('doc 140.638 at delta0', 140.638, round(f0, 3), tol=0.0)
chk('doc 95.176 at 0.33', 95.176, round(f33, 3), tol=0.0)
chk('doc: delta0 printed as 0.0099700233 in 5.1', 0.0099700233, round(M['delta0'], 10), tol=0.0)
gm = math.fsum(g) / k
print(f'  mean(g_delivered)      = {gm!r}')
print(f'  min/max g_delivered    = {min(g)!r} / {max(g)!r}')
print(f'  geometric mean g_deliv = {math.exp(Vd / k)!r}')
print(f'  geometric mean at unconstrained EG_S = {math.exp(G["EG_S_primal"] / k)!r}')
chk('doc "all 18 gains sit at ~206": mean(g_delivered) rounds to 206', 206,
    round(gm), mode='eq')
chk('doc "all 18 gains ... against a floor of 140.638": min g_delivered > floor', True,
    min(g) > f0, mode='eq')
chk('doc "all 18 gains sit at ~206" as a RANGE over g_delivered (|g-206|/206 <= 5%)', True,
    all(abs(x - 206) / 206 <= 0.05 for x in g), mode='eq')
chk('doc "u_i(Z)/k ~ 182-187"', (182, 187), (round(min(u) / k), round(max(u) / k)),
    mode='eq')
try:
    orc = json.loads(pathlib.Path('/tmp/u8v2/oracle_gate_out.json').read_text())
except FileNotFoundError:
    print('  (run oracle_gate.py first for the gate-gains oracle)')
else:
    gg = orc['gate_gains']
    print(f'  ORACLE gate gains (delta=None solve): min {min(gg)!r} max {max(gg)!r} '
          f'mean {math.fsum(gg) / len(gg)!r}')
    chk('ORACLE gate EG_S primal reproduces manifest', G['EG_S_primal'],
        orc['EG_S_primal'], tol=0.0)
    chk('ORACLE gate EG_S upper reproduces manifest', G['EG_S_upper'],
        orc['EG_S_upper'], tol=0.0)
    chk('ORACLE gate bracket reproduces manifest', G['bracket'], orc['bracket'], tol=0.0)
    chk('ORACLE gate n_cuts reproduces manifest', G['n_cuts'], orc['n_cuts'], mode='eq')
    chk('ORACLE M_max_dev_rel reproduces manifest', G['M_max_dev_rel'],
        orc['M_max_dev_rel'], tol=0.0)
    chk('ORACLE M_spread_rel reproduces manifest', G['M_spread_rel'],
        orc['M_spread_rel'], tol=0.0)
    chk('ORACLE V reproduces manifest', Vd, orc['V'], tol=0.0)
    chk('ORACLE V == metrics.json winner.stage2_value (1e-9)', True,
        abs(Vd - float(orc['stage2_value'])) <= 1e-9, mode='eq')
    chk('ORACLE staff order reproduces manifest', staff, orc['staff'], mode='eq')
    chk('*** doc 5.1 "all 18 gains sit at ~206" vs the REAL gate gains', True,
        all(abs(x - 206) / 206 <= 0.05 for x in gg), mode='eq')
    chk('doc 5.1 substance: every gate gain > the 140.638 floor', True,
        min(gg) > f0, mode='eq')
chk('doc "seed clears the floor by a factor of ~1.3"', 1.3,
    round(min(u) / k / f0, 1), tol=0.0)

# ------------------------------------------------------------------ 9. v1 cross
sec('V1 CROSS-CHECKS (finding c and finding 5)')
if M1 is None:
    print('  V1 manifest not present -- INCONCLUSIVE')
else:
    chk('v1 k = 13', 13, M1['k'], mode='eq')
    chk('v1 n_exact_ties = 75', 75, M1['first_movers']['n_exact_ties'], mode='eq')
    print(f"  v1 tied_M_share = {M1['first_movers']['tied_M_share']!r}")
    b1 = [j for j in range(M1['k']) if M1['prop_gap_delivered'][j] < 0]
    chk('v1: 4 of 13 below proportionality', 4, len(b1), mode='eq')
    mn1 = [min(p['prop_gap']) for p in M1['points']]
    print(f"  v1 min prop_gap per point: {[round(x, 4) for x in mn1]}")
    chk('v1 erosion ~32%', 32, round(100 * (mn1[4] - mn1[0]) / mn1[4]), mode='eq')
    g1 = M1['g_delivered']
    print(f"  v1 mean(g_delivered) = {math.fsum(g1) / M1['k']!r}  "
          f"min/max = {min(g1)!r}/{max(g1)!r}   (5.1 v1 text said 'all 13 gains ~ 90')")
    chk('v1 M_max_dev 0.3224 and 0.33 > it', True,
        0.33 > M1['gate']['M_max_dev_rel'], mode='eq')
    print(f"  v1 gate M_max_dev_rel = {M1['gate']['M_max_dev_rel']!r}")
    print(f"  v1 EG^bal(0.33).upper = {M1['points'][4]['upper']!r}  "
          f"EG_S13 upper = {M1['gate']['EG_S13_upper']!r}  "
          f"diff = {M1['gate']['EG_S13_upper'] - M1['points'][4]['upper']:+.3e}")
    print(f"  v1 gate reference = {M1['gate']['reference']!r}  "
          f"delta_upper = {M1['gate']['delta_upper']!r}  "
          f"(v2 gate has reference=None -> delta_upper=None, matches_reference vacuous)")
    print(f"  v1 certified_upper = {M1['certified_upper']!r}")
    for p in M1['points']:
        if p['scip']:
            print(f"   v1 scip@{p['delta']}: dual={p['scip']['dual_bound']!r} "
                  f"upper={p['upper']!r} diff={p['scip']['dual_bound'] - p['upper']:+.3e} "
                  f"vs certified diff="
                  f"{p['scip']['dual_bound'] - M1['certified_upper'][M1['grid'].index(p['delta'])]:+.3e}")

# ------------------------------------------------------------------ 10. STATE
sec('STATE.md FACTS CONSISTENCY')
chk('premium in 0.72-0.78 nats', True,
    0.72 <= (cu[0] - Vd) and (pts[4]['upper'] - Vd) <= 0.78, mode='eq')
chk('D1prime 146-155x floor', (146, 155),
    (math.floor(M['softness'][0]['gap'] / 0.005),
     math.floor(M['softness'][2]['gap'] / 0.005)), mode='eq')
chk('33-fold widening buys 0.051 nats', 0.051,
    round(cu[4] - cu[0], 3), tol=0.0)
chk('33-fold widening buys 0.051 nats (points.upper)', 0.051,
    round(pts[4]['upper'] - pts[0]['upper'], 3), tol=0.0)
chk('widening factor 0.33/delta0 ~ 33', 33, round(0.33 / M['delta0']), mode='eq')
chk('no delta* (delta* <= delta0, 0 solves)', 0, D['n_solves'], mode='eq')

sec('SUMMARY')
print(f'  PASS {len(PASS)}   FAIL {len(FAIL)}')
for n, d, gt in FAIL:
    print(f'   FAILED: {n}  doc={d!r} got={gt!r}')
