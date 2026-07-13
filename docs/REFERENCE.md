# SubtlePatterns — Reference

Complete per-pattern reference. For the high-level overview, see [README.md](../README.md). For recipes, see [COOKBOOK.md](COOKBOOK.md).

## Pattern families

There are **17 pattern families**. Each accepts a `family` string and an optional `variant` string. Unknown fields on a config are silently ignored, so you can copy a config from one family to another without errors.

The variant lists below are the ones exercised by the test suite (`tests/test_patterns.py::test_variant_renders`); other strings are accepted but not documented.

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

## Built-in presets

Run `subtle-patterns list-presets` for the full list. Twenty are shipped:

* **Patterns** (14): `blueprint`, `circuit_traces`, `constellation`, `contour_lines`, `dot_grid`, `fractal_silhouette`, `hex_mesh`, `noise_field`, `organic_blobs`, `scanlines`, `topographic`, `triangular_mesh`, `voronoi`, `wave_field`
* **Overlays** (6): `blueprint_overlay`, `hex_constellation`, `minimal_lines`, `noetroniq_network`, `starlight_dust`, `topographic_organic`
