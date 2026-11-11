import hashlib
import json


def lambda_handler(event, context):
    value = event.get("message", "LazyTown").encode("utf-8")
    iterations = int(event.get("iterations", 250_000))
    for _ in range(iterations):
        value = hashlib.sha256(value).digest()
    return {"statusCode": 200, "body": json.dumps({"iterations": iterations, "hash": value.hex()})}
