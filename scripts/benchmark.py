#!/usr/bin/env python3
"""
Benchmark one AWS Lambda function using AWS CLI.

Cold samples:
- update function Description to force a configuration refresh
- wait for function-updated
- invoke with LogType=Tail
- accept the sample only when REPORT contains Init Duration

Warm samples:
- invoke repeatedly without config changes

No Python SDK dependency is required; only AWS CLI.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import uuid

REPORT_RE = re.compile(
    r"REPORT RequestId: .*?"
    r"Duration:\s+(?P<duration>[0-9.]+)\s+ms\s+"
    r"Billed Duration:\s+(?P<billed>[0-9.]+)\s+ms\s+"
    r"Memory Size:\s+(?P<memory>[0-9.]+)\s+MB\s+"
    r"Max Memory Used:\s+(?P<max_memory>[0-9.]+)\s+MB"
    r"(?:\s+Init Duration:\s+(?P<init>[0-9.]+)\s+ms)?",
    re.DOTALL,
)

def run(cmd: list[str], capture=True) -> str:
    proc = subprocess.run(
        cmd,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    return proc.stdout.strip() if capture else ""

def force_refresh(function_name: str) -> None:
    nonce = f"lazytown-bench-{uuid.uuid4().hex[:16]}"
    run([
        "aws", "lambda", "update-function-configuration",
        "--function-name", function_name,
        "--description", nonce,
        "--output", "json",
    ])
    run([
        "aws", "lambda", "wait", "function-updated",
        "--function-name", function_name,
    ])

def invoke(function_name: str, payload_path: Path) -> tuple[dict, float, str]:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        response_path = Path(tf.name)

    cmd = [
        "aws", "lambda", "invoke",
        "--function-name", function_name,
        "--payload", f"fileb://{payload_path}",
        "--cli-binary-format", "raw-in-base64-out",
        "--log-type", "Tail",
        "--query", "LogResult",
        "--output", "text",
        str(response_path),
    ]

    started = time.perf_counter()
    log_b64 = run(cmd)
    client_ms = (time.perf_counter() - started) * 1000.0

    try:
        response = json.loads(response_path.read_text(encoding="utf-8") or "{}")
    finally:
        response_path.unlink(missing_ok=True)

    log_text = base64.b64decode(log_b64).decode("utf-8", errors="replace")
    return response, client_ms, log_text

def parse_report(log_text: str) -> dict:
    m = REPORT_RE.search(log_text)
    if not m:
        raise RuntimeError(f"REPORT line not found:\n{log_text}")

    duration = float(m.group("duration"))
    billed = float(m.group("billed"))
    memory = float(m.group("memory"))
    max_memory = float(m.group("max_memory"))
    init = float(m.group("init")) if m.group("init") else None

    return {
        "duration_ms": duration,
        "billed_ms": billed,
        "memory_mb": memory,
        "max_memory_mb": max_memory,
        "init_ms": init,
        "cold_total_ms": (duration + init) if init is not None else None,
        "is_cold": init is not None,
    }

def append_row(output: Path, row: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    exists = output.exists()
    fields = [
        "timestamp",
        "label",
        "function_name",
        "run_type",
        "run_number",
        "is_cold",
        "init_ms",
        "duration_ms",
        "cold_total_ms",
        "billed_ms",
        "memory_mb",
        "max_memory_mb",
        "client_ms",
        "response_status_code",
    ]
    with output.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow(row)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--function-name", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--payload", required=True, type=Path)
    ap.add_argument("--cold", type=int, default=30)
    ap.add_argument("--warm", type=int, default=30)
    ap.add_argument("--output", type=Path, default=Path("results/raw.csv"))
    ap.add_argument("--cold-retries", type=int, default=3)
    args = ap.parse_args()

    if not args.payload.exists():
        ap.error(f"Payload not found: {args.payload}")

    print(f"[+] Function: {args.function_name}")
    print(f"[+] Label:    {args.label}")
    print(f"[+] Cold:     {args.cold}")
    print(f"[+] Warm:     {args.warm}")
    print()

    for i in range(1, args.cold + 1):
        accepted = False
        for attempt in range(1, args.cold_retries + 1):
            print(f"[cold {i:02d}/{args.cold:02d}] refresh (attempt {attempt})")
            force_refresh(args.function_name)
            response, client_ms, logs = invoke(args.function_name, args.payload)
            report = parse_report(logs)

            if not report["is_cold"]:
                print("  ! No Init Duration; retrying")
                continue

            append_row(args.output, {
                "timestamp": int(time.time()),
                "label": args.label,
                "function_name": args.function_name,
                "run_type": "cold",
                "run_number": i,
                **report,
                "client_ms": round(client_ms, 3),
                "response_status_code": response.get("statusCode", ""),
            })
            print(
                f"  init={report['init_ms']:.2f} ms "
                f"duration={report['duration_ms']:.2f} ms "
                f"cold_total={report['cold_total_ms']:.2f} ms"
            )
            accepted = True
            break

        if not accepted:
            raise RuntimeError(f"Could not obtain a cold sample for run {i}")

    # One warm-up invoke after the last config refresh, then measured warm samples.
    invoke(args.function_name, args.payload)

    for i in range(1, args.warm + 1):
        response, client_ms, logs = invoke(args.function_name, args.payload)
        report = parse_report(logs)
        append_row(args.output, {
            "timestamp": int(time.time()),
            "label": args.label,
            "function_name": args.function_name,
            "run_type": "warm",
            "run_number": i,
            **report,
            "client_ms": round(client_ms, 3),
            "response_status_code": response.get("statusCode", ""),
        })
        print(
            f"[warm {i:02d}/{args.warm:02d}] "
            f"duration={report['duration_ms']:.2f} ms "
            f"client={client_ms:.2f} ms"
        )

    print(f"\n[+] Results appended to {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
