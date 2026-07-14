"""Tests for the warp system (core.warp + engine integration)."""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from subtle_patterns import render_overlay, render_pattern
from subtle_patterns.core.config import PatternConfig
from subtle_patterns.core.warp import (
    AFFINE_WARPS,
    WarpKind,
    WarpSpec,
    compute_warp,
)


# ---------------------------------------------------------------------------
# WarpKind enum
# ---------------------------------------------------------------------------

class TestWarpKind:
    def test_all_warps_distinct(self):
        # Every member of the enum should have a unique value.
        values = [k.value for k in WarpKind]
        assert len(values) == len(set(values))

    def test_affine_set_matches_documented(self):
        # The AFFINE_WARPS set should be a subset of WarpKind and should
        # include the documented affine warps.
        for kind in (
            WarpKind.TILT_X, WarpKind.TILT_Y, WarpKind.TILT_XY,
            WarpKind.SCALE_H, WarpKind.SCALE_V,
            WarpKind.SHEAR_X, WarpKind.SHEAR_Y,
        ):
            assert kind in AFFINE_WARPS

    def test_non_affine_warps_excluded_from_affine_set(self):
        for kind in (
            WarpKind.CYLINDER_H, WarpKind.CYLINDER_V,
            WarpKind.SPHERE, WarpKind.RIPPLE, WarpKind.TWIST,
        ):
            assert kind not in AFFINE_WARPS

    def test_from_string(self):
        assert WarpKind("tilt_x") is WarpKind.TILT_X
        assert WarpKind("ripple") is WarpKind.RIPPLE

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            WarpKind("not-a-warp")


# ---------------------------------------------------------------------------
# compute_warp
# ---------------------------------------------------------------------------

class TestComputeWarp:
    def test_none_returns_empty_spec(self):
        spec = compute_warp(WarpKind.NONE, width=800, height=600, strength=0.5)
        assert spec == WarpSpec()

    def test_zero_strength_returns_empty_spec(self):
        spec = compute_warp(WarpKind.TILT_X, width=800, height=600, strength=0.0)
        assert spec == WarpSpec()

    def test_affine_warp_returns_transform(self):
        for kind in AFFINE_WARPS:
            spec = compute_warp(kind, width=800, height=600, strength=0.5)
            assert spec.transform.startswith("matrix("), f"{kind} returned no transform"
            assert spec.filter_id is None
            assert spec.filter_defs == ""

    def test_non_affine_warp_returns_filter(self):
        for kind in (WarpKind.CYLINDER_H, WarpKind.SPHERE, WarpKind.RIPPLE, WarpKind.TWIST):
            spec = compute_warp(kind, width=800, height=600, strength=0.5)
            assert spec.transform == "", f"{kind} should not return a transform"
            assert spec.filter_id is not None
            assert "<filter" in spec.filter_defs
            assert f'id="{spec.filter_id}"' in spec.filter_defs
            assert "feDisplacementMap" in spec.filter_defs

    def test_strength_zero_is_identity(self):
        for kind in WarpKind:
            spec = compute_warp(kind, width=800, height=600, strength=0.0)
            assert spec.transform == ""
            assert spec.filter_id is None

    def test_invalid_strength_raises(self):
        with pytest.raises(ValueError):
            compute_warp(WarpKind.TILT_X, width=800, height=600, strength=-0.1)
        with pytest.raises(ValueError):
            compute_warp(WarpKind.TILT_X, width=800, height=600, strength=1.5)

    def test_invalid_size_raises(self):
        with pytest.raises(ValueError):
            compute_warp(WarpKind.TILT_X, width=0, height=600, strength=0.5)
        with pytest.raises(ValueError):
            compute_warp(WarpKind.TILT_X, width=800, height=-1, strength=0.5)

    def test_wrong_kind_type_raises(self):
        with pytest.raises(TypeError):
            compute_warp("tilt_x", width=800, height=600, strength=0.5)  # type: ignore[arg-type]

    def test_transform_scales_with_size(self):
        # tilt_x e = strength * (height/2) * 0.4 -> linear in height
        spec_400 = compute_warp(WarpKind.TILT_X, width=800, height=400, strength=1.0)
        spec_800 = compute_warp(WarpKind.TILT_X, width=800, height=800, strength=1.0)
        # Extract e from each transform
        def e_from(spec):
            inner = spec.transform[len("matrix("):-1]
            parts = inner.split()
            return float(parts[4])
        assert e_from(spec_800) == pytest.approx(2 * e_from(spec_400))

    def test_filter_defs_have_unique_ids(self):
        a = compute_warp(WarpKind.RIPPLE, width=800, height=600, strength=0.5)
        b = compute_warp(WarpKind.TWIST, width=800, height=600, strength=0.5)
        assert a.filter_id != b.filter_id

    def test_all_warps_produce_different_filter_defs(self):
        """Regression: the 5 non-affine warps must produce *visibly
        different* displacement fields. If they all produce the same
        bytes, every warp will render identically in the browser.
        """
        kinds = [WarpKind.RIPPLE, WarpKind.TWIST, WarpKind.SPHERE,
                 WarpKind.CYLINDER_H, WarpKind.CYLINDER_V]
        defs = {k: compute_warp(k, width=800, height=600, strength=0.5).filter_defs
                for k in kinds}
        for a in kinds:
            for b in kinds:
                if a >= b: continue
                assert defs[a] != defs[b], (
                    f"{a.value} and {b.value} produce identical filter defs"
                )


