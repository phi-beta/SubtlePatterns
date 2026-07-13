"""SVG element builder for SubtlePatterns.

We build SVG using :mod:`xml.etree.ElementTree` (stdlib) so the library
stays zero-dependency. An optional :mod:`lxml` backend produces slightly
more compact output and is significantly faster on large patterns.

Element factory pattern::

    g = SvgGroup(stroke="#0d2f57", stroke_opacity=0.2)
    g.line(0, 0, 100, 100)
    g.path("M0 0 L 10 10", fill="none")
    svg = SvgDocument(width=1600, height=900).add(g).to_string()
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, Iterable, Sequence

_SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", _SVG_NS)


def _q(tag: str) -> str:
    """Return a Clark-notation tag for a default-namespaced element."""
    if ":" in tag:
        return tag
    return f"{{{_SVG_NS}}}{tag}"


# ---------------------------------------------------------------------------
# Low-level element builder
# ---------------------------------------------------------------------------

class SvgElement:
    """A tiny wrapper around an ElementTree ``Element`` with attribute helpers."""

    __slots__ = ("_el",)

    def __init__(self, tag: str, **attrs: Any) -> None:
        self._el = ET.Element(_q(tag))
        # ElementTree's `Element(tag, attrib=...)` accepts a dict, but for
        # ergonomic call-site use we accept **kwargs and apply them after.
        for k, v in _strip_none(attrs).items():
            k_attr = k.replace("__", ":").replace("_", "-")
            self._el.set(k_attr, _coerce_attr(v))

    def set(self, **attrs: Any) -> "SvgElement":
        for k, v in attrs.items():
            if v is None:
                continue
            k_attr = k.replace("__", ":").replace("_", "-")
            self._el.set(k_attr, _coerce_attr(v))
        return self

    def add(self, child: "SvgElement") -> "SvgElement":
        self._el.append(child._el)  # noqa: SLF001
        return self

    def add_many(self, children: Iterable["SvgElement"]) -> "SvgElement":
        for c in children:
            self._el.append(c._el)  # noqa: SLF001
        return self

    def extend_attrs(self, attrs: dict[str, Any]) -> "SvgElement":
        for k, v in attrs.items():
            if v is None:
                continue
            k_attr = k.replace("__", ":").replace("_", "-")
            self._el.set(k_attr, _coerce_attr(v))
        return self

    @property
    def raw(self) -> ET.Element:
        return self._el


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _coerce_attr(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        if v == int(v):
            return str(int(v))
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return str(v)


# ---------------------------------------------------------------------------
# Group with shape helpers
# ---------------------------------------------------------------------------

class SvgGroup(SvgElement):
    """A ``<g>`` element with helpers for common shapes."""

    def __init__(self, **attrs: Any) -> None:
        super().__init__("g", **attrs)

    # ---- primitives -----------------------------------------------------

    def line(self, x1: float, y1: float, x2: float, y2: float) -> "SvgElement":
        el = SvgElement(
            "line",
            x1=f"{x1:.3f}", y1=f"{y1:.3f}",
            x2=f"{x2:.3f}", y2=f"{y2:.3f}",
        )
        self.add(el)
        return el

    def path(self, d: str, **attrs: Any) -> "SvgElement":
        el = SvgElement("path", d=d, **attrs)
        self.add(el)
        return el

    def circle(self, cx: float, cy: float, r: float, **attrs: Any) -> "SvgElement":
        el = SvgElement("circle", cx=f"{cx:.3f}", cy=f"{cy:.3f}", r=f"{r:.3f}", **attrs)
        self.add(el)
        return el

    def rect(self, x: float, y: float, w: float, h: float, **attrs: Any) -> "SvgElement":
        el = SvgElement("rect", x=f"{x:.3f}", y=f"{y:.3f}",
                        width=f"{w:.3f}", height=f"{h:.3f}", **attrs)
        self.add(el)
        return el

    def polygon(self, points: Sequence[tuple[float, float]], **attrs: Any) -> "SvgElement":
        pts = " ".join(f"{x:.3f},{y:.3f}" for x, y in points)
        el = SvgElement("polygon", points=pts, **attrs)
        self.add(el)
        return el

    # ---- bulk writers ---------------------------------------------------

    def add_path_list(self, paths: Iterable[str], **attrs: Any) -> int:
        """Add many ``<path>`` elements sharing the same attrs. Returns count."""
        n = 0
        for d in paths:
            if d:
                self.path(d, **attrs)
                n += 1
        return n

    def add_circle_list(
        self,
        points: Iterable[tuple[float, float]],
        radius: float | Sequence[float],
        **attrs: Any,
    ) -> int:
        n = 0
        idx = 0
        for p in points:
            if isinstance(radius, (int, float)):
                r = float(radius)
            else:
                r = float(radius[idx])
            self.circle(p[0], p[1], r, **attrs)
            n += 1
            idx += 1
        return n


# ---------------------------------------------------------------------------
# Document root
# ---------------------------------------------------------------------------

class SvgDocument(SvgElement):
    """The ``<svg>`` root. Use :meth:`to_string` to serialize.

    Defaults follow production practice:

    * ``xmlns="http://www.w3.org/2000/svg"`` — required.
    * ``viewBox`` matches ``width``/``height`` for crisp scaling.
    * ``role="img"`` and ``aria-hidden="true"`` — overlays are decorative.
    * No ``xmlns:xlink`` (we never use ``xlink:href``).
    """

    def __init__(
        self,
        *,
        width: float,
        height: float,
        view_box: tuple[float, float, float, float] | None = None,
        title: str | None = None,
        desc: str | None = None,
        **attrs: Any,
    ) -> None:
        if view_box is None:
            view_box = (0.0, 0.0, float(width), float(height))
        # Materialise any provided `aria_hidden` (Python kw) into `aria-hidden`.
        if "aria_hidden" in attrs and "aria-hidden" not in attrs:
            attrs["aria-hidden"] = attrs.pop("aria_hidden")
        # The xmlns declaration is added by ElementTree automatically because
        # we register the default namespace at module import time; do NOT
        # also set it as a literal attribute.
        attrs.pop("xmlns", None)
        super().__init__(
            "svg",
            width=f"{width:.3f}",
            height=f"{height:.3f}",
            viewBox=" ".join(f"{v:g}" for v in view_box),
            role="img",
            **{"aria-hidden": "true"},
            **attrs,
        )
        if title:
            title_el = SvgElement("title")
            title_el._el.text = title  # noqa: SLF001  (set child text, not attr)
            self.add(title_el)
        if desc:
            desc_el = SvgElement("desc")
            desc_el._el.text = desc  # noqa: SLF001
            self.add(desc_el)

    def add(self, child: SvgElement) -> "SvgDocument":  # type: ignore[override]
        self._el.append(child._el)  # noqa: SLF001
        return self

    def to_string(self, *, pretty: bool = False) -> str:
        """Serialize to a UTF-8 string.

        With ``pretty=False`` (default) the output is single-line for compact
        transport, since SVGs are usually inlined or served as static files
        where every byte counts. Set ``pretty=True`` for a multi-line
        human-readable dump.
        """
        if pretty:
            ET.indent(self._el, space="  ")
        body = ET.tostring(self._el, encoding="unicode")
        if "ns0:" in body:
            body = _strip_default_ns_prefix(body)
        if not body.startswith("<?xml"):
            body = '<?xml version="1.0" encoding="UTF-8"?>\n' + body
        return body


def _strip_default_ns_prefix(body: str) -> str:
    """Replace ``<ns0:tag>`` with ``<tag>`` when the document has a default ns."""
    return (
        body
        .replace("<ns0:", "<")
        .replace("</ns0:", "</")
        .replace("xmlns:ns0=", "xmlns=")
    )
