"""instance_diff.py -- compare two descaled instances, separating rescale from re-estimation.

    .venv/bin/python3 tools/measure/instance_diff.py OLD.json.gz NEW.json.gz
    .venv/bin/python3 tools/measure/instance_diff.py OLD.json.gz NEW.json.gz --json out.json

Why this exists.  `m_rel = M / median(positive M)`, so the descaling divisor is a property of
the *export*, not of the world.  When it moves between exports every zip's `m_rel` moves with
it, and a raw `m_rel` ratio conflates two different things:

  * a **uniform rescale**, which by scale invariance is a no-op -- it shifts `sum_i log g_i` by
    `n log kappa`, the same constant for every partition, so it cannot move an optimum, a gap or
    a certificate; and
  * a genuine **re-estimation** of a zip's opportunity, which moves everything.

The divisor ratio is recoverable without ever seeing a currency amount.  Zips whose dollar
opportunity did not change all land on the single constant `K = divisor_old / divisor_new`, so
`K` is the *mode* of the ratio distribution and `f = ratio / K` is the real per-zip change.
Measured on v1 -> v2 (2026-09-04): `K = 1.650015` with 440 of 1,229 shared zips at `f = 1`,
which is why the raw ratios looked like a flat multiplier applied to a block.  They were the
zips that had not moved at all.

Caveat on the source format: the upstream table has one row per *zip x rep*, with the zip's
opportunity repeated on every row.  Sales sum cleanly across rows; opportunity does not.  The
exporter already collapses this -- `nodes.z` and `nodes.m_rel` are parallel, one entry per zip --
so nothing here double-counts.  `--row-inflation` reports what a naive row-sum *would* have
inflated each export by, which is the number to check a dollar total against.

Read-only over `td/`.  Prints a report; `--json` also writes a manifest with both instance
hashes so a run is reproducible.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
from typing import Any

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "..", "..")))
from td import instance  # noqa: E402

Zip = str
UNCH_TOL = 2e-5          # |f - 1| below this is "unchanged"; the export carries 6 sig figs
MODE_HALFWIDTH = 1e-4    # relative half-width of the window used to locate the divisor mode


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _M(G: Any, z: Zip) -> float:
    return float(G.nodes[z]["M"])


def _book(G: Any, z: Zip) -> float:
    return sum(float(v) for v in (G.nodes[z].get("S") or {}).values())


def _free(G: Any, z: Zip) -> float:
    return float(G.nodes[z].get("S_free", 0.0) or 0.0)


def divisor_ratio(ratios: np.ndarray) -> float:
    """`K = divisor_old / divisor_new`, read off as the mode of the ratio distribution.

    Unchanged zips share one exact ratio up to export rounding, so the mode is a spike.  A
    coarse histogram locates it; the median of the spike's window is the estimate.
    """
    if ratios.size == 0:
        raise ValueError("no shared zips: the two instances have no zip in common")
    logs = np.log(ratios)
    counts, edges = np.histogram(logs, bins=max(32, int(np.sqrt(ratios.size))))
    lo, hi = edges[int(np.argmax(counts))], edges[int(np.argmax(counts)) + 1]
    peak = ratios[(logs >= lo) & (logs <= hi)]
    k = float(np.median(peak))
    window = np.abs(ratios / k - 1.0) < MODE_HALFWIDTH
    return float(np.median(ratios[window])) if window.any() else k


def composition(G: Any) -> dict[str, int]:
    """Zip counts by candidacy class, in `docs/CHANNEL.md`'s vocabulary."""
    out = {"contested": 0, "uncontested": 0, "vacant": 0, "untapped": 0}
    for z in G:
        n = sum(1 for v in (G.nodes[z].get("S") or {}).values() if float(v) > 0)
        if n >= 2:
            out["contested"] += 1
        elif n == 1:
            out["uncontested"] += 1
        elif _free(G, z) > 0:
            out["vacant"] += 1
        else:
            out["untapped"] += 1
    return out


def saturation(G: Any, zips: list[Zip] | None = None) -> float:
    zs = list(G) if zips is None else zips
    den = sum(_M(G, z) for z in zs)
    return (sum(_book(G, z) for z in zs) / den) if den else 0.0


def row_inflation(G: Any) -> float:
    """What summing the opportunity column over source rows would inflate the total by."""
    tot = rows = 0.0
    for z in G:
        m = _M(G, z)
        tot += m
        rows += max(1, sum(1 for v in (G.nodes[z].get("S") or {}).values() if float(v) > 0)) * m
    return rows / tot if tot else float("nan")


def untapped_mass(G: Any) -> float:
    return sum(_M(G, z) for z in G if _book(G, z) <= 0 and _free(G, z) <= 0)


