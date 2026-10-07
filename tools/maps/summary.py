"""summary.py -- the summary page of a run folder in the 2026-10-02 deck look (#120): the legacy
`plan_summary` (vendored in `tools/maps/legacy/` from tag `archive/pre-support-2026-09`) on the run
adapted to its inputs.  Ported from `runs/autonomous_2026-10-05/batch/{adapt,wrap}.py` (m5,
gitignored), which were copies of `runs/sweep/caps_2026-10-02/`'s.

    "$TD_PY" tools/maps/summary.py <work_dir> --label TEXT --zip-cache DIR [--gap-fill grey]
        --geo-cache DIR [plan_summary flags]

`adapt(run_dir, dst, fac)` writes plan_summary's inputs (`assignment.csv`, `districts.csv`,
`plan.json`, `params.json`) into `dst`.  The spec comes from `run.json`'s `spec` and the dist_max
text from its `max_dist_km`/`dist_km`; the ledger has one row per (ZCTA, fine channel) including
zero-m_rel rows (NO_CELL, DROPPED, #116): those stay in assignment.csv at M_cell 0 as territory
and never enter $ or state shares.  `fac` is $M per m_rel of each current channel.  No
wholesaler is written: reps are out of scope, and no rep or firm name reaches a page.

The CLI runs plan_summary unchanged except: IFA as a business channel, strip and footer text
without the archived staffing model, the strip comparing the mean $ per district with the looks
scorer's target (`tools/looks/score.py` TARGET, DOLLAR_BAND), the title (`title_text`) giving
`--label` (which carries render.py's ", FAILS M1"), each channel's final band (`final_bands`, #128)
and the plan's internal bands in brackets, and the channel maps' fill (`draw_channel_map`, the
owner's rulings of 2026-10-07, #128), which replaces the legacy reach layer (a Voronoi diagram
clipped to each ZIP's filed state), so the page is no longer the legacy render.  A state the
ledger holds in one district of the channel is filled whole in its colour; a state it splits is
drawn by ZCTA, each clipped to its filed state so no colour crosses a state line (the ZIP pages
draw whole ZCTAs, and M1 is judged on whole ZCTAs: the clip is display only).  A split state's
land in no ZCTA filed there (`state_cut`: land in no ZCTA, and a neighbour's ZCTA's land across
the line) takes the colour of the nearest district holding ZCTAs in that state (`nearest_gap`),
or with `--gap-fill grey` is grey.  ZCTAs are 2025 TIGER/Line ZCTA520 simplified by 250 m and
state shapes the 2025 cartographic ones (cb_2025_us_state_500k) simplified by
`STATE_SIMPLIFY_M`, read from the ZIP pages' pickles in `--zip-cache` (`zip_pages.geometry`) and
reprojected to the legacy LAEA.  Colours, labels, the structure panel and the layout stay the
legacy code's.  It runs in its own process (`tools/maps/render.py`): the legacy code's `td`
package shadows today's.
"""
import ast
import collections
import csv
import json
import os
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LEGACY = os.path.join(HERE, "legacy")
BUNDLE = {"national": "N", "WH": "WH", "FI": "FI", "WIFI": "WHFI_PLUS", "IFA": "IFA"}
CHAN = {"wells_wh": "N_WH", "national_chase": "N_FI", "wells_fi": "N_FI", "wh": "WH", "fi": "FI", "ifa": "IFA"}
UNASSIGNED = "#dcdcdc"                  # zip_pages.py's
OPEN_M = 1000.0                         # zip_pages.py's opening of land in no ZCTA
STATE_SIMPLIFY_M = 1000.0               # the state shapes: a fifth of a pixel; unsimplified, most of the SVG
STATE_LINE = "#606060"                  # zip_pages.py's dashed state lines
RASTER_FILL = True                      # the by-ZCTA fill as an image inside the SVG (62 MB as paths)
GAP_FILLS = ("grey", "nearest")         # --gap-fill: land in no ZCTA in a split state
GAP_STEP_M = 2000.0                     # nearest_gap's spacing of ZCTA boundary points
GAP_REACH_M = 5000.0                    # nearest_gap reads the ZCTAs this near the gap
GAP_SNAP_M = 10.0                       # nearest_gap snaps those points to this grid
FOOTER_GAP = {"grey": "grey: land in no ZCTA, unassigned",
              "nearest": "land in no ZCTA shaded by nearest district (exact on the ZIP pages)"}
