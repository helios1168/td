"""Independent re-run of the U8-band v2 GATE only (delta=None), to reproduce
section 10.0's EG_S bracket and to obtain the 18 gains at the unconstrained optimum
that section 5.1 asserts "sit at ~206".

Run from /Users/ntlee/projects/td/.claude/worktrees/w2-phase0 with the repo-root venv:
  /Users/ntlee/projects/td/.venv/bin/python3 -u /tmp/u8v2/oracle_gate.py
"""
from __future__ import annotations

import json
import math
import sys

sys.path.insert(0, '/Users/ntlee/projects/td/.claude/worktrees/w2-phase0')

from td import channel                               # noqa: E402
from td.solvers import eg_band                       # noqa: E402
from tools.measure import frontier                   # noqa: E402
from td import instance as descaled                  # noqa: E402

INST = '/Users/ntlee/projects/td/instance_descaled_v2.json.gz'
DRAW = ('/Users/ntlee/projects/td/.claude/worktrees/w2-phase0/'
        'battery/results/draw_k18_v2_20260904')

draw_dir, label = frontier.resolve_draw_dir(DRAW)
to_district = frontier.read_draw(draw_dir + '/draw.csv')
metrics = frontier.read_metrics(draw_dir + '/metrics.json')
winner = dict(metrics.get('winner') or {})
d = descaled.load_descaled(INST)
res = channel.stage2(d.G, to_district, reps_order=d.reps, theta=0.4, lam=0.3,
                     filler_capture='theta')
sigma = {str(a): str(b) for a, b in res['assignment'].items()}
s = frontier.build_setting(d.G, to_district, sigma, theta=0.4, lam=0.3,
                           filler_capture='theta')

print('k', s.k, 'n', len(s.nodes), 'T', repr(s.T))
print('V(recomputed)                 ', repr(s.V))
print('winner.stage2_value (metrics) ', repr(winner.get('stage2_value')))
if 'stage2_value' in winner:
    print('  V - stage2_value =', repr(s.V - float(winner['stage2_value'])))
print('delta0', repr(s.delta0), 'spread0', repr(s.spread0))
print('staff order', list(s.staff))
print('districts  ', list(s.districts))

sol = eg_band.solve_band(s.U, s.M, None)
print('EG_S primal', repr(sol.primal))
print('EG_S upper ', repr(sol.upper))
print('bracket', repr(sol.bracket), 'n_cuts', sol.n_cuts, 'status', sol.status)
tgt = float(s.M.sum()) / s.k
print('M_max_dev_rel', repr(float(abs(sol.m - tgt).max() / tgt)))
print('M_spread_rel ', repr(float((sol.m.max() - sol.m.min()) / sol.m.mean())))
g = [float(x) for x in sol.g]
print('GATE gains (unconstrained optimum), sorted:')
print('  ', [round(x, 3) for x in sorted(g)])
print('  min %r  max %r  mean %r' % (min(g), max(g), math.fsum(g) / len(g)))
print('  sum log g =', repr(math.fsum(math.log(x) for x in g)))
floor0 = 0.3 * (1 - s.delta0) * tgt
floor33 = 0.3 * (1 - 0.33) * tgt
print('  P5.3 floor at delta0 =', repr(floor0), ' at 0.33 =', repr(floor33))
print('  min gate gain / floor0 =', repr(min(g) / floor0))
print('  all gate gains within 5% of 206?',
      all(abs(x - 206) / 206 <= 0.05 for x in g))
print('  all gate gains within 5% of 213?',
      all(abs(x - 213) / 213 <= 0.05 for x in g))
print('  u_i(Z)/k range', repr(float(s.u_total.min() / s.k)),
      repr(float(s.u_total.max() / s.k)))
print('  seed g = u_i(Z)/k ; min/floor0 =', repr(float(s.u_total.min() / s.k) / floor0))
print('  delivered gains min/max/mean',
      repr(float(s.g_delivered.min())), repr(float(s.g_delivered.max())),
      repr(float(s.g_delivered.mean())))
json.dump({'gate_gains': g, 'EG_S_primal': sol.primal, 'EG_S_upper': sol.upper,
           'bracket': sol.bracket, 'n_cuts': sol.n_cuts,
           'M_max_dev_rel': float(abs(sol.m - tgt).max() / tgt),
           'M_spread_rel': float((sol.m.max() - sol.m.min()) / sol.m.mean()),
           'V': s.V, 'delta0': s.delta0, 'spread0': s.spread0,
           'stage2_value': winner.get('stage2_value'),
           'staff': list(s.staff), 'districts': list(s.districts)},
          open('/tmp/u8v2/oracle_gate_out.json', 'w'), indent=1)
print('WROTE /tmp/u8v2/oracle_gate_out.json')
