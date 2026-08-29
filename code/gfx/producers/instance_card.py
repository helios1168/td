"""
gfx/producers/instance_card.py -- the instance card (PLAN.md Part D "Common figure set").

Panels: pre-merger A/B territories (if per-node rep_a/rep_b are in the instance JSON) ·
free-Nash map · best contiguous incumbent (grey = unsolved) · u_a/u_b heatmaps on a
shared scale · covariate box.

Usage:
    python -m gfx.producers.instance_card <instance.json> --out <png>
"""
from __future__ import annotations

import sys

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from .. import geom, maps, schemas, style
from . import _common


def _rep_legend(reps):
    return [Line2D([], [], marker="o", ls="", color=style.rep_color(i), label=str(r))
            for i, r in enumerate(reps)]


def _best_contiguous_row(rows):
    """Best feasible allocation among `rows` (row schema from contig_methods.base.evaluate):
    prefer status 'optimal'/'optimal_rooted', else the highest LB among feasible rows."""
    if not rows:
        return None
    feasible = [r for r in rows if r.get("feasible") and r.get("to_a") is not None]
    if not feasible:
        return None
    def key(r):
        pref = 0 if str(r.get("status_eff", r.get("status"))).startswith("optimal") else 1
        lb = r.get("LB")
        return (pref, -(lb if lb is not None else float("-inf")))
    return sorted(feasible, key=key)[0]


def build(d: dict) -> plt.Figure:
    v = schemas.validate_instance_json(d)
    if v:
        raise ValueError(f"invalid instance JSON: {v[:5]}")
    style.use_rc()
    nodes = d["nodes"]
    polys, bounds = geom.polys_from_pos(nodes, d["pos"])
    spec = d["spec"]
    theta = spec.get("params", {}).get("theta", 0.40)
    lam = spec.get("params", {}).get("lam", 0.30)
    ua, ub = _common.utilities(d["A"], d["B"], d["M"], theta, lam)
    ua_map = dict(zip(nodes, ua.tolist()))
    ub_map = dict(zip(nodes, ub.tolist()))
    vmin, vmax = float(min(ua.min(), ub.min())), float(max(ua.max(), ub.max()))

    fig, axes = plt.subplots(2, 4, figsize=style.FIGSIZE["card"])
    fig.suptitle(spec.get("name", "instance"), fontsize=11)

    # -- pre-merger territories (optional) -----------------------------------
    if d.get("rep_a") and d.get("rep_b"):
        reps_a = sorted(set(d["rep_a"]))
        reps_b = sorted(set(d["rep_b"]))
        ia = {r: i for i, r in enumerate(reps_a)}
        ib = {r: i for i, r in enumerate(reps_b)}
        ra_of = dict(zip(nodes, d["rep_a"]))
        rb_of = dict(zip(nodes, d["rep_b"]))
        maps.choropleth(axes[0, 0], polys, lambda z: style.rep_color(ia[ra_of[z]]),
                        bounds=bounds, title="pre-merger: firm A territories",
                        legend=_rep_legend(reps_a) if len(reps_a) <= 8 else None)
        maps.choropleth(axes[0, 1], polys, lambda z: style.rep_color(ib[rb_of[z]]),
                        bounds=bounds, title="pre-merger: firm B territories",
                        legend=_rep_legend(reps_b) if len(reps_b) <= 8 else None)
    else:
        for ax, lab in ((axes[0, 0], "A"), (axes[0, 1], "B")):
            ax.axis("off")
            ax.text(0.5, 0.5, f"pre-merger firm-{lab} territories\nnot available for this pair",
                    ha="center", va="center", fontsize=7, transform=ax.transAxes)

    # -- free-Nash map --------------------------------------------------------
    free = set(d.get("free_to_a") or [])
    maps.choropleth(axes[0, 2], polys,
                    lambda z: style.PALETTE["A"] if z in free else style.PALETTE["B"],
                    bounds=bounds, title="free Nash",
                    legend=[Line2D([], [], marker="s", ls="", color=style.PALETTE["A"], label="A"),
                           Line2D([], [], marker="s", ls="", color=style.PALETTE["B"], label="B")])

    # -- best contiguous incumbent (grey = unsolved) --------------------------
    best = _best_contiguous_row(d.get("rows"))
    ax_c = axes[0, 3]
    if best is None:
        maps.choropleth(ax_c, polys, lambda z: style.PALETTE["unsolved"], bounds=bounds,
                        title="best contiguous incumbent\n(unsolved)")
    else:
        to_a = set(best["to_a"])
        maps.choropleth(ax_c, polys,
                        lambda z: style.PALETTE["A"] if z in to_a else style.PALETTE["B"],
                        bounds=bounds,
                        title=f"best contiguous incumbent\n({best.get('method','?')}, "
                              f"{best.get('status_eff', best.get('status','?'))})")

    # -- u_a / u_b heatmaps on a shared scale ---------------------------------
    maps.heatmap(axes[1, 0], polys, ua_map, bounds=bounds, cmap=style.PALETTE["cmap_ua"],
                vmin=vmin, vmax=vmax, title=r"$u_a(z)$", cbar_label="value")
    maps.heatmap(axes[1, 1], polys, ub_map, bounds=bounds, cmap=style.PALETTE["cmap_ub"],
                vmin=vmin, vmax=vmax, title=r"$u_b(z)$", cbar_label="value")

    # -- covariate box ---------------------------------------------------------
    ax_cov = axes[1, 2]
    ax_cov.axis("off")
    cov = d.get("covariates") or {}
    lines = [f"n = {len(nodes)}", f"tier = {spec.get('tier')}", f"seed = {spec.get('seed')}"]
    for k in ("pair_components", "articulation_points", "block_tree_is_path",
              "active_frac", "gini_u", "top5_share_u", "n_states"):
        if k in cov:
            val = cov[k]
            lines.append(f"{k} = {val:.3g}" if isinstance(val, float) else f"{k} = {val}")
    ax_cov.text(0.0, 1.0, "\n".join(lines), family="monospace", fontsize=7, va="top",
               transform=ax_cov.transAxes)
    ax_cov.set_title("covariates", fontsize=8)

    axes[1, 3].axis("off")
    style.tight_layout(fig)
    return fig


def main(argv=None):
    p = _common.base_parser(__doc__)
    p.add_argument("instance_json")
    args = p.parse_args(argv)
    d = _common.load_json(args.instance_json)
    fig = build(d)
    style.check_text_overlap(fig)
    style.save(fig, args.out, inputs=[args.instance_json], producer="instance_card")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
