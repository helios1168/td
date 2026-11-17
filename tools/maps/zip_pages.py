"""zip_pages.py -- the ZIP-level pages of a run folder in the required look: one page per planning
channel (#120; ported from `runs/autonomous_2026-10-05/batch_border/zip_pages.py`, m5, gitignored).

    "$TD_PY" tools/maps/zip_pages.py <run_dir> <label> <out_dir> [--corridor] [--fac PATH]
        [--cache DIR] [--style exec] [--title TEXT] [--no-footer] [--palette clean]

`tools/maps/render.py` calls `main`; this CLI is the same.  The pages are the primary view of a
rendered run (owner, 2026-10-13): `zip_summary.png`, then one `zip_<channel>.png` per planning
channel, and `zip_pages.pdf` holding them in that order, all in `out_dir`; `main` returns those
paths, the PDF last.  A channel page's title is `<label>  ·  <channel>: K districts`.

The summary page (`summary_page`, title `<label>  ·  territories per state`) is a CONUS state
map: each state filled by how many districts, across all planning channels, own a ZCTA filed
there (the ledger's `state`; `state_territories`), on a light ramp of 1 to `COUNT_BINS`+; its
label the state and each channel's count there (`N 2 · W 3`, `ABBR`), a count of 2 or more in
bold.  A state is split in a channel when 2+ of its districts own ZCTAs there (`split_states`);
a split state has a thick dark outline, and the caption lists each channel's split states.  The
Northeast inset (`NORTHEAST`) carries the small states; a state label that does not fit inside
its state gets a leader line, and on the main map is left to the inset when the state is in it.

`--style exec` (default off; the default output is unchanged) also writes `zip_exec_<channel>.png`
per channel (`exec_page`), a layperson's map after the Census regions map: each district dissolved
to one flat polygon in one of `EXEC_PALETTE`'s muted colours (no two neighbours alike), land in no
ZCTA that lies against districts joined to them (`exec_fill_gaps`), thin district outlines, bold
state borders, `N-08 · $1.2B` at the district's area centroid, the biggest metros lightly, a small
legend; no pieces, necks or ZIP texture.  In `zip_pages.pdf` these pages follow the summary.

Three opt-in flags restyle the owner pages (each default leaves the output unchanged): `--title TEXT`
is the whole suptitle of every page (summary, channel, exec); `--no-footer` drops every bottom
`fig.text` caption (legends, inset titles and in-map labels stay) and trims the empty band;
`--palette clean` calms the colours of the summary and channel pages only: a Blues ramp from a pale
blue-grey instead of YlGnBu's yellow, the split outline in the ramp's dark navy at `CLEAN_SPLIT_LW`,
drawn on the state with islands dropped, inlets closed and the line simplified by `CLEAN_SIMPLIFY_M`
(`clean_outline`) so coasts do not blob, and on the
channel page `CLEAN_PALETTE` assigned by `colouring_far` (no alike colour within `CLEAN_NEAR_M`
when avoidable, alike = Lab distance under `CLEAN_ALIKE`).

Every page labels the major metros (`metros`): the `METROS` CBSA Metro Areas with the most
opportunity $ in the run's ledger (owned rows, through the ledger's `cbsa`), each at its CBSA's
gazetteer internal point and named by the first principal city of its title (two for `TWIN`),
from the tracked `reference/2025/areas.csv.gz`.  `place_labels` sets a dot and a label in rank
order, trying offsets around the dot, then further ones with a leader line, and drops a metro
whose label would overlap a placed label, dot or district number, so dense areas thin out; the
insets, at a larger scale, carry more.

Every ZCTA a district owns in the ledger (zero-m_rel territory included) is filled in its
district's colour, drawn with `zcta_polygons` (td/output.py) and `look.polygon_path` (a copy of its
`_polygon_path`).  CONUS
land in no ZCTA is drawn light grey as unassigned land and joins no district (owner ruling).  The
land is the 2025 cartographic-boundary states (cb_2025_us_state_500k) less the union of every
CONUS ZCTA, opened by `OPEN_M` so the slivers of a 250 m simplification and a generalised
shoreline do not read as land.  Insets: the NYC metro, and with --corridor BOS-WAS.

The look itself lives in `tools/maps/look.py`, which imports nothing from `td` (so a Snowflake
notebook can use it): every style constant (`PALETTE`, `CLEAN_*`, `EXEC_*`, `NYC`, `NORTHEAST`, ...),
the helpers (`neighbours`, `colouring`, `colouring_far`, `borders`, `place_labels`, `label_metros`,
`exec_fill_gaps`, `count_fill`, `clean_outline`, `no_zcta_land`, `bbox`, `top_metros`,
`state_territories`, ...) and the page drawers `draw`, `draw_states`, `page`, `exec_page` and
`summary_page`.  This file re-exports them, so `zip_pages.X` is unchanged, and keeps what reads
the run folder, ledger, caches, `td.geo`, `td.output` and `tools/looks/score.py`: `read_areas`,
`page`, `exec_page` and `summary_page` here call `look`'s with the areas path, the channel's $
target and band and the run path relative to `$TD_REPO`; then `metros`, `geometry`, the CLI, `main`.

The inputs that are not tracked are read from `$TD_REPO` or flags, never copied into the repo:
`--cache` holds `cb_2025_us_state_500k.zip` and the pickled ZCTA polygons, state shapes and
no-ZCTA land (built from `$TD_REPO/data/public` on a miss); `--fac` the $ per m_rel of each
current channel (`tables.json`'s `fac`, from the owner's channel totals).  The run path in the
footer is relative to `$TD_REPO`.
"""
from __future__ import annotations

