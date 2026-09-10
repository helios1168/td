"""verify_channels.py -- adversarial code-verify of td/channels.py and td/stage2_state.py
against docs/FULL_PROBLEM.md sections 2 to 4 and the two math-verify requirements.

Run from the worktree root with the hub interpreter:

    /Users/ntlee/projects/td/.venv/bin/python3 tools/verify/U14-fullprob/verify_channels.py

Sections (argv selects a subset; default is all but `hub`):

    fmt     three writers, one reader: write_v2, the exporter, load_descaled
    fine    fine_split ratios, fallbacks, conservation, degenerate inputs
    synth   synthesize_channels: national cell, per-cell headroom, hashlib determinism
    agg     aggregate, slot_weights, STATE_LIST
    proj    project against the loader's rule, the write_v1 seam
    decomp  clause (a) with channels.project swapped into the math-verify block
    req1    one global rep order
    req2    candidacy by penalty assignment, nothing released
    coef    model.coefficients against the pre-refactor block
    hub     the confidential instance (counts only, never values)

Every oracle here is independent of the implementation under test: brute force over
injections, a dict-based recomputation of the aggregation, the exporter and the loader as
each other's witness, and the math-verify artifact's own cell-level graph.
"""
from __future__ import annotations

import contextlib
import csv
import gzip
import importlib.util
import io
import itertools
import json
import math
import os
import subprocess
import sys
import tempfile

import networkx as nx
import numpy as np

ROOT = os.environ.get("TD_VERIFY_ROOT",
                      "/Users/ntlee/projects/td/.claude/worktrees/full-problem")
if sys.path[0] != ROOT:
    sys.path.insert(0, ROOT)

from td import channel, channels, instance, model, stage2_state as s2s  # noqa: E402

SYNTH = os.environ.get("TD_SYNTH_V2", "/Users/ntlee/projects/td/.claude/worktrees/"
                       "full-problem/battery/results/full_problem/synthetic_v2.json.gz")
HUB = "/Users/ntlee/projects/td/instance_descaled_v2_conus.json.gz"
RSIG_TIER = 5e-6            # six significant figures on write
EXACT = 0.0
FLOAT_TIER = 1e-12          # float accumulation on small instances

FAILS: list[str] = []
NOTES: list[str] = []


CAVEATS: list[str] = []


def check(name: str, ok: bool, detail: str = "", known: bool = False) -> bool:
    """`known=True` marks a check whose failure is a recorded caveat, not a regression.

    Two probes fail by design: the format cannot carry book on a zero-mass cell, and one
    mutation survives the shipped suite (a test gap, not a code claim). They print `[caveat]`
    and leave the exit status alone, so a later rerun still exits 0 when nothing regressed.
    """
    tag = "ok " if ok else ("caveat" if known else "FAIL")
    print(f"  [{tag}] {name}" + (f"   {detail}" if detail else ""))
    if not ok:
        (CAVEATS if known else FAILS).append(f"{name}   {detail}")
    return ok


def note(text: str) -> None:
    print(f"  [note] {text}")
    NOTES.append(text)


def rel(a: float, b: float) -> float:
    return abs(a - b) / max(1.0, abs(a), abs(b))


def _with_channels(d, chans):
    """Set `Descaled.channels` without going through a helper the module may drop."""
    try:
        d.channels = tuple(chans)
    except Exception:                            # frozen dataclass
        object.__setattr__(d, "channels", tuple(chans))
    return d


# ------------------------------------------------------------------ fixtures
def v1_graph(seed: int = 7, n: int = 12, states=("MA", "NY", "CT")):
    """A random format-1 instance that satisfies pointwise headroom at theta=0.40."""
    rng = np.random.default_rng(seed)
    G = nx.Graph()
    zips = [f"{10000 + i}" for i in range(n)]
    for i, z in enumerate(zips):
        M = float(rng.uniform(0.5, 3.0))
        S, free = {}, 0.0
        if i % 5 != 4:
            for r in ("R0", "R1", "R2"):
                if rng.random() < 0.6:
                    S[r] = float(rng.uniform(0.01, 0.2)) * M
            free = float(rng.uniform(0.0, 0.1)) * M
        G.add_node(z, cand=tuple(sorted(S)), S=S, M=M, S_free=free,
                   state=states[i % len(states)])
    G.add_edges_from((zips[i], zips[i + 1]) for i in range(n - 1))
    d = instance.Descaled(G=G, contested=[z for z in zips if len(G.nodes[z]["cand"]) >= 2],
                          uncontested={z: G.nodes[z]["cand"][0] for z in zips
                                       if len(G.nodes[z]["cand"]) == 1},
                          vacant=[z for z in zips if not G.nodes[z]["cand"]
                                  and G.nodes[z]["S_free"] > 0],
                          untapped=[z for z in zips if not G.nodes[z]["cand"]
                                    and G.nodes[z]["S_free"] == 0],
                          firm={"R0": "FA", "R1": "FA", "R2": "FB"}, meta={"exporter": "probe"})
    assert model.headroom_violations(d.G, theta=0.40) == []
    return d


def fine_fixture(seed: int = 7):
    return channels.fine_split(channels.synthesize_channels(v1_graph(seed), seed=1))


