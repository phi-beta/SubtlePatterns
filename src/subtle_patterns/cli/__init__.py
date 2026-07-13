"""Command-line interface for SubtlePatterns.

Entry point: ``subtle-patterns`` (see ``pyproject.toml`` ``[project.scripts]``).

Subcommands:

* ``render <preset>`` — render a single built-in pattern preset.
* ``render-config <file>`` — render a config from a JSON/YAML file.
* ``overlay <file>`` — render a multi-layer overlay from a JSON/YAML file.
* ``overlay <preset>`` — render a built-in overlay preset.
* ``inline <key=value;...>`` — render an inline ``PatternConfig``.
* ``list-presets`` — print every registered preset.
* ``gallery`` — generate a self-contained HTML preview of all presets.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
from typing import Any, Optional, Sequence, Tuple

from ..core.config import (
    BlendMode,
    Color,
    OverlayConfig,
    PatternConfig,
    parse_config_file,
)
from ..core.random_utils import derive_seed
from ..engine import render_overlay, render_pattern
from ..presets import get_preset, list_presets

__all__ = ["cli", "build_parser", "main"]


# ---------------------------------------------------------------------------
# Size / colour parsing
# ---------------------------------------------------------------------------

_SIZE_RE = re.compile(r"^(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)$")
_ASPECT_RE = re.compile(r"^(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)$")


def _parse_size(value: str) -> Tuple[float, float]:
    """Parse ``"WIDTHxHEIGHT"`` (e.g. ``"1600x900"``)."""
    m = _SIZE_RE.match(value.strip())
    if not m:
        raise argparse.ArgumentTypeError(
            f"Size must look like '1600x900', got {value!r}"
        )
    return (float(m.group(1)), float(m.group(2)))


def _parse_aspect(value: str) -> float:
    """Parse ``"W:H"`` (e.g. ``"16:9"``)."""
    m = _ASPECT_RE.match(value.strip())
    if not m:
        raise argparse.ArgumentTypeError(
            f"Aspect must look like '16:9', got {value!r}"
        )
    a, b = float(m.group(1)), float(m.group(2))
    if b <= 0:
        raise argparse.ArgumentTypeError("Aspect ratio denominator must be > 0")
    return a / b


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    p = argparse.ArgumentParser(
        prog="subtle-patterns",
        description=(
            "Render subtle SVG overlay patterns for website backgrounds. "
            "Patterns are mostly-transparent; layer them over your background "
            "and under your text."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              subtle-patterns render hex_mesh --size 1600x900 --seed 42
              subtle-patterns render-config my-pattern.yaml --out my-pattern.svg
              subtle-patterns overlay examples/noetroniq_network.yaml --out overlay.svg
              subtle-patterns gallery --backdrop "linear-gradient(135deg,#001f3f,#0d2f57)"
            """),
    )
    p.add_argument(
        "--version", action="version",
        version=f"subtle-patterns {__version__}",
    )

    sub = p.add_subparsers(dest="command", required=True, metavar="COMMAND")

    # ---- render --------------------------------------------------------
    p_render = sub.add_parser(
        "render",
        help="Render a single pattern preset as SVG.",
        description="Render a single built-in pattern preset as SVG.",
    )
    p_render.add_argument("preset", help="Name of the preset to render.")
    p_render.add_argument(
        "--size", type=_parse_size, default=(1600.0, 900.0),
        metavar="WxH",
        help="Canvas size in user units (default: 1600x900).",
    )
    p_render.add_argument("--seed", type=int, default=0, help="Master seed (default: 0).")
    p_render.add_argument("--variant", default=None, help="Override the preset's variant.")
    p_render.add_argument(
        "--stroke", type=Color, default=None,
        help="Override stroke colour (CSS colour).",
    )
    p_render.add_argument("--fill", type=Color, default=None, help="Override fill colour.")
    p_render.add_argument(
        "--stroke-opacity", type=float, default=None,
        help="Override stroke opacity (0..1).",
    )
    p_render.add_argument("--fill-opacity", type=float, default=None, help="Override fill opacity (0..1).")
    p_render.add_argument("--spacing", type=float, default=None, help="Override spacing.")
    p_render.add_argument("--density", type=float, default=None, help="Override density.")
    p_render.add_argument("--out", "-o", default=None, help="Output file (default: stdout).")
    p_render.add_argument("--pretty", action="store_true", help="Pretty-print the SVG.")
    p_render.set_defaults(_func=_cmd_render)

    # ---- render-config -------------------------------------------------
    p_rc = sub.add_parser(
        "render-config",
        help="Render a pattern config from a JSON/YAML file.",
        description="Render a single pattern described by a JSON or YAML config file.",
    )
    p_rc.add_argument("config_file", help="Path to the JSON/YAML config file.")
    p_rc.add_argument("--size", type=_parse_size, default=None, metavar="WxH",
                       help="Override canvas size.")
    p_rc.add_argument("--seed", type=int, default=0, help="Master seed (default: 0).")
    p_rc.add_argument("--out", "-o", default=None, help="Output file (default: stdout).")
    p_rc.add_argument("--pretty", action="store_true", help="Pretty-print the SVG.")
    p_rc.set_defaults(_func=_cmd_render_config)

    # ---- overlay -------------------------------------------------------
    p_ov = sub.add_parser(
        "overlay",
        help="Render a multi-layer overlay (preset or config file).",
        description=(
            "Render a multi-layer overlay. If the argument names a known "
            "overlay preset, that preset is used. Otherwise it is treated "
            "as a path to a JSON/YAML overlay config."
        ),
    )
    p_ov.add_argument("source", help="Preset name or config file path.")
    p_ov.add_argument("--size", type=_parse_size, default=None, metavar="WxH",
                       help="Override canvas size.")
    p_ov.add_argument("--seed", type=int, default=0, help="Master seed (default: 0).")
    p_ov.add_argument("--out", "-o", default=None, help="Output file (default: stdout).")
    p_ov.add_argument("--pretty", action="store_true", help="Pretty-print the SVG.")
    p_ov.set_defaults(_func=_cmd_overlay)

    # ---- inline --------------------------------------------------------
    p_inline = sub.add_parser(
        "inline",
        help="Render a pattern from an inline key=value string.",
        description=(
            "Render a pattern specified as a ;-separated key=value string. "
            "Example: subtle-patterns inline 'family=contour_lines;stroke=#0d2f57;levels=14'"
        ),
    )
    p_inline.add_argument("spec", help="Inline config spec, e.g. 'family=hex_mesh;spacing=48'.")
    p_inline.add_argument("--size", type=_parse_size, default=(1600.0, 900.0), metavar="WxH")
    p_inline.add_argument("--seed", type=int, default=0, help="Master seed (default: 0).")
    p_inline.add_argument("--out", "-o", default=None, help="Output file (default: stdout).")
    p_inline.add_argument("--pretty", action="store_true", help="Pretty-print the SVG.")
    p_inline.set_defaults(_func=_cmd_inline)

    # ---- list-presets --------------------------------------------------
    p_lp = sub.add_parser(
        "list-presets",
        help="List every registered preset.",
        description="Print the names of every registered preset, one per line.",
    )
    p_lp.add_argument(
        "--kind", choices=("all", "pattern", "overlay"), default="all",
        help="Filter by preset kind (default: all).",
    )
    p_lp.add_argument(
        "--json", action="store_true",
        help="Emit JSON instead of plain text.",
    )
    p_lp.set_defaults(_func=_cmd_list_presets)

    # ---- gallery -------------------------------------------------------
    p_gal = sub.add_parser(
        "gallery",
        help="Generate a self-contained HTML preview of every preset.",
        description=(
            "Render every preset into a single self-contained HTML file. "
            "Use --out to write to disk; the default is 'preview.html'."
        ),
    )
    p_gal.add_argument(
        "--backdrop", default="linear-gradient(135deg,#001f3f,#0d2f57)",
        help="CSS background applied to every preview tile.",
    )
    p_gal.add_argument(
        "--tile-size", type=_parse_size, default=(480.0, 270.0),
        metavar="WxH", help="Preview tile size in CSS pixels (default: 480x270).",
    )
    p_gal.add_argument(
        "--seed", type=int, default=0, help="Master seed for the gallery.",
    )
    p_gal.add_argument(
        "--columns", type=int, default=2,
        help="Number of tile columns in the gallery (default: 2).",
    )
    p_gal.add_argument(
        "--title", default="SubtlePatterns — preset gallery",
        help="HTML <title> for the page.",
    )
    p_gal.add_argument(
        "--out", "-o", default="preview.html",
        help="Output HTML file (default: preview.html).",
    )
    p_gal.add_argument(
        "--include", action="append", default=None,
        help="Only include these presets (may be given multiple times).",
    )
    p_gal.add_argument(
        "--exclude", action="append", default=None,
        help="Skip these presets (may be given multiple times).",
    )
    p_gal.set_defaults(_func=_cmd_gallery)

    return p


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _maybe_override(cfg: PatternConfig, args: argparse.Namespace) -> PatternConfig:
    """Apply CLI overrides to a PatternConfig."""
    overrides: dict[str, Any] = {}
    if getattr(args, "variant", None) is not None:
        overrides["variant"] = args.variant
    if getattr(args, "stroke", None) is not None:
        overrides["stroke"] = args.stroke
    if getattr(args, "fill", None) is not None:
        overrides["fill"] = args.fill
    if getattr(args, "stroke_opacity", None) is not None:
        overrides["stroke_opacity"] = args.stroke_opacity
    if getattr(args, "fill_opacity", None) is not None:
        overrides["fill_opacity"] = args.fill_opacity
    if getattr(args, "spacing", None) is not None:
        overrides["spacing"] = args.spacing
    if getattr(args, "density", None) is not None:
        overrides["density"] = args.density
    if not overrides:
        return cfg
    return cfg.merged(overrides)


