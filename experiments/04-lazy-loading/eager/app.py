import json
import pandas as pd

def lambda_handler(event, context):
    request_type = event.get("type", "simple")

    if request_type == "simple":
        return {
            "statusCode": 200,
            "body": json.dumps({"mode": "simple", "ok": True}),
        }

    rows = event.get("rows", [])
    frame = pd.DataFrame(rows)
    total = int(frame["value"].sum()) if not frame.empty else 0

    return {
        "statusCode": 200,
        "body": json.dumps({"mode": "report", "total": total}),
    }


