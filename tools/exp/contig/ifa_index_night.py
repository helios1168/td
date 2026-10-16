"""ifa_index_night.py -- IFA_INDEX.md of the night's K folders (K48..K54) under a sealed root.

    "$TD_PY" tools/exp/contig/ifa_index_night.py <ifa root> [K ...]
    "$TD_PY" tools/exp/contig/ifa_index_night.py --gate <folder> --out <evidence.json>

`--gate` is the sealed and warm driver's gate stage (a capped child): `tools/mandates/check.py`'s own output and exit
code, with the gate's status, items, diagnostic and the neck and piece sides it judged written to `--out`, which the
driver reads (`sealed.manhattan_verdict`); no audit hook is installed in the driver's threads.

Per K: the M1 verdict (a fresh run of the gate, `tools/mandates/check.py` `m1`, on the folder's ledger:
every neck, piece, coverage and ownership item, and "unverified"), districts in, under and over the
window (exact: the unrounded m_rel at the IFA rate against $1,000-1,437.5M, edges included, and run.json's
own `window` verdict; the rounded `usd_m` decides nothing), the worst district's $, the split states
(a state whose ledger rows sit in 2+ districts), the mean $ per district and the page links.

A K is `passes` when the gate's verdict is clean except for the Manhattan items and every district is in the
window.  The Manhattan exception (owner, 2026-10-14, td#140: the Manhattan neck and a detached piece
holding Manhattan) is read off the gate's items, never off a district name: an item is excepted only when the
neck or piece it names contains a ZCTA whose primary county is 36061 (`reference/2025/zcta_reference.csv.gz`,
as `docs/F0.tex` defines the Manhattan set), and the index lists each excepted item.  Any other item (a neck
or piece without Manhattan, an unresolved neck, a coverage or ownership item), a verdict of
`unverified` or a diagnostic folder blocks the pass.

The district masses are the current ones: the folder's ledger (`ledger.csv`, ZCTA and fine channel to
district) joined to the full extract (`$TD_REPO/instance_descaled.json.gz`), never run.json's saved
`m_rel`.  A saved mass that disagrees with them, a ledger cell with no extract mass or a district set
that differs from run.json's raises: a connected ownership change cannot keep a pass on stale masses.  The one
omission that is not a ledger cell with no mass is a `NO_CELL` territory row at `m_rel` 0 (a footprint cell the
extract lacks, `output.ledger`): it adds 0 to its district.
"""
from __future__ import annotations

import collections
import contextlib
import csv
import importlib.util
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from td import audit, data, geo  # noqa: E402

LO, HI = 1000.0, 1437.5         # the IFA window, $M per district
RATE = 1.2519681558             # $M per m_rel (merge.py's DOLLARS_PER_M_REL, the IFA rate)
MASS_RTOL = 1e-9                # saved vs recomputed district mass (summation order only)
MANHATTAN_COUNTY = "36061"
EVIDENCE = "gate-evidence.json"  # a point's gate stage output, next to its `merged` folder
PIECE = re.compile(r"^(\S+)/(\S+): detached piece of (\d+) ZIPs \((\w+)\.\.\.\)")

_check = None


def check_gate():
    """`tools/mandates/check.py`, loaded once."""
    global _check
    if _check is None:
        spec = importlib.util.spec_from_file_location("mandates_check",
                                                      os.path.join(ROOT, "tools", "mandates", "check.py"))
        _check = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_check)
    return _check


def manhattan_zips(ref=None) -> frozenset:
    """The ZCTAs of the reference table whose primary county is 36061 (New York County)."""
    ref = geo.read_reference() if ref is None else ref
    return frozenset(z for z, c in zip(ref["zcta"], ref["county"]) if c == MANHATTAN_COUNTY)


