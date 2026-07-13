"""Fractal / recursive patterns: fractal_silhouette.

Two variants are provided:

* the default ``""`` variant emits a single SVG path containing every
  kept rectangle of a Sierpinski-carpet-like subdivision. This keeps the
  output size small (one path, all rects concatenated) and is the
  preferred variant for any non-trivial canvas.

* the ``"hilbert"`` variant emits a Hilbert-curve path, useful for the
  classic "tracing" overlay look.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from ..core.config import PatternConfig
from ..core.random_utils import make_rng
from ..svg import SvgGroup
from . import Size, register


@register("fractal_silhouette")
def _fractal_silhouette(
    layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int
) -> None:
    """A recursive subdivision silhouette.

    ``variant``:

    * ``""`` (default) — Sierpinski-carpet-like; emits **one path**.
    * ``"hilbert"`` — Hilbert curve; emits **one path**.
    * ``"tree"`` — recursive branching tree; emits **one path**.
    """
    rng = make_rng(seed, "fractal_silhouette", cfg.variant)
    w, h = size

    if cfg.variant == "hilbert":
        order = max(2, min(6, int(cfg.levels * 0.5)))
        unit = max(8.0, cfg.spacing)
        n = (1 << order)
        side = (n - 1) * unit
        ox = (w - side) * 0.5
        oy = (h - side) * 0.5
        points = _hilbert(order)
        parts: list[str] = []
        for i, (x, y) in enumerate(points):
            px = ox + x * unit
            py = oy + y * unit
            parts.append(f"{'M' if i == 0 else 'L'}{px:.2f},{py:.2f}")
        layer.path("".join(parts))
        return

    if cfg.variant == "tree":
        # A simple recursive tree: from the bottom centre, branch upward.
        path = _fractal_tree(
            w * 0.5, h,
            length=cfg.spacing * 1.2,
            angle=-math.pi / 2,
            depth=max(2, int(cfg.levels * 0.4)),
            spread=math.radians(25 + cfg.jitter * 30),
            length_scale=0.7,
            rng=rng,
        )
        layer.path(path)
        return

    # Default: Sierpinski-carpet-like, single path.
    max_depth = max(1, min(6, int(cfg.levels * 0.4)))
    base_prob = max(0.05, min(0.95, cfg.amplitude / 100.0))
    parts = []
    _emit_carpet_path(0, 0, w, h, 0, max_depth, base_prob, rng, parts)
    if parts:
        layer.path("".join(parts))


def _emit_carpet_path(
    x: float, y: float, w: float, h: float, depth: int,
    max_depth: int, base_prob: float, rng, parts: list,
) -> None:
    """Emit a Sierpinski-carpet silhouette as a single concatenated path.

    At each level, we recurse into 3x3 sub-cells; the centre cell is always
    carved (removed). Each leaf cell we keep contributes a single
    ``M..h..v..h..Z`` rectangle to the path.
    """
    if depth >= max_depth or w < 1.0 or h < 1.0:
        # Leaf: emit a filled rectangle (the keep region).
        parts.append(f"M{x:.2f},{y:.2f}h{w:.2f}v{h:.2f}h{-w:.2f}Z")
        return
    if rng.random() < base_prob ** (depth + 1):
        # Carve this cell entirely.
        return
    cw = w / 3
    ch = h / 3
    for cy in range(3):
        for cx in range(3):
            if cx == 1 and cy == 1:
                # Always carve the centre.
                continue
            if rng.random() < base_prob ** (depth + 1):
                # Probabilistic carve.
                continue
            _emit_carpet_path(
                x + cx * cw, y + cy * ch, cw, ch,
                depth + 1, max_depth, base_prob, rng, parts,
            )


def _fractal_tree(
    x: float, y: float,
    *,
    length: float,
    angle: float,
    depth: int,
    spread: float,
    length_scale: float,
    rng,
) -> str:
    """Return path data for a recursive branching tree.

    At each step, branch into 2 children whose angles are ``angle ± spread``
    and whose lengths are scaled by ``length_scale``.
    """
    x2 = x + math.cos(angle) * length
    y2 = y + math.sin(angle) * length
    if depth <= 0 or length < 0.5:
        return f"M{x:.2f},{y:.2f}L{x2:.2f},{y2:.2f}"
    # Recurse into two branches.
    a1 = angle - spread * rng.uniform(0.7, 1.0)
    a2 = angle + spread * rng.uniform(0.7, 1.0)
    next_len = length * length_scale * rng.uniform(0.85, 1.1)
    return (
        f"M{x:.2f},{y:.2f}L{x2:.2f},{y2:.2f}"
        + _fractal_tree(x2, y2, length=next_len, angle=a1, depth=depth - 1,
                        spread=spread, length_scale=length_scale, rng=rng)
        + _fractal_tree(x2, y2, length=next_len, angle=a2, depth=depth - 1,
                        spread=spread, length_scale=length_scale, rng=rng)
    )


def _hilbert(order: int) -> list[tuple[int, int]]:
    """Generate the (x, y) points of a Hilbert curve of the given order."""
    if order == 0:
        return [(0, 0)]
    sub = _hilbert(order - 1)
    n = 1 << (order - 1)
    out: list[tuple[int, int]] = []
    # Quadrant 0 (top-left): rotate 90° counter-clockwise.
    for x, y in sub:
        out.append((y, x))
    # Quadrant 1 (top-right): identity.
    for x, y in sub:
        out.append((x, y + n))
    # Quadrant 2 (bottom-right): identity.
    for x, y in sub:
        out.append((x + n, y + n))
    # Quadrant 3 (bottom-left): rotate 90° clockwise.
    for x, y in sub:
        out.append((n - 1 - y, n - 1 - x + n))
    return out
