"""test_rep_export.py -- `tools/rep_export.py` on a six-zip, three-rep toy: shares that sum to
one (or to zero), the `top`/`n` reading of a zip's own book, and the polygon promises
(`territories`, `footprints`, `contested`) built over `tools/geom_export.py`'s own machinery.

No network: `td.geo.zcta_points`'s cache-if-absent file is pre-seeded (`_seed_cache`, the same
route `tests/test_geo.py` uses), so the driver runs under `--no-basemap` with neither a
shapefile nor a live gazetteer download.

    D01 (top R1)  90001 CA  R1 6, R2 2, free 1     -- contested, n=2
                  90002 CA  R1 4, free 1           -- n=1
                  90003 CA  free 3, no rep         -- n=0, vacant
    D02 (top R2)  10001 NY  R2 5                   -- n=1
                  10002 NY  R3 0 (a candidate, no book), free 2   -- n=0
                  10003 NY  nothing at all         -- n=0, untapped

R3 is a candidate at 10002 (the instance's `share` dict carries the key) but never holds a
positive share anywhere, which is what exercises `footprints["R3"] == []` -- a rep can be a
candidate with no territory at all.
"""
from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import instance as descaled                                          # noqa: E402

REP_EXPORT = os.path.join(ROOT, "tools", "rep_export.py")

# zip -> (state, m_rel, {rep: S}, S_free)
TOY = {
    "90001": ("CA", 9.0, {"R1": 6.0, "R2": 2.0}, 1.0),
    "90002": ("CA", 5.0, {"R1": 4.0}, 1.0),
    "90003": ("CA", 3.0, {}, 3.0),
    "10001": ("NY", 5.0, {"R2": 5.0}, 0.0),
    "10002": ("NY", 2.0, {"R3": 0.0}, 2.0),
    "10003": ("NY", 1.0, {}, 0.0),
}
# 90001 loses R2, so no zip anywhere has two candidates with a positive share
TOY_NO_CONTEST = dict(TOY, **{"90001": ("CA", 9.0, {"R1": 8.0}, 1.0)})

EXPECTED_TOP = {"90001": "R1", "90002": "R1", "90003": "", "10001": "R2", "10002": "", "10003": ""}
EXPECTED_N = {"90001": 2, "90002": 1, "90003": 0, "10001": 1, "10002": 0, "10003": 0}

# real gazetteer internal points for these six zips, tab-delimited with the file's own
# trailing-space header quirk (see td/geo.py and tests/test_geo.py)
FAKE_GAZ = (
    "GEOID\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG  \n"
    "90001\t2000\t0\t0.772\t0.000\t33.974026\t-118.249510\n"
    "90002\t2000\t0\t0.772\t0.000\t33.949099\t-118.246737\n"
    "90003\t2000\t0\t0.772\t0.000\t33.964131\t-118.272783\n"
    "10001\t3000\t0\t1.158\t0.000\t40.750636\t-73.997177\n"
    "10002\t3000\t0\t1.158\t0.000\t40.715776\t-73.986211\n"
    "10003\t3000\t0\t1.158\t0.000\t40.731829\t-73.989181\n"
)


def _seed_cache(dest):
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "2020_Gaz_zcta_national.txt"), "w", encoding="latin-1") as fh:
        fh.write(FAKE_GAZ)


def _write_instance(path, toy) -> str:
    """The `td_instance_descaled/1` file: `S_i(z) = share_i(z) * m_rel(z)` round-trips exactly
    (the same construction `tests/test_staff.py::_write_instance` uses)."""
    zips = sorted(toy)
    obj = dict(format=descaled.FORMAT,
               nodes=dict(z=zips,
                          m_rel=[toy[z][1] for z in zips],
                          share=[{r: s / toy[z][1] for r, s in toy[z][2].items()} for z in zips],
                          state=[toy[z][0] for z in zips],
                          share_free=[toy[z][3] / toy[z][1] for z in zips]),
               edges=dict(u=zips[:-1], v=zips[1:]), firm={}, meta={})
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)
    return path


