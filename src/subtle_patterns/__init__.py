"""subtle_patterns — public package.

Public symbols are imported lazily here so that sub-modules can be loaded
independently (e.g. ``from subtle_patterns.svg import SvgDocument``) without
triggering the config validation code paths.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = [
    "BlendMode",
    "Color",
    "OverlayConfig",
    "PatternConfig",
    "Size",
    "gallery_html",
    "get_preset",
    "list_presets",
    "parse_config_file",
    "render_overlay",
    "render_pattern",
]


def __getattr__(name: str):  # PEP 562 lazy module attribute
    if name in {"PatternConfig", "OverlayConfig", "Color", "BlendMode", "Size", "parse_config_file"}:
        from .core import config as _cfg
        return getattr(_cfg, name)
    if name in {"render_pattern", "render_overlay"}:
        from .engine import render_pattern, render_overlay
        return locals()[name]
    if name in {"list_presets", "get_preset"}:
        from . import presets as _p
        return getattr(_p, name)
    if name == "gallery_html":
        from .preview import gallery_html
        return gallery_html
    raise AttributeError(f"module 'subtle_patterns' has no attribute {name!r}")
