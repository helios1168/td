"""kgrid_review.py -- the IFA K grid's review bundle (2026-10-13): per K, the run folder's
summary.png, zip_IFA.png, districts.csv, run.json, score.txt and check.txt copied to <out>/K<N>/,
the REVIEW.md table and "needs your eye" lines on stdout, and <out>/REVIEW.pdf (one page per K).

    "$TD_PY" tools/exp/contig/kgrid_review.py <out> [K ...]
"""
import csv, json, os, re, shutil, sys

from PIL import Image

USD = 1.2519681558
LO, HI = 798.74, 1148.19
G = "runs/exp/contig/ifa/kgrid"
FILES = ("summary.png", "zip_IFA.png", "districts.csv", "run.json", "score.txt", "check.txt")


def holders(run_dir):
    """district -> set of states it holds, from the ledger."""
    out = {}
    for r in csv.DictReader(open(os.path.join(run_dir, "ledger.csv"))):
        if r["district"]:
            out.setdefault(r["district"], set()).add(r["state"])
            if r["zip_code"] == "10001":
                out.setdefault("_manhattan", set()).add(r["district"])
    return out


def row(k, out):
    d = f"{G}/K{k}"
    if not os.path.exists(os.path.join(d, "run.json")):
        return f"| {k} | | | | | | | | error (no run folder) | |", [f"K{k}: no run folder"]
    run = json.load(open(os.path.join(d, "run.json")))
    os.makedirs(os.path.join(out, f"K{k}"), exist_ok=True)
    for f in FILES:
        if os.path.exists(os.path.join(d, f)):
            shutil.copy2(os.path.join(d, f), os.path.join(out, f"K{k}", f))
    hold = holders(d)
    manhattan = {x.split("/")[-1] for x in hold.get("_manhattan", ())}
    md = {j for j, s in hold.items() if "MD" in s and not j.startswith("_")}
    ks = [str(len(list(csv.DictReader(open(os.path.join(s["run"], "districts.csv"))))))
          for s in json.load(open(os.path.join(d, "manifest.json")))["source_runs"]]
    score = open(os.path.join(d, "score.txt")).read()
    split = re.search(r"distinct split states: (\d+)", score).group(1)
    gw = run["m1_gap_width"]["failing"] if "m1_gap_width" in run else []
    strict = run["m1_default"]["failing"]
    gw = [x.split("/")[-1] for x in gw]
    strict = [x.split("/")[-1] for x in strict]
    dist = run["districts"]
    usd = {j: v["usd_m"] for j, v in dist.items()}
    under = [j for j, v in dist.items() if v["m_rel"] < LO]
    over = [j for j, v in dist.items() if v["m_rel"] > HI]
    inn = len(dist) - len(under) - len(over)
    dev = {j: max(1000.0 - usd[j], usd[j] - 1437.5, 0.0) for j in dist}
    worst = max(dist, key=lambda j: (dev[j], abs(usd[j] - 1218.75)))
    worst_s = f"{worst} ${usd[worst]:,.1f}M" + (f" ({dev[worst]:,.1f}M outside)" if dev[worst] else " (in)")
    mean = sum(usd.values()) / len(usd)
    m1_other = [j for j in gw if j not in manhattan]
    win_other = [j for j in under + over if j not in md]
    label = ("fails M1" if m1_other else "out of window" if win_other else
             "eligible (Manhattan neck and MD F1 excepted)")
    eye = [f"K{k}: {j} fails M1 (gap width), not the Manhattan neck" for j in m1_other]
    eye += [f"K{k}: {j} out of the window at ${usd[j]:,.1f}M (not the MD F1 district)" for j in win_other]
    m1s = f"{run['m1']['status']} ({', '.join(gw) or 'none'}) / {run['m1_default']['status']} ({', '.join(strict) or 'none'})"
    return (f"| {k} | {'+'.join(ks)} | {split} | {m1s} | {inn}/{len(under)}/{len(over)} | {worst_s} | "
            f"${mean:,.1f}M | {label} | [map](K{k}/summary.png), [ZIP](K{k}/zip_IFA.png) |", eye)


def main(argv):
    out, ks = argv[0], [int(x) for x in argv[1:]] or list(range(48, 55))
    print("| K | region Ks (NE+MA+SA+SC+MW+W) | split states | M1 gap width (failing) / strict (failing) "
          "| districts in/under/over window | worst district | mean $/district | label | map |")
    print("|---|---|---|---|---|---|---|---|---|")
    eye = []
    for k in ks:
        line, e = row(k, out)
        print(line)
        eye += e
    print("\nNeeds your eye (auto):")
    for e in eye:
        print("-", e)
    pages = [Image.open(os.path.join(out, f"K{k}", "summary.png")).convert("RGB")
             for k in ks if os.path.exists(os.path.join(out, f"K{k}", "summary.png"))]
    pages[0].save(os.path.join(out, "REVIEW.pdf"), save_all=True, append_images=pages[1:])


if __name__ == "__main__":
    main(sys.argv[1:])
