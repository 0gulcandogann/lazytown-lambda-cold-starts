
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

RESET = "\033[0m"
BOLD = "\033[1m"
BLUE = "\033[38;5;39m"
CYAN = "\033[38;5;45m"
GREEN = "\033[38;5;82m"
YELLOW = "\033[38;5;220m"
ORANGE = "\033[38;5;208m"
MAGENTA = "\033[38;5;213m"
GRAY = "\033[38;5;245m"
WHITE = "\033[38;5;255m"

ORDER = ["slide08-128mb", "slide08-512mb", "slide08-1024mb", "slide08-1769mb"]

def c(text: str, code: str, enabled: bool) -> str:
    return f"{code}{text}{RESET}" if enabled else text

def load_rows(path: Path):
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_label = {r["label"]: r for r in rows}
    return [by_label[x] for x in ORDER if x in by_label]

def num(row, key):
    value = row.get(key, "")
    return None if value in ("", None) else float(value)

def memory_name(label: str) -> str:
    return label.replace("slide08-", "").replace("mb", " MB").upper()

def bar(value: float, max_value: float, width: int = 24) -> str:
    filled = max(1, round((value / max_value) * width))
    return "█" * filled + "░" * (width - filled)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("summary", type=Path)
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args()

    rows = load_rows(args.summary)
    if len(rows) != 4:
        raise SystemExit(
            "Slide 8 için 4 satır bekleniyor: "
            + ", ".join(ORDER)
        )

    enabled = not args.no_color and "NO_COLOR" not in os.environ

    cold_values = [num(r, "cold_total_p50_ms") for r in rows]
    max_cold = max(cold_values)

    fastest = min(rows, key=lambda r: num(r, "cold_total_p50_ms"))
    first = rows[0]
    first_cold = num(first, "cold_total_p50_ms")
    fastest_cold = num(fastest, "cold_total_p50_ms")
    improvement = (first_cold - fastest_cold) / first_cold * 100

    W = 86
    print(c("╔" + "═" * W + "╗", BLUE, enabled))
    print(
        c("║", BLUE, enabled)
        + c("  ⚡ TRAINING #3 — MEMORY TUNING".ljust(W), BOLD + WHITE, enabled)
        + c("║", BLUE, enabled)
    )
    print(c("╠" + "═" * W + "╣", BLUE, enabled))
    print(
        c("║", BLUE, enabled)
        + c(
            "  MEMORY      COLD TOTAL P50                     WARM P50      BILLED P50".ljust(W),
            GRAY,
            enabled,
        )
        + c("║", BLUE, enabled)
    )
    print(c("╠" + "═" * W + "╣", BLUE, enabled))

    colors = [CYAN, GREEN, YELLOW, ORANGE]
    for row, color in zip(rows, colors):
        mem = memory_name(row["label"])
        cold = num(row, "cold_total_p50_ms")
        warm = num(row, "warm_p50_ms")
        billed = num(row, "billed_p50_ms")
        graph = bar(cold, max_cold, 24)

        line = (
            f"  {mem:<10} "
            f"{graph}  "
            f"{cold:>8.2f} ms   "
            f"{warm:>8.2f} ms   "
            f"{billed:>8.2f} ms"
        )
        print(
            c("║", BLUE, enabled)
            + c(line.ljust(W), color, enabled)
            + c("║", BLUE, enabled)
        )

    print(c("╠" + "═" * W + "╣", BLUE, enabled))

    hero = (
        f"  128 MB → {memory_name(fastest['label'])}: "
        f"{first_cold:.2f} ms → {fastest_cold:.2f} ms   ↓ {improvement:.2f}%"
    )
    print(
        c("║", BLUE, enabled)
        + c(hero.ljust(W), BOLD + ORANGE, enabled)
        + c("║", BLUE, enabled)
    )

    fastest_line = (
        f"  FASTEST → {memory_name(fastest['label'])}  •  "
        f"Cold Total P50 {fastest_cold:.2f} ms"
    )
    print(
        c("║", BLUE, enabled)
        + c(fastest_line.ljust(W), BOLD + GREEN, enabled)
        + c("║", BLUE, enabled)
    )

    print(c("╚" + "═" * W + "╝", BLUE, enabled))

if __name__ == "__main__":
    main()
