"""seed_support.py -- #81's variant seed: the support arm's drawn districts as Hess centres.

The variant runs lane A's location–allocation loop (`hess.plan`) from the support arm's map
instead of the k-means seed.  Each district's centre is the opportunity-weighted centroid of the
ZIPs it draws in the support arm's ledger, c_j = Σ_z m_z p_z / Σ_z m_z, with m_z the ZIP's m_rel
summed over its fine-channel cells and p_z its point in km (EPSG:5070, as `hess.positions`).
Centres come in district-id order, so variant district j starts at the support district that
sorts j-th.  Cells with no district (not placed) are skipped.
"""
from __future__ import annotations

import collections
import csv
import math

SUPPORT_LEDGER = ("/Users/Shared/sv-ntlee/td/runs/sweep/looks_2026-10-01/stage2/"
                  "A_fi1600_v1_na16_WH12_FI24/ledger.csv")


def read(path: str, channel: str) -> tuple:
    """({zip: district}, {zip: m_rel}) of `channel`'s placed cells in a ledger."""
    owner, mass = {}, collections.defaultdict(float)
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["model_channel"] != channel or not r["district"]:
                continue
            z = r["zip_code"]
            if owner.setdefault(z, r["district"]) != r["district"]:
                raise ValueError(f"{path}: ZIP {z} has two districts in {channel}")
            mass[z] += float(r["m_rel"])
    return owner, dict(mass)


def centroids(owner: dict, mass: dict, p: dict) -> dict:
    """{district: opportunity-weighted centroid of its ZIPs}, unweighted when its mass is 0."""
    by = collections.defaultdict(list)
    for z, j in owner.items():
        by[j].append(z)
    out = {}
    for j, zs in by.items():
        w = [mass[z] for z in zs] if math.fsum(mass[z] for z in zs) > 0 else [1.0] * len(zs)
        tot = math.fsum(w)
        out[j] = (math.fsum(wi * p[z][0] for wi, z in zip(w, zs)) / tot,
                  math.fsum(wi * p[z][1] for wi, z in zip(w, zs)) / tot)
    return out


def centres(path: str, channel: str, p: dict) -> tuple:
    """(district ids sorted, their centres): the seed of `hess.plan` for `channel`."""
    owner, mass = read(path, channel)
    c = centroids(owner, mass, p)
    ids = sorted(c)
    return ids, [c[j] for j in ids]


def objective(owner: dict, mass: dict, p: dict) -> float:
    """Σ_z m_z ‖p_z − c_j‖², c_j the centroid of z's district: a map's Hess score at its own
    centroids, in m_rel · km²."""
    c = centroids(owner, mass, p)
    return math.fsum(mass[z] * ((p[z][0] - c[j][0]) ** 2 + (p[z][1] - c[j][1]) ** 2)
                     for z, j in owner.items() if mass[z] > 0)