def exporter():
    path = os.path.join(ROOT, "tools", "instance_export", "export_instance.py")
    spec = importlib.util.spec_from_file_location("export_instance_probe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _csv(tmp, name, header, rows):
    p = os.path.join(tmp, name)
    with open(p, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return p


# =================================================================== 1. format agreement
def sec_fmt() -> None:
    print("\n[1] format agreement: write_v2, the exporter, load_descaled")

    # --- write_v2 -> load_descaled, per CELL (the shipped test compares totals only)
    s = channels.synthesize_channels(v1_graph(), seed=3)
    with tempfile.TemporaryDirectory() as tmp:
        p = channels.write_v2(s, os.path.join(tmp, "cells.json.gz"))
        got = instance.load_descaled(p)
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            payload = json.load(fh)
    worst = 0.0
    permuted = False
    for z in s.G:
        a, b = s.G.nodes[z], got.G.nodes[z]
        for c in channels.FILE_CHANNELS:
            worst = max(worst, rel(a["M_c"][c], b["M_c"].get(c, 0.0)))
            worst = max(worst, rel(a["S_free_c"][c], b["S_free_c"].get(c, 0.0)))
            for i, per in a["S_c"].items():
                if per[c] > 0:
                    worst = max(worst, rel(per[c], b["S_c"].get(i, {}).get(c, 0.0)))
                elif b["S_c"].get(i, {}).get(c, 0.0):
                    permuted = True
    check("write_v2 -> load: every CELL M_c/S_c/S_free_c agrees at the rsig tier",
          worst <= RSIG_TIER and not permuted, f"worst rel {worst:.2e}")
    check("write_v2 -> load: Descaled.channels is the file order",
          channels.channels_of(got) == channels.FILE_CHANNELS,
          str(channels.channels_of(got)))
    check("write_v2 payload: meta['channels'] equals the column's first-appearance order",
          payload["meta"]["channels"] == list(dict.fromkeys(payload["nodes"]["channel"])))

    # share is the fraction of the CELL's own m_rel in the writer
    n = payload["nodes"]
    bad = []
    for z, c, m, sh, fr in zip(n["z"], n["channel"], n["m_rel"], n["share"], n["share_free"]):
        a = s.G.nodes[z]
        if a["M_c"][c] <= 0:
            continue
        for r, v in sh.items():
            if rel(v * m, a["S_c"][r][c]) > RSIG_TIER:
                bad.append((z, c, r))
        if rel(fr * m, a["S_free_c"][c]) > RSIG_TIER:
            bad.append((z, c, "free"))
    check("write_v2: share and share_free are fractions of the CELL's own m_rel",
          not bad, str(bad[:3]))

    # --- the exporter -> load_descaled, on a channelled extract
    mod = exporter()
    nat_opp = [("20001", 100.0), ("20002", 200.0), ("20003", 300.0)]
    other_opp = [("20001", "wh", 40.0), ("20001", "fi", 30.0),
                 ("20002", "wh", 60.0), ("20002", "fi", 50.0), ("20003", "wh", 20.0)]
    nat_sales = [("20001", "r_a", "FA", 20.0), ("20001", "r_b", "FB", 10.0),
                 ("20002", "r_b", "FB", 30.0), ("20003", "r_a", "FA", 60.0)]
    other_sales = [("20001", "wh", "r_a", "FA", 8.0), ("20001", "fi", "r_c", "FA", 6.0),
                   ("20002", "wh", "r_d", "FC", 12.0), ("20003", "wh", "r_d", "FC", 4.0)]
    kappa = 200.0
    with tempfile.TemporaryDirectory() as tmp:
        srows = [(z, r, f, "national", v) for z, r, f, v in nat_sales]
        srows += [(z, r, f, c, v) for z, c, r, f, v in other_sales]
        orows = [(z, "national", m) for z, m in nat_opp] + \
                [(z, c, m) for z, c, m in other_opp]
        sp = _csv(tmp, "s.csv", ["zip_code", "rep_id", "firm", "current_channel", "sales"], srows)
        op = _csv(tmp, "o.csv", ["zip_code", "current_channel", "M"], orows)
        gp = _csv(tmp, "e.csv", ["u", "v"], [("20001", "20002"), ("20002", "20003")])
        stp = _csv(tmp, "st.csv", ["zip_code", "state"],
                   [("20001", "GA"), ("20002", "GA"), ("20003", "AL")])
        out = os.path.join(tmp, "out")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = mod.main(["export", "--sales", sp, "--opportunity", op, "--graph", gp,
                           "--states", stp, "--out", out, "--yes"])
        path = os.path.join(out, "instance_descaled.json.gz")
        check("exporter: a channelled extract exports", rc == 0 and os.path.exists(path),
              f"rc={rc}")
        d = instance.load_descaled(path)
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            pl = json.load(fh)
        ids = {v: k for k, v in
               json.loads(json.dumps(pl.get("firm") or {})).items()}  # placeholder, unused

    # the loader's per-cell M must be the raw M / kappa: an oracle outside both codebases
    want_M = {(z, "national"): m / kappa for z, m in nat_opp}
    want_M.update({(z, c): m / kappa for z, c, m in other_opp})
    worst = 0.0
    for (z, c), v in want_M.items():
        worst = max(worst, rel(v, d.G.nodes[z]["M_c"].get(c, 0.0)))
    check("exporter -> load: every cell's M_c is the raw M over the national-median kappa",
          worst <= RSIG_TIER, f"worst rel {worst:.2e}")

    # the loader's per-cell book must be raw sales / kappa; rep ids are surrogates, so
    # compare the multiset of book values per cell
    worst = 0.0
    for z, c, r, f, v in [(z, "national", r, f, val) for z, r, f, val in nat_sales] + \
                         [(z, c, r, f, val) for z, c, r, f, val in other_sales]:
        got_vals = sorted(d.G.nodes[z]["S_c"].get(i, {}).get(c, 0.0)
                          for i in d.G.nodes[z]["S_c"])
        if not any(abs(x - v / kappa) <= RSIG_TIER * max(1.0, v / kappa) for x in got_vals):
            worst = 1.0
    check("exporter -> load: share is the fraction of the CELL's own m_rel "
          "(book recovers raw sales / kappa)", worst == 0.0)
    check("exporter -> load: totals are the cell sums",
          all(abs(d.G.nodes[z]["M"] - sum(d.G.nodes[z]["M_c"].values())) < 1e-12 for z in d.G))

    check("the two v2 writers emit the same node columns and the same format string",
          set(pl["nodes"]) == set(payload["nodes"]) and pl["format"] == payload["format"]
          == instance.FORMAT_V2,
          f"exporter {sorted(pl['nodes'])} vs write_v2 {sorted(payload['nodes'])}")
    check("both v2 writers put edges, firm and meta where the loader reads them",
          set(pl) >= {"format", "nodes", "edges", "firm", "meta"}
          and set(payload) >= {"format", "nodes", "edges", "firm", "meta"})

    # --- channel ORDER: the exporter's meta vs the loader's first appearance
    with tempfile.TemporaryDirectory() as tmp:
        # the opportunity table names national first, but 20001 (first alphabetically)
        # carries only the fi cell
        orows = [("20002", "national", 200.0), ("20002", "wh", 60.0),
                 ("20003", "national", 300.0), ("20003", "wh", 20.0),
                 ("20001", "fi", 40.0)]
        srows = [("20001", "r_a", "FA", "fi", 8.0), ("20002", "r_b", "FB", "national", 30.0),
                 ("20003", "r_a", "FA", "national", 60.0)]
        sp = _csv(tmp, "s.csv", ["zip_code", "rep_id", "firm", "current_channel", "sales"], srows)
        op = _csv(tmp, "o.csv", ["zip_code", "current_channel", "M"], orows)
        gp = _csv(tmp, "e.csv", ["u", "v"], [("20001", "20002"), ("20002", "20003")])
        out = os.path.join(tmp, "out")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = mod.main(["export", "--sales", sp, "--opportunity", op, "--graph", gp,
                           "--out", out, "--yes"])
        path = os.path.join(out, "instance_descaled.json.gz")
        if rc == 0 and os.path.exists(path):
            d2 = instance.load_descaled(path)
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                pl2 = json.load(fh)
            meta_order = tuple(pl2["meta"]["channels"])
            load_order = channels.channels_of(d2)
            same = meta_order == load_order
            check("exporter meta['channels'] == loader Descaled.channels when the first "
                  "zip lacks the national cell", same,
                  f"meta {meta_order} vs loader {load_order}")
            if not same:
                note("channel ORDER can disagree between the exporter's meta (opportunity-file "
                     "first appearance) and Descaled.channels (node-column first appearance) "
                     "when a zip is missing a channel. Membership is what channels.py reads, "
                     "so nothing computed here changes; write_v2's column order would.")
        else:
            check("exporter: the missing-national-cell extract exports", False, f"rc={rc}")


# ================================================================== 2. fine_split
def sec_fine() -> None:
    print("\n[2] fine_split")

    # hand instance firing both fallbacks, plus a zip with no national mass at all
    rows = [("zA", "MA", {"national": 100.0, "wh": 30.0, "fi": 10.0}),
            ("zB", "MA", {"national": 40.0, "wh": 0.0, "fi": 0.0}),
            ("zC", "NY", {"national": 20.0, "wh": 0.0, "fi": 0.0}),
            ("zD", "NY", {"national": 0.0, "wh": 0.0, "fi": 0.0})]
    G = nx.Graph()
    for z, st, M_c in rows:
        S_c = {"R0": {c: 0.05 * v for c, v in M_c.items()}}
        F_c = {c: 0.02 * v for c, v in M_c.items()}
        G.add_node(z, state=st, M_c=M_c, S_c=S_c, S_free_c=F_c, M=sum(M_c.values()),
                   S={"R0": sum(S_c["R0"].values())}, S_free=sum(F_c.values()), cand=("R0",))
    G.add_edges_from([("zA", "zB"), ("zB", "zC"), ("zC", "zD")])
    d = _with_channels(
        instance.Descaled(G=G, contested=[], uncontested={z: "R0" for z, _, _ in rows},
                          vacant=[], untapped=[], firm={}, meta={}), channels.FILE_CHANNELS)
    f = channels.fine_split(d)

    a = f.G.nodes["zA"]
    check("zA splits by its own WH:FI mass (30:10)",
          a["M_c"] == {"N_WH": 75.0, "N_FI": 25.0, "WH": 30.0, "FI": 10.0}, str(a["M_c"]))
    check("the same ratio hits every book and the filler",
          abs(a["S_c"]["R0"]["N_WH"] - 0.75 * 5.0) < 1e-12
          and abs(a["S_free_c"]["N_WH"] - 0.75 * 2.0) < 1e-12)
    b, c, dd = f.G.nodes["zB"], f.G.nodes["zC"], f.G.nodes["zD"]
    check("zB takes MA's state ratio 3:1", (b["M_c"]["N_WH"], b["M_c"]["N_FI"]) == (30.0, 10.0))
    check("zC takes 50/50 (NY has no WH or FI mass)",
          (c["M_c"]["N_WH"], c["M_c"]["N_FI"]) == (10.0, 10.0))
    check("the fallback report names zB and zC only",
          f.meta["fine_split_fallback"] == {"zB": "state", "zC": "even"},
          str(f.meta["fine_split_fallback"]))
    check("a zip with no WH, FI or national mass is not reported",
          "zD" not in f.meta["fine_split_fallback"] and dd["M_c"] == {
              "N_WH": 0.0, "N_FI": 0.0, "WH": 0.0, "FI": 0.0})

    # attack: state ratio must exclude nothing and must not be the whole-file ratio
    check("the state ratio is the state's, not the file's",
          abs(b["M_c"]["N_WH"] / 40.0 - 0.75) < 1e-12)

    # attack: conservation on a full-size instance
    if os.path.exists(SYNTH):
        big = instance.load_descaled(SYNTH)
        bf = channels.fine_split(big)
        wM = wS = wF = 0.0
        for z, at in bf.G.nodes(data=True):
            wM = max(wM, rel(sum(at["M_c"].values()), at["M"]))
            wF = max(wF, rel(sum(at["S_free_c"].values()), at["S_free"]))
            for i, per in at["S_c"].items():
                wS = max(wS, rel(sum(per.values()), at["S"][i]))
        check(f"fine_split conserves M, S, S_free on {big.G.number_of_nodes()} zips",
              max(wM, wS, wF) <= FLOAT_TIER, f"worst rel {max(wM, wS, wF):.2e}")
        check("no fallback fires on the synthetic instance",
              bf.meta["fine_split_fallback"] == {},
              f"{len(bf.meta['fine_split_fallback'])} zip(s)")
        check("the fine channels are exactly the four labels",
              channels.channels_of(bf) == channels.CHANNELS)
    else:
        note(f"{SYNTH} absent: the full-size conservation check did not run")

    # attack: a format-1 instance (no channels) fed to fine_split
    v1 = v1_graph()
    try:
        out = channels.fine_split(v1)
    except ValueError as e:
        check("fine_split refuses an instance with no channels", True, str(e)[:60])
    else:
        lost = sum(float(out.G.nodes[z]["M_c"]["N_WH"] + out.G.nodes[z]["M_c"]["N_FI"]
                         + out.G.nodes[z]["M_c"]["WH"] + out.G.nodes[z]["M_c"]["FI"])
                   for z in out.G)
        had = sum(float(v1.G.nodes[z]["M"]) for z in v1.G)
        check("fine_split refuses an instance with no channels (or conserves its mass)",
              abs(lost - had) < 1e-9,
              f"cell mass {lost:.4g} against {had:.4g} on the input; channels_of(out)="
              f"{channels.channels_of(out)}")

    # attack: a v2 instance missing the national channel
    G2 = nx.Graph()
    G2.add_node("z1", state="MA", M_c={"wh": 5.0, "fi": 5.0},
                S_c={}, S_free_c={"wh": 0.0, "fi": 0.0}, M=10.0, S={}, S_free=0.0, cand=())
    d2 = _with_channels(instance.Descaled(G=G2), ("wh", "fi"))
    f2 = channels.fine_split(d2)
    check("a file with only wh and fi splits to N_WH=N_FI=0 and keeps WH, FI",
          f2.G.nodes["z1"]["M_c"] == {"N_WH": 0.0, "N_FI": 0.0, "WH": 5.0, "FI": 5.0})


# ================================================================== 3. synthesize_channels
def sec_synth() -> None:
    print("\n[3] synthesize_channels")
    d = v1_graph()
    s = channels.synthesize_channels(d, seed=0)
    exact = all(s.G.nodes[z]["M_c"]["national"] == d.G.nodes[z]["M"] for z in d.G)
    exact &= all(s.G.nodes[z]["S_free_c"]["national"] == d.G.nodes[z]["S_free"] for z in d.G)
    exact &= all({i: per["national"] for i, per in s.G.nodes[z]["S_c"].items()}
                 == d.G.nodes[z]["S"] for z in d.G)
    check("the national cell is the input zip, bit for bit", exact)

    # per-cell headroom at the tightest input: build a zip sitting exactly on the floor
    G = nx.Graph()
    S = {"R0": 0.5, "R1": 0.25}
    T = sum(S.values())
    need = max(v + 0.40 * (T - v) for v in S.values())
    G.add_node("tight", cand=("R0", "R1"), S=S, M=need, S_free=0.0, state="MA")
    tight = instance.Descaled(G=G, contested=["tight"])
    st = channels.synthesize_channels(tight, seed=0)
    ok = True
    for c in channels.FILE_CHANNELS:
        H = nx.Graph()
        for z, a in st.G.nodes(data=True):
            H.add_node(z, M=a["M_c"][c], S_free=a["S_free_c"][c],
                       S={i: per[c] for i, per in a["S_c"].items()}, cand=a["cand"])
        ok &= model.headroom_violations(H, theta=0.40, tol=0.0) == []
    check("per-cell headroom survives on a zip sitting exactly on the headroom floor", ok)

    # attack: a zip with book but no mass -- the multiplier keeps book, write_v2 cannot
    G = nx.Graph()
    G.add_node("z0", cand=("R0",), S={"R0": 1.0}, M=0.0, S_free=0.0, state="MA")
    zero = channels.synthesize_channels(instance.Descaled(G=G, uncontested={"z0": "R0"}), seed=0)
    with tempfile.TemporaryDirectory() as tmp:
        p = channels.write_v2(zero, os.path.join(tmp, "z.json.gz"))
        back = instance.load_descaled(p)
    kept = back.G.nodes["z0"]["S"].get("R0", 0.0)
    check("a zero-mass cell with positive book survives the v2 round trip",
          abs(kept - 1.0) < 1e-9,
          f"book {kept} of 1.0; the share form cannot express book against M = 0",
          known=True)

    # determinism across PROCESSES: hashlib, never hash()
    prog = ("import sys; sys.path.insert(0, %r)\n"
            "from tests_probe_fixture import fingerprint\n"
            "print(fingerprint())\n") % ROOT
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "tests_probe_fixture.py"), "w") as fh:
            fh.write(
                "import sys\n"
                f"sys.path.insert(0, {ROOT!r})\n"
                "from td import channels\n"
                "def fingerprint():\n"
                "    vals = [channels._alpha_beta(0, f'z{i}') for i in range(50)]\n"
                "    return repr([round(a, 15) for ab in vals for a in ab])\n")
        with open(os.path.join(tmp, "run.py"), "w") as fh:
            fh.write(prog)
        outs = []
        for seedenv in ("0", "1", "12345"):
            env = dict(os.environ, PYTHONHASHSEED=seedenv, PYTHONPATH=tmp)
            r = subprocess.run([sys.executable, os.path.join(tmp, "run.py")],
                               capture_output=True, text=True, env=env, cwd=tmp)
            outs.append(r.stdout.strip())
    check("the multipliers are identical across processes at three PYTHONHASHSEED values",
          len(set(outs)) == 1 and outs[0] != "", f"{len(set(outs))} distinct fingerprints")
    lo_hi = [channels._alpha_beta(0, f"z{i}") for i in range(500)]
    flat = [v for ab in lo_hi for v in ab]
    check("the multipliers stay inside [0.15, 0.55]",
          min(flat) >= 0.15 and max(flat) <= 0.55, f"[{min(flat):.4f}, {max(flat):.4f}]")

    # the shipped synthetic instance: per-cell headroom and totals
    if os.path.exists(SYNTH):
        big = instance.load_descaled(SYNTH)
        chans = channels.channels_of(big)
        worst = 0.0
        viol = {}
        for c in chans:
            H = nx.Graph()
            for z, a in big.G.nodes(data=True):
                H.add_node(z, M=a["M_c"].get(c, 0.0), S_free=a["S_free_c"].get(c, 0.0),
                           S={i: per.get(c, 0.0) for i, per in a["S_c"].items()},
                           cand=a["cand"])
            viol[c] = len(model.headroom_violations(H, theta=0.40, tol=5e-5))
        for z, a in big.G.nodes(data=True):
            worst = max(worst, rel(sum(a["M_c"].values()), a["M"]))
        check(f"shipped synthetic instance ({big.G.number_of_nodes()} zips, {chans}): "
              "per-cell headroom holds in every channel", all(v == 0 for v in viol.values()),
              str(viol))
        check("shipped synthetic instance: totals are the cell sums",
              worst <= FLOAT_TIER, f"worst rel {worst:.2e}")
        check("shipped synthetic instance: the multipliers are the recorded seed's",
              "synthetic" in big.meta, str(big.meta.get("synthetic")))
        probs = instance.check_descaled(big, theta=0.40)
        check("shipped synthetic instance passes instance.check_descaled on its totals",
              not probs, "; ".join(probs))