# ---------------------------------------------------------------------------
# Non-affine PNG generation: correctness regression tests
# ---------------------------------------------------------------------------

class TestNonAffinePngs:
    """Regression tests for the displacement-map PNGs.

    An earlier bug had the PNG IDAT stream missing per-row filter
    bytes. PNG decoders tolerate this on 1-row PNGs but produce a
    garbled image on multi-row PNGs (sphere, twist), which made
    every non-affine warp produce the same output. These tests
    catch the regression by decoding the PNGs back to raw RGBA
    bytes and asserting that the fields are non-trivial.
    """

    @staticmethod
    def _decode_png_rgba(png: bytes) -> tuple:
        """Decode a minimal RGBA PNG back to (width, height, raw_rgba).

        Expects the PNG to follow the spec: each scanline prefixed
        with a 0 filter byte.
        """
        import struct
        import zlib
        data = png[8:]
        width = height = 0
        idat = bytearray()
        while data:
            length = struct.unpack(">I", data[:4])[0]
            typ = data[4:8]
            chunk = data[8:8 + length]
            data = data[8 + length + 4:]
            if typ == b"IHDR":
                width, height, _bd, _ct = struct.unpack(">IIBB", chunk[:10])
            elif typ == b"IDAT":
                idat.extend(chunk)
        decompressed = zlib.decompress(bytes(idat))
        row_bytes = width * 4
        raw = bytearray()
        for j in range(height):
            start = j * (1 + row_bytes) + 1  # +1 to skip filter byte
            raw.extend(decompressed[start:start + row_bytes])
        return width, height, bytes(raw)

    def test_ripple_png_is_multicoloured(self):
        from subtle_patterns.core.warp import _ripple_png
        w, h, raw = self._decode_png_rgba(_ripple_png())
        assert (w, h) == (64, 1)
        r_values = {raw[i * 4] for i in range(w)}
        assert len(r_values) >= 16, f"ripple R has only {len(r_values)} distinct values"
        assert max(r_values) - min(r_values) >= 100

    def test_twist_png_has_2d_variation(self):
        from subtle_patterns.core.warp import _twist_png
        w, h, raw = self._decode_png_rgba(_twist_png())
        assert (w, h) == (32, 32)
        # y-variation: G changes row-to-row
        g_first = [raw[i * 4 + 1] for i in range(w)]
        g_last = [raw[(h - 1) * w * 4 + i * 4 + 1] for i in range(w)]
        assert g_first != g_last, "twist PNG has no y-variation"
        # x-variation: G changes column-to-column within a row
        first_col = [raw[j * w * 4 + 1] for j in range(h)]
        last_col = [raw[j * w * 4 + (w - 1) * 4 + 1] for j in range(h)]
        assert first_col != last_col, "twist PNG has no x-variation"

    def test_sphere_png_has_radial_variation(self):
        from subtle_patterns.core.warp import _sphere_png
        w, h, raw = self._decode_png_rgba(_sphere_png())
        assert (w, h) == (32, 32)
        r_values = {raw[i * 4] for i in range(w * h)}
        g_values = {raw[i * 4 + 1] for i in range(w * h)}
        assert len(r_values) >= 8, f"sphere R has only {len(r_values)} distinct values"
        assert len(g_values) >= 8, f"sphere G has only {len(g_values)} distinct values"
        assert max(r_values) - min(r_values) >= 50
        assert max(g_values) - min(g_values) >= 50

    def test_cylinder_h_png_varies_along_y(self):
        from subtle_patterns.core.warp import _cylinder_h_png
        w, h, raw = self._decode_png_rgba(_cylinder_h_png())
        assert (w, h) == (1, 48)
        g_values = [raw[j * 4 + 1] for j in range(h)]
        # The cylinder_h field is a parabola: max deviation at the
        # centre, zero at the edges. So first/last rows match but the
        # centre should differ from the edges.
        assert len(set(g_values)) >= 16, "cylinder_h G channel is too uniform"
        centre = h // 2
        assert abs(g_values[centre] - g_values[0]) >= 50, (
            f"cylinder_h centre-to-edge variation = {abs(g_values[centre] - g_values[0])}"
        )

    def test_cylinder_v_png_varies_along_x(self):
        from subtle_patterns.core.warp import _cylinder_v_png
        w, h, raw = self._decode_png_rgba(_cylinder_v_png())
        assert (w, h) == (64, 1)
        r_values = [raw[i * 4] for i in range(w)]
        assert len(set(r_values)) >= 16, "cylinder_v R channel is too uniform"

    def test_all_non_affine_pngs_are_distinct(self):
        """A critical regression: the 5 non-affine warps must produce
        distinct PNG bytes. If they don't, every warp will produce
        the same visual output.
        """
        from subtle_patterns.core.warp import (
            _ripple_png, _twist_png, _sphere_png,
            _cylinder_h_png, _cylinder_v_png,
        )
        pngs = {
            "ripple": _ripple_png(),
            "twist": _twist_png(),
            "sphere": _sphere_png(),
            "cylinder_h": _cylinder_h_png(),
            "cylinder_v": _cylinder_v_png(),
        }
        for a_name, a_png in pngs.items():
            for b_name, b_png in pngs.items():
                if a_name >= b_name:
                    continue
                assert a_png != b_png, (
                    f"{a_name} and {b_name} PNGs are byte-identical; "
                    "the corresponding warps will produce the same output"
                )

    def test_pngs_have_correct_filter_bytes(self):
        """Each scanline must be prefixed with a 0 filter byte.

        A missing filter byte was the root cause of an earlier bug
        where every non-affine warp produced identical output.
        """
        import struct
        import zlib
        from subtle_patterns.core.warp import (
            _ripple_png, _twist_png, _sphere_png,
            _cylinder_h_png, _cylinder_v_png,
        )
        for png_name, png_bytes in [
            ("ripple", _ripple_png()),
            ("twist", _twist_png()),
            ("sphere", _sphere_png()),
            ("cylinder_h", _cylinder_h_png()),
            ("cylinder_v", _cylinder_v_png()),
        ]:
            data = png_bytes[8:]
            width = height = 0
            idat = bytearray()
            while data:
                length = struct.unpack(">I", data[:4])[0]
                typ = data[4:8]
                chunk = data[8:8 + length]
                data = data[8 + length + 4:]
                if typ == b"IHDR":
                    width, height = struct.unpack(">II", chunk[:8])
                elif typ == b"IDAT":
                    idat.extend(chunk)
            raw = zlib.decompress(bytes(idat))
            row_bytes = width * 4
            expected = height * (1 + row_bytes)
            assert len(raw) == expected, (
                f"{png_name}: IDAT has {len(raw)} bytes, expected {expected} "
                f"({height} rows × (1 filter byte + {row_bytes} RGBA bytes))"
            )


