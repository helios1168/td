"""build.py -- the map shortlist (#120, mandate T1): its generated view and its deck.

    "$TD_PY" tools/shortlist/build.py [--registry PATH]
    "$TD_PY" tools/shortlist/build.py --deck <dir> [--tier T ...] [--jobs N]

The registry is `tools/shortlist/shortlist.json` (moved from the gitignored `runs/shortlist/` on
2026-10-06): `tiers` (tier -> what it means) and `maps`, one entry per map shown to the owner or
stakeholders: `id`, `tier`, `rank`, `label` (layout and K per channel), `run` (the run folder),
`images` (the renderer's outputs in that folder: `summary.png` first, then `zip_pages.pdf`),
`notes`, the metrics shown (`metrics`, or `score`: a score file and its key), and `shown_images`,
what was shown before the renderer existed.  Paths are relative to `$TD_REPO`.  Edit the JSON by
hand; an entry that drops out moves to a superseded tier and is never deleted.

Without `--deck` it writes the generated view `$TD_REPO/runs/shortlist/INDEX.md` and copies each
entry's summary page into `runs/shortlist/tier<T>/<rank>_<id>.png`.  Each row's M1 is the gate's
verdict the run's `render.json` records (`tools/maps/render.py`).  With `--deck`, every entry (of
the `--tier`s given) is rendered first unless its render is current, `--jobs` at a time, each page
titled `render_label(entry)`, IFA runs with the BOS-WAS inset; then `<dir>/deck.pdf` holds the
summary pages in tier and rank order and `<dir>/DECK.md` lists each page's entry and images.
`tools/mandates/check.py --tracking` checks the registry against the runs.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
REGISTRY = os.path.join(HERE, "shortlist.json")
RENDER = os.path.join(ROOT, "tools", "maps", "render.py")


def td_repo() -> str:
    return os.environ.get("TD_REPO", ROOT)


def _render():
    if "maps_render" not in sys.modules:
        spec = importlib.util.spec_from_file_location("maps_render", RENDER)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["maps_render"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["maps_render"]


def load(path: str = REGISTRY) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def entries(cfg: dict, tiers=None) -> list:
    """The registry's entries in tier order (the order of `tiers` in the file), then rank."""
    order = list(cfg["tiers"])
    keep = [str(t) for t in tiers] if tiers else order
    return sorted((e for e in cfg["maps"] if str(e["tier"]) in keep),
                  key=lambda e: (order.index(str(e["tier"])), e["rank"]))


def path(p: str, base: str | None = None) -> str:
    """A registry path made absolute against `base` (default `$TD_REPO`)."""
    return p if os.path.isabs(p) else os.path.join(base or td_repo(), p)


def render_label(e: dict) -> str:
    """The title `tools/maps/render.py` gives an entry's pages: its id and label."""
    return f"{e['id']}: {e['label']}"


def corridor(run_dir: str) -> bool:
    """True for a run with an IFA channel: its pages get the BOS-WAS inset."""
    with open(os.path.join(run_dir, "districts.csv"), newline="", encoding="utf-8") as fh:
        return any(r["channel"] == "IFA" for r in csv.DictReader(fh))


def metrics(e: dict, base: str) -> dict:
    """The metrics shown for `e`: its own, or summed from its score file; a missing one is None."""
    if "score" not in e:
        return e.get("metrics") or {}
    with open(path(e["score"][0], base), encoding="utf-8") as fh:
        chs = json.load(fh)[e["score"][1]]
    return {"districts": sum(v["k"] for v in chs.values()),
            "within10": sum(v["within10"] for v in chs.values()) if all("within10" in v for v in chs.values()) else None,
            "worst": round(100 * max(v["worst"] for v in chs.values()), 1),
            "splits": sum(len(v["split"]) for v in chs.values()),
            "thin": sum(len(v["thin"]) for v in chs.values()), "small": sum(len(v["small"]) for v in chs.values())}


