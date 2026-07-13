"""Lattice patterns: grid, dot grid, hex mesh, triangular mesh.

These are the *tidy* patterns — every element sits on a regular grid. They
are the most legible family, ideal for technical / structural aesthetics
(network diagrams, blueprint-style overlays, isometric look).
"""

from __future__ import annotations

import math
import random
from typing import Iterable, List, Tuple

from ..core.config import PatternConfig
from ..core.geometry import (
    Point,
    hex_corner,
    hex_grid_centers,
    hex_path,
    polyline_path,
)
from ..core.random_utils import jitter_position, make_rng
from ..svg import SvgElement, SvgGroup
from . import Size, register


# ---------------------------------------------------------------------------
# grid — orthogonal line lattice
# ---------------------------------------------------------------------------

@register("grid")
def _grid(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """An orthogonal grid of thin lines.

    ``variant`` controls the cell geometry:

    * ``""`` (default) — square cells.
    * ``"isometric"`` — 30°/60° lines (classic iso grid).
    * ``"offset"`` — every other row is offset by half a cell.
    * ``"double"`` — square cells + a fainter sub-cell at half spacing.
    """
    rng = make_rng(seed, "grid", cfg.variant)
    spacing = max(2.0, cfg.spacing / max(0.2, cfg.density))
    jitter = cfg.jitter * spacing * 0.4
    w, h = size

    if cfg.variant == "isometric":
        # Two sets of lines at ±30°, packed into one path.
        angles = (math.radians(30), math.radians(-30))
        parts: list[str] = []
        extent = max(w, h) * 1.5
        n_steps = int(extent / spacing) + 4
        for ang in angles:
            dx, dy = math.cos(ang), math.sin(ang)
            px, py = -dy, dx
            for i in range(-n_steps, n_steps):
                ox = px * i * spacing + w * 0.5
                oy = py * i * spacing + h * 0.5
                x0, y0 = ox - dx * extent, oy - dy * extent
                x1, y1 = ox + dx * extent, oy + dy * extent
                parts.append(f"M{x0:.1f},{y0:.1f}L{x1:.1f},{y1:.1f}")
        layer.path("".join(parts))
    else:
        # Pack all vertical lines into one path, all horizontal into another.
        v_lines: list[str] = []
        x = -spacing
        while x <= w + spacing:
            jx = x + (rng.uniform(-jitter, jitter) if jitter else 0)
            v_lines.append(f"M{jx:.1f},0L{jx:.1f},{h:.1f}")
            x += spacing
        h_lines: list[str] = []
        y = -spacing
        while y <= h + spacing:
            jy = y + (rng.uniform(-jitter, jitter) if jitter else 0)
            h_lines.append(f"M0,{jy:.1f}L{w:.1f},{jy:.1f}")
            y += spacing
        if v_lines:
            layer.path("".join(v_lines))
        if h_lines:
            layer.path("".join(h_lines))
        if cfg.variant == "double":
            # Fainter half-spacing sub-grid, also packed.
            sub = SvgGroup(
                stroke=cfg.stroke,
                stroke_opacity=cfg.stroke_opacity * 0.4 * cfg.opacity,
                stroke_width=max(0.3, cfg.thickness * 0.5),
                fill="none",
            )
            sub_v: list[str] = []
            x = -spacing / 2
            while x <= w + spacing:
                sub_v.append(f"M{x:.1f},0L{x:.1f},{h:.1f}")
                x += spacing
            sub_h: list[str] = []
            y = -spacing / 2
            while y <= h + spacing:
                sub_h.append(f"M0,{y:.1f}L{w:.1f},{y:.1f}")
                y += spacing
            sub.path("".join(sub_v) + "".join(sub_h))
            layer.add(sub)


# ---------------------------------------------------------------------------
# dot_grid — points on a lattice
# ---------------------------------------------------------------------------

@register("dot_grid")
def _dot_grid(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """A grid of dots, optionally jittered.

    ``variant``:

    * ``""`` — uniform circles. Output is packed into a single ``<path>``
      (with arc ops) so a 1600×900 overlay costs ~30 KB instead of ~150 KB.
    * ``"scaled"`` — each dot's radius is jittered; emitted as multiple
      bucketed paths (one per radius bucket) to keep the size low.
    * ``"rings"`` — dots become thin rings.
    """
    rng = make_rng(seed, "dot_grid", cfg.variant)
    spacing = max(2.0, cfg.spacing / max(0.2, cfg.density))
    jitter = cfg.jitter * spacing * 0.4
    w, h = size

    if cfg.variant == "rings":
        ring = SvgGroup(
            fill="none",
            stroke=cfg.stroke,
            stroke_opacity=cfg.stroke_opacity * cfg.opacity,
            stroke_width=max(0.3, cfg.thickness),
        )
        y = -spacing
        while y <= h + spacing:
            x = -spacing
            while x <= w + spacing:
                jx, jy = jitter_position(rng, x, y, jitter) if jitter else (x, y)
                ring.circle(jx, jy, cfg.radius)
                x += spacing
            y += spacing
        layer.add(ring)
        return

    # Emit as a sequence of <use> elements referencing a shared <symbol>.
    # A 1600x900 overlay with default config costs ~6 KB instead of ~150 KB.
    dot_id = "sp-dot"
    fill = str(cfg.fill) if cfg.fill != "none" else "#888888"
    base_r = cfg.radius

    # We need a <defs> block in the document. Since the pattern only has
    # a layer group, we embed a <defs> with a single <circle> symbol as
    # the layer's first child (browsers tolerate defs inside a g).
    defs = SvgElement("defs")
    defs_id = f"sp-defs-{cfg.seed}-{cfg.variant or 'd'}"
    defs.extend_attrs({"id": defs_id})
    # Multiple buckets for the "scaled" variant.
    if cfg.variant == "scaled":
        n_buckets = 4
        for b in range(n_buckets):
            r = base_r * (0.4 + 1.2 * b / (n_buckets - 1))
            sym = SvgElement(
                "circle", id=f"{dot_id}-{b}", cx="0", cy="0",
                r=f"{r:.2f}", fill=fill,
                fill_opacity=f"{cfg.fill_opacity * cfg.opacity:.3f}",
            )
            defs._el.append(sym._el)  # noqa: SLF001
    else:
        sym = SvgElement(
            "circle", id=dot_id, cx="0", cy="0",
            r=f"{base_r:.2f}", fill=fill,
            fill_opacity=f"{cfg.fill_opacity * cfg.opacity:.3f}",
        )
        defs._el.append(sym._el)  # noqa: SLF001
    layer._el.append(defs._el)  # noqa: SLF001

    if cfg.variant != "scaled":
        y = -spacing
        while y <= h + spacing:
            x = -spacing
            while x <= w + spacing:
                jx, jy = jitter_position(rng, x, y, jitter) if jitter else (x, y)
                use = SvgElement("use", href=f"#{dot_id}", x=f"{jx:.1f}", y=f"{jy:.1f}")
                layer._el.append(use._el)  # noqa: SLF001
                x += spacing
            y += spacing
    else:
        n_buckets = 4
        y = -spacing
        while y <= h + spacing:
            x = -spacing
            while x <= w + spacing:
                jx, jy = jitter_position(rng, x, y, jitter) if jitter else (x, y)
                scale = rng.uniform(0.4, 1.6)
                b = min(n_buckets - 1, max(0, int(scale * n_buckets)))
                use = SvgElement("use", href=f"#{dot_id}-{b}", x=f"{jx:.1f}", y=f"{jy:.1f}")
                layer._el.append(use._el)  # noqa: SLF001
                x += spacing
            y += spacing


# ---------------------------------------------------------------------------
# hex_mesh — hexagonal mesh
# ---------------------------------------------------------------------------

@register("hex_mesh")
def _hex_mesh(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """A tessellated hexagon mesh.

    ``variant``:

    * ``""`` (default) — outlines only.
    * ``"filled"`` — alternating shaded hexagons (creates a chevron effect).
    * ``"triangulated"`` — adds a centre-to-corner line in every hex.
    """
    rng = make_rng(seed, "hex_mesh", cfg.variant)
    radius = max(2.0, cfg.spacing * 0.55) / max(0.3, cfg.density ** 0.5)
    pointy = cfg.variant != "flat_top"

    paths: list[str] = []
    for cx, cy in hex_grid_centers(*size, radius, pointy=pointy):
        paths.append(hex_path((cx, cy), radius, pointy=pointy))
    if paths:
        layer.path("".join(paths))

    if cfg.variant == "triangulated":
        tri_paths: list[str] = []
        for cx, cy in hex_grid_centers(*size, radius, pointy=pointy):
            for i in range(6):
                x1, y1 = cx, cy
                x2, y2 = hex_corner((cx, cy), radius, i, pointy=pointy)
                tri_paths.append(f"M{x1:.1f},{y1:.1f}L{x2:.1f},{y2:.1f}")
        layer.path("".join(tri_paths))
    elif cfg.variant == "filled":
        # Pick a deterministic 50% of cells to fill.
        filled = SvgGroup(
            fill=cfg.fill,
            fill_opacity=cfg.fill_opacity * cfg.opacity,
            stroke="none",
        )
        for cx, cy in hex_grid_centers(*size, radius, pointy=pointy):
            if rng.random() < 0.5:
                pts = [hex_corner((cx, cy), radius * 0.92, i, pointy=pointy) for i in range(6)]
                filled.polygon(pts)
        layer.add(filled)


# ---------------------------------------------------------------------------
# triangular_mesh — Delaunay-style triangle mesh
# ---------------------------------------------------------------------------

@register("triangular_mesh")
def _triangular_mesh(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """A triangle mesh.

    We don't run a full Delaunay triangulation (that needs scipy); instead
    we lay out a regular triangular grid by stacking two offset rows. This
    gives the look of a triangular mesh at zero extra dependency.

    ``variant``:

    * ``""`` — equilateral triangles in a 50/50 up/down pattern.
    * ``"shaded"`` — every other triangle is faintly filled.
    """
    rng = make_rng(seed, "triangular_mesh", cfg.variant)
    h_step = max(4.0, cfg.spacing * math.sqrt(3.0) / 2.0) / max(0.3, cfg.density ** 0.5)
    w_step = cfg.spacing
    w, h = size
    paths: list[str] = []
    shaded: list[str] = []
    row = 0
    y = -h_step
    while y <= h + h_step:
        x_offset = (w_step / 2.0) if (row % 2) else 0.0
        x = -w_step
        while x <= w + w_step:
            x0, y0 = x + x_offset, y
            x1, y1 = x + x_offset + w_step, y
            x2 = x + x_offset + w_step / 2.0
            y2 = y + h_step
            tri = f"M{x0:.2f},{y0:.2f}L{x1:.2f},{y1:.2f}L{x2:.2f},{y2:.2f}Z"
            if cfg.variant == "shaded" and (row + (1 if (x // w_step) % 2 else 0)) % 2:
                shaded.append(tri)
            else:
                paths.append(tri)
            x += w_step
        row += 1
        y += h_step
    if paths:
        layer.path("".join(paths))
    if shaded:
        fill_group = SvgGroup(
            fill=cfg.fill,
            fill_opacity=cfg.fill_opacity * cfg.opacity,
            stroke="none",
        )
        fill_group.path("".join(shaded))
        layer.add(fill_group)
