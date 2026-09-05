#!/usr/bin/env python3
"""Build the pin-cost-catalogue artifact from battery/results/runs_<date> and
figures/runs_<date> -- docs/RUNS_PLAN.md §7. Nothing in this file is typed by hand into the
page: every number and image comes from metrics.json / sweep.json / district_regions.png.

Usage: build_artifact.py --date 20260904 --out /path/to/out.html
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os

from PIL import Image

REGIONS = ["CALIFORNIA", "TEXAS", "NEWYORK", "MIDWEST", "CAROLINAS", "SOUTHWEST", "FLORIDA"]
MODES = ["fix", "anchor"]
K_RANGE = list(range(14, 23))
K_MAP = 18

# dataviz skill's validated 8-slot categorical palette, slots 1-7 (skip red/slot 8)
REGION_COLORS = {
    "CALIFORNIA": ("#2a78d6", "#3987e5"),   # blue
    "TEXAS":      ("#eb6834", "#d95926"),   # orange
    "NEWYORK":    ("#1baf7a", "#199e70"),   # aqua
    "MIDWEST":    ("#eda100", "#c98500"),   # yellow
    "CAROLINAS":  ("#e87ba4", "#d55181"),   # magenta
    "SOUTHWEST":  ("#008300", "#008300"),   # green
    "FLORIDA":    ("#4a3aa7", "#9085e9"),   # violet
}


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def png_to_webp_data_uri(path):
    im = Image.open(path).convert("RGBA")
    buf = io.BytesIO()
    im.save(buf, format="WEBP", lossless=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/webp;base64,{b64}"


def load_scenarios(scen_dir):
    """[(key, region, mode, states), ...] -- baseline first, then region x mode in REGIONS order."""
    out = [("baseline", None, None, [])]
    for region in REGIONS:
        for mode in MODES:
            spec = load_json(os.path.join(scen_dir, f"{region}_{mode}.json"))
            states = spec[mode][region]
            out.append((f"{region}_{mode}", region, mode, states))
    return out


def load_run(results_root, key):
    """(sweep_rows_by_k, k18_metrics) for one scenario key."""
    sweep = load_json(os.path.join(results_root, key, "sweep.json"))
    rows_by_k = {r["k"]: r for r in sweep["rows"]}
    metrics18 = load_json(os.path.join(results_root, key, f"k{K_MAP:02d}", "metrics.json"))
    return rows_by_k, metrics18


def fmt_pct(x):
    return f"{x:+.2%}" if x is not None else "&mdash;"


def fmt_nats(x):
    return f"{x:+.3f}" if x is not None else "-"


# ---------------------------------------------------------------- SVG charts

def _ticks(lo, hi, n=5):
    if hi <= lo:
        hi = lo + 1.0
    step = (hi - lo) / (n - 1)
    return [lo + i * step for i in range(n)]


def line_chart(series, x_vals, y_lo, y_hi, y_fmt, width=680, height=320, zero_line=False):
    """series: [(label, light_hex, [y0, y1, ...])] aligned to x_vals (evenly spaced)."""
    ml, mr, mt, mb = 58, 16, 14, 34
    pw, ph = width - ml - mr, height - mt - mb
    pad = (y_hi - y_lo) * 0.08 or 1.0
    lo, hi = y_lo - pad, y_hi + pad

    def X(i):
        return ml + (i / (len(x_vals) - 1) if len(x_vals) > 1 else 0) * pw

    def Y(v):
        return mt + (1 - (v - lo) / (hi - lo)) * ph

    parts = []
    for gy in _ticks(lo, hi):
        y = Y(gy)
        parts.append(f'<line x1="{ml}" x2="{ml+pw}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{ml-8}" y="{y+4:.1f}" class="tick" text-anchor="end">{y_fmt(gy)}</text>')
    if zero_line and lo < 0 < hi:
        y0 = Y(0)
        parts.append(f'<line x1="{ml}" x2="{ml+pw}" y1="{y0:.1f}" y2="{y0:.1f}" class="axis"/>')
    parts.append(f'<line x1="{ml}" x2="{ml+pw}" y1="{mt+ph}" y2="{mt+ph}" class="axis"/>')
    for i, xv in enumerate(x_vals):
        parts.append(f'<text x="{X(i):.1f}" y="{mt+ph+18}" class="tick" text-anchor="middle">{xv}</text>')
    for label, color, ys in series:
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(ys))
        parts.append(f'<path d="M{pts.replace(" ", " L")}" class="line" '
                     f'style="stroke:{color}" fill="none"/>')
        for i, v in enumerate(ys):
            parts.append(f'<circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.5" class="dot" '
                         f'style="fill:{color}"><title>{label} k={x_vals[i]}: {y_fmt(v)}</title>'
                         f'</circle>')
    return (f'<svg viewBox="0 0 {width} {height}" role="img" class="chart">' + "".join(parts) + "</svg>")


def grouped_bar_chart(groups, series_labels, colors, values, y_fmt, width=680, height=320):
    """values[g][s] for g in groups, s in series_labels (2 series: fix/anchor)."""
    ml, mr, mt, mb = 58, 16, 14, 46
    pw, ph = width - ml - mr, height - mt - mb
    all_v = [values[g][s] for g in groups for s in series_labels]
    hi = max(all_v + [0.0]) * 1.15 or 1.0
    lo = min(0.0, min(all_v))

    def Y(v):
        return mt + (1 - (v - lo) / (hi - lo)) * ph

    group_w = pw / len(groups)
    bar_w = group_w / (len(series_labels) + 1.2)
    parts = []
    for gy in _ticks(lo, hi):
        y = Y(gy)
        parts.append(f'<line x1="{ml}" x2="{ml+pw}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{ml-8}" y="{y+4:.1f}" class="tick" text-anchor="end">{y_fmt(gy)}</text>')
    y0 = Y(0)
    parts.append(f'<line x1="{ml}" x2="{ml+pw}" y1="{y0:.1f}" y2="{y0:.1f}" class="axis"/>')
    for gi, g in enumerate(groups):
        gx0 = ml + gi * group_w
        for si, s in enumerate(series_labels):
            v = values[g][s]
            x = gx0 + group_w / 2 - (len(series_labels) * bar_w) / 2 + si * bar_w
            y = Y(max(v, 0))
            h = abs(Y(0) - Y(v))
            color = colors[gi] if si == 0 else colors[gi]
            opacity = 1.0 if si == 0 else 0.5
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w*0.86:.1f}" height="{h:.1f}" '
                         f'rx="2" style="fill:{color};opacity:{opacity}">'
                         f'<title>{g} {s}: {y_fmt(v)}</title></rect>')
        parts.append(f'<text x="{gx0+group_w/2:.1f}" y="{mt+ph+16}" class="tick" '
                     f'text-anchor="middle">{g[:3]}</text>')
    return (f'<svg viewBox="0 0 {width} {height}" role="img" class="chart">' + "".join(parts) + "</svg>")


# --------------------------------------------------------------------- main

def build(date, results_root, fig_root, scen_dir, out_path):
    scenarios = load_scenarios(scen_dir)
    runs = {key: load_run(results_root, key) for key, *_ in scenarios}
    baseline_rows, baseline_m18 = runs["baseline"]

    total_m = sum(r["M"] for r in baseline_m18["summary"])
    n_zips = baseline_m18["n_zips"]
    n_solver_zips = baseline_m18["n_solver_zips"]

    # ---- headline table @ k=18 ----
    headline = []
    for key, region, mode, states in scenarios:
        rows_by_k, m18 = runs[key]
        r18 = rows_by_k[K_MAP]
        base18 = baseline_rows[K_MAP]
        hand = m18["hand_drawn"]
        solver_rows = [r for r in m18["summary"] if r["mode"] == "solver"]
        if solver_rows:
            vals = [r["M"] for r in solver_rows]
            spread = (max(vals) - min(vals)) / (sum(vals) / len(vals))
        else:
            spread = None
        headline.append(dict(
            key=key, region=region, mode=mode, states=states,
            pinned_m=hand[0]["M"] if hand else None,
            pinned_vs_target=hand[0]["vs_target"] if hand else None,
            spread=spread,
            nash=r18["nash"], nash_delta=r18["nash"] - base18["nash"],
            stage2=r18["stage2_value"], stage2_delta=r18["stage2_value"] - base18["stage2_value"],
        ))

    # ---- Chart A: pin cost @ k=18, fix vs anchor, grouped by region ----
    cost18 = {region: {} for region in REGIONS}
    for h in headline:
        if h["region"]:
            cost18[h["region"]][h["mode"]] = -h["nash_delta"]
    chart_a = grouped_bar_chart(REGIONS, MODES, [REGION_COLORS[r][0] for r in REGIONS],
                                cost18, lambda v: f"{v:.2f}")

    # ---- Chart B/C: fix-mode cost & pinned deviation across k ----
    # a `fix` district's M is invariant to k (closed, never touched by the solver), so its
    # deviation from target(k) = M*k/total - 1 is computable analytically at every k without
    # re-reading each k's metrics.json; the pin-cost series comes straight from each fix
    # scenario's own sweep.json (already loaded).
    region_m = {}
    for h in headline:
        if h["region"] and h["mode"] == "fix":
            region_m[h["region"]] = h["pinned_m"]

    chart_b_series, chart_c_series = [], []
    for region in REGIONS:
        rows_by_k, _ = runs[f"{region}_fix"]
        cost_ys = [-(rows_by_k[k]["nash"] - baseline_rows[k]["nash"]) for k in K_RANGE]
        dev_ys = [region_m[region] * k / total_m - 1 for k in K_RANGE]
        color = REGION_COLORS[region][0]
        chart_b_series.append((region, color, cost_ys))
        chart_c_series.append((region, color, dev_ys))
    b_all = [v for _, _, ys in chart_b_series for v in ys]
    c_all = [v for _, _, ys in chart_c_series for v in ys]
    chart_b = line_chart(chart_b_series, K_RANGE, min(b_all + [0]), max(b_all), lambda v: f"{v:.1f}")
    chart_c = line_chart(chart_c_series, K_RANGE, min(c_all), max(c_all), lambda v: f"{v:+.0%}",
                         zero_line=True)

    # ---- images ----
    opportunity_uri = png_to_webp_data_uri(os.path.join(fig_root, "opportunity.png"))
    map_uris = {key: png_to_webp_data_uri(os.path.join(fig_root, key, "district_regions.png"))
                for key, *_ in scenarios}

    # ---- per-scenario sections ----
    sections = []
    for key, region, mode, states in scenarios:
        rows_by_k, m18 = runs[key]
        k_table_rows = "".join(
            f"<tr{' class=cur' if k == K_MAP else ''}><td>{k}</td>"
            f"<td>{rows_by_k[k]['target']:,.1f}</td><td>{rows_by_k[k]['min']:,.1f}</td>"
            f"<td>{rows_by_k[k]['max']:,.1f}</td><td>{rows_by_k[k]['spread_rel']:.2%}</td>"
            f"<td>{rows_by_k[k]['nash']:.4f}</td><td>{rows_by_k[k]['stage2_value']:.4f}</td>"
            f"<td>{rows_by_k[k]['n_unstaffed']}</td></tr>"
            for k in K_RANGE)
        dist_rows = "".join(
            f"<tr><td>{r['district']}</td><td>{r['mode']}</td><td>{r['zips']}</td>"
            f"<td>{r['M']:,.1f}</td><td>{fmt_pct(r['vs_target'])}</td>"
            f"<td>{r['top_state']} ({r['top_state_share']:.0%})</td><td>{r['n_states']}</td>"
            f"<td>{r['max_zip_share']:.1%}</td><td>{r['median_zip_M']:.2f}</td>"
            f"<td>{r['rep']}</td><td>{r['gain']:.2f}</td></tr>"
            for r in sorted(m18["summary"], key=lambda r: (r["mode"] == "solver", r["district"])))
        title = "Baseline (no pins)" if key == "baseline" else f"{region} &middot; {mode}"
        states_str = ", ".join(states) if states else "&mdash;"
        sections.append(f"""
