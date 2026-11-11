from summarize_v3 import summarize_rows


def row(label, kind, init="", restore="", dur="1", total=""):
    return {"label": label, "run_type": kind, "init_ms": init, "restore_ms": restore,
            "duration_ms": dur, "cold_total_ms": total}


def test_restore_counts_as_startup():
    s = summarize_rows([row("snap", "cold", restore="300", dur="10", total="310"), row("snap", "warm", dur="2")])
    assert s["snap"]["startup_p50"] == 300 and s["snap"]["cold_total_p50"] == 310 and s["snap"]["warm_p50"] == 2


def test_p50_is_median():
    rows = [row("a", "cold", init=str(v), total=str(v)) for v in (10, 20, 30, 40)]
    assert summarize_rows(rows)["a"]["cold_total_p50"] == 25
