"""__main__.py -- `python -m twin_export {stats|twin|validate|audit}`.

Exit codes
    0   success
    2   a privacy guard fired (k-anonymity, or the JSON leak guard)
    3   a validation or twin_check failure
    4   an input could not be read, joined, or made sense of

Nothing is written until the stage that writes it succeeds; `twin` refuses to write the
instance file until the audit table has been shown and confirmed (`--yes` for a scripted
run, but the runbook asks the user to read it).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from . import __version__
from . import _territory_vendored as TV
from . import audit as AU
from . import io as IO
from . import synth as SY
from .agg import Agg, KAnonError
from .check import format_rows, twin_check
from .config import Cfg
from .io import InputError, LeakGuardError
from .stats import blocks

EXIT_OK, EXIT_PRIVACY, EXIT_CHECK, EXIT_INPUT = 0, 2, 3, 4


# ------------------------------------------------------------------------- args
def build_parser():
    p = argparse.ArgumentParser(
        prog="python -m twin_export",
        description="Build a privacy-audited synthetic twin of a confidential ZCTA "
                    "instance.  Two files leave: twin_stats.json and "
                    "twin_instance.json.gz.  See README.md for the runbook.")
    p.add_argument("command", choices=["stats", "twin", "validate", "audit"])
    g = p.add_argument_group("inputs")
    g.add_argument("--graph", help="edge table (.parquet/.feather -- the expected "
                                   "work-machine format), edge list (.csv), pickled "
                                   "networkx graph (.gpickle/.pkl), .graphml/.gml, or .npz")
    g.add_argument("--graph-format", default=None,
                   help="override the format inferred from the extension")
    g.add_argument("--u-col", default=None, help="edge-table column holding the first ZCTA")
    g.add_argument("--v-col", default=None, help="edge-table column holding the second ZCTA")
    g.add_argument("--build-rook-from", default=None,
                   help="build Rook adjacency from a polygon shapefile (needs geopandas); "
                        "never downloads anything")
    g.add_argument("--states", default=None, help="zcta,state table (if the graph has no "
                                                  "state attribute)")
    g.add_argument("--coords", default=None, help="zcta,lon,lat table; used only for the "
                                                  "W11 km radius, never exported per ZCTA")
    g.add_argument("--opportunity", help="zcta,M")
    g.add_argument("--sales", help="zcta,A,B")
    g.add_argument("--reps", help="zcta,rep_a,rep_b")
    g.add_argument("--tiger-shapefile", default=None,
                   help="optional local TIGER shapefile; enables graph.edge_jaccard_vs_tiger")

    o = p.add_argument_group("outputs")
    o.add_argument("--out", default=".", help="output directory (default: cwd)")
    o.add_argument("--stats", default=None, help="an existing twin_stats.json to reuse")
    o.add_argument("--twin", default=None, help="an existing twin_instance.json.gz "
                                                "(validate --twin)")
    o.add_argument("--explain", action="store_true",
                   help="also write leaving.txt: what is in twin_stats.json, in English")
    o.add_argument("--yes", action="store_true", help="skip the interactive confirmation")

    d = p.add_argument_group("dials")
    d.add_argument("--min-support", type=int, default=20)
    d.add_argument("--min-state", type=int, default=100)
    d.add_argument("--sigma", type=float, default=0.10, dest="rank_sigma",
                   help="rank-jitter sigma (default 0.10)")
    d.add_argument("--theta", type=float, default=0.40)
    d.add_argument("--lam", type=float, default=0.30)
    d.add_argument("--n-bins", type=int, default=200)
    d.add_argument("--seed", type=int, default=0)
    d.add_argument("--no-strip-scale", dest="strip_scale", action="store_false",
                   default=True, help="export values in their own units (NOT recommended)")
    d.add_argument("--strip-penetration", action="store_true",
                   help="round the exported saturation to the nearest 0.05")
    d.add_argument("--jitter-smooth", type=float, default=0.0,
                   help="graph-smooth the rank jitter (off by default)")
    d.add_argument("--coarsen", default=None, choices=[None, "decile", "percentile"])
    d.add_argument("--swap-rounds", type=int, default=0)
    d.add_argument("--no-radius-km", dest="radius_km", action="store_false", default=True,
                   help="omit the W11 km territory-radius aggregates")
    d.add_argument("--tiger-vintage", default="2025")
    d.add_argument("--zcta-vintage", default="2025")
    d.add_argument("--allow-partial", action="store_true",
                   help="proceed when fewer than 99%% of graph ZCTAs join to values")
    d.add_argument("--sigma-sweep", default=None,
                   help="audit only: comma-separated sigmas, e.g. 0.05,0.10,0.15,0.20")
    d.add_argument("--quiet", action="store_true")
    return p


def cfg_from_args(a):
    return Cfg(min_support=a.min_support, min_state=a.min_state, rank_sigma=a.rank_sigma,
               theta=a.theta, lam=a.lam, n_bins=a.n_bins, seed=a.seed,
               strip_scale=a.strip_scale, strip_penetration=a.strip_penetration,
               jitter_smooth=a.jitter_smooth, coarsen=a.coarsen,
               swap_rounds=a.swap_rounds, radius_km=a.radius_km,
               tiger_vintage=a.tiger_vintage, zcta_vintage=a.zcta_vintage,
               allow_partial=a.allow_partial, verbose=not a.quiet)


# ------------------------------------------------------------------------ loading
def load_instance(a, cfg):
    for name in ("opportunity", "sales", "reps"):
        if not getattr(a, name):
            raise InputError("--%s is required for `%s`" % (name, a.command))
    if not a.graph and not a.build_rook_from:
        raise InputError("--graph (or --build-rook-from) is required")
    G, greport = IO.read_graph(a.graph, states=a.states, fmt=a.graph_format,
                               u_col=a.u_col, v_col=a.v_col,
                               build_rook_from=a.build_rook_from, verbose=cfg.verbose)
    inst, jreport = IO.join_inputs(G, a.opportunity, a.sales, a.reps, cfg)
    if a.coords:
        IO.attach_coords(inst, a.coords, cfg)
    inst.no_polygon_count = jreport["only_in_values"]["count"]
    return inst, dict(graph=greport, join=jreport)


def tiger_edges_if_asked(a, cfg):
    if not a.tiger_shapefile:
        return None
    try:
        import geopandas  # noqa: F401
    except ImportError:
        cfg.log("--tiger-shapefile given but geopandas is not installed; skipping "
                "graph.edge_jaccard_vs_tiger")
        return None
    cfg.log("building the TIGER comparison graph from %s" % a.tiger_shapefile)
    T, _ = IO.read_graph(None, build_rook_from=a.tiger_shapefile, verbose=cfg.verbose)
    return list(T.edges)


# ---------------------------------------------------------------------- commands
def cmd_stats(a, cfg):
    inst, reports = load_instance(a, cfg)
    t0 = time.time()
    agg = Agg(min_support=cfg.min_support, enforce=True)
    st = blocks(inst, cfg, agg, tiger_edges=tiger_edges_if_asked(a, cfg))
    st["meta"] = _meta(cfg, inst, reports)
    st["inputs"] = _input_report(reports)
    path = os.path.join(a.out, "twin_stats.json")
    _ensure_out(a.out)
    IO.write_json_guarded(st, path, round_sig_digits=cfg.round_sig, verbose=cfg.verbose)
    cfg.log("stats: %d ZCTAs, %d statistics, %.1fs"
            % (inst.n, len(agg.keys()), time.time() - t0))
    if a.explain:
        write_leaving(st, os.path.join(a.out, "leaving.txt"), cfg)
    return EXIT_OK


def cmd_twin(a, cfg):
    inst, reports = load_instance(a, cfg)
    st = _load_or_make_stats(a, cfg, inst, reports)
    cfg.log("synthesising the twin (sigma=%.3f, seed=%d) ..." % (cfg.rank_sigma, cfg.seed))
    t0 = time.time()
    tw = SY.build_twin(inst, st, cfg)
    cfg.log("synthesis done in %.1fs" % (time.time() - t0))

    au = AU.audit(inst, tw, cfg)
    print("")
    print(AU.format_audit(au))
    print("")
    if not a.yes:
        try:
            resp = input("Export this twin?  The two files leave the work machine. [y/N] ")
        except EOFError:
            resp = ""
        if resp.strip().lower() not in ("y", "yes"):
            print("aborted; nothing written")
            return EXIT_OK

    _ensure_out(a.out)
    twin_obj = _twin_object(inst, tw, cfg, au)
    tinst = IO.twin_to_instance(twin_obj)
    problems = TV.validate(tinst.to_schema_graph(), theta=cfg.theta, lam=cfg.lam)
    if problems:
        print("twin failed the vendored territory.validate:", file=sys.stderr)
        for p in problems:
            print("  " + p, file=sys.stderr)
        return EXIT_CHECK
    rows, passed, twin_stats = twin_check(st, tinst, cfg)
    print("")
    print(format_rows(rows))
    st["twin_check"] = dict(rows=rows, passed=bool(passed))
    st["audit"] = au

    tpath = os.path.join(a.out, "twin_instance.json.gz")
    IO.write_twin(twin_obj, tpath, verbose=cfg.verbose)
    IO.write_json_guarded(au, os.path.join(a.out, "twin_audit.json"),
                          round_sig_digits=cfg.round_sig, verbose=cfg.verbose)
    IO.write_json_guarded(st, os.path.join(a.out, "twin_stats.json"),
                          round_sig_digits=cfg.round_sig, verbose=cfg.verbose)
    if a.explain:
        write_leaving(st, os.path.join(a.out, "leaving.txt"), cfg)
    del twin_stats
    if not passed:
        print("\ntwin_check did NOT pass -- see the FAIL rows above.", file=sys.stderr)
        return EXIT_CHECK
    print("\ntwin_check passed.")
    return EXIT_OK


def cmd_validate(a, cfg):
    if a.twin:
        obj = IO.read_twin(a.twin)
        tinst = IO.twin_to_instance(obj)
        problems = TV.validate(tinst.to_schema_graph(), theta=cfg.theta, lam=cfg.lam)
        print("twin: n=%d m=%d" % (tinst.n, tinst.G.number_of_edges()))
        if problems:
            for p in problems:
                print("  PROBLEM: " + p)
            return EXIT_CHECK
        print("  vendored territory.validate: clean")
        if a.stats:
            with open(a.stats) as f:
                st = json.load(f)
            rows, passed, _ = twin_check(st, tinst, cfg)
            print("")
            print(format_rows(rows))
            st["twin_check"] = dict(rows=rows, passed=bool(passed))
            IO.write_json_guarded(st, a.stats, round_sig_digits=cfg.round_sig,
                                  verbose=cfg.verbose)
            return EXIT_OK if passed else EXIT_CHECK
        return EXIT_OK

    inst, reports = load_instance(a, cfg)
    print("real instance: n=%d m=%d  reps %dA x %dB  states %s"
          % (inst.n, inst.G.number_of_edges(), reports["join"]["n_rep_a"],
             reports["join"]["n_rep_b"], reports["join"]["n_states"] or "none"))
    problems = TV.validate(inst.to_schema_graph(), theta=cfg.theta, lam=cfg.lam)
    if problems:
        print("\nthe REAL data does not satisfy the model's assumptions:")
        for p in problems:
            print("  PROBLEM: " + p)
        print("\nPointwise headroom violations (M_z < max(A+theta*B, B+theta*A)) are a "
              "modelling question, not a bug in this tool -- read CLAUDE.md 'The Model in "
              "One Page' and settle them before exporting.  Disconnected components and "
              "isolated ZCTAs are expected on a national graph (islands).")
        return EXIT_CHECK
    print("  vendored territory.validate: clean")
    return EXIT_OK


def cmd_audit(a, cfg):
    inst, reports = load_instance(a, cfg)
    st = _load_or_make_stats(a, cfg, inst, reports)
    if a.sigma_sweep:
        sigmas = [float(s) for s in str(a.sigma_sweep).split(",") if s.strip()]
        rows = AU.sigma_sweep(inst, st, cfg, sigmas, SY.build_twin, None)
        print("")
        print(AU.format_sweep(rows))
        st.setdefault("audit", {})["sigma_sweep"] = rows
        _ensure_out(a.out)
        IO.write_json_guarded(st, os.path.join(a.out, "twin_stats.json"),
                              round_sig_digits=cfg.round_sig, verbose=cfg.verbose)
        return EXIT_OK
    tw = SY.build_twin(inst, st, cfg)
    au = AU.audit(inst, tw, cfg)
    print("")
    print(AU.format_audit(au))
    _ensure_out(a.out)
    IO.write_json_guarded(au, os.path.join(a.out, "twin_audit.json"),
                          round_sig_digits=cfg.round_sig, verbose=cfg.verbose)
    return EXIT_OK


# -------------------------------------------------------------------- assembling
def _ensure_out(out):
    if out and not os.path.isdir(out):
        os.makedirs(out, exist_ok=True)


def _load_or_make_stats(a, cfg, inst, reports):
    if a.stats and os.path.exists(a.stats):
        cfg.log("reusing %s" % a.stats)
        with open(a.stats) as f:
            return json.load(f)
    cfg.log("computing the aggregates (no --stats given) ...")
    agg = Agg(min_support=cfg.min_support, enforce=True)
    st = blocks(inst, cfg, agg, tiger_edges=tiger_edges_if_asked(a, cfg))
    st["meta"] = _meta(cfg, inst, reports)
    st["inputs"] = _input_report(reports)
    return st


def _meta(cfg, inst, reports):
    m = cfg.to_dict()
    m.update(twin_export_version=__version__, built=time.strftime("%Y-%m-%d"),
             n=inst.n, m=inst.G.number_of_edges(),
             python="%d.%d" % (sys.version_info[0], sys.version_info[1]),
             numpy=np.__version__,
             graph_hash=IO.graph_hash(inst.z, [(inst.z[u], inst.z[v])
                                               for u, v in inst.G.edges]),
             sigma_effective=cfg.rank_sigma,
             scale_convention="median")
    del reports
    return m


def _input_report(reports):
    j = dict(reports["join"])
    g = dict(reports["graph"])
    g.pop("source", None)
    return dict(join=j, graph=g)


def _twin_object(inst, tw, cfg, au):
    z = list(inst.z)
    meta = dict(seed=cfg.seed, rank_sigma=cfg.rank_sigma, coarsen=cfg.coarsen,
                swap_rounds=cfg.swap_rounds, alpha=tw["report"]["reps"]["alpha"],
                n_rep_a=tw["report"]["reps"]["n_rep_a"],
                n_rep_b=tw["report"]["reps"]["n_rep_b"],
                theta=cfg.theta, lam=cfg.lam,
                graph_hash=IO.graph_hash(z, [(z[u], z[v]) for u, v in inst.G.edges]),
                tiger_vintage=cfg.tiger_vintage, zcta_vintage=cfg.zcta_vintage,
                n=inst.n, m=inst.G.number_of_edges(),
                twin_export_version=__version__, built=time.strftime("%Y-%m-%d"),
                min_support=cfg.min_support, min_state=cfg.min_state,
                strip_scale=cfg.strip_scale, scale_convention="median",
                jitter_smooth=cfg.jitter_smooth,
                sigma_effective=au.get("sigma_effective"))
    # Round here, not in the writer, so that validate/twin_check below see exactly the
    # numbers that get written.  M rounds up and A, B round down, so six-significant-figure
    # rounding can never turn a satisfied headroom constraint into a violated one.
    Mr = _round_dir(tw["M"], cfg.round_sig, up=True)
    Ar = _round_dir(tw["A"], cfg.round_sig, up=False)
    Br = _round_dir(tw["B"], cfg.round_sig, up=False)
    nodes = dict(z=z, A=[float(x) for x in Ar], B=[float(x) for x in Br],
                 M=[float(x) for x in Mr],
                 rep_a=[int(x) for x in tw["rep_a"]], rep_b=[int(x) for x in tw["rep_b"]])
    if inst.state is not None:
        nodes["state"] = list(inst.state)
    edges = dict(u=[z[int(u)] for u, _ in inst.G.edges],
                 v=[z[int(v)] for _, v in inst.G.edges])
    audit_small = dict(verdict=au["verdict"],
                       individual_max_spearman=au["individual_max_spearman"],
                       neighbourhood_min_corr=au["neighbourhood_min_corr"],
                       rank_sigma=au["rank_sigma"], rho2_expected=au["rho2_expected"],
                       headroom=au.get("headroom"), reps=au.get("reps"))
    return dict(meta=meta, nodes=nodes, edges=edges, audit=audit_small)


def _round_dir(v, sig, up):
    """Round every element to `sig` significant figures, always up or always down."""
    import math
    out = np.asarray(v, dtype=float).copy()
    nz = out > 0
    e = np.floor(np.log10(np.maximum(out[nz], 1e-300)))
    f = np.power(10.0, sig - 1 - e)
    scaled = out[nz] * f
    out[nz] = (np.ceil(scaled) if up else np.floor(scaled)) / f
    del math
    return out


# ------------------------------------------------------------------- leaving.txt
LEAVING_INTRO = """\
WHAT LEAVES THIS MACHINE
========================
Generated from twin_stats.json itself, so it cannot drift from what was actually written.

