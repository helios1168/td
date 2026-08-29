"""agg.py -- the k-anonymity gate every exported number passes through.

`Agg.put(key, value, n_support)` is the only way a number gets into `twin_stats.json`.
When `enforce=True` (the export path) a value backed by fewer than `min_support` ZCTAs
raises `KAnonError` naming the key, and the run exits 2.  When `enforce=False` (the
`twin_check` recomputation on the synthetic twin, which is not confidential) the support is
recorded but nothing raises.

`smoothed_quantiles` is the windowed-order-statistic quantile used *everywhere* a quantile
appears: a reported quantile is the mean of the order statistics in a window around the
rank, never a single ZCTA's value, and never the min or the max.
"""
from __future__ import annotations

import math
from contextlib import contextmanager

import numpy as np


class KAnonError(Exception):
    """A number was backed by fewer than `min_support` underlying ZCTAs."""


class LeakGuardError(Exception):
    """The JSON writer found something that must not leave the work machine."""


class Agg(object):
    def __init__(self, min_support=20, enforce=True):
        self.min_support = int(min_support)
        self.enforce = bool(enforce)
        self._flat = {}          # dotted key -> value
        self._support = {}       # dotted key -> n_support
        self._notes = {}         # dotted key -> note
        self._prefix = []
        self.violations = []     # recorded when enforce=False

    # ------------------------------------------------------------------ structure
    @contextmanager
    def block(self, prefix):
        self._prefix.append(str(prefix))
        try:
            yield self
        finally:
            self._prefix.pop()

    def key(self, key):
        return ".".join(self._prefix + [str(key)])

    # ----------------------------------------------------------------------- put
    def put(self, key, value, n_support, note=""):
        """Record one scalar (or short list of scalars) under the current block prefix."""
        full = self.key(key)
        n_support = int(n_support)
        # A support of exactly 0 is a structural zero -- an empty category reveals nothing
        # about any individual ZCTA, so it is exempt.  1..min_support-1 is the danger zone.
        if 0 < n_support < self.min_support:
            msg = ("k-anonymity: %r is backed by %d ZCTAs, below min_support=%d"
                   % (full, n_support, self.min_support))
            if self.enforce:
                raise KAnonError(msg)
            self.violations.append(dict(key=full, n_support=n_support))
        value = _clean(value)
        self._flat[full] = value
        self._support[full] = n_support
        if note:
            self._notes[full] = note
        return value

    def put_vec(self, key, values, n_support, note=""):
        """Record a vector (quantile ladder, histogram, ...) as one k-anonymised item."""
        return self.put(key, [_clean(v) for v in list(values)], n_support, note=note)

    def get(self, full_key, default=None):
        return self._flat.get(full_key, default)

    def keys(self):
        return sorted(self._flat)

    # -------------------------------------------------------------------- output
    def to_dict(self):
        out = {}
        for full in sorted(self._flat):
            parts = full.split(".")
            d = out
            for p in parts[:-1]:
                d = d.setdefault(p, {})
                if not isinstance(d, dict):
                    raise ValueError("Agg: key collision at %r" % full)
            d[parts[-1]] = self._flat[full]
        out["_support"] = dict((k, int(v)) for k, v in sorted(self._support.items()))
        if self._notes:
            out["_notes"] = dict(sorted(self._notes.items()))
        return out

    def flat(self):
        return dict(self._flat)


def _clean(v):
    """numpy scalars -> python; NaN/inf -> None (JSON has no literal for them)."""
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, (str, bool, type(None))):
        return v
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    f = float(v)
    if math.isnan(f) or math.isinf(f):
        return None
    return f


# ------------------------------------------------------------------- quantiles
def window_halfwidth(n):
    """The order-statistic window half-width: max(10, ceil(0.002 n))."""
    return int(max(10, math.ceil(0.002 * n)))


def smoothed_quantiles(x, qs, min_support=20, sorted_input=False):
    """Windowed quantiles: the mean of the order statistics within +/- w of the rank.

    Returns (values, n_support) where n_support is the smallest window actually averaged
    (windows are clipped at the ends of the sample, which is exactly where a raw quantile
    would start leaking individual ZCTAs).
    """
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = x.size
    if n == 0:
        return [None] * len(qs), 0
    s = x if sorted_input else np.sort(x)
    w = window_halfwidth(n)
    vals, sup = [], []
    for q in qs:
        r = int(round(float(q) * (n - 1)))
        lo, hi = max(0, r - w), min(n - 1, r + w)
        if hi - lo + 1 < min_support:              # widen rather than report a thin window
            need = min_support - (hi - lo + 1)
            lo = max(0, lo - need)
            hi = min(n - 1, hi + need)
        vals.append(float(s[lo:hi + 1].mean()))
        sup.append(hi - lo + 1)
    return vals, int(min(sup))


def smoothed_quantile_scalar(x, q, min_support=20):
    v, s = smoothed_quantiles(x, [q], min_support=min_support)
    return v[0], s
