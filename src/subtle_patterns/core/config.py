"""Configuration schema for SubtlePatterns.

A SubtlePatterns configuration is a plain Python ``dict`` (or JSON / YAML file)
that fully describes a pattern or multi-layer overlay. This module provides
dataclasses that validate and normalize the schema, plus helpers to load
configs from disk.

Why dataclasses (and not pydantic)?
    Zero hard dependencies, simple semantics, and the validation surface is
    small. ``__post_init__`` checks cover everything we need; richer frameworks
    would be over-engineering.

Two top-level shapes:

* :class:`PatternConfig` — describes a single pattern.
* :class:`OverlayConfig` — describes a multi-layer overlay (a list of
  ``PatternConfig`` + global rendering options).
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence, Tuple, Union

from .warp import WarpKind

# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

Size = Tuple[float, float]
"""A canvas size as ``(width, height)`` in user units (no unit, no px suffix)."""


class Color(str):
    """A string subclass that validates CSS colour syntax.

    Accepts any of: ``#rgb``, ``#rgba``, ``#rrggbb``, ``#rrggbbaa``,
    ``rgb(r,g,b)``, ``rgba(r,g,b,a)``, or the keywords ``none``/``currentColor``.

    Stored as the *normalized* lower-case form so configs are deterministic.
    """

    _HEX = re.compile(r"^#[0-9a-fA-F]{3}([0-9a-fA-F]{1}([0-9a-fA-F]{2}([0-9a-fA-F]{2})?)?)?$")
    _FUNC = re.compile(
        r"^rgba?\(\s*"
        r"(-?\d+(?:\.\d+)?%?)\s*[, ]\s*"
        r"(-?\d+(?:\.\d+)?%?)\s*[, ]\s*"
        r"(-?\d+(?:\.\d+)?%?)"
        r"(?:\s*[,/]\s*(-?\d+(?:\.\d+)?%?))?"
        r"\s*\)$"
    )

    def __new__(cls, value: str) -> "Color":
        if not isinstance(value, str):
            raise TypeError(f"Color must be a string, got {type(value).__name__}")
        v = value.strip()
        low = v.lower()
        if low in {"none", "currentcolor", "transparent"}:
            return super().__new__(cls, low)
        if cls._HEX.match(v):
            return super().__new__(cls, "#" + v[1:].lower())
        m = cls._FUNC.match(v)
        if m:
            return super().__new__(cls, v.replace(" ", "").lower())
        raise ValueError(f"Invalid CSS colour: {value!r}")

    @property
    def is_opaque(self) -> bool:
        """``True`` if the colour is guaranteed to be fully opaque.

        ``#rrggbb`` and ``rgb()`` are opaque; ``#rrggbbaa``, ``rgba()``,
        ``transparent``, and ``none`` are not. ``currentColor`` is treated
        as opaque (its alpha is resolved by the consumer).
        """
        if self == "none" or self == "transparent":
            return False
        if self.startswith("#"):
            return len(self) in (4, 7)  # rgb / rrggbb
        if self.startswith("rgb("):
            return True
        if self.startswith("rgba("):
            return False
        return True  # currentColor, named colours


class BlendMode(str, Enum):
    """SVG compositing blend modes.

    Subset of the CSS Compositing & Blending Level 1 set that is well-supported
    in modern browsers and renders usefully for pattern overlays. Order is
    roughly "least → most destructive" so iterating in the REPL is useful.
    """

    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    DARKEN = "darken"
    LIGHTEN = "lighten"
    COLOR_DODGE = "color-dodge"
    COLOR_BURN = "color-burn"
    HARD_LIGHT = "hard-light"
    SOFT_LIGHT = "soft-light"
    DIFFERENCE = "difference"
    EXCLUSION = "exclusion"
    HUE = "hue"
    SATURATION = "saturation"
    COLOR = "color"
    LUMINOSITY = "luminosity"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _clamp(name: str, value: float, lo: float, hi: float) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{name!r} must be a finite number, got {value!r}")
    if value < lo or value > hi:
        raise ValueError(f"{name!r}={value!r} out of range [{lo}, {hi}]")
    return float(value)


def _coerce_color(name: str, value: Any) -> Color:
    if isinstance(value, Color):
        return value
    if value is None:
        return Color("none")
    if isinstance(value, str):
        return Color(value)
    raise TypeError(f"{name!r} must be a string colour or None, got {type(value).__name__}")


def _coerce_positive(name: str, value: Any, *, allow_zero: bool = False) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name!r} must be a number, got {type(value).__name__}") from exc
    if not math.isfinite(f):
        raise ValueError(f"{name!r} must be finite")
    if allow_zero:
        if f < 0:
            raise ValueError(f"{name!r} must be >= 0, got {f!r}")
    else:
        if f <= 0:
            raise ValueError(f"{name!r} must be > 0, got {f!r}")
    return f


# ---------------------------------------------------------------------------
# PatternConfig
# ---------------------------------------------------------------------------

#: Names of every pattern family the library ships with. Used for validation
#: and to drive ``subtle-patterns list-presets``.
PATTERN_FAMILIES: frozenset[str] = frozenset({
    "grid",
    "dot_grid",
    "diagonal_lines",
    "cross_hatch",
    "hex_mesh",
    "triangular_mesh",
    "wave_field",
    "contour_lines",
    "topographic",
    "voronoi",
    "organic_blobs",
    "constellation",
    "particles",
    "fractal_silhouette",
    "noise_field",
    "scanlines",
    "circuit_traces",
})


@dataclass
class PatternConfig:
    """Declarative configuration for a single pattern.

    The most common fields are listed first. Each pattern family reads a
    subset of the fields below; unknown fields are *silently ignored* so
    configs can be copy-pasted across families without errors (but the
    :attr:`family` field controls dispatch).

    Attributes
    ----------
    family:
        Pattern family name. Must be one of :data:`PATTERN_FAMILIES`.
    stroke / fill:
        Primary colours. Default is no stroke and a very light fill — pattern
        authors should set at least one.
    stroke_opacity / fill_opacity:
        Alpha applied to ``stroke``/``fill`` *before* the layer's own
        ``opacity`` is applied. Default 0.15 for stroke, 0.12 for fill.
    opacity:
        Layer-level opacity. The rendered element opacity is
        ``stroke_opacity * opacity`` (or ``fill_opacity * opacity``).
    spacing:
        Primary spacing parameter (grid cell size, dot pitch, hex radius, etc.).
        Family-specific meaning.
    density:
        Element density multiplier (0.1 → 1.0+). 1.0 = "as designed".
    thickness:
        Stroke width.
    radius:
        Primary radius (dot radius, particle radius, hex corner radius, …).
    levels:
        Number of contour / isoline / wave levels.
    amplitude:
        Wave amplitude / blob amplitude in user units.
    frequency:
        Wave / noise spatial frequency (cycles per user unit). Higher = more
        cycles.
    jitter:
        Random positional jitter in [0, 1]. 0 = perfectly regular.
    seed:
        Per-pattern seed override. Combined with the renderer-level seed to
        produce a deterministic stream.
    blend_mode:
        Compositing mode for this pattern's layer.
    curve_segments:
        Number of cubic Bezier segments per curve. Higher = smoother, more
        expensive.
    variant:
        Family-specific preset name (e.g. ``"hex.flat"``, ``"wave.tanh"``).
        See :doc:`docs/REFERENCE` for the list per family.
    """

    family: str
    stroke: Color = field(default_factory=lambda: Color("none"))
    fill: Color = field(default_factory=lambda: Color("none"))
    stroke_opacity: float = 0.15
    fill_opacity: float = 0.12
    opacity: float = 1.0
    spacing: float = 40.0
    density: float = 1.0
    thickness: float = 1.0
    radius: float = 1.5
    levels: int = 12
    amplitude: float = 30.0
    frequency: float = 0.01
    jitter: float = 0.0
    seed: int = 0
    blend_mode: BlendMode = BlendMode.NORMAL
    curve_segments: int = 32
    variant: str = ""
    warp: WarpKind = WarpKind.NONE
    warp_strength: float = 0.3

    # ---- Validation ------------------------------------------------------

    def __post_init__(self) -> None:
        if self.family not in PATTERN_FAMILIES:
            raise ValueError(
                f"Unknown pattern family {self.family!r}. "
                f"Valid options: {sorted(PATTERN_FAMILIES)}"
            )
        self.stroke = _coerce_color("stroke", self.stroke)
        self.fill = _coerce_color("fill", self.fill)
        self.stroke_opacity = _clamp("stroke_opacity", self.stroke_opacity, 0.0, 1.0)
        self.fill_opacity = _clamp("fill_opacity", self.fill_opacity, 0.0, 1.0)
        self.opacity = _clamp("opacity", self.opacity, 0.0, 1.0)
        self.spacing = _coerce_positive("spacing", self.spacing)
        self.density = _clamp("density", self.density, 0.05, 10.0)
        self.thickness = _clamp("thickness", self.thickness, 0.0, 32.0)
        self.radius = _clamp("radius", self.radius, 0.0, 1024.0)
        self.levels = int(self.levels)
        if self.levels < 1 or self.levels > 256:
            raise ValueError(f"levels={self.levels!r} out of range [1, 256]")
        self.amplitude = float(self.amplitude)
        if not math.isfinite(self.amplitude):
            raise ValueError("amplitude must be finite")
        self.frequency = _coerce_positive("frequency", self.frequency)
        self.jitter = _clamp("jitter", self.jitter, 0.0, 1.0)
        self.seed = int(self.seed)
        if isinstance(self.blend_mode, str) and not isinstance(self.blend_mode, BlendMode):
            self.blend_mode = BlendMode(self.blend_mode)
        self.curve_segments = int(self.curve_segments)
        if self.curve_segments < 2 or self.curve_segments > 512:
            raise ValueError(
                f"curve_segments={self.curve_segments!r} out of range [2, 512]"
            )
        if not isinstance(self.variant, str):
            raise TypeError("variant must be a string")
        if isinstance(self.warp, str) and not isinstance(self.warp, WarpKind):
            self.warp = WarpKind(self.warp)
        elif not isinstance(self.warp, WarpKind):
            raise TypeError(
                f"warp must be a WarpKind or string, got {type(self.warp).__name__}"
            )
        self.warp_strength = _clamp("warp_strength", self.warp_strength, 0.0, 1.0)
        if not (self.stroke != "none" or self.fill != "none"):
            # Patterns with neither stroke nor fill produce no visible output.
            # We allow it (the user may be compositing via blend modes) but
            # emit a warning at render-time, not here, to keep this constructor
            # side-effect-free.
            pass

    # ---- Construction ----------------------------------------------------

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PatternConfig":
        """Build a config from a plain ``dict`` (e.g. loaded from JSON/YAML).

        Unknown keys are *silently ignored* so the same dict can be reused
        across families. ``family`` is required. Numeric values that are
        passed as strings (e.g. from ``parse_inline``) are coerced to their
        declared type.
        """
        if "family" not in data:
            raise ValueError("Pattern config requires a 'family' key")
        known = {f.name: f for f in fields(cls)}
        type_map: dict[str, type] = {
            "stroke": Color,
            "fill": Color,
            "stroke_opacity": float,
            "fill_opacity": float,
            "opacity": float,
            "spacing": float,
            "density": float,
            "thickness": float,
            "radius": float,
            "levels": int,
            "amplitude": float,
            "frequency": float,
            "jitter": float,
            "seed": int,
            "curve_segments": int,
            "blend_mode": str,
            "warp": str,
            "warp_strength": float,
        }
        kwargs: dict[str, Any] = {}
        for k, v in data.items():
            if k not in known:
                continue
            if k in type_map and v is not None and not isinstance(v, type_map[k]):
                try:
                    v = type_map[k](v)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Config field {k!r} could not be coerced to "
                        f"{type_map[k].__name__} from {v!r}"
                    )
            kwargs[k] = v
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain ``dict`` representation (JSON-serializable)."""
        out: dict[str, Any] = {}
        for f in fields(self):
            v = getattr(self, f.name)
            if isinstance(v, Color):
                v = str(v)
            elif isinstance(v, BlendMode):
                v = v.value
            elif isinstance(v, WarpKind):
                v = v.value
            out[f.name] = v
        return out

    def merged(self, overrides: Mapping[str, Any]) -> "PatternConfig":
        """Return a copy with the given overrides applied."""
        d = self.to_dict()
        d.update(overrides)
        return PatternConfig.from_dict(d)


