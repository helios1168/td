"""ziptable.py -- the zip table, the unit the pipeline passes from stage to stage.

One row per instance zip, columns exactly::

    zip,state,x,y,opportunity,district[,rep]

sorted by zip, the zip a 5-character string so `01103` keeps its leading zero, `x`/`y` the
LAEA projection of the gazetteer's internal point (empty when the gazetteer has no point for
that zip), `state` the instance's own state code (empty when unknown), `opportunity` the
instance's `M_z`, and `district` the label the table is carrying.  `rep` is optional: the
rep staffing the zip's district (`tools/staff.py`) or, inside a split district, the rep owning
the zip (`tools/split_district.py`); `read` returns it as `""` when the column is absent, and
`write` emits the column only when some row carries a rep, so a plain map stays six columns.

The table lives in `draw.csv` itself: the two columns every reader already knows are the first
and the last, and the four in between are what a map needed the instance and the gazetteer for.
A table is therefore self-sufficient -- `render` draws it with no instance file, no gazetteer
join and no confidential lookup beyond the masses the table already carries -- and an
intermediate step of a solver can be written out and drawn exactly like a final draw.

`render` calls the builders in `tools/us_maps.py`.  `tools/` is not a package, so it is loaded
by path (the route `tests/test_geo.py` uses).  Per-state clipping and heavy state lines are
always on here: a table carries `state` per zip, so the clip needs no argument the caller could
forget, and every map drawn from a table is the one whose point is where the borders sit
against state lines.
"""
from __future__ import annotations

import csv
import importlib.util
import math
import os
import sys

COLUMNS: tuple[str, ...] = ("zip", "state", "x", "y", "opportunity", "district")
REP = "rep"                        # the optional seventh column

# `--bold-states`' own settings, applied unconditionally: see the module docstring.
STATE_W = 1.6
STATE_COLOR = "#555555"

FIGURES: dict[str, str] = {
    "districts": "districts.png",
    "regions_voronoi": "district_regions_voronoi.png",
}

_US_MAPS = None


def _zip5(z) -> str:
    """`1103` and `"01103"` alike -> `"01103"`; the join key everything downstream uses."""
    return str(z).strip().zfill(5)


# ------------------------------------------------------------------------------ build / io
def build(d, xy: dict, labels: dict, reps: dict | None = None) -> list[dict]:
    """One row per zip of the loaded instance `d`, from `{zip: (x, y)}` and `{zip: district}`.

    A zip absent from `xy` gets an empty `x`/`y` and is still a row: it carries opportunity and
    a district, it is simply not drawable.  A zip absent from `labels` gets an empty district,
    which is what an unfinished labelling looks like.  `reps` is `{zip: rep}` for the optional
    `rep` column; absent, every row carries `""`.
    """
    rows = []
    for z in d.G:
        node = d.G.nodes[z]
        p = xy.get(z)
        rows.append(dict(
            zip=_zip5(z),
            state=str(node.get("state") or ""),
            x=None if p is None else float(p[0]),
            y=None if p is None else float(p[1]),
            opportunity=float(node["M"]),
            district=str(labels.get(z, "")),
            rep=str((reps or {}).get(z, "")),
        ))
    rows.sort(key=lambda r: r["zip"])
    return rows


def write(path: str, rows: list[dict]) -> str:
    """Write `rows` to `path` as the zip table, creating the directory if it is absent.

    `None` becomes an empty field; floats are written by `str`, which round-trips exactly.
    The `rep` column is written only when some row carries a rep.
    """
    cols = list(COLUMNS) + ([REP] if any(r.get(REP) for r in rows) else [])
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r[c]) for c in cols})
    return path


