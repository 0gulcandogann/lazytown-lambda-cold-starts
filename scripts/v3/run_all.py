#!/usr/bin/env python3
"""Run every v3 benchmark (T1-T10) plus the T11 re-run of the original functions.

Jobs for one function run sequentially (each cold sample rewrites its config);
different functions run in parallel, highest-priority tests first.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from build import ROOT, load_variants
from deploy import function_name

PRIORITY = ["T9", "T3", "T5", "T4", "T2", "T6", "T1", "T7", "T8", "T10"]
RAW = ROOT / "results-v3" / "raw"
E = "experiments"
OLD = [  # (function, label, payload) — original v2 runs, T11
    ("lazytown-slide03-python-baseline", "slide03-python-baseline", f"{E}/01-python-baseline/payload.json"),
    ("lazytown-slide05-python", "slide05-python", f"{E}/02-python-vs-go/payload.json"),
    ("lazytown-slide05-go", "slide05-go", f"{E}/02-python-vs-go/payload.json"),
    ("lazytown-slide06-arm64", "slide06-arm64", f"{E}/03-arm64/payload.json"),
    ("lazytown-slide06-x86", "slide06-x86", f"{E}/03-arm64/payload.json"),
    ("lazytown-slide07-eager", "slide07-eager-simple", f"{E}/04-lazy-loading/payload-simple.json"),
    ("lazytown-slide07-eager", "slide07-eager-report", f"{E}/04-lazy-loading/payload-report.json"),
    ("lazytown-slide07-lazy", "slide07-lazy-simple", f"{E}/04-lazy-loading/payload-simple.json"),
    ("lazytown-slide07-lazy", "slide07-lazy-report", f"{E}/04-lazy-loading/payload-report.json"),
    *[(f"lazytown-slide08-mem-{m}", f"slide08-{m}mb", f"{E}/05-memory-tuning/payload.json") for m in (128, 512, 1024, 1769)],
    ("lazytown-slide09-fat", "slide09-fat", f"{E}/06-package-diet/payload.json"),
    ("lazytown-slide09-slim", "slide09-slim", f"{E}/06-package-diet/payload.json"),
    ("lazytown-final-python-baseline", "slide10-python-baseline", f"{E}/07-final-race/payload.json"),
    ("lazytown-final-python-arm64", "slide10-python-arm64", f"{E}/07-final-race/payload.json"),
    ("lazytown-final-python-optimized", "slide10-python-optimized", f"{E}/07-final-race/payload.json"),
    ("lazytown-final-go", "slide10-go", f"{E}/07-final-race/payload.json"),
]


def _job(label: str, payload: str, snapstart: bool = False) -> dict:
    return {"label": label, "payload": payload, "snapstart": snapstart, "output": str(RAW / f"{label}.csv")}


def build_groups() -> list[dict]:
    def rank(v: dict) -> int:
        return min(PRIORITY.index(t) for t in v["test_ids"])

    groups = []
    for v in sorted(load_variants(), key=rank):
        groups.append({"function": function_name(v), "jobs": [
            _job(f"{v['name']}-{p}", f"experiments-v3/payloads/{p}.json", v["snapstart"]) for p in v["payloads"]]})
    old: dict[str, list] = {}
    for fn, label, payload in OLD:
        old.setdefault(fn, []).append(_job(f"old-{label}", payload))
    groups += [{"function": fn, "jobs": jobs} for fn, jobs in old.items()]
    return groups


def run_group(group: dict, cold: int, warm: int, retries: int = 2) -> list[str]:
    failed = []
    for job in group["jobs"]:
        out = Path(job["output"])
        if out.exists():
            continue  # already measured; delete the file to re-run
        tmp = out.with_suffix(".partial")
        log = RAW / "logs" / f"{job['label']}.log"
        cmd = [sys.executable, str(ROOT / "scripts" / "benchmark.py"), "--function-name", group["function"],
               "--label", job["label"], "--payload", job["payload"], "--cold", str(cold),
               "--warm", str(warm), "--output", str(tmp)]
        if job["snapstart"]:
            cmd.append("--snapstart")
        for attempt in range(retries + 1):
            tmp.unlink(missing_ok=True)
            with log.open("w") as fh:
                rc = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT).returncode
            if rc == 0:
                tmp.rename(out)
                print(f"[ok] {job['label']}", flush=True)
                break
            print(f"[retry {attempt + 1}] {job['label']}", flush=True)
        else:
            failed.append(job["label"])
            print(f"[FAIL] {job['label']} (see {log})", flush=True)
    return failed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parallel", type=int, default=8)
    ap.add_argument("--cold", type=int, default=30)
    ap.add_argument("--warm", type=int, default=30)
    args = ap.parse_args()
    (RAW / "logs").mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(args.parallel) as pool:
        failed = sum(pool.map(lambda g: run_group(g, args.cold, args.warm), build_groups()), [])
    print("FAILED: " + " ".join(failed) if failed else "ALL OK")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
