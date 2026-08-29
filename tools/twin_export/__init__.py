"""twin_export -- build a privacy-audited synthetic twin of a confidential ZCTA instance.

Runs on the work machine only.  Self-contained: numpy / scipy / networkx, with pandas +
pyarrow expected for the parquet/feather graph cache and geopandas optional.  It never
imports anything from the territory-division repo; the handful of functions it needs from
`code/territory.py` are vendored verbatim in `_territory_vendored.py` and kept honest by a
sync test in the repo.

Two files leave the work machine:

    twin_stats.json        aggregates only, every number k-anonymised (Agg.put)
    twin_instance.json.gz  a synthetic instance on public ZCTA ids, rank-jittered

See README.md for the runbook.
"""
from __future__ import annotations

import sys

__version__ = "1.0.0"

if sys.version_info < (3, 9):
    raise RuntimeError(
        "twin_export needs Python 3.9 or newer (found %d.%d); it is written to run on an "
        "unknown work-machine interpreter, so it uses no 3.10+ syntax, but 3.9 is the floor."
        % (sys.version_info[0], sys.version_info[1]))
