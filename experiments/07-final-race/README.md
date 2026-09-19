# 07 — Final race

Final SHA-256 workload used to compare a progressively optimized Python setup with a Go reference implementation.

Build Go first:

```bash
./build-go.sh
```

Then build and deploy the SAM stack:

```bash
sam build --use-container
sam deploy --guided
```

`go-build/bootstrap` is generated locally and intentionally ignored by Git.
