"""Line / hatch patterns: diagonal_lines, cross_hatch, scanlines, circuit_traces."""

from __future__ import annotations

import math

from ..core.config import PatternConfig
from ..core.geometry import line_intersection
from ..core.random_utils import make_rng
from ..svg import SvgGroup
from . import Size, register


# ---------------------------------------------------------------------------
# diagonal_lines — parallel diagonals
# ---------------------------------------------------------------------------

@register("diagonal_lines")
def _diagonal_lines(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """A set of parallel diagonal lines at a single angle.

    ``variant``:

    * ``""`` (default) — 45° lines.
    * ``"steeper"`` — 60° lines.
    * ``"shallow"`` — 15° lines.
    * ``"crossed"`` — two perpendicular sets (becomes ``cross_hatch``).
    """
    angle = {
        "steeper": math.radians(60),
        "shallow": math.radians(15),
    }.get(cfg.variant, math.radians(45))
    spacing = max(2.0, cfg.spacing / max(0.2, cfg.density))
    w, h = size
    # Project the perpendicular extent needed to cover the canvas.
    extent = math.hypot(w, h)
    dx, dy = math.cos(angle), math.sin(angle)
    px, py = -dy, dx
    n = int(extent / spacing) + 4
    paths: list[str] = []
    for i in range(-n, n):
        ox = px * i * spacing + w * 0.5
        oy = py * i * spacing + h * 0.5
        paths.append(
            f"M{ox - dx * extent:.1f},{oy - dy * extent:.1f}"
            f"L{ox + dx * extent:.1f},{oy + dy * extent:.1f}"
        )
    if paths:
        layer.path("".join(paths))
    if cfg.variant == "crossed":
        # Perpendicular second set, packed into the same path.
        a2 = angle + math.pi / 2
        dx, dy = math.cos(a2), math.sin(a2)
        px, py = -dy, dx
        n2 = int(extent / spacing) + 4
        more: list[str] = []
        for i in range(-n2, n2):
            ox = px * i * spacing + w * 0.5
            oy = py * i * spacing + h * 0.5
            more.append(
                f"M{ox - dx * extent:.1f},{oy - dy * extent:.1f}"
                f"L{ox + dx * extent:.1f},{oy + dy * extent:.1f}"
            )
        if more:
            layer.path("".join(more))


# ---------------------------------------------------------------------------
# cross_hatch — two (or more) sets of lines
# ---------------------------------------------------------------------------

@register("cross_hatch")
def _cross_hatch(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """Multi-angle cross-hatch.

    ``variant``:

    * ``""`` — two sets at 30° and 120° (gives a 60° rhombus grid).
    * ``"triple"`` — three sets at 0°, 60°, 120°.
    * ``"weave"`` — a denser weave: 0° and 90° plus fainter 30°/60°.
    """
    angles = {
        "triple": (0.0, math.radians(60), math.radians(120)),
        "weave": (0.0, math.radians(90), math.radians(30), math.radians(60)),
    }.get(cfg.variant, (math.radians(30), math.radians(120)))
    spacing = max(2.0, cfg.spacing / max(0.2, cfg.density))
    w, h = size
    extent = math.hypot(w, h)
    paths: list[str] = []
    n = int(extent / spacing) + 4
    for ang in angles:
        dx, dy = math.cos(ang), math.sin(ang)
        px, py = -dy, dx
        for i in range(-n, n):
            ox = px * i * spacing + w * 0.5
            oy = py * i * spacing + h * 0.5
            paths.append(
                f"M{ox - dx * extent:.1f},{oy - dy * extent:.1f}"
                f"L{ox + dx * extent:.1f},{oy + dy * extent:.1f}"
            )
    if paths:
        layer.path("".join(paths))
    if cfg.variant == "weave":
        # Overlay a faint 0°/90° set on top, at 2x spacing.
        sub = SvgGroup(
            stroke=cfg.stroke,
            stroke_opacity=cfg.stroke_opacity * 0.4 * cfg.opacity,
            stroke_width=max(0.3, cfg.thickness * 0.7),
            fill="none",
        )
        sub_paths: list[str] = []
        x = -spacing * 2
        while x <= w + spacing * 2:
            sub_paths.append(f"M{x:.1f},0L{x:.1f},{h:.1f}")
            x += spacing * 2
        y = -spacing * 2
        while y <= h + spacing * 2:
            sub_paths.append(f"M0,{y:.1f}L{w:.1f},{y:.1f}")
            y += spacing * 2
        sub.path("".join(sub_paths))
        layer.add(sub)


# ---------------------------------------------------------------------------
# scanlines — horizontal scanlines (CRT / print look)
# ---------------------------------------------------------------------------

@register("scanlines")
def _scanlines(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """Horizontal scanlines.

    ``variant``:

    * ``""`` — uniform spacing.
    * ``"halftone"`` — varying line thickness, sinusoidal across the width.
    """
    spacing = max(1.0, cfg.spacing / max(0.2, cfg.density))
    w, h = size
    if cfg.variant == "halftone":
        # Build a single path with varying stroke; the only way to vary
        # stroke-width per-line in SVG is one path per line.
        from ..svg import SvgGroup as _G
        for y in range(-int(spacing), int(h + spacing), int(spacing)):
            phase = y * cfg.frequency * 6.283
            thickness = max(0.3, cfg.thickness * (0.4 + 0.6 * (0.5 + 0.5 * math.sin(phase))))
            opacity = cfg.stroke_opacity * (0.4 + 0.6 * (0.5 + 0.5 * math.cos(phase * 0.7)))
            line_g = _G(
                stroke=cfg.stroke,
                stroke_opacity=opacity * cfg.opacity,
                stroke_width=thickness,
                fill="none",
            )
            line_g.path(f"M0,{y:.2f}L{w:.2f},{y:.2f}")
            layer.add(line_g)
    else:
        y = 0.0
        while y <= h + spacing:
            layer.path(f"M0,{y:.2f}L{w:.2f},{y:.2f}")
            y += spacing


# ---------------------------------------------------------------------------
# circuit_traces — orthogonal lines with right-angle turns
# ---------------------------------------------------------------------------

@register("circuit_traces")
def _circuit_traces(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """Orthogonal polyline traces reminiscent of a PCB.

    Each trace is a random walk that turns only at right angles. ``levels``
    controls the number of traces; ``spacing`` controls the step size.
    """
    rng = make_rng(seed, "circuit_traces", cfg.variant)
    w, h = size
    step = max(4.0, cfg.spacing)
    n_traces = max(1, int(cfg.levels * cfg.density))
    paths: list[str] = []
    for _ in range(n_traces):
        # Pick a starting point on a random edge.
        side = rng.choice(("top", "bottom", "left", "right"))
        if side == "top":
            x, y = rng.uniform(0, w), -2
        elif side == "bottom":
            x, y = rng.uniform(0, w), h + 2
        elif side == "left":
            x, y = -2, rng.uniform(0, h)
        else:
            x, y = w + 2, rng.uniform(0, h)
        n_steps = rng.randint(int(cfg.amplitude * 0.5), int(cfg.amplitude * 1.5) + 1)
        pts: list[tuple[float, float]] = [(x, y)]
        direction = rng.choice((0, 1, 2, 3))  # 0=E,1=S,2=W,3=N
        dxs = (1, 0, -1, 0)
        dys = (0, 1, 0, -1)
        for _ in range(n_steps):
            # Bias: 70% chance to keep direction, 30% to turn.
            if rng.random() < 0.3:
                direction = (direction + rng.choice((-1, 1))) % 4
            steps = rng.randint(1, max(1, int(step * 1.5)))
            x += dxs[direction] * steps
            y += dys[direction] * steps
            x = max(-2, min(w + 2, x))
            y = max(-2, min(h + 2, y))
            pts.append((x, y))
        # Serialise as polyline.
        parts = [f"M{pts[0][0]:.2f},{pts[0][1]:.2f}"]
        for px, py in pts[1:]:
            parts.append(f"L{px:.2f},{py:.2f}")
        paths.append("".join(parts))
        # Tiny terminator dot.
        if rng.random() < 0.6:
            layer.circle(pts[-1][0], pts[-1][1], max(0.6, cfg.thickness * 1.4))
    if paths:
        layer.path("".join(paths))
