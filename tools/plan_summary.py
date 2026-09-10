"""plan_summary.py: a realised `tools/full_plan.py` run -> one figure a stakeholder can read.

    .venv/bin/python3 tools/plan_summary.py battery/results/full_problem/v3_seq_warm \\
        --geo-cache /Users/ntlee/projects/td/data/geo

`tools/plan_maps.py` answers "is this district a territory or a scatter", one bundle at a time.
This answers the question above it: what does the whole plan do to the country.  One
`maps/summary.png` (and `.svg`) carrying

  * a CONUS map of the **channel structure by state**: which plan pattern each state falls
    into (`structure_panel`, unchanged), with the number of wholesalers serving that state
    (distinct used slots with a positive share of it, `plan.json`'s own `per_state`) printed
    under its code, and
  * **one map per bundle** present in the run (`N`, `WH`, `FI`, `WHFI`, `WHFI_PLUS`, `WH_PLUS`,
    `FI_PLUS`, or any other bundle name the run carries), drawn as the app's own **reach**
    layer only (by the user's request of 2026-09-11, dropping the earlier zip-level rendering):
    state outlines, each district's reach filled solid in its own hue and outlined, state codes,
    and the id labelled with its wholesaler.  No zip geometry is drawn: no ZCTA cell fills, no
    opportunity shading, no district ZCTA-union outline.  `app/mapfig.py` needs plotly, which
    the hub venv lacks, so the layering is reproduced here in matplotlib rather than imported.

A district id is displayed through `display_id`: `WHFI_PLUS_07` reads as `WIFI_07` on every
label and strip; the underlying id is never rewritten, so `assignment.csv`/`districts.csv` and
this figure agree on what a district is called, only not on how it is printed.

Geometry still comes from `tools/geom_export.py::export`, one payload per bundle; it needs the
real ZCTA polygons of a bundle's own zips to build `district_reach` at all, even though the map
draws only that one layer.  Each bundle's payload is pickled under `maps/cache/<bundle>_geom.pkl`,
keyed by that bundle's own zip-to-district mapping (and the gazetteer vintage), so a rerun after
an edit to the figure costs seconds and a rerun after a new realise recomputes only the bundles
that changed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import geo                                                        # noqa: E402
import geom_export                                                        # noqa: E402
import run_draw                                                           # noqa: E402
import us_maps                                                            # noqa: E402

OTHER = "other"                 # `tools/plan_realise.py::OTHER`, the no-district pseudo-label

# The three channels the business runs.  `N_WH` and `N_FI` are the two halves of the national
# book (the wholesale side and the field side); a stakeholder reads them as one channel, so the
# footer's residual line folds them together.
BUSINESS = ("National", "WH", "FI")
CHANNEL_BUSINESS = {"N_WH": "National", "N_FI": "National", "WH": "WH", "FI": "FI"}

PLUS = "⁺"                 # superscript plus, `bundle_label`'s own "FI+" reading

# What a state's plan pattern is, in the order the classifier tests them.  "all merged" is a
# state some `WHFI_PLUS` district holds a share of: one rep for national, WH and FI there, the
# "all" district the plan opens where no single channel can reach a book.
PATTERNS = ("three channels", "WH+FI merged", "all merged", "national dropped", "partial",
            "unserved")
PATTERN_FILL = {
    "three channels":   "#a6cee3",
    "WH+FI merged":     "#b2a0d6",
    "all merged":       "#f4a3b5",
    "national dropped": "#fdbf6f",
    "partial":          "#f3e79b",
    "unserved":         "#e2e2e2",
}
PATTERN_TEXT = {
    "three channels":   "three channels, three reps",
    "WH+FI merged":     "WH + FI merged, one rep",
    "all merged":       "all three channels, one rep",
    "national dropped": "national folded into WH and FI",
    "partial":          "one or two channels",
    "unserved":         "no channel",
}

SPLIT_HATCH = "#8a8a8a"
STATE_CODE_MIN_AREA = 2.0e10    # m^2: a state under 20,000 km^2 (RI DE CT) gets no code

# The bundle map's own reading order and titles.  A bundle not on this list (a future bundle
# name) is titled by its own name and sorted after the seven known ones.
BUNDLE_ORDER = ["N", "WH", "FI", "WHFI", "WHFI_PLUS", "WH_PLUS", "FI_PLUS"]
BUNDLE_TITLE = {
    "N":          "National only",
    "WH":         "WH only",
    "FI":         "FI only",
    "WHFI":       "WH + FI merged, one wholesaler (national separate)",
    "WHFI_PLUS":  "WIFI: national + WH + FI, one wholesaler",
    "WH_PLUS":    "National + WH, one wholesaler",
    "FI_PLUS":    "National + FI, one wholesaler",
}

# A bundle panel's own house style: the app's colours and line weights, scaled down for a panel
# that is a fraction of the page rather than the app's own full-width map.
STATE_OUTLINE_COLOR = "#b0b0b0"
STATE_OUTLINE_W = 0.4           # the app's 0.8, halved for a panel
REACH_FILL_ALPHA = 0.6          # solid: with no zip geometry drawn on top, the reach is the
                                 # district's whole reading, not a pale ground under it
REACH_OUTLINE_W = 1.1

# The small northeast states and a split CA's Bay Area / LA districts are smaller than a label
# box at the default min_ratio=1.0, so their fill stays hidden under the label; a wider search
# radius gives the moved label somewhere clear to land instead of overlapping its neighbour.
LABEL_ROOM = 4.0
LEADER_RADII = (0.09, 0.16)

DPI = 110
FIG_WIDTH = 22.0
ROW_HEIGHT_IN = 6.8             # one row of panels, the maps' own aspect at this width
TITLE_IN = 0.7                  # figure inches reserved above the grid for the suptitle
FOOTER_IN = 1.3                 # figure inches below the grid: the last row's own strip, then
                                 # the footer: more than one line, since the last row has no
                                 # following row's hspace gap to draw its strip into
GRID_HSPACE = 0.12              # fraction of one row's own height; `hspace` is not a fixed
                                 # inch offset, so this has to shrink with `ROW_HEIGHT_IN`


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", help="a finished plan run, already realised")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--dpi", type=int, default=DPI)
    ap.add_argument("--simplify", type=float, default=geom_export.SIMPLIFY,
                    help="district/state ring tolerance in metres (default: geom_export's own)")
    ap.add_argument("--no-cache", action="store_true",
                    help="export bundle geometry again, ignoring maps/cache")
    ap.add_argument("--kappa", type=float, default=None,
                    help="descaled mass -> currency; the descaled instances carry none")
    return ap


# ------------------------------------------------------------------ what the run says
def bundle_kind(bundle: str) -> str:
    """`pure`, `plus` (carries the national book too) or `merged` (one rep, WH and FI)."""
    if bundle.startswith("WHFI"):
        return "merged"
    if bundle.endswith("_PLUS"):
        return "plus"
    return "pure"


def bundle_label(bundle: str) -> str:
    """The bundle in the reader's words."""
    kind = bundle_kind(bundle)
    if bundle == "N":
        return "National"
    if kind == "merged":
        base = "WH+FI merged"
        return f"{base}{PLUS}" if bundle.endswith("_PLUS") else base
    if kind == "plus":
        return f"{bundle[:-5]}{PLUS} (national folded in)"
    return bundle