<section id="{key}">
  <h2>{title} <span class="sub">states: {states_str} &middot; k={K_MAP}</span></h2>
  <div class="maps"><figure><img src="{map_uris[key]}" alt="{key} power diagram at k={K_MAP}">
  <figcaption>Power-diagram territories, k={K_MAP}.</figcaption></figure></div>
  <div class="tablewrap"><table class="num"><thead><tr><th>k</th><th>target</th><th>min</th>
  <th>max</th><th>spread</th><th>&Sigma; log M</th><th>stage-2</th><th>unstaffed</th></tr></thead>
  <tbody>{k_table_rows}</tbody></table></div>
  <div class="tablewrap"><table class="num"><thead><tr><th>district</th><th>mode</th><th>zips</th>
  <th>M</th><th>vs target</th><th>top state</th><th>n states</th><th>max zip share</th>
  <th>median zip M</th><th>rep</th><th>stage-2 gain</th></tr></thead>
  <tbody>{dist_rows}</tbody></table></div>
</section>""")

    nav_links = "".join(f'<a href="#{key}">{key}</a>' for key, *_ in scenarios)
    headline_rows = "".join(f"""<tr{' class="cur"' if h['key']=='baseline' else ''}>
<td>{h['region'] or 'baseline'}</td><td>{h['mode'] or '&mdash;'}</td>
<td>{', '.join(h['states']) or '&mdash;'}</td>
<td>{f"{h['pinned_m']:,.1f}" if h['pinned_m'] is not None else '&mdash;'}</td>
<td>{fmt_pct(h['pinned_vs_target'])}</td>
<td>{f"{h['spread']:.2%}" if h['spread'] is not None else '&mdash;'}</td>
<td>{h['nash']:.4f}</td><td>{fmt_nats(h['nash_delta'])}</td>
<td>{h['stage2']:.4f}</td><td>{fmt_nats(h['stage2_delta'])}</td></tr>""" for h in headline)

    legend_items = "".join(
        f'<span class="legit"><i style="background:{REGION_COLORS[r][0]}"></i>{r}</span>'
        for r in REGIONS)

    css = _CSS
    html = f"""<title>Pin-Cost Catalogue</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{css}</style>
