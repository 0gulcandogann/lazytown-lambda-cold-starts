import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from build import INTERPRETERS, build, load_variants, pyc_magics

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "experiments-v3" / "app"


def magic(version: str) -> bytes:
    out = subprocess.check_output(
        [INTERPRETERS[version], "-c", "import importlib.util,sys;sys.stdout.write(importlib.util.MAGIC_NUMBER.hex())"],
        text=True)
    return bytes.fromhex(out)


def v(app="tiny", pyc="none", deps=False, runtime="python3.14", arch="arm64"):
    return {"name": f"t-{app}-{pyc}", "app": app, "runtime": runtime, "arch": arch,
            "memory": 512, "deps": deps, "pyc": pyc, "snapstart": False, "env": {}}


def test_pyc_right_magic(tmp_path):
    assert pyc_magics(build(v(pyc="right"), tmp_path)) == {magic("3.14")}


def test_pyc_none_has_no_pyc(tmp_path):
    assert pyc_magics(build(v(pyc="none"), tmp_path)) == set()


def test_pyc_wrong_is_313(tmp_path):
    assert pyc_magics(build(v(pyc="wrong"), tmp_path)) == {magic("3.13")}


def test_pyc_right_for_315_runtime(tmp_path):
    assert pyc_magics(build(v(pyc="right", runtime="python3.15"), tmp_path)) == {magic("3.15")}


def test_zip_has_app_at_root(tmp_path):
    names = zipfile.ZipFile(build(v(app="eager"), tmp_path)).namelist()
    assert "app.py" in names


def _call(app: str, event: dict) -> dict:
    code = (f"import json,sys;sys.path.insert(0,{str(APP)!r});"
            f"m=__import__({app!r});print(json.dumps(m.lambda_handler({event!r},None)))")
    return json.loads(subprocess.check_output([sys.executable, "-c", code], text=True))


@pytest.mark.parametrize("app", ["eager", "lazy_fn", "lazy_pep810"])
def test_handler_contract_report(app):
    out = _call(app, {"type": "report", "rows": [{"value": 1}] * 3})
    assert json.loads(out["body"]) == {"mode": "report", "total": 3}


@pytest.mark.parametrize("app", ["eager", "lazy_fn", "lazy_pep810"])
def test_handler_contract_simple(app):
    assert json.loads(_call(app, {"type": "simple"})["body"]) == {"mode": "simple", "ok": True}


def test_lazy_fn_simple_does_not_import_pandas():
    code = (f"import sys;sys.path.insert(0,{str(APP)!r});import lazy_fn;"
            "lazy_fn.lambda_handler({'type':'simple'},None);print('pandas' in sys.modules)")
    assert subprocess.check_output([sys.executable, "-c", code], text=True).strip() == "False"


def test_pep810_simple_does_not_import_pandas():
    code = (f"import sys;sys.path.insert(0,{str(APP)!r});import lazy_pep810;"
            "lazy_pep810.lambda_handler({'type':'simple'},None);print('pandas' in sys.modules)")
    assert subprocess.check_output([sys.executable, "-c", code], text=True).strip() == "False"


def test_variants_cover_all_tests():
    ids = {t for var in load_variants() for t in var["test_ids"]}
    assert ids >= {"T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10"}


def test_variant_names_unique_and_short():
    names = [var["name"] for var in load_variants()]
    assert len(names) == len(set(names))
    assert all(len("lazytown-v3-" + n) <= 64 for n in names)


def test_report_payload_has_1000_rows():
    p = json.loads((ROOT / "experiments-v3" / "payloads" / "report.json").read_text())
    assert p["type"] == "report" and len(p["rows"]) == 1000
