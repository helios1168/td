"""
test_run_draw_locks.py -- tools/run_draw.py's --lock-zips: pin named zips into named
districts before the solve, exactly like an anchor district's own zips (tools/run_draw.py
docstring, "Override translation" in the app rebuild plan).

A small synthetic descaled instance (15 zips, two states) plus a fake gazetteer cache drive
`run_draw.main` end to end; no network, no real instance file.  One locked zip is left out of
the gazetteer cache on purpose, so it takes the same coordinate-less `pinned` path a fixed
district's own zips take.
"""
from __future__ import annotations

import gzip
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

from td import geo, ziptable                            # noqa: E402
from td.instance import FORMAT                           # noqa: E402
import run_draw                                          # noqa: E402

# a zero-padded zip first, so the locks file can exercise --lock-zips' zip normalisation
TX_ZIPS = ["01234"] + [f"1000{i}" for i in range(1, 8)]   # 8 zips, state TX
NY_ZIPS = [f"2000{i}" for i in range(7)]                  # 7 zips, state NY
ALL_ZIPS = TX_ZIPS + NY_ZIPS

EAST_ZIPS = TX_ZIPS[:3]              # locked into "EAST"
NEWDIST_ZIPS = NY_ZIPS[:2]           # locked into "NEWDIST", a brand-new name
COORDLESS = NEWDIST_ZIPS[1]          # left out of the gazetteer cache on purpose

REPS = ["rep0", "rep1", "rep2", "rep3"]


def _locks_dict() -> dict[str, str]:
    locks = {z: "EAST" for z in EAST_ZIPS}
    locks.update({z: "NEWDIST" for z in NEWDIST_ZIPS})
    return locks


def _write_locks(path: str) -> None:
    locks = dict(_locks_dict())
    locks["1234"] = locks.pop("01234")     # unpadded key: run_draw must normalise it back
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(locks, fh)


def _write_instance(path: str) -> None:
    """Every zip carries positive opportunity and book for two of four reps, cycled, so every
    rep in REPS is a candidate somewhere and stage 2 can staff all three districts."""
    state = {z: ("TX" if z in TX_ZIPS else "NY") for z in ALL_ZIPS}
    share = {}
    for i, z in enumerate(ALL_ZIPS):
        r1, r2 = REPS[i % 4], REPS[(i + 1) % 4]
        share[z] = {r1: 0.3, r2: 0.2}
    obj = dict(
        format=FORMAT,
        nodes=dict(
            z=ALL_ZIPS,
            m_rel=[10.0 for _ in ALL_ZIPS],
            share=[share[z] for z in ALL_ZIPS],
            state=[state[z] for z in ALL_ZIPS],
        ),
        edges=dict(u=[], v=[]),
    )
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _write_geo_cache(dest: str) -> None:
    """A fake gazetteer cache (`tests/test_geo.py`'s pattern): every zip but `COORDLESS`."""
    os.makedirs(dest, exist_ok=True)
    lines = ["GEOID\tALAND\tAWATER\tALAND_SQMI\tAWATER_SQMI\tINTPTLAT\tINTPTLONG  \n"]
    for i, z in enumerate(ALL_ZIPS):
        if z == COORDLESS:
            continue
        lines.append(f"{z}\t0\t0\t0.0\t0.0\t{32.0 + i * 0.7:.4f}\t{-100.0 + i * 0.6:.4f}\n")
    with open(os.path.join(dest, geo.GAZ_TXT), "w", encoding="latin-1") as fh:
        fh.writelines(lines)


def test_lock_zips_pin_named_zips_into_named_districts():
    with tempfile.TemporaryDirectory() as tmp:
        inst = os.path.join(tmp, "instance_descaled.json.gz")
        cache = os.path.join(tmp, "geo")
        locks_path = os.path.join(tmp, "locks.json")
        out_dir = os.path.join(tmp, "out")
        _write_instance(inst)
        _write_geo_cache(cache)
        _write_locks(locks_path)

        rc = run_draw.main([inst, "--k", "3", "--seeds", "0", "--workers", "1",
                            "--lock-zips", locks_path, "--geo-cache", cache,
                            "--out", out_dir])
        assert rc == 0, rc

        rows = ziptable.read(os.path.join(out_dir, "k03", "draw.csv"))
        by_zip = {r["zip"]: r["district"] for r in rows}
        for z in EAST_ZIPS:
            assert by_zip[z] == "EAST", (z, by_zip[z])
        for z in NEWDIST_ZIPS:
            assert by_zip[z] == "NEWDIST", (z, by_zip[z])   # COORDLESS included: the pinned path

        districts = {r["district"] for r in rows}
        assert len(districts) == 3, districts

        with open(os.path.join(out_dir, "k03", "metrics.json"), encoding="utf-8") as fh:
            metrics = json.load(fh)
        assert metrics["locks"] == _locks_dict()             # "1234" normalised to "01234"
        lock_rows = [r for r in metrics["hand_drawn"] if r["mode"] == "lock"]
        assert {r["district"] for r in lock_rows} == {"EAST", "NEWDIST"}


def test_lock_into_fix_district_is_an_error():
    with tempfile.TemporaryDirectory() as tmp:
        locks_path = os.path.join(tmp, "locks.json")
        with open(locks_path, "w", encoding="utf-8") as fh:
            json.dump({TX_ZIPS[0]: "SOUTH"}, fh)
        try:
            run_draw.main(["nonexistent_instance.json.gz", "--fix", "SOUTH=TX",
                          "--lock-zips", locks_path, "--out", os.path.join(tmp, "out")])
        except ValueError as e:
            assert "SOUTH" in str(e)
        else:
            raise AssertionError("expected ValueError for a lock into a --fix district")