def _run(tmp, toy=TOY) -> dict:
    """A whole driver run in `tmp`; returns the loaded `reps.json`."""
    geo_cache = os.path.join(tmp, "geo")
    _seed_cache(geo_cache)
    inst = _write_instance(os.path.join(tmp, "instance_descaled.json.gz"), toy)
    out_dir = os.path.join(tmp, "out")
    proc = subprocess.run([sys.executable, REP_EXPORT, inst, "--out", out_dir,
                           "--geo-cache", geo_cache, "--no-basemap"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    with open(os.path.join(out_dir, "reps.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _keys(obj):
    """Every dict key anywhere in a JSON-shaped value, depth-first."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


# --------------------------------------------------------------------------------- the shares
def test_cli_writes_reps_json_for_the_instance_at_hand():
    with tempfile.TemporaryDirectory() as tmp:
        g = _run(tmp)
        assert os.path.exists(os.path.join(tmp, "out", "timings.json"))
    assert g["crs"] == "laea"
    assert g["instance"] == "instance_descaled.json.gz"
    assert g["reps"] == ["R2", "R3", "R1"]              # first-appearance order, model.reps
    assert sorted(g["zips"]) == sorted(TOY)


def test_shares_sum_to_one_or_the_zip_has_no_book_at_all():
    with tempfile.TemporaryDirectory() as tmp:
        g = _run(tmp)
    for z, info in g["zips"].items():
        total = sum(info["shares"].values()) + info["free"]
        assert total == 0.0 or abs(total - 1.0) < 1e-9, (z, info)


def test_top_is_the_argmax_of_the_zips_own_shares():
    with tempfile.TemporaryDirectory() as tmp:
        g = _run(tmp)
    assert {z: info["top"] for z, info in g["zips"].items()} == EXPECTED_TOP


def test_n_counts_the_candidates_with_a_positive_share():
    with tempfile.TemporaryDirectory() as tmp:
        g = _run(tmp)
    assert {z: info["n"] for z, info in g["zips"].items()} == EXPECTED_N


def test_weight_sums_to_one_over_every_zip():
    with tempfile.TemporaryDirectory() as tmp:
        g = _run(tmp)
    assert abs(sum(info["weight"] for info in g["zips"].values()) - 1.0) < 1e-9


def test_book_share_plus_free_share_sums_to_one():
    with tempfile.TemporaryDirectory() as tmp:
        g = _run(tmp)
    assert abs(sum(g["book_share"].values()) + g["free_share"] - 1.0) < 1e-9
    assert abs(g["book_share"]["R3"]) < 1e-12                    # R3 never holds a share


# --------------------------------------------------------------------------- the polygon half
def test_footprints_keys_equal_reps_even_a_rep_with_no_territory():
    with tempfile.TemporaryDirectory() as tmp:
        g = _run(tmp)
    assert set(g["footprints"]) == set(g["reps"]) == {"R1", "R2", "R3"}
    assert g["footprints"]["R3"]["rings"] == []                  # candidate, never a share
    assert g["footprints"]["R1"]["rings"] and g["footprints"]["R2"]["rings"]


def test_contested_is_non_empty_only_when_some_zip_has_two_reps():
    with tempfile.TemporaryDirectory() as tmp:
        g_yes = _run(tmp, toy=TOY)
    assert g_yes["contested"]["rings"]

    with tempfile.TemporaryDirectory() as tmp:
        g_no = _run(tmp, toy=TOY_NO_CONTEST)
    assert g_no["contested"]["rings"] == []


# ------------------------------------------------------------------------- confidentiality
def test_no_raw_mass_anywhere_in_the_file():
    with tempfile.TemporaryDirectory() as tmp:
        g = _run(tmp)
    assert not ({"M", "S", "opportunity"} & set(_keys(g)))
