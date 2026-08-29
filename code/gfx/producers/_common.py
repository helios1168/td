"""
gfx/producers/_common.py -- shared CLI/loading helpers. Not a producer itself (no NAME/
main entry point picked up by anything; just imported by the producer modules).
"""
from __future__ import annotations

import argparse
import gzip
import json


def load_json(path: str) -> dict:
    """Load a JSON file, transparently gunzipping `.gz` paths (twin_instance.json.gz)."""
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as f:
        return json.load(f)


def load_jsonl(path: str) -> list:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_csv(path: str) -> list:
    import csv
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def base_parser(desc: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=desc)
    p.add_argument("--out", required=True, help="output PNG path")
    return p


def utilities(A, B, M, theta: float = 0.40, lam: float = 0.30):
    """u_a, u_b per zip, the territory.py / contig_methods.base convention -- duplicated
    here (not imported) so the gfx package never depends on a solver module."""
    import numpy as np

    A = np.asarray(A, float); B = np.asarray(B, float); M = np.asarray(M, float)
    c1, c2 = 1.0 - lam, theta * (1.0 - lam)
    return c1 * A + c2 * B + lam * M, c2 * A + c1 * B + lam * M
