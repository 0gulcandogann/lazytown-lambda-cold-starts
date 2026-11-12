import csv
import re
from pathlib import Path

import pytest
from pptx import Presentation

from deck import SRC, build_deck

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def deck(tmp_path_factory):
    if not SRC.exists():
        pytest.skip("source deck not available")
    return Presentation(build_deck(tmp_path_factory.mktemp("d") / "v3.pptx"))


def texts(slide):
    return " ".join(sh.text_frame.text for sh in slide.shapes if sh.has_text_frame) + " " + " ".join(
        c.text for sh in slide.shapes if sh.has_table for r in sh.table.rows for c in r.cells)


def notes(slide):
    return slide.notes_slide.notes_text_frame.text


def test_twelve_slides(deck):
    assert len(deck.slides) == 12


@pytest.mark.parametrize("idx,needle", [
    (4, "Round 1"), (5, "MORNING"), (6, "TRAINING #1"), (7, "Training #2"),
    (8, "Training #3"), (9, "TRAINING #4"), (10, "FINAL RACE"), (11, "ASK YOURSELF")])
def test_slide_order(deck, idx, needle):
    assert needle in texts(deck.slides[idx])


def test_notes_total_ten_minutes(deck):
    assert "10:00" in notes(deck.slides[11])


def _measured():
    vals = []
    for r in csv.DictReader((ROOT / "results-v3" / "summary.csv").open()):
        vals += [float(v) for k, v in r.items() if k != "label" and v and "_n" not in k]
    return vals


def test_every_ms_number_is_measured(deck):
    vals = _measured()
    S = {r["label"]: r for r in csv.DictReader((ROOT / "results-v3" / "summary.csv").open())}
    ct = lambda k: float(S[k]["cold_total_p50"])
    extra = {634.49, 59.93, 0.0,  # importtime log; "unused deps: +0 ms"
             ct("tiny-py-tiny") - ct("tiny-go-tiny"), ct("tiny-py-tiny") - ct("tiny-py313-tiny")}
    bad = []
    for i, s in enumerate(deck.slides, 1):
        for m in re.finditer(r"(\d[\d.,]*)\s*(?:ms|milisaniye)", texts(s) + " " + notes(s)):
            raw = m.group(1).rstrip(".")
            if re.fullmatch(r"\d+,\d{2}", raw):  # Turkish decimal comma: 50,89
                raw = raw.replace(",", ".")
            n = float(raw.replace(",", ""))
            ok = any(abs(n - v) < 0.006 or (n == int(n) and round(v) == n) for v in vals) or \
                any(abs(n - e) < 1 for e in extra)
            if not ok and i > 4:
                bad.append((i, m.group(0)))
    assert bad == []


def test_pyc_step_percent_is_not_misattributed(deck):
    # final-free -> final-pyc is ~-64%; -71% is only vs the x86 baseline
    n = notes(deck.slides[10])
    assert "yüzde 71" not in n or "baseline'a göre yüzde 71" in n
    assert "yüzde 64" in n


def test_final_race_notes_disclose_snapstart_method(deck):
    assert "eşzamanlı" in notes(deck.slides[10])


def test_slide4_puts_imports_in_init(deck):
    t = texts(deck.slides[3])
    assert "imports" in t and "top-level" in t


def test_slide7_single_code_snippet(deck):
    pics = [sh for sh in deck.slides[6].shapes if sh.shape_type == 13 and sh.left < 12700 * 320]
    assert len(pics) == 1


def test_slide10_memory_claim_scoped_to_init(deck):
    t = texts(deck.slides[9])
    assert "not the imports" not in t and "init" in t.lower()


def test_final_table_merges_lazy_rows_and_labels_baseline(deck):
    t = texts(deck.slides[10])
    assert "3.15 lazy import" not in t
    assert "no .pyc" in t


def test_accuracy_caveats_in_notes(deck):
    assert "gözlem" in notes(deck.slides[6])           # burst CPU is observed, not documented
    assert "Ağustos 2025" in notes(deck.slides[6])     # INIT is billed
    assert "tek bir cold start" in notes(deck.slides[5])
    assert "mutlu" not in notes(deck.slides[8])