def bundle_title(bundle: str) -> str:
    """The bundle map's title: the fixed reading for the seven named bundles, else its name."""
    return BUNDLE_TITLE.get(bundle, bundle)


def display_id(district: str) -> str:
    """The drawn id: `WHFI_PLUS_07` -> `WIFI_07`; every other id unchanged.

    Display only: labels and strips read through this, `assignment.csv` and `districts.csv`
    keep their own ids exactly as the realiser wrote them.
    """
    prefix = "WHFI_PLUS_"
    return f"WIFI_{district[len(prefix):]}" if district.startswith(prefix) else district


def load_assignment(path: str) -> dict:
    """One pass over `assignment.csv`: who holds what, per bundle and per business channel.

    A district's zip set does not depend on the channel row it was read from, so the per-bundle
    mapping dedupes; the per-channel sets do not, because a zip can be held on one half of the
    national book and dropped on the other.  `mass_by_bundle` sums `M_cell` per (bundle, zip)
    for exactly that reason too: the national book's two channel rows for one zip both carry
    bundle `N`, so a bundle map's opportunity shading has to add them rather than pick one.
    """
    zips_by_bundle: dict[str, dict] = {}
    mass_by_bundle: dict[str, dict] = {}
    unheld = {c: set() for c in BUSINESS}
    residual = {c: 0.0 for c in BUSINESS}
    districts = {c: set() for c in BUSINESS}
    held_states: dict[tuple, set] = {}
    zip_state: dict[str, str] = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            chan = CHANNEL_BUSINESS.get(row["channel"])
            if chan is None:
                continue
            zip_state[row["zip"]] = row["state"]
            name = row["district"]
            if not name or name == OTHER:
                unheld[chan].add(row["zip"])
                residual[chan] += float(row["M_cell"] or 0.0)
                continue
            bundle = row["bundle"]
            zips_by_bundle.setdefault(bundle, {})[row["zip"]] = name
            cell = mass_by_bundle.setdefault(bundle, {})
            cell[row["zip"]] = cell.get(row["zip"], 0.0) + float(row["M_cell"] or 0.0)
            districts[chan].add(name)
            held_states.setdefault((chan, row["state"]), set()).add(name)
    splits = {c: {s for (ch, s), ds in held_states.items() if ch == c and len(ds) > 1}
              for c in BUSINESS}
    return dict(zips_by_bundle=zips_by_bundle, mass_by_bundle=mass_by_bundle, unheld=unheld,
                residual=residual, districts=districts, splits=splits, zip_state=zip_state)