def index_md(cfg: dict, base: str, view: str) -> str:
    """INDEX.md's text; copies each entry's summary page into `view`/tier<T>/ on the way."""
    for d in os.listdir(view) if os.path.isdir(view) else []:
        if d.startswith("tier") and os.path.isdir(os.path.join(view, d)):
            shutil.rmtree(os.path.join(view, d))
    f = lambda x: "–" if x is None else x                       # noqa: E731
    md = ["# Map shortlist", "",
          "Built by `tools/shortlist/build.py` from `tools/shortlist/shortlist.json`; edit the JSON, "
          "not this file.  Each image is `tools/maps/render.py`'s output in the run's folder; M1 is "
          "the gate's verdict its `render.json` records.", ""]
    for t, desc in cfg["tiers"].items():
        md += [f"## Tier {t}", "", desc, "",
               "| # | map | districts | within ±10% | worst | split states | thin | small | audit | M1 | image |",
               "|---|---|---|---|---|---|---|---|---|---|---|"]
        notes = []
        for e in entries(cfg, [t]):
            m, run = metrics(e, base), path(e["run"], base)
            sc = os.path.join(run, "scorecard.md")
            v = re.search(r"Verdict: (\w+)", open(sc, encoding="utf-8").read()) if os.path.exists(sc) else None
            r = _render().read(run) if os.path.isdir(run) else None
            m1 = r["m1"]["status"] if r else "not rendered"
            image = path(e["images"][0], base) if e.get("images") else None
            if image and os.path.exists(image):
                dest = os.path.join(view, f"tier{t}", f"{e['rank']}_{e['id']}.png")
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy(image, dest)
            md.append(f"| {e['rank']} | **{e['id']}**: {e['label']} | {f(m.get('districts'))} | "
                      f"{f(m.get('within10'))}/{f(m.get('districts'))} | {f(m.get('worst'))}% | "
                      f"{f(m.get('splits'))} | {f(m.get('thin'))} | {f(m.get('small'))} | "
                      f"{v.group(1) if v else '?'} | {m1} | `{image}` |")
            notes.append(f"- **{e['id']}**: {e['notes']} Run: `{e['run']}`")
        md += [""] + notes + [""]
    return "\n".join(md)


def render_one(e: dict, base: str, logs: str) -> tuple:
    """(id, "current" | "rendered" | "failed: ..."): `e`'s run rendered unless current."""
    run, label = path(e["run"], base), render_label(e)
    ok, _ = _render().current(run, label, corridor(run))
    if ok:
        return e["id"], "current"
    os.makedirs(logs, exist_ok=True)
    with open(os.path.join(logs, f"{e['id']}.log"), "w", encoding="utf-8") as fh:
        got = subprocess.run([sys.executable, "-u", RENDER, run, "--label", label]
                             + (["--corridor"] if corridor(run) else []),
                             stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    return e["id"], "rendered" if got.returncode == 0 else f"failed: exit {got.returncode}, see {fh.name}"


def deck(cfg: dict, base: str, out: str, tiers=None, jobs: int = 4) -> list:
    """Render every selected entry unless current, then write `out`/deck.pdf and DECK.md; the
    (id, outcome) of each entry."""
    chosen = entries(cfg, tiers)
    _render()                                      # loaded once, before the threads share it
    with concurrent.futures.ThreadPoolExecutor(jobs) as pool:
        done = list(pool.map(lambda e: render_one(e, base, os.path.join(out, "logs")), chosen))
    failed = [d for d in done if d[1].startswith("failed")]
    if failed:
        raise RuntimeError("; ".join(f"{i} {s}" for i, s in failed))
    from PIL import Image                          # a raster PDF, like the ZIP pages
    pages = [Image.open(path(e["images"][0], base)).convert("RGB") for e in chosen]
    pages[0].save(os.path.join(out, "deck.pdf"), save_all=True, append_images=pages[1:], resolution=100)
    lines = ["# Deck", "", f"Built by `tools/shortlist/build.py --deck` from `tools/shortlist/shortlist.json`, "
             f"tiers {', '.join(map(str, tiers)) if tiers else 'all'}; `deck.pdf` holds the summary pages in this order.", "",
             "| page | id | tier | label | M1 | images |", "|---|---|---|---|---|---|"]
    for i, e in enumerate(chosen, 1):
        r = _render().read(path(e["run"], base))
        lines.append(f"| {i} | {e['id']} | {e['tier']} | {e['label']} | {r['m1']['status']} | "
                     + ", ".join(f"`{path(p, base)}`" for p in e["images"]) + " |")
    with open(os.path.join(out, "DECK.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return done


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tools/shortlist/build.py", description=__doc__.splitlines()[0])
    ap.add_argument("--registry", default=REGISTRY)
    ap.add_argument("--deck", metavar="DIR", help="render the entries and assemble DIR/deck.pdf")
    ap.add_argument("--tier", action="append", help="only this tier (repeatable; with --deck)")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args(argv)
    cfg, base = load(a.registry), td_repo()
    if a.deck:
        os.makedirs(a.deck, exist_ok=True)
        for i, s in deck(cfg, base, os.path.abspath(a.deck), a.tier, a.jobs):
            print(f"{i}: {s}")
        print(f"deck: {os.path.join(os.path.abspath(a.deck), 'deck.pdf')}")
    view = os.path.join(base, "runs", "shortlist")
    os.makedirs(view, exist_ok=True)
    with open(os.path.join(view, "INDEX.md"), "w", encoding="utf-8") as fh:
        fh.write(index_md(cfg, base, view))
    print(f"shortlist: {len(cfg['maps'])} maps, {os.path.join(view, 'INDEX.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
