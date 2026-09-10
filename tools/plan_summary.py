"""plan_summary.py: a realised `tools/full_plan.py` run -> one figure a stakeholder can read.

    .venv/bin/python3 tools/plan_summary.py battery/results/full_problem/v3_seq_warm \\
        --geo-cache /Users/ntlee/projects/td/data/geo

`tools/plan_maps.py` answers "is this district a territory or a scatter", one bundle at a time.
This answers the question above it: what does the whole plan do to the country.  One
`maps/summary.png` (and `.svg`) carrying

  * a CONUS map of the **channel structure by state**, saying which of the three business
    channels a state actually gets and by how many districts, the district borders over it, and
  * one panel per **business channel** (National, WH, FI), every district that carries that
    channel filled and labelled with its id and wholesaler.

The figure speaks in business channels, not bundles.  A bundle is how the plan was solved
(`N`, `WH`, `FI`, `WH_PLUS`, `FI_PLUS`, `WHFI`); a channel is what a customer sees.  A merged
`WHFI` district appears on both the WH and the FI panel, same colour, same id, cross-hatched; a
`FI_PLUS` district appears on the FI panel and on the National panel, diagonally hatched, because
it is the district that folded the national book in.  Zips of a channel that no district holds
are light grey, and their mass is the residual in the footer.

Geometry is the state-clipped Voronoi tessellation of the zip points, dissolved by district.
That is the layer `tools/geom_export.py` exports as `district_reach`; the real ZCTA polygons it
exports as `districts` are not used here.  `zip_cells` says why: at national scale the ZCTA
dissolve is confetti.
The tessellation and each bundle's dissolved districts are pickled under `maps/cache/`, keyed by
a hash of the zip-to-district mapping, so a rerun after an edit to the figure costs seconds and
a rerun after a new realise recomputes only what changed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from td import geo                                                        # noqa: E402
import geom_export                                                        # noqa: E402
import us_maps                                                            # noqa: E402

OTHER = "other"                 # `tools/plan_realise.py::OTHER`, the no-district pseudo-label

# The three channels the business runs.  `N_WH` and `N_FI` are the two halves of the national
# book (the wholesale side and the field side); a stakeholder reads them as one channel, so the
# figure folds them together and the National panel shows every district holding either half.
BUSINESS = ("National", "WH", "FI")
CHANNEL_BUSINESS = {"N_WH": "National", "N_FI": "National", "WH": "WH", "FI": "FI"}

PLUS = "⁺"                 # superscript plus: "FI+", the bundle that carries national too

# What a state's plan pattern is, in the order the classifier tests them.
PATTERNS = ("three channels", "WH+FI merged", "national dropped", "partial", "unserved")
PATTERN_FILL = {
    "three channels":   "#cfe0ee",
    "WH+FI merged":     "#ded2ea",
    "national dropped": "#f4dac6",
    "partial":          "#eae5c9",
    "unserved":         "#ededed",
}

# Outline styles on the structure panel, one per business channel.  A plus bundle keeps its own
# channel's colour and takes the national line weight, rather than being drawn twice (once dark
# for national, once in colour for its channel), which at this scale reads as one thick smear.
#
# `offset` is in points, and it is what makes the panel readable at all: most district borders
# are state borders, so all three channels want the same line, and whichever is drawn last hides
# the other two.  Offset by a couple of points each and a shared border reads as three parallel
# lines.  The offsets are deliberately not diagonal-symmetric, since a (1, 1) shift vanishes on
# a border that itself runs at 45 degrees.
LINE = {
    "National": dict(color="#1b1d22", linewidth=1.9, linestyle="-", offset=(0.0, 0.0)),
    "WH":       dict(color="#1f5fa8", linewidth=1.1, linestyle="-", offset=(2.0, 1.1)),
    "FI":       dict(color="#c0392b", linewidth=1.1, linestyle=(0, (3.5, 2.5)),
                     offset=(-2.0, -1.1)),
    "merged":   dict(color="#6f3d9e", linewidth=1.4, linestyle=(0, (1.0, 1.6)),
                     offset=(-2.0, 1.1)),
}
STYLE_KEYS = ("color", "linewidth", "linestyle", "offset")

HATCH = {"pure": "", "plus": "///", "merged": "xxx"}
HATCH_COLOR = (0.16, 0.16, 0.18, 0.55)

GROUND = "#f6f6f6"              # a state with no zip of this channel at all
UNSERVED = "#d8d8d8"            # a zip of this channel that no district holds
STATE_LINE = "#9d9d9d"
SPLIT_HATCH = "#a6a6a6"

FIGSIZE = (16.0, 14.0)
DPI = 110


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", help="a finished plan run, already realised")
    ap.add_argument("--geo-cache", default=geo.DEFAULT_DEST)
    ap.add_argument("--dpi", type=int, default=DPI)
    ap.add_argument("--simplify", type=float, default=geom_export.SIMPLIFY,
                    help="district ring tolerance in metres (default: geom_export's own)")
    ap.add_argument("--no-cache", action="store_true", help="dissolve again, ignoring maps/cache")
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


def load_assignment(path: str) -> dict:
    """One pass over `assignment.csv`: who holds what, per bundle and per business channel.

    A district's zip set does not depend on the channel row it was read from, so the per-bundle
    mapping dedupes; the per-channel sets do not, because a zip can be held on one half of the
    national book and dropped on the other.
    """
    zips_by_bundle: dict[str, dict] = {}
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
            zips_by_bundle.setdefault(row["bundle"], {})[row["zip"]] = name
            districts[chan].add(name)
            held_states.setdefault((chan, row["state"]), set()).add(name)
    splits = {c: {s for (ch, s), ds in held_states.items() if ch == c and len(ds) > 1}
              for c in BUSINESS}
    return dict(zips_by_bundle=zips_by_bundle, unheld=unheld, residual=residual,
                districts=districts, splits=splits, zip_state=zip_state)


def district_meta(path: str) -> dict:
    """`{district: row}` from `districts.csv`, or `{}` when the run has no such file."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8", newline="") as fh:
        return {row["district"]: row for row in csv.DictReader(fh)}


