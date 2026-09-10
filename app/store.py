"""The step.json ledger for one run directory: how the app tells `draw`, `clip`, `staff`,
`override`, `split` and `import` runs apart, finds their parents and children, and reads back
what a driver has written so far.

A run directory holds one `step.json` (kind, parent, params, argv, pid, started, outputs,
scenario, member) and whatever a driver writes under it; the outputs never carry an absolute
path, only one relative to the run directory, so a run directory can be moved or copied along
with its tree. `scenario` (a slug) and `member` (the slug plus its k and delta) tie a grid
launch's chains together; `scenarios()` groups runs by scenario for the app's pickers, and a
run made before this ledger existed carries neither and reads as legacy. This module never
runs a driver itself (`app.runner` does that) and never imports streamlit or pandas, so the
whole thing is testable from the solver venv.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from . import runner

STEP = "step.json"
FAILURE = "failure.json"

VIEW = "view.json"
STAMP = "%Y%m%d_%H%M%S"


def slugify(text: str) -> str:
    """A user-typed scenario name reduced to `[a-z0-9-]`: lowercased, every run of anything
    else (spaces, punctuation, underscores) turned into one hyphen, leading and trailing
    hyphens stripped. Underscores become hyphens so `_k(\\d+)_` and `_stamp` still parse a
    member name out of a directory name. Empty input, or input that is all punctuation, falls
    back to `grid-<YYYYmmdd>-<HHMM>`, so a scenario always has a name to key its runs on."""
    slug = re.sub(r"[^a-z0-9-]+", "-", text.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or f"grid-{datetime.now():%Y%m%d-%H%M}"


def member_name(slug: str, k: int, delta: float, channel: str | None = None) -> str:
    """The name of one scenario member: the slug, an optional channel token, the district count
    unpadded, and the delta as a bare percent (`custom_k8_d5`, `custom_k10_d7.5`,
    `v3-seq-warm_fi_k19_d20`). A member with no channel is named exactly as it always was."""
    dpct = round(delta * 100, 4)
    token = f"_{channel_token(channel)}" if channel else ""
    return f"{slug}{token}_k{int(k)}_d{dpct:g}"


def channel_token(channel: str) -> str:
    """A channel or bundle name as one lower-case `[a-z0-9]` token, so it can sit inside a
    member name and a run directory name: `_PLUS` and `+` spell `plus`, every other separator
    drops (`national` -> `national`, `WH_PLUS` -> `whplus`, `WHFI` -> `whfi`)."""
    text = channel.lower().replace("_plus", "plus").replace("+", "plus")
    return re.sub(r"[^a-z0-9]", "", text)


def new_run_dir(root: Path, kind: str, member: str | int) -> Path:
    """Create and return `<root>/<member>_<kind>_<YYYYmmdd_HHMMSS>`, made unique with a `-2`,
    `-3`, ... suffix when two runs of the same member and kind land in the same second.
    `member` is normally a scenario member name (`custom_k10_d5`, built by `member_name`); a
    caller with no scenario at all (a legacy child) may still pass a bare int `k`, in which
    case the member part of the name is `f"k{k}"`."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    member = f"k{int(member)}" if isinstance(member, int) else member
    base = f"{member}_{kind}_{datetime.now():{STAMP}}"
    name, n = base, 2
    while (root / name).exists():
        name = f"{base}-{n}"
        n += 1
    run = root / name
    run.mkdir()
    return run


def write_step(run: Path, *, kind: str, parent: str | None, params: dict, argv: list[str],
               outputs: dict, scenario: str | None = None, member: str | None = None) -> dict:
    """Write `step.json` for a run just created: no process has been launched yet, so `pid`
    and `started` are both `None` until `app.runner.launch`/`launch_chain` fills them in.
    `scenario` and `member` tie the run to a scenario ledger entry (`scenario_of`, `member_of`
    walk the lineage to find them); a run outside a scenario leaves both `None`."""
    step = dict(kind=kind, parent=parent, params=params, argv=argv, pid=None, started=None,
               outputs=outputs, scenario=scenario, member=member)
    _write(run, step)
    return step


def read_step(run: Path) -> dict:
    return json.loads((Path(run) / STEP).read_text(encoding="utf-8"))


def update_step(run: Path, **fields) -> dict:
    """Merge `fields` into the existing `step.json` and rewrite it."""
    step = read_step(run)
    step.update(fields)
    _write(run, step)
    return step


def _write(run: Path, step: dict) -> None:
    (Path(run) / STEP).write_text(json.dumps(step, indent=2) + "\n", encoding="utf-8")


