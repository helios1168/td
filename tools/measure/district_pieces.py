"""District fragmentation measured three ways: by area, by opportunity, by zip count.

Territory here is the union of a district's zips' **real 2025 ZCTA polygons**, the same ground
`geom.json`'s `cells` draw, so a part is a genuinely connected run of published boundaries and a
gap between two of a district's zips counts as a gap.  Nothing is tessellated.

The largest-part statistic is reported on three denominators, because the first one alone
misleads:

    area   -- the share of the district's territory area
    mass   -- the share of the district's M, the quantity stage 1 actually equalises
    zips   -- the share of the district's zip count, the unweighted structural reading

A district is genuinely in pieces when all three are low.  When `area` is low and `mass` is
high, the district is one core plus an outlying rural zip whose ZCTA is physically large and
nearly empty -- `docs/OPTIONS_power-cell-contiguity.md` §3's D01 at 55%, whose second part
carries 0.14% of the district's opportunity.  Area is not what the draw balances.

Each zip is charged to the part its own polygon overlaps most.  Unlike a tessellation these
polygons do not tile the plane, so a zip that meets no part at all is simply not charged.
"""
from __future__ import annotations

import argparse
import os
import sys


def _parts(geom) -> list:
    """The connected polygons of a (multi)polygon, largest first."""
    gs = list(getattr(geom, "geoms", [geom]))
    return sorted((g for g in gs if not g.is_empty), key=lambda g: g.area, reverse=True)


def piece_fractions(cells: dict, districts: dict, values: dict) -> dict:
    """`{district: {...}}` -- the largest-part share on each of the three denominators.

    `cells` is `{zip: polygon}`, the real ZCTA boundaries from `td.geo.zcta_polygons`,
    `districts` is the `{zip: district}` labelling to dissolve by, and `values` is `{zip: M}`.
    Zips absent from `cells` are ignored, since they have no ground to contribute.

    Returned per district: `n_parts`, `area`, `mass`, `zips` (the three largest-part shares),
    `n_zips`, `m_total`, `area_total`, and `parts` -- a list of `(area share, mass share,
    zip count)` for every part, largest-area first, so a caller can see whether the remainder
    is one secondary lobe or a scatter.
    """
    import shapely

    groups: dict = {}
    for z, g in cells.items():
        d = districts.get(z)
        if d is not None:
            groups.setdefault(d, []).append(z)

    out = {}
    for d, zs in groups.items():
        ps = _parts(shapely.make_valid(shapely.union_all([cells[z] for z in zs])))
        area_tot = sum(p.area for p in ps) or 1.0
        charge = {}
        for z in zs:
            c = cells[z]
            charge[z] = max(range(len(ps)),
                            key=lambda i: shapely.make_valid(ps[i]).intersection(c).area)
        m_of = [0.0] * len(ps)
        n_of = [0] * len(ps)
        for z, i in charge.items():
            m_of[i] += max(float(values.get(z, 0.0)), 0.0)
            n_of[i] += 1
        m_tot = sum(m_of) or 1.0
        out[d] = dict(
            n_parts=len(ps),
            area=ps[0].area / area_tot,
            mass=max(m_of) / m_tot,
            zips=max(n_of) / len(zs),
            n_zips=len(zs),
            m_total=sum(m_of),
            area_total=area_tot,
            parts=[(p.area / area_tot, m_of[i] / m_tot, n_of[i]) for i, p in enumerate(ps)],
        )
    return out


def report(fractions: dict, say=print) -> None:
    """One line per district, worst area share first -- the §3 table with its two companions."""
    say(f"{'district':<9}{'parts':>6}{'area':>8}{'mass':>9}{'zips':>8}{'n':>6}")
    for d in sorted(fractions, key=lambda d: (fractions[d]["area"], str(d))):
        r = fractions[d]
        say(f"{str(d):<9}{r['n_parts']:>6}{r['area']:>8.0%}{r['mass']:>9.2%}"
            f"{r['zips']:>8.1%}{r['n_zips']:>6}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("draw", help="a draw.csv from tools/run_draw.py")
    ap.add_argument("instance", nargs="?", default="instance_descaled_v2.json.gz")
    ap.add_argument("--geo-cache", default=None)
    ap.add_argument("--zcta-shp", default=None,
                    help="the TIGER/Line ZCTA520 shapefile the polygons come from")
    ap.add_argument("--detail", default=None, metavar="DISTRICT",
                    help="also list every part of this district")
    args = ap.parse_args(argv)

    root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", ".."))
    for p in (root, os.path.join(root, "tools")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import us_maps as U                                    # noqa: E402
    from td import geo, instance as descaled               # noqa: E402

    cache = args.geo_cache or geo.DEFAULT_DEST
    d = descaled.load_descaled(args.instance)
    M = {z: float(d.G.nodes[z]["M"]) for z in d.G}
    draw = {z: v for z, v in U.read_draw(args.draw).items() if z in M}
    # Real ZCTA polygons, the same ground `geom.json`'s `cells` draw.  A district's parts are
    # then the parts of the union of its own zips' published boundaries, so a gap between two
    # of its zips counts as a gap rather than being tiled over by a catchment.
    polys = geo.zcta_polygons(sorted(draw), args.zcta_shp or geo.ZCTA_SHP)
    cells = {z: polys[z] for z in sorted(draw) if z in polys}

    fr = piece_fractions(cells, draw, M)
    report(fr)
    if args.detail and args.detail in fr:
        r = fr[args.detail]
        print(f"\n{args.detail}: {r['n_parts']} parts, M {r['m_total']:.2f}")
        for i, (a, m, n) in enumerate(r["parts"]):
            print(f"  part {i}: area {a:7.2%}  mass {m:7.2%}  zips {n:4d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