@contextlib.contextmanager
def recorded_sides():
    """Yield `{"necks": {item text: ZCTAs}, "pieces": {(district, first ZIP, size): ZCTAs}}`, filled by the
    gate's own calls while the block runs: `audit.neck_item` sees each proved neck's part cut off and
    `audit.district_pieces` each detached piece, so the sides are the ones the gate judged.  A piece key
    two calls fill with different sets is None (never excepted)."""
    real_item, real_pieces = audit.neck_item, audit.district_pieces
    sides = {"necks": {}, "pieces": {}}

    def neck_item(ch, j, nk, kind="neck"):
        text = real_item(ch, j, nk, kind)
        if kind == "neck" and nk.status == "proved":
            sides["necks"][text] = frozenset(nk.zips)
        return text

    def district_pieces(owner, adj, mass):
        got = real_pieces(owner, adj, mass)
        for j, comps in got.items():
            for c in comps[1:]:
                key, c = (j, min(c), len(c)), frozenset(c)
                sides["pieces"][key] = c if sides["pieces"].get(key, c) == c else None
        return got

    audit.neck_item, audit.district_pieces = neck_item, district_pieces
    try:
        yield sides
    finally:
        audit.neck_item, audit.district_pieces = real_item, real_pieces


def sides_to_json(sides: dict) -> dict:
    """`recorded_sides`' record as plain JSON: necks by text, pieces as `[district, first ZIP, size, ZCTAs|None]`."""
    return {"necks": {t: sorted(zs) for t, zs in sides["necks"].items()},
            "pieces": [[j, first, size, None if zs is None else sorted(zs)]
                       for (j, first, size), zs in sorted(sides["pieces"].items())]}


def sides_from_json(doc: dict) -> dict:
    return {"necks": {t: frozenset(zs) for t, zs in doc["necks"].items()},
            "pieces": {(j, first, size): None if zs is None else frozenset(zs)
                       for j, first, size, zs in doc["pieces"]}}


def gate_evidence(folder: str, out: str) -> int:
    """The gate stage of a sealed or warm point, a child process (its cap and the `--hours` stop can end it):
    `tools/mandates/check.py`'s own `main` on `folder`, so the log and the exit code are the gate's, with the
    result of its `m1` and the sides `recorded_sides` saw written to `out` (`EVIDENCE`) for the driver to read.
    The audit hooks are installed in this process only; a gate that dies leaves no evidence."""
    mod = check_gate()
    if os.path.exists(out):
        os.remove(out)
    got, real = [], mod.m1

    def m1(run_dir, g=None):
        got.append(real(run_dir, g))
        return got[-1]

    mod.m1 = m1
    try:
        with recorded_sides() as sides:
            rc = mod.main([folder])
    finally:
        mod.m1 = real
    if len(got) != 1:
        raise RuntimeError(f"the gate judged {len(got)} folders, not 1")
    chk = got[0]["check"]
    doc = {"folder": os.path.abspath(folder), "rc": rc, "status": chk.status, "summary": chk.summary,
           "items": list(chk.items), "diagnostic": got[0]["diagnostic"], "sides": sides_to_json(sides)}
    with open(out + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, default=str)
        fh.write("\n")
    os.replace(out + ".tmp", out)
    return rc


def read_gate_evidence(path: str, folder: str, gate_rc: int) -> dict:
    """`gate_evidence`'s record at `path` with its sides rebuilt; raises when it is missing, unreadable, of another
    folder or of another exit code than the one the driver saw."""
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc["folder"] != os.path.abspath(folder) or doc["rc"] != gate_rc:
        raise ValueError(f"{path} is the gate evidence of {doc['folder']} (exit {doc['rc']}), "
                         f"not of {os.path.abspath(folder)} (exit {gate_rc})")
    return {**doc, "sides": sides_from_json(doc["sides"])}


def side_of(item: str, sides: dict):
    """The ZCTAs of the neck or piece a gate item names, or None for any other item."""
    if item in sides["necks"]:
        return sides["necks"][item]
    m = PIECE.match(item)
    return sides["pieces"].get((m.group(2), m.group(4), int(m.group(3)))) if m else None


def m1_verdict(status: str, summary: str, items: list, sides: dict, manhattan, diagnostic=None) -> dict:
    """`{"passes", "excepted": [(item, Manhattan ZCTAs)], "blocking": [text]}` of a gate result: the pass is
    the gate's own except for the items whose side holds a Manhattan ZCTA; the mass necks the gate lists
    beside M1 fail nothing."""
    blocking, excepted = [], []
    if status == "unverified":
        blocking.append(f"M1 unverified: {summary}")
    if diagnostic is not None:
        blocking.append(f"diagnostic folder ({diagnostic.get('label') or 'diagnostic band'}), never a deliverable")
    for item in items:
        if audit.MASS_NECK in item:
            continue
        side = side_of(item, sides)
        hit = sorted(side & manhattan) if side else []
        (excepted if hit else blocking).append((item, hit) if hit else item)
    if status == "fail" and not (excepted or blocking):
        blocking.append(f"M1 fail: {summary}")
    return {"passes": not blocking, "excepted": excepted, "blocking": blocking}


