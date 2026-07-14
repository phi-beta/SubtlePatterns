"""Render an :class:`OverlayConfig` or :class:`PatternConfig` to an SVG string.

This is the top-level dispatch. The actual drawing logic lives in
:mod:`subtle_patterns.patterns`; the engine's job is to:

1. Resolve the :class:`PatternConfig` (validate, normalize, derive seed).
2. Build an :class:`SvgDocument` and a per-layer :class:`SvgGroup`.
3. Dispatch to the right pattern implementation.
4. Combine layers with the requested blend mode and opacity.
5. Serialize.

The split is deliberate: :mod:`patterns` is purely about geometry and
returns a list of low-level SVG elements (or path-data strings); this
module owns the "make it a document" concerns.
"""

from __future__ import annotations

import xml.etree.ElementTree as _ET
from typing import Mapping, Sequence, Tuple, Union

from .core.config import (
    BlendMode,
    Color,
    OverlayConfig,
    PatternConfig,
    Size,
)
from .core.random_utils import derive_seed
from .core.warp import WarpSpec, compute_warp
from .patterns import PATTERN_REGISTRY, get_pattern
from .svg import SvgDocument, SvgElement, SvgGroup

SizeLike = Union[Size, Tuple[int, int], Mapping[str, float]]


def _coerce_size(size: SizeLike | None, default: Size) -> Size:
    if size is None:
        return default
    if isinstance(size, Mapping):
        return (float(size.get("width", default[0])), float(size.get("height", default[1])))
    if isinstance(size, (tuple, list)) and len(size) == 2:
        return (float(size[0]), float(size[1]))
    raise TypeError(f"size must be (width, height) or a mapping, got {type(size).__name__}")


def _ensure_pattern(cfg: PatternConfig | Mapping[str, any]) -> PatternConfig:
    if isinstance(cfg, PatternConfig):
        return cfg
    return PatternConfig.from_dict(cfg)


def _layer_attrs(cfg: PatternConfig) -> dict[str, object]:
    """Per-layer SVG attributes derived from the config."""
    attrs: dict[str, object] = {
        "fill": str(cfg.fill),
        "fill_opacity": cfg.fill_opacity * cfg.opacity,
        "stroke": str(cfg.stroke),
        "stroke_opacity": cfg.stroke_opacity * cfg.opacity,
        "stroke_width": cfg.thickness,
    }
    # Heuristic: if neither stroke nor fill is set, give the layer a
    # sensible default colour (the consumer can override).
    if cfg.stroke == "none" and cfg.fill == "none":
        attrs["stroke"] = "#888888"
        attrs["stroke_opacity"] = 0.10 * cfg.opacity
    return attrs


def _draw_pattern(
    layer: SvgGroup,
    cfg: PatternConfig,
    size: Size,
    *,
    seed: int,
) -> None:
    """Dispatch to the pattern implementation, with the correct seed."""
    impl = get_pattern(cfg.family)
    layer_seed = derive_seed(seed, cfg.seed, cfg.family, "layer")
    impl(layer, cfg, size, seed=layer_seed)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_pattern(
    config: PatternConfig | Mapping[str, any] | str,
    *,
    size: SizeLike | None = None,
    seed: int = 0,
) -> str:
    """Render a single pattern and return an SVG string.

    Parameters
    ----------
    config:
        A :class:`PatternConfig`, a plain ``dict`` (``{"family": ...}``),
        or the **name of a built-in preset** (e.g. ``"hex_mesh"``).
    size:
        ``(width, height)`` in user units. Default ``(1600, 900)``.
    seed:
        Master seed. Combined with the config's ``seed`` field and family
        name to derive a deterministic per-layer stream.
    """
    if isinstance(config, str):
        from .presets import get_preset
        cfg = get_preset(config)
        # Overlay presets are also valid input here — render them as-is.
        if isinstance(cfg, OverlayConfig):
            if size is not None:
                w, h = _coerce_size(size, default=(cfg.width, cfg.height))
                cfg = OverlayConfig(
                    layers=cfg.layers,
                    width=w, height=h,
                    aspect_ratio=cfg.aspect_ratio,
                    background=cfg.background,
                    title=cfg.title,
                )
            return render_overlay(cfg, seed=seed)
    else:
        cfg = _ensure_pattern(config)

    # Re-do the coerce using a sane default if `size` was None.
    if size is None:
        w, h = 1600.0, 900.0
    else:
        w, h = _coerce_size(size, default=(1600.0, 900.0))

    overlay = OverlayConfig.from_pattern(cfg, width=w, height=h)
    return render_overlay(overlay, seed=seed)


