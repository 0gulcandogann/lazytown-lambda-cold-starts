# 06 — Package diet

Same handler, different dependency footprint:

- `fat/`: pandas, numpy, requests, Pillow are packaged but not imported.
- `slim/`: no third-party requirements.

Build and inspect the SAM build directories:

```bash
sam build --use-container
./measure-package-size.sh
```