def compare(old_path: str, new_path: str) -> dict[str, Any]:
    a, b = instance.load_descaled(old_path), instance.load_descaled(new_path)
    Ga, Gb = a.G, b.G
    za, zb = set(Ga.nodes), set(Gb.nodes)
    shared = sorted(za & zb)

    ma = np.array([_M(Ga, z) for z in shared])
    mb = np.array([_M(Gb, z) for z in shared])
    ratio = mb / ma
    K = divisor_ratio(ratio)
    f = ratio / K
    unch = np.abs(f - 1.0) < UNCH_TOL
    moved = f[~unch]

    tot_a = sum(_M(Ga, z) for z in Ga)
    tot_b = sum(_M(Gb, z) for z in Gb)
    unt_a, unt_b = untapped_mass(Ga), untapped_mass(Gb)

    return dict(
        old=os.path.abspath(old_path), new=os.path.abspath(new_path),
        old_sha256=sha256(old_path), new_sha256=sha256(new_path),
        n_zips_old=len(za), n_zips_new=len(zb),
        n_reps_old=len(a.reps), n_reps_new=len(b.reps),
        reps_retained=len(set(a.reps) & set(b.reps)),
        shared=len(shared), only_old=len(za - zb), only_new=len(zb - za),
        old_is_subset=bool(not (za - zb)),
        divisor_ratio_K=K,
        n_unchanged=int(unch.sum()), n_grew=int((f > 1 + UNCH_TOL).sum()),
        n_shrank=int((f < 1 - UNCH_TOL).sum()),
        unchanged_mass_share_old=float(ma[unch].sum() / ma.sum()) if ma.size else 0.0,
        f_percentiles={str(p): float(np.percentile(f, p))
                       for p in (0, 1, 5, 25, 50, 75, 95, 99, 100)},
        f_moved_median=float(np.median(moved)) if moved.size else float("nan"),
        f_moved_max=float(moved.max()) if moved.size else float("nan"),
        total_old=float(tot_a), total_new=float(tot_b),
        total_new_in_old_units=float(tot_b / K),
        real_growth_all=float((tot_b / K) / tot_a),
        real_growth_worked=float(((tot_b - unt_b) / K) / (tot_a - unt_a)),
        untapped_share_old=float(unt_a / tot_a), untapped_share_new=float(unt_b / tot_b),
        composition_old=composition(Ga), composition_new=composition(Gb),
        saturation_old=saturation(Ga), saturation_new=saturation(Gb),
        saturation_shared_old=saturation(Ga, shared), saturation_shared_new=saturation(Gb, shared),
        book_growth_shared=float((sum(_book(Gb, z) for z in shared) / K)
                                 / sum(_book(Ga, z) for z in shared)),
        M_growth_shared=float((mb.sum() / K) / ma.sum()),
        row_inflation_old=row_inflation(Ga), row_inflation_new=row_inflation(Gb),
        unchanged_tol=UNCH_TOL,
    )


def report(d: dict[str, Any]) -> str:
    L = []
    L.append(f"zips      {d['n_zips_old']:>8,} -> {d['n_zips_new']:>8,}"
             f"   ({'old is a strict subset' if d['old_is_subset'] else str(d['only_old']) + ' dropped'}"
             f", {d['only_new']:,} new)")
    L.append(f"reps      {d['n_reps_old']:>8,} -> {d['n_reps_new']:>8,}   ({d['reps_retained']} retained)")
    L.append("")
    L.append(f"divisor ratio K = {d['divisor_ratio_K']:.9f}   (a uniform rescale: a no-op for the objective)")
    L.append(f"  of {d['shared']:,} shared zips: {d['n_unchanged']:,} unchanged, "
             f"{d['n_grew']:,} grew, {d['n_shrank']:,} shrank")
    L.append(f"  unchanged hold {d['unchanged_mass_share_old']*100:.1f}% of the old total")
    if d["n_grew"] or d["n_shrank"]:
        L.append(f"  among movers: median x{d['f_moved_median']:.4f}, max x{d['f_moved_max']:.3f}")
    L.append("")
    L.append(f"real growth   all opportunity x{d['real_growth_all']:.4f}"
             f"    worked zips only x{d['real_growth_worked']:.4f}")
    L.append(f"  total {d['total_old']:,.1f} -> {d['total_new']:,.1f} "
             f"({d['total_new_in_old_units']:,.1f} in old units)")
    L.append("")
    co, cn = d["composition_old"], d["composition_new"]
    L.append("composition   contested  uncontested  vacant  untapped")
    L.append(f"  old        {co['contested']:>9,} {co['uncontested']:>12,} {co['vacant']:>7,} {co['untapped']:>9,}")
    L.append(f"  new        {cn['contested']:>9,} {cn['uncontested']:>12,} {cn['vacant']:>7,} {cn['untapped']:>9,}")
    L.append(f"  untapped share of opportunity: {d['untapped_share_old']*100:.1f}% -> {d['untapped_share_new']*100:.1f}%")
    L.append("")
    L.append(f"saturation    {d['saturation_old']*100:.1f}% -> {d['saturation_new']*100:.1f}%")
    L.append(f"  on shared zips only: {d['saturation_shared_old']*100:.1f}% -> {d['saturation_shared_new']*100:.1f}%"
             f"  (M x{d['M_growth_shared']:.4f} vs book x{d['book_growth_shared']:.4f})")
    L.append("")
    L.append(f"row inflation (what a naive row-sum of opportunity would give): "
             f"old x{d['row_inflation_old']:.4f}, new x{d['row_inflation_new']:.4f}")
    L.append("  -- different factors, so a dollar total taken that way is not comparable across exports")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("old", help="the earlier instance_descaled*.json.gz")
    ap.add_argument("new", help="the later one")
    ap.add_argument("--json", dest="out", default=None, help="also write the manifest here")
    args = ap.parse_args(argv)

    d = compare(args.old, args.new)
    print(report(d))
    if args.out:
        payload = dict(d, written=_dt.datetime.now().isoformat(timespec="seconds"))
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