# ---------------------------------------------------------------------------
# PatternConfig integration
# ---------------------------------------------------------------------------

class TestPatternConfigWarp:
    def test_default_is_none_zero_three(self):
        cfg = PatternConfig(family="grid")
        assert cfg.warp is WarpKind.NONE
        assert cfg.warp_strength == pytest.approx(0.3)

    def test_warp_string_coerced(self):
        cfg = PatternConfig(family="grid", warp="ripple")
        assert cfg.warp is WarpKind.RIPPLE

    def test_invalid_warp_string_raises(self):
        with pytest.raises(ValueError):
            PatternConfig(family="grid", warp="not-a-warp")

    def test_warp_strength_clamps_low(self):
        with pytest.raises(ValueError):
            PatternConfig(family="grid", warp_strength=-0.1)

    def test_warp_strength_clamps_high(self):
        with pytest.raises(ValueError):
            PatternConfig(family="grid", warp_strength=1.5)

    def test_to_dict_round_trip(self):
        cfg = PatternConfig(family="grid", warp="tilt_x", warp_strength=0.5)
        d = cfg.to_dict()
        assert d["warp"] == "tilt_x"
        assert d["warp_strength"] == pytest.approx(0.5)
        # Round-trip through from_dict
        cfg2 = PatternConfig.from_dict(d)
        assert cfg2.warp is WarpKind.TILT_X
        assert cfg2.warp_strength == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Engine: rendered output
