# SubtlePatterns — Reference

Complete per-pattern reference. For the high-level overview, see [README.md](../README.md). For recipes, see [COOKBOOK.md](COOKBOOK.md).

## Pattern families

There are **17 pattern families**. Each accepts a `family` string and an optional `variant` string. Unknown fields on a config are silently ignored, so you can copy a config from one family to another without errors.

The variant lists below are the ones exercised by the test suite (`tests/test_patterns.py::test_variant_renders`); other strings are accepted but not documented.

In addition, every pattern supports a layer-level **spatial warp** that bends the pattern onto a non-flat surface — see [Spatial warps](#spatial-warps) below.

### Conventions

* All sizes are in **user units** (no `px` suffix in the SVG output; the SVG is scalable).
* `stroke_opacity` and `fill_opacity` are both multiplied by `opacity` at render time.
* `variant` strings are case-sensitive.

### `grid` — orthogonal line lattice

Variants: `""` (default), `isometric`, `double`.

| Field        | Default | Notes |
|--------------|---------|-------|
| `spacing`    | 40      | Distance between adjacent lines |
| `thickness`  | 1.0     | Stroke width |
| `jitter`     | 0.0     | Per-line positional jitter in [0, 1] (scaled by spacing) |

`isometric` emits 30°/60° lines; `double` adds a fainter half-spacing sub-grid; `offset` alternates row positions by half a cell.

### `dot_grid` — point lattice

Variants: `""`, `scaled`, `rings`.

| Field         | Default | Notes |
|---------------|---------|-------|
| `spacing`     | 40      | Dot pitch |
| `radius`      | 1.5     | Dot radius |
| `jitter`      | 0.0     | Per-dot positional jitter |
| `fill`        | `#0d2f57` (preset) | Dot fill colour |

`scaled` perturbs each dot's radius 0.4×–1.6×; `rings` renders dots as outlined circles.

### `hex_mesh` — hexagonal mesh

Variants: `""` (default outlines), `triangulated` (outlines + centre-to-corner spokes), `filled` (random 50% filled).

| Field        | Default | Notes |
|--------------|---------|-------|
| `spacing`    | 40      | Cell pitch (hexes tile at radius = 0.55 × spacing) |
| `thickness`  | 1.0     | Outline stroke width |

### `triangular_mesh`

Variants: `""`, `shaded` (every other triangle faintly filled).

### `diagonal_lines`

Variants: `""` (45°), `crossed` (adds a perpendicular set).

### `cross_hatch`

Variants: `""` (30°/120°), `triple` (0°/60°/120°), `weave` (4 sets + faint 0°/90° overlay).

### `scanlines`

Variants: `""` (uniform), `halftone` (per-line thickness varies sinusoidally across the width).

### `circuit_traces`

Orthogonal PCB-style traces. Each trace starts on a random edge, then does a random walk with 70% chance to keep its current direction and 30% to turn left/right.

| Field        | Default | Notes |
|--------------|---------|-------|
| `spacing`    | 14      | Step length |
| `levels`     | 12      | Number of traces |
| `amplitude`  | 24      | Mean trace length (in step units) |

### `wave_field`

Variants: `""` (Perlin), `fbm` (multi-octave FBM).

A row of smoothly varying lines stacked across the canvas.

| Field        | Default | Notes |
|--------------|---------|-------|
| `spacing`    | 12      | Distance between rows |
| `amplitude`  | 18      | Wave amplitude (user units) |
| `frequency`  | 0.012   | Spatial frequency (cycles per user unit) |

### `contour_lines`

Iso-lines of a Perlin field, drawn by **marching squares**.

Variants: `""`, `emphasis` (every 5th line is bolder).

| Field        | Default | Notes |
|--------------|---------|-------|
| `levels`     | 12      | Number of contour bands |
| `amplitude`  | 30      | Noise amplitude |
| `frequency`  | 0.01    | Noise spatial frequency |

### `topographic`

FBM-based iso-lines — gives the classic "squiggly mountain" look.

### `voronoi`

Variants: `""`, `relaxed` (Lloyd-relaxed seeds → more uniform cell area).

| Field        | Default | Notes |
|--------------|---------|-------|
| `levels`     | 12      | Approximate number of seed points |
| `spacing`    | 14      | Coarse sampling grid for the boundary walk |

### `organic_blobs`

Variants: `""`, `cubic` (Catmull-Rom smoothing).

| Field        | Default | Notes |
|--------------|---------|-------|
| `levels`     | 12      | Number of blobs |
| `spacing`    | 80      | Reference blob radius |
| `amplitude`  | 25      | Radial perturbation |
| `frequency`  | 0.01    | Noise frequency |

### `constellation`

Variants: `""` (uniform random), `clustered` (Gaussian cluster around `levels/3` centres), `spiral` (logarithmic spiral).

For each point, connects the *nearest* other point with a thin line.

| Field        | Default | Notes |
|--------------|---------|-------|
| `levels`     | 60      | Point count ≈ 6 × `levels` |
| `spacing`    | 80      | Maximum connection length |
| `radius`     | 1.5     | Dot radius |

### `particles`

Variants: `""` (uniform), `size_curve+field` (radius power-law with Perlin-driven opacity). Internally the `size_curve` and `field` modifiers compose; `""` uses neither.

| Field        | Default | Notes |
|--------------|---------|-------|
| `levels`     | 80      | Particle count ≈ 6 × `levels` |
| `radius`     | 1.5     | Base radius |

### `fractal_silhouette`

Variants: `""` (Sierpinski-carpet-like), `hilbert` (Hilbert curve), `tree` (recursive branching tree).

| Field        | Default | Notes |
|--------------|---------|-------|
| `levels`     | 8       | Recursion depth (or Hilbert order = `levels/2`) |
| `amplitude`  | 60      | Carve probability seed (higher = more open) |

### `noise_field`

A field of dots whose **density follows a noise function**. The output is a single packed `<path>` containing every dot.

Variants: `""` (Perlin), `fbm`, `turbulence` (absolute-value Perlin for ridges).

| Field        | Default | Notes |
|--------------|---------|-------|
| `spacing`    | 8       | Cell size of the underlying grid |
| `radius`     | 0.7     | Dot radius |
| `density`    | 1.0     | Density multiplier |
| `frequency`  | 0.012   | Noise frequency |

## Common parameters

| Field           | Type    | Default    | Range           | Notes |
|-----------------|---------|------------|-----------------|-------|
| `family`        | str     | (required) | one of 17       | Pattern family |
| `variant`       | str     | `""`       | family-specific | Sub-variant |
| `stroke`        | Color   | `"none"`   | CSS colour      | Stroke colour |
| `fill`          | Color   | `"none"`   | CSS colour      | Fill colour |
| `stroke_opacity`| float   | 0.15       | 0..1            | Stroke alpha |
| `fill_opacity`  | float   | 0.12       | 0..1            | Fill alpha |
| `opacity`       | float   | 1.0        | 0..1            | Layer-level opacity (multiplies both) |
| `spacing`       | float   | 40.0       | > 0             | Primary spacing parameter |
| `density`       | float   | 1.0        | 0.05..10.0      | Element density multiplier |
| `thickness`     | float   | 1.0        | 0..32           | Stroke width |
| `radius`        | float   | 1.5        | 0..1024         | Primary radius |
| `levels`        | int     | 12         | 1..256          | Family-specific level count |
| `amplitude`     | float   | 30.0       | any             | Wave/perturbation amplitude |
| `frequency`     | float   | 0.01       | > 0             | Noise/wave frequency |
| `jitter`        | float   | 0.0        | 0..1            | Random positional jitter (scaled by spacing) |
| `seed`          | int     | 0          | any             | Per-pattern seed override |
| `blend_mode`    | BlendMode| NORMAL    | 15 modes        | `mix-blend-mode` for the layer |
| `curve_segments`| int     | 32         | 2..512          | Cubic Bezier sampling resolution |
| `warp`          | WarpKind| `"none"`   | 12 kinds        | Spatial warp applied to the layer (see below) |
| `warp_strength` | float   | 0.3        | 0..1            | Warp amplitude (0 = identity) |

## Overlay parameters

| Field        | Type    | Default    | Notes |
|--------------|---------|------------|-------|
| `layers`     | list    | `[]`       | Ordered list of `PatternConfig` or dicts |
| `width`      | float   | 1600.0     | Canvas width in user units |
| `height`     | float   | 900.0      | Canvas height in user units |
| `aspect_ratio` | float | 16/9       | Used if a dimension is missing |
| `background` | Color   | `"none"`   | Optional canvas fill (set only if you want a backdrop) |
| `title`      | str     | `""`       | Optional `<title>` for accessibility |

## Blend modes

`BlendMode` is one of (subset of CSS Compositing Level 1):

`normal`, `multiply`, `screen`, `overlay`, `darken`, `lighten`, `color-dodge`, `color-burn`, `hard-light`, `soft-light`, `difference`, `exclusion`, `hue`, `saturation`, `color`, `luminosity`.

Blend modes are applied per layer via `style="mix-blend-mode: …"` on the layer's `<g>`.

## Spatial warps

A *warp* bends a pattern layer onto a non-flat surface so the same flat-XY pattern can read as if it were projected onto a tilted plane, wrapped around a cylinder, rippled like water, twisted like a screw, or projected onto a sphere.

* **Affine** warps (`tilt_x`, `tilt_y`, `tilt_xy`, `scale_h`, `scale_v`, `shear_x`, `shear_y`) emit a single `<g transform="matrix(...)">`. They are zero-overhead and deterministic.
* **Non-affine** warps (`cylinder_h`, `cylinder_v`, `sphere`, `ripple`, `twist`) emit a single `<defs>` block per warp with a `<filter>` containing `<feTurbulence>` and `<feDisplacementMap>`. The layer's `<g>` references it via `filter="url(#sp-warp-...)"`. This is the standard SVG idiom for non-affine spatial warps and is supported in every modern browser.

`warp_strength` is in `[0, 1]`. `0` is the identity (no transform emitted). `1` is a strong, easily visible warp.

| Warp           | Kind          | Looks like                                       |
|----------------|---------------|--------------------------------------------------|
| `none`         | identity      | No change                                        |
| `tilt_x`       | affine        | Pattern tipped around a horizontal axis          |
| `tilt_y`       | affine        | Pattern tipped around a vertical axis            |
| `tilt_xy`      | affine        | 3-D "perspective floor" combined tilt            |
| `scale_h`      | affine        | Horizontal squash (1 = half-width)               |
| `scale_v`      | affine        | Vertical squash (1 = half-height)                |
| `shear_x`      | affine        | Horizontal shear (parallelogram)                 |
| `shear_y`      | affine        | Vertical shear (parallelogram)                   |
| `cylinder_h`   | non-affine    | Wrapped around a horizontal cylinder             |
| `cylinder_v`   | non-affine    | Wrapped around a vertical cylinder               |
| `sphere`       | non-affine    | Projected onto a sphere (fish-eye / dome)        |
| `ripple`       | non-affine    | Sinusoidal wave displacement                     |
| `twist`        | non-affine    | Rotation around centre, increasing with distance |

Example — a 2-layer overlay where the grid is bent onto a perspective floor and the dot grid is not:

```yaml
layers:
  - family: grid
    stroke: "#1d4d80"
    stroke_opacity: 0.18
    spacing: 60
    warp: tilt_xy
    warp_strength: 0.6
  - family: dot_grid
    fill: "#d4af37"
    fill_opacity: 0.30
    spacing: 120
    radius: 1.6
    # no warp: stays on the unwarped plane
```

Five presets exercise the warps: `tilted_grid`, `cylindrical_blueprint`, `ripple_field`, `twisted_ribbon`, `dome_horizon`.

## Built-in presets

Run `subtle-patterns list-presets` for the full list. Twenty are shipped:

* **Patterns** (14): `blueprint`, `circuit_traces`, `constellation`, `contour_lines`, `dot_grid`, `fractal_silhouette`, `hex_mesh`, `noise_field`, `organic_blobs`, `scanlines`, `topographic`, `triangular_mesh`, `voronoi`, `wave_field`
* **Overlays** (6): `blueprint_overlay`, `hex_constellation`, `minimal_lines`, `noetroniq_network`, `starlight_dust`, `topographic_organic`
* **Warped overlays** (5): `tilted_grid` (perspective floor), `cylindrical_blueprint` (around a horizontal cylinder), `ripple_field` (sinusoidal wave), `twisted_ribbon` (screw-like twist), `dome_horizon` (projected onto a sphere)
