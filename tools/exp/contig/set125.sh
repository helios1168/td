#!/bin/zsh
# #125: the ne_plains_wh11 layout (runs/exp/contig/wh_dollar/s13_WH11.toml) at another K per channel.
# A copy with the K set and every channel declared at δ 0.02 -> replan.py (the smallest δ up to the
# channel's final_delta 0.10; split lists restated unchanged) -> run.py draw (arm 1, sequential,
# border term) -> repair.py pass 1 -> a second pass when M1 still fails -> render.py, check.py, score.py.
# usage: [LAYOUT=ne6] set125.sh <id> <K national> <K WH> <K FI> <K WIFI> [repair.py extra args, e.g. --jobs 2]
# LAYOUT=ne6 (issue item 7): WIFI holds New England only; the plains (ID MT ND NE SD WY NM OK KS) join
# the national, WH and FI domains, with ne6_clean's (2026-10-02) 1600 km distance caps for ID MT ND NE
# SD WY NM.  LAYOUT=ne6m5 is ne6 with WH's max_size 5 (ne6_clean's): at s13's 4, WH 11 has no plan
# below δ 0.647 there.
# Output in $TD_REPO/runs/exp/contig/set125/; run it from the worktree that holds this script.
set -u
export TD_REPO=${TD_REPO:-/Users/Shared/sv-ntlee/td}
P=$TD_REPO/.venv/bin/python3; R=$TD_REPO/runs/exp/contig; S=$R/set125
W=$(cd "$(dirname "$0")/../../.." && pwd)
id=$1; kn=$2; kw=$3; kf=$4; kc=$5; shift 5; extra="$*"
mkdir -p $S/_specs; cd $W
base=$S/_specs/$id-base.toml; sp=$S/_specs/$id.toml
"$P" - $R/wh_dollar/s13_WH11.toml $base $kn $kw $kf $kc ${LAYOUT:-ne_plains} <<'PY'
import re, sys
src, out, *ks, layout = sys.argv[1:]
text = open(src).read()
if layout.startswith("ne6"):
    plains = ["ID", "MT", "ND", "NE", "SD", "WY", "NM", "OK", "KS"]
    wide = "".join(f", {u} = 1600" for u in plains[:6] + ["NM"])
    text = text.replace('units = ["ME", "NH", "VT", "MA", "RI", "CT", ' + ", ".join(f'"{u}"' for u in plains) + "]",
                        'units = ["ME", "NH", "VT", "MA", "RI", "CT"]')
    text = re.sub(r'units = \[("(?:MS|AL)", [^\]]*)\]',
                  lambda m: "units = [" + m.group(1) + "".join(f', "{u}"' for u in plains) + "]", text)
    text = re.sub(r"(?m)^(dist_km = \{.*?) \}$", lambda m: m.group(1) + wide + " }", text)
    assert text.count('"KS"') == 4 and 'CT"]' in text, "ne6 layout edit missed a domain"
    if layout == "ne6m5":
        text = re.sub(r"(?s)(\[channels\.WH\]\n.*?)^max_size = 4$", r"\g<1>max_size = 5", text, count=1,
                      flags=re.M)
for c, k in zip(("national", "WH", "FI", "WIFI"), ks):
    head, sec, rest = re.match(rf"(?s)(.*?\[channels\.{c}\]\n)(.*?)(\n\[.*|\Z)", text).groups()
    sec = re.sub(r"(?m)^k = \d+$", f"k = {k}", sec)
    sec = re.sub(r"(?m)^delta = [\d.]+$", "delta = 0.02", sec)
    text = head + sec + rest
text = re.sub(r'name = "ne_okks_s13_na15_WH11_FI20_CB3"',
              f'name = "{layout}_na{ks[0]}_WH{ks[1]}_FI{ks[2]}_CB{ks[3]}"', text)
open(out, "w").write(f"# #125: a copy of {src} in the {layout} layout with K set and each channel "
                     "declared at δ 0.02\n" + text)
PY
"$P" -u tools/exp/contig/replan.py $base --out-spec $sp --plans $S/_plans --report $S/_specs/$id.json \
  --free national=CA,FL,NY,TX --free WH=CA,FL,NJ,NY,PA,TX --free FI=CA,FL,NC,NY,OH,PA,TN,TX \
  > $S/$id-replan.log 2>&1 || { echo "$id: no plan at ±10%: $(tail -1 $S/$id-replan.log)" > $S/$id.done
  /Users/Shared/sv-ntlee/agent/notify "#125 $id: no plan at ±10%"; exit 1; }
"$P" -u tools/exp/contig/run.py $sp --plans $S/_plans --out $S/$id-draw --arm arm1 --sequential \
  --parent $R/border/ne_plains_wh11-r2-all > $S/$id-draw.log 2>&1
[ -f $S/$id-draw/ledger.csv ] || { echo "$id: draw failed" > $S/$id.done
  /Users/Shared/sv-ntlee/agent/notify "#125 $id: draw failed"; exit 1; }
"$P" -u tools/exp/contig/repair.py $S/$id-draw --out $S/$id-r1 --plans $S/_plans --keep-support --flow \
  --h0 3 --max-zctas 1500 --time-limit 600 --neck-time-limit 120 --budget 1800 \
  --label "#125 $id (ne_plains layout), repair pass 1" ${=extra} > $S/$id-r1.log 2>&1
last=$id-r1
if ! "$P" tools/mandates/check.py $S/$last > /dev/null 2>&1; then
  "$P" -u tools/exp/contig/repair.py $S/$last --out $S/$id-r2 --plans $S/_plans --keep-support --flow \
    --h0 8 --max-zctas 2000 --time-limit 300 --neck-time-limit 240 --budget 1800 \
    --label "#125 $id (ne_plains layout), repair pass 2" ${=extra} > $S/$id-r2.log 2>&1
  [ -f $S/$id-r2/ledger.csv ] && last=$id-r2
fi
"$P" tools/maps/render.py $S/$last > $S/$last.render.log 2>&1
"$P" tools/mandates/check.py $S/$last > $S/$last.check.txt 2>&1
"$P" tools/looks/score.py $S/$last > $S/$last.score.txt 2>&1
echo "$id: $last $(rg -o 'M1 \w+' $S/$last.check.txt | head -1); $(head -c 300 $S/$last.score.txt | tr '\n' ' ')" > $S/$id.done
/Users/Shared/sv-ntlee/agent/notify "#125 $(cat $S/$id.done | head -c 200)"