# ---------------------------------------------------------------------------

class TestEngineWarp:
    def _render_grid(self, **warp_kwargs):
        return render_pattern(
            {"family": "grid", "stroke": "#1d4d80", "stroke_opacity": 0.4,
             "spacing": 40, "thickness": 1, **warp_kwargs},
            size=(800, 600), seed=42,
        )

    def test_no_warp_no_transform_no_filter(self):
        svg = self._render_grid()
        assert "transform=" not in svg
        assert "<filter" not in svg
        assert 'filter="' not in svg

    def test_affine_warp_emits_transform(self):
        svg = self._render_grid(warp="tilt_x", warp_strength=0.5)
        assert 'transform="matrix(' in svg

    def test_non_affine_warp_emits_filter(self):
        svg = self._render_grid(warp="ripple", warp_strength=0.5)
        assert "<filter " in svg
        assert 'filter="url(#sp-warp-ripple)"' in svg
        assert "<feDisplacementMap" in svg

    def test_all_warps_produce_valid_xml(self):
        # Each warp should produce parseable XML, regardless of the
        # browser's ability to render the filter.
        for kind in WarpKind:
            for strength in (0.0, 0.5):
                svg = self._render_grid(warp=kind.value, warp_strength=strength)
                # Must parse without error.
                ET.fromstring(svg)

    def test_zero_strength_emits_no_overhead(self):
        # strength=0 should be a true no-op (no transform, no filter).
        svg = self._render_grid(warp="tilt_x", warp_strength=0.0)
        assert "transform=" not in svg
        assert "<filter" not in svg

    def test_multiple_warped_layers_share_defs(self):
        # Two layers, both with filters, should emit exactly one warp-
        # specific <defs> block (with id="sp-warp-defs"), regardless of
        # any per-pattern <defs> for symbols.
        cfg = {
            "layers": [
                {"family": "grid", "stroke": "#1d4d80", "stroke_opacity": 0.2,
                 "spacing": 40, "warp": "ripple", "warp_strength": 0.3},
                {"family": "dot_grid", "fill": "#1d4d80", "fill_opacity": 0.3,
                 "spacing": 40, "radius": 2, "warp": "twist", "warp_strength": 0.3},
            ],
            "width": 800, "height": 600,
        }
        svg = render_overlay(cfg, seed=42)
        # Exactly one warp-defs wrapper.
        assert svg.count('id="sp-warp-defs"') == 1
        # Both filters are inside it.
        assert "sp-warp-ripple" in svg
        assert "sp-warp-twist" in svg
        # Both layers reference their respective filter.
        assert svg.count('filter="url(#sp-warp-ripple)"') == 1
        assert svg.count('filter="url(#sp-warp-twist)"') == 1

    def test_warps_dont_break_determinism(self):
        # The same config + seed must produce byte-identical output.
        kwargs = {"warp": "tilt_x", "warp_strength": 0.4}
        a = self._render_grid(**kwargs)
        b = self._render_grid(**kwargs)
        assert a == b

    def test_different_strengths_produce_different_output(self):
        a = self._render_grid(warp="tilt_x", warp_strength=0.2)
        b = self._render_grid(warp="tilt_x", warp_strength=0.8)
        assert a != b

    def test_warp_does_not_affect_seed_stream(self):
        # The warp should be applied AFTER the pattern draws; the per-
        # layer RNG stream should not change. We verify this by checking
        # that the pattern's *output* (the number of <line> elements
        # in the grid) is identical with and without the warp.
        without = self._render_grid()
        with_warp = self._render_grid(warp="tilt_xy", warp_strength=0.5)
        # Same number of <line> elements inside the layer's <g>.
        def line_count(svg: str) -> int:
            return svg.count("<line ")
        assert line_count(without) == line_count(with_warp)
