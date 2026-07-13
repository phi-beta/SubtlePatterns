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
