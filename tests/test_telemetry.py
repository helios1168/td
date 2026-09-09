"""test_telemetry.py -- td/telemetry.py: nesting, tick accumulation, the write round trip,
`maybe_profile`, and the module-level hooks being no-ops with no `Timings` active.

No instance, no solver: everything here is `Timings` and a temp directory.
"""
from __future__ import annotations

import json
import os
import tempfile

from td import telemetry


def test_no_active_timings_is_a_no_op():
    assert telemetry.current() is None
    telemetry.tick("lp.assign", 1.0)                  # must not raise with nothing active
    with telemetry.phase("load") as ph:
        ph.note(x=1)                                  # goes nowhere; also must not raise
    assert telemetry.current() is None


def test_a_timings_is_current_until_written():
    T = telemetry.Timings("clip")
    assert telemetry.current() is T
    with tempfile.TemporaryDirectory() as tmp:
        T.write(tmp)
    assert telemetry.current() is None


def test_close_deactivates_without_writing():
    T = telemetry.Timings("draw_job")
    assert telemetry.current() is T
    T.close()
    assert telemetry.current() is None


def test_nesting_depth():
    T = telemetry.Timings("clip")
    try:
        with T.phase("outer"):
            with T.phase("inner"):
                pass
    finally:
        T.close()
    depths = {p["name"]: p["depth"] for p in T.phases}
    assert depths == {"outer": 0, "inner": 1}


def test_tick_accumulates_across_calls_and_bulk_merges():
    T = telemetry.Timings("clip")
    try:
        T.tick("lp.assign", 0.1)
        T.tick("lp.assign", 0.2)
        assert T.ticks["lp.assign"] == {"n": 2, "wall": 0.1 + 0.2}

        T.tick("lp.assign", 1.5, n=3)                 # a worker's summed totals, one call
        assert T.ticks["lp.assign"] == {"n": 5, "wall": 0.1 + 0.2 + 1.5}
    finally:
        T.close()


def test_module_level_tick_and_phase_reach_the_active_timings():
    T = telemetry.Timings("clip")
    try:
        with telemetry.phase("solve") as ph:
            telemetry.tick("lp.assign", 0.05)
            ph.note(status=0)
        assert T.ticks["lp.assign"]["n"] == 1
        assert T.phases[-1]["name"] == "solve" and T.phases[-1]["note"] == {"status": 0}
    finally:
        T.close()


def test_write_round_trips_the_documented_shape():
    T = telemetry.Timings("clip")
    with T.phase("load"):
        pass
    with T.phase("solve") as ph:
        ph.note(nodes=3, dual_bound=1.5, gap=0.0, status=0)
    T.tick("lp.assign", 0.02)

    with tempfile.TemporaryDirectory() as tmp:
        path = T.write(tmp)
        assert path == os.path.join(tmp, "timings.json")
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)

    assert payload["driver"] == "clip"
    assert isinstance(payload["argv"], list)
    assert "started" in payload and "finished" in payload
    for key in ("wall", "cpu", "rss_peak_mb"):
        assert isinstance(payload[key], float) and payload[key] >= 0.0

    names = [p["name"] for p in payload["phases"]]
    assert names == ["load", "solve"]
    solve = payload["phases"][1]
    assert solve["depth"] == 0
    assert solve["note"] == {"nodes": 3, "dual_bound": 1.5, "gap": 0.0, "status": 0}
    for f in ("start", "wall", "cpu"):
        assert isinstance(solve[f], float)

    assert payload["ticks"] == {"lp.assign": {"n": 1, "wall": 0.02}}
    assert telemetry.current() is None                # write() deactivated it


def test_write_gives_a_second_driver_its_own_sibling_file():
    with tempfile.TemporaryDirectory() as tmp:
        clip = telemetry.Timings("clip")
        with clip.phase("solve") as ph:
            ph.note(status=0)
        clip_path = clip.write(tmp)
        assert clip_path == os.path.join(tmp, "timings.json")

        geom = telemetry.Timings("geom")
        geom_path = geom.write(tmp)
        assert geom_path == os.path.join(tmp, "timings.geom.json")

        with open(clip_path, encoding="utf-8") as fh:
            assert json.load(fh)["driver"] == "clip"           # untouched by the geom write
        with open(geom_path, encoding="utf-8") as fh:
            assert json.load(fh)["driver"] == "geom"


def test_write_twice_with_the_same_driver_overwrites():
    with tempfile.TemporaryDirectory() as tmp:
        first = telemetry.Timings("clip")
        first.tick("lp.assign", 0.1)
        first_path = first.write(tmp)

        second = telemetry.Timings("clip")
        second.tick("lp.assign", 0.2)
        second_path = second.write(tmp)

        assert second_path == first_path == os.path.join(tmp, "timings.json")
        with open(second_path, encoding="utf-8") as fh:
            payload = json.load(fh)
        assert payload["ticks"] == {"lp.assign": {"n": 1, "wall": 0.2}}


def test_maybe_profile_writes_profile_prof_only_under_td_profile():
    def _main():
        T = telemetry.Timings("geom")
        with T.phase("load"):
            sum(range(1000))
        with tempfile.TemporaryDirectory() as tmp:
            T.write(tmp)
            return tmp, os.path.exists(os.path.join(tmp, "profile.prof"))

    old = os.environ.pop("TD_PROFILE", None)
    try:
        _tmp, has_prof = telemetry.maybe_profile(_main)()
        assert not has_prof

        os.environ["TD_PROFILE"] = "1"
        _tmp2, has_prof2 = telemetry.maybe_profile(_main)()
        assert has_prof2
    finally:
        if old is None:
            os.environ.pop("TD_PROFILE", None)
        else:
            os.environ["TD_PROFILE"] = old