def _emit(svg: str, out: Optional[str]) -> None:
    if out is None:
        sys.stdout.write(svg)
        if not svg.endswith("\n"):
            sys.stdout.write("\n")
    else:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(svg)
            if not svg.endswith("\n"):
                fh.write("\n")


def _cmd_render(args: argparse.Namespace) -> int:
    if args.preset not in list_presets():
        sys.stderr.write(
            f"Unknown preset {args.preset!r}. "
            f"Run 'subtle-patterns list-presets' to see options.\n"
        )
        return 2
    cfg = get_preset(args.preset)
    if hasattr(cfg, "layers"):
        # Allow rendering an overlay preset via `render` too.
        svg = render_overlay(cfg, size=args.size, seed=args.seed)
    else:
        cfg = _maybe_override(cfg, args)  # type: ignore[arg-type]
        svg = render_pattern(cfg, size=args.size, seed=args.seed)
    _emit(svg, args.out)
    return 0


def _cmd_render_config(args: argparse.Namespace) -> int:
    cfg = parse_config_file(args.config_file)
    if hasattr(cfg, "layers"):
        svg = render_overlay(cfg, size=args.size, seed=args.seed)
    else:
        svg = render_pattern(cfg, size=args.size, seed=args.seed)
    if args.pretty:
        from ..core.config import OverlayConfig as _OC  # noqa: PLC0415
        from ..engine import _coerce_size  # noqa: PLC0415
        from ..svg import _strip_default_ns_prefix  # noqa: PLC0415
        import xml.etree.ElementTree as _ET  # noqa: PLC0415
        size = _coerce_size(args.size, default=(1600.0, 900.0))
        if hasattr(cfg, "family"):
            ov = _OC.from_pattern(cfg, width=size[0], height=size[1])
        else:
            ov = cfg  # type: ignore[assignment]
        # Re-serialize with indent.
        root = _ET.fromstring(svg)
        _ET.indent(root, space="  ")
        body = _ET.tostring(root, encoding="unicode")
        if "ns0:" in body:
            body = _strip_default_ns_prefix(body)
        svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + body
    _emit(svg, args.out)
    return 0


