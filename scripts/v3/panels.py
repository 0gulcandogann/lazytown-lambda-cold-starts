#!/usr/bin/env python3
"""Terminal-style PNG panels matching the LazyTown deck (dark, mono, cyan/gold/orange/green)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Bold.ttf"
BG = (11, 13, 20, 255)
BORDER = (40, 110, 200, 255)
TEXT = (200, 205, 215, 255)
DIM = (130, 135, 150, 255)
CYAN, GOLD, ORANGE, GREEN, RED = (0, 153, 181), (179, 149, 0), (192, 96, 15), (76, 175, 26), (220, 60, 50)
PALETTE = [CYAN, GOLD, GREEN, ORANGE, (150, 90, 200), RED]
KW = {"import", "def", "return", "if", "lazy", "from", "as", "for", "in"}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size)


def _frame(d: ImageDraw.ImageDraw, w: int, h: int, s: int) -> None:
    d.rectangle([s, s, w - s - 1, h - s - 1], outline=BORDER, width=max(2, s // 2))


def bar_panel(title: str, rows: list[tuple[str, float]], footer: list[str], out: Path,
              width: int = 1220, unit: str = "ms", colors: list | None = None,
              footer_colors: list | None = None) -> Path:
    s = width / 610
    fs, pad, rh = int(15 * s), int(14 * s), int(24 * s)
    th = int(46 * s)
    h = th + pad + rh * len(rows) + pad + (int(26 * s) * len(footer)) + pad
    im = Image.new("RGBA", (width, h), BG)
    d = ImageDraw.Draw(im)
    _frame(d, width, h, int(4 * s))
    d.text((pad + int(6 * s), th // 2), title, font=_font(fs, True), fill=TEXT, anchor="lm")
    d.line([int(4 * s), th, width - int(4 * s), th], fill=BORDER, width=max(2, int(s)))
    label_w, val_w = int(180 * s), int(130 * s)
    bar_x0, bar_x1 = pad + label_w, width - pad - val_w
    vmax = max(v for _, v in rows) or 1
    colors = colors or PALETTE
    y = th + pad
    for i, (label, v) in enumerate(rows):
        c = colors[i % len(colors)]
        d.text((pad + int(6 * s), y + rh // 2), label, font=_font(fs), fill=c, anchor="lm")
        x = bar_x0 + max(int(3 * s), int((bar_x1 - bar_x0) * v / vmax))
        d.rectangle([bar_x0, y + int(3 * s), x, y + rh - int(3 * s)], fill=c)
        d.text((width - pad, y + rh // 2), f"{v:,.2f} {unit}", font=_font(fs), fill=c, anchor="rm")
        y += rh
    y += pad
    if footer:
        d.line([int(4 * s), y - pad // 2, width - int(4 * s), y - pad // 2], fill=BORDER, width=max(2, int(s)))
    for i, line in enumerate(footer):
        fc = (footer_colors or [ORANGE, GREEN, CYAN])[i % 3]
        d.text((pad + int(6 * s), y + int(13 * s)), line, font=_font(fs, True), fill=fc, anchor="lm")
        y += int(26 * s)
    im.save(out)
    return out


def _code_tokens(line: str):
    import re
    for tok in re.findall(r'\s+|"[^"]*"|#.*|\w+|[^\w\s]', line):
        if tok.startswith("#"):
            yield tok, DIM
        elif tok.startswith('"'):
            yield tok, (152, 195, 121)
        elif tok in KW:
            yield tok, (198, 120, 221)
        elif tok.isdigit():
            yield tok, (209, 154, 102)
        else:
            yield tok, TEXT


def code_panel(lines: list[str], out: Path, highlight: set[int] = frozenset(), width: int = 900,
               size: int = 26, title: str | None = None) -> Path:
    f = _font(size)
    lh, pad = int(size * 1.55), int(size * 0.9)
    th = int(size * 2) if title else 0
    h = th + pad * 2 + lh * len(lines)
    im = Image.new("RGBA", (width, h), (24, 27, 40, 255))
    d = ImageDraw.Draw(im)
    if title:
        d.text((pad, th // 2), title, font=_font(int(size * 0.8), True), fill=DIM, anchor="lm")
    y = th + pad
    for i, line in enumerate(lines):
        x = pad
        if i in highlight:
            w = int(d.textlength(line.strip(), font=f))
            ind = int(d.textlength(line[: len(line) - len(line.lstrip())], font=f))
            d.rectangle([x + ind - 6, y - 4, x + ind + w + 6, y + lh - 8], outline=(255, 192, 0), width=3)
        for tok, c in _code_tokens(line):
            d.text((x, y), tok, font=f, fill=c)
            x += d.textlength(tok, font=f)
        y += lh
    im.save(out)
    return out


def table_panel(title: str, header: list[str], rows: list[list[str]], out: Path, width: int = 800,
                size: int = 22, footer: str | None = None, row_colors: list | None = None) -> Path:
    f, fb = _font(size), _font(size, True)
    lh, pad = int(size * 1.7), int(size * 0.9)
    ncol = len(header)
    first = int(width * 0.42)
    rest = (width - 2 * pad - first) / max(1, ncol - 1)
    xs = [pad] + [pad + first + rest * i for i in range(ncol - 1)]
    h = pad + lh * (2 + len(rows)) + (lh if footer else 0) + pad
    im = Image.new("RGBA", (width, h), BG)
    d = ImageDraw.Draw(im)
    _frame(d, width, h, 4)
    y = pad
    d.text((width // 2, y + lh // 2), title, font=fb, fill=TEXT, anchor="mm")
    y += lh
    for i, col in enumerate(header):
        d.text((xs[i] + (0 if i == 0 else rest - pad), y + lh // 2), col, font=fb, fill=DIM,
               anchor="lm" if i == 0 else "rm")
    y += lh
    d.line([pad, y, width - pad, y], fill=BORDER, width=2)
    for r, row in enumerate(rows):
        c = (row_colors or [TEXT])[r % len(row_colors or [TEXT])]
        for i, cell in enumerate(row):
            d.text((xs[i] + (0 if i == 0 else rest - pad), y + lh // 2), cell, font=f, fill=c,
                   anchor="lm" if i == 0 else "rm")
        y += lh
    if footer:
        d.text((width // 2, y + lh // 2), footer, font=fb, fill=GREEN, anchor="mm")
    im.save(out)
    return out