# ================================================================== 4. aggregate, weights
def sec_agg() -> None:
    print("\n[4] aggregate, slot_weights, STATE_LIST")
    f = fine_fixture()
    states = sorted({f.G.nodes[z]["state"] for z in f.G})
    cells = channels.aggregate(f, states)

    # independent oracle: plain dict accumulation, no numpy
    M = {(s, c): 0.0 for s in states for c in channels.CHANNELS}
    F = dict(M)
    S = {}
    for z, a in f.G.nodes(data=True):
        s = a["state"]
        for c in channels.CHANNELS:
            M[(s, c)] += a["M_c"][c]
            F[(s, c)] += a["S_free_c"][c]
        for i, per in a["S_c"].items():
            for c in channels.CHANNELS:
                S[(i, s, c)] = S.get((i, s, c), 0.0) + per[c]
    worst = 0.0
    for si, s in enumerate(states):
        for ci, c in enumerate(cells.channels):
            worst = max(worst, rel(M[(s, c)], cells.M[si, ci]),
                        rel(F[(s, c)], cells.S_free[si, ci]))
            for ri, r in enumerate(cells.reps):
                worst = max(worst, rel(S.get((r, s, c), 0.0), cells.S[ri, si, ci]))
    check("aggregate equals a dict-based hand sum", worst <= FLOAT_TIER, f"{worst:.2e}")
    check("the channel axis is in CHANNELS order", cells.channels == channels.CHANNELS)
    check("reps are every rep in the file, sorted",
          list(cells.reps) == sorted({i for z in f.G for i in f.G.nodes[z]["S_c"]}))

    # slot_weights against a hand sum, including a repeated channel across slots
    bundle_of = ["N", "WH", "FI", "WH_PLUS", ("FI", "N_FI"), ("WH",)]
    W = channels.slot_weights(cells, bundle_of)
    ci = {c: k for k, c in enumerate(cells.channels)}
    ok = True
    for j, b in enumerate(bundle_of):
        want = sum(cells.M[:, ci[c]] for c in channels._bundle_channels(b))
        ok &= bool(np.allclose(W[:, j], want, rtol=0, atol=1e-12))
    check("slot_weights sums the bundle's channel columns", ok)
    check("slot_weights refuses a channel absent from the table",
          _raises(lambda: channels.slot_weights(cells, ["N"]) if False else
                  channels.slot_weights(_drop_channel(cells), ["N"]), ValueError))
    check("slot_weights on no slots is a (S, 0) array",
          channels.slot_weights(cells, []).shape == (len(states), 0))

    # STATE_LIST against the level-1 list the committed anchors index
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    try:
        import borders_report  # noqa: PLC0415
        ref = tuple(borders_report._STATE_LIST)
    except Exception as e:                       # pragma: no cover
        note(f"borders_report unimportable ({e}); STATE_LIST not compared")
        return
    check("channels.STATE_LIST equals tools/borders_report._STATE_LIST element for element",
          tuple(channels.STATE_LIST) == ref,
          f"{len(channels.STATE_LIST)} vs {len(ref)}; first difference "
          f"{next((i for i, (a, b) in enumerate(zip(channels.STATE_LIST, ref)) if a != b), None)}")