def district_meta(path: str) -> dict:
    """`{district: row}` from `districts.csv`, or `{}` when the run has no such file."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8", newline="") as fh:
        return {row["district"]: row for row in csv.DictReader(fh)}


def classify_state(present: set) -> str:
    """The state's plan pattern from the bundles holding a positive share of it."""
    if not present:
        return "unserved"
    if any(b.startswith("WHFI") and b.endswith("_PLUS") for b in present):
        return "all merged"
    if any(b.startswith("WHFI") for b in present):
        return "WH+FI merged"
    if any(b.endswith("_PLUS") for b in present) and "N" not in present:
        return "national dropped"
    if {"N", "WH", "FI"} <= present:
        return "three channels"
    return "partial"


def state_patterns(plan: dict) -> dict:
    """`{state: pattern}` from `plan.json`'s per-state slot shares."""
    bundle_of = {s["id"]: s["bundle"] for s in plan.get("slots", []) if s.get("used")}
    out = {}
    for state, entry in plan.get("per_state", {}).items():
        present = {bundle_of[k] for k, v in entry.items()
                   if k in bundle_of and float(v) > 0.0}
        out[state] = classify_state(present)
    return out


def wholesaler_counts(plan: dict) -> dict:
    """`{state: n}`, the number of used slots (any bundle) with a positive share of that state
    in `plan.json`'s `per_state`, the same reading `state_patterns` takes of the same table,
    counting slots rather than collapsing them to a pattern."""
    used = {s["id"] for s in plan.get("slots", []) if s.get("used")}
    return {state: sum(1 for k, v in entry.items() if k in used and float(v) > 0.0)
            for state, entry in plan.get("per_state", {}).items()}


def kappa_of(params: dict, given: float | None) -> float | None:
    """Descaled mass -> currency, if anything on disk carries it.

    `--kappa` first, then `params.json`, then the instance's own meta, which the descaled
    instances do not carry (`scale_stripped`), so this normally comes back `None` and every
    mass on the figure is in descaled units.
    """
    if given is not None:
        return given
    for key in ("kappa", "kappa_value"):
        if isinstance(params.get(key), (int, float)):
            return float(params[key])
    path = params.get("instance")
    if not path or not os.path.exists(path):
        return None
    try:
        import gzip
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            meta = json.load(fh).get("meta", {})
    except Exception:
        return None
    return float(meta["kappa"]) if isinstance(meta.get("kappa"), (int, float)) else None


