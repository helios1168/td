"""Make a synthetic stand-in for the live sales table, shaped like the 2026-10-18 profile
(`00_profile.sql`): two firms, one channelized (specialists, one home channel each) and one not
(generalists working every channel on a smaller territory), four channels, real public ZIPs,
every name and number made up.  Nothing is read from the live data.

Writes to data/safe/ (gitignored):
  td_synth.csv.gz   raw(zip_code, firm, wholesaler, channel, opportunity, sales), channel = the firm's own
  channel_map.csv   (firm, source_channel, channel): the generalist firm's codes -> the channelized firm's
  td_synth_truth.csv the answer key: each wholesaler's role, home channel and latent skill

Sales are opportunity x channel base rate x skill x firm effect x noise, with the same effort per
zip for both roles: an index that recovers skill for both roles is measuring people, not time
split.  `--check` loads the files into DuckDB, runs 03_rank.sql, and prints how its ranks and
plain within-channel volume track the answer key.

    python3 tools/snowflake/synth.py [--seed 7] [--check]
"""
import argparse, csv, gzip, math, os, random, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(os.environ.get("TD_REPO", ROOT), "data", "safe")
CHANNELS = {"IFA": 0.86, "FI": 0.46, "National": 0.38, "WH": 0.14}   # share of ZIPs with the channel
BASE = {"IFA": 0.15, "FI": 0.10, "National": 0.08, "WH": 0.12}       # channel penetration
SPECIALISTS = {"IFA": 26, "FI": 18, "National": 16, "WH": 10}       # firm A, 70 in all
N_GENERALISTS = 70                                                   # firm B
FIRM_A, FIRM_B = "FX001", "FX002"
FIRM_EFFECT = {FIRM_A: 1.0, FIRM_B: 0.9}
# firm B's own channel codes; two of them fold into National
B_CODES = {"B1": "FI", "B2": "IFA", "B3": "National", "B4": "National", "B5": "WH"}


def zips(n, rng):
    path = os.path.join(ROOT, "reference", "2025", "zcta_reference.csv.gz")
    with gzip.open(path, "rt") as fh:
        z = [r["zcta"] for r in csv.DictReader(fh) if r["graph_vertex"] == "1"]
    return sorted(rng.sample(z, n))          # sorted ZIPs are roughly geographic, so chunks are territories


