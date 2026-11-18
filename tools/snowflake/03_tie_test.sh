#!/bin/sh
# Runs 03_scenario_test.sh with every edit row at one and the same timestamp (Snowflake's CURRENT_TIMESTAMP can tie
# across statements): the scenario's key edits still win over the sheet, and an owner edit over the key edits, by the
# block order (sheet, key edits, owner edits), not by time.  The two cases ordering key edits inside one block
# (null_before, null_after) are left out: inside a block a tie shows as TWO ANSWERS, loud, not wrong.  One case is added:
# under CA1_R105N an owner edit (R47 role FI, in the owner edits block) wins over the key edit (R47 NATIONAL).
# Prints "03_scenario_test: ok" (with the tie) or stops at the failed check.  Run from anywhere: sh 03_tie_test.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
t=$(mktemp "$here/.tie_XXXXXX")
trap 'rm -f "$t"' EXIT
python3 - "$here/03_scenario_test.sh" "$t" <<'PY'
import sys
s = open(sys.argv[1]).read()
tie = "-e 's/TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()/TIMESTAMP DEFAULT now()/' \\\n"
assert s.count(tie) == 1, "03_scenario_test.sh changed: the timestamp translation is not where the tie test expects it"
s = s.replace(tie, "-e 's/TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()/TIMESTAMP DEFAULT make_timestamp(2026, 1, 1, 0, 0, 0)/' \\\n"
              "    -e \"s/^--owner edits: end\\$/${OWNER:-}\\\\\\\n--owner edits: end/\" \\\n")
s = "\n".join(l for l in s.split("\n") if not l.startswith("case_ null_before") and not l.startswith("case_ null_after"))
s += ('\nOWNER="INSERT INTO ssdb_integration.lr_strategy.tmp_m_edit (holder, role) VALUES (\'R47\', \'FI\');"\n'
      'T_OWNER=$(printf \'%s\' "$T_CA1N" | sed \'s#Lee, Ann|Y|NATIONAL|CA#Lee, Ann|Y|FI|CA#\')\n'
      'case_ owner_beats_key \'CA1_R105N\' "$none" "$none" "$T_OWNER" \'\' \'EDITED\'\n')
open(sys.argv[2], "w").write(s)
PY
sh "$t"