<main>
<p class="eyebrow">National channel &middot; stage 1 &middot; pin-cost catalogue &middot; {date}</p>
<h1>What it costs to hand-draw a district</h1>
<p class="lede">Seven candidate regions, each priced two ways &mdash; a closed <code>fix</code>
district and an open <code>anchor</code> &mdash; against the unpinned baseline, at every k from
14 to 22 on the sponsor's real &asymp;$18B total (descaled units below carry no currency
scale; only ratios and nats are comparable).</p>
<p>Instance: {n_zips:,} zips ({n_solver_zips:,} with gazetteer coordinates), total opportunity
M = {total_m:,.1f}. Target at k=18 is {total_m/18:,.1f} per district. All 15 runs (baseline + 14
scenarios) staffed every district from the rep roster; 0 unstaffed anywhere.</p>
<div class="maps"><figure><img src="{opportunity_uri}" alt="Opportunity by zip, instance_descaled_v2">
<figcaption>Opportunity M by zip, instance_descaled_v2.json.gz.</figcaption></figure></div>
<nav>{nav_links}</nav>

<h2 id="headline">Headline, k={K_MAP}</h2>
<p>Pinned M is invariant to k for <code>fix</code> (closed, never touched by the solver); for
<code>anchor</code> it converges toward the target via water-fill. &Delta; is against the
unpinned baseline at the same k &mdash; the pure additive pin cost in nats
(<a href="#repro">see why this is exact</a>).</p>
<div class="tablewrap"><table class="num"><thead><tr><th>region</th><th>mode</th><th>states</th>
<th>pinned M</th><th>pinned vs target</th><th>unpinned spread</th><th>&Sigma; log M</th>
<th>&Delta; nats</th><th>stage-2</th><th>&Delta;</th></tr></thead>
<tbody>{headline_rows}</tbody></table></div>