def discover(root: Path) -> list[Path]:
    """Every run directory under `root` that carries a `step.json`, newest first by the
    timestamp the name ends in (`<kind>_<slug>_<YYYYmmdd_HHMMSS>[-n]`), then by name, so a
    `clip_*` and a `draw_*` made in the same second stay together rather than grouping by kind."""
    root = Path(root)
    if not root.is_dir():
        return []
    dirs = [p for p in root.iterdir() if p.is_dir() and (p / STEP).exists()]
    return sorted(dirs, key=lambda p: (_stamp(p.name), p.name), reverse=True)


def _stamp(name: str) -> str:
    """The `YYYYmmdd_HHMMSS` a run directory name ends in, uniqueness suffix dropped."""
    parts = name.split("_")
    return "_".join(parts[-2:]).split("-")[0] if len(parts) >= 3 else name


def k_of(run: Path, root: Path) -> int | None:
    """The district count a run was made for: its own `params.k`, else the nearest ancestor's,
    else the `k<kk>` in its name. `None` for a hand-imported table that says nothing."""
    for step_run in reversed(lineage(run, root)):
        k = read_step(step_run).get("params", {}).get("k")
        if k is not None:
            return int(k)
    match = re.search(r"_k(\d+)_", Path(run).name)
    return int(match.group(1)) if match else None


def scenario_of(run: Path, root: Path) -> str | None:
    """The scenario slug a run belongs to: its own `step.json["scenario"]`, else the nearest
    ancestor's. `None` for a run with no scenario anywhere in its lineage (a legacy run)."""
    for step_run in reversed(lineage(run, root)):
        scenario = read_step(step_run).get("scenario")
        if scenario is not None:
            return scenario
    return None


def member_of(run: Path, root: Path) -> str | None:
    """The scenario member name a run belongs to, the same way `scenario_of` walks the
    lineage for the scenario slug. `None` for a run with no member anywhere in its lineage."""
    for step_run in reversed(lineage(run, root)):
        member = read_step(step_run).get("member")
        if member is not None:
            return member
    return None


def staffing_run(run: Path, root: Path) -> Path | None:
    """Nearest run at or above `run` in its own lineage whose kind is `staff`: the source
    of the whole-map assignment/unstaffed_districts picture a split only ever narrows one
    district of, never replaces. None when the lineage carries no staff run."""
    for step_run in reversed(lineage(run, root)):
        if read_step(step_run).get("kind") == "staff":
            return step_run
    return None


def label(run: Path, root: Path) -> str:
    """What a picker shows for a run: `custom_k10_d5 · clip · 2026-09-08 14:42:39`. Read from
    the ledger rather than the directory name, so runs made under an older naming read the
    same way. A run with no member anywhere in its lineage (a legacy run) falls back to
    `k18 · clip · 2026-09-08 14:42:39`."""
    step = read_step(run)
    when = step.get("started") or _stamp(Path(run).name)
    try:
        when = datetime.strptime(when, STAMP).isoformat(sep=" ", timespec="seconds")
    except ValueError:
        when = when.replace("T", " ")
    member = member_of(run, root)
    if member is None:
        k = k_of(run, root)
        member = f"k{k}" if k is not None else "k?"
    return f"{member} · {step.get('kind', '?')} · {when}"


def _output_path(run: Path, key: str) -> Path | None:
    rel = read_step(run).get("outputs", {}).get(key)
    if not rel:
        return None
    path = (Path(run) / rel).resolve()
    return path if path.exists() else None


def table_path(run: Path) -> Path | None:
    return _output_path(run, "table")


def metrics_path(run: Path) -> Path | None:
    return _output_path(run, "metrics")


def geom_path(run: Path) -> Path | None:
    return _output_path(run, "geom")


def failure(run: Path) -> dict | None:
    path = Path(run) / FAILURE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def status(run: Path) -> str:
    """`queued`, `running`, `done` or `failed`. A table on disk wins outright, since a driver
    that already wrote its output is done regardless of what its pid is doing; short of that, a
    live pid means running, and a dead one (or a failure.json with no table) means failed. A
    chain member started by `app.runner.launch_chain` shares its predecessor's pid, so it reads
    running for as long as the chain is still working its way to that member's own step."""
    if table_path(run) is not None:
        return "done"
    step = read_step(run)
    pid = step.get("pid")
    if pid is not None and runner._alive(pid):
        return "running"
    if (Path(run) / FAILURE).exists() or pid is not None:
        return "failed"
    return "queued"


