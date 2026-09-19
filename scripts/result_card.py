#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
BLUE = "\033[38;5;39m"
CYAN = "\033[38;5;45m"
YELLOW = "\033[38;5;220m"
ORANGE = "\033[38;5;208m"
GREEN = "\033[38;5;82m"
MAGENTA = "\033[38;5;213m"
WHITE = "\033[38;5;255m"
GRAY = "\033[38;5;245m"


def paint(text: str, style: str, enabled: bool) -> str:
    return f"{style}{text}{RESET}" if enabled else text


def read_summary(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def value(row: dict, key: str) -> float | None:
    raw = row.get(key, "")
    if raw in (None, "", "None"):
        return None
    return float(raw)


def title_for(label: str) -> str:
    prefixes = [f"slide{i:02d}-" for i in range(1, 13)]
    for prefix in prefixes:
        label = label.replace(prefix, "")
    return label.replace("-", " ").upper()


def fmt(v: float | None) -> str:
    return "—" if v is None else f"{v:.2f} ms"


def ascii_bar(v: float | None, maximum: float | None, width: int = 30) -> str:
    if v is None or not maximum:
        return " " * width
    n = max(1, min(width, round((v / maximum) * width)))
    return "█" * n + "░" * (width - n)


def single_card(row: dict, colors: bool, custom_title: str | None = None) -> str:
    init = value(row, "init_p50_ms")
    cold = value(row, "cold_total_p50_ms")
    warm = value(row, "warm_p50_ms")
    p90 = value(row, "cold_total_p90_ms")
    billed = value(row, "billed_p50_ms")

    width = 58
    heading = custom_title or title_for(row["label"])
    lines = [
        paint("╔" + "═" * width + "╗", BLUE, colors),
        paint("║", BLUE, colors)
        + paint(f"  ⚡ LAZYTOWN BENCHMARK  •  {heading}".ljust(width), BOLD + WHITE, colors)
        + paint("║", BLUE, colors),
        paint("╠" + "═" * width + "╣", BLUE, colors),
        paint("║", BLUE, colors)
        + f"  Samples          {row.get('cold_n', '?')} cold  •  {row.get('warm_n', '?')} warm".ljust(width)
        + paint("║", BLUE, colors),
        paint("║", BLUE, colors) + " " * width + paint("║", BLUE, colors),
    ]

    metrics = [
        ("INIT P50", init, YELLOW),
        ("COLD TOTAL P50", cold, ORANGE + BOLD),
        ("WARM P50", warm, GREEN),
        ("COLD P90", p90, MAGENTA),
        ("BILLED P50", billed, CYAN),
    ]
    for name, v, style in metrics:
        if v is None:
            continue
        text = f"  {name:<20} {fmt(v):>13}"
        lines.append(
            paint("║", BLUE, colors)
            + paint(text.ljust(width), style, colors)
            + paint("║", BLUE, colors)
        )

    lines.extend([
        paint("║", BLUE, colors) + " " * width + paint("║", BLUE, colors),
        paint("║", BLUE, colors)
        + paint("  HERO METRIC".ljust(width), DIM + GRAY, colors)
        + paint("║", BLUE, colors),
        paint("║", BLUE, colors)
        + paint(f"  COLD TOTAL P50  →  {fmt(cold)}".ljust(width), BOLD + ORANGE, colors)
        + paint("║", BLUE, colors),
        paint("╚" + "═" * width + "╝", BLUE, colors),
    ])
    return "\n".join(lines)


def comparison_card(a: dict, b: dict, colors: bool, title: str) -> str:
    av = value(a, "cold_total_p50_ms")
    bv = value(b, "cold_total_p50_ms")
    maximum = max(v for v in (av, bv) if v is not None)
    an = title_for(a["label"])
    bn = title_for(b["label"])
    width = 82

    def line(name: str, v: float | None, style: str) -> str:
        content = f"  {name:<20} {ascii_bar(v, maximum)}  {fmt(v):>10}"
        return paint("║", BLUE, colors) + paint(content.ljust(width), style, colors) + paint("║", BLUE, colors)

    lines = [
        paint("╔" + "═" * width + "╗", BLUE, colors),
        paint("║", BLUE, colors)
        + paint(f"  🏁 {title}".ljust(width), BOLD + WHITE, colors)
        + paint("║", BLUE, colors),
        paint("╠" + "═" * width + "╣", BLUE, colors),
        line(an, av, CYAN),
        line(bn, bv, YELLOW),
    ]

    if av and bv:
        faster_name, faster, slower = (an, av, bv) if av < bv else (bn, bv, av)
        delta_ms = slower - faster
        pct = (delta_ms / slower) * 100
        lines += [
            paint("║", BLUE, colors) + " " * width + paint("║", BLUE, colors),
            paint("║", BLUE, colors)
            + paint(
                f"  {faster_name} → Δ {delta_ms:.3f} ms  •  {pct:.3f}% lower Cold Total P50".ljust(width),
                BOLD + ORANGE,
                colors,
            )
            + paint("║", BLUE, colors),
        ]

    lines.append(paint("╚" + "═" * width + "╝", BLUE, colors))
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Screenshot-friendly LazyTown benchmark cards")
    ap.add_argument("summary", type=Path)
    ap.add_argument("--label", help="Show only one benchmark label")
    ap.add_argument("--compare", help="Compare --label against a second label")
    ap.add_argument("--title", help="Custom card title")
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args()

    rows = read_summary(args.summary)
    by_label = {r["label"]: r for r in rows}
    colors = not args.no_color and "NO_COLOR" not in os.environ

    if args.label:
        if args.label not in by_label:
            raise SystemExit(f"Unknown label: {args.label}\nAvailable: {', '.join(by_label)}")
        if args.compare:
            if args.compare not in by_label:
                raise SystemExit(f"Unknown label: {args.compare}\nAvailable: {', '.join(by_label)}")
            print(comparison_card(by_label[args.label], by_label[args.compare], colors, args.title or "ROUND 1 — COLD TOTAL P50"))
        else:
            print(single_card(by_label[args.label], colors, args.title))
        return

    for i, row in enumerate(rows):
        if i:
            print()
        print(single_card(row, colors))


if __name__ == "__main__":
    main()
