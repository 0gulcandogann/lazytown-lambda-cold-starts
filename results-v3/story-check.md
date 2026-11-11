# Story check — planned message vs measured result (Cold Total P50, 30 cold + 30 warm each)

| Slide | Planned message | Measured | Verdict / new message |
|---|---|---|---|
| 5 Round 1 | Tiny handler: Python ≈ Go | Py 3.14 79.6, Py 3.13 63.8, Go 50.9 ms. Old tie re-ran as 63.9 vs 63.8 (old 6.8 MB Go build). | **Changed.** Go now ahead by 29 ms (stripped 2.6 MB binary). Punchline kept: "29 ms. That's it?" — while pandas will cost ~2000 ms. Python nugget: 3.13→3.14 cost +16 ms cold. |
| 6 Morning (importtime) | pandas dominates init | 624 modules; pandas+numpy = 634 of ~716 ms init (with .pyc) | **Supported.** |
| 7 Lazy (fn) | simple faster, report slower; why = init burst CPU | simple 719→82 (−89%); report 739→2689 (3.6x slower); same import at 1769 MB: 792. Init 128 MB 719 vs 1769 MB 714. | **Supported + explained.** Init runs with burst CPU regardless of memory; handler at 512 MB gets ~⅓ vCPU. |
| 8 .pyc | read-only FS → recompile every cold start | no .pyc 2040 → right .pyc 719 (−65%). wrong-version .pyc 2045 (= none). | **Strongly supported.** Biggest pure-Python win. |
| 9 PEP 810 | `lazy import` = lazy without moving code | 3.15: eager 753/748 → lazy 80/1329 (simple/report, 1024 MB) | **Supported.** Same trade-off as fn-level lazy, cleaner code. Preview runtime. |
| 10 Free wins | ARM64 + memory | ARM64: 948→719 (−24%). SHA CPU-bound warm: 128 MB 2115 ms → 1769 MB 124 ms (17x) and 19% *cheaper* (264→214 GB-ms). Init flat ~80 ms. | **Changed detail:** old "1024 = same cost" → now 1769 is fastest *and* cheapest for CPU-bound work. |
| 11 Final race | fair race | simple/report: baseline 2507/2507 · +ARM64+1024 2034/2039 · +.pyc 737/725 · +.pyc+lazy 80/1341 · +.pyc+PEP810 80/1329 · +.pyc+SnapStart 390/559 · Go(ref) 49/50 | **New message:** .pyc = no-regret (−71% both paths). Lazy = −97% for simple, but report pays. SnapStart = best for report (−78%). Pick by traffic mix. |
| T11 | reproducibility | 19/19 original runs within −4.5%…+2.0% | Methodology holds. |