# ------------------------------------------------------------------ geometry, cached
def _cache_key(mapping: dict) -> str:
    """A pickle's key: what it was built from, the gazetteer vintage included.

    The vintage belongs in every key, not only the tessellation's (trap 22): the points move
    between vintages, so geometry built on the 2025 points is not the same shape as one built on
    2020's, and a key that omitted it would serve the stale pickle.
    """
    h = hashlib.sha1()
    for z in sorted(mapping):
        h.update(f"{z}:{mapping[z]}\n".encode())
    h.update(f"|gaz{geo.GAZ_VINTAGE}".encode())
    return h.hexdigest()


def _read_cache(path: str, key: str):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as fh:
            blob = pickle.load(fh)
    except Exception:
        return None                                # a stale or truncated pickle is not an error
    return blob["polys"] if blob.get("key") == key else None


def _write_cache(path: str, key: str, polys: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        pickle.dump({"key": key, "polys": polys}, fh, protocol=4)


def ordered_bundles(present) -> list:
    """The bundles present, in the fixed reading order; an unknown bundle sorts last by name."""
    known = [b for b in BUNDLE_ORDER if b in present]
    other = sorted(b for b in present if b not in BUNDLE_ORDER)
    return known + other


def bundle_rows(bundle: str, run: dict, xy: dict) -> list:
    """Geometry rows for one bundle: one per zip a district of it holds, `opportunity` the sum
    of `M_cell` over that zip's rows of this bundle (`mass_by_bundle`)."""
    mapping = run["zips_by_bundle"].get(bundle, {})
    mass = run["mass_by_bundle"].get(bundle, {})
    out = []
    for z, d in sorted(mapping.items()):
        pt = xy.get(z)
        x, y = pt if pt else (None, None)
        out.append(dict(zip=z, state=run["zip_state"].get(z, ""), district=d, x=x, y=y,
                        opportunity=mass.get(z, 0.0)))
    return out


def bundle_geom(bundle: str, rows: list, states_gdf, zcta_polys: dict, cells_source: str,
               cache_dir: str, use_cache: bool = True,
               simplify: float = geom_export.SIMPLIFY) -> dict:
    """One bundle's `geom_export` payload, pickled under `cache_dir/<bundle>_geom.pkl`, keyed
    on that bundle's own zip-to-district mapping."""
    mapping = {r["zip"]: r["district"] for r in rows}
    path = os.path.join(cache_dir, f"{bundle}_geom.pkl")
    key = _cache_key(mapping)
    hit = _read_cache(path, key) if use_cache else None
    if hit is not None:
        return hit
    payload = geom_export.export(rows, states_gdf, zcta_polys, cells_source, simplify)
    _write_cache(path, key, payload)
    return payload


def bundle_split_states(bundle: str, run: dict) -> set:
    """States where more than one district of `bundle` holds a zip."""
    held: dict[str, set] = {}
    for z, d in run["zips_by_bundle"].get(bundle, {}).items():
        held.setdefault(run["zip_state"].get(z, ""), set()).add(d)
    return {s for s, ds in held.items() if len(ds) > 1}


def bundle_strip(bundle: str, run: dict, meta: dict, kappa) -> str:
    """The strip under a bundle map: how many districts, how big, how split, how staffed."""
    districts = sorted(set(run["zips_by_bundle"].get(bundle, {}).values()))
    n_split = len(bundle_split_states(bundle, run))
    masses = [float(meta[d]["mass"]) for d in districts if d in meta and meta[d].get("mass")]
    unit = "" if kappa is None else "$"
    scale = 1.0 if kappa is None else kappa
    span = (f"mass {unit}{min(masses) * scale:,.0f} to {unit}{max(masses) * scale:,.0f}"
            if masses else "mass n/a")
    staffed = sum(1 for d in districts if (meta.get(d) or {}).get("staffed") == "1")
    return (f"{len(districts)} districts  ·  {span}  ·  {n_split} split states  ·  "
            f"{staffed} staffed")


def states_of(row: dict) -> list:
    """`[(state, share)]` from a `districts.csv` row's `states` column, `AZ:0.78,CO:1`."""
    out = []
    for part in (row.get("states") or "").split(","):
        if ":" not in part:
            continue
        st, share = part.split(":", 1)
        out.append((st.strip(), float(share)))
    return out


def states_text(row: dict) -> str:
    """The states a district holds, in the reader's words: `AZ 78 %, CO, NM`."""
    return ", ".join(st if sh >= 0.995 else f"{st} {100 * sh:.0f} %" for st, sh in states_of(row))


# ------------------------------------------------------------------ drawing
def _fill(ax, geom, **kw) -> None:
    from matplotlib.patches import PathPatch
    for path in us_maps._poly_paths(geom):
        ax.add_patch(PathPatch(path, **kw))


def _outline(ax, geom, *, zorder=3.0, **style):
    from matplotlib.collections import LineCollection
    segs = us_maps._lines_of(geom.boundary)
    if not segs:
        return None
    lc = LineCollection(segs, zorder=zorder, capstyle="round", joinstyle="round",
                        colors=style.get("color"), linewidths=style.get("linewidth", 1.0),
                        linestyles=style.get("linestyle", "-"))
    ax.add_collection(lc)
    return lc


def _state_codes(ax, states: dict, *, fontsize: float, zorder: float = 2.6,
                 second: dict | None = None) -> None:
    """Two-letter codes on every state big enough to hold one, at its largest part's
    representative point, in the dark label grey with no box so the fill shows through.

    `second`, when given, is a `{code: value}` printed as a second line under the code, same
    size (the structure map's wholesaler count; "0" for a state absent from it)."""
    for code, geom in states.items():
        part = us_maps._largest_part(geom)
        if part.area < STATE_CODE_MIN_AREA:
            continue
        p = part.representative_point()
        text = code if second is None else f"{code}\n{second.get(code, 0)}"
        ax.text(p.x, p.y, text, fontsize=fontsize, color=us_maps.LABEL_TEXT, ha="center",
                va="center", zorder=zorder, alpha=0.85, linespacing=1.0)


def _frame(ax, bounds, pad=0.015) -> None:
    x0, y0, x1, y1 = bounds
    mx, my = pad * (x1 - x0), pad * (y1 - y0)
    ax.set_xlim(x0 - mx, x1 + mx)
    ax.set_ylim(y0 - my, y1 + my)
    ax.set_aspect("equal")
    ax.set_axis_off()


def _label(district: str, meta: dict) -> str:
    """The drawn label: the district id (`display_id`), the wholesaler under it when known."""
    wh = (meta.get(district) or {}).get("wholesaler") or ""
    shown = display_id(district)
    return f"{shown}\n{wh}" if wh else shown


# ------------------------------------------------------------------ a bundle map, the app's own look
def _ring_path(ring: list):
    from matplotlib.path import Path
    codes = [Path.MOVETO] + [Path.LINETO] * (len(ring) - 1)
    return Path(ring, codes)


def _compound_path(rings: list):
    """One `matplotlib.path.Path` over several rings (a multi-part polygon, or holes folded in
    alongside exteriors), or `None` when there is nothing to draw."""
    from matplotlib.path import Path
    paths = [_ring_path(r) for r in rings if len(r) >= 3]
    return Path.make_compound_path(*paths) if paths else None


def _fill_rings(ax, rings: list, **kw) -> None:
    from matplotlib.patches import PathPatch
    path = _compound_path(rings)
    if path is not None:
        ax.add_patch(PathPatch(path, **kw))


def _stroke_rings(ax, rings: list, *, color, linewidth, zorder=3.0) -> None:
    from matplotlib.collections import LineCollection
    segs = [np.asarray(r, dtype=float) for r in rings if len(r) >= 2]
    if not segs:
        return
    ax.add_collection(LineCollection(segs, colors=color, linewidths=linewidth,
                                     capstyle="round", joinstyle="round", zorder=zorder))


def _payload_state_labels(ax, states: dict, *, fontsize=7, zorder=3.0) -> None:
    """State codes at the app's own label points (`payload["states"][code]["label"]`), exactly
    as `app/mapfig.py::figure` draws its state handles."""
    for code, info in states.items():
        point = info.get("label")
        if not point:
            continue
        ax.text(point[0], point[1], code, fontsize=fontsize, color=us_maps.TEXT, ha="center",
                va="center", zorder=zorder, alpha=0.85)


def _reach_polygon(info: dict):
    """A shapely (Multi)Polygon from a `district_reach` entry's rings, for label placement
    only; the reach layer never carries holes (`geom_export`'s own docstring)."""
    import shapely
    parts = [shapely.Polygon(r) for r in info.get("rings", []) if len(r) >= 4]
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else shapely.MultiPolygon(parts)


def draw_bundle_map(fig, ax, bundle: str, payload: dict, meta: dict, run: dict, kappa,
                    land=None) -> str:
    """One bundle's map: the app's reach layer only (2026-09-11), state outlines, each
    district's reach filled solid in its own hue and outlined, state codes, and a label per
    district.  No zip geometry: no ZCTA cells, no opportunity shading, no district ZCTA-union
    outline.  Sets the panel's title and returns the strip drawn under it."""
    states = payload.get("states", {})
    districts = payload.get("districts", {})
    reach = payload.get("district_reach", {})
    colour_of = {d: info.get("color", "#888888") for d, info in districts.items()}

    for info in states.values():                                       # 1. state outlines
        _stroke_rings(ax, info["rings"], color=STATE_OUTLINE_COLOR, linewidth=STATE_OUTLINE_W,
                     zorder=1.0)

    for d, info in sorted(reach.items()):                               # 2. district reach fill
        colour = colour_of.get(d, info.get("color", "#888888"))
        _fill_rings(ax, info["rings"], facecolor=colour, edgecolor=colour, linewidth=0.3,
                   alpha=REACH_FILL_ALPHA, zorder=1.5)

    for d, info in sorted(reach.items()):                               # 3. reach outline
        colour = colour_of.get(d, info.get("color", "#888888"))
        _stroke_rings(ax, info["rings"], color=colour, linewidth=REACH_OUTLINE_W, zorder=2.8)

    _payload_state_labels(ax, states)                                   # 4. state codes

    polys = {d: p for d, info in reach.items() for p in [_reach_polygon(info)] if p is not None}
    if polys:                                                           # 5. district labels
        labels = {_label(d, meta): p for d, p in polys.items()}
        anchors = {name: (us_maps._largest_part(g).representative_point().x,
                          us_maps._largest_part(g).representative_point().y)
                  for name, g in labels.items()}
        footprint = {name: us_maps._largest_part(g).area for name, g in labels.items()}
        us_maps._place_labels(fig, ax, sorted(labels), anchors, footprint, fontsize=7.2,
                              avoid_polys=labels, land=land, min_ratio=LABEL_ROOM,
                              leader_radii=LEADER_RADII)

    ax.set_title(bundle_title(bundle), color=us_maps.TEXT, fontsize=13, fontweight="bold", pad=6)
    return bundle_strip(bundle, run, meta, kappa)


# ------------------------------------------------------------------ the structure map
def structure_panel(ax, run: dict, states: dict, wholesalers: dict | None = None) -> None:
    """The structure map: a fill per state pattern, the state's code and wholesaler count on
    it, a hatch where the state is split between districts of some channel.

    No district borders here: an earlier version drew each channel's cuts over this map in its
    own line style, and where three channels share a state line, which is most of them, the
    three lines read as one smear.  The bundle maps carry the borders.
    """
    from matplotlib.patches import Patch
    import matplotlib

    matplotlib.rcParams["hatch.linewidth"] = 0.5
    counts = {p: 0 for p in PATTERNS}
    split_any = set().union(*run["splits"].values()) if run["splits"] else set()
    for code, geom in states.items():
        pattern = run["patterns"].get(code, "unserved")
        counts[pattern] = counts.get(pattern, 0) + 1
        _fill(ax, geom, facecolor=PATTERN_FILL[pattern], edgecolor="none", zorder=1.0)
        if code in split_any:
            _fill(ax, geom, facecolor="none", edgecolor=SPLIT_HATCH, hatch="///",
                  linewidth=0.0, zorder=1.4)
    for geom in states.values():
        _outline(ax, geom, color="#6f6f6f", linewidth=0.7, zorder=2.0)
    _state_codes(ax, states, fontsize=8.5, second=wholesalers)

    handles = [Patch(facecolor=PATTERN_FILL[p], edgecolor="#8a8a8a",
                     label=f"{PATTERN_TEXT[p]}  ({counts.get(p, 0)})")
               for p in PATTERNS if counts.get(p, 0)]
    handles.append(Patch(facecolor="white", edgecolor=SPLIT_HATCH, hatch="///",
                         label=f"split between districts  ({len(split_any)})"))
    legend = ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, 0.0),
                       frameon=False, fontsize=9.5, handlelength=1.9, title="State pattern",
                       title_fontproperties=dict(weight="bold", size=10))
    legend._legend_box.align = "left"


