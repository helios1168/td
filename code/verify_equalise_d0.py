"""Re-verify Appendix A's 'equalisation can destroy value' numbers at d=(0,0).
Unconstrained equalising MILP on the zip50 instance: min |g_a/Amax - g_b/Bmax|
over ALL subsets (not just prefixes), then report welfare share vs the
utilitarian max, and the best prefix's KS gap / welfare share for comparison."""
import pickle, sys
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds

with open("/tmp/z50.pkl", "rb") as f:
    d = pickle.load(f)
A, B, M = (np.asarray(d[k], float) for k in ("Az", "Bz", "Mz"))
th, lam = 0.40, 0.30
c1, c2 = 1 - lam, th * (1 - lam)
ua = c1 * A + c2 * B + lam * M
ub = c2 * A + c1 * B + lam * M
Amax, Bmax = ua.sum(), ub.sum()
n = len(ua)

# utilitarian max welfare (exact: take every zip with ua>ub)
util = sum(max(ua[i], ub[i]) for i in range(n))

# MILP: vars = [x_1..x_n, t]; ga/Amax - gb/Bmax = sum x*(ua/Amax + ub/Bmax) - 1
w = ua / Amax + ub / Bmax
c = np.zeros(n + 1); c[-1] = 1.0
A1 = np.concatenate([w, [-1.0]])   #  sum w x - 1 <= t
A2 = np.concatenate([-w, [-1.0]])  # -(sum w x - 1) <= t
cons = LinearConstraint(np.vstack([A1, A2]), -np.inf, [1.0, -1.0])
integ = np.concatenate([np.ones(n), [0]])
res = milp(c=c, constraints=cons, integrality=integ,
           bounds=Bounds(np.zeros(n + 1), np.concatenate([np.ones(n), [np.inf]])),
           options=dict(mip_rel_gap=0.0))
x = np.round(res.x[:n]).astype(bool)
ga, gb = ua[x].sum(), ub[~x].sum()
ks = abs(ga / Amax - gb / Bmax)
print(f"equalising MILP (all subsets): KS gap {ks:.6g}  welfare {(ga+gb)/util:.1%}  "
      f"ga {ga:.4f} gb {gb:.4f}  product {ga*gb:.3f}")

# best prefix by KS gap
order = np.argsort(-(ua / ub))
cua, cub = np.concatenate([[0], np.cumsum(ua[order])]), np.concatenate([[0], np.cumsum(ub[order])])
gak, gbk = cua, ub.sum() - cub
ksk = np.abs(gak / Amax - gbk / Bmax)
k = int(np.argmin(ksk))
print(f"best prefix by KS gap: k={k}  KS gap {ksk[k]:.6g}  welfare {(gak[k]+gbk[k])/util:.1%}")
# Nash for context
prod = gak * gbk; kn = int(np.argmax(prod))
print(f"prefix Nash: k={kn}  welfare {(gak[kn]+gbk[kn])/util:.1%}  KS gap {ksk[kn]:.6g}")
