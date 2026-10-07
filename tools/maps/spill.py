"""spill.py -- the land a ZCTA has across a state line (#128), for the required-look maps.

A ZCTA is filed under its primary county's state (`td/geo.py`) but drawn whole, so where its
polygon crosses a state line its district's colour spills into the neighbour: 137 CONUS ZCTAs
have county land in more than one state.  The ZIP pages hatch that part (`zip_pages.py`), and each
channel's footer there and on the summary names the states that look split only because of it.
The summary itself draws no spill: its fill is a Voronoi diagram clipped to each ZIP's filed state.

- `spill_geometry`: {ZCTA: the part of its 2025 TIGER/Line ZCTA520 polygon outside its filed
  state's 2025 TIGER/Line state polygon}, in `geo.CRS`, for every ZCTA whose county land
  (`reference/2025/zcta_overlay.csv.gz`) touches a state other than its filed one; `cached_spill`
  pickles it in the ZIP pages' cache, keyed on those ZCTAs and the state file's sha256.
- `spill_part`: one ZCTA's polygon less its filed state's.
- `split_drawn`: a drawn ZCTA polygon cut into the part drawn as today and the hatched part.
- `spill_only`: per planning channel, the states the ledger holds in one district of that
  channel that are drawn in more than one through county land over `SPILL_KM2` km² in them.

The state and ZCTA files are read from `$TD_REPO/data/public`, never copied into the repo.
"""
from __future__ import annotations

import collections
import csv
import gzip
import hashlib
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
TD_REPO = os.environ.get("TD_REPO", ROOT)

import shapely                                      # noqa: E402

from td import geo                                  # noqa: E402

PUBLIC = os.path.join(TD_REPO, "data", "public")
STATE_FILE = os.path.join(PUBLIC, "tl_2025_us_state.zip")
ZCTA_FILE = os.path.join(PUBLIC, "tl_2025_us_zcta520.zip")
OVERLAY = os.path.join(geo.REFERENCE_DIR, "zcta_overlay.csv.gz")
REFERENCE = os.path.join(geo.REFERENCE_DIR, "zcta_reference.csv.gz")
SPILL_KM2 = 1.0             # a state counts in the footer from this much county land in it
ZCTA_BATCH = 500


def fips_usps(state_file: str = STATE_FILE) -> dict:
    """{state FIPS: USPS code} for CONUS, from the state file's attributes."""
    df = geo._read(state_file, ["STATEFP", "STUSPS"], geometry=False)
    return {f: s for f, s in zip(df["STATEFP"], df["STUSPS"]) if f in geo.CONUS_STATEFP}


def state_land(fips: dict, overlay: str = OVERLAY) -> dict:
    """{ZCTA: {state: county land m²}} from the overlay's county layer."""
    land = collections.defaultdict(collections.Counter)
    with gzip.open(overlay, "rt") as fh:
        for r in csv.DictReader(fh):
            if r["layer"] == "county":
                land[r["zcta"]][fips.get(r["geoid"][:2], "?")] += float(r["land_m2"])
    return land


def filed_states(reference: str = REFERENCE) -> dict:
    """{ZCTA: filed state} from the reference table."""
    with gzip.open(reference, "rt") as fh:
        return {r["zcta"]: r["state"] for r in csv.DictReader(fh)}


def crossing(land: dict, filed: dict) -> dict:
    """{ZCTA: filed state} for every ZCTA with county land in another state."""
    return {z: filed[z] for z, by in land.items() if z in filed and set(by) - {filed[z]}}


def spill_geometry(cross: dict, state_file: str = STATE_FILE, zcta_file: str = ZCTA_FILE) -> dict:
    """{ZCTA: polygon minus its filed state's polygon} for `cross` ({ZCTA: filed state}), in
    `geo.CRS`, unsimplified; a ZCTA with nothing outside its state is left out."""
    st = geo._read(state_file, ["STUSPS"])
    states = dict(zip(st["STUSPS"], st.geometry))
    zs = sorted(cross)
    out = {}
    for i in range(0, len(zs), ZCTA_BATCH):
        df = geo._read(zcta_file, ["ZCTA5CE20"],
                       where=f"ZCTA5CE20 IN ({','.join(repr(z) for z in zs[i:i + ZCTA_BATCH])})")
        for z, poly in zip(df["ZCTA5CE20"], df.geometry):
            part = spill_part(poly, states[cross[z]])
            if part is not None:
                out[z] = part
    return out


def spill_part(poly, state):
    """The part of ZCTA polygon `poly` outside its filed state's polygon `state`, or None."""
    part = shapely.difference(poly, state)
    return None if part.is_empty or part.area <= 0 else part


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def cached_spill(cache: str, cross: dict, state_file: str = STATE_FILE,
                 zcta_file: str = ZCTA_FILE) -> dict:
    """`spill_geometry(cross)`, pickled as `cache/spill.pkl` under a key of `cross` and the state
    file's sha256; rebuilt when either changes."""
    key = hashlib.sha256((_sha256(state_file) + repr(sorted(cross.items()))).encode()).hexdigest()
    path = os.path.join(cache, "spill.pkl")
    if os.path.exists(path):
        with open(path, "rb") as fh:
            blob = pickle.load(fh)
        if blob.get("key") == key:
            return blob["spill"]
    out = spill_geometry(cross, state_file, zcta_file)
    with open(path + ".tmp", "wb") as fh:
        pickle.dump({"key": key, "spill": out}, fh, protocol=4)
    os.replace(path + ".tmp", path)
    return out


def split_drawn(poly, spill):
    """(the part of drawn ZCTA polygon `poly` drawn as today, the hatched part): `poly` less
    `spill`, and `spill` itself (None for a ZCTA with no spill)."""
    if spill is None:
        return poly, None
    return shapely.difference(poly, spill), spill


def spill_only(owned: dict, filed: dict, land: dict, km2: float = SPILL_KM2) -> dict:
    """{planning channel: sorted states} the ledger holds in one district of that channel that
    are drawn in more than one: a state takes each district holding one of its ZCTAs, and each
    district holding a ZCTA with more than `km2` km² of county land in it.  `owned` is
    {(ZCTA, planning channel): district}, `filed` {ZCTA: filed state}."""
    led = collections.defaultdict(set)
    drawn = collections.defaultdict(set)
    for (z, ch), d in owned.items():
        led[(ch, filed[z])].add(d)
        drawn[(ch, filed[z])].add(d)
        for s, m2 in land.get(z, {}).items():
            if m2 > km2 * 1e6:
                drawn[(ch, s)].add(d)
    out = collections.defaultdict(list)
    for (ch, s), ds in sorted(drawn.items()):
        if len(ds) > 1 and len(led.get((ch, s), ())) == 1:
            out[ch].append(s)
    return dict(out)


def ledger_owned(ledger: str) -> tuple:
    """({(ZCTA, planning channel): district}, {ZCTA: filed state}) of a run's `ledger.csv`."""
    owned, filed = {}, {}
    with open(ledger, newline="") as fh:
        for r in csv.DictReader(fh):
            filed[r["zip_code"]] = r["state"]
            if r["district"]:
                owned[(r["zip_code"], r["model_channel"])] = r["district"]
    return owned, filed


def spill_text(states: list) -> str:
    """The footer line of one channel."""
    n = len(states)
    return (f"{n} state{'s' if n != 1 else ''} look{'s' if n == 1 else ''} split only because of "
            f"cross-state ZIPs: {', '.join(states) or 'none'}")
