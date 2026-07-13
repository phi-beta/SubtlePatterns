# SubtlePatterns — Cookbook

Recipes for common overlay compositions. Every recipe can be saved as a YAML/JSON file and rendered via `subtle-patterns render-config` / `subtle-patterns overlay`.

## 1. Subtle blueprint grid (technical / drafting feel)

```yaml
# blueprint.yaml
family: grid
stroke: "#1d4d80"
stroke_opacity: 0.10
spacing: 32
thickness: 0.5
variant: double
```

```bash
subtle-patterns render-config blueprint.yaml --out blueprint.svg --size 1600x900
```

## 2. Topographic / organic feel (eco / cartographic)

```yaml
# topo_organic.yaml
width: 1600
height: 900
layers:
  - family: topographic
    stroke: "#5a3e1b"
    stroke_opacity: 0.18
    levels: 12
    amplitude: 60
    frequency: 0.0035
  - family: organic_blobs
    stroke: "#0d2f57"
    stroke_opacity: 0.10
    levels: 14
    spacing: 90
    amplitude: 18
    variant: cubic
  - family: particles
    fill: "#d4af37"
    fill_opacity: 0.20
    levels: 80
    radius: 0.8
    variant: size_curve+field
```

## 3. Starlight (dark backgrounds)

```yaml
# starlight.yaml
width: 1600
height: 900
background: "#000000"   # optional — only if you want a backdrop
layers:
  - family: noise_field
    fill: "#ffffff"
    fill_opacity: 0.10
    spacing: 6
    radius: 0.5
    frequency: 0.02
    variant: fbm
  - family: constellation
    fill: "#ffffff"
    fill_opacity: 0.30
    levels: 40
    radius: 1.0
    variant: clustered
```

## 4. Network / "blueprint" overlay (3 layers)

```yaml
# network.yaml
width: 1600
height: 900
layers:
  - family: grid
    stroke: "#1d4d80"
    stroke_opacity: 0.10
    spacing: 40
    variant: double
  - family: dot_grid
    fill: "#d4af37"
    fill_opacity: 0.25
    spacing: 80
    radius: 2
  - family: diagonal_lines
    stroke: "#8f211f"
    stroke_opacity: 0.10
    spacing: 120
    variant: steeper
```

## 5. Multiline coloured stack with blend modes

Each layer is colour-keyed; the `screen` blend mode lifts dark areas only, so the result is colour-saturated without losing detail.

```yaml
# blended.yaml
width: 1600
height: 900
layers:
  - family: contour_lines
    stroke: "#0d2f57"
    stroke_opacity: 0.20
    levels: 14
    blend_mode: screen
  - family: organic_blobs
    stroke: "#8f211f"
    stroke_opacity: 0.20
    levels: 12
    blend_mode: screen
  - family: noise_field
    fill: "#d4af37"
    fill_opacity: 0.20
    spacing: 12
    variant: turbulence
    blend_mode: overlay
```

## 6. Tweak a preset at the CLI

```bash
# Tighter grid with double-variant
subtle-patterns render blueprint --variant double --spacing 24 --stroke-opacity 0.18 \
    --out blueprint-tighter.svg

# Same pattern, more dots
subtle-patterns render dot_grid --density 1.5 --fill "#ffffff" --fill-opacity 0.15 \
    --out dot-grid-dense.svg
```

## 7. Inline from the shell (no file)

```bash
subtle-patterns inline 'family=contour_lines;stroke=#0d2f57;stroke_opacity=0.18;levels=14' \
    --out contours.svg
```

## 8. Generate a preview gallery

```bash
subtle-patterns gallery \
    --backdrop "linear-gradient(135deg,#001f3f,#0d2f57)" \
    --columns 3 --tile-size 480x270 \
    --out preview.html
```

The output is a self-contained HTML file with every preset on a tile of the configured backdrop. Open it in any browser.

## 9. Filter presets

```bash
# Only the geometric patterns
subtle-patterns gallery --include hex_mesh --include triangular_mesh --include dot_grid \
    --out geometric-only.html

# Skip the heavy ones
subtle-patterns gallery --exclude voronoi --exclude wave_field --out quick-preview.html
```

## 10. Embedding patterns in HTML

```html
<div class="hero" style="background: linear-gradient(135deg,#001f3f,#0d2f57); position: relative;">
  <img src="noetroniq_network.svg" alt="" aria-hidden="true"
       style="position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none;">
  <h1>Welcome</h1>
  <p>Subtle texture sits between the gradient and the text.</p>
</div>
```

Key rules:
* The pattern sits **on top of** the background.
* The text sits **on top of** the pattern.
* `pointer-events: none` lets clicks pass through the overlay.
* `aria-hidden="true"` keeps screen readers from announcing the pattern.
* The SVG `viewBox` matches its `width`/`height`, so the pattern scales to fit its container at any size without distortion.

## 11. Tuning opacity for a busy background

| Background type          | Recommended pattern opacity |
|--------------------------|-----------------------------|
| Plain colour             | 0.20 – 0.30                 |
| Subtle gradient          | 0.12 – 0.20                 |
| Busy gradient or image   | 0.06 – 0.12                 |
| Image with high contrast | 0.04 – 0.08                 |

If you can't see the pattern, raise `stroke_opacity`/`fill_opacity`. If the pattern fights the text, lower them.

## 12. Per-layer blend modes

Setting `blend_mode: "screen"` on a layer uses CSS `mix-blend-mode`, so the layer only *lifts* dark areas. Useful for adding "glow" to a dark hero without lightening the bright parts.

Common pairings:

* `screen` — additive on dark backgrounds.
* `multiply` — subtractive on light backgrounds (adds "ink" without darkening highlights).
* `overlay` — soft contrast booster; requires a non-grey pattern colour.
* `soft-light` — gentler than `overlay`; good for fine adjustments.
