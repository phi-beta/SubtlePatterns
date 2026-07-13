"""Test pattern-family implementations."""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from subtle_patterns import (  # noqa: E402
    OverlayConfig,
    PatternConfig,
    render_overlay,
    render_pattern,
)
from subtle_patterns.core.config import PATTERN_FAMILIES  # noqa: E402
from subtle_patterns.patterns import PATTERN_REGISTRY  # noqa: E402


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------

def test_every_pattern_family_is_registered() -> None:
    """Every name in PATTERN_FAMILIES has an implementation."""
    for fam in PATTERN_FAMILIES:
        assert fam in PATTERN_REGISTRY, f"{fam!r} missing from PATTERN_REGISTRY"


def test_registry_only_contains_known_families() -> None:
    """No orphan implementations registered."""
    for fam in PATTERN_REGISTRY:
        assert fam in PATTERN_FAMILIES, f"{fam!r} registered but not in PATTERN_FAMILIES"


# ---------------------------------------------------------------------------
# Per-family smoke tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("family,variant", [
    ("grid", ""),
    ("grid", "isometric"),
    ("grid", "double"),
    ("dot_grid", ""),
    ("dot_grid", "scaled"),
    ("dot_grid", "rings"),
    ("hex_mesh", ""),
    ("hex_mesh", "triangulated"),
    ("hex_mesh", "filled"),
    ("diagonal_lines", ""),
    ("diagonal_lines", "crossed"),
    ("cross_hatch", ""),
    ("cross_hatch", "triple"),
    ("cross_hatch", "weave"),
    ("wave_field", ""),
    ("wave_field", "fbm"),
    ("contour_lines", ""),
    ("contour_lines", "emphasis"),
    ("topographic", ""),
    ("voronoi", ""),
    ("voronoi", "relaxed"),
    ("organic_blobs", ""),
    ("organic_blobs", "cubic"),
    ("constellation", ""),
    ("constellation", "clustered"),
    ("constellation", "spiral"),
    ("particles", ""),
    ("particles", "size_curve+field"),
    ("fractal_silhouette", ""),
    ("fractal_silhouette", "hilbert"),
    ("fractal_silhouette", "tree"),
    ("noise_field", ""),
    ("noise_field", "fbm"),
    ("noise_field", "turbulence"),
    ("scanlines", ""),
    ("scanlines", "halftone"),
    ("circuit_traces", ""),
    ("triangular_mesh", ""),
    ("triangular_mesh", "shaded"),
])
def test_variant_renders(family: str, variant: str) -> None:
    cfg = PatternConfig(family=family, variant=variant)
    svg = render_pattern(cfg, size=(240, 160), seed=1)
    ET.fromstring(svg)  # must be valid XML


# ---------------------------------------------------------------------------
# Specific visual / structural assertions
# ---------------------------------------------------------------------------

def test_grid_emits_one_path() -> None:
    """The grid pattern packs everything into one or two <path>s."""
    svg = render_pattern(PatternConfig(family="grid"), size=(200, 100), seed=0)
    root = ET.fromstring(svg)
    paths = root.findall(".//{http://www.w3.org/2000/svg}path")
    # Default variant emits 2 paths (vertical + horizontal lines).
    assert 1 <= len(paths) <= 2


def test_hex_mesh_count_roughly_matches_grid_extent() -> None:
    """At a given spacing, hex_mesh should produce ≈ ceil(w*h / cell_area) cells."""
    import math
    spacing = 36
    radius = spacing * 0.55
    pointy = True
    dx = radius * math.sqrt(3.0)
    dy = 1.5 * radius
    rows = int(100 / dy) + 2
    cols = int(200 / dx) + 2
    expected = rows * cols
    svg = render_pattern(PatternConfig(family="hex_mesh", spacing=spacing), size=(200, 100), seed=0)
    # Count `M` commands in the path data — each one is a hex start.
    # The default hex_mesh variant emits one big path with all hexes packed.
    m_count = svg.count("M")
    # The triangulation variant adds a 2nd set of 6 lines per hex.
    assert expected // 2 <= m_count <= expected * 2 + 50  # hex lines + triangulation lines


def test_deterministic_overlay_across_seeds() -> None:
    ov = OverlayConfig(layers=[
        PatternConfig(family="grid"),
        PatternConfig(family="dot_grid"),
    ])
    a = render_overlay(ov, seed=42)
    b = render_overlay(ov, seed=42)
    assert a == b


def test_different_seeds_produce_different_overlays() -> None:
    ov = OverlayConfig(layers=[
        PatternConfig(family="constellation"),
        PatternConfig(family="dot_grid"),
    ])
    a = render_overlay(ov, seed=1)
    b = render_overlay(ov, seed=2)
    assert a != b
