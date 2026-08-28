# Tail distribution for M_z / A_z / B_z

## What changed

Added `_dpln(rng, n, sigma, alpha=None, beta=None)` to synth.py: a multiplicative
noise generator that returns plain `rng.lognormal(0, sigma, n)` when `alpha`/`beta`
are unset (the exact call used today, not a reimplementation, to preserve the
Generator's random-stream consumption), or a double Pareto-lognormal (dPlN) draw
otherwise:

```
exp(sigma * standard_normal(n) + exponential(1/alpha, n) - exponential(1/beta, n))
```

`alpha` sets upper-tail heaviness (smaller = heavier), `beta` sets lower-tail
heaviness. As alpha, beta -> inf this converges to lognormal(0, sigma), so dPlN
nests the current model exactly.

`make_instance` gets four new keyword-only-in-effect params, all defaulting to
no-op: `m_tail_alpha=None, m_tail_beta=None` (M_z), `sales_tail=0.20` (replaces the
old hardcoded `.20` sigma for A_z/B_z), `sales_tail_alpha=None, sales_tail_beta=None`
(A_z/B_z). Mz, Az, Bz each route through `_dpln`; Az and Bz still draw two
independent noise vectors, matching the original two separate `rng.lognormal` calls.

## Why

Eeckhout (2004, AER, "Gibrat's Law for (All) Cities") shows the full city-size
distribution is lognormal; Zipf's-law/Pareto behavior in the literature is mostly
an artifact of upper-tail-only truncation. Reed (2001, Econ. Lett.; 2002, J.
Regional Sci.) and Reed & Jorgensen (2004, Comm. Stat.) derive dPlN as the same
Gibrat mechanism run for a random (exponential) holding time, producing a
lognormal body with genuine Pareto tails on both ends. Giesen, Zimmermann &
Suedekum (2010, J. Urban Econ., "The Size Distribution Across All Cities --
Double Pareto Lognormal Strikes") show dPlN fits the full US city-size
distribution measurably better than pure lognormal or pure Pareto; since dPlN
nests lognormal as alpha, beta -> inf, this refines rather than contradicts
Eeckhout.

ZIP/ZCTA-level population specifically does not appear to follow a power law
(informal but methodologically sound analysis of real Census ZCTA data),
plausibly because USPS administratively redraws ZIP boundaries to keep per-zip
delivery volume comparable -- this suppresses the organic heavy-tailedness that
makes city-size data Pareto-tailed. So M_z (opportunity, closer in spirit to
population) stays near-lognormal by default (`m_tail_alpha/beta` exist but
default off). A_z/B_z (actual wholesaler sales) are driven by financial-advisor
/ broker-dealer office concentration -- a B2B commercial-real-estate clustering
pattern, not residential population, and not subject to the ZCTA-smoothing
effect -- so they get their own separately-tunable, potentially-heavier dial.

## Backward compatibility

Verified by running every existing SCENARIOS entry (S1-S6) at seeds 1 and 2 with
unchanged default args, comparing against a frozen copy of the pre-edit
`make_instance`: all 12 runs bit-identical (`np.array_equal` on `Az`, `Bz`, `Mz`)
and `G.graph["Sa"]`, `["Sb"]`, `["Mtot"]`, `["corr_AB"]` equal to full float
precision. Overall result: **PASS**, all 12/12.

## How to use it

New params on `make_instance`: `m_tail_alpha`, `m_tail_beta` (M_z tail shape,
default off), `sales_tail` (default `0.20`, same value as before), `sales_tail_alpha`,
`sales_tail_beta` (A_z/B_z tail shape, default off). New scenario `S7_heavytail`:
`dict(alpha=1.0, sales_tail_alpha=1.0, sales_tail_beta=3.5)` -- alpha=1.0 is the
Zipf-like organic-city value for the upper tail; beta=3.5 (~3.5x alpha) reflects
the literature's steeper lower tail.

Concentration effect (seed=1, n=200, A_z): baseline max/mean=6.07, top-5%-share=19.9%;
`sales_tail_alpha=1.0, sales_tail_beta=3.5` gives max/mean=22.21, top-5%-share=47.5%.

`territory.validate(G)` on `S7_heavytail` (seed=1) returns `[]`. The first-pass
headroom repair fires on 3 zips under the heavy tail vs 0 under plain defaults
(same seed/params otherwise); the hard-fix second pass fires on 0 in both cases.
