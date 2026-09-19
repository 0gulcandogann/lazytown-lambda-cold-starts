#!/usr/bin/env bash
set -euo pipefail

echo "Build first:"
echo "  sam build --use-container"
echo

for fn in Slide09Fat Slide09Slim; do
  dir=".aws-sam/build/$fn"
  if [[ -d "$dir" ]]; then
    echo "$fn"
    du -sh "$dir"
    echo
  fi
done
