"""override.py: the map-override driver. Mode A relabels a parent zip table by hand and reports
balance, contiguity and a diff, with no solver rerun; Mode B (reran through a driver, wave 2)
is a stub here.

    .venv/bin/python3 tools/override.py instance_descaled_v2_conus.json.gz \\
        --table battery/results/app/draw_.../k18/draw.csv --edits edits.json --mode A \\
        --out battery/results/app/override_...

edits.json: `{"moves": [{"unit": "state"|"zip", "id": "TX", "to": "D05"}], "hold": {"states":
[...], "zips": [...]}}`. A state move relabels every row of that state; a zip move relabels one
row; a move to a district id absent from the parent creates it. Mode A ignores `hold`, since it
reruns nothing.

The table is the unit: balance, contiguity and the diff all come from the table alone, never
from the instance. The instance is opened once, only to assert the CONUS ground set holds
(`td.geo.assert_conus`). A district's owner-state set is every state where the district holds
at least `eta` of that state's own opportunity, the same rule `tools/state_splits.py` uses for
its z-flags; contiguity checks that set against the state rook graph (`td.geo.state_rook`), and
a district owning no state reads as disconnected rather than trivially connected.
"""
from __future__ import annotations

import argparse
import json
import os
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

    rows, n_relabelled = apply_moves(parent_rows, moves)

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

    state_districts: dict[str, set[str]] = {}
    for r in rows:
        if r["state"] and r["district"]:
            state_districts.setdefault(r["state"], set()).add(r["district"])
    states_split = sorted(s for s, ds in state_districts.items() if len(ds) > 1)

    metrics = dict(
        mode="A", k=k, moves=moves,
        balance=ziptable.balance(rows, k),
        balance_before=ziptable.balance(parent_rows, k),
        contiguity=contig,
        diff=dict(zips_relabelled=n_relabelled, districts=districts_diff),
        states_split=states_split,
        edits_honoured=True,
    )
    return rows, metrics


def mode_b() -> int:
    """Wave 2 fills this in: translate `edits.json` and `os.execv` the parent kind's driver."""
    print("Mode B lands in wave 2")
    return 2


# --------------------------------------------------------------------------------------- CLI
def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("instance", help="the descaled instance (.json.gz)")
    ap.add_argument("--table", required=True, help="the parent zip table (draw.csv)")
    ap.add_argument("--edits", required=True, help="edits.json: moves plus an optional hold set")
    ap.add_argument("--mode", required=True, choices=("A", "B"),
                    help="A relabels only; B reruns the parent kind's driver")
    ap.add_argument("--eta", type=float, default=0.01,
                    help="share of a state's opportunity a district must hold to own it")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--out", required=True, help="output directory")
    return ap


def main(argv=None) -> int:
    args = build_argparser().parse_args(argv)
    if args.mode == "B":
        return mode_b()

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
