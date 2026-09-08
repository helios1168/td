"""override.py: the map-override driver. Mode A relabels a parent zip table by hand and reports
balance, contiguity and a diff, with no solver rerun; Mode B feeds the same edits back into the
engine that drew the parent and reports the same numbers about what came out.

    .venv/bin/python3 tools/override.py instance_descaled_v2_conus.json.gz \\
        --table battery/results/app/draw_.../k18/draw.csv --edits edits.json --mode A \\
        --out battery/results/app/override_...

    .venv/bin/python3 tools/override.py instance_descaled_v2_conus.json.gz \\
        --table battery/results/app/clip_.../d0.1/draw.csv --edits edits.json --mode B \\
        --parent battery/results/app/clip_... --out battery/results/app/override_...

edits.json: `{"moves": [{"unit": "state"|"zip", "id": "TX", "to": "D05"}], "hold": {"states":
[...], "zips": [...]}}`. A state move relabels every row of that state; a zip move relabels one
row; a move to a district id absent from the parent creates it. Mode A ignores `hold`, since it
reruns nothing.

The table is the unit: balance, contiguity and the diff all come from the table alone, never
from the instance. In Mode A the instance is opened once, only to assert the CONUS ground set
holds (`td.geo.assert_conus`); Mode B leaves that to the engine it reruns, which asserts it
before doing anything. A district's owner-state set is every state where the district holds at
least `eta` of that state's own opportunity, the same rule `tools/state_splits.py` uses for its
z-flags; contiguity checks that set against the state rook graph (`td.geo.state_rook`), and a
district owning no state reads as disconnected rather than trivially connected.

Mode B needs `--parent`, the parent run directory, because the edits are translated into the
flags of whichever engine drew it: it walks `step.json` `parent` links up to the nearest run of
kind `draw` or `clip` and reruns *that* run's own argv, with `--out` pointed inside this run and
one extra flag, `--lock-zips locks.json` for a draw or `--bounds bounds.json` for a clip. An
`import` root has no engine to rerun and exits nonzero. Everything in the lineage between the
engine and the parent is a relabel, so an earlier override survives a Mode B rerun only where
the edits hold it: `edits_honoured` in `metrics.json` says, per move and per hold, whether the
final table carries the label that was asked for.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Iterable

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import geo, instance, ziptable                                      # noqa: E402


# --------------------------------------------------------------------------------- relabelling
def apply_moves(rows: list[dict], moves: list[dict]) -> tuple[list[dict], int]:
    """Apply `moves` in order to a copy of `rows`; return the copy and how many rows changed.

    A `"state"` move relabels every row carrying that state; a `"zip"` move relabels the one row
    with that zip. Unknown state or zip raises `ValueError`, before any row is touched by that
    move. A row's `rep` is cleared to `""` only if its final district differs from the one it
    started with, so a move that lands back on a row's original district leaves it untouched.
    """
    out = [dict(r) for r in rows]
    original = {r["zip"]: r["district"] for r in rows}
    by_zip = {r["zip"]: r for r in out}
    by_state: dict[str, list[dict]] = {}
    for r in out:
        by_state.setdefault(r["state"], []).append(r)

    for mv in moves:
        unit, mid, to = mv["unit"], str(mv["id"]).strip(), mv["to"]
        if unit == "state":
            sid = mid.upper()
            targets = by_state.get(sid)
            if not targets:
                raise ValueError(f"unknown state {sid!r}: not in the parent table")
            for r in targets:
                r["district"] = to
        elif unit == "zip":
            zid = mid.zfill(5)
            r = by_zip.get(zid)
            if r is None:
                raise ValueError(f"unknown zip {zid!r}: not in the parent table")
            r["district"] = to
        else:
            raise ValueError(f"unknown move unit {unit!r}: expected 'state' or 'zip'")

    n_relabelled = 0
    for r in out:
        if r["district"] != original[r["zip"]]:
            r[ziptable.REP] = ""
            n_relabelled += 1
    return out, n_relabelled


# --------------------------------------------------------------------------------- contiguity
def owner_sets(rows: list[dict], eta: float) -> dict[str, set[str]]:
    """`{district: {state, ...}}`: the states a district holds at least `eta` of.

    Every non-empty district in `rows` gets an entry, even an empty set, so a district with no
    state above `eta` still reads as owning nothing rather than being absent from the result.
    """
    mass_by_state: dict[str, float] = {}
    mass_by_pair: dict[tuple[str, str], float] = {}
    districts: set[str] = set()
    for r in rows:
        state, district, m = r["state"], r["district"], float(r["opportunity"])
        if state:
            mass_by_state[state] = mass_by_state.get(state, 0.0) + m
        if district:
            districts.add(district)
            if state:
                key = (state, district)
                mass_by_pair[key] = mass_by_pair.get(key, 0.0) + m

    out: dict[str, set[str]] = {d: set() for d in districts}
    for (state, district), m in mass_by_pair.items():
        total = mass_by_state.get(state, 0.0)
        if total > 0 and m / total >= eta:
            out[district].add(state)
    return out


def contiguity(owner_sets: dict[str, set[str]], rook: dict[str, Iterable[str]]) -> dict[str, bool]:
    """`{district: bool}`: is each district's owner-state set connected in `rook`?

    The empty set reads as disconnected: a district owning no state is not a map a rep can work.
    """
    out: dict[str, bool] = {}
    for district, states in owner_sets.items():
        if not states:
            out[district] = False
            continue
        seen = {next(iter(states))}
        stack = list(seen)
        while stack:
            s = stack.pop()
            for t in rook.get(s, ()):
                if t in states and t not in seen:
                    seen.add(t)
                    stack.append(t)
        out[district] = seen == states
    return out


# ------------------------------------------------------------------------------------- report
def report(parent_rows: list[dict], rows: list[dict], k: int,
          rook: dict[str, Iterable[str]], eta: float) -> dict:
    """Balance, contiguity, diff and split states for a child table against its parent.

    Both modes report the same five numbers about their own table, so both compute them here;
    the child table is whatever produced it, a relabel in Mode A and an engine rerun in Mode B.
    `k` is the same before and after, so balance is measured against one target.
    """
    owners = owner_sets(rows, eta)
    contig = contiguity(owners, rook)

    total = sum(float(r["opportunity"]) for r in rows)
    mass_before: dict[str, float] = {}
    mass_after: dict[str, float] = {}
    for r in parent_rows:
        if r["district"]:
            mass_before[r["district"]] = mass_before.get(r["district"], 0.0) + float(r["opportunity"])
    for r in rows:
        if r["district"]:
            mass_after[r["district"]] = mass_after.get(r["district"], 0.0) + float(r["opportunity"])
    districts_diff = {
        d: dict(share_before=mass_before.get(d, 0.0) / total if total else 0.0,
               share_after=mass_after.get(d, 0.0) / total if total else 0.0)
        for d in sorted(set(mass_before) | set(mass_after))
    }

    before = {r["zip"]: r["district"] for r in parent_rows}
    n_relabelled = sum(1 for r in rows if before.get(r["zip"]) != r["district"])

    state_districts: dict[str, set[str]] = {}
    for r in rows:
        if r["state"] and r["district"]:
            state_districts.setdefault(r["state"], set()).add(r["district"])
    states_split = sorted(s for s, ds in state_districts.items() if len(ds) > 1)

    return dict(
        balance=ziptable.balance(rows, k),
        balance_before=ziptable.balance(parent_rows, k),
        contiguity=contig,
        diff=dict(zips_relabelled=n_relabelled, districts=districts_diff),
        states_split=states_split,
    )


# --------------------------------------------------------------------------------------- mode A
def mode_a(parent_rows: list[dict], edits: dict, rook: dict[str, Iterable[str]],
          eta: float) -> tuple[list[dict], dict]:
    """Relabel `parent_rows` by `edits["moves"]` and report balance, contiguity and a diff.

    `k` is fixed at the parent's own district count, so balance is measured against the same
    target before and after. `edits_honoured` is always true here: a relabel is exact, unlike a
    Mode B rerun where a hold or a lock can fail to hold.
    """
    moves = edits.get("moves", [])
    k = len({r["district"] for r in parent_rows if r["district"]})
    rows, _ = apply_moves(parent_rows, moves)

    metrics = dict(mode="A", k=k, moves=moves,
                  **report(parent_rows, rows, k, rook, eta),
                  edits_honoured=True)
    return rows, metrics


# --------------------------------------------------------------------------------- mode B: setup
ENGINE_KINDS = ("draw", "clip")


def engine_ancestor(parent: str) -> tuple[str, dict]:
    """The nearest run at or above `parent` an engine actually produced, and its `step.json`.

    Mode B reruns an engine, so it needs one. Relabels (Mode A) and imports carry no driver to
    rerun, and a lineage of nothing else is refused here rather than at the point where an argv
    would have to be invented.
    """
    root = os.path.dirname(os.path.abspath(parent))
    run = os.path.abspath(parent)
    seen: list[str] = []
    while True:
        path = os.path.join(run, "step.json")
        if not os.path.exists(path):
            sys.exit(f"--parent: no step.json in {run}")
        with open(path, encoding="utf-8") as fh:
            step = json.load(fh)
        seen.append(os.path.basename(run))
        if step.get("kind") in ENGINE_KINDS:
            return run, step
        nxt = step.get("parent")
        if not nxt or nxt in seen:
            sys.exit(f"--parent {os.path.basename(os.path.abspath(parent))}: no draw or clip "
                     f"ancestor ({' <- '.join(seen)}); mode B has no engine to rerun")
        run = os.path.join(root, nxt)


def _state_zips(by_state: dict[str, list[str]], code) -> list[str]:
    zips = by_state.get(str(code).strip().upper())
    if not zips:
        raise ValueError(f"unknown state {str(code).strip().upper()!r}: not in the parent table")
    return zips


def _known_zip(label: dict[str, str], code) -> str:
    z = str(code).strip().zfill(5)
    if z not in label:
        raise ValueError(f"unknown zip {z!r}: not in the parent table")
    return z


def _index(parent_rows: list[dict]) -> tuple[dict[str, str], dict[str, str], dict[str, list[str]]]:
    """`({zip: district}, {zip: state}, {state: [zip]})` over the parent table."""
    label = {r["zip"]: r["district"] for r in parent_rows}
    state_of = {r["zip"]: r["state"] for r in parent_rows}
    by_state: dict[str, list[str]] = {}
    for r in parent_rows:
        by_state.setdefault(r["state"], []).append(r["zip"])
    return label, state_of, by_state


def draw_locks(parent_rows: list[dict], edits: dict) -> dict[str, str]:
    """`{zip: district}` for `run_draw.py --lock-zips`: the moved units at the label they were
    asked for, the held units at the label they carry in the parent table.

    Everything not named here is redrawn free, which is what makes the caveat the UI shows true:
    the other districts are re-seeded and renamed, and only the moved and held names persist.
    A move wins over a hold on the same unit, so a contradictory pair pins the zip where the
    move asked rather than refusing the run.
    """
    label, _state_of, by_state = _index(parent_rows)
    locks: dict[str, str] = {}
    for mv in edits.get("moves") or []:
        unit, mid, to = mv["unit"], mv["id"], str(mv["to"])
        if unit == "state":
            for z in _state_zips(by_state, mid):
                locks[z] = to
        elif unit == "zip":
            locks[_known_zip(label, mid)] = to
        else:
            raise ValueError(f"unknown move unit {unit!r}: expected 'state' or 'zip'")
    hold = edits.get("hold") or {}
    for code in hold.get("states") or []:
        for z in _state_zips(by_state, code):
            locks.setdefault(z, label[z])
    for code in hold.get("zips") or []:
        z = _known_zip(label, code)
        locks.setdefault(z, label[z])
    return locks


def clip_bounds(parent_rows: list[dict], edits: dict, eta: float) -> dict:
    """The same edits as a `state_splits.py --bounds` document (`parse_bounds` for the schema).

    A state move is a `fix`: the clip decides which districts a state touches, and a moved state
    must touch the target and nothing else. A zip move is weaker by nature, since level 1 knows
    nothing about zips: the state is `force`d to touch the target so level 1 sends it mass at
    all, and the zip is `pull`ed there at level 2, which is only a preference. A held state keeps
    the district set it holds in the parent table, at the same `eta` the clip uses for its own
    z-flags; when that set has more than one district, the split it stands for is reproduced
    only by freezing the state's zips at their parent labels.
    """
    label, state_of, by_state = _index(parent_rows)
    owners = owner_sets(parent_rows, eta)

    force: list[list[str]] = []
    fix: dict[str, list[str]] = {}
    freeze: dict[str, str] = {}
    pull: dict[str, str] = {}
    moved_states: set[str] = set()
    moved_zips: set[str] = set()

    for mv in edits.get("moves") or []:
        unit, mid, to = mv["unit"], mv["id"], str(mv["to"])
        if unit == "state":
            sid = str(mid).strip().upper()
            _state_zips(by_state, sid)
            fix[sid] = [to]
            moved_states.add(sid)
        elif unit == "zip":
            z = _known_zip(label, mid)
            pair = [state_of[z], to]
            if pair not in force:
                force.append(pair)
            pull[z] = to
            moved_zips.add(z)
        else:
            raise ValueError(f"unknown move unit {unit!r}: expected 'state' or 'zip'")

    hold = edits.get("hold") or {}
    for code in hold.get("states") or []:
        sid = str(code).strip().upper()
        zips = _state_zips(by_state, sid)
        if sid in moved_states:
            continue
        held = sorted(d for d, states in owners.items() if sid in states)
        if not held:
            raise ValueError(f"hold state {sid!r} owns no district at eta={eta:g}: nothing to fix")
        fix[sid] = held
        if len(held) > 1:
            for z in zips:
                if z not in moved_zips:
                    freeze[z] = label[z]
    for code in hold.get("zips") or []:
        z = _known_zip(label, code)
        if z not in moved_zips:
            freeze.setdefault(z, label[z])

    doc = dict(force=force, fix=fix, freeze=freeze, pull=pull)
    return {key: val for key, val in doc.items() if val}


def edits_honoured(parent_rows: list[dict], rows: list[dict], edits: dict) -> dict:
    """Per move and per hold, does the final table carry the label that was asked for?

    A lock is exact and a `fix` is a bound, but a `pull` is a preference and a rerun can rename
    or re-seed anything it was not told to keep, so this is read off the table rather than
    assumed. A hold counts as honoured when the unit still carries its parent label.
    """
    before, _state_of, by_state = _index(parent_rows)
    after = {r["zip"]: r["district"] for r in rows}

    moves = []
    for mv in edits.get("moves") or []:
        unit, mid, to = mv["unit"], mv["id"], str(mv["to"])
        if unit == "state":
            zips = _state_zips(by_state, mid)
        else:
            zips = [_known_zip(before, mid)]
        moves.append(dict(unit=unit, id=mv["id"], to=to,
                         honoured=all(after.get(z) == to for z in zips)))

    states = {}
    for code in (edits.get("hold") or {}).get("states") or []:
        sid = str(code).strip().upper()
        states[sid] = all(after.get(z) == before[z] for z in _state_zips(by_state, sid))
    zips_held = {}
    for code in (edits.get("hold") or {}).get("zips") or []:
        z = _known_zip(before, code)
        zips_held[z] = after.get(z) == before[z]
    return dict(moves=moves, hold=dict(states=states, zips=zips_held))


# ---------------------------------------------------------------------------------- mode B: run
def _set_flag(argv: list[str], flag: str, value: str) -> list[str]:
    """`argv` with `flag`'s value replaced, or the flag and value appended when it is absent."""
    out = list(argv)
    if flag in out:
        out[out.index(flag) + 1] = value
        return out
    return out + [flag, value]


