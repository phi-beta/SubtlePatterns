"""Value-noise implementations for the noise-driven pattern families.

We use Perlin's classic 2-D gradient noise, plus a value-noise variant
(cheap and visually fine for subtle backgrounds). Both are seeded by the
config's seed and re-seeded per call, so two patterns using the same seed
plus different ``variant`` strings will produce different fields.
"""

from __future__ import annotations

import math
import random
from typing import Tuple

from .random_utils import fade, lerp, make_rng


# ---------------------------------------------------------------------------
# Perlin gradient noise
# ---------------------------------------------------------------------------

# Pre-computed 256-unit gradients for Perlin noise. Chosen to be unit
# length and evenly distributed. The permutation table is shuffled with
# our seeded RNG.
_GRAD2: list[Tuple[float, float]] = [
    (1.0, 1.0), (1.0, -1.0), (-1.0, 1.0), (-1.0, -1.0),
    (1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0),
] * 32  # 256 entries; we only use them modulo 8 anyway


class Perlin2D:
    """Perlin gradient noise in 2-D.

    The implementation is the standard Ken Perlin reference version
    (``Improving Noise`` SIGGRAPH 2002), with the permutation table seeded
    deterministically.

    >>> p = Perlin2D(seed=42)
    >>> p(0.0, 0.0)        # doctest: +ELLIPSIS
    0.0...
    """

    __slots__ = ("perm", "perm_mod12")

    def __init__(self, seed: int, *tags: int | str) -> None:
        rng = make_rng(seed, *tags)
        perm = list(range(256))
        rng.shuffle(perm)
        # Duplicate the table so we can index freely without modulo.
        self.perm = perm + perm
        self.perm_mod12 = [v % 8 for v in self.perm]

    def _grad(self, hash_idx: int, x: float, y: float) -> float:
        h = hash_idx & 7
        u = x if h < 4 else y
        v = y if h < 4 else x
        g = _GRAD2[hash_idx]
        return (g[0] * u + g[1] * v)

    def __call__(self, x: float, y: float) -> float:
        xi = math.floor(x) & 255
        yi = math.floor(y) & 255
        xf = x - math.floor(x)
        yf = y - math.floor(y)
        u = fade(xf)
        v = fade(yf)
        p = self.perm
        pm = self.perm_mod12
        a = p[xi] + yi
        aa = pm[a]
        ab = pm[a + 1]
        b = p[xi + 1] + yi
        ba = pm[b]
        bb = pm[b + 1]
        x1 = lerp(
            self._grad(aa, xf, yf),
            self._grad(ba, xf - 1.0, yf),
            u,
        )
        x2 = lerp(
            self._grad(ab, xf, yf - 1.0),
            self._grad(bb, xf - 1.0, yf - 1.0),
            u,
        )
        # Approx range ~ [-1, 1]; we won't normalize further since callers
        # care about *shape* not exact amplitude.
        return lerp(x1, x2, v)


# ---------------------------------------------------------------------------
# FBM (fractal Brownian motion)
# ---------------------------------------------------------------------------

def fbm2d(
    perlin: Perlin2D,
    x: float,
    y: float,
    *,
    octaves: int = 4,
    lacunarity: float = 2.0,
    persistence: float = 0.5,
) -> float:
    """Multi-octave Perlin noise.

    The classic 1985 formulation: sum Perlin at increasing frequencies with
    decreasing amplitudes.
    """
    total = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_amp = 0.0
    for _ in range(octaves):
        total += perlin(x * frequency, y * frequency) * amplitude
        max_amp += amplitude
        amplitude *= persistence
        frequency *= lacunarity
    return total / max_amp if max_amp > 0 else 0.0