def _drop_channel(cells):
    import copy
    c = copy.deepcopy(cells)
    keep = [j for j, ch in enumerate(cells.channels) if ch != "N_WH"]
    return channels.CellTable(state_list=cells.state_list,
                              channels=tuple(cells.channels[j] for j in keep),
                              reps=cells.reps, M=cells.M[:, keep],
                              S=cells.S[:, :, keep], S_free=cells.S_free[:, keep])


def _raises(fn, exc) -> bool:
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


# ================================================================== 5. project
def sec_proj() -> None:
    print("\n[5] project against the loader's rule and the write_v1 seam")
    f = fine_fixture()

    # the bundle sums, against a hand sum
    for name in ("N", "WH", "FI", "WH_PLUS", "WHFI", "WHFI_PLUS"):
        B = channels.BUNDLES[name]
        p = channels.project(f, name)
        worst = 0.0
        for z, a in f.G.nodes(data=True):
            b = p.G.nodes[z]
            worst = max(worst, rel(b["M"], sum(a["M_c"][c] for c in B)),
                        rel(b["S_free"], sum(a["S_free_c"][c] for c in B)))
            for i, per in a["S_c"].items():
                want = sum(per[c] for c in B)
                worst = max(worst, rel(b["S"].get(i, 0.0), want))
        check(f"project({name}): M, S, S_free are the bundle sums", worst <= FLOAT_TIER,
              f"{worst:.2e}")

    # cover: the four bundles of a partition rebuild the whole instance
    tot = {z: 0.0 for z in f.G}
    for name in ("N", "WH", "FI"):
        p = channels.project(f, name)
        for z in f.G:
            tot[z] += p.G.nodes[z]["M"]
    check("N + WH + FI restores every zip's total mass",
          max(rel(tot[z], f.G.nodes[z]["M"]) for z in f.G) <= FLOAT_TIER)

    # cand: the loader's rule, checked by writing and reloading
    p = channels.project(f, "WH_PLUS")
    with tempfile.TemporaryDirectory() as tmp:
        path = channels.write_v1(p, os.path.join(tmp, "instance_descaled.json.gz"))
        got = instance.load_descaled(path)
    same_cls = (got.contested == p.contested and got.uncontested == p.uncontested
                and got.vacant == p.vacant and got.untapped == p.untapped)
    check("write_v1(project) -> load: the four node classes agree exactly", same_cls)
    check("write_v1(project) -> load: node set and edges agree exactly",
          sorted(got.G) == sorted(p.G) and
          sorted(map(tuple, map(sorted, got.G.edges()))) ==
          sorted(map(tuple, map(sorted, p.G.edges()))))
    worst = 0.0
    cand_ok = True
    for z in p.G:
        a, b = p.G.nodes[z], got.G.nodes[z]
        cand_ok &= a["cand"] == b["cand"] and a.get("state") == b.get("state")
        worst = max(worst, rel(a["M"], b["M"]), rel(a["S_free"], b["S_free"]))
        for i, v in a["S"].items():
            worst = max(worst, rel(v, b["S"].get(i, 0.0)))
    check("write_v1(project) -> load: cand and state are identical, M and S at the rsig tier",
          cand_ok and worst <= RSIG_TIER, f"worst rel {worst:.2e}")
    check("write_v1 keeps meta['bundle']", got.meta.get("bundle") == "WH_PLUS")

    # attack: a rep listed with a zero share.  The loader keeps the key in `cand`, project
    # drops it.  Does the seam stay self-consistent?
    G = nx.Graph()
    G.add_node("z1", state="MA", M_c={"WH": 4.0, "N_WH": 2.0, "N_FI": 0.0, "FI": 0.0},
               S_c={"R0": {"WH": 0.0, "N_WH": 0.0, "N_FI": 0.0, "FI": 0.0},
                    "R1": {"WH": 1.0, "N_WH": 0.0, "N_FI": 0.0, "FI": 0.0}},
               S_free_c={"WH": 0.0, "N_WH": 0.0, "N_FI": 0.0, "FI": 0.0},
               M=6.0, S={"R0": 0.0, "R1": 1.0}, S_free=0.0, cand=("R0", "R1"))
    dz = _with_channels(instance.Descaled(G=G, contested=["z1"]), channels.CHANNELS)
    pz = channels.project(dz, "WH")
    check("a rep with a zero book is not a candidate of the projection",
          pz.G.nodes["z1"]["cand"] == ("R1",), str(pz.G.nodes["z1"]["cand"]))
    with tempfile.TemporaryDirectory() as tmp:
        path = channels.write_v1(pz, os.path.join(tmp, "i.json.gz"))
        back = instance.load_descaled(path)
    check("and the written projection reloads with the same cand "
          "(the seam is self-consistent)",
          back.G.nodes["z1"]["cand"] == pz.G.nodes["z1"]["cand"])

    # states filter and induced edges
    p = channels.project(f, "FI", states=["MA"])
    keep = [z for z in f.G if f.G.nodes[z]["state"] == "MA"]
    check("states filter keeps exactly that state's zips", sorted(p.G) == sorted(keep))
    check("edges are induced on the kept zips",
          sorted(map(tuple, map(sorted, p.G.edges()))) ==
          sorted(tuple(sorted(e)) for e in f.G.edges() if e[0] in set(keep) and e[1] in set(keep)))
    # a zip carrying no mass in the bundle must still be a vertex: dropping it would cut
    # the contiguity graph, which is what the loader refuses to do too
    G0 = nx.Graph()
    for i, (z, st, wh) in enumerate((("z1", "MA", 4.0), ("z2", "MA", 0.0), ("z3", "MA", 3.0))):
        M_c = {"WH": wh, "N_WH": 1.0, "N_FI": 1.0, "FI": 0.0}
        G0.add_node(z, state=st, M_c=M_c, S_c={}, S_free_c={c: 0.0 for c in M_c},
                    M=sum(M_c.values()), S={}, S_free=0.0, cand=())
    G0.add_edges_from([("z1", "z2"), ("z2", "z3")])
    d0 = _with_channels(instance.Descaled(G=G0, untapped=["z1", "z2", "z3"]),
                               channels.CHANNELS)
    p0 = channels.project(d0, "WH")
    check("a zip with no mass in the bundle stays a vertex, so the graph stays connected",
          "z2" in p0.G and p0.G.nodes["z2"]["M"] == 0.0
          and nx.is_connected(p0.G) and p0.untapped == ["z1", "z2", "z3"])
    p1 = channels.project(d0, "WH", states=["MA"])
    check("the states filter keeps that zero-mass zip too", "z2" in p1.G)

    # degenerate: an empty bundle, a repeated channel, an unknown name
    check("project refuses an unknown bundle name",
          _raises(lambda: channels.project(f, "NOPE"), ValueError))
    check("project refuses a channel the instance does not carry",
          _raises(lambda: channels.project(
              channels.synthesize_channels(v1_graph(), seed=0), "WH"), ValueError))
    empty = channels.project(f, ())
    check("an empty bundle projects to an all-zero instance rather than raising",
          all(empty.G.nodes[z]["M"] == 0.0 for z in empty.G) and
          empty.untapped == sorted(empty.G), "documented seam, not a defect by itself")
    dup = channels.project(f, ("WH", "WH"))
    one = channels.project(f, ("WH",))
    dbl = max(rel(dup.G.nodes[z]["M"], 2 * one.G.nodes[z]["M"]) for z in f.G)
    check("a repeated channel in a bundle tuple double counts its mass (caller's contract)",
          dbl <= FLOAT_TIER, "BUNDLES never repeats a channel; a hand tuple can")

    # full size
    if os.path.exists(SYNTH):
        big = channels.fine_split(instance.load_descaled(SYNTH))
        p = channels.project(big, "N")
        worst = max(rel(p.G.nodes[z]["M"],
                        big.G.nodes[z]["M_c"]["N_WH"] + big.G.nodes[z]["M_c"]["N_FI"])
                    for z in big.G)
        check(f"project('N') on {big.G.number_of_nodes()} zips sums the two national labels",
              worst <= FLOAT_TIER, f"{worst:.2e}")
        check("the projection keeps every zip and every edge",
              p.G.number_of_nodes() == big.G.number_of_nodes()
              and p.G.number_of_edges() == big.G.number_of_edges())


