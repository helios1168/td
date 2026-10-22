"""snowflake.py -- the stakeholder package: one long Snowflake dataset and the owner pages of every map.

    "$TD_PY" tools/export/snowflake.py data   <out_dir>   # long CSV.gz + districts CSV
    "$TD_PY" tools/export/snowflake.py render <out_dir>   # zip_pages per scenario + <FAMILY>_pages.pdf

`SCENARIOS` is the whole record of what ships: scenario name, family, source run folder (a ledger.csv
and districts.csv, read from `$TD_REPO`). Add a map by adding a row; the name follows `scenario_name`.

Naming (owner, 2026-10-22): `<FAMILY>_K<total>_<CH><k>...`, channels in the order N, WH, FI, WIFI with
empty channels left out (`WIFI_K50_N15_WIFI35`); IFA is `IFA_K<k>`. No internal map id appears. When two
maps share a name, the later one carries a suffix (`_R2` for ne-48-bal-r2).

The long file has the 12 columns of the archived export
(`archive/pre-support-2026-09:exports/database/all_scenarios_nationwide_zcta_long.csv.gz`): one row per
(scenario, ZCTA, fine channel); `rep` is `None` (the ledgers carry no staffing, OD3);
`has_commercial_opportunity` is `m_rel > 0`, the archived exporter's rule.

Pages: `tools/maps/zip_pages.py --corridor --no-footer --palette clean`, label = scenario name, `--fac`
1.0 per channel (these ledgers hold m_rel in $M from the usd extract; the default fac table would show
$ ~24% high). PDFs are joined with `pdfunite`.
"""
from __future__ import annotations

import collections
import csv
import gzip
import io
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TD_REPO = os.environ.get("TD_REPO", "/Users/Shared/sv-ntlee/td")
E = os.path.join(TD_REPO, "runs", "exp")

# (family, source run folder, name suffix, internal map id -- for this record only, never printed)
SCENARIOS = [
    ("WIFI", f"{E}/national_2026-10-14/warm/ne-48-bal/merged", "", "ne-48-bal"),
    ("WIFI", f"{E}/sealed_2026-10-14/main_unsealed/ne-48-bal-r2", "_R2", "ne-48-bal-r2"),
    ("WIFI", f"{E}/national_2026-10-14/warm/ne-cmp-tierP/merged", "", "ne-cmp-tierP"),
    ("WIFI", f"{E}/national_2026-10-14/warm/ne-50-filight/merged", "", "ne-50-filight"),
    # nw34-50 was run on m2; its merged folder was copied to the same path on m5 (2026-10-22)
    ("WIFI", f"{E}/national_2026-10-14/grid2/warm/nw34-50/merged", "", "nw34-50"),
    ("WIFI", f"{E}/national_2026-10-15_p3/w1-52-bal/merged", "", "w1-52 (balanced)"),
] + [("IFA", f"{E}/sealed_2026-10-14/ifa/K{k}", "", f"IFA K{k}") for k in range(48, 55)]

TAG = {"national": "N", "WH": "WH", "FI": "FI", "WIFI": "WIFI"}
FINE = {"national_chase": ("National (Chase)", "national_chase"), "wells_wh": ("Wells WH", "national_wells_wh"),
        "wells_fi": ("Wells FI", "national_wells_fi"), "wh": ("WH", "wh"), "fi": ("FI", "fi"), "ifa": ("IFA", "ifa")}
COLUMNS = ["scenario", "zip_code", "current_channel", "canonical_channel", "state", "model_channel", "bundle",
           "district", "district_channels", "rep", "m_rel", "has_commercial_opportunity"]
DISTRICT_COLUMNS = ["channel", "district", "district_name", "copy", "support", "planned_mass", "drawn_mass",
                    "pieces", "source_run", "source_district"]
LONG = "all_scenarios_nationwide_zcta_long.csv.gz"
DISTRICTS = "all_scenarios_districts.csv"


def districts(run):
    with open(os.path.join(run, "districts.csv"), newline="") as fh:
        return list(csv.DictReader(fh))


def scenario_name(family, rows, suffix):
    if family == "IFA":
        return f"IFA_K{len(rows)}{suffix}"
    k = collections.Counter(r["channel"] for r in rows)
    return f"{family}_K{len(rows)}_" + "_".join(f"{TAG[c]}{k[c]}" for c in TAG if k[c]) + suffix


def named():
    out, seen = [], set()
    for family, run, suffix, _ in SCENARIOS:
        name = scenario_name(family, districts(run), suffix)
        if name in seen:
            sys.exit(f"duplicate scenario name {name}: give one of the maps a suffix in SCENARIOS")
        seen.add(name)
        out.append((name, family, run))
    return out


def data(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    total = 0
    # mtime=0: the gzip header carries no timestamp, so a rerun on the same sources is byte-identical
    with io.TextIOWrapper(gzip.GzipFile(os.path.join(out_dir, LONG), "wb", mtime=0), newline="") as fl, \
            open(os.path.join(out_dir, DISTRICTS), "w", newline="") as fd:
        wl, wd = csv.writer(fl), csv.writer(fd)
        wl.writerow(COLUMNS)
        wd.writerow(["scenario"] + DISTRICT_COLUMNS)
        for name, _, run in named():
            for r in districts(run):
                wd.writerow([name] + [r.get(c, "") for c in DISTRICT_COLUMNS])
            keys = set()
            with open(os.path.join(run, "ledger.csv"), newline="") as fh:
                for r in csv.DictReader(fh):
                    current, canonical = FINE[r["current_channel"]]
                    key = (r["zip_code"], canonical)
                    if key in keys:
                        sys.exit(f"{name}: {key} twice")
                    if r["rep"]:
                        sys.exit(f"{name}: a rep label in the ledger; masking review needed before export")
                    keys.add(key)
                    wl.writerow([name, r["zip_code"], current, canonical, r["state"], r["model_channel"],
                                 r["district_channels"], r["district"], r["district_channels"], "None", r["m_rel"],
                                 "True" if float(r["m_rel"]) > 0 else "False"])
            total += len(keys)
            print(f"{name:34} {len(keys):7} rows")
    print(f"total {total} rows -> {out_dir}")


def render(out_dir):
    py = os.path.join(TD_REPO, ".venv", "bin", "python3")
    fac = os.path.join(tempfile.mkdtemp(), "fac1.json")
    with open(fac, "w") as fh:
        json.dump({"fac": {c: 1.0 for c in FINE}}, fh)
    env = dict(os.environ, TD_REPO=TD_REPO)
    jobs = []
    for name, family, run in named():
        d = os.path.join(out_dir, "pages", name)
        os.makedirs(d, exist_ok=True)
        jobs.append((family, d, subprocess.Popen(
            [py, "-u", os.path.join(ROOT, "tools", "maps", "zip_pages.py"), run, name, d, "--corridor",
             "--fac", fac, "--no-footer", "--palette", "clean"],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)))
    by_family = collections.defaultdict(list)
    for family, d, p in jobs:
        _, err = p.communicate()
        if p.returncode:
            sys.exit(f"render failed for {d}:\n{err.decode()[-2000:]}")
        by_family[family].append(os.path.join(d, "zip_pages.pdf"))
    for family, pdfs in by_family.items():
        subprocess.run(["pdfunite", *pdfs, os.path.join(out_dir, f"{family}_pages.pdf")], check=True)
        print(f"{family}_pages.pdf: {len(pdfs)} maps")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("data", "render"):
        sys.exit(__doc__)
    {"data": data, "render": render}[sys.argv[1]](sys.argv[2])
