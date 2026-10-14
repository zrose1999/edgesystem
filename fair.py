"""EDGE fair prices. Removes the bookmaker margin with Shin's method.

Proportional removal (each side's implied probability divided by the booksum) spreads the
margin evenly, which leaves longshots overrated and favourites underrated. Shin's method models
the margin as protection against informed bettors and puts more of it on the longshot. It is the
better-tested estimate, and it matters most on moneylines with a big favourite and on three-way
soccer markets.

  fair.probs({"home": -180, "away": +155})            -> {"home": 0.627, "away": 0.373}
  fair.probs({"home": +140, "draw": +240, "away": +200})

Two outcomes: Shin is exact and equals subtracting half the overround from each side.
Three or more: z (the informed share) is found by bisection.
No margin, or a negative one (an arb across books): falls back to proportional.
Standard library only.
"""

from math import sqrt


def implied(american):
    a = float(american)
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def _shin_given_z(pi, booksum, z):
    return [(sqrt(z * z + 4 * (1 - z) * p * p / booksum) - z) / (2 * (1 - z)) for p in pi]


def shin(pi):
    """Shin probabilities from a list of implied probabilities (with margin)."""
    booksum = sum(pi)
    if booksum <= 1.0 or len(pi) < 2:
        return [p / booksum for p in pi]
    if len(pi) == 2:
        over = (booksum - 1) / 2
        out = [p - over for p in pi]
        if min(out) <= 0:
            return [p / booksum for p in pi]
        return out
    lo, hi = 0.0, 0.5
    for _ in range(80):
        z = (lo + hi) / 2
        if sum(_shin_given_z(pi, booksum, z)) > 1:
            lo = z
        else:
            hi = z
    out = _shin_given_z(pi, booksum, (lo + hi) / 2)
    s = sum(out)
    return [p / s for p in out]


def probs(prices, keys=None):
    """Fair probabilities for a dict of American prices, e.g. {"home": -150, "away": 130}."""
    keys = keys or [k for k in ("home", "away", "draw", "over", "under") if k in prices]
    fair = shin([implied(prices[k]) for k in keys])
    return dict(zip(keys, fair))


def proportional(prices, keys=None):
    keys = keys or [k for k in ("home", "away", "draw", "over", "under") if k in prices]
    total = sum(implied(prices[k]) for k in keys)
    return {k: implied(prices[k]) / total for k in keys}
