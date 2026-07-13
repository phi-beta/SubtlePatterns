"""Test configuration dataclasses."""

from __future__ import annotations

import json
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from subtle_patterns.core.config import (  # noqa: E402
    BlendMode,
    Color,
    OverlayConfig,
    PATTERN_FAMILIES,
    PatternConfig,
    parse_config_file,
    parse_inline,
)


# ---------------------------------------------------------------------------
# Color
# ---------------------------------------------------------------------------

class TestColor:
    def test_hex_3(self):
        assert str(Color("#abc")) == "#abc"

    def test_hex_6(self):
        assert str(Color("#ABCDEF")) == "#abcdef"

    def test_hex_8_normalizes(self):
        assert str(Color("#aabbccdd")) == "#aabbccdd"

    def test_rgba_keeps_function_form(self):
        c = Color("rgba(0,128,255,0.5)")
        # Whitespace stripped but structure preserved.
        assert c == "rgba(0,128,255,0.5)"

    def test_named_keyword(self):
        assert Color("none") == "none"
        assert Color("currentColor") == "currentcolor"
        assert Color("transparent") == "transparent"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            Color("not-a-color")
        with pytest.raises(ValueError):
            Color("#xyz")

    def test_is_opaque(self):
        assert Color("#fff").is_opaque
        assert Color("#ffffff").is_opaque
        assert Color("rgb(0,0,0)").is_opaque
        assert not Color("rgba(0,0,0,0.5)").is_opaque
        assert not Color("transparent").is_opaque
        assert not Color("#ffffff80").is_opaque
        assert Color("currentColor").is_opaque


# ---------------------------------------------------------------------------
# PatternConfig
# ---------------------------------------------------------------------------

class TestPatternConfig:
    def test_minimal_valid(self):
        cfg = PatternConfig(family="grid")
        assert cfg.family == "grid"
        assert cfg.stroke_opacity == 0.15
        assert cfg.fill_opacity == 0.12

    def test_unknown_family_rejected(self):
        with pytest.raises(ValueError, match="Unknown pattern family"):
            PatternConfig(family="made-up-pattern")

    def test_opacity_clamped(self):
        with pytest.raises(ValueError):
            PatternConfig(family="grid", stroke_opacity=2.0)
        with pytest.raises(ValueError):
            PatternConfig(family="grid", opacity=-0.1)

    def test_levels_bounded(self):
        with pytest.raises(ValueError):
            PatternConfig(family="contour_lines", levels=0)
        with pytest.raises(ValueError):
            PatternConfig(family="contour_lines", levels=1000)

    def test_curve_segments_bounded(self):
        with pytest.raises(ValueError):
            PatternConfig(family="wave_field", curve_segments=1)
        with pytest.raises(ValueError):
            PatternConfig(family="wave_field", curve_segments=1000)

    def test_blend_mode_coerced_from_string(self):
        cfg = PatternConfig(family="grid", blend_mode="multiply")
        assert cfg.blend_mode == BlendMode.MULTIPLY

    def test_blend_mode_rejects_invalid(self):
        with pytest.raises(ValueError):
            PatternConfig(family="grid", blend_mode="not-a-mode")

    def test_from_dict_drops_unknown_keys(self):
        cfg = PatternConfig.from_dict({
            "family": "grid",
            "spacing": 50,
            "unknown_field": "ignored",
        })
        assert cfg.spacing == 50
        assert cfg.family == "grid"

    def test_from_dict_requires_family(self):
        with pytest.raises(ValueError, match="family"):
            PatternConfig.from_dict({"spacing": 50})

    def test_to_dict_round_trip(self):
        original = PatternConfig(family="contour_lines", spacing=42, levels=10)
        d = original.to_dict()
        rebuilt = PatternConfig.from_dict(d)
        assert rebuilt == original

    def test_merged_overrides(self):
        base = PatternConfig(family="grid", spacing=40, stroke="#000000")
        merged = base.merged({"spacing": 100, "stroke": "#ffffff"})
        assert merged.spacing == 100
        assert merged.stroke == "#ffffff"
        assert merged.family == "grid"
        # Base is unchanged.
        assert base.spacing == 40

    def test_all_families_construct(self):
        for fam in PATTERN_FAMILIES:
            PatternConfig(family=fam)


# ---------------------------------------------------------------------------
# OverlayConfig
# ---------------------------------------------------------------------------

class TestOverlayConfig:
    def test_empty_layers(self):
        ov = OverlayConfig()
        assert ov.layers == []
        assert ov.width == 1600.0
        assert ov.height == 900.0
        assert ov.background == "none"

    def test_layers_can_be_dicts_or_configs(self):
        ov = OverlayConfig(layers=[
            PatternConfig(family="grid"),
            {"family": "dot_grid", "spacing": 30},
        ])
        assert len(ov.layers) == 2
        assert ov.layers[0].family == "grid"
        assert ov.layers[1].spacing == 30

    def test_from_dict_requires_layers(self):
        with pytest.raises(ValueError, match="layers"):
            OverlayConfig.from_dict({"width": 100, "height": 100})

    def test_from_pattern_wraps_single(self):
        p = PatternConfig(family="grid")
        ov = OverlayConfig.from_pattern(p)
        assert len(ov.layers) == 1
        assert ov.layers[0] is p

    def test_aspect_ratio_validated(self):
        with pytest.raises(ValueError):
            OverlayConfig(aspect_ratio=0)
        with pytest.raises(ValueError):
            OverlayConfig(aspect_ratio=200)


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------

class TestParseConfigFile:
    def test_loads_json(self, tmp_path):
        path = tmp_path / "cfg.json"
        path.write_text(json.dumps({"family": "grid", "spacing": 60}))
        cfg = parse_config_file(path)
        assert isinstance(cfg, PatternConfig)
        assert cfg.family == "grid"
        assert cfg.spacing == 60

    def test_loads_yaml(self, tmp_path):
        yaml = pytest.importorskip("yaml")
        path = tmp_path / "cfg.yaml"
        path.write_text("family: contour_lines\nspacing: 50\nlevels: 12\n")
        cfg = parse_config_file(path)
        assert isinstance(cfg, PatternConfig)
        assert cfg.family == "contour_lines"
        assert cfg.spacing == 50
        assert cfg.levels == 12

    def test_overlay_yaml_routes_to_overlay(self, tmp_path):
        pytest.importorskip("yaml")
        path = tmp_path / "ov.yaml"
        path.write_text(
            "width: 800\nheight: 600\n"
            "layers:\n  - family: grid\n  - family: dot_grid\n"
        )
        cfg = parse_config_file(path)
        assert isinstance(cfg, OverlayConfig)
        assert len(cfg.layers) == 2

    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            parse_config_file("/nonexistent/path.yaml")


# ---------------------------------------------------------------------------
# Inline parsing
# ---------------------------------------------------------------------------

class TestParseInline:
    def test_basic(self):
        cfg = parse_inline("family=grid;spacing=50;stroke=#0d2f57")
        assert cfg.family == "grid"
        assert cfg.spacing == 50
        assert cfg.stroke == "#0d2f57"

    def test_requires_family(self):
        with pytest.raises(ValueError, match="family"):
            parse_inline("spacing=50")

    def test_rejects_layers(self):
        with pytest.raises(ValueError, match="layers"):
            parse_inline("family=grid;layers=[1,2,3]")