import argparse
import collections
import csv
import importlib.util
import json
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
TD_REPO = os.environ.get("TD_REPO", ROOT)

import matplotlib                                   # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                     # noqa: E402
import shapely                                      # noqa: E402
from pyproj import Transformer                      # noqa: E402

from td import geo                                  # noqa: E402
from td.output import zcta_polygons                 # noqa: E402


def _load_look():
    """`look.py` beside this file as module `maps_look` (this file may itself be loaded by path)."""
    if "maps_look" not in sys.modules:
        spec = importlib.util.spec_from_file_location("maps_look", os.path.join(HERE, "look.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["maps_look"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["maps_look"]


look = _load_look()
assert look.CRS == geo.CRS, (look.CRS, geo.CRS)
from maps_look import (  # noqa: E402,F401  (re-exported: `zip_pages.X` resolves as before)
    OPEN_M, UNASSIGNED, UNASSIGNED_TEXT, OTHER_FILL, OTHER_EDGE, NYC, CORRIDOR, NORTHEAST, CHANNELS, ABBR,
    NAME, COUNT_BINS, SPLIT_EDGE, CLEAN_CMAP, CLEAN_RAMP, CLEAN_BEND, CLEAN_SPLIT_EDGE, CLEAN_SPLIT_LW,
    CLEAN_SIMPLIFY_M, CLEAN_ISLAND_M2, CLEAN_NEAR_M, CLEAN_ALIKE, METROS, TWIN, PALETTE, CLEAN_PALETTE,
    EXEC_PALETTE, EXEC_LAND, EXEC_STATE_LINE, EXEC_METROS, EXEC_GAP, EXEC_HOLE_M2, METRO_HANDLE, NEAR, LEADER,
    FIG_H, FOOTER_IN, no_zcta_land, bbox, neighbours, colouring, lab, colouring_far, borders,
    state_territories, split_states, metro_name, top_metros, place_labels, label_metros, frame, draw,
    exec_label_point, exec_text, exec_fill_gaps, count_fill, state_text, clean_outline, draw_states,
    polygon_path,
)

CACHE = os.path.join(TD_REPO, "runs", "autonomous_2026-10-05", "batch", "geo")
FAC_JSON = os.path.join(TD_REPO, "runs", "sweep", "grid_2026-10-01", "tables.json")
AREAS = os.path.join(geo.REFERENCE_DIR, "areas.csv.gz")
SCORE = os.path.join(ROOT, "tools", "looks", "score.py")


def score_constant(name):
    import ast
    for node in ast.parse(open(SCORE).read()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


TARGET, DOLLAR_BAND, DOLLARS = (score_constant(n) for n in ("TARGET", "DOLLAR_BAND", "DOLLARS"))


def read_fac(path: str = FAC_JSON) -> dict:
    """$M per m_rel of each current channel."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["fac"]


def cached(name, build, cache: str = CACHE):
    path = os.path.join(cache, name)
    if os.path.exists(path):
        with open(path, "rb") as fh:
            return pickle.load(fh)
    out = build()
    with open(path, "wb") as fh:
        pickle.dump(out, fh, protocol=4)
    return out


def all_zctas() -> list:
    import gzip
    with gzip.open(os.path.join(geo.REFERENCE_DIR, "zcta_reference.csv.gz"), "rt") as fh:
        return sorted({r["zcta"] for r in csv.DictReader(fh) if r["graph_vertex"] == "1"})


def states(cache: str = CACHE) -> dict:
    st = geo._read(os.path.join(cache, "cb_2025_us_state_500k.zip"), ["STATEFP", "STUSPS"])
    st = st[st["STATEFP"].isin(geo.CONUS_STATEFP)]
    return dict(zip(st["STUSPS"], st.geometry))


def read_areas(path: str = AREAS) -> dict:
    """`look.read_areas` with the tracked `reference/2025/areas.csv.gz` as the default path."""
    return look.read_areas(path)


def page(run_dir, label, ch, *args, **kw):
    """`look.page` with the run path relative to `$TD_REPO` and the channel's $ target and band."""
    return look.page(os.path.relpath(run_dir, TD_REPO), label, ch, *args, target=TARGET.get(ch),
                     band=DOLLAR_BAND, **kw)


def exec_page(label, ch, *args, **kw):
    """`look.exec_page` with the channel's $ target and band."""
    return look.exec_page(label, ch, *args, target=TARGET.get(ch), band=DOLLAR_BAND, **kw)


def summary_page(run_dir, *args, **kw):
    """`look.summary_page` with the run path relative to `$TD_REPO`."""
    return look.summary_page(os.path.relpath(run_dir, TD_REPO), *args, **kw)


def metros(weight: dict, n: int = METROS) -> list:
    """[(x, y, name)] in `geo.CRS`: `top_metros` on the tracked CBSA points."""
    top = top_metros(weight, read_areas(), n)
    if not top:
        return []
    tr = Transformer.from_crs("EPSG:4326", geo.CRS, always_xy=True)
    xs, ys = tr.transform([t[1] for t in top], [t[2] for t in top])
    return [(x, y, t[0]) for t, x, y in zip(top, xs, ys)]


def geometry(cache: str = CACHE) -> tuple:
    """(ZCTA polygons, state shapes, no-ZCTA land), each pickled in `cache` (`zcta_polys.pkl`,
    `states.pkl`, `no_zcta_land.pkl`) and built on a miss; the summary page reads the first two
    (`tools/maps/summary.py`)."""
    public = os.path.join(TD_REPO, "data", "public")
    polys = cached("zcta_polys.pkl", lambda: zcta_polygons(all_zctas(), public), cache)
    st = cached("states.pkl", lambda: states(cache), cache)
    gap = cached("no_zcta_land.pkl", lambda: no_zcta_land(polys, st), cache)
    return polys, st, gap


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("label")
    ap.add_argument("out_dir")
    ap.add_argument("--corridor", action="store_true")
    ap.add_argument("--fac", default=FAC_JSON, help="tables.json with `fac`, $M per m_rel")
    ap.add_argument("--cache", default=CACHE, help="the state shapes and the pickled geometry")
    ap.add_argument("--style", choices=("default", "exec"), default="default",
                    help="exec: also write the executive page zip_exec_<channel>.png (after the summary in the PDF)")
    ap.add_argument("--title", default=None, help="the whole suptitle of every page (default `<label>  ·  ...`)")
    ap.add_argument("--no-footer", action="store_true", help="drop the captions at the bottom of every page")
    ap.add_argument("--palette", choices=("default", "clean"), default="default",
                    help="clean: calmer summary ramp and split outline, spread district colours (module doc)")
    a = ap.parse_args(argv)
    look = dict(title=a.title, footer=not a.no_footer)
    FAC = read_fac(a.fac)
    polys, st, gap = geometry(a.cache)
    with open(os.path.join(a.run_dir, "districts.csv"), newline="") as fh:
        names = {r["district"]: r["district_name"] for r in csv.DictReader(fh)}
    owned = collections.defaultdict(lambda: collections.defaultdict(set))
    usd = collections.defaultdict(collections.Counter)
    by_cbsa = collections.Counter()
    filed = set()
    with open(os.path.join(a.run_dir, "ledger.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if not r["district"]:
                continue
            owned[r["model_channel"]][r["district"]].add(r["zip_code"])
            filed.add((r["model_channel"], r["district"], r["state"]))
            m = float(r["m_rel"])
            if m > 0:
                usd[r["model_channel"]][r["district"]] += m * FAC[r["current_channel"]]
                if r.get("cbsa"):
                    by_cbsa[r["cbsa"]] += m * FAC[r["current_channel"]]
    zst = {}
    with open(os.path.join(a.run_dir, "ledger.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            zst[r["zip_code"]] = r["state"]
    insets = [NYC] + ([CORRIDOR] if a.corridor else [])
    metro = metros(by_cbsa)
    counts = state_territories(filed)
    fig, path = summary_page(a.run_dir, a.label, counts, {c: len(owned[c]) for c in owned}, st, metro,
                             a.out_dir, palette=a.palette, **look)
    plt.close(fig)
    written = [path]
    execs = []
    print(f"summary: {len(counts)} states, {sum(map(len, split_states(counts).values()))} (state, channel) "
          f"splits, {len(metro)} metros -> {path}", flush=True)
    for ch in sorted(owned, key=CHANNELS.index):
        rows = owned[ch]
        held = collections.defaultdict(set)
        for d, zs in rows.items():
            for z in zs:
                held[zst[z]].add(d)
        split = sorted(s for s, ds in held.items() if len(ds) > 1)
        missing = sorted({z for zs in rows.values() for z in zs} - set(polys))
        extra = {"splits": f"{len(split)} split states: {' '.join(split) or 'none'}"
                 + (f"  ·  {len(missing)} owned ZCTAs with no polygon" if missing else "")}
        mine = {z for zs in rows.values() for z in zs}
        other_names = [c for c in owned if c != ch
                       and any(z not in mine for zs in owned[c].values() for z in zs)]
        elsewhere = {z for c in other_names for zs in owned[c].values() for z in zs} - mine
        other = (shapely.union_all([polys[z] for z in elsewhere if z in polys]).buffer(150).buffer(-150)
                 if elsewhere else None)
        fig, path = page(a.run_dir, a.label, ch, rows, polys, st, gap, other, other_names, names,
                         {d: usd[ch][d] for d in rows}, insets, a.out_dir, extra, metro,
                         palette=a.palette, **look)
        plt.close(fig)
        written.append(path)
        if a.style == "exec":
            fig, xpath = exec_page(a.label, ch, rows, polys, st, gap, {d: usd[ch][d] for d in rows}, a.out_dir, metro,
                                  title=a.title)
            plt.close(fig)
            execs.append(xpath)
        print(f"{ch}: {len(rows)} districts, {sum(map(len, rows.values()))} ZCTAs, "
              f"{len(missing)} without polygon, splits {len(split)} -> {path}", flush=True)
    from PIL import Image                          # a raster PDF: the vector one runs to 100+ MB
    written[1:1] = execs
    pages = [Image.open(p).convert("RGB") for p in written]
    written.append(os.path.join(a.out_dir, "zip_pages.pdf"))
    pages[0].save(written[-1], save_all=True, append_images=pages[1:], resolution=130)
    return written


if __name__ == "__main__":
    main()