# ---------------------------------------------------------------------------
# OverlayConfig
# ---------------------------------------------------------------------------

@dataclass
class OverlayConfig:
    """Multi-layer overlay configuration.

    Attributes
    ----------
    layers:
        Ordered list of :class:`PatternConfig`. Rendered bottom-to-top, so
        later layers appear *on top* of earlier ones.
    width / height:
        Canvas size. Either can be set; the other is inferred from
        ``aspect_ratio`` (default 16:9) if missing.
    aspect_ratio:
        Used to fill in a missing dimension. Ignored if both are given.
    background:
        Optional backdrop fill — by default the overlay is fully transparent
        so it can be layered on any background. If set, must be a CSS colour
        or ``"none"`` (the default).
    title:
        Optional ``<title>`` for accessibility tools.
    """

    layers: list[PatternConfig] = field(default_factory=list)
    width: float = 1600.0
    height: float = 900.0
    aspect_ratio: float = 16.0 / 9.0
    background: Color = field(default_factory=lambda: Color("none"))
    title: str = ""

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError(
                f"width/height must be positive, got {self.width}x{self.height}"
            )
        if not (0.01 <= self.aspect_ratio <= 100.0):
            raise ValueError(f"aspect_ratio={self.aspect_ratio!r} out of range")
        self.background = _coerce_color("background", self.background)
        if not isinstance(self.title, str):
            raise TypeError("title must be a string")
        # Normalize layer configs.
        normalized: list[PatternConfig] = []
        for i, layer in enumerate(self.layers):
            if isinstance(layer, PatternConfig):
                normalized.append(layer)
            elif isinstance(layer, Mapping):
                normalized.append(PatternConfig.from_dict(layer))
            else:
                raise TypeError(
                    f"layers[{i}] must be a PatternConfig or dict, got "
                    f"{type(layer).__name__}"
                )
        self.layers = normalized

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OverlayConfig":
        if "layers" not in data:
            raise ValueError("Overlay config requires a 'layers' key")
        d = dict(data)
        d.setdefault("width", 1600.0)
        d.setdefault("height", 900.0)
        d.setdefault("aspect_ratio", 16.0 / 9.0)
        return cls(**d)

    def to_dict(self) -> dict[str, Any]:
        return {
            "layers": [layer.to_dict() for layer in self.layers],
            "width": self.width,
            "height": self.height,
            "aspect_ratio": self.aspect_ratio,
            "background": str(self.background),
            "title": self.title,
        }

    @classmethod
    def from_pattern(
        cls,
        pattern: Union[PatternConfig, Mapping[str, Any]],
        **overrides: Any,
    ) -> "OverlayConfig":
        """Convenience: build a single-layer overlay from a pattern config."""
        cfg = (
            pattern
            if isinstance(pattern, PatternConfig)
            else PatternConfig.from_dict(pattern)
        )
        width = float(overrides.pop("width", 1600.0))
        height = float(overrides.pop("height", 900.0))
        aspect = float(overrides.pop("aspect_ratio", 16.0 / 9.0))
        background = overrides.pop("background", "none")
        title = overrides.pop("title", "")
        if overrides:
            raise TypeError(f"Unexpected keyword arguments: {sorted(overrides)}")
        return cls(
            layers=[cfg],
            width=width,
            height=height,
            aspect_ratio=aspect,
            background=Color(background),
            title=title,
        )


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------

