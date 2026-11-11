#!/usr/bin/env bash
# T11: re-measure the original (v2) deployed functions with their original payloads.
set -u
cd "$(dirname "$0")/../.."
E=experiments
OUT=results-v3/raw-old-rerun.csv
run() { python3 scripts/benchmark.py --function-name "$1" --label "$2" --payload "$3" --cold 30 --warm 30 --output "$OUT.$2" > "results-v3/logs/old-$2.log" 2>&1; }
mkdir -p results-v3/logs
run lazytown-slide03-python-baseline slide03-python-baseline $E/01-python-baseline/payload.json &
run lazytown-slide05-python slide05-python $E/02-python-vs-go/payload.json &
run lazytown-slide05-go slide05-go $E/02-python-vs-go/payload.json &
run lazytown-slide06-arm64 slide06-arm64 $E/03-arm64/payload.json &
run lazytown-slide06-x86 slide06-x86 $E/03-arm64/payload.json &
run lazytown-slide07-eager slide07-eager-simple $E/04-lazy-loading/payload-simple.json &
run lazytown-slide07-lazy slide07-lazy-simple $E/04-lazy-loading/payload-simple.json &
run lazytown-slide09-fat slide09-fat $E/06-package-diet/payload.json &
run lazytown-slide09-slim slide09-slim $E/06-package-diet/payload.json &
for m in 128 512 1024 1769; do run lazytown-slide08-mem-$m slide08-${m}mb $E/05-memory-tuning/payload.json & done
run lazytown-final-python-baseline slide10-python-baseline $E/07-final-race/payload.json &
run lazytown-final-python-arm64 slide10-python-arm64 $E/07-final-race/payload.json &
run lazytown-final-python-optimized slide10-python-optimized $E/07-final-race/payload.json &
run lazytown-final-go slide10-go $E/07-final-race/payload.json &
wait
# report payloads run on the same functions after simple ones finish (one config at a time per function)
run lazytown-slide07-eager slide07-eager-report $E/04-lazy-loading/payload-report.json &
run lazytown-slide07-lazy slide07-lazy-report $E/04-lazy-loading/payload-report.json &
wait
echo done
