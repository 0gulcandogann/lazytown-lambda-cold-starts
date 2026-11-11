#!/usr/bin/env python3
"""Build Lazy_Town_v3.pptx from the v2 deck: same art, Python-first story, measured numbers.

Slide mapping (v2 -> v3): 1-4 same, 5 Round 1, 9 -> 6 morning (importtime), 7 lazy,
6 -> 8 .pyc, clone(5) -> 9 PEP 810, 8 -> 10 free wins, 10 -> 11 final race, 12 closing.
v2 slide 11 (who won, numbers baked into the background art) is dropped.
"""
from __future__ import annotations

import argparse
import copy
import csv
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

ROOT = Path(__file__).resolve().parents[2]
SRC = Path.home() / "Downloads" / "Lazy_Town_v2.pptx"
DST = Path.home() / "Downloads" / "Lazy_Town_v3.pptx"
PANELS = ROOT / "results-v3" / "panels"
GREEN, WHITE = RGBColor(0x92, 0xD0, 0x50), RGBColor(0xF2, 0xF2, 0xF2)


# ---------- low-level helpers ----------

def shape(slide, shape_id: int):
    return next(s for s in slide.shapes if s.shape_id == shape_id)


def _has_text(p) -> bool:
    return any((r.findtext(qn("a:t")) or "").strip() for r in p.findall(qn("a:r")))


def set_lines(sh, lines: list[str], size: float | None = None) -> None:
    """Replace a text frame's paragraphs, reusing paragraph i's formatting (or the last one)."""
    txBody = sh.text_frame._txBody
    paras = txBody.findall(qn("a:p"))
    templates = [copy.deepcopy(p) for p in paras]
    for p in paras:
        txBody.remove(p)
    for i, line in enumerate(lines):
        j = min(i, len(templates) - 1)
        if line and not _has_text(templates[j]):
            # blank template paragraph: use the nearest earlier (else first) paragraph with real text
            with_text = [k for k, t in enumerate(templates) if _has_text(t)]
            j = max((k for k in with_text if k <= j), default=with_text[0])
        p = copy.deepcopy(templates[j])
        runs = p.findall(qn("a:r"))
        if not runs:  # blank line on a blank template: keep it as is
            txBody.append(p)
            continue
        for r in runs[1:]:
            p.remove(r)
        if line:
            runs[0].find(qn("a:t")).text = line
            if size:
                rpr = runs[0].find(qn("a:rPr"))
                if rpr is None:
                    from lxml import etree
                    rpr = etree.Element(qn("a:rPr"))
                    runs[0].insert(0, rpr)
                rpr.set("sz", str(int(size * 100)))
        else:
            p.remove(runs[0])
        txBody.append(p)


def set_run(sh, para: int, run: int, text: str) -> None:
    sh.text_frame.paragraphs[para].runs[run].text = text


def replace_picture(slide, shape_id: int, png: Path, top_pt: float | None = None,
                    width_pt: float | None = None, left_pt: float | None = None) -> None:
    from PIL import Image
    pic = shape(slide, shape_id)
    _, rid = slide.part.get_or_add_image_part(str(png))
    pic._element.blipFill.find(qn("a:blip")).set(qn("r:embed"), rid)
    w, h = Image.open(png).size
    if width_pt:
        pic.width = Pt(width_pt)
    if left_pt is not None:
        pic.left = Pt(left_pt)
    pic.height = Emu(int(pic.width * h / w))
    if top_pt is not None:
        pic.top = Pt(top_pt)
    pic._element.blipFill.find(qn("a:srcRect")) is not None and pic._element.blipFill.remove(
        pic._element.blipFill.find(qn("a:srcRect")))


def remove_shape(slide, shape_id: int) -> None:
    el = shape(slide, shape_id)._element
    el.getparent().remove(el)


def set_notes(slide, text: str) -> None:
    slide.notes_slide.notes_text_frame.text = text.strip()


def clone_slide(prs, src):
    new = prs.slides.add_slide(src.slide_layout)  # don't touch new.shapes: it is cached lazily
    rid_map = {}
    for rid, rel in src.part.rels.items():
        if rel.reltype.endswith(("/notesSlide", "/slideLayout")):
            continue
        rid_map[rid] = new.part.relate_to(rel._target, rel.reltype)
    cSld = copy.deepcopy(src._element.cSld)
    for el in cSld.iter():
        for attr in list(el.attrib):
            if attr.startswith("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"):
                if el.attrib[attr] in rid_map:
                    el.attrib[attr] = rid_map[el.attrib[attr]]
    # add_slide already cached new.shapes -> its spTree; fill that same element in place.
    dst = new._element.cSld
    tree = dst.find(qn("p:spTree"))
    for child in list(tree):
        tree.remove(child)
    for child in cSld.find(qn("p:spTree")):
        tree.append(child)
    bg = cSld.find(qn("p:bg"))
    if bg is not None:
        old_bg = dst.find(qn("p:bg"))
        if old_bg is not None:
            dst.remove(old_bg)
        dst.insert(0, bg)
    return new


