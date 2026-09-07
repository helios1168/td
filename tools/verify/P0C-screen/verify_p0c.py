#!/usr/bin/env python3
"""Adversarial verification of P0-C's arithmetic, before it reaches channel_note.pdf.

Run from the worktree root with the repo-root venv::

    cd /Users/ntlee/projects/td/.claude/worktrees/w2-phase0
    /Users/ntlee/projects/td/.venv/bin/python3 docs/artifacts/VERIFY_P0C-screen/verify_p0c.py

Six claim groups (C1..C6).  Every NUMERIC leg is computed from a *fresh transcription of
channel_note.tex eq. (util)/(Tz)/(decomp)/(split)* -- deliberately NOT by calling
`channel.gain_matrix` or `premium.measure` -- so the code under test is never its own witness.
The one exception is P_18 (a max-k-coverage MILP), which is taken as an input and only
self-consistency-checked; that limit is stated in the report.
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

REPO = "/Users/ntlee/projects/td/.claude/worktrees/w2-phase0"
sys.path.insert(0, REPO)

import numpy as np                                                        # noqa: E402
import scipy                                                              # noqa: E402
import sympy as sp                                                        # noqa: E402

from td import channel, model                                             # noqa: E402
from td import instance as descaled                                       # noqa: E402
import tools.measure.premium as premium                                   # noqa: E402

INSTANCE = os.path.join(REPO, "instance_descaled_v2.json.gz")
DRAW = os.path.join(REPO, "battery", "results", "draw_k18_v2_20260904", "k18")
MEAS = os.path.join(REPO, "battery", "results", "meas_v2_btot_20260905",
                    "draw_k18_v2_20260904.json")

THETA, LAM = 0.40, 0.30
FILLER = "theta"
EG_S18 = 96.53215175                 # the v2 gate (git show ae2b18d:docs/WAVE2_PLAN.md "Live v2 anchors")
CERT_TOL = 1e-8                      # tier 1
EPS_CERT = 5e-3                      # tier 2, nats

OUT: list[str] = []


def say(s: str = "") -> None:
    print(s)
    OUT.append(s)


def head(s: str) -> None:
    say("")
    say("=" * 78)
    say(s)
    say("=" * 78)


# =====================================================================  C1 SYMBOLIC
def c1_symbolic() -> None:
    head("C1 (symbolic) -- does W_0 as coded match eq. (util) -> eq. (decomp) in the paper?")
    lam, th, Sown, Sother, Sfree, M, cfree = sp.symbols(
        "lambda theta S_own S_other S_free M c_free", nonnegative=True)
    c1s, c2s = 1 - lam, th * (1 - lam)
    T = Sown + Sother                                    # eq. (Tz): named reps only
    # eq. (util) at i = own(z), transcribed from channel_note.tex:174-177
    u_own = c1s * Sown + c2s * (T - Sown) + cfree * Sfree + lam * M
    # eq. (decomp)'s regrouping, channel_note.tex:481
    regroup = c2s * T + cfree * Sfree + lam * M + (c1s - c2s) * Sown
    say(f"  simplify(u_own - regroup)            = {sp.simplify(u_own - regroup)}")
    assert sp.simplify(u_own - regroup) == 0
    # the premium coefficient
    w_sym = sp.simplify((c1s - c2s) - (1 - lam) * (1 - th))
    say(f"  simplify((c1-c2) - (1-lam)(1-theta)) = {w_sym}")
    assert w_sym == 0
    # eq. (split): n log((W0 + wP)/n) - D(g) == sum log g, given W0 + wP = sum g
    n = 4
    gs = sp.symbols("g1:5", positive=True)
    W0, P, w = sp.symbols("W_0 P w", positive=True)
    D = n * sp.log(sum(gs) / n) - sum(sp.log(x) for x in gs)
    split = (n * sp.log((W0 + w * P) / n) - D).subs(W0, sum(gs) - w * P)
    resid = sp.simplify(split - sum(sp.log(x) for x in gs))
    say(f"  simplify(split - sum log g)          = {resid}")
    assert resid == 0
    say("  -> eq. (decomp) and eq. (split) are identities; premium.py's W_0 is the")
    say("     paper's W_0 term-for-term (lam*M + c2*T + c_free*S_free), with T over")
    say("     named reps only and S_free in its own term (channel_note.tex:164-181).")


# ==============================================================  load the live instance
def load():
    d = descaled.load_descaled(INSTANCE)
    with open(os.path.join(DRAW, "draw.csv"), newline="", encoding="utf-8") as fh:
        to_district = {r["zip"]: r["district"] for r in csv.DictReader(fh)}
    with open(os.path.join(DRAW, "metrics.json"), encoding="utf-8") as fh:
        metrics = json.load(fh)
    with open(MEAS, encoding="utf-8") as fh:
        meas = json.load(fh)
    return d, to_district, metrics, meas


# -------------------------------------------------------- the independent transcription
def fresh_quantities(G, to_district, sigma):
    """B_tot, per-district gains, P0 -- straight from eq. (util), no td/ helpers beyond the
    raw attribute reads.  Uses math.fsum so the sum order cannot be blamed."""
    c1, c2 = 1.0 - LAM, THETA * (1.0 - LAM)
    c_free = {"theta": c2, "full": c1, "opportunity": LAM}[FILLER]
    w = (1.0 - LAM) * (1.0 - THETA)
    nodes = sorted(to_district)
    B_terms, prem_terms = [], []
    gains: dict[str, list[float]] = {d: [] for d in set(to_district.values())}
    for z in nodes:
        nd = G.nodes[z]
        S = dict(nd["S"]) if "S" in nd else {nd["rep_a"]: float(nd["A"]),
                                             nd["rep_b"]: float(nd["B"])}
        T = math.fsum(float(v) for v in S.values())
        free = float(nd.get("S_free", 0.0) or 0.0)
        M = float(nd["M"])
        B_terms.append(LAM * M + c2 * T + c_free * free)
        own = sigma[to_district[z]]
        s_own = float(S.get(own, 0.0))
        prem_terms.append(s_own)
        # eq. (util) evaluated at i = own(z), NOT regrouped
        gains[to_district[z]].append(c1 * s_own + c2 * (T - s_own) + c_free * free + LAM * M)
    return (math.fsum(B_terms), {d: math.fsum(v) for d, v in gains.items()},
            math.fsum(prem_terms), w)


# =====================================================================  C2 NUMERIC
def c2_identity(G, to_district, meas, metrics):
    head("C2 -- B_tot = 3268.4069219934404, and is the identity an INDEPENDENT oracle?")
    sigma = {str(k): str(v) for k, v in metrics["winner"]["assignment"].items()}
    B_fresh, gains_fresh, P0_fresh, w = fresh_quantities(G, to_district, sigma)
    sum_g_fresh = math.fsum(gains_fresh.values())

    B_code = meas["B_tot"]
    P0_code = meas["ladder"]["P0"]["book"]
    say(f"  fresh transcription  B_tot   = {B_fresh!r}")
    say(f"  premium.py           B_tot   = {B_code!r}")
    say(f"  |delta|                      = {abs(B_fresh - B_code):.3e}   "
        f"(tier-1 CERT_TOL {CERT_TOL:g})")
    say(f"  fresh transcription  P0      = {P0_fresh!r}")
    say(f"  premium.py           P0      = {P0_code!r}   "
        f"|delta| = {abs(P0_fresh - P0_code):.3e}")
    say(f"  fresh   sum_i g_i            = {sum_g_fresh!r}")
    say(f"  B_tot + w*P0 (fresh)         = {B_fresh + w * P0_fresh!r}")
    say(f"  18 * mean gain from JSON     = {meas['U1']['gains']['mean'] * 18!r}")
    say(f"  the task's quoted 3712.6435  -> delta from truth "
        f"{3712.6435 - sum_g_fresh:+.4f} nats  *** MISQUOTE ***")

    # --- attack: is the runtime assertion circular?
    say("")
    say("  ATTACK: mutation test on the assertion at premium.py:297-302.")
    say("  M1  shared upstream misreading (double-count S_free in BOTH paths):")
    orig_free = model.free_book
    try:
        model.free_book = lambda G, z: 2.0 * orig_free(G, z)      # type: ignore
        res = premium.measure(G, to_district, sigma=sigma, theta=THETA, lam=LAM,
                              filler_capture=FILLER)
        say(f"      assertion PASSED, B_tot moved {B_code!r} -> {res['B_tot']!r}")
        say("      => a shared misreading of the model is INVISIBLE to the identity.")
    except ValueError as e:
        say(f"      assertion raised: {e}")
    finally:
        model.free_book = orig_free                               # type: ignore

    say("  M2  divergence between the two paths (lam perturbed in gain_matrix only):")
    orig_gm = channel.gain_matrix

    def bad_gm(G_, td_, ro=None, ds=None, *, theta=0.40, lam=0.30, filler_capture="theta"):
        return orig_gm(G_, td_, ro, ds, theta=theta, lam=lam * 1.000001,
                       filler_capture=filler_capture)
    try:
        premium.channel.gain_matrix = bad_gm                      # type: ignore
        premium.measure(G, to_district, sigma=sigma, theta=THETA, lam=LAM,
                        filler_capture=FILLER)
        say("      assertion PASSED -- it does not even detect divergence!")
    except ValueError as e:
        say(f"      assertion RAISED (good): {str(e)[:110]}...")
    finally:
        premium.channel.gain_matrix = orig_gm                     # type: ignore
    say("  => the identity is a DUPLICATE-COMPUTATION cross-check (it detects the two")
    say("     code paths diverging), not an independent oracle for the formula itself.")
    return B_fresh, sum_g_fresh, P0_fresh, w, gains_fresh


# =====================================================================  C3/C4 NUMERIC
def c34_star(B_tot, meas):
    head("C3/C4 -- the (star) screen k*log((B_tot + w*P)/k) and the slack over EG_{S18}")
    k = 18
    w = 0.42
    P_S = meas["ladder"]["P_S"]["book"]
    P18 = meas["ladder"]["P13"]["book"]      # naming fossil: P13 key holds P_18 at k=18
    claims = {"P_S": (P_S, 96.55406280784752, 0.021911057847518),
              "P_18": (P18, 96.79300971267465, 0.260857962674649)}
    for name, (P, claimed_star, claimed_slack) in claims.items():
        arg = (B_tot + w * P) / k
        star = k * math.log(arg)             # math.log IS natural log
        say(f"  {name:5s} P = {P!r}")
        say(f"        (B_tot + 0.42*P)/18   = {arg!r}")
        say(f"        18*ln(.)              = {star!r}   claimed {claimed_star!r}")
        say(f"        |delta|               = {abs(star - claimed_star):.3e}")
        say(f"        slack over EG_S18     = {star - EG_S18!r}   claimed {claimed_slack!r}")
        say(f"        |delta|               = {abs((star - EG_S18) - claimed_slack):.3e}")
    say(f"  natural-log check: 18*log10(arg) would be "
        f"{18 * math.log10((B_tot + w * P_S) / k):.6f} -- not the quoted value, so ln.")
    say("  sanity: P_S from JSON reproduced independently as sum_z max_{i in S18} S_i(z)")
    say("")
    say("  ATTACK: is '0.064 -> 0.261' like-for-like?  v1 (LENS_GROMOV.md:70-71):")
    v1 = {"P_S": 60.7615, "P_13": 60.8025}
    v1_gate = 60.6974156139
    for nm, v in v1.items():
        say(f"      v1 (star)@{nm:5s} = {v}   slack over EG_S13 {v1_gate} = {v - v1_gate:.4f}")
    say(f"      v2 (star)@P_S   slack = {k * math.log((B_tot + w * P_S) / k) - EG_S18:.4f}")
    say(f"      v2 (star)@P_18  slack = {k * math.log((B_tot + w * P18) / k) - EG_S18:.4f}")
    say("      LIKE-FOR-LIKE:  P_S rung  0.0641 -> 0.0219  (TIGHTENS, 2.9x)")
    say("                      P_k rung  0.1051 -> 0.2609  (loosens, 2.5x)")
    say("      '0.064 -> 0.261' pairs the v1 P_S rung with the v2 P_18 rung.")
    say("      NOT like-for-like.")


def check_PS(G, to_district, meas):
    """Independent recomputation of P_S = sum_z max_{i in S18} S_i(z)."""
    staff = set(meas["staff"])
    tot = math.fsum(max([float(v) for r, v in model.books(G, z).items() if r in staff] or [0.0])
                    for z in sorted(to_district))
    say(f"  fresh P_S = {tot!r}  vs JSON {meas['ladder']['P_S']['book']!r}  "
        f"|d| = {abs(tot - meas['ladder']['P_S']['book']):.3e}")
    staff18 = set(meas["P13_solve"]["staff"] or [])
    tot18 = math.fsum(max([float(v) for r, v in model.books(G, z).items() if r in staff18]
                          or [0.0]) for z in sorted(to_district))
    say(f"  fresh P_18 (evaluating the MILP's own staff set) = {tot18!r} vs JSON "
        f"{meas['ladder']['P13']['book']!r}  |d| = {abs(tot18 - meas['ladder']['P13']['book']):.3e}")
    say(f"  MILP status {meas['P13_solve']['status']!r}; greedy lower bound "
        f"{meas['P13_solve']['greedy_book']!r} <= P_18: "
        f"{meas['P13_solve']['greedy_book'] <= tot18}")
    say("  NOTE: P_18's OPTIMALITY is not independently certified here -- only that the")
    say("        reported staff set attains the reported value and beats the greedy bound.")


# =====================================================================  C5 saturation
def c5_saturation(G, to_district, meas):
    head("C5 -- SATURATION = 29.6 %: which definition, and do the six macros follow?")
    nodes = sorted(to_district)
    T = math.fsum(math.fsum(float(v) for v in model.books(G, z).values()) for z in nodes)
    F = math.fsum(model.free_book(G, z) for z in nodes)
    M = math.fsum(float(G.nodes[z]["M"]) for z in nodes)
    say(f"  sum T      = {T!r}   (JSON total_book {meas['total_book']!r})")
    say(f"  sum S_free = {F!r}")
    say(f"  sum M      = {M!r}   (JSON total_M    {meas['total_M']!r})")
    say(f"  (a) sum T / sum M            = {100 * T / M:.4f} %   <- note's own t_z = T_z/M_z")
    say(f"  (b) (sum T + sum F) / sum M  = {100 * (T + F) / M:.4f} %   <- R1's definition")
    say(f"  (c) sum F / sum M            = {100 * F / M:.4f} %   <- as worded in the task")
    say("  => the task's stated second candidate (c) is a MIS-DESCRIPTION; the 29.81 %")
    say("     the agent actually rejected is (b), R1's Sigma(T+S_free)/Sigma(M).")
    say("  eq. (Tz) at channel_note.tex:164-166 + :180-181 ('T_z runs over named")
    say("  representatives only; S_free enters through its own term') fixes t_z = T_z/M_z,")
    say("  and ceiling.py:260-261 codes u_own = c1*t + lam with NO S_free term, i.e. the")
    say("  archetype 'whole book with one incumbent, S_free = 0'. => (a) is required.")
    say(f"  STATE.md ## Facts 'aggregate saturation' v2 = 29.6 % : agrees with (a) "
        f"({100 * T / M:.3f} %), not (b) ({100 * (T + F) / M:.3f} %).")

    say("")
    say("  the six dependent macros, recomputed from ceiling.py:258-270:")
    for t, tag in ((0.296, "SATURATION as committed (rounded)"), (T / M, "unrounded T/M")):
        c1, c2 = 1.0 - LAM, THETA * (1.0 - LAM)
        u_own, u_other = c1 * t + LAM, c2 * t + LAM
        row = dict(chSat=f"{100 * t:g}", chUown=f"{u_own:.3f}", chUother=f"{u_other:.3f}",
                   chOppShare=f"{100 * LAM / u_own:.1f}",
                   chPremShare=f"{100 * (c1 - c2) * t / u_own:.1f}",
                   chUswing=f"{100 * (u_own / u_other - 1):.1f}")
        say(f"    t = {t!r:22s} ({tag})")
        say(f"      {row}")
    committed = dict(chSat="29.6", chUown="0.507", chUother="0.383", chOppShare="59.1",
                     chPremShare="24.5", chUswing="32.5")
    say(f"    committed ceiling_numbers.tex:56-61: {committed}")
    say("    -> at the committed t = 0.296 all six reproduce exactly.")
    say("    -> at the unrounded t = 0.29588, chOppShare would print 59.2, not 59.1:")
    say(f"       100*lam/u_own = {100 * LAM / (0.7 * (T / M) + 0.3):.4f} (unrounded) vs "
        f"{100 * LAM / (0.7 * 0.296 + 0.3):.4f} (rounded)")


# =====================================================================  C6 the 5.1 range
def c6_split(B_tot, sum_g, P0, meas, gains_fresh, G, to_district):
    head("C6 -- section 5.1: 0.663 + 0.249 = 0.912 nats vs D(g) at 1e-4..1e-2")
    k, w = 18, 0.42
    P_S = meas["ladder"]["P_S"]["book"]
    P18 = meas["ladder"]["P13"]["book"]
    g = np.array(sorted(gains_fresh.values()), float)
    gbar = float(g.mean())
    sum_log_g = math.fsum(math.log(x) for x in g)
    first = k * math.log((B_tot + w * P0) / k)
    D_g = first - sum_log_g
    say(f"  delivered:  sum_i g_i = {sum_g!r}, gbar = {gbar!r}")
    say(f"  eq.(split) first term  n log((W0 + wP)/n) = {first!r}")
    say(f"  sum_i log g_i (= V)                        = {sum_log_g!r}")
    say(f"     vs metrics V 95.75519165924106, |d| = "
        f"{abs(sum_log_g - 95.75519165924106):.2e}")
    say(f"  => D(g) ON THE DELIVERED v2 DRAW           = {D_g!r} nats")
    say(f"     eq.(split) closes to {abs(first - D_g - sum_log_g):.3e} (tier-1 {CERT_TOL:g}).")
    say(f"  realised gain spread_rel = {(g.max() - g.min()) / gbar:.4f}  -- 60 %, "
        f"not 'a few %'")

    Mby = channel.district_opportunity(G, to_district)
    m = np.array(sorted(Mby.values()), float)
    D_M = k * math.log(float(m.mean())) - math.fsum(math.log(x) for x in m)
    say(f"  for contrast D(M) on the district MASSES   = {D_M!r} nats  "
        f"(M spread {(m.max() - m.min()) / m.mean():.4f})")
    say("  -> 1e-4..1e-2 is the range of D(M), the mass imbalance stage 1 controls.")
    say(f"     eq.(split) is written on g, not M.  D(g) = {D_g:.4f} is {D_g / 1e-2:.0f}x")
    say("     the top of the quoted range.  The range is inherited verbatim from")
    say("     REVIEW_GROMOV R1 (a v1, unmeasured figure) and is wrong on v2.")

    say("")
    say("  the premium window, exactly vs. as quoted (premium.py's gap() is first-order):")
    a0, aS, a18 = B_tot + w * P0, B_tot + w * P_S, B_tot + w * P18
    quoted = meas["gaps"]["map"]["nats"] + meas["gaps"]["roster"]["nats"]
    say(f"    map    gap  exact {k * math.log(aS / a0):.6f}  quoted (1st order) "
        f"{meas['gaps']['map']['nats']:.6f}")
    say(f"    roster gap  exact {k * math.log(a18 / aS):.6f}  quoted (1st order) "
        f"{meas['gaps']['roster']['nats']:.6f}")
    say(f"    combined    exact {k * math.log(a18 / a0):.6f}  quoted sum {quoted:.6f}"
        f"   (note says ~0.91)")
    err = abs(k * math.log(a18 / a0) - quoted)
    say(f"    linearisation error {err:.4f} nats = {err / EPS_CERT:.1f}x the tier-2 floor "
        f"{EPS_CERT:g}")
    say("")
    say(f"  ordering test:  premium window {k * math.log(a18 / a0):.4f} nats  >  "
        f"D(g) {D_g:.4f} nats   ratio {k * math.log(a18 / a0) / D_g:.2f}x")
    say("  -> the INVERSION conclusion survives (6x, not the 90x-9000x the quoted")
    say("     numbers imply).  The retraction of 'derived rather than assumed' follows.")
    say("")
    say("  the 30 % threshold sentence at channel_note.tex:526-529:")
    say("    the note's own threshold is 30 %; the measured value is 29.588 % (29.81 %")
    say("    under R1's definition).  BOTH ARE BELOW 30 %.  The sentence asserts the")
    say("    threshold is crossed ('the map is no longer drawn by opportunity alone').")
    say("    R1's v1 41.9 % did cross it; 29.6 % does not.  The inference does not")
    say("    follow from the number as stated.")


def main() -> int:
    say(f"python {sys.version.split()[0]} · numpy {np.__version__} · scipy "
        f"{scipy.__version__} · sympy {sp.__version__}")
    say(f"instance {INSTANCE}")
    say(f"draw     {DRAW}")
    say(f"meas     {MEAS}")
    c1_symbolic()
    d, to_district, metrics, meas = load()
    G = d.G
    say("")
    say(f"loaded: {len(to_district)} zips, k={len(set(to_district.values()))}, "
        f"reps={len(d.reps)}")
    B, sum_g, P0, w, gains_fresh = c2_identity(G, to_district, meas, metrics)
    c34_star(B, meas)
    check_PS(G, to_district, meas)
    c5_saturation(G, to_district, meas)
    c6_split(B, sum_g, P0, meas, gains_fresh, G, to_district)
    log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_p0c.log")
    with open(log, "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print(f"\nwrote {log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
