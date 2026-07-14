"""Built-in pattern and overlay presets.

A preset is a complete, ready-to-render :class:`PatternConfig` or
:class:`OverlayConfig` registered under a string name. Use them via the
Python API (``get_preset("hex_mesh")``) or the CLI
(``subtle-patterns render hex_mesh``).

Presets are intended as *starting points* — copy any preset, tweak the
fields that matter to your design, and feed the result to
:func:`~subtle_patterns.render_pattern` / :func:`~subtle_patterns.render_overlay`.
"""

from __future__ import annotations

from typing import Dict, Union

from .core.config import OverlayConfig, PatternConfig

_PRESETS: Dict[str, Union[PatternConfig, OverlayConfig]] = {}


def _add(p: Union[PatternConfig, OverlayConfig]) -> None:
    """Backwards-compatible helper; prefer :func:`register_preset`."""
    if hasattr(p, "family"):
        register_preset(p.family, p)  # type: ignore[arg-type]
    else:
        raise TypeError(
            "Overlay presets need an explicit name; use register_preset(name, cfg)."
        )


def register_preset(name: str, cfg: Union[PatternConfig, OverlayConfig, dict]) -> None:
    """Register a preset under ``name``."""
    if isinstance(cfg, dict):
        if "layers" in cfg:
            cfg_obj: Union[PatternConfig, OverlayConfig] = OverlayConfig.from_dict(cfg)
        else:
            cfg_obj = PatternConfig.from_dict(cfg)
    else:
        cfg_obj = cfg
    if name in _PRESETS:
        raise ValueError(f"Preset {name!r} is already registered")
    _PRESETS[name] = cfg_obj


def list_presets() -> list[str]:
    """Return the names of every registered preset, sorted."""
    return sorted(_PRESETS.keys())


def get_preset(name: str) -> Union[PatternConfig, OverlayConfig]:
    """Return the preset registered under ``name``."""
    if name not in _PRESETS:
        raise KeyError(f"Unknown preset {name!r}. Use list_presets() to see options.")
    return _PRESETS[name]


# ---------------------------------------------------------------------------
# Built-in pattern presets
# ---------------------------------------------------------------------------

register_preset("hex_mesh", {
    "family": "hex_mesh",
    "stroke": "#0d2f57",
    "stroke_opacity": 0.18,
    "stroke_width": 0.8,  # NOTE: not a field; silently dropped
    "thickness": 0.8,
    "spacing": 36,
    "variant": "",
})

register_preset("dot_grid", {
    "family": "dot_grid",
    "fill": "#0d2f57",
    "fill_opacity": 0.20,
    "spacing": 24,
    "radius": 1.5,
    "jitter": 0.0,
})

register_preset("blueprint", {
    "family": "grid",
    "stroke": "#1d4d80",
    "stroke_opacity": 0.15,
    "spacing": 32,
    "thickness": 0.6,
    "variant": "double",
})

register_preset("contour_lines", {
    "family": "contour_lines",
    "stroke": "#0d2f57",
    "stroke_opacity": 0.18,
    "levels": 14,
    "amplitude": 50,
    "frequency": 0.0045,
    "variant": "emphasis",
})

register_preset("topographic", {
    "family": "topographic",
    "stroke": "#5a3e1b",
    "stroke_opacity": 0.22,
    "levels": 12,
    "amplitude": 60,
    "frequency": 0.004,
    "thickness": 0.7,
})

register_preset("wave_field", {
    "family": "wave_field",
    "stroke": "#0d2f57",
    "stroke_opacity": 0.15,
    "spacing": 12,
    "amplitude": 18,
    "frequency": 0.012,
    "variant": "fbm",
})

register_preset("circuit_traces", {
    "family": "circuit_traces",
    "stroke": "#39ff14",
    "stroke_opacity": 0.18,
    "thickness": 0.7,
    "spacing": 14,
    "levels": 24,
    "amplitude": 24,
})

register_preset("constellation", {
    "family": "constellation",
    "stroke": "#d4af37",
    "stroke_opacity": 0.25,
    "fill": "#d4af37",
    "fill_opacity": 0.4,
    "levels": 60,
    "spacing": 80,
    "radius": 1.4,
})

register_preset("voronoi", {
    "family": "voronoi",
    "stroke": "#0d2f57",
    "stroke_opacity": 0.18,
    "levels": 26,
    "spacing": 14,
    "thickness": 0.6,
    "variant": "relaxed",
})

register_preset("organic_blobs", {
    "family": "organic_blobs",
    "stroke": "#0d2f57",
    "stroke_opacity": 0.18,
    "levels": 18,
    "spacing": 90,
    "amplitude": 25,
    "frequency": 0.0015,
    "variant": "cubic",
})

