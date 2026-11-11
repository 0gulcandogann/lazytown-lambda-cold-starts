#!/usr/bin/env python3
"""Delete LazyTown v3 resources (and, with --include-old, the original v2 SAM stacks)."""
from __future__ import annotations

import argparse
import json
import subprocess

V3 = "lazytown-v3-"
OLD_PREFIXES = ("lazytown-slide", "lazytown-final-")
OLD_STACKS = [f"lazytown-slide{n:02d}" for n in (3, 5, 6, 7, 8, 9, 10)]


def targets(names: list[str], include_old: bool = False) -> list[str]:
    return [n for n in names if n.startswith(V3) or (include_old and n.startswith(OLD_PREFIXES))]


def _aws(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["aws", *args], text=True, capture_output=True, check=check)


def _functions() -> list[str]:
    out = _aws("lambda", "list-functions", "--query", "Functions[].FunctionName", "--output", "json", check=True)
    return json.loads(out.stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-old", action="store_true")
    args = ap.parse_args()
    if args.include_old:
        for stack in OLD_STACKS:
            r = _aws("cloudformation", "delete-stack", "--stack-name", stack)
            print(f"[stack] {stack}: {'delete requested' if r.returncode == 0 else r.stderr.strip()}")
        for stack in OLD_STACKS:
            _aws("cloudformation", "wait", "stack-delete-complete", "--stack-name", stack)
    for fn in targets(_functions(), args.include_old):
        r = _aws("lambda", "delete-function", "--function-name", fn)
        print(f"[fn] {fn}: {'deleted' if r.returncode == 0 else r.stderr.strip()}")
        _aws("logs", "delete-log-group", "--log-group-name", f"/aws/lambda/{fn}")
    left = targets(_functions(), args.include_old)
    print("LEFT: " + (" ".join(left) if left else "none"))
    return 1 if left else 0


if __name__ == "__main__":
    raise SystemExit(main())