def lineage(run: Path, root: Path) -> list[Path]:
    """The chain of runs from the root ancestor to `run` itself, root first."""
    root = Path(root)
    chain = [Path(run)]
    parent = read_step(chain[-1]).get("parent")
    while parent:
        chain.append(root / parent)
        parent = read_step(chain[-1]).get("parent")
    return list(reversed(chain))


def children(run: Path, root: Path) -> list[Path]:
    """Every run directly parented on `run`, newest first."""
    name = Path(run).name
    return [d for d in discover(root) if read_step(d).get("parent") == name]


def scenarios(root: Path) -> list[tuple[str | None, list[Path]]]:
    """Every scenario under `root`, as `(slug, runs)` pairs: newest-first by the newest run
    each scenario holds, its own runs newest first too. Runs with no scenario (made before this
    ledger, or hand-imported) are grouped last under the slug `None`."""
    groups: dict[str | None, list[Path]] = {}
    order: list[str | None] = []
    for run in discover(root):
        slug = scenario_of(run, root)
        if slug not in groups:
            groups[slug] = []
            order.append(slug)
        groups[slug].append(run)
    order = [slug for slug in order if slug is not None] + ([None] if None in groups else [])
    return [(slug, groups[slug]) for slug in order]


def read_view(run: Path) -> dict:
    """The view.json beside run's step.json, or {} if this run has never been named."""
    path = Path(run) / VIEW
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

def _write_view(run: Path, view: dict) -> None:
    (Path(run) / VIEW).write_text(json.dumps(view, indent=2) + "\n", encoding="utf-8")

def write_view(run: Path, root: Path, *, name: str, default_for: str | None = None) -> dict:
    """Name `run` (or rename it) and, when default_for is given, flag it default for that
    member. At most one run holds default_for == <member> at a time: every other run of
    that member currently holding the flag is cleared first. Additive only, alongside
    step.json, never touching it. Single-user local Streamlit process: no lock."""
    run = Path(run)
    if default_for:
        for other in named_runs(root, default_for):
            if other == run:
                continue
            v = read_view(other)
            if v.get("default_for") == default_for:
                v["default_for"] = None
                _write_view(other, v)
    view = dict(read_view(run), name=name, default_for=default_for)
    _write_view(run, view)
    return view

def named_runs(root: Path, member: str) -> list[Path]:
    """Every run of `member` that carries a view.json, newest first."""
    return [r for r in discover(root)
            if member_of(r, root) == member and (r / VIEW).exists()]

def default_for(root: Path, member: str) -> Path | None:
    """The run currently flagged default for `member`, or None."""
    return next((r for r in named_runs(root, member)
                if read_view(r).get("default_for") == member), None)

def members(root: Path, scenario: str | None) -> list[tuple[str, list[Path]]]:
    """Every member the given scenario holds a run for, as (member, runs) pairs: newest
    first by each member's newest run, its own runs newest first too - scenarios()'s own
    shape, one level down. A run outside any member (legacy) is not grouped here."""
    groups: dict[str, list[Path]] = {}
    order: list[str] = []
    for run in discover(root):
        if scenario_of(run, root) != scenario:
            continue
        member = member_of(run, root)
        if member is None:
            continue
        if member not in groups:
            groups[member] = []
            order.append(member)
        groups[member].append(run)
    return [(m, groups[m]) for m in order]

_MEMBER_RE = re.compile(r"(?:_([a-z0-9]+))?_k(\d+)_d([\d.]+)$")

# what a channel token reads as in the pickers; a token this does not name shows uppercased
CHANNEL_LABELS = {"national": "national", "wh": "WH", "fi": "FI", "whplus": "WH⁺",
                  "fiplus": "FI⁺", "whfi": "WH+FI", "whfiplus": "WH+FI⁺"}

def member_label(member: str) -> str:
    """"k10 · d10", or "FI · k19 · d20" for a member carrying a channel token, for the sidebar
    picker and the "make default" checkbox text. Reuses the delta *string* straight from the
    member name rather than round-tripping it through float() - member_name's own formatting
    doesn't round-trip cleanly (e.g. 7.5 -> 7.500000000000001), and there is no reason to pay
    that here."""
    match = _MEMBER_RE.search(member)
    if match is None:
        return member
    parts = [f"k{match.group(2)}", f"d{match.group(3)}"]
    if match.group(1):
        parts.insert(0, channel_label(match.group(1)))
    return " · ".join(parts)


def channel_label(channel: str) -> str:
    """The display name of a channel or bundle, from either the raw name or its token."""
    token = channel_token(channel)
    return CHANNEL_LABELS.get(token, token.upper())
