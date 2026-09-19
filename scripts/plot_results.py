#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path
import matplotlib.pyplot as plt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("summary", type=Path)
    ap.add_argument("--output", type=Path, default=Path("results/cold-p50.png"))
    ap.add_argument("--title", default="Cold Total P50")
    args = ap.parse_args()

    labels, values = [], []
    with args.summary.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            value = row.get("cold_total_p50_ms", "")
            if value:
                labels.append(row["label"])
                values.append(float(value))

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(labels, values)
    ax.set_ylabel("ms")
    ax.set_title(args.title)
    ax.tick_params(axis="x", rotation=20)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.1f} ms",
            ha="center",
            va="bottom",
        )

    fig.tight_layout()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180)
    print(f"Wrote {args.output}")

if __name__ == "__main__":
    main()
