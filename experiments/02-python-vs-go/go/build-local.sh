#!/usr/bin/env bash
set -euo pipefail
go mod download
GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go build -tags lambda.norpc -o bootstrap main.go
