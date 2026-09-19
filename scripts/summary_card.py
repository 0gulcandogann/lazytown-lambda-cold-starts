#!/usr/bin/env python3

import argparse
import csv
import re
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────
# ANSI COLORS
# ─────────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

BLACK = "\033[30m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
GRAY = "\033[90m"


def paint(text, *styles):
    return "".join(styles) + str(text) + RESET


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def normalize(value):
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def fnum(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fmt_ms(value):
    return f"{fnum(value):,.2f} ms"


def fmt_ratio(cold, warm):
    cold = fnum(cold)
    warm = fnum(warm)

    if warm <= 0:
        return "-"

    return f"{cold / warm:,.1f}x"


def fmt_gap(cold, warm):
    return f"{fnum(cold) - fnum(warm):,.2f} ms"


def get_field(row, *aliases):
    normalized_row = {
        normalize(key): value
        for key, value in row.items()
        if key is not None
    }

    for alias in aliases:
        key = normalize(alias)

        if key in normalized_row:
            return normalized_row[key]

    return ""


def parsed_row(row):
    return {
        "label": get_field(
            row,
            "label",
            "name",
        ),

        "cold_n": get_field(
            row,
            "cold_n",
            "cold n",
            "cold_count",
            "cold_samples",
        ),

        "warm_n": get_field(
            row,
            "warm_n",
            "warm n",
            "warm_count",
            "warm_samples",
        ),

        "init_p50": get_field(
            row,
            "init_p50",
            "init p50",
            "init_p50_ms",
        ),

        "cold_total_p50": get_field(
            row,
            "cold_total_p50",
            "cold total p50",
            "cold_total_p50_ms",
            "cold_p50",
        ),

        "warm_p50": get_field(
            row,
            "warm_p50",
            "warm p50",
            "warm_p50_ms",
        ),

        "cold_p90": get_field(
            row,
            "cold_p90",
            "cold p90",
            "cold_p90_ms",
            "cold_total_p90",
            "cold_total_p90_ms",
            "p90_cold",
            "p90_cold_ms",
        ),
    }


# ─────────────────────────────────────────────────────────────
# FINAL RACE ORDER
# ─────────────────────────────────────────────────────────────

def final_race_order(row):
    label = row["label"].lower()

    if "python-baseline" in label:
        return 1

    if "python-arm64" in label:
        return 2

    if "python-optimized" in label:
        return 3

    if label.endswith("-go") or "slide10-go" in label:
        return 4

    return 99


# ─────────────────────────────────────────────────────────────
# ROW COLOR
# ─────────────────────────────────────────────────────────────

def row_color(label):
    label = label.lower()

    if "python-baseline" in label:
        return MAGENTA

    if "python-arm64" in label:
        return YELLOW

    if "python-optimized" in label:
        return CYAN

    if label.endswith("-go") or "slide10-go" in label:
        return GREEN

    return WHITE


# ─────────────────────────────────────────────────────────────
# TABLE
# ─────────────────────────────────────────────────────────────

def render_table(rows, title):

    headers = [
        "LABEL",
        "COLD",
        "WARM",
        "INIT P50",
        "COLD TOTAL P50",
        "WARM P50",
        "COLD P90",
        "COLD-WARM",
        "RATIO",
    ]

    data = []

    for row in rows:
        cold_total = fnum(row["cold_total_p50"])
        warm = fnum(row["warm_p50"])

        data.append([
            row["label"],
            row["cold_n"],
            row["warm_n"],
            fmt_ms(row["init_p50"]),
            fmt_ms(cold_total),
            fmt_ms(warm),
            fmt_ms(row["cold_p90"]),
            fmt_gap(cold_total, warm),
            fmt_ratio(cold_total, warm),
        ])

    # ─────────────────────────────────────────────────────────
    # WIDTHS
    # ─────────────────────────────────────────────────────────

    widths = []

    for index, header in enumerate(headers):
        width = len(header)

        for row in data:
            width = max(
                width,
                len(str(row[index]))
            )

        widths.append(width + 2)

    def border(left, middle, right, fill="─"):
        return (
            left
            + middle.join(
                fill * width
                for width in widths
            )
            + right
        )

    def row_line(values):
        cells = []

        for index, value in enumerate(values):
            value = str(value)
            inner_width = widths[index] - 2

            if index == 0:
                cells.append(
                    f" {value:<{inner_width}} "
                )
            else:
                cells.append(
                    f" {value:>{inner_width}} "
                )

        return "│" + "│".join(cells) + "│"

    table_width = (
        sum(widths)
        + len(widths)
        + 1
    )

    # ─────────────────────────────────────────────────────────
    # TITLE
    # ─────────────────────────────────────────────────────────

    print()

    print(
        paint(
            "╔"
            + "═" * (table_width - 2)
            + "╗",
            CYAN,
        )
    )

    title_text = f" {title} "

    available = table_width - 2

    if len(title_text) > available:
        title_text = title_text[:available]

    padding = available - len(title_text)

    left_padding = padding // 2
    right_padding = padding - left_padding

    title_line = (
        "║"
        + " " * left_padding
        + title_text
        + " " * right_padding
        + "║"
    )

    print(
        paint(
            title_line,
            BOLD,
            CYAN,
        )
    )

    print(
        paint(
            "╚"
            + "═" * (table_width - 2)
            + "╝",
            CYAN,
        )
    )

    print()

    # ─────────────────────────────────────────────────────────
    # TABLE HEADER
    # ─────────────────────────────────────────────────────────

    print(
        paint(
            border("┌", "┬", "┐"),
            CYAN,
        )
    )

    print(
        paint(
            row_line(headers),
            BOLD,
            YELLOW,
        )
    )

    print(
        paint(
            border(
                "├",
                "┼",
                "┤",
                "═",
            ),
            CYAN,
        )
    )

    # ─────────────────────────────────────────────────────────
    # TABLE ROWS
    # ─────────────────────────────────────────────────────────

    for index, values in enumerate(data):

        label = values[0]
        color = row_color(label)

        # Whole row receives same color.
        # Alignment remains correct because ANSI codes
        # are added AFTER the row string is created.
        print(
            paint(
                row_line(values),
                color,
            )
        )

        if index != len(data) - 1:
            print(
                paint(
                    border(
                        "├",
                        "┼",
                        "┤",
                    ),
                    GRAY,
                    DIM,
                )
            )

    print(
        paint(
            border("└", "┴", "┘"),
            CYAN,
        )
    )

    # ─────────────────────────────────────────────────────────
    # BENCHMARK SUMMARY
    # ─────────────────────────────────────────────────────────

    total_cold = sum(
        int(fnum(row["cold_n"]))
        for row in rows
    )

    total_warm = sum(
        int(fnum(row["warm_n"]))
        for row in rows
    )

    total = total_cold + total_warm

    print()

    print(
        paint(
            " BENCHMARK SUMMARY",
            BOLD,
            CYAN,
        )
        + paint(
            f"  •  Variants: {len(rows)}",
            WHITE,
        )
        + paint(
            f"  •  Cold: {total_cold}",
            MAGENTA,
        )
        + paint(
            f"  •  Warm: {total_warm}",
            GREEN,
        )
        + paint(
            f"  •  Total Invocations: {total}",
            WHITE,
        )
    )

    # ─────────────────────────────────────────────────────────
    # FASTEST
    # ─────────────────────────────────────────────────────────

    valid_rows = [
        row
        for row in rows
        if fnum(row["cold_total_p50"]) > 0
    ]

    if valid_rows:

        fastest = min(
            valid_rows,
            key=lambda row: fnum(
                row["cold_total_p50"]
            )
        )

        slowest = max(
            valid_rows,
            key=lambda row: fnum(
                row["cold_total_p50"]
            )
        )

        fastest_ms = fnum(
            fastest["cold_total_p50"]
        )

        slowest_ms = fnum(
            slowest["cold_total_p50"]
        )

        print()

        print(
            paint(
                " FASTEST",
                BOLD,
                GREEN,
            )
            + paint(
                "  →  ",
                WHITE,
            )
            + paint(
                fastest["label"],
                BOLD,
                GREEN,
            )
            + paint(
                f"  •  {fastest_ms:,.2f} ms",
                GREEN,
            )
        )

    # ─────────────────────────────────────────────────────────
    # SLIDE 10 SPECIAL SUMMARY
    # ─────────────────────────────────────────────────────────

    labels = {
        row["label"]: row
        for row in rows
    }

    baseline = next(
        (
            row
            for row in rows
            if "python-baseline"
            in row["label"].lower()
        ),
        None,
    )

    optimized = next(
        (
            row
            for row in rows
            if "python-optimized"
            in row["label"].lower()
        ),
        None,
    )

    go_row = next(
        (
            row
            for row in rows
            if row["label"].lower().endswith("-go")
            or "slide10-go"
            in row["label"].lower()
        ),
        None,
    )

    if baseline and optimized:

        baseline_ms = fnum(
            baseline["cold_total_p50"]
        )

        optimized_ms = fnum(
            optimized["cold_total_p50"]
        )

        if baseline_ms > 0:

            python_gain = (
                (
                    baseline_ms
                    - optimized_ms
                )
                / baseline_ms
            ) * 100

            print(
                paint(
                    " PYTHON GAIN",
                    BOLD,
                    CYAN,
                )
                + paint(
                    f"  →  {baseline_ms:,.2f} ms",
                    MAGENTA,
                )
                + paint(
                    "  →  ",
                    WHITE,
                )
                + paint(
                    f"{optimized_ms:,.2f} ms",
                    CYAN,
                )
                + paint(
                    f"  •  ↓ {python_gain:.2f}%",
                    BOLD,
                    CYAN,
                )
            )

    if optimized and go_row:

        optimized_ms = fnum(
            optimized["cold_total_p50"]
        )

        go_ms = fnum(
            go_row["cold_total_p50"]
        )

        delta = optimized_ms - go_ms

        print(
            paint(
                " FINAL GAP",
                BOLD,
                YELLOW,
            )
            + paint(
                "  →  Python ",
                WHITE,
            )
            + paint(
                f"{optimized_ms:,.2f} ms",
                CYAN,
            )
            + paint(
                "  vs  Go ",
                WHITE,
            )
            + paint(
                f"{go_ms:,.2f} ms",
                GREEN,
            )
            + paint(
                f"  •  Δ {delta:,.2f} ms",
                BOLD,
                YELLOW,
            )
        )

    print()


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Render Lambda benchmark results "
            "as a colored terminal card."
        )
    )

    parser.add_argument(
        "csv_file",
        nargs="?",
        default="results/summary.csv",
        help="Path to summary.csv",
    )

    parser.add_argument(
        "--filter",
        default=None,
        help=(
            "Only display labels containing text. "
            "Example: --filter slide10-"
        ),
    )

    parser.add_argument(
        "--title",
        default=(
            "LAZYTOWN - FULL BENCHMARK RESULTS"
        ),
        help="Card title",
    )

    args = parser.parse_args()

    path = Path(args.csv_file)

    if not path.exists():
        print(
            f"ERROR: {path} not found.",
            file=sys.stderr,
        )
        sys.exit(1)

    with path.open(
        newline="",
        encoding="utf-8-sig",
    ) as file:

        reader = csv.DictReader(file)
        raw_rows = list(reader)

    if not raw_rows:
        print("No benchmark data found.")
        sys.exit(1)

    rows = [
        parsed_row(row)
        for row in raw_rows
    ]

    rows = [
        row
        for row in rows
        if row["label"]
    ]

    if args.filter:

        search = args.filter.lower()

        rows = [
            row
            for row in rows
            if search
            in row["label"].lower()
        ]

    if not rows:
        print(
            f"No rows matched filter: "
            f"{args.filter!r}"
        )
        sys.exit(1)

    # For Slide 10, show the story in logical order:
    # Baseline -> ARM64 -> Optimized -> Go
    if any(
        "slide10-" in row["label"].lower()
        for row in rows
    ):
        rows.sort(
            key=final_race_order
        )

    render_table(
        rows,
        args.title,
    )


if __name__ == "__main__":
    main()