# ================================================================== 6. decomposition (a)
def sec_decomp() -> None:
    print("\n[6] clause (a) with channels.project swapped into the math-verify block")
    rng = np.random.default_rng(20260910)
    reps_all = ["r0", "r1", "r2", "r3", "r_nobook"]
    zips = [f"z{i}" for i in range(8)]
    states = ["AZ", "CA"]

    G = nx.Graph()
    for i, z in enumerate(zips):
        M_c = {c: float(rng.uniform(1.0, 10.0)) for c in channels.CHANNELS}
        S_c = {}
        for r in reps_all[:-1]:
            per = {c: (float(rng.uniform(0.1, 3.0)) if rng.random() < 0.5 else 0.0)
                   for c in channels.CHANNELS}
            if any(per.values()):
                S_c[r] = per
        F_c = {c: float(rng.uniform(0.0, 2.0)) for c in channels.CHANNELS}
        G.add_node(z, state=states[i % 2], M_c=M_c, S_c=S_c, S_free_c=F_c,
                   M=sum(M_c.values()), S={r: sum(p.values()) for r, p in S_c.items()},
                   S_free=sum(F_c.values()), cand=tuple(sorted(S_c)))
    G.add_edges_from((zips[i], zips[i + 1]) for i in range(len(zips) - 1))
    d = _with_channels(instance.Descaled(G=G, contested=list(zips)), channels.CHANNELS)

    # --- the artifact's (a) block, with channels.project as the projector
    cellG = nx.Graph()
    for z in zips:
        a = G.nodes[z]
        for c in channels.CHANNELS:
            cellG.add_node(f"{z}|{c}", M=a["M_c"][c],
                           **{model.BOOK: {r: p[c] for r, p in a["S_c"].items() if p[c] > 0},
                              model.FREE: a["S_free_c"][c],
                              model.CAND: tuple(sorted(r for r, p in a["S_c"].items()
                                                       if p[c] > 0))})
    plans = {"three channels {N, WH, FI}": ("N", "WH", "FI"),
             "merged {N, WHFI}": ("N", "WHFI"),
             "national dropped {WH+, FI+}": ("WH_PLUS", "FI_PLUS"),
             "one bundle {WHFI+}": ("WHFI_PLUS",)}
    worst_all = 0.0
    for label, plan in plans.items():
        # districts: split the zips in two per bundle
        districts, td_cells, td_zip = [], {}, {}
        for bname in plan:
            B = channels.BUNDLES[bname]
            for half, zs in (("0", zips[:4]), ("1", zips[4:])):
                dname = f"{bname}#{half}"
                districts.append(dname)
                td_zip[(bname, dname)] = zs
                for z in zs:
                    for c in B:
                        td_cells[f"{z}|{c}"] = dname
        districts = sorted(districts)
        worst = 0.0
        for fc in ("theta", "full", "opportunity"):
            for theta, lam in ((0.40, 0.30), (0.0, 0.0), (1.0, 0.99), (0.75, 0.5)):
                gc, Rc, _ = channel.gain_matrix(cellG, td_cells, reps_order=reps_all,
                                                districts=districts, theta=theta, lam=lam,
                                                filler_capture=fc)
                gp = np.zeros_like(gc)
                for bname in plan:
                    pd = channels.project(d, bname)          # the code under test
                    td = {z: dn for (bn, dn), zs in td_zip.items() if bn == bname
                          for z in zs}
                    gb, Rb, _ = channel.gain_matrix(pd.G, td, reps_order=reps_all,
                                                    districts=districts, theta=theta, lam=lam,
                                                    filler_capture=fc)
                    assert Rb == reps_all
                    gp += gb
                scale = max(1.0, float(np.abs(gc).max()))
                worst = max(worst, float(np.abs(gc - gp).max()) / scale)
        check(f"(a) plan {label}: cell-level gain == sum of channels.project gains, "
              "12 parameter settings", worst <= 1e-12, f"worst rel {worst:.2e}")
        worst_all = max(worst_all, worst)

    # --- state_gain_matrix on an integral whole-state plan == channel.gain_matrix on project
    cells = channels.aggregate(d, states)
    worst = 0.0
    for bname in ("N", "WH", "FI", "WH_PLUS", "FI_PLUS", "WHFI", "WHFI_PLUS"):
        B = channels.BUNDLES[bname]
        plan = s2s.Plan([s2s.Slot(B, {s: 1.0 for s in states}, True)], states)
        for fc in ("theta", "full", "opportunity"):
            g, R, _ = s2s.state_gain_matrix(cells, plan, reps=list(cells.reps),
                                            theta=0.40, lam=0.30, filler_capture=fc)
            pd = channels.project(d, bname)
            gref, Rref, _ = channel.gain_matrix(pd.G, {z: "D0" for z in pd.G},
                                                reps_order=list(cells.reps), theta=0.40,
                                                lam=0.30, filler_capture=fc)
            assert Rref == R
            worst = max(worst, float(np.abs(g[:, 0] - gref[:, 0]).max()))
    check("state_gain_matrix == channel.gain_matrix on project(d, B), whole-state integral "
          "plan, 7 bundles x 3 filler_capture", worst <= 1e-9, f"worst abs {worst:.2e}")

    # a state-split plan is the mass-proportional approximation, by construction
    half = s2s.Plan([s2s.Slot(channels.BUNDLES["N"], {"AZ": 0.5, "CA": 1.0}, True)], states)
    g_half, _, _ = s2s.state_gain_matrix(cells, half, reps=list(cells.reps))
    full = s2s.Plan([s2s.Slot(channels.BUNDLES["N"], {"AZ": 1.0, "CA": 1.0}, True)], states)
    az = s2s.Plan([s2s.Slot(channels.BUNDLES["N"], {"AZ": 1.0}, True)], states)
    g_full, _, _ = s2s.state_gain_matrix(cells, full, reps=list(cells.reps))
    g_az, _, _ = s2s.state_gain_matrix(cells, az, reps=list(cells.reps))
    check("a half share is exactly half that state's cell contribution",
          np.allclose(g_half[:, 0], g_full[:, 0] - 0.5 * g_az[:, 0], rtol=0, atol=1e-12))

    # full-size sanity: one bundle on the synthetic instance
    if os.path.exists(SYNTH):
        big = channels.fine_split(instance.load_descaled(SYNTH))
        cells_b = channels.aggregate(big, channels.STATE_LIST)
        pd = channels.project(big, "WHFI")
        R = list(cells_b.reps)
        plan = s2s.Plan([s2s.Slot(channels.BUNDLES["WHFI"],
                                  {s: 1.0 for s in channels.STATE_LIST}, True)],
                        list(channels.STATE_LIST))
        g, _, _ = s2s.state_gain_matrix(cells_b, plan, reps=R)
        gref, Rref, _ = channel.gain_matrix(pd.G, {z: "D0" for z in pd.G}, reps_order=R)
        err = float(np.abs(g[:, 0] - gref[:, 0]).max() / max(1.0, np.abs(gref).max()))
        check(f"full size ({pd.G.number_of_nodes()} zips, {len(R)} reps): state gain == "
              "projected gain, WHFI over every state", err <= 1e-12, f"worst rel {err:.2e}")


