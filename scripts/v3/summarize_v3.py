#!/usr/bin/env python3
"""Merge results-v3/raw/*.csv and write summary.csv, summary.md, reproducibility.md."""
from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results-v3"


def _p(vals: list[float], q: float) -> float | None:
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    return statistics.quantiles(sorted(vals), n=100, method="inclusive")[int(q * 100) - 1]


def summarize_rows(rows: list[dict]) -> dict[str, dict]:
    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        groups[r["label"]].append(r)
    out = {}
    for label, rs in sorted(groups.items()):
        cold = [r for r in rs if r["run_type"] == "cold"]
        warm = [r for r in rs if r["run_type"] == "warm"]
        start = [float(r.get("init_ms") or r.get("restore_ms")) for r in cold if (r.get("init_ms") or r.get("restore_ms"))]
        total = [float(r["cold_total_ms"]) for r in cold if r.get("cold_total_ms")]
        wd = [float(r["duration_ms"]) for r in warm]
        out[label] = {
            "label": label, "cold_n": len(cold), "warm_n": len(warm),
            "startup_p50": statistics.median(start) if start else None,
            "cold_total_p50": statistics.median(total) if total else None,
            "cold_total_p90": _p(total, 0.90),
            "warm_p50": statistics.median(wd) if wd else None,
        }
    return out


def main() -> int:
    rows, fields = [], None
    for f in sorted((OUT / "raw").glob("*.csv")):
        with f.open() as fh:
            for r in csv.DictReader(fh):
                r.setdefault("restore_ms", "")
                rows.append(r)
    fields = list(rows[0].keys())
    with (OUT / "raw.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    summ = summarize_rows(rows)
    cols = ["label", "cold_n", "warm_n", "startup_p50", "cold_total_p50", "cold_total_p90", "warm_p50"]
    fmt = lambda v: "" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v))
    with (OUT / "summary.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for s in summ.values():
            w.writerow([fmt(s[c]) for c in cols])
    md = ["| Label | Cold n | Warm n | Init/Restore P50 | Cold Total P50 | Cold Total P90 | Warm P50 |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    md += ["| " + " | ".join(fmt(s[c]) for c in cols) + " |" for s in summ.values()]
    (OUT / "summary.md").write_text("\n".join(md) + "\n")
    old = {r["label"]: float(r["cold_total_p50_ms"]) for r in csv.DictReader((ROOT / "results" / "summary.csv").open())}
    rep = ["| Original run (v2) | v2 Cold Total P50 (then) | Re-run today | Δ |", "|---|---:|---:|---:|"]
    for label, then in old.items():
        now = summ.get(f"old-{label}", {}).get("cold_total_p50")
        if now is not None:
            rep.append(f"| {label} | {then:.2f} | {now:.2f} | {100 * (now - then) / then:+.1f}% |")
    (OUT / "reproducibility.md").write_text(
        "# T11 — re-running the original v2 functions (unchanged code/config, same payloads)\n\n" + "\n".join(rep) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