FOOTER_CLIP = "ZCTAs drawn clipped to their filed state; M1 is judged on whole ZCTAs (ZIP pages)"


def _resolve(path: str) -> str:
    """A path a run recorded, made absolute against `$TD_REPO` when relative."""
    return path if os.path.isabs(path) else os.path.join(os.environ.get("TD_REPO", ROOT), path)


def _pct(delta: float) -> str:
    """A band δ as the percentage the pages print: 0.1 as `10`, 3.1025 as `310.2`."""
    text = f"{100 * delta:.1f}"
    return text[:-2] if text.endswith(".0") else text


def final_bands(src: str) -> dict:
    """{planning channel: final band δ} of run folder `src`: `contig.json`'s `repair_band` when the
    repair recorded one (a diagnostic band included), else `run.json`'s `final_delta` (#127's
    whole-unit maps record their band there), else the spec's `final_delta`."""
    run = json.load(open(os.path.join(src, "run.json")))
    contig = {}
    if os.path.exists(os.path.join(src, "contig.json")):
        contig = json.load(open(os.path.join(src, "contig.json"))).get("channels", {})
    out = {}
    for c, ch in run["channels"].items():
        if "repair_band" in contig.get(c, {}):
            out[c] = contig[c]["repair_band"]["delta"]
        elif ch.get("final_delta") is not None:
            out[c] = ch["final_delta"]
    if set(run["channels"]) - set(out):
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from td import spec as tdspec
        spec = tdspec.load(_resolve(run["spec"]))
        out.update({c: spec.channels[c].final_delta for c in run["channels"] if c not in out})
    return out


