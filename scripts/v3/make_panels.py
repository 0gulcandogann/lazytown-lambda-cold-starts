#!/usr/bin/env python3
"""Render every deck panel from results-v3/summary.csv (no hand-typed numbers)."""
from __future__ import annotations

import csv
import re
from pathlib import Path

from panels import CYAN, GOLD, GREEN, ORANGE, RED, bar_panel, code_panel, table_panel

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results-v3"
OUT = RES / "panels"


def load() -> dict[str, dict[str, float]]:
    out = {}
    for r in csv.DictReader((RES / "summary.csv").open()):
        out[r["label"]] = {k: float(v) for k, v in r.items() if k != "label" and v}
    return out


def pct(a: float, b: float) -> str:
    return f"{100 * (a - b) / a:.2f}%"


def warm_gb_ms() -> dict[int, float]:
    import statistics
    rows = list(csv.DictReader((RES / "raw.csv").open()))
    out = {}
    for m in (128, 512, 1024, 1769):
        billed = [float(r["billed_ms"]) for r in rows if r["label"] == f"sha-{m}-sha" and r["run_type"] == "warm"]
        out[m] = statistics.median(billed) * m / 1024
    return out


def importtime_top() -> tuple[float, float, int]:
    """(pandas cumulative ms, other top-level imports ms, module count) from the Lambda log."""
    pandas = other = 0.0
    n = 0
    for line in (RES / "importtime-raw.txt").read_text().splitlines():
        m = re.match(r"import time:\s+(\d+)\s+\|\s+(\d+)\s+\|( *)(\S+)", line)
        if not m:
            continue
        n += 1
        if len(m.group(3)) <= 1:  # top-level import
            if m.group(4) == "pandas":
                pandas = int(m.group(2)) / 1000
            else:
                other += int(m.group(2)) / 1000
    return pandas, other, n


