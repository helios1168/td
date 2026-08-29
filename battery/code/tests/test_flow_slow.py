"""
test_flow_slow.py -- the measurement tier for W4 (Option D / D+C).  `TD_SLOW=1` only.

`test_flow.py` proves the formulation and the contract.  This module answers the questions
the option comparison actually needs, and prints them as tables:

  1  the full T0 ground-truth tier through the real driver, three methods, zero bugs
  2  the T1 sweep (63 pairs, 5..82 zips, 60 s cap): what certifies and what does not
  3  a size ladder across all six registry keys: the largest n each one still certifies
  4  the six named contiguity failures (CLAUDE.md trap 11): status, gap, time, components
  5  the eps sensitivity of the chord method: k, eps, achieved gap, nodes, time

Everything runs through `contiguity_bench.py` with a worker pool, so the wall time is a few
minutes rather than an hour (the T1 sweep is ~6 min on 8 workers), and the driver itself
(spawn, SIGALRM backstop, validator, scoring) is exercised on every job.  Results land in a
per-pid `battery/results/contiguity/` directory that is deleted afterwards -- never anything
under `battery/figures/`.

What is asserted vs. what is reported.  Correctness is asserted everywhere: every row valid,
`LB <= UB`, `excess_pieces == 0` and a real certificate behind every `optimal`, no bugs from
the harness' cross-method audit, and every T1 pair up to `N_ALWAYS` zips certified.  Above
that the numbers are *reported*, because "where does the flow LP run out of steam" is the
finding W4 exists to produce (OPTIONS.md §4 names LP weakness at scale as the expected
outcome), not a property to be asserted into existence.  The one aggregate assertion,
`CERT_FLOOR`, is a regression guard set well below what was measured.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if p not in sys.path:
        sys.path.insert(0, p)

from contig_methods import REGISTRY, base                       # noqa: E402
from instances import build_T1, build_pair, named_failures      # noqa: E402

SLOW = True
THETA, LAM = 0.40, 0.30
WORKERS = 8
CAP = 60.0
# Measured on this machine (2026-08-29, 8 workers, 60 s cap): every T1 pair up to 45 zips
# certified under both methods; 94 of 126 rows certified overall.  The guards sit below
# both, so they catch a regression without re-freezing a timing-dependent result.
N_ALWAYS = 45
CERT_FLOOR = 0.65
FLOW_KEYS = ("flow", "flow_loosecaps", "flow_selroot", "flow_rooted", "flow_pwl",
             "flow_pwl_e4")
GLOBAL_KEYS = tuple(k for k in FLOW_KEYS if k != "flow_rooted")

# largest certified n seen by each registry key, filled in as the tests run and printed by
# the last one
_CERTIFIED_N: dict = {}


def _note_certified(method, n, ok):
    cur = _CERTIFIED_N.setdefault(method, dict(best=0, worst_fail=None))
    if ok:
        cur["best"] = max(cur["best"], n)
    elif cur["worst_fail"] is None or n < cur["worst_fail"]:
        cur["worst_fail"] = n


# ==================================================================== the driver, wrapped
def bench(tag, *, methods, tiers, cap=CAP, workers=WORKERS, regex=None, timeout=7200):
    """Run `contiguity_bench.py` and return `(rows, bugs)`; always cleans up its run dir."""
    run_id = f"_test_w4slow_{tag}_{os.getpid()}"
    out = os.path.join(ROOT, "battery", "results", "contiguity", run_id)
    shutil.rmtree(out, ignore_errors=True)
    cmd = [sys.executable, os.path.join(ROOT, "battery", "code", "contiguity_bench.py"),
           "--methods", ",".join(methods), "--tiers", ",".join(tiers),
           "--cap", str(cap), "--workers", str(workers), "--run-id", run_id, "--quiet"]
    if regex:
        cmd += ["--instances", regex]
    try:
        t0 = time.time()
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        assert p.returncode == 0, p.stderr[-4000:]
        with open(os.path.join(out, "rows.jsonl")) as f:
            rows = [json.loads(line) for line in f if line.strip()]
        with open(os.path.join(out, "bugs.json")) as f:
            bugs = json.load(f)
        print(f"[bench {tag}] {len(rows)} rows in {time.time() - t0:.0f}s wall "
              f"({workers} workers, cap {cap:g}s)")
        return rows, bugs
    finally:
        shutil.rmtree(out, ignore_errors=True)


def _g(row, key, default=None):
    v = row.get(key, default)
    return default if v is None else v


def _check_row(row):
    """Contract hygiene that must hold on every row regardless of status."""
    assert row["valid"], (row["instance"], row["method"], row["violations"])
    ub, lb = row.get("UB"), row.get("LB")
    if ub is not None and lb is not None:
        assert lb <= ub + base.CERT_TOL + _g(row, "eps", 0.0), \
            (row["instance"], row["method"], lb, ub)
    if row.get("to_a") is not None and row["status_eff"].startswith("optimal"):
        assert row["excess_pieces"] == 0, (row["instance"], row["method"])


def _table(rows, methods, sort_key=lambda r: (r["n"], r["instance"])):
    """One line per (instance, method), sorted by size."""
    by = {}
    for r in rows:
        by.setdefault(r["instance"], {})[r["method"]] = r
    head = f"{'instance':<30}{'n':>5}{'cc':>4}  " + "".join(
        f"{m:<34}" for m in methods)
    print(head)
    print("-" * len(head))
    for name in sorted(by, key=lambda k: sort_key(next(iter(by[k].values())))):
        r0 = next(iter(by[name].values()))
        cells = []
        for m in methods:
            r = by[name].get(m)
            if r is None:
                cells.append(f"{'-':<34}")
                continue
            gap = r.get("gap_nats")
            gtxt = "        -" if gap is None else f"{gap:9.2e}"
            cells.append(f"{r['status_eff']:<15}{gtxt} {_g(r, 't_total', 0.0):6.1f}s   ")
        print(f"{name:<30}{r0['n']:>5}{_g(r0, 'pair_components', 0):>4}  " + "".join(cells))


def _covariate_report(rows, methods):
    """What actually predicts a miss.

    OPTIONS.md's fourth regime is "sparse active zips with zero-value glue", and the W4 brief
    flags glue degeneracy as out of scope for the formulation but worth *measuring* -- so the
    point-biserial correlation between certification and `active_frac` is reported here
    alongside size and structure.  Reported, never asserted: with 63 pairs these are
    descriptive, not inferential.
    """
    import numpy as np                                       # noqa: PLC0415
    cov = {sp.name: build_pair(sp).covariates for sp in build_T1()}
    keys = ("n", "n_edges", "pair_components", "articulation_points", "gini_u",
            "top5_share_u", "active_frac")
    print("\n[what predicts a miss]  point-biserial corr(certified, covariate), "
          "and the two group means")
    hdr = f"{'method':<10}{'covariate':<22}{'corr':>8}{'mean|certified':>17}{'mean|missed':>14}"
    print(hdr)
    print("-" * len(hdr))
    for m in methods:
        rr = [r for r in rows if r["method"] == m]
        y = np.array([1.0 if r["status_eff"] == "optimal" else 0.0 for r in rr])
        if y.min() == y.max():
            print(f"{m:<10}(all rows agree; no contrast)")
            continue
        for k in keys:
            v = np.array([float(cov[r["instance"]].get(k) or 0.0) for r in rr])
            c = float(np.corrcoef(y, v)[0, 1]) if v.std() > 0 else float("nan")
            print(f"{m:<10}{k:<22}{c:>8.3f}{v[y == 1].mean():>17.3f}{v[y == 0].mean():>14.3f}")


# ================================================================ 1. T0 through the driver
def test_flow_slow_1_t0_full_harness():
    """The curated ground-truth tier, three methods, through the pool.  `bugs.json` is the
    harness' own cross-method audit (LB above another method's global UB, invalid
    certificates, product above the free product) -- it must be empty."""
    methods = ("flow", "flow_pwl", "flow_rooted")
    rows, bugs = bench("t0", methods=methods, tiers=("T0",))
    assert not bugs, bugs
    assert len(rows) == 3 * 13, len(rows)
    for r in rows:
        _check_row(r)
        want = "optimal_rooted" if r["method"] == "flow_rooted" else "optimal"
        assert r["status_eff"] == want, (r["instance"], r["method"], r["status_eff"])
        if r["method"] != "flow_rooted":
            assert r["valid_certificate"], (r["instance"], r["method"])
        _note_certified(r["method"], r["n"], True)
    _table(rows, methods)


# ============================================================================ 2. T1 sweep
def test_flow_slow_2_t1_sweep():
    """63 real battery pairs, 5 to 82 zips, 60 s cap -- where the wall actually is.

    Measured 2026-08-29: both methods certify every pair up to 45 zips; from 50 zips up the
    single flow MILP becomes the binding constraint and 32 of 126 rows stop on the cap, each
    with a valid bound and a 1e-4..1e-2 nat gap.  Size alone does not predict it -- four
    62-zip two-component pairs certify in under 4 s while a 50-zip single-component pair does
    not -- which is the LP-strength story, not a scale story, and is exactly what Option D
    was expected to expose (OPTIONS.md §4).  `flow` reached 69 zips, `flow_pwl` 62.
    """
    methods = ("flow", "flow_pwl")
    rows, bugs = bench("t1", methods=methods, tiers=("T1",))
    assert not bugs, bugs
    specs = {s.name: s for s in build_T1()}
    assert len(rows) == 2 * len(specs), (len(rows), len(specs))

    for r in rows:
        _check_row(r)
        certified = r["status_eff"] == "optimal"
        _note_certified(r["method"], r["n"], certified)
        if certified:
            assert r["valid_certificate"], (r["instance"], r["method"])
        elif r["n"] <= N_ALWAYS:
            raise AssertionError((r["instance"], r["method"], r["n"], r["status_eff"],
                                  r.get("gap_nats"), r.get("message")))

    _table(rows, methods)
    big = [r for r in rows if r["n"] > 62]
    print("\n[T1 > 62 zips]")
    for r in sorted(big, key=lambda r: (r["n"], r["method"])):
        print(f"  {r['instance']:<28} n={r['n']:>3} {r['method']:<10} {r['status_eff']:<15}"
              f" gap={_g(r, 'gap_nats', float('nan')):.3e} t={_g(r, 't_total', 0):.1f}s"
              f" iters={r['iters']} nodes={r['nodes']}")
    cert = sum(1 for r in rows if r["status_eff"] == "optimal")
    share = cert / len(rows)
    print(f"\n[T1 certified] {cert}/{len(rows)} rows ({100.0 * share:.1f}%), by method: " +
          ", ".join(f"{m}={sum(1 for r in rows if r['method'] == m and r['status_eff'] == 'optimal')}"
                    f"/{sum(1 for r in rows if r['method'] == m)}" for m in methods))
    uncert = sorted({r["n"] for r in rows if r["status_eff"] != "optimal"})
    print(f"[T1 uncertified sizes] {uncert}")
    _covariate_report(rows, methods)
    assert share >= CERT_FLOOR, f"certified share {share:.3f} below the {CERT_FLOOR} guard"


# =============================================================== 3. the six variants, laddered
def test_flow_slow_3_variant_ladder():
    """All six registry keys on a size ladder cut out of T1.

    The full 63-pair sweep is run for `flow` and `flow_pwl` (test 2); the four controls --
    the two encoding variants, the rooted restriction and the coarse eps -- only need a
    ladder to answer "largest n still certified", so they get one pair per size bucket.
    """
    sizes = (8, 15, 27, 34, 45, 56, 62, 82)
    picked, seen = [], set()
    for s in sorted(build_T1(), key=lambda s: (s.n_expected, s.name)):
        if s.n_expected in sizes and s.n_expected not in seen:
            seen.add(s.n_expected)
            picked.append(s.name)
    regex = "^(" + "|".join(re.escape(n) for n in picked) + ")$"
    rows, bugs = bench("ladder", methods=FLOW_KEYS, tiers=("T1",), regex=regex)
    assert not bugs, bugs
    assert len(rows) == len(FLOW_KEYS) * len(picked), (len(rows), len(picked))

    for r in rows:
        _check_row(r)
        certified = r["status_eff"].startswith("optimal")
        _note_certified(r["method"], r["n"], certified)
        if r["method"] in GLOBAL_KEYS and r["status_eff"] == "optimal":
            assert r["valid_certificate"], (r["instance"], r["method"])
        if r["method"] == "flow_rooted":
            assert r["ub_scope"] == "rooted" and not r["valid_certificate"]

    _table(rows, FLOW_KEYS)

    # the rooted restriction's price, wherever both certified the same instance
    by = {}
    for r in rows:
        by.setdefault(r["instance"], {})[r["method"]] = r
    print("\n[cost of fixing roots]  global optimum vs the rooted restriction")
    for name, d in sorted(by.items(), key=lambda kv: next(iter(kv[1].values()))["n"]):
        g, rt = d.get("flow"), d.get("flow_rooted")
        if g and rt and g.get("LB") is not None and rt.get("LB") is not None:
            print(f"  {name:<30} n={g['n']:>3}  flow {g['LB']:.6f}   "
                  f"rooted {rt['LB']:.6f}   loss {g['LB'] - rt['LB']:.2e} nats")


# ==================================================================== 4. the named failures
def test_flow_slow_4_named_failures():
    """The six pairs that broke the legacy loop (CLAUDE.md trap 11 / PLAN.md C.0).

    Three of them are the disconnection mechanism, which this formulation handles by
    construction; two are pure scale at 125 and 205 zips, which is where the flow LP is
    expected to lose.  Nothing here is asserted beyond validity and `LB <= UB` -- the point
    is the table.
    """
    nf = named_failures()
    regex = "^(" + "|".join(re.escape(s.name) for s in nf) + ")$"
    methods = ("flow", "flow_pwl")
    rows, bugs = bench("named", methods=methods, tiers=("T1", "T2", "T4"), regex=regex)
    assert not bugs, bugs
    got = {r["instance"] for r in rows}
    assert {s.name for s in nf} <= got, ({s.name for s in nf} - got)

    for r in rows:
        _check_row(r)
        _note_certified(r["method"], r["n"], r["status_eff"] == "optimal")

    print("\n[named failures]")
    hdr = (f"{'instance':<28}{'n':>5}{'cc':>4}{'method':>10}  {'status':<15}"
           f"{'gap_nats':>11}{'t':>8}{'iters':>7}{'nodes':>9}  rung")
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(rows, key=lambda r: (r["n"], r["method"])):
        extra = r.get("extra") or {}
        print(f"{r['instance']:<28}{r['n']:>5}{_g(r, 'pair_components', 0):>4}"
              f"{r['method']:>10}  {r['status_eff']:<15}"
              f"{_g(r, 'gap_nats', float('nan')):>11.3e}{_g(r, 't_total', 0.0):>7.1f}s"
              f"{r['iters']:>7}{r['nodes']:>9}  {extra.get('milp_rung')}")


# ================================================================== 5. eps sensitivity (D3)
def test_flow_slow_5_eps_sensitivity():
    """`flow_pwl` at 1e-6 against `flow_pwl_e4` at 1e-4, in process so the k / eps / node
    numbers line up per instance.  The trade is rows against certified tightness: k scales
    like `log(g_hi/g_lo) / sqrt(8*eps)`, so a 100x looser eps is a 10x smaller model."""
    specs = sorted(build_T1(), key=lambda s: s.n_expected)
    sizes = (13, 27, 45, 56)
    picked, seen = [], set()
    for s in specs:
        if s.n_expected in sizes and s.n_expected not in seen:
            seen.add(s.n_expected)
            picked.append(s)
    hdr = (f"{'instance':<28}{'n':>5}{'method':>13}{'k_a':>6}{'k_b':>6}{'eps':>11}"
           f"{'gap_nats':>11}{'nodes':>9}{'rows':>8}{'t':>8}")
    print("\n[eps sensitivity]")
    print(hdr)
    print("-" * len(hdr))
    for sp in picked:
        pi = build_pair(sp)
        for key in ("flow_pwl", "flow_pwl_e4"):
            spec = REGISTRY[key]
            t0 = time.time()
            res = base.run_method(spec.solve, pi.G, pi.nodes, theta=THETA, lam=LAM, rho=0.0,
                                  respect_state=False, time_limit=CAP, seed=0, **spec.kwargs)
            row = base.evaluate(pi.G, pi.nodes, res, theta=THETA, lam=LAM)
            assert row["valid"], (sp.name, key, row["violations"])
            e = res.extra
            print(f"{sp.name:<28}{pi.n:>5}{key:>13}{e['k_a']:>6}{e['k_b']:>6}"
                  f"{res.eps:>11.3e}{row['gap_nats']:>11.3e}{res.nodes:>9}"
                  f"{e['n_rows']:>8}{time.time() - t0:>7.1f}s"
                  f"{'' if res.status == 'optimal' else '  [' + res.status + ']'}")
            _note_certified(key, pi.n, res.status == "optimal")
            if res.status == "optimal":
                assert row["gap_nats"] <= base.CERT_TOL + res.eps, (sp.name, key)
    print("  (k ~ log(range)/sqrt(8*eps): a 100x looser eps buys a ~10x smaller model)")


# ============================================================================== 6. summary
def test_flow_slow_6_summary():
    """Largest n certified by each registry key across everything this module ran."""
    assert _CERTIFIED_N, "run the whole module: nothing was recorded"
    print("\n[largest certified n per variant]")
    print(f"{'method':<16}{'largest certified n':>22}{'smallest uncertified n':>26}")
    for m in FLOW_KEYS:
        d = _CERTIFIED_N.get(m)
        if not d:
            continue
        wf = d["worst_fail"]
        print(f"{m:<16}{d['best']:>22}{('-' if wf is None else wf):>26}")


if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in list(globals().items())
                     if k.startswith("test_") and callable(v)]:
        t = time.time()
        fn()
        print(f"PASS {name} ({time.time() - t:.1f}s)\n")
