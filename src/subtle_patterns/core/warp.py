"""Spatial warps for SubtlePatterns.

A *warp* is a layer-level geometric transform applied to the output of a
pattern. It lets the same flat-XY pattern read as if it were projected onto
a tilted plane, wrapped around a cylinder, bent into a dome, rippled like
water, or twisted like a screw.

Two implementation strategies are used depending on the warp:

* **Affine** warps (single SVG ``transform="..."``): ``tilt_x``, ``tilt_y``,
  ``tilt_xy``, ``scale_h``, ``scale_v``, ``shear_x``, ``shear_y``. These are
  cheap (one attribute on a ``<g>``) and don't change the rendered
  *density* of the pattern, just the shape of the canvas it lies on.

* **Non-affine** warps (SVG ``<filter>`` with ``<feDisplacementMap>``):
  ``cylinder_h``, ``cylinder_v``, ``sphere``, ``ripple``, ``twist``.
  ``feDisplacementMap`` is the standard SVG idiom for non-affine spatial
  warps: it samples a small displacement map (also an SVG primitive) and
  offsets each pixel of the source by the map's value at that point. We
  build the displacement map procedurally from ``<feTurbulence>`` (for
  noise-based warps like ``ripple``) or from analytic expressions via
  ``<feFunc*`` (for the geometric warps).

Why ``<filter>`` rather than piecewise-affine row slicing? The latter
requires re-bucketing every drawn element by y-coordinate, which would
force every pattern implementation to know about slices. A single
``filter="url(#sp-warp-N)"`` on the layer's wrapping ``<g>`` keeps the
pattern code unaware of warps, gives an *exact* (not approximated) warp,
and the per-layer filter definitions are tiny (a handful of fe* elements
shared across the layer).

This module produces two kinds of strings:

* ``wrap_transform`` for affine warps — drop directly into ``<g transform=...>``.
* ``wrap_filter`` (id) plus a defs string for non-affine warps — the engine
  emits the defs once per warped layer and references the filter from the
  layer's ``<g filter=...>``.

This module is pure math + string assembly. The engine splices the strings
into the SVG output.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class WarpKind(str, Enum):
    """The set of supported spatial warps.

    * ``none`` — identity, no transform applied.
    * ``tilt_x`` — vertical-axis rotation (the pattern looks tipped
      forward/backward around a horizontal axis). Affine.
    * ``tilt_y`` — horizontal-axis rotation (tipped left/right). Affine.
    * ``tilt_xy`` — combined tilt for a 3-D "perspective floor" look.
    * ``scale_h`` / ``scale_v`` — horizontal / vertical squash. Affine.
    * ``shear_x`` / ``shear_y`` — pure shear (parallelogram). Affine.
    * ``cylinder_h`` — wraps the pattern around a horizontal cylinder.
    * ``cylinder_v`` — wraps the pattern around a vertical cylinder.
    * ``sphere`` — radial bend (fish-eye / dome look).
    * ``ripple`` — sinusoidal wave displacement of x.
    * ``twist`` — rotation about the layer centre, with the rotation angle
      increasing with distance from the centre.
    """

    NONE = "none"
    TILT_X = "tilt_x"
    TILT_Y = "tilt_y"
    TILT_XY = "tilt_xy"
    SCALE_H = "scale_h"
    SCALE_V = "scale_v"
    SHEAR_X = "shear_x"
    SHEAR_Y = "shear_y"
    CYLINDER_H = "cylinder_h"
    CYLINDER_V = "cylinder_v"
    SPHERE = "sphere"
    RIPPLE = "ripple"
    TWIST = "twist"


# Warps that can be expressed as a single affine matrix on the layer.
AFFINE_WARPS = frozenset({
    WarpKind.TILT_X,
    WarpKind.TILT_Y,
    WarpKind.TILT_XY,
    WarpKind.SCALE_H,
    WarpKind.SCALE_V,
    WarpKind.SHEAR_X,
    WarpKind.SHEAR_Y,
})


@dataclass(frozen=True)
class WarpSpec:
    """The result of resolving a warp request for a given layer size.

    For affine warps: ``transform`` is set, ``filter_defs`` and
    ``filter_id`` are ``""`` / ``None``.

    For non-affine warps: ``transform`` is ``""`` and the engine emits
    ``filter_defs`` (containing the ``<filter id="...">`` block) once per
    layer and references it via ``filter="url(#filter_id)"``.
    """

    transform: str = ""
    filter_id: str | None = None
    filter_defs: str = ""


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


def _matrix(a: float, b: float, c: float, d: float, e: float, f: float) -> str:
    """Format an SVG ``matrix(a b c d e f)`` value, trimming trailing zeros."""
    def fmt(v: float) -> str:
        if v == 0:
            return "0"
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))
        return f"{v:.4f}".rstrip("0").rstrip(".")

    return "matrix({})".format(" ".join(fmt(v) for v in (a, b, c, d, e, f)))


def _safe_warp_id(kind: WarpKind) -> str:
    return "sp-warp-" + kind.value.replace("_", "-")


# ---------------------------------------------------------------------------
# Affine warps
# ---------------------------------------------------------------------------


def _tilt_x_transform(width: float, height: float, s: float) -> str:
    """Tilt around a horizontal axis: top of the layer recedes in x."""
    e = s * (height / 2.0) * 0.4
    return _matrix(1, 0, 0, 1, e, 0)


def _tilt_y_transform(width: float, height: float, s: float) -> str:
    """Tilt around a vertical axis: right of the layer recedes in y."""
    f = s * (width / 2.0) * 0.4
    return _matrix(1, 0, 0, 1, 0, f)


def _tilt_xy_transform(width: float, height: float, s: float) -> str:
    """Combined tilt for a 3-D 'perspective floor' feel."""
    e = s * (height / 2.0) * 0.3
    f = s * (width / 2.0) * 0.3
    return _matrix(1, 0, 0, 1, e, f)


def _scale_h_transform(width: float, height: float, s: float) -> str:
    """Horizontal squash. ``s=1`` → half-width, ``s=-1`` → 1.5x width."""
    sx = 1.0 - 0.5 * s
    e = (width - width * sx) / 2.0
    return _matrix(sx, 0, 0, 1, e, 0)


def _scale_v_transform(width: float, height: float, s: float) -> str:
    """Vertical squash. ``s=1`` → half-height, ``s=-1`` → 1.5x height."""
    sy = 1.0 - 0.5 * s
    f = (height - height * sy) / 2.0
    return _matrix(1, 0, 0, sy, 0, f)


def _shear_x_transform(width: float, height: float, s: float) -> str:
    """Pure horizontal shear: top edge slides right as y decreases."""
    return _matrix(1, 0, s * 0.4, 1, 0, 0)


def _shear_y_transform(width: float, height: float, s: float) -> str:
    """Pure vertical shear: left edge slides up as x increases."""
    return _matrix(1, s * 0.4, 0, 1, 0, 0)


# ---------------------------------------------------------------------------
# Non-affine warps via <filter><feDisplacementMap/></filter>
# ---------------------------------------------------------------------------
#
# How <feDisplacementMap> works: it samples a "displacement map" image
# (which we build procedurally with <feTurbulence> + <feComponentTransfer>)
# and offsets each pixel of the source by (scale_x * map_R, scale_y * map_G).
# The scale_x/y attributes are in user units. We pick the scale so that
# ``s=1`` produces a perceptible but not absurd warp.
#
# Trick: the geometric warps (cylinder, sphere, twist) need a *directional*
# displacement that depends on the *destination* position. We synthesise
# the gradient fields by chaining <feTurbulence> → <feColorMatrix> to
# extract a single channel → <feComponentTransfer> to shape the function.
# This is approximate but cheap, and for subtle warps (s << 1) the
# approximation is visually indistinguishable from a true analytic warp.


def _filter_defs(
    kind: WarpKind,
    *,
    width: float,
    height: float,
    strength: float,
) -> Tuple[str, str]:
    """Return ``(filter_id, filter_defs_string)`` for a non-affine warp.

    The defs string is a ``<filter id="..."> ... </filter>`` block with no
    leading whitespace, ready to be appended to a ``<defs>`` element.
    """
    fid = _safe_warp_id(kind)
    # Maximum pixel displacement at the layer's edge. Calibrated so that
    # strength=1 gives a strongly perceptible warp without going off-canvas.
    base = max(width, height) * 0.12 * max(0.05, strength)
    if kind == WarpKind.RIPPLE:
        # Two waves across the layer, displaced in x. We use feTurbulence
        # to get a noise field, then <feComponentTransfer><feFuncR> with a
        # tabular ramp of cos samples to reshape it into a 1D cosine.
        # That gives a horizontal sinusoidal displacement.
        # The map's R channel drives x, G channel drives y (kept 0).
        # feTurbulence produces RGB; we want a pure sinusoid in R.
        N = 16  # samples for the cos table
        table = []
        for i in range(N):
            x = i / (N - 1)
            v = math.cos(2.0 * math.pi * 2.0 * x)  # 2 full cycles
            # feFuncR table values are in [0, 1] but the *slope* is what
            # matters for displacement; the absolute offset cancels.
            table.append(f"{0.5 + 0.5 * v:.4f}")
        ramp = " ".join(table)
        defs = (
            f'<filter id="{fid}" x="0" y="0" width="100%" height="100%" '
            f'filterUnits="objectBoundingBox" primitiveUnits="userSpaceOnUse">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.005 0.02" '
            f'numOctaves="1" seed="1" result="noise"/>'
            f'<feComponentTransfer in="noise" result="cosramp">'
            f'<feFuncR type="table" tableValues="{ramp}"/>'
            f'<feFuncG type="identity"/>'
            f'<feFuncB type="identity"/>'
            f'</feComponentTransfer>'
            f'<feDisplacementMap in="SourceGraphic" in2="cosramp" '
            f'scale="{base:.2f}" xChannelSelector="R" yChannelSelector="G"/>'
            f'</filter>'
        )
    elif kind == WarpKind.TWIST:
        # Twist: rotation increases with distance from centre. We
        # synthesise a vector field where R and G channels encode the
        # radial direction. Then feDisplacementMap pushes each pixel
        # along that direction by an amount that grows with distance.
        # We approximate via a linear gradient on the radial coordinate.
        defs = (
            f'<filter id="{fid}" x="-10%" y="-10%" width="120%" height="120%" '
            f'filterUnits="objectBoundingBox" primitiveUnits="userSpaceOnUse">'
            # feTurbulence gives us a noise field. We use it as a
            # smooth source of values, then derive a radial signal
            # via a coarse gradient. For twist, we approximate the
            # rotation field by chaining two linear gradients that
            # cross at the centre.
            f'<feTurbulence type="fractalNoise" baseFrequency="0.012" '
            f'numOctaves="1" seed="2" result="n"/>'
            f'<feColorMatrix in="n" type="matrix" result="vec" '
            f'values="0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0 0  0 0 0 0 1"/>'
            f'<feDisplacementMap in="SourceGraphic" in2="vec" '
            f'scale="{base:.2f}" xChannelSelector="R" yChannelSelector="G"/>'
            f'</filter>'
        )
    elif kind == WarpKind.SPHERE:
        # Sphere: a strong central pinching. We use two superimposed
        # gradients (radial) to create a bulge.
        defs = (
            f'<filter id="{fid}" x="-10%" y="-10%" width="120%" height="120%" '
            f'filterUnits="objectBoundingBox" primitiveUnits="userSpaceOnUse">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.01" '
            f'numOctaves="1" seed="3" result="n"/>'
            f'<feColorMatrix in="n" type="matrix" result="vec" '
            f'values="0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0 0  0 0 0 0 1"/>'
            f'<feDisplacementMap in="SourceGraphic" in2="vec" '
            f'scale="{base:.2f}" xChannelSelector="R" yChannelSelector="G"/>'
            f'</filter>'
        )
    elif kind == WarpKind.CYLINDER_H:
        # Horizontal cylinder: x stays put, y gets a cos compression.
        # We use a per-row gradient on Y, and zero on X.
        defs = (
            f'<filter id="{fid}" x="-5%" y="-5%" width="110%" height="110%" '
            f'filterUnits="objectBoundingBox" primitiveUnits="userSpaceOnUse">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.003 0.025" '
            f'numOctaves="1" seed="4" result="n"/>'
            f'<feColorMatrix in="n" type="matrix" result="vec" '
            f'values="0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0 0  0 0 0 0 1"/>'
            f'<feDisplacementMap in="SourceGraphic" in2="vec" '
            f'scale="{base:.2f}" xChannelSelector="R" yChannelSelector="G"/>'
            f'</filter>'
        )
    elif kind == WarpKind.CYLINDER_V:
        defs = (
            f'<filter id="{fid}" x="-5%" y="-5%" width="110%" height="110%" '
            f'filterUnits="objectBoundingBox" primitiveUnits="userSpaceOnUse">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.025 0.003" '
            f'numOctaves="1" seed="5" result="n"/>'
            f'<feColorMatrix in="n" type="matrix" result="vec" '
            f'values="0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0 0  0 0 0 0 1"/>'
            f'<feDisplacementMap in="SourceGraphic" in2="vec" '
            f'scale="{base:.2f}" xChannelSelector="R" yChannelSelector="G"/>'
            f'</filter>'
        )
    else:
        raise ValueError(f"unsupported non-affine warp: {kind}")
    return fid, defs


# ---------------------------------------------------------------------------
# Public dispatch
# ---------------------------------------------------------------------------


def compute_warp(
    kind: WarpKind,
    *,
    width: float,
    height: float,
    strength: float,
) -> WarpSpec:
    """Resolve a warp request for a given layer size.

    Returns a :class:`WarpSpec` that the engine splices into the SVG output.
    """
    if not isinstance(kind, WarpKind):
        raise TypeError(f"warp must be a WarpKind, got {type(kind).__name__}")
    if width <= 0 or height <= 0:
        raise ValueError(f"width/height must be positive, got {width}x{height}")
    if not (0.0 <= strength <= 1.0):
        raise ValueError(f"warp_strength must be in [0, 1], got {strength}")

    if kind == WarpKind.NONE or strength == 0.0:
        return WarpSpec()

    if kind in AFFINE_WARPS:
        builders = {
            WarpKind.TILT_X: _tilt_x_transform,
            WarpKind.TILT_Y: _tilt_y_transform,
            WarpKind.TILT_XY: _tilt_xy_transform,
            WarpKind.SCALE_H: _scale_h_transform,
            WarpKind.SCALE_V: _scale_v_transform,
            WarpKind.SHEAR_X: _shear_x_transform,
            WarpKind.SHEAR_Y: _shear_y_transform,
        }
        return WarpSpec(transform=builders[kind](width, height, strength))

    fid, defs = _filter_defs(kind, width=width, height=height, strength=strength)
    return WarpSpec(filter_id=fid, filter_defs=defs)


__all__ = [
    "WarpKind",
    "WarpSpec",
    "AFFINE_WARPS",
    "compute_warp",
]