def importtime_lines() -> list[str]:
    pick = ["pandas", "numpy", "numpy._core._multiarray_umath", "pandas.core.frame", "pandas._libs.tslibs.timestamps",
            "dateutil", "logging", "json"]
    rows = {}
    for line in (RES / "importtime-raw.txt").read_text().splitlines():
        m = re.match(r"import time:\s+(\d+)\s+\|\s+(\d+)\s+\|(\s*)(\S+)", line)
        if m and m.group(4) in pick and m.group(4) not in rows:
            rows[m.group(4)] = (int(m.group(1)), int(m.group(2)))
    out = ["  self ms | cumul ms | module"]
    for name in sorted(rows, key=lambda n: -rows[n][1]):
        s, c = rows[name]
        out.append(f"{s / 1000:9.1f} | {c / 1000:8.1f} | {name}")
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    S = load()
    c = lambda label: S[label]["cold_total_p50"]
    st = lambda label: S[label]["startup_p50"]

    # Slide 5 — Round 1
    bar_panel("ROUND 1 — COLD TOTAL P50 (TINY HANDLER)",
              [("PYTHON 3.13", c("tiny-py313-tiny")), ("PYTHON 3.14", c("tiny-py-tiny")), ("GO", c("tiny-go-tiny"))],
              [f"GO vs PY 3.14 -> Δ {c('tiny-py-tiny') - c('tiny-go-tiny'):.2f} ms",
               f"PY 3.13 -> 3.14: +{c('tiny-py-tiny') - c('tiny-py313-tiny'):.2f} ms"],
              OUT / "s05_round1.png", colors=[GREEN, CYAN, GOLD])

    # Slide 6 — morning (importtime)
    pd_ms, other_ms, nmod = importtime_top()
    bar_panel("INIT — WHERE DOES THE TIME GO?",
              [("INIT P50", st("eager-importtime-simple")), ("import pandas", pd_ms), ("other imports", other_ms)],
              [f"{nmod} modules imported", f"pandas + numpy = {100 * pd_ms / st('eager-importtime-simple'):.0f}% of init"],
              OUT / "s06_init.png", colors=[CYAN, ORANGE, GREEN])
    code_panel(importtime_lines(), OUT / "s06_importtime.png", width=1100, size=24,
               title="$ PYTHONPROFILEIMPORTTIME=1   (CloudWatch, one cold start)")

    # Slide 7 — lazy
    table_panel("SIMPLE REQUEST", ["Variant", "Init P50", "Cold Total P50"],
                [["Eager", f"{st('eager-512-simple'):.2f} ms", f"{c('eager-512-simple'):.2f} ms"],
                 ["Lazy", f"{st('lazyfn-512-simple'):.2f} ms", f"{c('lazyfn-512-simple'):.2f} ms"]],
                OUT / "s07_simple.png", width=770, size=21,
                footer=f"↓ {pct(c('eager-512-simple'), c('lazyfn-512-simple'))}")
    bar_panel("TRAINING #1 — REPORT, COLD TOTAL P50",
              [("EAGER REPORT", c("eager-512-report")), ("LAZY REPORT", c("lazyfn-512-report"))],
              [f"SAME LAZY IMPORT @1769 MB: {c('lazyfn-1769-report'):.2f} ms",
               "INIT CPU IS BOOSTED. HANDLER CPU ISN'T."],
              OUT / "s07_report.png", colors=[CYAN, GOLD], footer_colors=[ORANGE, GREEN])

    # Slide 8 — .pyc
    bar_panel("TRAINING #2 — COLD TOTAL P50 (pandas, 512 MB)",
              [("NO .pyc", c("eager-pyc-none-simple")), (".pyc FOR 3.13", c("eager-pyc-wrong-simple")),
               (".pyc FOR 3.14", c("eager-512-simple"))],
              [f"RIGHT .pyc -> {pct(c('eager-pyc-none-simple'), c('eager-512-simple'))} lower Cold Total P50",
               "WRONG-VERSION .pyc = NO .pyc"],
              OUT / "s08_pyc.png", colors=[RED, GOLD, GREEN])

    # Slide 9 — PEP 810
    code_panel(["import json", "lazy import pandas as pd      # PEP 810", "",
                "def lambda_handler(event, context):",
                "    if event[\"type\"] == \"simple\":",
                "        return ...             # pandas never loads",
                "    df = pd.DataFrame(...)     # loads here, once"],
               OUT / "s09_code.png", highlight={1}, width=1100, size=26, title="app.py — python3.15")

    # Slide 10 — free wins
    g = warm_gb_ms()
    bar_panel("TRAINING #4 — MEMORY (CPU-BOUND HANDLER)",
              [(f"{m} MB", c(f"sha-{m}-sha")) for m in (128, 512, 1024, 1769)],
              ["WARM COST GB-ms: " + " / ".join(f"{g[m]:.0f}" for m in (128, 512, 1024, 1769)),
               f"1769 MB: {S['sha-128-sha']['warm_p50'] / S['sha-1769-sha']['warm_p50']:.0f}x faster, "
               f"{100 * (1 - g[1769] / g[128]):.0f}% cheaper than 128 MB"],
              OUT / "s10_memory.png", colors=[CYAN, GREEN, GOLD, ORANGE])
    bar_panel("ARM64 — pandas app, 512 MB",
              [("X86_64", c("eager-x86-512-simple")), ("ARM64", c("eager-512-simple"))],
              [f"↓ {pct(c('eager-x86-512-simple'), c('eager-512-simple'))}"],
              OUT / "s10_arm.png", colors=[CYAN, GOLD], font_scale=1.7)

    # Slide 11 — training card
    code_panel(["ROBBIE'S TRAINING",
                "✓ ARM64 + 1024 MB", "✓ .pyc precompiled", "✓ lazy import",
                f"simple {c('final-baseline-simple'):.0f} -> {c('final-opt-simple'):.0f} ms",
                f"↓ {pct(c('final-baseline-simple'), c('final-opt-simple'))}",
                f"report best: SnapStart {c('final-snap-report'):.0f} ms",
                f"↓ {pct(c('final-baseline-report'), c('final-snap-report'))}"],
               OUT / "s11_card.png", width=760, size=30)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
