"""Spatial warps for SubtlePatterns.

A *warp* is a layer-level geometric transform applied to the output of a
pattern. It lets the same flat-XY pattern read as if it were projected onto
a tilted plane, wrapped around a cylinder, bent into a dome, rippled like
water, or twisted like a screw.

Two implementation strategies are used depending on the warp:

* **Affine** warps (``tilt_x``, ``tilt_y``, ``tilt_xy``, ``scale_h``,
  ``scale_v``, ``shear_x``, ``shear_y``) emit a single
  ``<g transform="matrix(...)">``. The matrix is a true affine
  transform that visibly changes the pattern (skew for the tilts,
  non-uniform scaling anchored at one edge for the scales, real
  shear for the shears).

* **Non-affine** warps (``cylinder_h``, ``cylinder_v``, ``sphere``,
  ``ripple``, ``twist``) emit a single ``<defs>`` block per warp
  containing a ``<filter>`` that uses ``<feImage>`` (a tiny precomputed
  PNG of the displacement field) + ``<feDisplacementMap>``. The
  filter region is set to 150% of the layer so displaced pixels
  aren't clipped at the edges. Each PNG is between 200 and 2000 bytes
  base64-encoded.

This module is pure math + string assembly: it builds the transform
string (affine warps) or the filter ``defs`` string (non-affine
warps). The engine splices the strings into the SVG output.

Why not piecewise-affine row slicing for the non-affine warps? It would
require every pattern implementation to know about slices (to bucket
emitted elements by y). The ``<feImage>`` + ``<feDisplacementMap>``
approach keeps pattern code unaware of warps, gives an exact (not
approximated) result, and the per-warp defs are tiny.

Determinism: each warp's PNG is a pure function of ``(width, height,
strength)``, so re-rendering the same config produces byte-identical
SVG. The PNGs are computed at render time (not cached on disk) so the
math stays in one place.
"""

from __future__ import annotations

import base64
import math
import struct
import zlib
from dataclasses import dataclass
from enum import Enum


class WarpKind(str, Enum):
    """The set of supported spatial warps.

    * ``none`` — identity, no transform applied.
    * ``tilt_x`` — pattern tipped around a horizontal axis (skew:
      top and bottom slide in opposite directions).
    * ``tilt_y`` — pattern tipped around a vertical axis (skew:
      left and right slide in opposite directions).
    * ``tilt_xy`` — combined tilt for a 3-D "perspective floor" look.
    * ``scale_h`` — horizontal squash anchored at the centre. Useful
      for the "wide-angle" look.
    * ``scale_v`` — vertical squash anchored at the centre.
    * ``shear_x`` — pure horizontal shear (parallelogram).
    * ``shear_y`` — pure vertical shear (parallelogram).
    * ``cylinder_h`` — wrapped around a horizontal cylinder.
    * ``cylinder_v`` — wrapped around a vertical cylinder.
    * ``sphere`` — radial bulge (dome / fish-eye look).
    * ``ripple`` — sinusoidal wave displacement in x.
    * ``twist`` — rotation about the layer centre, with the rotation
      angle increasing with distance from the centre.
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
    ``filter_defs`` (containing the ``<filter id="...">`` block) once
    per layer and references it via ``filter="url(#filter_id)"``.
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
#
# All affine warps below produce non-trivial matrices (non-zero off-diagonal
# elements or non-uniform scaling) so they visibly change the pattern
# rather than just translating or uniformly squashing it.
#
# The constants ``0.6`` and ``0.5`` are perceptual gains — without them,
# ``strength=1`` would produce a very subtle effect on the standard
# 1600x900 canvas because the canvas is much wider than tall.
# Tweak them by visual feedback; the math itself is the standard
# skew/affine.


def _tilt_x_transform(width: float, height: float, s: float) -> str:
    """Tilt around a horizontal axis via vertical-axis skew.

    ``x' = x + s * 0.6 * (y - h/2)``
    ``y' = y``

    Top of the layer slides one way, bottom slides the other way. With
    ``s=1`` the top and bottom shift by ±0.3*h user units in opposite
    directions — a strong perspective tip.
    """
    c = s * 0.6
    f = -c * height / 2.0
    return _matrix(1, 0, c, 1, 0, f)


def _tilt_y_transform(width: float, height: float, s: float) -> str:
    """Tilt around a vertical axis via horizontal-axis skew.

    ``x' = x``
    ``y' = y + s * 0.6 * (x - w/2)``
    """
    b = s * 0.6
    e = -b * width / 2.0
    return _matrix(1, b, 0, 1, e, 0)


def _tilt_xy_transform(width: float, height: float, s: float) -> str:
    """Combined tilt: both x-skew and y-skew at 70% of full strength.

    Two skews combined give a 3-D "perspective floor" feel without
    a 3-D matrix. Half-amplitude is enough — at full strength on both
    axes the result reads as a different shape (parallelogram +
    shear), not a tilt.
    """
    c = s * 0.6 * 0.7
    f = -c * height / 2.0
    b = s * 0.6 * 0.7
    e = -b * width / 2.0
    return _matrix(1, b, c, 1, e, f)


def _scale_h_transform(width: float, height: float, s: float) -> str:
    """Non-uniform horizontal scaling anchored at the layer's centre.

    At ``s=1`` the layer is half-width (anchored at the centre), so
    the left and right edges pull toward the middle. This is a true
    visible non-uniform scaling: vertical lines stay vertical but
    become closer together.
    """
    sx = 1.0 - 0.5 * s
    e = width * (1.0 - sx) / 2.0
    return _matrix(sx, 0, 0, 1, e, 0)


def _scale_v_transform(width: float, height: float, s: float) -> str:
    """Non-uniform vertical scaling anchored at the layer's centre."""
    sy = 1.0 - 0.5 * s
    f = height * (1.0 - sy) / 2.0
    return _matrix(1, 0, 0, sy, 0, f)


