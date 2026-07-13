"""Curve patterns: wave_field, contour_lines, topographic."""

from __future__ import annotations

import math
from typing import List, Tuple

from ..core.config import PatternConfig
from ..core.noise import Perlin2D, fbm2d
from ..core.random_utils import make_rng
from ..svg import SvgGroup
from . import Size, register


# ---------------------------------------------------------------------------
# wave_field — a stack of smoothly varying lines
# ---------------------------------------------------------------------------

@register("wave_field")
def _wave_field(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """A field of wavy lines, one per row.

    Each line is the integral of a noise function so it looks like flowing
    topography. ``variant``:

    * ``""`` (default) — pure Perlin, one row per ``spacing`` units.
    * ``"fbm"`` — fractal Brownian motion (richer low-frequency content).
    * ``"tanh"`` — tames extremes to keep waves roughly bounded.
    * ``"cubic"`` — adds a cubic-Bezier smoothing on top of the polyline.
    """
    perlin = Perlin2D(seed, "wave_field", cfg.variant)
    spacing = max(2.0, cfg.spacing / max(0.2, cfg.density))
    w, h = size
    n_rows = int(h / spacing) + 2
    # Step length is set so each line has ~3 points per spacing unit
    # (smooth but not wasteful).
    step = max(spacing / 4, 4.0)
    paths: list[str] = []
    for i in range(-1, n_rows + 1):
        y_base = i * spacing
        x = -step
        pts: list[Tuple[float, float]] = []
        amp = cfg.amplitude
        freq = cfg.frequency
        while x <= w + step:
            t = x * freq
            n = (
                fbm2d(perlin, t, y_base * freq * 0.6, octaves=4)
                if cfg.variant == "fbm"
                else perlin(t, y_base * freq * 0.4)
            )
            if cfg.variant == "tanh":
                n = math.tanh(n * 1.4)
            y = y_base + n * amp
            pts.append((x, y))
            x += step
        parts = [f"M{pts[0][0]:.2f},{pts[0][1]:.2f}"]
        for px, py in pts[1:]:
            parts.append(f"L{px:.2f},{py:.2f}")
        paths.append("".join(parts))
    layer.add_path_list(paths)


# ---------------------------------------------------------------------------
# contour_lines — marching squares iso-lines
# ---------------------------------------------------------------------------

@register("contour_lines")
def _contour_lines(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """Iso-lines (contours) of a noise field, drawn by marching squares.

    ``variant``:

    * ``""`` (default) — uniform spacing between levels.
    * ``"emphasis"`` — every 5th line is bolder.
    * ``"labelled"`` — same as default, with a tiny tick at the level
      midpoints (a typical cartographic convention).
    """
    perlin = Perlin2D(seed, "contour_lines", cfg.variant)
    w, h = size
    cell = max(2.0, cfg.spacing * 0.5)
    cols = int(w / cell) + 1
    rows = int(h / cell) + 1
    # Sample the field on a regular grid.
    field: list[List[float]] = []
    amp = cfg.amplitude
    freq = cfg.frequency
    for j in range(rows + 1):
        row: list[float] = []
        for i in range(cols + 1):
            n = perlin(i * cell * freq, j * cell * freq)
            row.append(n * amp)
        field.append(row)

    n_levels = max(2, int(cfg.levels))
    if not field or not field[0]:
        return
    fmin = min(min(r) for r in field)
    fmax = max(max(r) for r in field)
    if fmax - fmin < 1e-6:
        return
    paths: list[str] = []
    emphasis_paths: list[str] = []
    for li in range(n_levels):
        level = fmin + (fmax - fmin) * (li + 0.5) / n_levels
        # Marching squares: 16 cases based on which corners are above level.
        for j in range(rows):
            for i in range(cols):
                tl = field[j][i]
                tr = field[j][i + 1]
                br = field[j + 1][i + 1]
                bl = field[j + 1][i]
                case = 0
                if tl > level: case |= 1
                if tr > level: case |= 2
                if br > level: case |= 4
                if bl > level: case |= 8
                if case in (0, 15):
                    continue
                # Cell corners in user coords.
                x0 = i * cell
                y0 = j * cell
                x1 = (i + 1) * cell
                y1 = (j + 1) * cell
                # Edge midpoints: top, right, bottom, left.
                def lerp(a: float, b: float, va: float, vb: float) -> Tuple[float, float]:
                    if abs(va - vb) < 1e-9:
                        return ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5)
                    t = (level - va) / (vb - va)
                    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                T = (x0, y0); R = (x1, y0); B = (x1, y1); L = (x0, y1)
                top = lerp(T, R, tl, tr)
                right = lerp(R, B, tr, br)
                bot = lerp(B, L, br, bl)
                left = lerp(L, T, bl, tl)
                # Emit segment based on case.
                seg: Tuple[Tuple[float, float], Tuple[float, float]] | None = None
                if case in (1, 14):   seg = (left, top)
                elif case in (2, 13): seg = (top, right)
                elif case in (3, 12): seg = (left, right)
                elif case in (4, 11): seg = (right, bot)
                elif case in (5, 10): seg = (left, bot)  # ambiguous
                elif case in (6, 9):  seg = (top, bot)
                elif case in (7, 8):   seg = (left, bot)
                if seg is None:
                    continue
                p1, p2 = seg
                d = f"M{p1[0]:.2f},{p1[1]:.2f}L{p2[0]:.2f},{p2[1]:.2f}"
                if cfg.variant == "emphasis" and li % 5 == 0:
                    emphasis_paths.append(d)
                else:
                    paths.append(d)
    if paths:
        layer.path("".join(paths))
    if emphasis_paths:
        sub = SvgGroup(
            stroke=cfg.stroke,
            stroke_opacity=cfg.stroke_opacity * 1.5 * cfg.opacity,
            stroke_width=max(0.3, cfg.thickness * 1.3),
            fill="none",
        )
        sub.path("".join(emphasis_paths))
        layer.add(sub)


# ---------------------------------------------------------------------------
# topographic — classic topo map
# ---------------------------------------------------------------------------

@register("topographic")
def _topographic(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """A topographic isoline field with FBM noise.

    This is essentially ``contour_lines`` with FBM as the underlying field
    (gives that classic "squiggly mountain" look) and a slightly different
    visual style: a faint dot at every isoline peak for a textured feel.
    """
    perlin = Perlin2D(seed, "topographic", cfg.variant)
    w, h = size
    cell = max(2.0, cfg.spacing * 0.6)
    cols = int(w / cell) + 1
    rows = int(h / cell) + 1
    field: list[List[float]] = []
    amp = cfg.amplitude
    freq = cfg.frequency
    for j in range(rows + 1):
        row: list[float] = []
        for i in range(cols + 1):
            n = fbm2d(perlin, i * cell * freq, j * cell * freq, octaves=5, persistence=0.55)
            row.append(n * amp)
        field.append(row)
    n_levels = max(2, int(cfg.levels))
    if not field or not field[0]:
        return
    fmin = min(min(r) for r in field)
    fmax = max(max(r) for r in field)
    if fmax - fmin < 1e-6:
        return
    paths: list[str] = []
    for li in range(n_levels):
        level = fmin + (fmax - fmin) * (li + 0.5) / n_levels
        for j in range(rows):
            for i in range(cols):
                tl = field[j][i]
                tr = field[j][i + 1]
                br = field[j + 1][i + 1]
                bl = field[j + 1][i]
                case = 0
                if tl > level: case |= 1
                if tr > level: case |= 2
                if br > level: case |= 4
                if bl > level: case |= 8
                if case in (0, 15):
                    continue
                x0 = i * cell
                y0 = j * cell
                x1 = (i + 1) * cell
                y1 = (j + 1) * cell

                def lerp(a, b, va, vb):
                    if abs(va - vb) < 1e-9:
                        return ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5)
                    t = (level - va) / (vb - va)
                    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                T = (x0, y0); R = (x1, y0); B = (x1, y1); L = (x0, y1)
                top = lerp(T, R, tl, tr)
                right = lerp(R, B, tr, br)
                bot = lerp(B, L, br, bl)
                left = lerp(L, T, bl, tl)
                seg = None
                if case in (1, 14):   seg = (left, top)
                elif case in (2, 13): seg = (top, right)
                elif case in (3, 12): seg = (left, right)
                elif case in (4, 11): seg = (right, bot)
                elif case in (5, 10): seg = (left, bot)
                elif case in (6, 9):  seg = (top, bot)
                elif case in (7, 8):   seg = (left, bot)
                if seg is None:
                    continue
                p1, p2 = seg
                paths.append(f"M{p1[0]:.1f},{p1[1]:.1f}L{p2[0]:.1f},{p2[1]:.1f}")
    if paths:
        layer.path("".join(paths))
