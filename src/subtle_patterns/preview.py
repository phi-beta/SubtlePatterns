"""Self-contained HTML preview gallery.

Generates a single HTML file that renders every requested preset over a
configurable CSS backdrop. The output is dependency-free (no JS, no
external CSS, no fonts) so it can be opened from the filesystem or served
from a static host.

Two input modes are supported:

* **preset mode** (``presets=...``) — every entry is a preset name; the
  preset config is looked up and rendered at the tile size.
* **sample mode** (``samples=...``) — each entry is a
  ``(name, svg, info)`` triple: a label, an already-rendered SVG string,
  and an info string. This is the mode used by the sample generator, so
  the ``preview.html`` matches the curated ``examples/samples/*.svg`` set
  one-for-one. The SVGs are resized to the tile size by replacing the
  root ``<svg>`` width/height; the existing ``viewBox`` keeps the pattern
  scale-correct.
"""

from __future__ import annotations

import html
import os
import re
from typing import Iterable, List, Optional, Sequence, Tuple

from .engine import render_overlay, render_pattern
from .presets import get_preset


def _render_preset(name: str, tile_size: Tuple[float, float], seed: int) -> str:
    """Render a single preset to an SVG string sized for the tile."""
    cfg = get_preset(name)
    if hasattr(cfg, "layers"):
        return render_overlay(cfg, size=tile_size, seed=seed)
    return render_pattern(cfg, size=tile_size, seed=seed)


# A sample is a (label, svg, info) triple. The svg is at full size; the
# gallery resizes it to the tile size for compact display (the full-size
# files live alongside the gallery as ``examples/samples/*.svg``).
Sample = Tuple[str, str, str]


_SVG_WIDTH_HEIGHT = re.compile(
    r'(<svg\b[^>]*?\bwidth=")[^"]*("[^>]*?\bheight=")[^"]*(")'
)


def _resize_svg_root(svg: str, size: Tuple[float, float]) -> str:
    """Resize an inlined SVG by replacing the root ``<svg>`` width/height.

    The pattern's existing ``viewBox`` is preserved, so the pattern
    scales to fit the new size. We use a small string substitution
    rather than parsing the SVG so this stays fast on large samples.
    """
    w, h = size
    new_svg, n = _SVG_WIDTH_HEIGHT.subn(
        lambda m: f'{m.group(1)}{w:.0f}{m.group(2)}{h:.0f}{m.group(3)}',
        svg, count=1,
    )
    if n == 0:
        # Fallback: the <svg> tag has no width/height; inject them right
        # after the tag name. Still better than nothing.
        new_svg = re.sub(
            r'(<svg\b)([^>]*?)(>)',
            lambda m: f'{m.group(1)}{m.group(2)} width="{w:.0f}" height="{h:.0f}"{m.group(3)}',
            svg, count=1,
        )
    # Strip the XML prolog (we're inlining into HTML).
    if new_svg.startswith("<?xml"):
        new_svg = new_svg.split("?>", 1)[1].lstrip()
    return new_svg


