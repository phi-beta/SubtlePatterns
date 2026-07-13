# SubtlePatterns — Design notes

The philosophy behind the library, the constraints we placed on output, and the trade-offs we made.

## What is "subtle"?

A subtle SVG overlay does three things:

1. **Adds visual information** without becoming the subject.
2. **Stays out of the way of text** layered above it.
3. **Survives recolouring and repositioning** without re-authoring.

These goals set the constraints below.

## Constraints

### No full-canvas background fills

A SubtlePatterns SVG is an **overlay**, never a backdrop. The library will never paint a `<rect>` covering the full canvas with a non-`none` fill unless you explicitly set `OverlayConfig.background`. The engine asserts this in tests.

Why: a pattern that *is* the background is no longer a pattern; it's a wallpaper. We want consumers to keep authoring the background (the gradient, the image, the brand colour) and treat the pattern as a *modifier* on top.

### Decorative accessibility metadata

Every emitted SVG carries `role="img"` and `aria-hidden="true"`. The pattern is, by design, a non-content visual. Screen readers will skip it. If you need to *describe* a pattern (e.g. for a public figure), use a separate `<img alt="…">` wrapper, not the pattern SVG itself.

### No `xlink:href`, no `xmlns:xlink`

Modern browsers (and the SVG 2 spec) use plain `href`. SubtlePatterns sticks to plain `href` so the output is the smallest valid SVG that works in the most places.

### No editor metadata, no empty groups

We strip whitespace, we don't emit Inkscape/Adobe namespaces, and we don't emit empty `<g>` elements. This keeps the bytes low and the file diff-friendly.

### No `viewBox` smoothing hacks

The SVG's `width`/`height` match the `viewBox`, and we don't set `preserveAspectRatio="none"`. The pattern always scales uniformly within its container.

## Defaults

The library's defaults are tuned for the *subtle* end of the spectrum. If a parameter has a default of 0.15, raising it to 0.50 is *opt-in* — you should see the difference as soon as you tweak it. This is the opposite of "everything is at 100 % and you dim it" libraries; we trust the user to know when they want a *loud* pattern.

## Why are there so many pattern families?

Each family has a distinct *visual* identity:

| Family          | Visual identity                                |
|-----------------|------------------------------------------------|
| `grid`          | Engineering, drafting, structured              |
| `dot_grid`      | Topology, measurement, halftone                |
| `hex_mesh`      | Architectural, organic, scientific             |
| `triangular_mesh` | Faceted, low-poly, geometric                  |
| `diagonal_lines` | Tension, motion, perspective                   |
| `cross_hatch`   | Crosshatch shading, classical printmaking      |
| `scanlines`     | CRT, print, halftone                           |
| `circuit_traces`| Electronic, schematic, PCB                     |
| `wave_field`    | Wind, water, heatmap, "soft"                   |
| `contour_lines` | Topographic map, heatmap isolines              |
| `topographic`   | Squiggly mountain, vintage map                 |
| `voronoi`       | Cellular, biological, organic tile             |
| `organic_blobs` | Cloud, inkblot, hand-painted                   |
| `constellation` | Network, neural, particle diagram              |
| `particles`     | Dust, stars, confetti                          |
| `fractal_silhouette` | Sierpinski, Hilbert, branching tree        |
| `noise_field`   | FBM noise, static, organic                     |

Picking the right family for your design context is the first authoring decision; everything else (spacing, colour, opacity) is fine-tuning.

## Why packing into single paths matters

A naive approach to `hex_mesh` at 1600×900 emits **1,536 `<path>` elements**, one per hex. Each `<path>` is a fixed-cost wrapper (about 30 bytes for the tag and the `M..L..L..L..L..L..L..Z` payload). Total: ~100 KB.

SubtlePatterns emits **one `<path>` per layer**, with all hexes concatenated as `M..L..L..L..L..L..L..ZM..L..L..L..L..L..L..Z…`. Same pixels, but the file is ~30 % smaller and the browser's paint cost is dramatically lower — modern browsers can rasterize a single complex path faster than thousands of small ones.

For the same reason:
* `dot_grid` uses `<use>` references against a single `<symbol>` definition.
* `noise_field` packs thousands of dots into one `<path>` of arc commands.
* `grid`, `triangular_mesh`, `wave_field`, `contour_lines`, etc. all use single paths.

## Determinism

Every pattern is fully deterministic from a config + seed. This is not a luxury — it's a contract. It means:

* You can commit a `pattern.svg` to git and review the diff when the library upgrades.
* You can A/B two seeds to find the right one, then lock the result.
* The same pattern over a *family* of related backgrounds (light, dark, gradient) will look *consistent*.

The library uses SHA-256 to derive a per-layer seed stream from the master seed. Changing the master seed by 1 produces a visually different pattern (avalanche effect, tested in `test_derive_seed_avalanche`).

## Output validation

Every emitted SVG is tested for:

* Valid XML (parses with `xml.etree`).
* Required attributes: `viewBox`, `role="img"`, `aria-hidden="true"`.
* No full-canvas background rects (when `OverlayConfig.background == "none"`).
* Correct number of layers (one `<g>` per overlay layer).

If you find a pattern that breaks one of these, it's a bug.
