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
        # 15. Dome horizon (sphere + topographic)
        (
            "15-dome-horizon.svg",
            lambda: render_overlay("dome_horizon", size=(1600, 900), seed=42),
            "Topographic noise + particles projected onto a sphere.",
        ),
        # 16-24. Per-warp showcases — one tile per warp kind, with
        # enough strength that the effect is unmistakable. Where a
        # preset name doesn't fit, we build the layer config inline.
        (
            "16-tilt-x.svg",
            lambda: render_pattern(
                {"family": "grid", "stroke": "#1d4d80", "stroke_opacity": 0.25,
                 "spacing": 40, "thickness": 0.8, "warp": "tilt_x", "warp_strength": 0.6},
                size=(1600, 900), seed=42,
            ),
            "Pure tilt_x: grid tipped around a horizontal axis (one-axis perspective).",
        ),
        (
            "17-tilt-y.svg",
            lambda: render_pattern(
                {"family": "grid", "stroke": "#1d4d80", "stroke_opacity": 0.25,
                 "spacing": 40, "thickness": 0.8, "warp": "tilt_y", "warp_strength": 0.6},
                size=(1600, 900), seed=42,
            ),
            "Pure tilt_y: grid tipped around a vertical axis (one-axis perspective).",
        ),
        (
            "18-cylindrical-vertical.svg",
            lambda: render_pattern(
                {"family": "grid", "stroke": "#1d4d80", "stroke_opacity": 0.25,
                 "spacing": 40, "thickness": 0.8,
                 "warp": "cylinder_v", "warp_strength": 0.6},
                size=(1600, 900), seed=42,
            ),
            "Grid wrapped around a vertical cylinder (cylinder_v warp).",
        ),
        (
            "19-scale-h.svg",
            lambda: render_pattern(
                {"family": "grid", "stroke": "#1d4d80", "stroke_opacity": 0.25,
                 "spacing": 40, "thickness": 0.8, "warp": "scale_h", "warp_strength": 0.7},
                size=(1600, 900), seed=42,
            ),
            "Horizontal squash (scale_h warp) — affine, like a wide-angle lens.",
        ),
        (
            "20-shear-x.svg",
            lambda: render_pattern(
                {"family": "grid", "stroke": "#1d4d80", "stroke_opacity": 0.25,
                 "spacing": 40, "thickness": 0.8, "warp": "shear_x", "warp_strength": 0.7},
                size=(1600, 900), seed=42,
            ),
            "Pure horizontal shear (shear_x warp) — a parallelogram.",
        ),
        (
            "21-tilted-contour.svg",
            lambda: render_pattern(
                {"family": "contour_lines", "stroke": "#0d2f57", "stroke_opacity": 0.20,
                 "levels": 14, "amplitude": 60, "frequency": 0.004, "jitter": 0.35,
                 "warp": "tilt_xy", "warp_strength": 0.5},
                size=(1600, 900), seed=42,
            ),
            "Contour lines bent onto a 3-D perspective floor (tilt_xy on a non-grid pattern).",
        ),
        (
            "22-gentle-twist.svg",
            lambda: render_pattern(
                {"family": "hex_mesh", "stroke": "#1d4d80", "stroke_opacity": 0.18,
                 "spacing": 40, "thickness": 0.6, "warp": "twist", "warp_strength": 0.25},
                size=(1600, 900), seed=42,
            ),
            "Gentle twist (warp_strength=0.25) — subtle, not yet a full screw.",
        ),
        (
            "23-strong-sphere.svg",
            lambda: render_pattern(
                {"family": "noise_field", "fill": "#d4af37", "fill_opacity": 0.15,
                 "spacing": 18, "radius": 0.5, "frequency": 0.02, "variant": "fbm",
                 "warp": "sphere", "warp_strength": 0.85},
                size=(1600, 900), seed=42,
            ),
            "Strong sphere (warp_strength=0.85) — a clear planetary bulge.",
        ),
        (
            "24-stacked-warps.svg",
            lambda: render_overlay(
                {"layers": [
                    # Bottom: faint noise dust on a sphere — the "horizon".
                    {"family": "noise_field", "fill": "#d4af37", "fill_opacity": 0.10,
                     "spacing": 22, "radius": 0.5, "frequency": 0.02, "variant": "fbm",
                     "warp": "sphere", "warp_strength": 0.5},
                    # Middle: a grid tilted on a different plane.
                    {"family": "grid", "stroke": "#1d4d80", "stroke_opacity": 0.18,
                     "spacing": 60, "thickness": 0.6,
                     "warp": "tilt_xy", "warp_strength": 0.45},
                    # Top: flat (no warp) — sits on the viewer's plane.
                    {"family": "dot_grid", "fill": "#ffffff", "fill_opacity": 0.20,
                     "spacing": 80, "radius": 1.2},
                ], "width": 1600, "height": 900},
                seed=42,
            ),
            "Three layers, three different warps: sphere, tilt_xy, and none — different surfaces stacked in one overlay.",
        ),
    ]


def main() -> int:
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    print(f"Writing samples to: {SAMPLES_DIR}")
    print()

    samples = make_samples()
    rendered: list[tuple[str, str, str]] = []  # (label, svg, info) for preview.html
    total = 0
    for filename, fn, desc in samples:
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
        # The label is the filename without the leading "NN-" and the
        # trailing ".svg" (e.g. "01-noetroniq-network.svg" -> "noetroniq-network").
        # We keep the dash form because that's the natural identifier.
        label = filename.split("-", 1)[1].rsplit(".svg", 1)[0]
        rendered.append((label, svg, desc))

    # Gallery — built from the *samples* we just rendered, so every
    # *.svg file in examples/samples/ has a corresponding tile in the
    # gallery, and nothing else. The tile SVGs are the inlined full-size
    # SVGs, resized to the tile dimensions by the gallery.
    gallery_path = os.path.join(SAMPLES_DIR, "preview.html")
    html = gallery_html(
        samples=rendered,
        backdrop="linear-gradient(135deg,#001f3f,#0d2f57)",
        tile_size=(480, 270),
        seed=42,
        columns=2,
        title=f"SubtlePatterns — {len(rendered)} curated samples",
    )
    with open(gallery_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print()
    print(f"  {'preview.html':35}  {len(html):>7,} bytes  full sample gallery")
    print()
    print(f"Total SVG payload: {total:,} bytes  ({(total / 1024):.1f} KB) across {len(samples)} samples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
