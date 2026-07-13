"""Deterministic seeded random-number utilities.

Patterns in this library must be **fully reproducible** from a config and a
seed — the same inputs must produce byte-identical SVG output. We use
:mod:`random`'s ``Random`` class with a per-pattern derived seed so that
changing one pattern's seed doesn't perturb the others.

We deliberately avoid NumPy here. The patterns are small enough that the
overhead of a Python-level RNG is negligible, and keeping the core
zero-dependency makes this library easier to ship in any Python project.
"""

from __future__ import annotations

import hashlib
import random
from typing import Iterator, Sequence, TypeVar

T = TypeVar("T")


def derive_seed(*parts: int | str) -> int:
    """Derive a 32-bit integer seed from arbitrary hashable parts.

    Uses SHA-256 and takes the first 4 bytes as a big-endian unsigned int.
    Different inputs produce *very* different seeds (avalanche effect), so
    tweaking one pattern's seed by +1 will visibly change the output.
    """
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8"))
        h.update(b"|")
    return int.from_bytes(h.digest()[:4], "big", signed=False)


def make_rng(seed: int, *tags: int | str) -> random.Random:
    """Return a :class:`random.Random` instance derived from ``seed`` and tags."""
    return random.Random(derive_seed(seed, *tags))


def jitter_position(
    rng: random.Random,
    x: float,
    y: float,
    amount: float,
    *,
    min_jitter: float = 0.0,
) -> tuple[float, float]:
    """Return ``(x, y)`` jittered by up to ``±amount`` on each axis.

    ``amount`` is interpreted in user units. ``min_jitter`` is the minimum
    displacement so that very small amounts still produce a little life.
    """
    if amount <= 0:
        return x, y
    dx = rng.uniform(-amount, amount)
    dy = rng.uniform(-amount, amount)
    if min_jitter > 0 and (dx * dx + dy * dy) < min_jitter * min_jitter:
        # Re-roll once with a fixed direction so the dot doesn't sit still.
        angle = rng.uniform(0, 6.283185307179586)
        dx = min_jitter * math_cos(angle)
        dy = min_jitter * math_sin(angle)
    return x + dx, y + dy


def math_cos(x: float) -> float:
    import math
    return math.cos(x)


def math_sin(x: float) -> float:
    import math
    return math.sin(x)


def pick(rng: random.Random, seq: Sequence[T]) -> T:
    """Return a random element of ``seq`` (raises IndexError on empty)."""
    if not seq:
        raise IndexError("pick() called on empty sequence")
    return seq[rng.randrange(len(seq))]


def weighted_pick(
    rng: random.Random,
    items: Sequence[T],
    weights: Sequence[float],
) -> T:
    """Pick an item from ``items`` according to non-negative ``weights``.

    ``sum(weights)`` does not need to be 1; the function normalizes.
    """
    if not items:
        raise IndexError("weighted_pick() called on empty items")
    if len(items) != len(weights):
        raise ValueError("items and weights must have the same length")
    total = sum(weights)
    if total <= 0:
        return items[rng.randrange(len(items))]
    target = rng.random() * total
    acc = 0.0
    for item, w in zip(items, weights):
        acc += w
        if target <= acc:
            return item
    return items[-1]


def smoothstep(t: float) -> float:
    """GLSL-style smoothstep — cubic Hermite interpolation in [0, 1]."""
    if t <= 0:
        return 0.0
    if t >= 1:
        return 1.0
    return t * t * (3.0 - 2.0 * t)


def fade(t: float) -> float:
    """Perlin's ``fade`` curve: ``6t^5 - 15t^4 + 10t^3``.

    Used by the :func:`~.noise.perlin2d` value-noise function for a smoother
    first derivative than linear or smoothstep.
    """
    return ((6 * t - 15) * t + 10) * t * t * t


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between ``a`` and ``b`` by ``t``."""
    return a + (b - a) * t


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def map_range(
    v: float,
    in_lo: float,
    in_hi: float,
    out_lo: float,
    out_hi: float,
    *,
    clamp_out: bool = True,
) -> float:
    """Re-map ``v`` from ``[in_lo, in_hi]`` to ``[out_lo, out_hi]``.

    If ``clamp_out`` is True, the result is clamped to the output range.
    """
    if in_hi == in_lo:
        return out_lo
    t = (v - in_lo) / (in_hi - in_lo)
    out = out_lo + t * (out_hi - out_lo)
    if clamp_out:
        out = max(out_lo, min(out_hi, out))
    return out