def business_of(bundle: str, meta: dict) -> tuple:
    """The business channels a bundle serves, from `districts.csv`'s own `channels` column.

    The column is the realiser's word on it; the bundle name is only the fallback, for a bundle
    that drew no district or a run written before the column existed.
    """
    for row in meta.values():
        if row.get("bundle") == bundle and row.get("channels"):
            seen = [CHANNEL_BUSINESS[c] for c in row["channels"].split()
                    if c in CHANNEL_BUSINESS]
            return tuple(c for c in BUSINESS if c in seen)
    name = bundle[:-5] if bundle.endswith("_PLUS") else bundle
    parts = ["WH", "FI"] if name.startswith("WHFI") else ([name] if name in BUSINESS else [])
    if name == "N" or bundle.endswith("_PLUS"):
        parts.append("National")
    return tuple(c for c in BUSINESS if c in parts)


def classify_state(present: set) -> str:
    """The state's plan pattern from the bundles holding a positive share of it."""
    if not present:
        return "unserved"
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
    between vintages, so a dissolved district built on the 2025 points is not the same shape as
    one built on 2020's, and a key that omitted it would serve the stale pickle.
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


def zip_cells(zips, zip_state: dict, states_gdf, geo_cache: str, cache_dir: str,
              use_cache: bool = True, report=None) -> dict:
    """`{zip: cell}`, each state tiled by its own zips: the app's `district_reach` ground.

    **Not** the real ZCTA polygons `tools/geom_export.py` dissolves into `geom.json`'s
    `districts`.  Both were tried; at national scale the ZCTA dissolve is confetti, because the
    instance holds a few thousand scattered zips and a ZCTA covers only its own populated
    ground, so a district that owns eight whole states draws as a spray of dots inside them.
    This is the same state-clipped Voronoi tessellation `geom_export` dissolves into
    `district_reach`, and it answers the question a plan-level map is asked: which ground does
    this district cover.  A district holding every zip of a state comes out as exactly that
    state's polygon, so whole-state districts need no special case.  Trap 23 applies to reading
    it: this is the contiguity model's own tessellation, not the published ZCTA boundaries.
    """
    say = report or (lambda _s: None)
    keys = sorted(zips)
    path = os.path.join(cache_dir, "cells.pkl")
    key = _cache_key({z: zip_state.get(z, "") for z in keys})
    hit = _read_cache(path, key) if use_cache else None
    if hit is not None:
        return hit
    import run_draw

    xy, missing = run_draw.coordinates(keys, geo_cache)
    if missing:
        say(f"summary: {len(missing)} zip(s) with no gazetteer point, drawn nowhere: "
            f"{', '.join(missing[:8])}")
    placed = [z for z in keys if z in xy]
    state_polys = dict(zip(states_gdf["STUSPS"].astype(str), states_gdf.geometry))
    clip = us_maps.clip_region([xy[z] for z in placed], states_gdf)
    cells = us_maps.voronoi_cells(placed, xy, clip, zip_state=zip_state,
                                  state_polys=state_polys)
    say(f"summary: {len(cells):,} cells over {len(placed):,} placed zip(s)")
    _write_cache(path, key, cells)
    return cells


