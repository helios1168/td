#!/usr/bin/env python3
"""
Verification for "Fair Territory Division in Two Dimensions".
Reproduces every number in the note. Net headroom convention throughout.

    python3 verify_2d.py
"""
import numpy as np
from scipy.ndimage import label as cclabel, binary_erosion
np.seterr(all='ignore')

# ---------------------------------------------------------------- territory
N = 600
g = np.linspace(1e-3, 1 - 1e-3, N)
Y, X = np.meshgrid(g, g, indexing='ij')
cell = (g[1] - g[0]) ** 2
S = np.stack([X, Y], -1)

def gauss(mu, cov):
    d = S - np.array(mu)
    ic = np.linalg.inv(np.array(cov)); det = np.linalg.det(np.array(cov))
    return np.exp(-.5 * np.einsum('...i,ij,...j->...', d, ic, d)) / (2 * np.pi * np.sqrt(det))

def norm(z):
    return z / (z.sum() * cell)

Sa, Sb, M, th, lam = 3.0, 1.8, 40.0, 0.40, 0.30
c1, c2 = 1 - lam, th * (1 - lam)          # NET headroom
Lam = c1 + c2
D = Lam * (Sa + Sb) + 2 * lam * M
q = (Sa * (1 + c2) - lam * Sb + lam * M) / D

fa = norm(gauss([.30, .40], [[.045, .010], [.010, .055]]))
fb = norm(gauss([.70, .62], [[.045, .010], [.010, .055]]))
m = norm(np.ones_like(X))

def build(fa_, fb_, m_, th_=th, lam_=lam, M_=M):
    C1, C2 = 1 - lam_, th_ * (1 - lam_)
    L = C1 + C2; Dd = L * (Sa + Sb) + 2 * lam_ * M_
    qq = (Sa * (1 + C2) - lam_ * Sb + lam_ * M_) / Dd
    P, Q, R = Sa * fa_, Sb * fb_, lam_ * M_ * m_
    ua, ub = C1 * P + C2 * Q + R, C2 * P + C1 * Q + R
    dPhi = (L * (P + Q) + 2 * lam_ * M_ * m_) / Dd
    return ua, ub, ua / ub, dPhi, qq

def ratio_quantile(r, dPhi, qq):
    """t* = R^{-1}(1-q): threshold whose superlevel set carries mixture mass q."""
    o = np.argsort(r.ravel())[::-1]
    cum = np.cumsum(dPhi.ravel()[o] * cell)
    return r.ravel()[o][int(np.searchsorted(cum, qq))]

def line_r2(mask):
    edge = mask & ~binary_erosion(mask)
    p = np.stack([X[edge], Y[edge]], 1)
    p = p[(p[:, 0] > .02) & (p[:, 0] < .98) & (p[:, 1] > .02) & (p[:, 1] < .98)]
    if len(p) < 20: return np.nan, 0
    A = np.c_[p[:, 0], np.ones(len(p))]
    coef, *_ = np.linalg.lstsq(A, p[:, 1], rcond=None)
    res = p[:, 1] - A @ coef
    return float(1 - (res ** 2).sum() / ((p[:, 1] - p[:, 1].mean()) ** 2).sum()), len(p)

print("=" * 68)
print("SEC 2-4  equal gain as a measure condition, and the ratio quantile")
ua, ub, r, dPhi, _ = build(fa, fb, m)
print(f"  mixture measure of Omega          = {(dPhi*cell).sum():.8f}   (must be 1)")
t_star = ratio_quantile(r, dPhi, q)
Om = r >= t_star
Ga = (ua * Om * cell).sum() - Sa
Gb = (ub * (~Om) * cell).sum() - Sb
print(f"  q                                 = {q:.6f}")
print(f"  t*                                = {t_star:.6f}")
print(f"  Phi(Omega_a)                      = {(dPhi*Om*cell).sum():.6f}")
print(f"  G_a, G_b                          = {Ga:.6f}, {Gb:.6f}   |gap| = {abs(Ga-Gb):.2e}")

