"""Organic / fluid patterns: organic_blobs, voronoi."""

from __future__ import annotations

import math
import random
from typing import List, Tuple

from ..core.config import PatternConfig
from ..core.geometry import dist, polyline_path, smooth_path
from ..core.noise import Perlin2D
from ..core.random_utils import make_rng
from ..svg import SvgGroup
from . import Size, register


# ---------------------------------------------------------------------------
# organic_blobs — soft, irregular closed shapes
# ---------------------------------------------------------------------------

@register("organic_blobs")
def _organic_blobs(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """A field of organic, blobby closed shapes.

    Each blob is a closed curve traced from a noise-perturbed circle.

    ``variant``:

    * ``""`` (default) — random centres, varying radii.
    * ``"cubic"`` — cubic Bezier smoothing on top of the polyline.
    * ``"puffs"`` — a tighter, puffier look (more points per blob).
    """
    perlin = Perlin2D(seed, "organic_blobs", cfg.variant)
    rng = make_rng(seed, "organic_blobs", cfg.variant, "jitter")
    w, h = size
    n_blobs = max(1, int(cfg.levels * cfg.density * 0.6))
    base_radius = max(6.0, cfg.spacing * 1.2)
    amp = cfg.amplitude
    freq = cfg.frequency
    n_pts = {
        "puffs": 32,
    }.get(cfg.variant, 20)
    paths: list[str] = []
    for k in range(n_blobs):
        cx = rng.uniform(0, w)
        cy = rng.uniform(0, h)
        r = base_radius * rng.uniform(0.5, 1.5)
        pts: list[Tuple[float, float]] = []
        for j in range(n_pts):
            ang = (j / n_pts) * 2 * math.pi
            # Offset the radius based on a low-frequency noise.
            offset = perlin(
                (cx + r * math.cos(ang)) * freq,
                (cy + r * math.sin(ang)) * freq,
            ) * amp
            rj = r + offset
            pts.append((cx + rj * math.cos(ang), cy + rj * math.sin(ang)))
        if cfg.variant == "cubic":
            d = smooth_path(pts, closed=True, tension=0.5)
        else:
            d = polyline_path(pts, closed=True)
        paths.append(d)
    if paths:
        layer.path("".join(paths))


# ---------------------------------------------------------------------------
# voronoi — a simple Voronoi diagram
# ---------------------------------------------------------------------------

@register("voronoi")
def _voronoi(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """A Voronoi diagram (random cell boundaries).

    We compute the diagram by brute-force: for every pixel column boundary
    in a coarse grid, find the closest seed point. This is O(W·H·N) which
    is fine for a moderate number of cells and small canvases; the engine
    scales ``cfg.spacing`` so a 1600×900 overlay still renders in < 1 s.

    ``variant``:

    * ``""`` (default) — cell boundaries only.
    * ``"filled"`` — each cell is faintly filled with a tint of the stroke.
    * ``"relaxed"`` — Lloyd-relaxed seeds (more uniform cell area).
    """
    rng = make_rng(seed, "voronoi", cfg.variant)
    w, h = size
    n_seeds = max(4, int(cfg.levels * cfg.density * 1.5))
    seeds: list[Tuple[float, float]] = [
        (rng.uniform(-0.05 * w, 1.05 * w), rng.uniform(-0.05 * h, 1.05 * h))
        for _ in range(n_seeds)
    ]
    if cfg.variant == "relaxed":
        seeds = _lloyd_relax(seeds, w, h, iterations=2)

    # Cell boundaries: walk a fine grid and detect changes in nearest seed.
    step = max(2.0, cfg.spacing * 0.3)
    cols = int(w / step) + 1
    rows = int(h / step) + 1
    paths: list[str] = []
    fill_paths: list[str] = []
    # For each cell, the boundary is the set of grid points where the
    # nearest seed changes. We accumulate edges into a set of (a,b) pairs
    # and merge them into polylines.
    boundary_edges: set[Tuple[Tuple[float, float], Tuple[float, float]]] = set()
    for j in range(rows + 1):
        for i in range(cols + 1):
            x = i * step
            y = j * step
            if x > w and y > h:
                continue
            x = min(x, w)
            y = min(y, h)
            # Find two nearest seeds.
            dists = sorted(((dist((x, y), s), idx) for idx, s in enumerate(seeds)))
            _, a = dists[0]
            _, b = dists[1]
            sa, sb = seeds[a], seeds[b]
            if cfg.variant == "filled":
                # Each grid cell becomes a polygon clipped to the canvas;
                # we only mark the cell as belonging to seed `a` for filling.
                # For efficiency, push a small rect (will be re-clipped at
                # composition). The cell fill is just a faint tint of the
                # stroke colour, so artefacts at the seams are invisible.
                fill_paths.append(
                    f"M{x:.2f},{y:.2f}h{step:.2f}v{step:.2f}h{-step:.2f}Z"
                )
            # Midpoint between sa and sb, perpendicular line = boundary.
            mx = (sa[0] + sb[0]) * 0.5
            my = (sa[1] + sb[1]) * 0.5
            # We add an "edge" by drawing a small perpendicular line centred
            # on the grid point in the direction of the gradient.
            gx = sa[0] - sb[0]
            gy = sa[1] - sb[1]
            length = math.hypot(gx, gy) or 1.0
            gx /= length
            gy /= length
            # Perpendicular direction.
            px, py = -gy, gx
            r = step * 0.9
            p1 = (mx + px * r, my + py * r)
            p2 = (mx - px * r, my - py * r)
            # Canonicalise edge so identical edges dedupe.
            edge = tuple(sorted((_round_pt(p1), _round_pt(p2))))
            boundary_edges.add(edge)  # type: ignore[arg-type]
    for a, b in boundary_edges:
        paths.append(f"M{a[0]:.1f},{a[1]:.1f}L{b[0]:.1f},{b[1]:.1f}")
    if cfg.variant == "filled":
        # Overlay a very faint tile fill — these tiny squares will average
        # out visually as a soft tint near each cell centre.
        # (Re-using a soft fill colour rather than the user's fill keeps
        # the pattern subtle by default.)
        sub = SvgGroup(
            fill="#888888",
            fill_opacity=0.04 * cfg.opacity,
            stroke="none",
        )
        sub.path("".join(fill_paths))
        layer.add(sub)
    if paths:
        layer.path("".join(paths))


def _round_pt(p: Tuple[float, float]) -> Tuple[float, float]:
    return (round(p[0], 1), round(p[1], 1))


def _lloyd_relax(
    seeds: list[Tuple[float, float]],
    w: float,
    h: float,
    *,
    iterations: int = 2,
) -> list[Tuple[float, float]]:
    """One round of Lloyd's relaxation by sampling the canvas.

    We sample a coarse grid, assign each sample to its nearest seed, and
    move each seed to the centroid of its Voronoi cell.
    """
    step = max(8.0, min(w, h) / 80)
    cols = int(w / step) + 1
    rows = int(h / step) + 1
    for _ in range(iterations):
        sums = [(0.0, 0.0, 0)] * len(seeds)  # (sx, sy, n)
        for j in range(rows + 1):
            for i in range(cols + 1):
                x = i * step
                y = j * step
                if x > w: x = w
                if y > h: y = h
                best = min(range(len(seeds)), key=lambda k: (seeds[k][0] - x) ** 2 + (seeds[k][1] - y) ** 2)
                sx, sy, n = sums[best]
                sums[best] = (sx + x, sy + y, n + 1)
        new_seeds: list[Tuple[float, float]] = []
        for (sx, sy, n), old in zip(sums, seeds):
            if n == 0:
                new_seeds.append(old)
            else:
                new_seeds.append((sx / n, sy / n))
        seeds = new_seeds
    return seeds
