# SubtlePatterns

> **Production-grade Python library for rendering subtle, mostly-transparent SVG overlay patterns for website backgrounds.**

`SubtlePatterns` generates reusable **SVG pattern overlays** — mostly-transparent images with low-opacity geometry, contours, particles, and gradients — designed to be layered on top of a website's background (a solid colour, image, or generated gradient) and *underneath* its text. The output never produces a flat image; it produces a *visual texture* that adds depth and complexity without competing for attention with foreground content.

```
┌──────────────────────────────────────────────┐
│ text (foreground)                            │  ← never touched by us
├──────────────────────────────────────────────┤
│ SubtlePatterns SVG (this library)            │  ← ~5–25% opacity, geometry
├──────────────────────────────────────────────┤
│ background colour / image / gradient         │  ← site-defined
└──────────────────────────────────────────────┘
```

## Highlights

- **17 pattern families, 25 built-in presets** — grid, dot grid, diagonal lines, cross-hatch, scanlines, circuit traces, hex mesh, triangular mesh, wave fields, contour lines, topographic isolines, Voronoi, organic blobs, particle constellations, fractals, noise field.
- **12 spatial warps** — tilt, scale, shear, cylindrical, spherical, ripple, twist. Every layer can be bent onto a non-flat surface: tilted floor, wrapped around a cylinder, projected onto a dome, rippled like water, or twisted like a screw. Affine warps emit a single `<g transform>`; non-affine warps use SVG `<filter><feDisplacementMap/></filter>`, the standard idiom for non-affine spatial warps.
- **Deterministic** — every pattern is fully reproducible from a config and a seed. Re-rendering the same config produces byte-identical SVG.
- **Rich configuration** — patterns accept colour, opacity, density, scale, jitter, stroke, fill, curvature, depth, blend mode, and layer-specific options. Configs are loadable from **Python dicts, JSON, or YAML**.
- **Composable** — multiple patterns can be layered into a single SVG with per-layer blend modes, opacity, and z-order.
- **Production-grade output** — minimal markup, no editor metadata, no unused namespaces, `viewBox`-scaled, accessible (`role="img"`, `aria-hidden="true"`), and ready to inline or serve as a static file.
- **CLI + Python API + HTML preview gallery** — generate single files, batch preset galleries, or a self-contained HTML preview page that shows every preset over a configurable backdrop.
- **Zero hard dependencies** for the core library. `pyyaml` and `lxml` are optional extras.

## Installation

```bash
pip install subtle-patterns            # core only (stdlib)
pip install subtle-patterns[yaml]      # + YAML config support
pip install subtle-patterns[lxml]      # + faster pretty-printing
pip install subtle-patterns[dev]       # everything you need to hack on it
```

## Quick start

### Python API

```python
from subtle_patterns import render_pattern, render_overlay, PatternConfig, OverlayConfig

# 1. A single pattern from a built-in preset
svg = render_pattern("hex_mesh", size=(800, 600), seed=42)
open("hex.svg", "w").write(svg)

# 2. A custom configuration
cfg = PatternConfig.from_dict({
    "family": "contour_lines",
    "stroke": "#0d2f57",
    "stroke_opacity": 0.18,
    "levels": 14,
    "amplitude": 60,
    "frequency": 0.004,
    "jitter": 0.35,
})
svg = render_pattern(cfg, size=(1600, 900), seed=7)

# 3. Multiple layers composited into one overlay
overlay = OverlayConfig(layers=[
    {"family": "grid",            "stroke": "#1d4d80", "stroke_opacity": 0.10, "spacing": 40},
    {"family": "dot_grid",        "fill":   "#d4af37", "fill_opacity":   0.20, "spacing": 80, "radius": 2},
    {"family": "diagonal_lines",  "stroke": "#8f211f", "stroke_opacity": 0.10, "spacing": 120, "thickness": 1},
])
svg = render_overlay(overlay, size=(1600, 900), seed=11)
```

### CLI

```bash
# Render a built-in preset
subtle-patterns render hex_mesh --size 1600x900 --seed 42 --out hex.svg

# Render a YAML/JSON config
subtle-patterns render-config examples/contour_lines.yaml --out contours.svg

# Render a multi-layer overlay
subtle-patterns overlay examples/noetroniq_network.yaml --out overlay.svg

# Generate a preview gallery of every preset over a backdrop
subtle-patterns gallery --backdrop "linear-gradient(135deg,#001f3f,#0d2f57)" \
    --out preview.html --columns 3

# List every preset
subtle-patterns list-presets
```

## Why "subtle"?

A SubtlePatterns SVG is designed to be **barely-there** — adding visual richness without becoming the subject. The default parameters reflect this:

| Property                 | Default       | Why                                          |
|--------------------------|---------------|----------------------------------------------|
| Element opacity          | 5–25 %        | Sits under text without competing with it    |
| Element count            | Dense         | Reads as *texture*, not *objects*            |
| Stroke widths            | 0.5 – 1.5 px  | Soft, not graphic                            |
| Colours                  | High-contrast | Patterns work over any background, *including* the same colour family |
| No `background` fills    | Always        | Patterns are an *overlay*, never a backdrop  |
| No drop shadows / glows  | Always        | Subtlety over spectacle                      |

## Project structure

```
SubtlePatterns/
├── src/subtle_patterns/
│   ├── core/             # Config schema, RNG, geometry helpers
│   ├── svg/              # SVG element builder + pretty-printer
│   ├── patterns/         # 12 pattern families
│   ├── presets/          # Built-in preset configurations
│   ├── cli/              # Command-line interface
│   └── __init__.py       # Public API
├── tests/                # pytest suite
├── examples/             # Example configs (YAML / JSON)
├── docs/                 # Reference + cookbook
├── scripts/              # Maintenance scripts (gallery regen, etc.)
├── pyproject.toml
└── README.md
```

## Documentation

- **[docs/REFERENCE.md](docs/REFERENCE.md)** — full pattern reference, every parameter, defaults, examples.
- **[docs/COOKBOOK.md](docs/COOKBOOK.md)** — recipes for common overlay compositions.
- **[docs/DESIGN_NOTES.md](docs/DESIGN_NOTES.md)** — design rationale, opacity philosophy, layering rules.
- **[docs/PERFORMANCE.md](docs/PERFORMANCE.md)** — output-size budget, complexity per family, browser paint cost.
- **[DOCUMENTATION_STANDARDS.md](DOCUMENTATION_STANDARDS.md)** — doc conventions this project follows.

## License

MIT — see [LICENSE](LICENSE).
