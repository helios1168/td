"""Export a run folder's ledger in the nationwide long schema the owner's database already holds
(archive `tools/export_all_scenarios_nationwide_long.py`, 2026-09-14): one row per (scenario, ZCTA,
source channel), columns exactly `scenario, zip_code, current_channel, canonical_channel, state,
model_channel, bundle, district, district_channels, rep, m_rel, has_commercial_opportunity`.

The scenario id is the run id (unique on the shortlist); `scenarios.csv` beside the file ties it to
the code commit, the branch, the spec and extract hashes and the source runs, so a row can be traced
to the exact solver run.  No dollars, no shares, no reps, no firms.

    "$TD_PY" tools/exp/contig/export_long.py <run_dir> [--branch NAME] [--rank N]
"""
import argparse, csv, datetime, gzip, json, os, subprocess, sys

COLUMNS = ["scenario", "zip_code", "current_channel", "canonical_channel", "state", "model_channel",
           "bundle", "district", "district_channels", "rep", "m_rel", "has_commercial_opportunity"]
SCENARIO_COLUMNS = ["scenario", "legacy_id", "k_total", "channels", "run_id", "run_folder", "branch", "commit",
                    "code_commit", "code_dirty", "spec_sha256", "instance_sha256", "source_runs",
                    "m1", "m1_gate", "shortlist_rank", "exported_at"]
# the extract's channel spellings -> the database's canonical names and bundles (archive exporter's
# SUBCHANNELS table, IFA added as its own bundle)
CANON = {"ifa": ("ifa", "IFA"), "National (Chase)": ("national_chase", "N"), "Wells WH": ("national_wells_wh", "N"),
         "Wells FI": ("national_wells_fi", "N"), "WH": ("wh", "WH"), "FI": ("fi", "FI")}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--branch", default=None, help="the branch the run folder is published on")
    ap.add_argument("--rank", default="", help="the shortlist rank, once registered")
    a = ap.parse_args(argv)
    run_dir = os.path.abspath(a.run_dir)
    man = json.load(open(os.path.join(run_dir, "manifest.json")))
    run_id = man["run_id"]
    rows = list(csv.DictReader(open(os.path.join(run_dir, "ledger.csv"))))
    out_dir = os.path.join(run_dir, "export")
    os.makedirs(out_dir, exist_ok=True)
    name = f"{run_id}_nationwide_zcta_long.csv"
    k = {}
    with open(os.path.join(out_dir, name), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            canon, bundle = CANON.get(r["current_channel"], (r["current_channel"].lower(), r["model_channel"]))
            m = float(r["m_rel"] or 0.0)
            k.setdefault(r["model_channel"], set()).add(r["district"])
            w.writerow({"scenario": run_id, "zip_code": r["zip_code"], "current_channel": r["current_channel"],
                        "canonical_channel": canon, "state": r["state"], "model_channel": r["model_channel"],
                        "bundle": bundle, "district": r["district"], "district_channels": r["district_channels"],
                        "rep": "", "m_rel": f"{m:.6f}", "has_commercial_opportunity": m > 0})
    with open(os.path.join(out_dir, name), "rb") as src, gzip.open(os.path.join(out_dir, name + ".gz"), "wb") as dst:
        dst.writelines(src)
    counts = {ch: len(d) for ch, d in sorted(k.items())}
    legacy = f"{sum(counts.values())}_total_" + "_".join(f"{n}{ch.lower()}" for ch, n in counts.items())
    branch = a.branch or subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True,
                                        cwd=run_dir).stdout.strip()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=run_dir).stdout.strip()
    prov = man.get("provenance", {})
    scen = {"scenario": run_id, "legacy_id": legacy, "k_total": sum(counts.values()),
            "channels": ";".join(f"{ch}={n}" for ch, n in counts.items()), "run_id": run_id,
            "run_folder": os.path.relpath(run_dir, subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                                                  capture_output=True, text=True, cwd=run_dir).stdout.strip()),
            "branch": branch, "commit": commit, "code_commit": prov.get("commit", ""), "code_dirty": prov.get("dirty", ""),
            "spec_sha256": man.get("scenario", {}).get("sha256", ""), "instance_sha256": prov.get("instance_sha256", ""),
            "source_runs": ";".join(f"{os.path.basename(os.path.dirname(s['run']))}/{os.path.basename(s['run'])}@{s['commit'][:7]}"
                                    for s in man.get("source_runs", [])),
            "m1": man.get("m1", ""), "m1_gate": man.get("m1_gate", ""), "shortlist_rank": a.rank,
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    with open(os.path.join(out_dir, "scenarios.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SCENARIO_COLUMNS)
        w.writeheader()
        w.writerow(scen)
    print(f"{name}: {len(rows)} rows, scenario {run_id} (legacy id {legacy}); scenarios.csv written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
