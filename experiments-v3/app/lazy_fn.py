import json


def lambda_handler(event, context):
    if event.get("type", "simple") == "simple":
        return {"statusCode": 200, "body": json.dumps({"mode": "simple", "ok": True})}

    import pandas as pd  # paid only by the request that needs it

    frame = pd.DataFrame(event.get("rows", []))
    total = int(frame["value"].sum()) if not frame.empty else 0
    return {"statusCode": 200, "body": json.dumps({"mode": "report", "total": total})}
