"""model_extract.py -- 02_model_extract.sql's CSV to td_instance_descaled/3 files, one per SOURCE x column.

    "$TD_PY" tools/snowflake/model_extract.py $TD_REPO/data/safe/<result>.csv [--out DIR]

Writes <out>/<source>_<column>/{instance_descaled.json.gz, channels.json, incumbent.csv} for column in DIST_CH, NEW_DIST,
CHANNEL: opportunity summed by (ZIP, fine channel), fine channel = export_instance.channel_name of the column's value
(NULL or blank: `blank`, reported, never dropped), m_rel = M / median positive cell M.  No sales, no firm, no rep:
`share` and `firm` are empty, incumbent.csv holds the TERR layer's surrogate holders.  Refuses (exit 1) while a
MUST_BE_ZERO check is not 0.  Default out: $TD_REPO/data/safe/model_extract_<csv stem>/ (data/safe/ is git-excluded).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
import statistics
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, ROOT)
from td import data  # noqa: E402

# by path: another `export` package can sit on sys.path
_spec = importlib.util.spec_from_file_location("export_instance", os.path.join(ROOT, "export", "export_instance.py"))
channel_name = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(channel_name)
channel_name = channel_name.channel_name

COLUMNS = ("DIST_CH", "NEW_DIST", "CHANNEL")
BLANK = "blank"


def read(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = [{k.strip().lower(): (v or "") for k, v in r.items()} for r in csv.DictReader(fh)]
    bad = [r for r in rows if r["layer"] == "CHECKS" and r["must_be_zero"] == "1" and float(r["value"] or 0) != 0]
    if bad:
        sys.exit("refused: " + "; ".join(f"{r['source']} {r['name']} = {r['value']}" for r in bad))
    return rows


def extract(opp, column, source, name):
    spell, mass, ncells = defaultdict(set), defaultdict(float), 0
    for r in opp:
        raw = r[column.lower()].strip()
        fine = channel_name(raw) or BLANK
        spell[fine].add(raw)
        mass[(r["zip_code"], fine)] += float(r["mm_opp"])
        ncells += int(r["n_cells"])
    cells = sorted(c for c in mass if mass[c] > 0)
    kappa = statistics.median(mass[c] for c in cells)
    chans = tuple(sorted({c for _, c in cells}))
    ex = data.Extract(chans, [z for z, _ in cells], [c for _, c in cells], [data.rsig(mass[c] / kappa) for c in cells],
                      [{} for _ in cells], [0.0] * len(cells), {},
                      dict(source=source, column=column, kappa_usd=kappa, input=name, n_cells=ncells))
    total = sum(ex.m_rel)
    docs = [dict(channel=c, spellings=sorted(spell[c]), cells=ex.channel.count(c), zips=len({z for z, k in cells if k == c}),
                 opportunity_share=data.rsig(sum(m for k, m in zip(ex.channel, ex.m_rel) if k == c) / total))
            for c in chans]
    return ex, dict(channels=docs)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    name = os.path.basename(a.csv)
    out = a.out or os.path.join(os.environ.get("TD_REPO", ROOT), "data", "safe", "model_extract_" + os.path.splitext(name)[0])
    rows = read(a.csv)
    sources = sorted({r["source"] for r in rows if r["layer"] == "OPP"})
    dirs = {s: re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "source" for s in sources}
    if len(set(dirs.values())) < len(dirs):
        sys.exit(f"refused: sources {sources} sanitise to the same directory name")
    for s in sources:
        opp = [r for r in rows if r["layer"] == "OPP" and r["source"] == s]
        for col in COLUMNS:
            d = os.path.join(out, f"{dirs[s]}_{col.lower()}")
            ex, chans = extract(opp, col, s, name)
            os.makedirs(d, exist_ok=True)
            data.write(ex, os.path.join(d, "instance_descaled.json.gz"))
            with open(os.path.join(d, "channels.json"), "w", encoding="utf-8") as fh:
                json.dump(chans, fh, indent=2, sort_keys=True)
                fh.write("\n")
            with open(os.path.join(d, "incumbent.csv"), "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh, lineterminator="\n")
                w.writerow(["zip", "channel", "holder"])
                w.writerows(sorted((r["zip_code"], r["channel"], r["holder"]) for r in rows
                                   if r["layer"] == "TERR" and r["source"] == s))
            back = data.load(os.path.join(d, "instance_descaled.json.gz"))
            nb = sum(c == BLANK for c in back.channel)
            print(f"{d}: {len(back.z)} cells, {len(back.channels)} channels, {nb} `{BLANK}` cells "
                  f"({data.rsig(sum(m for c, m in zip(back.channel, back.m_rel) if c == BLANK) / sum(back.m_rel))} of m_rel), "
                  f"conus dropped {data.conus(back).dropped}")


if __name__ == "__main__":
    main()
