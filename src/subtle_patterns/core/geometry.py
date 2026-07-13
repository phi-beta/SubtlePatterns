"""2-D geometry helpers for pattern construction.

All routines work in *user units* (i.e. raw SVG coordinates). Where a routine
produces an SVG path-data string (``d=`` attribute), the output is already
serialized and ready to drop into a ``<path>`` element.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

Point = Tuple[float, float]
Path = List[Point]


def hex_corner(center: Point, radius: float, i: int, *, pointy: bool = True) -> Point:
    """Return the ``i``-th corner of a regular hexagon centred on ``center``.

    ``pointy=True`` (default) gives pointy-top hexagons (vertices at top and
    bottom). ``pointy=False`` gives flat-top hexagons (vertices left and
    right).
    """
    if pointy:
        angle_deg = 60 * i - 30
    else:
        angle_deg = 60 * i
    angle = math.radians(angle_deg)
    return (center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle))


def hex_path(
    center: Point,
    radius: float,
    *,
    pointy: bool = True,
) -> str:
    """Return an SVG path-data string for a hexagon outline."""
    pts = [hex_corner(center, radius, i, pointy=pointy) for i in range(6)]
    parts = [f"M{pts[0][0]:.3f},{pts[0][1]:.3f}"]
    for x, y in pts[1:]:
        parts.append(f"L{x:.3f},{y:.3f}")
    parts.append("Z")
    return "".join(parts)


def hex_grid_centers(
    width: float,
    height: float,
    radius: float,
    *,
    pointy: bool = True,
) -> Iterable[Point]:
    """Yield the centres of a hexagon grid that covers ``width x height``.

    Hexagons are tiled with the standard "offset every other row" pattern.
    The grid extends slightly past the canvas edges so a border-hugging
    pattern doesn't show seams.
    """
    if pointy:
        dx = radius * math.sqrt(3.0)
        dy = 1.5 * radius
    else:
        dx = 1.5 * radius
        dy = radius * math.sqrt(3.0)
    rows = int(math.ceil(height / dy)) + 2
    cols = int(math.ceil(width / dx)) + 2
    for row in range(rows):
        for col in range(cols):
            x = col * dx - dx
            y = row * dy - dy
            if pointy and (row % 2) == 1:
                x += dx / 2
            if (not pointy) and (col % 2) == 1:
                y += dy / 2
            yield (x, y)


def polyline_path(points: Sequence[Point], *, closed: bool = False) -> str:
    """Return SVG path data for a polyline through ``points``."""
    if not points:
        return ""
    parts = [f"M{points[0][0]:.3f},{points[0][1]:.3f}"]
    for x, y in points[1:]:
        parts.append(f"L{x:.3f},{y:.3f}")
    if closed:
        parts.append("Z")
    return "".join(parts)


def smooth_path(
    points: Sequence[Point],
    *,
    tension: float = 0.5,
    closed: bool = False,
    segments: int = 16,
) -> str:
    """Return a Catmull-Rom-style smooth SVG path through ``points``.

    ``tension`` follows the SVG smooth-quadratic convention (0.5 = standard
    Catmull-Rom). ``segments`` is the resolution at which each segment is
    sampled before being emitted as a cubic Bezier ``C`` command.
    """
    if not points:
        return ""
    if len(points) == 1:
        x, y = points[0]
        return f"M{x:.3f},{y:.3f}"
    if len(points) == 2 and not closed:
        return polyline_path(points)

    # Mirror endpoints for closed/open curves.
    pts: list[Point] = list(points)
    if closed:
        pts = [pts[-1], *pts, pts[0], pts[1]]
    else:
        pts = [pts[0], *pts, pts[-1]]

    out: list[str] = []
    x0, y0 = pts[1]
    out.append(f"M{x0:.3f},{y0:.3f}")

    for i in range(1, len(pts) - 2):
        p0 = pts[i - 1]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[i + 2]

        c1x = p1[0] + (p2[0] - p0[0]) * tension / 3.0
        c1y = p1[1] + (p2[1] - p0[1]) * tension / 3.0
        c2x = p2[0] - (p3[0] - p1[0]) * tension / 3.0
        c2y = p2[1] - (p3[1] - p1[1]) * tension / 3.0
        out.append(
            f"C{c1x:.3f},{c1y:.3f} {c2x:.3f},{c2y:.3f} {p2[0]:.3f},{p2[1]:.3f}"
        )

    if closed:
        out.append("Z")
    return "".join(out)


def circle_path(cx: float, cy: float, r: float) -> str:
    """Return an SVG path data string for a circle (uses two arcs, no Z)."""
    return (
        f"M{cx - r:.3f},{cy:.3f}"
        f"a{r:.3f},{r:.3f} 0 1 0 {2 * r:.3f},0"
        f"a{r:.3f},{r:.3f} 0 1 0 {-2 * r:.3f},0"
    )


def path_length(points: Sequence[Point]) -> float:
    """Polyline length. Used by contour-style families for arc-length sampling."""
    if len(points) < 2:
        return 0.0
    total = 0.0
    prev = points[0]
    for p in points[1:]:
        dx = p[0] - prev[0]
        dy = p[1] - prev[1]
        total += math.hypot(dx, dy)
        prev = p
    return total


def line_intersection(
    p1: Point, p2: Point, p3: Point, p4: Point
) -> Point | None:
    """Return the intersection of segments p1p2 and p3p4, or None if parallel."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    if t < -1e-6 or t > 1 + 1e-6:
        return None
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def point_in_rect(p: Point, w: float, h: float) -> bool:
    return 0 <= p[0] <= w and 0 <= p[1] <= h
