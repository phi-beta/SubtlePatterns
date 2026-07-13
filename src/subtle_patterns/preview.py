"""Self-contained HTML preview gallery.

Generates a single HTML file that renders every requested preset over a
configurable CSS backdrop. The output is dependency-free (no JS, no
external CSS, no fonts) so it can be opened from the filesystem or served
from a static host.
"""

from __future__ import annotations

import html
import os
from typing import Iterable, Optional, Sequence, Tuple

from .engine import render_overlay, render_pattern
from .presets import get_preset


def _render_preset(name: str, tile_size: Tuple[float, float], seed: int) -> str:
    """Render a single preset to an SVG string sized for the tile."""
    cfg = get_preset(name)
    if hasattr(cfg, "layers"):
        return render_overlay(cfg, size=tile_size, seed=seed)
    return render_pattern(cfg, size=tile_size, seed=seed)


def gallery_html(
    *,
    presets: Optional[Iterable[str]] = None,
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
        registered presets.
    backdrop:
        CSS background applied to every tile.
    tile_size:
        ``(width, height)`` in CSS pixels. The SVG ``viewBox`` matches
        the tile size, so the pattern scales to fit.
    seed:
        Master seed passed to every preset render.
    columns:
        Number of tiles per row.
    title:
        HTML ``<title>`` and ``<h1>``.
    """
    if presets is None:
        from .presets import list_presets
        names = list(list_presets())
    else:
        names = list(presets)

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

    tiles_html: list[str] = []
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
        # Strip the XML prolog so we can inline the SVG inside HTML.
        if svg.startswith("<?xml"):
            svg = svg.split("?>", 1)[1].lstrip()
        tiles_html.append(
            f'<div class="tile">{svg}<div class="label">'
            f'{html.escape(name)}<span style="color:#999;margin-left:6px">{html.escape(info)}</span>'
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
        f'<p class="lead">{len(names)} presets · '
        f'{tile_size[0]:.0f}×{tile_size[1]:.0f} tiles · seed {seed} · '
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
