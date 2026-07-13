"""Particle / scatter patterns: constellation, particles."""

from __future__ import annotations

import math
import random
from typing import List, Tuple

from ..core.config import PatternConfig
from ..core.noise import Perlin2D
from ..core.random_utils import make_rng
from ..svg import SvgGroup
from . import Size, register


# ---------------------------------------------------------------------------
# constellation — scattered dots with thin connecting lines (network look)
# ---------------------------------------------------------------------------

@register("constellation")
def _constellation(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """A scatter of points with thin connecting lines to nearest neighbours.

    The look is "constellation / network diagram" — many points, sparse
    lines connecting only the *nearest* neighbour for each point so the
    network doesn't fill in.

    ``variant``:

    * ``""`` (default) — uniform random scatter.
    * ``"clustered"`` — points cluster around a few centres (use ``levels``
      to set the number of clusters).
    * ``"spiral"`` — points are placed on a logarithmic spiral.
    """
    rng = make_rng(seed, "constellation", cfg.variant)
    w, h = size
    n_points = max(20, int(cfg.levels * cfg.density * 6))
    points: list[Tuple[float, float]] = []
    if cfg.variant == "clustered":
        centres = [(rng.uniform(0.1 * w, 0.9 * w), rng.uniform(0.1 * h, 0.9 * h))
                   for _ in range(max(2, int(cfg.levels * 0.3)))]
        for _ in range(n_points):
            cx, cy = rng.choice(centres)
            # Gaussian-ish displacement.
            x = cx + rng.gauss(0, cfg.spacing * 0.6)
            y = cy + rng.gauss(0, cfg.spacing * 0.6)
            points.append((x, y))
    elif cfg.variant == "spiral":
        # Logarithmic spiral: r = a * e^(b*theta)
        a = cfg.spacing * 0.3
        b = cfg.spacing * 0.04
        cx, cy = w * 0.5, h * 0.5
        for i in range(n_points):
            t = i * 0.4
            r = a * math.exp(b * t)
            ang = t
            x = cx + r * math.cos(ang)
            y = cy + r * math.sin(ang)
            points.append((x, y))
    else:
        points = [(rng.uniform(0, w), rng.uniform(0, h)) for _ in range(n_points)]

    # Draw lines first (so dots sit on top).
    if points:
        max_dist = max(40.0, cfg.spacing * 1.4)
        line_paths: list[str] = []
        for i, p in enumerate(points):
            best_j = -1
            best_d2 = max_dist * max_dist
            for j, q in enumerate(points):
                if i == j:
                    continue
                dx = p[0] - q[0]
                dy = p[1] - q[1]
                d2 = dx * dx + dy * dy
                if d2 < best_d2:
                    best_d2 = d2
                    best_j = j
            if best_j >= 0:
                q = points[best_j]
                line_paths.append(f"M{p[0]:.2f},{p[1]:.2f}L{q[0]:.2f},{q[1]:.2f}")
        if line_paths:
            sub = SvgGroup(
                stroke=cfg.stroke,
                stroke_opacity=cfg.stroke_opacity * 0.6 * cfg.opacity,
                stroke_width=max(0.2, cfg.thickness * 0.7),
                fill="none",
            )
            sub.add_path_list(line_paths)
            layer.add(sub)

    # Dots.
    for p in points:
        r = cfg.radius * rng.uniform(0.6, 1.2)
        layer.circle(p[0], p[1], r)


# ---------------------------------------------------------------------------
# particles — small dots with varying size and opacity
# ---------------------------------------------------------------------------

@register("particles")
def _particles(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """A scatter of small dots with varying size and opacity.

    ``variant``:

    * ``""`` (default) — uniform random.
    * ``"size_curve"`` — radius follows a power law (most are tiny, a few
      are large — "stars in the sky" feel).
    * ``"field"`` — opacity varies smoothly across the canvas via Perlin
      noise (creates a soft "glow" zone).
    * ``"size_curve+field"`` — both.
    """
    perlin = Perlin2D(seed, "particles", cfg.variant) if "field" in cfg.variant else None
    rng = make_rng(seed, "particles", cfg.variant, "scatter")
    w, h = size
    # Default n is tuned so a 1600x900 canvas produces ~1500 dots.
    n = max(20, int(cfg.levels * cfg.density * 6))
    fill = str(cfg.fill) if cfg.fill != "none" else "#888888"
    base_op = cfg.fill_opacity * cfg.opacity
    for _ in range(n):
        x = rng.uniform(0, w)
        y = rng.uniform(0, h)
        r = cfg.radius * rng.uniform(0.5, 1.5)
        if "size_curve" in cfg.variant:
            r *= rng.uniform(0.3, 2.5) ** 2
        op = base_op
        if perlin is not None:
            t = perlin(x * cfg.frequency, y * cfg.frequency) * 0.5 + 0.5
            op *= 0.4 + 1.2 * t
        # We could group by opacity bucket to keep the DOM small, but
        # per-particle opacity is the whole point of the "field" variant.
        # For the non-field variants, fall through to a single <circle> on
        # the parent layer (no extra <g>).
        if perlin is None:
            layer.circle(x, y, r)
        else:
            sub = SvgGroup(
                fill=fill,
                fill_opacity=max(0.0, min(1.0, op)),
                stroke="none",
            )
            sub.circle(x, y, r)
            layer.add(sub)
