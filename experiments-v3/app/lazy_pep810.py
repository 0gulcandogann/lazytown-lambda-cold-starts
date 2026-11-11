import json

lazy import pandas as pd  # PEP 810 (Python 3.15): bound now, loaded on first use


def lambda_handler(event, context):
    if event.get("type", "simple") == "simple":
        return {"statusCode": 200, "body": json.dumps({"mode": "simple", "ok": True})}

    frame = pd.DataFrame(event.get("rows", []))
    total = int(frame["value"].sum()) if not frame.empty else 0
    return {"statusCode": 200, "body": json.dumps({"mode": "report", "total": total})}