def _engine_failure(engine_out: str, out: str, rc: int, table: str) -> str:
    """`<out>/failure.json`: the engine's own reason where it wrote one, else that it failed.

    `state_splits.py` distinguishes `infeasible` from `no_incumbent` and that distinction is the
    whole answer for an override the band cannot meet, so its file is copied out verbatim rather
    than restated. `run_draw.py` writes none, hence the fallback.
    """
    src = os.path.join(engine_out, "failure.json")
    dst = os.path.join(out, "failure.json")
    if os.path.exists(src):
        shutil.copyfile(src, dst)
        return dst
    message = (f"the engine exited {rc}" if rc
              else f"the engine exited 0 but wrote no {os.path.basename(table)}")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(dict(reason="engine_failed", returncode=rc, message=message), fh, indent=2)
        fh.write("\n")
    return dst


def mode_b(args) -> int:
    """Translate `edits.json` into the engine ancestor's own flags, rerun it, report what held."""
    run, step = engine_ancestor(args.parent)
    kind, params = step["kind"], step.get("params") or {}
    argv = list(step.get("argv") or [])
    if not argv:
        sys.exit(f"--parent: {os.path.basename(run)} carries no argv to rerun")

    parent_rows = ziptable.read(args.table)
    with open(args.edits, encoding="utf-8") as fh:
        edits = json.load(fh)

    os.makedirs(args.out, exist_ok=True)
    engine_out = os.path.join(args.out, "engine")
    k = int(params["k"])

    try:
        if kind == "draw":
            key, document = "locks", draw_locks(parent_rows, edits)
            path = os.path.join(args.out, "locks.json")
            cmd = _set_flag(_set_flag(argv, "--out", engine_out), "--lock-zips", path)
            table = os.path.join(engine_out, f"k{k:02d}", "draw.csv")
        else:
            key, document = "bounds", clip_bounds(parent_rows, edits, args.eta)
            path = os.path.join(args.out, "bounds.json")
            delta = params["delta"]
            delta = float(delta[0] if isinstance(delta, (list, tuple)) else delta)
            cmd = _set_flag(_set_flag(argv, "--out", engine_out), "--bounds", path)
            table = os.path.join(engine_out, f"d{delta:g}", "draw.csv")
    except ValueError as exc:
        sys.exit(str(exc))

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(document, fh, indent=2)
        fh.write("\n")

    print(f"override B: rerunning {kind} {os.path.basename(run)} into {engine_out}", flush=True)
    rc = subprocess.run(cmd, check=False).returncode
    if rc != 0 or not os.path.exists(table):
        failure = _engine_failure(engine_out, args.out, rc, table)
        print(f"override B: the {kind} rerun failed (exit {rc}); wrote {failure}", flush=True)
        return 1

    rows = ziptable.read(table)
    rook, _ = geo.state_rook(args.geo_cache)
    metrics = dict(mode="B", engine=kind, engine_run=os.path.basename(run), engine_out="engine",
                  k=k, moves=edits.get("moves") or [],
                  **report(parent_rows, rows, k, rook, args.eta),
                  **{key: document},
                  edits_honoured=edits_honoured(parent_rows, rows, edits))
    if kind == "clip":
        splits = os.path.join(os.path.dirname(table), "splits.json")
        if os.path.exists(splits):
            with open(splits, encoding="utf-8") as fh:
                metrics["bounds_honoured"] = json.load(fh).get("bounds_honoured")

    ziptable.write(os.path.join(args.out, "draw.csv"), rows)
    with open(os.path.join(args.out, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
        fh.write("\n")

    honoured = metrics["edits_honoured"]
    n_edits = (len(honoured["moves"]) + len(honoured["hold"]["states"])
              + len(honoured["hold"]["zips"]))
    n_held = (sum(1 for m in honoured["moves"] if m["honoured"])
             + sum(1 for ok in honoured["hold"]["states"].values() if ok)
             + sum(1 for ok in honoured["hold"]["zips"].values() if ok))
    bal, bal0 = metrics["balance"], metrics["balance_before"]
    n_disc = sum(1 for ok in metrics["contiguity"].values() if not ok)
    print(f"override B: {kind} rerun; {n_held}/{n_edits} edit(s) honoured; "
          f"{metrics['diff']['zips_relabelled']} zip(s) relabelled; "
          f"max_dev_rel {bal0['max_dev_rel']:.4f} -> {bal['max_dev_rel']:.4f}; "
          f"{n_disc} district(s) disconnected", flush=True)
    return 0


# --------------------------------------------------------------------------------------- CLI
def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("instance", help="the descaled instance (.json.gz)")
    ap.add_argument("--table", required=True, help="the parent zip table (draw.csv)")
    ap.add_argument("--edits", required=True, help="edits.json: moves plus an optional hold set")
    ap.add_argument("--mode", required=True, choices=("A", "B"),
                    help="A relabels only; B reruns the parent kind's driver")
    ap.add_argument("--parent", default=None,
                    help="the parent run directory (its step.json); mode B only, where the "
                         "nearest draw or clip ancestor is the engine that gets rerun")
    ap.add_argument("--eta", type=float, default=0.01,
                    help="share of a state's opportunity a district must hold to own it")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--out", required=True, help="output directory")
    return ap


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    if args.mode == "B":
        if not args.parent:
            sys.exit("--mode B needs --parent: the edits are translated into the flags of "
                     "whichever engine drew the parent")
        return mode_b(args)

    d = instance.load_descaled(args.instance)
    geo.assert_conus(d)

    parent_rows = ziptable.read(args.table)
    with open(args.edits, encoding="utf-8") as fh:
        edits = json.load(fh)
    rook, _ = geo.state_rook(args.geo_cache)

    try:
        rows, metrics = mode_a(parent_rows, edits, rook, args.eta)
    except ValueError as exc:
        sys.exit(str(exc))

    ziptable.write(os.path.join(args.out, "draw.csv"), rows)
    with open(os.path.join(args.out, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
        fh.write("\n")

    bal, bal0 = metrics["balance"], metrics["balance_before"]
    n_disc = sum(1 for ok in metrics["contiguity"].values() if not ok)
    print(f"override A: {metrics['diff']['zips_relabelled']} zip(s) relabelled; "
          f"max_dev_rel {bal0['max_dev_rel']:.4f} -> {bal['max_dev_rel']:.4f}; "
          f"{n_disc} district(s) disconnected", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