def window_verdict(dist: dict) -> tuple:
    """(over, under) district lists, exact: the unrounded m_rel in dollars (`RATE`) against the owner's window,
    edges included, so a breach of any size is outside.  A district run.json records as outside its window
    (`window`, merge.py's check against the m_rel bounds) is outside here too; the rounded `usd_m` and the
    rounded m_rel bounds decide nothing."""
    lo, hi = LO * 1e6, HI * 1e6
    over, under = [], []
    for j, v in sorted(dist.items()):
        usd = v["m_rel"] * RATE * 1e6
        got = "under" if usd < lo else "over" if usd > hi else v.get("window", "in")
        if got == "over":
            over.append(j)
        elif got == "under":
            under.append(j)
    return over, under


def extract_masses(ext: data.Extract) -> dict:
    """{(ZCTA, fine channel): m_rel} of `ext`, a ZIP's duplicate cells summed as `output.ledger` does."""
    mass = collections.defaultdict(float)
    for z, f, m in zip(ext.z, ext.channel, ext.m_rel):
        mass[z, f] += m
    return mass


def cell_mass(row: dict, mass: dict) -> float:
    """The extract's mass of a ledger row's cell (ZCTA, fine channel).  A cell the extract lacks is territory
    at zero mass only when the ledger says so (`audit.NO_CELL` with `m_rel` 0, the footprint cells `output.ledger`
    adds); any other omission raises, and so does a `NO_CELL` row whose cell the extract holds."""
    key = (row["zip_code"], row["current_channel"])
    no_cell = row.get("reason") == audit.NO_CELL
    if key in mass:
        if no_cell:
            raise ValueError(f"ledger cell {key[0]}/{key[1]} ({row['district']}) is {audit.NO_CELL} but is in the extract")
        return mass[key]
    if no_cell and str(row.get("m_rel", "")).strip() and float(row["m_rel"]) == 0.0:
        return 0.0
    raise ValueError(f"ledger cell {key[0]}/{key[1]} ({row['district']}) has no mass in the extract")


def current_masses(ledger: list, ext: data.Extract) -> dict:
    """{district: m_rel} of the ledger's cells (ZCTA, fine channel) read from `ext` (`cell_mass`: a zero-mass
    `NO_CELL` territory row the extract lacks adds 0, any other cell it does not hold raises)."""
    mass = extract_masses(ext)
    parts = collections.defaultdict(list)
    for r in ledger:
        if r["district"]:
            parts[r["district"]].append(cell_mass(r, mass))
    return {j: math.fsum(ms) for j, ms in parts.items()}


def checked_districts(saved: dict, now: dict) -> dict:
    """run.json's `districts` with `m_rel` replaced by `now`, the masses of the current ledger; raises when
    the district sets differ or a saved `m_rel` is off the current one by more than `MASS_RTOL`."""
    if set(saved) != set(now):
        raise ValueError(f"run.json districts and the ledger's differ: only in run.json "
                         f"{sorted(set(saved) - set(now))}, only in the ledger {sorted(set(now) - set(saved))}")
    off = sorted(j for j in saved if not math.isclose(saved[j]["m_rel"], now[j], rel_tol=MASS_RTOL, abs_tol=1e-12))
    if off:
        raise ValueError(f"run.json m_rel differs from the ledger joined to the extract in {len(off)} districts, "
                         f"first {off[0]} (saved {saved[off[0]]['m_rel']!r}, current {now[off[0]]!r})")
    return {j: {**v, "m_rel": now[j]} for j, v in saved.items()}


def full_extract() -> str:
    return os.path.join(os.environ.get("TD_REPO", ROOT), "instance_descaled.json.gz")