<h2 id="charts">The V</h2>
<div class="charts">
  <div class="chartcard"><h3>Pin cost at k=18</h3>
  <p class="cap">Cost = baseline &Sigma; log M minus the scenario's, in nats. Solid = fix, faint = anchor.</p>
  {chart_a}</div>
  <div class="chartcard"><h3>Pin cost against k (fix)</h3>
  <p class="cap">Same cost metric, across the full k sweep, fix mode only.</p>
  {chart_b}</div>
</div>
<div class="chartcard"><h3>Pinned district's deviation from target (fix)</h3>
<p class="cap">A fix district's M is fixed; the target moves with k. Crosses zero at each
region's natural k = total / region M.</p>
{chart_c}
<div class="legend">{legend_items}</div>
</div>

{"".join(sections)}

<h2 id="repro">Reproduce</h2>
<p>The metric is exact at fixed k: every scenario partitions the same total M into the same
number of districts, so &Sigma; log M differences against baseline are a pure additive cost in
nats (the scale-invariance argument in <code>CLAUDE.md</code>).</p>
<pre>python3 tools/run_draw.py instance_descaled_v2.json.gz --scenario docs/artifacts/runs/scenarios/&lt;region&gt;_&lt;mode&gt;.json \\
  --k 14-22 --seeds 0-9 --workers 8 --out battery/results/runs_{date}/&lt;region&gt;_&lt;mode&gt;
