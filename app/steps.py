"""Argv builders for every driver kind, and the grid expansion that turns one set of k values
into six draw-then-clip-then-geom chains.

Every builder returns a plain `list[str]`, ready for `app.runner.launch` or `launch_chain`;
nothing here runs a process. `grid` is the one function that does I/O, and it does it only
through `app.store`: it creates the draw and clip run directories, writes their `step.json`
(carrying the scenario slug and this chain's member name), and, when the scenario carries pins,
writes `scenario.json` into the draw directory, since that file is `run_draw.py`'s own input
and has nowhere else to come from. That `scenario.json` is the fixed/anchored districts a user
pinned; it has nothing to do with the scenario slug in `step.json`, an unfortunate but
unavoidable collision in the one English word both ideas want.
"""
from __future__ import annotations

import json
import os
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


def clip_argv(python, repo, instance, run, *, draw: Path, k, delta, time_limit, theta, lam,
             filler_capture, geo_cache, rounds=5, eta=0.01, anchor_homes=True, engine=None,
             strategy=None, primal_seconds=None, threads=None) -> list[str]:
    argv = [str(python), str(Path(repo) / "tools" / "state_splits.py"), str(instance),
           "--draw", str(draw), "--k", str(k), "--delta", str(delta),
           "--time-limit", str(time_limit), "--theta", str(theta), "--lam", str(lam),
           "--filler-capture", str(filler_capture), "--rounds", str(rounds), "--eta", str(eta)]
    if anchor_homes:
        argv.append("--anchor-homes")
    if engine is not None:
        argv += ["--engine", str(engine)]
    if strategy is not None:
        argv += ["--strategy", str(strategy)]
    if primal_seconds is not None:
        argv += ["--primal-seconds", str(primal_seconds)]
    if threads is not None:
        argv += ["--threads", str(threads)]
    argv += ["--no-maps", "--geo-cache", str(geo_cache), "--out", str(run)]
    return argv


def geom_argv(python, repo, table, run, *, geo_cache) -> list[str]:
    return [str(python), str(Path(repo) / "tools" / "geom_export.py"),
           "--table", str(table), "--out", str(run), "--geo-cache", str(geo_cache)]


def staff_argv(python, repo, instance, run, *, table, keep=None, release=None, theta, lam,
              filler_capture, districts=None) -> list[str]:
    if (keep is None) == (release is None):
        raise ValueError("staff_argv needs exactly one of keep or release")
    argv = [str(python), str(Path(repo) / "tools" / "staff.py"), str(instance),
           "--table", str(table)]
    argv += ["--keep", _csv(keep)] if keep is not None else ["--release", _csv(release)]
    argv += ["--theta", str(theta), "--lam", str(lam), "--filler-capture", str(filler_capture)]
    if districts is not None:
        argv += ["--districts", _csv(districts)]
    argv += ["--out", str(run)]
    return argv


def staff_and_split_argv(python, repo, instance, run, *, table, keep=None, release=None,
                         theta, lam, filler_capture, districts=None,
                         multi: dict[str, int] | None = None,
                         exact=False, time_limit=60, geom: Path | None = None) -> list[str]:
    if (keep is None) == (release is None):
        raise ValueError("staff_and_split_argv needs exactly one of keep or release")
    argv = [str(python), str(Path(repo) / "tools" / "staff_and_split.py"), str(instance),
           "--table", str(table)]
    argv += ["--keep", _csv(keep)] if keep is not None else ["--release", _csv(release)]
    argv += ["--theta", str(theta), "--lam", str(lam), "--filler-capture", str(filler_capture)]
    if districts is not None:
        argv += ["--districts", _csv(districts)]
    if multi:
        argv += ["--multi", ",".join(f"{d}:{n}" for d, n in multi.items())]
        if exact:
            argv.append("--exact")
        argv += ["--time-limit", str(time_limit)]
        if geom is not None:
            argv += ["--geom", str(geom)]
    argv += ["--out", str(run)]
    return argv


def override_argv(python, repo, instance, run, *, table, edits: Path, mode,
                 parent: Path | None = None) -> list[str]:
    argv = [str(python), str(Path(repo) / "tools" / "override.py"), str(instance),
           "--table", str(table), "--edits", str(edits), "--mode", str(mode)]
    if parent is not None:
        argv += ["--parent", str(parent)]
    return argv + ["--out", str(run)]


