from benchmark import parse_report

def test_parse_restore_duration():
    log = ("REPORT RequestId: x Duration: 10.00 ms Billed Duration: 200 ms Memory Size: 1024 MB "
           "Max Memory Used: 90 MB Restore Duration: 180.50 ms Billed Restore Duration: 150 ms")
    r = parse_report(log)
    assert r["is_cold"] and r["restore_ms"] == 180.5 and r["cold_total_ms"] == 190.5

def test_parse_warm_has_no_cold_total():
    r = parse_report("REPORT RequestId: x Duration: 1.20 ms Billed Duration: 2 ms Memory Size: 512 MB Max Memory Used: 40 MB")
    assert not r["is_cold"] and r["cold_total_ms"] is None and r["restore_ms"] is None

def test_parse_init_unchanged():
    r = parse_report("REPORT RequestId: x Duration: 2.00 ms Billed Duration: 70 ms Memory Size: 512 MB Max Memory Used: 40 MB Init Duration: 63.00 ms")
    assert r["init_ms"] == 63.0 and r["cold_total_ms"] == 65.0

from pathlib import Path
from benchmark import invoke_cmd

def test_invoke_cmd_adds_qualifier():
    cmd = invoke_cmd("fn", Path("p.json"), Path("out.json"), qualifier="3")
    assert cmd[cmd.index("--qualifier") + 1] == "3"

def test_invoke_cmd_without_qualifier():
    assert "--qualifier" not in invoke_cmd("fn", Path("p.json"), Path("out.json"))
