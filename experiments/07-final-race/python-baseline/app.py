import hashlib
import json

# Intentionally eager/heavy baseline:
# This simulates a Python Lambda carrying application baggage it does not
# need for the selected simple request.
import pandas as pd  # noqa: F401
import requests      # noqa: F401

DEFAULT_ITERATIONS = 20_000

def lambda_handler(event, context):
    message = event.get("message", "LazyTown")
    iterations = int(event.get("iterations", DEFAULT_ITERATIONS))

    value = message.encode("utf-8")
    for _ in range(iterations):
        value = hashlib.sha256(value).digest()

    return {
        "statusCode": 200,
        "body": json.dumps({
            "hash": value.hex(),
            "iterations": iterations,
        }),
    }
