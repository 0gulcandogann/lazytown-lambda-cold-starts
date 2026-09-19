#!/usr/bin/env bash
set -euo pipefail

mkdir -p go-build
(
  cd go
  go mod download
  GOOS=linux GOARCH=arm64 CGO_ENABLED=0 \
    go build -tags lambda.norpc -o ../go-build/bootstrap .
)
file go-build/bootstrap
