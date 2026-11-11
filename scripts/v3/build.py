#!/usr/bin/env python3
"""Build one deployment zip per LazyTown v3 variant (see experiments-v3/variants.json)."""
from __future__ import annotations

import argparse
import functools
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experiments-v3"
DEPS = ["pandas==3.1.1", "numpy==2.5.4"]
WRONG_PYC = "3.13"  # deliberately not the runtime's version


def _find(version: str) -> str:
    return subprocess.check_output(["uv", "python", "find", "--no-project", version], text=True).strip()


class _Interpreters(dict):
    def __missing__(self, version: str) -> str:
        self[version] = _find(version)
        return self[version]


INTERPRETERS = _Interpreters()


def load_variants() -> list[dict]:
    return json.loads((EXP / "variants.json").read_text())


def _pyver(runtime: str) -> str:
    return runtime.removeprefix("python")


@functools.cache
def _deps_dir(runtime: str, arch: str) -> Path:
    out = ROOT / "build" / "deps" / f"{runtime}-{arch}"
    if not out.exists():
        plat = "aarch64" if arch == "arm64" else "x86_64"
        subprocess.run(["uv", "pip", "install", "-q", "--target", str(out),
                        "--python-platform", f"{plat}-manylinux_2_28",
                        "--python-version", _pyver(runtime), "--only-binary", ":all:",
                        "--no-compile", *DEPS], check=True)
    return out


def _strip_pyc(d: Path) -> None:
    for p in list(d.rglob("__pycache__")):
        shutil.rmtree(p)
    for p in d.rglob("*.pyc"):
        p.unlink()


def _compile(d: Path, version: str) -> None:
    subprocess.run([INTERPRETERS[version], "-m", "compileall", "-q", "-j", "0",
                    "--invalidation-mode", "unchecked-hash", str(d)], check=True)


def _go(stage: Path, arch: str) -> None:
    env = {**os.environ, "GOOS": "linux", "GOARCH": "arm64" if arch == "arm64" else "amd64",
           "CGO_ENABLED": "0"}
    subprocess.run(["go", "build", "-tags", "lambda.norpc", "-trimpath", "-ldflags", "-s -w",
                    "-o", str(stage / "bootstrap"), "."], cwd=EXP / "go", env=env, check=True)


def build(variant: dict, out_dir: Path) -> Path:
    """Stage and zip one variant; returns the zip path."""
    stage = Path(out_dir) / variant["name"]
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True)
    if variant["app"] == "go":
        _go(stage, variant["arch"])
    else:
        if variant["deps"]:
            shutil.copytree(_deps_dir(variant["runtime"], variant["arch"]), stage, dirs_exist_ok=True)
        shutil.copy(EXP / "app" / f"{variant['app']}.py", stage / "app.py")
        _strip_pyc(stage)
        if variant["pyc"] == "right":
            _compile(stage, _pyver(variant["runtime"]))
        elif variant["pyc"] == "wrong":
            _compile(stage, WRONG_PYC)
    zip_path = Path(out_dir) / f"{variant['name']}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted(stage.rglob("*")):
            if f.is_file():
                info = zipfile.ZipInfo.from_file(f, f.relative_to(stage).as_posix())
                info.compress_type = zipfile.ZIP_DEFLATED
                with f.open("rb") as fh:
                    z.writestr(info, fh.read())
    shutil.rmtree(stage)
    return zip_path


def pyc_magics(zip_path: Path) -> set[bytes]:
    with zipfile.ZipFile(zip_path) as z:
        return {z.read(n)[:4] for n in z.namelist() if n.endswith(".pyc")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "build" / "zips")
    ap.add_argument("names", nargs="*")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for v in load_variants():
        if args.names and v["name"] not in args.names:
            continue
        z = build(v, args.out)
        print(f"{v['name']},{z.stat().st_size},{sum(i.file_size for i in zipfile.ZipFile(z).infolist())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
