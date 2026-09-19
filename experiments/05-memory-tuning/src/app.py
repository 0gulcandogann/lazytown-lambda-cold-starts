import hashlib
import json

DEFAULT_ITERATIONS = 250_000

def lambda_handler(event, context):
    message = event.get("message", "LazyTown")
    iterations = int(event.get("iterations", DEFAULT_ITERATIONS))

    value = message.encode("utf-8")

    for _ in range(iterations):
        value = hashlib.sha256(value).digest()

    return {
        "statusCode": 200,
        "body": json.dumps({
            "iterations": iterations,
            "hash": value.hex(),
        }),
    }
