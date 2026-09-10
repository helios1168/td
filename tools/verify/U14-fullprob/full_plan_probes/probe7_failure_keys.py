"""Re-check of item 5e after the integration edit that adds an optional `passes` key.

`_write_failure` now copies `exc.passes` into the record when the exception carries one, which
`td.solvers.level0.solve_passes` now attaches.  So the "same keys as
`tools/state_splits.py::_write_failure`" contract holds only for a failure raised elsewhere.
Both cases are written here and compared with the reference record.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toy                                                            # noqa: E402,F401
import full_plan as cli                                               # noqa: E402
import state_splits as ss_cli                                         # noqa: E402
from td.solvers import state_splits as ss                             # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as tmp:
        ref_dir, mine = os.path.join(tmp, "ref"), os.path.join(tmp, "mine")
        os.makedirs(ref_dir)
        os.makedirs(mine)
        plain = ss.SolveFailure(2, "The problem is infeasible. (HiGHS Status 8)")
        ss_cli._write_failure(ref_dir, "d0.05", 0.05, plain, 1.0)
        with open(os.path.join(ref_dir, "failure.json"), encoding="utf-8") as fh:
            ref = json.load(fh)

        cli._write_failure(mine, "joint", plain, 1.0)
        with open(os.path.join(mine, "failure.json"), encoding="utf-8") as fh:
            bare = json.load(fh)

        carried = ss.SolveFailure(2, "The problem is infeasible. (HiGHS Status 8)")
        carried.passes = [dict(name="cover_N", value=2.0, certified=True, status=0,
                               seconds=0.1),
                          dict(name="cover_WH", value=None, certified=False, status=2,
                               seconds=0.2)]
        cli._write_failure(mine, "joint", carried, 1.0)
        with open(os.path.join(mine, "failure.json"), encoding="utf-8") as fh:
            withp = json.load(fh)

        print("reference keys:", sorted(ref))
        print("bare failure keys equal:", set(bare) == set(ref), sorted(bare))
        print("carried failure keys equal:", set(withp) == set(ref), sorted(withp))
        print("extra keys:", sorted(set(withp) - set(ref)))
        print("reason/solve_seconds intact:",
              withp["reason"] == ref["reason"], withp["solve_seconds"])


if __name__ == "__main__":
    main()
