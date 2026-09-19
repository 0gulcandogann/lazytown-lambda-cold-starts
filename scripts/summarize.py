#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
import statistics
import subprocess
import sys

def number(v):
    if v in ("", None, "None"):
        return None
    return float(v)

def p90(values):
    vals = sorted(values)
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    return statistics.quantiles(vals, n=100, method="inclusive")[89]

def fmt(v):
    return "" if v is None else f"{v:.2f}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("--csv", type=Path, default=Path("results/summary.csv"))
    ap.add_argument("--md", type=Path, default=Path("results/summary.md"))
    ap.add_argument("--pretty", action="store_true", help="Print screenshot-friendly terminal cards")
    ap.add_argument("--pretty-label", help="With --pretty, show only this label")
    args = ap.parse_args()

    groups = defaultdict(list)
    with args.input.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            groups[row["label"]].append(row)

    summary = []
    for label, rows in sorted(groups.items()):
        cold = [r for r in rows if r["run_type"] == "cold"]
        warm = [r for r in rows if r["run_type"] == "warm"]

        init = [number(r["init_ms"]) for r in cold if number(r["init_ms"]) is not None]
        cold_total = [number(r["cold_total_ms"]) for r in cold if number(r["cold_total_ms"]) is not None]
        warm_duration = [number(r["duration_ms"]) for r in warm if number(r["duration_ms"]) is not None]
        billed = [number(r["billed_ms"]) for r in rows if number(r["billed_ms"]) is not None]
        client = [number(r["client_ms"]) for r in rows if number(r["client_ms"]) is not None]

        summary.append({
            "label": label,
            "cold_n": len(cold),
            "warm_n": len(warm),
            "init_p50_ms": statistics.median(init) if init else None,
            "init_p90_ms": p90(init),
            "cold_total_p50_ms": statistics.median(cold_total) if cold_total else None,
            "cold_total_p90_ms": p90(cold_total),
            "warm_p50_ms": statistics.median(warm_duration) if warm_duration else None,
            "warm_p90_ms": p90(warm_duration),
            "billed_p50_ms": statistics.median(billed) if billed else None,
            "client_p50_ms": statistics.median(client) if client else None,
        })

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    fields = list(summary[0].keys()) if summary else []
    with args.csv.open("w", newline="", encoding="utf-8") as f:
        if fields:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(summary)

    md = [
        "| Label | Cold n | Warm n | Init P50 | Cold Total P50 | Warm P50 | Cold P90 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary:
        md.append(
            f"| {r['label']} | {r['cold_n']} | {r['warm_n']} | "
            f"{fmt(r['init_p50_ms'])} | {fmt(r['cold_total_p50_ms'])} | "
            f"{fmt(r['warm_p50_ms'])} | {fmt(r['cold_total_p90_ms'])} |"
        )

    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"Wrote {args.csv}")
    print(f"Wrote {args.md}")

    if args.pretty:
        cmd = [sys.executable, str(Path(__file__).with_name("result_card.py")), str(args.csv)]
        if args.pretty_label:
            cmd += ["--label", args.pretty_label]
        subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