def _cmd_overlay(args: argparse.Namespace) -> int:
    if args.source in list_presets():
        cfg = get_preset(args.source)
    elif os.path.isfile(args.source):
        cfg = parse_config_file(args.source)
    else:
        sys.stderr.write(
            f"{args.source!r} is neither a known preset nor an existing file.\n"
        )
        return 2
    if not hasattr(cfg, "layers"):
        sys.stderr.write(
            f"Preset {args.source!r} is a single pattern, not an overlay. "
            "Use `render` instead.\n"
        )
        return 2
    svg = render_overlay(cfg, size=args.size, seed=args.seed)
    if args.pretty:
        from ..svg import _strip_default_ns_prefix  # noqa: PLC0415
        import xml.etree.ElementTree as _ET  # noqa: PLC0415
        root = _ET.fromstring(svg)
        _ET.indent(root, space="  ")
        body = _ET.tostring(root, encoding="unicode")
        if "ns0:" in body:
            body = _strip_default_ns_prefix(body)
        svg = '<?xml version="1.0" encoding="UTF-8"?>\n' + body
    _emit(svg, args.out)
    return 0


def _cmd_inline(args: argparse.Namespace) -> int:
    from ..core.config import parse_inline
    cfg = parse_inline(args.spec)
    if hasattr(cfg, "layers"):
        svg = render_overlay(cfg, size=args.size, seed=args.seed)
    else:
        svg = render_pattern(cfg, size=args.size, seed=args.seed)
    _emit(svg, args.out)
    return 0