def adapt(src: str, dst: str, fac: dict) -> str:
    """Write plan_summary's inputs for run folder `src` into `dst` (module doc); a one-line report."""
    os.makedirs(dst, exist_ok=True)
    led = list(csv.DictReader(open(src + "/ledger.csv")))
    dis = list(csv.DictReader(open(src + "/districts.csv")))
    newid = {}
    for ch in BUNDLE:
        ds = sorted(r["district"] for r in dis if r["channel"] == ch)
        for i, d in enumerate(ds, 1):
            newid[d] = f"{BUNDLE[ch]}_{i:02d}"
    usd = collections.Counter(); st_mass = collections.defaultdict(collections.Counter)
    zero = 0
    with open(dst + "/assignment.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["zip", "state", "channel", "bundle", "district", "M_cell"])
        for r in led:
            ch = r["model_channel"]
            if ch not in BUNDLE:
                continue
            d = newid.get(r["district"], "")
            m = float(r["m_rel"]) * fac[r["current_channel"]]
            w.writerow([r["zip_code"], r["state"], CHAN[r["current_channel"]], BUNDLE[ch], d or "other", f"{m:.6f}"])
            if m <= 0.0:
                zero += 1
                continue
            if d:
                usd[d] += m; st_mass[d][r["state"]] += m
    with open(dst + "/districts.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["district", "bundle", "mass", "wholesaler", "staffed", "states", "dev"])
        tau = {ch: sum(float(x["drawn_mass"]) for x in dis if x["channel"] == ch) / sum(x["channel"] == ch for x in dis) for ch in BUNDLE if any(x["channel"] == ch for x in dis)}
        for r in dis:
            d = newid[r["district"]]; tot = sum(st_mass[d].values())
            w.writerow([d, BUNDLE[r["channel"]], f"{usd[d]:.1f}", "", "0",
                        ",".join(f"{s}:{v / tot:.4f}" for s, v in st_mass[d].most_common()), f"{float(r['drawn_mass']) / tau[r['channel']] - 1:.6f}"])
    per_state = collections.defaultdict(dict)
    for d, c in st_mass.items():
        for s, v in c.items():
            per_state[s][d] = v / sum(st_mass[x][s] for x in st_mass if s in st_mass[x])
    json.dump({"slots": [{"id": d, "bundle": d.rsplit("_", 1)[0], "used": True} for d in newid.values()],
               "per_state": per_state}, open(dst + "/plan.json", "w"))
    _ch = tomllib.load(open(_resolve(json.load(open(src.rstrip("/") + "/run.json"))["spec"]), "rb"))["channels"]
    _ab = {"national": "N", "WH": "WH", "FI": "FI", "WIFI": "WIFI"}
    _bands = " ".join(f"{_ab.get(c, c)} ±{100 * v['delta']:.1f}%" for c, v in _ch.items() if c != "WIFI")
    _final = final_bands(src)
    _final_text = " ".join(f"{_ab.get(c, c)} ±{_pct(_final[c])}%" for c in _ch if c in _final)
    _sizes = " ".join(f"{_ab.get(c, c)} {v['max_size']}" for c, v in _ch.items() if c != "WIFI")
    _main = next(v for c, v in _ch.items() if c != "WIFI")
    _by = collections.defaultdict(list)
    for st, km in _main.get("dist_km", {}).items():
        _by[km].append(st)
    dist_max = f"{_main['max_dist_km']}" + (" (" + "; ".join(f"{km} {' '.join(sorted(sts))}" for km, sts in sorted(_by.items(), reverse=True)) + ")" if _by else "")
    json.dump({"route": "stay", "band_lo": 0.90, "band_hi": 1.10, "dist_max": dist_max, "n_max": 6,
               "bands_text": _bands, "sizes_text": _sizes, "final_bands_text": _final_text},
              open(dst + "/params.json", "w"))
    return f"{dst} {len(newid)} districts, {zero} zero-m_rel rows kept as territory only"


def _score_constant(name):
    tree = ast.parse(open(os.path.join(ROOT, "tools", "looks", "score.py")).read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


def main(argv: list) -> int:
    """plan_summary on `argv` (module doc), `--label TEXT`, `--zip-cache DIR` and `--gap-fill`
    taken out first."""
    sys.path[:0] = [LEGACY, os.path.join(LEGACY, "tools")]
    import plan_summary as ps
    TARGET = _score_constant("TARGET")                  # $ per district, by planning channel
    DOLLAR_BAND = _score_constant("DOLLAR_BAND")
    CHANNEL_OF = {"N": "national", "WH": "WH", "FI": "FI", "WHFI_PLUS": "WIFI", "IFA": "IFA"}

    ps.BUSINESS = ps.BUSINESS + ("IFA",)
    ps.CHANNEL_BUSINESS["IFA"] = "IFA"
    ps.BUNDLE_TITLE.update({"N": "National", "WH": "WH", "FI": "FI", "WHFI_PLUS": "WIFI: national + WH + FI"})
    argv = list(argv)
    i = argv.index("--zip-cache")
    geom = zcta_geometry(argv[i + 1], ps.geo.LAEA)
    del argv[i:i + 2]
    gap_fill = "nearest"
    if "--gap-fill" in argv:
        i = argv.index("--gap-fill")
        gap_fill = argv[i + 1]
        del argv[i:i + 2]
    if gap_fill not in GAP_FILLS:
        raise SystemExit(f"--gap-fill {gap_fill!r}: one of {', '.join(GAP_FILLS)}")
    ps.draw_bundle_map = lambda fig, ax, bundle, payload, meta, run, kappa, land=None: draw_channel_map(
        ps, geom, fig, ax, bundle, payload, meta, run, kappa, land, gap_fill)

    def strip(bundle, run, meta, kappa):
        ds = sorted(set(run["zips_by_bundle"].get(bundle, {}).values()))
        m = [float(meta[d]["mass"]) for d in ds if d in meta]
        mean = sum(m) / len(m)
        t = TARGET.get(CHANNEL_OF.get(bundle, bundle))
        vs = (f"target \\${t / 1e6:,.0f}M ±{100 * DOLLAR_BAND:.0f}%, {100 * (mean * 1e6 / t - 1):+.1f}%"
              if t else "no $ target")
        dv = [float(meta[d]["dev"]) for d in ds if d in meta]
        worst = max(map(abs, dv))
        within = sum(abs(x) <= 0.10 for x in dv)
        return (f"{len(ds)} districts  ·  \\${min(m):,.0f}M to \\${max(m):,.0f}M, drawn mean \\${mean:,.0f}M ({vs})  ·  "
                f"{within}/{len(ds)} within ±10%, worst {100 * worst:.1f}%  ·  "
                f"{len(ps.bundle_split_states(bundle, run))} split states")
    ps.bundle_strip = strip
    ps.footer_line = lambda run, staffing, kappa: (
        f"{len({d for c in ps.BUSINESS for d in run['districts'][c]})} districts  ·  margin-off plan, "
        f"whole-ZIP drawing, audited  ·  $ from the channel totals  ·  {FOOTER_GAP[gap_fill]}  ·  "
        f"{FOOTER_CLIP}")
    ps.TITLE_IN = 1.35
    label = None
    if "--label" in argv:
        i = argv.index("--label")
        label = argv[i + 1]
        del argv[i:i + 2]
    ps.title_line = lambda tag, params, n: title_text(label or tag, params)
    return ps.main(argv)


def title_text(label: str, params: dict) -> str:
    """The page title: `label` as render.py gives it (its ", FAILS M1" included), each channel's
    final band and the plan's internal ones, dist_max and the state caps."""
    return (f"{label}\nfinal band {params['final_bands_text']} (plan's internal {params['bands_text']})"
            f"\ndist_max {params['dist_max']}  ·  max states/district {params['sizes_text']}")


def zcta_geometry(cache: str, laea: str) -> dict:
    """The ZIP pages' pickles in `cache` (`zip_pages.geometry`, `EPSG:5070`) for `draw_channel_map`:
    {"polys": {ZCTA: polygon} as stored, "move": a function taking a list of those to the legacy
    LAEA, "states": {USPS: shape} in LAEA simplified by `STATE_SIMPLIFY_M`, "cut": `state_cut`'s
    memo}; the ZCTAs move per state, only those of split states."""
    import numpy as np
    import pickle
    import shapely
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:5070", laea, always_xy=True)

    def move(geoms):
        return list(shapely.transform(np.asarray(geoms, dtype=object),
                                      lambda xy: np.column_stack(tr.transform(xy[:, 0], xy[:, 1]))))

    def load(name):
        with open(os.path.join(cache, name), "rb") as fh:
            return pickle.load(fh)
    states = load("states.pkl")
    return {"polys": load("zcta_polys.pkl"), "move": move,
            "states": {s: g.simplify(STATE_SIMPLIFY_M, preserve_topology=True)
                       for s, g in zip(states, move(list(states.values())))},
            "cut": {}}


def state_cut(geom: dict, state: str, zip_state: dict) -> tuple:
    """({ZCTA: its polygon clipped to `state`'s drawn shape} for each ZCTA `zip_state` files in
    `state`, the shape's land in none of them opened by `OPEN_M`): land in no ZCTA and a
    neighbour's ZCTA's land across the line alike.  Memoised in `geom["cut"]`, as every channel
    of the page reads the same."""
    import numpy as np
    import shapely
    if state not in geom["cut"]:
        shape = geom["states"][state]
        zs = sorted(z for z, s in zip_state.items() if s == state and z in geom["polys"])
        polys = np.asarray(geom["move"]([geom["polys"][z] for z in zs]) if zs else [], dtype=object)
        shapely.prepare(shape)
        out = polys.copy()
        cross = ~shapely.within(polys, shape) if len(polys) else np.zeros(0, dtype=bool)
        out[cross] = shapely.intersection(polys[cross], shape)
        gap = shapely.difference(shape, shapely.union_all(out)) if len(out) else shape
        geom["cut"][state] = (dict(zip(zs, out)), gap.buffer(-OPEN_M).buffer(OPEN_M))
    return geom["cut"][state]


def nearest_gap(gap, polys: list, districts: list, step: float = GAP_STEP_M) -> dict:
    """{district: [pieces of `gap`]}: each point of `gap` (land in no ZCTA inside one state) given to
    the district of the nearest ZCTA among `polys` (held by `districts`, in that state) within
    `GAP_REACH_M` of it, by a Voronoi diagram of their boundaries' points `step` m apart."""
    import numpy as np
    import shapely
    out = collections.defaultdict(list)
    if gap.is_empty or not polys:
        return out
    near = shapely.STRtree(polys).query(gap.buffer(GAP_REACH_M), predicate="intersects")
    near = near if len(near) else np.arange(len(polys))
    pts, lab = [], []
    for i in near:
        xy = shapely.get_coordinates(shapely.segmentize(polys[i].simplify(step / 4).boundary, step))
        pts.append(xy)
        lab += [districts[i]] * len(xy)
    pts = np.round(np.concatenate(pts) / GAP_SNAP_M) * GAP_SNAP_M   # near-twins break GEOS's Voronoi
    pts, first = np.unique(pts, axis=0, return_index=True)      # a shared edge keeps one owner
    lab = [lab[i] for i in first]
    if len(set(lab)) == 1:
        out[lab[0]].append(gap)
        return out
    cells = shapely.make_valid(shapely.get_parts(shapely.voronoi_polygons(
        shapely.multipoints(pts), extend_to=gap.envelope.buffer(step))))
    at = shapely.STRtree(cells).query(shapely.points(pts), predicate="within")
    owner = dict(zip(at[1], at[0]))                              # cell -> its point
    parts = shapely.get_parts(shapely.make_valid(gap))        # reprojected, clipped: may self-touch
    parts = parts[shapely.get_type_id(parts) == 3]              # its polygons, not stray lines
    ci, pi = shapely.STRtree(parts).query(cells, predicate="intersects")
    for c, piece in zip(ci, shapely.intersection(cells[ci], parts[pi], grid_size=1.0)):
        if not piece.is_empty and c in owner:
            out[lab[owner[c]]].append(piece)
    return out


def draw_channel_map(ps, geom: dict, fig, ax, bundle: str, payload: dict, meta: dict, run: dict, kappa,
                     land=None, gap_fill: str = "nearest") -> str:
    """One channel's map (the legacy `draw_bundle_map`'s place, module doc): a state the ledger
    holds in one district of the channel filled whole in its colour; a state it splits drawn by
    ZCTA clipped to the state (`state_cut`), its land in no ZCTA filed there in its nearest
    district's colour (`nearest_gap`; `gap_fill` "grey": grey); state lines, state codes and
    district labels as the legacy code places them.  Sets the panel's title and returns the strip."""
    from matplotlib.collections import PatchCollection
    from matplotlib.patches import PathPatch
    districts = payload.get("districts", {})
    colour_of = {d: info.get("color", "#888888") for d, info in districts.items()}
    fill_of = {d: _on_white(c, ps.REACH_FILL_ALPHA) for d, c in colour_of.items()}
    mapping = run["zips_by_bundle"].get(bundle, {})
    held = collections.defaultdict(set)
    for z, d in mapping.items():
        held[run["zip_state"][z]].add(d)
    for s, ds in sorted(held.items()):
        if len(ds) == 1 and s in geom["states"]:
            fill = fill_of.get(next(iter(ds)), "#888888")
            ax.add_patch(PathPatch(_path(geom["states"][s]), facecolor=fill, edgecolor=fill, linewidth=0.2,
                                   zorder=1.5))
    by_district = collections.defaultdict(list)
    for s in sorted(s for s, ds in held.items() if len(ds) > 1 and s in geom["states"]):
        clipped, gap = state_cut(geom, s, run["zip_state"])
        mine = [(p, mapping[z]) for z, p in sorted(clipped.items()) if z in mapping and not p.is_empty]
        for p, d in mine:
            by_district[d].append(p)
        if gap.is_empty:
            continue
        if gap_fill == "nearest" and mine:
            for d, pieces in sorted(nearest_gap(gap, *map(list, zip(*mine))).items()):
                by_district[d].extend(pieces)
        else:
            ax.add_patch(PathPatch(_path(gap), facecolor=UNASSIGNED, edgecolor="none", zorder=1.2,
                                   rasterized=RASTER_FILL))
    for d, polys in sorted(by_district.items()):
        fill = fill_of.get(d, "#888888")
        ax.add_collection(PatchCollection([PathPatch(_path(p)) for p in polys if not p.is_empty],
                                          facecolor=fill, edgecolor=fill, linewidth=0.2, zorder=1.5,
                                          rasterized=RASTER_FILL))
    for shape in geom["states"].values():
        ax.add_patch(PathPatch(_path(shape), facecolor="none", edgecolor=STATE_LINE, linewidth=0.4,
                               linestyle=(0, (4, 2)), zorder=2.0))
    ps._payload_state_labels(ax, payload.get("states", {}))
    polys = {d: p for d, info in districts.items() if d in set(mapping.values())
             for p in [ps._reach_polygon(info)] if p is not None}
    if polys:                                   # the legacy placement, on each district's ZCTA union
        um = ps.us_maps
        labels = {ps._label(d, meta): p for d, p in polys.items()}
        anchors = {name: (um._largest_part(g).representative_point().x,
                          um._largest_part(g).representative_point().y) for name, g in labels.items()}
        footprint = {name: um._largest_part(g).area for name, g in labels.items()}
        um._place_labels(fig, ax, sorted(labels), anchors, footprint, fontsize=7.2, avoid_polys=labels,
                         land=land, min_ratio=ps.LABEL_ROOM, leader_radii=ps.LEADER_RADII)
    ax.set_title(ps.bundle_title(bundle), color=ps.us_maps.TEXT, fontsize=13, fontweight="bold", pad=6)
    return ps.bundle_strip(bundle, run, meta, kappa)


def _on_white(colour: str, alpha: float) -> tuple:
    """`colour` at `alpha` over white, opaque: the legacy fill's look, with no darker seam where
    two ZCTAs' edges overlap."""
    import matplotlib.colors
    return tuple(1 - alpha * (1 - c) for c in matplotlib.colors.to_rgb(colour))


def _path(geom):
    """A matplotlib compound path of `geom`'s polygons, oriented so the nonzero rule leaves holes
    (`td/output.py`'s `_polygon_path`, which this process cannot import)."""
    import numpy as np
    import shapely
    from matplotlib.path import Path
    from shapely.geometry.polygon import orient
    parts = shapely.get_parts(shapely.get_parts(geom))         # a clip's collection holds multipolygons
    rings = [ring for part in parts if part.geom_type == "Polygon" and not part.is_empty
             for ring in (orient(part, 1.0).exterior, *orient(part, 1.0).interiors)]
    return Path.make_compound_path(*(Path(np.asarray(r.coords)[:, :2], closed=True) for r in rings))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
