"""Miscellaneous patterns: noise_field.

A pure noise visualisation that maps Perlin values to a small dot
density grid. Useful as a "noise / dust" overlay.
"""

from __future__ import annotations

import math

from ..core.config import PatternConfig
from ..core.noise import Perlin2D, fbm2d
from ..core.random_utils import make_rng
from ..svg import SvgElement, SvgGroup
from . import Size, register


@register("noise_field")
def _noise_field(layer: SvgGroup, cfg: PatternConfig, size: Size, *, seed: int) -> None:
    """A field of dots whose density follows a noise function.

    Each cell in a coarse grid is either drawn (probabilistically, with
    probability from the noise) or skipped. The result is a noisy "dust"
    field with organically varying density.

    Output is packed as ``<use>`` references against a shared ``<circle>``
    symbol (defined in a per-layer ``<defs>``), so 5000 dots cost ~6 bytes
    each instead of ~80.

    ``variant``:

    * ``""`` (default) — single-octave Perlin.
    * ``"fbm"`` — multi-octave FBM (richer texture).
    * ``"turbulence"`` — absolute-value FBM (sharp ridges, billow look).
    """
    perlin = Perlin2D(seed, "noise_field", cfg.variant)
    rng = make_rng(seed, "noise_field", cfg.variant, "scatter")
    w, h = size
    cell = max(2.0, cfg.spacing * 0.4)
    cols = int(w / cell) + 1
    rows = int(h / cell) + 1
    base_prob = max(0.05, min(0.95, cfg.density * 0.35))
    freq = cfg.frequency * 8
    fill = str(cfg.fill) if cfg.fill != "none" else "#888888"
    base_r = cfg.radius

    # Pack into 4 radius buckets so we get 4 symbols total, not one per dot.
    n_buckets = 4
    bucket_radii = [base_r * (0.5 + 1.0 * b / (n_buckets - 1)) for b in range(n_buckets)]
    fill_opacity = cfg.fill_opacity * cfg.opacity
    defs = SvgElement("defs")
    defs_id = f"sp-noise-defs-{cfg.seed}-{cfg.variant or 'd'}"
    defs.extend_attrs({"id": defs_id})
    for b, r in enumerate(bucket_radii):
        sym = SvgElement(
            "circle", id=f"sp-nd-{b}", cx="0", cy="0",
            r=f"{r:.2f}", fill=fill,
            fill_opacity=f"{fill_opacity:.3f}",
        )
        defs._el.append(sym._el)  # noqa: SLF001
    layer._el.append(defs._el)  # noqa: SLF001

    for j in range(rows):
        for i in range(cols):
            x = i * cell + cell * 0.5
            y = j * cell + cell * 0.5
            if cfg.variant == "fbm":
                n = fbm2d(perlin, x * freq, y * freq, octaves=4, persistence=0.5)
            elif cfg.variant == "turbulence":
                n = abs(perlin(x * freq, y * freq)) * 2 - 1
            else:
                n = perlin(x * freq, y * freq)
            p = base_prob * (0.5 + 0.5 * n)
            if rng.random() < p:
                jx = x + rng.uniform(-cell * 0.4, cell * 0.4)
                jy = y + rng.uniform(-cell * 0.4, cell * 0.4)
                # Random per-dot radius, bucketed.
                r_norm = rng.random()
                b = min(n_buckets - 1, int(r_norm * n_buckets))
                use = SvgElement(
                    "use", href=f"#sp-nd-{b}", x=f"{jx:.1f}", y=f"{jy:.1f}",
                )
                layer._el.append(use._el)  # noqa: SLF001