def split_argv(python, repo, instance, run, *, table, district, reps: list[str], theta, lam,
              filler_capture, exact=False, time_limit=60, geom: Path | None = None) -> list[str]:
    argv = [str(python), str(Path(repo) / "tools" / "split_district.py"), str(instance),
           "--table", str(table), "--district", str(district), "--reps", _csv(reps),
           "--theta", str(theta), "--lam", str(lam), "--filler-capture", str(filler_capture)]
    if exact:
        argv.append("--exact")
    if geom is not None:
        argv += ["--geom", str(geom)]
    argv += ["--time-limit", str(time_limit), "--out", str(run)]
    return argv


def grid(root: Path, *, name: str = "", ks: list[int], delta, seeds, workers, theta, lam,
        filler_capture, time_limit, pins: dict | None, python, repo, instance,
        geo_cache, engine: str | None = None, strategy: str | None = None,
        threads: int | None = None) -> list[list[tuple[Path, list[str]]]]:
    """One draw-clip-geom chain per k, all sharing one scenario: `name` is the user's typed
    text, slugified (`store.slugify`) into the scenario slug that ties every chain's runs
    together for `store.scenarios` and the other tabs' pickers. Each chain's own member name is
    the slug plus its k and delta (`store.member_name`); the run directories are named from
    that member, and both the draw and clip steps record `scenario` and `member`, plus the raw
    `name` in their own `params["scenario_name"]`, so a legacy caller (`name=""`) still gets a
    working, if anonymous, scenario. A draw process at this delta and this scenario, its
    state-split clip, and the geometry export that turns the clip's winning table into the map
    the UI actually shows (invariant 3: the clip's table is the result, the draw is only how it
    got there). Six k values make six chains, each its own `run_draw.py` process.

    `threads`, left `None`, is split evenly across the chains this call launches at once:
    `max(2, cpu_count // len(ks))` per clip, so six concurrent chains do not each size their own
    portfolio for the whole machine. A caller passing `threads` explicitly gets that value on
    every clip instead."""
    root = Path(root)
    slug = store.slugify(name)
    dname = f"d{delta:g}"
    chain_threads = (threads if threads is not None
                    else max(2, (os.cpu_count() or 2) // max(1, len(ks))))
    chains: list[list[tuple[Path, list[str]]]] = []
    for k in ks:
        kk = f"k{k:02d}"
        member = store.member_name(slug, k, delta)

        draw_dir = store.new_run_dir(root, "draw", member)
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
                       instance=str(instance), pins=pins, scenario_name=name),
            argv=d_argv, scenario=slug, member=member,
            outputs={"table": f"{kk}/draw.csv", "metrics": f"{kk}/metrics.json",
                    "timings": "timings.json"})
        draw_table = draw_dir / draw_step["outputs"]["table"]

        clip_dir = store.new_run_dir(root, "clip", member)
        c_argv = clip_argv(python, repo, instance, clip_dir, draw=draw_table, k=k, delta=delta,
                          time_limit=time_limit, theta=theta, lam=lam,
                          filler_capture=filler_capture, geo_cache=geo_cache, engine=engine,
                          strategy=strategy, threads=chain_threads)
        clip_step = store.write_step(
            clip_dir, kind="clip", parent=draw_dir.name,
            params=dict(k=k, delta=delta, time_limit=time_limit, theta=theta, lam=lam,
                       filler_capture=filler_capture, rounds=5, eta=0.01,
                       anchor_homes=True, geo_cache=str(geo_cache), instance=str(instance),
                       scenario_name=name, engine=engine, strategy=strategy,
                       threads=chain_threads),
            argv=c_argv, scenario=slug, member=member,
            outputs={"table": f"{dname}/draw.csv", "metrics": f"{dname}/splits.json",
                    "geom": "geom.json", "timings": "timings.json"})
        clip_table = clip_dir / clip_step["outputs"]["table"]

        g_argv = geom_argv(python, repo, clip_table, clip_dir, geo_cache=geo_cache)

        chains.append([(draw_dir, d_argv), (clip_dir, c_argv), (clip_dir, g_argv)])
    return chains
