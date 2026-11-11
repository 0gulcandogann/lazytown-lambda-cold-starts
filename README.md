# LazyTown Lambda Cold Starts

> A reproducible AWS Lambda benchmark project for testing what actually moves Python cold-start latency: architecture, dependency loading, memory/CPU allocation, package size, and runtime choice.

The project uses a simple LazyTown-inspired idea: **Sportacus is already moving; Robbie needs a better wake-up routine.** The point is not that one language universally “wins.” The point is to **measure the workload, isolate the bottleneck, change one thing, and measure again.**

## Headline result (v3, November 2026)

Same app for every variant (a `simple` request and a pandas `report` request), python3.14, eu-central-1,
30 cold + 30 warm per cell. Full table: [`results-v3/summary.md`](results-v3/summary.md).

```text
Cold Total P50                     simple       report
Python baseline (x86, 512 MB)    2506.73 ms   2507.44 ms
+ ARM64 + 1024 MB                2033.68 ms   2038.55 ms
+ .pyc precompiled                736.52 ms    725.17 ms   <- no-regret: both paths -71%
+ .pyc + lazy import               79.84 ms   1340.81 ms   <- simple -96.8%, report pays later
+ .pyc + SnapStart                389.80 ms    559.00 ms   <- best report path (paid feature)
Python 3.15 `lazy import`          79.97 ms   1328.80 ms   (PEP 810, preview runtime)
Go (reference)                     49.40 ms     50.10 ms
```

What v3 found that v2 did not:

- **`.pyc` matters most.** `/var/task` is read-only, so Python cannot write `__pycache__` and recompiles every
  cold start: pandas init 2039.99 → 719.49 ms (−64.7%). A `.pyc` built for the wrong Python version is ignored
  (2045.19 ms).
- **Why lazy imports can be slower:** init runs with boosted CPU regardless of memory (eager pandas init: 716.61 ms
  at 128 MB vs 712.48 ms at 1769 MB); the handler gets CPU proportional to memory. The same lazy import costs
  2689.39 ms at 512 MB and 792.49 ms at 1769 MB.
- **Reproducibility:** all 19 original v2 runs were re-measured unchanged and landed within −4.5%…+2.0%
  ([`results-v3/reproducibility.md`](results-v3/reproducibility.md)).

How to run it: [`experiments-v3/README.md`](experiments-v3/README.md). The original v2 experiments below are kept
as they were.

## v2 headline (original run)

```text
Python baseline     2457.86 ms Cold Total P50
Python optimized      82.34 ms Cold Total P50

96.65% lower Cold Total P50
```

That is a **combined configuration result for this workload**, not a universal Python/Lambda guarantee. The optimized variant changes architecture, memory allocation, and unnecessary dependency loading together.

## What this repository tests

| Experiment | Question | Main observation from this run |
|---|---|---:|
| Python baseline | What does a tiny Python Lambda look like? | 64.76 ms Cold Total P50 |
| Python vs Go | Does runtime choice dominate a tiny handler? | 65.62 ms vs 65.60 ms |
| ARM64 | Does architecture matter? | 85.09 → 65.22 ms |
| Lazy loading | What happens when a heavy import is avoidable? | 1796.69 → 66.88 ms on the simple path |
| Memory tuning | Does more memory/CPU help CPU-bound work? | 2129.00 → 236.62 ms |
| Package diet | Does a large package hurt if it is not imported? | 65.56 → 64.75 ms |
| Final race | What does the combined Python setup look like? | 2457.86 → 82.34 ms |

All values above are **Cold Total P50**, where this project defines:

```text
Cold Total = Init Duration + Duration
```

## Repository layout

```text
.
├── README.md
├── experiments/
│   ├── 01-python-baseline/
│   ├── 02-python-vs-go/
│   ├── 03-arm64/
│   ├── 04-lazy-loading/
│   ├── 05-memory-tuning/
│   ├── 06-package-diet/
│   └── 07-final-race/
├── results/
│   ├── raw.csv
│   ├── summary.csv
│   └── summary.md
└── scripts/
    ├── benchmark.py
    ├── summarize.py
    └── plot_results.py
```

## Requirements

You need:

- an AWS account with permission to deploy and invoke Lambda functions
- AWS CLI v2 configured locally
- AWS SAM CLI
- Python 3.13 for local script checks
- Go matching the version declared by the experiment `go.mod` files when building Go locally
- Docker if you use `sam build --use-container`

> These experiments create AWS resources and may incur AWS charges. Delete test stacks when you are finished.

## Quick start