def _shear_x_transform(width: float, height: float, s: float) -> str:
    """Pure horizontal shear: top edge slides right as y decreases.

    ``x' = x + s * 0.5 * y``
    """
    c = s * 0.5
    return _matrix(1, 0, c, 1, 0, 0)


def _shear_y_transform(width: float, height: float, s: float) -> str:
    """Pure vertical shear: left edge slides up as x increases.

    ``y' = y + s * 0.5 * x``
    """
    b = s * 0.5
    return _matrix(1, b, 0, 1, 0, 0)


# ---------------------------------------------------------------------------
# Non-affine warps via <filter><feImage><feDisplacementMap/></filter>
# ---------------------------------------------------------------------------
#
# Each non-affine warp generates a tiny PNG (1D ramp or small 2D field)
# that encodes the per-pixel displacement (R = x displacement, G = y
# displacement), with 0.5 meaning "no shift" and ±0.45 meaning "max
# shift in that direction". The PNG is embedded as a data: URL inside
# an <feImage>, then <feDisplacementMap> uses it as the in2 source.
# The filter region is 150% of the layer (centered) so displaced
# pixels aren't clipped at the edges.


def _png_chunk(out: bytearray, typ: bytes, data: bytes) -> None:
    out.extend(struct.pack(">I", len(data)))
    out.extend(typ)
    out.extend(data)
    out.extend(struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))