def chunks(seq, k):
    return [seq[i * len(seq) // k:(i + 1) * len(seq) // k] for i in range(k)]


def build(seed):
    rng = random.Random(seed)
    zs = zips(10000, rng)
    cells = [(z, c) for z in zs for c, f in CHANNELS.items() if rng.random() < f]
    # which firm covers each cell: A only, B only, or both
    cover = {}
    for cell in cells:
        u = rng.random()
        cover[cell] = {FIRM_A} if u < 0.35 else {FIRM_B} if u < 0.70 else {FIRM_A, FIRM_B}
    truth, owner = [], {}
    n = 0
    for c, k in SPECIALISTS.items():         # firm A: each channel's cells split among its specialists
        mine = [cell for cell in cells if cell[1] == c and FIRM_A in cover[cell]]
        for part in chunks(mine, k):
            n += 1
            w = f"WX{n:04d}"
            truth.append({"wholesaler": w, "firm": FIRM_A, "role": "specialist", "home_channel": c,
                          "skill": round(math.exp(rng.gauss(0, 0.35)), 4)})
            for cell in part:
                owner[cell, FIRM_A] = w
    terr = chunks(zs, N_GENERALISTS)         # firm B: each generalist works every channel in a smaller territory
    for part in terr:
        n += 1
        w = f"WX{n:04d}"
        truth.append({"wholesaler": w, "firm": FIRM_B, "role": "generalist", "home_channel": "",
                      "skill": round(math.exp(rng.gauss(0, 0.35)), 4)})
        for z in part:
            for c in CHANNELS:
                if (z, c) in cover and FIRM_B in cover[z, c]:
                    owner[(z, c), FIRM_B] = w
    skill = {t["wholesaler"]: t["skill"] for t in truth}
    b_code = {c: [k for k, v in B_CODES.items() if v == c] for c in CHANNELS}
    # firm A specialists also show some sales outside their home channel (only 10 of 140 sell in one channel)
    home = {}
    for (cell, f), w in owner.items():
        if f == FIRM_A:
            home.setdefault(w, set()).add(cell[0])
    spill = {}
    for w, zset in home.items():
        for z in zset:
            for c in CHANNELS:
                if (z, c) in cover and FIRM_A in cover[z, c] and owner[(z, c), FIRM_A] != w and rng.random() < 0.08:
                    spill.setdefault((z, c), []).append(w)
    rows = []
    for cell in cells:
        z, c = cell
        opp = round(math.exp(rng.gauss(0, 1.2)), 4)
        both = len(cover[cell]) == 2
        slots = [(f, owner[cell, f], 1.0) for f in sorted(cover[cell])]
        slots += [(FIRM_A, w, 0.2) for w in spill.get(cell, [])]
        crow = []
        for f, w, effort in slots:
            code = c if f == FIRM_A else rng.choice(b_code[c])
            if rng.random() < 0.35:
                s = 0.0                                  # a row in the territory with no sales
            else:
                s = opp * BASE[c] * skill[w] * FIRM_EFFECT[f] * effort * (0.75 if both else 1.0)
                s = round(min(s * math.exp(rng.gauss(0, 0.5)), 0.9 * opp / len(slots)), 4)
            if rng.random() < 0.015:
                w = "VACANT"                             # a vacancy holds this book
            parts = rng.choice([2, 3, 4]) if rng.random() < 0.08 else 1    # the unknown extra grain
            for i in range(parts):
                crow.append([z, f, w, code, 0.0, round(s / parts, 4)])
        if len(crow) > 1 and rng.random() < 0.05:        # opportunity split over two rows
            crow[0][4], crow[1][4] = round(opp * 0.6, 4), round(opp * 0.4, 4)
        else:
            crow[0][4] = opp                             # opportunity on one row, the rest 0
        rows += crow
    for r in rng.sample(rows, 14):                       # reversals
        rows.append([r[0], r[1], r[2], r[3], 0.0, -round(rng.uniform(0.001, 0.01), 4)])
    for r in rng.sample([r for r in rows if r[4] == 0.0], 14):  # opportunity adjustments
        r[4] = -round(rng.uniform(0.001, 0.01), 4)
    r = rng.choice(rows)
    rows.append([None, r[1], r[2], r[3], 0.0, round(rng.uniform(0.01, 0.1), 4)])  # one row with no ZIP
    rng.shuffle(rows)
    return rows, truth


def write(rows, truth):
    os.makedirs(OUT, exist_ok=True)
    with gzip.open(os.path.join(OUT, "td_synth.csv.gz"), "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["zip_code", "firm", "wholesaler", "channel", "opportunity", "sales"])
        w.writerows(["" if v is None else v for v in r] for r in rows)
    with open(os.path.join(OUT, "channel_map.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["firm", "source_channel", "channel"])
        w.writerows([FIRM_A, c, c] for c in CHANNELS)
        w.writerows([FIRM_B, k, v] for k, v in B_CODES.items())
    with open(os.path.join(OUT, "td_synth_truth.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(truth[0]))
        w.writeheader()
        w.writerows(truth)


def check():
    sql = open(os.path.join(ROOT, "tools", "snowflake", "03_rank.sql")).read().strip().rstrip(";")
    d = OUT
    script = f"""
CREATE TABLE raw AS SELECT * FROM read_csv('{d}/td_synth.csv.gz', types={{'zip_code': 'VARCHAR'}});
CREATE TABLE channel_map AS SELECT * FROM read_csv('{d}/channel_map.csv');
CREATE TABLE filler_keys AS SELECT 'VACANT' AS key;
CREATE TABLE truth AS SELECT * FROM read_csv('{d}/td_synth_truth.csv');
SELECT COUNT(*) AS unmapped FROM raw r LEFT JOIN channel_map cm
  ON cm.firm = r.firm AND cm.source_channel = r.channel WHERE cm.channel IS NULL;
CREATE TABLE ranked AS {sql};
-- how each measure tracks the answer key (skill x firm effect), by role
WITH w AS (SELECT DISTINCT r.wholesaler, r.index_overall, t.role,
                  t.skill * CASE r.firm WHEN '{FIRM_A}' THEN {FIRM_EFFECT[FIRM_A]} ELSE {FIRM_EFFECT[FIRM_B]} END AS ability
           FROM ranked r JOIN truth t USING (wholesaler)),
v AS (SELECT r.channel, r.wholesaler, t.role, r.perf_index, r.sales,
             t.skill * CASE r.firm WHEN '{FIRM_A}' THEN {FIRM_EFFECT[FIRM_A]} ELSE {FIRM_EFFECT[FIRM_B]} END AS ability,
             RANK() OVER (PARTITION BY r.channel ORDER BY r.sales DESC) AS volume_rank, r.ranked_in_channel, r.rank_in_channel
      FROM ranked r JOIN truth t USING (wholesaler)
      WHERE t.role = 'generalist' OR t.home_channel = r.channel)
SELECT 'overall' AS measure, role, COUNT(*) AS n, ROUND(CORR(index_overall, ability), 3) AS corr_with_ability, NULL AS mean_pct_rank
FROM w GROUP BY role
UNION ALL
SELECT 'channel index', role, COUNT(*), ROUND(CORR(perf_index, ability), 3), ROUND(AVG(rank_in_channel / ranked_in_channel), 3) FROM v GROUP BY role
UNION ALL
SELECT 'channel volume', role, COUNT(*), ROUND(CORR(sales, ability), 3), ROUND(AVG(volume_rank / ranked_in_channel), 3) FROM v GROUP BY role
ORDER BY 1, 2;
SELECT COUNT(DISTINCT wholesaler) AS wholesalers, COUNT(*) AS wholesaler_channels FROM ranked;
"""
    r = subprocess.run(["duckdb", "-box"], input=script, capture_output=True, text=True)
    sys.stdout.write(r.stdout + r.stderr)
    return r.returncode


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    rows, truth = build(a.seed)
    write(rows, truth)
    cells = len({(r[0], B_CODES.get(r[3], r[3])) for r in rows})
    print(f"{OUT}: {len(rows)} rows, {cells} cells, {len(truth)} wholesalers")
    return check() if a.check else 0


if __name__ == "__main__":
    sys.exit(main())