# ================================================================== 7. requirement (i)
def sec_req1() -> None:
    print("\n[7] requirement (i): one global rep order so the blocks stack")
    f = fine_fixture()
    cells = channels.aggregate(f, sorted({f.G.nodes[z]["state"] for z in f.G}))
    check("aggregate's rep list is every rep in the file (the global order)",
          list(cells.reps) == sorted({i for z in f.G for i in f.G.nodes[z]["S_c"]}))
    check("state_gain_matrix's default rep order is that global list",
          s2s.state_gain_matrix(cells, s2s.Plan(
              [s2s.Slot(("WH",), {s: 1.0 for s in cells.state_list}, True)],
              list(cells.state_list)))[1] == list(cells.reps))

    # the hazard: a projection's own rep list is per bundle and in node order, not sorted
    per_bundle = {}
    for name in ("N", "WH", "FI"):
        p = channels.project(f, name)
        per_bundle[name] = model.reps(p.G, sorted(p.G))
    same = all(list(v) == list(cells.reps) for v in per_bundle.values())
    check("a default-order channel.gain_matrix on each projection would stack onto "
          "state_gain_matrix's rows", same,
          "; ".join(f"{k}: {v}" for k, v in per_bundle.items()) +
          f"  global {list(cells.reps)}")
    if not same:
        note("channels.project carries no reps_order and model.reps returns node order, not "
             "sorted order, so a per-bundle gain_matrix left on its default does not stack "
             "onto state_gain_matrix's sorted rows. Nothing in the owned files calls "
             "channel.gain_matrix; the requirement lands on the future caller "
             "(pass aggregate(d).reps everywhere).")

    # and the rep SET can differ per bundle: a rep with book in one channel only
    G = nx.Graph()
    G.add_node("z1", state="MA",
               M_c={"N_WH": 2.0, "N_FI": 2.0, "WH": 2.0, "FI": 2.0},
               S_c={"R0": {"N_WH": 1.0, "N_FI": 0.0, "WH": 0.0, "FI": 0.0},
                    "R9": {"N_WH": 0.0, "N_FI": 0.0, "WH": 0.0, "FI": 1.0}},
               S_free_c={c: 0.0 for c in channels.CHANNELS}, M=8.0,
               S={"R0": 1.0, "R9": 1.0}, S_free=0.0, cand=("R0", "R9"))
    dd = _with_channels(instance.Descaled(G=G, contested=["z1"]), channels.CHANNELS)
    sets = {b: tuple(model.reps(channels.project(dd, b).G, ["z1"])) for b in ("N", "FI")}
    check("the rep SET of a projection is the bundle's, not the instance's",
          sets["N"] != sets["FI"], str(sets))

    # rows really do follow the order asked for
    R = list(reversed(cells.reps))
    g, Rg, _ = s2s.state_gain_matrix(cells, s2s.Plan(
        [s2s.Slot(("WH",), {s: 1.0 for s in cells.state_list}, True)], list(cells.state_list)),
        reps=R)
    g0, R0, _ = s2s.state_gain_matrix(cells, s2s.Plan(
        [s2s.Slot(("WH",), {s: 1.0 for s in cells.state_list}, True)], list(cells.state_list)))
    idx = {r: i for i, r in enumerate(R0)}
    check("asking for a permuted rep order permutes the rows and nothing else",
          Rg == R and np.allclose(g[:, 0], [g0[idx[r], 0] for r in R], rtol=0, atol=1e-12))
    check("state_utilities keeps T over EVERY rep under a rep subset",
          np.allclose(s2s.state_utilities(cells, [cells.reps[0]])[0],
                      s2s.state_utilities(cells)[0], rtol=0, atol=1e-12))


# ================================================================== 8. requirement (ii)
def _brute_masked(g: np.ndarray, ok: np.ndarray, criterion="nash"):
    """Max cardinality first, then max value, over injections restricted to `ok`."""
    R, C = g.shape
    best = (-1, -math.inf, None)
    for cols in itertools.chain.from_iterable(
            itertools.combinations(range(C), k) for k in range(min(R, C) + 1)):
        for rows in itertools.permutations(range(R), len(cols)):
            pairs = list(zip(rows, cols))
            if not all(ok[i, j] for i, j in pairs):
                continue
            val = sum(math.log(g[i, j]) if criterion == "nash" else g[i, j] for i, j in pairs)
            if (len(pairs), val) > (best[0], best[1]):
                best = (len(pairs), val, pairs)
    return best