Two files, and nothing else:

  twin_stats.json        aggregate statistics.  No per-ZCTA number appears in it.  Every
                         value was gated on k-anonymity (min_support = %(min_support)d
                         underlying ZCTAs); every quantile is the mean of a window of order
                         statistics, never a single ZCTA's value, and no minimum or maximum
                         is reported; the largest coarse-CDF bin is merged downward until no
                         single ZCTA supplies half its mass; per-state blocks appear only for
                         states with at least %(min_state)d ZCTAs (everything else is pooled
                         into OTHER); every number is rounded to %(round_sig)d significant
                         figures.
  twin_instance.json.gz  a SYNTHETIC instance.  Public ZCTA ids, the public Rook edge list
                         and public state membership are real; M, A, B and the rep maps are
                         redrawn from the aggregates after a rank jitter of sigma =
                         %(rank_sigma)s.  Rep names are replaced by integers.  No geometry.

Scale: %(scale_note)s

The aggregate blocks in twin_stats.json:
"""

BLOCK_NOTES = {
    "scale": "market-share ratios: saturation (A+B over M), book ratio, active/glue shares",
    "marginals": "distribution shape of M, A, B and the A/M, B/M ratios: lognormal and "
                 "dPlN fits, windowed quantiles, a coarse CDF of bin means",
    "conditional": "how the A/B share varies across M-deciles, and how A and B co-move",
    "headroom": "how much slack M leaves over max(A + theta B, B + theta A)",
    "spatial": "how strongly neighbouring ZCTAs resemble each other (Moran's I, hop "
               "correlations) -- the structure the twin is meant to reproduce",
    "graph": "adjacency structure only; derivable from public TIGER geometry",
    "territories": "how many reps each firm has, how big and how fragmented their "
                   "territories are, how misaligned the two firms' maps are, and what the "
                   "census decomposition looks like",
    "per_state": "per-state medians and IQRs, for states above the size floor",
    "radius": "how far a rep's ZCTAs sit from the rep's own centre, in hops and km "
              "(W11 travel-cost calibration)",
    "twin_check": "the same statistics recomputed on the synthetic twin, with tolerances",
    "audit": "the privacy audit: individual-level vs neighbourhood-level agreement",
    "meta": "settings and versions",
    "inputs": "join diagnostics: how many ZCTAs matched between the graph and the tables",
}


def write_leaving(st, path, cfg):
    meta = st.get("meta", {})
    scale_note = ("stripped -- M, A and B were all divided by one common number, the "
                  "median positive M, so no dollar amount appears anywhere and every "
                  "ratio is untouched"
                  if meta.get("strip_scale", True)
                  else "NOT stripped -- values are in their own units (--no-strip-scale)")
    txt = [LEAVING_INTRO % dict(min_support=meta.get("min_support", cfg.min_support),
                                min_state=meta.get("min_state", cfg.min_state),
                                round_sig=meta.get("round_sig", cfg.round_sig),
                                rank_sigma=meta.get("rank_sigma", cfg.rank_sigma),
                                scale_note=scale_note)]
    for k in sorted(st):
        if k.startswith("_"):
            continue
        n_keys = len(st[k]) if isinstance(st[k], dict) else 1
        txt.append("  %-14s %4d entries   %s" % (k, n_keys, BLOCK_NOTES.get(k, "")))
    sup = st.get("_support", {})
    if sup:
        vals = sorted(sup.values())
        txt.append("")
        txt.append("k-anonymity: %d gated statistics; smallest support %d ZCTAs, median %d."
                   % (len(vals), vals[0], vals[len(vals) // 2]))
    ac = st.get("audit", {})
    if ac:
        txt.append("")
        txt.append("audit verdict: %s" % ac.get("verdict", "(not run)"))
    tc = st.get("twin_check", {})
    if tc:
        bad = [r["key"] for r in tc.get("rows", []) if r.get("ok") is False]
        txt.append("twin_check: %s%s" % ("passed" if tc.get("passed") else "FAILED",
                                         ("; failing keys: " + ", ".join(bad[:10]))
                                         if bad else ""))
    txt.append("")
    txt.append("Read before exporting: (1) the audit contrast above -- individual-level "
               "columns weak, neighbourhood-level columns strong; (2) every twin_check row "
               "with ok=false; (3) this file.")
    with open(path, "w") as f:
        f.write("\n".join(txt) + "\n")
    cfg.log("wrote %s" % path)
    return path


# --------------------------------------------------------------------------- main
def main(argv=None):
    a = build_parser().parse_args(argv)
    cfg = cfg_from_args(a)
    fn = dict(stats=cmd_stats, twin=cmd_twin, validate=cmd_validate, audit=cmd_audit)[a.command]
    try:
        return fn(a, cfg)
    except KAnonError as e:
        print("\nPRIVACY GUARD: %s" % e, file=sys.stderr)
        print("Nothing was written.  Raise --min-state, raise --min-support, or drop the "
              "offending block.", file=sys.stderr)
        return EXIT_PRIVACY
    except LeakGuardError as e:
        print("\nPRIVACY GUARD: %s" % e, file=sys.stderr)
        print("Nothing was written.", file=sys.stderr)
        return EXIT_PRIVACY
    except InputError as e:
        print("\nINPUT ERROR: %s" % e, file=sys.stderr)
        return EXIT_INPUT


if __name__ == "__main__":
    sys.exit(main())