register_preset("scanlines", {
    "family": "scanlines",
    "stroke": "#000000",
    "stroke_opacity": 0.08,
    "spacing": 4,
    "thickness": 0.4,
    "variant": "halftone",
})

register_preset("fractal_silhouette", {
    "family": "fractal_silhouette",
    "fill": "#0d2f57",
    "fill_opacity": 0.10,
    "stroke": "none",
    "levels": 8,
    "amplitude": 60,
})

register_preset("noise_field", {
    "family": "noise_field",
    "fill": "#0d2f57",
    "fill_opacity": 0.18,
    "spacing": 14,
    "radius": 0.7,
    "density": 0.7,
    "frequency": 0.012,
    "variant": "turbulence",
})

register_preset("triangular_mesh", {
    "family": "triangular_mesh",
    "stroke": "#0d2f57",
    "stroke_opacity": 0.18,
    "spacing": 28,
    "thickness": 0.6,
})

# ---------------------------------------------------------------------------
# Built-in overlay presets (multi-layer)
# ---------------------------------------------------------------------------

register_preset("noetroniq_network", {
    "width": 1600,
    "height": 900,
    "title": "NOETRONIQ network overlay",
    "layers": [
        {
            "family": "grid",
            "stroke": "#1d4d80",
            "stroke_opacity": 0.10,
            "spacing": 40,
            "thickness": 0.6,
            "variant": "double",
        },
        {
            "family": "dot_grid",
            "fill": "#d4af37",
            "fill_opacity": 0.22,
            "spacing": 80,
            "radius": 2.0,
        },
        {
            "family": "diagonal_lines",
            "stroke": "#8f211f",
            "stroke_opacity": 0.10,
            "spacing": 160,
            "thickness": 1.0,
        },
    ],
})

register_preset("blueprint_overlay", {
    "width": 1600,
    "height": 900,
    "title": "Blueprint overlay",
    "layers": [
        {"family": "grid", "stroke": "#1d4d80", "stroke_opacity": 0.10, "spacing": 32, "thickness": 0.5, "variant": "double"},
        {"family": "contour_lines", "stroke": "#0d2f57", "stroke_opacity": 0.10, "levels": 10, "amplitude": 40, "frequency": 0.005, "thickness": 0.5},
        {"family": "circuit_traces", "stroke": "#1d4d80", "stroke_opacity": 0.10, "levels": 18, "spacing": 16, "amplitude": 24},
    ],
})

register_preset("topographic_organic", {
    "width": 1600,
    "height": 900,
    "title": "Topographic organic overlay",
    "layers": [
        {"family": "topographic", "stroke": "#5a3e1b", "stroke_opacity": 0.18, "levels": 12, "amplitude": 60, "frequency": 0.0035, "thickness": 0.6},
        {"family": "organic_blobs", "stroke": "#0d2f57", "stroke_opacity": 0.10, "levels": 14, "spacing": 90, "amplitude": 18, "frequency": 0.0012, "variant": "cubic"},
        {"family": "particles", "fill": "#d4af37", "fill_opacity": 0.20, "levels": 80, "radius": 0.8, "variant": "size_curve+field"},
    ],
})

register_preset("starlight_dust", {
    "width": 1600,
    "height": 900,
    "title": "Starlight dust overlay",
    "layers": [
        {"family": "noise_field", "fill": "#ffffff", "fill_opacity": 0.10, "spacing": 18, "radius": 0.5, "frequency": 0.02, "variant": "fbm"},
        {"family": "constellation", "fill": "#ffffff", "fill_opacity": 0.30, "stroke": "#ffffff", "stroke_opacity": 0.10, "levels": 40, "radius": 1.0, "variant": "clustered"},
    ],
})

register_preset("hex_constellation", {
    "width": 1600,
    "height": 900,
    "title": "Hex constellation overlay",
    "layers": [
        {"family": "hex_mesh", "stroke": "#0d2f57", "stroke_opacity": 0.12, "spacing": 60, "thickness": 0.6, "variant": "triangulated"},
        {"family": "constellation", "fill": "#d4af37", "fill_opacity": 0.30, "stroke": "#d4af37", "stroke_opacity": 0.10, "levels": 30, "spacing": 100, "radius": 1.2},
    ],
})

register_preset("minimal_lines", {
    "width": 1600,
    "height": 900,
    "title": "Minimal lines overlay",
    "layers": [
        {"family": "diagonal_lines", "stroke": "#0d2f57", "stroke_opacity": 0.10, "spacing": 80, "thickness": 0.5},
        {"family": "cross_hatch", "stroke": "#0d2f57", "stroke_opacity": 0.06, "spacing": 120, "thickness": 0.4, "variant": "triple"},
    ],
})

