from PIL import Image

from panels import bar_panel, code_panel, table_panel


def test_bar_panel_size_and_mode(tmp_path):
    p = bar_panel("ROUND 1 — COLD TOTAL P50", [("PYTHON", 65.6), ("GO", 54.3)], ["GO → faster"],
                  tmp_path / "b.png", width=1220)
    im = Image.open(p)
    assert im.size[0] == 1220 and im.mode == "RGBA"


def test_code_panel_highlights_marked_line(tmp_path):
    p = code_panel(["import json", "lazy import pandas as pd"], tmp_path / "c.png", highlight={1}, width=900)
    assert Image.open(p).size[0] == 900


def test_table_panel(tmp_path):
    p = table_panel("SIMPLE", ["Variant", "Cold P50"], [["Eager", "1.0 ms"]], tmp_path / "t.png", width=800)
    assert Image.open(p).size[0] == 800


def test_font_scale_makes_taller_panel(tmp_path):
    a = Image.open(bar_panel("T", [("A", 1.0)], ["f"], tmp_path / "a.png", width=600))
    b = Image.open(bar_panel("T", [("A", 1.0)], ["f"], tmp_path / "b.png", width=600, font_scale=1.6))
    assert b.size[1] > a.size[1] * 1.4