Clone the repository, choose an experiment, build it, and deploy it with SAM.

```bash
git clone <your-repository-url>
cd lazytown-lambda-cold-starts

cd experiments/03-arm64
sam build --use-container
sam deploy --guided
```

Then benchmark one of the deployed functions from the repository root:

```bash
python scripts/benchmark.py \
  --function-name lazytown-slide06-arm64 \
  --label arm64-local-run \
  --payload experiments/03-arm64/payload.json \
  --cold 30 \
  --warm 30 \
  --output results/my-run.csv
```

Summarize the run:

```bash
python scripts/summarize.py results/my-run.csv \
  --csv results/my-summary.csv \
  --md results/my-summary.md
```

## Experiments

### 01 — Python baseline

A tiny Python 3.13 Lambda returning JSON. Use it to establish a simple baseline before adding heavier work.

```bash
cd experiments/01-python-baseline
sam build
sam deploy --guided
```

### 02 — Python vs Go

Equivalent tiny handlers on ARM64 at 512 MB. This is intentionally small: it demonstrates why runtime assumptions should be measured rather than guessed.

For the local Go binary:

```bash
cd experiments/02-python-vs-go/go
./build-local.sh
```

### 03 — ARM64

Same Python source and memory setting; architecture is the controlled variable.

```text
x86_64  85.09 ms
ARM64   65.22 ms
```

### 04 — Lazy loading

Both variants package pandas. The difference is **when pandas is imported**.

Eager:

```python
import pandas as pd
```

Lazy:

```python
if request_type == "report":
    import pandas as pd
```

The simple path improved dramatically because it never needed pandas. The report path did not: delaying work is not the same as eliminating it.

### 05 — Memory tuning

Runs the same SHA-256 workload at 128, 512, 1024, and 1769 MB. Lambda memory also affects available CPU, so CPU-bound handlers can respond strongly to this setting.

### 06 — Package diet

Compares a package containing large third-party dependencies with a minimal package while the handler imports neither. In this run the cold-start difference was small, which helps separate **shipping dependencies** from **importing dependencies**.

### 07 — Final race

The final workload compares:

- Python baseline: x86_64, 512 MB, eager pandas + requests
- Python + ARM64: same baseline with ARM64
- Python optimized: ARM64, higher memory, unnecessary third-party dependencies removed
- Go reference: equivalent SHA-256 workload on ARM64

Build the Go custom-runtime binary first:

```bash
cd experiments/07-final-race
./build-go.sh
sam build --use-container
sam deploy --guided
```

The template expects `go-build/bootstrap`; that directory is intentionally ignored by Git.

## Benchmark methodology

Each checked-in label contains **30 accepted cold samples and 30 warm samples**.

For a requested cold sample, `scripts/benchmark.py`:

1. updates the Lambda function description with a unique nonce,
2. waits for the configuration update,
3. invokes the function with tail logs,
4. parses the Lambda `REPORT` line,
5. accepts the sample only when `Init Duration` is present.

This is a **best-effort benchmark technique**, not an AWS API that guarantees a cold start. Warm measurements are collected without another configuration change after one unmeasured warm-up invocation.

## Reproduce the checked-in summary

The aggregate CSV and Markdown summary can be regenerated from the raw dataset:

```bash
python scripts/summarize.py results/raw.csv
```

The repository includes all **1,140 raw rows** used for the checked-in aggregate results.

## Important caveats

- The tiny Python-vs-Go experiment and the final race use different workloads; do not compare their absolute numbers directly.
- The final Python baseline → optimized result changes multiple variables and is not an isolated optimization.
- The lazy-loading report path shows that moving an import into the handler can simply move the cost into the first request.
- The package-size measurement refers to the SAM build directory, not deployment ZIP size.
- `client_ms` includes local CLI/network overhead and is not Lambda execution duration.
- The existing billed-duration aggregate is not sufficient for a rigorous cost comparison between cold and warm executions.

## Useful commands

Check Python syntax:

```bash
python -m compileall experiments scripts
```

Build the final Go binary:

```bash
cd experiments/07-final-race
./build-go.sh
file go-build/bootstrap
```

Generate plots from the checked-in summary:

```bash
python -m pip install -r scripts/requirements-dev.txt
python scripts/plot_results.py results/summary.csv
```

## Takeaway

The biggest lesson from this benchmark is not “Python beats Go” or “always use ARM.” It is simpler:

> **Measure. Find the bottleneck. Change one thing. Measure again.**

A small code decision such as avoiding an unnecessary import can matter more than an optimization that sounds much larger on paper.