def footer_line(run: dict, staffing: dict, kappa) -> str:
    n_districts = len({d for c in BUSINESS for d in run["districts"][c]})
    reps = len(staffing.get("reps", []))
    idle = len(staffing.get("unmatched_reps", []))
    unit = "" if kappa is None else "$"
    scale = 1.0 if kappa is None else kappa
    residual = "  ".join(f"{c} {unit}{run['residual'][c] * scale:,.0f}" for c in BUSINESS)
    return (f"{n_districts} districts  ·  {reps - idle} of {reps} reps staffed, {idle} idle  ·  "
            f"unheld mass by channel:  {residual}")


def wholesaler_count(meta: dict) -> int:
    """The number of distinct wholesalers staffing the plan: the non-empty `wholesaler` values
    `districts.csv` itself carries, one row per district."""
    return len({row["wholesaler"] for row in meta.values() if row.get("wholesaler")})


def title_line(tag: str, params: dict, n_wholesalers: int) -> str:
    def cap(key):
        v = params.get(key)
        return "none" if v is None else (f"{v:g}" if isinstance(v, (int, float)) else str(v))
    return (f"{tag}  ·  {params.get('route', '?')} route  ·  band "
            f"{params.get('band_lo', 0):.2f}-{params.get('band_hi', 0):.2f}  ·  dist_max "
            f"{cap('dist_max')}  ·  n_max {cap('n_max')}  ·  {n_wholesalers} wholesalers")