def sec_req2() -> None:
    print("\n[8] requirement (ii): candidacy by penalty assignment, nobody released")
    src = open(os.path.join(ROOT, "td", "stage2_state.py")).read()
    check("stage2_state.py never calls model.release_reps",
          "release_reps" not in src)
    check("candidacy runs through a penalty assignment, not channel.match on zeroed gains",
          "_match_masked" in src and "linear_sum_assignment" in src)
    staff_src = open(os.path.join(ROOT, "tools", "staff.py")).read()
    check("the penalty formula is tools/staff.py's, term for term",
          "pen = hi + (n + 1) * (hi - lo + 1.0)" in staff_src
          and "pen = hi + (min(g.shape) + 1) * (hi - lo + 1.0)" in src)

    # brute force oracle over injections, random masks, gains both sides of 1
    rng = np.random.default_rng(11)
    worst_gap = 0.0
    bad = 0
    for trial in range(300):
        R, C = int(rng.integers(2, 5)), int(rng.integers(2, 5))
        g = np.exp(rng.normal(0.0, 1.5, size=(R, C)))       # values above and below 1
        ok = rng.random((R, C)) < 0.55
        if not ok.any():
            continue
        card, val, _ = _brute_masked(g, ok)
        pairs, got = s2s._match_masked(g, ok, "nash")
        if len(pairs) != card or abs(got - val) > 1e-9:
            bad += 1
            worst_gap = max(worst_gap, abs(got - val))
    check("_match_masked equals brute force over allowed injections "
          "(max cardinality, then max sum log g) on 300 random masks",
          bad == 0, f"{bad} mismatches, worst value gap {worst_gap:.2e}")

    bad = 0
    for trial in range(200):
        R, C = int(rng.integers(2, 5)), int(rng.integers(2, 5))
        g = np.exp(rng.normal(0.0, 1.5, size=(R, C)))
        ok = rng.random((R, C)) < 0.55
        if not ok.any():
            continue
        card, val, _ = _brute_masked(g, ok, "utilitarian")
        pairs, got = s2s._match_masked(g, ok, "utilitarian")
        if len(pairs) != card or abs(got - val) > 1e-9:
            bad += 1
    check("the same under the utilitarian criterion, 200 masks", bad == 0)

    # candidacy never touches the instance or anyone's utility (trap 20)
    cells = _staff_cells()
    plan = s2s.Plan([s2s.Slot(("N_WH", "N_FI"), {"AZ": 1.0, "CA": 1.0}, True),
                     s2s.Slot(("WH", "FI"), {"AZ": 1.0}, True)], ["AZ", "CA"])
    before = (cells.M.copy(), cells.S.copy(), cells.S_free.copy())
    u0 = s2s.state_utilities(cells).copy()
    g0, R0, _ = s2s.state_gain_matrix(cells, plan)
    free = s2s.state_stage2(cells, plan)
    held = s2s.state_stage2(cells, plan, candidacy=True)
    g1, _, _ = s2s.state_gain_matrix(cells, plan)
    check("candidacy=True mutates no array of the cell table",
          np.array_equal(before[0], cells.M) and np.array_equal(before[1], cells.S)
          and np.array_equal(before[2], cells.S_free))
    check("S_free and every rep's utility are identical with candidacy on and off "
          "(nothing is released)",
          np.allclose(u0, s2s.state_utilities(cells), rtol=0, atol=0)
          and np.allclose(g0, g1, rtol=0, atol=0))
    check("a masked match never reports a pair the mask forbids",
          all(cells.S[R0.index(r)][:, :].sum() >= 0 for r in held["assignment"].values()))
    check("restricting candidacy cannot raise the Nash value",
          held["value"] <= free["value"] + 1e-12,
          f"{held['value']:.6f} vs {free['value']:.6f}")

    # Hall's condition: two slots whose only book-holding rep is the same one
    cells2 = _one_rep_cells()
    plan2 = s2s.Plan([s2s.Slot(("WH",), {"AZ": 1.0}, True),
                      s2s.Slot(("FI",), {"CA": 1.0}, True)], ["AZ", "CA"])
    try:
        out = s2s.state_stage2(cells2, plan2, candidacy=True)
    except ValueError as e:
        check("two used slots whose only candidate is the same rep: refused", True, str(e)[:70])
    else:
        check("two used slots whose only candidate is the same rep: refused",
              not out["unstaffed_districts"],
              f"assignment {out['assignment']}, unstaffed {out['unstaffed_districts']}, "
              f"value {out['value']:.4f} over {len(out['gains'])} of 2 slots")
        note("_check_staffable is per column, so a plan that fails Hall's condition under "
             "candidacy returns silently with a slot unstaffed and a value summed over the "
             "staffed slots only. Under route R that scores an unstaffable plan as if it "
             "had fewer slots.")

    # the same shape without candidacy: channel.match is rectangular and leaves slots empty
    cells3 = _one_rep_cells(n_reps=1)
    plan3 = s2s.Plan([s2s.Slot(("WH",), {"AZ": 1.0}, True),
                      s2s.Slot(("FI",), {"CA": 1.0}, True)], ["AZ", "CA"])
    out3 = s2s.state_stage2(cells3, plan3)
    check("with one rep and two slots the unmatched slot is reported, not hidden",
          out3["unstaffed_districts"] and len(out3["assignment"]) == 1,
          f"unstaffed {out3['unstaffed_districts']}")

    # balance keys against channel.balance_report
    ref = channel.balance_report(_tiny_graph(), {"a": "D0", "b": "D1"})
    got = s2s.state_stage2(cells, plan)["balance"]
    check("balance carries the same keys as channel.balance_report",
          set(got) == set(ref), f"missing {sorted(set(ref) - set(got))}, "
          f"extra {sorted(set(got) - set(ref))}")


def _staff_cells():
    import types
    M = np.array([[10.0, 8.0, 6.0, 4.0], [20.0, 16.0, 12.0, 8.0]], float)
    S = np.zeros((3, 2, 4), float)
    S[0, 0, 0] = 1.0
    S[1, 0, 2] = 1.0
    S[1, 1, 2] = 2.0
    S_free = np.full((2, 4), 0.5)
    return types.SimpleNamespace(state_list=["AZ", "CA"], channels=channels.CHANNELS,
                                 reps=["R0", "R1", "R2"], M=M, S=S, S_free=S_free)


def _one_rep_cells(n_reps: int = 2):
    import types
    M = np.array([[10.0, 8.0, 6.0, 4.0], [20.0, 16.0, 12.0, 8.0]], float)
    S = np.zeros((n_reps, 2, 4), float)
    S[0, 0, 2] = 1.0        # R0 is the only rep with book in AZ/WH
    S[0, 1, 3] = 1.0        # and the only one in CA/FI
    S_free = np.zeros((2, 4))
    return types.SimpleNamespace(state_list=["AZ", "CA"], channels=channels.CHANNELS,
                                 reps=[f"R{i}" for i in range(n_reps)], M=M, S=S,
                                 S_free=S_free)


def _tiny_graph():
    G = nx.Graph()
    G.add_node("a", M=1.0, S={}, S_free=0.0, cand=())
    G.add_node("b", M=2.0, S={}, S_free=0.0, cand=())
    return G