def reorder(prs, order: list) -> None:
    """order: list of slide objects in desired order; slides not listed are deleted."""
    lst = prs.slides._sldIdLst
    order_ids = [s.slide_id for s in order]  # resolve before the list is emptied
    ids = list(lst)
    for sld in ids:
        if int(sld.get("id")) not in order_ids:
            prs.part.drop_rel(sld.get(qn("r:id")))
        lst.remove(sld)
    id_el = {int(e.get("id")): e for e in ids}
    for sid in order_ids:
        lst.append(id_el[sid])
    assert len(prs.slides) == len(order)


def summary() -> dict[str, dict[str, float]]:
    return {r["label"]: {k: float(v) for k, v in r.items() if k != "label" and v}
            for r in csv.DictReader((ROOT / "results-v3" / "summary.csv").open())}


# ---------- the build ----------

def build_deck(out: Path = DST) -> Path:
    S = summary()
    c = lambda label: S[label]["cold_total_p50"]
    prs = Presentation(str(SRC))
    v2 = list(prs.slides)  # v2[0] is slide 1
    s5, s6, s7, s8, s9, s10, s12 = v2[4], v2[5], v2[6], v2[7], v2[8], v2[9], v2[11]
    s_pep = clone_slide(prs, s5)

    # --- 5: Round 1 ---
    replace_picture(s5, 117, PANELS / "s05_round1.png", top_pt=150)
    set_lines(shape(s5, 119), ["ARM64 - 512 MB", "", "Same payload:", "30 Cold / 30 Warm"])
    set_lines(shape(s5, 120), ["Sportacus vs Robbie", "",
                               f"\t{c('tiny-py-tiny') - c('tiny-go-tiny'):.0f} ms", "", "WAIT... THAT'S IT?"])

    # --- 6 (v2 #9): Robbie's morning ---
    set_lines(shape(s9, 171), ["ROBBIE'S MORNING"], size=14)
    set_lines(shape(s9, 172), ["Where does init go?", "Ask Python itself."])
    replace_picture(s9, 173, PANELS / "s06_init.png", top_pt=150)
    replace_picture(s9, 174, PANELS / "s06_importtime.png")
    cap = copy.deepcopy(shape(s5, 121)._element)  # small caption textbox style
    s9.shapes._spTree.append(cap)
    capsh = s9.shapes[-1]
    capsh.left, capsh.top, capsh.width = Pt(525), Pt(240), Pt(333)
    set_lines(capsh, ["Never-imported deps: +0 ms"])

    # --- 7: lazy ---
    set_lines(shape(s7, 138), ["TRAINING #1: BE LAZY ON PURPOSE"])
    replace_picture(s7, 146, PANELS / "s07_simple.png")
    replace_picture(s7, 145, PANELS / "s07_report.png")
    ratio = c("lazyfn-512-report") / c("eager-512-report")
    set_lines(shape(s7, 150), [f"{ratio:.1f}x SLOWER"])

    # --- 8 (v2 #6): .pyc ---
    set_run(shape(s6, 127), 0, 0, "Training #2:")
    for r in shape(s6, 127).text_frame.paragraphs[0].runs[1:]:
        r.text = ""
    shape(s6, 127).text_frame.paragraphs[0].runs[1].text = "Pre-compile"
    replace_picture(s6, 128, PANELS / "s08_pyc.png", top_pt=140)
    set_lines(shape(s6, 130), ["WHY SO SLOW?"])
    set_lines(shape(s6, 132), ["/var/task is", "read-only:", "no __pycache__,", "recompile on", "every cold start"],
              size=11)
    set_lines(shape(s6, 129), ["THE FIX:", "python3.14 -m", " compileall -q", " --invalidation-mode",
                               " unchecked-hash .", "Same version as", "the runtime!"], size=10)

    # --- 9 (clone of v2 #5): PEP 810 ---
    set_lines(shape(s_pep, 116), ["Training #3:", "lazy import"])
    replace_picture(s_pep, 117, PANELS / "s09_code.png", top_pt=140, width_pt=380, left_pt=80)
    set_lines(shape(s_pep, 121), ["Python 3.15 - PEP 810"])
    set_lines(shape(s_pep, 118), ["RESULT"])
    set_lines(shape(s_pep, 119), [f"simple: {c('eager-315-simple'):.0f} -> {c('pep810-315-simple'):.0f} ms", "",
                                  "report:", f"{c('eager-315-report'):.0f} -> {c('pep810-315-report'):.0f} ms"])
    set_lines(shape(s_pep, 120), ["No code moves.", "", "Same trade-off", "", "Lambda: preview"])

    # --- 10 (v2 #8): free wins ---
    set_lines(shape(s8, 158), ["TRAINING #4: FREE WINS"])
    set_lines(shape(s8, 159), ["No Python change needed."])
    replace_picture(s8, 160, PANELS / "s10_memory.png")
    set_lines(shape(s8, 161), ["ARM64"])
    replace_picture(s8, 163, PANELS / "s10_arm.png", top_pt=95, width_pt=250, left_pt=615)
    set_lines(shape(s8, 162), ["AND INIT?"])
    set_lines(shape(s8, 164), ["Init stays ~80 ms at", "every size. Memory", "speeds the handler,",
                               "not the imports."])
    remove_shape(s8, 165)  # the memory panel's footer already carries this line

    # --- 11 (v2 #10): final race ---
    set_lines(shape(s10, 181), ["Same app:", "simple + report.", "30 cold per cell."])
    replace_picture(s10, 182, PANELS / "s11_card.png", top_pt=172, width_pt=230, left_pt=103)
    remove_shape(s10, 184)
    _final_table(shape(s10, 183), S)

    # --- 12: closing ---
    set_lines(shape(s12, 200), ["ASK YOURSELF:", "What runs at init?", "Is it precompiled?",
                                "Does every request need it?"])

    order = [*v2[:4], s5, s9, s7, s6, s_pep, s8, s10, s12]
    for slide, text in zip(order, NOTES):
        set_notes(slide, text)
    reorder(prs, order)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    return out


