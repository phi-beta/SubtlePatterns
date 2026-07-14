"""Generate sample SVGs + a preview.html gallery.

Run as a script (not part of the package):

    PYTHONPATH=src python scripts/generate_samples.py
"""

from __future__ import annotations

import os
import sys
import time
import xml.etree.ElementTree as ET

# Make the package importable.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from subtle_patterns import render_overlay, render_pattern, list_presets  # noqa: E402
from subtle_patterns.preview import gallery_html  # noqa: E402

# ---------------------------------------------------------------------------
# Sample definitions
# ---------------------------------------------------------------------------

# Each sample is (filename, render_function_callable, description).
# The render functions all return an SVG string.

SAMPLES_DIR = os.path.join(ROOT, "examples", "samples")


def make_samples():
    return [
        # 1. The NOETRONIQ network overlay (3-layer, blueprint + dots + diagonals)
        (
            "01-noetroniq-network.svg",
            lambda: render_overlay("noetroniq_network", size=(1600, 900), seed=42),
            "3-layer NOETRONIQ network overlay (the reference pattern, upscaled to 1600x900).",
        ),
        # 2. Blueprint overlay (technical / drafting)
        (
            "02-blueprint-overlay.svg",
            lambda: render_overlay("blueprint_overlay", size=(1600, 900), seed=42),
            "Multi-layer blueprint (grid + contour + circuit traces), deep blue.",
        ),
        # 3. Topographic organic (earth tones)
        (
            "03-topographic-organic.svg",
            lambda: render_overlay("topographic_organic", size=(1600, 900), seed=42),
            "FBM topographic lines + organic blobs + dust.",
        ),
        # 4. Starlight dust (deep navy)
        (
            "04-starlight-dust.svg",
            lambda: render_overlay("starlight_dust", size=(1600, 900), seed=42),
            "White-on-navy: noise dust + clustered constellation.",
        ),
        # 5. Hex constellation (architectural)
        (
            "05-hex-constellation.svg",
            lambda: render_overlay("hex_constellation", size=(1600, 900), seed=42),
            "Triangulated hex mesh + gold constellation points.",
        ),
        # 6. Minimal lines (single family, very subtle)
        (
            "06-minimal-lines.svg",
            lambda: render_overlay("minimal_lines", size=(1600, 900), seed=42),
            "Diagonals + triple cross-hatch at very low opacity.",
        ),
        # 7. Custom contour lines (single-family, in deep blue)
        (
            "07-contour-lines.svg",
            lambda: render_pattern("contour_lines", size=(1600, 900), seed=42),
            "Standalone contour_lines preset — every 5th line is bold.",
        ),
        # 8. Custom hex mesh (single-family, in deep blue)
        (
            "08-hex-mesh.svg",
            lambda: render_pattern("hex_mesh", size=(1600, 900), seed=42),
            "Standalone hex_mesh preset — pointy-top hexagons, subtle blue.",
        ),
        # 9. Wave field (Perlin FBM)
        (
            "09-wave-field.svg",
            lambda: render_pattern("wave_field", size=(1600, 900), seed=42),
            "FBM wave field — many horizontal flowing lines.",
        ),
        # 10. Voronoi (relaxed, structural)
        (
            "10-voronoi.svg",
            lambda: render_pattern("voronoi", size=(1600, 900), seed=42),
            "Voronoi diagram with Lloyd-relaxed seeds for uniform cell sizes.",
        ),
        # 11-15. Warped overlays — show off the spatial-warp system
        # (tilt, cylinder, ripple, twist, sphere). Each uses the same
        # families as the unwarped presets but bends them onto a
        # non-flat surface via layer-level <g transform="..."> or
        # <filter> wrapping.
        (
            "11-tilted-grid.svg",
            lambda: render_overlay("tilted_grid", size=(1600, 900), seed=42),
            "Perspective floor: grid + dot_grid, both wrapped with tilt_xy.",
        ),
        (
            "12-cylindrical-blueprint.svg",
            lambda: render_overlay("cylindrical_blueprint", size=(1600, 900), seed=42),
            "Grid + circuit traces wrapped around a horizontal cylinder.",
        ),
        (
            "13-ripple-field.svg",
            lambda: render_overlay("ripple_field", size=(1600, 900), seed=42),
            "Wave field + flat dot grid; the field is sinusoidal-rippled.",
        ),
        (
            "14-twisted-ribbon.svg",
            lambda: render_overlay("twisted_ribbon", size=(1600, 900), seed=42),
            "Hex mesh + constellation twisted around the layer's vertical centre.",
        ),
        (
            "15-dome-horizon.svg",
            lambda: render_overlay("dome_horizon", size=(1600, 900), seed=42),
            "Topographic noise + particles projected onto a sphere.",
        ),
    ]


def main() -> int:
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    print(f"Writing samples to: {SAMPLES_DIR}")
    print()

    total = 0
    for filename, fn, desc in make_samples():
        t0 = time.time()
        svg = fn()
        dt = time.time() - t0
        # Validate
        ET.fromstring(svg)
        path = os.path.join(SAMPLES_DIR, filename)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        size = len(svg)
        total += size
        print(f"  {filename:35}  {size:>7,} bytes  {dt*1000:6.1f}ms  {desc}")

    # Gallery
    gallery_path = os.path.join(SAMPLES_DIR, "preview.html")
    html = gallery_html(
        presets=list_presets(),
        backdrop="linear-gradient(135deg,#001f3f,#0d2f57)",
        tile_size=(480, 270),
        seed=42,
        columns=2,
        title="SubtlePatterns — sample gallery (built-in presets)",
    )
    with open(gallery_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print()
    print(f"  {'preview.html':35}  {len(html):>7,} bytes  full preset gallery")
    print()
    print(f"Total SVG payload: {total:,} bytes  ({(total / 1024):.1f} KB) across {len(make_samples())} samples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