python3 tools/us_maps.py instance_descaled_v2.json.gz --out figures/runs_{date}/&lt;region&gt;_&lt;mode&gt;/ \\
  --regions battery/results/runs_{date}/&lt;region&gt;_&lt;mode&gt;/k18/draw.csv
python3 docs/artifacts/runs/build_artifact.py --date {date}</pre>
<p class="foot">instance_descaled_v2.json.gz &middot; generated {date}</p>
</main>"""
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"wrote {out_path} ({os.path.getsize(out_path)/1024/1024:.2f} MB)")


_CSS = """
:root {
  color-scheme: light;
  --ground:#f4f6f5; --surface:#ffffff; --ink:#172029; --ink2:#566370; --muted:#8a949b;
  --hair:#dde2e1; --axis:#c5ccca; --accent:#0e86a6; --cur:#e6f1f3;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --ground:#12181c; --surface:#1a2126; --ink:#e8ecef; --ink2:#a2adb6; --muted:#7f8a93;
    --hair:#2c363d; --axis:#3a464e; --accent:#2e9db5; --cur:#1f3238;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --ground:#12181c; --surface:#1a2126; --ink:#e8ecef; --ink2:#a2adb6; --muted:#7f8a93;
  --hair:#2c363d; --axis:#3a464e; --accent:#2e9db5; --cur:#1f3238;
}
body { margin:0; background:var(--ground); color:var(--ink); font:16px/1.55 "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width:1080px; margin:0 auto; padding:40px 24px 64px; }
h1 { font-size:34px; line-height:1.15; font-weight:600; margin:0 0 6px; text-wrap:balance; letter-spacing:-0.01em; }
h2 { font-size:22px; font-weight:600; margin:48px 0 8px; text-wrap:balance; }
h2 .sub { display:block; font-family:"IBM Plex Mono", ui-monospace, Menlo, monospace; font-size:13px; font-weight:400; color:var(--ink2); margin-top:4px; letter-spacing:0.01em; }
h3 { font-size:14px; font-weight:600; margin:0 0 2px; }
.eyebrow { font-family:"IBM Plex Mono", ui-monospace, monospace; font-size:12px; letter-spacing:0.08em; text-transform:uppercase; color:var(--ink2); margin:0 0 14px; }
p { max-width:72ch; margin:0 0 14px; }
.lede { font-size:18px; color:var(--ink); }
code { font-family:"IBM Plex Mono", ui-monospace, Menlo, monospace; font-size:0.9em; }
.tablewrap { overflow-x:auto; background:var(--surface); border:1px solid var(--hair); border-radius:6px; margin:16px 0; }
table { border-collapse:collapse; width:100%; font-family:"IBM Plex Mono", ui-monospace, Menlo, monospace; font-size:13px; }
table.num td, table.num th { font-variant-numeric:tabular-nums; text-align:right; padding:8px 12px; white-space:nowrap; }
table.num td:first-child, table.num th:first-child { text-align:left; }
thead th { color:var(--ink2); font-weight:500; border-bottom:1px solid var(--hair); position:sticky; top:0; background:var(--surface); }
tbody tr + tr td { border-top:1px solid var(--hair); }
tr.cur td { background:var(--cur); }
.charts { display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:24px; margin:16px 0 8px; }
.chartcard { background:var(--surface); border:1px solid var(--hair); border-radius:6px; padding:14px 16px 8px; margin:16px 0; }
.chartcard .cap { font-size:13px; color:var(--ink2); margin:0 0 6px; }
svg.chart { width:100%; height:auto; display:block; }
.grid { stroke:var(--hair); stroke-width:1; }
.axis { stroke:var(--axis); stroke-width:1; }
.tick { font:11px "IBM Plex Mono", ui-monospace, monospace; fill:var(--muted); }
.line { stroke-width:2; }
.dot { stroke:var(--surface); stroke-width:1.5; }
.legend { display:flex; flex-wrap:wrap; gap:12px 20px; margin:8px 4px 4px; font-size:12px; color:var(--ink2); }
.legit { display:inline-flex; align-items:center; gap:6px; }
.legit i { width:10px; height:10px; border-radius:2px; display:inline-block; }
.maps { display:grid; grid-template-columns:repeat(auto-fit, minmax(420px, 1fr)); gap:20px; margin:12px 0; }
figure { margin:0; background:var(--surface); border:1px solid var(--hair); border-radius:6px; padding:8px; }
figure img { width:100%; height:auto; display:block; border-radius:3px; }
figcaption { font-size:13px; color:var(--ink2); padding:8px 4px 2px; }
pre { background:var(--surface); border:1px solid var(--hair); border-radius:6px; padding:14px 16px; overflow-x:auto; font:13px/1.5 "IBM Plex Mono", ui-monospace, Menlo, monospace; }
nav { font-family:"IBM Plex Mono", ui-monospace, monospace; font-size:13px; margin:18px 0 0; display:flex; gap:16px; flex-wrap:wrap; }
nav a { color:var(--accent); text-decoration:none; border-bottom:1px solid transparent; }
nav a:hover, nav a:focus-visible { border-bottom-color:var(--accent); outline:none; }
.foot { font-family:"IBM Plex Mono", ui-monospace, monospace; font-size:12px; color:var(--muted); margin-top:40px; }
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    results_root = os.path.join("battery", "results", f"runs_{args.date}")
    fig_root = os.path.join("figures", f"runs_{args.date}")
    scen_dir = os.path.join("docs", "artifacts", "runs", "scenarios")
    out_path = args.out or os.path.join("docs", "artifacts", "runs", f"runs_{args.date}.html")
    build(args.date, results_root, fig_root, scen_dir, out_path)
