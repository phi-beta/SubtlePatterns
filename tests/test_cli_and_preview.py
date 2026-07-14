"""Test the HTML preview gallery and CLI."""

from __future__ import annotations

import json
import os
import sys
from io import StringIO

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from subtle_patterns import list_presets  # noqa: E402
from subtle_patterns.cli import build_parser, main  # noqa: E402
from subtle_patterns.preview import gallery_html, write_gallery  # noqa: E402


# ---------------------------------------------------------------------------
# Gallery HTML
# ---------------------------------------------------------------------------

def test_gallery_html_includes_all_presets() -> None:
    html = gallery_html(presets=["hex_mesh", "dot_grid"], title="t")
    assert "t" in html
    assert "hex_mesh" in html
    assert "dot_grid" in html


def test_gallery_html_self_contained() -> None:
    """No external script or stylesheet links."""
    html = gallery_html(presets=["hex_mesh"], backdrop="red", columns=1, seed=0)
    assert "<script" not in html.lower()
    assert "<link " not in html.lower()
    assert "stylesheet" not in html.lower()


def test_gallery_html_strips_xml_prolog() -> None:
    """Inlined SVGs must not contain <?xml ...?> declarations."""
    html = gallery_html(presets=["hex_mesh"], columns=1, seed=0)
    assert "<?xml" not in html


def test_write_gallery(tmp_path) -> None:
    out = tmp_path / "g.html"
    path = write_gallery(
        str(out), presets=["hex_mesh"], columns=1, seed=0, title="t",
    )
    assert os.path.isfile(path)
    assert os.path.getsize(path) > 100


def test_gallery_samples_mode_includes_every_sample(tmp_path) -> None:
    """Sample mode shows one tile per (label, svg, info) entry, in order."""
    svgs = [
        ("alpha", "<svg xmlns='http://www.w3.org/2000/svg' width='1600' height='900' viewBox='0 0 1600 900'><rect/></svg>", "first"),
        ("beta",  "<svg xmlns='http://www.w3.org/2000/svg' width='1600' height='900' viewBox='0 0 1600 900'><circle/></svg>", "second"),
        ("gamma", "<svg xmlns='http://www.w3.org/2000/svg' width='1600' height='900' viewBox='0 0 1600 900'><path/></svg>", "third"),
    ]
    html = gallery_html(samples=svgs, columns=2, title="sample-mode-test")
    # All three labels present.
    for label, _, _ in svgs:
        assert label in html
    # Tile count matches.
    assert html.count('class="tile"') == 3
    # The XML prolog is stripped from inlined SVGs.
    assert "<?xml" not in html
    # Tiles are in the order given.
    pos_alpha = html.index("alpha")
    pos_beta = html.index("beta")
    pos_gamma = html.index("gamma")
    assert pos_alpha < pos_beta < pos_gamma


def test_gallery_samples_mode_resizes_svg_root() -> None:
    """The inlined <svg> width/height is replaced with the tile size."""
    samples = [("x", "<svg xmlns='http://www.w3.org/2000/svg' width='1600' height='900' viewBox='0 0 1600 900'><rect/></svg>", "")]
    html = gallery_html(samples=samples, tile_size=(480, 270), columns=1, title="t")
    # The original 1600/900 are gone, replaced with 480/270.
    assert 'width="1600"' not in html
    assert 'height="900"' not in html
    assert 'width="480"' in html
    assert 'height="270"' in html


def test_gallery_samples_mode_ignores_presets() -> None:
    """When samples is given, presets are ignored (no preset re-render)."""
    samples = [("only-sample", "<svg xmlns='http://www.w3.org/2000/svg' width='1600' height='900' viewBox='0 0 1600 900'/>", "")]
    html = gallery_html(
        samples=samples,
        presets=["hex_mesh"],  # this should be ignored
        title="t",
    )
    # Only the sample label appears; the preset name does not.
    assert "only-sample" in html
    assert "hex_mesh" not in html
    assert html.count('class="tile"') == 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_help() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--help"])


def test_cli_render_to_stdout(capsys) -> None:
    rc = main(["render", "dot_grid", "--size", "200x100", "--seed", "7"])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert "<?xml" in captured.out
    # Width attribute is formatted with up to 3 decimal places; assert on a
    # substring that's invariant to the float-formatting choice.
    assert 'width="200' in captured.out
    assert 'height="100' in captured.out


def test_cli_render_to_file(tmp_path) -> None:
    out = tmp_path / "g.svg"
    rc = main(["render", "hex_mesh", "--size", "240x160", "--seed", "1", "--out", str(out)])
    assert rc == 0
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<?xml")
    assert "<svg" in text


def test_cli_render_unknown_preset(tmp_path) -> None:
    out = tmp_path / "x.svg"
    rc = main(["render", "not-a-real-preset", "--out", str(out)])
    assert rc == 2
    assert not out.exists()


def test_cli_list_presets(capsys) -> None:
    rc = main(["list-presets"])
    captured = capsys.readouterr()
    assert rc == 0
    # The output should contain a known pattern name and a known overlay name.
    text = captured.out
    assert "hex_mesh" in text
    assert "noetroniq_network" in text


def test_cli_list_presets_json(capsys) -> None:
    rc = main(["list-presets", "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    data = json.loads(captured.out)
    assert any(d["name"] == "hex_mesh" for d in data)


def test_cli_inline(tmp_path) -> None:
    out = tmp_path / "i.svg"
    rc = main([
        "inline", "family=dot_grid;spacing=42;stroke=#0d2f57;stroke_opacity=0.2",
        "--out", str(out),
    ])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    # 42 should appear in some path coordinate.
    assert "42" in text or "stroke" in text


def test_cli_render_config_yaml(tmp_path) -> None:
    pytest.importorskip("yaml")
    cfg_path = tmp_path / "p.yaml"
    cfg_path.write_text("family: dot_grid\nspacing: 33\n")
    out = tmp_path / "p.svg"
    rc = main(["render-config", str(cfg_path), "--out", str(out)])
    assert rc == 0
    assert out.exists()


def test_cli_gallery(tmp_path) -> None:
    out = tmp_path / "g.html"
    rc = main([
        "gallery", "--include", "hex_mesh", "--include", "noetroniq_network",
        "--out", str(out), "--columns", "1", "--seed", "0",
    ])
    assert rc == 0
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "<!doctype html>" in text
    assert "hex_mesh" in text
    assert "noetroniq_network" in text
