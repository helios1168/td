"""render.py -- the one tracked renderer of a map in the required look (#120, mandate T1).

    "$TD_PY" tools/maps/render.py <run_dir> [--label TEXT] [--corridor] [--fac PATH]
        [--geo-cache DIR] [--zcta-shp PATH] [--zip-cache DIR] [--if-stale]

Writes into the run's own folder:

- `summary.png` and `summary.svg`: the 2026-10-02 deck look (`tools/maps/summary.py`, the
  legacy `plan_summary` from tag `archive/pre-support-2026-09`, vendored in `tools/maps/legacy/`);
- `zip_<channel>.png` and `zip_pages.pdf`: the ZIP-level pages (`tools/maps/zip_pages.py`): grey
  unassigned land, the NYC inset, and with `--corridor` (IFA) the BOS-WAS one;
- `render.json`: the renderer's commit, dirty flag and code hash (`CODE`), each input's sha256
  (`INPUTS` and the $ factors file), the label and title, M1's verdict from the gate
  (`tools/mandates/check.py`'s `m1`), and each image's sha256.

Every page's title is the label (a shortlist entry's `<id>: <label>`, `tools/shortlist/build.py`;
the run folder's name without one) and ends ", FAILS M1" when the gate fails and the label does
not say so already (", M1 unverified" when the gate cannot tell).  `python -m td maps` is a debug
view, never this.  A render is current (`current`) while its inputs, label, corridor flag, images
and the renderer's code hash are those `render.json` records; a moved HEAD alone does not age it.

The inputs that are not tracked are read from `$TD_REPO` paths or flags and never copied into the
repo: the 2025 ZCTA shapefile and geo cache the legacy code reads (`LEGACY_ARCHIVE`), the ZIP
pages' cache (`zip_pages.CACHE`) and the $ factors (`zip_pages.FAC_JSON`, `tables.json`'s `fac`).
Nothing masked reaches a page: no rep, firm or sales; district names are CBSA names.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TD_REPO = os.environ.get("TD_REPO", ROOT)
RENDER_JSON = "render.json"
INPUTS = ("ledger.csv", "districts.csv", "run.json")
CODE = (os.path.join("tools", "maps"), os.path.join("tools", "looks", "score.py"))
LEGACY_ARCHIVE = os.path.join(TD_REPO, "runs", "sweep", "grid_2026-10-01", "present", "legacy", "archive")
GEO_CACHE = os.path.join(LEGACY_ARCHIVE, "geo")
ZCTA_SHP = os.path.join(LEGACY_ARCHIVE, "data", "tiger", "2025", "tl_2025_us_zcta520.shp")
FAILS = "FAILS M1"


def _load(name: str, path: str):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def code_sha256(root: str = ROOT) -> str:
    """The sha256 over the renderer's code (`CODE`): each file's path under `root` and bytes."""
    files = []
    for part in CODE:
        path = os.path.join(root, part)
        files += ([path] if os.path.isfile(path) else
                  [os.path.join(d, f) for d, _, fs in os.walk(path) for f in fs if f.endswith(".py")])
    h = hashlib.sha256()
    for path in sorted(files):
        h.update(os.path.relpath(path, root).encode() + b"\0")
        with open(path, "rb") as fh:
            h.update(fh.read())
    return h.hexdigest()


def code_state() -> dict:
    """The commit, dirty flag and diff hash of the checkout (`tools/exp/sweep.py`'s), and the
    renderer's code hash."""
    sweep = _load("exp_sweep", os.path.join(ROOT, "tools", "exp", "sweep.py"))
    return {**sweep.code_state(), "code_sha256": code_sha256()}


def title(label: str, gate: dict) -> str:
    """The page title (module doc)."""
    if gate["status"] == "fail" and FAILS not in label:
        return f"{label}, {FAILS}"
    if gate["status"] == "unverified":
        return f"{label}, M1 unverified"
    return label


def read(run_dir: str):
    """The run's `render.json`, or None."""
    path = os.path.join(run_dir, RENDER_JSON)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def current(run_dir: str, label: str | None = None, corridor: bool | None = None,
            fac: str | None = None) -> tuple:
    """(True, "") when the run's render is current for `label` and `corridor` (None: any), else
    (False, why): no `render.json`, an input, the $ factors, an image or the renderer's code hash
    changed, or another label or corridor flag."""
    r = read(run_dir)
    if r is None:
        return False, f"no {RENDER_JSON}"
    if label is not None and r.get("label") != label:
        return False, f"rendered with label {r.get('label')!r}, not {label!r}"
    if corridor is not None and bool(r.get("corridor")) != corridor:
        return False, f"rendered with corridor {r.get('corridor')}, not {corridor}"
    for name, sha in r.get("inputs", {}).items():
        path = os.path.join(run_dir, name)
        if not os.path.exists(path) or sha256_file(path) != sha:
            return False, f"{name} changed since the render"
    fac_rec = r.get("fac") or {}
    fac_path = fac or fac_rec.get("path")
    if not fac_path or not os.path.exists(fac_path) or sha256_file(fac_path) != fac_rec.get("sha256"):
        return False, "the $ factors changed since the render"
    for name, sha in r.get("images", {}).items():
        path = os.path.join(run_dir, name)
        if not os.path.exists(path) or sha256_file(path) != sha:
            return False, f"{name} is not the render's"
    if r.get("renderer", {}).get("code_sha256") != code_sha256():
        return False, "the renderer's code changed since the render"
    return True, ""


def gate(run_dir: str) -> dict:
    """M1's verdict on the run from `tools/mandates/check.py`'s gate: status, summary, diagnostic."""
    check = _load("mandates_check", os.path.join(ROOT, "tools", "mandates", "check.py"))
    got = check.m1(run_dir)
    return {"status": got["status"], "summary": got["summary"], "diagnostic": got["diagnostic"]}


def render(run_dir: str, label: str | None = None, corridor: bool = False, fac: str | None = None,
           geo_cache: str = GEO_CACHE, zcta_shp: str = ZCTA_SHP, zip_cache: str | None = None,
           log=print) -> dict:
    """Render `run_dir` (module doc); its `render.json` record."""
    run_dir = os.path.abspath(run_dir)
    summary = _load("maps_summary", os.path.join(HERE, "summary.py"))
    zip_pages = _load("maps_zip_pages", os.path.join(HERE, "zip_pages.py"))
    fac = os.path.abspath(fac or zip_pages.FAC_JSON)
    label = label or os.path.basename(run_dir)
    inputs = {n: sha256_file(os.path.join(run_dir, n)) for n in INPUTS}
    renderer = code_state()
    verdict = gate(run_dir)
    text = title(label, verdict)
    log(f"{run_dir}: M1 {verdict['status']}; title {text!r}")
    with tempfile.TemporaryDirectory(prefix="td-render-") as work:
        log(summary.adapt(run_dir, work, zip_pages.read_fac(fac)))
        env = {**os.environ, "TD_ZCTA_SHP": zcta_shp}
        proc = subprocess.Popen([sys.executable, "-u", os.path.join(HERE, "summary.py"), work,
                                 "--label", text, "--geo-cache", geo_cache], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for old in glob.glob(os.path.join(run_dir, "zip_*.png")):
            os.remove(old)
        written = zip_pages.main([run_dir, text, run_dir, "--fac", fac]
                                 + (["--corridor"] if corridor else [])
                                 + (["--cache", zip_cache] if zip_cache else []))
        out, _ = proc.communicate()
        log(out.rstrip())
        if proc.returncode:
            raise RuntimeError(f"plan_summary failed ({proc.returncode}) on {run_dir}")
        for ext in ("png", "svg"):
            shutil.copyfile(os.path.join(work, "maps", f"summary.{ext}"),
                            os.path.join(run_dir, f"summary.{ext}"))
    images = ["summary.png", "summary.svg"] + [os.path.basename(p) for p in written]
    doc = {"renderer": renderer, "inputs": inputs, "fac": {"path": fac, "sha256": sha256_file(fac)},
           "geo_cache": geo_cache, "zcta_shp": zcta_shp,
           "zip_cache": os.path.abspath(zip_cache or zip_pages.CACHE),
           "label": label, "title": text, "corridor": corridor, "m1": verdict,
           "images": {n: sha256_file(os.path.join(run_dir, n)) for n in images},
           "rendered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    path = os.path.join(run_dir, RENDER_JSON)
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(path + ".tmp", path)
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tools/maps/render.py", description=__doc__.splitlines()[0])
    ap.add_argument("run_dir")
    ap.add_argument("--label", default=None, help="the page title (default the folder's name)")
    ap.add_argument("--corridor", action="store_true", help="add the BOS-WAS inset (IFA)")
    ap.add_argument("--fac", default=None, help="tables.json with `fac` (default zip_pages.FAC_JSON)")
    ap.add_argument("--geo-cache", default=GEO_CACHE, help="the legacy code's geo cache")
    ap.add_argument("--zcta-shp", default=ZCTA_SHP, help="the 2025 TIGER ZCTA shapefile")
    ap.add_argument("--zip-cache", default=None, help="the ZIP pages' cache (default zip_pages.CACHE)")
    ap.add_argument("--if-stale", action="store_true", help="skip a run whose render is current")
    a = ap.parse_args(argv)
    label = a.label or os.path.basename(os.path.abspath(a.run_dir))
    if a.if_stale:
        ok, _ = current(a.run_dir, label, a.corridor, a.fac)
        if ok:
            print(f"{a.run_dir}: render current, skipped")
            return 0
    doc = render(a.run_dir, label, a.corridor, a.fac, a.geo_cache, a.zcta_shp, a.zip_cache)
    print(f"{a.run_dir}: {', '.join(doc['images'])}, {RENDER_JSON}; M1 {doc['m1']['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