def _make_png_rgba(width: int, height: int, rgba: bytes) -> bytes:
    """Build a minimal RGBA PNG from raw pixel bytes.

    ``rgba`` is the row-major pixel data (no filter bytes). Each
    output scanline is prefixed with a 0 filter byte ("None" filter
    type) per the PNG spec. Many SVG renderers tolerate missing
    filter bytes on 1-row PNGs but not on multi-row PNGs, so this
    is important to get right.
    """
    row_bytes = width * 4
    if len(rgba) != row_bytes * height:
        raise ValueError(
            f"rgba size mismatch: expected {row_bytes * height} bytes "
            f"for {width}x{height} RGBA, got {len(rgba)}"
        )
    out = bytearray(b"\x89PNG\r\n\x1a\n")
    _png_chunk(out, b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    # Per the PNG spec, every scanline starts with a filter type byte.
    # Filter type 0 = "None" (no filtering). We prepend 0 to every row.
    raw = bytearray()
    for j in range(height):
        raw.append(0)
        raw.extend(rgba[j * row_bytes : (j + 1) * row_bytes])
    _png_chunk(out, b"IDAT", zlib.compress(bytes(raw), 9))
    _png_chunk(out, b"IEND", b"")
    return bytes(out)


def _png_data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


# Maximum channel deviation from 0.5. PNG encodes in [0.5 - amp, 0.5 + amp]
# so the max displacement is amp * scale, where scale is the
# feDisplacementMap scale attribute.
_DISP_AMP = 0.45


def _cylinder_h_png(height_norm: int = 48) -> bytes:
    """Vertical 1D ramp (1 column, ``height_norm`` rows).

    Encodes a horizontal-cylinder projection. y' = R*sin((y-cy)/R)
    is approximated by a parabola: dy = -amp * (1 - y^2), which is
    zero at the top and bottom and maximum inward at the centre.
    dx is zero.
    """
    rgba = bytearray()
    for j in range(height_norm):
        y = j / max(height_norm - 1, 1) * 2.0 - 1.0
        # Negative dy pushes pixels toward y=0 (the "equator" of the
        # cylinder). With the filter's `scale`, the max dy is
        # -amp * scale user units (inward at the centre).
        dy = -_DISP_AMP * (1.0 - y * y)
        r_chan = 0.5  # no x displacement
        g_chan = 0.5 + dy
        rgba.extend([
            int(round(max(0, min(255, r_chan * 255)))),
            int(round(max(0, min(255, g_chan * 255)))),
            0, 255,
        ])
    return _make_png_rgba(1, height_norm, bytes(rgba))


def _cylinder_v_png(width_norm: int = 64) -> bytes:
    """Horizontal 1D ramp (1 row, ``width_norm`` columns)."""
    rgba = bytearray()
    for i in range(width_norm):
        x = i / max(width_norm - 1, 1) * 2.0 - 1.0
        dx = -_DISP_AMP * (1.0 - x * x)
        r_chan = 0.5 + dx
        g_chan = 0.5
        rgba.extend([
            int(round(max(0, min(255, r_chan * 255)))),
            int(round(max(0, min(255, g_chan * 255)))),
            0, 255,
        ])
    return _make_png_rgba(width_norm, 1, bytes(rgba))


def _sphere_png(size: int = 32) -> bytes:
    """2D radial bulge field.

    The "dome" effect: pixels near the centre of the field are pushed
    outward radially. A radial field: k(r) = 1 + (1 - r/R)^2 * 1.5
    for r < R, k(r) = 1 otherwise. Displacement vector = (nx, ny) * (k-1)
    where (nx, ny) are normalised coords in [-1, 1].
    """
    R = 0.7
    rgba = bytearray()
    pixels = []
    for j in range(size):
        for i in range(size):
            x = i / max(size - 1, 1) * 2.0 - 1.0
            y = j / max(size - 1, 1) * 2.0 - 1.0
            r = math.sqrt(x * x + y * y)
            if r >= R:
                k = 1.0
            else:
                k = 1.0 + (1.0 - r / R) ** 2 * 1.5
            dx = x * (k - 1.0)
            dy = y * (k - 1.0)
            pixels.append((dx, dy))
    max_abs = max(max(abs(dx), abs(dy)) for dx, dy in pixels) or 1.0
    for dx, dy in pixels:
        r_chan = 0.5 + _DISP_AMP * dx / max_abs
        g_chan = 0.5 + _DISP_AMP * dy / max_abs
        rgba.extend([
            int(round(max(0, min(255, r_chan * 255)))),
            int(round(max(0, min(255, g_chan * 255)))),
            0, 255,
        ])
    return _make_png_rgba(size, size, bytes(rgba))


def _ripple_png(width_norm: int = 64, cycles: int = 2) -> bytes:
    """Horizontal 1D ramp: dx = sin(2*pi*cycles*x)."""
    rgba = bytearray()
    for i in range(width_norm):
        x = i / max(width_norm - 1, 1)
        v = math.sin(2.0 * math.pi * cycles * x)
        r_chan = 0.5 + _DISP_AMP * v
        g_chan = 0.5
        rgba.extend([
            int(round(max(0, min(255, r_chan * 255)))),
            int(round(max(0, min(255, g_chan * 255)))),
            0, 255,
        ])
    return _make_png_rgba(width_norm, 1, bytes(rgba))


def _twist_png(width: int = 32, height: int = 32) -> bytes:
    """2D twist field. Rotation about (0, 0) in normalised coords.

    theta = s * pi/2 * y_norm
    (x', y') = rotate((x, y), theta)
    dx = (cos-1)*x - sin*y
    dy = sin*x + (cos-1)*y
    """
    rgba = bytearray()
    pixels = []
    for j in range(height):
        for i in range(width):
            x = i / max(width - 1, 1) * 2.0 - 1.0
            y = j / max(height - 1, 1) * 2.0 - 1.0
            theta = y * math.pi / 2.0
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            dx = (cos_t - 1.0) * x - sin_t * y
            dy = sin_t * x + (cos_t - 1.0) * y
            pixels.append((dx, dy))
    max_abs = max(max(abs(dx), abs(dy)) for dx, dy in pixels) or 1.0
    for dx, dy in pixels:
        r_chan = 0.5 + _DISP_AMP * dx / max_abs
        g_chan = 0.5 + _DISP_AMP * dy / max_abs
        rgba.extend([
            int(round(max(0, min(255, r_chan * 255)))),
            int(round(max(0, min(255, g_chan * 255)))),
            0, 255,
        ])
    return _make_png_rgba(width, height, bytes(rgba))


# Maximum displacement in user units, used as the feDisplacementMap scale.
# This is multiplied with the PNG channel value's deviation from 0.5
# (max 0.45) to get the actual pixel shift in user units.
def _filter_defs(kind: WarpKind, *, width: float, height: float, strength: float) -> tuple[str, str]:
    """Return ``(filter_id, filter_defs_string)`` for a non-affine warp.

    ``scale`` is the maximum displacement in user units at
    ``strength=1``. It's calibrated to the larger of width/height so
    the effect scales with the layer size.
    """
    fid = _safe_warp_id(kind)
    # Max displacement is 12% of the larger dimension, scaled by
    # strength. With PNG amp=0.45, peak pixel shift = 0.45 * scale.
    base = max(width, height) * 0.12 * max(0.05, strength)
    scale = base / _DISP_AMP  # so peak shift is `base` user units

    if kind == WarpKind.RIPPLE:
        png = _ripple_png()
    elif kind == WarpKind.TWIST:
        png = _twist_png()
    elif kind == WarpKind.SPHERE:
        png = _sphere_png()
    elif kind == WarpKind.CYLINDER_H:
        png = _cylinder_h_png()
    elif kind == WarpKind.CYLINDER_V:
        png = _cylinder_v_png()
    else:
        raise ValueError(f"unsupported non-affine warp: {kind}")

    data_url = _png_data_url(png)
    # Filter region: 50% padding on every side so displaced pixels
    # aren't clipped. Pixels outside the layer's own rect are also
    # drawn (they come from the source itself; the padding just lets
    # them be visible after displacement).
    defs = (
        f'<filter id="{fid}" x="-25%" y="-25%" width="150%" height="150%" '
        f'filterUnits="objectBoundingBox" primitiveUnits="userSpaceOnUse">'
        f'<feImage href="{data_url}" result="disp" preserveAspectRatio="none"/>'
        f'<feDisplacementMap in="SourceGraphic" in2="disp" '
        f'scale="{scale:.2f}" xChannelSelector="R" yChannelSelector="G"/>'
        f'</filter>'
    )
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