def dissolve_groups(name: str, mapping: dict, cells, cache_dir: str,
                    use_cache: bool = True) -> dict:
    """`{group: (multi)polygon}` for `{zip: group}`, pickled under `cache_dir/<name>.pkl`.

    `cells` is a zero-argument callable returning `{zip: cell}`, a callable rather than the
    dict itself so a fully cached rerun never builds the tessellation at all.

    Cached unsimplified, and simplified only at draw time (`simplify_polys`), because
    `us_maps.district_borders` finds a shared border by intersecting two boundaries exactly:
    two districts simplified independently no longer share their vertices, and two thirds of
    the internal borders on the structure panel disappear.
    """
    path = os.path.join(cache_dir, f"{name}.pkl")
    key = _cache_key(mapping)
    hit = _read_cache(path, key) if use_cache else None
    if hit is not None:
        return hit
    ground = cells()
    held = {z: d for z, d in mapping.items() if z in ground}
    polys = us_maps.dissolve({z: ground[z] for z in held}, held)
    _write_cache(path, key, polys)
    return polys


def simplify_polys(polys: dict, tolerance: float) -> dict:
    """Fill geometry for the channel panels; at 2 km the boundary moves under one pixel."""
    if not tolerance:
        return polys
    return {d: us_maps._valid(g.simplify(tolerance, preserve_topology=True))
            for d, g in polys.items()}


def _lighten(color: str, t: float) -> tuple:
    from matplotlib.colors import to_rgb
    r, g, b = to_rgb(color)
    return (r + (1.0 - r) * t, g + (1.0 - g) * t, b + (1.0 - b) * t)


