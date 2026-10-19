"""Make a synthetic stand-in for the live sales table, shaped like the 2026-10-18 profile
(`00_profile.sql`): two firms, one channelized (specialists, one home channel each) and one not
(generalists working every channel on a smaller territory), four channels, real public ZIPs,
every name and number made up.  Nothing is read from the live data.

Writes to data/safe/ (gitignored):
  td_synth.csv.gz   raw(zip_code, firm, wholesaler, channel, opportunity, sales), channel = the firm's own
  channel_map.csv   (firm, source_channel, channel): the generalist firm's codes -> the channelized firm's
  territory.csv     (firm, wholesaler, zip_code, channel): assigned territories, channel = the channelized firm's
  td_synth_truth.csv the answer key: each wholesaler's role, home channel and latent skill

Opportunity sits on firm A's rows only and is NULL on firm B's, as in the live table, so it sums
once per (zip, channel); a few cells only firm B works carry none.  Sales are opportunity x channel base rate x skill x firm effect x noise, with the same effort per
zip for both roles: an index that recovers skill for both roles is measuring people, not time
split.  Out-of-territory sales come from three places: specialists' stray sales in other channels,
sales in another wholesaler's zips, and orphan zips no territory holds.  `--check` loads the files
into DuckDB, runs 03_rank.sql and 05_rank_territory.sql, and prints how they track the answer key.

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
    firm_of = {t["wholesaler"]: t["firm"] for t in truth}
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
    # sales in another wholesaler's zips: a same-firm colleague who could work that channel
    pool = {(f, c): sorted({w for (cell, ff), w in owner.items() if ff == f and cell[1] == c})
            for f in (FIRM_A, FIRM_B) for c in CHANNELS}
    for cell in cells:
        if rng.random() < 0.03:
            f = rng.choice(sorted(cover[cell]))
            w = rng.choice(pool[f, cell[1]])
            if w != owner[cell, f]:
                spill.setdefault(cell, []).append(w)
    orphans = set(rng.sample(zs, len(zs) * 3 // 100))   # zips no territory holds; their sales stay
    territory = sorted((f, w, cell[0], cell[1]) for (cell, f), w in owner.items() if cell[0] not in orphans)
    rows = []
    for cell in cells:
        z, c = cell
        opp = round(math.exp(rng.gauss(0, 1.2)), 4)
        both = len(cover[cell]) == 2
        slots = [(f, owner[cell, f], 1.0) for f in sorted(cover[cell])]
        slots += [(firm_of[w], w, 0.2) for w in spill.get(cell, [])]
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
        # opportunity lives on firm A's rows only (NULL on firm B's), so a plain SUM counts it once;
        # a cell only firm B works gets an A row that carries it, except a few that have none
        a_idx = [i for i, r in enumerate(crow) if r[1] == FIRM_A]
        if not a_idx and rng.random() < 0.95:
            crow.append([z, FIRM_A, "VACANT", c, 0.0, 0.0])
            a_idx = [len(crow) - 1]
        for r in crow:
            if r[1] == FIRM_B:
                r[4] = None
        if len(a_idx) > 1 and rng.random() < 0.05:       # opportunity split over two rows
            crow[a_idx[0]][4], crow[a_idx[1]][4] = round(opp * 0.6, 4), round(opp * 0.4, 4)
        elif a_idx:
            crow[a_idx[0]][4] = opp                      # opportunity on one row, the rest 0
        rows += crow
    for r in rng.sample(rows, 14):                       # reversals
        rows.append([r[0], r[1], r[2], r[3], None if r[1] == FIRM_B else 0.0, -round(rng.uniform(0.001, 0.01), 4)])
    for r in rng.sample([r for r in rows if r[4] == 0.0], 14):  # opportunity adjustments
        r[4] = -round(rng.uniform(0.001, 0.01), 4)
    r = rng.choice(rows)
    rows.append([None, r[1], r[2], r[3], None if r[1] == FIRM_B else 0.0, round(rng.uniform(0.01, 0.1), 4)])  # one row with no ZIP
    rng.shuffle(rows)
    return rows, truth, territory


def write(rows, truth, territory):
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
    with open(os.path.join(OUT, "territory.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["firm", "wholesaler", "zip_code", "channel"])
        w.writerows(territory)
    with open(os.path.join(OUT, "td_synth_truth.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(truth[0]))
        w.writeheader()
        w.writerows(truth)


def check():
    def q(name):
        return open(os.path.join(ROOT, "tools", "snowflake", name)).read().strip().rstrip(";")
    sql = q("03_rank.sql")
    d = OUT
    script = f"""
CREATE TABLE raw AS SELECT * FROM read_csv('{d}/td_synth.csv.gz', types={{'zip_code': 'VARCHAR'}});
CREATE TABLE channel_map AS SELECT * FROM read_csv('{d}/channel_map.csv');
CREATE TABLE filler_keys AS SELECT 'VACANT' AS key;
CREATE TABLE truth AS SELECT * FROM read_csv('{d}/td_synth_truth.csv');
CREATE TABLE territory AS SELECT * FROM read_csv('{d}/territory.csv', types={{'zip_code': 'VARCHAR'}});
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
{q("04_territory_profile.sql")};
CREATE TABLE ranked_t AS {q("05_rank_territory.sql")};
-- territory ranking: index per unit of ability (1.0 = fair) and tracking, with and without outside sales
WITH w AS (SELECT DISTINCT r.wholesaler, r.index_overall, r.index_territory_only, r.out_share, t.role,
                  t.skill * CASE r.firm WHEN '{FIRM_A}' THEN {FIRM_EFFECT[FIRM_A]} ELSE {FIRM_EFFECT[FIRM_B]} END AS ability
           FROM ranked_t r JOIN truth t USING (wholesaler))
SELECT role, COUNT(*) AS n, ROUND(AVG(out_share), 3) AS out_share,
       ROUND(AVG(index_overall / ability), 3) AS with_outside_per_ability,
       ROUND(AVG(index_territory_only / ability), 3) AS territory_only_per_ability,
       ROUND(CORR(index_overall, ability), 3) AS corr_with_outside,
       ROUND(CORR(index_territory_only, ability), 3) AS corr_territory_only
FROM w GROUP BY role ORDER BY role;
"""
    r = subprocess.run(["duckdb", "-box"], input=script, capture_output=True, text=True)
    sys.stdout.write(r.stdout + r.stderr)
    return r.returncode


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    rows, truth, territory = build(a.seed)
    write(rows, truth, territory)
    cells = len({(r[0], B_CODES.get(r[3], r[3])) for r in rows})
    print(f"{OUT}: {len(rows)} rows, {cells} cells, {len(truth)} wholesalers")
    return check() if a.check else 0


if __name__ == "__main__":
    sys.exit(main())