def load(root: str, k: int, manhattan=None, g=None, extract=None) -> dict:
    d = os.path.join(root, f"K{k}")
    run = json.load(open(os.path.join(d, "run.json")))
    names = {r["district"]: r["district_name"] for r in csv.DictReader(open(os.path.join(d, "districts.csv")))}
    ledger = list(csv.DictReader(open(os.path.join(d, "ledger.csv"))))
    dist = checked_districts(run["districts"], current_masses(ledger, data.load(extract or full_extract())))
    held = collections.defaultdict(set)
    for r in ledger:
        if r["district"]:
            held[r["state"]].add(r["district"])
    split = sorted(s for s, ds in held.items() if len(ds) > 1)
    with recorded_sides() as sides:
        gate = check_gate().m1(d, g)
    chk = gate["check"]
    m1 = m1_verdict(chk.status, chk.summary, chk.items, sides,
                    manhattan_zips() if manhattan is None else manhattan, gate["diagnostic"])
    exact = {j: v["m_rel"] * RATE for j, v in dist.items()}
    usd = dict(exact)
    over, under = window_verdict(dist)
    worst = max(exact, key=lambda j: max(exact[j] - HI, LO - exact[j]))
    return {"k": k, "m1": m1, "m1_status": chk.status, "names": names, "split": split, "usd": usd, "worst": worst,
            "over": over, "under": under, "n": len(dist), "in": len(dist) - len(over) - len(under),
            "mean": sum(usd.values()) / len(usd),
            "region": json.load(open(os.path.join(d, "manifest.json"))).get("command", "")}


def main(argv) -> int:
    if argv and argv[0] == "--gate":     # the sealed driver's gate stage: --gate <folder> --out <evidence>
        return gate_evidence(argv[1], argv[argv.index("--out") + 1])
    root = os.path.abspath(argv[0])
    ks = [int(x) for x in argv[1:]] or list(range(48, 55))
    out = ["# IFA K48..K54, night of 2026-10-14 (sealed root)", "",
           "Window $1,000-1,437.5M per district (m_rel 798.74-1,148.19), judged on the unrounded mass of the current ledger. M1 under the",
           "water and empty-land gate (branch m5-studio/ifa-night), run fresh on each folder's ledger; Manhattan is",
           "the only allowed exception (owner, 2026-10-14, td#140): an item counts as Manhattan only when the neck or",
           "piece it names holds a ZCTA of county 36061, and every excepted item is listed below.",
           "A K `passes` when the gate is clean but for those items and every district is in the window.", ""]
    rows, notes = [], []
    manhattan = manhattan_zips()
    for k in ks:
        r = load(root, k, manhattan)
        worst, m1 = r["worst"], r["m1"]
        verdict = "passes" if m1["passes"] and not r["over"] and not r["under"] else "FAILS"
        if m1["blocking"]:
            gate = f"NOT clean: {len(m1['blocking'])} items outside the Manhattan exception"
        else:
            gate = f"clean but for {len(m1['excepted'])} Manhattan items" if m1["excepted"] else "clean"
        links = f"[zip_pages.pdf](K{k}/zip_pages.pdf), [zip_summary.png](K{k}/zip_summary.png)"
        rows.append(f"| {k} | {verdict} | {gate} | {r['in']}/{len(r['under'])}/{len(r['over'])} "
                    f"| {worst} ${r['usd'][worst]:,.1f}M | {len(r['split'])}: {' '.join(r['split'])} "
                    f"| ${r['mean']:,.1f}M | {links} |")
        notes.append(f"### K{k}\n")
        notes += [f"- EXCEPTED (Manhattan: {' '.join(zs[:4])}{'...' if len(zs) > 4 else ''}): {i}" for i, zs in m1["excepted"]]
        notes += [f"- BLOCKING: {i}" for i in m1["blocking"]]
        notes += [] if m1["excepted"] or m1["blocking"] else ["- no neck or piece"]
        notes.append("")
    out += ["| K | verdict | M1 gate | districts in/under/over | worst district | split states | mean $/district | pages |",
            "|---|---|---|---|---|---|---|---|"] + rows + ["", "## M1 items per K (the gate, run fresh)", ""] + notes
    out += ["Paths are relative to this folder under `$TD_REPO/runs/exp/sealed_2026-10-14/ifa/` (gitignored, hub only)."]
    open(os.path.join(root, "IFA_INDEX.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out[:20]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