def _cmd_list_presets(args: argparse.Namespace) -> int:
    names = list_presets()
    rows = []
    for name in names:
        cfg = get_preset(name)
        kind = "overlay" if hasattr(cfg, "layers") else "pattern"
        if args.kind != "all" and args.kind != kind:
            continue
        if hasattr(cfg, "layers"):
            label = f"{kind:<8} {len(cfg.layers)} layers"
        else:
            label = f"{kind:<8} {cfg.family}"
            if cfg.variant:
                label += f" / {cfg.variant}"
        rows.append((name, label))
    if args.json:
        json.dump(
            [{"name": n, "kind": k.split()[0], "info": k} for n, k in rows],
            sys.stdout, indent=2,
        )
        sys.stdout.write("\n")
    else:
        width = max(len(n) for n, _ in rows) if rows else 0
        for n, k in rows:
            sys.stdout.write(f"{n:<{width}}  {k}\n")
    return 0


def _cmd_gallery(args: argparse.Namespace) -> int:
    from ..preview import gallery_html
    presets = [
        n for n in list_presets()
        if (not args.include or n in args.include)
        and (not args.exclude or n not in args.exclude)
    ]
    html = gallery_html(
        presets=presets,
        backdrop=args.backdrop,
        tile_size=args.tile_size,
        seed=args.seed,
        columns=args.columns,
        title=args.title,
    )
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)
    sys.stderr.write(f"Wrote {args.out} ({len(html):,} bytes, {len(presets)} presets)\n")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

# Imported lazily so help text doesn't have to import the whole package.
__version__ = "0.1.0"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "_func", None)
    if handler is None:
        parser.print_help()
        return 1
    try:
        return int(handler(args) or 0)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"error: {type(exc).__name__}: {exc}\n")
        return 1


def cli() -> None:
    """``console_scripts`` entry point."""
    raise SystemExit(main())
