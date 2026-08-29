"""config.py -- one settings object, shared by every stage.

Defaults are the ones approved at the U3 design review (PLAN.md C.2 plus the 2026-08-29
privacy-dial decisions): rank jitter sigma = 0.10, per-state blocks only for states with at
least 100 ZCTAs, k-anonymity floor 20, scale stripped by the median, six significant figures
in every exported number.
"""
from __future__ import annotations

import json


class Cfg(object):
    """Settings for the whole pipeline.  Plain attributes; `to_dict` goes into `meta`."""

    #: keys recorded into twin_stats.json / twin_instance.json meta
    META_KEYS = ("min_support", "min_state", "rank_sigma", "theta", "lam", "n_bins", "seed",
                 "strip_scale", "strip_penetration", "round_sig", "jitter_smooth", "coarsen",
                 "swap_rounds", "radius_km", "tiger_vintage", "zcta_vintage")

    def __init__(self,
                 min_support=20,
                 min_state=100,
                 rank_sigma=0.10,
                 theta=0.40,
                 lam=0.30,
                 n_bins=200,
                 seed=0,
                 strip_scale=True,
                 strip_penetration=False,
                 round_sig=6,
                 jitter_smooth=0.0,
                 coarsen=None,
                 swap_rounds=0,
                 radius_km=True,
                 tiger_vintage="2025",
                 zcta_vintage="2025",
                 hop_max=5,
                 n_sources=2000,
                 max_pairs=200000,
                 allow_partial=False,
                 verbose=True):
        self.min_support = int(min_support)
        self.min_state = int(min_state)
        self.rank_sigma = float(rank_sigma)
        self.theta = float(theta)
        self.lam = float(lam)
        self.n_bins = int(n_bins)
        self.seed = int(seed)
        self.strip_scale = bool(strip_scale)
        self.strip_penetration = bool(strip_penetration)
        self.round_sig = int(round_sig)
        self.jitter_smooth = float(jitter_smooth)
        self.coarsen = coarsen                      # None | "decile" | "percentile"
        self.swap_rounds = int(swap_rounds)
        self.radius_km = bool(radius_km)
        self.tiger_vintage = str(tiger_vintage)
        self.zcta_vintage = str(zcta_vintage)
        self.hop_max = int(hop_max)
        self.n_sources = int(n_sources)
        self.max_pairs = int(max_pairs)
        self.allow_partial = bool(allow_partial)
        self.verbose = bool(verbose)

    # theta values the headroom-slack block is reported at
    THETA_GRID = (0.2, 0.4, 0.6)
    # min_share values the census block is reported at
    MIN_SHARE_GRID = (0.01, 0.02, 0.05)

    def to_dict(self):
        return dict((k, getattr(self, k)) for k in self.META_KEYS)

    def __repr__(self):
        return "Cfg(%s)" % json.dumps(self.to_dict(), sort_keys=True)

    def log(self, msg):
        if self.verbose:
            print(msg, flush=True)