def read(path: str) -> list[dict]:
    """Read a zip table back into `build`'s own shape, floats parsed and empties as `None`."""
    with open(path, newline="", encoding="utf-8") as fh:
        rdr = csv.DictReader(fh)
        missing = [c for c in COLUMNS if c not in (rdr.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing column(s) {missing}; "
                             f"a zip table has {list(COLUMNS)}")
        rows = []
        for r in rdr:
            x, y = (r["x"] or "").strip(), (r["y"] or "").strip()
            rows.append(dict(
                zip=_zip5(r["zip"]),
                state=(r["state"] or "").strip(),
                x=float(x) if x else None,
                y=float(y) if y else None,
                opportunity=float((r["opportunity"] or "").strip() or 0.0),
                district=(r["district"] or "").strip(),
                rep=(r.get(REP) or "").strip(),
            ))
    return rows


# ------------------------------------------------------------------------------ projections
def labels(rows: list[dict]) -> dict[str, str]:
    """`{zip: district}` -- what `us_maps.read_draw` returns for the same file."""
    return {r["zip"]: r["district"] for r in rows}


def masses(rows: list[dict]) -> dict[str, float]:
    """`{zip: M_z}`."""
    return {r["zip"]: float(r["opportunity"]) for r in rows}


def balance(rows: list[dict], k: int) -> dict:
    """Equal-opportunity balance of the table's own labelling, against the `k`-way target.

    `target` is `total / k`, not the mean of the districts present, so a table missing a
    district reads as unbalanced rather than as balanced over fewer.  `nash` is `sum_j log g_j`,
    `ceiling` its `k log(total/k)` maximum, and `gap` the difference.
    """
    if k <= 0:
        raise ValueError(f"k must be positive; got {k}")
    per: dict[str, float] = {}
    for r in rows:
        if r["district"]:
            per[r["district"]] = per.get(r["district"], 0.0) + float(r["opportunity"])
    if not per:
        raise ValueError("no labelled rows: the table carries no district")
    g = [per[d] for d in sorted(per)]
    total = float(sum(g))
    tau = total / k
    nash = sum(math.log(v) for v in g) if all(v > 0 for v in g) else -math.inf
    ceiling = k * math.log(tau) if tau > 0 else -math.inf
    return dict(
        k=k,
        n_districts=len(g),
        total=total,
        target=tau,
        spread_rel=(max(g) - min(g)) / tau,
        max_dev_rel=max(abs(v / tau - 1.0) for v in g),
        nash=nash,
        ceiling=ceiling,
        gap=ceiling - nash,
    )


# ------------------------------------------------------------------------------ rendering
def _us_maps():
    """`tools/us_maps.py` as a module.  `tools/` is not a package, so this loads it by path."""
    global _US_MAPS
    if _US_MAPS is None:
        mod = sys.modules.get("us_maps")
        if mod is None:
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "tools", "us_maps.py")
            spec = importlib.util.spec_from_file_location("us_maps", path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules["us_maps"] = mod
            spec.loader.exec_module(mod)
        _US_MAPS = mod
    return _US_MAPS


def render(rows: list[dict], out_dir: str, states, *,
           which: tuple[str, ...] = ("districts", "regions_voronoi"),
           report=None) -> list[str]:
    """Draw the table into `out_dir` and return the paths written.

    `states` is the basemap GeoDataFrame (`td.geo.states_outline`), or `None` for no basemap --
    which also means no per-state clipping, the branch the tests use so they need no network.
    A row with no `x`/`y` is not drawn but still counts toward its district's legend entry,
    exactly as it did when the maps were built from a two-column draw plus the instance.
    """
    unknown = [w for w in which if w not in FIGURES]
    if unknown:
        raise ValueError(f"unknown figure(s) {unknown}; known: {sorted(FIGURES)}")
    um = _us_maps()

    drawn = [r for r in rows if r["district"]]
    districts = {r["zip"]: r["district"] for r in drawn}
    values = {r["zip"]: float(r["opportunity"]) for r in drawn}
    xy = {r["zip"]: (r["x"], r["y"]) for r in drawn if r["x"] is not None and r["y"] is not None}
    zip_state = {r["zip"]: r["state"] for r in drawn}
    state_polys = None if states is None else dict(zip(states["STUSPS"], states.geometry))

    os.makedirs(out_dir, exist_ok=True)
    written = []
    for name in which:
        out = os.path.join(out_dir, FIGURES[name])
        if name == "districts":
            written.append(um.figure_districts(districts, values, xy, states, out,
                                               state_w=STATE_W, state_color=STATE_COLOR))
        else:
            kw = dict(report=report, state_w=STATE_W, state_color=STATE_COLOR)
            if state_polys is not None:
                kw.update(zip_state=zip_state, state_polys=state_polys)
            written.append(um.figure_district_regions(districts, values, xy, states, out, **kw))
    return written