# ---------------------------------------------------------------------------
# Warped overlays
# ---------------------------------------------------------------------------
#
# These show off the spatial-warp system. Each preset takes a familiar
# pattern and bends it onto a non-flat surface: a tilted floor, a
# horizontal cylinder, a rippling water surface, a twisted ribbon, or a
# spherical dome. The warp is layer-level, so a single preset can mix
# warped and unwarped layers (useful for layering a warped noise field
# under an unwarped grid).
#
# `warp_strength` defaults to 0.3 in PatternConfig; the presets below
# override it because they're meant to demonstrate the warps, not hide
# them.

register_preset("tilted_grid", {
    "width": 1600,
    "height": 900,
    "title": "Tilted perspective grid",
    "layers": [
        # Heavy grid pushed back with a tilt_xy warp — gives a clear
        # "perspective floor" look without resorting to 3-D math.
        {"family": "grid", "stroke": "#1d4d80", "stroke_opacity": 0.18,
         "spacing": 60, "thickness": 0.8, "warp": "tilt_xy", "warp_strength": 0.6},
        # Sparse dots overlaid on the same plane (same warp) read as
        # perspective markers receding into the distance.
        {"family": "dot_grid", "fill": "#d4af37", "fill_opacity": 0.30,
         "spacing": 120, "radius": 1.6, "warp": "tilt_xy", "warp_strength": 0.6},
    ],
})

register_preset("cylindrical_blueprint", {
    "width": 1600,
    "height": 900,
    "title": "Cylindrical blueprint overlay",
    "layers": [
        # Grid wrapped around a horizontal cylinder. Lines at the top
        # and bottom stay straight; lines near the centre compress,
        # making the centre look closer to the viewer.
        {"family": "grid", "stroke": "#1d4d80", "stroke_opacity": 0.20,
         "spacing": 50, "thickness": 0.6, "warp": "cylinder_h", "warp_strength": 0.45},
        # Light circuit traces wrapped the same way for depth.
        {"family": "circuit_traces", "stroke": "#d4af37", "stroke_opacity": 0.10,
         "levels": 14, "spacing": 18, "amplitude": 22, "warp": "cylinder_h", "warp_strength": 0.45},
    ],
})

register_preset("ripple_field", {
    "width": 1600,
    "height": 900,
    "title": "Rippling wave field",
    "layers": [
        # A dense wave field, rippled like the surface of a pond. The
        # `ripple` warp displaces every x in the layer sinusoidally.
        {"family": "wave_field", "stroke": "#1d4d80", "stroke_opacity": 0.18,
         "spacing": 12, "amplitude": 18, "frequency": 0.012,
         "warp": "ripple", "warp_strength": 0.5},
        # A faint dot grid floating above, not warped — gives a sense
        # of the unwarped plane for contrast.
        {"family": "dot_grid", "fill": "#d4af37", "fill_opacity": 0.15,
         "spacing": 80, "radius": 1.0},
    ],
})

register_preset("twisted_ribbon", {
    "width": 1600,
    "height": 900,
    "title": "Twisted ribbon overlay",
    "layers": [
        # A hex mesh twisted around the layer's vertical centre. The
        # hexes near the top and bottom keep their orientation; the
        # ones in the middle rotate the most, creating a 3-D
        # screw-like ribbon.
        {"family": "hex_mesh", "stroke": "#1d4d80", "stroke_opacity": 0.18,
         "spacing": 40, "thickness": 0.6, "warp": "twist", "warp_strength": 0.5},
        # A subtle constellation follows the same twist.
        {"family": "constellation", "fill": "#d4af37", "fill_opacity": 0.25,
         "stroke": "#d4af37", "stroke_opacity": 0.10,
         "levels": 30, "radius": 1.2, "warp": "twist", "warp_strength": 0.5},
    ],
})

register_preset("dome_horizon", {
    "width": 1600,
    "height": 900,
    "title": "Dome horizon overlay",
    "layers": [
        # A topographic noise field projected onto a sphere — reads
        # as a horizon curving over a planetary surface.
        {"family": "topographic", "stroke": "#5a3e1b", "stroke_opacity": 0.20,
         "levels": 12, "amplitude": 60, "frequency": 0.0035, "thickness": 0.6,
         "warp": "sphere", "warp_strength": 0.5},
        # A few faint gold points to mark the curvature.
        {"family": "particles", "fill": "#d4af37", "fill_opacity": 0.18,
         "levels": 60, "radius": 1.0, "warp": "sphere", "warp_strength": 0.5},
    ],
})


