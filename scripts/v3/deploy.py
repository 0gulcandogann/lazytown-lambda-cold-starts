#!/usr/bin/env python3
"""Deploy LazyTown v3 variants with plain AWS CLI (no SAM)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from build import ROOT, load_variants

PREFIX = "lazytown-v3-"
TAG = "project=lazytown-v3"
ROLE_NAME = "lazytown-v3-exec"
FALLBACK_ROLE_PREFIX = "lazytown-slide03-"
DIRECT_LIMIT = 50 * 1024 * 1024
TRUST = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {
    "Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}


def function_name(variant: dict) -> str:
    return PREFIX + variant["name"]


def create_cmd(variant: dict, zip_path: Path, role_arn: str, zip_bytes: int,
               bucket: str | None = None) -> list[str]:
    is_go = variant["app"] == "go"
    if zip_bytes > DIRECT_LIMIT:
        code = ["--code", f"S3Bucket={bucket},S3Key={zip_path.name}"]
    else:
        code = ["--zip-file", f"fileb://{zip_path}"]
    cmd = ["aws", "lambda", "create-function", "--function-name", function_name(variant),
           "--runtime", variant["runtime"], "--role", role_arn,
           "--handler", "bootstrap" if is_go else "app.lambda_handler",
           "--architectures", variant["arch"], "--memory-size", str(variant["memory"]),
           "--timeout", "60", "--tags", TAG, *code, "--output", "json"]
    if variant.get("env"):
        env = ",".join(f"{k}={v}" for k, v in variant["env"].items())
        cmd += ["--environment", f"Variables={{{env}}}"]
    if variant.get("snapstart"):
        cmd += ["--snap-start", "ApplyOn=PublishedVersions"]
    return cmd


def _aws(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["aws", *args], text=True, capture_output=True, check=check)


def ensure_role() -> str:
    got = _aws("iam", "get-role", "--role-name", ROLE_NAME, "--query", "Role.Arn",
               "--output", "text", check=False)
    if got.returncode == 0:
        return got.stdout.strip()
    made = _aws("iam", "create-role", "--role-name", ROLE_NAME, "--tags", "Key=project,Value=lazytown-v3",
                "--assume-role-policy-document", json.dumps(TRUST), "--query", "Role.Arn",
                "--output", "text", check=False)
    if made.returncode == 0:
        _aws("iam", "attach-role-policy", "--role-name", ROLE_NAME, "--policy-arn",
             "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")
        time.sleep(12)  # IAM propagation before Lambda can assume it
        return made.stdout.strip()
    print(f"[!] create-role denied, falling back to {FALLBACK_ROLE_PREFIX}* role", file=sys.stderr)
    return _aws("iam", "list-roles", "--query",
                f"Roles[?starts_with(RoleName,'{FALLBACK_ROLE_PREFIX}')].Arn | [0]",
                "--output", "text").stdout.strip()


def bucket_name(account: str) -> str:
    return f"lazytown-v3-artifacts-{account}"


def ensure_bucket() -> str:
    account = _aws("sts", "get-caller-identity", "--query", "Account", "--output", "text").stdout.strip()
    name = bucket_name(account)
    if _aws("s3api", "head-bucket", "--bucket", name, check=False).returncode != 0:
        region = _aws("configure", "get", "region").stdout.strip()
        _aws("s3api", "create-bucket", "--bucket", name,
             "--create-bucket-configuration", f"LocationConstraint={region}")
    return name


def deploy(variant: dict, zip_path: Path, role_arn: str, bucket: str | None = None) -> str:
    name = function_name(variant)
    size = zip_path.stat().st_size
    try:
        if size > DIRECT_LIMIT:
            _aws("s3", "cp", str(zip_path), f"s3://{bucket or ensure_bucket()}/{zip_path.name}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"{name}: upload failed: {e}") from e
    _aws("lambda", "delete-function", "--function-name", name, check=False)
    if size > DIRECT_LIMIT and bucket is None:
        bucket = ensure_bucket()
    res = subprocess.run(create_cmd(variant, zip_path, role_arn, size, bucket), text=True, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"{name}: {res.stderr.strip()}")
    _aws("lambda", "wait", "function-active-v2", "--function-name", name)
    return name


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zips", type=Path, default=ROOT / "build" / "zips")
    ap.add_argument("names", nargs="*")
    args = ap.parse_args()
    role = ensure_role()
    print(f"[+] role {role}")
    failed = []
    for v in load_variants():
        if args.names and v["name"] not in args.names:
            continue
        try:
            print(f"[+] {deploy(v, args.zips / (v['name'] + '.zip'), role)}")
        except RuntimeError as e:
            print(f"[!] {e}", file=sys.stderr)
            failed.append(v["name"])
    if failed:
        print("FAILED: " + " ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
