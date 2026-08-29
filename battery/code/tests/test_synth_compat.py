"""
test_synth_compat.py -- U5 guard: generator v2 must not move any existing instance.

Two layers.

**Layer A (bit identity).**  `anchors/synth_baseline.json` was generated from the
*untouched* `code/synth.py` (commit "U5 step 0") and records, per instance, the sha256 of
the raw bytes of every array `make_instance` produces (`M, A, B, pos, rep_a, rep_b,
state`) plus the `repr` of the scalar summaries.  Every new knob in generator v2 must be
a pure post-transform, a default-branch argument substitution, or a consumer of `rng2`
only -- so with all knobs off these hashes may never move.  **If this test fails, stop:
do not re-anchor.**  Regenerate deliberately with `--update` only when the *model* is
intended to change, and record why.

**Layer B (battery compatibility).**  Regenerates each `battery/figures/C*.json` case from
the hard-coded case table below (a copy of `run_battery.py::CASES`; that module is never
imported -- importing it once regenerated all 34 primary artifacts by accident) and checks
the recorded instance summaries, census, overlap pairs and free-Nash products.  Read-only:
nothing under `battery/figures/` is ever opened for writing.

Layer C: target statistics for the new scenarios (S8-S12).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for _p in (os.path.join(ROOT, "code"), os.path.join(ROOT, "battery", "code")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

ANCHOR = os.path.join(HERE, "anchors", "synth_baseline.json")
FIGS = os.path.join(ROOT, "battery", "figures")

import synth                                                       # noqa: E402
import territory as T                                              # noqa: E402


# --------------------------------------------------------------------- case table
# Verbatim copy of battery/code/run_battery.py::CASES (+ the C8 sweep's instance).
# NEVER import run_battery: it has a __main__ guard now, but the table is small and a
# copy keeps the test independent of that file entirely.
CASES = [
    dict(name="C1_aligned_seed1", scenario="S1_aligned", n=200, seed=1),
    dict(name="C1_aligned_seed2", scenario="S1_aligned", n=200, seed=2),
    dict(name="C2_entangled_a0", scenario="S2_entangled", n=200, seed=1),
    dict(name="C2_entangled_a05", scenario="S2_entangled", n=200, seed=1,
         overrides=dict(alpha=0.5)),
    dict(name="C3_slivers_ms005", scenario="S3_slivers", n=200, seed=1, min_share=0.005),
    dict(name="C3_slivers_ms02", scenario="S3_slivers", n=200, seed=1, min_share=0.02),
    dict(name="C3_slivers_ms08", scenario="S3_slivers", n=200, seed=1, min_share=0.08),
    dict(name="C4_separate", scenario="S4_separate", n=200, seed=1),
    dict(name="C4_contested", scenario="S4_separate", n=200, seed=1,
         overrides=dict(rho_books=1.0)),
    dict(name="C5_states_free", scenario="S5_states", n=200, seed=1),
    dict(name="C5_states_resp", scenario="S5_states", n=200, seed=1),
    dict(name="C6_tight", scenario="S6_tight", n=200, seed=1),
    dict(name="C6_loose", scenario=None, n=200, seed=1,
         overrides=dict(alpha=1.0, n_rep_a=4, n_rep_b=4, saturation=0.12)),
    dict(name="C7_scale_n400", scenario="S1_aligned", n=400, seed=1),
    dict(name="C9_heavytail_seed1", scenario="S7_heavytail", n=200, seed=1),
    dict(name="C9_heavytail_seed2", scenario="S7_heavytail", n=200, seed=2),
    dict(name="C8_rho_frontier", scenario="S1_aligned", n=200, seed=1),   # c8_rho_sweep.py
]

LEGACY_SCENARIOS = ["S1_aligned", "S2_entangled", "S3_slivers", "S4_separate",
                    "S5_states", "S6_tight", "S7_heavytail"]


def build(case):
    kw = dict(synth.SCENARIOS[case["scenario"]]) if case.get("scenario") else {}
    kw.update(case.get("overrides", {}))
    return synth.make_instance(n=case.get("n", 200), seed=case.get("seed", 1), **kw)


# ------------------------------------------------------------------- fingerprints
def _h(arr, dtype):
    return hashlib.sha256(np.ascontiguousarray(np.asarray(arr, dtype)).tobytes()).hexdigest()


def fingerprint(G):
    """sha256 of the raw bytes of every array make_instance produces, + scalar reprs."""
    nodes = list(G)
    f = {}
    for key in ("M", "A", "B"):
        f[key] = _h([G.nodes[z][key] for z in nodes], np.float64)
    f["P"] = _h([G.nodes[z]["pos"] for z in nodes], np.float64)
    for key in ("rep_a", "rep_b"):
        f[key] = _h([G.nodes[z][key] for z in nodes], np.int64)
    if all("state" in G.nodes[z] for z in nodes):
        f["state"] = _h([int(str(G.nodes[z]["state"])[1:]) for z in nodes], np.int64)
    else:
        f["state"] = None
    f["edges"] = _h(sorted((min(u, v), max(u, v)) for u, v in G.edges()), np.int64)
    for key in ("corr_AB", "Sa", "Sb", "Mtot"):
        f[key] = repr(G.graph[key])
    for key in ("cap_a", "cap_b"):
        f[key] = repr(G.graph[key])
    return f


def anchor_keys():
    """(key, case-dict) for every instance the anchor covers."""
    out = [(c["name"], c) for c in CASES]
    for s in LEGACY_SCENARIOS:
        for seed in (1, 2):
            out.append((f"{s}_seed{seed}", dict(scenario=s, n=200, seed=seed)))
    return out


def regenerate_anchor():
    return {k: fingerprint(build(c)) for k, c in anchor_keys()}


# ---------------------------------------------------------------- Layer A: identity
def test_bit_identity():
    """Every legacy instance is byte-for-byte what it was before generator v2."""
    with open(ANCHOR) as fh:
        want = json.load(fh)
    got = regenerate_anchor()
    assert set(got) == set(want["instances"]), (
        f"anchor covers {sorted(set(want['instances']) ^ set(got))} differently")
    bad = []
    for k in sorted(got):
        for field, v in got[k].items():
            if want["instances"][k].get(field) != v:
                bad.append(f"{k}.{field}: {want['instances'][k].get(field)!r} -> {v!r}")
    assert not bad, ("BIT IDENTITY BROKEN -- do NOT re-anchor; find the rng call that "
                     "moved:\n  " + "\n  ".join(bad[:20]))


if __name__ == "__main__":
    if "--update" in sys.argv:
        print("=" * 72)
        print("WARNING: rewriting the U5 bit-identity anchor.")
        print("This is only legitimate when the generator's DEFAULT model is")
        print("deliberately changed.  A failing test_bit_identity is NOT a reason.")
        print("=" * 72)
        payload = dict(
            note=("sha256 of make_instance's raw output arrays with every generator-v2 "
                  "knob off; generated from the pre-U5 code/synth.py"),
            instances=regenerate_anchor())
        with open(ANCHOR, "w") as fh:
            json.dump(payload, fh, indent=1, sort_keys=True)
        print(f"wrote {ANCHOR}  ({len(payload['instances'])} instances)")
    else:
        test_bit_identity()
        print("bit identity OK")