def _final_table(gf, S) -> None:
    c = lambda label: S[label]["cold_total_p50"]
    rows = [
        ("Python baseline (x86, 512)", "final-baseline"),
        ("+ ARM64 + 1024 MB", "final-free"),
        ("+ .pyc", "final-pyc"),
        ("+ .pyc + lazy", "final-opt"),
        ("+ .pyc + SnapStart", "final-snap"),
        ("3.15 lazy import", "pep810-315"),
        ("Go (reference)", "final-go"),
    ]
    tbl = gf.table._tbl
    trs = tbl.findall(qn("a:tr"))
    template = trs[2]
    for tr in trs[1:]:
        tbl.remove(tr)
    best_simple = min(c(f"{k}-simple") for _, k in rows[:-1])
    best_report = min(c(f"{k}-report") for _, k in rows[:-1])
    for name, key in rows:
        tr = copy.deepcopy(template)
        tr.set("h", "300000")
        tbl.append(tr)
    table = gf.table
    hdr = ["VARIANT", "SIMPLE", "REPORT"]
    for j, t in enumerate(hdr):
        table.cell(0, j).text_frame.paragraphs[0].runs[0].text = t
    table.rows[0].height = Emu(300000)
    for i, (name, key) in enumerate(rows, start=1):
        vals = [name, f"{c(key + '-simple'):,.2f} ms", f"{c(key + '-report'):,.2f} ms"]
        for j, v in enumerate(vals):
            run = table.cell(i, j).text_frame.paragraphs[0].runs[0]
            run.text = v
            run.font.size = Pt(12)
            win = (j == 1 and c(key + "-simple") == best_simple) or (j == 2 and c(key + "-report") == best_report)
            run.font.color.rgb = GREEN if win else WHITE
    for j in range(3):
        table.cell(0, j).text_frame.paragraphs[0].runs[0].font.size = Pt(11)
    gf.height = Emu(300000 * (len(rows) + 1))