def parse_config_file(
    path: Union[str, os.PathLike[str]],
    *,
    prefer: str = "auto",
) -> Union[PatternConfig, OverlayConfig]:
    """Load a config from a JSON or YAML file.

    The shape is auto-detected: configs with a ``layers`` key become
    :class:`OverlayConfig`; everything else becomes a :class:`PatternConfig`.

    Parameters
    ----------
    path:
        File path. Extension ``.yaml`` / ``.yml`` triggers YAML parsing if
        PyYAML is available; otherwise JSON is used and the file is parsed
        by extension first.
    prefer:
        ``"auto"`` (default), ``"yaml"``, or ``"json"`` — force a parser.
    """
    path = str(path)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()

    ext = os.path.splitext(path)[1].lower()
    use_yaml = prefer == "yaml" or (prefer == "auto" and ext in {".yaml", ".yml"})
    use_json = prefer == "json" or (prefer == "auto" and ext == ".json")

    data: Any
    if use_yaml:
        try:
            import yaml  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "PyYAML is required to load YAML configs. "
                "Install with `pip install subtle-patterns[yaml]`."
            ) from exc
        data = yaml.safe_load(text)
    elif use_json:
        data = json.loads(text)
    else:
        # Try YAML first if available, then fall back to JSON.
        try:
            import yaml  # type: ignore
            data = yaml.safe_load(text)
        except ImportError:
            data = json.loads(text)

    if not isinstance(data, Mapping):
        raise ValueError(f"Config root in {path} must be a mapping, got {type(data).__name__}")

    if "layers" in data:
        return OverlayConfig.from_dict(data)
    return PatternConfig.from_dict(data)


# ---------------------------------------------------------------------------
# Inline string parsing (handy for the CLI and ad-hoc scripting)
# ---------------------------------------------------------------------------

def parse_inline(query: str) -> Union[PatternConfig, OverlayConfig]:
    """Parse a tiny ``key=value;key=value;...`` string into a config.

    Example::

        parse_inline("family=contour_lines;stroke=#0d2f57;levels=14")
    """
    out: dict[str, str] = {}
    for chunk in query.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError(f"Expected key=value, got {chunk!r}")
        k, _, v = chunk.partition("=")
        out[k.strip()] = v.strip()
    if "layers" in out:
        raise ValueError("'layers' is not valid in an inline pattern string")
    if "family" not in out:
        raise ValueError("Inline pattern string must include 'family=...'")
    return PatternConfig.from_dict(out)
