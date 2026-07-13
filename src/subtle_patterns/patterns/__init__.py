"""Pattern family implementations.

Each pattern is a callable that takes a populated :class:`SvgGroup` and
appends SVG elements to it. The signature is::

    def pattern_X(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None

Patterns are registered in :data:`PATTERN_REGISTRY` (a plain dict keyed by
family name) and dispatched by the engine.

Design rules for pattern authors:

* Do not draw a background. The overlay is *always* transparent.
* Prefer path elements (one per logical group) over thousands of small
  elements when the geometry is repetitive — this is the single biggest
  size/perf win for SVGs.
* Honour ``cfg.density`` — it scales the element count multiplicatively.
  Patterns that can't easily scale by density should still respect it for
  spacing (e.g. a denser grid has a smaller cell size).
* Honour ``cfg.jitter`` — even a very small jitter (~0.05) breaks the
  obvious "this is a regular pattern" feel.
* Never write to ``layer._el`` directly; use ``layer.path``, ``layer.line``,
  ``layer.circle``, ``layer.rect``, ``layer.polygon``, or
  ``layer.add_path_list``.
"""

from __future__ import annotations

import math
from typing import Callable, Dict

from ..core.config import PatternConfig
from ..core.geometry import (
    Point,
    circle_path,
    dist,
    hex_corner,
    hex_grid_centers,
    hex_path,
    line_intersection,
    path_length,
    point_in_rect,
    polyline_path,
    smooth_path,
)
from ..core.random_utils import make_rng
from ..svg import SvgGroup

Size = tuple[float, float]
PatternImpl = Callable[[SvgGroup, PatternConfig, Size, int], None]

PATTERN_REGISTRY: Dict[str, PatternImpl] = {}


def register(name: str):
    """Decorator: register a pattern implementation under ``name``."""

    def deco(fn: PatternImpl) -> PatternImpl:
        if name in PATTERN_REGISTRY:
            raise ValueError(f"Pattern {name!r} is already registered")
        PATTERN_REGISTRY[name] = fn
        fn.__pattern_name__ = name  # type: ignore[attr-defined]
        return fn

    return deco


def get_pattern(name: str) -> PatternImpl:
    if name not in PATTERN_REGISTRY:
        raise KeyError(f"Unknown pattern family {name!r}")
    return PATTERN_REGISTRY[name]


__all__ = ["register", "get_pattern", "PATTERN_REGISTRY", "Size", "PatternImpl"]


# Eagerly import the pattern modules so they self-register on package import.
from . import (  # noqa: E402, F401
    lattices,
    lines_hatches,
    curves,
    organic,
    particles,
    fractals,
    misc,
)
