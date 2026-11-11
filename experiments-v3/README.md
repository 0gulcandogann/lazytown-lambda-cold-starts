# LazyTown v3 experiments

All variants live in [`variants.json`](variants.json) and share four tiny apps in [`app/`](app/) plus one Go
handler in [`go/`](go/). Every Python variant with dependencies ships the same `pandas==3.1.1` / `numpy==2.5.4`.

| Field | Meaning |
|---|---|
| `app` | `eager` (module-level import), `lazy_fn` (import inside the handler), `lazy_pep810` (`lazy import`, 3.15), `tiny`, `sha` |
| `pyc` | `none` (no bytecode), `wrong` (compiled by Python 3.13), `right` (compiled by the runtime's version, `--invalidation-mode unchecked-hash`) |
| `test_ids` | which question (T1–T10) the variant answers — see the table below |

| Test | Question |
|---|---|
| T1 | Tiny handler: Python 3.13 / 3.14 vs Go |
| T2 | Where does init go? (`PYTHONPROFILEIMPORTTIME=1` inside Lambda → [`../results-v3/importtime.txt`](../results-v3/importtime.txt)) |
| T3 | Lazy import (inside the handler), simple vs report |
| T4 | Does memory change init? (128 vs 1769 MB) |
| T5 | `.pyc`: none / wrong version / right version |
| T6 | PEP 810 `lazy import` on python3.15 (preview) |
| T7 | x86_64 vs arm64 |
| T8 | Memory → CPU for a CPU-bound handler |
| T9 | Fair final race (same app, both request types) |
| T10 | SnapStart (cold = `Restore Duration`; samples from one barrier-synchronized burst on a fresh version) |
| T11 | Re-run of the original v2 functions |

## Run

Requires AWS CLI (v1 or v2), `uv`, Go, and an execution role. No SAM.

```bash
uv venv && uv pip install pytest pillow python-pptx boto3 pandas==3.1.1 numpy==2.5.4
.venv/bin/pytest -q tests                     # local checks (no AWS)
.venv/bin/python scripts/v3/build.py          # build/zips/*.zip
.venv/bin/python scripts/v3/deploy.py         # lazytown-v3-* functions (tag project=lazytown-v3)
.venv/bin/python scripts/v3/run_all.py        # results-v3/raw/*.csv (8 functions in parallel)
.venv/bin/python scripts/v3/summarize_v3.py   # results-v3/summary.{csv,md}, reproducibility.md
.venv/bin/python scripts/v3/cleanup.py        # delete everything again
```

Cost: everything except SnapStart fits the Lambda free tier. SnapStart bills snapshot cache (min. 3 h) and
restores; delete published versions right after T10 (`run_all` does not do it for you).
