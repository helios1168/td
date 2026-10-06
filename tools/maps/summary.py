"""summary.py -- the summary page of a run folder in the 2026-10-02 deck look (#120): the legacy
`plan_summary` (vendored in `tools/maps/legacy/` from tag `archive/pre-support-2026-09`) on the run
adapted to its inputs.  Ported from `runs/autonomous_2026-10-05/batch/{adapt,wrap}.py` (m5,
gitignored), which were copies of `runs/sweep/caps_2026-10-02/`'s.

    "$TD_PY" tools/maps/summary.py <work_dir> --label TEXT --geo-cache DIR [plan_summary flags]

`adapt(run_dir, dst, fac)` writes plan_summary's inputs (`assignment.csv`, `districts.csv`,
`plan.json`, `params.json`) into `dst`.  The spec comes from `run.json`'s `spec` and the dist_max
text from its `max_dist_km`/`dist_km`; the ledger has one row per (ZCTA, fine channel) including
zero-m_rel rows (NO_CELL, DROPPED, #116): those stay in assignment.csv at M_cell 0 as territory
and never enter $ or state shares.  `fac` is $M per m_rel of each current channel.  No
wholesaler is written: reps are out of scope, and no rep or firm name reaches a page.

The CLI runs plan_summary unchanged except: IFA as a business channel, strip and footer text
without the archived staffing model, the strip comparing the mean $ per district with the looks
scorer's target (`tools/looks/score.py` TARGET, DOLLAR_BAND), and the title giving `--label`, the
drawn band (the final ±10%) and the plan's internal bands in brackets.  It runs in its own process
(`tools/maps/render.py`): the legacy code's `td` package shadows today's.
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


def _resolve(path: str) -> str:
    """A path a run recorded, made absolute against `$TD_REPO` when relative."""
    return path if os.path.isabs(path) else os.path.join(os.environ.get("TD_REPO", ROOT), path)


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
    _sizes = " ".join(f"{_ab.get(c, c)} {v['max_size']}" for c, v in _ch.items() if c != "WIFI")
    _main = next(v for c, v in _ch.items() if c != "WIFI")
    _by = collections.defaultdict(list)
    for st, km in _main.get("dist_km", {}).items():
        _by[km].append(st)
    dist_max = f"{_main['max_dist_km']}" + (" (" + "; ".join(f"{km} {' '.join(sorted(sts))}" for km, sts in sorted(_by.items(), reverse=True)) + ")" if _by else "")
    json.dump({"route": "stay", "band_lo": 0.90, "band_hi": 1.10, "dist_max": dist_max, "n_max": 6,
               "bands_text": _bands, "sizes_text": _sizes},
              open(dst + "/params.json", "w"))
    return f"{dst} {len(newid)} districts, {zero} zero-m_rel rows kept as territory only"


def _score_constant(name):
    tree = ast.parse(open(os.path.join(ROOT, "tools", "looks", "score.py")).read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


def main(argv: list) -> int:
    """plan_summary on `argv` (module doc), `--label TEXT` taken out first."""
    sys.path[:0] = [LEGACY, os.path.join(LEGACY, "tools")]
    import plan_summary as ps
    TARGET = _score_constant("TARGET")                  # $ per district, by planning channel
    DOLLAR_BAND = _score_constant("DOLLAR_BAND")
    CHANNEL_OF = {"N": "national", "WH": "WH", "FI": "FI", "WHFI_PLUS": "WIFI", "IFA": "IFA"}

    ps.BUSINESS = ps.BUSINESS + ("IFA",)
    ps.CHANNEL_BUSINESS["IFA"] = "IFA"
    ps.BUNDLE_TITLE.update({"N": "National", "WH": "WH", "FI": "FI", "WHFI_PLUS": "WIFI: national + WH + FI"})

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
        f"whole-ZIP drawing, audited  ·  $ from the channel totals")
    ps.TITLE_IN = 1.35
    argv = list(argv)
    label = None
    if "--label" in argv:
        i = argv.index("--label")
        label = argv[i + 1]
        del argv[i:i + 2]
    ps.title_line = lambda tag, params, n: (f"{label or tag}\ndrawn band ±10% (plan's internal {params['bands_text']})"
                                            f"\ndist_max {params['dist_max']}"
                                            f"  ·  max states/district {params['sizes_text']}")
    return ps.main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