def district_colors(names) -> dict:
    """A fill per district, stable across panels so a merged district looks the same on both.

    `geom_export.palette` strides the hue circle, so consecutively numbered districts land far
    apart; past its 50 entries the lightness steps instead of the hue repeating exactly.
    """
    pal = geom_export.palette()
    out = {}
    for i, d in enumerate(sorted(names, key=str)):
        out[d] = _lighten(pal[i % len(pal)], 0.42 + 0.16 * ((i // len(pal)) % 3))
    return out


# ------------------------------------------------------------------ drawing
def _fill(ax, geom, **kw) -> None:
    from matplotlib.patches import PathPatch
    for path in us_maps._poly_paths(geom):
        ax.add_patch(PathPatch(path, **kw))


def _outline(ax, geom, *, halo=0.0, zorder=3.0, offset=None, **style):
    from matplotlib.collections import LineCollection
    from matplotlib.transforms import offset_copy
    import matplotlib.patheffects as pe
    segs = us_maps._lines_of(geom.boundary)
    if not segs:
        return None
    lc = LineCollection(segs, zorder=zorder, capstyle="round", joinstyle="round",
                        colors=style.get("color"), linewidths=style.get("linewidth", 1.0),
                        linestyles=style.get("linestyle", "-"))
    if offset and any(offset):
        lc.set_transform(offset_copy(ax.transData, fig=ax.figure, x=offset[0], y=offset[1],
                                     units="points"))
    if halo:
        lc.set_path_effects([pe.withStroke(linewidth=style.get("linewidth", 1.0) + halo,
                                           foreground="white")])
    ax.add_collection(lc)
    return lc


def _frame(ax, bounds, pad=0.015) -> None:
    x0, y0, x1, y1 = bounds
    mx, my = pad * (x1 - x0), pad * (y1 - y0)
    ax.set_xlim(x0 - mx, x1 + mx)
    ax.set_ylim(y0 - my, y1 + my)
    ax.set_aspect("equal")
    ax.set_axis_off()


def _label(district: str, meta: dict) -> str:
    """The drawn label: the district id, the wholesaler under it when one is known."""
    wh = (meta.get(district) or {}).get("wholesaler") or ""
    return f"{district}\n{wh}" if wh else district


def draw_rank(bundle: str) -> tuple:
    """Heaviest line first, so the thinner channels stay visible where two follow one border."""
    kind = bundle_kind(bundle)
    if kind == "pure":
        return (0, {"N": 0, "WH": 1, "FI": 2}.get(bundle, 3), bundle)
    return (1 if kind == "plus" else 2, 0, bundle)


def channel_group(channel: str, polys: dict, unheld: dict, meta: dict) -> dict:
    """`{district: polygon}` for one business channel, the unheld ground included.

    The unheld ground is in the group so that where a channel simply stops, at a state no
    district of it reaches, the panel draws that edge as a border of the channel, which is the
    whole point of a plan map that allows dropped channels.
    """
    group = {}
    for bundle, ps in polys.items():
        if channel in business_of(bundle, meta):
            group.update(ps)
    if unheld.get(channel):
        group.update(unheld[channel])
    return group


def structure_panel(ax, run: dict, polys: dict, unheld: dict, meta: dict, states: dict,
                    legend_ax) -> None:
    """The top map: a fill per state pattern, the cut lines of each business channel over it.

    Only district-vs-district borders are drawn (`us_maps.district_borders`), never a whole
    district boundary: the coastline is not a decision, and drawn three times over it swamps
    the lines that are.  A district that carries two channels therefore has its border drawn
    twice, once in each channel's colour and at that channel's offset, which is the honest
    reading: that border is both the WH cut and the national cut.  A merged district is the
    exception the eye needs help with, so its own outline goes on once in purple.
    """
    from matplotlib.collections import LineCollection
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    import matplotlib

    matplotlib.rcParams["hatch.linewidth"] = 0.45
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
        _outline(ax, geom, color=STATE_LINE, linewidth=0.55, zorder=2.0)

    x0, y0, x1, y1 = ax.get_xlim()[0], ax.get_ylim()[0], ax.get_xlim()[1], ax.get_ylim()[1]
    eps = 1e-4 * float(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5)
    rows = []
    from matplotlib.transforms import offset_copy
    for i, channel in enumerate(BUSINESS):
        group = channel_group(channel, polys, unheld, meta)
        segs = us_maps.district_borders(group, eps)
        style = LINE[channel]
        lc = LineCollection(segs, colors=style["color"], linewidths=style["linewidth"],
                            linestyles=style["linestyle"], zorder=3.0 + 0.1 * i,
                            capstyle="round", joinstyle="round")
        lc.set_transform(offset_copy(ax.transData, fig=ax.figure, x=style["offset"][0],
                                     y=style["offset"][1], units="points"))
        ax.add_collection(lc)
        rows.append(dict(style, label=channel, n=len(run["districts"][channel])))
    merged = {d: g for b, ps in polys.items() if bundle_kind(b) == "merged"
              for d, g in ps.items()}
    for geom in merged.values():
        _outline(ax, geom, halo=0.9, zorder=3.4, **{k: LINE["merged"][k] for k in STYLE_KEYS})
    if merged:
        rows.append(dict(LINE["merged"], label="WH+FI merged", n=len(merged)))

    legend_ax.set_axis_off()
    handles = [Patch(facecolor=PATTERN_FILL[p], edgecolor="#b6b6b6",
                     label=f"{p}  ({counts.get(p, 0)})") for p in PATTERNS]
    handles.append(Patch(facecolor="white", edgecolor=SPLIT_HATCH, hatch="///",
                         label=f"split between districts  ({len(split_any)})"))
    first = legend_ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 1.0),
                             frameon=False, fontsize=9, handlelength=1.9,
                             title="State pattern", title_fontproperties=dict(weight="bold",
                                                                              size=9.5))
    first._legend_box.align = "left"
    legend_ax.add_artist(first)
    lines = [Line2D([0], [0], color=r["color"], linewidth=r["linewidth"],
                    linestyle=r["linestyle"], label=f"{r['label']}  ({r['n']})")
             for r in rows]
    second = legend_ax.legend(handles=lines, loc="upper left", bbox_to_anchor=(0.0, 0.66),
                              frameon=False, fontsize=9, handlelength=2.6,
                              title="District borders, by channel", title_fontproperties=dict(
                                  weight="bold", size=9.5))
    second._legend_box.align = "left"


def channel_panel(ax, fig, channel: str, run: dict, polys: dict, states: dict, colors: dict,
                  meta: dict, unheld, kappa, land=None) -> str:
    """One business channel: every district that carries it, filled, hatched by type."""
    for geom in states.values():
        _fill(ax, geom, facecolor=GROUND, edgecolor="none", zorder=0.5)
    if unheld is not None:
        for geom in unheld.values():
            _fill(ax, geom, facecolor=UNSERVED, edgecolor="none", zorder=1.0)

    drawn, kinds = {}, {}
    for bundle in sorted(polys, key=draw_rank):
        if channel not in business_of(bundle, meta):
            continue
        kind = bundle_kind(bundle)
        for name, geom in polys[bundle].items():
            _fill(ax, geom, facecolor=colors[name], edgecolor="none", zorder=1.5)
            if HATCH[kind]:
                _fill(ax, geom, facecolor="none", edgecolor=HATCH_COLOR, hatch=HATCH[kind],
                      linewidth=0.0, zorder=1.7)
            _outline(ax, geom, color="#4a4a4a", linewidth=0.7, zorder=2.5)
            drawn[name] = geom
            kinds[name] = bundle
    for geom in states.values():
        _outline(ax, geom, color=STATE_LINE, linewidth=0.4, zorder=2.2)

    labels = {_label(d, meta): g for d, g in drawn.items()}
    anchors = {k: (us_maps._largest_part(g).representative_point().x,
                   us_maps._largest_part(g).representative_point().y)
               for k, g in labels.items()}
    footprint = {k: us_maps._largest_part(g).area for k, g in labels.items()}
    # `min_ratio` above 1: a label only stays on its district if the district is several times
    # the label box.  At 1.0 two small neighbours both keep their spot and print on top of each
    # other (WHFI_01 over FI_03 on the d600_free FI panel); above it the smaller one takes a
    # leader line instead, and `_place_labels` does check leader labels for collisions.
    us_maps._place_labels(fig, ax, sorted(labels), anchors, footprint, fontsize=5.6,
                          avoid_polys=labels, land=land, min_ratio=2.5)
    ax.set_title(channel, color=us_maps.TEXT, fontsize=13, fontweight="bold", pad=6)
    return stats_line(channel, drawn, kinds, run, meta, kappa)


def stats_line(channel: str, drawn: dict, kinds: dict, run: dict, meta: dict, kappa) -> str:
    """The strip under a channel panel: how many districts, of what kind, how big, how staffed."""
    by_kind: dict[str, int] = {}
    for name, bundle in kinds.items():
        key = "pure" if bundle_kind(bundle) == "pure" else bundle_label(bundle).split(" (")[0]
        by_kind[key] = by_kind.get(key, 0) + 1
    mix = ", ".join(f"{n} {k}" for k, n in sorted(by_kind.items(), key=lambda kv: -kv[1]))
    masses = [float(meta[d]["mass"]) for d in drawn if d in meta and meta[d].get("mass")]
    unit = "" if kappa is None else "$"
    scale = 1.0 if kappa is None else kappa
    span = (f"mass {unit}{min(masses) * scale:,.0f} to {unit}{max(masses) * scale:,.0f}"
            if masses else "mass n/a")
    staffed = sum(1 for d in drawn if (meta.get(d) or {}).get("staffed") == "1")
    return (f"{len(drawn)} districts: {mix}\n{span}  ·  "
            f"{len(run['splits'][channel])} split states  ·  {staffed} staffed")


def footer_line(run: dict, staffing: dict, kappa) -> str:
    n_districts = len({d for c in BUSINESS for d in run["districts"][c]})
    reps = len(staffing.get("reps", []))
    idle = len(staffing.get("unmatched_reps", []))
    unit = "" if kappa is None else "$"
    scale = 1.0 if kappa is None else kappa
    residual = "  ".join(f"{c} {unit}{run['residual'][c] * scale:,.0f}" for c in BUSINESS)
    return (f"{n_districts} districts  ·  {reps - idle} of {reps} reps staffed, {idle} idle  ·  "
            f"unheld mass by channel:  {residual}")


def title_line(tag: str, params: dict) -> str:
    def cap(key):
        v = params.get(key)
        return "none" if v is None else (f"{v:g}" if isinstance(v, (int, float)) else str(v))
    return (f"{tag}  ·  {params.get('route', '?')} route  ·  band "
            f"{params.get('band_lo', 0):.2f}-{params.get('band_hi', 0):.2f}  ·  dist_max "
            f"{cap('dist_max')}  ·  n_max {cap('n_max')}")


# ------------------------------------------------------------------ the figure
def summary(run_dir: str, geo_cache: str, *, dpi: int = DPI,
            simplify: float = geom_export.SIMPLIFY, use_cache: bool = True,
            kappa: float | None = None, report=None) -> list:
    """Write `<run_dir>/maps/summary.png` and `.svg`; return the paths written."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

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
    kappa = kappa_of(params, kappa)

    gdf = geo.states_outline(geo_cache)
    states = dict(zip(gdf["STUSPS"].astype(str), gdf.geometry))
    bounds = (min(g.bounds[0] for g in states.values()),
              min(g.bounds[1] for g in states.values()),
              max(g.bounds[2] for g in states.values()),
              max(g.bounds[3] for g in states.values()))

    cache_dir = os.path.join(run_dir, "maps", "cache")
    every = sorted({z for m in run["zips_by_bundle"].values() for z in m}
                   | {z for s in run["unheld"].values() for z in s})
    ground: dict = {}

    def cells():
        if not ground:
            ground.update(zip_cells(every, run["zip_state"], gdf, geo_cache, cache_dir,
                                    use_cache, say))
        return ground

    polys = {b: dissolve_groups(f"{b}_districts", m, cells, cache_dir, use_cache)
             for b, m in sorted(run["zips_by_bundle"].items())}
    unheld = {c: dissolve_groups(f"unheld_{c}", {z: OTHER for z in sorted(run["unheld"][c])},
                                 cells, cache_dir, use_cache)
              for c in BUSINESS if run["unheld"][c]}
    drawn = {b: simplify_polys(p, simplify) for b, p in polys.items()}
    shown = {c: simplify_polys(p, simplify) for c, p in unheld.items()}
    colors = district_colors({d for m in polys.values() for d in m})

    fig = plt.figure(figsize=FIGSIZE, dpi=dpi, facecolor=us_maps.BG)
    left, right, low = 0.015, 0.985, 0.105
    grid = fig.add_gridspec(2, 1, height_ratios=[2.4, 1.0], left=left, right=right,
                            top=0.945, bottom=low, hspace=0.05)
    top = grid[0].subgridspec(1, 2, width_ratios=[4.4, 1.0], wspace=0.0)
    ax_map = fig.add_subplot(top[0, 0])
    ax_key = fig.add_subplot(top[0, 1])
    _frame(ax_map, bounds)
    ax_map.set_title("Channel structure by state", color=us_maps.TEXT, fontsize=14,
                     fontweight="bold", pad=8)
    structure_panel(ax_map, run, polys, unheld, meta, states, ax_key)

    bottom = grid[1].subgridspec(1, len(BUSINESS), wspace=0.02)
    for i, channel in enumerate(BUSINESS):
        ax = fig.add_subplot(bottom[0, i])
        _frame(ax, bounds)
        strip = channel_panel(ax, fig, channel, run, drawn, states, colors, meta,
                              shown.get(channel), kappa, land=us_maps.land_union(gdf))
        # in figure coordinates, not the axes': `_place_labels` may widen a panel's limits for
        # a leader label, which under `aspect="equal"` moves that axes' box and would leave the
        # three strips at three heights
        ax.text(left + (i + 0.5) * (right - left) / len(BUSINESS), low - 0.008, strip,
                transform=fig.transFigure, ha="center", va="top", fontsize=8.2,
                color=us_maps.TEXT, linespacing=1.5)

    kinds = {bundle_kind(b) for b in drawn}
    keys = [Patch(facecolor="#e3e3e3", edgecolor="#4a4a4a", linewidth=0.7,
                  label="one district, one channel")]
    if "plus" in kinds:
        keys.append(Patch(facecolor="#e3e3e3", edgecolor=HATCH_COLOR, hatch="///",
                          label=f"{PLUS} district: carries the national book too"))
    if "merged" in kinds:
        keys.append(Patch(facecolor="#e3e3e3", edgecolor=HATCH_COLOR, hatch="xxx",
                          label="merged district: one rep for WH and FI"))
    if shown:
        keys.append(Patch(facecolor=UNSERVED, edgecolor="none", label="held by no district"))
    fig.legend(handles=keys, loc="lower center", bbox_to_anchor=(0.5, 0.036), ncol=len(keys),
               frameon=False, fontsize=9.5, handlelength=1.8)

    fig.suptitle(title_line(os.path.basename(os.path.abspath(run_dir)), params),
                 color=us_maps.TEXT, fontsize=15, fontweight="bold", y=0.986)
    fig.text(0.5, 0.012, footer_line(run, staffing, kappa), ha="center", va="bottom",
             fontsize=10, color=us_maps.TEXT)

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
