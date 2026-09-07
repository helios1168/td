"""Same gate oracle, on the v1 (k=13) instance, to judge whether section 5.1's
pre-existing '13 gains sit at ~90' was itself a delivered-gains number."""
from __future__ import annotations

import math
import sys

sys.path.insert(0, '/Users/ntlee/projects/td/.claude/worktrees/w2-phase0')

from td import channel                               # noqa: E402
from td import instance as descaled                  # noqa: E402
from td.solvers import eg_band                       # noqa: E402
from tools.measure import frontier                   # noqa: E402

INST = '/Users/ntlee/projects/td/instance_descaled.json.gz'
DRAW = ('/Users/ntlee/projects/td/.claude/worktrees/w2-phase0/'
        'battery/results/draw_k13_20260901')

draw_dir, _ = frontier.resolve_draw_dir(DRAW)
to_district = frontier.read_draw(draw_dir + '/draw.csv')
d = descaled.load_descaled(INST)
res = channel.stage2(d.G, to_district, reps_order=d.reps, theta=0.4, lam=0.3,
                     filler_capture='theta')
sigma = {str(a): str(b) for a, b in res['assignment'].items()}
s = frontier.build_setting(d.G, to_district, sigma, theta=0.4, lam=0.3,
                           filler_capture='theta')
sol = eg_band.solve_band(s.U, s.M, None)
g = sorted(float(x) for x in sol.g)
tgt = float(s.M.sum()) / s.k
print('v1 k', s.k, 'EG_S primal', repr(sol.primal))
print('v1 GATE gains sorted:', [round(x, 3) for x in g])
print('v1 gate min/max/mean', min(g), max(g), math.fsum(g) / len(g))
print('v1 delivered gains min/max/mean', float(s.g_delivered.min()),
      float(s.g_delivered.max()), float(s.g_delivered.mean()))
print('v1 floor at delta0', 0.3 * (1 - s.delta0) * tgt,
      ' at 0.33', 0.3 * (1 - 0.33) * tgt)
print('v1 u_i(Z)/k range', float(s.u_total.min() / s.k), float(s.u_total.max() / s.k))