def gallery_html(
    *,
    presets: Optional[Iterable[str]] = None,
    samples: Optional[Sequence[Sample]] = None,
    backdrop: str = "linear-gradient(135deg,#001f3f,#0d2f57)",
    tile_size: Tuple[float, float] = (480.0, 270.0),
    seed: int = 0,
    columns: int = 2,
    title: str = "SubtlePatterns — preset gallery",
) -> str:
    """Build a self-contained HTML preview page.

    Parameters
    ----------
    presets:
        Iterable of preset names to include. ``None`` (default) = all
        registered presets. Mutually exclusive with ``samples``: if
        ``samples`` is given, ``presets`` is ignored.
    samples:
        Sequence of ``(label, full_size_svg, info)`` triples — the
        curated set of samples. When given, the gallery shows the
        sample SVGs (resized to the tile size) one tile per entry.
        This is the mode used by ``scripts/generate_samples.py`` so
        that ``preview.html`` always shows the same N tiles as there
        are ``*.svg`` files in ``examples/samples/``.
    backdrop:
        CSS background applied to every tile.
    tile_size:
        ``(width, height)`` in CSS pixels. The SVG ``viewBox`` matches
        the tile size, so the pattern scales to fit.
    seed:
        Master seed passed to every preset render (preset mode only).
    columns:
        Number of tiles per row.
    title:
        HTML ``<title>`` and ``<h1>``.
    """
    css = f"""
    :root {{
      --tile-w: {tile_size[0]:.0f}px;
      --tile-h: {tile_size[1]:.0f}px;
      --columns: {columns};
      --backdrop: {backdrop};
      --fg: #f5f5f5;
      --muted: #c5c5c5;
      --border: rgba(255,255,255,0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0a0a0a;
      color: var(--fg);
      padding: 32px;
    }}
    h1 {{
      font-size: 20px;
      font-weight: 500;
      margin: 0 0 4px 0;
      letter-spacing: 0.02em;
    }}
    p.lead {{
      margin: 0 0 32px 0;
      color: var(--muted);
      font-size: 13px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(var(--columns), 1fr);
      gap: 18px;
    }}
    .tile {{
      position: relative;
      border: 1px solid var(--border);
      border-radius: 6px;
      overflow: hidden;
      background: var(--backdrop);
      aspect-ratio: {tile_size[0]:.0f} / {tile_size[1]:.0f};
    }}
    .tile svg {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      display: block;
    }}
    .label {{
      position: absolute;
      left: 8px;
      bottom: 8px;
      background: rgba(0,0,0,0.55);
      color: var(--fg);
      padding: 3px 8px;
      border-radius: 3px;
      font-size: 11px;
      font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
      letter-spacing: 0.02em;
    }}
    .meta {{
      display: flex;
      gap: 16px;
      color: var(--muted);
      font-size: 12px;
      margin-top: 4px;
    }}
    @media (max-width: 900px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
    """

    tiles_html: List[str] = []
    names: List[str] = []

    if samples is not None:
        # Sample mode: each entry is (label, full_size_svg, info). We
        # resize the SVG to the tile dimensions via a string substitution
        # on the root <svg> width/height. The viewBox is preserved, so
        # the pattern scales to fit.
        for label, svg, info in samples:
            names.append(label)
            svg_resized = _resize_svg_root(svg, tile_size)
            tiles_html.append(
                f'<div class="tile">{svg_resized}<div class="label">'
                f'{html.escape(label)}'
                f'<span style="color:#999;margin-left:6px">{html.escape(info)}</span>'
                f'</div></div>'
            )
    else:
        # Preset mode: render each preset to a tile-sized SVG.
        if presets is None:
            from .presets import list_presets
            names = list(list_presets())
        else:
            names = list(presets)
        for name in names:
            try:
                svg = _render_preset(name, tile_size, seed)
            except Exception as exc:  # noqa: BLE001
                tiles_html.append(
                    f'<div class="tile"><div class="label">{html.escape(name)} '
                    f'<span style="color:#f87171">(error: {html.escape(str(exc))})</span></div></div>'
                )
                continue
            cfg = get_preset(name)
            if hasattr(cfg, "layers"):
                info = f"{len(cfg.layers)} layers"
            else:
                info = cfg.family + (f" / {cfg.variant}" if cfg.variant else "")
            if svg.startswith("<?xml"):
                svg = svg.split("?>", 1)[1].lstrip()
            tiles_html.append(
                f'<div class="tile">{svg}<div class="label">'
                f'{html.escape(name)}'
                f'<span style="color:#999;margin-left:6px">{html.escape(info)}</span>'
                f'</div></div>'
            )

    out = (
        '<!doctype html>\n'
        '<html lang="en">\n'
        f'<head><meta charset="utf-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{html.escape(title)}</title>\n'
        f'<style>{css}</style></head>\n'
        '<body>\n'
        f'<h1>{html.escape(title)}</h1>\n'
        f'<p class="lead">{len(names)} tiles · '
        f'{tile_size[0]:.0f}×{tile_size[1]:.0f} · seed {seed} · '
        f'{html.escape(backdrop)}</p>\n'
        '<div class="grid">\n'
        + "\n".join(tiles_html)
        + "\n</div>\n"
        '</body></html>\n'
    )
    return out


def write_gallery(
    path: str,
    **kwargs,
) -> str:
    """Build a gallery and write it to ``path``. Returns the path written."""
    html_text = gallery_html(**kwargs)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html_text)
    return os.path.abspath(path)
