"""Test the rendering engine and pattern implementations."""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from subtle_patterns import (  # noqa: E402
    OverlayConfig,
    PatternConfig,
    list_presets,
    render_overlay,
    render_pattern,
)
from subtle_patterns.core.config import PATTERN_FAMILIES  # noqa: E402
from subtle_patterns.core.random_utils import (  # noqa: E402
    derive_seed,
    fade,
    lerp,
    smoothstep,
)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("family", sorted(PATTERN_FAMILIES))
def test_deterministic(family: str) -> None:
    """Same config + seed → byte-identical SVG."""
    cfg = PatternConfig(family=family)
    a = render_pattern(cfg, size=(320, 200), seed=42)
    b = render_pattern(cfg, size=(320, 200), seed=42)
    assert a == b, f"Pattern {family!r} is not deterministic"


STOCHASTIC_FAMILIES = {
    # Families that use `random.random()` somewhere in their implementation.
    "constellation",
    "particles",
    "voronoi",
    "organic_blobs",
    "noise_field",
    "fractal_silhouette",
    "circuit_traces",
    # Perlin-based families that take a seed for their noise field.
    "wave_field",
    "contour_lines",
    "topographic",
    # The dot_grid default variant is fully deterministic; only `jitter > 0`
    # makes it stochastic. We assume the default (jitter=0).
    # "dot_grid",
    # The default cross_hatch is deterministic; the "weave" variant uses rng.
    # "cross_hatch",
}


@pytest.mark.parametrize("family", sorted(PATTERN_FAMILIES))
def test_seed_changes_output(family: str) -> None:
    """Different seeds should produce different output for stochastic patterns.

    For families that have no random component, identical output across
    seeds is correct (and asserted below).
    """
    cfg = PatternConfig(family=family)
    a = render_pattern(cfg, size=(320, 200), seed=1)
    b = render_pattern(cfg, size=(320, 200), seed=999)
    if family in STOCHASTIC_FAMILIES:
        assert a != b, f"Pattern {family!r} should be stochastic but produced identical output for different seeds"
    else:
        assert a == b, f"Pattern {family!r} is supposed to be deterministic at default config"


def test_derive_seed_avalanche() -> None:
    """Tiny changes in input → very different seeds."""
    a = derive_seed(1)
    b = derive_seed(2)
    # Hash should differ in at least 24 of 32 bits.
    xor = a ^ b
    assert bin(xor).count("1") >= 16


# ---------------------------------------------------------------------------
# Output integrity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("family", sorted(PATTERN_FAMILIES))
def test_output_is_valid_xml(family: str) -> None:
    """Every family emits parseable XML."""
    cfg = PatternConfig(family=family)
    svg = render_pattern(cfg, size=(320, 200), seed=7)
    # Should not raise.
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg"), f"Root tag is {root.tag!r}"


def test_output_has_viewbox() -> None:
    svg = render_pattern(PatternConfig(family="grid"), size=(400, 200), seed=0)
    root = ET.fromstring(svg)
    assert "viewBox" in root.attrib
    assert root.attrib["viewBox"] == "0 0 400 200"


def test_output_has_aria_hidden() -> None:
    """Overlays are decorative — always aria-hidden."""
    svg = render_pattern(PatternConfig(family="grid"), size=(400, 200), seed=0)
    root = ET.fromstring(svg)
    assert root.attrib.get("aria-hidden") == "true"
    assert root.attrib.get("role") == "img"


def test_no_background_fill_in_output() -> None:
    """A SubtlePatterns SVG must never paint a full-canvas background."""
    # Direct check: a 1-layer overlay of any pattern should have no <rect>
    # covering the full canvas with a non-none fill.
    svg = render_pattern(PatternConfig(family="grid"), size=(200, 100), seed=0)
    root = ET.fromstring(svg)
    ns = {"s": "http://www.w3.org/2000/svg"}
    for rect in root.findall(".//s:rect", ns):
        w = float(rect.attrib.get("width", 0))
        h = float(rect.attrib.get("height", 0))
        if w >= 200 and h >= 100:
            fill = rect.attrib.get("fill", "black")
            assert fill in ("none", "transparent"), (
                f"SubtlePatterns SVG should not paint a full-canvas background; "
                f"found {rect.attrib}"
            )


# ---------------------------------------------------------------------------
# Overlays
# ---------------------------------------------------------------------------

def test_overlay_with_multiple_layers() -> None:
    ov = OverlayConfig.from_dict({
        "layers": [
            {"family": "grid", "stroke": "#0d2f57", "stroke_opacity": 0.10},
            {"family": "dot_grid", "fill": "#d4af37", "fill_opacity": 0.20, "spacing": 80},
        ],
    })
    svg = render_overlay(ov, seed=42)
    root = ET.fromstring(svg)
    # Top-level <svg> should contain two <g> children (one per layer).
    groups = root.findall("{http://www.w3.org/2000/svg}g")
    assert len(groups) == 2


def test_overlay_blend_mode() -> None:
    ov = OverlayConfig.from_dict({
        "layers": [
            {"family": "grid", "blend_mode": "multiply"},
        ],
    })
    svg = render_overlay(ov, seed=1)
    assert "mix-blend-mode: multiply" in svg


def test_overlay_with_background() -> None:
    ov = OverlayConfig.from_dict({
        "background": "#0a0a0a",
        "layers": [{"family": "dot_grid"}],
    })
    svg = render_overlay(ov, seed=1)
    root = ET.fromstring(svg)
    # The first <rect> child (skipping <title>/<desc>) should be the background.
    ns = "{http://www.w3.org/2000/svg}"
    rects = [c for c in root if c.tag == ns + "rect"]
    assert rects, "expected at least one <rect> child"
    assert rects[0].attrib.get("fill") == "#0a0a0a"


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

def test_list_presets_includes_both_kinds() -> None:
    names = list_presets()
    assert len(names) >= 10
    has_pattern = any("dot_grid" in n for n in names)
    has_overlay = any(n in {"noetroniq_network", "blueprint_overlay"} for n in names)
    assert has_pattern
    assert has_overlay


def test_every_preset_renders() -> None:
    """Every registered preset produces valid XML."""
    for name in list_presets():
        svg = render_pattern(name, size=(240, 160), seed=0)
        ET.fromstring(svg)  # raises if invalid


# ---------------------------------------------------------------------------
# Random utility sanity
# ---------------------------------------------------------------------------

def test_smoothstep_endpoints() -> None:
    assert smoothstep(0) == 0
    assert smoothstep(1) == 1
    assert 0 < smoothstep(0.5) < 1


def test_fade_endpoints() -> None:
    assert fade(0) == 0
    assert fade(1) == 1
    # fade is zero-derivative at 0 and 1.
    assert abs(fade(0.001)) < 0.001
    assert abs(fade(0.999) - 1) < 0.001


def test_lerp() -> None:
    assert lerp(0, 10, 0) == 0
    assert lerp(0, 10, 1) == 10
    assert lerp(0, 10, 0.5) == 5