def render_overlay(
    config: OverlayConfig | Mapping[str, any] | str,
    *,
    size: SizeLike | None = None,
    seed: int = 0,
) -> str:
    """Render a multi-layer overlay and return an SVG string.

    Parameters
    ----------
    config:
        An :class:`OverlayConfig`, a plain ``dict`` (``{"layers": [...]}``),
        or the name of a built-in **overlay** preset.
    size:
        ``(width, height)`` override. If omitted, the config's ``width``
        and ``height`` are used.
    seed:
        Master seed.
    """
    if isinstance(config, str):
        from .presets import get_preset
        cfg = get_preset(config)
        if not isinstance(cfg, OverlayConfig):
            cfg = OverlayConfig.from_pattern(cfg)
    elif isinstance(config, OverlayConfig):
        cfg = config
    else:
        cfg = OverlayConfig.from_dict(config)

    if size is not None:
        w, h = _coerce_size(size, default=(cfg.width, cfg.height))
        cfg = OverlayConfig(
            layers=cfg.layers,
            width=w,
            height=h,
            aspect_ratio=cfg.aspect_ratio,
            background=cfg.background,
            title=cfg.title,
        )

    doc = SvgDocument(
        width=cfg.width,
        height=cfg.height,
        title=cfg.title or None,
        desc="SubtlePatterns overlay (decorative).",
    )

    # Optional backdrop fill.
    if cfg.background != "none":
        doc.add(SvgElement("rect", x=0, y=0, width=cfg.width, height=cfg.height, fill=str(cfg.background)))

    # Collect filter <defs> emitted by warped layers so we can attach them
    # to a single top-level <defs> instead of one per layer.
    warp_filter_ids: dict[str, str] = {}

    for i, layer_cfg in enumerate(cfg.layers):
        # Blend modes are applied per layer; SVG supports this via
        # `style="mix-blend-mode: ..."` on the layer <g>.
        layer_attrs: dict[str, object] = dict(_layer_attrs(layer_cfg))
        if layer_cfg.blend_mode != BlendMode.NORMAL:
            layer_attrs["style"] = f"mix-blend-mode: {layer_cfg.blend_mode.value}"

        # Spatial warp: either an affine transform on the layer's <g>, or
        # an SVG <filter> with <feDisplacementMap> (referenced from the
        # layer's <g filter="url(#...)">). See `core.warp` for the math.
        warp_spec: WarpSpec = compute_warp(
            layer_cfg.warp,
            width=cfg.width,
            height=cfg.height,
            strength=layer_cfg.warp_strength,
        )
        if warp_spec.transform:
            layer_attrs["transform"] = warp_spec.transform
        if warp_spec.filter_id is not None:
            layer_attrs["filter"] = f"url(#{warp_spec.filter_id})"
            warp_filter_ids[warp_spec.filter_id] = warp_spec.filter_defs

        layer = SvgGroup(**layer_attrs)
        _draw_pattern(layer, layer_cfg, (cfg.width, cfg.height), seed=derive_seed(seed, i, "layer"))
        doc.add(layer)

    # Emit a single <defs> with every distinct filter used by any layer.
    # We splice this into the SVG via a raw element because the doc's
    # <defs> handling is normally done implicitly by the SvgElement API.
    if warp_filter_ids:
        defs_el = SvgElement("defs", id="sp-warp-defs")
        for fid, defs_xml in warp_filter_ids.items():
            # The filter's id="..." is the same as the key; defs_xml is
            # the entire <filter ...>...</filter> string, so we attach
            # it as a raw child by parsing the outer tag.
            defs_el._el.append(_ET.fromstring(defs_xml))  # noqa: SLF001
        # Inject the <defs> as the first child of the root <svg> (after
        # any <title>/<desc>).
        insert_at = 0
        for child in doc._el:  # noqa: SLF001
            tag = child.tag.split("}")[-1]
            if tag in ("title", "desc"):
                insert_at += 1
            else:
                break
        doc._el.insert(insert_at, defs_el._el)  # noqa: SLF001

    return doc.to_string(pretty=False)