print("\nSEC 5  fragility: two distinct sensitivities")
h = 0.004
Rcdf = lambda t: (dPhi * (r < t) * cell).sum()
area = lambda t: float(((r >= t) * cell).sum())
Rp = (Rcdf(t_star + h) - Rcdf(t_star - h)) / (2 * h)
Ap = abs((area(t_star + h) - area(t_star - h)) / (2 * h))
print(f"  R'(t*)      = {Rp:.4f}   mixture mass per unit threshold")
print(f"  |dArea/dt|  = {Ap:.4f}   territory area per unit threshold")
print(f"  ratio range = [{r.min():.4f}, {r.max():.4f}]   t* at {100*Rcdf(t_star):.1f}th percentile")

print("\nSEC 6  comparative statics")
e = 2e-3
def ts(th_=th, lam_=lam, M_=M):
    ua_, ub_, r_, d_, q_ = build(fa, fb, m, th_, lam_, M_)
    return ratio_quantile(r_, d_, q_)
print(f"  dt*/dtheta  = {(ts(th_=th+e)-ts(th_=th-e))/(2*e):+.6f}")
print(f"  dt*/dlambda = {(ts(lam_=lam+e)-ts(lam_=lam-e))/(2*e):+.6f}")
print(f"  dt*/dM      = {(ts(M_=M+e)-ts(M_=M-e))/(2*e):+.6f}")

print("\nSEC 7  boundary geometry")
print(f"  lambda=0.30, equal-covariance Gaussians: straight-line R^2 = {line_r2(Om)[0]:.5f}")
ua0, ub0, r0, d0, q0 = build(fa, fb, m, lam_=1e-9)
Om0 = r0 >= ratio_quantile(r0, d0, q0)
print(f"  lambda->0  , equal-covariance Gaussians: straight-line R^2 = {line_r2(Om0)[0]:.6f}  (LDA half-plane)")

print("\nSEC 8  connectedness replaces MLR; bimodality does NOT disconnect in 2-D")
print("     separation  components  >1% area   boundary R^2")
for sep, sd in [(.25, .012), (.45, .012), (.65, .010), (.80, .008)]:
    FA = norm(.5 * gauss([.5 - sep / 2, .25], [[sd, 0], [0, sd]])
              + .5 * gauss([.5 + sep / 2, .25], [[sd, 0], [0, sd]]))
    ua2, ub2, r2, d2, _ = build(FA, fb, m)
    reg = r2 >= ratio_quantile(r2, d2, q)
    lab, nc = cclabel(reg)
    big = sum(1 for i in range(1, nc + 1) if (lab == i).sum() * cell > 0.01)
    print(f"        {sep:.2f}          {nc:>2}         {big:>2}          {line_r2(reg)[0]:.4f}")

print("\nSEC 9  Kalai-Smorodinsky in two dimensions")
A_ = (ua * cell).sum() - Sa
B_ = (ub * cell).sum() - Sb
Ka, Kb, KM = Sa * (B_ * c1 + A_ * c2), Sb * (B_ * c2 + A_ * c1), lam * M * (A_ + B_)
K = Ka + Kb + KM
qK = (A_ * B_ + B_ * Sa) / K
dK = (Ka * fa + Kb * fb + KM * m) / K
tK = ratio_quantile(r, dK, qK)
OK_ = r >= tK
GaK = (ua * OK_ * cell).sum() - Sa
GbK = (ub * (~OK_) * cell).sum() - Sb
print(f"  G_a^max, G_b^max = {A_:.4f}, {B_:.4f}")
print(f"  q_KS = {qK:.6f}   t*_KS = {tK:.6f}")
print(f"  G_a/G_a^max = {GaK/A_:.6f}   G_b/G_b^max = {GbK/B_:.6f}   |diff| = {abs(GaK/A_-GbK/B_):.2e}")
print("=" * 68)