# ------------------------------------------------------------------ the figure
def summary(run_dir: str, geo_cache: str, *, dpi: int = DPI,
            simplify: float = geom_export.SIMPLIFY, use_cache: bool = True,
            kappa: float | None = None, report=None) -> list:
    """Write `<run_dir>/maps/summary.png` and `.svg`; return the paths written."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    say = report or (lambda _s: None)
    run = load_assignment(os.path.join(run_dir, "assignment.csv"))
    meta = district_meta(os.path.join(run_dir, "districts.csv"))
    with open(os.path.join(run_dir, "plan.json"), encoding="utf-8") as fh:
        plan = json.load(fh)
    with open(os.path.join(run_dir, "params.json"), encoding="utf-8") as fh:
        params = json.load(fh)
    staffing = {}
    if os.path.exists(os.path.join(run_dir, "staffing.json")):
        with open(os.path.join(run_dir, "staffing.json"), encoding="utf-8") as fh:
            staffing = json.load(fh)
    run["patterns"] = state_patterns(plan)
    wholesalers = wholesaler_counts(plan)
    kappa = kappa_of(params, kappa)

    gdf = geo.states_outline(geo_cache)
    states = dict(zip(gdf["STUSPS"].astype(str), gdf.geometry))
    bounds = (min(g.bounds[0] for g in states.values()),
              min(g.bounds[1] for g in states.values()),
              max(g.bounds[2] for g in states.values()),
              max(g.bounds[3] for g in states.values()))
    land = us_maps.land_union(gdf)

    cache_dir = os.path.join(run_dir, "maps", "cache")
    every = sorted({z for m in run["zips_by_bundle"].values() for z in m})
    xy, missing = run_draw.coordinates(every, geo_cache)
    if missing:
        say(f"summary: {len(missing)} zip(s) with no gazetteer point, drawn nowhere: "
            f"{', '.join(missing[:8])}")
    zcta_polys = geo.zcta_polygons(every)
    missing_zcta = {z for z in every if z not in zcta_polys}
    if missing_zcta:
        say(f"summary: {len(missing_zcta)} zip(s) with no ZCTA polygon, dropped from the "
            f"geometry: {', '.join(sorted(missing_zcta)[:8])}")
    cells_source = f"{os.path.basename(geo.ZCTA_SHP)} simplify={geom_export.CELLS_SIMPLIFY:g}m"

    bundles, payloads = [], {}
    for b in ordered_bundles([bd for bd, m in run["zips_by_bundle"].items() if m]):
        rows = [r for r in bundle_rows(b, run, xy) if r["zip"] not in missing_zcta]
        if len(rows) < 2:
            say(f"summary: bundle {b} has fewer than 2 placed zip(s), skipped")
            continue
        bundles.append(b)
        payloads[b] = bundle_geom(b, rows, gdf, zcta_polys, cells_source, cache_dir, use_cache,
                                  simplify)
        say(f"summary: {b} geometry ready ({len(payloads[b].get('districts', {}))} district(s))")

    n_panels = 1 + len(bundles)
    n_rows = -(-n_panels // 2)                        # ceil
    height = TITLE_IN + FOOTER_IN + n_rows * ROW_HEIGHT_IN
    fig = plt.figure(figsize=(FIG_WIDTH, height), dpi=dpi, facecolor=us_maps.BG)
    left, right = 0.015, 0.985
    grid = fig.add_gridspec(n_rows, 2, left=left, right=right,
                            top=1 - TITLE_IN / height, bottom=FOOTER_IN / height,
                            hspace=GRID_HSPACE, wspace=0.03)

    panels = [None] + bundles
    for idx, bundle in enumerate(panels):
        r, c = divmod(idx, 2)
        cell = grid[r, c]
        ax = fig.add_subplot(cell)
        _frame(ax, bounds)
        if bundle is None:
            ax.set_title("Channel structure by state", color=us_maps.TEXT, fontsize=13,
                         fontweight="bold", pad=6)
            structure_panel(ax, run, states, wholesalers)
            continue
        strip = draw_bundle_map(fig, ax, bundle, payloads[bundle], meta, run, kappa, land=land)
        box = cell.get_position(fig)
        fig.text((box.x0 + box.x1) / 2, box.y0 - 0.12 / height, strip,
                 transform=fig.transFigure, ha="center", va="top", fontsize=8.6,
                 color=us_maps.TEXT, linespacing=1.5)

    fig.suptitle(title_line(os.path.basename(os.path.abspath(run_dir)), params,
                            wholesaler_count(meta)),
                 color=us_maps.TEXT, fontsize=15, fontweight="bold",
                 y=1 - 0.25 * TITLE_IN / height)
    # the footer sits at the very bottom of the reserved band, below the last row's own strip
    # (drawn just under the grid, `box.y0 - 0.12 / height`), never sharing its line
    fig.text(0.5, 0.15 / height, footer_line(run, staffing, kappa), ha="center",
             va="bottom", fontsize=10.5, color=us_maps.TEXT)

    out_dir = os.path.join(run_dir, "maps")
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for ext in ("png", "svg"):
        path = os.path.join(out_dir, f"summary.{ext}")
        fig.savefig(path, dpi=dpi, facecolor=us_maps.BG)
        written.append(path)
    plt.close(fig)
    return written


def _main(args) -> int:
    run_dir = os.path.abspath(args.run_dir)
    written = summary(run_dir, args.geo_cache, dpi=args.dpi,
                      simplify=args.simplify, use_cache=not args.no_cache,
                      kappa=args.kappa, report=lambda s: print(s, flush=True))
    for path in written:
        print(f"wrote {path} ({os.path.getsize(path) / 1e6:.2f} MB)", flush=True)
    return 0


def main(argv=None) -> int:
    return _main(build_argparser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
