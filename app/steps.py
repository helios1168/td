"""Argv builders for every driver kind, and the grid expansion that turns one set of k values
into six draw-then-clip-then-geom chains.

Every builder returns a plain `list[str]`, ready for `app.runner.launch` or `launch_chain`;
nothing here runs a process. `grid` is the one function that does I/O, and it does it only
through `app.store`: it creates the draw and clip run directories, writes their `step.json`,
and, when the scenario carries pins, writes `scenario.json` into the draw directory, since that
file is `run_draw.py`'s own input and has nowhere else to come from.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import store


def _csv(names) -> str:
    """A `--keep`/`--release`/`--reps` value: a string is passed through, anything else is
    joined with commas."""
    return names if isinstance(names, str) else ",".join(names)


def draw_argv(python, repo, instance, run, *, k, seeds, workers, theta, lam, filler_capture,
             geo_cache, scenario: Path | None) -> list[str]:
    argv = [str(python), str(Path(repo) / "tools" / "run_draw.py"), str(instance),
           "--k", str(k), "--seeds", str(seeds), "--workers", str(workers),
           "--theta", str(theta), "--lam", str(lam), "--filler-capture", str(filler_capture),
           "--geo-cache", str(geo_cache), "--out", str(run)]
    if scenario is not None:
        argv += ["--scenario", str(scenario)]
    return argv


def clip_argv(python, repo, instance, run, *, draw: Path, k, delta, time_limit, geo_cache,
             rounds=5, eta=0.01, anchor_homes=True) -> list[str]:
    argv = [str(python), str(Path(repo) / "tools" / "state_splits.py"), str(instance),
           "--draw", str(draw), "--k", str(k), "--delta", str(delta),
           "--time-limit", str(time_limit), "--rounds", str(rounds), "--eta", str(eta)]
    if anchor_homes:
        argv.append("--anchor-homes")
    argv += ["--no-maps", "--geo-cache", str(geo_cache), "--out", str(run)]
    return argv


def geom_argv(python, repo, table, run, *, geo_cache) -> list[str]:
    return [str(python), str(Path(repo) / "tools" / "geom_export.py"),
           "--table", str(table), "--out", str(run), "--geo-cache", str(geo_cache)]


def staff_argv(python, repo, instance, run, *, table, keep=None, release=None, theta, lam,
              filler_capture) -> list[str]:
    if (keep is None) == (release is None):
        raise ValueError("staff_argv needs exactly one of keep or release")
    argv = [str(python), str(Path(repo) / "tools" / "staff.py"), str(instance),
           "--table", str(table)]
    argv += ["--keep", _csv(keep)] if keep is not None else ["--release", _csv(release)]
    argv += ["--theta", str(theta), "--lam", str(lam), "--filler-capture", str(filler_capture),
            "--out", str(run)]
    return argv


def override_argv(python, repo, instance, run, *, table, edits: Path, mode,
                 parent: Path | None = None) -> list[str]:
    argv = [str(python), str(Path(repo) / "tools" / "override.py"), str(instance),
           "--table", str(table), "--edits", str(edits), "--mode", str(mode)]
    if parent is not None:
        argv += ["--parent", str(parent)]
    return argv + ["--out", str(run)]


def split_argv(python, repo, instance, run, *, table, district, reps: list[str], exact=False,
              time_limit=60) -> list[str]:
    argv = [str(python), str(Path(repo) / "tools" / "split_district.py"), str(instance),
           "--table", str(table), "--district", str(district), "--reps", _csv(reps)]
    if exact:
        argv.append("--exact")
    argv += ["--time-limit", str(time_limit), "--out", str(run)]
    return argv


def grid(root: Path, *, ks: list[int], delta, seeds, workers, theta, lam,
        filler_capture, time_limit, pins: dict | None, python, repo, instance,
        geo_cache) -> list[list[tuple[Path, list[str]]]]:
    """One draw-clip-geom chain per k: a draw process at this delta and this scenario, its
    state-split clip, and the geometry export that turns the clip's winning table into the map
    the UI actually shows (invariant 3: the clip's table is the result, the draw is only how it
    got there). Six k values make six chains, each its own `run_draw.py` process."""
    root = Path(root)
    dname = f"d{delta:g}"
    chains: list[list[tuple[Path, list[str]]]] = []
    for k in ks:
        kk = f"k{k:02d}"

        draw_dir = store.new_run_dir(root, "draw", k)
        scenario = None
        if pins:
            scenario = draw_dir / "scenario.json"
            scenario.write_text(json.dumps(pins, indent=2) + "\n", encoding="utf-8")
        d_argv = draw_argv(python, repo, instance, draw_dir, k=k, seeds=seeds, workers=workers,
                          theta=theta, lam=lam, filler_capture=filler_capture,
                          geo_cache=geo_cache, scenario=scenario)
        draw_step = store.write_step(
            draw_dir, kind="draw", parent=None,
            params=dict(k=k, seeds=str(seeds), workers=workers, theta=theta, lam=lam,
                       filler_capture=filler_capture, geo_cache=str(geo_cache),
                       instance=str(instance), pins=pins),
            argv=d_argv,
            outputs={"table": f"{kk}/draw.csv", "metrics": f"{kk}/metrics.json"})
        draw_table = draw_dir / draw_step["outputs"]["table"]

        clip_dir = store.new_run_dir(root, "clip", k)
        c_argv = clip_argv(python, repo, instance, clip_dir, draw=draw_table, k=k, delta=delta,
                          time_limit=time_limit, geo_cache=geo_cache)
        clip_step = store.write_step(
            clip_dir, kind="clip", parent=draw_dir.name,
            params=dict(k=k, delta=delta, time_limit=time_limit, rounds=5, eta=0.01,
                       anchor_homes=True, geo_cache=str(geo_cache), instance=str(instance)),
            argv=c_argv,
            outputs={"table": f"{dname}/draw.csv", "metrics": f"{dname}/splits.json",
                    "geom": "geom.json"})
        clip_table = clip_dir / clip_step["outputs"]["table"]

        g_argv = geom_argv(python, repo, clip_table, clip_dir, geo_cache=geo_cache)

        chains.append([(draw_dir, d_argv), (clip_dir, c_argv), (clip_dir, g_argv)])
    return chains