NOTES = [
    # 1
    """Slayt 1: LazyTown — 00:00–00:25
Herkese merhaba.
Bugün tembellikten bahsedeceğiz. Ama doğru yerde yapılan tembellikten: Lambda'daki Python kodumuzu hızlandıran türden.
Sorum şu: Robbie'yi, yani Python'ı, yarışa hazırlamak için neyi değiştirmemiz gerekiyor?
On dakikada Python'ın neden yavaş uyandığını ölçeceğiz ve bunu Python'ın kendi araçlarıyla düzelteceğiz. Hadi başlayalım.""",
    # 2
    """Slayt 2: Tanışma — 00:25–00:40
Ben Oğulcan. Cloud security tarafındayım, AWS Community Builder'ım. Normalde güvenlik yazıyorum; bugün biraz Robbie'nin tarafındayım. Ama söz, bugün kimseyi IAM policy'leriyle korkutmayacağım.""",
    # 3
    """Slayt 3: Meet Our Runners — 00:40–01:10
Yarışmacılarla tanışalım. Sportacus, Go: compiled binary ile piste çıkıyor. Robbie, Python: hepimizin sevdiği, ecosystem'i güçlü, ama sabah import'larını yapmadan yataktan kalkamayan yarışmacımız.
Bugün derdimiz Sportacus'le değil, Robbie'yle.""",
    # 4
    """Slayt 4: Wake Up, Robbie! — 01:10–02:00
Hazır bir execution environment yoksa Lambda sıfırdan kurar: runtime başlar, modülünüz import edilir, init kodu çalışır. Ancak ondan sonra handler request'i görür. Buna cold start diyoruz: idle'dan sonra, deploy'dan sonra ve scale ederken.
Environment hazırsa warm invocation: request doğrudan handler'a gider.
Benim takip ettiğim sayı Cold Total P50: Init Duration artı handler Duration, cold invocation'lar içinde median. Bu AWS'in verdiği bir metric değil, benim hesapladığım bir toplam. Her ölçüm otuz cold, otuz warm.""",
    # 5
    """Slayt 5: Round 1 — 02:00–02:40
İlk tur: minik bir handler. ARM64, 512 MB, aynı payload. Küçük JSON girer, küçük JSON çıkar.
Go 50,89 milisaniye. Python 3.14 79,59. Fark 29 milisaniye. Bu kadar mı? Evet. Bu kadar küçük bir işte sayıyı dil değil, Lambda'nın kendi init'i belirliyor.
Python'cılar için küçük bir not: aynı kod Python 3.13 runtime'ında 63,83. Yani 3.14'e geçmek bu testte cold start'a 16 milisaniye ekledi. Yükseltme bedava değil; ölçün.
Ama gerçek bir Python uygulaması boş gelmez. Yanında import'larla gelir. Asıl yarış orada başlıyor.""",
    # 6
    """Slayt 6: Robbie's Morning — 02:40–03:30
Pandas kullanan bir Lambda aldım ve Python'ın kendisine sordum: PYTHONPROFILEIMPORTTIME=1. Bu, python -X importtime'ın environment variable hali; çıktısı direkt CloudWatch'a düşüyor.
Init P50 716,31 milisaniye. Bunun 634 milisaniyesi tek satır: import pandas. Arkasından 624 modül geliyor. Init'in yüzde 89'u.
Sağ altta bir not daha: eski deneyde 125 megabaytlık kullanılmayan paketi taşıdım ama import etmedim. Fark yok, bugün tekrar ölçtüm, yine yok. Taşımak bedava; import etmek değil.
Yani Robbie'nin sabahı bavulu toplarken değil, kahvaltıda gidiyor.""",
    # 7
    """Slayt 7: Training #1: Be Lazy On Purpose — 03:30–04:50
İlk antrenman: bilerek tembel olmak.
Fonksiyon iki tür request alıyor: simple ve pandas'lı report. Import'u report'un code path'ine taşıyorum. Simple request 719,49'dan 82,46 milisaniyeye iniyor. Yüzde 89.
Ama report request: eager 739,08, lazy 2689,39. Üç buçuk kat yavaş. Aynı import, aynı iş. Neden?
Geçen sefer burada 'bilmiyorum' diyordum. Bu sefer ölçtüm. Eager sürümün init'i 128 megabaytta 716,61, 1769'da 712,48 milisaniye. Memory init'i hiç değiştirmiyor. Çünkü Lambda init sırasında burst CPU veriyor. Handler'da ise CPU memory'yle orantılı; 512 megabayt kabaca üçte bir vCPU. Import'u handler'a taşıyınca aynı iş kısık CPU'da çalışıyor. Aynı lazy sürüm 1769 megabaytta 792,49'a iniyor.
Aklınızda tek cümle kalacaksa: işi ortadan mı kaldırdın, yoksa sadece erteledin mi?""",
    # 8
    """Slayt 8: Training #2: Pre-compile — 04:50–06:00
Bu sunumun bence en Python'a özel kısmı.
Python bir modülü import ederken önce __pycache__ içinde derlenmiş .pyc arar. Yoksa kaynağı derler ve sonucu oraya yazmaya çalışır. Lambda'da kodunuzun durduğu /var/task salt okunur. Yazamaz. Paketiniz .pyc'siz geldiyse, pandas'ın yüzlerce dosyası her cold start'ta baştan derleniyor.
uv pip install varsayılan olarak .pyc üretmez. pip üretir ama build makinenizin Python'ıyla.
Ölçüm: .pyc yok, 2039,99 milisaniye. Python 3.13 için derlenmiş .pyc'yi 3.14 runtime'ına koydum: 2045,19. Hiç işe yaramıyor, çünkü Python sadece kendi sürümünün etiketli dosyasını okur. Doğru sürüm: 719,49. Yüzde 65.
Tek komut: python3.14 -m compileall, invalidation mode unchecked-hash. Zip timestamp'leriyle uğraşmasın diye.
Ve bu bir trade-off değil: hem simple hem report hızlanıyor.""",
    # 9
    """Slayt 9: Training #3: lazy import — 06:00–06:50
Python 3.15 ile gelen PEP 810: lazy import. Import'u fonksiyonun içine taşımak zorunda değilsiniz. Dosyanın başına lazy import pandas as pd yazıyorsunuz; isim hemen bağlanıyor, modül ilk kullanıldığı anda yükleniyor.
Lambda'da Python 3.15 şu an public preview. Yine de ölçtüm, 1024 megabayt: simple request eager 753,34, lazy 79,97. Report: eager 747,79, lazy 1328,80.
Fonksiyon içi import'la aynı trade-off; bedel yine erteleniyor. Ama kod okunur kalıyor, linter'lar ve tip kontrolü mutlu.""",
    # 10
    """Slayt 10: Training #4: Free Wins — 06:50–07:40
Python koduna dokunmadan alınan iki kazanç.
ARM64: aynı pandas uygulaması x86'da 948,03, ARM64'te 719,49. Yüzde 24, template'te tek satır. Bağımlılıklarınızın ARM64 wheel'i var mı, önce ona bakın.
Memory: init her boyutta 80 milisaniye civarında kalıyor; az önce gördüğümüz burst CPU. Ama CPU yoğun bir handler'da 128 megabaytta 2196,22, 1769'da 225,15. Warm'da 17 kat hızlı ve GB-milisaniye olarak yüzde 19 daha ucuz, çünkü süre memory'den daha hızlı düşüyor.
Yani memory import'u hızlandırmaz, handler'ı hızlandırır.""",
    # 11
    """Slayt 11: The Final Race — 07:40–09:10
Final. Bu sefer adil: hepsi aynı uygulama, aynı bağımlılıklar, hem simple hem report request. Her hücre otuz cold start.
Baseline: x86, 512 megabayt, .pyc yok. Yaklaşık 2507 milisaniye.
ARM64 ve 1024 megabayt: 2034. Bedava kazançlar ama hâlâ iki saniye.
Üstüne .pyc: 736,52 ve 725,17. Pişmanlıksız adım, iki yolda da yüzde 71.
Üstüne lazy import: simple 79,84. Ama report 1340,81. Trade-off'u görüyorsunuz.
Report yolu çoksa SnapStart: init'i önceden alınmış bir snapshot'tan geri yüklüyor. 389,80 ve 559. Report'ta en iyisi. Dürüst olayım, SnapStart ücretli: snapshot saklama ve her restore için ödeme var.
Go referans olarak 49,40.
Peki kim kazandı? Go hâlâ önde, onu inkâr etmeyeceğim. Ama Robbie simple request'te 2,5 saniyeden 80 milisaniyeye geldi: yüzde 96,81. Dili değiştirmedik; Python'ın nasıl uyandığını değiştirdik.
Bu rakamlar bu workload, bu region ve bu runtime için. Bir de: eski sunumdaki 19 testi bugün tekrar çalıştırdım, hepsi yüzde 5 içinde aynı çıktı.""",
    # 12
    """Slayt 12: Kapanış — 09:10–10:00
Kendi Lambda'nıza dönünce üç soru sorun.
Init'te ne çalışıyor? python -X importtime söylüyor.
Paketiniz precompiled mı, ve doğru Python sürümüyle mi?
Her request bu import'a gerçekten ihtiyaç duyuyor mu?
Robbie'den öğrendiğim şey bu: gereksiz işi yapmamak da bir performans stratejisi. Önce ölçün, sonra canınızı yakan yeri düzeltin.
Kodlar ve bütün ham ölçümler QR'daki sayfada. Dinlediğiniz için teşekkür ederim.
(Toplam: 10:00)""",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DST)
    print(build_deck(ap.parse_args().out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