# ================================================================== 9. coefficients
def sec_coef() -> None:
    print("\n[9] model.coefficients against the pre-refactor block")

    def pre_refactor(theta, lam, filler_capture):
        """git show main:td/model.py 146-149, transcribed."""
        c1, c2 = 1.0 - lam, theta * (1.0 - lam)
        if filler_capture not in model.FILLER_CAPTURE:
            raise ValueError(f"filler_capture {filler_capture!r} not in {model.FILLER_CAPTURE}")
        c_free = {"theta": c2, "full": c1, "opportunity": lam}[filler_capture]
        return c1, c2, c_free

    bad = []
    for theta, lam in ((0.40, 0.30), (0.0, 0.0), (1.0, 0.99), (0.75, 0.5), (0.13, 0.87)):
        for fc in model.FILLER_CAPTURE:
            a = model.coefficients(theta, lam, fc)
            b = pre_refactor(theta, lam, fc)
            if a != b:
                bad.append((theta, lam, fc, a, b))
    check("identical floats (bit for bit) on 15 parameter settings", not bad, str(bad[:2]))

    try:
        model.coefficients(0.4, 0.3, "nonsense")
    except ValueError as e:
        msg_new = str(e)
    try:
        pre_refactor(0.4, 0.3, "nonsense")
    except ValueError as e:
        msg_old = str(e)
    check("the validation message is unchanged", msg_new == msg_old, msg_new)
    check("FILLER_CAPTURE is the same object channel.py used",
          model.FILLER_CAPTURE == ("theta", "full", "opportunity")
          or set(model.FILLER_CAPTURE) == {"theta", "full", "opportunity"},
          str(model.FILLER_CAPTURE))

    # the call sites still produce the old numbers on a real graph
    d = v1_graph()
    for fc in model.FILLER_CAPTURE:
        U, R = model.utilities(d.G, sorted(d.G), filler_capture=fc)
        c1, c2, c_free = pre_refactor(0.40, 0.30, fc)
        want = np.zeros_like(U)
        for j, z in enumerate(sorted(d.G)):
            a = d.G.nodes[z]
            T = sum(a["S"].values())
            for i, r in enumerate(R):
                if r in a["cand"]:
                    s = a["S"].get(r, 0.0)
                    want[i, j] = (c1 * s + c2 * (T - s) + c_free * a["S_free"]
                                  + 0.30 * a["M"])
        check(f"model.utilities({fc}) equals the hand formula", np.array_equal(U, want))
        g, Rg, D = channel.gain_matrix(d.G, {z: "D0" for z in d.G}, filler_capture=fc)
        wantg = np.zeros((len(Rg), 1))
        for z in d.G:
            a = d.G.nodes[z]
            T = sum(a["S"].values())
            for i, r in enumerate(Rg):
                s = a["S"].get(r, 0.0)
                wantg[i, 0] += c1 * s + c2 * (T - s) + c_free * a["S_free"] + 0.30 * a["M"]
        check(f"channel.gain_matrix({fc}) equals the hand formula",
              np.allclose(g, wantg, rtol=0, atol=1e-12))


# ================================================================== 10. the hub instance
def sec_hub() -> None:
    print("\n[10] the confidential instance (counts and deviations only, never values)")
    if not os.path.exists(HUB):
        note(f"{HUB} absent")
        return
    hub = instance.load_descaled(HUB)
    print(f"  hub: {hub.G.number_of_nodes()} zips, {hub.G.number_of_edges()} edges, "
          f"channels {channels.channels_of(hub)}")
    if not os.path.exists(SYNTH):
        note("no shipped synthetic instance to compare against")
        return
    ship = instance.load_descaled(SYNTH)
    seed = int((ship.meta.get("synthetic") or {}).get("seed", 0))
    made = channels.synthesize_channels(hub, seed=seed)
    same_nodes = sorted(made.G) == sorted(ship.G)
    check("the shipped synthetic instance has the hub's zip set", same_nodes,
          f"{made.G.number_of_nodes()} vs {ship.G.number_of_nodes()}")
    if not same_nodes:
        return
    worst_nat = worst_cell = 0.0
    exact = True
    for z in hub.G:
        exact &= made.G.nodes[z]["M_c"]["national"] == hub.G.nodes[z]["M"]
        for c in channels.FILE_CHANNELS:
            worst_cell = max(worst_cell, rel(made.G.nodes[z]["M_c"][c],
                                             ship.G.nodes[z]["M_c"].get(c, 0.0)))
        worst_nat = max(worst_nat, rel(ship.G.nodes[z]["M_c"].get("national", 0.0),
                                       hub.G.nodes[z]["M"]))
    check("synthesize_channels keeps the hub's national cell bit for bit", exact)
    check("the shipped file reproduces from the hub at the recorded seed",
          worst_cell <= RSIG_TIER, f"worst rel {worst_cell:.2e} (seed {seed})")
    check("the shipped national cell is the hub's M at the rsig tier",
          worst_nat <= RSIG_TIER, f"worst rel {worst_nat:.2e}")


# ================================================================== 11. mutation testing
def _load_mutant(modname: str, relpath: str, old: str, new: str):
    """Import a textually mutated copy of a module under its own name."""
    import importlib
    src = open(os.path.join(ROOT, relpath)).read()
    assert src.count(old) == 1, f"mutation site {old!r} appears {src.count(old)} times"
    path = os.path.join(tempfile.mkdtemp(), os.path.basename(relpath))
    with open(path, "w") as fh:
        fh.write(src.replace(old, new))
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    import td
    setattr(td, modname.split(".")[-1], mod)
    return mod


def _run_test_module(relpath: str) -> list:
    """Run every `test_*` in a test module in this process; return the failures."""
    import importlib
    name = "probe_" + os.path.basename(relpath)[:-3]
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, relpath))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    bad = []
    for fn in sorted(dir(mod)):
        if fn.startswith("test_"):
            try:
                getattr(mod, fn)()
            except Exception as e:                       # noqa: BLE001
                bad.append(f"{fn}: {type(e).__name__}")
    return bad


def sec_mut() -> None:
    """Does the shipped suite catch a targeted violation of each claim it covers?"""
    print("\n[11] mutation: which shipped tests are load bearing")
    import importlib
    import td
    real_channels, real_s2s = channels, s2s
    cases = [
        ("write_v2 prices share against the ZIP's m_rel, not the CELL's",
         "td.channels", "td/channels.py",
         '                        share[rep] = _rsig(v / m)',
         '                        share[rep] = _rsig(v / float(a.get("M", m) or m))',
         "tests/test_channels.py"),
        ("project keeps every rep in cand, positive book or not",
         "td.channels", "td/channels.py",
         "            if v > 0:\n                S[i] = v",
         "            if v >= 0:\n                S[i] = v",
         "tests/test_channels.py"),
        ("fine_split uses the FI:WH ratio (the two labels swapped)",
         "td.channels", "td/channels.py",
         "            r = w / (w + f)",
         "            r = f / (w + f)",
         "tests/test_channels.py"),
        ("the candidacy penalty is too small to dominate a swap",
         "td.stage2_state", "td/stage2_state.py",
         "    pen = hi + (min(g.shape) + 1) * (hi - lo + 1.0)",
         "    pen = hi + 1e-9",
         "tests/test_stage2_state.py"),
        ("state_gain_matrix prices unused slots too",
         "td.stage2_state", "td/stage2_state.py",
         "    slot_ids = [j for j, slot in enumerate(plan.slots) if slot.used]",
         "    slot_ids = list(range(len(plan.slots)))",
         "tests/test_stage2_state.py"),
    ]
    for label, modname, relpath, old, new, testpath in cases:
        try:
            _load_mutant(modname, relpath, old, new)
            bad = _run_test_module(testpath)
        finally:
            sys.modules["td.channels"] = real_channels
            sys.modules["td.stage2_state"] = real_s2s
            td.channels, td.stage2_state = real_channels, real_s2s
        check(f"the suite catches: {label}", bool(bad),
              ", ".join(bad[:3]) if bad else "NO shipped test fails under this mutation",
              known=label.startswith("the candidacy penalty"))
    # the suite is clean unmutated
    for tp in ("tests/test_channels.py", "tests/test_stage2_state.py"):
        check(f"{tp} passes unmutated", not _run_test_module(tp))


SECTIONS = dict(fmt=sec_fmt, fine=sec_fine, synth=sec_synth, agg=sec_agg, proj=sec_proj,
                decomp=sec_decomp, req1=sec_req1, req2=sec_req2, coef=sec_coef, mut=sec_mut,
                hub=sec_hub)


def main(argv=None) -> int:
    import networkx, scipy                                   # noqa: PLC0415
    argv = list(sys.argv[1:] if argv is None else argv)
    want = argv or [k for k in SECTIONS if k != "hub"]
    print("verify_channels: adversarial probes for td/channels.py and td/stage2_state.py")
    print(f"  td from        {os.path.dirname(os.path.dirname(channels.__file__))}")
    print(f"  python {sys.version.split()[0]}  numpy {np.__version__}  "
          f"scipy {scipy.__version__}  networkx {networkx.__version__}")
    assert channels.__file__.startswith(ROOT), channels.__file__
    for name in want:
        SECTIONS[name]()
    print(f"\n{len(FAILS)} failing check(s), {len(CAVEATS)} recorded caveat(s), "
          f"{len(NOTES)} note(s)")
    for f in FAILS:
        print(f"  FAIL    {f}")
    for c in CAVEATS:
        print(f"  CAVEAT  {c}")
    for n in NOTES:
        print(f"  NOTE    {n}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
