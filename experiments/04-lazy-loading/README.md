# 04 — Lazy loading

Compares eager and conditional pandas imports.

- `payload-simple.json`: request path does not need pandas.
- `payload-report.json`: request path does need pandas.

Use `sam build --use-container` so native dependencies are built for the Lambda target architecture.
