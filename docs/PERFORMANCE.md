# SubtlePatterns — Performance

How big is the output, how fast is the render, and what does the browser do with it?

## Output size budgets

These are the typical byte counts at **1600 × 900** (default config) on a modern laptop:

| Family                 | Size    | Notes |
|------------------------|---------|-------|
| `grid` (default)       | ~2 KB   | Packed into 2 paths (V + H) |
| `diagonal_lines`       | ~3 KB   | Packed into 1 path |
| `cross_hatch`          | ~6 KB   | 2–4 paths |
| `fractal_silhouette`   | ~3 KB   | 1 path (carpet) or 1 path (Hilbert) |
| `circuit_traces`       | ~10 KB  | 1 path + dots |
| `organic_blobs`        | ~10 KB  | 1 path per blob |
| `voronoi` (default)    | ~3 KB   | 1 path (brute-force) |
| `scanlines`            | ~25 KB  | 1 path per line (halftone) |
| `constellation`        | ~30 KB  | 1 path (lines) + N circles (dots) |
| `particles` (default)  | ~4 KB   | 1 path |
| `particles` (`size_curve+field`) | ~50 KB | 1 `<g>` per particle (varied opacity) |
| `triangular_mesh`      | ~100 KB | 1 packed path (1500 triangles × 6 vertices) |
| `hex_mesh`             | ~150 KB | 1 packed path (~1500 hexes × 6 vertices) |
| `contour_lines`        | ~120 KB | Many short line segments per iso-line |
| `topographic`          | ~90 KB  | Same, FBM field |
| `noise_field`          | ~120 KB | 1 packed path (thousands of arc ops) |
| `wave_field`           | ~450 KB | One path per row × ~80 rows × many points |

A 1600×900 overlay is **typically 10–150 KB** for most families. A multi-layer overlay (3 layers) is usually 50–400 KB. Both fit comfortably in a single HTTP response.

## Render speed (Python)

Measured on a 2023 laptop, single thread, no JIT:

| Family                 | Time     | Notes |
|------------------------|----------|-------|
| `grid`                 | < 1 ms   | |
| `diagonal_lines`       | < 1 ms   | |
| `circuit_traces`       | ~1 ms    | 24 traces × random walk |
| `fractal_silhouette`   | < 1 ms   | Carpet / Hilbert / tree |
| `wave_field`           | ~200 ms  | 80 rows × ~200 sample points × Perlin |
| `contour_lines`        | ~25 ms   | 14 levels × 32×18 grid × marching squares |
| `topographic`          | ~30 ms   | 12 levels × 26×15 grid × FBM × marching squares |
| `voronoi`              | ~1 s     | O(W·H·N) brute-force — the slow one |
| `noise_field`          | ~70 ms   | 1 packed path, ~6000 arc ops |
| `hex_mesh`             | ~7 ms    | 1 packed path |
| `dot_grid`             | ~10 ms   | `<use>` references |

Total time to render a 3-layer overlay (`noetroniq_network`-class): typically 30–80 ms.

The slow outlier is `voronoi`. The brute-force nearest-seed walk is O(W·H·N). For a 1600×900 canvas with 30 seeds, that's ~43 million operations. A future optimization (Fortune's algorithm, jump flooding, or just a much coarser sample grid with edge refinement) is on the roadmap — see `docs/DESIGN_NOTES.md`.

## Browser paint cost

The browser's GPU rasterizer can paint a single complex path faster than thousands of small ones. The packing in SubtlePatterns is therefore both a wire-size optimization *and* a paint-cost optimization.

In practice, on a 2023 MacBook Pro:

* 1 KB packed path: < 1 ms to paint.
* 100 KB packed path: ~5–15 ms.
* 450 KB packed path (`wave_field`): ~30–60 ms.

If you find a particular pattern is painting slowly, the most impactful knobs (in order) are:

1. **Lower `levels`** (for noise-based patterns).
2. **Increase `spacing`** (for grid/dot families) — fewer cells, less path data.
3. **Switch to `variant=""`** if you're on a heavier variant (e.g. `hex_mesh.triangulated` is 6× the path data of the default).
4. **Resize the canvas** with `--size` — a 1200×675 canvas is 56 % the area of a 1600×900, with proportional cost.

## Caching

Because the output is fully deterministic, you can:

* Pre-render and cache the SVG bytes at build time (`subtle-patterns render …`).
* Serve as a static file with `Cache-Control: public, max-age=31536000, immutable`.
* Use content-hashing in the URL for cache-busting on config changes.

The library is a build-time tool. It is not designed to render patterns per-request in a web server — that would be wasteful given the output is fully deterministic.

## Memory

Peak heap usage is dominated by the `path_data` strings. For a 1 MB SVG output, peak Python heap is ~5–10 MB (path strings + ElementTree nodes + Perlin permutation table). There are no leaks; the entire request is short-lived.

## When NOT to use SubtlePatterns

* You need an animated pattern (use SMIL or CSS animations on a single SVG element).
* You need a pattern whose parameters are bound to user data (use a JS-side renderer).
* You need raster output (use a server-side rasterizer like `resvg` or `librsvg`).

SubtlePatterns is a **build-time, deterministic SVG generator**. If you need any of the above, you want a different tool.