# ---------------------------------------------------------------------------
# Perspective + 2D waveform presets
# ---------------------------------------------------------------------------


register_preset("vanishing_corridor", {
    "width": 1600,
    "height": 900,
    "title": "Vanishing corridor (depth warp, 1-point perspective)",
    "layers": [
        # Heavy grid receding toward a vanishing point at the top
        # centre. Use the depth warp to add a true 1-point perspective
        # — horizontal lines converge to the vanishing point as
        # strength increases.
        {"family": "grid", "stroke": "#1d4d80", "stroke_opacity": 0.20,
         "spacing": 60, "thickness": 0.8,
         "warp": "depth", "warp_strength": 0.6,
         "warp_options": {"vp_x": 0.5, "vp_y": 0.0, "depth": 1.2}},
        # Sparse gold dots follow the same perspective — they read
        # as distance markers receding into the corridor.
        {"family": "dot_grid", "fill": "#d4af37", "fill_opacity": 0.30,
         "spacing": 120, "radius": 1.6,
         "warp": "depth", "warp_strength": 0.6,
         "warp_options": {"vp_x": 0.5, "vp_y": 0.0, "depth": 1.2}},
    ],
})


register_preset("off_axis_perspective", {
    "width": 1600,
    "height": 900,
    "title": "Off-axis perspective (depth with custom vanishing point)",
    "layers": [
        # Same depth warp, but the vanishing point is at (0.2, 0.2)
        # — off-centre. The grid recedes toward the upper-left, so
        # the perspective is no longer symmetric.
        {"family": "grid", "stroke": "#5a3e1b", "stroke_opacity": 0.18,
         "spacing": 50, "thickness": 0.6,
         "warp": "depth", "warp_strength": 0.55,
         "warp_options": {"vp_x": 0.2, "vp_y": 0.2, "depth": 1.0}},
        # A topographic layer follows the same perspective, with
        # amplitude reduced so the contour lines stay readable.
        {"family": "topographic", "stroke": "#1d4d80", "stroke_opacity": 0.20,
         "levels": 10, "amplitude": 40, "frequency": 0.005, "thickness": 0.5,
         "warp": "depth", "warp_strength": 0.55,
         "warp_options": {"vp_x": 0.2, "vp_y": 0.2, "depth": 1.0}},
    ],
})


register_preset("diagonal_interference", {
    "width": 1600,
    "height": 900,
    "title": "Diagonal interference (wave_2d with cross term)",
    "layers": [
        # Two-axis sine wave with a non-zero cross term — produces
        # an interference pattern with peaks and nodes on a diagonal
        # grid. The 2D wave displaces the wave-field layer in both
        # x and y.
        {"family": "wave_field", "stroke": "#1d4d80", "stroke_opacity": 0.20,
         "spacing": 14, "amplitude": 18, "frequency": 0.012,
         "warp": "wave_2d", "warp_strength": 0.5,
         "warp_options": {"freq_x": 2, "freq_y": 1, "phase": 0, "cross": 0.5}},
        # A flat dot grid (no warp) sits on top, providing a steady
        # reference point against the moving field below.
        {"family": "dot_grid", "fill": "#d4af37", "fill_opacity": 0.18,
         "spacing": 110, "radius": 1.4},
    ],
})


register_preset("radial_pulse", {
    "width": 1600,
    "height": 900,
    "title": "Radial pulse (wave_2d with equal x and y frequencies)",
    "layers": [
        # freq_x == freq_y produces a radial wave pattern: the
        # displacement is strongest along the diagonals, weakest
        # along the axes. Combined with the wave_field pattern, this
        # reads as concentric ripples emanating from the centre.
        {"family": "wave_field", "stroke": "#1d4d80", "stroke_opacity": 0.18,
         "spacing": 12, "amplitude": 20, "frequency": 0.014,
         "warp": "wave_2d", "warp_strength": 0.6,
         "warp_options": {"freq_x": 1.5, "freq_y": 1.5, "phase": 0.25, "cross": 0.3}},
        # A constellation in gold sits on top, slightly out of phase
        # with the field — the dots feel like they're drifting in
        # the wave.
        {"family": "constellation", "fill": "#d4af37", "fill_opacity": 0.22,
         "stroke": "#d4af37", "stroke_opacity": 0.10,
         "levels": 40, "radius": 1.2,
         "warp": "wave_2d", "warp_strength": 0.4,
         "warp_options": {"freq_x": 1.5, "freq_y": 1.5, "phase": 0.5, "cross": 0.3}},
    ],
})

